"""
個別育成など CLI 用の選手要約行（表示のみ。成長・育成ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from basketball_sim.models.player import Player
from basketball_sim.systems.draft import (
    build_draft_candidate_role_shape_label,
    build_draft_candidate_strength_weakness_line,
)

_DEV_CLI_ATTR_KEYS: Tuple[str, ...] = (
    "three",
    "shoot",
    "drive",
    "passing",
    "rebound",
    "defense",
    "handling",
    "iq",
    "speed",
    "power",
    "stamina",
    "ft",
)

_DEV_CLI_ATTR_LABELS_JA: Dict[str, str] = {
    "three": "3P",
    "shoot": "シュート",
    "drive": "突破",
    "passing": "パス",
    "rebound": "リバ",
    "defense": "守備",
    "handling": "球さばき",
    "iq": "判断力",
    "speed": "スピード",
    "power": "フィジカル",
    "stamina": "スタミナ",
    "ft": "FT",
}


def _dev_cli_safe_int(player: Player, key: str) -> int:
    try:
        return int(getattr(player, key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def build_player_development_priority_label(player: Player) -> str:
    """優先育成 / 将来枠 / 即戦力化候補 / バランス型（簡易・表示のみ）。"""
    try:
        age = int(getattr(player, "age", 22) or 22)
        ovr = int(getattr(player, "ovr", 0) or 0)
        raw = str(getattr(player, "potential", "C") or "C").upper().strip()
        ch = raw[0] if raw else "C"
        if ch not in ("S", "A", "B", "C", "D"):
            ch = "C"
        ps = {"S": 92, "A": 78, "B": 64, "C": 52, "D": 40}.get(ch, 52)
    except Exception:
        return "情報なし"

    if ovr >= 67 or (ovr >= 64 and age >= 24):
        return "即戦力化候補"
    if ch in ("S", "A") and age <= 21 and ovr <= 62:
        return "優先育成"
    if (ch in ("S", "A", "B") and age <= 23 and ovr < 63) or (ps >= 70 and age <= 22 and ovr < 64):
        return "将来枠"
    return "バランス型"


def build_player_development_growth_focus_label(player: Player) -> str:
    """第二に低い能力（伸ばしどころの目安）。表示のみ。"""
    pairs: List[Tuple[str, int]] = [(k, _dev_cli_safe_int(player, k)) for k in _DEV_CLI_ATTR_KEYS]
    if len({v for _, v in pairs}) <= 1:
        return "情報なし"
    asc = sorted(pairs, key=lambda x: (x[1], x[0]))
    if len(asc) < 2:
        return "情報なし"
    k2 = asc[1][0]
    return _DEV_CLI_ATTR_LABELS_JA.get(k2, k2)


def format_player_development_cli_hint(player: Player) -> str:
    """個別育成一覧の補助1行。"""
    try:
        pri = build_player_development_priority_label(player)
        sw = build_draft_candidate_strength_weakness_line(player)
        grow = build_player_development_growth_focus_label(player)
        shape = build_draft_candidate_role_shape_label(player)
        return f"{pri} / {sw} / 伸ばしどころ:{grow} | {shape}"
    except Exception:
        return "情報なし"
