"""team_tactics.defense_style pressure → Match._simulate_possession steal_rate（第3弾B）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_defense_style_steal_rate_delta,
)


def _team(tid: int, name: str) -> Team:
    return Team(team_id=tid, name=name, league_level=1, team_training_focus="balanced")


def _with_defense_style(t: Team, defense_style: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "defense_style": defense_style,
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_pressure_balanced_strategy_full_t1_delta():
    """T4: 戦略 balanced かつ pressure → 満額 T1（+0.002）。"""
    t = _with_defense_style(_team(1, "A"), "pressure")
    t.strategy = "balanced"
    assert get_defense_style_steal_rate_delta(t, "balanced") == 0.002


def test_pressure_defense_strategy_dampened():
    """T2: 戦略 defense かつ pressure → 0.2〜0.4 減衰（0.3 倍）で満額より小さい。"""
    t = _with_defense_style(_team(2, "B"), "pressure")
    t.strategy = "defense"
    d = get_defense_style_steal_rate_delta(t, "defense")
    assert d == 0.002 * 0.3
    assert d < 0.002


def test_pressure_run_and_gun_strategy_conflict_zero():
    """T3: 戦略 run_and_gun かつ pressure → 0（衝突）。"""
    t = _with_defense_style(_team(3, "C"), "pressure")
    t.strategy = "run_and_gun"
    assert get_defense_style_steal_rate_delta(t, "run_and_gun") == 0.0


def test_non_pressure_defense_style_zero():
    """protect_* / balanced の defense_style は steal 加算 0（ヘルパー）。"""
    t = _with_defense_style(_team(4, "D"), "protect_paint")
    t.strategy = "balanced"
    assert get_defense_style_steal_rate_delta(t, "balanced") == 0.0
