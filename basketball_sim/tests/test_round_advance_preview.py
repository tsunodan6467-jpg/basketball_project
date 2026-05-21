"""round_advance_preview: 次ラウンド read-only プレビュー。"""

from __future__ import annotations

import pytest

from basketball_sim.systems.round_advance_preview import (
    DEFAULT_NOTES,
    SCREEN_TITLE,
    build_round_advance_preview_dict,
    format_round_advance_preview_lines,
)


class _T:
    def __init__(self, tid: int, name: str) -> None:
        self.team_id = tid
        self.name = name


class _Ev:
    def __init__(
        self,
        rnd: int,
        home: _T,
        away: _T,
        ct: str = "regular_season",
        event_type: str = "game",
    ) -> None:
        self.event_id = f"r{rnd}_{home.name}_{away.name}"
        self.event_type = event_type
        self.round_number = rnd
        self.home_team = home
        self.away_team = away
        self.competition_type = ct
        self.label = "lbl"
        self.day_of_week = "Sat"


class _SeasonWithEvents:
    def __init__(
        self,
        *,
        current_round: int = 1,
        total_rounds: int = 3,
        season_finished: bool = False,
        events: dict | None = None,
        game_results: list | None = None,
    ) -> None:
        self.current_round = current_round
        self.total_rounds = total_rounds
        self.season_finished = season_finished
        self.game_results = list(game_results) if game_results is not None else []
        self._events = events or {}

    def get_events_for_round(self, r: int):
        return list(self._events.get(r, []))

    def _get_round_config(self, r: int):
        return {"month": 10 + r}


class _SeasonNoGetter:
    def __init__(self, current_round: int = 1, total_rounds: int = 3) -> None:
        self.current_round = current_round
        self.total_rounds = total_rounds
        self.season_finished = False


def test_season_none_does_not_crash() -> None:
    d = build_round_advance_preview_dict(None, None)
    assert d["screen_title"] == SCREEN_TITLE
    assert d["summary"]["can_advance"] is False
    assert len(d["warnings"]) >= 1
    assert d["next_round_events"] == []
    lines = format_round_advance_preview_lines(None, None)
    assert isinstance(lines, list)
    assert any("ラウンド進行プレビュー" in ln for ln in lines)


def test_season_finished_cannot_advance() -> None:
    s = _SeasonWithEvents(current_round=33, total_rounds=33, season_finished=True)
    u = _T(1, "User")
    d = build_round_advance_preview_dict(s, u)
    assert d["summary"]["can_advance"] is False
    assert d["next_round_events"] == []
    assert any("終了" in w for w in d["warnings"])


def test_next_round_user_game_present() -> None:
    u = _T(1, "User")
    o = _T(2, "Other")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, u, o)]},
    )
    d = build_round_advance_preview_dict(s, u)
    assert d["summary"]["can_advance"] is True
    assert d["summary"]["next_round"] == 2
    assert d["user_game"]["has_game"] is True
    assert d["summary"]["user_team_game_count"] == 1
    assert len(d["next_round_events"]) == 1
    row = d["next_round_events"][0]
    assert row["is_user_team_game"] is True
    assert row["opponent"] == "Other"
    assert row["home_away_short"] == "H"


def test_next_round_no_user_game() -> None:
    a = _T(2, "Alpha")
    b = _T(3, "Beta")
    u = _T(1, "User")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, a, b)]},
    )
    d = build_round_advance_preview_dict(s, u)
    assert d["summary"]["can_advance"] is True
    assert d["user_game"]["has_game"] is False
    assert d["summary"]["user_team_game_count"] == 0
    assert len(d["next_round_events"]) == 1
    assert d["next_round_events"][0]["is_user_team_game"] is False


def test_no_get_events_for_round_stub() -> None:
    s = _SeasonNoGetter(current_round=1, total_rounds=3)
    u = _T(1, "User")
    d = build_round_advance_preview_dict(s, u)
    assert d["summary"]["can_advance"] is True
    assert d["next_round_events"] == []
    assert any("get_events_for_round" in w for w in d["warnings"])


