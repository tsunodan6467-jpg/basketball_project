"""
GM ダッシュボード用の読み取り専用テキスト（CLI main.py と GUI 共通）。

input() を使わない確認系の単一ソースにする。

表示ルール（人事ロスターと共通）の説明: docs/GM_ROSTER_DISPLAY_RULES.md
"""

from __future__ import annotations

from typing import Any, List, Tuple

from basketball_sim.systems.contract_logic import get_team_payroll
from basketball_sim.systems.money_display import format_money_yen_ja_readable
from basketball_sim.systems.japan_regulation_display import get_player_nationality_bucket_label
from basketball_sim.systems.salary_cap_budget import (
    cap_status,
    get_soft_cap,
    league_level_for_team,
)


def sort_roster_for_gm_view(players: List[Any]) -> List[Any]:
    position_order = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
    return sorted(
        players,
        key=lambda p: (
            position_order.get(getattr(p, "position", "SF"), 99),
            -getattr(p, "ovr", 0),
            getattr(p, "name", ""),
        ),
    )


def get_current_starting_five(user_team: Any) -> List[Any]:
    if hasattr(user_team, "get_starting_five"):
        try:
            return list(user_team.get_starting_five() or [])
        except Exception:
            pass
    roster = sort_roster_for_gm_view(getattr(user_team, "players", []) or [])
    return roster[:5]


def get_starting_player_ids(user_team: Any) -> set:
    return {
        getattr(p, "player_id", None)
        for p in get_current_starting_five(user_team)
    }


def get_current_sixth_man(user_team: Any):
    if hasattr(user_team, "get_sixth_man"):
        try:
            return user_team.get_sixth_man()
        except Exception:
            pass
    return None


def _player_active_for_bench_order(p: Any) -> bool:
    """負傷・引退を除く（main.get_current_bench_order と同義の安全版）。"""
    m = getattr(p, "is_injured", None)
    if callable(m):
        try:
            if m():
                return False
        except Exception:
            pass
    else:
        if getattr(p, "injured", False):
            return False
    if bool(getattr(p, "is_retired", False)):
        return False
    return True


def get_available_starting_candidates(
    user_team: Any, current_starters: List[Any], slot_index: int
) -> List[Any]:
    """
    CLI change_starting_lineup と同一の候補ロジック。
    slot_index: 0=PG … 4=C（現在のスタメン5人の並びに対応）。
    """
    if slot_index < 0 or slot_index >= len(current_starters):
        return []
    slot_player = current_starters[slot_index]
    slot_position = getattr(slot_player, "position", "SF")

    candidates: List[Any] = []
    for p in sort_roster_for_gm_view(list(getattr(user_team, "players", []) or [])):
        if not _player_active_for_bench_order(p):
            continue

        same_position = getattr(p, "position", "SF") == slot_position
        current_ids_except_slot = {
            getattr(sp, "player_id", None)
            for i, sp in enumerate(current_starters)
            if i != slot_index
        }

        if getattr(p, "player_id", None) in current_ids_except_slot:
            continue

        if same_position or p == slot_player:
            candidates.append(p)

    if candidates:
        return candidates

    fallback: List[Any] = []
    for p in sort_roster_for_gm_view(list(getattr(user_team, "players", []) or [])):
        if not _player_active_for_bench_order(p):
            continue

        current_ids_except_slot = {
            getattr(sp, "player_id", None)
            for i, sp in enumerate(current_starters)
            if i != slot_index
        }

        if getattr(p, "player_id", None) in current_ids_except_slot:
            continue

        fallback.append(p)

    return fallback


