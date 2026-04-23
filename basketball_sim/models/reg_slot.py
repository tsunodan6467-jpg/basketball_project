"""国内リーグ1試合分の schedule 文脈（schedule_care v1 用・RegSlot 受け渡し基盤）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegSlot:
    """
    同一 round 内の当該 Team にとけるレギュラーシーズン通算 N 戦目（1 始まり）と
    当該 SeasonEvent 由来の曜日補助。
    """

    round_index: int
    dow: str | None
