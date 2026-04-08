#!/usr/bin/env python3
"""
Observe S6 tiny offers over real save or simulated league state (not wired to production).

Uses `_calculate_offer_diagnostic` only. Run from repo root:

  python tools/fa_offer_real_distribution_observer.py
  python tools/fa_offer_real_distribution_observer.py --save path/to/file.sav
  python tools/fa_offer_real_distribution_observer.py --seasons 1 --seed 42

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
        help="Path to .sav file (pickle). If set, skip world generation.",
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
    return p.parse_args()


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


def _select_fa_sample(free_agents: List[Player], cap: int) -> List[Player]:
    pool = [p for p in free_agents if getattr(p, "team_id", None) is None]
    if not pool:
        pool = list(free_agents)
    pool.sort(key=_fa_salary, reverse=True)
    return pool[: max(1, cap)]


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


def _aggregate(rows: List[Dict[str, Any]]) -> None:
    buf = _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    n = len(rows)
    n_s1 = sum(1 for r in rows if r["soft_cap_early"])
    n_zero = sum(1 for r in rows if r["final_offer"] == 0)
    n_tiny = sum(1 for r in rows if 0 < r["final_offer"] <= TINY_MAX)
    n_le_3m = sum(1 for r in rows if 0 < r["final_offer"] <= BAND_3M)
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
    print("---")
    print(f"total_samples (team x fa): {n}")
    print(f"soft_cap_early True:       {n_s1} ({pct(n_s1)})")
    print(f"final_offer == 0:          {n_zero} ({pct(n_zero)})")
    print(f"0 < final <= {TINY_MAX}:        {n_tiny} ({pct(n_tiny)})")
    print(f"0 < final <= {BAND_3M}:        {n_le_3m} ({pct(n_le_3m)})")
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


def main() -> None:
    args = _parse_args()
    if args.save:
        teams, fas = _load_teams_fas_from_save(Path(args.save))
    else:
        teams, fas = _build_simulated_world(args)

    if not teams:
        print("no teams; abort")
        return

    _sync_payroll_budget_with_roster_payroll(teams)
    _sync_payroll_budget_with_roster_payroll(teams)

    fa_sample = _select_fa_sample(fas, args.fa_cap)
    rows = _run_matrix(teams, fa_sample)
    _aggregate(rows)


if __name__ == "__main__":
    main()
