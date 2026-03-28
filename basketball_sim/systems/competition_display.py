"""
大会の内部キー（competition_type 等）→ 本作の固定表示名。

正本: docs/SCHEDULE_MENU_SPEC_V1.md §1
GUI・日程表示はここ経由で統一し、シミュ本体の識別子は変更しない。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

# competition_type（主キー）→ 画面表示名
_COMPETITION_TYPE_LABEL_JA: dict[str, str] = {
    "regular_season": "日本リーグ",
    "emperor_cup": "全日本カップ",
    "easl": "東アジアカップ",
    "asia_cl": "アジアカップ",
    "intercontinental": "世界一決定戦",
    "playoff": "ディビジョンPO",
    "final_boss": "スペシャルマッチ",
}

CompetitionCategory = Literal["domestic_league", "domestic_cup", "international_club", "other"]


def competition_display_name(competition_type: Optional[str]) -> str:
    """competition_type を本作の固定日本語名に変換。未知は「未分類」。"""
    k = str(competition_type or "").strip().lower()
    if not k:
        return "—"
    return _COMPETITION_TYPE_LABEL_JA.get(k, "未分類")


def competition_category(competition_type: Optional[str]) -> CompetitionCategory:
    """日程フィルタ等用の粗い分類（表示専用ロジック）。"""
    k = str(competition_type or "").strip().lower()
    if k == "regular_season":
        return "domestic_league"
    if k in {"emperor_cup"}:
        return "domestic_cup"
    if k in {"easl", "asia_cl", "intercontinental", "final_boss"}:
        return "international_club"
    if k == "playoff":
        return "other"
    return "other"


def competition_display_name_from_event(event: Any) -> str:
    """SeasonEvent 等から competition_type を推して表示名を返す。"""
    ct = getattr(event, "competition_type", None)
    return competition_display_name(ct if ct is not None else None)
