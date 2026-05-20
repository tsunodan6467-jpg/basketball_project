from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.tactics_summary_readonly import (
    SCREEN_TITLE,
    build_tactics_summary_readonly_dict,
    export_tactics_summary_json_from_world,
    write_tactics_summary_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world
from basketball_sim.systems.team_tactics import get_default_team_tactics, normalize_team_tactics

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "tactic_items",
    "rotation_items",
    "player_role_items",
    "sections",
    "notes",
)


def test_build_tactics_summary_required_top_keys() -> None:
    d = build_tactics_summary_readonly_dict(None)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["screen_title"] == SCREEN_TITLE
    assert d["screen_title"] == "戦術・ローテーションサマリー（閲覧）"


def test_build_tactics_summary_team_none() -> None:
    d = build_tactics_summary_readonly_dict(None, season_count=2, at_annual_menu=True)
    assert d["team_name"] == "-"
    assert d["league_level"] is None
    assert d["player_role_items"] == []
    assert d["summary"]["has_team_tactics"] is False
    joined = "\n".join(d["notes"])
    assert "チーム情報が未接続" in joined


def test_reads_dict_team_tactics() -> None:
    tt = get_default_team_tactics()
    tt["preset_meta"] = {"version": 1, "playstyle_preset_id": "balanced_v1", "rotation_preset_id": "win_now_v1"}
    tt["rotation"]["starters"] = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
    tt["rotation"]["target_minutes"] = {"1": 32.0, "2": 30.0}
    tt["roles"] = {"1": {"main_role": "star", "offense_involvement": "high"}}
    p1 = SimpleNamespace(player_id=1, name="一郎", position="PG")
    p2 = SimpleNamespace(player_id=2, name="二郎", position="SG")
    p3 = SimpleNamespace(player_id=3, name="三郎", position="SF")
    p4 = SimpleNamespace(player_id=4, name="四郎", position="PF")
    p5 = SimpleNamespace(player_id=5, name="五郎", position="C")
    team = SimpleNamespace(
        name="戦術FC",
        league_level=1,
        strategy="balanced",
        players=[p1, p2, p3, p4, p5],
        team_tactics=tt,
    )
    d = build_tactics_summary_readonly_dict(team, max_players=8)
    assert d["team_name"] == "戦術FC"
    assert d["summary"]["has_team_tactics"] is True
    assert d["summary"]["starter_count"] == 5
    assert d["summary"]["target_minutes_count"] >= 2
    assert len(d["player_role_items"]) >= 5
    assert d["player_role_items"][0]["starter"] is True
    assert d["player_role_items"][0]["player_id"] == 1
    assert isinstance(d["player_role_items"][0]["player_id"], int)
    assert "order" in d["player_role_items"][0]


def test_player_role_items_include_player_id() -> None:
    starters = {pos: i + 10 for i, pos in enumerate(["PG", "SG", "SF", "PF", "C"])}
    tt = get_default_team_tactics()
    tt["rotation"]["starters"] = starters
    players = [
        SimpleNamespace(player_id=i + 10, name=f"P{i}", position=pos)
        for i, pos in enumerate(["PG", "SG", "SF", "PF", "C"])
    ]
    team = SimpleNamespace(name="ID", league_level=1, strategy="balanced", players=players, team_tactics=tt)
    d = build_tactics_summary_readonly_dict(team, max_players=8)
    ids = {row["player_id"] for row in d["player_role_items"]}
    assert ids == {10, 11, 12, 13, 14}
    for row in d["player_role_items"]:
        assert isinstance(row["player_id"], int)
        assert isinstance(row["order"], int)
        assert row["player_id"] != row["order"]


def test_team_tactics_unchanged_after_build() -> None:
    tt = get_default_team_tactics()
    tt["rotation"]["starters"] = {"PG": 10}
    tt["rotation"]["bench_order"] = [11, 12]
    team = SimpleNamespace(
        name="Mut",
        league_level=1,
        strategy="defense",
        players=[
            SimpleNamespace(player_id=10, name="A", position="PG"),
            SimpleNamespace(player_id=11, name="B", position="SG"),
            SimpleNamespace(player_id=12, name="C", position="SF"),
        ],
        team_tactics=tt,
    )
    before = copy.deepcopy(team.team_tactics)
    build_tactics_summary_readonly_dict(team)
    assert team.team_tactics == before
    assert team.team_tactics["rotation"]["starters"]["PG"] == 10


