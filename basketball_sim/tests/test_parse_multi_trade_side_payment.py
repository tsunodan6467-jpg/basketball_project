"""`main.parse_multi_trade_side_payment`（multi 現金・RB 入力・CLI/GUI 共通趣旨）。"""

from basketball_sim.main import parse_multi_trade_side_payment


def test_parse_cash_empty_is_zero():
    ok, v, msg = parse_multi_trade_side_payment("", 1_000_000, is_cash=True)
    assert ok and v == 0 and msg == ""


def test_parse_cash_comma_and_spaces():
    ok, v, _ = parse_multi_trade_side_payment(" 1,234,567 ", 2_000_000, is_cash=True)
    assert ok and v == 1_234_567


def test_parse_cash_over_limit():
    ok, v, msg = parse_multi_trade_side_payment("100", 50, is_cash=True)
    assert not ok and v == 0 and "円" in msg


def test_parse_rb_negative():
    ok, _, _ = parse_multi_trade_side_payment("-1", 100, is_cash=False)
    assert not ok


def test_parse_invalid_not_integer():
    ok, _, msg = parse_multi_trade_side_payment("12a", 100, is_cash=True)
    assert not ok and "整数" in msg


def test_parse_rb_over_limit_message_no_yen_suffix():
    ok, _v, msg = parse_multi_trade_side_payment("999", 10, is_cash=False)
    assert not ok
    assert "円" not in msg
