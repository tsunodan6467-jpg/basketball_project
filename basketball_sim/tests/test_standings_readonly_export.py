from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.standings_readonly import (
    STANDINGS_COLUMNS,
    build_standings_readonly_dict,
    export_standings_json_from_world,
    write_standings_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world


REQUIRED_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "season_label",
    "summary",
    "columns",
    "divisions",
    "notes",
)


class _Team:
    def __init__(self, tid: int, name: str, w: int, l: int, pf: int, pa: int, **kw: object) -> None:
        self.team_id = tid
        self.name = name
        self.regular_wins = w
        self.regular_losses = l
        self.regular_points_for = pf
        self.regular_points_against = pa
        self.is_user_team = bool(kw.get("is_user_team", False))


class _SeasonStub:
    """test_information_display と同型の最小 Season スタブ。"""

    def __init__(self) -> None:
        t1 = _Team(1, "A", 3, 0, 300, 270)
        t2 = _Team(2, "B", 2, 1, 280, 275)
        t3 = _Team(3, "UserTeam", 0, 3, 200, 310, is_user_team=True)
        self.leagues = {1: [t2, t1, t3]}
        self.season_finished = False
        self.season_no = 1
        self.current_round = 0
        self.total_rounds = 34

    def get_standings(self, teams):
        return sorted(
            teams,
            key=lambda t: (t.regular_wins, t.regular_points_for - t.regular_points_against),
            reverse=True,
        )


def test_build_standings_returns_required_keys() -> None:
    team = SimpleNamespace(
        name="テストFC",
        league_level=2,
        regular_wins=10,
        regular_losses=5,
        players=[],
    )
    d = build_standings_readonly_dict(None, team, season_count=2, at_annual_menu=True)
    for k in REQUIRED_KEYS:
        assert k in d
    assert d["screen_title"] == "順位表（閲覧）"
    assert d["team_name"] == "テストFC"
    assert d["league_level"] == 2
    assert d["columns"] == list(STANDINGS_COLUMNS)
    assert len(d["divisions"]) == 3
    assert isinstance(d["notes"], list)


def test_no_season_has_flag_and_placeholder_messages() -> None:
    team = SimpleNamespace(name="X", league_level=1, regular_wins=0, regular_losses=0, players=[])
    d = build_standings_readonly_dict(None, team)
    assert d["summary"]["has_season"] is False
    for div in d["divisions"]:
        assert div["rows"] == []
        assert "未接続" in div["empty_message"]


def test_with_season_populates_d1_and_marks_user_row() -> None:
    season = _SeasonStub()
    team = _Team(99, "UserTeam", 0, 0, 0, 0)
    d = build_standings_readonly_dict(season, team, season_count=None, at_annual_menu=None)
    assert d["summary"]["has_season"] is True
    d1 = d["divisions"][0]
    assert d1["level"] == 1
    assert d1["division_label"] == "D1"
    assert len(d1["rows"]) == 3
    assert d1["empty_message"] == ""
    user_rows = [r for r in d1["rows"] if r["is_user_row"]]
    assert len(user_rows) == 1
    assert user_rows[0]["team_name"] == "UserTeam"
    for r in d1["rows"]:
        for col in STANDINGS_COLUMNS:
            assert col in r
    # D2/D3: スタブにリーグ母集団が無いため空
    assert d["divisions"][1]["rows"] == []
    assert d["divisions"][2]["rows"] == []


def test_write_standings_json_utf8(tmp_path: Path) -> None:
    team = SimpleNamespace(name="日本語クラブ", league_level=1, regular_wins=0, regular_losses=0, players=[])
    snap = build_standings_readonly_dict(None, team)
    out = tmp_path / "standings.json"
    write_standings_json(snap, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"


def test_export_standings_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1)
    team.regular_wins = 3
    team.regular_losses = 7
    team.players = []
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
    snap = export_standings_json_from_world(sav, out)
    assert out.is_file()
    assert snap["team_name"] == "セーブ出口FC"
    assert snap["summary"]["has_season"] is False
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["season_label"] == "年度メニュー（シーズン 1）"
    assert body["summary"]["current_division"].startswith("D")
