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


def _team_key_for_schedule(team: Any) -> int:
    tid = getattr(team, "team_id", None)
    return int(tid) if tid is not None else id(team)


def user_still_active_in_emperor_cup_field(season: Any, user_team: Any) -> bool:
    """全日本カップのブラケットにまだ残っている（または未開催前で登録済み）か。"""
    if season is None or user_team is None:
        return False
    uid = _team_key_for_schedule(user_team)
    cur = getattr(season, "emperor_cup_current_teams", None) or []
    if any(_team_key_for_schedule(t) == uid for t in cur):
        return True
    played = getattr(season, "emperor_cup_played_stages", None) or set()
    if not played:
        bye = getattr(season, "emperor_cup_bye_teams", None) or []
        r1 = getattr(season, "emperor_cup_round1_teams", None) or []
        return any(_team_key_for_schedule(t) == uid for t in bye) or any(
            _team_key_for_schedule(t) == uid for t in r1
        )
    return False


def user_team_participates_in_easl_stage(season: Any, user_team: Any, stage: Optional[str]) -> bool:
    """
    表示用: 当該 EASL ステージで自チームが関与する見込みがあるか（SeasonEvent 非格納の補完用）。
    シミュ正本の再現ではなく、漏れ防止のためのヒューリスティック。
    """
    if season is None or user_team is None:
        return False
    st = str(stage or "").strip()
    if not st:
        return False
    if not bool(getattr(season, "easl_enabled", False)):
        return False

    matchdays = getattr(season, "easl_matchdays", None) or {}
    if st.startswith("group_md"):
        pairs = matchdays.get(st, []) or []
        for home_team, away_team in pairs:
            if _team_matches_side(user_team, home_team) or _team_matches_side(user_team, away_team):
                return True
        return False

    if st == "semifinal":
        ko = getattr(season, "easl_knockout_teams", None) or []
        if ko:
            return any(_team_matches_side(user_team, t) for t in ko)
        groups = getattr(season, "easl_groups", None) or {}
        for tlist in groups.values():
            for t in tlist:
                if _team_matches_side(user_team, t):
                    return True
        return False

    if st == "final":
        fin = getattr(season, "easl_current_finalists", None) or []
        if fin:
            return any(_team_matches_side(user_team, t) for t in fin)
        ko = getattr(season, "easl_knockout_teams", None) or []
        if ko:
            return any(_team_matches_side(user_team, t) for t in ko)
        return False

    return False


def _append_national_window_placeholder_if_needed(
    season: Any,
    user_team: Any,
    round_number: int,
    rounds_until: int,
    month_label: str,
    rows: List[Dict[str, Any]],
) -> None:
    """
    代表ウィンドウ週は日本リーグの SeasonEvent が空になりやすい。
    全日本カップ / EASL と同様、日程「すべて」で見落としにくいよう表示のみ補完する。
    """
    if season is None or user_team is None:
        return
    if any(int(row.get("round") or 0) == int(round_number) for row in rows):
        return
    nat_get = getattr(season, "_get_round_national_window", None)
    if not callable(nat_get):
        return
    try:
        window_key = nat_get(int(round_number))
    except Exception:
        return
    if not window_key:
        return
    resolve = getattr(season, "_resolve_national_team_window_type", None)
    window_type: Optional[str] = None
    if callable(resolve):
        try:
            window_type = resolve(window_key)
        except Exception:
            window_type = None
    label_fn = getattr(season, "_get_national_team_window_label", None)
    label = label_fn(window_type) if callable(label_fn) else "代表ウィーク"
    rows.append(
        {
            "round": int(round_number),
            "rounds_until": rounds_until,
            "month_label": month_label,
            "competition_type": "national_team_window",
            "competition_display": label,
            "competition_category": competition_category("national_team_window"),
            "ha_short": "—",
            "ha_long": "（代表ウィンドウ）",
            "opponent": "（日本リーグの対戦カードはありません）",
            "event_id": f"national_window_r{int(round_number)}",
            "label": str(window_key),
        }
    )


def is_schedule_row_display_supplement(row: Dict[str, Any]) -> bool:
    """SeasonEvent に無い行を日程タブで補完しているか（表示専用）。"""
    eid = str(row.get("event_id") or "")
    return (
        eid.startswith("emperor_cup_week_r")
        or eid.startswith("easl_week_r")
        or eid.startswith("national_window_r")
    )


def count_user_games_in_sim_round(season: Any, user_team: Any, round_number: int) -> int:
    """シミュレーション1ラウンド（進行1回）に含まれる自チームの game イベント数。"""
    if season is None or user_team is None:
        return 0
    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return 0
    try:
        events = list(getter(int(round_number)) or [])
    except Exception:
        return 0
    n = 0
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        h = getattr(ev, "home_team", None)
        a = getattr(ev, "away_team", None)
        if _team_matches_side(user_team, h) or _team_matches_side(user_team, a):
            n += 1
    return n


