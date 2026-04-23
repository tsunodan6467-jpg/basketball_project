"""usage_policy.evaluation_focus → get_evaluation_focus_substitute_overlay（合法通過後候補 v1）。"""

from unittest import mock

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_evaluation_focus_substitute_overlay,
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


def _team_with_eval(focus: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": focus,
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": "standard",
            "foreign_player_usage": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_overall_is_always_zero():
    t = _team_with_eval("overall")
    p = _player(1)
    assert get_evaluation_focus_substitute_overlay(t, p) == 0.0


def test_offense_higher_for_high_offense_stats():
    t = _team_with_eval("offense")
    low = _player(1, shoot=50, three=50, drive=50, passing=50)
    high = _player(2, shoot=90, three=90, drive=90, passing=90)
    o_low = get_evaluation_focus_substitute_overlay(t, low)
    o_high = get_evaluation_focus_substitute_overlay(t, high)
    assert o_high > o_low
    assert -0.25 - 1e-9 <= o_low <= 0.25 + 1e-9
    assert -0.25 - 1e-9 <= o_high <= 0.25 + 1e-9


def test_defense_higher_for_high_defense_rebound():
    t = _team_with_eval("defense")
    low = _player(1, defense=50, rebound=50)
    high = _player(2, defense=90, rebound=90)
    o_low = get_evaluation_focus_substitute_overlay(t, low)
    o_high = get_evaluation_focus_substitute_overlay(t, high)
    assert o_high > o_low


def test_potential_higher_for_higher_cap():
    t = _team_with_eval("potential")
    lo = _player(1, potential="D")
    hi = _player(2, potential="S")
    o_lo = get_evaluation_focus_substitute_overlay(t, lo)
    o_hi = get_evaluation_focus_substitute_overlay(t, hi)
    assert o_hi > o_lo
    assert o_hi == pytest.approx(0.25)
    assert o_lo == pytest.approx(-0.25)


def test_t1_magnitude_at_most_configured():
    t_off = _team_with_eval("offense")
    t_def = _team_with_eval("defense")
    t_pot = _team_with_eval("potential")
    p = _player(1, shoot=99, three=99, drive=99, passing=99, defense=99, rebound=99, potential="S")
    for tt in (t_off, t_def, t_pot):
        v = abs(get_evaluation_focus_substitute_overlay(tt, p))
        assert v <= 0.25 + 1e-9


def test_find_best_substitute_prefers_higher_offense_when_focus_offense():
    """
    合法候補同士で、他オーバーレイ0・本流項が揃うよう近づけ、攻撃重視で攻撃高の選手が選ばれる。
    overall では同条件で攻撃差が 0 なら同点（先に見た方が残る）で攻撃高が外れない。
    """
    t = _team_with_eval("offense")
    # 7人: 先発5 + 控え2。out は SF 103。控え 106/107 は同ポジ同 OVR。106 は攻撃低、107 は攻撃高
    p101 = _player(101, position="PG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p102 = _player(102, position="SG", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p103 = _player(103, position="SF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p104 = _player(104, position="PF", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p105 = _player(105, position="C", ovr=70, shoot=60, three=60, drive=60, passing=60)
    p106 = _player(106, position="SF", ovr=70, shoot=50, three=50, drive=50, passing=50, defense=60, rebound=60)
    p107 = _player(107, position="SF", ovr=70, shoot=90, three=90, drive=90, passing=90, defense=60, rebound=60)
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
                    pick = rot._find_best_substitute(out, in_cands, 0, 160)
    assert pick is p107

    d = get_default_team_tactics()
    t.team_tactics = d
    t.team_tactics["usage_policy"] = {**d["usage_policy"], "evaluation_focus": "overall"}
    ensure_team_tactics_on_team(t)
    rot0 = RotationSystem(t, active, starters=starters)
    with mock.patch.object(rot0, "_get_sixth_man_key", return_value=None):
        with mock.patch.object(rot0, "_get_bench_order_bonus_map", return_value={}):
            with mock.patch("basketball_sim.systems.rotation.get_form_weight_fatigue_substitute_overlay", _z):
                with mock.patch("basketball_sim.systems.rotation.get_foreign_player_usage_substitute_overlay", _z):
                    pick0 = rot0._find_best_substitute(out, in_cands, 0, 160)
    # 同点なら先頭 106 が best のまま
    assert pick0 is p106
