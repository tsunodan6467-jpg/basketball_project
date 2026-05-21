"""
1 ラウンド進行直後の CLI 短い結果サマリー（表示のみ）。

game_results の追加分 slice から自チーム試合だけを表示する。
simulate_next_round 本体・save 構造は変更しない。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = [
    "format_post_advance_result_summary_lines",
]

_SCREEN_TITLE = "【ラウンド結果サマリー】"


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _user_team_name(user_team: Any) -> str:
    if user_team is None:
        return ""
    return str(getattr(user_team, "name", "") or "").strip()


def _parse_user_game_row(
    user_name: str,
    row: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not isinstance(row, dict):
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
        "mark": mark,
        "line": f"{mark} {score_text}",
        "won": user_score is not None and opp_score is not None and user_score > opp_score,
        "lost": user_score is not None and opp_score is not None and user_score < opp_score,
        "draw": user_score is not None and opp_score is not None and user_score == opp_score,
        "unknown": user_score is None or opp_score is None,
    }


def _build_one_liner(wins: int, losses: int, draws: int) -> str:
    if wins == 0 and losses == 0 and draws == 0:
        return "ひとこと: このラウンドの自チーム試合結果はありません。"
    if draws > 0:
        return (
            f"ひとこと: {wins}勝{losses}敗{draws}分。"
            "次ラウンド前にロスター/戦術確認推奨。"
        )
    if losses == 0 and wins > 0:
        return f"ひとこと: {wins}勝0敗。好調を維持しています。"
    if wins == 0 and losses > 0:
        return "ひとこと: 0勝{}敗。次ラウンド前にロスター/戦術確認推奨。".format(losses)
    return (
        f"ひとこと: {wins}勝{losses}敗。"
        "次ラウンド前にロスター/戦術確認推奨。"
    )


def format_post_advance_result_summary_lines(
    user_team: Any,
    new_results: Any,
    *,
    round_label: Optional[str] = None,
    max_games: int = 5,
) -> List[str]:
    """
    game_results[before_count:] から自チーム試合だけを短く表示する行リストを返す。
    """
    user_name = _user_team_name(user_team)
    raw = list(new_results or [])
    games: List[Dict[str, Any]] = []
    if user_name:
        for row in raw:
            parsed = _parse_user_game_row(user_name, row)
            if parsed is not None:
                games.append(parsed)

    lines: List[str] = [_SCREEN_TITLE]
    if round_label and str(round_label).strip():
        lines.append(f"対象: {str(round_label).strip()}")
    lines.append(f"自チーム試合: {len(games)} 試合")

    cap = max(0, int(max_games))
    shown = games[:cap] if cap else []
    for g in shown:
        lines.append(str(g.get("line", "")))

    remaining = len(games) - len(shown)
    if remaining > 0:
        lines.append(f"ほか {remaining} 試合")

    wins = sum(1 for g in games if g.get("won"))
    losses = sum(1 for g in games if g.get("lost"))
    draws = sum(1 for g in games if g.get("draw"))
    lines.append(_build_one_liner(wins, losses, draws))
    return lines

