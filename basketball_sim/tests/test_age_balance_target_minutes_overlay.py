"""usage_policy.age_balance → get_age_balance_target_minutes_overlay（Rotation 目標分 T1）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team, get_age_balance_target_minutes_overlay


def _player(pid: int, age: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality="Japan",
        position="PG",
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


def _team(tid: int) -> Team:
    t = Team(team_id=tid, name="T", league_level=1, team_training_focus="balanced")
    t.add_player(_player(1, 24))
    return t


def _with_age_balance(t: Team, ab: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": ab,
            "injury_care": "standard",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_age_balance_balanced_is_zero():
    t = _with_age_balance(_team(1), "balanced")
    assert get_age_balance_target_minutes_overlay(t, "balanced", 20) == 0.0
    assert get_age_balance_target_minutes_overlay(t, "development", 25) == 0.0


def test_youth_full_on_balanced_usage():
    t = _with_age_balance(_team(2), "youth")
    # young: +0.3 T1, balanced usage ×1.0
    assert get_age_balance_target_minutes_overlay(t, "balanced", 20) == 0.3
    # mid: 0
    assert get_age_balance_target_minutes_overlay(t, "balanced", 28) == 0.0
    # veteran: -0.3
    assert get_age_balance_target_minutes_overlay(t, "balanced", 35) == -0.3


def test_development_youth_dampened():
    t = _with_age_balance(_team(3), "youth")
    # 0.3 * 0.3 = 0.09
    assert abs(get_age_balance_target_minutes_overlay(t, "development", 20) - 0.09) < 1e-9


def test_win_now_veteran_dampened():
    t = _with_age_balance(_team(4), "veteran")
    # veteran band +0.3, win_now × veteran 0.3
    assert abs(get_age_balance_target_minutes_overlay(t, "win_now", 35) - 0.09) < 1e-9


def test_win_now_youth_opposing_reduced():
    t = _with_age_balance(_team(5), "youth")
    # young +0.3, win_now × youth 0.5
    assert abs(get_age_balance_target_minutes_overlay(t, "win_now", 20) - 0.15) < 1e-9


def test_development_veteran_opposing_reduced():
    t = _with_age_balance(_team(6), "veteran")
    # young -0.3, development × veteran 0.5
    assert abs(get_age_balance_target_minutes_overlay(t, "development", 20) - (-0.15)) < 1e-9
