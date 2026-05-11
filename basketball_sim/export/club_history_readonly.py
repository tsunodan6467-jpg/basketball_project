"""
Godot クラブ史（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team.get_club_history_report_text / get_club_history_summary / get_club_history_season_rows は
  内部で _ensure_history_fields() を呼び得るため **本モジュールでは呼ばない**。
  （pickle 復元直後のオブジェクトに対するメモリ上の正規化を避ける）
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCREEN_TITLE = "クラブ史（閲覧）"
DEFAULT_TEAM_NAME = "自クラブ"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。操作は含みません。",
]

_SPARSE_SECTION_LINE = "クラブ史データはまだ少ない状態です。"

# ソースリスト側の上限（max_events が未指定でも暴走しないように）
_MAX_MILESTONE_SCAN = 120
_MAX_TRANSACTION_SCAN = 40
_MAX_FINANCE_SCAN = 30
_MAX_SEASON_ROWS = 40
_DEFAULT_EVENTS_CAP = 200


def _safe_str(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_sequence(obj: Any, attr: str) -> List[Any]:
    if obj is None:
        return []
    raw = getattr(obj, attr, None)
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return []


def _format_season_label(value: Any) -> str:
    """Team._format_history_season_label と同じ表記ルール（export 専用・Tk 非依存）。"""
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"Season {value}"
    text = str(value).strip()
    if not text:
        return "-"
    low = text.lower()
    if low.startswith("season"):
        return text
    if text.isdigit():
        return f"Season {int(text)}"
    return text


def _division_from_league_level(league_level_value: Any) -> str:
    if league_level_value is None:
        return "-"
    try:
        n = int(league_level_value)
        return f"D{n}"
    except (TypeError, ValueError):
        s = str(league_level_value).strip()
        if s.upper().startswith("D") and s[1:].isdigit():
            return f"D{int(s[1:])}"
        return s if s else "-"


def _record_str(wins: Any, losses: Any) -> str:
    try:
        wi = int(wins) if wins is not None else None
    except (TypeError, ValueError):
        wi = None
    try:
        lo = int(losses) if losses is not None else None
    except (TypeError, ValueError):
        lo = None
    if wi is not None and lo is not None:
        return f"{wi}勝{lo}敗"
    return "-"


def _result_str(league_level_label: str, rank: Any) -> str:
    r = rank
    if r is None or r == "" or r == "-":
        return f"{league_level_label} 順位未記録"
    try:
        ri = int(r)
        return f"{league_level_label} {ri}位"
    except (TypeError, ValueError):
        return f"{league_level_label} {r}"


def _milestone_stats(
    milestones: Sequence[Any],
    *,
    exclude_test_seed: bool = True,
) -> tuple[int, int, int]:
    """
    get_club_history_summary と同等の数え方（読み取りのみ・リストは変更しない）。
    Returns:
        (titles_count, promotions_count, relegations_count)
    """
    total_titles = 0
    promotions = 0
    relegations = 0

    for item in milestones:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "") or "")
        category = str(item.get("category", "") or "")
        milestone_type = str(item.get("milestone_type", item.get("type", "")) or "")
        note = str(item.get("note", "") or "")
        competition_name = str(item.get("competition_name", "") or "")
        result = str(item.get("result", "") or "")

        if exclude_test_seed and "test_seed" in note.lower():
            continue

        title_blob = " | ".join(
            [
                title.lower(),
                note.lower(),
                competition_name.lower(),
                category.lower(),
                milestone_type.lower(),
                result.lower(),
            ]
        )

        is_title = (
            "優勝" in title
            or "優勝" in note
            or "撃破" in title
            or "撃破" in note
            or milestone_type.lower() in {"champion", "winner"}
            or result.lower() in {"champion", "winner", "victory", "cleared"}
        )

        if is_title:
            total_titles += 1

        if "昇格" in title or milestone_type == "promotion" or "promot" in category.lower():
            promotions += 1

        if "降格" in title or milestone_type == "relegation" or "relegat" in category.lower():
            relegations += 1

    return total_titles, promotions, relegations


def _build_season_rows(team: Any) -> List[Dict[str, Any]]:
    seasons = _iter_sequence(team, "history_seasons")
    if not seasons:
        return []
    tail = seasons[-_MAX_SEASON_ROWS:] if len(seasons) > _MAX_SEASON_ROWS else seasons
    rows: List[Dict[str, Any]] = []
    for item in reversed(tail):
        if not isinstance(item, dict):
            continue
        season_label = item.get("season")
        if season_label is None:
            season_label = item.get("season_index", "-")
        season_s = _format_season_label(season_label)

        wins = item.get("wins", item.get("regular_wins", "-"))
        losses = item.get("losses", item.get("regular_losses", "-"))

        league_level_value = item.get("league_level", "-")
        division = _division_from_league_level(league_level_value)

        rank = item.get("rank", "-")
        result = _result_str(division, rank)
        note = _safe_str(item.get("note", ""), "")

        rows.append(
            {
                "season": season_s,
                "division": division,
                "record": _record_str(wins, losses),
                "result": result,
                "note": note if note else "-",
            }
        )
    return rows


def _milestone_event_text(item: dict) -> str:
    title = _safe_str(item.get("title", None), "")
    if not title or title == "-":
        title = _safe_str(
            item.get("competition_name", None) or item.get("milestone_type") or item.get("type"),
            "-",
        )
    detail = _safe_str(item.get("detail", None), "")
    if not detail or detail == "-":
        detail = _safe_str(item.get("note", None), "")
    if detail and detail != "-":
        return f"{title}（{detail}）"
    return title


def _transaction_event_text(item: dict) -> str:
    ttype = _safe_str(item.get("transaction_type", None), "unknown").replace("_", " ")
    pname = _safe_str(item.get("player_name", None), "Unknown")
    note = _safe_str(item.get("note", None), "")
    if note and note != "-":
        return f"{ttype} | {pname} | {note}"
    return f"{ttype} | {pname}"


def _finance_event_text(item: dict) -> str:
    if not isinstance(item, dict):
        return _safe_str(item, "-")[:400]
    parts: List[str] = []
    for key in ("label", "kind", "title", "description", "note", "summary"):
        v = item.get(key)
        if v is not None and str(v).strip():
            parts.append(str(v).strip())
    if parts:
        return " / ".join(parts[:6])[:400]
    return str(item)[:400]


def _build_events(team: Any, *, max_events: Optional[int]) -> List[Dict[str, Any]]:
    raw: List[Dict[str, Any]] = []

    milestones = _iter_sequence(team, "history_milestones")[-_MAX_MILESTONE_SCAN:]
    for item in reversed(milestones):
        if not isinstance(item, dict):
            continue
        season = _format_season_label(item.get("season", item.get("season_index")))
        text = _milestone_event_text(item)
        raw.append({"label": season, "text": text})

    transactions = _iter_sequence(team, "history_transactions")[-_MAX_TRANSACTION_SCAN:]
    for item in reversed(transactions):
        if not isinstance(item, dict):
            continue
        raw.append({"label": "トランザクション", "text": _transaction_event_text(item)})

    finances = _iter_sequence(team, "finance_history")[-_MAX_FINANCE_SCAN:]
    for item in reversed(finances):
        if isinstance(item, dict):
            raw.append({"label": "財務", "text": _finance_event_text(item)})
        else:
            raw.append({"label": "財務", "text": _safe_str(item, "-")[:400]})

    if max_events is not None:
        try:
            cap = int(max_events)
        except (TypeError, ValueError):
            cap = None
        if cap is not None and cap >= 0:
            raw = raw[:cap]
    else:
        raw = raw[:_DEFAULT_EVENTS_CAP]

    out: List[Dict[str, Any]] = []
    for i, row in enumerate(raw, start=1):
        out.append({"order": i, "label": row["label"], "text": row["text"]})
    return out


def _build_sections(
    team_name: str,
    league_level: Optional[int],
    summary: Dict[str, Any],
    season_rows: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    lv_text = f"D{league_level}" if league_level is not None else "-"
    overview_lines = [
        f"クラブ名: {team_name}",
        f"現在のリーグ段階: {lv_text}",
        f"記録済みシーズン数: {summary.get('seasons_recorded', 0)}",
        (
            f"タイトル相当マイルストーン: {summary.get('titles_count', 0)} / "
            f"昇格: {summary.get('promotions_count', 0)} / "
            f"降格: {summary.get('relegations_count', 0)}"
        ),
    ]

    season_lines: List[str]
    if season_rows:
        season_lines = []
        for r in season_rows:
            base = (
                f"{r.get('season', '-')} | {r.get('division', '-')} | "
                f"{r.get('record', '-')} | {r.get('result', '-')}"
            )
            n = r.get("note", "-")
            if n and str(n).strip() and str(n) != "-":
                season_lines.append(f"{base} | {n}")
            else:
                season_lines.append(base)
    else:
        season_lines = ["シーズン履歴はまだありません。"]

    if events:
        event_lines = [f"- {e.get('label', '-')}: {e.get('text', '-')}" for e in events[:30]]
    else:
        event_lines = ["主な出来事の記録はまだありません。"]

    sparse = (
        summary.get("seasons_recorded", 0) == 0
        and summary.get("titles_count", 0) == 0
        and summary.get("promotions_count", 0) == 0
        and summary.get("relegations_count", 0) == 0
        and not events
    )
    if sparse:
        overview_lines.append(_SPARSE_SECTION_LINE)

    return [
        {"title": "クラブ概要", "lines": overview_lines},
        {"title": "シーズン履歴", "lines": season_lines},
        {"title": "主な出来事", "lines": event_lines},
    ]


def build_club_history_readonly_dict(team: Any, *, max_events: Optional[int] = None) -> Dict[str, Any]:
    """
    クラブ史閲覧用 dict を返す（pickle セーブは触らない）。

    Team のクラブ史系メソッドは呼ばず、history_* 列の getattr のみで組み立てる。
    """
    if team is None:
        summary = {
            "founded_label": "-",
            "seasons_recorded": 0,
            "titles_count": 0,
            "promotions_count": 0,
            "relegations_count": 0,
            "history_events_count": 0,
        }
        sections = [
            {"title": "クラブ概要", "lines": [f"クラブ名: {DEFAULT_TEAM_NAME}", _SPARSE_SECTION_LINE]},
            {"title": "シーズン履歴", "lines": ["シーズン履歴はまだありません。"]},
            {"title": "主な出来事", "lines": ["主な出来事の記録はまだありません。"]},
        ]
        return {
            "screen_title": SCREEN_TITLE,
            "team_name": DEFAULT_TEAM_NAME,
            "league_level": None,
            "summary": summary,
            "sections": sections,
            "season_rows": [],
            "events": [],
            "notes": list(DEFAULT_NOTES),
        }

    team_name = _safe_str(getattr(team, "name", None), DEFAULT_TEAM_NAME)
    if team_name == "-":
        team_name = DEFAULT_TEAM_NAME

    league_level = _safe_int_optional(getattr(team, "league_level", None))

    seasons = _iter_sequence(team, "history_seasons")
    milestones = _iter_sequence(team, "history_milestones")
    titles_count, promotions_count, relegations_count = _milestone_stats(milestones)

    events_full = _build_events(team, max_events=max_events)
    # max_events が None のときは全件（ソース上限内）。件数は最終 events の長さ
    history_events_count = len(events_full)

    summary = {
        "founded_label": "-",
        "seasons_recorded": len(seasons),
        "titles_count": int(titles_count),
        "promotions_count": int(promotions_count),
        "relegations_count": int(relegations_count),
        "history_events_count": int(history_events_count),
    }

    season_rows = _build_season_rows(team)
    sections = _build_sections(team_name, league_level, summary, season_rows, events_full)

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "summary": summary,
        "sections": sections,
        "season_rows": season_rows,
        "events": events_full,
        "notes": list(DEFAULT_NOTES),
    }


def write_club_history_json(data: Dict[str, Any], output_path: Path | str) -> Path:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def export_club_history_json_from_world(save_path: Path | str, output_path: Path | str) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でクラブ史用 JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    snap = build_club_history_readonly_dict(user, max_events=None)
    write_club_history_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot club history JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    args = parser.parse_args(argv)
    export_club_history_json_from_world(args.save, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
