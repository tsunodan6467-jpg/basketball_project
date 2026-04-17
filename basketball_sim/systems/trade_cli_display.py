"""
トレード CLI 用の短い得失サマリー（表示のみ。トレード評価・成立処理は変更しない）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from basketball_sim.systems.draft import (
    build_draft_candidate_role_shape_label,
)
from basketball_sim.systems.free_agent_cli_display import build_free_agent_slot_label


def _safe_int(player: Any, key: str) -> int:
    try:
        return int(getattr(player, key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _axis_avgs(players: Sequence[Any]) -> Dict[str, float]:
    if not players:
        return {}
    n = float(len(players))
    out: Dict[str, float] = {}
    out["outside"] = sum((_safe_int(p, "three") + _safe_int(p, "shoot")) / 2.0 for p in players) / n
    out["handler"] = sum((_safe_int(p, "passing") + _safe_int(p, "handling")) / 2.0 for p in players) / n
    out["inside"] = sum((_safe_int(p, "rebound") + _safe_int(p, "power")) / 2.0 for p in players) / n
    out["defense"] = sum(float(_safe_int(p, "defense")) for p in players) / n
    out["ovr"] = sum(float(_safe_int(p, "ovr")) for p in players) / n
    out["age"] = sum(float(_safe_int(p, "age")) for p in players) / n
    out["pot"] = sum(
        float({"S": 92, "A": 78, "B": 64, "C": 52, "D": 40}.get(str(getattr(p, "potential", "C") or "C").upper()[:1], 52))
        for p in players
    ) / n
    return out


def _top_two_axis_labels(avgs: Dict[str, float]) -> str:
    if not avgs:
        return "情報なし"
    pairs: List[Tuple[str, float]] = [
        ("外角", float(avgs.get("outside", 0.0))),
        ("ハンドラー", float(avgs.get("handler", 0.0))),
        ("インサイド", float(avgs.get("inside", 0.0))),
        ("守備", float(avgs.get("defense", 0.0))),
    ]
    ranked = sorted(pairs, key=lambda x: (-x[1], x[0]))
    a, b = ranked[0][0], ranked[1][0]
    return f"{a}・{b}" if a != b else a


def _majority_role_shape(players: Sequence[Any]) -> str:
    if not players:
        return "情報なし"
    votes: List[str] = []
    for p in players:
        try:
            votes.append(build_draft_candidate_role_shape_label(p))
        except Exception:
            votes.append("情報なし")
    best = max(set(votes), key=lambda v: votes.count(v))
    return best if best != "情報なし" else "役割混合型"


def _slot_mix_label(players: Sequence[Any]) -> str:
    if not players:
        return "情報なし"
    slots: List[str] = []
    for p in players:
        try:
            slots.append(build_free_agent_slot_label(p))
        except Exception:
            slots.append("バランス型")
    if not slots:
        return "情報なし"
    return max(set(slots), key=lambda s: slots.count(s))


def build_trade_gain_loss_lines(
    user_receive: Sequence[Any],
    user_give: Sequence[Any],
) -> List[str]:
    """
    ユーザー視点で「受け取る／出す」選手群から短い得失行を返す（改行なしの各行）。
    """
    recv = list(user_receive or [])
    give = list(user_give or [])
    if not recv or not give:
        return ["【トレード比較】", "情報なし（選手が選ばれていません）", ""]

    try:
        ar = _axis_avgs(recv)
        ag = _axis_avgs(give)
    except Exception:
        return ["【トレード比較】", "情報なし", ""]

    recv_line = f"受取側: {_majority_role_shape(recv)} / 強み傾向:{_top_two_axis_labels(ar)} / {_slot_mix_label(recv)}"
    give_line = f"放出側: {_majority_role_shape(give)} / 強み傾向:{_top_two_axis_labels(ag)} / {_slot_mix_label(give)}"

    do = float(ar.get("outside", 0.0)) - float(ag.get("outside", 0.0))
    di = float(ar.get("inside", 0.0)) - float(ag.get("inside", 0.0))
    dd = float(ar.get("defense", 0.0)) - float(ag.get("defense", 0.0))
    dh = float(ar.get("handler", 0.0)) - float(ag.get("handler", 0.0))
    dov = float(ar.get("ovr", 0.0)) - float(ag.get("ovr", 0.0))
    dage = float(ar.get("age", 0.0)) - float(ag.get("age", 0.0))
    dpot = float(ar.get("pot", 0.0)) - float(ag.get("pot", 0.0))

    gains: List[str] = []
    losses: List[str] = []
    if di >= 4.0:
        gains.append("インサイド補強")
    elif di <= -4.0:
        losses.append("インサイドが弱くなる")
    if dd >= 3.5:
        gains.append("守備強化")
    elif dd <= -3.5:
        losses.append("守備が弱くなる")
    if do >= 3.5:
        gains.append("外角寄り")
    elif do <= -3.5:
        losses.append("外角が弱くなる")
    if dh >= 3.5:
        gains.append("ハンドラー補強")
    elif dh <= -3.5:
        losses.append("ハンドラー不足が目立つ可能性")

    gain_txt = "・".join(gains) if gains else "目立ったプラス軸は小さめ"
    loss_txt = "・".join(losses) if losses else "目立ったマイナス軸は小さめ"

    direction = "バランス寄りの組み替え"
    if dov >= 3.0 and dage >= 1.0:
        direction = "今勝ちに寄る交換（即戦力寄り）"
    elif dov <= -2.0 and dpot >= 6.0:
        direction = "将来寄りの組み替え"
    elif dov >= 2.0:
        direction = "能力面はやや上振れ"
    elif dov <= -2.0:
        direction = "能力面はやや下振れ"

    notes: List[str] = []
    if len(recv) < len(give):
        notes.append("ロスター人数が減る")
    if dage >= 2.5:
        notes.append("年齢層が上がる")
    elif dage <= -2.5:
        notes.append("若返り寄り")
    if dpot <= -6.0:
        notes.append("将来性が下がりやすい")

    pos_r = [str(getattr(p, "position", "") or "").upper() for p in recv]
    pos_g = [str(getattr(p, "position", "") or "").upper() for p in give]
    gr = sum(1 for x in pos_r if x in ("PG", "SG"))
    br = sum(1 for x in pos_r if x in ("PF", "C"))
    gg = sum(1 for x in pos_g if x in ("PG", "SG"))
    bg = sum(1 for x in pos_g if x in ("PF", "C"))
    if gr + br > 0 and gg + bg > 0:
        if gg - gr >= 1 and bg <= br:
            notes.append("ガード層が薄くなる可能性")
        if bg - br >= 1 and gg <= gr:
            notes.append("ビッグ層が薄くなる可能性")

    out_lines = [
        "【トレード比較】",
        recv_line,
        give_line,
        f"補強め（平均差）: {gain_txt}",
        f"注意め（平均差）: {loss_txt}",
        f"方向性: {direction}",
    ]
    if notes:
        out_lines.append(f"注意: {'・'.join(notes[:4])}")
    out_lines.append("")
    return out_lines


def format_trade_cli_summary_lines(
    user_receive: Sequence[Any],
    user_give: Sequence[Any],
) -> List[str]:
    """CLI 用。`build_trade_gain_loss_lines` と同義。"""
    return build_trade_gain_loss_lines(user_receive, user_give)


__all__ = ["build_trade_gain_loss_lines", "format_trade_cli_summary_lines"]
