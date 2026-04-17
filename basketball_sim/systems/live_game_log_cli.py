"""
試合中 CLI ログ用の短い勢い・節目補助（表示のみ。PBP 内容や試合ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _sign_diff(h: int, a: int) -> int:
    d = int(h) - int(a)
    if d > 0:
        return 1
    if d < 0:
        return -1
    return 0


def build_live_game_momentum_note(
    state: Dict[str, Any],
    *,
    prev_home: int,
    prev_away: int,
    new_home: int,
    new_away: int,
    home_name: str,
    away_name: str,
    scoring_team_key: Any,
    home_team_key: Any,
    away_team_key: Any,
    points: int,
    quarter: Any,
    clock_seconds: Any,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    得点1回分の状態更新と、出すなら1行の補助文（【試合動向】…）を返す。
    state は Match 側で保持するミュータブル dict（last_score_team_key, streak_pts）。
    """
    try:
        ph, pa = int(prev_home), int(prev_away)
        nh, na = int(new_home), int(new_away)
        pts = int(points or 0)
        q = int(quarter or 1)
        clk = int(clock_seconds or 0)
    except (TypeError, ValueError):
        return state, None

    if pts <= 0:
        return state, None

    prev_sig = _sign_diff(ph, pa)
    new_sig = _sign_diff(nh, na)
    prev_abs = abs(ph - pa)
    new_abs = abs(nh - na)

    # 連続得点（同一チームの無解答ストリーク）
    last_k = state.get("last_score_team_key")
    if scoring_team_key is not None and last_k == scoring_team_key:
        state["streak_pts"] = int(state.get("streak_pts", 0) or 0) + pts
    else:
        state["last_score_team_key"] = scoring_team_key
        state["streak_pts"] = pts

    streak = int(state.get("streak_pts", 0) or 0)
    is_home_score = scoring_team_key is not None and scoring_team_key == home_team_key
    team_label = str(home_name if is_home_score else away_name)

    parts: list[str] = []

    # 1) 逆転（同点除く・リードが入れ替わり）
    if prev_sig != 0 and new_sig != 0 and prev_sig != new_sig:
        parts.append("逆転")

    # 2) 同点になった
    if new_sig == 0 and prev_sig != 0:
        parts.append("同点")

    # 3) 2桁差に到達（今回の得点で初めて10点差以上）
    if new_abs >= 10 and prev_abs < 10 and new_sig != 0:
        parts.append("2桁リード")

    # 4) 連続得点ラン（補助。上記が無いときだけ目立たせる）
    if streak >= 6 and not parts:
        parts.append(f"{team_label}が{streak}-0ラン")

    # 5) 終盤の節目（他が無くても、僅差で得点が動いたときのみ）
    is_late = q >= 4 and clk <= 120
    if is_late and new_abs <= 10 and not parts and pts >= 2:
        parts.append("勝負所")

    if not parts:
        return state, None

    tail = "・".join(parts)
    if is_late and "勝負所" not in tail and ("逆転" in tail or "同点" in tail or "2桁リード" in tail):
        tail = tail + "（終盤）"

    line = f"【試合動向】{tail}"
    return state, line


def format_live_game_highlight_line(
    state: Dict[str, Any],
    **kwargs: Any,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """build_live_game_momentum_note のエイリアス（呼び出し側の可読性用）。"""
    return build_live_game_momentum_note(state, **kwargs)


__all__ = [
    "build_live_game_momentum_note",
    "format_live_game_highlight_line",
]
