"""
自動役割タグ（表示専用）。判定正本: docs/AUTO_ROLE_TAG_PARAMS.md

数値シミュ・起用の正本には使わない。手動 main_role とは別系統。
人事ロスター / GM スタメン・ベンチの行末「タグ:」表示用（gm_dashboard_text が参照）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from basketball_sim.systems.team_tactics import ROLE_DEFAULTS, ensure_team_tactics_on_team, get_safe_team_tactics

# 内部キー（docs/AUTO_ROLE_TAG_PARAMS.md §2 と一致）
TAG_BENCH_SCORER = "bench_scorer"
TAG_ACE = "ace"
TAG_FLOOR_GENERAL = "floor_general"
TAG_SHOOTER = "shooter"
TAG_RIM_PROTECTOR = "rim_protector"
TAG_PERIMETER_STOPPER = "perimeter_stopper"
TAG_ROLE_PLAYER = "role_player"

AUTO_ROLE_TAG_JA: Dict[str, str] = {
    TAG_BENCH_SCORER: "ベンチスコアラー",
    TAG_ACE: "エース",
    TAG_FLOOR_GENERAL: "司令塔",
    TAG_SHOOTER: "シューター",
    TAG_RIM_PROTECTOR: "守護神",
    TAG_PERIMETER_STOPPER: "エースストッパー",
    TAG_ROLE_PLAYER: "ロールプレイヤー",
}


def japanese_label_for_auto_role_tag_key(key: str) -> str:
    return AUTO_ROLE_TAG_JA.get(key, AUTO_ROLE_TAG_JA[TAG_ROLE_PLAYER])


def _ranks_desc(players: List[Any], value_fn) -> Dict[int, int]:
    """値が大きいほど順位 1。同値は player_id 昇順。"""
    sorted_ps = sorted(
        players,
        key=lambda p: (-float(value_fn(p)), int(getattr(p, "player_id", 0) or 0)),
    )
    out: Dict[int, int] = {}
    for i, p in enumerate(sorted_ps, 1):
        pid = getattr(p, "player_id", None)
        if pid is not None:
            out[int(pid)] = i
    return out


def _role_row(roles: Mapping[str, Any], pid: int) -> Dict[str, str]:
    raw = roles.get(str(pid))
    row = dict(ROLE_DEFAULTS)
    if isinstance(raw, dict):
        row.update({k: str(raw.get(k, row[k])) for k in ROLE_DEFAULTS})
    return row


def _tm_map(team: Any) -> Dict[int, float]:
    ensure_team_tactics_on_team(team)
    rot = (get_safe_team_tactics(team).get("rotation") or {})  # type: ignore[union-attr]
    raw = rot.get("target_minutes") if isinstance(rot, dict) else {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[int, float] = {}
    for k, v in raw.items():
        try:
            pid = int(str(k).strip())
        except (TypeError, ValueError):
            continue
        try:
            out[pid] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _target_minutes_for_player(tm: Dict[int, float], pid: int) -> float:
    return float(tm.get(pid, 0.0))


def _scoring_sum(p: Any) -> int:
    return int(getattr(p, "shoot", 0) or 0) + int(getattr(p, "three", 0) or 0) + int(getattr(p, "drive", 0) or 0)


def _clutch_ord(row: Dict[str, str]) -> int:
    m = {"go_to": 3, "standard": 2, "limited": 1}
    return m.get(row.get("clutch_priority", "standard"), 2)


def _inv_ord(row: Dict[str, str]) -> int:
    m = {"high": 3, "standard": 2, "low": 1}
    return m.get(row.get("offense_involvement", "standard"), 2)


def _shot_pri_ord(row: Dict[str, str]) -> int:
    m = {"aggressive": 3, "standard": 2, "passive": 1}
    return m.get(row.get("shot_priority", "standard"), 2)


def _pm_ord(row: Dict[str, str]) -> int:
    m = {"primary": 3, "secondary": 2, "minimal": 1}
    return m.get(row.get("playmaking_role", "secondary"), 2)


def _is_bench_scorer(
    p: Any,
    *,
    starter_ids: set,
    sixth_id: Optional[int],
    roster: List[Any],
    bench: List[Any],
    roles: Mapping[str, Any],
    tm: Dict[int, float],
    ranks_all_tm: Dict[int, int],
    ranks_bench_tm: Dict[int, int],
    ranks_bench_ovr: Dict[int, int],
    ranks_bench_sed: Dict[int, int],
) -> bool:
    pid = getattr(p, "player_id", None)
    if pid is None or pid in starter_ids:
        return False
    row = _role_row(roles, int(pid))
    b = (
        (sixth_id is not None and int(pid) == int(sixth_id))
        or (
            ranks_all_tm.get(int(pid), 999) <= 8
            and ranks_bench_tm.get(int(pid), 999) <= 3
        )
    )
    if not b:
        return False
    if ranks_bench_ovr.get(int(pid), 999) > 3:
        return False
    if ranks_bench_sed.get(int(pid), 999) > 2:
        return False
    sed_rank1_pids = {qpid for qpid, r in ranks_bench_sed.items() if r == 1}
    e = (
        row.get("offense_involvement") == "high"
        or row.get("shot_priority") == "aggressive"
        or int(pid) in sed_rank1_pids
    )
    return e


def _is_ace(
    p: Any,
    *,
    starter_ids: set,
    roster: List[Any],
    roles: Mapping[str, Any],
    ranks_all_ovr: Dict[int, int],
    ranks_all_tm: Dict[int, int],
) -> bool:
    pid = getattr(p, "player_id", None)
    if pid is None or pid not in starter_ids:
        return False
    row = _role_row(roles, int(pid))
    if ranks_all_ovr.get(int(pid), 999) > 2:
        return False
    c = (
        ranks_all_tm.get(int(pid), 999) <= 3
        or row.get("offense_involvement") == "high"
        or row.get("clutch_priority") == "go_to"
    )
    return c


def _is_floor_general(p: Any, *, roles: Mapping[str, Any], ranks_all_pass: Dict[int, int]) -> bool:
    pid = getattr(p, "player_id", None)
    if pid is None:
        return False
    row = _role_row(roles, int(pid))
    if row.get("playmaking_role") == "primary":
        return True
    return ranks_all_pass.get(int(pid), 999) <= 3 and row.get("offense_involvement") != "low"


def _is_shooter(p: Any, *, roles: Mapping[str, Any], ranks_all_three: Dict[int, int]) -> bool:
    pid = getattr(p, "player_id", None)
    if pid is None:
        return False
    row = _role_row(roles, int(pid))
    if ranks_all_three.get(int(pid), 999) > 3:
        return False
    return row.get("shot_priority") == "aggressive" or int(getattr(p, "three", 0) or 0) >= 62


def _is_defense_block(p: Any, *, roles: Mapping[str, Any], ranks_all_def: Dict[int, int]) -> bool:
    pid = getattr(p, "player_id", None)
    if pid is None:
        return False
    row = _role_row(roles, int(pid))
    return row.get("defense_assignment") == "stopper" and ranks_all_def.get(int(pid), 999) <= 4


def _defense_kind(p: Any) -> Optional[str]:
    pos = str(getattr(p, "position", "SF") or "SF")
    if pos in ("PF", "C"):
        return TAG_RIM_PROTECTOR
    if pos in ("PG", "SG", "SF"):
        return TAG_PERIMETER_STOPPER
    return None


def compute_auto_role_tags_for_team(team: Any) -> Dict[int, str]:
    """
    各 player_id に内部タグキーを1つ返す。docs/AUTO_ROLE_TAG_PARAMS.md 準拠。
    """
    from basketball_sim.systems import gm_dashboard_text as gmd

    ensure_team_tactics_on_team(team)
    tactics = get_safe_team_tactics(team)
    roles: Mapping[str, Any] = dict(tactics.get("roles") or {})

    roster = gmd.sort_roster_for_gm_view(list(getattr(team, "players", []) or []))
    starter_ids = {x for x in gmd.get_starting_player_ids(team) if x is not None}
    sm = gmd.get_current_sixth_man(team)
    sixth_id = getattr(sm, "player_id", None) if sm is not None else None

    bench = [p for p in roster if getattr(p, "player_id", None) not in starter_ids]

    tm = _tm_map(team)

    ranks_all_tm = _ranks_desc(roster, lambda p: _target_minutes_for_player(tm, int(getattr(p, "player_id", -1))))
    ranks_bench_tm = _ranks_desc(bench, lambda p: _target_minutes_for_player(tm, int(getattr(p, "player_id", -1))))
    ranks_all_ovr = _ranks_desc(roster, lambda p: int(getattr(p, "ovr", 0) or 0))
    ranks_bench_ovr = _ranks_desc(bench, lambda p: int(getattr(p, "ovr", 0) or 0))
    ranks_bench_sed = _ranks_desc(bench, lambda p: _scoring_sum(p))
    ranks_all_pass = _ranks_desc(roster, lambda p: int(getattr(p, "passing", 0) or 0))
    ranks_all_three = _ranks_desc(roster, lambda p: int(getattr(p, "three", 0) or 0))
    ranks_all_def = _ranks_desc(roster, lambda p: int(getattr(p, "defense", 0) or 0))

    out: Dict[int, str] = {}
    for p in roster:
        pid = getattr(p, "player_id", None)
        if pid is None:
            continue
        ip = int(pid)
        if _is_bench_scorer(
            p,
            starter_ids=starter_ids,
            sixth_id=sixth_id,
            roster=roster,
            bench=bench,
            roles=roles,
            tm=tm,
            ranks_all_tm=ranks_all_tm,
            ranks_bench_tm=ranks_bench_tm,
            ranks_bench_ovr=ranks_bench_ovr,
            ranks_bench_sed=ranks_bench_sed,
        ):
            out[ip] = TAG_BENCH_SCORER
        elif _is_ace(
            p,
            starter_ids=starter_ids,
            roster=roster,
            roles=roles,
            ranks_all_ovr=ranks_all_ovr,
            ranks_all_tm=ranks_all_tm,
        ):
            out[ip] = TAG_ACE
        elif _is_floor_general(p, roles=roles, ranks_all_pass=ranks_all_pass):
            out[ip] = TAG_FLOOR_GENERAL
        elif _is_shooter(p, roles=roles, ranks_all_three=ranks_all_three):
            out[ip] = TAG_SHOOTER
        elif _is_defense_block(p, roles=roles, ranks_all_def=ranks_all_def):
            kind = _defense_kind(p)
            if kind is not None:
                out[ip] = kind
            else:
                out[ip] = TAG_ROLE_PLAYER
        else:
            out[ip] = TAG_ROLE_PLAYER
    return out
