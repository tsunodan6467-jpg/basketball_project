"""team_tactics.offense_creation → Match._get_assist_chance（第4〜6弾: ball_move / iso / pick_and_roll）。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_offense_creation_assist_delta,
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


def _with_offense_creation(t: Team, offense_creation: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "offense_creation": offense_creation,
            "defense_style": "balanced",
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_ball_move_balanced_strategy_full_t1():
    """T4: strategy balanced かつ ball_move → 満額 +0.003。"""
    t = _with_offense_creation(_team(1, "A"), "ball_move")
    assert get_offense_creation_assist_delta(t, "balanced") == 0.003


def test_ball_move_three_or_inside_dampened_smaller_than_balanced():
    """T2: three_point / inside は既に assist 上げ方向 → 0.3 倍で小さい。"""
    t = _with_offense_creation(_team(2, "B"), "ball_move")
    b = get_offense_creation_assist_delta(t, "balanced")
    t3 = get_offense_creation_assist_delta(t, "three_point")
    ins = get_offense_creation_assist_delta(t, "inside")
    assert t3 == 0.003 * 0.3
    assert ins == 0.003 * 0.3
    assert abs(t3) < abs(b)
    assert abs(ins) < abs(b)


def test_post_still_zero():
    """post → 0 は意図的（get_offense_creation_assist_delta の fallthrough 注記と同趣旨）。"""
    t = _with_offense_creation(_team(3, "P"), "post")
    assert get_offense_creation_assist_delta(t, "balanced") == 0.0


def test_pick_and_roll_balanced_positive_smaller_than_ball_move():
    """第6弾: balanced + pick_and_roll は正で、ball_move より小さい T1。"""
    t = _with_offense_creation(_team(6, "Pr"), "pick_and_roll")
    p = get_offense_creation_assist_delta(t, "balanced")
    t_bm = _with_offense_creation(_team(6, "Bm"), "ball_move")
    b = get_offense_creation_assist_delta(t_bm, "balanced")
    assert p == 0.0014
    assert 0 < p < b
    assert b == 0.003


def test_pick_and_roll_three_or_inside_dampened():
    """第6弾 T2: three_point / inside は ball_move と同系 0.3 倍。"""
    t = _with_offense_creation(_team(7, "P7"), "pick_and_roll")
    full = get_offense_creation_assist_delta(t, "balanced")
    t3 = get_offense_creation_assist_delta(t, "three_point")
    ins = get_offense_creation_assist_delta(t, "inside")
    assert t3 == pytest.approx(0.0014 * 0.3, abs=1e-9)
    assert ins == pytest.approx(0.0014 * 0.3, abs=1e-9)
    assert t3 < full
    assert ins < full


def test_ordering_ball_move_pick_and_roll_iso():
    """符号・大きさ: ball_move > pick_and_roll > 0 > iso（balanced 満額）。"""
    tb = _with_offense_creation(_team(9, "B9"), "ball_move")
    tp = _with_offense_creation(_team(9, "P9"), "pick_and_roll")
    ti = _with_offense_creation(_team(9, "I9"), "iso")
    b = get_offense_creation_assist_delta(tb, "balanced")
    p = get_offense_creation_assist_delta(tp, "balanced")
    i = get_offense_creation_assist_delta(ti, "balanced")
    assert b > p > 0 > i


def test_iso_balanced_negative_opposite_to_ball_move():
    """T1/T4: balanced + iso → 満額 -0.002。ball_move +0.003 とは逆方向。"""
    t_iso = _with_offense_creation(_team(4, "I"), "iso")
    t_bm = _with_offense_creation(_team(4, "M"), "ball_move")
    di = get_offense_creation_assist_delta(t_iso, "balanced")
    db = get_offense_creation_assist_delta(t_bm, "balanced")
    assert di == -0.002
    assert db == 0.003
    assert di * db < 0


def test_iso_run_and_gun_or_defense_damped():
    """T2b: run_and_gun / defense では既に assist 下げ方向 → 0.3 倍で小さい負。"""
    t = _with_offense_creation(_team(5, "X"), "iso")
    d_rg = get_offense_creation_assist_delta(t, "run_and_gun")
    d_def = get_offense_creation_assist_delta(t, "defense")
    assert d_rg == -0.002 * 0.3
    assert d_def == -0.002 * 0.3
    assert abs(d_rg) < 0.002


def test_get_assist_chance_ball_move_adds_small_delta_vs_post():
    """同一ラインワップで offense_creation だけ切替え、差はオーバーレイ分（Player 二重体の混在を避ける）。"""
    home = _with_offense_creation(_team(1, "H"), "ball_move")
    home.strategy = "balanced"
    away = _with_offense_creation(_team(2, "A"), "balanced")
    m = Match(home_team=home, away_team=away)
    shooter = m.home_starters[0]
    a = m._get_assist_chance(home, m.home_starters, shooter, "two", False)
    home.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "offense_creation": "post",
            "defense_style": "balanced",
        },
    }
    ensure_team_tactics_on_team(home)
    b = m._get_assist_chance(home, m.home_starters, shooter, "two", False)
    assert a - b == pytest.approx(0.003, abs=1e-6)
