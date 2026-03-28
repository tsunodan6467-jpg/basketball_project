"""Phase B: team_tactics の rotation を試合先発・ローテへ弱く接続する挙動のテスト。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    collect_tactics_starter_players,
    ensure_team_tactics_on_team,
    get_rotation_target_minutes_by_player_id,
)


def _player(pid: int, position: str, ovr: int = 68, nationality: str = "Japan") -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality=nationality,
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
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team_with_tactics(starters_ovr: int, bench_ovr: int, tactics_starters: dict) -> Team:
    t = Team(team_id=1, name="Home", league_level=1)
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]
    for i, pos in enumerate(positions, start=1):
        ovr = starters_ovr if i <= 5 else bench_ovr
        t.add_player(_player(100 + i, pos, ovr=ovr))
    t.team_tactics = {
        "version": 1,
        "rotation": {"starters": tactics_starters},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(t)
    return t


def test_collect_tactics_starter_players_requires_all_slots():
    t = _team_with_tactics(80, 60, {"PG": 101, "SG": 102, "SF": None, "PF": 104, "C": 105})
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    assert collect_tactics_starter_players(t, active) is None


def test_collect_tactics_starter_players_returns_ordered_lineup():
    t = _team_with_tactics(80, 60, {"PG": 105, "SG": 104, "SF": 103, "PF": 102, "C": 101})
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    lineup = collect_tactics_starter_players(t, active)
    assert lineup is not None
    assert [getattr(p, "player_id", None) for p in lineup] == [105, 104, 103, 102, 101]


def test_get_rotation_target_minutes_by_player_id():
    t = Team(team_id=1, name="X", league_level=1)
    t.team_tactics = {
        "rotation": {"target_minutes": {"101": 30, "bad": "x"}},
    }
    m = get_rotation_target_minutes_by_player_id(t)
    assert m.get(101) == pytest.approx(30.0)
    assert len(m) == 1


def test_match_applies_tactics_starter_only_within_ovr_gap():
    """ベース先発が高評価でも、戦術1スロットは被害者との OVR 差≤3 なら差し替え可。"""
    home = Team(team_id=1, name="Home", league_level=1)
    home.add_player(_player(201, "C", ovr=85))
    home.add_player(_player(202, "PF", ovr=85))
    home.add_player(_player(203, "SF", ovr=85))
    home.add_player(_player(204, "SG", ovr=80))
    home.add_player(_player(205, "PG", ovr=85))
    home.add_player(_player(206, "SG", ovr=78))

    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {"SG": 206}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)

    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(300 + i, pos, ovr=70))

    m = Match(home_team=home, away_team=away)
    ids = {getattr(p, "player_id", None) for p in m.home_starters}
    assert 206 in ids
    assert 204 not in ids


def test_match_skips_tactics_starter_when_ovr_gap_exceeds_three():
    home = Team(team_id=1, name="Home", league_level=1)
    home.add_player(_player(201, "C", ovr=85))
    home.add_player(_player(202, "PF", ovr=85))
    home.add_player(_player(203, "SF", ovr=85))
    home.add_player(_player(204, "SG", ovr=80))
    home.add_player(_player(205, "PG", ovr=85))
    home.add_player(_player(207, "SG", ovr=70))

    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {"SG": 207}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)

    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(400 + i, pos, ovr=70))

    m = Match(home_team=home, away_team=away)
    ids = {getattr(p, "player_id", None) for p in m.home_starters}
    assert 204 in ids
    assert 207 not in ids


def test_match_fallback_victim_when_base_lineup_has_no_same_position():
    """ベース先発に SG がいないとき、フォールバックで OVR 最低席と差し替え（§5.1-3）。"""
    home = Team(team_id=1, name="Home", league_level=1)
    home.add_player(_player(301, "PG", ovr=92))
    home.add_player(_player(302, "PG", ovr=91))
    home.add_player(_player(303, "SF", ovr=90))
    home.add_player(_player(304, "PF", ovr=89))
    home.add_player(_player(305, "C", ovr=88))
    home.add_player(_player(306, "SG", ovr=87))
    home.add_player(_player(307, "SG", ovr=70))
    home.add_player(_player(308, "PF", ovr=65))

    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {"SG": 306}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)

    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(600 + i, pos, ovr=70))

    m = Match(home_team=home, away_team=away)
    ids = {getattr(p, "player_id", None) for p in m.home_starters}
    assert 306 in ids
    assert 305 not in ids


def test_match_skips_tactics_when_player_position_mismatches_slot():
    home = Team(team_id=1, name="Home", league_level=1)
    home.add_player(_player(201, "C", ovr=85))
    home.add_player(_player(202, "PF", ovr=85))
    home.add_player(_player(203, "SF", ovr=85))
    home.add_player(_player(204, "SG", ovr=80))
    home.add_player(_player(205, "PG", ovr=85))
    home.add_player(_player(206, "SG", ovr=78))

    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {"PG": 206}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)

    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(500 + i, pos, ovr=70))

    m = Match(home_team=home, away_team=away)
    ids = {getattr(p, "player_id", None) for p in m.home_starters}
    assert 205 in ids
    assert 206 not in ids


def test_match_falls_back_when_tactics_violates_on_court_foreign_cap():
    home = Team(team_id=1, name="Home", league_level=1)
    home.add_player(_player(101, "PG", ovr=88, nationality="Foreign"))
    home.add_player(_player(102, "SG", ovr=88, nationality="Foreign"))
    home.add_player(_player(103, "SF", ovr=88, nationality="Foreign"))
    home.add_player(_player(104, "PF", ovr=70, nationality="Japan"))
    home.add_player(_player(105, "C", ovr=70, nationality="Japan"))
    home.add_player(_player(106, "PG", ovr=65, nationality="Japan"))
    home.add_player(_player(107, "SG", ovr=65, nationality="Japan"))
    home.add_player(_player(108, "SF", ovr=65, nationality="Japan"))

    home.team_tactics = {
        "version": 1,
        "rotation": {
            "starters": {"PG": 101, "SG": 102, "SF": 103, "PF": 104, "C": 105},
        },
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)

    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(300 + i, pos, ovr=70))

    m = Match(home_team=home, away_team=away)
    foreign_on_court = sum(
        1 for p in m.home_starters if getattr(p, "nationality", "") == "Foreign"
    )
    assert foreign_on_court <= 2
    assert {101, 102, 103} != {getattr(p, "player_id", None) for p in m.home_starters}


def test_rotation_applies_weak_target_minutes_overlay():
    """同条件でベース先発（ランク0）は約33分台。10分へ20%ブレンドならオーバーレイありで下がる。"""
    t = Team(team_id=1, name="Home", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        t.add_player(_player(400 + i, pos, ovr=70))
    t.team_tactics = {
        "version": 1,
        "rotation": {"target_minutes": {"400": 10.0}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(t)
    active = [p for p in t.players if not p.is_injured() and not p.is_retired]
    starters = active[:5]
    rot = RotationSystem(t, active, starters=starters)
    p400 = next(p for p in active if p.player_id == 400)
    key400 = rot._player_key(p400)
    with_overlay = rot._build_target_minutes_map()
    rot._tactics_target_minutes = {}
    base_only = rot._build_target_minutes_map()
    assert with_overlay[key400] < base_only[key400]
    assert with_overlay[key400] > 10.0
