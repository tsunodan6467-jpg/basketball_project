"""
日程メニュー用の読み取り専用ビュー生成（Season を壊さない）。

正本: docs/SCHEDULE_MENU_SPEC_V1.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.competition_display import (
    competition_category,
    competition_display_name,
    competition_display_name_from_event,
)


def _team_matches_side(user_team: Any, side: Any) -> bool:
    if user_team is None or side is None:
        return False
    if user_team is side:
        return True
    uid = getattr(user_team, "team_id", None)
    oid = getattr(side, "team_id", None)
    if uid is not None and oid is not None and int(uid) == int(oid):
        return True
    return False


def home_away_for_user(user_team: Any, home_team: Any, away_team: Any) -> Tuple[str, str]:
    """(一覧用短縮, 詳細用長文)。"""
    if _team_matches_side(user_team, home_team):
        return "H", "ホーム"
    if _team_matches_side(user_team, away_team):
        return "A", "アウェイ"
    return "—", "—"


def opponent_name_for_user(user_team: Any, home_team: Any, away_team: Any) -> str:
    if _team_matches_side(user_team, home_team):
        return str(getattr(away_team, "name", "-") or "-")
    if _team_matches_side(user_team, away_team):
        return str(getattr(home_team, "name", "-") or "-")
    return "-"


def round_month_label(season: Any, round_number: int) -> str:
    getter = getattr(season, "_get_round_config", None)
    if callable(getter):
        try:
            cfg = getter(int(round_number)) or {}
        except Exception:
            cfg = {}
    else:
        cfg = {}
    m = cfg.get("month")
    try:
        if m is not None:
            return f"{int(m)}月頃"
    except (TypeError, ValueError):
        pass
    return "—"


def upcoming_rows_for_user_team(
    season: Any,
    user_team: Any,
    *,
    league_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    自チームが関係する未来の SeasonEvent 行（主にリーグ戦）。
    current_round は「消化済みラウンド数」。次に進むのは current_round + 1。
    """
    if season is None or user_team is None:
        return []
    if bool(getattr(season, "season_finished", False)):
        return []

    cr = int(getattr(season, "current_round", 0) or 0)
    total = int(getattr(season, "total_rounds", 0) or 0)
    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return []

    rows: List[Dict[str, Any]] = []
    for r in range(cr + 1, total + 1):
        try:
            events = list(getter(r) or [])
        except Exception:
            continue
        month_lbl = round_month_label(season, r)
        rounds_until = max(0, r - cr)

        for ev in events:
            if str(getattr(ev, "event_type", "") or "") != "game":
                continue
            home_team = getattr(ev, "home_team", None)
            away_team = getattr(ev, "away_team", None)
            if not _team_matches_side(user_team, home_team) and not _team_matches_side(
                user_team, away_team
            ):
                continue
            ct = str(getattr(ev, "competition_type", "") or "")
            if league_only and ct != "regular_season":
                continue
            ha_s, ha_l = home_away_for_user(user_team, home_team, away_team)
            opp = opponent_name_for_user(user_team, home_team, away_team)
            rows.append(
                {
                    "round": r,
                    "rounds_until": rounds_until,
                    "month_label": month_lbl,
                    "competition_type": ct,
                    "competition_display": competition_display_name_from_event(ev),
                    "competition_category": competition_category(ct),
                    "ha_short": ha_s,
                    "ha_long": ha_l,
                    "opponent": opp,
                    "event_id": str(getattr(ev, "event_id", "") or ""),
                    "label": str(getattr(ev, "label", "") or ""),
                }
            )
    return rows


def next_round_schedule_lines(season: Any, user_team: Any) -> List[str]:
    """次ラウンド（シミュ進行1回分）の自チーム試合サマリ。複数あれば列挙。"""
    if season is None or user_team is None:
        return ["データがありません。"]
    if bool(getattr(season, "season_finished", False)):
        return ["シーズンは終了しています。"]

    cr = int(getattr(season, "current_round", 0) or 0)
    total = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > total:
        return ["これ以上のリーグラウンドはありません。"]

    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return ["日程データを取得できませんでした。"]

    try:
        events = list(getter(nxt) or [])
    except Exception:
        return ["日程データを取得できませんでした。"]

    mine: List[str] = []
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        home_team = getattr(ev, "home_team", None)
        away_team = getattr(ev, "away_team", None)
        if not _team_matches_side(user_team, home_team) and not _team_matches_side(
            user_team, away_team
        ):
            continue
        ha_s, _ = home_away_for_user(user_team, home_team, away_team)
        opp = opponent_name_for_user(user_team, home_team, away_team)
        comp = competition_display_name_from_event(ev)
        mine.append(f"・{comp}  {ha_s}  vs {opp}")

    month_lbl = round_month_label(season, nxt)
    header = f"次に進むラウンド: {nxt} / {total}  （{month_lbl}）"
    if not mine:
        return [
            header,
            "このラウンドに自チームのリーグ予定はありません（代表ウィーク等の可能性があります）。",
            "補足: 全日本カップ・東アジアカップ等は別経路で消化されるため、別画面の大会進行で確認してください。",
        ]
    return [header, *mine]


