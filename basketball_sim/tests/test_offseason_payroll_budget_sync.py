"""オフFA直前: payroll_budget と実ペイロールの max 同期（Offseason.run 第1弾）。"""

import inspect

from basketball_sim.models import offseason as off_mod
from basketball_sim.models.offseason import _sync_payroll_budget_with_roster_payroll
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


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
    assert team.payroll_budget == 20_000_000


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
