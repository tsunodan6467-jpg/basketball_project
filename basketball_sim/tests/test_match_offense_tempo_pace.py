"""team_tactics.team_strategy.offense_tempo → Match 総ポゼ数（弱い上乗せ）。"""

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team


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
    return t


def _with_offense_tempo(t: Team, offense_tempo: str) -> Team:
    t.team_tactics = {"version": 1, "team_strategy": {"offense_tempo": offense_tempo}}
    ensure_team_tactics_on_team(t)
    return t


def test_offense_tempo_fast_vs_slow_changes_total_possessions_weakly():
    away = _with_offense_tempo(_team(2, "Away"), "standard")
    home_fast = _with_offense_tempo(_team(1, "HomeFast"), "fast")
    home_slow = _with_offense_tempo(_team(3, "HomeSlow"), "slow")
    m_fast = Match(home_team=home_fast, away_team=away)
    m_slow = Match(home_team=home_slow, away_team=away)
    # fast: +2 / slow: -2 on home only → 差は 4（clamp 内）
    assert m_fast._get_total_possessions() - m_slow._get_total_possessions() == 4
    assert 140 <= m_fast._get_total_possessions() <= 180
    assert 140 <= m_slow._get_total_possessions() <= 180


def test_offense_tempo_does_not_override_existing_pace_baseline():
    """既存補正は温存: offense_tempo 以外同一なら、fast と standard の差は 2 だけ（ホーム分）。"""
    away = _with_offense_tempo(_team(2, "Away"), "standard")
    home_std = _with_offense_tempo(_team(1, "HomeStd"), "standard")
    home_fast = _with_offense_tempo(_team(3, "HomeF"), "fast")
    m_std = Match(home_team=home_std, away_team=away)
    m_f = Match(home_team=home_fast, away_team=away)
    assert m_f._get_total_possessions() - m_std._get_total_possessions() == 2
