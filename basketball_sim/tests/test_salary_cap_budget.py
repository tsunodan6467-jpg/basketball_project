"""Step 3: キャップ・贅沢税・ペイロール判定。"""

from basketball_sim.config.game_constants import LEAGUE_SALARY_CAP
from basketball_sim.systems.salary_cap_budget import (
    can_absorb_salary_under_soft_cap,
    cap_status,
    compute_luxury_tax,
    get_hard_cap,
    get_soft_cap,
    is_payroll_over_club_budget,
)


def test_hard_soft_cap():
    assert get_hard_cap() == LEAGUE_SALARY_CAP
    assert get_soft_cap() == int(round(LEAGUE_SALARY_CAP * 1.20))


def test_cap_status_tiers():
    h = get_hard_cap()
    s = get_soft_cap()
    assert cap_status(h - 1) == "under_cap"
    assert cap_status(h + 1) == "over_cap"
    assert cap_status(s + 1) == "over_soft_cap"


def test_luxury_tax_only_above_soft():
    s = get_soft_cap()
    assert compute_luxury_tax(s) == 0
    assert compute_luxury_tax(s + 1_000_000) > 0


def test_trade_soft_cap_probe():
    cur = 14_000_000
    ok, proj, st = can_absorb_salary_under_soft_cap(cur, 0, 3_000_000)
    assert proj == 17_000_000
    assert isinstance(ok, bool)


def test_payroll_budget_warning():
    assert is_payroll_over_club_budget(100, 50) is True
    assert is_payroll_over_club_budget(40, 50) is False


def test_offseason_phase_list_matches_run():
    from basketball_sim.systems.offseason_phases import OFFSEASON_PHASES

    assert len(OFFSEASON_PHASES) == 17
