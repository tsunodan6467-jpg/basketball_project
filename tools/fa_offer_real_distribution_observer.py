#!/usr/bin/env python3
"""
Observe S6 tiny offers over real save or simulated league state (not wired to production).

Uses `_calculate_offer_diagnostic` only. Run from repo root:

  python tools/fa_offer_real_distribution_observer.py
  python tools/fa_offer_real_distribution_observer.py --save path/to/file.sav
  python tools/fa_offer_real_distribution_observer.py --seasons 1 --seed 42
  python tools/fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy
  python tools/fa_offer_real_distribution_observer.py --save-list a.sav b.sav

Optional population modes (default unchanged): see docs/FA_OBSERVER_MATRIX_REDESIGN_PLAN_2026-04.md

See docs/FA_S6_TINY_OFFER_DECISION_MEMO_2026-04.md
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.models.offseason import (  # noqa: E402
    _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER,
    _sync_payroll_budget_with_roster_payroll,
)
from basketball_sim.models.player import Player  # noqa: E402
from basketball_sim.models.team import Team  # noqa: E402
from basketball_sim.persistence.save_load import load_world, validate_payload  # noqa: E402
from basketball_sim.systems import free_agency as fa_mod  # noqa: E402
from basketball_sim.utils.sim_rng import init_simulation_random  # noqa: E402

TINY_MAX = 300_000
BAND_3M = 3_000_000
BAND_10M = 10_000_000
HIGH_SALARY = 50_000_000


class _SilentWriter:
    def write(self, _data: str) -> int:
        return len(_data)

    def flush(self) -> None:
        return None


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FA offer diagnostic distribution observer")
    p.add_argument(
        "--save",
        type=str,
        default="",
        help="Path to .sav file (pickle). If set, skip world generation. "
        "Mutually exclusive with --save-list.",
    )
    p.add_argument(
        "--save-list",
        nargs="+",
        default=None,
        metavar="PATH",
        help="Run observer once per .sav path, in order (same population-mode / fa-cap as single run). "
        "Mutually exclusive with --save.",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed for simulated world")
    p.add_argument(
        "--fa-cap",
        type=int,
        default=40,
        help="Top N free agents by salary to pair with each team",
    )
    p.add_argument(
        "--seasons",
        type=int,
        default=0,
        help="If >0, run Season.simulate_to_end() this many times after world build (slow)",
    )
    p.add_argument(
        "--population-mode",
        choices=("default", "mixed_mid_fa_roomy"),
        default="default",
        help="default: top fa-cap FAs by salary x all teams (legacy). "
        "mixed_mid_fa_roomy: FA salary rank band + optional top-N roomiest teams.",
    )
    p.add_argument(
        "--fa-rank-start",
        type=int,
        default=11,
        help="1-based inclusive start rank by FA salary (desc). Used only when --population-mode mixed_mid_fa_roomy.",
    )
    p.add_argument(
        "--fa-rank-end",
        type=int,
        default=50,
        help="1-based inclusive end rank by FA salary (desc). Used only when --population-mode mixed_mid_fa_roomy.",
    )
    p.add_argument(
        "--roomy-team-count",
        type=int,
        default=0,
        help="If >0, keep only this many teams with largest (payroll_budget - roster payroll). "
        "0 means all teams. Used only when --population-mode mixed_mid_fa_roomy.",
    )
    return p.parse_args()


def _check_save_args_exclusive(save: str, save_list: Optional[List[str]]) -> Optional[str]:
    if save and save_list is not None:
        return "use either --save or --save-list, not both"
    return None


def _load_teams_fas_from_save(path: Path) -> Tuple[List[Team], List[Player]]:
    payload = load_world(path)
    validate_payload(payload)
    teams = list(payload.get("teams") or [])
    fas = list(payload.get("free_agents") or [])
    return teams, fas


def _build_simulated_world(args: argparse.Namespace) -> Tuple[List[Team], List[Player]]:
    from basketball_sim.main import (
        CITY_MARKET_SIZE,
        apply_user_team_to_league,
        assign_fictional_teams_and_rival,
        auto_draft_players,
        choose_icon_player_auto,
        create_fictional_player_pool,
        create_icon_player,
    )
    from basketball_sim.models.season import Season
    from basketball_sim.systems.generator import generate_teams

    init_simulation_random(args.seed)
    silent = _SilentWriter()
    with contextlib.redirect_stdout(silent):
        home = "東京" if "東京" in CITY_MARKET_SIZE else next(iter(CITY_MARKET_SIZE.keys()))
        market = float(CITY_MARKET_SIZE.get(home, 1.0))
        teams = generate_teams()
        user_team = apply_user_team_to_league(teams, "ObserverClub", home, market)
        icon_player = create_icon_player(choose_icon_player_auto())
        pool = create_fictional_player_pool()
        auto_draft_players(pool, user_team, icon_player)
        free_agents: List[Player] = []
        assign_fictional_teams_and_rival(teams, user_team, pool, free_agents)

        if args.seasons > 0:
            season = Season(teams, free_agents)
            for _ in range(args.seasons):
                season.simulate_to_end()

    return teams, free_agents


def _fa_salary(p: Player) -> int:
    try:
        return max(0, int(getattr(p, "salary", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _fa_pool_by_salary_desc(free_agents: List[Player]) -> List[Player]:
    pool = [p for p in free_agents if getattr(p, "team_id", None) is None]
    if not pool:
        pool = list(free_agents)
    pool.sort(key=_fa_salary, reverse=True)
    return pool


def _select_fa_sample(free_agents: List[Player], cap: int) -> List[Player]:
    pool = _fa_pool_by_salary_desc(free_agents)
    return pool[: max(1, cap)]


def _select_fa_sample_by_salary_rank(
    free_agents: List[Player],
    rank_start: int,
    rank_end: int,
) -> List[Player]:
    """1-based inclusive ranks on salary-descending FA pool (same pool as legacy top-N)."""
    pool = _fa_pool_by_salary_desc(free_agents)
    if not pool:
        return []
    rs = max(1, int(rank_start))
    re = max(rs, int(rank_end))
    rs_c = min(rs, len(pool))
    re_c = min(re, len(pool))
    if rs_c > re_c:
        return []
    # inclusive ranks [rs_c, re_c] -> slice [rs_c - 1 : re_c]
    return pool[rs_c - 1 : re_c]


def _team_roster_payroll(team: Team) -> int:
    return int(
        sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in getattr(team, "players", []) or [])
    )


def _team_payroll_room(team: Team) -> int:
    budget = int(getattr(team, "payroll_budget", 0) or 0)
    return max(0, budget - _team_roster_payroll(team))


def _select_teams_by_room(teams: List[Team], top_n: int) -> List[Team]:
    if top_n <= 0:
        return list(teams)
    n = min(int(top_n), len(teams))
    if n <= 0:
        return []
    sorted_teams = sorted(
        teams,
        key=lambda t: (-_team_payroll_room(t), -int(getattr(t, "team_id", 0))),
    )
    return sorted_teams[:n]


def _run_matrix(
    teams: List[Team],
    fa_sample: List[Player],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team in teams:
        for fa in fa_sample:
            d = fa_mod._calculate_offer_diagnostic(team, fa)
            lv = int(d.get("league_level") or getattr(team, "league_level", 1) or 1)
            lv = max(1, min(3, lv))
            fo = int(d["final_offer"])
            se = bool(d["soft_cap_early"])
            rtb = d.get("room_to_budget")
            rtb_i: Optional[int] = int(rtb) if rtb is not None else None
            sal = _fa_salary(fa)
            rows.append(
                {
                    "team_name": getattr(team, "name", "?"),
                    "team_id": int(getattr(team, "team_id", -1)),
                    "league_level": lv,
                    "soft_cap_early": se,
                    "final_offer": fo,
                    "room_to_budget": rtb_i,
                    "payroll_before": int(d["payroll_before"]),
                    "payroll_budget": _payroll_budget_display(team, d),
                    "fa_salary": sal,
                    "fa_id": int(getattr(fa, "player_id", 0)),
                    "diag": d,
                }
            )
    return rows


def _payroll_budget_display(team: Team, d: Dict[str, Any]) -> int:
    v = d.get("payroll_budget")
    if v is not None:
        return int(v)
    return int(getattr(team, "payroll_budget", 0) or 0)


def _aggregate(rows: List[Dict[str, Any]], population_banner: str = "") -> None:
    buf = _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    n = len(rows)
    n_s1 = sum(1 for r in rows if r["soft_cap_early"])
    n_zero = sum(1 for r in rows if r["final_offer"] == 0)
    n_tiny = sum(1 for r in rows if 0 < r["final_offer"] <= TINY_MAX)
    n_le_3m = sum(1 for r in rows if 0 < r["final_offer"] <= BAND_3M)
    n_le_10m = sum(1 for r in rows if 0 < r["final_offer"] <= BAND_10M)
    n_le_buffer = sum(1 for r in rows if 0 < r["final_offer"] <= buf)
    n_final_eq_buffer = sum(1 for r in rows if r["final_offer"] == buf)
    n_final_open_lt_buffer = sum(1 for r in rows if 0 < r["final_offer"] < buf)
    n_final_gt_buffer = sum(1 for r in rows if r["final_offer"] > buf)
    n_s6_tiny = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    )
    n_s6_le_3m = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= BAND_3M
    )
    n_s6_le_10m = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= BAND_10M
    )
    n_s6_le_buffer = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= buf
    )
    n_room_le = sum(
        1
        for r in rows
        if r["room_to_budget"] is not None and r["room_to_budget"] <= TINY_MAX
    )
    n_high_tiny = sum(
        1
        for r in rows
        if (not r["soft_cap_early"])
        and 0 < r["final_offer"] <= TINY_MAX
        and r["fa_salary"] >= HIGH_SALARY
    )

    by_lv = Counter(r["league_level"] for r in rows)
    by_lv_s6_tiny = Counter(
        r["league_level"] for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    )

    def pct(x: int) -> str:
        if n <= 0:
            return "0.00%"
        return f"{100.0 * x / n:.2f}%"

    print("FA offer real/sim distribution observer (_calculate_offer_diagnostic)")
    if population_banner:
        print(population_banner)
    print("---")
    print(f"total_samples (team x fa): {n}")
    print(f"soft_cap_early True:       {n_s1} ({pct(n_s1)})")
    print(f"final_offer == 0:          {n_zero} ({pct(n_zero)})")
    print(f"0 < final <= {TINY_MAX}:        {n_tiny} ({pct(n_tiny)})")
    print(f"0 < final <= {BAND_3M}:        {n_le_3m} ({pct(n_le_3m)})")
    print(f"0 < final <= {BAND_10M}:       {n_le_10m} ({pct(n_le_10m)})")
    print(f"0 < final <= buffer ({buf:,}): {n_le_buffer} ({pct(n_le_buffer)})")
    print(f"final_offer == buffer ({buf:,}): {n_final_eq_buffer} ({pct(n_final_eq_buffer)})")
    print(f"0 < final_offer < buffer:        {n_final_open_lt_buffer} ({pct(n_final_open_lt_buffer)})")
    print(f"final_offer > buffer:            {n_final_gt_buffer} ({pct(n_final_gt_buffer)})")
    print(
        "soft_cap_early False & "
        f"0 < final <= {TINY_MAX}: {n_s6_tiny} ({pct(n_s6_tiny)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= {BAND_3M}: {n_s6_le_3m} ({pct(n_s6_le_3m)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= {BAND_10M}: {n_s6_le_10m} ({pct(n_s6_le_10m)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= buffer: {n_s6_le_buffer} ({pct(n_s6_le_buffer)})"
    )
    print(
        "room_to_budget not None & "
        f"<= {TINY_MAX}:          {n_room_le} ({pct(n_room_le)})"
    )
    print(
        f"high FA (sal>={HIGH_SALARY}) & S6-tiny: {n_high_tiny} ({pct(n_high_tiny)})"
    )
    print("---")
    print("samples by team league_level (all pairs):")
    for lv in (1, 2, 3):
        c = by_lv.get(lv, 0)
        print(f"  D{lv}: {c} ({pct(c)})")
    print("S6-tiny pairs by team league_level:")
    for lv in (1, 2, 3):
        c = by_lv_s6_tiny.get(lv, 0)
        print(f"  D{lv}: {c}")
    print("---")
    tiny_rows = [
        r
        for r in rows
        if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    ]
    tiny_rows.sort(key=lambda r: (-r["fa_salary"], -r["final_offer"]))
    print("sample S6-tiny cases (up to 5):")
    for i, r in enumerate(tiny_rows[:5]):
        print(f"  [{i + 1}] team={r['team_name']} id={r['team_id']} league=D{r['league_level']}")
        print(f"      payroll_before={r['payroll_before']:,}")
        print(f"      payroll_budget={r['payroll_budget']:,}")
        print(f"      room_to_budget={r['room_to_budget']}")
        print(f"      fa_salary={r['fa_salary']:,} fa_id={r['fa_id']}")
        print(f"      final_offer={r['final_offer']:,} soft_cap_early={r['soft_cap_early']}")


def _run_one_observation(args: argparse.Namespace, *, save_path: Optional[str]) -> bool:
    """Load or build world, run matrix, print aggregate. Returns False on abort."""
    if save_path:
        sp = Path(save_path)
        if not sp.is_file():
            print(f"save file not found: {sp}")
            return False
        teams, fas = _load_teams_fas_from_save(sp)
    else:
        teams, fas = _build_simulated_world(args)

    if not teams:
        print("no teams; abort")
        return False

    _sync_payroll_budget_with_roster_payroll(teams)
    _sync_payroll_budget_with_roster_payroll(teams)

    population_banner = ""
    if args.population_mode == "default":
        fa_sample = _select_fa_sample(fas, args.fa_cap)
        team_subset = teams
    else:
        if args.fa_rank_end < args.fa_rank_start:
            print("fa-rank-end must be >= fa-rank-start; abort")
            return False
        fa_sample = _select_fa_sample_by_salary_rank(fas, args.fa_rank_start, args.fa_rank_end)
        if not fa_sample:
            print("no FAs in selected salary-rank band; abort")
            return False
        team_subset = _select_teams_by_room(teams, args.roomy_team_count)
        if not team_subset:
            print("no teams after room filter; abort")
            return False
        rtc = args.roomy_team_count
        rtc_note = "all teams" if rtc <= 0 else f"top {min(rtc, len(teams))} by payroll room"
        population_banner = (
            f"population_mode={args.population_mode} "
            f"fa_salary_ranks={args.fa_rank_start}-{args.fa_rank_end} ({len(fa_sample)} FAs) "
            f"teams={len(team_subset)} ({rtc_note})"
        )

    rows = _run_matrix(team_subset, fa_sample)
    _aggregate(rows, population_banner=population_banner)
    return True


def main() -> None:
    args = _parse_args()
    err = _check_save_args_exclusive(args.save, args.save_list)
    if err:
        print(err, file=sys.stderr)
        sys.exit(2)

    if args.save_list is not None:
        total = len(args.save_list)
        for i, path in enumerate(args.save_list, start=1):
            print()
            print("=" * 72)
            print(f"# save [{i}/{total}]: {path}")
            print("=" * 72)
            if not _run_one_observation(args, save_path=path):
                sys.exit(1)
        return

    save_path = args.save if args.save else None
    if not _run_one_observation(args, save_path=save_path):
        sys.exit(1)


if __name__ == "__main__":
    main()
