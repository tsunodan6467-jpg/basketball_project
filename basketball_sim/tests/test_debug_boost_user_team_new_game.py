"""`BASKETBALL_SIM_DEBUG_BOOST_USER_TEAM=1` 時のみの新規開始用 user 強化（環境変数・no-op 確認）。"""

from __future__ import annotations

from basketball_sim.main import (
    DEBUG_BOOST_USER_TEAM_ENV,
    apply_debug_boost_user_team_for_new_game,
    debug_boost_user_team_env_enabled,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


def _sample_user_team() -> Team:
    p = Player(
        player_id=1,
        name="T",
        age=22,
        nationality="Japan",
        position="PG",
        height_cm=190.0,
        weight_kg=85.0,
        shoot=60,
        three=55,
        drive=58,
        passing=62,
        rebound=40,
        defense=55,
        ft=70,
        stamina=75,
        ovr=68,
        potential="B",
        archetype="guard",
        usage_base=22,
        team_id=33,
    )
    t = Team(team_id=33, name="U", league_level=3, players=[p], money=2_000_000_000)
    t.popularity = 45
    t.sponsor_power = 50
    t.fan_base = 5000
    t.market_size = 1.15
    return t


def test_debug_boost_env_disabled_by_default(monkeypatch):
    monkeypatch.delenv(DEBUG_BOOST_USER_TEAM_ENV, raising=False)
    assert debug_boost_user_team_env_enabled() is False


def test_debug_boost_env_enabled_only_for_exact_one(monkeypatch):
    monkeypatch.setenv(DEBUG_BOOST_USER_TEAM_ENV, "1")
    assert debug_boost_user_team_env_enabled() is True
    monkeypatch.setenv(DEBUG_BOOST_USER_TEAM_ENV, "true")
    assert debug_boost_user_team_env_enabled() is False


def test_apply_debug_boost_noop_when_env_off(monkeypatch):
    monkeypatch.delenv(DEBUG_BOOST_USER_TEAM_ENV, raising=False)
    t = _sample_user_team()
    before_m = t.money
    before_ovr = t.players[0].ovr
    apply_debug_boost_user_team_for_new_game(t)
    assert t.money == before_m
    assert t.players[0].ovr == before_ovr


def test_apply_debug_boost_when_env_on(monkeypatch):
    monkeypatch.setenv(DEBUG_BOOST_USER_TEAM_ENV, "1")
    t = _sample_user_team()
    apply_debug_boost_user_team_for_new_game(t)
    assert t.money == 50_000_000_000
    assert t.sponsor_power == 100
    assert t.fan_base >= 25_000
    assert t.popularity >= 95
    assert t.players[0].ovr >= 68 + 12
