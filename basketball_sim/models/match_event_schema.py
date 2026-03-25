"""
Match.play_by_play_log に積まれるイベント辞書の「形」のドキュメント（Phase 0）。

実装は Match._record_event が唯一の正。ここは TypedDict で IDE 補助と契約の固定用。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class PlayByPlayEvent(TypedDict, total=False):
    """1 プレー相当の構造化ログ（必須でないキーは NotRequired）。"""

    quarter: int
    clock_seconds: int
    possession_no: int
    offense_team_id: Optional[Any]
    defense_team_id: Optional[Any]
    event_type: str
    primary_player_id: Optional[Any]
    primary_player_name: Optional[str]
    secondary_player_id: Optional[Any]
    secondary_player_name: Optional[str]
    description_key: str
    home_score: int
    away_score: int
    meta: Dict[str, Any]


# 将来: commentary_log / play_sequence_log も同様に TypedDict 化可能

__all__ = ["PlayByPlayEvent", "PlayByPlayLog"]

PlayByPlayLog = List[PlayByPlayEvent]
