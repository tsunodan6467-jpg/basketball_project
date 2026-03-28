"""
チーム戦術設定。

Phase A: 永続化・正規化・メニュー。
Phase B: rotation（先発5人・控え順・目標分数）を試合ローテへ弱く接続（詳細は Match / RotationSystem）。
"""

from __future__ import annotations

from typing import AbstractSet, Any, Dict, List, Optional, Set, Tuple

TACTICS_SCHEMA_VERSION = 1

STARTER_POSITIONS: Tuple[str, ...] = ("PG", "SG", "SF", "PF", "C")

TEAM_STRATEGY_DEFAULTS: Dict[str, str] = {
    "offense_tempo": "standard",
    "offense_style": "balanced",
    "offense_creation": "ball_move",
    "defense_style": "balanced",
    "rebound_style": "balanced",
    "transition_style": "situational",
}

ALLOWED_OFFENSE_TEMPO = frozenset({"slow", "standard", "fast"})
ALLOWED_OFFENSE_STYLE = frozenset({"balanced", "inside", "three_point", "drive"})
ALLOWED_OFFENSE_CREATION = frozenset({"ball_move", "pick_and_roll", "iso", "post"})
ALLOWED_DEFENSE_STYLE = frozenset({"balanced", "protect_paint", "protect_three", "pressure"})
ALLOWED_REBOUND_STYLE = frozenset({"get_back", "balanced", "crash_offense"})
ALLOWED_TRANSITION_STYLE = frozenset({"push", "situational", "half_court"})

ROTATION_DEFAULTS: Dict[str, Any] = {
    "starters": {},
    "bench_order": [],
    "target_minutes": {},
    "sub_policy": "standard",
    "fatigue_policy": "standard",
    "foul_policy": "standard",
    "clutch_policy": "stars",
}

ALLOWED_SUB_POLICY = frozenset({"standard", "starters_long", "bench_deep", "youth_dev"})
ALLOWED_FATIGUE_POLICY = frozenset({"strict", "standard", "push"})
ALLOWED_FOUL_POLICY = frozenset({"early_pull", "standard", "ride"})
ALLOWED_CLUTCH_POLICY = frozenset({"stars", "hot_hand", "defense", "offense"})

# ネスト名は依頼書どおり（Team.usage_policy 文字列とは別物）
USAGE_POLICY_DEFAULTS: Dict[str, str] = {
    "priority": "balanced",
    "evaluation_focus": "overall",
    "form_weight": "standard",
    "age_balance": "balanced",
    "injury_care": "standard",
    "schedule_care": "standard",
    "foreign_player_usage": "balanced",
}

ALLOWED_USAGE_PRIORITY = frozenset({"win", "balanced", "development"})
ALLOWED_EVALUATION_FOCUS = frozenset({"overall", "offense", "defense", "potential"})
ALLOWED_FORM_WEIGHT = frozenset({"high", "standard", "skill"})
ALLOWED_AGE_BALANCE = frozenset({"veteran", "balanced", "youth"})
ALLOWED_INJURY_CARE = frozenset({"high", "standard", "low"})
ALLOWED_SCHEDULE_CARE = frozenset({"rest", "standard", "win"})
ALLOWED_FOREIGN_USAGE = frozenset({"stars", "balanced", "japan_core"})

PLAYBOOK_DEFAULTS: Dict[str, str] = {
    "pick_and_roll": "standard",
    "spain_pick_and_roll": "standard",
    "handoff": "standard",
    "off_ball_screen": "standard",
    "post_up": "standard",
    "transition": "standard",
}

ALLOWED_PLAYBOOK_LEVEL = frozenset({"low", "standard", "high"})

ROLE_DEFAULTS: Dict[str, str] = {
    "main_role": "none",
    "offense_involvement": "standard",
    "shot_priority": "standard",
    "clutch_priority": "standard",
    "playmaking_role": "secondary",
    "defense_assignment": "standard",
}

