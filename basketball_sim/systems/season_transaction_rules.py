"""
レギュラー中のロスター移動（トレード・インシーズンFA）の可否。

ROUND_CONFIG（models/season.py）の月対応に合わせ、3月第2週終了（ラウンド22消化後）から
シーズン終了までロックする。オフシーズンは season が無いか season_finished で解放。
"""

from __future__ import annotations

from typing import Any, Optional

from basketball_sim.config.game_constants import REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND


def inseason_roster_moves_unlocked(season: Optional[Any]) -> bool:
    """
    シーズン中にユーザー/CPU がトレードやインシーズンFAを行ってよいか。

    - season is None: 年度メニュー等（オフシーズン想定）→ 可
    - season_finished: シーズン締め済み → 可（次ループは Offseason）
    - それ以外: 消化済みラウンド数がカットオフ未満なら可
    """
    if season is None:
        return True
    if getattr(season, "season_finished", False):
        return True
    cr = int(getattr(season, "current_round", 0) or 0)
    return cr < REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND


def cpu_inseason_fa_allowed_for_simulated_round(round_number: int) -> bool:
    """simulate_next_round で処理するラウンド番号（1始まり）で CPU FA を走らせるか。"""
    return int(round_number) <= REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND


# CLI 用（main.py）
INSEASON_TRADE_LOCK_MESSAGE_JA = (
    "トレード期限を過ぎています（3月第2週終了・ラウンド22消化後はシーズン終了まで不可）。"
)
