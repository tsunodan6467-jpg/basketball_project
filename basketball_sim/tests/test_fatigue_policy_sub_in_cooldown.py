"""rotation.fatigue_policy → get_fatigue_policy_sub_in_cooldown_adjustment / RotationSystem._can_sub_in（v1）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_fatigue_policy_sub_in_cooldown_adjustment,
)


def _player(pid: int, position: str, ovr: int = 70, fatigue: int = 0) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
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
        fatigue=fatigue,
    )


def _team(fatigue_pol: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    rot = dict(d["rotation"])
    rot["fatigue_policy"] = fatigue_pol
    t.team_tactics = {**d, "rotation": rot}
    ensure_team_tactics_on_team(t)
    return t


def test_standard_adjustment_always_zero():
    t = _team("standard")
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 0) == 0
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 90) == 0


def test_strict_high_fatigue_plus_one_low_zero():
    t = _team("strict")
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 55) == 1
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 49) == 0


def test_push_adjustment_is_minus_one():
    t = _team("push")
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 0) == -1
    assert get_fatigue_policy_sub_in_cooldown_adjustment(t, 95) == -1


def test_adjustment_only_minus_one_zero_one():
    t_std = _team("standard")
    t_st = _team("strict")
    t_pu = _team("push")
    for f in (0, 25, 50, 75, 100):
        for tt in (t_std, t_st, t_pu):
            v = get_fatigue_policy_sub_in_cooldown_adjustment(tt, f)
            assert v in (-1, 0, 1)


def _nine_player_rot(fatigue_pol: str, bench_fatigue: int) -> tuple[RotationSystem, Player]:
    """9人ロスターでベース IN クールダウンが 8 possession（>0.1 分出場済みで 6 化を避ける）。"""
    t = _team(fatigue_pol)
    ps = [_player(100 + i, ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF"][i], fatigue=bench_fatigue if i == 8 else 0)
          for i in range(9)]
    for p in ps:
        t.add_player(p)
    starters = ps[:5]
    bench_p = ps[8]
    bench_p.fatigue = bench_fatigue
    rot = RotationSystem(t, ps, starters=starters)
    k = rot._player_key(bench_p)
    rot.last_sub_out_possession[k] = 0
    rot._add_minutes(bench_p, 1.0)
    return rot, bench_p


def test_can_sub_in_order_strict_slower_standard_push_faster():
    """同条件で strict < standard < push の順に再投入が許可されやすい（高疲労・base cd 8）。"""
    r_st, b_st = _nine_player_rot("strict", 60)
    r_std, b_std = _nine_player_rot("standard", 60)
    r_pu, b_pu = _nine_player_rot("push", 60)
    tot = 160
    poss = 7
    assert r_st._can_sub_in(b_st, poss, tot) is False
    assert r_std._can_sub_in(b_std, poss, tot) is False
    assert r_pu._can_sub_in(b_pu, poss, tot) is True

    assert r_std._can_sub_in(b_std, 8, tot) is True
    assert r_st._can_sub_in(b_st, 8, tot) is False
    assert r_st._can_sub_in(b_st, 9, tot) is True