ALLOWED_MAIN_ROLE = frozenset(
    {
        "none",
        "ace",
        "second_scorer",
        "playmaker",
        "shooter",
        "post_scorer",
        "defense_ace",
        "rebounder",
        "sixth_man",
        "energy",
    }
)
ALLOWED_INVOLVEMENT = frozenset({"high", "standard", "low"})
ALLOWED_SHOT_PRIORITY = frozenset({"aggressive", "standard", "passive"})
ALLOWED_CLUTCH_PRIORITY = frozenset({"go_to", "standard", "limited"})
ALLOWED_PLAYMAKING_ROLE = frozenset({"primary", "secondary", "minimal"})
ALLOWED_DEFENSE_ASSIGNMENT = frozenset({"stopper", "standard", "light"})


def get_default_team_tactics() -> Dict[str, Any]:
    return {
        "version": TACTICS_SCHEMA_VERSION,
        "team_strategy": dict(TEAM_STRATEGY_DEFAULTS),
        "rotation": {
            "starters": {},
            "bench_order": [],
            "target_minutes": {},
            "sub_policy": ROTATION_DEFAULTS["sub_policy"],
            "fatigue_policy": ROTATION_DEFAULTS["fatigue_policy"],
            "foul_policy": ROTATION_DEFAULTS["foul_policy"],
            "clutch_policy": ROTATION_DEFAULTS["clutch_policy"],
        },
        "usage_policy": dict(USAGE_POLICY_DEFAULTS),
        "roles": {},
        "playbook": dict(PLAYBOOK_DEFAULTS),
    }


def _pick_str(value: Any, allowed: frozenset, default: str) -> str:
    s = str(value or "").strip()
    if s in allowed:
        return s
    return default


