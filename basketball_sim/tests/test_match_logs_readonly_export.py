"""Tests for basketball_sim.export.match_logs_readonly."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.match_logs_readonly import (
    SCREEN_TITLE,
    _MSG_NO_LOGS,
    _MSG_NO_SEASON,
    build_match_logs_readonly_dict,
    export_match_logs_json_from_world,
    write_match_logs_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import normalize_payload, save_world

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "season_label",
    "summary",
    "match_logs",
    "empty_message",
    "notes",
)

ENTRY_REQUIRED_KEYS = (
    "match_id",
    "event_id",
    "round",
    "competition_type",
    "stage",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "user_team",
    "user_result",
    "summary_line",
    "commentary_excerpt",
    "key_plays",
    "captured_at",
)


def _team(name: str = "テストFC") -> SimpleNamespace:
    return SimpleNamespace(name=name, league_level=1)


def _season(*, match_logs=None, current_round=3, total_rounds=33) -> SimpleNamespace:
    return SimpleNamespace(
        current_round=current_round,
        total_rounds=total_rounds,
        match_logs=list(match_logs or []),
    )


def _sample_log(
    *,
    match_id: str = "evt-1",
    round_no: int = 1,
    summary_line: str = "○ テストFC 80 - 70 Opponent",
    user_result: str = "W",
) -> dict:
    return {
        "match_id": match_id,
        "event_id": match_id,
        "round": round_no,
        "competition_type": "regular_season",
        "stage": "regular_season",
        "week": round_no,
        "day_of_week": "Sat",
        "home_team": "テストFC",
        "away_team": "Opponent",
        "home_score": 80,
        "away_score": 70,
        "user_team_involved": True,
        "user_team": "テストFC",
        "user_result": user_result,
        "summary_line": summary_line,
        "commentary_excerpt": {
            "head": ["h1"],
            "tail": ["t1"],
            "total_lines": 100,
        },
        "key_plays": [
            {
                "play_no": 1,
                "quarter": 4,
                "result_type": "made_2",
                "commentary_text": "score",
                "home_score": 80,
                "away_score": 70,
            }
        ],
        "captured_at": "simulate_next_round",
    }


def test_build_required_top_keys() -> None:
    d = build_match_logs_readonly_dict(None, _team())
    for key in REQUIRED_TOP_KEYS:
        assert key in d
    assert d["screen_title"] == SCREEN_TITLE
    assert isinstance(d["summary"], dict)
    assert isinstance(d["match_logs"], list)
    assert isinstance(d["notes"], list)


def test_no_season_empty_payload() -> None:
    d = build_match_logs_readonly_dict(None, _team(), season_count=2, at_annual_menu=True)
    assert d["summary"]["has_season"] is False
    assert d["summary"]["has_logs"] is False
    assert d["match_logs"] == []
    assert d["empty_message"] == _MSG_NO_SEASON


def test_season_without_logs_empty_payload() -> None:
    season = _season(match_logs=[], current_round=5, total_rounds=33)
    d = build_match_logs_readonly_dict(season, _team(), season_count=1)
    assert d["summary"]["has_season"] is True
    assert d["summary"]["has_logs"] is False
    assert d["summary"]["count"] == 0
    assert d["summary"]["exported_count"] == 0
    assert d["summary"]["current_round"] == 5
    assert d["summary"]["total_rounds"] == 33
    assert d["match_logs"] == []
    assert d["empty_message"] == _MSG_NO_LOGS


def test_with_logs_preserves_summary_fields() -> None:
    logs = [_sample_log(match_id="a", round_no=1), _sample_log(match_id="b", round_no=2)]
    season = _season(match_logs=logs, current_round=2, total_rounds=33)
    d = build_match_logs_readonly_dict(season, _team())
    assert d["summary"]["has_logs"] is True
    assert d["summary"]["count"] == 2
    assert d["summary"]["exported_count"] == 2
    assert d["summary"]["latest_round"] == 2
    assert d["empty_message"] == ""
    assert len(d["match_logs"]) == 2
    for key in ENTRY_REQUIRED_KEYS:
        assert key in d["match_logs"][0]
    assert d["match_logs"][0]["summary_line"].startswith("○")
    assert d["match_logs"][0]["user_result"] == "W"


def test_max_logs_limits_tail_and_counts() -> None:
    logs = [
        _sample_log(match_id="r1", round_no=1),
        _sample_log(match_id="r2", round_no=2),
        _sample_log(match_id="r3", round_no=3),
    ]
    season = _season(match_logs=logs)
    d = build_match_logs_readonly_dict(season, _team(), max_logs=1)
    assert d["summary"]["count"] == 3
    assert d["summary"]["exported_count"] == 1
    assert d["summary"]["latest_round"] == 3
    assert len(d["match_logs"]) == 1
    assert d["match_logs"][0]["match_id"] == "r3"


def test_max_logs_invalid_falls_back_to_default() -> None:
    logs = [_sample_log(match_id=f"r{i}", round_no=i) for i in range(1, 4)]
    season = _season(match_logs=logs)
    d = build_match_logs_readonly_dict(season, _team(), max_logs=0)
    assert d["summary"]["exported_count"] == 3


def test_commentary_excerpt_missing_normalized() -> None:
    raw = _sample_log()
    del raw["commentary_excerpt"]
    season = _season(match_logs=[raw])
    entry = build_match_logs_readonly_dict(season, _team())["match_logs"][0]
    assert entry["commentary_excerpt"] == {"head": [], "tail": [], "total_lines": 0}


def test_commentary_excerpt_broken_normalized() -> None:
    raw = _sample_log()
    raw["commentary_excerpt"] = "broken"
    season = _season(match_logs=[raw])
    entry = build_match_logs_readonly_dict(season, _team())["match_logs"][0]
    assert entry["commentary_excerpt"]["head"] == []
    assert entry["commentary_excerpt"]["tail"] == []
    assert entry["commentary_excerpt"]["total_lines"] == 0


def test_key_plays_sanitize_events_and_objects() -> None:
    raw = _sample_log()
    raw["key_plays"] = [
        {
            "play_no": 1,
            "quarter": 1,
            "result_type": "made_2",
            "commentary_text": "ok",
            "events": [{"nested": True}],
            "bad_obj": object(),
        },
        "not-a-dict",
        {
            "play_no": 2,
            "quarter": 2,
            "result_type": "miss",
            "commentary_text": "ok2",
        },
    ]
    season = _season(match_logs=[raw])
    entry = build_match_logs_readonly_dict(season, _team())["match_logs"][0]
    assert json.dumps(entry["key_plays"], ensure_ascii=False)
    for play in entry["key_plays"]:
        assert "events" not in play
        assert "bad_obj" not in play


def test_key_plays_capped_at_eight_on_export() -> None:
    raw = _sample_log()
    raw["key_plays"] = [{"play_no": i, "quarter": 1, "result_type": "x"} for i in range(1, 12)]
    season = _season(match_logs=[raw])
    entry = build_match_logs_readonly_dict(season, _team())["match_logs"][0]
    assert len(entry["key_plays"]) == 8
    assert entry["key_plays"][0]["play_no"] == 4
    assert entry["key_plays"][-1]["play_no"] == 11


def test_write_match_logs_json_utf8_and_trailing_newline(tmp_path: Path) -> None:
    season = _season(match_logs=[_sample_log()])
    snap = build_match_logs_readonly_dict(season, _team(name="日本語クラブ"))
    out = tmp_path / "match_logs.json"
    write_match_logs_json(snap, out)
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"


def test_export_match_logs_json_from_world_with_logs(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1)
    team.players = []
    season = _season(match_logs=[_sample_log()], current_round=6, total_rounds=33)
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 42,
        "season_count": 1,
        "at_annual_menu": False,
        "tracked_player_name": None,
        "resume_season": season,
    }
    save_world(sav, payload)
    out = tmp_path / "from_py.json"
    snap = export_match_logs_json_from_world(sav, out, max_logs=50)
    assert out.is_file()
    assert snap["summary"]["has_logs"] is True
    assert snap["summary"]["count"] == 1
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["screen_title"] == SCREEN_TITLE
    assert len(body["match_logs"]) == 1


def test_export_old_save_without_match_logs_attribute(tmp_path: Path) -> None:
    sav = tmp_path / "old.sav"
    team = Team(team_id=1, name="OldFC", league_level=1)
    team.players = []
    season = SimpleNamespace(current_round=1, total_rounds=33)
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 1,
        "season_count": 1,
        "at_annual_menu": False,
        "tracked_player_name": None,
        "resume_season": season,
    }
    save_world(sav, payload)
    loaded = normalize_payload(
        {
            "teams": payload["teams"],
            "free_agents": [],
            "user_team_id": 1,
            "season_count": 1,
            "at_annual_menu": False,
            "tracked_player_name": None,
            "resume_season": season,
        }
    )
    assert loaded["resume_season"].match_logs == []
    out = tmp_path / "out.json"
    snap = export_match_logs_json_from_world(sav, out)
    assert snap["summary"]["count"] == 0
    assert snap["empty_message"] == _MSG_NO_LOGS


def test_export_annual_menu_no_season(tmp_path: Path) -> None:
    sav = tmp_path / "annual.sav"
    team = Team(team_id=7, name="AnnualFC", league_level=2)
    team.players = []
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 7,
        "season_count": 4,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    snap = export_match_logs_json_from_world(sav, tmp_path / "m.json")
    assert snap["summary"]["has_season"] is False
    assert snap["empty_message"] == _MSG_NO_SEASON
