from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.facility_summary_readonly import (
    build_facility_summary_readonly_dict,
    export_facility_summary_json_from_world,
    write_facility_summary_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "facilities",
    "sections",
    "notes",
)

FACILITY_KEYS = ("arena", "training", "medical", "front_office")
FACILITY_ROW_KEYS = ("key", "label", "level", "max_level", "level_label", "effect_hint")


def test_build_facility_summary_team_none() -> None:
    d = build_facility_summary_readonly_dict(None)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["team_name"] == "自クラブ"
    assert d["league_level"] is None
    assert isinstance(d["summary"], dict)
    assert isinstance(d["facilities"], list)
    assert isinstance(d["sections"], list)
    assert isinstance(d["notes"], list)
    assert len(d["facilities"]) == 4
    assert "未接続" in "".join(d["notes"])


def test_build_facility_summary_required_facility_rows() -> None:
    team = Team(team_id=1, name="テストFC", league_level=2)
    team.arena_level = 3
    team.training_facility_level = 4
    team.medical_facility_level = 2
    team.front_office_level = 5
    team.facility_upgrade_points = 12
    d = build_facility_summary_readonly_dict(team)
    assert d["team_name"] == "テストFC"
    assert d["league_level"] == 2
    assert d["summary"]["facility_upgrade_points"] == 12
    assert d["summary"]["facility_count"] == 4
    assert d["summary"]["max_level"] == 10
    keys = [f["key"] for f in d["facilities"]]
    assert keys == list(FACILITY_KEYS)
    for f in d["facilities"]:
        for col in FACILITY_ROW_KEYS:
            assert col in f
        assert f["max_level"] == 10
        assert "Lv." in f["level_label"]


def test_levels_clamped_and_average() -> None:
    team = SimpleNamespace(
        name="Clamp",
        league_level=1,
        arena_level=0,
        training_facility_level=99,
        medical_facility_level="5",
        front_office_level=None,
        facility_upgrade_points=7,
    )
    d = build_facility_summary_readonly_dict(team)
    assert d["facilities"][0]["level"] == 1
    assert d["facilities"][1]["level"] == 10
    assert d["facilities"][2]["level"] == 5
    assert d["facilities"][3]["level"] == 1
    assert d["summary"]["average_level"] == 4.2


def test_facility_upgrade_points_invalid_becomes_zero() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
        facility_upgrade_points="not-a-number",
    )
    d = build_facility_summary_readonly_dict(team)
    assert d["summary"]["facility_upgrade_points"] == 0


def test_facility_upgrade_points_negative_clamped_to_zero() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
        facility_upgrade_points=-5,
    )
    d = build_facility_summary_readonly_dict(team)
    assert d["summary"]["facility_upgrade_points"] == 0


def test_write_facility_summary_json_utf8(tmp_path: Path) -> None:
    team = Team(team_id=1, name="日本語クラブ", league_level=1)
    d = build_facility_summary_readonly_dict(team)
    out = tmp_path / "fac.json"
    write_facility_summary_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"


def test_export_facility_summary_json_from_world_minimal_save_no_season(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="施設出口FC", league_level=1)
    team.arena_level = 2
    team.training_facility_level = 3
    team.medical_facility_level = 1
    team.front_office_level = 4
    team.facility_upgrade_points = 100
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 42,
        "season_count": 1,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "from_py.json"
    snap = export_facility_summary_json_from_world(sav, out)
    assert out.is_file()
    assert snap["team_name"] == "施設出口FC"
    assert snap["summary"]["facility_upgrade_points"] == 100
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["facilities"][0]["level"] == 2
    assert body["facilities"][1]["level"] == 3


def test_sections_structure() -> None:
    team = Team(team_id=1, name="S", league_level=1)
    d = build_facility_summary_readonly_dict(team)
    assert len(d["sections"]) >= 3
    for sec in d["sections"]:
        assert "title" in sec
        assert "lines" in sec
        assert isinstance(sec["lines"], list)


def test_export_module_does_not_import_save_world() -> None:
    import basketball_sim.export.facility_summary_readonly as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "save_world" not in src
