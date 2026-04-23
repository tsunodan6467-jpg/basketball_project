"""rotation.clutch_policy → get_clutch_policy_substitute_overlay / RotationSystem._find_best_substitute（終盤 v1）。"""

from unittest import mock

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_clutch_policy_substitute_overlay,
    get_default_team_tactics,
    get_evaluation_focus_substitute_overlay,
)


def _player(
    pid: int,
    *,
    position: str = "SF",
    ovr: int = 70,
    shoot: int = 60,
    three: int = 60,
    drive: int = 60,
    passing: int = 60,
    defense: int = 60,
    rebound: int = 60,
    fatigue: int = 0,
) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=198.0,
        weight_kg=90.0,
        shoot=shoot,
        three=three,
        drive=drive,
        passing=passing,
        rebound=rebound,
        defense=defense,
        ft=60,
        stamina=70,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
        fatigue=fatigue,
    )


def _team_with_clutch(clutch: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    rot = dict(d["rotation"])
    rot["clutch_policy"] = clutch
    t.team_tactics = {**d, "rotation": rot}
    ensure_team_tactics_on_team(t)
    return t


def test_overlay_zero_when_not_late_or_closing():
    t = _team_with_clutch("stars")
    p = _player(1)
    assert get_clutch_policy_substitute_overlay(t, p, False, False, roster_rank=0) == 0.0


def test_stars_favors_better_rank_and_ovr():
    t = _team_with_clutch("stars")
    hi = _player(1, ovr=82)
    lo = _player(2, ovr=62)
    late = get_clutch_policy_substitute_overlay(t, hi, True, False, roster_rank=0)
    late_lo = get_clutch_policy_substitute_overlay(t, lo, True, False, roster_rank=9)
    assert late > late_lo
    assert abs(late) <= 0.22 + 1e-9
    assert abs(late_lo) <= 0.22 + 1e-9


def test_defense_overlay_prefers_defensive_profile():
    t = _team_with_clutch("defense")
    d_hi = _player(1, defense=92, rebound=92, shoot=45, three=45)
    d_lo = _player(2, defense=48, rebound=48, shoot=88, three=88)
    v_hi = get_clutch_policy_substitute_overlay(t, d_hi, True, True, roster_rank=5)
    v_lo = get_clutch_policy_substitute_overlay(t, d_lo, True, True, roster_rank=5)
    assert v_hi > v_lo


def test_find_best_substitute_defense_picks_defender_late():
    t = _team_with_clutch("defense")
    p101 = _player(101, position="PG", ovr=70)
    p102 = _player(102, position="SG", ovr=70)
    p103 = _player(103, position="SF", ovr=70)
    p104 = _player(104, position="PF", ovr=70)
    p105 = _player(105, position="C", ovr=70)
    p106 = _player(
        106,
        position="SF",
        ovr=70,
        defense=92,
        rebound=92,
        shoot=45,
        three=45,
        drive=55,
        passing=55,
    )
    p107 = _player(
        107,
        position="SF",
        ovr=70,
        defense=45,
        rebound=45,
        shoot=88,
        three=88,
        drive=60,
        passing=60,
    )
    for p in (p101, p102, p103, p104, p105, p107, p106):
        t.add_player(p)

    starters = [p101, p102, p103, p104, p105]
    active = [p101, p102, p103, p104, p105, p106, p107]
    rot = RotationSystem(t, active, starters=starters)
    out = p103
    in_cands = [p106, p107]

    def _z(*_a, **_k):
        return 0.0

    with mock.patch.object(rot, "_get_sixth_man_key", return_value=None):
        with mock.patch.object(rot, "_get_bench_order_bonus_map", return_value={}):
            with mock.patch("basketball_sim.systems.rotation.get_form_weight_fatigue_substitute_overlay", _z):
                with mock.patch("basketball_sim.systems.rotation.get_foreign_player_usage_substitute_overlay", _z):
                    with mock.patch(
                        "basketball_sim.systems.rotation.get_evaluation_focus_substitute_overlay", _z
                    ):
                        with mock.patch(
                            "basketball_sim.systems.rotation.get_injury_care_substitute_overlay", _z
                        ):
                            pick = rot._find_best_substitute(out, in_cands, 155, 160)
    assert pick is p106


def test_find_best_substitute_offense_picks_shooter_late():
    t = _team_with_clutch("offense")
    p101 = _player(101, position="PG", ovr=70)
    p102 = _player(102, position="SG", ovr=70)
    p103 = _player(103, position="SF", ovr=70)
    p104 = _player(104, position="PF", ovr=70)
    p105 = _player(105, position="C", ovr=70)
    p106 = _player(
        106,
        position="SF",
        ovr=70,
        defense=92,
        rebound=92,
        shoot=45,
        three=45,
        drive=55,
        passing=55,
    )
    p107 = _player(
        107,
        position="SF",
        ovr=70,
        defense=45,
        rebound=45,
        shoot=88,
        three=88,
        drive=60,
        passing=60,
    )
    for p in (p101, p102, p103, p104, p105, p106, p107):
        t.add_player(p)

    starters = [p101, p102, p103, p104, p105]
    active = [p101, p102, p103, p104, p105, p106, p107]
    rot = RotationSystem(t, active, starters=starters)
    out = p103
    in_cands = [p106, p107]

    def _z(*_a, **_k):
        return 0.0

    with mock.patch.object(rot, "_get_sixth_man_key", return_value=None):
        with mock.patch.object(rot, "_get_bench_order_bonus_map", return_value={}):
            with mock.patch("basketball_sim.systems.rotation.get_form_weight_fatigue_substitute_overlay", _z):
                with mock.patch("basketball_sim.systems.rotation.get_foreign_player_usage_substitute_overlay", _z):
                    with mock.patch(
                        "basketball_sim.systems.rotation.get_evaluation_focus_substitute_overlay", _z
                    ):
                        with mock.patch(
                            "basketball_sim.systems.rotation.get_injury_care_substitute_overlay", _z
                        ):
                            pick = rot._find_best_substitute(out, in_cands, 155, 160)
    assert pick is p107


def test_hot_hand_differs_from_offense_equal_four_way_mean():
    """同じ shoot+three+drive+passing 平均でも、hot_hand は three/shoot 寄りで差が付く。"""
    t_hot = _team_with_clutch("hot_hand")
    t_off = _team_with_clutch("offense")
    a = _player(1, shoot=50, three=50, drive=62, passing=62)
    b = _player(2, shoot=62, three=62, drive=50, passing=50)
    off_a = get_clutch_policy_substitute_overlay(t_off, a, True, True, roster_rank=5)
    off_b = get_clutch_policy_substitute_overlay(t_off, b, True, True, roster_rank=5)
    assert off_a == pytest.approx(off_b)
    hot_a = get_clutch_policy_substitute_overlay(t_hot, a, True, True, roster_rank=5)
    hot_b = get_clutch_policy_substitute_overlay(t_hot, b, True, True, roster_rank=5)
    assert hot_b > hot_a


def test_find_best_substitute_hot_hand_prefers_sharp_shooter_late():
    t = _team_with_clutch("hot_hand")
    p101 = _player(101, position="PG", ovr=70)
    p102 = _player(102, position="SG", ovr=70)
    p103 = _player(103, position="SF", ovr=70)
    p104 = _player(104, position="PF", ovr=70)
    p105 = _player(105, position="C", ovr=70)
    p106 = _player(106, position="SF", ovr=70, shoot=50, three=50, drive=62, passing=62)
    p107 = _player(107, position="SF", ovr=70, shoot=62, three=62, drive=50, passing=50)
    for p in (p101, p102, p103, p104, p105, p106, p107):
        t.add_player(p)

    starters = [p101, p102, p103, p104, p105]
    active = [p101, p102, p103, p104, p105, p106, p107]
    rot = RotationSystem(t, active, starters=starters)
    out = p103
    in_cands = [p106, p107]

    def _z(*_a, **_k):
        return 0.0

    with mock.patch.object(rot, "_get_sixth_man_key", return_value=None):
        with mock.patch.object(rot, "_get_bench_order_bonus_map", return_value={}):
            with mock.patch("basketball_sim.systems.rotation.get_form_weight_fatigue_substitute_overlay", _z):
                with mock.patch("basketball_sim.systems.rotation.get_foreign_player_usage_substitute_overlay", _z):
                    with mock.patch(
                        "basketball_sim.systems.rotation.get_evaluation_focus_substitute_overlay", _z
                    ):
                        with mock.patch(
                            "basketball_sim.systems.rotation.get_injury_care_substitute_overlay", _z
                        ):
                            pick = rot._find_best_substitute(out, in_cands, 155, 160)
    assert pick is p107


def test_overlay_abs_bounded():
    t = _team_with_clutch("offense")
    p = _player(1, shoot=99, three=99, drive=99, passing=99)
    v = abs(get_clutch_policy_substitute_overlay(t, p, True, True, roster_rank=0))
    assert v <= 0.22 + 1e-9


def test_evaluation_focus_overall_unchanged_independent_of_clutch():
    """起用テンプレ overall=0 はそのまま。clutch は rotation 側で別加算。"""
    t = _team_with_clutch("stars")
    t.team_tactics = {
        **get_default_team_tactics(),
        "usage_policy": {**get_default_team_tactics()["usage_policy"], "evaluation_focus": "overall"},
        "rotation": {**get_default_team_tactics()["rotation"], "clutch_policy": "stars"},
    }
    ensure_team_tactics_on_team(t)
    p = _player(1, ovr=80)
    assert get_evaluation_focus_substitute_overlay(t, p) == 0.0
    assert get_clutch_policy_substitute_overlay(t, p, True, False, roster_rank=0) != 0.0
