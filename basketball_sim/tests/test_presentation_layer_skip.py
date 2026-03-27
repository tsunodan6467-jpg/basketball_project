"""PresentationLayer.skip_to_end の安全な読み飛ばし。"""

from basketball_sim.systems.presentation_layer import PresentationLayer


class _MatchStub:
    def __init__(self) -> None:
        self.play_sequence_log = [
            {"result_type": "made_2", "primary_player_name": "A", "home_score": 2, "away_score": 0},
            {"result_type": "made_2", "primary_player_name": "B", "home_score": 2, "away_score": 2},
        ]


def test_skip_to_end_moves_cursor_to_end():
    layer = PresentationLayer(_MatchStub())
    events = layer.build()
    assert len(events) >= 2
    assert layer.get_next_event() is not None
    layer.skip_to_end()
    assert layer.get_next_event() is None
    assert layer.presentation_index == len(events)
