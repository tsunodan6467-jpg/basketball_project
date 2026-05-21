"""
次ラウンド（current_round + 1）の予定を、状態変更なしで dict / lines として返す。

- 読み取り専用。Season / Team の状態を変更しない。
- simulate_next_round / Match.simulate は呼ばない。
- save / JSON 書込をしない。
- schedule_display / weekly_advance_cli_display の既存 read-only 部品を再利用する。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from basketball_sim.systems.competition_display import competition_display_name_from_event
from basketball_sim.systems.schedule_display import (
    count_user_games_in_sim_round,
    home_away_for_user,
    next_advance_display_hints,
    next_round_schedule_lines,
    opponent_name_for_user,
    schedule_month_week_label,
)
from basketball_sim.systems.weekly_advance_cli_display import format_weekly_advance_check_lines

__all__ = [
    "SCREEN_TITLE",
    "DEFAULT_NOTES",
    "build_round_advance_preview_dict",
    "format_round_advance_preview_lines",
]

SCREEN_TITLE = "ラウンド進行プレビュー（読取専用）"

DEFAULT_NOTES = [
    "読み取り専用。simulate_next_round / Match.simulate は呼びません。",
    "結果予測ではなく、次ラウンド予定の確認です。",
]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _team_display_name(team: Any) -> str:
    if team is None:
        return "—"
    name = getattr(team, "name", None)
    if name is None:
        return "—"
    s = str(name).strip()
    return s if s else "—"


def _next_round_number(season: Any) -> Optional[int]:
    if season is None:
        return None
    cr = _safe_int(getattr(season, "current_round", 0), 0)
    return cr + 1


def _season_label_text(
    season: Any,
    *,
    season_count: Optional[int],
    next_round: Optional[int],
    total_rounds: Optional[int],
    next_round_month_week: str,
    can_advance: bool,
) -> str:
    if season is None or not can_advance or next_round is None or total_rounds is None:
        return "—"
    sy = max(1, int(season_count) if season_count is not None else 1)
    cal = next_round_month_week if next_round_month_week and next_round_month_week != "—" else "—"
    return f"{sy}年目　{cal}　ラウンド{next_round}/{total_rounds}"


def _build_warnings(
    season: Any,
    user_team: Any,
    *,
    next_round: Optional[int],
    total_rounds: Optional[int],
    events_fetch_failed: bool,
    getter_missing: bool,
) -> List[str]:
    warnings: List[str] = []
    if season is None:
        warnings.append("シーズン情報がありません。")
    if user_team is None:
        warnings.append("ユーザーチーム情報がありません。")
    if season is not None:
        if bool(getattr(season, "season_finished", False)):
            warnings.append("シーズンは終了しています。ラウンド進行はできません。")
        tr = _safe_int(getattr(season, "total_rounds", 0), 0)
        if tr <= 0:
            warnings.append("総ラウンド数が取得できません。")
        if next_round is not None and tr > 0 and next_round > tr:
            warnings.append("次ラウンドは総ラウンド数を超えています。")
    if getter_missing:
        warnings.append("日程データ（get_events_for_round）を取得できません。")
    if events_fetch_failed:
        warnings.append("次ラウンドのイベント取得中にエラーが発生しました。")
    return warnings


def _event_to_preview_row(season: Any, user_team: Any, event: Any) -> Dict[str, Any]:
    home_team = getattr(event, "home_team", None)
    away_team = getattr(event, "away_team", None)
    ha_short, ha_long = home_away_for_user(user_team, home_team, away_team)
    is_user = ha_short in ("H", "A")
    opponent = opponent_name_for_user(user_team, home_team, away_team) if is_user else "—"
    try:
        comp_display = str(competition_display_name_from_event(event)).strip() or "-"
    except Exception:
        comp_display = str(getattr(event, "competition_type", "") or "-").strip() or "-"
    eid = str(getattr(event, "event_id", "") or "").strip() or "-"
    return {
        "event_id": eid,
        "event_type": str(getattr(event, "event_type", "") or "-"),
        "competition_type": str(getattr(event, "competition_type", "") or "-"),
        "competition_display": comp_display,
        "home_team": _team_display_name(home_team),
        "away_team": _team_display_name(away_team),
        "is_user_team_game": is_user,
        "opponent": opponent,
        "home_away_short": ha_short,
        "home_away_long": ha_long,
        "label": str(getattr(event, "label", "") or ""),
        "day_of_week": str(getattr(event, "day_of_week", "") or ""),
        "is_display_supplement": False,
    }


def _fetch_next_round_events(
    season: Any,
    user_team: Any,
    next_round: int,
    max_events: int,
) -> tuple[List[Dict[str, Any]], bool, bool]:
    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return [], False, True
    try:
        raw = list(getter(int(next_round)) or [])
    except Exception:
        return [], True, False
    cap = max(0, int(max_events))
    sliced = raw[:cap] if cap else []
    rows = [_event_to_preview_row(season, user_team, ev) for ev in sliced]
    return rows, False, False


def _safe_schedule_lines(season: Any, user_team: Any) -> List[str]:
    try:
        return list(next_round_schedule_lines(season, user_team))
    except Exception:
        return ["日程データを取得できませんでした。"]


def _safe_advance_hint(season: Any, user_team: Any) -> Dict[str, str]:
    try:
        block, one = next_advance_display_hints(season, user_team)
        return {
            "block": block if isinstance(block, str) else "",
            "one_line": one if isinstance(one, str) else "",
        }
    except Exception:
        return {"block": "", "one_line": ""}


def _safe_weekly_check_lines(
    season: Any,
    user_team: Any,
    free_agents: Any,
) -> List[str]:
    try:
        return list(
            format_weekly_advance_check_lines(
                season=season,
                user_team=user_team,
                free_agents=free_agents,
            )
        )
    except Exception:
        return ["【週送り前チェック】", "情報取得に失敗しました"]


def build_round_advance_preview_dict(
    season: Any,
    user_team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    free_agents: Any = None,
    max_events: int = 32,
    include_weekly_check: bool = True,
) -> Dict[str, Any]:
    _ = at_annual_menu  # reserved for future season_label alignment

    current_round: Optional[int] = None
    next_round: Optional[int] = None
    total_rounds: Optional[int] = None
    season_finished = False
    can_advance = False
    next_round_month_week = "—"
    user_team_game_count = 0

    if season is not None:
        current_round = _safe_int(getattr(season, "current_round", 0), 0)
        total_rounds = _safe_int(getattr(season, "total_rounds", 0), 0)
        season_finished = bool(getattr(season, "season_finished", False))
        next_round = current_round + 1
        if not season_finished and total_rounds > 0 and next_round <= total_rounds:
            can_advance = True
            try:
                next_round_month_week = schedule_month_week_label(season, next_round)
            except Exception:
                next_round_month_week = "—"
            try:
                user_team_game_count = count_user_games_in_sim_round(
                    season, user_team, next_round
                )
            except Exception:
                user_team_game_count = 0

    events_fetch_failed = False
    getter_missing = False
    next_round_events: List[Dict[str, Any]] = []
    if season is not None and can_advance and next_round is not None:
        next_round_events, events_fetch_failed, getter_missing = _fetch_next_round_events(
            season, user_team, next_round, max_events
        )

    warnings = _build_warnings(
        season,
        user_team,
        next_round=next_round,
        total_rounds=total_rounds,
        events_fetch_failed=events_fetch_failed,
        getter_missing=getter_missing,
    )

    season_label = _season_label_text(
        season,
        season_count=season_count,
        next_round=next_round,
        total_rounds=total_rounds,
        next_round_month_week=next_round_month_week,
        can_advance=can_advance,
    )

    user_games = [row for row in next_round_events if row.get("is_user_team_game")]
    schedule_lines = _safe_schedule_lines(season, user_team) if season is not None else []
    advance_hint = _safe_advance_hint(season, user_team) if season is not None else {"block": "", "one_line": ""}
    weekly_check_lines: List[str] = []
    if include_weekly_check and season is not None:
        weekly_check_lines = _safe_weekly_check_lines(season, user_team, free_agents)

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": _team_display_name(user_team),
        "summary": {
            "current_round": current_round,
            "next_round": next_round if can_advance else None,
            "total_rounds": total_rounds,
            "season_finished": season_finished,
            "can_advance": can_advance,
            "season_label": season_label,
            "next_round_month_week": next_round_month_week if can_advance else "—",
            "user_team_game_count": user_team_game_count if can_advance else 0,
        },
        "user_game": {
            "has_game": len(user_games) > 0,
            "games": user_games,
            "summary_lines": schedule_lines,
        },
        "next_round_events": next_round_events,
        "advance_hint": advance_hint,
        "schedule_lines": schedule_lines,
        "weekly_check_lines": weekly_check_lines,
        "warnings": warnings,
        "notes": list(DEFAULT_NOTES),
    }


def format_round_advance_preview_lines(
    season: Any,
    user_team: Any,
    **kwargs: Any,
) -> List[str]:
    data = build_round_advance_preview_dict(season, user_team, **kwargs)
    summary = data.get("summary") or {}
    lines: List[str] = [
        f"【{data.get('screen_title', SCREEN_TITLE)}】",
        f"クラブ: {data.get('team_name', '—')}",
    ]

    cr = summary.get("current_round")
    tr = summary.get("total_rounds")
    nr = summary.get("next_round")
    cal = summary.get("next_round_month_week") or "—"
    if cr is not None and tr is not None:
        lines.append(f"現在: ラウンド {cr} / {tr}")
    else:
        lines.append("現在: —")

    if summary.get("can_advance") and nr is not None and tr is not None:
        lines.append(f"次の進行: ラウンド {nr} / {tr}（{cal}）")
        lines.append(f"自チーム試合: {summary.get('user_team_game_count', 0)} 試合")
    else:
        lines.append("次の進行: 進行不可")

    one_line = (data.get("advance_hint") or {}).get("one_line") or ""
    if one_line.strip():
        lines.append(f"進行予告: {one_line.strip()}")

    for w in data.get("warnings") or []:
        if isinstance(w, str) and w.strip():
            lines.append(f"注意: {w.strip()}")

    schedule_lines = data.get("schedule_lines") or []
    for ln in schedule_lines[:4]:
        if isinstance(ln, str) and ln.strip():
            lines.append(ln.strip())

    for note in data.get("notes") or []:
        if isinstance(note, str) and note.strip():
            lines.append(note.strip())

    return lines

