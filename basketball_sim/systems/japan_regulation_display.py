"""
日本独自ルールの GUI 向け表示文（判定ロジックは japan_regulation / competition_rules に委譲）。
"""

from __future__ import annotations

from typing import Any, List, Optional

from basketball_sim.systems.competition_rules import get_competition_rule, normalize_competition_type
from basketball_sim.systems.competition_display import competition_display_name
from basketball_sim.systems.japan_regulation import count_regulation_slots, lineup_passes_on_court
from basketball_sim.systems.competition_rules import league_contract_active_rule


def gui_next_competition_type(season: Any, user_team: Any) -> str:
    """直近の自チーム試合に相当する competition_type（無ければ regular_season）。"""
    try:
        from basketball_sim.systems.schedule_display import upcoming_rows_for_user_team

        rows: List[dict] = upcoming_rows_for_user_team(season, user_team, league_only=False)
        if rows:
            ct = str(rows[0].get("competition_type") or "").strip()
            if ct:
                return normalize_competition_type(ct)
    except Exception:
        pass
    return "regular_season"


def format_competition_rules_brief(competition_type: Optional[str]) -> str:
    """大会別の登録／オンザコートを短く（人間向け）。"""
    ct = normalize_competition_type(competition_type)
    act = get_competition_rule(ct, "active")
    oc = get_competition_rule(ct, "on_court")
    name = competition_display_name(ct)
    if name == "未分類" and ct:
        name = ct
    fm_a = int(act.get("foreign_max", 3))
    sm_a = int(act.get("special_max", 1))
    fm_o = int(oc.get("foreign_max", 2))
    sm_o = int(oc.get("special_max", 1))
    af_a = bool(act.get("asia_as_foreign", False))
    af_o = bool(oc.get("asia_as_foreign", False))

    if af_a:
        line_a = f"試合登録: 外国籍+アジア 最大{fm_a}名／帰化 最大{sm_a}名（アジアは外国籍扱い）"
    else:
        line_a = f"試合登録: 外国籍 最大{fm_a}名／アジア・帰化 合計 最大{sm_a}名"

    if af_o:
        line_o = f"オンザコート: 外国籍+アジア 最大{fm_o}名／帰化 最大{sm_o}名（アジアは外国籍扱い）"
    else:
        line_o = f"オンザコート: 外国籍 最大{fm_o}名／アジア・帰化 合計 最大{sm_o}名"

    return f"【{name}】\n{line_a}\n{line_o}"


def format_contract_roster_summary(team: Any) -> str:
    """本契約ロスターの枠（日本リーグ基準・共通カウント）。"""
    players = list(getattr(team, "players", None) or [])
    rule = league_contract_active_rule()
    f, s = count_regulation_slots(players, rule)
    fm = int(rule.get("foreign_max", 3))
    sm = int(rule.get("special_max", 1))
    n_asia = sum(1 for p in players if getattr(p, "nationality", "") == "Asia")
    n_nat = sum(1 for p in players if getattr(p, "nationality", "") == "Naturalized")
    return (
        f"本契約枠: 外国籍カウント {f}/{fm} ｜ アジア・帰化カウント {s}/{sm} "
        f"（内訳: アジア{n_asia}・帰化{n_nat}）"
    )


def format_starting_lineup_caution(team: Any, competition_type: Optional[str]) -> str:
    """先発5人が当該大会のオンザコート枠を満たさない場合の注意文（空なら問題なし）。"""
    ct = normalize_competition_type(competition_type)
    oc_rule = get_competition_rule(ct, "on_court")
    try:
        from basketball_sim.systems.gm_dashboard_text import get_current_starting_five

        starters = list(get_current_starting_five(team) or [])
    except Exception:
        starters = []
    if len(starters) != 5:
        return ""
    if lineup_passes_on_court(starters, oc_rule):
        return ""
    lines = []
    if bool(oc_rule.get("asia_as_foreign", False)):
        lines.append("※この大会ではアジア選手は外国籍枠に数えられます。")
    lines.append(
        "※現在の先発5人は、この大会のオンザコート枠を超える可能性があります（試合側で調整されます）。"
    )
    return "\n".join(lines)


def format_roster_window_jp_header(season: Any, team: Any) -> str:
    """人事ウィンドウ上部用の短いブロック。"""
    ct = gui_next_competition_type(season, team)
    cap = format_contract_roster_summary(team)
    rules = format_competition_rules_brief(ct)
    return f"{cap}\n\n次の主な試合想定:\n{rules}"
