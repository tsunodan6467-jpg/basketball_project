"""`main.validate_multi_trade_player_counts`（multi 人数ルール・CLI/GUI 共通）。"""

from basketball_sim.main import validate_multi_trade_player_counts


def test_validate_multi_trade_player_counts_ok_pairs():
    assert validate_multi_trade_player_counts(1, 1)[0]
    assert validate_multi_trade_player_counts(2, 2)[0]
    assert validate_multi_trade_player_counts(2, 3)[0]
    assert validate_multi_trade_player_counts(3, 2)[0]


def test_validate_multi_trade_player_counts_rejects_diff_over_one():
    ok, msg = validate_multi_trade_player_counts(3, 1)
    assert not ok
    assert "最大" in msg or "差" in msg


def test_validate_multi_trade_player_counts_rejects_out_of_range():
    assert not validate_multi_trade_player_counts(0, 1)[0]
    assert not validate_multi_trade_player_counts(1, 4)[0]
