"""usage_policy.schedule_care × RegSlot → get_schedule_care_target_minutes_overlay / Rotation 目標分 T1。"""

from basketball_sim.models.player import Player
from basketball_sim.models.reg_slot import RegSlot
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_schedule_care_target_minutes_overlay,
)


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
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
    t.add_player(_player(1))
    return t


def _with_usage(t: Team, schedule_care: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": schedule_care,
            "foreign_player_usage": "balanced",
        },
        "rotation": {},
        "team_strategy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(t)
    return t


def test_reg_slot_none_overlay_zero():
    t = _with_usage(_team(1), "rest")
    assert get_schedule_care_target_minutes_overlay(t, None, "regular_season") == 0.0


def test_round_index_one_all_modes_zero():
    t = _with_usage(_team(2), "rest")
    assert get_schedule_care_target_minutes_overlay(t, RegSlot(1, "Wed"), "regular_season") == 0.0
    t2 = _with_usage(_team(3), "win")
    assert get_schedule_care_target_minutes_overlay(t2, RegSlot(1, None), "regular_season") == 0.0
    t3 = _with_usage(_team(4), "standard")
    assert get_schedule_care_target_minutes_overlay(t3, RegSlot(1, "Sat"), "regular_season") == 0.0


def test_round_index_two_plus_rest_standard_win():
    t_r = _with_usage(_team(5), "rest")
    t_s = _with_usage(_team(6), "standard")
    t_w = _with_usage(_team(7), "win")
    slot2 = RegSlot(2, "Sat")
    assert get_schedule_care_target_minutes_overlay(t_r, slot2, "regular_season") == -0.3
    assert get_schedule_care_target_minutes_overlay(t_s, slot2, "regular_season") == 0.0
    assert get_schedule_care_target_minutes_overlay(t_w, slot2, "regular_season") == 0.2


def test_non_regular_season_competition_overlay_zero_with_two_game_slot():
    t = _with_usage(_team(8), "rest")
    assert get_schedule_care_target_minutes_overlay(t, RegSlot(2, None), "playoff") == 0.0


def test_rotation_target_minutes_diff_none_vs_r2_rest_and_win():
    """
    同一 team / 同一先発: reg_slot なし と round_index=2 では
    rest は少し下がり、win は少し上がる（他条件同一）。
    """
    t = Team(team_id=99, name="Home", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        p = _player(500 + i)
        p.position = pos
        t.add_player(p)
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": "rest",
            "foreign_player_usage": "balanced",
        },
        "rotation": {},
        "team_strategy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(t)
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    starters = active[:5]
    k0 = RotationSystem(t, active, starters=starters)._player_key(starters[0])

    rot0 = RotationSystem(
        t, active, starters=starters, competition_type="regular_season", reg_slot=None
    )
    m0 = rot0._build_target_minutes_map()
    rot_r = RotationSystem(
        t,
        active,
        starters=starters,
        competition_type="regular_season",
        reg_slot=RegSlot(2, None),
    )
    m_r = rot_r._build_target_minutes_map()
    t.team_tactics["usage_policy"]["schedule_care"] = "win"
    ensure_team_tactics_on_team(t)
    rot_w = RotationSystem(
        t,
        active,
        starters=starters,
        competition_type="regular_season",
        reg_slot=RegSlot(2, None),
    )
    m_w = rot_w._build_target_minutes_map()
    # +0.2 - (-0.3) = 0.5 between win and rest at r2
    assert m_r[k0] < m0[k0]
    assert m_w[k0] > m0[k0]
    assert abs((m_w[k0] - m_r[k0]) - 0.5) < 1e-6