def _normalize_team_strategy(raw: Any) -> Dict[str, str]:
    out = dict(TEAM_STRATEGY_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    out["offense_tempo"] = _pick_str(raw.get("offense_tempo"), ALLOWED_OFFENSE_TEMPO, out["offense_tempo"])
    out["offense_style"] = _pick_str(raw.get("offense_style"), ALLOWED_OFFENSE_STYLE, out["offense_style"])
    out["offense_creation"] = _pick_str(
        raw.get("offense_creation"), ALLOWED_OFFENSE_CREATION, out["offense_creation"]
    )
    out["defense_style"] = _pick_str(raw.get("defense_style"), ALLOWED_DEFENSE_STYLE, out["defense_style"])
    out["rebound_style"] = _pick_str(raw.get("rebound_style"), ALLOWED_REBOUND_STYLE, out["rebound_style"])
    out["transition_style"] = _pick_str(
        raw.get("transition_style"), ALLOWED_TRANSITION_STYLE, out["transition_style"]
    )
    return out


def _safe_int_pid(value: Any) -> Optional[int]:
    try:
        v = int(value)
        if v <= 0:
            return None
        return v
    except (TypeError, ValueError):
        return None


def _dedupe_starters_inplace(starters: Dict[str, Optional[int]]) -> None:
    used: Set[int] = set()
    for pos in STARTER_POSITIONS:
        pid = starters.get(pos)
        if pid is None:
            continue
        if pid in used:
            starters[pos] = None
        else:
            used.add(pid)


def _normalize_starters(raw: Any) -> Dict[str, Optional[int]]:
    out: Dict[str, Optional[int]] = {pos: None for pos in STARTER_POSITIONS}
    if not isinstance(raw, dict):
        return out
    for pos in STARTER_POSITIONS:
        pid = raw.get(pos)
        if pid is None or pid == "" or str(pid).strip() == "":
            out[pos] = None
            continue
        out[pos] = _safe_int_pid(pid)
    return out


def _normalize_bench_order(raw: Any) -> List[int]:
    if not isinstance(raw, list):
        return []
    out: List[int] = []
    seen = set()
    for item in raw:
        pid = _safe_int_pid(item)
        if pid is None or pid in seen:
            continue
        out.append(pid)
        seen.add(pid)
    return out


def _normalize_target_minutes(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, float] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if not key:
            continue
        try:
            m = float(v)
        except (TypeError, ValueError):
            continue
        m = max(0.0, min(40.0, m))
        out[key] = m
    return out


def _normalize_rotation(raw: Any) -> Dict[str, Any]:
    base = dict(ROTATION_DEFAULTS)
    if not isinstance(raw, dict):
        raw = {}
    base["starters"] = _normalize_starters(raw.get("starters"))
    # 同一選手の重複先発指定を後勝ちで除去
    _dedupe_starters_inplace(base["starters"])
    base["bench_order"] = _normalize_bench_order(raw.get("bench_order"))
    base["target_minutes"] = _normalize_target_minutes(raw.get("target_minutes"))
    base["sub_policy"] = _pick_str(raw.get("sub_policy"), ALLOWED_SUB_POLICY, ROTATION_DEFAULTS["sub_policy"])
    base["fatigue_policy"] = _pick_str(
        raw.get("fatigue_policy"), ALLOWED_FATIGUE_POLICY, ROTATION_DEFAULTS["fatigue_policy"]
    )
    base["foul_policy"] = _pick_str(raw.get("foul_policy"), ALLOWED_FOUL_POLICY, ROTATION_DEFAULTS["foul_policy"])
    base["clutch_policy"] = _pick_str(
        raw.get("clutch_policy"), ALLOWED_CLUTCH_POLICY, ROTATION_DEFAULTS["clutch_policy"]
    )
    return base


def _normalize_usage_policy(raw: Any) -> Dict[str, str]:
    out = dict(USAGE_POLICY_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    out["priority"] = _pick_str(raw.get("priority"), ALLOWED_USAGE_PRIORITY, out["priority"])
    out["evaluation_focus"] = _pick_str(
        raw.get("evaluation_focus"), ALLOWED_EVALUATION_FOCUS, out["evaluation_focus"]
    )
    out["form_weight"] = _pick_str(raw.get("form_weight"), ALLOWED_FORM_WEIGHT, out["form_weight"])
    out["age_balance"] = _pick_str(raw.get("age_balance"), ALLOWED_AGE_BALANCE, out["age_balance"])
    out["injury_care"] = _pick_str(raw.get("injury_care"), ALLOWED_INJURY_CARE, out["injury_care"])
    out["schedule_care"] = _pick_str(raw.get("schedule_care"), ALLOWED_SCHEDULE_CARE, out["schedule_care"])
    out["foreign_player_usage"] = _pick_str(
        raw.get("foreign_player_usage"), ALLOWED_FOREIGN_USAGE, out["foreign_player_usage"]
    )
    return out


def _normalize_playbook(raw: Any) -> Dict[str, str]:
    out = dict(PLAYBOOK_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for key in PLAYBOOK_DEFAULTS:
        out[key] = _pick_str(raw.get(key), ALLOWED_PLAYBOOK_LEVEL, out[key])
    return out


def _normalize_roles(raw: Any, valid_player_ids: Optional[AbstractSet[int]] = None) -> Dict[str, Dict[str, str]]:
    """
    valid_player_ids が与えられたとき、ロスター外のキーは捨てる。
    """
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for pk, val in raw.items():
        sid = str(pk).strip()
        pid = _safe_int_pid(sid)
        if pid is None:
            continue
        if valid_player_ids is not None and pid not in valid_player_ids:
            continue
        if not isinstance(val, dict):
            row = dict(ROLE_DEFAULTS)
        else:
            row = dict(ROLE_DEFAULTS)
            row["main_role"] = _pick_str(val.get("main_role"), ALLOWED_MAIN_ROLE, row["main_role"])
            row["offense_involvement"] = _pick_str(
                val.get("offense_involvement"), ALLOWED_INVOLVEMENT, row["offense_involvement"]
            )
            row["shot_priority"] = _pick_str(val.get("shot_priority"), ALLOWED_SHOT_PRIORITY, row["shot_priority"])
            row["clutch_priority"] = _pick_str(
                val.get("clutch_priority"), ALLOWED_CLUTCH_PRIORITY, row["clutch_priority"]
            )
            row["playmaking_role"] = _pick_str(
                val.get("playmaking_role"), ALLOWED_PLAYMAKING_ROLE, row["playmaking_role"]
            )
            row["defense_assignment"] = _pick_str(
                val.get("defense_assignment"), ALLOWED_DEFENSE_ASSIGNMENT, row["defense_assignment"]
            )
        out[str(pid)] = row
    return out


def normalize_team_tactics(raw: Any, valid_player_ids: Optional[AbstractSet[int]] = None) -> Dict[str, Any]:
    """欠損・不正値を標準で埋めた tactics dict を返す（新しい dict）。"""
    if not isinstance(raw, dict):
        return get_default_team_tactics()
    ver = raw.get("version")
    try:
        v = int(ver)
    except (TypeError, ValueError):
        v = 0
    if v < 1 or v > TACTICS_SCHEMA_VERSION:
        v = TACTICS_SCHEMA_VERSION
    return {
        "version": TACTICS_SCHEMA_VERSION,
        "team_strategy": _normalize_team_strategy(raw.get("team_strategy")),
        "rotation": _normalize_rotation(raw.get("rotation")),
        "usage_policy": _normalize_usage_policy(raw.get("usage_policy")),
        "roles": _normalize_roles(raw.get("roles"), valid_player_ids=valid_player_ids),
        "playbook": _normalize_playbook(raw.get("playbook")),
    }


def _roster_player_ids(team: Any) -> Set[int]:
    ids: Set[int] = set()
    players = getattr(team, "players", None) or []
    for p in players:
        pid = getattr(p, "player_id", None)
        try:
            if pid is not None:
                ids.add(int(pid))
        except (TypeError, ValueError):
            continue
    return ids


def collect_tactics_starter_players(team: Any, active_players: List[Any]) -> Optional[List[Any]]:
    """
    rotation.starters が PG〜C すべて埋まり、アクティブに存在し、選手IDが5人とも異なるときだけ
    その順の Player リストを返す。それ以外は None（呼び出し側でアルゴリズム先発へフォールバック）。
    """
    raw = getattr(team, "team_tactics", None)
    if not isinstance(raw, dict):
        return None
    rot = raw.get("rotation")
    if not isinstance(rot, dict):
        return None
    norm = _normalize_starters(rot.get("starters"))
    _dedupe_starters_inplace(norm)

    by_id: Dict[int, Any] = {}
    for p in active_players:
        if p is None:
            continue
        pid = getattr(p, "player_id", None)
        if pid is None:
            continue
        try:
            by_id[int(pid)] = p
        except (TypeError, ValueError):
            continue

    lineup: List[Any] = []
    seen: Set[int] = set()
    for pos in STARTER_POSITIONS:
        pid = norm.get(pos)
        if pid is None:
            return None
        if pid in seen:
            return None
        p = by_id.get(int(pid))
        if p is None:
            return None
        lineup.append(p)
        seen.add(pid)
    return lineup


def get_rotation_target_minutes_by_player_id(team: Any) -> Dict[int, float]:
    """rotation.target_minutes を player_id -> 分 に正規化（試合オーバーレイ用。軽量読み取り）。"""
    raw = getattr(team, "team_tactics", None)
    if not isinstance(raw, dict):
        return {}
    rot = raw.get("rotation")
    if not isinstance(rot, dict):
        return {}
    raw_map = _normalize_target_minutes(rot.get("target_minutes"))
    out: Dict[int, float] = {}
    for k, v in raw_map.items():
        pid = _safe_int_pid(k)
        if pid is None:
            continue
        out[pid] = float(v)
    return out


def get_rotation_bench_order_player_ids(team: Any) -> List[int]:
    """rotation.bench_order を正規化した ID 列（Team.bench_order が空のときの控え優先のフォールバック用）。"""
    raw = getattr(team, "team_tactics", None)
    if not isinstance(raw, dict):
        return []
    rot = raw.get("rotation")
    if not isinstance(rot, dict):
        return []
    return _normalize_bench_order(rot.get("bench_order"))


def ensure_team_tactics_on_team(team: Any) -> None:
    """Team に team_tactics を必ず dict で載せ、内容を正規化する（インプレース）。"""
    raw = getattr(team, "team_tactics", None)
    if not isinstance(raw, dict):
        raw = {}
    valid = _roster_player_ids(team)
    normalized = normalize_team_tactics(raw, valid_player_ids=valid if valid else None)
    setattr(team, "team_tactics", normalized)


def get_safe_team_tactics(team: Any) -> Dict[str, Any]:
    """読み取り専用用途。正規化コピーを返す。"""
    ensure_team_tactics_on_team(team)
    return dict(getattr(team, "team_tactics", {}) or {})