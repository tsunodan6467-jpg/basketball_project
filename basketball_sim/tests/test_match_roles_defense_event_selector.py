"""defense_assignment をスティール記録者選択へ極小接続するテスト。"""

from __future__ import annotations

from unittest import mock

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_roles_defense_event_weight_multiplier,
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


def _set_defense_assignment(team: Team, pid: int, defense_assignment: str) -> None:
    raw = dict(getattr(team, "team_tactics", {}) or get_default_team_tactics())
    roles = dict(raw.get("roles") or {})
    roles[str(pid)] = {
        "main_role": "none",
        "offense_involvement": "standard",
        "shot_priority": "standard",
        "clutch_priority": "standard",
        "playmaking_role": "secondary",
        "defense_assignment": defense_assignment,
    }
    raw["roles"] = roles
    team.team_tactics = raw
    ensure_team_tactics_on_team(team)


def _capture_steal_weights(m: Match, lineup: list[Player]) -> list[int]:
    captured: dict[str, list[int]] = {}

    def _fake_choices(population, weights=None, k=1):
        captured["weights"] = list(weights or [])
        return [population[0]]

    with mock.patch("basketball_sim.models.match.random.choices", side_effect=_fake_choices):
        m._pick_stealer(lineup)
    return captured["weights"]


def test_roles_defense_event_multiplier_stopper_and_light():
    t = _team(1, "T1")
    p = t.players[0]
    _set_defense_assignment(t, p.player_id, "stopper")
    assert get_roles_defense_event_weight_multiplier(t, p) == 1.05
    _set_defense_assignment(t, p.player_id, "light")
    assert get_roles_defense_event_weight_multiplier(t, p) == 0.96


def test_roles_defense_event_multiplier_standard_missing_invalid_fallback_to_one():
    t = _team(2, "T2")
    p = t.players[0]
    _set_defense_assignment(t, p.player_id, "standard")
    assert get_roles_defense_event_weight_multiplier(t, p) == 1.0
    _set_defense_assignment(t, p.player_id, "invalid_value")
    assert get_roles_defense_event_weight_multiplier(t, p) == 1.0
    t.team_tactics["roles"] = {}
    ensure_team_tactics_on_team(t)
    assert get_roles_defense_event_weight_multiplier(t, p) == 1.0
    assert get_roles_defense_event_weight_multiplier(t, None) == 1.0


def test_pick_stealer_weight_moves_stopper_gt_standard_gt_light_for_same_player():
    home = _team(10, "H")
    away = _team(20, "A")
    m = Match(home, away)
    target_pid = m.home_starters[0].player_id

    _set_defense_assignment(home, target_pid, "standard")
    std_w = _capture_steal_weights(m, m.home_starters)

    _set_defense_assignment(home, target_pid, "stopper")
    stopper_w = _capture_steal_weights(m, m.home_starters)

    _set_defense_assignment(home, target_pid, "light")
    light_w = _capture_steal_weights(m, m.home_starters)

    idx = next(i for i, p in enumerate(m.home_starters) if p.player_id == target_pid)
    assert stopper_w[idx] > std_w[idx] > light_w[idx]


def test_defense_roles_helper_is_not_used_by_block_rebound_or_foul_selectors():
    home = _team(11, "H2")
    away = _team(21, "A2")
    m = Match(home, away)

    with mock.patch(
        "basketball_sim.models.match.get_roles_defense_event_weight_multiplier",
        side_effect=AssertionError("should not be called"),
    ):
        m._pick_blocker(m.home_starters, is_three=False)
        m._pick_rebounder(m.home_starters, "defense")
        m._pick_fouler(m.home_starters)
