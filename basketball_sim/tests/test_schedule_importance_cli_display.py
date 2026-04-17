"""schedule_importance_cli_display: 表示のみ・例外に強いことの軽い検証。"""
from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.schedule_importance_cli_display import (
    build_match_importance_tags,
    format_schedule_importance_cli_lines,
    format_user_standings_importance_cli_lines,
)


def _team(tid, name, w, l, pf=100, pa=90, *, user=False, lv=1):
    return SimpleNamespace(
        team_id=tid,
        name=name,
        regular_wins=w,
        regular_losses=l,
        regular_points_for=pf,
        regular_points_against=pa,
        is_user_team=user,
        league_level=lv,
    )


def _season(league_level, teams, results=None):
    def get_standings(ts):
        return sorted(
            list(ts),
            key=lambda t: (
                int(getattr(t, "regular_wins", 0) or 0),
                int(getattr(t, "regular_points_for", 0) or 0)
                - int(getattr(t, "regular_points_against", 0) or 0),
            ),
            reverse=True,
        )

    return SimpleNamespace(
        leagues={league_level: teams},
        get_standings=get_standings,
        game_results=list(results or []),
    )


def test_top_four_head_to_head_tag() -> None:
    teams = [_team(1, "User", 22, 0, user=True), _team(2, "Opp", 21, 1)]
    teams.extend(_team(10 + i, f"X{i}", 10, 10) for i in range(10))
    s = _season(1, teams)
    u, o = teams[0], teams[1]
    tags = build_match_importance_tags(s, u, o, league_level=1)
    assert "上位直接対決" in tags


def test_po_bubble_and_streak() -> None:
    teams = [_team(i + 1, f"Hi{i}", 20, 0) for i in range(7)]
    teams.append(_team(99, "User", 10, 10, user=True))
    teams.extend(_team(20 + i, f"Lo{i}", 5, 15) for i in range(4))
    res = [{"home_team": "User", "away_team": "X", "home_score": 80, "away_score": 90}] * 4
    s = _season(1, teams, results=res)
    u = teams[7]
    o = teams[0]
    tags = build_match_importance_tags(s, u, o, league_level=1)
    assert "PO圏争い" in tags
    assert "連敗ストップがかかる" in tags


def test_format_lines_non_empty() -> None:
    teams = [_team(i + 1, f"T{i}", 16 - (i // 2), i % 5) for i in range(12)]
    teams[7] = _team(77, "User", 10, 10, user=True)
    s = _season(1, teams)
    lines = format_schedule_importance_cli_lines(s, teams[7], teams[0])
    assert lines
    assert lines[0].startswith("【試合重要度】")


def test_standings_footer_lines() -> None:
    teams = [_team(i + 1, f"Hi{i}", 20, 0) for i in range(7)]
    teams.append(_team(55, "User", 10, 10, user=True))
    teams.extend(_team(30 + i, f"Lo{i}", 5, 15) for i in range(4))
    s = _season(1, teams)
    u = teams[7]
    lines = format_user_standings_importance_cli_lines(s, u)
    assert any("【試合重要度】" in x for x in lines)


def test_broken_season_safe() -> None:
    s = SimpleNamespace(leagues=None)
    lines = format_schedule_importance_cli_lines(s, _team(1, "U", 1, 1, user=True), None)
    assert lines == ["【試合重要度】情報なし"]
