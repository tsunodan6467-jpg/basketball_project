"""
Steamworks 実績の API 名（Steam パートナー画面の Achievement → API Name と完全一致）。

運用:
- ダッシュボードで実績を追加したら、ここに同じ文字列を `frozenset` に追加する。
- 空の frozenset のときは名前チェックを行わない（開発中・プロトタイプ用）。
- リリース前は空でなく、定義済み名だけに給することを推奨（タイポで無言失敗しにくい）。

ゲーム内では `steamworks_bridge.unlock_achievement` のみを呼ぶ。
"""

from __future__ import annotations

STEAM_ACHIEVEMENT_API_NAMES: frozenset[str] = frozenset({
    "ACH_PHASE0_TEST",
})
