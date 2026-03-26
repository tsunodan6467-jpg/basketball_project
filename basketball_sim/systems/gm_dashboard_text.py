"""
GM ダッシュボード用の読み取り専用テキスト（CLI main.py と GUI 共通）。

input() を使わない確認系の単一ソースにする。
"""

from __future__ import annotations

from typing import Any, List

from basketball_sim.systems.contract_logic import (
    SALARY_CAP_DEFAULT,
    SALARY_SOFT_LIMIT_MULTIPLIER,
    get_team_payroll,
)


def sort_roster_for_gm_view(players: List[Any]) -> List[Any]:
    position_order = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
    return sorted(
        players,
        key=lambda p: (
            position_order.get(getattr(p, "position", "SF"), 99),
            -getattr(p, "ovr", 0),
            getattr(p, "name", ""),
        ),
    )


def get_current_starting_five(user_team: Any) -> List[Any]:
    if hasattr(user_team, "get_starting_five"):
        try:
            return list(user_team.get_starting_five() or [])
        except Exception:
            pass
    roster = sort_roster_for_gm_view(getattr(user_team, "players", []) or [])
    return roster[:5]


def get_starting_player_ids(user_team: Any) -> set:
    return {
        getattr(p, "player_id", None)
        for p in get_current_starting_five(user_team)
    }


def get_current_sixth_man(user_team: Any):
    if hasattr(user_team, "get_sixth_man"):
        try:
            return user_team.get_sixth_man()
        except Exception:
            pass
    return None


def format_team_identity_text(team: Any) -> str:
    getter = getattr(team, "get_usage_policy_label", None)
    if callable(getter):
        try:
            usage_label = str(getter())
        except Exception:
            usage_label = str(getattr(team, "usage_policy", "balanced"))
    else:
        usage_label = str(getattr(team, "usage_policy", "balanced"))
    lines = [
        f"クラブ名      : {getattr(team, 'name', '-')}",
        f"拠点地        : {getattr(team, 'home_city', 'Unknown')}",
        f"市場規模      : {float(getattr(team, 'market_size', 1.0)):.2f}",
        f"人気          : {getattr(team, 'popularity', 0)}",
        f"資金          : ${int(getattr(team, 'money', 0)):,}",
        f"戦術          : {getattr(team, 'strategy', 'balanced')}",
        f"HCスタイル    : {getattr(team, 'coach_style', 'balanced')}",
        f"起用方針      : {usage_label}",
    ]
    return "\n".join(lines)


def format_salary_cap_text(team: Any) -> str:
    payroll = int(get_team_payroll(team))
    hard_cap = int(SALARY_CAP_DEFAULT)
    soft_cap = int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER)

    if payroll > soft_cap:
        status = "OVER SOFT CAP"
    elif payroll > hard_cap:
        status = "OVER CAP"
    else:
        status = "UNDER CAP"

    cap_space = hard_cap - payroll
    soft_room = soft_cap - payroll

    lines = [
        f"Team Payroll : ${payroll:,}",
        f"Hard Cap     : ${hard_cap:,}",
        f"Soft Cap     : ${soft_cap:,}",
        "",
        f"Status       : {status}",
    ]
    if cap_space >= 0:
        lines.append(f"Cap Space    : ${cap_space:,}")
    else:
        lines.append(f"Cap Over     : ${abs(cap_space):,}")

    if soft_room >= 0:
        lines.append(f"Soft Room    : ${soft_room:,}")
    else:
        lines.append(f"Soft Over    : ${abs(soft_room):,}")

    return "\n".join(lines)


def format_gm_roster_text(team: Any) -> str:
    roster = sort_roster_for_gm_view(list(getattr(team, "players", []) or []))
    if not roster:
        return "ロスターが存在しません。"

    starter_ids = get_starting_player_ids(team)
    sixth_man = get_current_sixth_man(team)
    sixth_man_id = getattr(sixth_man, "player_id", None) if sixth_man is not None else None

    lines_out: List[str] = []
    for i, p in enumerate(roster, 1):
        player_id = getattr(p, "player_id", None)

        if player_id in starter_ids:
            role_mark = "★"
        elif player_id == sixth_man_id:
            role_mark = "6"
        else:
            role_mark = " "

        lines_out.append(
            f"{i:>2}. {role_mark} {str(getattr(p, 'name', '-')):<15} "
            f"{str(getattr(p, 'position', '-')):<2} "
            f"OVR:{int(getattr(p, 'ovr', 0)):<2} "
            f"Age:{int(getattr(p, 'age', 0)):<2} "
            f"{str(getattr(p, 'nationality', 'Japan')):<12} "
            f"Salary:${int(getattr(p, 'salary', 0)):,}"
        )

    lines_out.append("")
    lines_out.append("★ = スタメン")
    lines_out.append("6 = シックスマン")
    return "\n".join(lines_out)
