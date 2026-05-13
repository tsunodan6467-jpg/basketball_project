from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import basketball_sim.export.contract_personnel_summary_readonly as cps_mod
from basketball_sim.export.contract_personnel_summary_readonly import (
    build_contract_personnel_summary_readonly_dict,
    export_contract_personnel_summary_json_from_world,
    write_contract_personnel_summary_json,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "contract_items",
    "risk_items",
    "player_contract_rows",
    "roster_balance_items",
    "sections",
    "notes",
)


def _player(
    pid: int,
    *,
    name: str,
    position: str,
    ovr: int,
    age: int = 24,
    nationality: str = "Japan",
    salary: int = 5_000_000,
    contract_years_left: int = 2,
) -> Player:
    return Player(
        player_id=pid,
        name=name,
        age=age,
        nationality=nationality,
        position=position,
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=contract_years_left,
        contract_total_years=2,
        team_id=1,
        fatigue=0,
        injury_games_left=0,
    )


def test_build_contract_personnel_summary_required_top_keys() -> None:
    d = build_contract_personnel_summary_readonly_dict(None)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["screen_title"] == "契約・人事サマリー（閲覧）"


def test_build_contract_personnel_summary_team_none_safe() -> None:
    d = build_contract_personnel_summary_readonly_dict(None)
    assert d["team_name"] == "-"
    assert d["league_level"] is None
    assert d["player_contract_rows"] == []
    assert d["roster_balance_items"] == []
    assert isinstance(d["sections"], list)
    assert any("未接続" in n for n in d["notes"])


def test_reads_player_salary_and_contract_years() -> None:
    p = _player(1, name="A", position="PG", ovr=70, salary=12_000_000, contract_years_left=3)
    team = Team(team_id=1, name="読取FC", league_level=1, players=[p])
    d = build_contract_personnel_summary_readonly_dict(team, max_players=8)
    assert d["summary"]["has_salary_data"] is True
    assert d["summary"]["has_contract_data"] is True
    row = d["player_contract_rows"][0]
    assert row["salary"] == 12_000_000
    assert row["contract_years"] == 3


def test_missing_salary_does_not_crash() -> None:
    p = SimpleNamespace(
        name="安い",
        position="SG",
        age=25,
        ovr=60,
        potential="B",
        salary=None,
        contract_years_left=1,
        nationality="Japan",
        injury_games_left=0,
    )
    team = SimpleNamespace(name="NS", league_level=1, players=[p], fa_shortlist=None)
    d = build_contract_personnel_summary_readonly_dict(team)
    assert d["player_contract_rows"][0]["salary"] is None
    assert d["player_contract_rows"][0]["salary_label"] == "-"


def test_missing_contract_years_does_not_crash() -> None:
    p = SimpleNamespace(
        name="無期限風",
        position="PF",
        age=28,
        ovr=55,
        potential="C",
        salary=8_000_000,
        contract_years_left=None,
        nationality="USA",
        injury_games_left=0,
    )
    team = SimpleNamespace(name="NS2", league_level=2, players=[p], fa_shortlist=[])
    d = build_contract_personnel_summary_readonly_dict(team)
    assert d["player_contract_rows"][0]["contract_years"] is None
    assert d["player_contract_rows"][0]["contract_status"] == "unknown"
    assert "契約データ" in "".join(d["notes"]) or d["summary"]["has_contract_data"] is False


def test_max_players_limits_rows() -> None:
    players = [_player(i, name=f"P{i}", position="C", ovr=50 + i, salary=1_000_000 * i) for i in range(1, 11)]
    team = Team(team_id=1, name="多人数", league_level=1, players=players)
    d = build_contract_personnel_summary_readonly_dict(team, max_players=3)
    assert len(d["player_contract_rows"]) == 3


def test_order_by_salary_desc_when_salaries_present() -> None:
    low = _player(1, name="低", position="C", ovr=90, salary=1_000_000)
    high = _player(2, name="高", position="C", ovr=50, salary=50_000_000)
    mid = _player(3, name="中", position="C", ovr=70, salary=10_000_000)
    team = Team(team_id=1, name="順序", league_level=1, players=[low, high, mid])
    d = build_contract_personnel_summary_readonly_dict(team, max_players=8)
    names = [r["player_name"] for r in d["player_contract_rows"]]
    assert names[0] == "高"
    assert names[1] == "中"
    assert names[2] == "低"


def test_roster_balance_includes_position_counts() -> None:
    team = Team(
        team_id=1,
        name="Pos",
        league_level=1,
        players=[
            _player(1, name="a", position="PG", ovr=50),
            _player(2, name="b", position="PG", ovr=51),
            _player(3, name="c", position="C", ovr=52),
        ],
    )
    d = build_contract_personnel_summary_readonly_dict(team)
    by_key = {it["key"]: it["value"] for it in d["roster_balance_items"]}
    assert by_key.get("pg_count") == 2
    assert by_key.get("c_count") == 1


