"""
Godot 財務サマリー（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk 仮 GUI には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team の財務系スカラー・finance_history を getattr / dict 取得のみで読む
  （代入・履歴の append・財務記録の確定 API・pickle セーブの上書きは行わない）。
- finance_report_display の format_* は _ensure_history_fields を呼び得るため、
  本モジュールでは利用しない（純粋な money 表示ヘルパのみ import）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SCREEN_TITLE = "財務サマリー（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。予算変更・投資・契約更新などの操作は含みません。",
]

NOTE_NO_TEAM = "チーム情報が未接続のため、財務情報の一部は表示できません。"


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


def _int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _team_display_name(team: Any) -> str:
    if team is None:
        return "-"
    n = _safe_get(team, "name", None)
    if isinstance(n, str) and n.strip():
        return n.strip()
    return "-"


def _league_level_optional(team: Any) -> Any:
    if team is None:
        return None
    lv = _safe_get(team, "league_level", None)
    if lv is None:
        return None
    try:
        return int(lv)
    except (TypeError, ValueError):
        return None


def _format_money_label(amount: Optional[int]) -> str:
    if amount is None:
        return "-"
    try:
        from basketball_sim.systems.money_display import format_money_yen_ja_readable

        return format_money_yen_ja_readable(int(amount))
    except Exception:
        return "-"


def _format_signed_money_label(amount: Optional[int]) -> str:
    if amount is None:
        return "-"
    try:
        from basketball_sim.systems.money_display import format_signed_money_yen_ja_readable

        return format_signed_money_yen_ja_readable(int(amount))
    except Exception:
        return "-"


def _payroll_total(team: Any) -> Optional[int]:
    if team is None:
        return None
    try:
        from basketball_sim.systems.contract_logic import get_team_payroll

        return int(get_team_payroll(team))
    except Exception:
        players = _safe_get(team, "players", None) or []
        if not isinstance(players, (list, tuple)):
            return None
        total = 0
        for p in players:
            v = _int_optional(_safe_get(p, "salary", None))
            if v is not None and v > 0:
                total += v
        return total


def _soft_salary_cap(team: Any) -> Optional[int]:
    if team is None:
        return None
    try:
        from basketball_sim.systems.salary_cap_budget import get_soft_cap, league_level_for_team

        lv = league_level_for_team(team)
        return int(get_soft_cap(league_level=lv))
    except Exception:
        return None


def _finance_history_list(team: Any) -> List[Any]:
    if team is None:
        return []
    raw = _safe_get(team, "finance_history", None)
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    return []


def _history_entry_mapping(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        return entry
    return {
        "season_label": getattr(entry, "season_label", None),
        "revenue": getattr(entry, "revenue", None),
        "expense": getattr(entry, "expense", None),
        "cashflow": getattr(entry, "cashflow", None),
        "note": getattr(entry, "note", None),
    }


def _build_history_rows(
    team: Any,
    *,
    max_history: int,
) -> List[Dict[str, Any]]:
    """
    履歴はストレージ順のまま、末尾から最大 max_history 件を返す（並べ替えない）。
    """
    hist = _finance_history_list(team)
    total = len(hist)
    lim = max(1, int(max_history))
    tail = hist[-lim:] if hist else []
    rows: List[Dict[str, Any]] = []
    for i, entry in enumerate(tail, start=1):
        m = _history_entry_mapping(entry)
        rev = _int_optional(m.get("revenue"))
        exp = _int_optional(m.get("expense"))
        cf_raw = m.get("cashflow", None)
        cf = _int_optional(cf_raw)
        if cf is None and rev is not None and exp is not None:
            cf = int(rev) - int(exp)
        season = m.get("season_label", None)
        season_s = str(season).strip() if season is not None else ""
        note_raw = m.get("note", None)
        note_s = str(note_raw).replace("\n", " ").strip() if note_raw is not None else ""
        rows.append(
            {
                "order": i,
                "season": season_s if season_s else None,
                "label": season_s if season_s else "-",
                "revenue": rev,
                "revenue_label": _format_money_label(rev),
                "expense": exp,
                "expense_label": _format_money_label(exp),
                "cashflow": cf,
                "cashflow_label": _format_signed_money_label(cf),
                "memo": note_s if note_s else "-",
            }
        )
    return rows


def _finance_item(
    key: str,
    label: str,
    value: Any,
    display_value: str,
    memo: str = "",
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display_value": display_value,
        "memo": memo,
    }


def build_finance_summary_readonly_dict(
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_history: int = 5,
) -> Dict[str, Any]:
    """
    Godot 向け財務サマリー dict（読み取り専用）。

    team が None でも例外にしない。
    finance_history は並べ替えず、末尾 max_history 件のみ history_rows に含める。
    """
    notes = list(DEFAULT_NOTES)
    if team is None:
        notes.append(NOTE_NO_TEAM)

    team_name = _team_display_name(team)
    league_level = _league_level_optional(team)

    money = _int_optional(_safe_get(team, "money", None)) if team is not None else None
    revenue_ls = _int_optional(_safe_get(team, "revenue_last_season", None)) if team is not None else None
    expense_ls = _int_optional(_safe_get(team, "expense_last_season", None)) if team is not None else None
    cashflow_ls = _int_optional(_safe_get(team, "cashflow_last_season", None)) if team is not None else None

    payroll = _payroll_total(team)
    cap_soft = _soft_salary_cap(team)
    cap_room: Optional[int] = None
    if cap_soft is not None and payroll is not None:
        cap_room = int(cap_soft) - int(payroll)

    hist_full = _finance_history_list(team)
    hist_count = len(hist_full)
    history_rows = _build_history_rows(team, max_history=max_history)
    displayed = len(history_rows)

    summary: Dict[str, Any] = {
        "money": money,
        "money_label": _format_money_label(money),
        "revenue_last_season": revenue_ls,
        "revenue_last_season_label": _format_money_label(revenue_ls),
        "expense_last_season": expense_ls,
        "expense_last_season_label": _format_money_label(expense_ls),
        "cashflow_last_season": cashflow_ls,
        "cashflow_last_season_label": _format_signed_money_label(cashflow_ls),
        "salary_cap": cap_soft,
        "salary_cap_label": _format_money_label(cap_soft),
        "salary_total": payroll,
        "salary_total_label": _format_money_label(payroll),
        "salary_cap_room": cap_room,
        "salary_cap_room_label": _format_signed_money_label(cap_room) if cap_room is not None else "-",
        "finance_history_count": hist_count,
        "has_finance_history": hist_count > 0,
        "season_count": season_count,
        "at_annual_menu": at_annual_menu,
    }

    finance_items: List[Dict[str, Any]] = [
        _finance_item("money", "現在資金", money, _format_money_label(money)),
        _finance_item("revenue_last_season", "前季収入", revenue_ls, _format_money_label(revenue_ls)),
        _finance_item("expense_last_season", "前季支出", expense_ls, _format_money_label(expense_ls)),
        _finance_item("cashflow_last_season", "前季収支", cashflow_ls, _format_signed_money_label(cashflow_ls)),
        _finance_item("salary_cap", "サラリー上限（ソフトキャップ）", cap_soft, _format_money_label(cap_soft)),
        _finance_item("salary_total", "選手年俸合計", payroll, _format_money_label(payroll)),
        _finance_item(
            "salary_cap_room",
            "サラリー余力（上限−年俸合計）",
            cap_room,
            _format_signed_money_label(cap_room) if cap_room is not None else "-",
        ),
    ]

    ctx_parts: List[str] = []
    if season_count is not None:
        ctx_parts.append(f"セーブ上のシーズン回数: {season_count}")
    if at_annual_menu is True:
        ctx_parts.append("年度メニュー直後のセーブの可能性があります。")
    ctx_line = " / ".join(ctx_parts) if ctx_parts else None

    lines_overview: List[str] = [f"クラブ: {team_name}"]
    if ctx_line:
        lines_overview.append(ctx_line)
    lines_overview.extend(
        [
            f"現在資金: {summary['money_label']}",
            f"サラリー上限: {summary['salary_cap_label']}",
            f"選手年俸合計: {summary['salary_total_label']}",
            f"サラリー余力: {summary['salary_cap_room_label']}",
        ]
    )

    lines_prev: List[str] = [
        f"前季収入: {summary['revenue_last_season_label']}",
        f"前季支出: {summary['expense_last_season_label']}",
        f"前季収支: {summary['cashflow_last_season_label']}",
    ]

    lim = max(1, int(max_history))
    lines_hist: List[str] = [
        f"履歴あり: {hist_count}件",
        f"表示件数: {displayed}件（ストレージ順の末尾から最大{lim}件・並べ替えなし）",
    ]

    lines_caution: List[str] = [
        "読み取り専用です。",
        "予算変更・投資・契約更新などの操作は未接続です。",
    ]

    sections: List[Dict[str, Any]] = [
        {"title": "財務概要", "lines": lines_overview},
        {"title": "前季収支", "lines": lines_prev},
        {"title": "財務履歴", "lines": lines_hist},
        {"title": "注意", "lines": lines_caution},
    ]

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "summary": summary,
        "finance_items": finance_items,
        "history_rows": history_rows,
        "sections": sections,
        "notes": notes,
    }


def write_finance_summary_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_finance_summary_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_history: int = 5,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で財務サマリー用 JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    raw_sc = payload.get("season_count")
    try:
        season_count_i: Optional[int] = int(raw_sc) if raw_sc is not None else None
    except (TypeError, ValueError):
        season_count_i = None
    raw_am = payload.get("at_annual_menu")
    if raw_am is None:
        at_annual_i: Optional[bool] = None
    else:
        at_annual_i = bool(raw_am)
    snap = build_finance_summary_readonly_dict(
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_history=max_history,
    )
    write_finance_summary_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot finance summary JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-history",
        type=int,
        default=5,
        metavar="N",
        help="Max finance_history rows from the tail of the list (default: 5)",
    )
    args = parser.parse_args(argv)
    export_finance_summary_json_from_world(args.save, args.output, max_history=int(args.max_history))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
