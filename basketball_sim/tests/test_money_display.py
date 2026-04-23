from basketball_sim.systems.money_display import (
    format_money_yen_ja_readable,
    format_signed_money_yen_ja_readable,
)


def test_six_million():
    assert format_money_yen_ja_readable(6_000_000) == "600万円"


def test_fifteen_million():
    assert format_money_yen_ja_readable(15_000_000) == "1500万円"


def test_ninety_eight_million():
    assert format_money_yen_ja_readable(98_000_000) == "9800万円"


def test_one_oku_two_hundred_man():
    assert format_money_yen_ja_readable(102_000_000) == "1億200万円"


def test_one_oku_fifteen_hundred_man():
    assert format_money_yen_ja_readable(115_000_000) == "1億1500万円"


def test_five_oku_three_thousand_man():
    assert format_money_yen_ja_readable(530_000_000) == "5億3000万円"


def test_floor_under_one_million():
    assert format_money_yen_ja_readable(999_999) == "0万円"


def test_negative():
    assert format_money_yen_ja_readable(-6_000_000) == "−600万円"


def test_signed_positive():
    assert format_signed_money_yen_ja_readable(115_000_000) == "+1億1500万円"


def test_signed_negative():
    assert format_signed_money_yen_ja_readable(-6_000_000) == "−600万円"
