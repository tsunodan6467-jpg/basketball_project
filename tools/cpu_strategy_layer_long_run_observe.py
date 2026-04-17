"""
CPU クラブ戦略レイヤの長期観測（CLI・非対話・本体ロジック非改変）。

`generate_teams` → 全チーム CPU → 年次で Season + Offseason を静かに完走し、
各スナップショットで `get_cpu_club_strategy` のタグ分布と、履歴から読める
トレード獲得 / FA 署名の件数差分をざっくり集計する。

例:
  python tools/cpu_strategy_layer_long_run_observe.py --years 5 --seed 424242 \\
    --out reports/cpu_strategy_layer_longrun.txt

※ 観測専用。ゲーム本体やセーブ形式には触れない。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import Offseason  # noqa: E402
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.systems.cpu_club_strategy import get_cpu_club_strategy  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402


def _cpu_teams(teams: List[Any]) -> List[Any]:
    return [t for t in teams if not bool(getattr(t, "is_user_team", False))]


def _cum_trade_in(team: Any) -> int:
    n = 0
    for r in getattr(team, "history_transactions", None) or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("transaction_type", "")).lower() != "trade":
            continue
        note = str(r.get("note", "") or "").lower()
        if "trade_in" in note or "acquired from" in note:
            n += 1
    return n


def _cum_fa_sign(team: Any) -> int:
    n = 0
    for r in getattr(team, "history_transactions", None) or []:
        if not isinstance(r, dict):
            continue
        tt = str(r.get("transaction_type", "")).lower()
        if tt in ("free_agent", "free_agent_sign"):
            n += 1
    return n


def _roster_mean_age_ovr(team: Any) -> Tuple[Optional[float], Optional[float]]:
    ps = list(getattr(team, "players", None) or [])
    if not ps:
        return None, None
    ages = [float(getattr(p, "age", 0) or 0) for p in ps]
    ovrs = [float(getattr(p, "ovr", 0) or 0) for p in ps]
    return sum(ages) / len(ages), sum(ovrs) / len(ovrs)


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


def _strategy_counts(teams: List[Any]) -> Tuple[Dict[str, int], Dict[Tuple[int, str], int]]:
    """全体タグ件数と (league_level, tag) 件数。"""
    overall: Dict[str, int] = defaultdict(int)
    by_lv: Dict[Tuple[int, str], int] = defaultdict(int)
    for t in _cpu_teams(teams):
        tag = get_cpu_club_strategy(t).strategy_tag
        ll = int(getattr(t, "league_level", 2) or 2)
        overall[tag] += 1
        by_lv[(ll, tag)] += 1
    return dict(overall), dict(by_lv)


def _lines_strategy_block(
    label: str,
    overall: Dict[str, int],
    by_lv: Dict[Tuple[int, str], int],
) -> List[str]:
    lines = [f"\n=== {label} strategy_tag (CPU clubs) ==="]
    total = sum(overall.values()) or 1
    for tag in ("rebuild", "hold", "push"):
        c = int(overall.get(tag, 0))
        lines.append(f"  ALL {tag:7s} {c:3d}  ({100.0 * c / total:4.1f}%)")
    for lvl in (1, 2, 3):
        sub = sum(int(by_lv.get((lvl, tg), 0)) for tg in ("rebuild", "hold", "push"))
        if sub == 0:
            continue
        lines.append(f"  D{lvl} (n={sub})")
        for tag in ("rebuild", "hold", "push"):
            c = int(by_lv.get((lvl, tag), 0))
            lines.append(f"      {tag:7s} {c:3d}  ({100.0 * c / sub:4.1f}%)")
    return lines


def _lines_perf_by_tag(teams: List[Any]) -> List[str]:
    """現在の regular_wins をタグ別に平均（CPUのみ）。"""
    buckets: DefaultDict[str, List[int]] = defaultdict(list)
    for t in _cpu_teams(teams):
        tag = get_cpu_club_strategy(t).strategy_tag
        buckets[tag].append(int(getattr(t, "regular_wins", 0) or 0))
    lines = ["  regular_wins mean by strategy_tag (this snapshot):"]
    for tag in ("rebuild", "hold", "push"):
        xs = buckets.get(tag) or []
        if not xs:
            lines.append(f"    {tag}: (none)")
        else:
            lines.append(f"    {tag}: n={len(xs)} mean={statistics.mean(xs):.2f}")
    return lines


def _lines_roster_youth_by_tag(teams: List[Any]) -> List[str]:
    """ロスター平均年齢 / OVR をタグ別に（チーム平均の平均）。"""
    ages: DefaultDict[str, List[float]] = defaultdict(list)
    ovrs: DefaultDict[str, List[float]] = defaultdict(list)
    for t in _cpu_teams(teams):
        tag = get_cpu_club_strategy(t).strategy_tag
        ma, mo = _roster_mean_age_ovr(t)
        if ma is not None:
            ages[tag].append(ma)
        if mo is not None:
            ovrs[tag].append(mo)
    lines = ["  roster mean age / ovr (team means → mean by tag):"]
    for tag in ("rebuild", "hold", "push"):
        if ages[tag]:
            lines.append(
                f"    {tag}: teams={len(ages[tag])} age_mean={statistics.mean(ages[tag]):.2f} "
                f"ovr_mean={statistics.mean(ovrs[tag]):.2f}"
            )
        else:
            lines.append(f"    {tag}: (none)")
    return lines


def observe(*, years: int, seed: int, lines: List[str]) -> None:
    sim_rng_mod.init_simulation_random(int(seed))
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    prev_trade: Dict[int, int] = {}
    prev_fa: Dict[int, int] = {}
    prev_tag: Dict[int, str] = {}

    delta_trade_by_prev_tag: DefaultDict[str, List[int]] = defaultdict(list)
    delta_fa_by_prev_tag: DefaultDict[str, List[int]] = defaultdict(list)

    def snapshot(label: str, record_deltas: bool) -> None:
        nonlocal prev_trade, prev_fa, prev_tag
        o, blv = _strategy_counts(teams)
        lines.extend(_lines_strategy_block(label, o, blv))
        lines.extend(_lines_perf_by_tag(teams))
        lines.extend(_lines_roster_youth_by_tag(teams))

        if record_deltas and prev_tag:
            for t in _cpu_teams(teams):
                tid = int(getattr(t, "team_id", -1) or -1)
                ct, cf = _cum_trade_in(t), _cum_fa_sign(t)
                pt, pf = prev_trade.get(tid, 0), prev_fa.get(tid, 0)
                tag0 = prev_tag.get(tid, "hold")
                delta_trade_by_prev_tag[tag0].append(ct - pt)
                delta_fa_by_prev_tag[tag0].append(cf - pf)

        prev_trade = {int(getattr(t, "team_id", -1) or -1): _cum_trade_in(t) for t in _cpu_teams(teams)}
        prev_fa = {int(getattr(t, "team_id", -1) or -1): _cum_fa_sign(t) for t in _cpu_teams(teams)}
        prev_tag = {int(getattr(t, "team_id", -1) or -1): get_cpu_club_strategy(t).strategy_tag for t in _cpu_teams(teams)}

    lines.append(f"CPU strategy layer long-run observe | seed={seed} years={years}")
    snapshot("opening", record_deltas=False)

    for y in range(1, years + 1):
        lines.append(f"\n--- Season {y} (quiet) ---")
        season = _run_season_quiet(teams, free_agents)
        free_agents = list(getattr(season, "free_agents", []) or [])
        lines.append(f"--- after_season_y{y} ---")
        snapshot(f"after_season_y{y}", record_deltas=True)

        lines.append(f"--- Offseason {y} (quiet) ---")
        _offseason_quiet(teams, free_agents)
        lines.append(f"--- after_offseason_y{y} ---")
        snapshot(f"after_offseason_y{y}", record_deltas=True)

    lines.append("\n=== Cumulative deltas by strategy_tag at previous snapshot (per team, then mean) ===")
    lines.append(
        "Interpretation: after each snapshot, compare new history rows vs previous counts; "
        "attribute delta to tag observed on the team at the **previous** snapshot."
    )
    for tag in ("rebuild", "hold", "push"):
        dt = delta_trade_by_prev_tag.get(tag) or []
        df = delta_fa_by_prev_tag.get(tag) or []
        mt = statistics.mean(dt) if dt else 0.0
        mf = statistics.mean(df) if df else 0.0
        lines.append(f"  prev_tag={tag}: teams={len(dt)} d_trade_in_mean={mt:.3f} d_fa_sign_mean={mf:.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU strategy layer long-run observer")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42_424_242)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "cpu_strategy_layer_longrun.txt",
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
