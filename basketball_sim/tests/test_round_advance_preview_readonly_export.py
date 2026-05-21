"""round_advance_preview_readonly: .sav から read-only export / CLI。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from basketball_sim.export import round_advance_preview_readonly as rap_export
from basketball_sim.export.round_advance_preview_readonly import (
    export_round_advance_preview_json_from_world,
    format_round_advance_preview_lines_from_world,
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


def _payload_with_season(
    user: _T,
    other: _T,
    season: Any,
    *,
    season_count: int = 1,
    at_annual_menu: bool = False,
) -> Dict[str, Any]:
    return {
        "teams": [user, other],
        "user_team_id": user.team_id,
        "resume_season": season,
        "season_count": season_count,
        "at_annual_menu": at_annual_menu,
        "free_agents": [],
    }


def _patch_world(monkeypatch: pytest.MonkeyPatch, payload: Dict[str, Any], user: _T) -> None:
    import basketball_sim.persistence.save_load as sl

    monkeypatch.setattr(sl, "load_world", lambda _path: payload)
    monkeypatch.setattr(sl, "validate_payload", lambda _p: None)
    monkeypatch.setattr(sl, "find_user_team", lambda _teams, _uid: user)


def test_export_round_advance_preview_json_from_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    out = tmp_path / "preview.json"
    snap = export_round_advance_preview_json_from_world("dummy.sav", out)

    assert out.is_file()
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["screen_title"]
    assert body["summary"]["can_advance"] is True
    assert body["summary"]["next_round"] == 2
    assert body["user_game"]["has_game"] is True
    assert snap["summary"]["next_round"] == body["summary"]["next_round"]


def test_non_destructive_season_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        game_results=[],
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    before_cr = season.current_round
    before_gr = list(season.game_results)
    before_fin = season.season_finished

    out = tmp_path / "preview.json"
    export_round_advance_preview_json_from_world("dummy.sav", out)
    format_round_advance_preview_lines_from_world("dummy.sav")

    assert season.current_round == before_cr
    assert season.game_results == before_gr
    assert season.season_finished == before_fin


def test_resume_season_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    payload = _payload_with_season(user, other, None)
    _patch_world(monkeypatch, payload, user)

    out = tmp_path / "preview.json"
    snap = export_round_advance_preview_json_from_world("dummy.sav", out)

    assert out.is_file()
    assert snap["summary"]["can_advance"] is False
    assert len(snap["warnings"]) >= 1


def test_format_lines_from_world(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    lines = format_round_advance_preview_lines_from_world("dummy.sav")
    text = "\n".join(lines)
    assert isinstance(lines, list)
    assert "ラウンド進行プレビュー" in text
    assert "読み取り専用" in text


def test_cli_main_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    out = tmp_path / "preview.json"
    code = rap_export._cli_main(
        [
            "--save",
            "dummy.sav",
            "--output",
            str(out),
            "--max-events",
            "8",
            "--no-weekly-check",
        ]
    )
    assert code == 0
    assert out.is_file()
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["weekly_check_lines"] == []


def test_cli_main_print_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    out = tmp_path / "preview.json"
    code = rap_export._cli_main(
        [
            "--save",
            "dummy.sav",
            "--output",
            str(out),
            "--print-lines",
        ]
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "ラウンド進行プレビュー" in captured or "Wrote" in captured


def test_save_world_and_match_simulate_not_called(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import basketball_sim.models.match as match_mod
    import basketball_sim.persistence.save_load as sl

    user = _T(1, "User")
    other = _T(2, "Other")
    season = _SeasonWithEvents(
        current_round=1,
        total_rounds=3,
        events={2: [_Ev(2, user, other)]},
    )
    payload = _payload_with_season(user, other, season)
    _patch_world(monkeypatch, payload, user)

    def _save_boom(*args, **kwargs):
        raise AssertionError("save_world must not be called from preview export")

    def _match_boom(*args, **kwargs):
        raise AssertionError("Match.simulate must not be called from preview export")

    monkeypatch.setattr(sl, "save_world", _save_boom)
    monkeypatch.setattr(match_mod.Match, "simulate", _match_boom)

    out = tmp_path / "preview.json"
    export_round_advance_preview_json_from_world("dummy.sav", out)
    format_round_advance_preview_lines_from_world("dummy.sav")
