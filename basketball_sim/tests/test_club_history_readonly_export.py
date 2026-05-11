from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from basketball_sim.export.club_history_readonly import (
    build_club_history_readonly_dict,
    export_club_history_json_from_world,
    write_club_history_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world


REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "sections",
    "season_rows",
    "events",
    "notes",
)

REQUIRED_SUMMARY_KEYS = (
    "founded_label",
    "seasons_recorded",
    "titles_count",
    "promotions_count",
    "relegations_count",
    "history_events_count",
)


def test_build_has_required_keys_and_list_types() -> None:
    team = Team(team_id=1, name="テストFC", league_level=2, players=[])
    d = build_club_history_readonly_dict(team)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    for k in REQUIRED_SUMMARY_KEYS:
        assert k in d["summary"]
    assert isinstance(d["sections"], list)
    assert isinstance(d["season_rows"], list)
    assert isinstance(d["events"], list)
    assert isinstance(d["notes"], list)


def test_team_none_does_not_crash() -> None:
    d = build_club_history_readonly_dict(None)
    assert d["team_name"] == "自クラブ"
    assert d["season_rows"] == []
    assert d["events"] == []


def test_empty_histories_does_not_crash() -> None:
    team = Team(team_id=1, name="新興クラブ", league_level=1, players=[])
    d = build_club_history_readonly_dict(team)
    assert d["summary"]["seasons_recorded"] == 0
    assert d["season_rows"] == []


def test_utf8_json_write(tmp_path: Path) -> None:
    team = Team(team_id=1, name="日本語クラブ史", league_level=1, players=[])
    d = build_club_history_readonly_dict(team)
    out = tmp_path / "club_history.json"
    write_club_history_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ史" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ史"


def test_max_events_limits_events() -> None:
    milestones = [{"season": 1, "title": f"イベント{i}", "detail": ""} for i in range(30)]
    team = SimpleNamespace(
        name="M",
        league_level=1,
        history_seasons=[],
        history_milestones=milestones,
        history_transactions=[],
        finance_history=[],
    )
    d = build_club_history_readonly_dict(team, max_events=3)
    assert len(d["events"]) <= 3
    assert d["summary"]["history_events_count"] == len(d["events"])


def test_simple_namespace_without_club_history_methods() -> None:
    """get_club_history_report_text を持たないオブジェクトでも落ちない。"""
    team = SimpleNamespace(
        name="簡易チーム",
        league_level=3,
        history_seasons=[],
        history_milestones=[],
        history_transactions=[],
        finance_history=[],
    )
    d = build_club_history_readonly_dict(team)
    assert d["team_name"] == "簡易チーム"
    assert d["league_level"] == 3


def test_season_rows_and_milestone_summary() -> None:
    team = Team(team_id=7, name="歴史FC", league_level=2, players=[])
    team.history_seasons = [
        {
            "season_index": 1,
            "league_level": 2,
            "regular_wins": 30,
            "regular_losses": 20,
            "rank": 3,
            "note": "昇格ならず",
        }
    ]
    team.history_milestones = [
        {"title": "天皇杯 優勝", "detail": "初タイトル", "note": ""},
        {"title": "昇格達成", "milestone_type": "promotion", "note": ""},
    ]
    d = build_club_history_readonly_dict(team)
    assert d["summary"]["seasons_recorded"] == 1
    assert d["summary"]["titles_count"] >= 1
    assert d["summary"]["promotions_count"] >= 1
    assert len(d["season_rows"]) == 1
    assert "30勝20敗" in d["season_rows"][0]["record"]
    assert d["season_rows"][0]["division"] == "D2"


def test_export_club_history_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1, players=[])
    team.history_seasons = [{"season_index": 1, "league_level": 1, "regular_wins": 1, "regular_losses": 1, "rank": 5}]
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 42,
        "season_count": 2,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "club_history_from_py.json"
    snap = export_club_history_json_from_world(sav, out)
    assert out.is_file()
    assert snap["team_name"] == "セーブ出口FC"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["screen_title"] == "クラブ史（閲覧）"
    assert len(body["season_rows"]) >= 1
