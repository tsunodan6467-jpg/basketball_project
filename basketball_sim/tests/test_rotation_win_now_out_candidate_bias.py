"""win_now 系の OUT 候補スコア微小補正（_get_win_now_out_candidate_bias）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import (
    RotationSystem,
    _WIN_NOW_OUT_CANDIDATE_CORE_BIAS,
    _WIN_NOW_OUT_CANDIDATE_MIN_TARGET,
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


def _team_with_lineup(seed_id: int = 1) -> Team:
    t = Team(team_id=seed_id, name=f"T{seed_id}", league_level=1, team_training_focus="balanced")
    t.team_tactics = get_default_team_tactics()
    ensure_team_tactics_on_team(t)
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF"]
    ages = [29, 28, 27, 26, 25, 24, 23, 22, 21]
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


def _rot(team: Team) -> RotationSystem:
    ps = list(team.players)
    return RotationSystem(team, ps, starters=ps[:5])


def test_win_now_bias_applies_only_core_target_band():
    t = _team_with_lineup(1)
    apply_rotation_preset_with_preset_meta(t, "win_now_v1")
    r = _rot(t)
    assert r._is_win_now_target_bias_active() is True
    assert r._get_win_now_out_candidate_bias(_WIN_NOW_OUT_CANDIDATE_MIN_TARGET) == _WIN_NOW_OUT_CANDIDATE_CORE_BIAS
    assert r._get_win_now_out_candidate_bias(_WIN_NOW_OUT_CANDIDATE_MIN_TARGET - 0.1) == 0.0


def test_balanced_and_development_are_not_targets():
    tb = _team_with_lineup(2)
    apply_rotation_preset_with_preset_meta(tb, "balanced_v1")
    rb = _rot(tb)
    assert rb._is_win_now_target_bias_active() is False
    assert rb._get_win_now_out_candidate_bias(30.0) == 0.0

    td = _team_with_lineup(3)
    apply_rotation_preset_with_preset_meta(td, "development_v1")
    rd = _rot(td)
    assert rd._is_win_now_target_bias_active() is False
    assert rd._get_win_now_out_candidate_bias(30.0) == 0.0


def test_out_candidate_score_directional_small_for_core_target():
    """
    同一選手の基礎 OUT スコアに対し、win_now の高 target だけ小さく減算されることを確認。
    """
    tb = _team_with_lineup(4)
    tw = _team_with_lineup(5)
    apply_rotation_preset_with_preset_meta(tb, "balanced_v1")
    apply_rotation_preset_with_preset_meta(tw, "win_now_v1")
    rb = _rot(tb)
    rw = _rot(tw)

    # helper 単体で方向と幅を確認（_get_out_candidates 本体に依存しない軽量確認）
    diff_core = rw._get_win_now_out_candidate_bias(22.0) - rb._get_win_now_out_candidate_bias(22.0)
    assert -1.0 <= diff_core < 0.0
    assert abs(diff_core - _WIN_NOW_OUT_CANDIDATE_CORE_BIAS) < 1e-6

    diff_low = rw._get_win_now_out_candidate_bias(16.0) - rb._get_win_now_out_candidate_bias(16.0)
    assert abs(diff_low) < 1e-6


def test_no_mutation_on_lineup_fields_during_out_candidate_eval():
    t = _team_with_lineup(6)
    apply_rotation_preset_with_preset_meta(t, "win_now_v1")
    before_start = list(getattr(t, "starting_lineup", []) or [])
    before_sixth = getattr(t, "sixth_man_id", None)
    before_bench = list(getattr(t, "bench_order", []) or [])
    r = _rot(t)
    target_map = r._build_target_minutes_map()
    _ = r._get_out_candidates(40, 160, target_map)
    assert list(getattr(t, "starting_lineup", []) or []) == before_start
    assert getattr(t, "sixth_man_id", None) == before_sixth
    assert list(getattr(t, "bench_order", []) or []) == before_bench

