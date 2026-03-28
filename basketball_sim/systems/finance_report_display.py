"""
経営ウィンドウ・CLI 向けの財務レポート整形（内訳・履歴）。

正本の revenue / expense / money は Team.record_financial_result に従う。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §0.3（内訳スナップショット）参照。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_FINANCE_HISTORY_DISPLAY_LIMIT = 5

REV_LABELS_JA: Dict[str, str] = {
    "gate": "チケット・興行",
    "sponsor": "スポンサー",
    "merchandise": "グッズ・物販",
    "media": "メディア・分配金",
    "performance_bonus": "成績ボーナス",
}

EXP_LABELS_JA: Dict[str, str] = {
    "payroll": "選手給与（年俸）",
    "facility_maintenance": "施設維持費",
    "scouting_and_ops": "スカウト・運用",
    "travel": "遠征・移動費",
    "league_fee": "リーグ・登録費",
    "admin": "管理・事務",
    "game_ops": "試合運営",
    "underperformance_penalty": "成績不振ペナルティ",
    "fan_service": "ファンサービス",
    "luxury_tax": "ラグジュアリータックス",
}


def normalize_breakdown_dict(raw: Any) -> Optional[Dict[str, int]]:
    if not isinstance(raw, dict) or not raw:
        return None
    out: Dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return out or None


def breakdown_matches_total(total: int, bd: Optional[Dict[str, int]]) -> bool:
    if bd is None:
        return False
    return sum(bd.values()) == int(total)


def format_finance_report_detail_lines(
    team: Any,
    *,
    history_limit: int = DEFAULT_FINANCE_HISTORY_DISPLAY_LIMIT,
) -> List[str]:
    """経営ウィンドウ「詳細レポート」用の行リスト。"""
    getter = getattr(team, "_ensure_history_fields", None)
    if callable(getter):
        try:
            getter()
        except Exception:
            pass

    history = list(getattr(team, "finance_history", None) or [])
    lines: List[str] = []

    snapshot = _latest_breakdown_entry(history)
    if snapshot is not None:
        rev = int(snapshot.get("revenue", 0))
        exp = int(snapshot.get("expense", 0))
        br = normalize_breakdown_dict(snapshot.get("breakdown_revenue"))
        be = normalize_breakdown_dict(snapshot.get("breakdown_expense"))
        lines.append("【収入内訳】（記録済みスナップショット）")
        if br and breakdown_matches_total(rev, br):
            for key in sorted(br.keys(), key=lambda x: (REV_LABELS_JA.get(x, x), x)):
                label = REV_LABELS_JA.get(key, key)
                lines.append(f"  {label}: {br[key]:,} 円")
            lines.append(f"  合計: {rev:,} 円")
        else:
            lines.append("  （内訳データなし・旧セーブ等）")
        lines.append("")
        lines.append("【支出内訳】（記録済みスナップショット）")
        if be and breakdown_matches_total(exp, be):
            for key in sorted(be.keys(), key=lambda x: (EXP_LABELS_JA.get(x, x), x)):
                label = EXP_LABELS_JA.get(key, key)
                lines.append(f"  {label}: {be[key]:,} 円")
            lines.append(f"  合計: {exp:,} 円")
        else:
            lines.append("  （内訳データなし・旧セーブ等）")
    else:
        lines.append("【収入・支出内訳】")
        lines.append("  内訳スナップショットはまだありません。")
        lines.append("  （オフシーズンの財務締め後に、収支と整合した内訳が記録されます）")

    lines.append("")
    lim = max(1, int(history_limit))
    lines.append(f"【財務推移】直近 {lim} 件（古い順）")
    if not history:
        lines.append("  （履歴なし）")
    else:
        tail = history[-lim:]
        for idx, entry in enumerate(tail, start=1):
            if not isinstance(entry, dict):
                continue
            r = int(entry.get("revenue", 0))
            e = int(entry.get("expense", 0))
            cf = int(entry.get("cashflow", r - e))
            note = str(entry.get("note", "") or "").replace("\n", " ")
            if len(note) > 48:
                note = note[:45] + "…"
            lines.append(f"  {idx}. 収入 {r:,} / 支出 {e:,} / 収支 {cf:+,} ｜ {note or '—'}")

    lines.append("")
    lines.append("【見込み】")
    lines.append("  来季の数値見込みは週次会計導入後に表示予定です。")

    return lines


def _latest_breakdown_entry(history: List[Any]) -> Optional[dict]:
    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        br = normalize_breakdown_dict(entry.get("breakdown_revenue"))
        be = normalize_breakdown_dict(entry.get("breakdown_expense"))
        if br and be and breakdown_matches_total(int(entry.get("revenue", 0)), br):
            if breakdown_matches_total(int(entry.get("expense", 0)), be):
                return entry
    return None
