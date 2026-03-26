"""Step 1: 契約ロスター（13枠・国籍）の検証。"""

import pytest

from basketball_sim.config.game_constants import CONTRACT_ROSTER_MAX, LEAGUE_ROSTER_FOREIGN_CAP
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.roster_rules import (
    RosterViolationError,
    can_add_contract_player,
    is_contract_roster_valid,
    validate_contract_roster,
)


def _make_player(pid: int, name: str, ovr: int, nationality: str = "Japan") -> Player:
    return Player(
        player_id=pid,
        name=name,
        age=25,
        nationality=nationality,
        position="SF",
        height_cm=200.0,
        weight_kg=95.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="B",
        archetype="wing",
        usage_base=20,
    )


def test_add_player_blocks_fourteenth():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(CONTRACT_ROSTER_MAX):
        t.add_player(_make_player(i + 1, f"P{i}", 60))
    assert len(t.players) == CONTRACT_ROSTER_MAX

    extra = _make_player(99, "Extra", 55)
    with pytest.raises(RosterViolationError):
        t.add_player(extra)


def test_foreign_cap_enforced():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(LEAGUE_ROSTER_FOREIGN_CAP):
        t.add_player(_make_player(i + 1, f"F{i}", 60, nationality="Foreign"))

    jp = _make_player(10, "JP", 60, "Japan")
    assert can_add_contract_player(t, jp)[0] is True

    foreign4 = _make_player(11, "F4", 60, nationality="Foreign")
    assert can_add_contract_player(t, foreign4)[0] is False


def test_validate_detects_overflow():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(CONTRACT_ROSTER_MAX + 1):
        t.players.append(_make_player(i + 1, f"P{i}", 60))
        t.players[-1].team_id = t.team_id
    errs = validate_contract_roster(t)
    assert any("超えています" in e for e in errs)


def test_is_valid_true_for_generator_like_roster():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(CONTRACT_ROSTER_MAX):
        t.add_player(_make_player(i + 1, f"P{i}", 60))
    assert is_contract_roster_valid(t) is True
