"""simulate_next_round / Match quiet モード。"""

from __future__ import annotations

import contextlib
import io
from unittest import mock

import pytest

from basketball_sim.main import generate_teams
from basketball_sim.models.match import Match
from basketball_sim.models.season import Season, SeasonEvent


def _make_two_team_season() -> Season:
    teams = generate_teams()
    season = Season(teams, [])
    home, away = teams[0], teams[1]
    season.events_by_round[1] = [
        SeasonEvent(
            event_id="r1g1",
            week=1,
            day_of_week="Wed",
            event_type="game",
            competition_id="regular_season",
            competition_type="regular_season",
            stage="regular_season",
            home_team=home,
            away_team=away,
            round_number=1,
            label="g1",
        ),
    ]
    return season


def test_match_quiet_init_suppresses_active_starters(capsys: pytest.CaptureFixture[str]) -> None:
    teams = generate_teams()
    home, away = teams[0], teams[1]
    Match(home_team=home, away_team=away, quiet=True)
    out = capsys.readouterr().out
    assert "[ACTIVE]" not in out
    assert "[STARTERS]" not in out


def test_match_quiet_simulate_suppresses_debug_tokens(capsys: pytest.CaptureFixture[str]) -> None:
    teams = generate_teams()
    home, away = teams[0], teams[1]
    match = Match(home_team=home, away_team=away, quiet=True)
    match.simulate()
    out = capsys.readouterr().out
    for token in ("[PBP]", "[COMMENTARY]", "[MINUTES]", "[PLAY]", "[SUB]", "[ACTIVE]", "[STARTERS]"):
        assert token not in out
    assert len(match.play_by_play_log) > 0


def test_match_quiet_false_still_prints_debug(capsys: pytest.CaptureFixture[str]) -> None:
    teams = generate_teams()
    home, away = teams[0], teams[1]
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        match = Match(home_team=home, away_team=away, quiet=False)
        match.simulate()
    out = sink.getvalue()
    assert any(token in out for token in ("[PBP]", "[COMMENTARY]", "[MINUTES]", "[ACTIVE]", "[STARTERS]"))


def test_simulate_next_round_quiet_advances_state(capsys: pytest.CaptureFixture[str]) -> None:
    season = _make_two_team_season()
    before_round = season.current_round
    before_results = len(season.game_results)
    season.simulate_next_round(quiet=True)
    capsys.readouterr()
    assert season.current_round == before_round + 1
    assert len(season.game_results) == before_results + 1
    row = season.game_results[-1]
    assert set(row.keys()) == {
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "score_diff",
        "total_score",
    }


def test_simulate_next_round_quiet_output_line_cap(capsys: pytest.CaptureFixture[str]) -> None:
    season = _make_two_team_season()
    season.simulate_next_round(quiet=True)
    out = capsys.readouterr().out
    line_count = len([ln for ln in out.splitlines() if ln.strip()])
    assert line_count <= 50
    assert "ラウンド消化試合数" in out


def test_finalize_season_compact_smoke() -> None:
    season = _make_two_team_season()
    season.game_count = 10
    season.total_points = 1400
    season._finalized = False

    captured: dict = {}

    def _fake_playoffs(*, quiet: bool = False):
        captured["quiet"] = quiet
        return {1: {"champion": None, "runner_up": None, "playoff_teams": []}}

    with mock.patch.object(season, "_simulate_all_playoffs", side_effect=_fake_playoffs), mock.patch.object(
        season, "_play_acl_competition"
    ), mock.patch.object(season, "_process_promotion_relegation"), mock.patch.object(
        season, "_process_finances"
    ), mock.patch.object(
        season, "_record_division_season_history"
    ), mock.patch.object(
        season, "_apply_career_stats"
    ), mock.patch.object(
        season, "_update_popularity"
    ), mock.patch.object(
        season, "_calculate_and_print_awards_by_division"
    ):
        season._finalize_season(compact=True)

    assert season.season_finished is True
    assert captured.get("quiet") is True


