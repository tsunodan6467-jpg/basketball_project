"""
Step 3: ソフトキャップ・贅沢税・ペイロール判定の単一入口。

契約を「増やせる/増やせない」は別ルール（枠・交渉）と組み合わせて使う。
"""

from __future__ import annotations

from typing import Optional, Tuple

from basketball_sim.config.game_constants import (
    LEAGUE_SALARY_CAP,
    LUXURY_TAX_RATE,
    SALARY_SOFT_LIMIT_MULTIPLIER,
)


def get_hard_cap(salary_cap: Optional[int] = None) -> int:
    return int(salary_cap if salary_cap is not None else LEAGUE_SALARY_CAP)


def get_soft_cap(salary_cap: Optional[int] = None) -> int:
    return int(round(get_hard_cap(salary_cap) * SALARY_SOFT_LIMIT_MULTIPLIER))


def cap_status(payroll: int, salary_cap: Optional[int] = None) -> str:
    """under_cap | over_cap | over_soft_cap"""
    h = get_hard_cap(salary_cap)
    s = get_soft_cap(salary_cap)
    if payroll > s:
        return "over_soft_cap"
    if payroll > h:
        return "over_cap"
    return "under_cap"


def payroll_exceeds_soft_cap(payroll: int, salary_cap: Optional[int] = None) -> bool:
    """
    プロジェクト後ペイロールがソフト上限を超えるか。
    再契約（evaluate_resign）・オフシーズン再契約UI・FA の上限感の共通判定に使う。
    """
    return cap_status(int(payroll), salary_cap=salary_cap) == "over_soft_cap"


def compute_luxury_tax(payroll: int, salary_cap: Optional[int] = None) -> int:
    """
    ソフトキャップ超過分に対する贅沢税（整数・v1 簡易）。
    ペイロールがソフト以下なら 0。
    """
    soft = get_soft_cap(salary_cap)
    over = max(0, int(payroll) - soft)
    return int(round(over * float(LUXURY_TAX_RATE)))


def projected_payroll_after_swap(
    current_payroll: int,
    outgoing_salary: int = 0,
    incoming_salary: int = 0,
) -> int:
    return max(0, int(current_payroll) - int(outgoing_salary) + int(incoming_salary))


def can_absorb_salary_under_soft_cap(
    current_payroll: int,
    outgoing_salary: int,
    incoming_salary: int,
    salary_cap: Optional[int] = None,
) -> Tuple[bool, int, str]:
    """
    トレード/FA の「ソフト上限を超えるか」判定のみ（ブロックはしない）。
    return: (ok_under_soft, projected, cap_status_str)
    """
    proj = projected_payroll_after_swap(current_payroll, outgoing_salary, incoming_salary)
    st = cap_status(proj, salary_cap=salary_cap)
    ok = st != "over_soft_cap"
    return ok, proj, st


def is_payroll_over_club_budget(payroll: int, payroll_budget: int) -> bool:
    """クラブの人件費目安を超えているか（警告用）。"""
    return int(payroll) > int(max(0, payroll_budget))
