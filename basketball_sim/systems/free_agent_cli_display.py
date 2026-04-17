"""
FA プール CLI 閲覧用の短い補助行（表示のみ。FA 市場・契約処理は変更しない）。
"""

from __future__ import annotations

from typing import Any, List, Optional

from basketball_sim.systems.draft import (
    build_draft_candidate_role_shape_label,
    build_draft_candidate_strength_weakness_line,
)
from basketball_sim.systems.helpers import print_separator


def build_free_agent_slot_label(player: Any) -> str:
    """即戦力 / ベテラン / 将来枠 / バランス型（実 OVR・年齢・POT からの簡易表示のみ）。"""
    try:
        age = int(getattr(player, "age", 25) or 25)
        ovr = int(getattr(player, "ovr", 0) or 0)
        raw = str(getattr(player, "potential", "C") or "C").upper().strip()
        ch = raw[0] if raw else "C"
        if ch not in ("S", "A", "B", "C", "D"):
            ch = "C"
    except Exception:
        return "情報なし"

    if age >= 32 and ovr >= 54:
        return "ベテラン"
    if ovr >= 66 or (ovr >= 62 and age >= 26):
        return "即戦力"
    if age <= 23 and ch in ("S", "A") and ovr <= 62:
        return "将来枠"
    if age <= 25 and ch in ("S", "A", "B") and ovr < 64:
        return "将来枠"
    return "バランス型"


def build_free_agent_value_label(player: Any, user_team: Any) -> str:
    """
    本格FA 同型の提示年俸とプール年俸の比から簡易ラベル（表示のみ）。
    算出不能時は空文字（行から省略）。
    """
    if user_team is None:
        return ""
    try:
        from basketball_sim.systems.free_agent_market import (
            ensure_fa_market_fields,
            offseason_manual_fa_offer_and_years,
        )
        from basketball_sim.systems.salary_cap_budget import league_level_for_team

        div = int(league_level_for_team(user_team))
        ensure_fa_market_fields(player, league_market_division=div)
        off, _yrs = offseason_manual_fa_offer_and_years(user_team, player)
        ref = int(getattr(player, "fa_pool_market_salary", 0) or 0)
        if ref <= 0 or off <= 0:
            return ""
        ratio = float(off) / float(ref)
        if ratio <= 0.90:
            return "割安感あり"
        if ratio >= 1.12:
            return "高額注意"
        return "標準圏"
    except Exception:
        return ""


def format_free_agent_cli_hint(player: Any, user_team: Optional[Any] = None) -> str:
    """FA 候補1人分の補助1行（獲得処理は行わない）。"""
    try:
        slot = build_free_agent_slot_label(player)
        sw = build_draft_candidate_strength_weakness_line(player)
        shape = build_draft_candidate_role_shape_label(player)
        val = build_free_agent_value_label(player, user_team) if user_team is not None else ""
        base = f"{slot} / {sw} / {shape}"
        return f"{base} / {val}" if val else base
    except Exception:
        return "情報なし"


def print_free_agent_pool_cli(
    user_team: Any,
    free_agents: Optional[List[Any]],
    *,
    season: Any = None,
    limit: int = 60,
) -> None:
    """トレードメニュー等から呼ぶ FA プール閲覧（契約・プール内容は変更しない）。"""
    try:
        from basketball_sim.systems.free_agent_market import ensure_fa_market_fields, normalize_free_agents
        from basketball_sim.systems.season_transaction_rules import (
            INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
            inseason_roster_moves_unlocked,
        )
        from basketball_sim.systems.salary_cap_budget import league_level_for_team
    except Exception:
        print_separator("FA候補プール")
        print("情報なし（表示モジュールの読み込みに失敗しました）")
        return

    print_separator("FA候補プール（閲覧）")
    if season is not None and not inseason_roster_moves_unlocked(season):
        print(INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA)
        print("（獲得は不可ですが、プールの閲覧のみ可能です）")

    raw = list(free_agents or [])
    if not raw:
        print("FA プールに選手がいません。")
        return

    try:
        div = int(league_level_for_team(user_team))
    except Exception:
        div = 3

    try:
        candidates = normalize_free_agents(raw, league_market_division=div)
    except Exception:
        candidates = raw

    candidates.sort(
        key=lambda p: (-int(getattr(p, "ovr", 0) or 0), str(getattr(p, "name", ""))),
    )
    cap = max(1, min(int(limit or 60), 120))
    shown = candidates[:cap]

    for i, p in enumerate(shown, 1):
        try:
            ensure_fa_market_fields(p, league_market_division=div)
        except Exception:
            pass
        nm = str(getattr(p, "name", "?"))
        pos = str(getattr(p, "position", "?"))
        ovr = int(getattr(p, "ovr", 0) or 0)
        age = int(getattr(p, "age", 0) or 0)
        pot = str(getattr(p, "potential", "?") or "?")
        sal = int(getattr(p, "fa_pool_market_salary", 0) or getattr(p, "salary", 0) or 0)
        sal_txt = f"{sal:,}円" if sal > 0 else "—"
        hint = format_free_agent_cli_hint(p, user_team=user_team)
        print(f"{i:>2}. {nm:<18} {pos:<3} OVR:{ovr:<2} POT:{pot:<2} {age:>2}歳  年俸目安:{sal_txt}")
        print(f"    {hint}")

    if len(candidates) > cap:
        print(f"…他 {len(candidates) - cap} 名（全 {len(candidates)} 名）")


__all__ = [
    "build_free_agent_slot_label",
    "build_free_agent_value_label",
    "format_free_agent_cli_hint",
    "print_free_agent_pool_cli",
]
