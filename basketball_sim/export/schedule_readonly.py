"""
Godot 日程 / スケジュール（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- 日程表示の正本ロジックは basketball_sim.systems.schedule_display（本モジュールでは変更しない）。
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

SCREEN_TITLE = "日程（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。操作は含みません。",
]

_MSG_NO_SEASON = "シーズン情報が未接続のため日程は表示できません。"


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_upcoming_row(raw: Dict[str, Any], season: Any) -> Dict[str, Any]:
    """schedule_display.upcoming_rows_for_user_team の1行を JSON 向けに正規化する。"""
    from basketball_sim.systems.schedule_display import detail_text_for_upcoming_row

    rnd = raw.get("round")
    round_int: Optional[int] = None
    if rnd is not None:
        try:
            round_int = int(rnd)
        except (TypeError, ValueError):
            round_int = None

    tr = int(getattr(season, "total_rounds", 0) or 0) if season is not None else 0
    if round_int is not None and tr > 0:
        round_label = f"ラウンド {round_int}/{tr}"
    elif round_int is not None:
        round_label = f"ラウンド {round_int}"
    else:
        round_label = "-"

    comp_disp = raw.get("competition_display")
    comp_type = raw.get("competition_type")
    competition_label = str(comp_disp or comp_type or "-").strip() or "-"
    competition_type = str(comp_type or "-").strip() or "-"

    ha = raw.get("ha_long") or raw.get("ha_short") or "-"
    ha_s = str(ha).strip() if ha is not None else "-"

    opp_raw = raw.get("opponent")
    opponent = str(opp_raw).strip() if opp_raw is not None else "-"

    month_label = str(raw.get("month_label") or "").strip() or "-"

    eid = raw.get("event_id")
    event_id = str(eid).strip() if eid is not None else "-"

    lbl = raw.get("label")
    label_extra = str(lbl).strip() if lbl is not None else ""

    detail = ""
    try:
        detail = str(detail_text_for_upcoming_row(raw)).strip()
    except Exception:
        detail = ""

    return {
        "round": round_int,
        "round_label": round_label,
        "month_label": month_label,
        "competition_type": competition_type,
        "competition_label": competition_label,
        "opponent": opponent,
        "home_away": ha_s,
        "detail": detail,
        "event_id": event_id,
        "label": label_extra if label_extra else "-",
        "is_user_team_game": True,
    }


def _next_game_dict_from_lines(lines: List[str], *, status: str) -> Dict[str, Any]:
    parts = [str(x).strip() for x in lines[:3] if str(x).strip()]
    label = " / ".join(parts) if parts else "次戦情報：未接続"
    return {
        "label": label,
        "competition": "-",
        "round_label": "-",
        "opponent": "-",
        "home_away": "-",
        "status": status,
    }


def _next_game_dict_from_upcoming_row(row: Dict[str, Any], season: Any) -> Dict[str, Any]:
    opp = str(row.get("opponent") or "").strip() or "—"
    ha = str(row.get("ha_long") or row.get("ha_short") or "").strip() or "—"
    comp = str(row.get("competition_display") or row.get("competition_type") or "").strip() or "試合"
    month = str(row.get("month_label") or "").strip()
    head = f"次戦：{opp}（{ha}）・{comp}"
    label = f"{head}・{month}" if month else head

    rnd = row.get("round")
    round_label = "-"
    tr = int(getattr(season, "total_rounds", 0) or 0)
    if rnd is not None:
        try:
            ri = int(rnd)
            round_label = f"ラウンド {ri}/{tr}" if tr > 0 else f"ラウンド {ri}"
        except (TypeError, ValueError):
            round_label = str(rnd)

    competition = str(row.get("competition_display") or row.get("competition_type") or "-").strip() or "-"

    return {
        "label": label,
        "competition": competition,
        "round_label": round_label,
        "opponent": opp,
        "home_away": ha,
        "status": "from_upcoming",
    }


def _build_next_game_dict(season: Any, team: Any) -> Dict[str, Any]:
    """
    home_dashboard_readonly._next_game_one_line と同優先度で次戦カード dict を組み立てる。

    1. Emperor Cup メイン次戦行
    2. Division Playoff メイン次戦行
    3. upcoming_rows の先頭行
    4. next_advance_display_hints の one_line
    5. フォールバック
    """
    if season is None or team is None:
        return {
            "label": "次戦情報：未接続",
            "competition": "-",
            "round_label": "-",
            "opponent": "-",
            "home_away": "-",
            "status": "unavailable",
        }

    from basketball_sim.systems.schedule_display import (
        build_division_playoff_main_next_lines,
        build_emperor_cup_main_next_lines,
        next_advance_display_hints,
        upcoming_rows_for_user_team,
    )

    sn = int(getattr(season, "season_no", 1) or 1)

    cup = build_emperor_cup_main_next_lines(season, team, season_year=sn)
    if cup:
        return _next_game_dict_from_lines(list(cup), status="from_emperor_cup_lines")

    po = build_division_playoff_main_next_lines(season, team, season_year=sn)
    if po:
        return _next_game_dict_from_lines(list(po), status="from_division_playoff_lines")

    rows = upcoming_rows_for_user_team(season, team, league_only=False)
    if rows:
        return _next_game_dict_from_upcoming_row(rows[0], season)

    block, one = next_advance_display_hints(season, team)
    if isinstance(one, str) and one.strip():
        return {
            "label": one.strip(),
            "competition": "-",
            "round_label": "-",
            "opponent": "-",
            "home_away": "-",
            "status": "from_advance_hint",
        }

    return {
        "label": "次戦情報：未接続",
        "competition": "-",
        "round_label": "-",
        "opponent": "-",
        "home_away": "-",
        "status": "no_match",
    }


def _build_advance_hint(season: Any, team: Any) -> Dict[str, str]:
    if season is None or team is None:
        return {"block": "", "one_line": ""}
    from basketball_sim.systems.schedule_display import next_advance_display_hints

    block, one = next_advance_display_hints(season, team)
    b = block if isinstance(block, str) else ""
    o = one if isinstance(one, str) else ""
    return {"block": b, "one_line": o}


def build_schedule_readonly_dict(
    season: Any,
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_upcoming: int = 8,
) -> Dict[str, Any]:
    """
    Godot 日程閲覧用 dict を返す（読み取り専用）。

    season が None の場合でも必須トップキーをすべて返す。
    """
    from basketball_sim.systems.schedule_display import upcoming_rows_for_user_team

    team_name = _team_display_name(team)
    lv_raw = getattr(team, "league_level", None) if team is not None else None
    league_level = _safe_int_optional(lv_raw)

    has_season = season is not None
    season_label = _season_progress_label(
        season,
        season_count=season_count,
        at_annual_menu=at_annual_menu,
    )

    if not has_season:
        summary: Dict[str, Any] = {
            "has_season": False,
            "current_round": None,
            "total_rounds": None,
            "upcoming_count": 0,
        }
        upcoming_games: List[Dict[str, Any]] = []
        next_game = {
            "label": "次戦情報：未接続",
            "competition": "-",
            "round_label": "-",
            "opponent": "-",
            "home_away": "-",
            "status": "unavailable",
        }
        advance_hint = {"block": "", "one_line": ""}
        empty_message = _MSG_NO_SEASON
    else:
        cr = _safe_int_optional(getattr(season, "current_round", None))
        tr = _safe_int_optional(getattr(season, "total_rounds", None))
        raw_rows = upcoming_rows_for_user_team(season, team, league_only=False)
        cap = max(0, int(max_upcoming))
        sliced = raw_rows[:cap] if cap else []
        upcoming_games = [_normalize_upcoming_row(r, season) for r in sliced]

        summary = {
            "has_season": True,
            "current_round": cr,
            "total_rounds": tr,
            "upcoming_count": len(upcoming_games),
        }
        next_game = _build_next_game_dict(season, team)
        advance_hint = _build_advance_hint(season, team)
        empty_message = ""

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": league_level,
        "season_label": season_label,
        "summary": summary,
        "next_game": next_game,
        "upcoming_games": upcoming_games,
        "advance_hint": advance_hint,
        "empty_message": empty_message,
        "notes": list(DEFAULT_NOTES),
    }


def write_schedule_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_schedule_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_upcoming: int = 8,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で日程閲覧用 JSON を書き出す。セーブファイルは上書きしない。

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
    snap = build_schedule_readonly_dict(
        season,
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_upcoming=max_upcoming,
    )
    write_schedule_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot schedule / calendar JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-upcoming",
        type=int,
        default=8,
        help="Max rows in upcoming_games (default: 8)",
    )
    args = parser.parse_args(argv)
    export_schedule_json_from_world(args.save, args.output, max_upcoming=int(args.max_upcoming))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
