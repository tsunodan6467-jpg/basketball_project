"""weekly_advance_cli_display: 週送り前表示のみ・落ちないことの軽い検証。"""
from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.weekly_advance_cli_display import (
    build_weekly_advance_focus_hint,
    format_weekly_advance_check_lines,
)


def test_format_lines_no_crash() -> None:
    ev = SimpleNamespace(
        event_type="game",
        competition_type="regular_season",
        home_team=None,
        away_team=None,
    )
    u = SimpleNamespace(team_id=1, name="U", league_level=1, players=[])
    o = SimpleNamespace(team_id=2, name="O")
    ev.home_team = u
    ev.away_team = o

    def get_events_for_round(rn):
        if rn == 1:
            return [ev]
        return []

    s = SimpleNamespace(
        current_round=0,
        total_rounds=30,
        season_finished=False,
        get_events_for_round=get_events_for_round,
        free_agents=[],
    )
    lines = format_weekly_advance_check_lines(season=s, user_team=u, free_agents=[])
    assert lines[0] == "【週送り前チェック】"
    assert any(l.startswith("今週:") for l in lines)
    assert any("進める前チェック:" in l for l in lines)


def test_format_season_finished_short() -> None:
    u = SimpleNamespace(team_id=1)
    s = SimpleNamespace(season_finished=True)
    lines = format_weekly_advance_check_lines(season=s, user_team=u)
    assert "【週送り前チェック】" in lines[0]


def test_focus_roster_priority() -> None:
    h = build_weekly_advance_focus_hint(
        roster_attn="ガード不足",
        mgmt_parts=["財務赤字傾向"],
        match_tags=["PO圏争い"],
    )
    assert "先発" in h


def test_focus_ok_default() -> None:
    h = build_weekly_advance_focus_hint(
        roster_attn="特記なし",
        mgmt_parts=[],
        match_tags=[],
    )
    assert "そのまま" in h
