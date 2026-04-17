"""club_dashboard_cli_display: 表示のみ・例外に強いことの軽い検証。"""
from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.club_dashboard_cli_display import (
    build_club_dashboard_focus_hint,
    format_club_dashboard_cli_lines,
)


def test_format_lines_no_crash_minimal() -> None:
    t = SimpleNamespace(
        league_level=1,
        money=50_000_000,
        owner_trust=55,
        owner_expectation="playoff_race",
        players=[],
    )
    lines = format_club_dashboard_cli_lines(user_team=t, season=None)
    assert lines[0] == "【クラブ総合ダッシュボード】"
    assert any("順位:" in x for x in lines)
    assert any("今やるべきこと:" in x for x in lines)


def test_format_lines_none_team() -> None:
    lines = format_club_dashboard_cli_lines(user_team=None)
    assert "チーム未接続" in lines[1]


def test_focus_hint_money() -> None:
    h = build_club_dashboard_focus_hint(
        SimpleNamespace(),
        None,
        money=1_000_000,
        trust=60,
        roster_attn="特記なし",
        match_tags=[],
        fa_count=0,
    )
    assert h == "財務確認"


def test_focus_hint_trust() -> None:
    h = build_club_dashboard_focus_hint(
        SimpleNamespace(),
        SimpleNamespace(season_finished=False),
        money=50_000_000,
        trust=30,
        roster_attn="特記なし",
        match_tags=[],
        fa_count=0,
    )
    assert "オーナー" in h
