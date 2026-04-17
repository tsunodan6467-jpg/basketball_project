"""
経営ウィンドウ・CLI 向けの財務レポート整形（内訳・履歴）。

正本の revenue / expense / money は Team.record_financial_result に従う。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §0.3（内訳スナップショット）参照。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_FINANCE_HISTORY_DISPLAY_LIMIT = 5
DEFAULT_INSEASON_CASH_LOG_DISPLAY_LIMIT = 40

# Team.inseason_cash_round_log の key → GUI 表示ラベル（内部キーはユーザーにそのまま出さない）
INSEASON_CASH_KEY_LABELS_JA: Dict[str, str] = {
    "inseason_league_distribution_round": "リーグ分配等",
    "inseason_matchday_estimate_round": "主場・門前概算",
}

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


def format_inseason_cash_round_log_lines(
    team: Any,
    *,
    max_entries: int = DEFAULT_INSEASON_CASH_LOG_DISPLAY_LIMIT,
) -> List[str]:
    """
    経営ウィンドウ「シーズン中収益（記録）」用。
    `finance_history` / 正本とは別リスト（`INSEASON_REVENUE_KEY_POLICY.md`）。
    """
    getter = getattr(team, "_ensure_history_fields", None)
    if callable(getter):
        try:
            getter()
        except Exception:
            pass

    raw = getattr(team, "inseason_cash_round_log", None)
    if not isinstance(raw, list) or not raw:
        return [
            "まだ記録はありません。",
            "（シーズンを進めると、ラウンドごとにここへ追記されます）",
        ]

    rows: List[Dict[str, Any]] = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        try:
            rn = int(e.get("round_number", -1))
            amt = int(e.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if rn < 0:
            continue
        k = str(e.get("key", "") or "")
        rows.append({"round_number": rn, "amount": amt, "key": k})

    if not rows:
        return [
            "まだ記録はありません。",
            "（シーズンを進めると、ラウンドごとにここへ追記されます）",
        ]

    rows.sort(key=lambda r: (int(r["round_number"]), int(r["amount"])))
    lim = max(1, int(max_entries))
    tail = rows[-lim:]
    if len(rows) > lim:
        header = f"直近 {lim} 件（古い順・全 {len(rows)} 件中）"
    else:
        header = "記録一覧（古い順）"

    out: List[str] = [header, ""]
    for r in tail:
        label = INSEASON_CASH_KEY_LABELS_JA.get(str(r["key"]), "その他")
        out.append(f"R{int(r['round_number'])}  {label}  +{int(r['amount']):,}円")
    out.append("")
    out.append("※年次の財務レポート（前季収支）とは別枠です。")
    return out


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


def format_cli_finance_screen_header_lines(team: Any) -> List[str]:
    """
    CLI「財務レポート」先頭用: 現状サマリーと主要内訳（表示のみ・数値ロジックは変更しない）。
    """
    getter = getattr(team, "_ensure_history_fields", None)
    if callable(getter):
        try:
            getter()
        except Exception:
            pass

    lines: List[str] = []
    try:
        money = int(getattr(team, "money", 0) or 0)
        rev = int(getattr(team, "revenue_last_season", 0) or 0)
        exp = int(getattr(team, "expense_last_season", 0) or 0)
        cf = int(getattr(team, "cashflow_last_season", 0) or 0)
        fh_raw = getattr(team, "finance_history", None) or []
        fh = list(fh_raw) if isinstance(fh_raw, list) else []
        n_fin = len(fh)

        lines.append("【財務サマリー】")
        lines.append(f"所持金: {money:,}円")

        if rev == 0 and exp == 0 and cf == 0:
            lines.append("前季収支: 未更新")
        elif cf > 0:
            lines.append(f"前季収支: {cf:+,}円（黒字）")
        elif cf < 0:
            lines.append(f"前季収支: {cf:+,}円（赤字）")
        else:
            lines.append(f"前季収支: {cf:+,}円（収支均衡）")

        lines.append(f"財務履歴: {n_fin}件" if n_fin else "財務履歴: 履歴なし")
        lines.append("")
        lines.append("【主要内訳】")

        snap = _latest_breakdown_entry(fh)
        if snap is not None:
            rtot = int(snap.get("revenue", 0))
            etot = int(snap.get("expense", 0))
            br = normalize_breakdown_dict(snap.get("breakdown_revenue"))
            be = normalize_breakdown_dict(snap.get("breakdown_expense"))
            lines.append(f"直近収入合計: {rtot:,}円")
            lines.append(f"直近支出合計: {etot:,}円")
            if br and breakdown_matches_total(rtot, br):
                top_r = sorted(br.items(), key=lambda x: -x[1])[:2]
                r_labels = " / ".join(REV_LABELS_JA.get(str(k), str(k)) for k, _ in top_r)
                lines.append(f"主な収入: {r_labels}")
            else:
                lines.append("主な収入: 情報なし")
            if be and breakdown_matches_total(etot, be):
                top_e = sorted(be.items(), key=lambda x: -x[1])[:2]
                e_labels = " / ".join(EXP_LABELS_JA.get(str(k), str(k)) for k, _ in top_e)
                lines.append(f"主な支出: {e_labels}")
            else:
                lines.append("主な支出: 情報なし")
        elif fh:
            last = fh[-1]
            if isinstance(last, dict):
                try:
                    rtot = int(last.get("revenue", 0) or 0)
                    etot = int(last.get("expense", 0) or 0)
                    lines.append(f"直近収入合計: {rtot:,}円")
                    lines.append(f"直近支出合計: {etot:,}円")
                    lines.append("主な収入: 情報なし")
                    lines.append("主な支出: 情報なし")
                except (TypeError, ValueError):
                    lines.append("情報なし")
            else:
                lines.append("情報なし")
        else:
            lines.append("情報なし")

        lines.append("")
        return lines
    except Exception:
        return [
            "【財務サマリー】",
            "情報なし",
            "",
            "【主要内訳】",
            "情報なし",
            "",
        ]
