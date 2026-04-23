"""usage_policy.injury_care + fatigue/stamina → get_injury_care_substitute_overlay（Rotation 交代候補 v1）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_form_weight_fatigue_substitute_overlay,
    get_injury_care_substitute_overlay,
)


def _player(pid: int, fatigue: int = 50, stamina_attr: int = 70, pos: str = "SG") -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=pos,
        height_cm=195.0,
        weight_kg=88.0,
        shoot=65,
        three=65,
        drive=60,
        passing=58,
        rebound=55,
        defense=60,
        ft=65,
        stamina=stamina_attr,
        ovr=70,
        potential="B",
        archetype="balanced",
        usage_base=22,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
        fatigue=fatigue,
    )


def _team(ic: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.add_player(_player(1))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": ic,
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_injury_care_standard_is_zero():
    t = _team("standard")
    assert get_injury_care_substitute_overlay(t, 0, 100) == 0.0
    assert get_injury_care_substitute_overlay(t, 100, 0) == 0.0


def test_injury_care_high_worse_when_high_fatigue_and_low_stamina():
    t = _team("high")
    bad = get_injury_care_substitute_overlay(t, 95, 20)
    better = get_injury_care_substitute_overlay(t, 15, 90)
    assert bad < better
    assert bad < 0.0
    assert -0.26 < bad < 0.0
    assert abs(bad) <= 0.25 + 1e-9


def test_injury_care_low_weaker_and_often_milder_than_high():
    t_h = _team("high")
    t_l = _team("low")
    f, s = 80, 40
    h = get_injury_care_substitute_overlay(t_h, f, s)
    lo = get_injury_care_substitute_overlay(t_l, f, s)
    assert h < 0.0
    assert lo >= -0.05
    assert lo <= 0.10 + 1e-9
    assert abs(lo) < abs(h)


def test_fresh_beats_tired_on_overlay_when_injury_high():
    """能力差を避けるため overlay 差だけ比較: 高では低疲労の上乗せ > 高疲労。"""
    t = _team("high")
    a = get_injury_care_substitute_overlay(t, 5, 90)
    b = get_injury_care_substitute_overlay(t, 95, 25)
    assert a > b


def test_injury_high_plus_form_weight_high_bounded():
    """form_weight=high 同時でも暴れすぎない（standard form で injury 分が主）。"""
    t = Team(team_id=2, name="T2", league_level=1, team_training_focus="balanced")
    t.add_player(_player(1))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "high",
            "age_balance": "balanced",
            "injury_care": "high",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    f = 60
    st = 70
    inj = get_injury_care_substitute_overlay(t, f, st)
    form = get_form_weight_fatigue_substitute_overlay(t, f)
    assert abs(inj) <= 0.25 + 1e-9
    assert abs(form) <= 0.3 + 1e-9
    assert abs(inj) + abs(form) < 0.6


def test_find_best_prefers_fresher_injury_care_high():
    """2 候補 OVR 同等・合法前提で injury_care=high なら疲労低い方が選ばれやすい（overlay 合算比較）。"""
    t = Team(team_id=3, name="T3", league_level=1, team_training_focus="balanced")
    t.add_player(_player(10, fatigue=5, stamina_attr=85))
    t.add_player(_player(11, fatigue=95, stamina_attr=35))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "high",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    low_f = next(p for p in active if p.player_id == 10)
    hi_f = next(p for p in active if p.player_id == 11)
    st_l = int(low_f.get_adjusted_attribute("stamina"))
    st_h = int(hi_f.get_adjusted_attribute("stamina"))
    s_high = get_injury_care_substitute_overlay(
        t, int(getattr(low_f, "fatigue", 0) or 0), st_l
    ) - get_injury_care_substitute_overlay(
        t, int(getattr(hi_f, "fatigue", 0) or 0), st_h
    )
    t.team_tactics["usage_policy"]["injury_care"] = "standard"
    ensure_team_tactics_on_team(t)
    s_std = get_injury_care_substitute_overlay(
        t, int(getattr(low_f, "fatigue", 0) or 0), st_l
    ) - get_injury_care_substitute_overlay(
        t, int(getattr(hi_f, "fatigue", 0) or 0), st_h
    )
    assert s_high > 0
    assert abs(s_std) < 1e-9


def test_find_best_substitute_prefers_fresher_when_injury_high() -> None:
    """2 候補は同ポジ同 OVR、差は疲労のみ。injury_care=high なら低疲労候補が選ばれる。"""
    t = Team(team_id=3, name="T3", league_level=1, team_training_focus="balanced")
    for i, f, st in [
        (1, 9, 88),
        (2, 8, 88),
        (3, 7, 88),
        (4, 6, 88),
        (5, 5, 88),
        (6, 3, 88),
        (7, 90, 35),
    ]:
        t.add_player(_player(100 + i, fatigue=f, stamina_attr=st, pos="PF"))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "high",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    starters = active[:5]
    p_out = starters[0]
    p_fresh = next(p for p in active if p.player_id == 106)
    p_tired = next(p for p in active if p.player_id == 107)
    assert p_fresh not in starters
    assert p_tired not in starters
    rot = RotationSystem(t, active, starters=starters)
    from unittest import mock

    with mock.patch.object(rot, "_is_lineup_legal_after_swap", return_value=True):
        with mock.patch.object(rot, "_pair_swap_blocked", return_value=False):
            pick = rot._find_best_substitute(p_out, [p_tired, p_fresh], 0, 160)
    assert pick is p_fresh
