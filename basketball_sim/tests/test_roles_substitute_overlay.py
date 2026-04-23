"""roles.shot_priority / offense_involvement / playmaking_role → substitute overlay（Rotation IN 候補）。"""

from unittest import mock

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_roles_offense_involvement_substitute_overlay,
    get_roles_playmaking_role_substitute_overlay,
    get_roles_shot_priority_substitute_overlay,
)


def _player(
    pid: int,
    *,
    position: str = "SF",
    ovr: int = 70,
    potential: str = "B",
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
        potential=potential,
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
        fatigue=fatigue,
    )


def _team_base(*, evaluation_focus: str = "overall") -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    d["usage_policy"] = {**d["usage_policy"], "evaluation_focus": evaluation_focus}
    t.team_tactics = d
    ensure_team_tactics_on_team(t)
    return t


def test_shot_priority_standard_overlay_zero():
    t = _team_base()
    p = _player(1)
    t.team_tactics["roles"] = {str(1): {"shot_priority": "standard", "offense_involvement": "standard"}}
    ensure_team_tactics_on_team(t)
    assert get_roles_shot_priority_substitute_overlay(t, p) == 0.0


def test_offense_involvement_standard_overlay_zero():
    t = _team_base()
    p = _player(1)
    t.team_tactics["roles"] = {str(1): {"shot_priority": "standard", "offense_involvement": "standard"}}
    ensure_team_tactics_on_team(t)
    assert get_roles_offense_involvement_substitute_overlay(t, p) == 0.0


def test_shot_priority_aggressive_favors_high_shoot_profile_over_passive():
    t_agg = _team_base()
    t_pas = _team_base()
    p = _player(1, shoot=85, three=85, drive=85, passing=50)
    t_agg.team_tactics["roles"] = {str(1): {"shot_priority": "aggressive", "offense_involvement": "standard"}}
    t_pas.team_tactics["roles"] = {str(1): {"shot_priority": "passive", "offense_involvement": "standard"}}
    ensure_team_tactics_on_team(t_agg)
    ensure_team_tactics_on_team(t_pas)
    o_agg = get_roles_shot_priority_substitute_overlay(t_agg, p)
    o_pas = get_roles_shot_priority_substitute_overlay(t_pas, p)
    assert o_agg > o_pas
    assert abs(o_agg) <= 0.12 + 1e-9
    assert abs(o_pas) <= 0.12 + 1e-9


def test_offense_involvement_high_favors_passing_drive_profile_over_low():
    t_hi = _team_base()
    t_lo = _team_base()
    p = _player(1, shoot=50, three=50, drive=85, passing=90, defense=60, rebound=60)
    t_hi.team_tactics["roles"] = {str(1): {"shot_priority": "standard", "offense_involvement": "high"}}
    t_lo.team_tactics["roles"] = {str(1): {"shot_priority": "standard", "offense_involvement": "low"}}
    ensure_team_tactics_on_team(t_hi)
    ensure_team_tactics_on_team(t_lo)
    o_hi = get_roles_offense_involvement_substitute_overlay(t_hi, p)
    o_lo = get_roles_offense_involvement_substitute_overlay(t_lo, p)
    assert o_hi > o_lo
    assert abs(o_hi) <= 0.12 + 1e-9
    assert abs(o_lo) <= 0.12 + 1e-9


def test_evaluation_focus_offense_damps_roles_overlays_vs_overall():
    """offense focus 時は roles 2 項目に damp 0.5（involvement は standard で shot のみ比較）。"""
    t_over = _team_base(evaluation_focus="overall")
    t_off = _team_base(evaluation_focus="offense")
    p = _player(1, shoot=90, three=90, drive=90, passing=50)
    roles = {str(1): {"shot_priority": "aggressive", "offense_involvement": "standard"}}
    t_over.team_tactics["roles"] = dict(roles)
    t_off.team_tactics["roles"] = dict(roles)
    ensure_team_tactics_on_team(t_over)
    ensure_team_tactics_on_team(t_off)
    s_over = get_roles_shot_priority_substitute_overlay(t_over, p)
    s_off = get_roles_shot_priority_substitute_overlay(t_off, p)
    assert s_off < s_over
    assert s_off == pytest.approx(s_over * 0.5, rel=0, abs=1e-6)
    assert get_roles_offense_involvement_substitute_overlay(t_over, p) == 0.0
    assert get_roles_offense_involvement_substitute_overlay(t_off, p) == 0.0


