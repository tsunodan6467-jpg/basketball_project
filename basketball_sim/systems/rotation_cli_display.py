"""
先発・ローテ CLI 用の布陣サマリー（表示のみ。スタメン／試合ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Any, List, Tuple

from basketball_sim.systems.gm_dashboard_text import get_current_bench_order, get_current_starting_five


def _safe_int_attr(player: Any, key: str) -> int:
    try:
        return int(getattr(player, key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _avg_starters(starters: List[Any], key: str) -> float:
    if not starters:
        return 0.0
    return float(sum(_safe_int_attr(p, key) for p in starters)) / float(len(starters))


def _band_outside(v: float) -> str:
    if v >= 60:
        return "強い"
    if v >= 48:
        return "普通"
    return "弱い"


def _band_inside(v: float) -> str:
    if v >= 58:
        return "強い"
    if v >= 48:
        return "普通"
    return "弱い"


def _band_defense(v: float) -> str:
    if v >= 60:
        return "強い"
    if v >= 50:
        return "普通"
    return "弱い"


def _handler_label(v: float) -> str:
    if v >= 58:
        return "足りる"
    if v >= 48:
        return "やや不足"
    return "不足"


def _bench_depth_label(bench: List[Any]) -> str:
    if not bench:
        return "情報なし"
    n = len(bench)
    av = float(sum(_safe_int_attr(p, "ovr") for p in bench)) / float(n)
    if n >= 5 and av >= 54:
        return "厚い"
    if n <= 2 or av < 48:
        return "薄い"
    return "普通"


def _collect_axis_scores(starters: List[Any]) -> List[Tuple[str, float]]:
    h = (_avg_starters(starters, "passing") + _avg_starters(starters, "handling")) / 2.0
    o = (_avg_starters(starters, "three") + _avg_starters(starters, "shoot")) / 2.0
    ins = (_avg_starters(starters, "rebound") + _avg_starters(starters, "power")) / 2.0
    d = _avg_starters(starters, "defense")
    return [("外角", o), ("ハンドリング", h), ("インサイド", ins), ("守備", d)]


def _build_strength_weakness_notes(axes: List[Tuple[str, float]]) -> Tuple[str, str]:
    if not axes:
        return "情報なし", "情報なし"
    ranked = sorted(axes, key=lambda x: (-x[1], x[0]))
    s1 = ranked[0][0]
    s2 = ranked[1][0] if len(ranked) > 1 else ranked[0][0]
    strong = f"{s1}・{s2}" if s1 != s2 else s1
    lo = sorted(axes, key=lambda x: (x[1], x[0]))
    weak = lo[0][0]
    if weak in (s1, s2) and s1 != s2 and len(lo) > 1:
        weak = lo[1][0]
    return strong, weak


def _build_attention_notes(starters: List[Any], bench: List[Any], bench_label: str) -> str:
    notes: List[str] = []
    pos = [str(getattr(p, "position", "") or "").upper() for p in starters]
    if "PG" not in pos:
        notes.append("ガード不足")
    if sum(1 for x in pos if x in ("PF", "C")) < 1:
        notes.append("ビッグ不足")
    if bench_label == "薄い":
        notes.append("ベンチ薄め")
    if not notes:
        return "特記なし"
    return "・".join(notes[:3])


def format_rotation_cli_summary_lines(team: Any) -> List[str]:
    """先発5＋ベンチ序列から読み取りのみで短い布陣サマリーを返す。"""
    try:
        starters = list(get_current_starting_five(team) or [])
        bench = list(get_current_bench_order(team) or [])
    except Exception:
        return ["【布陣サマリー】", "情報なし", "", "強み: 情報なし", "弱み: 情報なし", "注意点: 情報なし", ""]

    if len(starters) < 5:
        return ["【布陣サマリー】", "情報なし（先発が5人未満）", "", "強み: 情報なし", "弱み: 情報なし", "注意点: 情報なし", ""]

    try:
        h = (_avg_starters(starters, "passing") + _avg_starters(starters, "handling")) / 2.0
        o = (_avg_starters(starters, "three") + _avg_starters(starters, "shoot")) / 2.0
        ins = (_avg_starters(starters, "rebound") + _avg_starters(starters, "power")) / 2.0
        d = _avg_starters(starters, "defense")
        atk = (_avg_starters(starters, "shoot") + _avg_starters(starters, "three") + _avg_starters(starters, "drive")) / 3.0

        line1 = (
            f"ハンドラー: {_handler_label(h)} / 外角: {_band_outside(o)} / "
            f"インサイド: {_band_inside(ins)} / 守備: {_band_defense(d)} / "
            f"攻撃密度: {_band_outside(atk)}"
        )
        bench_lbl = _bench_depth_label(bench)
        line1b = f"ベンチ厚み: {bench_lbl}"

        axes = _collect_axis_scores(starters)
        sm_str, wk_str = _build_strength_weakness_notes(axes)
        attn = _build_attention_notes(starters, bench, bench_lbl)

        return [
            "【布陣サマリー】",
            line1,
            line1b,
            f"強み: {sm_str}",
            f"弱み: {wk_str}",
            f"注意点: {attn}",
            "",
        ]
    except Exception:
        return ["【布陣サマリー】", "情報なし", "", "強み: 情報なし", "弱み: 情報なし", "注意点: 情報なし", ""]
