"""GUI 用 `precheck_user_fa_sign`（`sign_free_agent` 前の可否・理由）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_market import precheck_user_fa_sign


def _player(
    player_id: int,
    *,
    ovr: int = 60,
    **kwargs: object,
) -> Player:
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
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    base.update(kwargs)
    return Player(**base)


def test_precheck_user_fa_sign_ok_empty_roster():
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[])
    fa = _player(99001, ovr=65)
    ok, msg = precheck_user_fa_sign(team, fa)
    assert ok is True
    assert msg == ""


def test_precheck_user_fa_sign_fails_insufficient_money():
    team = Team(team_id=1, name="T", league_level=1, money=1_000, players=[])
    fa = _player(99002, ovr=80)
    ok, msg = precheck_user_fa_sign(team, fa)
    assert ok is False
    assert "所持金" in msg


def test_precheck_user_fa_sign_fails_contract_roster_full():
    roster = [
        _player(i + 1, salary=1_000_000, contract_years_left=1, contract_total_years=1, team_id=1)
        for i in range(13)
    ]
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=roster)
    fa = _player(99003, ovr=60)
    ok, msg = precheck_user_fa_sign(team, fa)
    assert ok is False
    assert "上限" in msg or "13" in msg
