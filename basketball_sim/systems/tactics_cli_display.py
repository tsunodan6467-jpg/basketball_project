"""
戦術変更 CLI 用の布陣との相性サマリー（表示のみ。戦術・試合ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.gm_dashboard_text import get_current_bench_order, get_current_starting_five
from basketball_sim.systems.gm_ui_constants import STRATEGY_OPTIONS
from basketball_sim.systems.rotation_cli_display import (
    _avg_starters,
    _build_attention_notes,
    _bench_depth_label,
)


_STRATEGY_LABELS: Dict[str, str] = dict(STRATEGY_OPTIONS)


def _fit_word(score: float, hi: float, lo: float) -> str:
    if score >= hi:
        return "良い"
    if score >= lo:
        return "普通"
    return "悪い"


def _axis_strength_line(starters: List[Any]) -> str:
    h = (_avg_starters(starters, "passing") + _avg_starters(starters, "handling")) / 2.0
    o = (_avg_starters(starters, "three") + _avg_starters(starters, "shoot")) / 2.0
    ins = (_avg_starters(starters, "rebound") + _avg_starters(starters, "power")) / 2.0
    d = _avg_starters(starters, "defense")
    axes: List[Tuple[str, float]] = [("外角", o), ("ハンドリング", h), ("インサイド", ins), ("守備", d)]
    ranked = sorted(axes, key=lambda x: (-x[1], x[0]))
    s1 = ranked[0][0]
    s2 = ranked[1][0] if len(ranked) > 1 else ranked[0][0]
    if s1 == s2:
        return s1
    return f"{s1}・{s2}"


def build_tactic_cli_fit_summary(team: Any) -> Optional[Dict[str, str]]:
    """
    先発5＋ベンチから相性ラベル用の辞書を返す。先発不足などで判定できないとき None。
    """
    try:
        starters = list(get_current_starting_five(team) or [])
        bench = list(get_current_bench_order(team) or [])
    except Exception:
        return None

    if len(starters) < 5:
        return None

    try:
        o = (_avg_starters(starters, "three") + _avg_starters(starters, "shoot")) / 2.0
        h = (_avg_starters(starters, "passing") + _avg_starters(starters, "handling")) / 2.0
        ins = (_avg_starters(starters, "rebound") + _avg_starters(starters, "power")) / 2.0
        d = _avg_starters(starters, "defense")
        trans = (
            _avg_starters(starters, "speed")
            + _avg_starters(starters, "stamina")
            + _avg_starters(starters, "passing")
        ) / 3.0
        half = (h + d + ins) / 3.0

        bench_lbl = _bench_depth_label(bench)
        caution = _build_attention_notes(starters, bench, bench_lbl)
        play_to = _axis_strength_line(starters)

        cur_key = str(getattr(team, "strategy", "balanced") or "balanced")
        cur_label = _STRATEGY_LABELS.get(cur_key, cur_key)

        if cur_key == "run_and_gun":
            cur_fit = _fit_word(trans, 56.0, 46.0)
        elif cur_key == "three_point":
            cur_fit = _fit_word(o, 58.0, 48.0)
        elif cur_key == "defense":
            cur_fit = _fit_word(d, 60.0, 50.0)
        elif cur_key == "inside":
            cur_fit = _fit_word(ins, 58.0, 48.0)
        else:
            bal = (o + trans + d + ins) / 4.0
            cur_fit = _fit_word(bal, 54.0, 46.0)

        return {
            "outside": _fit_word(o, 58.0, 48.0),
            "transition": _fit_word(trans, 56.0, 46.0),
            "defense": _fit_word(d, 60.0, 50.0),
            "halfcourt": _fit_word(half, 55.0, 46.0),
            "play_to": play_to,
            "caution": caution,
            "current_label": cur_label,
            "current_fit": cur_fit,
        }
    except Exception:
        return None


def format_tactic_cli_summary_lines(team: Any) -> List[str]:
    """戦術メニュー直前に出す短い相性サマリー（各行はそのまま print 可能）。"""
    data = build_tactic_cli_fit_summary(team)
    if data is None:
        return [
            "【戦術サマリー】",
            "情報なし",
            "",
            "活かしやすい: 情報なし",
            "注意点: 情報なし",
            "現在の戦術との相性: 情報なし",
            "",
        ]

    line1 = (
        f"外角戦術: {data['outside']} / 速攻: {data['transition']} / "
        f"守備重視: {data['defense']} / ハーフコート: {data['halfcourt']}"
    )
    return [
        "【戦術サマリー】",
        line1,
        f"活かしやすい: {data['play_to']}",
        f"注意点: {data['caution']}",
        f"現在の戦術（{data['current_label']}）との相性: {data['current_fit']}",
        "",
    ]


__all__ = ["build_tactic_cli_fit_summary", "format_tactic_cli_summary_lines"]
