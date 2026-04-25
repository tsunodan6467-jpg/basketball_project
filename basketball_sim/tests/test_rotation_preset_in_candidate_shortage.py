"""ローテプリセット → IN 候補の shortage 項の小さな係数補正（RotationSystem._get_rotation_preset_shortage_multiplier）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import (
    RotationSystem,
    _DEV_YOUTH_MAX_AGE,
    _ROTATION_PRESET_SHORTAGE_MULT_DEV,
    _ROTATION_PRESET_SHORTAGE_MULT_WIN_NOW,
    _WIN_NOW_SHORTAGE_MIN_TARGET,
)
from basketball_sim.systems.team_tactics import (
    apply_rotation_preset_with_preset_meta,
    ensure_team_tactics_on_team,
    get_default_team_tactics,
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


def _team_with_lineup() -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.team_tactics = get_default_team_tactics()
    ensure_team_tactics_on_team(t)
    ps = [_player(100 + i, ovr=78 - i) for i in range(9)]
    for p in ps:
        t.add_player(p)
    t.set_starting_lineup_by_players(ps[:5])
    if hasattr(t, "set_sixth_man"):
        t.set_sixth_man(ps[5])
    return t


def _rs(t: Team) -> RotationSystem:
    ps = list(t.players)
    return RotationSystem(t, ps, starters=ps[:5])


def test_balanced_shortage_mult_is_one():
    t = _team_with_lineup()
    apply_rotation_preset_with_preset_meta(t, "balanced_v1")
    r = _rs(t)
    p = t.players[5]
    assert r._get_rotation_preset_shortage_multiplier(p, 25.0) == 1.0
    assert r._get_rotation_preset_shortage_multiplier(p, 16.0) == 1.0


def test_win_now_boosts_only_high_target():
    t = _team_with_lineup()
    before_sl = list(t.starting_lineup)
    sm = getattr(t, "sixth_man_id", None)
    bo = (
        list(t.bench_order) if hasattr(t, "bench_order") and t.bench_order is not None else None
    )
    apply_rotation_preset_with_preset_meta(t, "win_now_v1")
    assert list(t.starting_lineup) == before_sl
    if bo is not None and hasattr(t, "bench_order"):
        assert list(t.bench_order) == list(bo)
    if sm is not None and hasattr(t, "sixth_man_id"):
        assert getattr(t, "sixth_man_id", None) == sm

    r = _rs(t)
    p = t.players[5]
    assert t.usage_policy == "win_now"
    assert r._get_rotation_preset_shortage_multiplier(p, _WIN_NOW_SHORTAGE_MIN_TARGET) == _ROTATION_PRESET_SHORTAGE_MULT_WIN_NOW
    assert r._get_rotation_preset_shortage_multiplier(p, _WIN_NOW_SHORTAGE_MIN_TARGET - 0.1) == 1.0


def test_development_youth_only():
    t = _team_with_lineup()
    apply_rotation_preset_with_preset_meta(t, "development_v1")
    r = _rs(t)
    assert t.usage_policy == "development"
    y = _player(300, age=_DEV_YOUTH_MAX_AGE)
    o = _player(301, age=_DEV_YOUTH_MAX_AGE + 3)
    assert r._get_rotation_preset_shortage_multiplier(y, 10.0) == _ROTATION_PRESET_SHORTAGE_MULT_DEV
    assert r._get_rotation_preset_shortage_multiplier(o, 10.0) == 1.0


def test_in_candidates_shortage_term_larger_for_win_now_high_target():
    """同一生成手順のロスターで、win_now + 高 target の shortage 項が balanced より大きい。"""
    t0 = _team_with_lineup()
    apply_rotation_preset_with_preset_meta(t0, "balanced_v1")
    t1 = _team_with_lineup()
    apply_rotation_preset_with_preset_meta(t1, "win_now_v1")

    r0 = _rs(t0)
    r1 = _rs(t1)
    p0 = t0.players[5]
    p1 = t1.players[5]
    assert p0.player_id == p1.player_id
    target = 24.0
    played = 0.0
    shortage = max(0.0, target - played)
    s0 = shortage * r0._get_rotation_preset_shortage_multiplier(p0, target)
    s1 = shortage * r1._get_rotation_preset_shortage_multiplier(p1, target)
    assert s0 < s1
    assert s1 == shortage * _ROTATION_PRESET_SHORTAGE_MULT_WIN_NOW
