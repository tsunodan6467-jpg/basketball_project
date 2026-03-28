"""
メインスポンサー契約（management 永続化・sponsor_power の弱い反映）。

正本のシーズン収入はオフシーズン `record_financial_result` と内訳。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §2.5 / §3。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

MANAGEMENT_VERSION = 1

# id, 表示名, スポンサー力が寄せる目標値（1〜100）
MAIN_SPONSOR_TYPES: Tuple[Dict[str, Any], ...] = (
    {"id": "local", "label": "地域・ローカル企業", "target_power": 44},
    {"id": "standard", "label": "スタンダードパートナー", "target_power": 52},
    {"id": "national", "label": "全国ブランド", "target_power": 60},
    {"id": "title", "label": "冠・トップティア", "target_power": 68},
)

MAIN_SPONSOR_IDS = frozenset(x["id"] for x in MAIN_SPONSOR_TYPES)
MAX_SPONSOR_HISTORY = 24


def _spec_for_type(type_id: str) -> Dict[str, Any]:
    for spec in MAIN_SPONSOR_TYPES:
        if spec["id"] == type_id:
            return spec
    return MAIN_SPONSOR_TYPES[1]


def label_for_main_sponsor_type(type_id: str) -> str:
    return str(_spec_for_type(type_id).get("label", type_id))


def ensure_sponsor_management_on_team(team: Any) -> None:
    if not hasattr(team, "management") or team.management is None or not isinstance(team.management, dict):
        team.management = {}
    mg = team.management
    mg["version"] = int(max(int(mg.get("version", 1) or 1), MANAGEMENT_VERSION))
    sp = mg.get("sponsors")
    if not isinstance(sp, dict):
        sp = {}
        mg["sponsors"] = sp
    cur = str(sp.get("main_contract_type") or "standard")
    if cur not in MAIN_SPONSOR_IDS:
        cur = "standard"
    sp["main_contract_type"] = cur
    hist = sp.get("history")
    if not isinstance(hist, list):
        hist = []
        sp["history"] = hist


def commit_main_sponsor_contract(team: Any, type_id: str) -> Tuple[bool, str]:
    if not bool(getattr(team, "is_user_team", False)):
        return False, "自チームのみメインスポンサー契約を変更できます。"
    tid = str(type_id or "").strip()
    if tid not in MAIN_SPONSOR_IDS:
        return False, "不明な契約タイプです。"

    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_sponsor_management_on_team(team)

    sp = team.management["sponsors"]
    prev = str(sp.get("main_contract_type", "standard"))
    if prev == tid:
        return True, f"既に「{label_for_main_sponsor_type(tid)}」がメイン契約です。"

    before = int(getattr(team, "sponsor_power", 50))
    before = max(1, min(100, before))
    target = int(_spec_for_type(tid)["target_power"])
    raw = int(round(before + (target - before) * 0.22))
    after = max(1, min(100, raw))
    if after == before and target != before:
        after = max(1, min(100, before + (1 if target > before else -1)))

    sp["main_contract_type"] = tid
    team.sponsor_power = after

    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "main_contract_type": tid,
        "label": label_for_main_sponsor_type(tid),
        "previous_type": prev,
        "sponsor_power_before": before,
        "sponsor_power_after": after,
    }
    hist = sp["history"]
    hist.append(entry)
    while len(hist) > MAX_SPONSOR_HISTORY:
        hist.pop(0)

    return (
        True,
        f"メイン契約を「{entry['label']}」に更新しました。"
        f"スポンサー力 {before} → {after}（次回オフシーズン締めのスポンサー収入内訳に反映されます）。",
    )


def format_sponsor_history_lines(team: Any, *, limit: int = 8) -> List[str]:
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_sponsor_management_on_team(team)
    sp = team.management.get("sponsors", {})
    hist = list(sp.get("history") or [])
    if not hist:
        return ["（契約変更履歴はまだありません）"]
    lines: List[str] = []
    lim = max(1, int(limit))
    for row in hist[-lim:]:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", "-"))
        before = row.get("sponsor_power_before", "-")
        after = row.get("sponsor_power_after", "-")
        at = str(row.get("at", ""))[:19].replace("T", " ")
        lines.append(f"- {at}  {label}  （力 {before}→{after}）")
    return lines
