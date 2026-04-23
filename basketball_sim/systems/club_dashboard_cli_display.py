"""
GM メニュー用クラブ総合ダッシュボード（CLI 表示のみ）。
順位・財務・試合ロジックは変更しない。
"""

from __future__ import annotations

from typing import Any, List, Optional

from basketball_sim.systems.money_display import format_money_yen_ja_readable

_OWNER_EXPECTATION_LABELS = {
    "playoff_race": "PO争い",
    "rebuild": "再建",
    "title_challenge": "優勝挑戦",
    "title_or_bust": "優勝一択",
    "stay_competitive": "競争維持",
}


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _fmt_yen(n: int) -> str:
    try:
        return format_money_yen_ja_readable(int(n))
    except (TypeError, ValueError):
        return "情報なし"


def _owner_trust_band(trust: int) -> str:
    if trust >= 72:
        return "高め"
    if trust >= 48:
        return "普通"
    if trust >= 32:
        return "やや低め"
    return "要注意"


def _find_next_user_regular_opponent(season: Any, user_team: Any) -> Optional[Any]:
    if season is None or user_team is None:
        return None
    try:
        if bool(getattr(season, "season_finished", False)):
            return None
        cur = _safe_int(getattr(season, "current_round", 0), 0)
        total = _safe_int(getattr(season, "total_rounds", 0), 0)
        getter = getattr(season, "get_events_for_round", None)
        if not callable(getter) or total <= 0:
            return None
        for r in range(cur + 1, total + 1):
            for ev in getter(r) or []:
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


def _standings_summary_line(season: Any, user_team: Any) -> str:
    if season is None or user_team is None:
        return "順位: 情報なし（シーズン外）"
    try:
        from basketball_sim.systems.information_display import build_standings_rows
        from basketball_sim.systems.schedule_importance_cli_display import (
            build_match_importance_tags,
        )

        lv = max(1, min(3, _safe_int(getattr(user_team, "league_level", 1), 1)))
        rows = build_standings_rows(season, lv, user_team=user_team)
        urow = next((x for x in rows if x.get("is_user_row")), None)
        if not urow:
            return "順位: 情報なし"
        rk = int(urow.get("rank", 0) or 0)
        w = int(urow.get("wins", 0) or 0)
        ell = int(urow.get("losses", 0) or 0)
        base = f"{rk}位（{w}勝{ell}敗）"
        tags = build_match_importance_tags(season, user_team, None, league_level=lv)
        tag_txt = "・".join(tags[:3]) if tags else "情報なし"
        return f"順位: {base} / {tag_txt}"
    except Exception:
        return "順位: 情報なし"


def _finance_line(user_team: Any) -> str:
    try:
        money = _safe_int(getattr(user_team, "money", 0), 0)
        rev = _safe_int(getattr(user_team, "revenue_last_season", 0), 0)
        exp = _safe_int(getattr(user_team, "expense_last_season", 0), 0)
        cf = _safe_int(getattr(user_team, "cashflow_last_season", 0), 0)
        if rev == 0 and exp == 0 and cf == 0:
            cf_note = "前季収支 未更新"
        elif cf > 0:
            cf_note = "前季 黒字傾向"
        elif cf < 0:
            cf_note = "前季 赤字傾向"
        else:
            cf_note = "前季収支 不明"
        warn = ""
        if money < 10_000_000:
            warn = " / 財務注意"
        return f"財務: 所持金 {_fmt_yen(money)} / {cf_note}{warn}"
    except Exception:
        return "財務: 情報なし"


def _owner_line(user_team: Any) -> str:
    try:
        trust = _safe_int(getattr(user_team, "owner_trust", 0), 0)
        raw = str(getattr(user_team, "owner_expectation", "") or "").strip() or "未設定"
        exp_lbl = _OWNER_EXPECTATION_LABELS.get(raw, raw)
        band = _owner_trust_band(trust)
        warn = " / 信頼注意" if trust < 42 else ""
        return f"オーナー: 信頼度 {trust}（{band}） / 期待: {exp_lbl}{warn}"
    except Exception:
        return "オーナー: 情報なし"


def _roster_issue_line(user_team: Any) -> str:
    try:
        from basketball_sim.systems.rotation_cli_display import format_rotation_cli_summary_lines

        for ln in format_rotation_cli_summary_lines(user_team):
            if isinstance(ln, str) and ln.startswith("注意点:"):
                body = ln.split(":", 1)[1].strip()
                return f"編成課題: {body}"
    except Exception:
        pass
    return "編成課題: 情報なし"


