"""roles.clutch_priority をクラッチ時FGシューター選択へ極小接続するテスト。"""

from __future__ import annotations

from unittest import mock

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_roles_clutch_shooter_weight_multiplier,
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
        ovr=70,
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


def _set_role(team: Team, pid: int, clutch_priority: str) -> None:
    raw = dict(getattr(team, "team_tactics", {}) or get_default_team_tactics())
    roles = dict(raw.get("roles") or {})
    roles[str(pid)] = {
        "main_role": "none",
        "offense_involvement": "standard",
        "shot_priority": "standard",
        "clutch_priority": clutch_priority,
        "playmaking_role": "secondary",
        "defense_assignment": "standard",
    }
    raw["roles"] = roles
    team.team_tactics = raw
    ensure_team_tactics_on_team(team)


def _capture_weights(m: Match, team: Team, lineup: list[Player], shot_profile: str, *, clutch: bool) -> list[int]:
    captured: dict[str, list[int]] = {}

    def _fake_choices(population, weights=None, k=1):
        captured["weights"] = list(weights or [])
        return [population[0]]

    if clutch:
        m.total_possessions = 160
        m.current_possession = 157
        m.home_score = 80
        m.away_score = 75
    else:
        m.total_possessions = 160
        m.current_possession = 20
        m.home_score = 40
        m.away_score = 40

    with mock.patch("basketball_sim.models.match.random.choices", side_effect=_fake_choices):
        if shot_profile in {"two", "three"}:
            m._select_field_goal_shooter(team, lineup, shot_profile)
        else:
            m._select_shooter(team, lineup, shot_profile)
    return captured["weights"]


def test_roles_clutch_shooter_multiplier_non_clutch_is_one():
    t = _team(1, "T")
    p = t.players[0]
    _set_role(t, p.player_id, "go_to")
    assert get_roles_clutch_shooter_weight_multiplier(t, p, is_clutch=False) == 1.0


def test_roles_clutch_shooter_multiplier_handles_invalid_and_missing():
    t = _team(2, "T2")
    p = t.players[0]
    _set_role(t, p.player_id, "invalid_value")
    assert get_roles_clutch_shooter_weight_multiplier(t, p, is_clutch=True) == 1.0
    t.team_tactics["roles"] = {}
    ensure_team_tactics_on_team(t)
    assert get_roles_clutch_shooter_weight_multiplier(t, p, is_clutch=True) == 1.0


def test_non_clutch_fg_selection_stays_unchanged_even_go_to_or_limited():
    home = _team(10, "H")
    away = _team(20, "A")
    target_pid = home.players[0].player_id
    _set_role(home, target_pid, "standard")
    m = Match(home, away)
    std_w = _capture_weights(m, home, m.home_starters, "two", clutch=False)
    _set_role(home, target_pid, "go_to")
    go_to_w = _capture_weights(m, home, m.home_starters, "two", clutch=False)
    _set_role(home, target_pid, "limited")
    limited_w = _capture_weights(m, home, m.home_starters, "two", clutch=False)
    idx = next(i for i, p in enumerate(m.home_starters) if p.player_id == target_pid)
    assert go_to_w[idx] == std_w[idx]
    assert limited_w[idx] == std_w[idx]


def test_clutch_fg_selection_go_to_increases_vs_standard_for_same_player():
    home = _team(11, "H2")
    away = _team(21, "A2")
    target_pid = home.players[0].player_id
    _set_role(home, target_pid, "standard")
    m = Match(home, away)
    std_w = _capture_weights(m, home, m.home_starters, "three", clutch=True)
    _set_role(home, target_pid, "go_to")
    go_to_w = _capture_weights(m, home, m.home_starters, "three", clutch=True)
    idx = next(i for i, p in enumerate(m.home_starters) if p.player_id == target_pid)
    assert go_to_w[idx] > std_w[idx]


def test_clutch_fg_selection_limited_decreases_vs_standard_for_same_player():
    home = _team(12, "H3")
    away = _team(22, "A3")
    target_pid = home.players[0].player_id
    _set_role(home, target_pid, "standard")
    m = Match(home, away)
    std_w = _capture_weights(m, home, m.home_starters, "two", clutch=True)
    _set_role(home, target_pid, "limited")
    limited_w = _capture_weights(m, home, m.home_starters, "two", clutch=True)
    idx = next(i for i, p in enumerate(m.home_starters) if p.player_id == target_pid)
    assert limited_w[idx] < std_w[idx]


def test_ft_shooter_selection_not_affected_even_in_clutch_window():
    home = _team(13, "H4")
    away = _team(23, "A4")
    target_pid = home.players[0].player_id
    _set_role(home, target_pid, "standard")
    m = Match(home, away)
    std_w = _capture_weights(m, home, m.home_starters, "ft", clutch=True)
    _set_role(home, target_pid, "go_to")
    go_to_w = _capture_weights(m, home, m.home_starters, "ft", clutch=True)
    _set_role(home, target_pid, "limited")
    limited_w = _capture_weights(m, home, m.home_starters, "ft", clutch=True)
    idx = next(i for i, p in enumerate(m.home_starters) if p.player_id == target_pid)
    assert go_to_w[idx] == std_w[idx]
    assert limited_w[idx] == std_w[idx]

