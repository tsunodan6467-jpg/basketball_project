"""
CLI choice "9" 用シーズン完走サマリー（表示のみ）。

season / user_team / game_results 追加分 slice から表示行を組み立てる。
simulate 本体・save 構造は変更しない。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "format_season_end_summary_lines",
]

_SCREEN_TITLE = "【シーズン完走サマリー】"


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _team_name(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return str(obj.get("name", obj.get("team_name", "")) or "").strip()
    return str(getattr(obj, "name", "") or "").strip()


def _user_team_name(user_team: Any) -> str:
    return _team_name(user_team)


def _team_id(obj: Any) -> Optional[int]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return _safe_int(obj.get("team_id"))
    return _safe_int(getattr(obj, "team_id", None))


def _teams_match(user_team: Any, candidate: Any) -> bool:
    if user_team is None or candidate is None:
        return False
    uid = _team_id(user_team)
    cid = _team_id(candidate)
    if uid is not None and cid is not None and uid == cid:
        return True
    uname = _user_team_name(user_team)
    cname = _team_name(candidate)
    return bool(uname and cname and uname == cname)


def _division_label(level: Any) -> str:
    lv = _safe_int(level)
    if lv in (1, 2, 3):
        return f"D{lv}"
    return "未確認"


def _money_label(value: Any) -> str:
    money = _safe_int(value)
    if money is None:
        return "未確認"
    try:
        from basketball_sim.systems.money_display import format_money_yen_ja_readable

        return format_money_yen_ja_readable(money)
    except Exception:
        return f"{money:,}円"


def _parse_user_game_row(user_name: str, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(row, dict) or not user_name:
        return None
    home = str(row.get("home_team", "") or "").strip()
    away = str(row.get("away_team", "") or "").strip()
    if user_name not in (home, away):
        return None

    hs = _safe_int(row.get("home_score"))
    als = _safe_int(row.get("away_score"))
    if user_name == home:
        opponent = away or "—"
        user_score, opp_score = hs, als
    else:
        opponent = home or "—"
        user_score, opp_score = als, hs

    if user_score is None or opp_score is None:
        mark = "？"
        score_text = "結果不明"
    elif user_score > opp_score:
        mark = "○"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"
    elif user_score < opp_score:
        mark = "●"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"
    else:
        mark = "△"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"

    return {
        "line": f"{mark} {score_text}",
        "won": user_score is not None and opp_score is not None and user_score > opp_score,
        "lost": user_score is not None and opp_score is not None and user_score < opp_score,
        "draw": user_score is not None and opp_score is not None and user_score == opp_score,
        "unknown": user_score is None or opp_score is None,
    }


def _iter_user_games(user_team: Any, new_results: Any) -> List[Dict[str, Any]]:
    user_name = _user_team_name(user_team)
    games: List[Dict[str, Any]] = []
    if not user_name:
        return games
    for row in list(new_results or []):
        parsed = _parse_user_game_row(user_name, row)
        if parsed is not None:
            games.append(parsed)
    return games


def _count_user_record(user_games: List[Dict[str, Any]]) -> Tuple[int, int, int, int]:
    wins = sum(1 for g in user_games if g.get("won"))
    losses = sum(1 for g in user_games if g.get("lost"))
    draws = sum(1 for g in user_games if g.get("draw"))
    unknowns = sum(1 for g in user_games if g.get("unknown"))
    return wins, losses, draws, unknowns


def _recent_game_lines(
    user_games: List[Dict[str, Any]], max_recent_games: int
) -> List[str]:
    cap = max(0, int(max_recent_games))
    if cap <= 0 or not user_games:
        return []
    recent = user_games[-cap:]
    lines = ["直近試合:"]
    lines.extend(str(g.get("line", "")) for g in recent)
    return lines


def _find_user_rank(
    season: Any, user_team: Any, league_level_before: Optional[int]
) -> Optional[Tuple[int, int]]:
    level = _safe_int(league_level_before)
    if level is None or season is None or user_team is None:
        return None
    leagues = getattr(season, "leagues", None) or {}
    teams_in_level = leagues.get(level) if isinstance(leagues, dict) else None
    if not teams_in_level:
        return None
    get_standings = getattr(season, "get_standings", None)
    if not callable(get_standings):
        return None
    try:
        standings = list(get_standings(teams_in_level))
    except Exception:
        return None
    for rank, team in enumerate(standings, start=1):
        if _teams_match(user_team, team):
            return level, rank
    return None


def _playoff_summary(
    season: Any, user_team: Any, league_level_before: Optional[int]
) -> str:
    level = _safe_int(league_level_before)
    if level is None or season is None or user_team is None:
        return "PO: 未確認"
    po_results = getattr(season, "division_playoff_results", None) or {}
    if not isinstance(po_results, dict):
        return "PO: 未確認"
    result = po_results.get(level)
    if not isinstance(result, dict):
        return "PO: 未確認"

    div = _division_label(level)
    champion = result.get("champion")
    runner_up = result.get("runner_up")
    playoff_teams = list(result.get("playoff_teams") or [])

    if _teams_match(user_team, champion):
        return f"PO: {div}優勝"
    if _teams_match(user_team, runner_up):
        return f"PO: {div}準優勝"
    for team in playoff_teams:
        if _teams_match(user_team, team):
            return f"PO: {div}進出"
    return f"PO: {div}未進出"


def _user_in_competition_result(user_team: Any, results: Any) -> Optional[str]:
    if not isinstance(results, dict) or user_team is None:
        return None
    champion = results.get("champion")
    runner_up = results.get("runner_up")
    if _teams_match(user_team, champion):
        return "優勝"
    if _teams_match(user_team, runner_up):
        return "準優勝"
    for team in list(results.get("semifinalists") or []):
        if _teams_match(user_team, team):
            return "4強"
    return None


def _competition_summary(season: Any, user_team: Any) -> str:
    if season is None or user_team is None:
        return "大会: 未確認"
    parts: List[str] = []
    labels = (
        ("emperor_cup_results", "天皇杯"),
        ("easl_results", "EASL"),
        ("acl_results", "ACL"),
    )
    for attr, label in labels:
        results = getattr(season, attr, None)
        outcome = _user_in_competition_result(user_team, results)
        if outcome:
            parts.append(f"{label}{outcome}")
    if not parts:
        return "大会: 該当なし"
    return "大会: " + " / ".join(parts)


def _promotion_relegation_summary(
    user_team: Any, league_level_before: Optional[int]
) -> Tuple[str, str]:
    before = _safe_int(league_level_before)
    after = _safe_int(getattr(user_team, "league_level", None)) if user_team is not None else None
    if before is None or after is None:
        return "所属Division: 未確認", "昇降格: 未確認"

    before_label = _division_label(before)
    after_label = _division_label(after)
    division_line = f"所属Division: {before_label} → {after_label}"

    if before == after:
        return division_line, "昇降格: 変動なし"
    if before < after:
        return division_line, f"昇降格: {before_label} → {after_label} 降格"
    return division_line, f"昇降格: {before_label} → {after_label} 昇格"


def _build_one_liner(
    *,
    promoted: bool,
    relegated: bool,
    po_line: str,
) -> str:
    if relegated:
        return "ひとこと: 降格後の再建へ。契約・財務・主力整理を確認推奨。"
    if promoted:
        return "ひとこと: 昇格後の補強へ。ロスター規模と財務余力を確認推奨。"
    if "進出" in po_line or "優勝" in po_line or "準優勝" in po_line:
        return "ひとこと: オフシーズン準備へ。GM(8)・履歴(6)を確認推奨。"
    return "ひとこと: オフシーズン準備へ。GM(8)・履歴(6)を確認推奨。"


def format_season_end_summary_lines(
    season: Any,
    user_team: Any,
    new_results: Any,
    *,
    round_before: Optional[int] = None,
    league_level_before: Optional[int] = None,
    max_recent_games: int = 10,
) -> List[str]:
    """
    シーズン完走後の短い CLI サマリー行リストを返す（読み取り専用）。
    """
    lines: List[str] = [_SCREEN_TITLE]

    total_rounds = _safe_int(getattr(season, "total_rounds", None), 0) or 0
    current_round = _safe_int(getattr(season, "current_round", None), 0) or 0
    if total_rounds > 0:
        lines.append(f"対象: ラウンド {current_round}/{total_rounds}（完走）")
    else:
        lines.append("対象: シーズン完走")

    wins = _safe_int(getattr(user_team, "regular_wins", None), 0) or 0
    losses = _safe_int(getattr(user_team, "regular_losses", None), 0) or 0
    lines.append(f"レギュラー成績: {wins}勝{losses}敗")

    division_line, promo_line = _promotion_relegation_summary(user_team, league_level_before)
    lines.append(division_line)
    lines.append(promo_line)

    rank_info = _find_user_rank(season, user_team, league_level_before)
    if rank_info is not None:
        level, rank = rank_info
        lines.append(f"最終順位: {_division_label(level)} {rank}位")
    else:
        lines.append("最終順位: 未確認")

    po_line = _playoff_summary(season, user_team, league_level_before)
    lines.append(po_line)

    user_games = _iter_user_games(user_team, new_results)
    adv_w, adv_l, adv_d, adv_u = _count_user_record(user_games)
    record_parts = [f"{adv_w}勝{adv_l}敗"]
    if adv_d:
        record_parts.append(f"{adv_d}分")
    if adv_u:
        record_parts.append(f"{adv_u}不明")
    lines.append(f"今回進行分: 自チーム {len(user_games)} 試合 / {''.join(record_parts)}")

    lines.extend(_recent_game_lines(user_games, max_recent_games))
    lines.append(_competition_summary(season, user_team))

    money = getattr(user_team, "money", None) if user_team is not None else None
    trust = _safe_int(getattr(user_team, "owner_trust", None)) if user_team is not None else None
    money_text = _money_label(money)
    trust_text = str(trust) if trust is not None else "未確認"
    lines.append(f"資金/信頼: 所持金 {money_text} / オーナー信頼 {trust_text}")

    before_lv = _safe_int(league_level_before)
    after_lv = _safe_int(getattr(user_team, "league_level", None)) if user_team is not None else None
    promoted = (
        before_lv is not None and after_lv is not None and before_lv > after_lv
    )
    relegated = (
        before_lv is not None and after_lv is not None and before_lv < after_lv
    )
    lines.append(_build_one_liner(promoted=promoted, relegated=relegated, po_line=po_line))
    return lines
