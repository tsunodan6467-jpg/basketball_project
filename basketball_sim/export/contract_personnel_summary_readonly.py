"""
Godot 契約・人事サマリー（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView / Godot には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team / Player は getattr のみ（代入・ensure・FA 生成・契約更新 API は呼ばない）。
- リスク表示は簡易目安（memo に明記）。厳密な査定ロジックは持たない。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.export.finance_summary_readonly import (
    _format_money_label,
    _format_signed_money_label,
    _int_optional,
    _league_level_optional,
    _payroll_total,
    _safe_get,
    _soft_salary_cap,
    _team_display_name,
)
from basketball_sim.export.roster_readonly import (
    _contract_label,
    _player_id_int,
    _sort_rosters_for_readonly_display,
)
from basketball_sim.systems.japan_regulation_display import get_player_nationality_bucket_label

SCREEN_TITLE = "契約・人事サマリー（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。契約更新・交渉・獲得・解雇・FA操作などの操作は含みません。",
]

NOTE_NO_TEAM = "チーム情報が未接続のため、契約・人事情報の一部は表示できません。"
NOTE_CONTRACT_PARTIAL = "契約年数など一部の契約データは未接続です。"


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _salary_tuple(player: Any) -> Tuple[int, str]:
    raw = _safe_get(player, "salary", None)
    try:
        yen = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        yen = 0
    yen = max(0, yen)
    try:
        from basketball_sim.systems.money_display import format_money_yen_ja_readable

        label = format_money_yen_ja_readable(yen)
    except Exception:
        label = str(yen)
    return yen, label


def _contract_years_left_optional(player: Any) -> Optional[int]:
    cy = _safe_get(player, "contract_years_left", None)
    if cy is None:
        return None
    try:
        return int(cy)
    except (TypeError, ValueError):
        return None


def _ovr_int(player: Any) -> int:
    return _safe_int(_safe_get(player, "ovr", None), 0)


def _age_optional(player: Any) -> Optional[int]:
    return _int_optional(_safe_get(player, "age", None))


def _position_str(player: Any) -> str:
    raw = _safe_get(player, "position", None)
    s = str(raw).strip() if raw is not None else ""
    return s if s else "-"


def _potential_str(player: Any) -> str:
    raw = _safe_get(player, "potential", None)
    s = str(raw).strip() if raw is not None else ""
    return s if s else "-"


def _is_injured_like(player: Any) -> bool:
    gl = _safe_int(_safe_get(player, "injury_games_left", None), 0)
    if gl > 0:
        return True
    fn = getattr(player, "is_injured", None)
    if callable(fn):
        try:
            return bool(fn())
        except Exception:
            return False
    return bool(_safe_get(player, "injured", False))


def _player_memo_line(player: Any) -> str:
    if _is_injured_like(player):
        g = _safe_int(_safe_get(player, "injury_games_left", None), 0)
        return f"負傷関連（残り試合目安: {g}）"
    return "-"


def _ordered_players_for_table(players: List[Any]) -> List[Any]:
    """年俸降順 → OVR 降順 → 元ロスター順（並び替え安定）。"""
    base = _sort_rosters_for_readonly_display(list(players))
    salaries = [_salary_tuple(p)[0] for p in base]
    has_positive_salary = any(s > 0 for s in salaries)
    if has_positive_salary:
        return sorted(base, key=lambda p: (-_salary_tuple(p)[0], -_ovr_int(p), str(_safe_get(p, "name", ""))))
    if any(_ovr_int(p) > 0 for p in base):
        return sorted(base, key=lambda p: (-_ovr_int(p), str(_safe_get(p, "name", ""))))
    return list(base)


def _nationality_slot_label(player: Any) -> str:
    try:
        return str(get_player_nationality_bucket_label(player))
    except Exception:
        raw = _safe_get(player, "nationality", None)
        return str(raw).strip() if raw is not None and str(raw).strip() else "不明"


def _is_naturalized_player(player: Any) -> bool:
    if bool(_safe_get(player, "was_naturalized", False)):
        return True
    nat = str(_safe_get(player, "nationality", "") or "").strip()
    return nat == "Naturalized"


def _position_counts(players: List[Any]) -> Dict[str, int]:
    keys = ("PG", "SG", "SF", "PF", "C")
    counts = {k: 0 for k in keys}
    for p in players:
        pos = _position_str(p).upper()
        if pos in counts:
            counts[pos] += 1
    return counts


def _contract_item(
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


def _risk_item(
    key: str,
    label: str,
    value: Any,
    display_value: str,
    severity: str,
    memo: str = "",
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display_value": display_value,
        "severity": severity,
        "memo": memo,
    }


def _roster_balance_item(key: str, label: str, value: Any, display_value: str, memo: str = "") -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display_value": display_value,
        "memo": memo,
    }


def _collect_nationality_counts(players: List[Any]) -> Dict[str, int]:
    foreign = 0
    domestic = 0
    special_bucket = 0
    naturalized = 0
    unknown = 0
    for p in players:
        if _is_naturalized_player(p):
            naturalized += 1
        lbl = _nationality_slot_label(p)
        if lbl == "外国籍":
            foreign += 1
        elif lbl == "日本":
            domestic += 1
        elif lbl == "アジア/帰化":
            special_bucket += 1
        else:
            unknown += 1
    asian_estimate = max(0, special_bucket - naturalized)
    return {
        "foreign": foreign,
        "domestic": domestic,
        "special_bucket": special_bucket,
        "naturalized": naturalized,
        "asian_estimate": asian_estimate,
        "unknown": unknown,
    }


def _build_player_contract_rows(players: List[Any], *, max_players: int) -> List[Dict[str, Any]]:
    ordered = _ordered_players_for_table(players)
    lim = max(1, int(max_players))
    rows: List[Dict[str, Any]] = []
    row_order = 0
    for p in ordered[:lim]:
        if _safe_get(p, "player_id", None) is None:
            continue
        row_order += 1
        name = str(_safe_get(p, "name", None) or "").strip() or "無名選手"
        pos = _position_str(p)
        age = _age_optional(p)
        ovr = _ovr_int(p)
        pot = _potential_str(p)
        yen, sal_label = _salary_tuple(p)
        cy = _contract_years_left_optional(p)
        cy_label = _contract_label(cy)

        has_cy = cy is not None
        if has_cy:
            c_status = "known"
            c_status_label = "契約残あり" if cy > 0 else "満了シーズン"
        else:
            c_status = "unknown"
            c_status_label = "未接続"

        fa_flag = bool(cy is not None and cy <= 1)
        fa_flag_label = "満了近い" if fa_flag else "—"

        risk_bits: List[str] = []
        if fa_flag:
            risk_bits.append("契約満了近辺")
        if _is_injured_like(p):
            risk_bits.append("負傷・欠場リスク")
        risk_label = "・".join(risk_bits) if risk_bits else "—"

        rows.append(
            {
                "player_id": _player_id_int(p),
                "order": row_order,
                "player_name": name,
                "position": pos,
                "age": age,
                "overall": ovr,
                "potential": pot,
                "salary": yen if yen > 0 else None,
                "salary_label": sal_label if yen > 0 else "-",
                "contract_years": cy,
                "contract_years_label": cy_label,
                "contract_status": c_status,
                "contract_status_label": c_status_label,
                "nationality_slot": _nationality_slot_label(p),
                "nationality_slot_label": _nationality_slot_label(p),
                "fa_flag": fa_flag,
                "fa_flag_label": fa_flag_label,
                "risk_label": risk_label,
                "memo": _player_memo_line(p),
            }
        )
    return rows


def _build_roster_balance_items(players: List[Any], nat: Dict[str, int], pos_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    u23_n = 0
    vet_n = 0
    for p in players:
        a = _age_optional(p)
        if a is None:
            continue
        if a < 23:
            u23_n += 1
        if a >= 30:
            vet_n += 1

    items: List[Dict[str, Any]] = []
    for k, lab in (
        ("pg_count", "PG人数"),
        ("sg_count", "SG人数"),
        ("sf_count", "SF人数"),
        ("pf_count", "PF人数"),
        ("c_count", "C人数"),
    ):
        pos_key = k.replace("_count", "").upper()
        v = pos_counts.get(pos_key, 0)
        items.append(_roster_balance_item(k, lab, v, str(v), memo="ポジションはロスター表記に基づく簡易集計。"))

    items.append(_roster_balance_item("u23_count", "U23人数", u23_n, str(u23_n), memo="年齢22以下をU23相当として数える簡易目安。"))
    items.append(_roster_balance_item("age30_plus_count", "30歳以上人数", vet_n, str(vet_n), memo=""))

    unk = int(nat.get("unknown", 0))
    total_labeled = nat["foreign"] + nat["domestic"] + nat["special_bucket"]
    if len(players) > 0 and unk == len(players):
        items.append(
            _roster_balance_item(
                "nationality_breakdown",
                "国籍枠集計",
                None,
                "未接続",
                memo="国籍区分ラベルが全員不明のため、枠集計は未接続です。",
            )
        )
    elif unk > 0 and total_labeled == 0:
        items.append(
            _roster_balance_item(
                "nationality_breakdown",
                "国籍枠集計",
                None,
                "未接続",
                memo="国籍区分の自動集計ができませんでした（データ不足）。",
            )
        )
    else:
        items.append(
            _roster_balance_item(
                "foreign_player_count",
                "外国籍選手数",
                nat["foreign"],
                str(nat["foreign"]),
                memo="規則ベースの区分ラベルによる簡易集計。",
            )
        )
        items.append(
            _roster_balance_item(
                "asian_slot_estimate",
                "アジア枠（概算）",
                nat["asian_estimate"],
                str(nat["asian_estimate"]),
                memo="「アジア/帰化」区分から帰化を除いた概算。厳密な枠判定は未接続。",
            )
        )
        items.append(
            _roster_balance_item(
                "naturalized_player_count",
                "帰化選手数",
                nat["naturalized"],
                str(nat["naturalized"]),
                memo="was_naturalized または nationality=Naturalized で数える簡易集計。",
            )
        )
        items.append(
            _roster_balance_item(
                "domestic_player_count",
                "国内選手数",
                nat["domestic"],
                str(nat["domestic"]),
                memo="区分ラベル「日本」に基づく簡易集計。",
            )
        )
    return items


def _build_risk_items(
    *,
    expiring: int,
    high_salary: int,
    pos_counts: Dict[str, int],
    nat: Dict[str, int],
    u23: int,
    vet: int,
    cap_room: Optional[int],
    roster_count: int,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    sev_exp = "warn" if expiring >= 3 else "info"
    items.append(
        _risk_item(
            "expiring_contract_risk",
            "満了リスク",
            expiring,
            f"{expiring}名（残契約1年以内の目安）",
            sev_exp,
            memo="contract_years_left が 0〜1 の選手数による簡易目安。",
        )
    )
    sev_high = "warn" if high_salary >= 2 else "info"
    items.append(
        _risk_item(
            "high_salary_skew",
            "高年俸偏重リスク",
            high_salary,
            f"{high_salary}名（平均年俸の1.3倍以上の目安）",
            sev_high,
            memo="平均年俸が取れない場合は件数0扱い。簡易目安。",
        )
    )
    vals = [pos_counts[k] for k in ("PG", "SG", "SF", "PF", "C")]
    spread = max(vals) - min(vals) if vals else 0
    sev_pos = "caution" if spread >= 3 else "info"
    items.append(
        _risk_item(
            "position_skew",
            "ポジション偏り",
            spread,
            f"最大−最小={spread}",
            sev_pos,
            memo="各ポジション人数の差による簡易目安。",
        )
    )
    sev_nat = "caution" if nat["foreign"] >= 4 else "info"
    items.append(
        _risk_item(
            "foreign_slot_pressure",
            "外国籍枠の偏り",
            nat["foreign"],
            f"外国籍ラベル: {nat['foreign']}名",
            sev_nat,
            memo="登録ルールの上限とは照合していない簡易目安。",
        )
    )
    sev_youth = "caution" if roster_count >= 5 and u23 < 2 else "info"
    items.append(
        _risk_item(
            "youth_shortage",
            "若手不足",
            u23,
            f"U23相当: {u23}名",
            sev_youth,
            memo="年齢22以下をU23相当。簡易目安。",
        )
    )
    sev_vet = "info" if vet >= 8 else "info"
    items.append(
        _risk_item(
            "veteran_heavy",
            "ベテラン偏重",
            vet,
            f"30歳以上: {vet}名",
            sev_vet,
            memo="年齢30以上の人数。簡易目安。",
        )
    )
    if cap_room is None:
        sev_cap = "info"
        cap_disp = "未接続"
    elif cap_room < 0:
        sev_cap = "warn"
        cap_disp = _format_signed_money_label(cap_room)
    else:
        sev_cap = "info"
        cap_disp = _format_signed_money_label(cap_room)
    items.append(
        _risk_item(
            "salary_cap_room_shortage",
            "サラリー余力不足",
            cap_room,
            cap_disp,
            sev_cap,
            memo="ソフトキャップ−年俸合計。取得できない場合は未接続表示。簡易目安。",
        )
    )
    return items


def build_contract_personnel_summary_readonly_dict(
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_players: int = 8,
) -> Dict[str, Any]:
    notes = list(DEFAULT_NOTES)
    if team is None:
        notes.append(NOTE_NO_TEAM)

    team_name = _team_display_name(team)
    league_level = _league_level_optional(team)

    players: List[Any] = []
    if team is not None:
        raw = _safe_get(team, "players", None) or []
        if isinstance(raw, (list, tuple)):
            players = [p for p in raw if p is not None]

    roster_count = len(players)
    payroll = _payroll_total(team)
    cap_soft = _soft_salary_cap(team)
    cap_room: Optional[int] = None
    if cap_soft is not None and payroll is not None:
        cap_room = int(cap_soft) - int(payroll)

    salaries = [_salary_tuple(p)[0] for p in players]
    has_salary_data = bool(payroll is not None and payroll > 0) or any(s > 0 for s in salaries)
    cy_values = [_contract_years_left_optional(p) for p in players]
    has_contract_data = any(v is not None for v in cy_values)
    if team is not None and roster_count > 0 and not has_contract_data:
        notes.append(NOTE_CONTRACT_PARTIAL)

    expiring = sum(1 for v in cy_values if v is not None and 0 <= int(v) <= 1)

    avg_sal: Optional[int] = None
    if roster_count > 0 and payroll is not None and payroll > 0:
        avg_sal = int(payroll) // roster_count
    max_sal = max(salaries) if salaries else 0

    high_salary = 0
    if avg_sal and avg_sal > 0:
        threshold = int(avg_sal * 1.3)
        high_salary = sum(1 for s in salaries if s >= threshold)

    rookie_c = sum(1 for p in players if bool(_safe_get(p, "is_draft_rookie_contract", False)))
    vet_c = sum(1 for p in players if (_age_optional(p) is not None and _age_optional(p) >= 30))

    fa_short = _safe_get(team, "fa_shortlist", None) if team is not None else None
    if isinstance(fa_short, list):
        fa_candidate_count = len(fa_short)
    else:
        fa_candidate_count = 0

    nat = _collect_nationality_counts(players)
    pos_counts = _position_counts(players)

    u23_n = sum(1 for p in players if (a := _age_optional(p)) is not None and a < 23)

    summary: Dict[str, Any] = {
        "roster_count": roster_count if roster_count else None,
        "salary_total": payroll,
        "salary_total_label": _format_money_label(payroll) if payroll is not None else "-",
        "salary_cap": cap_soft,
        "salary_cap_label": _format_money_label(cap_soft) if cap_soft is not None else "-",
        "salary_cap_room": cap_room,
        "salary_cap_room_label": _format_signed_money_label(cap_room) if cap_room is not None else "-",
        "average_salary": avg_sal,
        "average_salary_label": _format_money_label(avg_sal) if avg_sal is not None else "-",
        "max_salary": max_sal if max_sal > 0 else None,
        "max_salary_label": _format_money_label(max_sal) if max_sal > 0 else "-",
        "expiring_contract_count": expiring,
        "fa_candidate_count": fa_candidate_count,
        "high_salary_count": high_salary,
        "rookie_contract_count": rookie_c,
        "veteran_contract_count": vet_c,
        "foreign_player_count": nat["foreign"] if roster_count else None,
        "asian_player_count": nat["asian_estimate"] if roster_count else None,
        "naturalized_player_count": nat["naturalized"] if roster_count else None,
        "domestic_player_count": nat["domestic"] if roster_count else None,
        "has_contract_data": has_contract_data,
        "has_salary_data": has_salary_data,
        "season_count": season_count,
        "at_annual_menu": at_annual_menu,
    }

    contract_items: List[Dict[str, Any]] = []
    if team is None:
        contract_items = [
            _contract_item("roster_count", "ロスター人数", None, "-", memo=NOTE_NO_TEAM),
            _contract_item("salary_total", "年俸合計", None, "-", memo=NOTE_NO_TEAM),
            _contract_item("salary_cap", "サラリーキャップ", None, "-", memo=NOTE_NO_TEAM),
            _contract_item("salary_cap_room", "サラリー余力", None, "-", memo=NOTE_NO_TEAM),
            _contract_item("contract_data_status", "契約情報の接続状況", "disconnected", "未接続", memo=NOTE_NO_TEAM),
        ]
    else:
        contract_items = [
            _contract_item("roster_count", "ロスター人数", roster_count, str(roster_count), memo=""),
            _contract_item(
                "salary_total",
                "年俸合計",
                payroll,
                _format_money_label(payroll) if payroll is not None else "-",
                memo="get_team_payroll 優先、失敗時は選手 salary 合算。",
            ),
            _contract_item(
                "salary_cap",
                "サラリーキャップ",
                cap_soft,
                _format_money_label(cap_soft) if cap_soft is not None else "-",
                memo="ソフトキャップ（財務サマリー export と同系の参照）。",
            ),
            _contract_item(
                "salary_cap_room",
                "サラリー余力",
                cap_room,
                _format_signed_money_label(cap_room) if cap_room is not None else "-",
                memo="上限−年俸合計。",
            ),
            _contract_item(
                "average_salary",
                "平均年俸",
                avg_sal,
                _format_money_label(avg_sal) if avg_sal is not None else "-",
                memo="年俸合計÷ロスター人数の概算。",
            ),
            _contract_item(
                "max_salary",
                "最高年俸",
                max_sal if max_sal > 0 else None,
                _format_money_label(max_sal) if max_sal > 0 else "-",
                memo="",
            ),
            _contract_item(
                "expiring_contracts",
                "契約満了予定",
                expiring,
                f"{expiring}名（残契約1年以内の目安）",
                memo="contract_years_left が 0〜1。",
            ),
            _contract_item(
                "fa_shortlist",
                "FA予備軍",
                fa_candidate_count,
                f"{fa_candidate_count}件（fa_shortlist 件数）",
                memo="リスト件数のみ。市場操作は未接続。",
            ),
            _contract_item(
                "high_salary_players",
                "高年俸選手数",
                high_salary,
                f"{high_salary}名（平均の1.3倍以上の目安）",
                memo="簡易目安。",
            ),
            _contract_item(
                "contract_data_status",
                "契約情報の接続状況",
                "ok" if has_contract_data else "partial",
                "接続" if has_contract_data else "一部未接続",
                memo=NOTE_CONTRACT_PARTIAL if not has_contract_data and roster_count > 0 else "",
            ),
        ]

    player_rows = _build_player_contract_rows(players, max_players=max_players) if team is not None else []

    roster_balance_items: List[Dict[str, Any]] = []
    risk_items: List[Dict[str, Any]] = []
    if team is not None and roster_count:
        roster_balance_items = _build_roster_balance_items(players, nat, pos_counts)
        risk_items = _build_risk_items(
            expiring=expiring,
            high_salary=high_salary,
            pos_counts=pos_counts,
            nat=nat,
            u23=u23_n,
            vet=vet_c,
            cap_room=cap_room,
            roster_count=roster_count,
        )
    elif team is None:
        roster_balance_items = []
        risk_items = [
            _risk_item("no_team", "チーム未接続", None, "-", "info", memo=NOTE_NO_TEAM),
        ]
    else:
        roster_balance_items = []
        risk_items = [
            _risk_item("empty_roster", "ロスター空", 0, "0名", "info", memo="選手リストが空です。"),
        ]

    ctx_parts: List[str] = []
    if season_count is not None:
        ctx_parts.append(f"セーブ上のシーズン回数: {season_count}")
    if at_annual_menu is True:
        ctx_parts.append("年度メニュー直後のセーブの可能性があります。")
    ctx_line = " / ".join(ctx_parts) if ctx_parts else None

    lines_contract: List[str] = [f"クラブ: {team_name}"]
    if ctx_line:
        lines_contract.append(ctx_line)
    if team:
        lines_contract.append(f"ロスター人数: {roster_count}名")
        lines_contract.append(f"年俸合計: {summary['salary_total_label']}")
        lines_contract.append(f"サラリー上限: {summary['salary_cap_label']}")
        lines_contract.append(f"サラリー余力: {summary['salary_cap_room_label']}")
        lines_contract.append(f"契約満了近辺（目安）: {expiring}名")
    else:
        lines_contract.append("ロスター人数: -")

    lines_risk = [ri["display_value"] + "（" + ri["label"] + "）" for ri in risk_items[:6]]

    lines_players: List[str] = []
    for r in player_rows[:5]:
        lines_players.append(
            f"{r['order']}. {r['player_name']} {r['position']} 年俸:{r['salary_label']} 契約:{r['contract_years_label']}"
        )
    if len(player_rows) > 5:
        lines_players.append(f"…他 {len(player_rows) - 5} 名は JSON 行参照")

    lines_balance = [f"{it['label']}: {it['display_value']}" for it in roster_balance_items[:8]]

    lines_notes = list(notes)

    sections: List[Dict[str, Any]] = [
        {"title": "契約概要", "lines": lines_contract},
        {"title": "人事リスク", "lines": lines_risk if lines_risk else ["リスク項目なし"]},
        {"title": "主要契約選手", "lines": lines_players if lines_players else ["表示対象なし"]},
        {"title": "ロスター構成", "lines": lines_balance if lines_balance else ["—"]},
        {"title": "注意", "lines": lines_notes},
    ]

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "summary": summary,
        "contract_items": contract_items,
        "risk_items": risk_items,
        "player_contract_rows": player_rows,
        "roster_balance_items": roster_balance_items,
        "sections": sections,
        "notes": notes,
    }


def write_contract_personnel_summary_json(data: Dict[str, Any], output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_contract_personnel_summary_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_players: int = 8,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で契約・人事サマリー用 JSON を書き出す。セーブファイルは上書きしない。

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
    snap = build_contract_personnel_summary_readonly_dict(
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_players=max_players,
    )
    write_contract_personnel_summary_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot contract/personnel summary JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-players",
        type=int,
        default=8,
        metavar="N",
        help="Max player_contract_rows (default: 8)",
    )
    args = parser.parse_args(argv)
    export_contract_personnel_summary_json_from_world(args.save, args.output, max_players=int(args.max_players))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
