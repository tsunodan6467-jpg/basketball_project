"""target_minutes overlay（20% blend）と交代候補方向の固定テスト。"""

from __future__ import annotations

from typing import Dict, List

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team, get_default_team_tactics


def _player(pid: int, *, position: str, ovr: int = 72, stamina: int = 70) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=25,
        nationality="Japan",
        position=position,
        height_cm=195.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=stamina,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=3_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team(n: int = 12, *, team_id: int = 1) -> Team:
    t = Team(team_id=team_id, name=f"T{team_id}", league_level=1, team_training_focus="balanced")
    t.team_tactics = get_default_team_tactics()
    ensure_team_tactics_on_team(t)
    positions = ["PG", "SG", "SF", "PF", "C"]
    for i in range(n):
        t.add_player(_player(100 + i, position=positions[i % len(positions)]))
    players = list(t.players)
    t.set_starting_lineup_by_players(players[:5])
    if hasattr(t, "set_sixth_man"):
        t.set_sixth_man(players[5])
    return t


def _rotation(team: Team) -> RotationSystem:
    active = [p for p in team.players if not p.is_injured() and not p.is_retired]
    starters = active[:5]
    return RotationSystem(team, active, starters=starters)


def _pid_to_key(rot: RotationSystem) -> Dict[int, int]:
    m: Dict[int, int] = {}
    for p in rot.active_players:
        m[int(p.player_id)] = rot._player_key(p)
    return m


def test_target_minutes_overlay_blend_formula_and_direction():
    """
    _build_target_minutes_map の overlay は常に 20% blend。
    高め overlay は上方向、低め overlay は下方向へ寄ることを固定化する。
    """
    t = _team(12, team_id=11)
    r = _rotation(t)
    pid_map = _pid_to_key(r)
    low_pid = int(r.active_players[0].player_id)
    high_pid = int(r.active_players[1].player_id)
    low_key = pid_map[low_pid]
    high_key = pid_map[high_pid]

    r._tactics_target_minutes = {}
    base_map = r._build_target_minutes_map()
    low_base = float(base_map[low_key])
    high_base = float(base_map[high_key])

    # 保存側 0/40 相当を与えても、試合用 target は clamp(4..38) 後に 20% blend。
    r._tactics_target_minutes = {low_pid: 0.0, high_pid: 40.0}
    with_overlay = r._build_target_minutes_map()
    low_overlay = float(with_overlay[low_key])
    high_overlay = float(with_overlay[high_key])

    low_o = r._clamp_target_minutes(0.0)
    high_o = r._clamp_target_minutes(40.0)
    low_expected = r._clamp_target_minutes(low_base + (low_o - low_base) * 0.20)
    high_expected = r._clamp_target_minutes(high_base + (high_o - high_base) * 0.20)

    assert low_overlay == pytest.approx(low_expected, abs=1e-9)
    assert high_overlay == pytest.approx(high_expected, abs=1e-9)
    assert low_overlay < low_base
    assert high_overlay > high_base
    assert all(4.0 <= float(v) <= 38.0 for v in with_overlay.values())


def test_target_minutes_overlay_empty_is_same_as_base():
    t = _team(12, team_id=12)
    r = _rotation(t)
    r._tactics_target_minutes = {}
    m0 = r._build_target_minutes_map()
    r._tactics_target_minutes = {}
    m1 = r._build_target_minutes_map()
    assert m0 == m1


def test_in_candidates_prefer_player_with_larger_target_shortage():
    """
    同条件（同 stamina/ovr/played）なら shortage の大きい方が IN 候補で有利。
    """
    t = _team(12, team_id=13)
    r = _rotation(t)
    p_a = r.bench[0]
    p_b = r.bench[1]

    key_a = r._player_key(p_a)
    key_b = r._player_key(p_b)
    for p in r.bench:
        r.player_minutes[r._player_key(p)] = 5.0

    target_map: Dict[int, float] = {r._player_key(p): 20.0 for p in r.active_players}
    target_map[key_a] = 30.0  # shortage 25
    target_map[key_b] = 10.0  # shortage 5

    ins: List[Player] = r._get_in_candidates(possession=40, total_possessions=160, target_map=target_map)
    assert p_a in ins and p_b in ins
    assert ins.index(p_a) < ins.index(p_b)


def test_out_candidates_prefer_player_more_over_target():
    """
    played が同じなら、target が低い選手ほど over_target が大きく OUT 候補で上位になりやすい。
    """
    t = _team(12, team_id=14)
    r = _rotation(t)
    a = r.current_lineup[0]
    b = r.current_lineup[1]
    key_a = r._player_key(a)
    key_b = r._player_key(b)

    for p in r.current_lineup:
        r.player_minutes[r._player_key(p)] = 20.0

    target_map: Dict[int, float] = {r._player_key(p): 20.0 for p in r.active_players}
    target_map[key_a] = 10.0  # over_target 10
    target_map[key_b] = 30.0  # over_target -10

    outs: List[Player] = r._get_out_candidates(possession=50, total_possessions=160, target_map=target_map)
    assert a in outs and b in outs
    assert outs.index(a) < outs.index(b)

