"""team_tactics 正規化・旧セーブ互換の最小テスト。"""

from types import SimpleNamespace

from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    normalize_team_tactics,
)


def test_normalize_empty_returns_full_defaults():
    out = normalize_team_tactics(None)
    assert out["version"] >= 1
    assert out["team_strategy"]["offense_tempo"] == "standard"
    assert out["playbook"]["pick_and_roll"] == "standard"


def test_normalize_strips_unknown_and_dedupes_starters():
    raw = {
        "version": 0,
        "team_strategy": {"offense_tempo": "nope", "offense_style": "inside"},
        "rotation": {
            "starters": {"PG": 1, "SG": 1, "SF": 2, "PF": None, "C": 3},
            "bench_order": [2, 2, 5],
            "target_minutes": {"1": 50, "2": -1},
        },
        "usage_policy": {"priority": "invalid"},
        "roles": {"1": {"main_role": "ace"}, "999": {"main_role": "ace"}},
        "playbook": {"pick_and_roll": "high"},
    }
    out = normalize_team_tactics(raw, valid_player_ids={1, 2, 3})
    assert out["team_strategy"]["offense_tempo"] == "standard"
    assert out["team_strategy"]["offense_style"] == "inside"
    assert out["rotation"]["starters"]["PG"] == 1
    assert out["rotation"]["starters"]["SG"] is None
    assert out["rotation"]["bench_order"] == [2, 5]
    assert out["rotation"]["target_minutes"]["1"] == 40.0
    assert out["rotation"]["target_minutes"]["2"] == 0.0
    assert out["usage_policy"]["priority"] == "balanced"
    assert "1" in out["roles"]
    assert "999" not in out["roles"]


def test_ensure_team_tactics_on_team_mutates_safe():
    team = SimpleNamespace(players=[], team_tactics="bad")
    ensure_team_tactics_on_team(team)
    assert isinstance(team.team_tactics, dict)
    assert team.team_tactics["team_strategy"]["defense_style"] == "balanced"


def test_ensure_filters_roles_by_roster():
    p = SimpleNamespace(player_id=10)
    team = SimpleNamespace(players=[p], team_tactics={"roles": {"10": {"main_role": "ace"}, "99": {"main_role": "ace"}}})
    ensure_team_tactics_on_team(team)
    assert "10" in team.team_tactics["roles"]
    assert "99" not in team.team_tactics["roles"]


def test_default_has_all_playbook_keys():
    d = get_default_team_tactics()
    assert set(d["playbook"].keys()) == {
        "pick_and_roll",
        "spain_pick_and_roll",
        "handoff",
        "off_ball_screen",
        "post_up",
        "transition",
    }
