"""
再契約（CLI）用の短い判断補助表示のみ。契約計算・再契約成立ロジックは変更しない。
"""

from __future__ import annotations

from typing import Any, List, Optional

from basketball_sim.systems.draft import (
    build_draft_candidate_role_shape_label,
    build_draft_candidate_strength_weakness_line,
)


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _pot_letter(player: Any) -> str:
    raw = str(getattr(player, "potential", "C") or "C").upper().strip()
    ch = raw[0] if raw else "C"
    if ch not in ("S", "A", "B", "C", "D"):
        ch = "C"
    return ch


def _team_ovr_rank(team: Any, player: Any) -> int:
    try:
        pid = getattr(player, "player_id", None)
        plist: List[Any] = list(getattr(team, "players", []) or [])
        ordered = sorted(
            plist,
            key=lambda p: _safe_int(getattr(p, "ovr", 0), 0),
            reverse=True,
        )
        for r, p in enumerate(ordered, 1):
            if getattr(p, "player_id", object()) == pid:
                return r
    except Exception:
        pass
    return 99


def build_re_sign_priority_label(
    team: Any,
    player: Any,
    *,
    ask_salary: Optional[int] = None,
    current_salary: Optional[int] = None,
) -> str:
    """
    優先再契約 / 将来確保 / 慎重判断 / ベテラン整理候補 / バランス型（表示のみ）。
    """
    try:
        age = _safe_int(getattr(player, "age", 0), 22)
        ovr = _safe_int(getattr(player, "ovr", 0), 0)
        rank = _team_ovr_rank(team, player)
        cur = _safe_int(
            current_salary if current_salary is not None else getattr(player, "salary", 0),
            0,
        )
        ask = _safe_int(
            ask_salary if ask_salary is not None else getattr(player, "desired_salary", cur),
            0,
        )
        ratio = (ask / max(1, cur)) if cur > 0 else 1.0
        letter = _pot_letter(player)
    except Exception:
        return "情報なし"

    if (age >= 34) or (age >= 31 and rank >= 11) or (age >= 32 and ovr < 58):
        return "ベテラン整理候補"
    if age <= 24 and letter in ("S", "A", "B") and ovr < 66 and rank > 5:
        return "将来確保"
    if (ratio >= 1.28 and cur >= 3_000_000) or (age >= 29 and 58 <= ovr <= 67 and rank >= 7):
        return "慎重判断"
    if rank <= 5 or ovr >= 72 or (ovr >= 68 and rank <= 7):
        return "優先再契約"
    return "バランス型"


def build_re_sign_value_label(
    team: Any,
    player: Any,
    *,
    ask_salary: Optional[int] = None,
    current_salary: Optional[int] = None,
) -> str:
    """契約負担感の簡易ラベル（残し得 / 標準圏 / 高額注意）。表示のみ。"""
    try:
        ask = _safe_int(
            ask_salary if ask_salary is not None else getattr(player, "desired_salary", 0),
            0,
        )
        cur = _safe_int(
            current_salary if current_salary is not None else getattr(player, "salary", 0),
            0,
        )
        if ask <= 0:
            return "情報なし"
        from basketball_sim.systems.resign_salary_anchor import get_resign_anchor_band

        lo, mid, eff_hi = get_resign_anchor_band(player, team)
        if ask <= max(lo, int(mid * 1.03)):
            return "残し得"
        if ask <= int(eff_hi * 1.10):
            return "標準圏"
        return "高額注意"
    except Exception:
        try:
            ask = _safe_int(
                ask_salary if ask_salary is not None else getattr(player, "desired_salary", 0),
                0,
            )
            cur = _safe_int(
                current_salary if current_salary is not None else getattr(player, "salary", 0),
                0,
            )
            if ask <= 0:
                return "情報なし"
            ratio = ask / max(1, cur)
            if ratio <= 1.08:
                return "残し得"
            if ratio <= 1.30:
                return "標準圏"
            return "高額注意"
        except Exception:
            return "情報なし"


def build_re_sign_depth_hint(team: Any, player: Any) -> str:
    """層の目安（厳密でない）。空文字なら省略可。"""
    try:
        pos = str(getattr(player, "position", "") or "").strip().upper()
        pid = getattr(player, "player_id", None)
        others = [
            p
            for p in list(getattr(team, "players", []) or [])
            if getattr(p, "player_id", object()) != pid
        ]
        guards = sum(
            1 for p in others if str(getattr(p, "position", "") or "").strip().upper() in ("PG", "SG")
        )
        bigs = sum(
            1 for p in others if str(getattr(p, "position", "") or "").strip().upper() in ("PF", "C")
        )
        rank = _team_ovr_rank(team, player)
        ovr = _safe_int(getattr(player, "ovr", 0), 0)
        if pos in ("PG", "SG") and guards <= 2:
            return "ガード層に必要"
        if pos in ("PF", "C") and bigs <= 2:
            return "ビッグ層維持に必要"
        if rank >= 9 and ovr >= 54:
            return "ベンチ要員として有用"
    except Exception:
        pass
    return ""


def format_re_sign_cli_hint(
    team: Any,
    player: Any,
    *,
    ask_salary: Optional[int] = None,
    current_salary: Optional[int] = None,
) -> str:
    """再契約候補1人分の補助1行（一覧・確認ダイアログ前のCLI用）。"""
    try:
        pri = build_re_sign_priority_label(
            team, player, ask_salary=ask_salary, current_salary=current_salary
        )
        sw = build_draft_candidate_strength_weakness_line(player)
        shape = build_draft_candidate_role_shape_label(player)
        val = build_re_sign_value_label(
            team, player, ask_salary=ask_salary, current_salary=current_salary
        )
        depth = build_re_sign_depth_hint(team, player)
        parts = [pri, sw, shape, val]
        if depth:
            parts.append(depth)
        return " / ".join(parts)
    except Exception:
        return "情報なし"
