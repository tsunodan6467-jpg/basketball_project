"""
Godot 試合ログ（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- 保存済み Season.match_logs の excerpt のみ export する（full PBP / full commentary なし）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from basketball_sim.export.home_dashboard_readonly import (
    _season_progress_label,
    _team_display_name,
)

SCREEN_TITLE = "試合ログ（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。操作は含みません。",
    "commentary は試合時点の head/tail excerpt のみ。full PBP は含みません。",
]

_MSG_NO_SEASON = "シーズン情報が未接続のため試合ログは表示できません。"
_MSG_NO_LOGS = "まだ保存済みの試合ログはありません。"

_DEFAULT_MAX_LOGS = 50
_MAX_KEY_PLAYS = 8

_KEY_PLAY_FIELDS = (
    "play_no",
    "quarter",
    "result_type",
    "text",
    "commentary_text",
    "home_score",
    "away_score",
)

_ENTRY_REQUIRED_KEYS = (
    "match_id",
    "event_id",
    "round",
    "competition_type",
    "stage",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "user_team",
    "user_result",
    "summary_line",
    "commentary_excerpt",
    "key_plays",
    "captured_at",
)


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _json_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return None


def _resolve_max_logs(max_logs: Any) -> int:
    try:
        cap = int(max_logs)
    except (TypeError, ValueError):
        return _DEFAULT_MAX_LOGS
    if cap <= 0:
        return _DEFAULT_MAX_LOGS
    return cap


def _normalize_commentary_excerpt(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"head": [], "tail": [], "total_lines": 0}

    head_raw = raw.get("head")
    tail_raw = raw.get("tail")
    head: List[str] = []
    tail: List[str] = []

    if isinstance(head_raw, list):
        head = [str(x) for x in head_raw]
    elif head_raw is not None:
        head = [str(head_raw)]

    if isinstance(tail_raw, list):
        tail = [str(x) for x in tail_raw]
    elif tail_raw is not None:
        tail = [str(tail_raw)]

    total = _safe_int_optional(raw.get("total_lines"))
    if total is None:
        total = len(head) + len(tail)

    return {"head": head, "tail": tail, "total_lines": int(total)}


def _normalize_key_play(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    out: Dict[str, Any] = {}
    for field in _KEY_PLAY_FIELDS:
        if field not in raw:
            continue
        val = raw[field]
        if field in ("play_no", "quarter", "home_score", "away_score"):
            out[field] = _safe_int_optional(val)
        elif field == "result_type":
            out[field] = _safe_str(val, "-")
        else:
            scalar = _json_scalar(val)
            if scalar is not None:
                out[field] = scalar if isinstance(scalar, str) else str(scalar)
            else:
                out[field] = _safe_str(val, "")
    return out if out else None


def _normalize_key_plays(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        play = _normalize_key_play(item)
        if play is not None:
            out.append(play)
    if len(out) > _MAX_KEY_PLAYS:
        out = out[-_MAX_KEY_PLAYS:]
    return out


def _normalize_match_log_entry(raw: Any) -> Dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}

    entry: Dict[str, Any] = {
        "match_id": _safe_str(src.get("match_id")),
        "event_id": _safe_str(src.get("event_id")),
        "round": _safe_int_optional(src.get("round")),
        "competition_type": _safe_str(src.get("competition_type")),
        "stage": _safe_str(src.get("stage")),
        "home_team": _safe_str(src.get("home_team")),
        "away_team": _safe_str(src.get("away_team")),
        "home_score": _safe_int_optional(src.get("home_score")),
        "away_score": _safe_int_optional(src.get("away_score")),
        "user_team": _safe_str(src.get("user_team")),
        "user_result": _safe_str(src.get("user_result"), "unknown"),
        "summary_line": _safe_str(src.get("summary_line")),
        "commentary_excerpt": _normalize_commentary_excerpt(src.get("commentary_excerpt")),
        "key_plays": _normalize_key_plays(src.get("key_plays")),
        "captured_at": _safe_str(src.get("captured_at"), "simulate_next_round"),
    }

    week = _safe_int_optional(src.get("week"))
    if week is not None:
        entry["week"] = week
    day = _safe_str(src.get("day_of_week"))
    if day:
        entry["day_of_week"] = day
    if src.get("user_team_involved") is not None:
        entry["user_team_involved"] = bool(src.get("user_team_involved"))

    return entry


def _latest_round(logs: List[Dict[str, Any]]) -> Optional[int]:
    rounds: List[int] = []
    for entry in logs:
        rnd = _safe_int_optional(entry.get("round"))
        if rnd is not None:
            rounds.append(rnd)
    return max(rounds) if rounds else None


def _slice_match_logs(logs: List[Dict[str, Any]], max_logs: int) -> List[Dict[str, Any]]:
    cap = _resolve_max_logs(max_logs)
    if len(logs) <= cap:
        return list(logs)
    return list(logs[-cap:])


def _raw_match_logs(season: Any) -> List[Any]:
    if season is None:
        return []
    raw = getattr(season, "match_logs", None)
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    return list(raw)


def build_match_logs_readonly_dict(
    season: Any,
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_logs: int = _DEFAULT_MAX_LOGS,
) -> Dict[str, Any]:
    """
    Godot 試合ログ閲覧用 dict を返す（読み取り専用）。

    season が None の場合でも必須トップキーをすべて返す。
    """
    team_name = _team_display_name(team)
    lv_raw = getattr(team, "league_level", None) if team is not None else None
    league_level = _safe_int_optional(lv_raw)
    season_label = _season_progress_label(
        season,
        season_count=season_count,
        at_annual_menu=at_annual_menu,
    )

    has_season = season is not None

    if not has_season:
        summary: Dict[str, Any] = {
            "has_season": False,
            "has_logs": False,
            "count": 0,
            "exported_count": 0,
            "latest_round": None,
            "current_round": None,
            "total_rounds": None,
        }
        return {
            "screen_title": SCREEN_TITLE,
            "team_name": team_name,
            "league_level": league_level,
            "season_label": season_label,
            "summary": summary,
            "match_logs": [],
            "empty_message": _MSG_NO_SEASON,
            "notes": list(DEFAULT_NOTES),
        }

    raw_logs = _raw_match_logs(season)
    normalized_all = [_normalize_match_log_entry(item) for item in raw_logs]
    total_count = len(normalized_all)
    exported = _slice_match_logs(normalized_all, max_logs)

    current_round = _safe_int_optional(getattr(season, "current_round", None))
    total_rounds = _safe_int_optional(getattr(season, "total_rounds", None))

    summary = {
        "has_season": True,
        "has_logs": total_count > 0,
        "count": total_count,
        "exported_count": len(exported),
        "latest_round": _latest_round(normalized_all),
        "current_round": current_round,
        "total_rounds": total_rounds,
    }

    if total_count == 0:
        empty_message = _MSG_NO_LOGS
    else:
        empty_message = ""

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "season_label": season_label,
        "summary": summary,
        "match_logs": exported,
        "empty_message": empty_message,
        "notes": list(DEFAULT_NOTES),
    }


def write_match_logs_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_match_logs_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_logs: int = _DEFAULT_MAX_LOGS,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で試合ログ用 JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    season = payload.get("resume_season")
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
    snap = build_match_logs_readonly_dict(
        season,
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_logs=max_logs,
    )
    write_match_logs_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot match logs JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-logs",
        type=int,
        default=_DEFAULT_MAX_LOGS,
        help=f"Max rows in match_logs (default: {_DEFAULT_MAX_LOGS})",
    )
    args = parser.parse_args(argv)
    export_match_logs_json_from_world(args.save, args.output, max_logs=int(args.max_logs))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
