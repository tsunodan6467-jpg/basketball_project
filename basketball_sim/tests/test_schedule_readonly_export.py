from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from basketball_sim.export.schedule_readonly import (
    SCREEN_TITLE,
    build_schedule_readonly_dict,
    export_schedule_json_from_world,
    write_schedule_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world

REQUIRED_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "season_label",
    "summary",
    "next_game",
    "upcoming_games",
    "advance_hint",
    "empty_message",
    "notes",
)


class _T:
    def __init__(self, tid: int, name: str) -> None:
        self.team_id = tid
        self.name = name


class _Ev:
    def __init__(self, rnd: int, home: _T, away: _T, ct: str = "regular_season") -> None:
        self.event_id = f"r{rnd}_{home.name}_{away.name}"
        self.event_type = "game"
        self.round_number = rnd
        self.home_team = home
        self.away_team = away
        self.competition_type = ct
        self.label = "lbl"


class _SeasonStub:
    """test_schedule_display._Season と同等（日程 upcoming 用）。"""

    def __init__(self) -> None:
        self.current_round = 1
        self.total_rounds = 2
        self.season_finished = False
        self.season_no = 1
        u = _T(1, "User")
        v = _T(2, "Other")
        w = _T(3, "Third")
        self._events = {
            2: [_Ev(2, u, v), _Ev(2, u, w, ct="emperor_cup")],
        }

    def get_events_for_round(self, r: int):
        return list(self._events.get(r, []))

    def _get_round_config(self, r: int):
        return {"month": 10 + r}


class _SeasonEmperorPlaceholder:
    """杯週が次ラウンドで、メイン次戦行が cup 側に寄るケース。"""

    def __init__(self) -> None:
        self.current_round = 12
        self.total_rounds = 14
        self.season_finished = False
        self.season_no = 1
        u = _T(1, "User")
        v = _T(2, "Other")
        self.emperor_cup_bye_teams = [u]
        self.emperor_cup_round1_teams = [v]
        self.emperor_cup_current_teams = []
        self.emperor_cup_played_stages = set()

    def get_events_for_round(self, r: int):
        if r == 13:
            return []
        if r == 14:
            return [_Ev(14, _T(1, "User"), _T(9, "Z"))]
        return []

    def _should_play_emperor_cup_this_round(self, r: int) -> bool:
        return r == 13

    def _get_round_config(self, r: int):
        return {"month": 1}


def test_build_schedule_required_keys() -> None:
    team = SimpleNamespace(name="テストFC", league_level=2, players=[])
    d = build_schedule_readonly_dict(None, team)
    for k in REQUIRED_KEYS:
        assert k in d
    assert d["screen_title"] == SCREEN_TITLE
    assert d["team_name"] == "テストFC"
    assert d["league_level"] == 2
    assert isinstance(d["summary"], dict)
    assert isinstance(d["next_game"], dict)
    assert isinstance(d["upcoming_games"], list)
    assert isinstance(d["advance_hint"], dict)
    assert "block" in d["advance_hint"] and "one_line" in d["advance_hint"]


def test_no_season_flags_and_empty_upcoming() -> None:
    team = SimpleNamespace(name="X", league_level=1, players=[])
    d = build_schedule_readonly_dict(None, team)
    assert d["summary"]["has_season"] is False
    assert d["upcoming_games"] == []
    assert d["summary"]["upcoming_count"] == 0
    assert d["next_game"]["status"] == "unavailable"
    assert d["next_game"]["label"] == "次戦情報：未接続"
    assert "未接続" in d["empty_message"]
    assert d["advance_hint"]["block"] == ""
    assert d["advance_hint"]["one_line"] == ""


def test_season_label_annual_menu_with_season_count() -> None:
    team = SimpleNamespace(name="X", league_level=1, players=[])
    d = build_schedule_readonly_dict(None, team, at_annual_menu=True, season_count=3)
    assert d["season_label"] == "年度メニュー（シーズン 3）"


def test_season_label_season_count_only() -> None:
    team = SimpleNamespace(name="X", league_level=1, players=[])
    d = build_schedule_readonly_dict(None, team, at_annual_menu=False, season_count=5)
    assert d["season_label"] == "シーズン 5（進行情報未接続）"


def test_write_schedule_json_utf8(tmp_path: Path) -> None:
    team = SimpleNamespace(name="日本語クラブ", league_level=1, players=[])
    snap = build_schedule_readonly_dict(None, team)
    out = tmp_path / "schedule.json"
    write_schedule_json(snap, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["team_name"] == "日本語クラブ"
    assert json.dumps(snap, ensure_ascii=False) == json.dumps(loaded, ensure_ascii=False)


def test_export_schedule_json_from_world_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1)
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
    snap = export_schedule_json_from_world(sav, out)
    assert out.is_file()
    assert snap["team_name"] == "セーブ出口FC"
    assert snap["summary"]["has_season"] is False
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["season_label"] == "年度メニュー（シーズン 1）"


def test_with_season_stub_upcoming_and_advance_hint() -> None:
    season = _SeasonStub()
    user = _T(1, "User")
    d = build_schedule_readonly_dict(season, user, max_upcoming=8)
    assert d["summary"]["has_season"] is True
    assert d["summary"]["current_round"] == 1
    assert d["summary"]["total_rounds"] == 2
    assert len(d["upcoming_games"]) == 2
    assert d["summary"]["upcoming_count"] == 2
    assert d["empty_message"] == ""
    row0 = d["upcoming_games"][0]
    assert row0["opponent"] == "Other"
    assert row0["competition_type"] == "regular_season"
    assert row0["is_user_team_game"] is True
    assert "detail" in row0 and len(row0["detail"]) > 0
    assert d["next_game"]["status"] == "from_upcoming"
    assert "Other" in d["next_game"]["label"]
    assert "2 試合" in d["advance_hint"]["block"] or "2試合" in d["advance_hint"]["block"]
    assert d["advance_hint"]["one_line"]


def test_max_upcoming_caps_rows() -> None:
    season = _SeasonStub()
    user = _T(1, "User")
    d = build_schedule_readonly_dict(season, user, max_upcoming=1)
    assert len(d["upcoming_games"]) == 1
    assert d["summary"]["upcoming_count"] == 1


def test_emperor_next_game_takes_priority_over_upcoming() -> None:
    season = _SeasonEmperorPlaceholder()
    user = _T(1, "User")
    d = build_schedule_readonly_dict(season, user, max_upcoming=8)
    assert d["next_game"]["status"] == "from_emperor_cup_lines"
    assert "全日本" in d["next_game"]["label"] or "カップ" in d["next_game"]["label"]


def test_export_max_upcoming_kwarg(tmp_path: Path) -> None:
    sav = tmp_path / "w2.sav"
    team = Team(team_id=1, name="A", league_level=1)
    team.players = []
    season = _SeasonStub()
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
    out = tmp_path / "sch.json"
    export_schedule_json_from_world(sav, out, max_upcoming=1)
    body = json.loads(out.read_text(encoding="utf-8"))
    assert len(body["upcoming_games"]) == 1
