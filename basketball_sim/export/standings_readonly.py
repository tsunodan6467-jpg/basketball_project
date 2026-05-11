"""
Godot 順位表 / リーグ状況（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- 順位行の正本は basketball_sim.systems.information_display.build_standings_rows
  （Season.get_standings を内部で利用し得るが、export 側は読み取りのみ）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from basketball_sim.export.home_dashboard_readonly import (
    _division_text,
    _season_progress_label,
    _team_display_name,
)
from basketball_sim.systems.information_display import build_standings_rows

SCREEN_TITLE = "順位表（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。操作は含みません。",
]

STANDINGS_COLUMNS: List[str] = [
    "rank",
    "team_name",
    "wins",
    "losses",
    "points_for",
    "points_against",
    "point_diff",
    "is_user_row",
]

_DIVISION_LEVELS: List[int] = [1, 2, 3]

_MSG_NO_SEASON = "シーズン情報が未接続のため順位表は表示できません。"
_MSG_EMPTY_DIVISION = "このディビジョンの順位データがありません。"


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _map_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """build_standings_rows の行を JSON 用キーへ写像する。"""
    return {
        "rank": int(raw["rank"]),
        "team_name": str(raw.get("name", "-") or "-"),
        "wins": int(raw.get("wins", 0) or 0),
        "losses": int(raw.get("losses", 0) or 0),
        "points_for": int(raw.get("pf", 0) or 0),
        "points_against": int(raw.get("pa", 0) or 0),
        "point_diff": int(raw.get("diff", 0) or 0),
        "is_user_row": bool(raw.get("is_user_row", False)),
    }


def _division_block(
    *,
    level: int,
    season: Any,
    team: Any,
    has_season: bool,
) -> Dict[str, Any]:
    label = f"D{int(level)}"
    if not has_season:
        return {
            "level": level,
            "division_label": label,
            "rows": [],
            "empty_message": _MSG_NO_SEASON,
        }
    raw_rows = build_standings_rows(season, level, user_team=team)
    rows = [_map_row(r) for r in raw_rows]
    msg = _MSG_EMPTY_DIVISION if not rows else ""
    return {
        "level": level,
        "division_label": label,
        "rows": rows,
        "empty_message": msg,
    }


def build_standings_readonly_dict(
    season: Any,
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Godot 順位表用 dict を返す（読み取り専用）。

    season が None の場合（年度メニュー直後のセーブ等）は has_season=False とし、
    全ディビジョンで rows を空にする。
    """
    team_name = _team_display_name(team)
    lv_raw = getattr(team, "league_level", None) if team is not None else None
    league_level = _safe_int_optional(lv_raw)

    has_season = season is not None
    season_label = _season_progress_label(
        season,
        season_count=season_count,
        at_annual_menu=at_annual_menu,
    )
    current_division = _division_text(team) if team is not None else "所属未定"

    divisions: List[Dict[str, Any]] = []
    for level in _DIVISION_LEVELS:
        divisions.append(
            _division_block(level=level, season=season, team=team, has_season=has_season)
        )

    summary: Dict[str, Any] = {
        "current_division": current_division,
        "division_count": len(_DIVISION_LEVELS),
        "has_season": has_season,
    }

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "season_label": season_label,
        "summary": summary,
        "columns": list(STANDINGS_COLUMNS),
        "divisions": divisions,
        "notes": list(DEFAULT_NOTES),
    }


def write_standings_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_standings_json_from_world(save_path: Path | str, output_path: Path | str) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で順位表用 JSON を書き出す。セーブファイルは上書きしない。

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
    snap = build_standings_readonly_dict(
        season,
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
    )
    write_standings_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot standings / league table JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    args = parser.parse_args(argv)
    export_standings_json_from_world(args.save, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
