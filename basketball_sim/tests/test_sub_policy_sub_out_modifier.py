"""rotation.sub_policy → get_sub_policy_sub_out_modifier / RotationSystem._can_sub_out（v1）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_sub_policy_sub_out_modifier,
)


def _player(pid: int, *, position: str = "SF", ovr: int = 70, age: int = 24) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality="Japan",
        position=position,
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
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team(sub_policy: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    rot = dict(d["rotation"])
    rot["sub_policy"] = sub_policy
    t.team_tactics = {**d, "rotation": rot}
    ensure_team_tactics_on_team(t)
    return t


def test_standard_modifier_is_zero():
    t = _team("standard")
    p = _player(1, ovr=90)
    assert get_sub_policy_sub_out_modifier(t, p, roster_rank=0) == 0.0


def test_starters_long_top_rank_gets_positive_modifier():
    t = _team("starters_long")
    assert get_sub_policy_sub_out_modifier(t, _player(1), roster_rank=0) == 1.0
    assert get_sub_policy_sub_out_modifier(t, _player(2), roster_rank=6) == 0.0


def test_bench_deep_top_rank_more_negative_than_standard():
    t_std = _team("standard")
    t_bench = _team("bench_deep")
    p = _player(1)
    assert get_sub_policy_sub_out_modifier(t_std, p, roster_rank=0) == 0.0
    assert get_sub_policy_sub_out_modifier(t_bench, p, roster_rank=0) == -1.0


def test_youth_dev_young_positive_veteran_negative():
    t = _team("youth_dev")
    young = _player(1, age=21)
    mid = _player(2, age=27)
    old = _player(3, age=33)
    assert get_sub_policy_sub_out_modifier(t, young, roster_rank=5) == 1.0
    assert get_sub_policy_sub_out_modifier(t, mid, roster_rank=5) == 0.0
    assert get_sub_policy_sub_out_modifier(t, old, roster_rank=5) == -1.0


def test_modifier_only_minus_one_zero_one():
    for pol in ("standard", "starters_long", "bench_deep", "youth_dev"):
        t = _team(pol)
        for rk in (0, 3, 7):
            for age in (20, 28, 35):
                v = get_sub_policy_sub_out_modifier(t, _player(1, age=age), roster_rank=rk)
                assert v in (-1.0, 0.0, 1.0)


def _build_rot_star_rank0(sub_pol: str) -> tuple[RotationSystem, Player]:
    t = _team(sub_pol)
    p101 = _player(101, position="PG", ovr=92)
    p102 = _player(102, position="SG", ovr=70)
    p103 = _player(103, position="SF", ovr=70)
    p104 = _player(104, position="PF", ovr=70)
    p105 = _player(105, position="C", ovr=70)
    p106 = _player(106, position="PG", ovr=70)
    p107 = _player(107, position="SG", ovr=70)
    p108 = _player(108, position="SF", ovr=70)
    p109 = _player(109, position="PF", ovr=70)
    p110 = _player(110, position="C", ovr=70)
    p111 = _player(111, position="PG", ovr=70)
    for p in (
        p101,
        p102,
        p103,
        p104,
        p105,
        p106,
        p107,
        p108,
        p109,
        p110,
        p111,
    ):
        t.add_player(p)
    starters = [p101, p102, p103, p104, p105]
    active = list(t.players)
    rot = RotationSystem(t, active, starters=starters)
    k = rot._player_key(p101)
    # 終盤: ベンチ0分強制が無効になり base min stint が 8（closing で min(10,8)）
    rot.last_sub_in_possession[k] = 148
    rot.lineup_entry_possession[k] = 148
    return rot, p101


def test_can_sub_out_bench_deep_allows_earlier_than_standard():
    """終盤・同じ last_in / stint で、bench_deep の rank0 だけが standard より 1 possession 早く OUT 可。"""
    r_std, star_std = _build_rot_star_rank0("standard")
    r_bd, star_bd = _build_rot_star_rank0("bench_deep")
    poss = 155
    assert r_std._can_sub_out(star_std, poss, 160) is False
    assert r_bd._can_sub_out(star_bd, poss, 160) is True


def test_can_sub_out_starters_long_stricter_than_standard_at_same_possession():
    """starters_long は rank0 の必要スタントが +1 され、同条件で standard より遅く OUT 可。"""
    r_std, star_std = _build_rot_star_rank0("standard")
    r_sl, star_sl = _build_rot_star_rank0("starters_long")
    poss = 156
    assert r_std._can_sub_out(star_std, poss, 160) is True
    assert r_sl._can_sub_out(star_sl, poss, 160) is False


def test_clutch_policy_unrelated_sub_policy_still_bounded():
    """clutch と独立。sub_policy のみの値域は {-1,0,1}。"""
    t = _team("bench_deep")
    d = get_default_team_tactics()
    t.team_tactics = {**d, "rotation": {**d["rotation"], "sub_policy": "bench_deep", "clutch_policy": "stars"}}
    ensure_team_tactics_on_team(t)
    v = get_sub_policy_sub_out_modifier(t, _player(1), roster_rank=0)
    assert v == -1.0
