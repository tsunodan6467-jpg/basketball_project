"""
シーズン中の順位・次戦まわりの「重要度」CLI 補助（表示のみ）。
順位計算・日程・試合シミュは変更しない。
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

_PO_BUBBLE_LO = 6
_PO_BUBBLE_HI = 10


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _league_teams(season: Any, league_level: int) -> List[Any]:
    try:
        leagues = getattr(season, "leagues", None)
        if not isinstance(leagues, dict):
            return []
        raw = leagues.get(int(league_level))
        if not raw:
            return []
        return list(raw)
    except Exception:
        return []


def _standings_order(season: Any, teams: List[Any]) -> List[Any]:
    getter = getattr(season, "get_standings", None)
    if callable(getter) and teams:
        try:
            return list(getter(list(teams)))
        except Exception:
            pass
    try:
        return sorted(
            list(teams),
            key=lambda t: (
                _safe_int(getattr(t, "regular_wins", 0), 0),
                _safe_int(getattr(t, "regular_points_for", 0), 0)
                - _safe_int(getattr(t, "regular_points_against", 0), 0),
            ),
            reverse=True,
        )
    except Exception:
        return list(teams)


def _rank_in_standings(ordered: List[Any], team: Any) -> Optional[int]:
    tid = getattr(team, "team_id", None)
    for i, t in enumerate(ordered, start=1):
        if getattr(t, "team_id", object()) == tid:
            return i
    return None


def _recent_win_loss_streak(season: Any, user_team: Any) -> Tuple[int, str]:
    """game_results から直近の連勝/連敗数（読み取りのみ）。"""
    results = list(getattr(season, "game_results", []) or [])
    if not results:
        return 0, ""
    uname = str(getattr(user_team, "name", "") or "").strip()
    if not uname:
        return 0, ""
    streak_ch = ""
    count = 0
    for row in reversed(results):
        home = str(row.get("home_team", "") or "").strip()
        away = str(row.get("away_team", "") or "").strip()
        if uname not in (home, away):
            continue
        try:
            hs = int(row.get("home_score", 0))
            aw = int(row.get("away_score", 0))
        except (TypeError, ValueError):
            continue
        won = (uname == home and hs > aw) or (uname == away and aw > hs)
        ch = "W" if won else "L"
        if not streak_ch:
            streak_ch = ch
            count = 1
        elif ch == streak_ch:
            count += 1
        else:
            break
    return count, streak_ch


def build_match_importance_tags(
    season: Any,
    user_team: Any,
    opp_team: Any,
    *,
    league_level: Optional[int] = None,
) -> List[str]:
    """
    短いタグの列（最大3つ目安）。相手なしのときは順位・境界・連勝敗のみ。
    """
    tags: List[str] = []
    try:
        lv = int(
            league_level if league_level is not None else getattr(user_team, "league_level", 1) or 1
        )
        teams = _league_teams(season, lv)
        ordered = _standings_order(season, teams)
        n = len(ordered)
        if n <= 0:
            return []

        ur = _rank_in_standings(ordered, user_team)
        if ur is None:
            return []

        orank: Optional[int] = None
        if opp_team is not None:
            orank = _rank_in_standings(ordered, opp_team)

        # --- 直接対決・接近戦 ---
        if orank is not None:
            if ur <= 4 and orank <= 4:
                tags.append("上位直接対決")
            elif abs(ur - orank) <= 2:
                tags.append("順位接近戦")
            elif ur <= 8 and orank <= 8 and n >= 9:
                tags.append("重要度高め")

        # --- PO 圏（簡易） ---
        if n >= 8 and _PO_BUBBLE_LO <= ur <= min(_PO_BUBBLE_HI, n - 1):
            tags.append("PO圏争い")

        # --- 昇格 / 降格の目安（シーズン制度の粗い近似・表示のみ） ---
        if lv == 1 and n >= 6 and ur >= n - 1:
            tags.append("降格圏争い")
        elif lv >= 2 and ur <= 4 and n >= 6:
            tags.append("昇格圏争い")
        elif lv >= 2 and n >= 6 and ur >= n - 2:
            tags.append("降格圏争い")

        # --- 連勝 / 連敗（取れたときのみ） ---
        sc, st = _recent_win_loss_streak(season, user_team)
        if sc >= 3 and st == "L":
            tags.append("連敗ストップがかかる")
        elif sc >= 3 and st == "W":
            tags.append("連勝継続がかかる")

        # 重複除去・順序維持
        out: List[str] = []
        for t in tags:
            if t and t not in out:
                out.append(t)
        if not out:
            out.append("順位積み上げ戦")
        return out[:4]
    except Exception:
        return []


def _context_subline(tags: List[str], *, has_opponent: bool) -> str:
    if not tags:
        return ""
    if "上位直接対決" in tags:
        return "順位上位同士 — 勝敗が卓を左右しやすい"
    if "順位接近戦" in tags:
        return "順位が接近 — 1勝の価値が大きい"
    if "PO圏争い" in tags:
        return "プレーオフ圏の得失に直結しやすい"
    if "昇格圏争い" in tags or "降格圏争い" in tags:
        return "シーズン終盤に向けた枠の争いに絡みやすい"
    if "連敗ストップがかかる" in tags:
        return "流れを切り替えたい局面"
    if "連勝継続がかかる" in tags:
        return "勢いを維持したい局面"
    if has_opponent and "重要度高め" in tags:
        return "上位同士に近い — 注目度が高い一戦"
    return ""


def format_schedule_importance_cli_lines(
    season: Any,
    user_team: Any,
    opp_team: Any,
    *,
    for_standings_only: bool = False,
) -> List[str]:
    """
    1〜2行の【試合重要度】ブロック。情報が取れなければ短いフォールバック。
    """
    try:
        tags = build_match_importance_tags(
            season,
            user_team,
            None if for_standings_only else opp_team,
        )
        if not tags:
            return ["【試合重要度】情報なし"]

        line1 = "【試合重要度】" + " / ".join(tags)
        sub = _context_subline(tags, has_opponent=not for_standings_only and opp_team is not None)
        if sub:
            return [line1, sub]
        return [line1]
    except Exception:
        return ["【試合重要度】情報なし"]


def format_user_standings_importance_cli_lines(season: Any, user_team: Any) -> List[str]:
    """順位表表示後のユーザー向け1ブロック（相手なし）。"""
    return format_schedule_importance_cli_lines(
        season, user_team, None, for_standings_only=True
    )


__all__ = [
    "build_match_importance_tags",
    "format_schedule_importance_cli_lines",
    "format_user_standings_importance_cli_lines",
]
