"""build_highlight_playlist_events / build_highlight_override_events_from_match の安全テスト。"""

from basketball_sim.systems.highlight_selector import (
    HIGHLIGHT_DEFAULT_MAX_EVENTS,
    build_highlight_override_events_from_match,
    build_highlight_playlist_events,
)
from basketball_sim.systems.presentation_layer import PresentationLayer


class _MatchStub:
    def __init__(self) -> None:
        self.play_sequence_log = [
            {
                "result_type": "made_2",
                "primary_player_name": "A",
                "quarter": 1,
                "clock_seconds": 600,
                "home_score": 2,
                "away_score": 0,
            },
            {
                "result_type": "made_3",
                "primary_player_name": "B",
                "quarter": 1,
                "clock_seconds": 580,
                "home_score": 2,
                "away_score": 3,
            },
            {
                "result_type": "made_2",
                "primary_player_name": "A",
                "quarter": 2,
                "clock_seconds": 400,
                "home_score": 4,
                "away_score": 3,
            },
        ]


def test_build_highlight_playlist_preserves_timeline_order():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    assert len(all_events) >= 3
    short = build_highlight_playlist_events(all_events, max_events=2, min_score=0)
    assert len(short) == 2
    nos = [e.get("play_no", -1) for e in short]
    assert nos == sorted(nos)


def test_build_highlight_from_match_returns_subset():
    out = build_highlight_override_events_from_match(_MatchStub(), max_events=HIGHLIGHT_DEFAULT_MAX_EVENTS)
    layer = PresentationLayer(_MatchStub())
    full = layer.build()
    assert len(out) <= len(full)
    assert len(out) <= HIGHLIGHT_DEFAULT_MAX_EVENTS
