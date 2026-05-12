"""
Godot オーナーミッション / クラブ評価（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk 仮 GUI / Godot には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team.owner_missions 等は getattr / dict 取得のみ（代入・append・評価 API は呼ばない）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCREEN_TITLE = "オーナーミッション（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。ミッション生成・評価更新・報酬付与などの操作は含みません。",
]

NOTE_NO_TEAM = "チーム情報が未接続のため、オーナーミッション情報の一部は表示できません。"

NOTE_NO_MISSIONS = "オーナーミッション情報が未設定です。"

_OWNER_EXPECTATION_LABELS = {
    "rebuild": "再建",
    "playoff_race": "PO争い",
    "promotion": "昇格必達",
    "title_challenge": "優勝挑戦",
    "title_or_bust": "優勝必須",
}


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


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


def _parse_owner_trust_int(team: Any) -> Optional[int]:
    if team is None:
        return None
    raw = _first_non_empty(
        _safe_get(team, "owner_trust", None),
        _safe_get(team, "owner_confidence", None),
        _safe_get(team, "chairman_trust", None),
    )
    if raw is None:
        return None
    try:
        v = int(float(raw)) if isinstance(raw, str) and "." in str(raw) else int(raw)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, v))


def _first_non_empty(*values: Any) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _owner_trust_rank_label(trust_int: Optional[int]) -> str:
    if trust_int is None:
        return "不明"
    from basketball_sim.models.team import _cli_owner_trust_band

    return str(_cli_owner_trust_band(int(trust_int)))


def _owner_expectation_display(team: Any) -> str:
    if team is None:
        return "-"
    raw = _safe_get(team, "owner_expectation", None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "-"
    key = str(raw).strip()
    return str(_OWNER_EXPECTATION_LABELS.get(key, key))


def _normalize_missions_list(team: Any) -> List[Any]:
    """owner_missions を list 化（読取のみ）。list / dict / None / 単独 dict に対応。"""
    if team is None:
        return []
    raw = _safe_get(team, "owner_missions", None)
    out: List[Any] = []
    if raw is None:
        pass
    elif isinstance(raw, list):
        out = list(raw)
    elif isinstance(raw, dict):
        inner = raw.get("missions")
        if isinstance(inner, list):
            out = list(inner)
        elif raw.get("mission_id") is not None or raw.get("title") is not None:
            out = [raw]
        else:
            vals = [v for v in raw.values() if isinstance(v, dict)]
            out = vals if vals else []
    else:
        return []

    if not out:
        legacy = _safe_get(team, "owner_mission", None)
        if legacy is not None and str(legacy).strip():
            out = [
                {
                    "mission_id": None,
                    "title": str(legacy).strip(),
                    "category": "legacy",
                    "status": "unknown",
                    "progress_text": "-",
                }
            ]
    return out


def _mission_title_from_entry(entry: Any) -> str:
    if isinstance(entry, dict):
        for k in ("title", "label", "name", "description", "key", "mission_id"):
            v = entry.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return "-"
    for k in ("title", "label", "name", "description", "key", "mission_id"):
        v = _safe_get(entry, k, None)
        if v is not None and str(v).strip():
            return str(v).strip()
    return "-"


def _mission_id_from_entry(entry: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get("mission_id") or entry.get("id")
    return _safe_get(entry, "mission_id", None) or _safe_get(entry, "id", None)


def _status_raw_original(entry: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get("status")
    return _safe_get(entry, "status", None)


def _status_raw_lower(entry: Any) -> Optional[str]:
    v = _status_raw_original(entry)
    if v is None:
        return None
    s = str(v).strip().lower()
    return s or None


def _status_label(raw: Optional[str]) -> str:
    if not raw:
        return "不明"
    m = {
        "active": "進行中",
        "ongoing": "進行中",
        "in_progress": "進行中",
        "completed": "達成",
        "success": "達成",
        "achieved": "達成",
        "failed": "未達",
        "missed": "未達",
        "pending": "保留",
        "unknown": "不明",
        "legacy": "（旧形式）",
    }
    return m.get(raw, "不明")


def _mission_category(entry: Any) -> str:
    if isinstance(entry, dict):
        v = entry.get("category")
        return str(v).strip() if v is not None and str(v).strip() else "-"
    v = _safe_get(entry, "category", None)
    return str(v).strip() if v is not None and str(v).strip() else "-"


def _mission_target_int(entry: Any) -> Optional[int]:
    if isinstance(entry, dict):
        tv = entry.get("target_value")
    else:
        tv = _safe_get(entry, "target_value", None)
    if tv is None:
        return None
    try:
        return int(tv)
    except (TypeError, ValueError):
        return None


def _mission_progress_int(entry: Any) -> Optional[int]:
    if isinstance(entry, dict):
        for k in ("progress", "current", "current_value", "progress_value"):
            v = entry.get(k)
            if v is None:
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    else:
        for k in ("progress", "current", "current_value", "progress_value"):
            v = _safe_get(entry, k, None)
            if v is None:
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    return None


def _mission_progress_label(entry: Any, target: Optional[int]) -> str:
    if isinstance(entry, dict):
        pt = entry.get("progress_text")
    else:
        pt = _safe_get(entry, "progress_text", None)
    if isinstance(pt, str) and pt.strip():
        return pt.strip()
    prog = _mission_progress_int(entry)
    if prog is not None and target is not None:
        return f"{prog} / {target}"
    if prog is not None:
        return str(prog)
    return "-"


def _mission_reward_penalty(entry: Any) -> Tuple[str, str]:
    def _one(getter: str) -> str:
        if isinstance(entry, dict):
            v = entry.get(getter)
        else:
            v = _safe_get(entry, getter, None)
        if v is None:
            return "-"
        try:
            return str(int(v))
        except (TypeError, ValueError):
            return str(v) if str(v).strip() else "-"

    return _one("reward_trust"), _one("penalty_trust")


def _mission_memo(entry: Any) -> str:
    if isinstance(entry, dict):
        d = entry.get("description")
    else:
        d = _safe_get(entry, "description", None)
    if isinstance(d, str) and d.strip():
        return d.strip()[:200]
    return "-"


def _count_mission_statuses(missions: List[Any]) -> Tuple[int, int, int, int]:
    active = completed = failed = 0
    for m in missions:
        raw = _status_raw_lower(m)
        if raw in ("success", "completed", "achieved"):
            completed += 1
        elif raw in ("failed", "missed"):
            failed += 1
        elif raw in ("active", "ongoing", "in_progress", None, ""):
            active += 1
        else:
            active += 1
    return len(missions), active, completed, failed


def _build_mission_items(missions: List[Any], *, max_missions: int) -> List[Dict[str, Any]]:
    lim = max(1, int(max_missions))
    items: List[Dict[str, Any]] = []
    for idx, entry in enumerate(missions[:lim], start=1):
        raw_orig = _status_raw_original(entry)
        raw_lower = _status_raw_lower(entry)
        tid = _mission_id_from_entry(entry)
        target = _mission_target_int(entry)
        reward, penalty = _mission_reward_penalty(entry)
        items.append(
            {
                "order": idx,
                "id": tid,
                "title": _mission_title_from_entry(entry),
                "category": _mission_category(entry),
                "status": raw_orig,
                "status_label": _status_label(raw_lower),
                "target": target,
                "progress": _mission_progress_int(entry),
                "progress_label": _mission_progress_label(entry, target),
                "reward": reward,
                "penalty": penalty,
                "memo": _mission_memo(entry),
            }
        )
    return items


def _build_evaluation_items(
    *,
    trust_int: Optional[int],
    mission_total: int,
    active_c: int,
    completed_c: int,
    failed_c: int,
    team: Any,
) -> List[Dict[str, Any]]:
    rank = _owner_trust_rank_label(trust_int)
    if trust_int is None:
        trust_disp = "-"
        trust_val: Any = None
    else:
        trust_disp = f"{trust_int}（{rank}）"
        trust_val = trust_int

    club_eval_disp = "-"
    club_memo = "専用フィールド club_evaluation はセーブに存在しません（owner_trust 帯からの読取表示のみ）。"
    if trust_int is not None:
        club_eval_disp = f"オーナー信頼ベース: {rank}（参考表示・読取のみ）"

    exp_label = _owner_expectation_display(team)

    rows: List[Dict[str, Any]] = [
        {
            "key": "owner_trust",
            "label": "オーナー信頼",
            "value": trust_val,
            "display_value": trust_disp,
            "memo": f"オーナー期待: {exp_label}" if team is not None else "-",
        },
        {
            "key": "active_missions",
            "label": "進行中ミッション",
            "value": active_c,
            "display_value": str(active_c),
            "memo": "status が進行系とみなした件数（読取のみ）",
        },
        {
            "key": "completed_missions",
            "label": "達成済みミッション",
            "value": completed_c,
            "display_value": str(completed_c),
            "memo": "-",
        },
        {
            "key": "failed_missions",
            "label": "未達ミッション",
            "value": failed_c,
            "display_value": str(failed_c),
            "memo": "-",
        },
        {
            "key": "club_evaluation",
            "label": "クラブ評価",
            "value": None,
            "display_value": club_eval_disp,
            "memo": club_memo,
        },
        {
            "key": "mission_total",
            "label": "ミッション件数（全件）",
            "value": mission_total,
            "display_value": str(mission_total),
            "memo": "max_missions による表示切り詰め前の総数",
        },
    ]
    return rows


def _section_lines_owner_trust(team: Any, trust_int: Optional[int], rank: str) -> List[str]:
    lines: List[str] = []
    if team is None:
        lines.append("チーム未接続のためオーナー信頼は表示できません。")
        return lines
    if trust_int is None:
        lines.append("オーナー信頼: 不明")
    else:
        lines.append(f"オーナー信頼: {trust_int} / 100（{rank}）")
    exp = _owner_expectation_display(team)
    lines.append(f"オーナー期待: {exp}")
    return lines


def _section_lines_missions(mission_items: List[Dict[str, Any]], missions_full: List[Any]) -> List[str]:
    if not missions_full:
        return [NOTE_NO_MISSIONS]
    lines: List[str] = []
    for it in mission_items:
        st = it.get("status_label", "不明")
        lines.append(f"{it.get('order', 0)}. {it.get('title', '-')} — {st}")
        if it.get("progress_label") not in (None, "-"):
            lines.append(f"   進捗: {it.get('progress_label')}")
    if len(missions_full) > len(mission_items):
        lines.append(f"（他 {len(missions_full) - len(mission_items)} 件は max_missions により省略）")
    return lines


def _section_lines_evaluation(evaluation_items: List[Dict[str, Any]]) -> List[str]:
    return [f"{r['label']}: {r['display_value']}" for r in evaluation_items]


def build_owner_mission_readonly_dict(
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_missions: int = 8,
) -> Dict[str, Any]:
    team_name = _team_display_name(team)
    league_level = _league_level_optional(team)
    missions_full = _normalize_missions_list(team)
    mission_total, active_c, completed_c, failed_c = _count_mission_statuses(missions_full)
    trust_int = _parse_owner_trust_int(team)
    rank = _owner_trust_rank_label(trust_int)

    summary: Dict[str, Any] = {
        "owner_trust": trust_int,
        "owner_trust_label": None if trust_int is None else f"{trust_int}（{rank}）",
        "owner_trust_rank": rank,
        "mission_count": mission_total,
        "active_mission_count": active_c,
        "completed_mission_count": completed_c,
        "failed_mission_count": failed_c,
        "has_owner_missions": mission_total > 0,
        "season_count": season_count,
        "at_annual_menu": at_annual_menu,
    }

    mission_items = _build_mission_items(missions_full, max_missions=max_missions)
    evaluation_items = _build_evaluation_items(
        trust_int=trust_int,
        mission_total=mission_total,
        active_c=active_c,
        completed_c=completed_c,
        failed_c=failed_c,
        team=team,
    )

    notes = list(DEFAULT_NOTES)
    if team is None:
        notes.append(NOTE_NO_TEAM)
    elif mission_total == 0:
        notes.append(NOTE_NO_MISSIONS)

    sections: List[Dict[str, Any]] = [
        {"title": "オーナー信頼", "lines": _section_lines_owner_trust(team, trust_int, rank)},
        {"title": "今季ミッション", "lines": _section_lines_missions(mission_items, missions_full)},
        {"title": "クラブ評価", "lines": _section_lines_evaluation(evaluation_items)},
        {
            "title": "注意",
            "lines": [
                "読み取り専用です。",
                "ミッションの再生成・評価確定・信頼度の変更は行いません。",
            ],
        },
    ]

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "summary": summary,
        "mission_items": mission_items,
        "evaluation_items": evaluation_items,
        "sections": sections,
        "notes": notes,
    }


def write_owner_mission_json(data: Dict[str, Any], output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_owner_mission_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_missions: int = 8,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でオーナーミッション閲覧用 JSON を書き出す。セーブファイルは上書きしない。
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
    snap = build_owner_mission_readonly_dict(
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_missions=max_missions,
    )
    write_owner_mission_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot owner mission / club evaluation JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-missions",
        type=int,
        default=8,
        metavar="N",
        help="Max mission rows in mission_items (default: 8)",
    )
    args = parser.parse_args(argv)
    export_owner_mission_json_from_world(args.save, args.output, max_missions=int(args.max_missions))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
