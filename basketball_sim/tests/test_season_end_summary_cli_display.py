"""season_end_summary_cli_display: シーズン完走サマリー。"""

from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.season_end_summary_cli_display import (
    format_season_end_summary_lines,
)


def _user(name: str = "UserFC", **kwargs):
    base = {"name": name, "regular_wins": 0, "regular_losses": 0, "league_level": 1, "money": 0, "owner_trust": 50}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _season(**kwargs):
    base = {
        "current_round": 33,
        "total_rounds": 33,
        "leagues": {1: [], 2: [], 3: []},
        "division_playoff_results": {},
        "emperor_cup_results": {},
        "easl_results": {},
        "acl_results": {},
    }
    base.update(kwargs)

    class _Season:
        def __init__(self, data):
            self.__dict__.update(data)

        def get_standings(self, teams):
            return list(teams)

    return _Season(base)


def test_minimal_input_returns_title() -> None:
    lines = format_season_end_summary_lines(None, None, None)
    assert isinstance(lines, list)
    assert lines[0] == "【シーズン完走サマリー】"


def test_regular_record_shown() -> None:
    u = _user(regular_wins=36, regular_losses=24)
    text = "\n".join(format_season_end_summary_lines(_season(), u, []))
    assert "レギュラー成績: 36勝24敗" in text


def test_relegation_display() -> None:
    u = _user(league_level=2)
    text = "\n".join(
        format_season_end_summary_lines(_season(), u, [], league_level_before=1)
    )
    assert "D1 → D2" in text
    assert "降格" in text
    assert "降格後の再建へ" in text


def test_no_movement_display() -> None:
    u = _user(league_level=2)
    text = "\n".join(
        format_season_end_summary_lines(_season(), u, [], league_level_before=2)
    )
    assert "昇降格: 変動なし" in text


def test_recent_games_tail_and_full_record() -> None:
    u = _user(name="UserFC")
    rows = [
        {"home_team": "UserFC", "away_team": f"A{i:02d}", "home_score": 80, "away_score": 70}
        for i in range(12)
    ]
    text = "\n".join(
        format_season_end_summary_lines(_season(), u, rows, max_recent_games=10)
    )
    assert "今回進行分: 自チーム 12 試合 / 12勝0敗" in text
    assert "A00" not in text
    assert "A01" not in text
    assert "A10" in text
    assert "A11" in text


def test_zero_games_does_not_crash() -> None:
    u = _user()
    text = "\n".join(format_season_end_summary_lines(_season(), u, []))
    assert "今回進行分: 自チーム 0 試合" in text


def test_playoff_champion() -> None:
    u = _user(name="UserFC")
    po = {1: {"champion": u, "runner_up": None, "playoff_teams": [u]}}
    text = "\n".join(
        format_season_end_summary_lines(
            _season(division_playoff_results=po), u, [], league_level_before=1
        )
    )
    assert "PO: D1優勝" in text


def test_playoff_runner_up() -> None:
    u = _user(name="UserFC")
    other = _user(name="OtherFC")
    po = {1: {"champion": other, "runner_up": u, "playoff_teams": [u, other]}}
    text = "\n".join(
        format_season_end_summary_lines(
            _season(division_playoff_results=po), u, [], league_level_before=1
        )
    )
    assert "PO: D1準優勝" in text


def test_playoff_participant() -> None:
    u = _user(name="UserFC")
    other = _user(name="OtherFC")
    po = {1: {"champion": other, "runner_up": None, "playoff_teams": [u, other]}}
    text = "\n".join(
        format_season_end_summary_lines(
            _season(division_playoff_results=po), u, [], league_level_before=1
        )
    )
    assert "PO: D1進出" in text


def test_playoff_not_participant() -> None:
    u = _user(name="UserFC")
    other = _user(name="OtherFC")
    po = {1: {"champion": other, "runner_up": None, "playoff_teams": [other]}}
    text = "\n".join(
        format_season_end_summary_lines(
            _season(division_playoff_results=po), u, [], league_level_before=1
        )
    )
    assert "PO: D1未進出" in text


def test_user_rank_from_standings() -> None:
    u = _user(name="UserFC")
    t2 = _user(name="Other")
    season = _season(leagues={1: [t2, u], 2: [], 3: []})
    text = "\n".join(
        format_season_end_summary_lines(season, u, [], league_level_before=1)
    )
    assert "最終順位: D1 2位" in text


def test_promotion_one_liner() -> None:
    u = _user(league_level=1)
    text = "\n".join(
        format_season_end_summary_lines(_season(), u, [], league_level_before=2)
    )
    assert "昇格" in text
    assert "昇格後の補強へ" in text
