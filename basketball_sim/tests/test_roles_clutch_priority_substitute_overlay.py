"""roles.clutch_priority → get_roles_clutch_priority_substitute_overlay / _find_best_substitute（終盤のみ）。"""

from unittest import mock

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_clutch_policy_substitute_overlay,
    get_default_team_tactics,
    get_roles_clutch_priority_substitute_overlay,
)


def _player(pid: int, **kwargs) -> Player:
    base = dict(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position="SF",
        height_cm=198.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=70,
        ovr=70,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
        fatigue=0,
    )
    base.update(kwargs)
    return Player(**base)


def _team_with_clutch_role(clutch_role: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    d["roles"] = {
        "1": {
            "clutch_priority": clutch_role,
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "secondary",
            "main_role": "none",
        }
    }
    t.team_tactics = d
    ensure_team_tactics_on_team(t)
    return t


def test_standard_zero_even_when_late():
    t = _team_with_clutch_role("standard")
    p = _player(1)
    assert get_roles_clutch_priority_substitute_overlay(t, p, True, False) == 0.0
    assert get_roles_clutch_priority_substitute_overlay(t, p, True, True) == 0.0


def test_go_to_positive_late_zero_early():
    t = _team_with_clutch_role("go_to")
    p = _player(1)
    assert get_roles_clutch_priority_substitute_overlay(t, p, False, False) == 0.0
    v = get_roles_clutch_priority_substitute_overlay(t, p, True, True)
    assert v > 0.0
    assert v <= 0.10 + 1e-9


def test_limited_negative_late_zero_early():
    t = _team_with_clutch_role("limited")
    p = _player(1)
    assert get_roles_clutch_priority_substitute_overlay(t, p, False, False) == 0.0
    v = get_roles_clutch_priority_substitute_overlay(t, p, True, False)
    assert v < 0.0
    assert v >= -0.10 - 1e-9


def test_personal_weaker_than_clutch_policy_cap():
    """|roles| max 0.10 < |clutch_policy| max 0.22。同時乗算でも個人の方が小さい帯。"""
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    d["rotation"] = {**d["rotation"], "clutch_policy": "defense"}
    d["roles"] = {
        "1": {
            "clutch_priority": "go_to",
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "secondary",
            "main_role": "none",
        }
    }
    t.team_tactics = d
    ensure_team_tactics_on_team(t)
    p = _player(1, defense=88, rebound=88, shoot=50, three=50)
    team = get_clutch_policy_substitute_overlay(t, p, True, True, roster_rank=5)
    personal = get_roles_clutch_priority_substitute_overlay(t, p, True, True)
    assert abs(personal) <= 0.10 + 1e-9
    assert abs(team) <= 0.22 + 1e-9
    assert 0.10 < 0.22 - 1e-9
    assert abs(personal) < abs(team)  # 典型ケース: 守備高めで team が十分プラス


def test_find_best_substitute_go_to_beats_limited_late_isolated():
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    d["rotation"] = {**d["rotation"], "clutch_policy": "offense"}
    t.team_tactics = d
    ensure_team_tactics_on_team(t)

    p101 = _player(101, position="PG", ovr=70)
    p102 = _player(102, position="SG", ovr=70)
    p103 = _player(103, position="SF", ovr=70)
    p104 = _player(104, position="PF", ovr=70)
    p105 = _player(105, position="C", ovr=70)
    p106 = _player(106, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=60, defense=60, rebound=60)
    p107 = _player(107, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=60, defense=60, rebound=60)
    t.team_tactics["roles"] = {
        "106": {
            "clutch_priority": "limited",
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "secondary",
            "main_role": "none",
        },
        "107": {
            "clutch_priority": "go_to",
            "shot_priority": "standard",
            "offense_involvement": "standard",
            "playmaking_role": "secondary",
            "main_role": "none",
        },
    }
    ensure_team_tactics_on_team(t)
    for p in (p101, p102, p103, p104, p105, p106, p107):
        t.add_player(p)

    starters = [p101, p102, p103, p104, p105]
    active = [p101, p102, p103, p104, p105, p106, p107]
    rot = RotationSystem(t, active, starters=starters)
    out = p103
    in_cands = [p106, p107]
    total = 200
    late_poss = 190

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
                                        with mock.patch(
                                            "basketball_sim.systems.rotation.get_roles_playmaking_role_substitute_overlay",
                                            _z,
                                        ):
                                            pick = rot._find_best_substitute(
                                                out, in_cands, late_poss, total
                                            )
    assert pick is p107


def test_missing_roles_row_is_zero():
    t = _team_with_clutch_role("go_to")
    t.team_tactics["roles"] = {}
    ensure_team_tactics_on_team(t)
    p = _player(1)
    assert get_roles_clutch_priority_substitute_overlay(t, p, True, True) == 0.0
