"""team_tactics.team_strategy.offense_style → Match._get_shot_mix（極小オーバーレイ、第2弾）。"""

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_offense_style_shot_mix_deltas,
)


def _player(pid: int, position: str) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
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


def _team(tid: int, name: str) -> Team:
    t = Team(team_id=tid, name=name, league_level=1, team_training_focus="balanced")
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        t.add_player(_player(tid * 100 + i + 1, pos))
    return t


def _with_offense_style(t: Team, offense_style: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {"offense_tempo": "standard", "offense_style": offense_style},
    }
    ensure_team_tactics_on_team(t)
    return t


def _shot_mix(m: Match):
    return m._get_shot_mix(
        m.home_team, m.away_team, m.home_starters, m.away_starters
    )


def test_get_shot_mix_balanced_strategy_inside_offense_style_small_change():
    """Team.strategy=balanced かつ offense_style=inside で _get_shot_mix に小さな差が乗る。"""
    away = _with_offense_style(_team(2, "Away"), "balanced")
    home_in = _with_offense_style(_team(1, "H1"), "inside")
    home_def = _with_offense_style(_team(1, "H0"), "balanced")
    for h in (home_in, home_def):
        h.strategy = "balanced"
    m_in = Match(home_team=home_in, away_team=away)
    m_def = Match(home_team=home_def, away_team=away)
    a, b, c = _shot_mix(m_in)
    a0, b0, c0 = _shot_mix(m_def)
    assert (a, b, c) != (a0, b0, c0)
    # T1: inside 満額は three_cutoff 方向がマイナス寄り
    assert a < a0


def test_get_offense_style_helper_same_direction_dampened_smaller_than_balanced_full():
    """同方向（戦略=inside, offense_style=inside）は T2 減衰し、満額（balanced+inside）より小さい。"""
    t_full = _with_offense_style(_team(1, "TFull"), "inside")
    t_same = _with_offense_style(_team(2, "TSame"), "inside")
    full = get_offense_style_shot_mix_deltas(t_full, "balanced")
    damp = get_offense_style_shot_mix_deltas(t_same, "inside")
    assert all(abs(damp[i]) < abs(full[i]) for i in range(3))
    assert all(damp[i] * full[i] > 0.0 for i in range(3) if full[i] != 0.0)
    k = 0.3
    for i in range(3):
        assert abs(damp[i] - full[i] * k) < 1e-9


def test_get_shot_mix_conflict_inside_vs_three_no_extra_vs_balanced_offense_style():
    """衝突（戦略=inside, offense_style=three_point）時はオーバーレイ0 → balanced offense と同味付けの shot_mix。"""
    away = _with_offense_style(_team(2, "Away"), "balanced")
    home_b = _with_offense_style(_team(1, "Hb"), "balanced")
    home_c = _with_offense_style(_team(1, "Hc"), "three_point")
    for h in (home_b, home_c):
        h.strategy = "inside"
    m_b = Match(home_team=home_b, away_team=away)
    m_c = Match(home_team=home_c, away_team=away)
    assert _shot_mix(m_b) == _shot_mix(m_c)
    assert get_offense_style_shot_mix_deltas(home_c, "inside") == (0.0, 0.0, 0.0)


def test_drive_balanced_nonzero_three_down_two_up():
    """T1+T4: strategy balanced + offense_style=drive、3↓2↑方向で非ゼロ。"""
    t = _with_offense_style(_team(10, "D0"), "drive")
    d3, d2, dsr = get_offense_style_shot_mix_deltas(t, "balanced")
    assert d3 < 0.0
    assert d2 > 0.0
    assert dsr >= 0.0


def test_drive_inside_strategy_damped():
    """T2: 戦略 inside + drive は同方向 → 0.3 減衰で満額より小さい。"""
    t = _with_offense_style(_team(11, "D1"), "drive")
    full = get_offense_style_shot_mix_deltas(t, "balanced")
    damp = get_offense_style_shot_mix_deltas(t, "inside")
    assert all(abs(damp[i]) < abs(full[i]) for i in range(3) if full[i] != 0.0)
    for i in range(3):
        assert abs(damp[i] - full[i] * 0.3) < 1e-9


def test_drive_three_or_run_and_gun_zero():
    """T3: three_point / run_and_gun 戦略は drive オーバーレイ 0。"""
    t = _with_offense_style(_team(12, "D2"), "drive")
    assert get_offense_style_shot_mix_deltas(t, "three_point") == (0.0, 0.0, 0.0)
    assert get_offense_style_shot_mix_deltas(t, "run_and_gun") == (0.0, 0.0, 0.0)


def test_drive_t1_weaker_than_inside():
    """T1: balanced 満額の drive ベクタは inside より各成分の絶対値が小さい。"""
    t_d = _with_offense_style(_team(13, "Wd"), "drive")
    t_i = _with_offense_style(_team(13, "Wi"), "inside")
    vd = get_offense_style_shot_mix_deltas(t_d, "balanced")
    vi = get_offense_style_shot_mix_deltas(t_i, "balanced")
    for i in range(3):
        assert abs(vd[i]) < abs(vi[i]) + 1e-9