def _make_multi_round_season(rounds: int = 5) -> Season:
    teams = generate_teams()
    season = Season(teams, [])
    home, away = teams[0], teams[1]
    for rnd in range(1, rounds + 1):
        season.events_by_round[rnd] = [
            SeasonEvent(
                event_id=f"r{rnd}g1",
                week=rnd,
                day_of_week="Wed",
                event_type="game",
                competition_id="regular_season",
                competition_type="regular_season",
                stage="regular_season",
                home_team=home,
                away_team=away,
                round_number=rnd,
                label=f"g{rnd}",
            ),
        ]
    return season


def test_simulate_multiple_rounds_quiet_advances_and_suppresses_debug(
    capsys: pytest.CaptureFixture[str],
) -> None:
    season = _make_multi_round_season(5)
    before_round = season.current_round
    before_results = len(season.game_results)
    season.simulate_multiple_rounds(5, quiet=True)
    out = capsys.readouterr().out
    assert season.current_round == before_round + 5
    assert len(season.game_results) == before_results + 5
    for token in ("[PBP]", "[COMMENTARY]", "[MINUTES]", "[PLAY]", "[SUB]"):
        assert token not in out
    line_count = len([ln for ln in out.splitlines() if ln.strip()])
    assert line_count <= 80


def test_simulate_multiple_rounds_before_after_slice() -> None:
    season = _make_multi_round_season(5)
    before = len(season.game_results)
    season.simulate_multiple_rounds(5, quiet=True)
    added = season.game_results[before:]
    assert isinstance(added, list)
    assert len(added) == 5
    assert set(added[0].keys()) == {
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "score_diff",
        "total_score",
    }


def test_post_summary_multi_round_max_games_ten() -> None:
    from basketball_sim.systems.post_advance_result_summary_cli_display import (
        format_post_advance_result_summary_lines,
    )

    class _T:
        name = "UserFC"

    rows = [
        {"home_team": "UserFC", "away_team": f"O{i}", "home_score": 80, "away_score": 70}
        for i in range(10)
    ]
    text = "\n".join(
        format_post_advance_result_summary_lines(
            _T(),
            rows,
            round_label="ラウンド 6〜10/33（5ラウンド進行分）",
            max_games=10,
        )
    )
    assert "自チーム試合: 10 試合" in text
    assert "ほか" not in text
    assert "5ラウンド進行分" in text
    assert "10勝0敗" in text


def test_simulate_to_end_quiet_finishes_without_debug_tokens(
    capsys: pytest.CaptureFixture[str],
) -> None:
    season = _make_multi_round_season(3)
    season.simulate_to_end(quiet=True)
    out = capsys.readouterr().out
    assert season.season_finished is True
    for token in ("[PBP]", "[COMMENTARY]", "[MINUTES]", "[PLAY]", "[SUB]"):
        assert token not in out


def _make_user_team_season(*, user_involved: bool = True) -> Season:
    teams = generate_teams()
    user = teams[0]
    user.is_user_team = True
    if user_involved:
        home, away = user, teams[1]
    else:
        home, away = teams[1], teams[2]
    season = Season(teams, [])
    season.events_by_round[1] = [
        SeasonEvent(
            event_id="r1g1",
            week=1,
            day_of_week="Wed",
            event_type="game",
            competition_id="regular_season",
            competition_type="regular_season",
            stage="regular_season",
            home_team=home,
            away_team=away,
            round_number=1,
            label="g1",
        ),
    ]
    return season


def test_simulate_next_round_quiet_captures_user_match_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    season = _make_user_team_season(user_involved=True)
    before_logs = len(season.match_logs)
    before_results = len(season.game_results)
    season.simulate_next_round(quiet=True)
    capsys.readouterr()

    assert len(season.game_results) == before_results + 1
    assert set(season.game_results[-1].keys()) == {
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "score_diff",
        "total_score",
    }
    assert len(season.match_logs) == before_logs + 1
    entry = season.match_logs[-1]
    assert entry["user_team_involved"] is True
    assert entry["event_id"] == "r1g1"
    assert entry["commentary_excerpt"]["total_lines"] > 0
    assert len(entry["key_plays"]) <= 8


def test_simulate_next_round_quiet_skips_non_user_match_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    season = _make_user_team_season(user_involved=False)
    before_logs = len(season.match_logs)
    season.simulate_next_round(quiet=True)
    capsys.readouterr()
    assert len(season.match_logs) == before_logs