def apply_starting_slot_change(team: Any, slot_index: int, new_player: Any) -> Tuple[bool, str]:
    """
    1枠だけスタメン差し替え。Team.set_starting_lineup_by_players を使用（CLI と同じ）。
    """
    starters = get_current_starting_five(team)
    if len(starters) < 5:
        return False, "スタメンが5人未満のため変更できません。"
    if slot_index < 0 or slot_index >= len(starters):
        return False, "枠の指定が不正です（PG〜C の5枠）。"
    cands = get_available_starting_candidates(team, starters, slot_index)
    npid = getattr(new_player, "player_id", None)
    if npid is None:
        return False, "選手IDが無効です。"
    if not any(getattr(p, "player_id", None) == npid for p in cands):
        return False, "その選手はこの枠には選べません。"
    updated = list(starters)
    updated[slot_index] = new_player
    setter = getattr(team, "set_starting_lineup_by_players", None)
    if not callable(setter):
        return False, "チームがスタメン設定に対応していません。"
    try:
        setter(updated)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def get_sixth_man_candidates(user_team: Any) -> List[Any]:
    """CLI change_sixth_man と同一の候補（先発以外の有効なロスター選手）。"""
    starter_ids = get_starting_player_ids(user_team)
    candidates: List[Any] = []
    for p in sort_roster_for_gm_view(list(getattr(user_team, "players", []) or [])):
        if not _player_active_for_bench_order(p):
            continue
        if getattr(p, "player_id", None) in starter_ids:
            continue
        candidates.append(p)
    return candidates


def apply_sixth_man_selection(team: Any, player: Any) -> Tuple[bool, str]:
    cands = get_sixth_man_candidates(team)
    npid = getattr(player, "player_id", None)
    if npid is None:
        return False, "選手IDが無効です。"
    if not any(getattr(p, "player_id", None) == npid for p in cands):
        return False, "その選手は6thに選べません。"
    setter = getattr(team, "set_sixth_man", None)
    if not callable(setter):
        return False, "チームが6th設定に対応していません。"
    setter(player)
    return True, ""


def apply_bench_order_swap(team: Any, index_a: int, index_b: int) -> Tuple[bool, str]:
    bench = get_current_bench_order(team)
    n = len(bench)
    if n < 2:
        return False, "ベンチが2人未満のため入れ替えできません。"
    if index_a < 0 or index_a >= n or index_b < 0 or index_b >= n:
        return False, "番号が不正です。"
    if index_a == index_b:
        return False, "同じ番号は入れ替えできません。"
    updated = bench[:]
    updated[index_a], updated[index_b] = updated[index_b], updated[index_a]
    setter = getattr(team, "set_bench_order_by_players", None)
    if not callable(setter):
        return False, "チームがベンチ序列設定に対応していません。"
    try:
        setter(updated)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def get_current_bench_order(user_team: Any) -> List[Any]:
    if hasattr(user_team, "get_bench_order_players"):
        try:
            return list(user_team.get_bench_order_players() or [])
        except Exception:
            pass
    starter_ids = get_starting_player_ids(user_team)
    roster = sort_roster_for_gm_view(list(getattr(user_team, "players", []) or []))
    return [
        p
        for p in roster
        if _player_active_for_bench_order(p) and getattr(p, "player_id", None) not in starter_ids
    ]


def _brief_player_line(p: Any) -> str:
    return (
        f"{str(getattr(p, 'name', '-')):<15} "
        f"{str(getattr(p, 'position', '-')):<2} "
        f"OVR:{int(getattr(p, 'ovr', 0)):<2} "
        f"Age:{int(getattr(p, 'age', 0)):<2} "
        f"{getattr(p, 'nationality', 'Japan')}"
    )


def format_starting_lineup_text(team: Any) -> str:
    starters = get_current_starting_five(team)
    if not starters:
        return "スタメン候補が不足しているか、まだ設定されていません。"
    lines: List[str] = ["【スタメン】", ""]
    for i, p in enumerate(starters, 1):
        lines.append(f"{i}. {_brief_player_line(p)}")
    return "\n".join(lines)


def format_sixth_man_line_text(team: Any) -> str:
    sm = get_current_sixth_man(team)
    if sm is None:
        return "6thマンが未設定です。"
    return "【6thマン】\n\n" + _brief_player_line(sm)


def format_bench_order_text(team: Any) -> str:
    bench = get_current_bench_order(team)
    if not bench:
        return "ベンチ候補が存在しません。"
    sixth = get_current_sixth_man(team)
    sid = getattr(sixth, "player_id", None) if sixth is not None else None
    lines: List[str] = ["【ベンチ序列】（先頭が7番手）", ""]
    for i, p in enumerate(bench, 1):
        mark = "6" if getattr(p, "player_id", None) == sid else " "
        lines.append(f"{i}. {mark} {_brief_player_line(p)}")
    lines.append("")
    lines.append("6 = 現在のシックスマン")
    return "\n".join(lines)