def test_risk_items_present_with_roster() -> None:
    p = _player(1, name="X", position="SF", ovr=60, salary=5_000_000, contract_years_left=1)
    team = Team(team_id=1, name="R", league_level=1, players=[p])
    d = build_contract_personnel_summary_readonly_dict(team)
    assert len(d["risk_items"]) >= 5
    keys = {it["key"] for it in d["risk_items"]}
    assert "expiring_contract_risk" in keys


def test_write_json_utf8_no_ascii_escape(tmp_path: Path) -> None:
    team = Team(
        team_id=1,
        name="日本語クラブ",
        league_level=1,
        players=[_player(1, name="契約太郎", position="PG", ovr=66)],
    )
    d = build_contract_personnel_summary_readonly_dict(team)
    out = tmp_path / "cps.json"
    write_contract_personnel_summary_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    assert "\\u" not in text or "契約太郎" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"


def test_export_from_world_minimal_save(tmp_path: Path) -> None:
    from basketball_sim.persistence.save_load import save_world

    sav = tmp_path / "minimal.sav"
    team = Team(team_id=7, name="Roundtrip FC", league_level=1)
    payload_in = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 7,
        "season_count": 2,
        "at_annual_menu": True,
        "tracked_player_name": None,
    }
    save_world(sav, payload_in)
    out = tmp_path / "cps_out.json"
    d = export_contract_personnel_summary_json_from_world(sav, out, max_players=8)
    assert out.is_file()
    assert d["team_name"] == "Roundtrip FC"
    assert d["summary"]["season_count"] == 2
    assert d["summary"]["at_annual_menu"] is True


def test_sections_structure() -> None:
    d = build_contract_personnel_summary_readonly_dict(None)
    titles = [s["title"] for s in d["sections"]]
    assert titles == ["契約概要", "人事リスク", "主要契約選手", "ロスター構成", "注意"]
    for s in d["sections"]:
        assert isinstance(s["lines"], list)
        assert all(isinstance(line, str) for line in s["lines"])


def test_export_module_ast_has_no_forbidden_calls() -> None:
    src = Path(cps_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned_call_roots = {
        "save_world",
        "renew_contract",
        "sign_player",
        "release_player",
        "generate_fa",
        "ensure_fa",
        "refresh_fa",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in banned_call_roots:
                pytest.fail(f"forbidden call {func.id}")
            if isinstance(func, ast.Attribute) and func.attr in banned_call_roots:
                pytest.fail(f"forbidden call .{func.attr}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in ("tkinter", "Godot", "godot"):
                    pytest.fail(f"forbidden import {alias.name}")
        if isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in ("tkinter", "godot"):
                    pytest.fail(f"forbidden from-import {node.module}")


def test_malformed_player_list_does_not_crash() -> None:
    team = SimpleNamespace(
        name="壊れ",
        league_level=1,
        players=[None, "x", SimpleNamespace(), _player(9, name="正常", position="C", ovr=40)],
        fa_shortlist=None,
    )
    d = build_contract_personnel_summary_readonly_dict(team)
    assert len(d["player_contract_rows"]) >= 1
    assert any(r["player_name"] == "正常" for r in d["player_contract_rows"])


def test_nationality_slot_unknown_shows_disconnected_aggregate() -> None:
    # nationality が規則ラベルに載らない値だと bucket は domestic でも表示ラベルは「不明」になり、集計は未接続分岐へ。
    p1 = SimpleNamespace(
        name="U1",
        position="PG",
        age=22,
        ovr=50,
        potential="D",
        salary=1,
        contract_years_left=2,
        nationality="UnlistedCountry",
        injury_games_left=0,
    )
    p2 = SimpleNamespace(
        name="U2",
        position="SG",
        age=23,
        ovr=51,
        potential="D",
        salary=2,
        contract_years_left=2,
        nationality="OtherUnknown",
        injury_games_left=0,
    )
    team = SimpleNamespace(name="全国籍不明", league_level=1, players=[p1, p2], fa_shortlist=[])
    d = build_contract_personnel_summary_readonly_dict(team)
    nb = next((it for it in d["roster_balance_items"] if it["key"] == "nationality_breakdown"), None)
    assert nb is not None
    assert nb["display_value"] == "未接続"


def test_cli_prints_wrote(tmp_path: Path) -> None:
    from basketball_sim.persistence.save_load import save_world

    sav = tmp_path / "cli.sav"
    team = Team(team_id=3, name="CLI FC", league_level=1)
    save_world(
        sav,
        {
            "teams": [team],
            "free_agents": [],
            "user_team_id": 3,
            "season_count": 1,
            "at_annual_menu": False,
            "tracked_player_name": None,
        },
    )
    out = tmp_path / "cli.json"
    cmd = [
        sys.executable,
        "-m",
        "basketball_sim.export.contract_personnel_summary_readonly",
        "--save",
        str(sav),
        "--output",
        str(out),
        "--max-players",
        "4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert f"Wrote {out}" in proc.stdout
