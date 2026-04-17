#!/usr/bin/env python3
"""
新規開始に近い世界を seed 固定で構築し、全48クラブの所持金を
「開始直後」と「N ラウンド進行後」で比較する調査用ツール。

用法:
  python tools/inspect_team_money_after_5_rounds.py --seed 424242 --rounds 5 --out reports/team_money_after_5_rounds_seed424242.txt

注意: `build_initial_game_world` の対話は使わず、inspect 系と同型の
generate_teams → apply_user_team_to_league → 自動編成 → v11 年俸 →
assign_fictional → normalize を再現する（調査専用）。
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _snapshot_money(teams: List[Any]) -> Dict[int, int]:
    return {int(getattr(t, "team_id", 0)): int(getattr(t, "money", 0) or 0) for t in teams}


def _build_world_like_new_game(seed: int) -> Tuple[List[Any], List[Any], Any]:
    from basketball_sim.main import (
        CITY_MARKET_SIZE,
        apply_user_team_to_league,
        assign_fictional_teams_and_rival,
        auto_draft_players,
        choose_icon_player_auto_from_league,
        create_icon_player,
    )
    from basketball_sim.systems.contract_logic import normalize_initial_payrolls_for_teams
    from basketball_sim.systems.generator import generate_fictional_player_pool, generate_teams
    from basketball_sim.systems.opening_roster_salary_v11 import (
        apply_user_team_opening_payroll_v11_if_roster_complete,
    )
    from basketball_sim.utils.sim_rng import init_simulation_random

    init_simulation_random(seed)
    teams = generate_teams()
    user_team = apply_user_team_to_league(
        teams,
        "Survey FC",
        "東京",
        float(CITY_MARKET_SIZE["東京"]),
    )

    icon_data = choose_icon_player_auto_from_league(teams)
    st = icon_data.get("team") if isinstance(icon_data, dict) else None
    sp = icon_data.get("player") if isinstance(icon_data, dict) else None
    if st is not None and sp is not None and sp in getattr(st, "players", []):
        st.remove_player(sp)
    icon_player = create_icon_player(icon_data)
    pool = list(generate_fictional_player_pool(180))
    auto_draft_players(pool, user_team, icon_player)
    apply_user_team_opening_payroll_v11_if_roster_complete(user_team)

    free_agents: List[Any] = []
    assign_fictional_teams_and_rival(teams, user_team, pool, free_agents)
    normalize_initial_payrolls_for_teams(teams)
    return teams, free_agents, user_team


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/team_money_after_5_rounds_seed424242.txt"),
    )
    args = ap.parse_args()

    from basketball_sim.models.season import Season

    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            teams, free_agents, _user_team = _build_world_like_new_game(args.seed)

    start = _snapshot_money(teams)

    with open(os.devnull, "w", encoding="utf-8") as dn2:
        with contextlib.redirect_stdout(dn2), contextlib.redirect_stderr(dn2):
            season = Season(teams, free_agents)
            season.simulate_multiple_rounds(max(0, int(args.rounds)))

    after = _snapshot_money(teams)

    rows: List[Dict[str, Any]] = []
    for t in sorted(teams, key=lambda x: int(getattr(x, "team_id", 0))):
        tid = int(getattr(t, "team_id", 0))
        lv = int(getattr(t, "league_level", 0) or 0)
        nm = str(getattr(t, "name", ""))
        s0 = start.get(tid, 0)
        s1 = after.get(tid, 0)
        rows.append(
            {
                "team_id": tid,
                "team_name": nm,
                "division": f"D{lv}",
                "league_level": lv,
                "tier": str(getattr(t, "initial_payroll_tier", "") or ""),
                "start_money": s0,
                "after_money": s1,
                "delta": s1 - s0,
            }
        )

    def _avg_for_level(lv: int, key: str) -> float:
        xs = [float(r[key]) for r in rows if r["league_level"] == lv]
        return mean(xs) if xs else 0.0

    neg = [r for r in rows if r["after_money"] < 0]
    neg_d3 = [r for r in neg if r["league_level"] == 3]
    d3_bottom = [r for r in rows if r["league_level"] == 3 and str(r["tier"]).lower() == "bottom"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write(
            f"seed={args.seed}  rounds_simulated={args.rounds}  teams={len(rows)}\n"
            "world_setup: generate_teams → apply_user_team_to_league(Survey FC,東京) → "
            "auto_draft + user opening v11 → assign_fictional_teams_and_rival → "
            "normalize_initial_payrolls_for_teams\n"
            "advance: Season (construct + simulate_multiple_rounds; stdout/stderr suppressed)\n\n"
        )

        fh.write(
            f"{'team_id':>6}  {'team_name':<28}  {'div':>4}  {'tier':<8}  "
            f"{'start_money':>14}  {'after_rounds':>14}  {'delta':>14}\n"
        )
        for r in rows:
            fh.write(
                f"{r['team_id']:>6}  {r['team_name'][:28]:<28}  {r['division']:>4}  {r['tier'][:8]:<8}  "
                f"{r['start_money']:>14,}  {r['after_money']:>14,}  {r['delta']:>14,}\n"
            )

        fh.write("\nDivision summary (averages over clubs in division)\n")
        for lv, label in ((1, "D1"), (2, "D2"), (3, "D3")):
            fh.write(
                f"{label}  n={sum(1 for r in rows if r['league_level']==lv)}\n"
                f"  avg start_money: {_avg_for_level(lv, 'start_money'):,.2f}\n"
                f"  avg after_{args.rounds}_rounds: {_avg_for_level(lv, 'after_money'):,.2f}\n"
                f"  avg delta: {_avg_for_level(lv, 'delta'):,.2f}\n"
            )

        fh.write("\nNegative money after rounds (after_money < 0)\n")
        fh.write(f"  all divisions: {len(neg)} club(s)\n")
        fh.write(f"  D3 only: {len(neg_d3)} club(s)\n")
        if neg:
            for r in sorted(neg, key=lambda x: x["after_money"]):
                fh.write(
                    f"    team_id={r['team_id']}  {r['team_name'][:24]}  {r['division']}  "
                    f"after={r['after_money']:,}  delta={r['delta']:,}\n"
                )

        fh.write("\nD3 clubs with initial_payroll_tier=bottom (individual)\n")
        for r in sorted(d3_bottom, key=lambda x: x["team_id"]):
            fh.write(
                f"  team_id={r['team_id']:>3}  {r['team_name'][:26]:<26}  "
                f"start={r['start_money']:>12,}  after={r['after_money']:>12,}  delta={r['delta']:>12,}\n"
            )

    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