def format_season_event_matchup_line(event: Any) -> str:
    """SeasonEvent 相当を情報画面・ログ用の1行に整形（大会名は本作固定マッピング）。"""
    et = str(getattr(event, "event_type", "") or "")
    if et and et != "game":
        return str(getattr(event, "label", "") or getattr(event, "title", "") or "")

    home = getattr(event, "home_team", None)
    away = getattr(event, "away_team", None)
    hn = str(getattr(home, "name", "-") or "-") if home is not None else "-"
    an = str(getattr(away, "name", "-") or "-") if away is not None else "-"
    if hn == "-" or an == "-":
        return str(getattr(event, "label", "") or "")

    comp = competition_display_name_from_event(event)
    return f"[{comp}] {hn} vs {an}"


def information_panel_schedule_lines(season: Any, *, max_events: int = 7) -> List[str]:
    """情報ウィンドウ「次ラウンド予定」用。全会場の対戦を列挙（schedule_display 正本）。"""
    if season is None:
        return ["シーズン未接続", "—"]
    if bool(getattr(season, "season_finished", False)):
        return ["シーズンは終了しています。", "—"]

    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return ["これ以上のリーグラウンドはありません。", "—"]

    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return ["日程データを取得できませんでした。", "—"]
    try:
        events = list(getter(nxt) or [])
    except Exception:
        return ["日程データを取得できませんでした。", "—"]

    month_lbl = round_month_label(season, nxt)
    lines = [f"次ラウンド: {nxt} / {tr}  （{month_lbl}）"]
    added = 0
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        line = format_season_event_matchup_line(ev)
        if line:
            lines.append(line)
            added += 1
        if added >= max_events:
            break

    if added == 0:
        lines.append("このラウンドに game イベントがありません（代表ウィーク等の可能性）。")
        lines.append("詳細は左メニュー「日程」から確認できます。")

    return lines


def past_league_result_rows(season: Any, user_team: Any) -> List[Dict[str, Any]]:
    """
    game_results から自チーム分のみ（第1稿は日本リーグ相当として固定表示）。
    ラウンド・H/A・延長はデータなしのため — / 不明。
    """
    if season is None or user_team is None:
        return []
    uname = str(getattr(user_team, "name", "") or "")
    if not uname:
        return []

    raw = list(getattr(season, "game_results", None) or [])
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        h = str(row.get("home_team", "") or "")
        aw = str(row.get("away_team", "") or "")
        if uname not in (h, aw):
            continue
        try:
            hs = int(row.get("home_score", 0) or 0)
            als = int(row.get("away_score", 0) or 0)
        except (TypeError, ValueError):
            continue
        if h == uname:
            ha_short, ha_long = "H", "ホーム"
            opp = aw
            won = hs > als
            is_draw = hs == als
        else:
            ha_short, ha_long = "A", "アウェイ"
            opp = h
            won = als > hs
            is_draw = hs == als

        if is_draw:
            wl = "引分"
        else:
            wl = "勝利" if won else "敗戦"
        score_line = f"{hs} - {als}"

        out.append(
            {
                "index": idx,
                "opponent": opp,
                "score": score_line,
                "result": wl,
                "ha_short": ha_short,
                "ha_long": ha_long,
                "competition_display": competition_display_name("regular_season"),
                "round_label": "—",
                "ot_label": "—",
                "note": (
                    "日本リーグ戦の記録のみ表示（大会種別・節は game_results に未格納のため —）。"
                    " 上が新しい試合順です。"
                ),
            }
        )
    out.reverse()
    for i, row in enumerate(out, start=1):
        row["display_order"] = i
    return out


def detail_text_for_upcoming_row(row: Dict[str, Any]) -> str:
    """一覧行 dict から詳細テキスト。"""
    lines = [
        f"ラウンド: {row.get('round', '—')}",
        f"あと {row.get('rounds_until', '—')} ラウンドで到来（シーズン進行ベース）",
        f"時期目安: {row.get('month_label', '—')}",
        f"大会: {row.get('competition_display', '—')}",
        f"H/A: {row.get('ha_long', '—')} ({row.get('ha_short', '—')})",
        f"対戦相手: {row.get('opponent', '—')}",
    ]
    lbl = row.get("label")
    if lbl:
        lines.append(f"内部ラベル: {lbl}")
    return "\n".join(lines)
