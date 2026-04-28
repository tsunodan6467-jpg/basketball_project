"""Match 個人ファウル正本 → RotationSystem 同期の土台（発生処理なし）。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team


def _player(pid: int, position: str = "SF", ovr: int = 70) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=198.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=70,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _build_match() -> Match:
    home = Team(team_id=1, name="Home", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        home.add_player(_player(200 + i, pos, ovr=78 - i))
    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)
    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(300 + i, pos, ovr=68 - i))
    away.team_tactics = {
        "version": 1,
        "rotation": {"starters": {}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(away)
    return Match(home_team=home, away_team=away)


def test_match_initializes_empty_personal_foul_dicts():
    m = _build_match()
    assert m.home_personal_fouls_by_player_id == {}
    assert m.away_personal_fouls_by_player_id == {}


def test_match_syncs_to_rotation_system_on_maybe_update_rotations():
    m = _build_match()
    m.home_personal_fouls_by_player_id[201] = 4
    m.away_personal_fouls_by_player_id[305] = 2
    m._maybe_update_rotations(0)
    assert m.home_rotation._personal_fouls_by_player_id.get(201) == 4
    assert m.away_rotation._personal_fouls_by_player_id.get(305) == 2


def test_set_personal_fouls_by_player_id_none_uses_empty_map():
    from basketball_sim.systems.rotation import RotationSystem

    t = Team(team_id=9, name="T", league_level=1)
    for i in range(8):
        t.add_player(_player(400 + i, "SG" if i == 0 else "SF", ovr=70))
    ps = list(t.players)
    r = RotationSystem(t, ps, starters=ps[:5])
    r.set_personal_fouls_by_player_id(None)
    assert r._personal_fouls_by_player_id == {}


def test_full_simulate_does_not_increase_fouls():
    m = _build_match()
    _ = m.simulate()
    assert m.home_personal_fouls_by_player_id == {}
    assert m.away_personal_fouls_by_player_id == {}


def test_set_personal_fouls_accepts_string_keys_in_dict():
    m = _build_match()
    r = m.home_rotation
    r.set_personal_fouls_by_player_id({"201": 3, "bad": 1})
    assert r._personal_fouls_by_player_id.get(201) == 3
