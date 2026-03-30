"""Step 3: キャップ・贅沢税・ペイロール判定。"""

from basketball_sim.config.game_constants import (
    LEAGUE_SALARY_CAP,
    LEAGUE_SALARY_CAP_BY_DIVISION,
    PAYROLL_LUXURY_TAX_BRACKET_WIDTH_1,
    SALARY_SOFT_LIMIT_MULTIPLIER,
)
from basketball_sim.models.team import Team
from basketball_sim.systems.salary_cap_budget import (
    can_absorb_salary_under_soft_cap,
    cap_status,
    compute_luxury_tax,
    get_hard_cap,
    get_payroll_floor,
    get_soft_cap,
    is_payroll_below_floor,
    is_payroll_over_club_budget,
    payroll_exceeds_soft_cap,
)


def test_hard_soft_cap_d1_defaults():
    assert get_hard_cap() == LEAGUE_SALARY_CAP == LEAGUE_SALARY_CAP_BY_DIVISION[1]
    assert get_soft_cap() == int(round(LEAGUE_SALARY_CAP * SALARY_SOFT_LIMIT_MULTIPLIER))
    assert get_hard_cap() == get_soft_cap()


def test_hard_cap_by_division():
    assert get_hard_cap(league_level=2) == LEAGUE_SALARY_CAP_BY_DIVISION[2]
    assert get_soft_cap(league_level=3) == int(
        round(LEAGUE_SALARY_CAP_BY_DIVISION[3] * SALARY_SOFT_LIMIT_MULTIPLIER)
    )
    assert get_hard_cap(league_level=1) == get_hard_cap(league_level=2) == get_hard_cap(league_level=3)


def test_cap_status_tiers():
    h = get_hard_cap()
    s = get_soft_cap()
    assert h == s
    assert cap_status(h - 1) == "under_cap"
    assert cap_status(h + 1) == "over_soft_cap"
    assert cap_status(s + 1) == "over_soft_cap"


def test_payroll_exceeds_soft_cap_matches_cap_status():
    s = get_soft_cap()
    assert payroll_exceeds_soft_cap(s) is False
    assert payroll_exceeds_soft_cap(s + 1) is True


def test_fa_signing_limit_uses_same_soft_cap():
    from basketball_sim.systems.free_agent_market import get_team_fa_signing_limit

    t = Team(team_id=1, name="T", league_level=1)
    t.players = []
    assert get_team_fa_signing_limit(t) == get_soft_cap(LEAGUE_SALARY_CAP)


def test_luxury_tax_only_above_soft():
    s = get_soft_cap()
    assert compute_luxury_tax(s) == 0
    assert compute_luxury_tax(s + 1_000_000) > 0


def test_luxury_tax_progressive_brackets():
    """超過分の最初の帯幅に段階倍率が掛かる（ドラフト RB と同型）。"""
    s = get_soft_cap()
    w1 = int(PAYROLL_LUXURY_TAX_BRACKET_WIDTH_1)
    # 帯1ぎりぎり: 超過 w1 → 税 w1 * 1
    assert compute_luxury_tax(s + w1) == w1
    # 帯1を1円超え: 超過 w1+1 → 税 w1*1 + 1*2
    assert compute_luxury_tax(s + w1 + 1) == w1 + 2


def test_trade_soft_cap_probe():
    s = get_soft_cap()
    cur = s - 5_000_000
    ok, proj, st = can_absorb_salary_under_soft_cap(cur, 0, 10_000_000)
    assert proj == cur + 10_000_000
    assert st == "over_soft_cap"
    assert ok is False


def test_payroll_floor_by_division():
    assert get_payroll_floor(1) > 0
    assert get_payroll_floor(2) > 0
    assert get_payroll_floor(3) == 0
    assert is_payroll_below_floor(100, 1) is True
    assert is_payroll_below_floor(100, 3) is False


def test_payroll_budget_warning():
    assert is_payroll_over_club_budget(100, 50) is True
    assert is_payroll_over_club_budget(40, 50) is False


def test_offseason_phase_list_matches_run():
    from basketball_sim.systems.offseason_phases import OFFSEASON_PHASES

    assert len(OFFSEASON_PHASES) == 17
