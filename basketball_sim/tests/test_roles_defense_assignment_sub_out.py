"""roles.defense_assignment → get_roles_defense_assignment_sub_out_modifier / _can_sub_out 実効 min stint。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_roles_defense_assignment_sub_out_modifier,
    get_sub_policy_sub_out_modifier,
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
    )
    base.update(kwargs)
    return Player(**base)


def _full_role_row(da: str) -> dict:
    return {
        "defense_assignment": da,
        "shot_priority": "standard",
        "offense_involvement": "standard",
        "playmaking_role": "secondary",
        "clutch_priority": "standard",
        "main_role": "none",
    }


def _team_with_da(da: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d = get_default_team_tactics()
    d["roles"] = {"1": _full_role_row(da)}
    t.team_tactics = d
    ensure_team_tactics_on_team(t)
    return t


def test_defense_assignment_standard_is_zero():
    t = _team_with_da("standard")
    p = _player(1)
    assert get_roles_defense_assignment_sub_out_modifier(t, p) == 0


def test_stopper_plus_one_light_minus_one():
    t_st = _team_with_da("stopper")
    t_lt = _team_with_da("light")
    p = _player(1)
    assert get_roles_defense_assignment_sub_out_modifier(t_st, p) == 1
    assert get_roles_defense_assignment_sub_out_modifier(t_lt, p) == -1


def test_clamp_sub_with_defense_stays_in_neg_one_to_plus_one():
    s1, s2 = 1, 1
    assert max(-1, min(1, s1 + s2)) == 1
    m1, m2 = -1, -1
    assert max(-1, min(1, m1 + m2)) == -1
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d0 = get_default_team_tactics()
    t.team_tactics = {
        **d0,
        "rotation": {**d0["rotation"], "sub_policy": "starters_long"},
        "roles": {"1": _full_role_row("stopper")},
    }
    ensure_team_tactics_on_team(t)
    p = _player(1)
    s = int(get_sub_policy_sub_out_modifier(t, p, roster_rank=0))
    d = get_roles_defense_assignment_sub_out_modifier(t, p)
    assert s == 1 and d == 1
    assert max(-1, min(1, s + d)) == 1


def test_clamp_mixed_cancels_to_zero():
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d0 = get_default_team_tactics()
    t.team_tactics = {
        **d0,
        "rotation": {**d0["rotation"], "sub_policy": "bench_deep"},
        "roles": {"1": _full_role_row("stopper")},
    }
    ensure_team_tactics_on_team(t)
    p = _player(1)
    s = int(get_sub_policy_sub_out_modifier(t, p, roster_rank=0))
    d2 = get_roles_defense_assignment_sub_out_modifier(t, p)
    assert s == -1 and d2 == 1
    assert max(-1, min(1, s + d2)) == 0


def test_missing_roles_row_zero_like_standard():
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.team_tactics = {**get_default_team_tactics(), "roles": {}}
    ensure_team_tactics_on_team(t)
    assert get_roles_defense_assignment_sub_out_modifier(t, _player(101)) == 0


def _build_rot_p101(
    sub_pol: str, da: str
) -> tuple[RotationSystem, Player, Team]:
    """p101=rank0。終盤 closing 相当で min stint 8（test_sub_policy 系と同型）。"""
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    d0 = get_default_team_tactics()
    t.team_tactics = {
        **d0,
        "rotation": {**d0["rotation"], "sub_policy": sub_pol},
        "roles": {"101": _full_role_row(da)},
    }
    ensure_team_tactics_on_team(t)
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
    for p in (p101, p102, p103, p104, p105, p106, p107, p108, p109, p110, p111):
        t.add_player(p)
    starters = [p101, p102, p103, p104, p105]
    active = list(t.players)
    rot = RotationSystem(t, active, starters=starters)
    k = rot._player_key(p101)
    rot.last_sub_in_possession[k] = 148
    rot.lineup_entry_possession[k] = 148
    return rot, p101, t


def test_can_sub_out_light_earlier_than_stopper_same_sub():
    """同 rank・同 sub_policy ・同 last_in: light のほうが stopper より早く OUT 可にできる。"""
    r_l, star_l, _t = _build_rot_p101("standard", "light")
    r_s, star_s, _ = _build_rot_p101("standard", "stopper")
    poss = 155
    tot = 160
    # light: adj -1 → eff 7, stopper: +1 → eff 9。last から 7 PO 時点で light のみ可
    assert r_l._can_sub_out(star_l, poss, tot) is True
    assert r_s._can_sub_out(star_s, poss, tot) is False


def test_sub_policy_still_runs_bench_deep_vs_double_negative_clamp():
    """
    bench_deep: s=-1 + light d=-1 → adj=-1（-2 は clamp）
    既存: standard rank0 では 155 でまだ不可、bench_deep は 155 で可
    今回: bench_deep + light は二重マイナスが抑えられ、従来 bench_deep 単独と同じ帯の振る舞いに近い
    """
    r_bd, star, _t = _build_rot_p101("bench_deep", "light")
    poss, tot = 155, 160
    r_std, star2, _ = _build_rot_p101("standard", "standard")
    r_bdl, star3, _ = r_bd, star, _t
    assert r_std._can_sub_out(star2, poss, tot) is False
    # bench_deep: s=-1, light d=-1, adj=clamp(-2,-1,1)=-1 → 従来と同じ eff
    assert r_bdl._can_sub_out(star3, poss, tot) is True
