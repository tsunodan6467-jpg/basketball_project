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
