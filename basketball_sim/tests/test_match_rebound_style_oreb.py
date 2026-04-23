"""team_tactics.rebound_style crash_offense / get_back → Match._get_offense_rebound_rate（第7弾）。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_rebound_style_offense_oreb_delta,
)


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


def _with_rebound_style(t: Team, rebound_style: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "defense_style": "balanced",
            "rebound_style": rebound_style,
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def _oreb(m: Match, home: Team) -> float:
    return m._get_offense_rebound_rate(
        home, m.away_team, m.home_starters, m.away_starters, False
    )


def test_crash_offense_balanced_small_positive_delta():
    """T1: balanced 戦略 + crash_offense → 満額 +0.008 相当の正。"""
    t = _with_rebound_style(_team(1, "C"), "crash_offense")
    assert get_rebound_style_offense_oreb_delta(t, "balanced") == 0.008


def test_get_back_balanced_small_negative_delta():
    """T1: get_back → -0.006。"""
    t = _with_rebound_style(_team(2, "G"), "get_back")
    assert get_rebound_style_offense_oreb_delta(t, "balanced") == -0.006


def test_crash_inside_strategy_damped():
    """T2: inside 戦略 + crash_offense は 0.3 倍で満額より小さい正。"""
    t = _with_rebound_style(_team(3, "I"), "crash_offense")
    full = get_rebound_style_offense_oreb_delta(t, "balanced")
    damp = get_rebound_style_offense_oreb_delta(t, "inside")
    assert damp == pytest.approx(0.008 * 0.3, abs=1e-9)
    assert 0 < damp < full


def test_rebound_balanced_zero_and_ordering():
    """balanced rebound_style は 0。crash > 0 > get_back（helper）。"""
    tb = _with_rebound_style(_team(4, "B4"), "balanced")
    assert get_rebound_style_offense_oreb_delta(tb, "balanced") == 0.0
    tc = _with_rebound_style(_team(4, "C4"), "crash_offense")
    tg = _with_rebound_style(_team(4, "G4"), "get_back")
    assert get_rebound_style_offense_oreb_delta(tc, "balanced") > 0
    assert get_rebound_style_offense_oreb_delta(tg, "balanced") < 0


def test_get_offense_rebound_rate_mutate_rebound_style():
    """同一 Match で rebound_style だけ切替、差がオーバーレイ分（integration）。"""
    home = _with_rebound_style(_team(1, "H"), "crash_offense")
    home.strategy = "balanced"
    away = _with_rebound_style(_team(2, "A"), "balanced")
    m = Match(home_team=home, away_team=away)
    a = _oreb(m, home)
    home.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "defense_style": "balanced",
            "rebound_style": "balanced",
        },
    }
    ensure_team_tactics_on_team(home)
    b = _oreb(m, home)
    assert a - b == pytest.approx(0.008, abs=1e-5)
