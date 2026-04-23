"""
トレード入力用の変換・候補生成（表示・評価・実行は円整数のまま）。

現金: 億 + 万（万は 0/1000/…/9000 の 1000万円刻み）→ 円
RB: 万円ベースの数値 0,500,…,4000（500万円刻み）→ 円
"""

from __future__ import annotations

from typing import List

YEN_PER_OKU = 100_000_000
YEN_PER_CASH_MAN = 10_000  # 「万」の係数（6000 → 6000万円）
YEN_PER_RB_MAN = 10_000  # 500 → 500万円


def compose_cash_yen_from_oku_man(oku: int, man: int) -> int:
    """oku: 億の整数、man: 万円の数（例 5000=5000万円）。"""
    return int(oku) * YEN_PER_OKU + int(man) * YEN_PER_CASH_MAN


def max_oku_for_cash(max_cash_yen: int) -> int:
    return max(0, int(max_cash_yen) // YEN_PER_OKU)


def valid_cash_man_values_for_oku(max_cash_yen: int, oku: int) -> List[int]:
    """指定した億に対し、上限内かつ 0〜9000・1000刻みの万の係数一覧。"""
    mcy = int(max_cash_yen)
    if oku < 0:
        return []
    if oku * YEN_PER_OKU > mcy:
        return []
    rem = mcy - oku * YEN_PER_OKU
    max_man = min(9000, rem // YEN_PER_CASH_MAN)
    max_man = (max_man // 1000) * 1000
    return list(range(0, max_man + 1, 1000))


def cash_man_presets_all() -> List[int]:
    return list(range(0, 9000 + 1, 1000))


def rb_man_choice_values_filtered(max_rb_yen: int) -> List[int]:
    """500万円刻み（万表記 0,500,…,4000）、max_rb_yen 円以下のみ。"""
    cap = int(max_rb_yen)
    return [m for m in range(0, 4000 + 500, 500) if m * YEN_PER_RB_MAN <= cap]


def rb_yen_from_man(rb_man: int) -> int:
    return int(rb_man) * YEN_PER_RB_MAN