def test_normalize_on_deepcopy_leaves_original_nested() -> None:
    raw = {
        "version": 1,
        "team_strategy": {"offense_tempo": "fast"},
        "rotation": {"starters": {}, "bench_order": [], "target_minutes": {"99": 12.5}},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
        "preset_meta": {"version": 1, "playstyle_preset_id": None, "rotation_preset_id": None},
    }
    snap = copy.deepcopy(raw)
    normalize_team_tactics(snap, valid_player_ids={99})
    assert raw["rotation"]["target_minutes"]["99"] == 12.5


def test_missing_rotation_and_roles_no_crash() -> None:
    team = SimpleNamespace(
        name="Sparse",
        league_level=2,
        strategy="balanced",
        players=[],
        team_tactics={"version": 1},
    )
    d = build_tactics_summary_readonly_dict(team)
    assert d["summary"]["starter_count"] == 0
    assert d["player_role_items"] == []


def test_max_players_limits_player_role_items() -> None:
    starters = {pos: i + 1 for i, pos in enumerate(["PG", "SG", "SF", "PF", "C"])}
    tt = get_default_team_tactics()
    tt["rotation"]["starters"] = starters
    players = [SimpleNamespace(player_id=i + 1, name=f"P{i}", position=pos) for i, pos in enumerate(["PG", "SG", "SF", "PF", "C"])]
    team = SimpleNamespace(name="Cap", league_level=1, strategy="balanced", players=players, team_tactics=tt)
    d = build_tactics_summary_readonly_dict(team, max_players=2)
    assert len(d["player_role_items"]) == 2


def test_write_tactics_summary_json_utf8(tmp_path: Path) -> None:
    team = Team(team_id=1, name="日本語戦術", league_level=1)
    team.strategy = "balanced"
    team.team_tactics = get_default_team_tactics()
    d = build_tactics_summary_readonly_dict(team)
    out = tmp_path / "tactics.json"
    write_tactics_summary_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語戦術" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語戦術"


def test_export_tactics_summary_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "t.sav"
    team = Team(team_id=7, name="出口戦術FC", league_level=1)
    team.strategy = "run_and_gun"
    team.team_tactics = get_default_team_tactics()
    team.players = []
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 7,
        "season_count": 3,
        "at_annual_menu": False,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "tactics_out.json"
    snap = export_tactics_summary_json_from_world(sav, out, max_players=4)
    assert out.is_file()
    assert snap["team_name"] == "出口戦術FC"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["summary"]["season_count"] == 3
    assert body["summary"]["at_annual_menu"] is False


def test_sections_structure() -> None:
    d = build_tactics_summary_readonly_dict(None)
    titles = [s["title"] for s in d["sections"]]
    assert titles == ["戦術概要", "攻撃方針", "守備方針", "ローテーション", "注意"]
    for sec in d["sections"]:
        assert "lines" in sec
        assert isinstance(sec["lines"], list)


def test_non_dict_team_tactics() -> None:
    team = SimpleNamespace(name="Weird", league_level=1, strategy="balanced", players=[], team_tactics="not-a-dict")
    d = build_tactics_summary_readonly_dict(team)
    assert d["summary"]["has_team_tactics"] is False
    assert "戦術設定が未接続" in "\n".join(d["notes"])


def test_object_team_not_crash() -> None:
    team = object()
    d = build_tactics_summary_readonly_dict(team)
    assert d["team_name"] == "-"


def test_invalid_players_list() -> None:
    team = SimpleNamespace(
        name="BadList",
        league_level=1,
        strategy="balanced",
        players="not-a-list",
        team_tactics=get_default_team_tactics(),
    )
    d = build_tactics_summary_readonly_dict(team)
    assert d["player_role_items"] == []


def test_export_module_ast_safety() -> None:
    import basketball_sim.export.tactics_summary_readonly as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "save_world" not in src
    assert "get_safe_team_tactics" not in src
    assert "ensure_team_tactics_on_team" not in src
    assert "MainMenuView" not in src
    assert "tkinter" not in src.lower()
    assert "team.team_tactics =" not in src

    tree = ast.parse(src)
    banned = {"save_world", "get_safe_team_tactics", "ensure_team_tactics_on_team"}
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned:
                bad.append(node.func.id)
    assert bad == []


def test_export_module_no_subscript_assign_on_team_tactics() -> None:
    import basketball_sim.export.tactics_summary_readonly as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "team.team_tactics[" not in src
