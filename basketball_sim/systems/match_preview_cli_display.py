"""
試合直前 CLI 用の対戦プレビュー（表示のみ。試合シミュ・日程ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.gm_dashboard_text import get_current_bench_order, get_current_starting_five
from basketball_sim.systems.rotation_cli_display import _avg_starters, _safe_int_attr


def _bench_avg_ovr(team: Any, bench: List[Any]) -> float:
    if not bench:
        return 0.0
    return float(sum(_safe_int_attr(p, "ovr") for p in bench)) / float(len(bench))


def _lineup_metrics(team: Any) -> Optional[Dict[str, float]]:
    try:
        starters = list(get_current_starting_five(team) or [])
        bench = list(get_current_bench_order(team) or [])
    except Exception:
        return None
    if len(starters) < 5:
        return None
    try:
        outside = (_avg_starters(starters, "three") + _avg_starters(starters, "shoot")) / 2.0
        handler = (_avg_starters(starters, "passing") + _avg_starters(starters, "handling")) / 2.0
        inside = (_avg_starters(starters, "rebound") + _avg_starters(starters, "power")) / 2.0
        defense = _avg_starters(starters, "defense")
        bench_layer = _bench_avg_ovr(team, bench)
        return {
            "outside": outside,
            "handler": handler,
            "inside": inside,
            "defense": defense,
            "bench": bench_layer,
        }
    except Exception:
        return None


def _edge(diff: float, thresh: float = 3.0) -> str:
    if diff >= thresh:
        return "自チーム優位"
    if diff <= -thresh:
        return "相手優位"
    return "五分"


def build_matchup_edges_summary(
    user_team: Any,
    opponent_team: Any,
) -> Optional[Dict[str, Any]]:
    """
    先発5＋ベンチ序列から読み取りのみで軸別の優劣ラベルを返す。判定不能時は None。
    """
    u = _lineup_metrics(user_team)
    o = _lineup_metrics(opponent_team)
    if u is None or o is None:
        return None
    try:
        out: Dict[str, Any] = {}
        for key in ("outside", "handler", "inside", "defense", "bench"):
            du = float(u[key]) - float(o[key])
            out[key] = _edge(du)
            out[f"{key}_diff"] = du
        return out
    except Exception:
        return None


def _spotlight_lines(edges: Dict[str, Any]) -> Tuple[str, str]:
    """見どころ・注目点の短文（情報のみ、勝敗予測ではない）。"""
    axis_map = [
        ("outside", "外角"),
        ("inside", "インサイド"),
        ("handler", "ハンドラー"),
        ("defense", "守備強度"),
        ("bench", "ベンチ層"),
    ]
    diffs: List[Tuple[str, float]] = []
    for key, label in axis_map:
        d = float(edges.get(f"{key}_diff", 0.0))
        diffs.append((label, d))
    best = max(diffs, key=lambda x: x[1])
    worst = min(diffs, key=lambda x: x[1])

    if best[1] >= 3.0 and worst[1] <= -3.0:
        spot = f"見どころ: {best[0]}では押せるが、{worst[0]}は苦戦注意"
    elif best[1] >= 3.0:
        spot = f"見どころ: {best[0]}で優位を取りにいける展開になりやすい"
    elif worst[1] <= -3.0:
        spot = f"見どころ: {worst[0]}差が目立ちやすい"
    else:
        spot = "見どころ: 各軸とも拮抗しやすい展開"

    note = "注目点: ディテールの積み重ねが勝負になりそう"
    if edges.get("inside") == "相手優位":
        note = "注目点: 相手ビッグ・リバウンド面への対応が鍵"
    elif edges.get("bench") == "相手優位":
        note = "注目点: ベンチ差で終盤の持ち球が試されそう"
    elif edges.get("outside") == "相手優位":
        note = "注目点: 相手の外線火力への対応が鍵"
    elif edges.get("handler") == "相手優位":
        note = "注目点: ハンドラー対決で主導権を握れるか"
    elif edges.get("defense") == "相手優位":
        note = "注目点: 相手守備の壁をどう崩すか"
    elif edges.get("bench") == "自チーム優位":
        note = "注目点: 控えの厚みを終盤に活かせるか"

    return spot, note


def format_match_preview_cli_lines(
    user_team: Any,
    opponent_team: Any,
    *,
    user_is_home: bool = True,
) -> List[str]:
    """
    自チーム視点の短い対戦サマリー。試合シミュ前の CLI 表示用。
    """
    opp_name = str(getattr(opponent_team, "name", "") or "相手")
    venue = "ホーム" if user_is_home else "アウェイ"
    header = f"対戦: {opp_name}（{venue}）"

    edges = build_matchup_edges_summary(user_team, opponent_team)
    if edges is None:
        return [
            "【試合プレビュー】",
            header,
            "情報なし（先発・布陣の参照に失敗したか、先発が5人未満です）",
            "",
        ]

    line_axes = (
        f"外角勝負: {edges['outside']} / インサイド勝負: {edges['inside']} / "
        f"ハンドラー勝負: {edges['handler']}"
    )
    line_more = f"守備強度: {edges['defense']} / ベンチ層: {edges['bench']}"
    spot, note = _spotlight_lines(edges)
    return [
        "【試合プレビュー】",
        header,
        line_axes,
        line_more,
        spot,
        note,
        "",
    ]


__all__ = ["build_matchup_edges_summary", "format_match_preview_cli_lines"]