def _next_match_line(season: Any, user_team: Any) -> str:
    opp = _find_next_user_regular_opponent(season, user_team)
    if opp is None:
        return "次戦: 情報なし"
    try:
        from basketball_sim.systems.schedule_importance_cli_display import (
            build_match_importance_tags,
        )

        tags = build_match_importance_tags(season, user_team, opp)
        oname = str(getattr(opp, "name", "?") or "?")
        tag_txt = "・".join(tags[:3]) if tags else "情報なし"
        return f"次戦: {oname} / {tag_txt}"
    except Exception:
        return "次戦: 情報なし"


def _has_expiring_contracts(user_team: Any) -> bool:
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
            return True
    except Exception:
        pass
    return False


def build_club_dashboard_focus_hint(
    user_team: Any,
    season: Any,
    *,
    money: int,
    trust: int,
    roster_attn: str,
    match_tags: List[str],
    fa_count: int = 0,
) -> str:
    """最下行用の短い優先アクション（表示のみ・単純ルール）。"""
    try:
        if money < 10_000_000:
            return "財務確認"
        if trust < 42:
            return "オーナー対応（信頼・ミッション）"
        if season is None or bool(getattr(season, "season_finished", False)):
            if _has_expiring_contracts(user_team):
                return "再契約候補の整理"
            return "次シーズン準備・情報確認"
        if roster_attn not in ("特記なし", "情報なし", ""):
            return "先発と戦術の見直し"
        for key in ("連敗ストップがかかる", "PO圏争い", "上位直接対決", "順位接近戦"):
            if key in match_tags:
                return "次戦への起用・戦術調整"
        if fa_count >= 12:
            return "FA確認"
        return "コンディション維持・情報確認"
    except Exception:
        return "情報確認"


def format_club_dashboard_cli_lines(
    *,
    user_team: Any,
    season: Any = None,
    all_teams: Any = None,
    free_agents: Any = None,
) -> List[str]:
    """
    5〜7行程度の総合ブロック。各ブロックは個別に try で守る呼び出し元想定。
    all_teams / free_agents は将来拡張用（未使用でも可）。
    """
    _ = all_teams
    if user_team is None:
        return ["【クラブ総合ダッシュボード】", "情報なし（チーム未接続）"]

    out: List[str] = ["【クラブ総合ダッシュボード】"]
    try:
        out.append(_standings_summary_line(season, user_team))
    except Exception:
        out.append("順位: 情報なし")
    try:
        out.append(_finance_line(user_team))
    except Exception:
        out.append("財務: 情報なし")
    try:
        out.append(_owner_line(user_team))
    except Exception:
        out.append("オーナー: 情報なし")
    try:
        out.append(_roster_issue_line(user_team))
    except Exception:
        out.append("編成課題: 情報なし")
    try:
        out.append(_next_match_line(season, user_team))
    except Exception:
        out.append("次戦: 情報なし")

    money = _safe_int(getattr(user_team, "money", 0), 0)
    trust = _safe_int(getattr(user_team, "owner_trust", 0), 0)
    roster_attn = ""
    try:
        from basketball_sim.systems.rotation_cli_display import format_rotation_cli_summary_lines

        for ln in format_rotation_cli_summary_lines(user_team):
            if isinstance(ln, str) and ln.startswith("注意点:"):
                roster_attn = ln.split(":", 1)[1].strip()
                break
    except Exception:
        roster_attn = "情報なし"

    match_tags: List[str] = []
    try:
        opp = _find_next_user_regular_opponent(season, user_team)
        if opp is not None and season is not None:
            from basketball_sim.systems.schedule_importance_cli_display import (
                build_match_importance_tags,
            )

            match_tags = list(build_match_importance_tags(season, user_team, opp))
    except Exception:
        match_tags = []

    fa_count = 0
    if isinstance(free_agents, list):
        fa_count = len(free_agents)
    elif season is not None:
        try:
            fa_count = len(list(getattr(season, "free_agents", []) or []))
        except Exception:
            fa_count = 0

    try:
        focus = build_club_dashboard_focus_hint(
            user_team,
            season,
            money=money,
            trust=trust,
            roster_attn=roster_attn,
            match_tags=match_tags,
            fa_count=fa_count,
        )
        out.append(f"今やるべきこと: {focus}")
    except Exception:
        out.append("今やるべきこと: 情報確認")

    return out


__all__ = [
    "build_club_dashboard_focus_hint",
    "format_club_dashboard_cli_lines",
]
