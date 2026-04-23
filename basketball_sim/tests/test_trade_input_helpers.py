"""trade_input_helpers: 億+万→円、RB 万選択→円（入力層のみ）。"""

from basketball_sim.systems.trade_input_helpers import (
    cash_man_presets_all,
    compose_cash_yen_from_oku_man,
    max_oku_for_cash,
    rb_man_choice_values_filtered,
    rb_yen_from_man,
    valid_cash_man_values_for_oku,
)


def test_compose_cash_examples() -> None:
    assert compose_cash_yen_from_oku_man(1, 5000) == 150_000_000
    assert compose_cash_yen_from_oku_man(0, 6000) == 60_000_000
    assert compose_cash_yen_from_oku_man(3, 0) == 300_000_000


def test_max_oku_for_cash() -> None:
    assert max_oku_for_cash(350_000_000) == 3
    assert max_oku_for_cash(99_999_999) == 0
    assert max_oku_for_cash(0) == 0


def test_valid_cash_man_values_for_oku_caps() -> None:
    # 3.5億 cap: 3億なら残り5000万 → 万係数最大5000
    v = valid_cash_man_values_for_oku(350_000_000, 3)
    assert v == [0, 1000, 2000, 3000, 4000, 5000]
    # 3億ちょうど: 3億なら万は0のみ
    v2 = valid_cash_man_values_for_oku(300_000_000, 3)
    assert v2 == [0]


def test_cash_man_presets_all() -> None:
    p = cash_man_presets_all()
    assert p[0] == 0 and p[-1] == 9000 and len(p) == 10


def test_rb_man_choice_values_filtered() -> None:
    assert rb_man_choice_values_filtered(0) == [0]
    # 万表示 2500=2500万円ちょうどまで許容
    assert rb_man_choice_values_filtered(25_000_000) == [0, 500, 1000, 1500, 2000, 2500]
    assert rb_man_choice_values_filtered(24_000_000) == [0, 500, 1000, 1500, 2000]
    assert rb_man_choice_values_filtered(40_000_000) == list(range(0, 4000 + 500, 500))


def test_rb_yen_from_man() -> None:
    assert rb_yen_from_man(500) == 5_000_000
    assert rb_yen_from_man(4000) == 40_000_000
