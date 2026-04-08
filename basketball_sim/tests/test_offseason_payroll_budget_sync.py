"""オフFA直前: payroll_budget と実ペイロール＋_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER の同期（Offseason.run）。"""

import inspect

from basketball_sim.models import offseason as off_mod
from basketball_sim.models.offseason import (
    _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER,
    _sync_payroll_budget_with_roster_payroll,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems import free_agency as fa_mod


def _player(pid: int, salary: int) -> Player:
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
        team_id=1,
    )


def test_sync_raises_payroll_budget_when_below_roster_payroll():
    roster = _player(1, 20_000_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 5_000_000
    _sync_payroll_budget_with_roster_payroll([team])
    assert team.payroll_budget == 20_000_000 + _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER


def test_sync_does_not_lower_payroll_budget_when_above_roster():
    roster = _player(2, 8_000_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 120_000_000
    _sync_payroll_budget_with_roster_payroll([team])
    assert team.payroll_budget == 120_000_000


def test_offseason_run_calls_sync_twice_before_fa_in_order():
    """設計書どおり: 手動FA直前・CPU FA 直前の2回（いずれも conduct_free_agency より前）。"""
    src = inspect.getsource(off_mod.Offseason.run)
    assert src.count("_sync_payroll_budget_with_roster_payroll(self.teams)") == 2
    pre_ui = src.index("_sync_payroll_budget_with_roster_payroll(self.teams)")
    ui = src.index("self._maybe_run_pre_conduct_free_agency_ui()")
    second = src.index(
        "_sync_payroll_budget_with_roster_payroll(self.teams)",
        pre_ui + 1,
    )
    conduct = src.index("conduct_free_agency(self.teams, self.free_agents)")
    assert pre_ui < ui < second < conduct


def test_sync_empty_and_none_teams_no_crash():
    _sync_payroll_budget_with_roster_payroll([])
    _sync_payroll_budget_with_roster_payroll(None)  # type: ignore[arg-type]


def test_sync_adds_payroll_budget_buffer_when_budget_equals_roster():
    """payroll_budget == roster のときも floor は roster + _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER。"""
    roster = _player(4, 20_000_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 20_000_000
    _sync_payroll_budget_with_roster_payroll([team])
    assert team.payroll_budget == 20_000_000 + _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER


def test_sync_gives_positive_room_to_budget_and_nonzero_calculate_offer_when_tight():
    """同期後は room_to_budget が _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER になりうる（芯は別段でクリップ）。"""
    roster = _player(5, 7_600_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 7_600_000
    fa = Player(
        player_id=88009,
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
        ovr=72,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    assert int(fa_mod._calculate_offer(team, fa)) == 0
    pb = int(team.payroll_budget)
    pr = 7_600_000
    assert max(0, pb - pr) == 0
    _sync_payroll_budget_with_roster_payroll([team])
    pb2 = int(team.payroll_budget)
    room = max(0, pb2 - pr)
    assert room == _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    off = int(fa_mod._calculate_offer(team, fa))
    assert off == 5_000_000
    assert off > 0
    assert off <= _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