def test_combined_abs_overlays_at_most_point_two_zero():
    t = _team_base()
    p = _player(1, shoot=95, three=95, drive=95, passing=95)
    t.team_tactics["roles"] = {
        str(1): {
            "shot_priority": "aggressive",
            "offense_involvement": "high",
            "playmaking_role": "secondary",
        }
    }
    ensure_team_tactics_on_team(t)
    s = get_roles_shot_priority_substitute_overlay(t, p)
    i = get_roles_offense_involvement_substitute_overlay(t, p)
    assert abs(s) + abs(i) <= 0.20 + 1e-9
    assert get_roles_playmaking_role_substitute_overlay(t, p) == 0.0


def test_playmaking_role_secondary_overlay_zero():
    t = _team_base()
    p = _player(1, passing=90, drive=80)
    t.team_tactics["roles"] = {
        str(1): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "secondary",
        }
    }
    ensure_team_tactics_on_team(t)
    assert get_roles_playmaking_role_substitute_overlay(t, p) == 0.0


def test_playmaking_role_primary_favors_high_passing():
    t = _team_base()
    lo = _player(1, passing=52, drive=55, shoot=50, three=50)
    hi = _player(2, passing=92, drive=55, shoot=50, three=50)
    roles_lo = {
        str(1): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        }
    }
    roles_hi = {
        str(2): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        }
    }
    t.team_tactics["roles"] = {**roles_lo, **roles_hi}
    ensure_team_tactics_on_team(t)
    o_lo = get_roles_playmaking_role_substitute_overlay(t, lo)
    o_hi = get_roles_playmaking_role_substitute_overlay(t, hi)
    assert o_hi > o_lo
    assert abs(o_hi) <= 0.10 + 1e-9
    assert abs(o_lo) <= 0.10 + 1e-9


def test_playmaking_role_minimal_is_opposite_bias_to_primary_high_passing():
    t_pri = _team_base()
    t_min = _team_base()
    p = _player(1, passing=90, drive=75, shoot=50, three=50)
    t_pri.team_tactics["roles"] = {
        str(1): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        }
    }
    t_min.team_tactics["roles"] = {
        str(1): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "minimal",
        }
    }
    ensure_team_tactics_on_team(t_pri)
    ensure_team_tactics_on_team(t_min)
    o_pri = get_roles_playmaking_role_substitute_overlay(t_pri, p)
    o_min = get_roles_playmaking_role_substitute_overlay(t_min, p)
    assert o_pri > 0.0
    assert o_min < 0.0
    assert o_pri > o_min


def test_playmaking_role_offense_focus_damps_vs_overall():
    t_over = _team_base(evaluation_focus="overall")
    t_off = _team_base(evaluation_focus="offense")
    p = _player(1, passing=88, drive=70, shoot=50, three=50)
    roles = {
        str(1): {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        }
    }
    t_over.team_tactics["roles"] = dict(roles)
    t_off.team_tactics["roles"] = dict(roles)
    ensure_team_tactics_on_team(t_over)
    ensure_team_tactics_on_team(t_off)
    o_over = get_roles_playmaking_role_substitute_overlay(t_over, p)
    o_off = get_roles_playmaking_role_substitute_overlay(t_off, p)
    assert o_off < o_over
    assert o_off == pytest.approx(o_over * 0.5, rel=0, abs=1e-6)


