from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.finance_summary_readonly import (
    build_finance_summary_readonly_dict,
    export_finance_summary_json_from_world,
    write_finance_summary_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world

REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "finance_items",
    "history_rows",
    "sections",
    "notes",
)


def test_build_finance_summary_required_top_keys() -> None:
    d = build_finance_summary_readonly_dict(None)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["screen_title"] == "財務サマリー（閲覧）"


def test_build_finance_summary_team_none() -> None:
    d = build_finance_summary_readonly_dict(None)
    assert d["team_name"] == "-"
    assert d["league_level"] is None
    assert d["history_rows"] == []
    assert "チーム情報が未接続" in "".join(d["notes"])
    assert d["summary"]["money"] is None
    assert d["summary"]["has_finance_history"] is False
    assert isinstance(d["finance_items"], list)
    assert len(d["finance_items"]) >= 7


def test_build_finance_summary_team_reads_financial_fields() -> None:
    team = Team(team_id=1, name="財務テストFC", league_level=2)
    team.money = 150_000_000
    team.revenue_last_season = 80_000_000
    team.expense_last_season = 70_000_000
    team.cashflow_last_season = 10_000_000
    d = build_finance_summary_readonly_dict(team)
    assert d["team_name"] == "財務テストFC"
    assert d["league_level"] == 2
    assert d["summary"]["money"] == 150_000_000
    assert d["summary"]["revenue_last_season"] == 80_000_000
    assert d["summary"]["expense_last_season"] == 70_000_000
    assert d["summary"]["cashflow_last_season"] == 10_000_000
    assert d["summary"]["finance_history_count"] == 0


def test_finance_history_dict_rows_and_max_history() -> None:
    hist = []
    for i in range(11):
        hist.append(
            {
                "season_label": f"S{i}",
                "revenue": 10_000_000 + i,
                "expense": 5_000_000,
                "cashflow": 5_000_000 + i,
                "note": f"n{i}",
            }
        )
    team = SimpleNamespace(
        name="Hist",
        league_level=1,
        money=1,
        revenue_last_season=0,
        expense_last_season=0,
        cashflow_last_season=0,
        players=[],
        finance_history=hist,
    )
    d = build_finance_summary_readonly_dict(team, max_history=3)
    assert d["summary"]["finance_history_count"] == 11
    assert len(d["history_rows"]) == 3
    # 末尾3件・ストレージ順維持（並べ替えなし）
    assert d["history_rows"][0]["season"] == "S8"
    assert d["history_rows"][1]["season"] == "S9"
    assert d["history_rows"][2]["season"] == "S10"
    assert d["history_rows"][0]["order"] == 1


def test_finance_history_object_list() -> None:
    class Row:
        def __init__(self) -> None:
            self.season_label = "2025"
            self.revenue = 100
            self.expense = 40
            self.cashflow = 60
            self.note = "ok"

    team = SimpleNamespace(
        name="Obj",
        league_level=1,
        money=0,
        revenue_last_season=None,
        expense_last_season=None,
        cashflow_last_season=None,
        players=[],
        finance_history=[Row()],
    )
    d = build_finance_summary_readonly_dict(team, max_history=5)
    assert len(d["history_rows"]) == 1
    assert d["history_rows"][0]["revenue"] == 100
    assert d["history_rows"][0]["memo"] == "ok"


def test_invalid_finance_values_do_not_crash() -> None:
    team = SimpleNamespace(
        name="Bad",
        league_level="x",
        money="not-int",
        revenue_last_season=None,
        expense_last_season="-",
        cashflow_last_season={},
        players="not-a-list",
        finance_history=[{"revenue": "x", "expense": None, "cashflow": None, "note": 1}],
    )
    d = build_finance_summary_readonly_dict(team)
    assert d["team_name"] == "Bad"
    assert d["league_level"] is None
    assert d["summary"]["money"] is None
    assert len(d["history_rows"]) in (0, 1)


def test_write_finance_summary_json_utf8(tmp_path: Path) -> None:
    team = Team(team_id=1, name="円マークFC", league_level=1)
    d = build_finance_summary_readonly_dict(team)
    out = tmp_path / "fin.json"
    write_finance_summary_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "円マークFC" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "円マークFC"


def test_export_finance_summary_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=7, name="出口財務FC", league_level=1)
    team.money = 50_000_000
    team.revenue_last_season = 10_000_000
    team.expense_last_season = 9_000_000
    team.cashflow_last_season = 1_000_000
    team.finance_history = [
        {"season_label": "Y1", "revenue": 100, "expense": 50, "cashflow": 50, "note": "a"},
    ]
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 7,
        "season_count": 2,
        "at_annual_menu": False,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "fin_out.json"
    snap = export_finance_summary_json_from_world(sav, out, max_history=5)
    assert out.is_file()
    assert snap["team_name"] == "出口財務FC"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["summary"]["money"] == 50_000_000
    assert len(body["history_rows"]) == 1


def test_sections_structure() -> None:
    d = build_finance_summary_readonly_dict(None)
    titles = [s["title"] for s in d["sections"]]
    assert "財務概要" in titles
    assert "前季収支" in titles
    assert "財務履歴" in titles
    assert "注意" in titles
    for sec in d["sections"]:
        assert "lines" in sec
        assert isinstance(sec["lines"], list)


def test_export_module_source_safety() -> None:
    import basketball_sim.export.finance_summary_readonly as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "save_world" not in src
    assert "record_financial_result" not in src
    assert "MainMenuView" not in src
    assert "ensure_team_tactics" not in src
    assert "tkinter" not in src.lower()
