"""team_tactics.team_strategy.transition_style → Match 総ポゼ数（極小 T1、T2 減衰、T3 衝突）。"""

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team, get_transition_style_pace_adjustment


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


def _team(tid: int, name: str) -> Team:
    t = Team(team_id=tid, name=name, league_level=1, team_training_focus="balanced")
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        t.add_player(_player(tid * 100 + i + 1, pos))
    t.strategy = "balanced"
    return t


def _with_transition(
    t: Team, transition_style: str, offense_tempo: str = "standard"
) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": offense_tempo,
            "transition_style": transition_style,
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_transition_style_push_raises_total_slightly_on_balanced():
    away = _with_transition(_team(2, "Away"), "situational", "standard")
    home_push = _with_transition(_team(1, "HomeP"), "push", "standard")
    home_sit = _with_transition(_team(3, "HomeS"), "situational", "standard")
    m_push = Match(home_team=home_push, away_team=away)
    m_sit = Match(home_team=home_sit, away_team=away)
    assert m_push._get_total_possessions() - m_sit._get_total_possessions() == 1
    assert 140 <= m_push._get_total_possessions() <= 180


def test_transition_style_half_court_lowers_total_slightly_on_balanced():
    away = _with_transition(_team(2, "Away"), "situational", "standard")
    home_hc = _with_transition(_team(1, "HomeHC"), "half_court", "standard")
    home_sit = _with_transition(_team(3, "HomeS"), "situational", "standard")
    m_hc = Match(home_team=home_hc, away_team=away)
    m_sit = Match(home_team=home_sit, away_team=away)
    assert m_hc._get_total_possessions() - m_sit._get_total_possessions() == -1
    assert 140 <= m_hc._get_total_possessions() <= 180


def test_offense_tempo_fast_dampens_push_bonus():
    away = _with_transition(_team(2, "Away"), "situational", "standard")
    h_push_std = _with_transition(_team(1, "HPs"), "push", "standard")
    h_sit_std = _with_transition(_team(3, "HSs"), "situational", "standard")
    h_push_fast = _with_transition(_team(4, "HPf"), "push", "fast")
    h_sit_fast = _with_transition(_team(5, "HSf"), "situational", "fast")
    m_ps = Match(home_team=h_push_std, away_team=away)
    m_ss = Match(home_team=h_sit_std, away_team=away)
    m_pf = Match(home_team=h_push_fast, away_team=away)
    m_sf = Match(home_team=h_sit_fast, away_team=away)
    d_std = m_ps._get_total_possessions() - m_ss._get_total_possessions()
    d_fast = m_pf._get_total_possessions() - m_sf._get_total_possessions()
    assert d_std == 1
    # fast+push: transition 成分は 0.5x→0（T2 減衰）。同じ fast の中では push でも増えない
    assert d_fast == 0
    assert d_std - d_fast == 1


def test_run_and_gun_plus_push_does_not_stack_transition_push():
    away = _with_transition(_team(2, "Away"), "situational", "standard")
    home_rag_sit = _with_transition(_team(1, "RagS"), "situational", "standard")
    home_rag_push = _with_transition(_team(3, "RagP"), "push", "standard")
    home_rag_sit.strategy = "run_and_gun"
    home_rag_push.strategy = "run_and_gun"
    m_sit = Match(home_team=home_rag_sit, away_team=away)
    m_push = Match(home_team=home_rag_push, away_team=away)
    assert m_push._get_total_possessions() == m_sit._get_total_possessions()
    assert get_transition_style_pace_adjustment(home_rag_push, "run_and_gun") == 0
    assert get_transition_style_pace_adjustment(home_rag_push, "balanced") == 1


def test_situational_and_ordering_helper():
    t = _team(9, "X")
    t.team_tactics = {
        "version": 1,
        "team_strategy": {"offense_tempo": "standard", "transition_style": "situational"},
    }
    ensure_team_tactics_on_team(t)
    assert get_transition_style_pace_adjustment(t, "balanced") == 0
    t2 = _with_transition(_team(8, "Y"), "push", "standard")
    t3 = _with_transition(_team(7, "Z"), "half_court", "standard")
    assert get_transition_style_pace_adjustment(t2, "balanced") > 0
    assert get_transition_style_pace_adjustment(t3, "balanced") < 0