def test_roles_three_item_combined_abs_cap():
    t = _team_base()
    p = _player(1, shoot=95, three=95, drive=95, passing=95)
    t.team_tactics["roles"] = {
        str(1): {
            "shot_priority": "aggressive",
            "offense_involvement": "high",
            "playmaking_role": "primary",
        }
    }
    ensure_team_tactics_on_team(t)
    s = get_roles_shot_priority_substitute_overlay(t, p)
    i = get_roles_offense_involvement_substitute_overlay(t, p)
    m = get_roles_playmaking_role_substitute_overlay(t, p)
    assert abs(s) + abs(i) + abs(m) <= 0.28 + 1e-9


def test_overall_no_damp_matches_double_offense_focus_for_same_roles():
    """defense focus でも damp 1.0（offense のみ 0.5）。"""
    t_def = _team_base(evaluation_focus="defense")
    t_off = _team_base(evaluation_focus="offense")
    p = _player(1, shoot=88, three=88, drive=88, passing=50)
    roles = {str(1): {"shot_priority": "aggressive", "offense_involvement": "standard"}}
    t_def.team_tactics["roles"] = dict(roles)
    t_off.team_tactics["roles"] = dict(roles)
    ensure_team_tactics_on_team(t_def)
    ensure_team_tactics_on_team(t_off)
    s_def = get_roles_shot_priority_substitute_overlay(t_def, p)
    s_off = get_roles_shot_priority_substitute_overlay(t_off, p)
    assert s_def == pytest.approx(s_off * 2.0, rel=0, abs=1e-5)


def test_find_best_substitute_roles_shot_priority_breaks_tie():
    t = _team_base(evaluation_focus="overall")
    t.team_tactics["roles"] = {
        "106": {"shot_priority": "aggressive", "offense_involvement": "standard"},
        "107": {"shot_priority": "aggressive", "offense_involvement": "standard"},
    }
    ensure_team_tactics_on_team(t)

    p101 = _player(101, position="PG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p102 = _player(102, position="SG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p103 = _player(103, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p104 = _player(104, position="PF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p105 = _player(105, position="C", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p106 = _player(106, position="SF", ovr=70, shoot=55, three=55, drive=55, passing=60)
    p107 = _player(107, position="SF", ovr=70, shoot=92, three=92, drive=92, passing=60)
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
                            with mock.patch(
                                "basketball_sim.systems.rotation.get_clutch_policy_substitute_overlay", _z
                            ):
                                with mock.patch(
                                    "basketball_sim.systems.rotation.get_roles_offense_involvement_substitute_overlay",
                                    _z,
                                ):
                                    with mock.patch(
                                        "basketball_sim.systems.rotation.get_roles_playmaking_role_substitute_overlay",
                                        _z,
                                    ):
                                        pick = rot._find_best_substitute(out, in_cands, 0, 160)
    assert pick is p107


def test_find_best_substitute_playmaking_role_breaks_tie():
    t = _team_base(evaluation_focus="overall")
    t.team_tactics["roles"] = {
        "106": {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        },
        "107": {
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "primary",
        },
    }
    ensure_team_tactics_on_team(t)

    p101 = _player(101, position="PG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p102 = _player(102, position="SG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p103 = _player(103, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p104 = _player(104, position="PF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p105 = _player(105, position="C", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p106 = _player(106, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=58, defense=60, rebound=60)
    p107 = _player(107, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=95, defense=60, rebound=60)
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
                            with mock.patch(
                                "basketball_sim.systems.rotation.get_clutch_policy_substitute_overlay", _z
                            ):
                                with mock.patch(
                                    "basketball_sim.systems.rotation.get_roles_shot_priority_substitute_overlay", _z
                                ):
                                    with mock.patch(
                                        "basketball_sim.systems.rotation.get_roles_offense_involvement_substitute_overlay",
                                        _z,
                                    ):
                                        pick = rot._find_best_substitute(out, in_cands, 0, 160)
    assert pick is p107
