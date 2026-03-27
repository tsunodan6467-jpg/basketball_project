import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


def _player(pid: int, position: str) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=190.0,
        weight_kg=85.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=68,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team(team_id: int, name: str, training_focus: str = "balanced") -> Team:
    t = Team(team_id=team_id, name=name, league_level=1, team_training_focus=training_focus)
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]
    for i, pos in enumerate(positions, start=1):
        t.add_player(_player(team_id * 100 + i, pos))
    return t


def test_special_training_effect_is_low_coefficient():
    away = _team(2, "Away", training_focus="balanced")

    home_bal = _team(1, "Home-Bal", training_focus="balanced")
    m_bal = Match(home_team=home_bal, away_team=away)
    off_bal, def_bal = m_bal._calculate_team_strength_from_players(home_bal, m_bal.home_starters)

    home_prec = _team(3, "Home-Prec", training_focus="precision_offense")
    m_prec = Match(home_team=home_prec, away_team=away)
    off_prec, def_prec = m_prec._calculate_team_strength_from_players(home_prec, m_prec.home_starters)

    home_int = _team(4, "Home-Int", training_focus="intense_defense")
    m_int = Match(home_team=home_int, away_team=away)
    off_int, def_int = m_int._calculate_team_strength_from_players(home_int, m_int.home_starters)

    assert off_prec - off_bal == pytest.approx(0.9)
    assert def_prec - def_bal == pytest.approx(0.0)
    assert def_int - def_bal == pytest.approx(0.9)
    assert off_int - off_bal == pytest.approx(0.0)


def test_intense_defense_pace_is_still_more_defensive_than_defense():
    away = _team(2, "Away", training_focus="balanced")

    home_def = _team(1, "Home-Def", training_focus="defense")
    m_def = Match(home_team=home_def, away_team=away)

    home_int = _team(3, "Home-Int", training_focus="intense_defense")
    m_int = Match(home_team=home_int, away_team=away)

    assert m_def._get_total_possessions() == 159
    assert m_int._get_total_possessions() == 158
