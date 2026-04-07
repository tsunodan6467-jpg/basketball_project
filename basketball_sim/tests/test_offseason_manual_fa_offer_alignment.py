"""オフ手動FA: `_calculate_offer` 同型の年俸・年数と `sign_free_agent` オーバーライドの整合。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems import free_agency as fa_mod
from basketball_sim.systems.free_agent_market import (
    MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER,
    estimate_fa_market_value,
    get_team_fa_signing_limit,
    offseason_manual_fa_offer_and_years,
    sign_free_agent,
)


def _player(player_id: int, *, ovr: int = 60, salary: int = 0, **kwargs: object) -> Player:
    base = dict(
        player_id=player_id,
        name=f"P{player_id}",
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
    base.update(kwargs)
    return Player(**base)


def test_offseason_manual_fa_offer_and_years_positive():
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[])
    fa = _player(88001, ovr=72, salary=4_000_000)
    off, yrs = offseason_manual_fa_offer_and_years(team, fa)
    assert off > 0
    assert 1 <= yrs <= 4


def test_offseason_manual_fa_fallback_when_payroll_budget_zeroes_calculate_offer():
    """
    `payroll_budget` が既存ペイロールに張り付いていると `_calculate_offer` は 0 になりうる。
    キャップ上まだ契約余地があるときは `min(estimate, room)` を core にし、
    オフ手動専用下限 `estimate * MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER` を乗せて `room` でクリップ。
    """
    roster = _player(101, ovr=60, salary=7_600_000, contract_years_left=1)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 7_600_000
    fa = _player(88009, ovr=72, salary=4_000_000)
    room = int(get_team_fa_signing_limit(team))
    assert room > 0
    assert int(fa_mod._calculate_offer(team, fa)) == 0
    est = int(estimate_fa_market_value(fa))
    off, yrs = offseason_manual_fa_offer_and_years(team, fa)
    expected = min(int(est * MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER), room)
    assert off == expected
    assert off > 0
    assert 1 <= yrs <= 4


def test_sign_free_agent_contract_override_sets_salary_and_years():
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[])
    fa = _player(88002, ovr=65)
    off, yrs = offseason_manual_fa_offer_and_years(team, fa)
    assert off > 0
    sign_free_agent(team, fa, contract_salary=off, contract_years=yrs)
    assert fa in team.players
    assert int(fa.salary) == off
    assert int(fa.contract_years_left) == yrs


def test_sign_free_agent_without_override_still_uses_estimate():
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[])
    fa = _player(88003, ovr=66)
    expected = int(estimate_fa_market_value(fa))
    sign_free_agent(team, fa)
    assert fa in team.players
    assert int(fa.salary) == expected
