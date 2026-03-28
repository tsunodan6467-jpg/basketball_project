"""
情報メニュー用の読み取り専用ビュー生成（Tk 非依存）。

正本: docs/INFORMATION_MENU_SPEC_V1.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.player_stats import PlayerStatsManager


def _league_teams(season: Any, level: int) -> List[Any]:
    if season is None:
        return []
    leagues = getattr(season, "leagues", None)
    if not isinstance(leagues, dict):
        return []
    teams = leagues.get(level)
    if not teams:
        return []
    return list(teams)


def build_standings_rows(
    season: Any,
    level: int,
    *,
    user_team: Any = None,
) -> List[Dict[str, Any]]:
    """
    D{level} の順位表行。Season.get_standings が正本。
    """
    teams = _league_teams(season, level)
    if not teams:
        return []

    getter = getattr(season, "get_standings", None)
    if callable(getter):
        try:
            standings = list(getter(teams))
        except Exception:
            standings = list(teams)
    else:
        standings = list(teams)

    uname = ""
    uid = None
    if user_team is not None:
        uname = str(getattr(user_team, "name", "") or "")
        uid = getattr(user_team, "team_id", None)

    rows: List[Dict[str, Any]] = []
    for rank, t in enumerate(standings, start=1):
        w = int(getattr(t, "regular_wins", 0) or 0)
        l = int(getattr(t, "regular_losses", 0) or 0)
        g = w + l
        wpct = (w / g) if g > 0 else 0.0
        pf = int(getattr(t, "regular_points_for", 0) or 0)
        pa = int(getattr(t, "regular_points_against", 0) or 0)
        diff = pf - pa
        name = str(getattr(t, "name", "-") or "-")

        is_user = bool(getattr(t, "is_user_team", False))
        if not is_user and uname and name == uname:
            is_user = True
        if not is_user and uid is not None:
            try:
                if int(getattr(t, "team_id", -1)) == int(uid):
                    is_user = True
            except (TypeError, ValueError):
                pass

        rows.append(
            {
                "rank": rank,
                "name": name,
                "wins": w,
                "losses": l,
                "win_pct": wpct,
                "pf": pf,
                "pa": pa,
                "diff": diff,
                "is_user_row": is_user,
            }
        )
    return rows


def build_team_summary_rows(
    season: Any,
    level: int,
) -> List[Dict[str, Any]]:
    """チーム成績タブ用（順位表と同順）。平均得失点は試合数で割る。"""
    base = build_standings_rows(season, level, user_team=None)
    out: List[Dict[str, Any]] = []
    for row in base:
        w = int(row["wins"])
        l = int(row["losses"])
        g = max(1, w + l)
        pf = int(row["pf"])
        pa = int(row["pa"])
        out.append(
            {
                **row,
                "avg_pf": pf / g,
                "avg_pa": pa / g,
                "avg_diff": (pf - pa) / g,
            }
        )
    return out


def player_stat_options() -> List[Tuple[str, str]]:
    """(コンボ表示ラベル, stat_key) の列。"""
    opts: List[Tuple[str, str]] = []
    for key, spec in PlayerStatsManager.STAT_DEFINITIONS.items():
        opts.append((str(spec.get("label", key)), key))
    return opts


def build_player_leaderboard_rows(
    season: Any,
    level: int,
    stat_key: str,
    *,
    top_n: int = 40,
    min_games: int = 1,
) -> List[Dict[str, Any]]:
    teams = _league_teams(season, level)
    if not teams:
        return []
    if stat_key not in PlayerStatsManager.STAT_DEFINITIONS:
        return []

    try:
        raw = PlayerStatsManager.get_leaderboard(
            teams=teams,
            stat_key=stat_key,
            top_n=top_n,
            min_games=min_games,
        )
    except Exception:
        return []

    spec = PlayerStatsManager.STAT_DEFINITIONS[stat_key]
    pgl = str(spec.get("per_game_label", ""))
    ttl = str(spec.get("total_label", ""))

    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(raw, start=1):
        rows.append(
            {
                "rank": i,
                "name": row.get("name", "-"),
                "team_name": row.get("team_name", "-"),
                "position": row.get("position", "-"),
                "ovr": row.get("ovr", "-"),
                "per_game": row.get("display_value", "-"),
                "per_game_label": pgl,
                "total": row.get("total", 0),
                "total_label": ttl,
                "games_played": row.get("games_played", 0),
            }
        )
    return rows


def build_information_news_lines(
    *,
    team_name: str,
    rank_text: str,
    wins: int,
    losses: int,
    external_items: Optional[List[str]] = None,
) -> List[str]:
    """
    情報ウィンドウ「リーグニュース」用。
    external_items があればそれをそのまま採用（主画面と同じ external_news_items）。
    """
    if external_items is not None:
        return list(external_items)
    lines = [
        f"{team_name} は現在 {rank_text}、戦績は {int(wins)}勝{int(losses)}敗",
        "リーグ各地でロスター争いが活発化しています",
        "次節へ向けてコンディション管理が注目されています",
        "オーナー評価と財務バランスの両立が今季の鍵です",
    ]
    return lines


def _fmt_player_award_line(season: Any, label: str, player: Any) -> Optional[str]:
    if player is None:
        return None
    pname = str(getattr(player, "name", "-") or "-")
    pid = getattr(player, "player_id", None)
    team_part = ""
    resolver = getattr(season, "_get_team_name", None)
    if callable(resolver) and pid is not None:
        try:
            tn = resolver(pid)
            if tn:
                team_part = f"（{tn}）"
        except Exception:
            pass
    return f"{label}: {pname}{team_part}"


def format_awards_lines_for_division(season: Any, level: int) -> List[str]:
    """D{level} の awards_by_division を表示用テキスト行に。"""
    if season is None:
        return ["シーズン未接続です。"]

    finished = bool(getattr(season, "season_finished", False))
    ab = getattr(season, "awards_by_division", None)
    if not isinstance(ab, dict):
        return ["表彰データがありません。"]

    bucket = ab.get(level)
    if not isinstance(bucket, dict):
        return [f"D{level} の表彰バケツがありません。"]

    def _has_any() -> bool:
        for k in ("mvp", "roty", "scoring_champ", "rebound_champ", "assist_champ", "block_champ", "steal_champ"):
            if bucket.get(k) is not None:
                return True
        for k in ("all_league_first", "all_league_second", "all_league_third"):
            v = bucket.get(k)
            if isinstance(v, list) and len(v) > 0:
                return True
        return False

    if not _has_any():
        if not finished:
            return [
                f"D{level} のシーズン表彰はまだ確定していません。",
                "レギュラー終了後の集計が反映されたら表示されます。",
            ]
        return [f"D{level} の確定表彰データがまだありません。"]

    lines: List[str] = [f"=== D{level} シーズン表彰（確定データ）==="]

    mvp = bucket.get("mvp")
    if mvp is not None:
        line = _fmt_player_award_line(season, "MVP", mvp)
        if line:
            lines.append(line)

    roty = bucket.get("roty")
    if roty is not None:
        line = _fmt_player_award_line(season, "新人王", roty)
        if line:
            lines.append(line)

    champs = [
        ("scoring_champ", "得点王"),
        ("rebound_champ", "リバウンド王"),
        ("assist_champ", "アシスト王"),
        ("block_champ", "ブロック王"),
        ("steal_champ", "スティール王"),
    ]
    for key, lab in champs:
        p = bucket.get(key)
        if p is None:
            continue
        line = _fmt_player_award_line(season, lab, p)
        if line:
            lines.append(line)

    def _player_brief(player: Any) -> str:
        if player is None:
            return ""
        pname = str(getattr(player, "name", "-") or "-")
        pid = getattr(player, "player_id", None)
        resolver = getattr(season, "_get_team_name", None)
        if callable(resolver) and pid is not None:
            try:
                tn = resolver(pid)
                if tn:
                    return f"{pname}（{tn}）"
            except Exception:
                pass
        return pname

    def _all_lines(title: str, players: Any) -> None:
        if not isinstance(players, list) or not players:
            return
        lines.append("")
        lines.append(title)
        for p in players[:15]:
            b = _player_brief(p)
            if b:
                lines.append(f" ・{b}")

    _all_lines("オールリーグ 1st", bucket.get("all_league_first"))
    _all_lines("オールリーグ 2nd", bucket.get("all_league_second"))
    _all_lines("オールリーグ 3rd", bucket.get("all_league_third"))

    return lines
