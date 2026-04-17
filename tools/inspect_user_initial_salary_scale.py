#!/usr/bin/env python3
"""
新規開始に近い形で「最初の D3 チーム＋自動編成」後のユーザーロスター年俸をダンプする。

用法:
  python tools/inspect_user_initial_salary_scale.py --seed 424242 --out reports/user_initial_salary_scale.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _salary_rows(team: Any) -> List[Dict[str, Any]]:
    rows = []
    for p in sorted(list(getattr(team, "players", []) or []), key=lambda x: (-int(getattr(x, "ovr", 0)), str(getattr(x, "name", "")))):
        rows.append(
            {
                "name": str(getattr(p, "name", ""))[:20],
                "pos": str(getattr(p, "position", "")),
                "age": int(getattr(p, "age", 0) or 0),
                "ovr": int(getattr(p, "ovr", 0) or 0),
                "nat": str(getattr(p, "nationality", ""))[:12],
                "salary": int(getattr(p, "salary", 0) or 0),
                "icon": bool(getattr(p, "is_icon", False)),
            }
        )
    return rows


def _summary(team: Any) -> Dict[str, int]:
    sals = [int(getattr(p, "salary", 0) or 0) for p in list(getattr(team, "players", []) or [])]
    n = len(sals)
    tot = sum(sals)
    return {
        "players": n,
        "total": tot,
        "avg": tot // n if n else 0,
        "max": max(sals) if sals else 0,
        "min": min(sals) if sals else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--out", type=Path, default=Path("reports/user_initial_salary_scale.txt"))
    args = ap.parse_args()

    from basketball_sim.main import (
        auto_draft_players,
        choose_icon_player_auto_from_league,
        create_icon_player,
    )
    from basketball_sim.systems.contract_logic import get_team_payroll
    from basketball_sim.systems.generator import generate_fictional_player_pool, generate_teams
    from basketball_sim.systems.opening_roster_salary_v11 import (
        apply_user_team_opening_payroll_v11_if_roster_complete,
    )
    from basketball_sim.utils.sim_rng import init_simulation_random

    seed = init_simulation_random(args.seed)
    teams = generate_teams()
    user_team = next(t for t in teams if int(getattr(t, "league_level", 0) or 0) == 3)
    user_team.is_user_team = True

    icon_data = choose_icon_player_auto_from_league(teams)
    st = icon_data.get("team") if isinstance(icon_data, dict) else None
    sp = icon_data.get("player") if isinstance(icon_data, dict) else None
    if st is not None and sp is not None and sp in getattr(st, "players", []):
        st.remove_player(sp)
    icon_player = create_icon_player(icon_data)
    pool = list(generate_fictional_player_pool(180))

    auto_draft_players(pool, user_team, icon_player)
    before = _summary(user_team)
    before["payroll_fn"] = int(get_team_payroll(user_team))
    applied = apply_user_team_opening_payroll_v11_if_roster_complete(user_team)
    after = _summary(user_team)
    after["payroll_fn"] = int(get_team_payroll(user_team))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write(f"seed={seed}  opening_v11_applied={applied}\n")
        n_foreign = sum(1 for p in getattr(user_team, "players", []) or [] if getattr(p, "nationality", "") == "Foreign")
        fh.write(
            f"user_team league_level={getattr(user_team, 'league_level', '?')} "
            f"initial_payroll_tier={getattr(user_team, 'initial_payroll_tier', '?')} "
            f"money={int(getattr(user_team, 'money', 0) or 0):,}  foreign_count={n_foreign}\n\n"
        )
        fh.write("AFTER auto_draft (before opening v11 user pass)\n")
        fh.write(f"  players={before['players']} total={before['total']:,} avg={before['avg']:,} "
                 f"max={before['max']:,} min={before['min']:,} get_team_payroll={before['payroll_fn']:,}\n\n")
        fh.write("AFTER opening v11 user pass\n")
        fh.write(f"  players={after['players']} total={after['total']:,} avg={after['avg']:,} "
                 f"max={after['max']:,} min={after['min']:,} get_team_payroll={after['payroll_fn']:,}\n\n")

        rows_after = _salary_rows(user_team)
        foreign = [r for r in rows_after if r["nat"] == "Foreign"]
        foreign.sort(key=lambda r: -r["salary"])
        jp = [r for r in rows_after if r["nat"] == "Japan"]
        jp.sort(key=lambda r: -r["salary"])
        fh.write("foreign top 3 by salary (name, nat, ovr, salary)\n")
        for r in foreign[:3]:
            fh.write(f"  {r['name']:<20}  {r['nat']:<10}  ovr={r['ovr']:>3}  {r['salary']:>12,}\n")
        fh.write("Japan players by salary (desc)\n")
        for r in jp:
            fh.write(f"  {r['name']:<20}  age={r['age']:>2}  ovr={r['ovr']:>3}  {r['salary']:>12,}\n")
        fh.write("\n")

        fh.write("name                  pos  age  ovr  nat          icon  salary\n")
        for r in rows_after:
            im = "Y" if r["icon"] else " "
            fh.write(
                f"{r['name']:<22}  {r['pos']:<3}  {r['age']:>3}  {r['ovr']:>3}  {r['nat']:<12}  {im}     {r['salary']:>12,}\n"
            )
    print(f"Wrote {args.out.resolve()} applied={applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
