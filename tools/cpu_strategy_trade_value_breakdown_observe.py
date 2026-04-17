"""
トレード獲得成立時に、TradeSystem.calculate_player_trade_value と同型の内訳を集計する。

獲得側 CPU チームの strategy_tag（獲得時点）で分類。本体は変更せず Team.add_history_transaction を一時ラップ。

内訳は trade_logic.calculate_player_trade_value と数式を揃える（コメントで対応行を明記）。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import Offseason  # noqa: E402
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.models.team import Team  # noqa: E402
from basketball_sim.systems.cpu_club_strategy import get_cpu_club_strategy  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.systems.trade_logic import TradeSystem  # noqa: E402
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402

_POTENTIAL_BONUS = {"S": 5.0, "A": 3.5, "B": 2.0, "C": 0.8, "D": 0.0}


def breakdown_trade_value(ts: TradeSystem, player: Any, team: Any) -> Dict[str, float]:
    ovr = float(getattr(player, "ovr", 50) or 50)
    age = float(getattr(player, "age", 25) or 25)
    potential = str(getattr(player, "potential", "C") or "C").upper()
    popularity = float(getattr(player, "popularity", 50) or 50)
    is_icon = bool(getattr(player, "is_icon", False))
    icon_locked = bool(getattr(player, "icon_locked", False))
    injured = bool(player.is_injured())

    m_fut = float(ts._cpu_future_value_trade_multiplier(team))
    try:
        raw_fvw = float(get_cpu_club_strategy(team, None).future_value_weight)
    except Exception:
        raw_fvw = 1.0

    ovr_term = ovr * 1.35
    youth_peak_raw = max(0.0, 28.0 - abs(age - 27.0)) * 0.40
    youth_peak_term = youth_peak_raw * m_fut
    contract = float(ts._get_contract_score(player))
    ac = float(ts._get_age_curve_bonus(player, team))
    future_pos_ac = max(0.0, ac)
    future_neg_ac = ac - future_pos_ac
    age_pos_term = future_pos_ac * m_fut
    age_neg_term = future_neg_ac
    pot_raw = float(_POTENTIAL_BONUS.get(potential, 0.0))
    pot_term = pot_raw * m_fut
    pop_term = max(0.0, popularity - 50.0) * 0.05
    icon_term = 12.0 if (is_icon or icon_locked) else 0.0
    inj_term = -4.0 if injured else 0.0

    fut_delta = (youth_peak_raw + pot_raw + future_pos_ac) * (m_fut - 1.0)

    total_calc = (
        ovr_term
        + youth_peak_term
        + contract
        + pot_term
        + age_pos_term
        + age_neg_term
        + pop_term
        + icon_term
        + inj_term
    )
    total_official = float(ts.calculate_player_trade_value(player, team))
    return {
        "ovr_term": ovr_term,
        "youth_peak_raw": youth_peak_raw,
        "youth_peak_term": youth_peak_term,
        "contract": contract,
        "age_pos_raw": future_pos_ac,
        "age_neg_raw": future_neg_ac,
        "age_pos_term": age_pos_term,
        "age_neg_term": age_neg_term,
        "pot_raw": pot_raw,
        "pot_term": pot_term,
        "pop_term": pop_term,
        "icon_term": icon_term,
        "inj_term": inj_term,
        "m_fut": m_fut,
        "raw_fvw": raw_fvw,
        "fut_delta_on_scaled_parts": fut_delta,
        "total_parts": round(total_calc, 2),
        "total_official": total_official,
    }


def _run_season_quiet(teams: List[Any], free_agents: List[Any]) -> Season:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        season = Season(teams, free_agents)
        safety = 0
        cap = max(500, int(getattr(season, "total_rounds", 0) or 0) + 400)
        while not bool(getattr(season, "season_finished", False)):
            season.simulate_next_round()
            safety += 1
            if safety > cap:
                raise RuntimeError(f"season loop exceeded cap={cap}")
    return season


def _offseason_quiet(teams: List[Any], free_agents: List[Any]) -> Offseason:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        off = Offseason(teams, free_agents)
        off.run()
    return off


def _install_hook(
    rows_by_tag: DefaultDict[str, List[Dict[str, Any]]],
    ts: TradeSystem,
) -> Any:
    orig = Team.add_history_transaction

    def wrapped(
        self: Any,
        transaction_type: str,
        player: Any = None,
        note: str = "",
        *,
        trade_cash_delta: Optional[int] = None,
        trade_counterparty_team_id: Optional[int] = None,
        trade_counterparty_name: str = "",
    ) -> None:
        orig(
            self,
            transaction_type,
            player,
            note,
            trade_cash_delta=trade_cash_delta,
            trade_counterparty_team_id=trade_counterparty_team_id,
            trade_counterparty_name=trade_counterparty_name,
        )
        if player is None:
            return
        if bool(getattr(self, "is_user_team", False)):
            return
        if str(transaction_type or "").lower() != "trade":
            return
        nl = str(note or "").lower()
        if "acquired from" not in nl and "trade_in" not in nl:
            return
        try:
            tag = get_cpu_club_strategy(self).strategy_tag
        except Exception:
            return
        if tag not in ("rebuild", "hold", "push"):
            return
        bd = breakdown_trade_value(ts, player, self)
        bd["tag"] = tag
        bd["seed"] = None  # filled by caller
        rows_by_tag[tag].append(bd)

    Team.add_history_transaction = wrapped  # type: ignore[method-assign]
    return orig


def _aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"n": 0}
    keys = [
        "ovr_term",
        "youth_peak_raw",
        "youth_peak_term",
        "contract",
        "age_pos_raw",
        "age_neg_raw",
        "age_pos_term",
        "age_neg_term",
        "pot_raw",
        "pot_term",
        "pop_term",
        "m_fut",
        "raw_fvw",
        "fut_delta_on_scaled_parts",
        "total_official",
    ]
    out: Dict[str, Any] = {"n": len(rows)}
    for k in keys:
        vals = [float(r[k]) for r in rows]
        out[f"mean_{k}"] = round(statistics.mean(vals), 4)
        out[f"p50_{k}"] = round(statistics.median(vals), 4)
    mismatch = sum(1 for r in rows if abs(float(r["total_parts"]) - float(r["total_official"])) > 0.02)
    out["parts_vs_official_mismatch_n"] = mismatch
    return out


def run_breakdown_observe(years: int, seed: int) -> Dict[str, Any]:
    years = max(1, min(8, int(years)))
    seed = int(seed)
    rows_by_tag: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    ts = TradeSystem()
    orig = _install_hook(rows_by_tag, ts)
    try:
        sim_rng_mod.init_simulation_random(seed)
        with contextlib.redirect_stdout(io.StringIO()):
            teams = generate_teams()
        for t in teams:
            if hasattr(t, "is_user_team"):
                t.is_user_team = False
        free_agents: List[Any] = []
        sync_player_id_counter_from_world(teams, free_agents)
        for _y in range(1, years + 1):
            season = _run_season_quiet(teams, free_agents)
            free_agents = list(getattr(season, "free_agents", []) or [])
            _offseason_quiet(teams, free_agents)
        for tag in rows_by_tag:
            for r in rows_by_tag[tag]:
                r["seed"] = seed
        all_rows = [r for xs in rows_by_tag.values() for r in xs]
        by_tag = {t: _aggregate(rows_by_tag[t]) for t in ("push", "hold", "rebuild")}
        return {
            "seed": seed,
            "years": years,
            "total": len(all_rows),
            "by_tag": by_tag,
        }
    finally:
        Team.add_history_transaction = orig  # type: ignore[method-assign]


def report_lines(data: Dict[str, Any]) -> List[str]:
    lines = [
        f"CPU strategy trade VALUE breakdown | seed={data['seed']} years={data['years']}",
        "Per incoming CPU trade player: components mirror trade_logic.calculate_player_trade_value.",
        "fut_delta_on_scaled_parts = (youth_peak_raw + pot_raw + age_pos_raw) * (m_fut - 1)",
        f"Total acquisitions recorded: {data['total']}",
        "",
    ]
    for tag in ("push", "hold", "rebuild"):
        lines.append(f"=== tag={tag} ===")
        agg = data["by_tag"][tag]
        if agg["n"] == 0:
            lines.append("  (none)")
            continue
        lines.append(f"  n={agg['n']}  parts_vs_official_mismatch_n={agg.get('parts_vs_official_mismatch_n', 0)}")
        for k in (
            "mean_ovr_term",
            "mean_youth_peak_raw",
            "mean_youth_peak_term",
            "mean_contract",
            "mean_age_pos_raw",
            "mean_age_neg_raw",
            "mean_age_pos_term",
            "mean_age_neg_term",
            "mean_pot_raw",
            "mean_pot_term",
            "mean_pop_term",
            "mean_m_fut",
            "mean_raw_fvw",
            "mean_fut_delta_on_scaled_parts",
            "mean_total_official",
        ):
            if k in agg:
                lines.append(f"  {k}: {agg[k]}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--out", type=Path, default=Path("reports") / "cpu_strategy_trade_value_breakdown.txt")
    args = ap.parse_args()
    data = run_breakdown_observe(int(args.years), int(args.seed))
    text = "\n".join(report_lines(data)) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