def test_non_destructive_current_round_and_game_results() -> None:
    u = _T(1, "User")
    o = _T(2, "Other")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        game_results=[],
        events={2: [_Ev(2, u, o)]},
    )
    before_cr = s.current_round
    before_gr = list(s.game_results)
    before_fin = s.season_finished
    build_round_advance_preview_dict(s, u)
    format_round_advance_preview_lines(s, u)
    assert s.current_round == before_cr
    assert s.game_results == before_gr
    assert s.season_finished == before_fin


def test_match_simulate_not_called(monkeypatch: pytest.MonkeyPatch) -> None:
    import basketball_sim.models.match as match_mod

    def _boom(*args, **kwargs):
        raise AssertionError("Match.simulate must not be called from preview")

    monkeypatch.setattr(match_mod.Match, "simulate", _boom)
    u = _T(1, "User")
    o = _T(2, "Other")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, u, o)]},
    )
    build_round_advance_preview_dict(s, u)
    format_round_advance_preview_lines(s, u)


def test_include_weekly_check_false() -> None:
    u = _T(1, "User")
    o = _T(2, "Other")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, u, o)]},
    )
    d = build_round_advance_preview_dict(s, u, include_weekly_check=False)
    assert d["weekly_check_lines"] == []


def test_format_lines_contains_keywords() -> None:
    u = _T(1, "User")
    o = _T(2, "Other")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, u, o)]},
    )
    lines = format_round_advance_preview_lines(s, u)
    text = "\n".join(lines)
    assert "ラウンド進行プレビュー" in text
    assert "読み取り専用" in text
    assert DEFAULT_NOTES[0] in text or any("読み取り専用" in ln for ln in lines)


def test_non_game_event_included() -> None:
    u = _T(1, "User")
    s = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, u, _T(2, "O"), event_type="break")]},
    )
    d = build_round_advance_preview_dict(s, u)
    assert len(d["next_round_events"]) == 1
    assert d["next_round_events"][0]["event_type"] == "break"


def _preview_lines_with_hint(monkeypatch: pytest.MonkeyPatch, one_line: str) -> list[str]:
    import basketball_sim.systems.round_advance_preview as rap

    def _fake_dict(season: object, user_team: object, **kwargs: object) -> dict:
        return {
            "screen_title": SCREEN_TITLE,
            "team_name": "T",
            "summary": {
                "current_round": 1,
                "next_round": 2,
                "total_rounds": 3,
                "can_advance": True,
                "next_round_month_week": "—",
                "user_team_game_count": 0,
            },
            "advance_hint": {"one_line": one_line},
            "warnings": [],
            "schedule_lines": [],
            "notes": [],
        }

    monkeypatch.setattr(rap, "build_round_advance_preview_dict", _fake_dict)
    return format_round_advance_preview_lines(None, None)


def test_format_lines_does_not_duplicate_advance_hint_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = _preview_lines_with_hint(monkeypatch, "進行予告: ラウンド6・テスト")
    hint_lines = [ln for ln in lines if ln.startswith("進行予告")]
    assert hint_lines == ["進行予告: ラウンド6・テスト"]
    assert "進行予告: 進行予告:" not in "\n".join(lines)

    lines_fw = _preview_lines_with_hint(monkeypatch, "進行予告：ラウンド6・テスト")
    hint_lines_fw = [ln for ln in lines_fw if ln.startswith("進行予告")]
    assert hint_lines_fw == ["進行予告：ラウンド6・テスト"]
    assert "進行予告：進行予告：" not in "\n".join(lines_fw)


def test_format_lines_adds_advance_hint_prefix_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = _preview_lines_with_hint(monkeypatch, "ラウンド6・自チーム 2試合まとめ進行")
    hint_lines = [ln for ln in lines if ln.startswith("進行予告")]
    assert hint_lines == ["進行予告: ラウンド6・自チーム 2試合まとめ進行"]
