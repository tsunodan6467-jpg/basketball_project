"""
GM の戦術・HC・起用の選択肢と安全な反映（CLI / GUI 共通）。

main.py の定義をここへ集約する。
"""

from __future__ import annotations

from typing import Any, List, Tuple

# (内部キー, 表示ラベル)
STRATEGY_OPTIONS: List[Tuple[str, str]] = [
    ("balanced", "バランス"),
    ("run_and_gun", "ラン＆ガン"),
    ("three_point", "スリーポイント偏重"),
    ("defense", "守備重視"),
    ("inside", "インサイド"),
]

COACH_STYLE_OPTIONS: List[Tuple[str, str]] = [
    ("balanced", "バランス"),
    ("offense", "攻撃重視"),
    ("defense", "守備重視"),
    ("development", "育成"),
]

USAGE_POLICY_OPTIONS: List[Tuple[str, str]] = [
    ("balanced", "バランス"),
    ("win_now", "勝利優先（今を勝つ）"),
    ("development", "育成・若手優先"),
]


def apply_team_gm_settings(
    team: Any,
    strategy: str,
    coach_style: str,
    usage_policy: str,
) -> Tuple[bool, str]:
    """
    戦術・HC・起用を Team に反映。値はホワイトリストのみ。

    Returns:
        (成功, 失敗時メッセージ)
    """
    valid_s = {k for k, _ in STRATEGY_OPTIONS}
    valid_c = {k for k, _ in COACH_STYLE_OPTIONS}
    valid_u = {k for k, _ in USAGE_POLICY_OPTIONS}
    if strategy not in valid_s:
        return False, "戦術の値が不正です。"
    if coach_style not in valid_c:
        return False, "HCスタイルの値が不正です。"
    if usage_policy not in valid_u:
        return False, "起用方針の値が不正です。"

    team.strategy = strategy
    team.coach_style = coach_style
    if hasattr(team, "set_usage_policy"):
        team.set_usage_policy(usage_policy)
    else:
        team.usage_policy = usage_policy
    return True, ""
