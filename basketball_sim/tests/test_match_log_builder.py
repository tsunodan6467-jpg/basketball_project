"""match_log_builder の単体テスト。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from basketball_sim.main import generate_teams
from basketball_sim.models.match import Match
from basketball_sim.models.season import SeasonEvent
from basketball_sim.systems.match_log_builder import build_user_match_log_entry


def _fake_event(**kwargs):
    defaults = {
        "event_id": "evt-001",
        "round_number": 3,
        "competition_type": "regular_season",
        "stage": "regular_season",
        "week": 3,
        "day_of_week": "Wed",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _fake_match(*, commentary_lines=None, play_sequence=None):
    lines = commentary_lines if commentary_lines is not None else ["line1", "line2"]
    plays = play_sequence if play_sequence is not None else [
        {
            "play_no": 1,
            "quarter": 1,
            "result_type": "made_2",
            "commentary_text": "score",
            "home_score": 2,
            "away_score": 0,
            "events": [{"nested": True}],
        }
    ]

    class _FakeMatch:
        def get_commentary_lines(self):
            return list(lines)

        def get_play_sequence_log(self):
            return list(plays)

    return _FakeMatch()


def test_user_involved_home_win_returns_entry() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="UserFC")
    away = SimpleNamespace(name="Opponent")
    event = _fake_event(home_team=home, away_team=away)
    match = _fake_match()

    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=82,
        away_score=76,
    )

    assert entry is not None
    assert entry["user_team_involved"] is True
    assert entry["user_result"] == "W"
    assert entry["summary_line"].startswith("○")
    assert "UserFC 82 - 76 Opponent" in entry["summary_line"]


def test_non_user_game_returns_none() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="TeamA")
    away = SimpleNamespace(name="TeamB")
    event = _fake_event(home_team=home, away_team=away)
    match = _fake_match()

    assert build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=70,
        away_score=68,
    ) is None


def test_away_user_win_and_loss() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="Opponent")
    away = SimpleNamespace(name="UserFC")
    event = _fake_event(home_team=home, away_team=away)
    match = _fake_match()

    win = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=70,
        away_score=75,
    )
    assert win is not None
    assert win["user_result"] == "W"
    assert win["summary_line"].startswith("○")

    loss = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=80,
        away_score=70,
    )
    assert loss is not None
    assert loss["user_result"] == "L"
    assert loss["summary_line"].startswith("●")


def test_commentary_excerpt_limits() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="UserFC")
    away = SimpleNamespace(name="Opponent")
    event = _fake_event(home_team=home, away_team=away)
    commentary = [f"c{i}" for i in range(20)]
    match = _fake_match(commentary_lines=commentary)

    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=80,
        away_score=70,
    )
    assert entry is not None
    excerpt = entry["commentary_excerpt"]
    assert excerpt["total_lines"] == 20
    assert len(excerpt["head"]) == 5
    assert len(excerpt["tail"]) == 5
    assert excerpt["head"] == ["c0", "c1", "c2", "c3", "c4"]
    assert excerpt["tail"] == ["c15", "c16", "c17", "c18", "c19"]
    assert "commentary_full" not in entry
    assert len(excerpt["head"]) + len(excerpt["tail"]) < 20


def test_key_plays_tail_limit_and_no_events() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="UserFC")
    away = SimpleNamespace(name="Opponent")
    event = _fake_event(home_team=home, away_team=away)
    plays = [
        {
            "play_no": i,
            "quarter": 1,
            "result_type": "made_2",
            "commentary_text": f"p{i}",
            "home_score": i,
            "away_score": 0,
            "events": [{"x": i}],
        }
        for i in range(1, 21)
    ]
    match = _fake_match(play_sequence=plays)

    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=80,
        away_score=70,
        max_key_plays=8,
    )
    assert entry is not None
    key_plays = entry["key_plays"]
    assert len(key_plays) == 8
    assert key_plays[0]["play_no"] == 13
    assert key_plays[-1]["play_no"] == 20
    for kp in key_plays:
        assert "events" not in kp


def test_unknown_scores_do_not_crash() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="UserFC")
    away = SimpleNamespace(name="Opponent")
    event = _fake_event(home_team=home, away_team=away)
    match = _fake_match()

    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=None,
        away_score=None,
    )
    assert entry is not None
    assert entry["user_result"] == "unknown"
    assert entry["summary_line"].startswith("？")
    assert entry["home_score"] is None
    assert entry["away_score"] is None


def test_event_metadata_included() -> None:
    user = SimpleNamespace(name="UserFC")
    home = SimpleNamespace(name="UserFC")
    away = SimpleNamespace(name="Opponent")
    event = _fake_event(
        event_id="meta-evt",
        home_team=home,
        away_team=away,
        round_number=7,
        competition_type="regular_season",
        stage="regular_season",
        week=7,
        day_of_week="Sat",
    )
    match = _fake_match()

    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=user,
        home_score=70,
        away_score=70,
    )
    assert entry is not None
    assert entry["event_id"] == "meta-evt"
    assert entry["match_id"] == "meta-evt"
    assert entry["round"] == 7
    assert entry["competition_type"] == "regular_season"
    assert entry["stage"] == "regular_season"
    assert entry["week"] == 7
    assert entry["day_of_week"] == "Sat"
    assert entry["user_result"] == "D"
    assert entry["summary_line"].startswith("△")


def test_real_match_commentary_and_key_plays_smoke() -> None:
    teams = generate_teams()
    home, away = teams[0], teams[1]
    home.is_user_team = True
    match = Match(home_team=home, away_team=away, quiet=True)
    match.simulate()
    event = SeasonEvent(
        event_id="real-1",
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
    )
    entry = build_user_match_log_entry(
        match=match,
        event=event,
        user_team=home,
        home_score=80,
        away_score=75,
    )
    assert entry is not None
    assert entry["commentary_excerpt"]["total_lines"] > 0
    assert len(entry["key_plays"]) <= 8
