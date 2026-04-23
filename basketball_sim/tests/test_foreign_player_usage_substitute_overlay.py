"""usage_policy.foreign_player_usage → get_foreign_player_usage_substitute_overlay（合法通過後候補のみ）。"""

from unittest import mock

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.competition_rules import get_competition_rule
from basketball_sim.systems.rotation import RotationSystem
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_foreign_player_usage_substitute_overlay,
)


def _player(pid: int, position: str, nationality: str) -> Player:
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
        ovr=70,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _on_court_rule() -> dict:
    return get_competition_rule("regular_season", "on_court")


def _usage_team(mode: str) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.add_player(_player(1, "SG", "Foreign"))
    t.add_player(_player(2, "SG", "Japan"))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": "standard",
            "foreign_player_usage": mode,
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def test_balanced_is_always_zero_for_any_bucket():
    t = _usage_team("balanced")
    r = _on_court_rule()
    assert get_foreign_player_usage_substitute_overlay(t, _player(1, "SG", "Foreign"), r) == 0.0
    assert get_foreign_player_usage_substitute_overlay(t, _player(2, "SG", "Japan"), r) == 0.0


def test_stars_gives_plus_for_regulation_foreign_bucket():
    t = _usage_team("stars")
    r = _on_court_rule()
    f = get_foreign_player_usage_substitute_overlay(t, _player(1, "SG", "Foreign"), r)
    j = get_foreign_player_usage_substitute_overlay(t, _player(2, "SG", "Japan"), r)
    assert f == pytest.approx(0.25)
    assert j == 0.0
    assert f > j


def test_japan_core_penalizes_foreign_bucket_and_bonuses_domestic():
    t = _usage_team("japan_core")
    r = _on_court_rule()
    f = get_foreign_player_usage_substitute_overlay(t, _player(1, "SG", "Foreign"), r)
    j = get_foreign_player_usage_substitute_overlay(t, _player(2, "SG", "Japan"), r)
    assert f == pytest.approx(-0.25)
    assert j == pytest.approx(0.1)
    assert j - f == pytest.approx(0.35)


def test_stars_japan_as_special_bucket_zero_prefer_stars_versus_foreign_plus():
    """Rule asia_as_foreign=False: Asia 国籍は special。stars は foreign bucket のみ +0.25。"""
    t = _usage_team("stars")
    r = _on_court_rule()  # asia_as_foreign False
    a = get_foreign_player_usage_substitute_overlay(t, _player(1, "SG", "Asia"), r)
    o = get_foreign_player_usage_substitute_overlay(t, _player(2, "SG", "Foreign"), r)
    assert a == 0.0
    assert o == pytest.approx(0.25)
    assert o > a


def test_illegal_in_candidate_does_not_receive_overlay_call():
    """
    _find_best_substitute では continue で弾かれた候補には
    外国籍起用オーバーレイ加算前でループを抜ける（合法通過後だけ加算）。
    コート2外国人上限・先発2F+3J のまま1人をJでアウトし、3人目Fは不合法、同ポジJは合法。
    """
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    t.add_player(_player(101, "PG", "Foreign"))
    t.add_player(_player(102, "SG", "Foreign"))
    t.add_player(_player(103, "SF", "Japan"))
    t.add_player(_player(104, "PF", "Japan"))
    t.add_player(_player(105, "C", "Japan"))
    t.add_player(_player(106, "PF", "Foreign"))
    t.add_player(_player(107, "PF", "Japan"))
    t.team_tactics = {
        "version": 1,
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "standard",
            "age_balance": "balanced",
            "injury_care": "standard",
            "schedule_care": "standard",
            "foreign_player_usage": "stars",
        },
    }
    ensure_team_tactics_on_team(t)
    by_id = {p.player_id: p for p in t.players}
    order = [101, 102, 103, 104, 105]
    starters = [by_id[i] for i in order]
    active = [by_id[i] for i in order + [106, 107]]
    rot = RotationSystem(t, active, starters=starters)
    p104 = by_id[104]
    p106 = by_id[106]
    p107 = by_id[107]
    in_candidates = [p106, p107]

    def _track(team, player, on_court):
        return get_foreign_player_usage_substitute_overlay(team, player, on_court)

    called: list = []

    def tr(team, pl, rule):
        called.append(int(getattr(pl, "player_id", 0) or 0))
        return _track(team, pl, rule)

    with mock.patch("basketball_sim.systems.rotation.get_foreign_player_usage_substitute_overlay", side_effect=tr):
        pick = rot._find_best_substitute(
            p104, in_candidates, possession=0, total_possessions=160
        )
    assert pick is not None
    assert pick.player_id == 107
    assert 106 not in called
    assert 107 in called
    assert called == [107]