def format_lineup_snapshot_text(team: Any) -> str:
    """スタメン・6th・ベンチを1画面用にまとめる（読み取り専用）。"""
    parts = [
        format_starting_lineup_text(team),
        "",
        "─" * 40,
        "",
        format_sixth_man_line_text(team),
        "",
        "─" * 40,
        "",
        format_bench_order_text(team),
        "",
        "※ スタメン枠の差し替えは、左メニュー「戦術」→ 上段「先発・6th・ベンチ」、または"
        "ターミナル「8. GMメニュー」のスタメン変更。カスタム解除は「自動スタメンに戻す」。",
    ]
    return "\n".join(parts)


def format_team_identity_text(team: Any) -> str:
    getter = getattr(team, "get_usage_policy_label", None)
    if callable(getter):
        try:
            usage_label = str(getter())
        except Exception:
            usage_label = str(getattr(team, "usage_policy", "balanced"))
    else:
        usage_label = str(getattr(team, "usage_policy", "balanced"))
    lines = [
        f"クラブ名      : {getattr(team, 'name', '-')}",
        f"拠点地        : {getattr(team, 'home_city', 'Unknown')}",
        f"市場規模      : {float(getattr(team, 'market_size', 1.0)):.2f}",
        f"人気          : {getattr(team, 'popularity', 0)}",
        f"資金          : {format_money_yen_ja_readable(int(getattr(team, 'money', 0) or 0))}",
        f"戦術          : {getattr(team, 'strategy', 'balanced')}",
        f"HCスタイル    : {getattr(team, 'coach_style', 'balanced')}",
        f"起用方針      : {usage_label}",
    ]
    return "\n".join(lines)


def format_salary_cap_text(team: Any) -> str:
    payroll = int(get_team_payroll(team))
    lv = league_level_for_team(team)
    league_cap = int(get_soft_cap(league_level=lv))

    st = cap_status(payroll, league_level=lv)
    if st == "over_soft_cap":
        status = "サラリーキャップ超過（贅沢税の対象。補強・契約はルール上制限され得ます）"
    else:
        status = "キャップ内"

    room = league_cap - payroll

    lines = [
        f"チーム年俸合計   : {format_money_yen_ja_readable(payroll)}",
        f"サラリーキャップ : {format_money_yen_ja_readable(league_cap)}（D{lv}・全ディビジョン同一・12億円）",
        "",
        f"状態             : {status}",
    ]
    if room >= 0:
        lines.append(f"キャップまでの余裕 : {format_money_yen_ja_readable(room)}")
    else:
        lines.append(
            f"キャップ超過分     : {format_money_yen_ja_readable(abs(room))}"
            "（贅沢税は年俸合計ベースで計算）"
        )

    return "\n".join(lines)


def format_gm_roster_text(team: Any) -> str:
    roster = sort_roster_for_gm_view(list(getattr(team, "players", []) or []))
    if not roster:
        return "ロスターが存在しません。"

    starter_ids = get_starting_player_ids(team)
    sixth_man = get_current_sixth_man(team)
    sixth_man_id = getattr(sixth_man, "player_id", None) if sixth_man is not None else None

    lines_out: List[str] = []
    for i, p in enumerate(roster, 1):
        player_id = getattr(p, "player_id", None)

        if player_id in starter_ids:
            role_mark = "★"
        elif player_id == sixth_man_id:
            role_mark = "6"
        else:
            role_mark = " "

        slot_lbl = get_player_nationality_bucket_label(p)
        lines_out.append(
            f"{i:>2}. {role_mark} {str(getattr(p, 'name', '-')):<15} "
            f"{str(getattr(p, 'position', '-')):<2} "
            f"OVR:{int(getattr(p, 'ovr', 0)):<2} "
            f"Age:{int(getattr(p, 'age', 0)):<2} "
            f"{str(getattr(p, 'nationality', 'Japan')):<12} "
            f"区分:{slot_lbl:<10} "
            f"Salary:{format_money_yen_ja_readable(int(getattr(p, 'salary', 0) or 0))}"
        )

    lines_out.append("")
    lines_out.append("★ = スタメン")
    lines_out.append("6 = シックスマン")
    lines_out.append("区分 = 本契約ロスター枠（外国籍／アジア・帰化／日本）")
    return "\n".join(lines_out)
