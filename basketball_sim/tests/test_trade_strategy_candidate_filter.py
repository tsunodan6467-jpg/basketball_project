"""conduct_trades 候補の CPU 戦略タグ別ロスター保護（薄いフィルタ）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.cpu_club_strategy import StrategyProfile
from basketball_sim.systems.trade import (
    PUSH_TRADE_PROTECT_MIN_OVR,
    STRATEGY_TRADE_PROTECT_MIN_REMAINING,
    _INCOMING_ASSET_SORT_ADJUST_CAP,
    _OUTGOING_ASSET_KEEP_BIAS_CAP,
    _apply_strategy_trade_candidate_filter,
    _incoming_trade_candidate_sort_key,
    _outgoing_trade_candidate_sort_key,
    _strategy_tag_protect_exclude_player,
    _trade_incoming_sort_adjustment_for_tag,
    _trade_outgoing_sort_adjustment_for_tag,
)


def _mk_player(pid: int, age: int, ovr: int, pot: str) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality="Japan",
        position="PG",
        height_cm=180.0,
        weight_kg=75.0,
        shoot=50,
        three=50,
        drive=50,
        passing=50,
        rebound=50,
        defense=50,
        ft=50,
        stamina=50,
        ovr=ovr,
        potential=pot,
        archetype="guard",
        usage_base=20,
        salary=500_000,
        contract_years_left=1,
        contract_total_years=1,
        team_id=1,
    )


@pytest.fixture
def dummy_team() -> Team:
    return Team(team_id=1, name="T", league_level=1, money=50_000_000, players=[], is_user_team=False)


def test_rebuild_protects_young_sa() -> None:
    assert _strategy_tag_protect_exclude_player(_mk_player(1, 22, 65, "S"), "rebuild") is True
    assert _strategy_tag_protect_exclude_player(_mk_player(2, 22, 65, "A"), "rebuild") is True
    assert _strategy_tag_protect_exclude_player(_mk_player(3, 23, 65, "S"), "rebuild") is False
    assert _strategy_tag_protect_exclude_player(_mk_player(4, 22, 65, "B"), "rebuild") is False


def test_push_protects_high_ovr() -> None:
    assert _strategy_tag_protect_exclude_player(_mk_player(1, 28, PUSH_TRADE_PROTECT_MIN_OVR, "D"), "push") is True
    assert _strategy_tag_protect_exclude_player(_mk_player(2, 28, PUSH_TRADE_PROTECT_MIN_OVR - 1, "D"), "push") is False


def test_hold_protects_minimal() -> None:
    assert _strategy_tag_protect_exclude_player(_mk_player(1, 21, 60, "S"), "hold") is True
    assert _strategy_tag_protect_exclude_player(_mk_player(2, 21, 60, "A"), "hold") is False
    assert _strategy_tag_protect_exclude_player(_mk_player(3, 22, 60, "S"), "hold") is False


def test_apply_filter_falls_back_when_too_few_remain(dummy_team: Team) -> None:
    """保護で候補が STRATEGY_TRADE_PROTECT_MIN_REMAINING 未満に削られる場合は元リストに戻す。"""
    players = [
        _mk_player(10, 20, 62, "S"),
        _mk_player(11, 20, 62, "S"),
        _mk_player(12, 20, 62, "S"),
        _mk_player(13, 20, 62, "S"),
        _mk_player(14, 28, 62, "D"),
        _mk_player(15, 28, 62, "D"),
    ]
    with patch("basketball_sim.systems.trade.get_cpu_club_strategy") as m:
        m.return_value = StrategyProfile("rebuild", 1.0, 1.0, 1.0)
        out = _apply_strategy_trade_candidate_filter(dummy_team, players)
    assert len(out) == len(players)


def test_apply_filter_keeps_when_enough_remain(dummy_team: Team) -> None:
    players = [
        _mk_player(20, 28, 62, "D"),
        _mk_player(21, 28, 62, "D"),
        _mk_player(22, 28, 62, "D"),
        _mk_player(23, 28, 62, "D"),
        _mk_player(24, 20, 62, "S"),
    ]
    with patch("basketball_sim.systems.trade.get_cpu_club_strategy") as m:
        m.return_value = StrategyProfile("rebuild", 1.0, 1.0, 1.0)
        out = _apply_strategy_trade_candidate_filter(dummy_team, players)
    assert len(out) == 4
    assert all(getattr(p, "player_id", 0) != 24 for p in out)


def test_apply_filter_empty_returns_original(dummy_team: Team) -> None:
    p = _mk_player(30, 20, 62, "S")
    with patch("basketball_sim.systems.trade.get_cpu_club_strategy") as m:
        m.return_value = StrategyProfile("rebuild", 1.0, 1.0, 1.0)
        out = _apply_strategy_trade_candidate_filter(dummy_team, [p])
    assert out == [p]


def test_rebuild_sort_bias_favors_keeping_young_high_pot_over_veteran() -> None:
    """将来枠（保護外の若手高ポテ）の keep バイアスがベテランより大きい＝昇順ソートで後ろに回りやすい。"""
    young = _mk_player(1, 24, 65, "S")
    vet = _mk_player(2, 32, 65, "D")
    assert _trade_outgoing_sort_adjustment_for_tag("rebuild", young) > _trade_outgoing_sort_adjustment_for_tag(
        "rebuild", vet
    )


def test_push_sort_bias_favors_keeping_high_ovr_over_low_ovr_youth() -> None:
    """即戦力寄り: 高 OVR の keep バイアスが低 OVR 若手より大きい。"""
    high = _mk_player(1, 28, 72, "D")
    low_youth = _mk_player(2, 22, 62, "B")
    assert _trade_outgoing_sort_adjustment_for_tag("push", high) > _trade_outgoing_sort_adjustment_for_tag(
        "push", low_youth
    )


def test_hold_sort_bias_stays_within_cap() -> None:
    """hold は極端な補正に寄らない（上限内）。"""
    samples = (
        _mk_player(1, 21, 60, "S"),
        _mk_player(2, 33, 68, "C"),
        _mk_player(3, 28, 73, "D"),
        _mk_player(4, 25, 66, "B"),
    )
    for p in samples:
        adj = _trade_outgoing_sort_adjustment_for_tag("hold", p)
        assert abs(adj) <= _OUTGOING_ASSET_KEEP_BIAS_CAP + 1e-9


def test_outgoing_sort_key_rebuild_young_tied_ovr_sorts_after_veteran(dummy_team: Team) -> None:
    """同 OVR 近傍で rebuild は若手高ポテのソートキーがベテランより大きい（放出候補の先頭から遠い）。"""
    young = _mk_player(10, 24, 66, "A")
    vet = _mk_player(11, 32, 66, "D")
    dummy_team.players = [young, vet]
    ky = _outgoing_trade_candidate_sort_key(dummy_team, young, strategy_tag="rebuild")
    kv = _outgoing_trade_candidate_sort_key(dummy_team, vet, strategy_tag="rebuild")
    assert ky > kv


def test_rebuild_incoming_bias_prefers_young_high_pot_over_veteran(dummy_team: Team) -> None:
    young = _mk_player(20, 22, 65, "S")
    vet = _mk_player(21, 34, 65, "D")
    assert _trade_incoming_sort_adjustment_for_tag("rebuild", young, dummy_team) > _trade_incoming_sort_adjustment_for_tag(
        "rebuild", vet, dummy_team
    )


def test_push_incoming_bias_prefers_high_ovr_over_raw_youth(dummy_team: Team) -> None:
    star = _mk_player(30, 28, 72, "D")
    raw = _mk_player(31, 20, 60, "B")
    assert _trade_incoming_sort_adjustment_for_tag("push", star, dummy_team) > _trade_incoming_sort_adjustment_for_tag(
        "push", raw, dummy_team
    )


def test_incoming_adjustment_respects_cap(dummy_team: Team) -> None:
    for p in (
        _mk_player(40, 19, 58, "S"),
        _mk_player(41, 35, 74, "D"),
        _mk_player(42, 26, 70, "C"),
    ):
        for tag in ("rebuild", "hold", "push"):
            a = _trade_incoming_sort_adjustment_for_tag(tag, p, dummy_team)
            assert abs(a) <= _INCOMING_ASSET_SORT_ADJUST_CAP + 1e-9


def test_hold_incoming_bias_not_extreme_vs_rebuild_push(dummy_team: Team) -> None:
    """hold の補正が rebuild/push ほど極端に振れない（同選手で幅が最小側）。"""
    p = _mk_player(50, 22, 68, "S")
    h = abs(_trade_incoming_sort_adjustment_for_tag("hold", p, dummy_team))
    r = abs(_trade_incoming_sort_adjustment_for_tag("rebuild", p, dummy_team))
    u = abs(_trade_incoming_sort_adjustment_for_tag("push", p, dummy_team))
    assert h <= max(r, u) + 0.15


def test_incoming_sort_key_rebuild_prefers_young_on_same_roster(dummy_team: Team) -> None:
    young = _mk_player(60, 23, 66, "A")
    vet = _mk_player(61, 33, 66, "D")
    dummy_team.players = [young, vet]
    ky = _incoming_trade_candidate_sort_key(dummy_team, young, strategy_tag="rebuild")
    kv = _incoming_trade_candidate_sort_key(dummy_team, vet, strategy_tag="rebuild")
    assert ky > kv
