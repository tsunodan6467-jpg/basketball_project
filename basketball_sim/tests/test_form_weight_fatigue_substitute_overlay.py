"""usage_policy.form_weight + fatigue → get_form_weight_fatigue_substitute_overlay（Rotation 交代候補 v1）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team, get_form_weight_fatigue_substitute_overlay


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position="SG",
        height_cm=195.0,
        weight_kg=88.0,
        shoot=65,
        three=65,
        drive=60,
        passing=58,
        rebound=55,
        defense=60,
        ft=65,
        stamina=70,
        ovr=70,
        potential="B",
        archetype="balanced",
        usage_base=22,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team_with_form(fw: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.add_player(_player(1))
    t.add_player(_player(2))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": fw,
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_form_weight_standard_is_zero():
    t = _team_with_form("standard")
    assert get_form_weight_fatigue_substitute_overlay(t, 0) == 0.0
    assert get_form_weight_fatigue_substitute_overlay(t, 100) == 0.0


def test_form_weight_high_low_fatigue_plus_high_minus():
    t = _team_with_form("high")
    lo = get_form_weight_fatigue_substitute_overlay(t, 0)
    hi = get_form_weight_fatigue_substitute_overlay(t, 100)
    assert lo > 0
    assert hi < 0
    assert abs(lo - 0.3) < 1e-9
    assert abs(hi + 0.3) < 1e-9


def test_form_weight_skill_weaker_than_high():
    t_high = _team_with_form("high")
    t_skill = _team_with_form("skill")
    f = 20
    high_v = get_form_weight_fatigue_substitute_overlay(t_high, f)
    skill_v = get_form_weight_fatigue_substitute_overlay(t_skill, f)
    assert high_v > 0 and skill_v > 0
    assert abs(skill_v) < abs(high_v)
    assert abs(skill_v - high_v * 0.5) < 1e-9


def test_low_fatigue_beats_high_fatigue_on_overlay_when_form_high():
    """同じチーム・form_weight=high なら、低疲労候補の上乗せ > 高疲労候補。"""
    t = _team_with_form("high")
    a = get_form_weight_fatigue_substitute_overlay(t, 8)
    b = get_form_weight_fatigue_substitute_overlay(t, 88)
    assert a > b
    # 中心 50 付近はほぼ同水準
    assert abs(get_form_weight_fatigue_substitute_overlay(t, 50)) < 1e-9
