"""現金・RB のトレード評価換算（1対1 / multi 共通定数）。"""

from basketball_sim.systems.trade_logic import (
    compute_trade_asset_bonus,
    trade_cash_value_bonus,
    trade_rb_value_bonus,
)


def test_trade_cash_bonus_one_hundred_million():
    assert abs(trade_cash_value_bonus(100_000_000) - 10.0) < 1e-6


def test_trade_rb_bonus_forty_million():
    assert abs(trade_rb_value_bonus(40_000_000) - 7.2) < 1e-6


def test_compute_trade_asset_bonus_sum():
    v = compute_trade_asset_bonus(100_000_000, 40_000_000)
    assert abs(v - 17.2) < 1e-6
