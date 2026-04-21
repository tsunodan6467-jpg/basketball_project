"""
金額の人間向け表示（内部の円整数は変更しない）。

100万円未満は切り捨て、最小表示単位は100万円（万円の整数倍）。
"""

from __future__ import annotations


def format_money_yen_ja_readable(yen: int) -> str:
    """
    円整数を 100万円単位で切り捨て、「〇〇万円」または「x億y万円」で返す。

    例: 6_000_000 → 「600万円」、102_000_000 → 「1億200万円」
    """
    y = int(yen)
    if y < 0:
        return "−" + format_money_yen_ja_readable(-y)
    truncated = (y // 1_000_000) * 1_000_000
    if truncated == 0:
        return "0万円"
    oku = truncated // 100_000_000
    man = (truncated % 100_000_000) // 10_000
    if oku == 0:
        return f"{man}万円"
    if man == 0:
        return f"{oku}億円"
    return f"{oku}億{man}万円"


def format_signed_money_yen_ja_readable(yen: int) -> str:
    """符号付き（+ / −）。0 は「0万円」。"""
    n = int(yen)
    if n == 0:
        return "0万円"
    if n > 0:
        return "+" + format_money_yen_ja_readable(n)
    return "−" + format_money_yen_ja_readable(-n)


# 呼び出し側の別名（指示書の名称に寄せる）
format_money_ja_rounded = format_money_yen_ja_readable
