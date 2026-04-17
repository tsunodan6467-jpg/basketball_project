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

# CLI 候補比較用の短文（表示のみ。target_power 等の数値ロジックは変更しない）
MAIN_SPONSOR_CLI_COMPARISON_HINTS: Dict[str, str] = {
    "local": "地元密着・安定寄り（スポンサー力は控えめ寄り）",
    "standard": "バランス型・はじめて向けの標準契約",
    "national": "全国ブランド・収入・スポンサー力ともに強め",
    "title": "大型冠・スポンサー力最大化寄り",
}


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


def format_sponsor_apply_preview_line(team: Any, type_id: str) -> str:
    """
    「メイン契約を反映」1行プレビュー（状態は変えない）。
    コストは現仕様どおり 0（所持金からの即時減算なし）。
    """
    if team is None:
        return "未設定（チーム未接続）／実行不可"
    if not bool(getattr(team, "is_user_team", False)):
        return "自チームのみ／実行不可"
    tid = str(type_id or "").strip()
    if tid not in MAIN_SPONSOR_IDS:
        return "契約種別が未設定／実行不可"
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_sponsor_management_on_team(team)
    sp = team.management["sponsors"]
    prev = str(sp.get("main_contract_type", "standard"))
    lab = label_for_main_sponsor_type(tid)
    if prev == tid:
        return f"費用なし・既に「{lab}」／反映しても変更なし（実行可だが効果なし）"
    before = int(getattr(team, "sponsor_power", 50))
    before = max(1, min(100, before))
    target = int(_spec_for_type(tid)["target_power"])
    raw = int(round(before + (target - before) * 0.22))
    after = max(1, min(100, raw))
    if after == before and target != before:
        after = max(1, min(100, before + (1 if target > before else -1)))
    return (
        f"費用なし・「{lab}」へ切替想定でスポンサー力 {before}→{after} 見込み"
        f"（次回オフのスポンサー収入内訳に反映）／実行可"
    )


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


def format_cli_sponsor_management_screen_lines(team: Any) -> List[str]:
    """
    CLI メインスポンサー画面用（サマリー＋候補比較）。読み取り中心（ensure は呼ばない）。
    """
    if team is None:
        return [
            "【スポンサーサマリー】",
            "現在契約: 情報なし",
            "契約状態: 情報なし",
            "スポンサー力: 情報なし",
            "履歴: 履歴なし",
            "直近更新: 情報なし",
            "",
            "【候補比較】",
            "情報なし",
            "",
        ]

    tid = ""
    n_hist = 0
    latest_line = "直近更新: 履歴なし"
    try:
        mg = getattr(team, "management", None)
        if isinstance(mg, dict):
            sp = mg.get("sponsors")
            if isinstance(sp, dict):
                tid = str(sp.get("main_contract_type") or "").strip()
                sh = sp.get("history")
                if isinstance(sh, list):
                    n_hist = len(sh)
                    if sh:
                        row = sh[-1]
                        if isinstance(row, dict):
                            lab = str(row.get("label") or "").strip() or "情報なし"
                            prev = str(row.get("previous_type") or "").strip()
                            at = str(row.get("at") or "").strip()
                            at_disp = at[:19].replace("T", " ") if at else ""
                            chg = f"（前: {prev}）" if prev else ""
                            if at_disp:
                                latest_line = f"直近更新: {at_disp} {lab}{chg}"
                            else:
                                latest_line = f"直近更新: {lab}{chg}"
    except Exception:
        tid = ""
        n_hist = 0
        latest_line = "直近更新: 情報なし"

    if tid and tid in MAIN_SPONSOR_IDS:
        try:
            cur_label = label_for_main_sponsor_type(tid)
        except Exception:
            cur_label = tid
        state = "契約中"
    elif tid:
        cur_label = tid
        state = "情報なし"
    else:
        cur_label = "未設定"
        state = "未設定"

    try:
        spow = int(getattr(team, "sponsor_power", 0) or 0)
        spow = max(1, min(100, spow))
        pow_line = f"スポンサー力: {spow} / 100"
    except (TypeError, ValueError):
        pow_line = "スポンサー力: 情報なし"

    hist_disp = f"{n_hist}件" if n_hist > 0 else "履歴なし"

    lines: List[str] = [
        "【スポンサーサマリー】",
        f"現在契約: {cur_label}",
        f"契約状態: {state}",
        pow_line,
        f"履歴: {hist_disp}",
        latest_line,
        "",
        "【候補比較】",
    ]
    for i, spec in enumerate(MAIN_SPONSOR_TYPES, start=1):
        sid = str(spec.get("id", "") or "")
        lab = str(spec.get("label", sid) or sid)
        hint = MAIN_SPONSOR_CLI_COMPARISON_HINTS.get(sid, "情報なし")
        mark = "（現在）" if sid and sid == tid else ""
        lines.append(f"{i}. {lab}{mark}  …  {hint}")
    lines.append("")
    return lines


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
