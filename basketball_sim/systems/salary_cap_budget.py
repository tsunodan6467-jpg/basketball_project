"""
Step 3: リーグ年俸上限（12 億・全 D 同一）・贅沢税・ペイロール判定の単一入口。

get_hard_cap / get_soft_cap は同一額（SALARY_SOFT_LIMIT_MULTIPLIER=1.0）。
契約を「増やせる/増やせない」は別ルール（枠・交渉）と組み合わせて使う。
"""

from __future__ import annotations

from typing import Optional, Tuple

from basketball_sim.config.game_constants import (
    LEAGUE_SALARY_CAP,
    LEAGUE_SALARY_CAP_BY_DIVISION,
    PAYROLL_FLOOR_BY_DIVISION,
    PAYROLL_LUXURY_TAX_BRACKET_MULT_1,
    PAYROLL_LUXURY_TAX_BRACKET_MULT_2,
    PAYROLL_LUXURY_TAX_BRACKET_MULT_3,
    PAYROLL_LUXURY_TAX_BRACKET_WIDTH_1,
    PAYROLL_LUXURY_TAX_BRACKET_WIDTH_2,
    SALARY_SOFT_LIMIT_MULTIPLIER,
)


def league_level_for_team(team: Optional[object]) -> int:
    if team is None:
        return 1
    lv = getattr(team, "league_level", None)
    if lv is None:
        return 1
    try:
        lv = int(lv)
    except (TypeError, ValueError):
        return 1
    return max(1, min(3, lv))


def get_hard_cap(salary_cap: Optional[int] = None, *, league_level: Optional[int] = None) -> int:
    """
    リーグ年俸上限（円）。API 名は後方互換のため get_hard_cap のまま。
    明示 salary_cap があればそれを上限として用いる（テスト・上書き用）。
    なければ league_level（省略時 D1）のリーグ既定を使う。
    """
    if salary_cap is not None:
        return int(salary_cap)
    lv = 1 if league_level is None else max(1, min(3, int(league_level)))
    return int(LEAGUE_SALARY_CAP_BY_DIVISION.get(lv, LEAGUE_SALARY_CAP))


def get_soft_cap(salary_cap: Optional[int] = None, *, league_level: Optional[int] = None) -> int:
    """贅沢税・上限判定の閾値。乗数 1.0 時は get_hard_cap と同一。"""
    return int(round(get_hard_cap(salary_cap, league_level=league_level) * SALARY_SOFT_LIMIT_MULTIPLIER))


def cap_status(payroll: int, salary_cap: Optional[int] = None, *, league_level: Optional[int] = None) -> str:
    """under_cap | over_soft_cap（10億〜12億の中間帯は廃止。閾値はリーグ上限＝ソフトと同一）。"""
    s = get_soft_cap(salary_cap, league_level=league_level)
    if int(payroll) > s:
        return "over_soft_cap"
    return "under_cap"


def payroll_exceeds_soft_cap(
    payroll: int, salary_cap: Optional[int] = None, *, league_level: Optional[int] = None
) -> bool:
    """
    プロジェクト後ペイロールがリーグ年俸上限（ソフト閾値）を超えるか。
    再契約（evaluate_resign）・オフシーズン再契約UI・FA の上限感の共通判定に使う。
    """
    return cap_status(int(payroll), salary_cap=salary_cap, league_level=league_level) == "over_soft_cap"


def compute_luxury_tax(
    payroll: int,
    salary_cap: Optional[int] = None,
    *,
    league_level: Optional[int] = None,
) -> int:
    """
    リーグ年俸上限超過分に対する段階式贅沢税（整数）。
    ドラフト RB の _tax_extra_for_total_spend と同型。
    """
    soft = get_soft_cap(salary_cap, league_level=league_level)
    over = max(0, int(payroll) - soft)
    if over <= 0:
        return 0

    w1 = int(PAYROLL_LUXURY_TAX_BRACKET_WIDTH_1)
    w2 = int(PAYROLL_LUXURY_TAX_BRACKET_WIDTH_2)
    m1 = int(PAYROLL_LUXURY_TAX_BRACKET_MULT_1)
    m2 = int(PAYROLL_LUXURY_TAX_BRACKET_MULT_2)
    m3 = int(PAYROLL_LUXURY_TAX_BRACKET_MULT_3)

    tier1 = min(over, w1)
    tier2 = min(max(over - w1, 0), w2)
    tier3 = max(over - w1 - w2, 0)
    return int(tier1 * m1 + tier2 * m2 + tier3 * m3)


def get_payroll_floor(league_level: int) -> int:
    """0 なら下限なし。"""
    lv = max(1, min(3, int(league_level)))
    return int(PAYROLL_FLOOR_BY_DIVISION.get(lv, 0))


def is_payroll_below_floor(payroll: int, league_level: int) -> bool:
    fl = get_payroll_floor(league_level)
    if fl <= 0:
        return False
    return int(payroll) < fl


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
    *,
    league_level: Optional[int] = None,
) -> Tuple[bool, int, str]:
    """
    トレード/FA の「リーグ年俸上限を超えるか」判定のみ（ブロックはしない）。
    return: (ok_under_soft, projected, cap_status_str)
    """
    proj = projected_payroll_after_swap(current_payroll, outgoing_salary, incoming_salary)
    st = cap_status(proj, salary_cap=salary_cap, league_level=league_level)
    ok = st != "over_soft_cap"
    return ok, proj, st


def is_payroll_over_club_budget(payroll: int, payroll_budget: int) -> bool:
    """クラブの人件費目安を超えているか（警告用）。"""
    return int(payroll) > int(max(0, payroll_budget))
