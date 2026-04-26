"""win_now 系専用の target minutes 微補正（第2段階）テスト。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import (
    RotationSystem,
    _WIN_NOW_TARGET_DEEP_BENCH_BIAS_MINUTES,
    _WIN_NOW_TARGET_DEEP_BENCH_RANK_MIN,
    _WIN_NOW_TARGET_TOP_BIAS_MINUTES,
    _WIN_NOW_TARGET_TOP_RANK_MAX,
)
from basketball_sim.systems.team_tactics import (
    apply_rotation_preset_with_preset_meta,
    ensure_team_tactics_on_team,
    get_default_team_tactics,
)


def _player(pid: int, *, age: int, ovr: int, position: str) -> Player:
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


def _team(seed_id: int = 1) -> Team:
    t = Team(team_id=seed_id, name=f"T{seed_id}", league_level=1, team_training_focus="balanced")
    t.team_tactics = get_default_team_tactics()
    ensure_team_tactics_on_team(t)
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF"]
    ages = [28, 27, 26, 25, 24, 23, 22, 21, 20]
    ovrs = [80, 79, 78, 77, 76, 74, 72, 70, 68]
    ps = [
        _player(100 + i, age=ages[i], ovr=ovrs[i], position=positions[i])
        for i in range(9)
    ]
    for p in ps:
        t.add_player(p)
    t.set_starting_lineup_by_players(ps[:5])
    if hasattr(t, "set_sixth_man"):
        t.set_sixth_man(ps[5])
    if hasattr(t, "bench_order"):
        t.bench_order = [p.player_id for p in ps[6:]]
    return t


def _rotation(team: Team) -> RotationSystem:
    ps = list(team.players)
    return RotationSystem(team, ps, starters=ps[:5])


def _rank_and_target_by_pid(rot: RotationSystem) -> tuple[dict[int, int], dict[int, float]]:
    rank_map = rot._get_rank_map()
    target_map = rot._build_target_minutes_map()
    rank_by_pid: dict[int, int] = {}
    target_by_pid: dict[int, float] = {}
    for p in rot.active_players:
        key = rot._player_key(p)
        rank_by_pid[int(p.player_id)] = int(rank_map[key])
        target_by_pid[int(p.player_id)] = float(target_map[key])
    return rank_by_pid, target_by_pid


def test_starters_long_only_bias_is_small_and_directional():
    """
    usage_policy は balanced のまま、sub_policy=starters_long だけで
    win_now 系 target 微補正（上位 +0.6 / 深い控え -0.4）が入ることを確認。
    """
    tb = _team(1)
    ts = _team(2)
    # 両方とも Team.usage_policy は balanced のまま
    rb = _rotation(tb)
    # sub_policy を starters_long へ
    raw = dict(ts.team_tactics or {})
    rot = dict(raw.get("rotation") or {})
    rot["sub_policy"] = "starters_long"
    raw["rotation"] = rot
    ts.team_tactics = raw
    ensure_team_tactics_on_team(ts)
    rs = _rotation(ts)

    ranks_b, tgt_b = _rank_and_target_by_pid(rb)
    ranks_s, tgt_s = _rank_and_target_by_pid(rs)
    assert ranks_b == ranks_s

    for pid, rk in ranks_b.items():
        diff = tgt_s[pid] - tgt_b[pid]
        if rk <= _WIN_NOW_TARGET_TOP_RANK_MAX:
            assert 0.0 < diff <= 1.0
            assert abs(diff - _WIN_NOW_TARGET_TOP_BIAS_MINUTES) < 1e-6
        elif rk >= _WIN_NOW_TARGET_DEEP_BENCH_RANK_MIN:
            assert -1.0 <= diff < 0.0
            assert abs(diff - _WIN_NOW_TARGET_DEEP_BENCH_BIAS_MINUTES) < 1e-6
        else:
            assert abs(diff) < 1e-6


def test_win_now_v1_top_band_higher_and_deep_bench_lower_than_balanced():
    tb = _team(3)
    tw = _team(4)
    apply_rotation_preset_with_preset_meta(tb, "balanced_v1")
    apply_rotation_preset_with_preset_meta(tw, "win_now_v1")
    rb = _rotation(tb)
    rw = _rotation(tw)
    ranks_b, tgt_b = _rank_and_target_by_pid(rb)
    ranks_w, tgt_w = _rank_and_target_by_pid(rw)
    assert ranks_b == ranks_w

    top = [pid for pid, rk in ranks_b.items() if rk <= _WIN_NOW_TARGET_TOP_RANK_MAX]
    deep = [pid for pid, rk in ranks_b.items() if rk >= _WIN_NOW_TARGET_DEEP_BENCH_RANK_MIN]
    assert top and deep
    top_diff = sum((tgt_w[pid] - tgt_b[pid]) for pid in top) / len(top)
    deep_diff = sum((tgt_w[pid] - tgt_b[pid]) for pid in deep) / len(deep)
    assert top_diff > 0.0
    assert deep_diff < 0.0


def test_development_v1_does_not_apply_win_now_specific_bias_helper():
    td = _team(5)
    apply_rotation_preset_with_preset_meta(td, "development_v1")
    rd = _rotation(td)
    # development では win_now 専用 helper は常に 0
    assert rd._is_win_now_target_bias_active() is False
    assert rd._get_win_now_target_bias_minutes(0) == 0.0
    assert rd._get_win_now_target_bias_minutes(8) == 0.0


def test_build_target_map_does_not_mutate_lineup_fields():
    tw = _team(6)
    before_start = list(getattr(tw, "starting_lineup", []) or [])
    before_sixth = getattr(tw, "sixth_man_id", None)
    before_bench = list(getattr(tw, "bench_order", []) or [])
    apply_rotation_preset_with_preset_meta(tw, "win_now_v1")
    r = _rotation(tw)
    _ = r._build_target_minutes_map()
    assert list(getattr(tw, "starting_lineup", []) or []) == before_start
    assert getattr(tw, "sixth_man_id", None) == before_sixth
    assert list(getattr(tw, "bench_order", []) or []) == before_bench

