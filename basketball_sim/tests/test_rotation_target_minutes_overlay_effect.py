"""target_minutes overlay（小差分0.20 / 大差分0.30）と交代候補方向の固定テスト。"""

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


def _simulate_rotation_minutes(team: Team, total_possessions: int = 160) -> Dict[int, float]:
    """
    RotationSystem を試合1本分相当進め、選手IDごとの出場時間を返す。
    Match 本体は使わないが、試合中ローテ更新と同じ get_lineup 経路を通す。
    """
    rot = _rotation(team)
    lineup = rot.get_current_lineup()
    poss_per_q = max(1, total_possessions // 4)
    for pos in range(total_possessions):
        quarter = min(4, (pos // poss_per_q) + 1)
        pos_in_q = pos % poss_per_q
        lineup = rot.get_lineup(
            current_lineup=lineup,
            possession=pos,
            total_possessions=total_possessions,
            quarter=quarter,
            possession_in_quarter=pos_in_q,
            possessions_per_quarter=poss_per_q,
            score_diff=0,
        )
    rot._update_play_time_until(total_possessions)
    out: Dict[int, float] = {}
    for p in rot.active_players:
        out[int(p.player_id)] = float(rot.player_minutes.get(rot._player_key(p), 0.0))
    return out


def _simulate_rotation_minutes_from_midgame(
    team: Team,
    *,
    start_possession: int = 80,
    total_possessions: int = 160,
    starter_minutes: float = 20.0,
    bench_minutes: float = 10.0,
) -> Dict[int, float]:
    """
    同一の中間状態（先発20分/ベンチ10分）を与えて後半だけ回す。
    target_minutes による出場時間差を安定して比較するための補助。
    """
    rot = _rotation(team)
    lineup = rot.get_current_lineup()
    lineup_keys = {rot._player_key(p) for p in lineup}
    for p in rot.active_players:
        key = rot._player_key(p)
        rot.player_minutes[key] = starter_minutes if key in lineup_keys else bench_minutes
        rot.last_sub_in_possession[key] = -999
        rot.lineup_entry_possession[key] = 0
    rot.last_processed_possession = start_possession

    poss_per_q = max(1, total_possessions // 4)
    for pos in range(start_possession, total_possessions):
        quarter = min(4, (pos // poss_per_q) + 1)
        pos_in_q = pos % poss_per_q
        lineup = rot.get_lineup(
            current_lineup=lineup,
            possession=pos,
            total_possessions=total_possessions,
            quarter=quarter,
            possession_in_quarter=pos_in_q,
            possessions_per_quarter=poss_per_q,
            score_diff=0,
        )
    rot._update_play_time_until(total_possessions)
    out: Dict[int, float] = {}
    for p in rot.active_players:
        out[int(p.player_id)] = float(rot.player_minutes.get(rot._player_key(p), 0.0))
    return out


def test_target_minutes_overlay_small_diff_keeps_0_20_blend():
    """
    小差分（diff < 8.0）では 0.20 blend を維持する。
    """
    t = _team(12, team_id=11)
    r = _rotation(t)
    pid_map = _pid_to_key(r)
    pid = int(r.active_players[0].player_id)
    key = pid_map[pid]

    r._tactics_target_minutes = {}
    base_map = r._build_target_minutes_map()
    base = float(base_map[key])
    overlay_raw = base + 4.0  # diff<8
    overlay = r._clamp_target_minutes(overlay_raw)
    assert abs(overlay - base) < 8.0

    r._tactics_target_minutes = {pid: overlay_raw}
    with_overlay = r._build_target_minutes_map()
    got = float(with_overlay[key])
    expected = r._clamp_target_minutes(base + (overlay - base) * 0.20)
    assert got == pytest.approx(expected, abs=1e-9)


def test_target_minutes_overlay_large_diff_uses_0_30_blend_up_and_down():
    """
    大差分（diff >= 8.0）では、上方向/下方向どちらも 0.30 blend。
    かつ出力 target は安全範囲（4..38）に収まる。
    """
    t = _team(12, team_id=15)
    r = _rotation(t)
    pid_map = _pid_to_key(r)
    down_pid = int(r.active_players[0].player_id)
    up_pid = int(r.active_players[1].player_id)
    down_key = pid_map[down_pid]
    up_key = pid_map[up_pid]

    r._tactics_target_minutes = {}
    base_map = r._build_target_minutes_map()
    down_base = float(base_map[down_key])
    up_base = float(base_map[up_key])

    r._tactics_target_minutes = {down_pid: 0.0, up_pid: 40.0}
    with_overlay = r._build_target_minutes_map()
    down_got = float(with_overlay[down_key])
    up_got = float(with_overlay[up_key])

    down_overlay = r._clamp_target_minutes(0.0)
    up_overlay = r._clamp_target_minutes(40.0)
    assert abs(down_overlay - down_base) >= 8.0
    assert abs(up_overlay - up_base) >= 8.0

    down_expected = r._clamp_target_minutes(down_base + (down_overlay - down_base) * 0.30)
    up_expected = r._clamp_target_minutes(up_base + (up_overlay - up_base) * 0.30)
    assert down_got == pytest.approx(down_expected, abs=1e-9)
    assert up_got == pytest.approx(up_expected, abs=1e-9)
    assert down_got < down_base
    assert up_got > up_base
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


def test_target_minutes_changes_simulated_minutes_directionally():
    """
    同一ロスター・同一進行で target_minutes あり/なしを比較し、
    高 target は増え、低 target は減る方向へ動くことを確認する。
    """
    t_base = _team(12, team_id=21)
    t_overlay = _team(12, team_id=22)

    # 同条件比較: 片方だけ target_minutes を付与
    high_pid = int(t_overlay.players[10].player_id)  # deep bench を厚めに
    low_pid = int(t_overlay.players[2].player_id)    # 先発帯を薄めに
    raw = dict(t_overlay.team_tactics or {})
    rot = dict(raw.get("rotation") or {})
    rot["target_minutes"] = {str(high_pid): 38.0, str(low_pid): 0.0}
    raw["rotation"] = rot
    t_overlay.team_tactics = raw
    ensure_team_tactics_on_team(t_overlay)

    m_base = _simulate_rotation_minutes(t_base, total_possessions=160)
    m_overlay = _simulate_rotation_minutes(t_overlay, total_possessions=160)

    assert m_overlay[high_pid] > m_base[high_pid]
    assert m_overlay[low_pid] < m_base[low_pid]