def next_advance_display_hints(season: Any, user_team: Any) -> Tuple[str, str]:
    """
    案A（表示のみ）: 進行1回あたりの自チーム試合数とまとめ進行の説明。
    Returns:
        (advance_button_area の複数行向け, 「次の試合」パネル向け1行)
    使えないときは ("", "")。
    """
    if season is None or user_team is None:
        return "", ""
    if bool(getattr(season, "season_finished", False)):
        return "", ""
    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return "", ""
    ng = count_user_games_in_sim_round(season, user_team, nxt)
    month_lbl = round_month_label(season, nxt)
    if ng <= 0:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"自チームの対戦カード（リーグ等）はこのラウンドではありません（代表・杯などは同じ進行で処理される場合があります）。"
        )
        one = (
            f"進行予告: ラウンド{nxt}・自チームの対戦カード0件（杯等は同進行）／試合の合間の介入なし"
        )
    elif ng == 1:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"この進行に自チームの試合は合計 1 試合です。"
        )
        one = f"進行予告: ラウンド{nxt}・自チーム 1試合をまとめてシミュ／試合の合間の介入なし"
    else:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"この進行に自チームの試合は合計 {ng} 試合あり、まとめてシミュされます。"
        )
        one = f"進行予告: ラウンド{nxt}・自チーム {ng}試合まとめ進行／試合の合間の介入なし"
    block_b = "同じラウンド内では、試合と試合のあいだに個別で戦術を変えることはできません（進行前の設定がそのまま使われます）。"
    return f"{block_a}\n{block_b}", one


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

        if not league_only:
            cup_checker = getattr(season, "_should_play_emperor_cup_this_round", None)
            if callable(cup_checker) and cup_checker(r) and user_still_active_in_emperor_cup_field(
                season, user_team
            ):
                has_cup_row = any(
                    str(row.get("competition_type") or "") == "emperor_cup" and int(row.get("round") or 0) == r
                    for row in rows
                )
                if not has_cup_row:
                    rows.append(
                        {
                            "round": r,
                            "rounds_until": rounds_until,
                            "month_label": month_lbl,
                            "competition_type": "emperor_cup",
                            "competition_display": "全日本カップ",
                            "competition_category": "cup",
                            "ha_short": "—",
                            "ha_long": "（大会週）",
                            "opponent": "（同ラウンド進行で消化・対戦は抽選）",
                            "event_id": f"emperor_cup_week_r{r}",
                            "label": "",
                        }
                    )

            stage_getter = getattr(season, "_get_round_easl_stage", None)
            if callable(stage_getter):
                try:
                    easl_stage = stage_getter(r)
                except Exception:
                    easl_stage = None
                if easl_stage and user_team_participates_in_easl_stage(season, user_team, easl_stage):
                    has_easl_row = any(
                        str(row.get("competition_type") or "") == "easl"
                        and int(row.get("round") or 0) == r
                        for row in rows
                    )
                    if not has_easl_row:
                        rows.append(
                            {
                                "round": r,
                                "rounds_until": rounds_until,
                                "month_label": month_lbl,
                                "competition_type": "easl",
                                "competition_display": competition_display_name("easl"),
                                "competition_category": competition_category("easl"),
                                "ha_short": "—",
                                "ha_long": "（大会週）",
                                "opponent": "（同ラウンド進行で消化・組み合わせは抽選）",
                                "event_id": f"easl_week_r{r}_{easl_stage}",
                                "label": str(easl_stage),
                            }
                        )

            _append_national_window_placeholder_if_needed(
                season, user_team, r, rounds_until, month_lbl, rows
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

    cup_fn = getattr(season, "_should_play_emperor_cup_this_round", None)
    if callable(cup_fn) and cup_fn(nxt) and user_still_active_in_emperor_cup_field(season, user_team):
        mine.append("・全日本カップ（同ラウンド進行で消化・日程タブの「すべて」にも表示）")

    easl_get = getattr(season, "_get_round_easl_stage", None)
    if callable(easl_get):
        try:
            easl_stage = easl_get(nxt)
        except Exception:
            easl_stage = None
        if easl_stage and user_team_participates_in_easl_stage(season, user_team, easl_stage):
            mine.append(
                f"・{competition_display_name('easl')}（同ラウンド進行で消化・日程タブの「すべて」にも表示）"
            )

    nat_get = getattr(season, "_get_round_national_window", None)
    if callable(nat_get):
        try:
            nat_key = nat_get(nxt)
        except Exception:
            nat_key = None
        if nat_key:
            resolve = getattr(season, "_resolve_national_team_window_type", None)
            wtype: Optional[str] = None
            if callable(resolve):
                try:
                    wtype = resolve(nat_key)
                except Exception:
                    wtype = None
            label_fn = getattr(season, "_get_national_team_window_label", None)
            nat_label = label_fn(wtype) if callable(label_fn) else "代表ウィーク"
            mine.append(
                f"・{nat_label}（日本リーグの対戦カードなし・日程「すべて」で表示補完）"
            )

    month_lbl = round_month_label(season, nxt)
    header = f"次の進行（ラウンド {nxt} / 全 {total}・{month_lbl}）"
    ng = count_user_games_in_sim_round(season, user_team, nxt)
    if ng <= 0:
        count_line = "この進行に含まれる自チームの対戦カード（game）: 0 試合（杯・代表などは下の行と同じ進行で処理）"
    elif ng == 1:
        count_line = "この進行に含まれる自チームの対戦カード（game）: 1 試合"
    else:
        count_line = f"この進行に含まれる自チームの対戦カード（game）: {ng} 試合（同一ラウンド内はまとめてシミュ）"
    footer = (
        "「次へ進む」1回＝このラウンドまるごと進みます。"
        "試合の合間に個別の戦術介入はありません（進行前の設定が同じラウンド内すべてに使われます）。"
    )

    if not mine:
        return [
            header,
            count_line,
            "このラウンドに自チームのリーグ対戦の行はありません（代表ウィーク・杯週の可能性があります）。",
            footer,
        ]
    return [header, count_line, *mine, footer]


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
    lines = [f"次の進行で消化するラウンド: {nxt} / {tr}  （{month_lbl}）"]
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
    if is_schedule_row_display_supplement(row):
        lines.append(
            "※この行は SeasonEvent に無い大会・ウィンドウのため、日程タブでは表示補完です。"
            "進行は他の行と同じラウンド内で一括処理されます。"
        )
    return "\n".join(lines)
