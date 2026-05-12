from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.owner_mission_readonly import (
    SCREEN_TITLE,
    build_owner_mission_readonly_dict,
    export_owner_mission_json_from_world,
    write_owner_mission_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "mission_items",
    "evaluation_items",
    "sections",
    "notes",
)


def test_build_owner_mission_required_top_keys() -> None:
    d = build_owner_mission_readonly_dict(None)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["screen_title"] == SCREEN_TITLE
    assert d["screen_title"] == "オーナーミッション（閲覧）"


def test_build_owner_mission_team_none() -> None:
    d = build_owner_mission_readonly_dict(None, season_count=1, at_annual_menu=False)
    assert d["team_name"] == "-"
    assert d["league_level"] is None
    assert d["mission_items"] == []
    assert d["summary"]["owner_trust"] is None
    assert d["summary"]["has_owner_missions"] is False
    joined = "\n".join(d["notes"])
    assert "チーム情報が未接続" in joined


def test_owner_trust_int_and_rank() -> None:
    team = SimpleNamespace(
        name="信頼FC",
        league_level=1,
        owner_trust=72,
        owner_expectation="playoff_race",
        owner_missions=[],
        owner_mission=None,
    )
    d = build_owner_mission_readonly_dict(team)
    assert d["summary"]["owner_trust"] == 72
    assert d["summary"]["owner_trust_rank"] == "高い"
    assert "72" in str(d["summary"]["owner_trust_label"])


def test_owner_missions_list_dict() -> None:
    team = SimpleNamespace(
        name="MFC",
        league_level=2,
        owner_trust=50,
        owner_expectation="rebuild",
        owner_mission=None,
        owner_missions=[
            {
                "mission_id": "wins_target",
                "title": "15勝以上",
                "category": "results",
                "status": "active",
                "target_value": 15,
                "progress_text": "3勝 / 目標15勝",
                "reward_trust": 6,
                "penalty_trust": -7,
            },
            {
                "mission_id": "rank_target",
                "title": "8位以内",
                "status": "success",
                "target_value": 8,
                "progress_text": "5位 / 目標8位以内",
            },
        ],
    )
    d = build_owner_mission_readonly_dict(team, max_missions=8)
    assert len(d["mission_items"]) == 2
    assert d["mission_items"][0]["status"] == "active"
    assert d["mission_items"][0]["status_label"] == "進行中"
    assert d["mission_items"][1]["status_label"] == "達成"
    assert d["summary"]["mission_count"] == 2
    assert d["summary"]["active_mission_count"] >= 1


def test_owner_missions_object_list() -> None:
    class M:
        def __init__(self) -> None:
            self.mission_id = "x1"
            self.title = "オブジェクト行"
            self.category = "results"
            self.status = "FAILED"
            self.target_value = 10
            self.progress = 2
            self.progress_text = ""
            self.reward_trust = 1
            self.penalty_trust = -2
            self.description = "desc"

    team = SimpleNamespace(
        name="Obj",
        league_level=1,
        owner_trust=40,
        owner_expectation="playoff_race",
        owner_missions=[M()],
        owner_mission=None,
    )
    d = build_owner_mission_readonly_dict(team)
    assert len(d["mission_items"]) == 1
    assert d["mission_items"][0]["title"] == "オブジェクト行"
    assert str(d["mission_items"][0]["status"]).lower() == "failed"
    assert d["mission_items"][0]["status_label"] == "未達"


def test_owner_missions_dict_single_mission_shape() -> None:
    team = SimpleNamespace(
        name="DictFC",
        league_level=3,
        owner_trust=30,
        owner_expectation="promotion",
        owner_mission=None,
        owner_missions={
            "mission_id": "solo",
            "title": "単体dict",
            "status": "pending",
            "category": "finance",
            "target_value": 0,
        },
    )
    d = build_owner_mission_readonly_dict(team)
    assert len(d["mission_items"]) == 1
    assert d["mission_items"][0]["title"] == "単体dict"
    assert d["mission_items"][0]["status_label"] == "保留"


def test_max_missions_limits_items_not_counts() -> None:
    missions = [
        {"mission_id": f"m{i}", "title": f"T{i}", "status": "active", "target_value": i}
        for i in range(10)
    ]
    team = SimpleNamespace(
        name="Many",
        league_level=1,
        owner_trust=50,
        owner_expectation="playoff_race",
        owner_missions=missions,
        owner_mission=None,
    )
    d = build_owner_mission_readonly_dict(team, max_missions=2)
    assert d["summary"]["mission_count"] == 10
    assert len(d["mission_items"]) == 2
    assert d["mission_items"][0]["order"] == 1
    assert d["mission_items"][1]["order"] == 2


def test_invalid_values_do_not_crash() -> None:
    team = SimpleNamespace(
        name="Bad",
        league_level="z",
        owner_trust="not-a-number",
        owner_expectation=None,
        owner_missions="not-list",
        owner_mission=None,
    )
    d = build_owner_mission_readonly_dict(team)
    assert d["team_name"] == "Bad"
    assert d["league_level"] is None
    assert d["mission_items"] == []


def test_write_owner_mission_json_utf8(tmp_path: Path) -> None:
    team = Team(team_id=1, name="日本語クラブ", league_level=1)
    team.owner_trust = 55
    team.owner_missions = []
    d = build_owner_mission_readonly_dict(team)
    out = tmp_path / "om.json"
    write_owner_mission_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"


def test_export_owner_mission_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=9, name="出口オーナーFC", league_level=1)
    team.owner_trust = 61
    team.owner_missions = [
        {
            "mission_id": "a",
            "title": "ミッションA",
            "category": "results",
            "status": "active",
            "target_value": 1,
            "progress_text": "進捗",
        }
    ]
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 9,
        "season_count": 4,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "om_out.json"
    snap = export_owner_mission_json_from_world(sav, out, max_missions=8)
    assert out.is_file()
    assert snap["team_name"] == "出口オーナーFC"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["summary"]["season_count"] == 4
    assert body["summary"]["at_annual_menu"] is True
    assert len(body["mission_items"]) == 1


def test_sections_structure() -> None:
    d = build_owner_mission_readonly_dict(None)
    titles = [s["title"] for s in d["sections"]]
    assert "オーナー信頼" in titles
    assert "今季ミッション" in titles
    assert "クラブ評価" in titles
    assert "注意" in titles
    for sec in d["sections"]:
        assert "lines" in sec
        assert isinstance(sec["lines"], list)


def test_legacy_owner_mission_string_when_list_empty() -> None:
    team = SimpleNamespace(
        name="Leg",
        league_level=1,
        owner_trust=50,
        owner_expectation="playoff_race",
        owner_missions=[],
        owner_mission="  PO進出を目指す  ",
    )
    d = build_owner_mission_readonly_dict(team)
    assert len(d["mission_items"]) == 1
    assert "PO進出" in d["mission_items"][0]["title"]


def test_export_module_ast_safety() -> None:
    import basketball_sim.export.owner_mission_readonly as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "save_world" not in src
    assert "record_financial_result" not in src
    assert "main_menu_view" not in src.lower()
    assert "tkinter" not in src.lower()
    assert "ensure_team_tactics" not in src
    assert "owner_missions.append" not in src
    assert "refresh_owner_missions" not in src
    assert "evaluate_owner_missions" not in src

    tree = ast.parse(src)
    banned_calls = {"save_world", "record_financial_result"}
    bad: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned_calls:
                bad.append(node.func.id)
    assert bad == []
