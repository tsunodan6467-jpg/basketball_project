"""
負傷発生後の起用・ローテ最低限の自動整合（試合終了フック用）。

負傷ロジック本体（いつケガが付与されるか）は変更せず、
team_tactics.rotation / Team の先発・6th・ベンチが負傷者を参照し続けないよう整える。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from basketball_sim.systems.competition_rules import get_competition_rule
from basketball_sim.systems.japan_regulation import lineup_passes_on_court
from basketball_sim.systems.team_tactics import (
    STARTER_POSITIONS,
    ensure_team_tactics_on_team,
    _dedupe_starters_inplace,
)


def _injured_player_ids(team: Any) -> Set[int]:
    out: Set[int] = set()
    for p in getattr(team, "players", None) or []:
        if p is None:
            continue
        inj = getattr(p, "is_injured", None)
        try:
            if callable(inj):
                if not inj():
                    continue
            elif not bool(getattr(p, "injured", False)):
                continue
        except Exception:
            continue
        pid = getattr(p, "player_id", None)
        try:
            if pid is not None:
                out.add(int(pid))
        except (TypeError, ValueError):
            continue
    return out


def _starters_map_from_starting_five(team: Any) -> Dict[str, Optional[int]]:
    """get_starting_five() の並びから PG〜C スロットへ player_id を割り当て（最低限の位置一致優先）。"""
    out: Dict[str, Optional[int]] = {pos: None for pos in STARTER_POSITIONS}
    five = []
    if hasattr(team, "get_starting_five"):
        try:
            five = list(team.get_starting_five() or [])
        except Exception:
            five = []
    used: Set[int] = set()

    for p in five:
        pid = getattr(p, "player_id", None)
        if pid is None:
            continue
        try:
            ip = int(pid)
        except (TypeError, ValueError):
            continue
        pos = str(getattr(p, "position", "") or "")
        if pos in out and out[pos] is None:
            out[pos] = ip
            used.add(ip)

    for p in five:
        pid = getattr(p, "player_id", None)
        if pid is None:
            continue
        try:
            ip = int(pid)
        except (TypeError, ValueError):
            continue
        if ip in used:
            continue
        for pos in STARTER_POSITIONS:
            if out[pos] is None:
                out[pos] = ip
                used.add(ip)
                break

    return out


def auto_repair_lineup_for_injuries(team: Any, competition_type: Optional[str] = None) -> bool:
    """
    負傷者が rotation / 先発ID / 6th / ベンチに残っている場合に除去・再割当する。

    Returns:
        チーム状態を変更した場合 True（ユーザーチーム向け通知用）。
    """
    if team is None or not hasattr(team, "players"):
        return False

    inj = _injured_player_ids(team)
    if not inj:
        return False

    changed = False

    ensure_team_tactics_on_team(team)
    tact = getattr(team, "team_tactics", None)
    if not isinstance(tact, dict):
        return False
    rot = tact.get("rotation")
    if not isinstance(rot, dict):
        return False

    tm = rot.get("target_minutes")
    if isinstance(tm, dict):
        for pid in inj:
            key = str(pid)
            try:
                cur = float(tm.get(key, 0) or 0)
            except (TypeError, ValueError):
                cur = 0.0
            if cur > 1e-6:
                tm[key] = 0.0
                changed = True

    st = rot.get("starters")

    before_sl = tuple(getattr(team, "starting_lineup", ()) or ())
    five_getter = getattr(team, "get_starting_five", None)
    five: list = []
    if callable(five_getter):
        try:
            five = list(five_getter() or [])
        except Exception:
            five = []
    setter_sl = getattr(team, "set_starting_lineup_by_players", None)
    if callable(setter_sl) and five:
        try:
            setter_sl(five)
        except Exception:
            pass
        if tuple(getattr(team, "starting_lineup", ()) or ()) != before_sl:
            changed = True

    if isinstance(st, dict):
        new_map = _starters_map_from_starting_five(team)
        for pos in STARTER_POSITIONS:
            nv = new_map.get(pos)
            ov = st.get(pos)
            try:
                on = int(ov) if ov is not None else None
            except (TypeError, ValueError):
                on = None
            try:
                nn = int(nv) if nv is not None else None
            except (TypeError, ValueError):
                nn = None
            if on != nn:
                st[pos] = nn
                changed = True
        _dedupe_starters_inplace(st)

    bo = rot.get("bench_order")
    if isinstance(bo, list):
        new_bo: list = []
        for x in bo:
            try:
                ip = int(x)
            except (TypeError, ValueError):
                continue
            if ip in inj:
                changed = True
                continue
            if ip not in new_bo:
                new_bo.append(ip)
        if new_bo != bo:
            rot["bench_order"] = new_bo
            changed = True

    sixth_cleared_for_injury = False
    sid = getattr(team, "sixth_man_id", None)
    if sid is not None:
        try:
            if int(sid) in inj:
                team.sixth_man_id = None
                changed = True
                sixth_cleared_for_injury = True
        except (TypeError, ValueError):
            pass

    if sixth_cleared_for_injury:
        sm_getter = getattr(team, "get_sixth_man", None)
        sm = None
        if callable(sm_getter):
            try:
                sm = sm_getter()
            except Exception:
                sm = None
        sm_setter = getattr(team, "set_sixth_man", None)
        if callable(sm_setter):
            try:
                if sm is not None:
                    sm_setter(sm)
                else:
                    clr = getattr(team, "clear_sixth_man", None)
                    if callable(clr):
                        clr()
            except Exception:
                pass

    before_b = tuple(getattr(team, "bench_order", ()) or ())
    bo_setter = getattr(team, "set_bench_order_by_players", None)
    bo_getter = getattr(team, "get_bench_order_players", None)
    if callable(bo_setter) and callable(bo_getter):
        try:
            bo_setter(list(bo_getter() or []))
        except Exception:
            pass
        if tuple(getattr(team, "bench_order", ()) or ()) != before_b:
            changed = True

    if changed and bool(getattr(team, "is_user_team", False)):
        setattr(
            team,
            "_injury_autorepair_notice_jp",
            "負傷者の目標出場を0にし、先発・6th・ベンチ候補を自動で差し替えました。"
            "必要であれば戦術でローテーションを手動で再構築してください。",
        )

    # 保存先発5人が当該大会のオンコート枠を満たさない場合はクリアし、次試合で再計算させる
    try:
        on_court = get_competition_rule(competition_type, "on_court")
        five_getter = getattr(team, "get_starting_five", None)
        five: list = []
        if callable(five_getter):
            try:
                five = list(five_getter() or [])
            except Exception:
                five = []
        if len(five) == 5 and not lineup_passes_on_court(five, on_court):
            clr = getattr(team, "clear_starting_lineup", None)
            if callable(clr):
                clr()
                changed = True
    except Exception:
        pass

    return changed
