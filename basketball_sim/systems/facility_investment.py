"""
施設投資（アリーナ・育成・メディカル・フロント）。

CLI（main.py）と GUI（main_menu_view）で共有する I/O なしのコア。
正本: docs/GM_MANAGEMENT_MENU_SPEC_V1.md（施設投資の GUI 接続）。
"""

from __future__ import annotations

from typing import Any, List, Tuple

FACILITY_LABELS = {
    "arena_level": "アリーナ",
    "training_facility_level": "トレーニング施設",
    "medical_facility_level": "メディカル施設",
    "front_office_level": "フロントオフィス",
}

FACILITY_BASE_COSTS = {
    "arena_level": 2_000_000,
    "training_facility_level": 1_200_000,
    "medical_facility_level": 1_000_000,
    "front_office_level": 900_000,
}

FACILITY_ORDER: Tuple[str, ...] = (
    "arena_level",
    "training_facility_level",
    "medical_facility_level",
    "front_office_level",
)

# Team._ensure_history_fields と整合（1〜10）
FACILITY_MAX_LEVEL = 10


def get_facility_upgrade_cost(team: Any, facility_key: str) -> int:
    current_level = int(getattr(team, facility_key, 1))
    base_cost = FACILITY_BASE_COSTS.get(facility_key, 1_000_000)
    return int(base_cost * max(1, current_level))


def can_commit_facility_upgrade(team: Any, facility_key: str) -> Tuple[bool, str]:
    """
    実行可否のみ（状態は変えない）。GUI のボタン活性やメッセージ用。
    戻り値: (可能か, ユーザー向け日本語メッセージ)
    """
    if facility_key not in FACILITY_BASE_COSTS:
        return False, "不明な施設です。"
    current = int(getattr(team, facility_key, 1))
    if current >= FACILITY_MAX_LEVEL:
        return False, "既に最大レベルです。"
    cost = get_facility_upgrade_cost(team, facility_key)
    money = int(getattr(team, "money", 0))
    if money < cost:
        return False, f"資金が不足しています（必要 {cost:,} 円）。"
    return True, ""


def commit_facility_upgrade(team: Any, facility_key: str) -> Tuple[bool, str]:
    """
    1 段階の投資を確定する（確認ダイアログは呼び出し側）。
    成功時のみ `record_financial_result` で支出を記録する。
    """
    ok, err = can_commit_facility_upgrade(team, facility_key)
    if not ok:
        return False, err

    label = FACILITY_LABELS.get(facility_key, facility_key)
    current_level = int(getattr(team, facility_key, 1))
    cost = get_facility_upgrade_cost(team, facility_key)

    setattr(team, facility_key, current_level + 1)

    if facility_key == "arena_level":
        team.popularity = int(getattr(team, "popularity", 0)) + 1
        team.fan_base = int(getattr(team, "fan_base", 0)) + 2
    elif facility_key == "training_facility_level":
        team.popularity = int(getattr(team, "popularity", 0)) + 1
    elif facility_key == "medical_facility_level":
        team.popularity = int(getattr(team, "popularity", 0)) + 1
    elif facility_key == "front_office_level":
        team.scout_level = int(getattr(team, "scout_level", 0)) + 3

    if hasattr(team, "record_financial_result"):
        team.record_financial_result(
            revenue=0,
            expense=cost,
            note=f"facility_upgrade:{facility_key}:Lv{current_level + 1}",
        )

    return True, f"{label} を Lv.{current_level} → Lv.{current_level + 1} に強化しました。"


def format_facility_status_lines(team: Any) -> List[str]:
    """CLI / ログ用のテキスト行（print しない）。"""
    lines: List[str] = []
    lines.append(f"現在資金: {int(getattr(team, 'money', 0)):,}円")
    lines.append("")
    for facility_key in FACILITY_ORDER:
        label = FACILITY_LABELS.get(facility_key, facility_key)
        level = int(getattr(team, facility_key, 1))
        upgrade_cost = get_facility_upgrade_cost(team, facility_key)
        lines.append(f"{label:<18} Lv.{level:<2} → 次回投資額 {upgrade_cost:,}円")
    lines.append("")
    lines.append(f"人気          : {int(getattr(team, 'popularity', 0))}")
    lines.append(f"ファン基盤      : {int(getattr(team, 'fan_base', 0))}")
    lines.append(f"スカウト水準    : {int(getattr(team, 'scout_level', 0))}")
    return lines
