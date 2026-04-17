"""
CPU 戦略タグ別の「トレード獲得選手」品質観測（CLI・非対話・本体非改変）。

獲得履歴が記録される瞬間の `get_cpu_club_strategy(獲得側チーム)` でタグ分類（推奨A）。

例:
  python tools/cpu_strategy_trade_quality_observe.py --years 5 --seed 424242 \\
    --out reports/cpu_strategy_trade_quality_y5_s424242.txt
"""

from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Tuple

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
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402

_POT_SCORE = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0, "E": 0}


def _pot_score(player: Any) -> int:
    p = str(getattr(player, "potential", "") or "").strip().upper()[:1]
    return int(_POT_SCORE.get(p, 0))


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


def _install_trade_acquire_hook(
    rows_by_tag: DefaultDict[str, List[Dict[str, Any]]],
) -> Tuple[Callable[..., Any], Callable[..., Any]]:
    """戻り値: (original_method, wrapper) 復元用。"""
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
        age = int(getattr(player, "age", 0) or 0)
        ovr = int(getattr(player, "ovr", 0) or 0)
        pot = _pot_score(player)
        young = age <= 24
        gem = young and str(getattr(player, "potential", "") or "").strip().upper()[:1] in ("S", "A")
        rows_by_tag[tag].append(
            {
                "age": age,
                "ovr": ovr,
                "pot": pot,
                "young": young,
                "gem": gem,
                "team_id": int(getattr(self, "team_id", -1) or -1),
                "player_id": int(getattr(player, "player_id", -1) or -1),
            }
        )

    Team.add_history_transaction = wrapped  # type: ignore[method-assign]
    return orig, wrapped


def _tag_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "mean_age": None,
            "p50_age": None,
            "mean_ovr": None,
            "p50_ovr": None,
            "age_le24_rate": None,
            "young_sa_rate": None,
            "mean_pot": None,
        }
    ages = [int(r["age"]) for r in rows]
    ovrs = [int(r["ovr"]) for r in rows]
    pots = [int(r["pot"]) for r in rows]
    young_n = sum(1 for r in rows if r["young"])
    gem_n = sum(1 for r in rows if r["gem"])
    n = len(rows)
    return {
        "n": n,
        "mean_age": statistics.mean(ages),
        "p50_age": statistics.median(ages),
        "mean_ovr": statistics.mean(ovrs),
        "p50_ovr": statistics.median(ovrs),
        "age_le24_rate": 100.0 * young_n / n,
        "young_sa_rate": 100.0 * gem_n / n,
        "mean_pot": statistics.mean(pots),
    }


def _lines_from_metrics(m: Dict[str, Any]) -> List[str]:
    if m["n"] == 0:
        return ["  (no acquisitions)"]
    return [
        f"  n={m['n']}",
        f"  mean_age={m['mean_age']:.2f}  p50_age={m['p50_age']:.1f}",
        f"  mean_ovr={m['mean_ovr']:.2f}  p50_ovr={m['p50_ovr']:.1f}",
        f"  age<=24_rate={m['age_le24_rate']:.1f}%",
        f"  young_high_pot_SA_rate={m['young_sa_rate']:.1f}%  (age<=24 & potential S/A)",
        f"  mean_potential_score={m['mean_pot']:.2f}  (S=4..C=1 proxy)",
    ]


def run_trade_quality_observe(years: int, seed: int) -> Dict[str, Any]:
    """
    1 seed 分のシムを実行し、タグ別トレード獲得の集計 dict を返す（CLI 以外からも利用可）。
    """
    years = max(1, min(8, int(years)))
    seed = int(seed)
    rows_by_tag: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    orig, _wr = _install_trade_acquire_hook(rows_by_tag)
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

        all_rows = [r for xs in rows_by_tag.values() for r in xs]
        by_tag = {tag: _tag_metrics(rows_by_tag[tag]) for tag in ("push", "hold", "rebuild")}
        return {
            "seed": seed,
            "years": years,
            "total": len(all_rows),
            "by_tag": by_tag,
        }
    finally:
        Team.add_history_transaction = orig  # type: ignore[method-assign]


def trade_quality_report_lines(data: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    lines.append(
        f"CPU strategy trade quality observe | seed={data['seed']} years={data['years']}\n"
        "Classification: strategy_tag on acquiring CPU team at add_history_transaction time (trade in).\n"
    )
    for y in range(1, int(data["years"]) + 1):
        lines.append(f"--- completed sim year {y} ---")
    lines.append(f"\nTotal trade player acquisitions (CPU, incoming): {data['total']}")
    for tag in ("push", "hold", "rebuild"):
        lines.append(f"\n=== tag={tag} ===")
        lines.extend(_lines_from_metrics(data["by_tag"][tag]))
    lines.append("\n=== Cross-tag comparison (same metrics) ===")
    for tag in ("push", "hold", "rebuild"):
        lines.append(f"  {tag}: n={data['by_tag'][tag]['n']}")
    return lines


def observe(*, years: int, seed: int, lines: List[str]) -> None:
    data = run_trade_quality_observe(years, seed)
    lines.extend(trade_quality_report_lines(data))


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU strategy trade acquisition quality observer")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42_424_242)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "cpu_strategy_trade_quality.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    lines: List[str] = []
    observe(years=years, seed=int(args.seed), lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
