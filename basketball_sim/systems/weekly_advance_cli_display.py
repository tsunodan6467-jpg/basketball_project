"""
1 ラウンド（週）進行直前の CLI 短い確認ブロック（表示のみ）。
simulate_next_round 本体・日程ロジックは変更しない。
"""

from __future__ import annotations

from typing import Any, List, Optional

__all__ = [
    "build_weekly_advance_focus_hint",
    "format_weekly_advance_check_lines",
]


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _user_regular_opponent_in_round(season: Any, user_team: Any, round_number: int) -> Optional[Any]:
    """指定ラウンドのレギュラー公式戦でユーザーの対戦相手（いなければ None）。"""
    if season is None or user_team is None:
        return None
    try:
        getter = getattr(season, "get_events_for_round", None)
        if not callable(getter):
            return None
        for ev in getter(int(round_number)) or []:
            if str(getattr(ev, "event_type", "") or "") != "game":
                continue
            if str(getattr(ev, "competition_type", "") or "") != "regular_season":
                continue
            h, a = getattr(ev, "home_team", None), getattr(ev, "away_team", None)
            if h is user_team:
                return a
            if a is user_team:
                return h
    except Exception:
        return None
    return None


def _roster_attention_raw(user_team: Any) -> str:
    try:
        from basketball_sim.systems.rotation_cli_display import format_rotation_cli_summary_lines

        for ln in format_rotation_cli_summary_lines(user_team):
            if isinstance(ln, str) and ln.startswith("注意点:"):
                return ln.split(":", 1)[1].strip()
    except Exception:
        pass
    return "情報なし"


def _mgmt_attention_parts(user_team: Any, season: Any, free_agents: Any) -> List[str]:
    parts: List[str] = []
    try:
        cf = _safe_int(getattr(user_team, "cashflow_last_season", 0), 0)
        rev = _safe_int(getattr(user_team, "revenue_last_season", 0), 0)
        exp = _safe_int(getattr(user_team, "expense_last_season", 0), 0)
        if (rev != 0 or exp != 0 or cf != 0) and cf < 0:
            parts.append("財務赤字傾向")
    except Exception:
        pass
    try:
        if _safe_int(getattr(user_team, "owner_trust", 50), 50) < 48:
            parts.append("信頼度低下気味")
    except Exception:
        pass
    try:
        for p in list(getattr(user_team, "players", []) or []):
            if _safe_int(getattr(p, "contract_years_left", 99), 99) != 1:
                continue
            try:
                from basketball_sim.systems.contract_logic import is_draft_rookie_contract_active
            except Exception:
                is_draft_rookie_contract_active = None
            if is_draft_rookie_contract_active is not None and is_draft_rookie_contract_active(p):
                continue
            parts.append("再契約候補あり")
            break
    except Exception:
        pass
    try:
        fa_n = 0
        if isinstance(free_agents, list):
            fa_n = len(free_agents)
        elif season is not None:
            fa_n = len(list(getattr(season, "free_agents", []) or []))
        if fa_n >= 12:
            parts.append("FA候補確認余地あり")
    except Exception:
        pass
    return parts[:4]


def build_weekly_advance_focus_hint(
    *,
    roster_attn: str,
    mgmt_parts: List[str],
    match_tags: List[str],
) -> str:
    """最終行「進める前チェック: …」（単純ルール・表示のみ）。"""
    try:
        bad_roster = roster_attn not in ("特記なし", "情報なし", "")
        if bad_roster:
            return "先発と戦術の再確認推奨"
        if any("財務" in x for x in mgmt_parts) or any("信頼" in x for x in mgmt_parts):
            return "財務と起用の確認推奨"
        for key in ("上位直接対決", "連敗ストップがかかる", "順位接近戦", "重要度高め"):
            if key in match_tags:
                return "戦術だけ再確認推奨"
        if not mgmt_parts and not bad_roster:
            return "そのまま進行可"
        return "状況確認推奨"
    except Exception:
        return "情報確認"


def format_weekly_advance_check_lines(
    *,
    season: Any,
    user_team: Any,
    free_agents: Any = None,
) -> List[str]:
    """3〜5 行程度。失敗しても呼び出し側で try する想定だが、内部も極力安全に。"""
    out: List[str] = ["【週送り前チェック】"]
    roster_attn = "情報なし"
    mgmt_parts: List[str] = []
    match_tags: List[str] = []

    try:
        if season is None or user_team is None or bool(getattr(season, "season_finished", False)):
            out.append("今週: 情報なし（レギュラー進行外）")
            out.append("注意: 特記なし")
            out.append(f"進める前チェック: {build_weekly_advance_focus_hint(roster_attn='特記なし', mgmt_parts=[], match_tags=[])}")
            return out
    except Exception:
        pass

    try:
        nxt = _safe_int(getattr(season, "current_round", 0), 0) + 1
        opp = _user_regular_opponent_in_round(season, user_team, nxt)
        from basketball_sim.systems.schedule_importance_cli_display import (
            build_match_importance_tags,
        )

        if opp is not None:
            match_tags = list(build_match_importance_tags(season, user_team, opp))
            tag_txt = "・".join(match_tags[:3]) if match_tags else "情報なし"
            out.append(f"今週: {tag_txt}")
        else:
            league_only = list(build_match_importance_tags(season, user_team, None))
            tag_txt = "・".join(league_only[:2]) if league_only else "順位積み上げ戦"
            out.append(f"今週: 当節レギュラー出走なし / {tag_txt}")
    except Exception:
        out.append("今週: 情報なし")

    try:
        roster_attn = _roster_attention_raw(user_team)
        if roster_attn in ("特記なし", "情報なし"):
            out.append("注意: 編成面 特記なし")
        else:
            out.append(f"注意: {roster_attn}")
    except Exception:
        out.append("注意: 情報なし")

    try:
        mgmt_parts = _mgmt_attention_parts(user_team, season, free_agents)
        if mgmt_parts:
            out.append(f"注意: {'・'.join(mgmt_parts)}")
        else:
            out.append("注意: 経営面 特記なし")
    except Exception:
        out.append("注意: 経営面 情報なし")

    try:
        hint = build_weekly_advance_focus_hint(
            roster_attn=roster_attn,
            mgmt_parts=mgmt_parts,
            match_tags=match_tags,
        )
        out.append(f"進める前チェック: {hint}")
    except Exception:
        out.append("進める前チェック: 情報確認")

    return out[:6]
