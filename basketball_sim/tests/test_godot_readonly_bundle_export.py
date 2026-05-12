"""Tests for basketball_sim.export.godot_readonly_bundle."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from basketball_sim.export import godot_readonly_bundle
from basketball_sim.export.godot_readonly_bundle import export_godot_readonly_bundle
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world


EXPECTED_JSON_NAMES: List[str] = [
    "home_dashboard_from_python.json",
    "roster_from_python.json",
    "club_history_from_python.json",
    "standings_from_python.json",
    "schedule_from_python.json",
    "facility_summary_from_python.json",
    "finance_summary_from_python.json",
    "owner_mission_from_python.json",
    "tactics_summary_from_python.json",
]


def _minimal_save(path: Path) -> None:
    team = Team(team_id=42, name="日本語バンドルFC", league_level=1)
    team.money = 1000
    team.regular_wins = 0
    team.regular_losses = 0
    team.owner_trust = 50.0
    team.players = []
    team.facility_upgrade_points = 0
    team.fa_shortlist = []
    payload: Dict[str, Any] = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 42,
        "season_count": 1,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(path, payload)


def test_expected_output_filenames_list() -> None:
    assert len(EXPECTED_JSON_NAMES) == 9
    assert "home_dashboard_from_python.json" in EXPECTED_JSON_NAMES
    assert "tactics_summary_from_python.json" in EXPECTED_JSON_NAMES


def test_bundle_result_contains_output_paths(tmp_path: Path) -> None:
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "out"
    _minimal_save(sav)
    result = export_godot_readonly_bundle(sav, out_dir)
    assert result["success_count"] == 9
    assert result["failed_count"] == 0
    assert Path(result["output_dir"]) == out_dir.resolve()
    keys = {e["key"] for e in result["succeeded"]}
    assert keys == {
        "home_dashboard",
        "roster",
        "club_history",
        "standings",
        "schedule",
        "facility_summary",
        "finance_summary",
        "owner_mission",
        "tactics_summary",
    }
    for name in EXPECTED_JSON_NAMES:
        assert (out_dir / name).is_file()


def test_bundle_writes_nine_json_files_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "godot_data"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, out_dir)
    for name in EXPECTED_JSON_NAMES:
        p = out_dir / name
        assert p.is_file()
        text = p.read_text(encoding="utf-8")
        assert "日本語" in text or name != "home_dashboard_from_python.json"
        data = json.loads(text)
        assert isinstance(data, dict)


def test_top_level_dict_each_output(tmp_path: Path) -> None:
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "out2"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, out_dir)
    for name in EXPECTED_JSON_NAMES:
        assert isinstance(json.loads((out_dir / name).read_text(encoding="utf-8")), dict)


def test_max_history_passed_to_finance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: Dict[str, Any] = {}

    real_fn = godot_readonly_bundle.export_finance_summary_json_from_world

    def _wrap(save: Path | str, op: Path | str, *, max_history: int = 5) -> Dict[str, Any]:
        captured["max_history"] = max_history
        return real_fn(save, op, max_history=max_history)

    monkeypatch.setattr(godot_readonly_bundle, "export_finance_summary_json_from_world", _wrap)
    sav = tmp_path / "m.sav"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, tmp_path / "out3", max_history=3)
    assert captured.get("max_history") == 3


def test_fail_fast_stops_after_first_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: List[str] = []

    def _boom_roster(save: Path | str, output_path: Path | str) -> Dict[str, Any]:
        calls.append("roster")
        raise RuntimeError("roster boom")

    monkeypatch.setattr(godot_readonly_bundle, "export_roster_json_from_world", _boom_roster)
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "ff"
    _minimal_save(sav)
    result = export_godot_readonly_bundle(sav, out_dir, continue_on_error=False)
    assert result["failed_count"] == 1
    assert result["success_count"] == 1  # home only
    assert result["failed"][0]["key"] == "roster"
    assert "home_dashboard_from_python.json" in result["succeeded"][0]["output"]
    assert not (out_dir / "club_history_from_python.json").exists()


def test_continue_on_error_records_and_continues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom_roster(save: Path | str, output_path: Path | str) -> Dict[str, Any]:
        raise RuntimeError("roster fail")

    monkeypatch.setattr(godot_readonly_bundle, "export_roster_json_from_world", _boom_roster)
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "coe"
    _minimal_save(sav)
    result = export_godot_readonly_bundle(sav, out_dir, continue_on_error=True)
    assert result["failed_count"] == 1
    assert result["success_count"] == 8
    assert (out_dir / "tactics_summary_from_python.json").is_file()
    assert not (out_dir / "roster_from_python.json").exists()


def test_output_dir_created_when_missing(tmp_path: Path) -> None:
    sav = tmp_path / "m.sav"
    nested = tmp_path / "a" / "b" / "c"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, nested)
    assert nested.is_dir()
    assert (nested / "home_dashboard_from_python.json").is_file()


def test_cli_main_prints_wrote_and_bundle_complete(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "cliout"
    _minimal_save(sav)
    code = godot_readonly_bundle._cli_main(
        [
            "--save",
            str(sav),
            "--output-dir",
            str(out_dir),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Wrote" in out
    assert "Bundle complete: 9 succeeded, 0 failed" in out


def test_cli_nonzero_when_bundle_has_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        godot_readonly_bundle,
        "export_standings_json_from_world",
        lambda s, o: (_ for _ in ()).throw(ValueError("standings x")),
    )
    sav = tmp_path / "m.sav"
    out_dir = tmp_path / "bad"
    _minimal_save(sav)
    code = godot_readonly_bundle._cli_main(["--save", str(sav), "--output-dir", str(out_dir), "--continue-on-error"])
    assert code == 1


def test_bundle_module_has_no_forbidden_import_patterns() -> None:
    here = Path(__file__).resolve()
    bundle_py = here.parents[1] / "export" / "godot_readonly_bundle.py"
    text = bundle_py.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "save_world" not in text
    assert "mainmenuview" not in lowered
    assert "tkinter" not in lowered
    assert "ensure_team_tactics_on_team" not in text
    assert "get_safe_team_tactics" not in text


def test_module_runnable_as_py_m() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "basketball_sim.export.godot_readonly_bundle", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "godot_readonly_bundle" in proc.stdout or "--save" in proc.stdout


def test_max_upcoming_schedule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: Dict[str, Any] = {}

    real = godot_readonly_bundle.export_schedule_json_from_world

    def _wrap(save: Path | str, op: Path | str, *, max_upcoming: int = 8) -> Dict[str, Any]:
        seen["max_upcoming"] = max_upcoming
        return real(save, op, max_upcoming=max_upcoming)

    monkeypatch.setattr(godot_readonly_bundle, "export_schedule_json_from_world", _wrap)
    sav = tmp_path / "m.sav"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, tmp_path / "schedout", max_upcoming=2)
    assert seen.get("max_upcoming") == 2


def test_max_missions_and_max_players_passed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    m_m: Dict[str, Any] = {}
    m_p: Dict[str, Any] = {}

    real_o = godot_readonly_bundle.export_owner_mission_json_from_world
    real_t = godot_readonly_bundle.export_tactics_summary_json_from_world

    def _wo(save: Path | str, op: Path | str, *, max_missions: int = 8) -> Dict[str, Any]:
        m_m["v"] = max_missions
        return real_o(save, op, max_missions=max_missions)

    def _wt(save: Path | str, op: Path | str, *, max_players: int = 8) -> Dict[str, Any]:
        m_p["v"] = max_players
        return real_t(save, op, max_players=max_players)

    monkeypatch.setattr(godot_readonly_bundle, "export_owner_mission_json_from_world", _wo)
    monkeypatch.setattr(godot_readonly_bundle, "export_tactics_summary_json_from_world", _wt)
    sav = tmp_path / "m.sav"
    _minimal_save(sav)
    export_godot_readonly_bundle(sav, tmp_path / "mpout", max_missions=3, max_players=4)
    assert m_m.get("v") == 3
    assert m_p.get("v") == 4
