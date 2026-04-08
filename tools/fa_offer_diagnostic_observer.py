#!/usr/bin/env python3
"""
S1 / S6 系の `_calculate_offer_diagnostic` 定点集計（本番未接続）。

`docs/FA_S6_TINY_OFFER_POLICY_NOTE_2026-04.md` の観測方針に沿い、
合成 Team/Player で再現可能なケースを走らせ stdout に件数を出す。

実行（リポジトリルート）:
    python tools/fa_offer_diagnostic_observer.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# リポジトリルートをパスに入れて `python tools/...` で実行可能にする
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.models.player import Player  # noqa: E402
from basketball_sim.models.team import Team  # noqa: E402
from basketball_sim.systems import free_agency as fa_mod  # noqa: E402
from basketball_sim.systems.salary_cap_budget import get_soft_cap  # noqa: E402


def _roster_player(pid: int, salary: int, *, league_team_id: int = 1) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=60,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=1,
        contract_total_years=2,
        team_id=league_team_id,
    )


def _fa_player(
    pid: int,
    *,
    ovr: int = 72,
    salary: int = 4_000_000,
) -> Player:
    return Player(
        player_id=pid,
        name="FA",
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def _build_cases() -> List[Tuple[str, Team, Player]]:
    """固定シードの代表ケース（乱数なし）。"""
    out: List[Tuple[str, Team, Player]] = []
    pid = 10_000

    sc1 = int(get_soft_cap(league_level=1))
    sc2 = int(get_soft_cap(league_level=2))

    # S1 D1: soft cap 到達
    r = _roster_player(pid, sc1)
    pid += 1
    t = Team(team_id=1, name="S1_D1", league_level=1, money=500_000_000, players=[r])
    t.payroll_budget = sc1 + 50_000_000
    out.append(("S1_D1_soft_cap", t, _fa_player(pid)))
    pid += 1

    # S1 D2（現設定では cap 同額だが league_level 差をログに残す）
    r2 = _roster_player(pid, sc2)
    pid += 1
    t2 = Team(team_id=2, name="S1_D2", league_level=2, money=500_000_000, players=[r2])
    t2.payroll_budget = sc2 + 50_000_000
    out.append(("S1_D2_soft_cap", t2, _fa_player(pid)))
    pid += 1

    # S6-0: room == 0
    r3 = _roster_player(pid, 7_600_000)
    pid += 1
    t3 = Team(team_id=3, name="S6a_D1_room0", league_level=1, money=500_000_000, players=[r3])
    t3.payroll_budget = 7_600_000
    out.append(("S6a_D1_budget_eq_roster", t3, _fa_player(pid)))
    pid += 1

    # S6-tiny: buffer 300k・中額 FA
    r4 = _roster_player(pid, 7_600_000)
    pid += 1
    t4 = Team(team_id=4, name="S6b_D1_tiny_mid", league_level=1, money=500_000_000, players=[r4])
    t4.payroll_budget = 7_900_000
    out.append(("S6b_D1_buffer300k_midFA", t4, _fa_player(pid)))
    pid += 1

    # S6-tiny: buffer 300k・高額 FA
    r5 = _roster_player(pid, 7_600_000)
    pid += 1
    t5 = Team(team_id=5, name="S6b_D1_tiny_high", league_level=1, money=500_000_000, players=[r5])
    t5.payroll_budget = 7_900_000
    out.append(("S6b_D1_buffer300k_highFA", t5, _fa_player(pid, salary=88_000_000)))
    pid += 1

    # D2 でも同型 S6-tiny（division 差の参照用）
    r6 = _roster_player(pid, 7_600_000)
    pid += 1
    t6 = Team(team_id=6, name="S6b_D2_tiny_mid", league_level=2, money=500_000_000, players=[r6])
    t6.payroll_budget = 7_900_000
    out.append(("S6b_D2_buffer300k_midFA", t6, _fa_player(pid)))
    pid += 1

    # healthy: 空ロスター・大きい budget・高額 FA
    t7 = Team(team_id=7, name="healthy_D1_empty", league_level=1, money=500_000_000, players=[])
    t7.payroll_budget = 500_000_000
    out.append(("healthy_D1_empty_highFA", t7, _fa_player(pid, salary=88_000_000)))
    pid += 1

    # test matrix 由来: D1 空・余裕大・salary 0（ovr 下限芯）
    t8 = Team(team_id=8, name="matrix_D1_empty", league_level=1, money=300_000_000, players=[])
    t8.payroll_budget = 400_000_000
    out.append(("matrix_D1_empty_ovr65", t8, _fa_player(pid, ovr=65, salary=0)))
    pid += 1

    # test matrix 由来: D2 ロスターあり・budget > payroll（通常オファー）
    t9 = Team(
        team_id=9,
        name="matrix_D2_roster",
        league_level=2,
        money=200_000_000,
        players=[_roster_player(pid, 5_000_000, league_team_id=9)],
    )
    pid += 1
    t9.payroll_budget = 150_000_000
    out.append(("matrix_D2_roomy", t9, _fa_player(pid, ovr=68, salary=6_000_000)))
    pid += 1

    return out


def _fa_salary_for_display(fa: Player, d: Dict[str, Any]) -> int:
    s = int(getattr(fa, "salary", 0) or 0)
    if s > 0:
        return s
    b = d.get("base")
    if b is not None:
        return int(b)
    return int(getattr(fa, "ovr", 60)) * 10_000


def _payroll_budget_display(team: Team, d: Dict[str, Any]) -> int:
    v = d.get("payroll_budget")
    if v is not None:
        return int(v)
    return int(getattr(team, "payroll_budget", 0) or 0)


def main() -> None:
    rows: List[Tuple[str, Team, Dict[str, Any], Player]] = []
    for label, team, fa in _build_cases():
        d = fa_mod._calculate_offer_diagnostic(team, fa)
        rows.append((label, team, d, fa))

    n = len(rows)
    n_zero = sum(1 for _, _, d, _ in rows if int(d["final_offer"]) == 0)
    n_tiny = sum(1 for _, _, d, _ in rows if 0 < int(d["final_offer"]) <= 300_000)
    n_s1 = sum(1 for _, _, d, _ in rows if d["soft_cap_early"] is True)
    n_room0 = sum(1 for _, _, d, _ in rows if d.get("room_to_budget") == 0)
    n_s6_room_le_300k = sum(
        1
        for _, _, d, _ in rows
        if d["soft_cap_early"] is False
        and d.get("room_to_budget") is not None
        and int(d["room_to_budget"]) <= 300_000
    )
    n_s6_false_tiny_offer = sum(
        1
        for _, _, d, _ in rows
        if d["soft_cap_early"] is False and 0 < int(d["final_offer"]) <= 300_000
    )

    print("FA offer diagnostic observer (synthetic matrix, not real saves)")
    print("---")
    print(f"total_cases:              {n}")
    print(f"soft_cap_early True:      {n_s1}")
    print(f"final_offer == 0:         {n_zero}")
    print(f"0 < final_offer <= 300k:  {n_tiny}")
    print(f"room_to_budget == 0:      {n_room0}")
    print(
        "soft_cap_early False & "
        "0 < final <= 300k:        {}".format(n_s6_false_tiny_offer)
    )
    print(
        "soft_cap_early False & "
        "room_to_budget <= 300k:   {}".format(n_s6_room_le_300k)
    )
    print("---")
    print("per_case:")
    for label, team, d, _fa in rows:
        fo = int(d["final_offer"])
        rtb = d.get("room_to_budget")
        rtb_s = "None" if rtb is None else str(int(rtb))
        pbd = _payroll_budget_display(team, d)
        print(
            f"  {label}: league={d.get('league_level')} "
            f"payroll_before={int(d['payroll_before']):,} "
            f"payroll_budget={pbd:,} "
            f"room_to_budget={rtb_s} final={fo:,} soft_early={d['soft_cap_early']}"
        )

    tiny_samples = [
        (label, team, d, fa)
        for label, team, d, fa in rows
        if d["soft_cap_early"] is False and 0 < int(d["final_offer"]) <= 300_000
    ]
    print("---")
    print("sample tiny offers (soft_cap_early False, 0 < final <= 300_000), up to 3:")
    for i, (label, team, d, fa) in enumerate(tiny_samples[:3]):
        sal = _fa_salary_for_display(fa, d)
        rtb = d.get("room_to_budget")
        print(f"  [{i + 1}] label={label}")
        print(f"      league_level={d.get('league_level')}")
        print(f"      payroll_before={int(d['payroll_before']):,}")
        print(f"      payroll_budget={_payroll_budget_display(team, d):,}")
        print(f"      room_to_budget={rtb}")
        print(f"      player_salary_or_effective_base={sal:,}")
        print(f"      final_offer={int(d['final_offer']):,}")


if __name__ == "__main__":
    main()
