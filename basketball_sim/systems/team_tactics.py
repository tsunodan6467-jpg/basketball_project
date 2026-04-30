"""
チーム戦術設定。

Phase A: 永続化・正規化・メニュー。
Phase B: rotation（先発5人・控え順・目標分数）を試合ローテへ弱く接続（詳細は Match / RotationSystem）。
"""

from __future__ import annotations

from typing import AbstractSet, Any, Dict, List, Optional, Set, Tuple

from basketball_sim.models.reg_slot import RegSlot
from basketball_sim.systems.competition_rules import normalize_competition_type
from basketball_sim.systems.japan_regulation import player_regulation_bucket_from_rule

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

# プレイスタイル用プリセット正典（v1）。ここでは dict のみ。apply / UI / preset_meta 更新は別タスク。
# v1 範囲: Team.strategy + team_strategy + playbook のみ（coach_style / Team.usage_policy / roles は含めない）。
PLAYSTYLE_PRESET_DEFS: Dict[str, Dict[str, Any]] = {
    "balanced_v1": {
        "label_ja": "バランス型",
        "team": {"strategy": "balanced"},
        "team_strategy": dict(TEAM_STRATEGY_DEFAULTS),
        "playbook": dict(PLAYBOOK_DEFAULTS),
    },
    "run_and_gun_3p_v1": {
        "label_ja": "ラン＆ガン3P型",
        "team": {"strategy": "run_and_gun"},
        "team_strategy": {
            "offense_tempo": "fast",
            "offense_style": "three_point",
            "offense_creation": "ball_move",
            "defense_style": "balanced",
            "rebound_style": "get_back",
            "transition_style": "push",
        },
        "playbook": {
            "pick_and_roll": "standard",
            "spain_pick_and_roll": "standard",
            "handoff": "high",
            "off_ball_screen": "high",
            "post_up": "low",
            "transition": "high",
        },
    },
    "defense_first_v1": {
        "label_ja": "堅守型",
        "team": {"strategy": "defense"},
        "team_strategy": {
            "offense_tempo": "slow",
            "offense_style": "inside",
            "offense_creation": "pick_and_roll",
            "defense_style": "protect_paint",
            "rebound_style": "get_back",
            "transition_style": "half_court",
        },
        "playbook": {
            "pick_and_roll": "standard",
            "spain_pick_and_roll": "standard",
            "handoff": "low",
            "off_ball_screen": "standard",
            "post_up": "standard",
            "transition": "low",
        },
    },
}

# ローテーション用プリセット正典（v1）。dict のみ。apply / UI / preset_meta は別タスク。
# v1: Team.usage_policy + usage_policy + rotation。先発/6th/ベンチ・roles は含めない。rotation.starters は {} 固定。
ROTATION_PRESET_DEFS: Dict[str, Dict[str, Any]] = {
    "balanced_v1": {
        "label_ja": "バランス型",
        "team": {"usage_policy": "balanced"},
        "usage_policy": dict(USAGE_POLICY_DEFAULTS),
        "rotation": {**dict(ROTATION_DEFAULTS), "starters": {}},
    },
    "win_now_v1": {
        "label_ja": "勝利優先型",
        "team": {"usage_policy": "win_now"},
        "usage_policy": {
            "priority": "win",
            "evaluation_focus": "overall",
            "form_weight": "skill",
            "age_balance": "veteran",
            "injury_care": "standard",
            "schedule_care": "win",
            "foreign_player_usage": "stars",
        },
        "rotation": {
            **dict(ROTATION_DEFAULTS),
            "starters": {},
            "sub_policy": "starters_long",
            "fatigue_policy": "push",
            "foul_policy": "ride",
            "clutch_policy": "stars",
        },
    },
    "development_v1": {
        "label_ja": "育成優先型",
        "team": {"usage_policy": "development"},
        "usage_policy": {
            "priority": "development",
            "evaluation_focus": "potential",
            "form_weight": "high",
            "age_balance": "youth",
            "injury_care": "high",
            "schedule_care": "rest",
            "foreign_player_usage": "balanced",
        },
        "rotation": {
            **dict(ROTATION_DEFAULTS),
            "starters": {},
            "sub_policy": "youth_dev",
            "fatigue_policy": "strict",
            "foul_policy": "early_pull",
            "clutch_policy": "hot_hand",
        },
    },
    "condition_care_v1": {
        "label_ja": "コンディション重視型",
        "team": {"usage_policy": "balanced"},
        "usage_policy": {
            "priority": "balanced",
            "evaluation_focus": "overall",
            "form_weight": "high",
            "age_balance": "balanced",
            "injury_care": "high",
            "schedule_care": "rest",
            "foreign_player_usage": "balanced",
        },
        "rotation": {
            **dict(ROTATION_DEFAULTS),
            "starters": {},
            "sub_policy": "standard",
            "fatigue_policy": "strict",
            "foul_policy": "standard",
            "clutch_policy": "hot_hand",
        },
    },
}

ALLOWED_PLAYBOOK_LEVEL = frozenset({"low", "standard", "high"})

# team_tactics["preset_meta"]["version"] はプリセット表示メタ用（TACTICS_SCHEMA_VERSION とは別）
PRESET_META_DEFAULT_V1: Dict[str, Any] = {
    "version": 1,
    "playstyle_preset_id": None,
    "rotation_preset_id": None,
}

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

# 役割詳細「参考役割」コンボ用（内部キー main_role → 日本語）。表示タグの主役は auto_role_tag。ALLOWED_MAIN_ROLE + none
MAIN_ROLE_COMBO_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("none", "未設定"),
    ("ace", "エース"),
    ("second_scorer", "セカンドスコアラー"),
    ("playmaker", "司令塔"),
    ("shooter", "シューター"),
    ("post_scorer", "ポスト得点役"),
    ("defense_ace", "守備エース"),
    ("rebounder", "リバウンド役"),
    ("sixth_man", "シックスマン"),
    ("energy", "エナジー役"),
)
_MAIN_ROLE_JA_BY_KEY: Dict[str, str] = {a: b for a, b in MAIN_ROLE_COMBO_OPTIONS}


def japanese_label_for_main_role_key(key: Optional[str]) -> Optional[str]:
    """
    main_role（参考役割）内部キー → 日本語。none / 空 / 不明は None。
    人事/GM の行末「タグ:」表示の主役は自動役割タグ（本関数は互換・他用途向けに残す）。
    """
    if not key or key == "none":
        return None
    return _MAIN_ROLE_JA_BY_KEY.get(key)
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
        "preset_meta": dict(PRESET_META_DEFAULT_V1),
    }


def _preset_meta_id_or_none(value: Any) -> Optional[str]:
    """プリセット ID: 非空 str のみ通し、それ以外は None。"""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    return None


def _normalize_preset_meta(raw: Any) -> Dict[str, Any]:
    """
    team_tactics['preset_meta']（表示用メタの入れ物）。

    トップレベルの team_tactics['version']（TACTICS_SCHEMA_VERSION）とは無関係な
    サブスキーマ版を raw['version'] として持つ（キー名は履歴都合で同名だが別物）。
    """
    if not isinstance(raw, dict):
        return dict(PRESET_META_DEFAULT_V1)
    try:
        meta_ver = int(raw.get("version", 1))
        if meta_ver < 1:
            meta_ver = 1
    except (TypeError, ValueError):
        meta_ver = 1
    return {
        "version": meta_ver,
        "playstyle_preset_id": _preset_meta_id_or_none(raw.get("playstyle_preset_id")),
        "rotation_preset_id": _preset_meta_id_or_none(raw.get("rotation_preset_id")),
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
        "preset_meta": _normalize_preset_meta(raw.get("preset_meta")),
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


def get_normalized_rotation_starters_map(team: Any) -> Dict[str, Optional[int]]:
    """`rotation.starters` を PG〜C で正規化（部分指定可）。試合先発の差し替え判定用。"""
    ensure_team_tactics_on_team(team)
    tact = getattr(team, "team_tactics", None)
    if not isinstance(tact, dict):
        return {pos: None for pos in STARTER_POSITIONS}
    rot = tact.get("rotation")
    if not isinstance(rot, dict):
        return {pos: None for pos in STARTER_POSITIONS}
    norm = _normalize_starters(rot.get("starters"))
    _dedupe_starters_inplace(norm)
    return dict(norm)


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


def get_offense_tempo_pace_adjustment(team: Any) -> int:
    """
    Match._get_total_possessions 用の弱い上乗せ。team_strategy.offense_tempo のみ参照。

    slow / standard / fast を小さな整数加減に落とし、正規化不能時は 0。
    Team.strategy や coach 由来のペース補正とは独立（二重定義にしないための専用ゲート）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return 0
        tempo = str(ts.get("offense_tempo") or "standard").strip()
    except Exception:
        return 0
    if tempo == "fast":
        return 3
    if tempo == "slow":
        return -3
    return 0


def get_transition_style_pace_adjustment(team: Any, offense_strategy: str) -> int:
    """
    Match._get_total_possessions 用の極小上乗せ。team_strategy.transition_style だけ参照。
    push / half_court / situational（0）。本流の offense_tempo（±3）・練習 transition（+2）・
    run_and_gun（+10）より常に小さい T1。T2 は同方向の offense_tempo で減衰、T3 は run_and_gun+push を二重にしない。
    """
    s = str(offense_strategy or "balanced").strip()
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return 0
        style = str(ts.get("transition_style") or "situational").strip()
        tempo = str(ts.get("offense_tempo") or "standard").strip()
    except Exception:
        return 0
    if style in ("", "situational"):
        return 0
    if style == "push":
        base = 2
    elif style == "half_court":
        base = -2
    else:
        return 0
    if s == "run_and_gun" and style == "push":
        return 0
    if style == "push" and tempo == "fast":
        return int(base * 0.5)
    if style == "half_court" and tempo == "slow":
        return int(base * 0.5)
    return base


# Rotation._build_target_minutes_map: usage_policy.age_balance（T1 極小）。Team.usage_policy 本流加減より小さい
_AGE_BALANCE_YOUNG_MAX: int = 25
_AGE_BALANCE_MID_MAX: int = 32
_AGE_BALANCE_VETERAN_MIN: int = 33
_AGE_BALANCE_T1: float = 0.3
# (usage_policy, age_balance) -> 減衰係数。未登録は 0.0
_AGE_BALANCE_USAGE_DAMP: Dict[Tuple[str, str], float] = {
    ("development", "youth"): 0.3,
    ("win_now", "veteran"): 0.3,
    ("balanced", "youth"): 1.0,
    ("balanced", "veteran"): 1.0,
    ("win_now", "youth"): 0.5,
    ("development", "veteran"): 0.5,
}


def _age_balance_band(age: int) -> str:
    if age <= _AGE_BALANCE_YOUNG_MAX:
        return "young"
    if 26 <= age <= _AGE_BALANCE_MID_MAX:
        return "mid"
    if age >= _AGE_BALANCE_VETERAN_MIN:
        return "veteran"
    return "mid"


def get_age_balance_target_minutes_overlay(team: Any, usage_policy: str, age: int) -> float:
    """
    team_tactics.usage_policy.age_balance → Rotation 目標分への極小上乗せ（分）。special 系の本流の後・clamp 前用。
    balanced（age_balance）のときは 0。不明値は 0。
    """
    s = str(usage_policy or "balanced").strip()
    if s not in ("balanced", "win_now", "development"):
        s = "balanced"
    try:
        try:
            ai = int(age)
        except (TypeError, ValueError):
            return 0.0
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        ab = str(up.get("age_balance") or "balanced").strip()
    except Exception:
        return 0.0
    if ab not in ("youth", "veteran", "balanced"):
        return 0.0
    if ab == "balanced":
        return 0.0
    band = _age_balance_band(ai)
    if ab == "youth":
        if band == "young":
            base = _AGE_BALANCE_T1
        elif band == "veteran":
            base = -_AGE_BALANCE_T1
        else:
            base = 0.0
    else:  # veteran
        if band == "young":
            base = -_AGE_BALANCE_T1
        elif band == "veteran":
            base = _AGE_BALANCE_T1
        else:
            base = 0.0
    if base == 0.0:
        return 0.0
    damp = _AGE_BALANCE_USAGE_DAMP.get((s, ab), 0.0)
    return base * damp


# Rotation._build_target_minutes_map: usage_policy.schedule_care × RegSlot（v1: 同一 round 2 戦目以降のみ T1）
_SCHEDULE_CARE_T1_REST: float = 0.3
_SCHEDULE_CARE_T1_WIN: float = 0.2


def get_schedule_care_target_minutes_overlay(
    team: Any,
    reg_slot: RegSlot | None,
    competition_type: str,
) -> float:
    """
    team_tactics.usage_policy.schedule_care + RegSlot → 目標分への極小上乗せ（分）。
    regular_season かつ round_index >= 2 のときのみ。age_balance の後・clamp 前用。
    reg_slot / fatigue とは別物（dow は v1 未使用）。
    """
    if reg_slot is None:
        return 0.0
    try:
        if normalize_competition_type(competition_type) != "regular_season":
            return 0.0
    except Exception:
        return 0.0
    if int(reg_slot.round_index) < 2:
        return 0.0
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        sc = str(up.get("schedule_care") or "standard").strip()
    except Exception:
        return 0.0
    if sc not in ALLOWED_SCHEDULE_CARE:
        sc = "standard"
    if sc == "standard":
        return 0.0
    if sc == "rest":
        return -_SCHEDULE_CARE_T1_REST
    if sc == "win":
        return _SCHEDULE_CARE_T1_WIN
    return 0.0


# Rotation._find_best_substitute: usage_policy.form_weight（v1: fatigue ベースの極小。好不調スカラーは使わない）
_FORM_WEIGHT_FATIGUE_T1: float = 0.3
_FORM_WEIGHT_SKILL_REL: float = 0.5


def get_form_weight_fatigue_substitute_overlay(team: Any, fatigue: int) -> float:
    """
    team_tactics.usage_policy.form_weight → 交代候補スコアへの極小上乗せ（v1: Player.fatigue のみ参照）。

    high: 低疲労ほど＋、高疲労ほど−（中心 50）。standard は 0。
    skill: high の疲労感度を弱める（同式 × 0.5）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        fw = str(up.get("form_weight") or "standard").strip()
    except Exception:
        return 0.0
    if fw not in ("high", "standard", "skill") or fw == "standard":
        return 0.0
    try:
        f = int(fatigue)
    except (TypeError, ValueError):
        return 0.0
    f = max(0, min(100, f))
    axis = (50.0 - float(f)) / 50.0
    if fw == "high":
        return _FORM_WEIGHT_FATIGUE_T1 * axis
    return _FORM_WEIGHT_FATIGUE_T1 * _FORM_WEIGHT_SKILL_REL * axis


# Rotation._find_best_substitute: usage_policy.foreign_player_usage（v1: 合法通過候補への極小。枠数は変えない）
_FOREIGN_USAGE_T1_PREFER: float = 0.25
_FOREIGN_USAGE_T1_JP_PEN: float = -0.25
_FOREIGN_USAGE_T1_JP_BONUS: float = 0.1


def get_foreign_player_usage_substitute_overlay(
    team: Any, player: Any, on_court_rule: Dict[str, object]
) -> float:
    """
    team_tactics.usage_policy.foreign_player_usage → 交代候補スコアへ（合法通過後のみ呼ぶ想定）。

    balanced: 0。stars: regulation bucket foreign を微プラス。japan_core: foreign 微マイナス、
    それ以外（domestic / special=アジア・帰化の扱いは on_court ルールに従う）を微プラス。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        mode = str(up.get("foreign_player_usage") or "balanced").strip()
    except Exception:
        return 0.0

    if mode not in ("stars", "japan_core"):
        return 0.0

    try:
        bucket = player_regulation_bucket_from_rule(player, on_court_rule)
    except Exception:
        return 0.0

    if mode == "stars":
        if bucket == "foreign":
            return _FOREIGN_USAGE_T1_PREFER
        return 0.0
    if bucket == "foreign":
        return _FOREIGN_USAGE_T1_JP_PEN
    return _FOREIGN_USAGE_T1_JP_BONUS


# Rotation._find_best_substitute: usage_policy.evaluation_focus（v1: 合法通過候補への極小。OVR 本流は不変更）
_EVALUATION_FOCUS_T1: float = 0.25
_OFF_DEF_AXIS_CENTER: float = 60.0
_OFF_DEF_AXIS_SPREAD: float = 40.0
_POT_CAP_CENTER: float = 83.5
_POT_CAP_HALF: float = 11.5


def get_evaluation_focus_substitute_overlay(team: Any, player: Any) -> float:
    """
    team_tactics.usage_policy.evaluation_focus → 交代候補スコアへ（合法通過後のみ呼ぶ想定）。

    overall: 0。offense/defense: 属性平均を get_adjusted_attribute で 1 本式に。potential: get_potential_cap_value を疲労なしで 1 本式に。
    上乗せ幅は T1=0.25 上限（form_weight / foreign_usage と同帯未満の安全寄りで固定）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        mode = str(up.get("evaluation_focus") or "overall").strip()
    except Exception:
        return 0.0

    if mode not in ("offense", "defense", "potential"):
        return 0.0
    t1 = _EVALUATION_FOCUS_T1

    if mode == "offense":
        a = 0.0
        for k in ("shoot", "three", "drive", "passing"):
            a += float(player.get_adjusted_attribute(k))
        m = a / 4.0
        ax = (m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD
        if ax < -1.0:
            ax = -1.0
        elif ax > 1.0:
            ax = 1.0
        return t1 * ax

    if mode == "defense":
        d = float(player.get_adjusted_attribute("defense"))
        r = float(player.get_adjusted_attribute("rebound"))
        m = (d + r) / 2.0
        ax = (m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD
        if ax < -1.0:
            ax = -1.0
        elif ax > 1.0:
            ax = 1.0
        return t1 * ax

    if mode == "potential":
        try:
            cap = int(player.get_potential_cap_value())
        except Exception:
            return 0.0
        if cap < 72:
            cap = 72
        elif cap > 95:
            cap = 95
        ax = (float(cap) - _POT_CAP_CENTER) / _POT_CAP_HALF
        if ax < -1.0:
            ax = -1.0
        elif ax > 1.0:
            ax = 1.0
        return t1 * ax
    return 0.0


# Rotation._find_best_substitute: roles（v1: 個人極小。shot+inv は従来どおり合算 0.20、全体は playmaking 込みで拡張）
_ROLES_SUBSTITUTE_T1: float = 0.12
_ROLES_SI_COMBINED_ABS_MAX: float = 0.20  # shot_priority + offense_involvement のみ（第1弾互換）
_ROLES_FULL_COMBINED_ABS_MAX: float = 0.28  # 上記 + playmaking_role（過大化防止）
_ROLES_PLAYMAKING_T1: float = 0.10
_ROLES_SUBSTITUTE_OFFENSE_FOCUS_DAMP: float = 0.5


def _roles_substitute_axis_clamp(m: float) -> float:
    ax = (m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD
    if ax < -1.0:
        return -1.0
    if ax > 1.0:
        return 1.0
    return ax


def _evaluation_focus_mode_for_roles_damp(team: Any) -> str:
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return "overall"
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return "overall"
        return str(up.get("evaluation_focus") or "overall").strip()
    except Exception:
        return "overall"


def _roles_row_for_player(team: Any, player: Any) -> Dict[str, str]:
    """ロール未登録・不正時は ROLE_DEFAULTS 相当（呼び出し側で standard→0 寄与）。"""
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return dict(ROLE_DEFAULTS)
        roles = raw.get("roles")
        if not isinstance(roles, dict):
            return dict(ROLE_DEFAULTS)
        try:
            pid = int(getattr(player, "player_id", 0) or 0)
        except (TypeError, ValueError):
            return dict(ROLE_DEFAULTS)
        if pid <= 0:
            return dict(ROLE_DEFAULTS)
        row = roles.get(str(pid))
        if isinstance(row, dict) and row:
            out = dict(ROLE_DEFAULTS)
            out["shot_priority"] = _pick_str(
                row.get("shot_priority"), ALLOWED_SHOT_PRIORITY, out["shot_priority"]
            )
            out["offense_involvement"] = _pick_str(
                row.get("offense_involvement"), ALLOWED_INVOLVEMENT, out["offense_involvement"]
            )
            out["playmaking_role"] = _pick_str(
                row.get("playmaking_role"), ALLOWED_PLAYMAKING_ROLE, out["playmaking_role"]
            )
            return out
    except Exception:
        pass
    return dict(ROLE_DEFAULTS)


def _compute_roles_substitute_overlays(team: Any, player: Any) -> Tuple[float, float, float]:
    """
    shot_priority / offense_involvement / playmaking_role を算出し、
    evaluation_focus==offense 時は共通 damp、shot+inv は従来どおり |s|+|i|≤0.20、
    最後に 3 項目合算で |s|+|i|+|p|≤FULL_MAX を 1 箇所でクリップ。
    """
    try:
        row = _roles_row_for_player(team, player)
        sp = row.get("shot_priority", ROLE_DEFAULTS["shot_priority"])
        oi = row.get("offense_involvement", ROLE_DEFAULTS["offense_involvement"])
        pm = row.get("playmaking_role", ROLE_DEFAULTS["playmaking_role"])
        if sp not in ALLOWED_SHOT_PRIORITY:
            sp = ROLE_DEFAULTS["shot_priority"]
        if oi not in ALLOWED_INVOLVEMENT:
            oi = ROLE_DEFAULTS["offense_involvement"]
        if pm not in ALLOWED_PLAYMAKING_ROLE:
            pm = ROLE_DEFAULTS["playmaking_role"]

        sh = float(player.get_adjusted_attribute("shoot"))
        th = float(player.get_adjusted_attribute("three"))
        dr = float(player.get_adjusted_attribute("drive"))
        pa = float(player.get_adjusted_attribute("passing"))
    except Exception:
        return (0.0, 0.0, 0.0)

    t1 = _ROLES_SUBSTITUTE_T1
    t1_pm = _ROLES_PLAYMAKING_T1
    shot_raw = 0.0
    if sp == "aggressive":
        m_sh = (sh + th + dr) / 3.0
        shot_raw = t1 * _roles_substitute_axis_clamp(m_sh)
    elif sp == "passive":
        m_sh = (sh + th + dr) / 3.0
        shot_raw = -t1 * _roles_substitute_axis_clamp(m_sh)

    inv_raw = 0.0
    if oi == "high":
        m_inv = (2.0 * pa + dr) / 3.0
        inv_raw = t1 * _roles_substitute_axis_clamp(m_inv)
    elif oi == "low":
        m_inv = (2.0 * pa + dr) / 3.0
        inv_raw = -t1 * _roles_substitute_axis_clamp(m_inv)

    pm_raw = 0.0
    if pm == "primary":
        m_pm = (3.0 * pa + dr) / 4.0
        pm_raw = t1_pm * _roles_substitute_axis_clamp(m_pm)
    elif pm == "minimal":
        m_pm = (3.0 * pa + dr) / 4.0
        pm_raw = -t1_pm * _roles_substitute_axis_clamp(m_pm)

    if shot_raw > t1:
        shot_raw = t1
    elif shot_raw < -t1:
        shot_raw = -t1
    if inv_raw > t1:
        inv_raw = t1
    elif inv_raw < -t1:
        inv_raw = -t1
    if pm_raw > t1_pm:
        pm_raw = t1_pm
    elif pm_raw < -t1_pm:
        pm_raw = -t1_pm

    damp = (
        _ROLES_SUBSTITUTE_OFFENSE_FOCUS_DAMP
        if _evaluation_focus_mode_for_roles_damp(team) == "offense"
        else 1.0
    )
    shot_raw *= damp
    inv_raw *= damp
    pm_raw *= damp

    si = abs(shot_raw) + abs(inv_raw)
    if si > _ROLES_SI_COMBINED_ABS_MAX and si > 0.0:
        factor_si = _ROLES_SI_COMBINED_ABS_MAX / si
        shot_raw *= factor_si
        inv_raw *= factor_si

    combined = abs(shot_raw) + abs(inv_raw) + abs(pm_raw)
    if combined > _ROLES_FULL_COMBINED_ABS_MAX and combined > 0.0:
        factor_all = _ROLES_FULL_COMBINED_ABS_MAX / combined
        shot_raw *= factor_all
        inv_raw *= factor_all
        pm_raw *= factor_all

    return (shot_raw, inv_raw, pm_raw)


def get_roles_shot_priority_substitute_overlay(team: Any, player: Any) -> float:
    """
    team_tactics.roles[pid].shot_priority → 交代候補スコアへ（合法通過後のみ想定）。

    aggressive: (shoot+three+drive)/3 を軸に高めを微プラス。passive: 同軸の逆方向。standard: 0。
    |overlay|≤0.12、offense_involvement との合算 |a|+|b|≤0.20（playmaking 無効時は第1弾互換）。
    playmaking 有効時は 3 項目で追加の合算クリップあり。evaluation_focus==offense のとき共通 damp（0.5）。
    """
    return _compute_roles_substitute_overlays(team, player)[0]


def get_roles_offense_involvement_substitute_overlay(team: Any, player: Any) -> float:
    """
    team_tactics.roles[pid].offense_involvement → 交代候補スコアへ（合法通過後のみ想定）。

    high: (2*passing+drive)/3 を軸に高めを微プラス。low: 逆方向。standard: 0。
    クリップ・damp は get_roles_shot_priority_substitute_overlay と同一内部で統一。
    """
    return _compute_roles_substitute_overlays(team, player)[1]


def get_roles_playmaking_role_substitute_overlay(team: Any, player: Any) -> float:
    """
    team_tactics.roles[pid].playmaking_role → 交代候補スコアへ（合法通過後のみ想定）。

    「配球役らしさ」: (3*passing+drive)/4 を軸に primary は微プラス、minimal は逆方向、secondary は 0。
    |overlay|≤0.10。shot / offense_involvement より弱い T1。roles 全体合算は FULL 上限で抑制。
    evaluation_focus==offense 時は shot / involvement と同じ共通 damp。
    """
    return _compute_roles_substitute_overlays(team, player)[2]


# Rotation._can_sub_out: rotation.sub_policy（v1: 必要スタント possession 数へ最大 ±1 のみ加算）
def get_sub_policy_sub_out_modifier(team: Any, player: Any, *, roster_rank: int = 99) -> float:
    """
    team_tactics.rotation.sub_policy → _can_sub_out の実効 min stint（possession）への加算。

    返値は {-1.0, 0.0, 1.0} のみ（T1 を possession 1 本に量子化した v1。standard は常に 0）。
    roster_rank は RotationSystem._get_rank_map と同じ（0 が最上位）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        rot = raw.get("rotation")
        if not isinstance(rot, dict):
            return 0.0
        mode = _pick_str(rot.get("sub_policy"), ALLOWED_SUB_POLICY, ROTATION_DEFAULTS["sub_policy"])
    except Exception:
        return 0.0

    if mode == "standard":
        return 0.0

    if mode == "starters_long":
        if roster_rank <= 3:
            return 1.0
        return 0.0

    if mode == "bench_deep":
        if roster_rank <= 3:
            return -1.0
        return 0.0

    if mode == "youth_dev":
        try:
            age = int(getattr(player, "age", 26))
        except (TypeError, ValueError):
            age = 26
        if age <= 23:
            return 1.0
        if age >= 31:
            return -1.0
        return 0.0

    return 0.0


def get_rotation_foul_policy(team: Any) -> str:
    """
    team_tactics.rotation.foul_policy → early_pull / standard / ride。
    不正・欠損は standard（ROTATION_DEFAULTS）。
    RotationSystem の foul トラブル OUT 補正などで使用。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return str(ROTATION_DEFAULTS["foul_policy"])
        rot = raw.get("rotation")
        if not isinstance(rot, dict):
            return str(ROTATION_DEFAULTS["foul_policy"])
        return str(
            _pick_str(rot.get("foul_policy"), ALLOWED_FOUL_POLICY, ROTATION_DEFAULTS["foul_policy"])
        )
    except Exception:
        return str(ROTATION_DEFAULTS["foul_policy"])


def get_roles_defense_assignment_sub_out_modifier(team: Any, player: Any) -> int:
    """
    team_tactics.roles[pid].defense_assignment → _can_sub_out の実効 min stint への加算（整数のみ）。

    stopper: +1。light: -1。standard / 欠損 / 不正: 0。Rotation 側で sub_policy 補正と合算し clamp する想定。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0
        roles = raw.get("roles")
        if not isinstance(roles, dict):
            return 0
        try:
            pid = int(getattr(player, "player_id", 0) or 0)
        except (TypeError, ValueError):
            return 0
        if pid <= 0:
            return 0
        row = roles.get(str(pid))
        if not isinstance(row, dict) or not row:
            return 0
        val = _pick_str(
            row.get("defense_assignment"), ALLOWED_DEFENSE_ASSIGNMENT, ROLE_DEFAULTS["defense_assignment"]
        )
    except Exception:
        return 0
    if val not in ALLOWED_DEFENSE_ASSIGNMENT or val == ROLE_DEFAULTS["defense_assignment"]:
        return 0
    if val == "stopper":
        return 1
    if val == "light":
        return -1
    return 0


# Rotation._can_sub_in: rotation.fatigue_policy（v1: 再投入クールダウン possession に最大 ±1）
_FATIGUE_POLICY_SUB_IN_STRICT_THRESHOLD: int = 50


def get_fatigue_policy_sub_in_cooldown_adjustment(team: Any, fatigue: int) -> int:
    """
    team_tactics.rotation.fatigue_policy → _can_sub_in の実効クールダウンへの加算（possession 数）。

    返値は {-1, 0, 1} のみ。form_weight（IN 候補スコア）とは別軸で、再投入の許可タイミングのみに効く。
    - standard: 常に 0
    - strict: fatigue が閾値以上なら +1（もう少し休ませる）
    - push: -1（多少早い再投入。高疲労でも最大 -1 に留める v1）
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0
        rot = raw.get("rotation")
        if not isinstance(rot, dict):
            return 0
        mode = _pick_str(
            rot.get("fatigue_policy"), ALLOWED_FATIGUE_POLICY, ROTATION_DEFAULTS["fatigue_policy"]
        )
    except Exception:
        return 0

    if mode == "standard":
        return 0
    try:
        f = int(fatigue)
    except (TypeError, ValueError):
        f = 0
    f = max(0, min(100, f))

    if mode == "strict":
        return 1 if f >= _FATIGUE_POLICY_SUB_IN_STRICT_THRESHOLD else 0
    if mode == "push":
        return -1
    return 0


# Rotation._find_best_substitute: rotation.clutch_policy（終盤のみ。evaluation_focus 以下の T1）
_CLUTCH_POLICY_T1: float = 0.22


def get_clutch_policy_substitute_overlay(
    team: Any,
    player: Any,
    is_late: bool,
    is_closing: bool,
    *,
    roster_rank: int = 99,
) -> float:
    """
    team_tactics.rotation.clutch_policy → 交代候補スコアへ（合法通過後のみ想定）。

    is_late / is_closing のいずれか真のときだけ非ゼロ。本流の終盤 rank 加点は変更せず極小オーバーレイ。
    roster_rank は RotationSystem._get_rank_map と同じ定義（0 が最上位）。
    """
    if not is_late and not is_closing:
        return 0.0
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        rot = raw.get("rotation")
        if not isinstance(rot, dict):
            return 0.0
        mode = _pick_str(
            rot.get("clutch_policy"), ALLOWED_CLUTCH_POLICY, ROTATION_DEFAULTS["clutch_policy"]
        )
    except Exception:
        return 0.0

    t1 = _CLUTCH_POLICY_T1

    def _clamp_ax(x: float) -> float:
        if x < -1.0:
            return -1.0
        if x > 1.0:
            return 1.0
        return x

    if mode == "stars":
        try:
            ovr = float(player.get_effective_ovr())
        except Exception:
            ovr = 60.0
        ax_ovr = _clamp_ax((ovr - 66.0) / 18.0)
        ax_rank = _clamp_ax((4.0 - float(roster_rank)) / 4.0)
        ax = 0.55 * ax_ovr + 0.45 * ax_rank
        return t1 * _clamp_ax(ax)

    if mode == "offense":
        a = 0.0
        for k in ("shoot", "three", "drive", "passing"):
            a += float(player.get_adjusted_attribute(k))
        m = a / 4.0
        ax = _clamp_ax((m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD)
        return t1 * ax

    if mode == "defense":
        d = float(player.get_adjusted_attribute("defense"))
        r = float(player.get_adjusted_attribute("rebound"))
        m = (d + r) / 2.0
        ax = _clamp_ax((m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD)
        return t1 * ax

    if mode == "hot_hand":
        sh = float(player.get_adjusted_attribute("shoot"))
        th = float(player.get_adjusted_attribute("three"))
        dr = float(player.get_adjusted_attribute("drive"))
        pa = float(player.get_adjusted_attribute("passing"))
        m = 0.38 * sh + 0.38 * th + 0.12 * dr + 0.12 * pa
        ax = _clamp_ax((m - _OFF_DEF_AXIS_CENTER) / _OFF_DEF_AXIS_SPREAD)
        return t1 * ax

    return 0.0


# Rotation._find_best_substitute: roles.clutch_priority（終盤のみ。clutch_policy より弱い T1）
_ROLES_CLUTCH_PRIORITY_T1: float = 0.10
_ROLES_CLUTCH_SHOOTER_MULTIPLIER_GO_TO: float = 1.06
_ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD: float = 1.00
_ROLES_CLUTCH_SHOOTER_MULTIPLIER_LIMITED: float = 0.94
_ROLES_DEFENSE_EVENT_MULTIPLIER_STOPPER: float = 1.05
_ROLES_DEFENSE_EVENT_MULTIPLIER_STANDARD: float = 1.00
_ROLES_DEFENSE_EVENT_MULTIPLIER_LIGHT: float = 0.96
_ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_STOPPER: float = 1.03
_ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_STANDARD: float = 1.00
_ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_LIGHT: float = 0.97


def get_roles_clutch_priority_substitute_overlay(
    team: Any, player: Any, is_late: bool, is_closing: bool
) -> float:
    """
    team_tactics.roles[pid].clutch_priority → 交代候補スコアへ（合法通過後のみ想定）。

    is_late / is_closing のいずれか真のときだけ。go_to: 微プラス。limited: 微マイナス。standard: 0。
    能力の再定義はせず、チームの rotation.clutch_policy を上書きしない微調整。|overlay|≤0.10（clutch_policy 0.22 未満）。
    """
    if not is_late and not is_closing:
        return 0.0
    t1 = _ROLES_CLUTCH_PRIORITY_T1
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        roles = raw.get("roles")
        if not isinstance(roles, dict):
            return 0.0
        try:
            pid = int(getattr(player, "player_id", 0) or 0)
        except (TypeError, ValueError):
            return 0.0
        if pid <= 0:
            return 0.0
        row = roles.get(str(pid))
        if not isinstance(row, dict) or not row:
            return 0.0
        cp = _pick_str(
            row.get("clutch_priority"), ALLOWED_CLUTCH_PRIORITY, ROLE_DEFAULTS["clutch_priority"]
        )
    except Exception:
        return 0.0
    if cp not in ALLOWED_CLUTCH_PRIORITY or cp == ROLE_DEFAULTS["clutch_priority"]:
        return 0.0
    if cp == "go_to":
        return t1
    if cp == "limited":
        return -t1
    return 0.0


def get_roles_clutch_shooter_weight_multiplier(team: Any, player: Any, *, is_clutch: bool) -> float:
    """
    team_tactics.roles[pid].clutch_priority をクラッチ時のFGシューター選択重みへ極小反映する。

    - 非クラッチ時は常に 1.0
    - go_to: 1.06 / limited: 0.94 / standard・欠損・不正: 1.0
    """
    if not is_clutch:
        return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
    if player is None:
        return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
    try:
        tactics = get_safe_team_tactics(team)
        roles = tactics.get("roles")
        if not isinstance(roles, dict):
            return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
        try:
            pid = int(getattr(player, "player_id", 0) or 0)
        except (TypeError, ValueError):
            return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
        if pid <= 0:
            return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
        row = roles.get(str(pid))
        if not isinstance(row, dict):
            return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
        cp = _pick_str(
            row.get("clutch_priority"), ALLOWED_CLUTCH_PRIORITY, ROLE_DEFAULTS["clutch_priority"]
        )
    except Exception:
        return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD
    if cp == "go_to":
        return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_GO_TO
    if cp == "limited":
        return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_LIMITED
    return _ROLES_CLUTCH_SHOOTER_MULTIPLIER_STANDARD


def get_roles_defense_event_weight_multiplier(team: Any, player: Any, *, event_type: str = "steal") -> float:
    """
    team_tactics.roles[pid].defense_assignment を守備イベント記録者の重みへ極小反映する。

    - steal: stopper 1.05 / light 0.96 / standard・欠損・不正 1.00
    - block: stopper 1.03 / light 0.97 / standard・欠損・不正 1.00
    """
    et = str(event_type or "steal").strip().lower()
    if et == "block":
        mul_stopper = _ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_STOPPER
        mul_standard = _ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_STANDARD
        mul_light = _ROLES_DEFENSE_BLOCK_EVENT_MULTIPLIER_LIGHT
    else:
        mul_stopper = _ROLES_DEFENSE_EVENT_MULTIPLIER_STOPPER
        mul_standard = _ROLES_DEFENSE_EVENT_MULTIPLIER_STANDARD
        mul_light = _ROLES_DEFENSE_EVENT_MULTIPLIER_LIGHT

    if player is None:
        return mul_standard
    try:
        tactics = get_safe_team_tactics(team)
        roles = tactics.get("roles")
        if not isinstance(roles, dict):
            return mul_standard
        try:
            pid = int(getattr(player, "player_id", 0) or 0)
        except (TypeError, ValueError):
            return mul_standard
        if pid <= 0:
            return mul_standard
        row = roles.get(str(pid))
        if not isinstance(row, dict):
            return mul_standard
        da = _pick_str(
            row.get("defense_assignment"),
            ALLOWED_DEFENSE_ASSIGNMENT,
            ROLE_DEFAULTS["defense_assignment"],
        )
    except Exception:
        return mul_standard

    if da == "stopper":
        return mul_stopper
    if da == "light":
        return mul_light
    return mul_standard


# Rotation._find_best_substitute: usage_policy.injury_care（v1: fatigue 主・stamina 補助。form_weight とは別軸）
_INJURY_CARE_T1_HIGH: float = 0.25
_INJURY_CARE_T1_LOW: float = 0.10


def get_injury_care_substitute_overlay(team: Any, fatigue: int, stamina: int) -> float:
    """
    team_tactics.usage_policy.injury_care → 交代候補スコアへ（合法通過後のみ）。

    ケガ発生率ではなく起用時の慎重さ。form_weight（調子の反映度）とは役割分離し、
    疲労を主に・スタミナ素地を補助に見る 1 本式（T1 は form_weight 帯以下）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        up = raw.get("usage_policy")
        if not isinstance(up, dict):
            return 0.0
        ic = str(up.get("injury_care") or "standard").strip()
    except Exception:
        return 0.0
    if ic not in ALLOWED_INJURY_CARE or ic == "standard":
        return 0.0
    try:
        f = int(fatigue)
        s = int(stamina)
    except (TypeError, ValueError):
        return 0.0
    f = max(0, min(100, f))
    s = max(0, min(100, s))
    f_n = f / 100.0
    s_risk = (100.0 - s) / 100.0
    concern = 0.65 * f_n + 0.35 * s_risk
    if ic == "high":
        return -_INJURY_CARE_T1_HIGH * concern
    if ic == "low":
        return min(_INJURY_CARE_T1_LOW, max(-0.05, _INJURY_CARE_T1_LOW * f_n - 0.04 * s_risk))
    return 0.0


# _get_shot_mix 用: team_strategy offense_style / defense_style の T1 ベクトルにだけ掛ける体感調整（pace / assist / steal 等には不適用）。
_TEAM_STRATEGY_SHOT_MIX_SCALE: float = 1.25


def _scale_shot_mix_deltas(deltas: Tuple[float, float, float]) -> Tuple[float, float, float]:
    s = _TEAM_STRATEGY_SHOT_MIX_SCALE
    d3, d2, dsr = deltas
    return (d3 * s, d2 * s, dsr * s)


# _get_shot_mix 用: team_strategy 由来の 3/2/shot 微調整（極小）。必ず本流 offense_strategy より小さい T1 固定値で抑える。
_OFFENSE_STYLE_T1_INSIDE: Tuple[float, float, float] = (-0.02, 0.01, 0.0015)
_OFFENSE_STYLE_T1_THREE: Tuple[float, float, float] = (0.025, 0.006, 0.001)
# drive: inside より弱い 3↓/2↑/shot 極小。ペース層（tempo / 総ポゼ）には触れない
_OFFENSE_STYLE_T1_DRIVE: Tuple[float, float, float] = (-0.012, 0.006, 0.0005)
# T2: offense_strategy == offense_style のとき tactics 上乗せを減衰（20〜40% の安全域として 0.3）
_OFFENSE_STYLE_SAME_DIRECTION_DAMP: float = 0.3


def get_offense_style_shot_mix_deltas(
    team: Any, offense_strategy: str
) -> Tuple[float, float, float]:
    """
    team_tactics.team_strategy.offense_style を _get_shot_mix へ接続するための極小オーバーレイ。
    返り値: (d_three_cutoff, d_two_cutoff, d_shot_rate_adjust)

    inside / three_point / drive。balanced は 0。Team.strategy 本流を上書きせず
    T1 小ささ / 同方向減衰 / 衝突ゼロ（drive×three 戦略、drive×run_and_gun 戦略 等）。
    """
    try:
        ensure_team_tactics_on_team(team)
        raw = getattr(team, "team_tactics", None)
        if not isinstance(raw, dict):
            return (0.0, 0.0, 0.0)
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return (0.0, 0.0, 0.0)
        style = str(ts.get("offense_style") or "balanced").strip()
    except Exception:
        return (0.0, 0.0, 0.0)

    if style not in ("inside", "three_point", "drive"):
        return (0.0, 0.0, 0.0)

    s = str(offense_strategy or "balanced").strip()
    if style == "inside":
        d3, d2, dsr = _OFFENSE_STYLE_T1_INSIDE
    elif style == "three_point":
        d3, d2, dsr = _OFFENSE_STYLE_T1_THREE
    else:
        d3, d2, dsr = _OFFENSE_STYLE_T1_DRIVE

    # T3: inside × three_point 衝突
    if (s == "inside" and style == "three_point") or (s == "three_point" and style == "inside"):
        return (0.0, 0.0, 0.0)
    # T3: drive 戦術 × 外枠/速攻 戦略は意味が衝突しやすい → 0（R&G は pace 層と二重のため）
    if style == "drive" and s in ("three_point", "run_and_gun"):
        return (0.0, 0.0, 0.0)

    k = _OFFENSE_STYLE_SAME_DIRECTION_DAMP
    # T2: 同方向減衰（戦略==スタイル）
    if s == style:
        return _scale_shot_mix_deltas((d3 * k, d2 * k, dsr * k))
    # T2: drive かつ 戦略 inside（ペイント同方向）→ 減衰
    if style == "drive" and s == "inside":
        return _scale_shot_mix_deltas((d3 * k, d2 * k, dsr * k))
    # T4: balanced 等 満額; 直交は同額のまま
    return _scale_shot_mix_deltas((d3, d2, dsr))


# _get_shot_mix 守備側: team_strategy.defense_style（第3弾A: protect_paint / protect_three のみ）。T1 < Team.strategy "defense" の -0.01(shot) 等。
_DEFENSE_STYLE_T1_PROTECT_PAINT: Tuple[float, float, float] = (0.012, -0.006, -0.0035)
_DEFENSE_STYLE_T1_PROTECT_THREE: Tuple[float, float, float] = (-0.012, 0.005, -0.0025)
# T2: Team.strategy == "defense" との同方向減衰（0.2〜0.4 の安全域として 0.3）
_DEFENSE_STYLE_WITH_DEFENSE_STRAT_DAMP: float = 0.3
_PLAYBOOK_SHOT_MIX_LEVEL_DELTA: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "off_ball_screen": {
        "high": (0.0015, -0.0007, 0.0),
        "low": (-0.0008, 0.0004, 0.0),
    },
    "post_up": {
        "high": (-0.0012, 0.0016, 0.0002),
        "low": (0.0006, -0.0008, -0.0001),
    },
}
_PLAYBOOK_SHOT_MIX_THREE_MIN: float = -0.0025
_PLAYBOOK_SHOT_MIX_THREE_MAX: float = 0.0025
_PLAYBOOK_SHOT_MIX_TWO_MIN: float = -0.0025
_PLAYBOOK_SHOT_MIX_TWO_MAX: float = 0.0025
_PLAYBOOK_SHOT_MIX_RATE_MIN: float = -0.0010
_PLAYBOOK_SHOT_MIX_RATE_MAX: float = 0.0010


def get_defense_style_shot_mix_deltas(
    defense_team: Any, defense_strategy: str
) -> Tuple[float, float, float]:
    """
    team_tactics.team_strategy.defense_style を _get_shot_mix 用の極小オーバーレイ（守備チーム文脈）で返す。

    返り値: (d_three_cutoff, d_two_cutoff, d_shot_rate_adjust)
    第3弾A: protect_paint / protect_three のみ。balanced / pressure は 0。steal 等は未接続。

    攻撃の offense_style 層を壊さない: defense_style は上書きでなく上乗せ。既存の defense 戦略/コーチより小さい T1 固定 + defense 戦略と同方向時の減衰 + balanced 満額(T3 相当).
    """
    try:
        ensure_team_tactics_on_team(defense_team)
        raw = getattr(defense_team, "team_tactics", None)
        if not isinstance(raw, dict):
            return (0.0, 0.0, 0.0)
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return (0.0, 0.0, 0.0)
        style = str(ts.get("defense_style") or "balanced").strip()
    except Exception:
        return (0.0, 0.0, 0.0)

    if style not in ("protect_paint", "protect_three"):
        return (0.0, 0.0, 0.0)

    if style == "protect_paint":
        d3, d2, dsr = _DEFENSE_STYLE_T1_PROTECT_PAINT
    else:
        d3, d2, dsr = _DEFENSE_STYLE_T1_PROTECT_THREE

    s = str(defense_strategy or "balanced").strip()
    if s == "defense":
        k = _DEFENSE_STYLE_WITH_DEFENSE_STRAT_DAMP
        return _scale_shot_mix_deltas((d3 * k, d2 * k, dsr * k))
    return _scale_shot_mix_deltas((d3, d2, dsr))


def get_playbook_shot_mix_deltas(offense_team: Any) -> Tuple[float, float, float]:
    """
    team_tactics.playbook の一部キーを _get_shot_mix へ極小加算する初回接続。

    対象は off_ball_screen / post_up のみ。standard は 0、high/low のみ微調整し、
    合計値は shot_mix 層専用の安全域でクランプする。
    """
    try:
        safe = get_safe_team_tactics(offense_team)
        pb = safe.get("playbook") if isinstance(safe.get("playbook"), dict) else {}
    except Exception:
        return (0.0, 0.0, 0.0)

    d3 = 0.0
    d2 = 0.0
    dsr = 0.0
    for key, by_level in _PLAYBOOK_SHOT_MIX_LEVEL_DELTA.items():
        lv = str(pb.get(key) or "standard").strip()
        a3, a2, asr = by_level.get(lv, (0.0, 0.0, 0.0))
        d3 += float(a3)
        d2 += float(a2)
        dsr += float(asr)
    d3 = max(_PLAYBOOK_SHOT_MIX_THREE_MIN, min(_PLAYBOOK_SHOT_MIX_THREE_MAX, d3))
    d2 = max(_PLAYBOOK_SHOT_MIX_TWO_MIN, min(_PLAYBOOK_SHOT_MIX_TWO_MAX, d2))
    dsr = max(_PLAYBOOK_SHOT_MIX_RATE_MIN, min(_PLAYBOOK_SHOT_MIX_RATE_MAX, dsr))
    return (d3, d2, dsr)


# 第3弾B: pressure → _simulate_possession.steal_rate だけ。+0.010(戦略) / +0.006(コーチ) より必ず小さい
_DEFENSE_STYLE_T1_PRESSURE_STEAL: float = 0.002


def get_defense_style_steal_rate_delta(
    defense_team: Any, defense_strategy: str
) -> float:
    """
    team_tactics.team_strategy.defense_style == pressure のみ、steal_rate への極小加算。

    protect_* や balanced は 0。T2: 戦略 defense と同方向時は減衰。T3: 戦略 run_and_gun は 0（衝突避け）。
    """
    try:
        ensure_team_tactics_on_team(defense_team)
        raw = getattr(defense_team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return 0.0
        style = str(ts.get("defense_style") or "balanced").strip()
    except Exception:
        return 0.0

    if style != "pressure":
        return 0.0

    base = _DEFENSE_STYLE_T1_PRESSURE_STEAL
    s = str(defense_strategy or "balanced").strip()
    if s == "run_and_gun":
        return 0.0
    if s == "defense":
        return base * _DEFENSE_STYLE_WITH_DEFENSE_STRAT_DAMP
    return base


# 第4弾: offense_creation ball_move → _get_assist_chance だけ。strategy +0.05 等より必ず小さい
_OFFENSE_CREATION_T1_BALL_MOVE_ASSIST: float = 0.003
# 第5弾: iso は負の微加算。絶対値は ball_move より小さめ
_OFFENSE_CREATION_T1_ISO_ASSIST: float = -0.002
# 第6弾: pick_and_roll は正だが ball_move より小さい（0.0012〜0.0015 帯の中間付近）
_OFFENSE_CREATION_T1_PICK_ROLL_ASSIST: float = 0.0014
# T2: three_point / inside は既に assist を上げる → 同方向減衰（offense_style と同オーダー 0.3）
# T2b( iso ): run_and_gun / defense は既に assist を下げる → 負の同方向減衰に同定数 0.3

# 第8弾: playbook を _get_assist_chance へ初接続（極小）。offense_creation の T1 より小さく保つ。
_PLAYBOOK_ASSIST_LEVEL_DELTA: Dict[str, Dict[str, float]] = {
    "pick_and_roll": {"high": 0.0012, "low": -0.0006},
    "spain_pick_and_roll": {"high": 0.0010, "low": -0.0005},
    "handoff": {"high": 0.0010, "low": -0.0005},
    "off_ball_screen": {"high": 0.0012, "low": -0.0004},
}
_PLAYBOOK_ASSIST_DELTA_MIN: float = -0.0015
_PLAYBOOK_ASSIST_DELTA_MAX: float = 0.0030


def get_offense_creation_assist_delta(
    offense_team: Any, offense_strategy: str
) -> float:
    """
    team_tactics.team_strategy.offense_creation → _get_assist_chance 用の極小オーバーレイ。

    ball_move: 正（第4弾）。pick_and_roll: 正でより小さい（第6弾）。iso: 負（第5弾）。post は意図的 0（下の fallthrough 注記）。

    ball_move / pick_and_roll T2: 戦略 three_point / inside で減衰。iso T2b: run_and_gun / defense で減衰。
    offense_creation は1値のため各値は排他。balanced は各 T1 満額扱い。
    """
    try:
        ensure_team_tactics_on_team(offense_team)
        raw = getattr(offense_team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return 0.0
        cr = str(ts.get("offense_creation") or "ball_move").strip()
    except Exception:
        return 0.0

    s = str(offense_strategy or "balanced").strip()

    if cr == "ball_move":
        base = _OFFENSE_CREATION_T1_BALL_MOVE_ASSIST
        if s in ("three_point", "inside"):
            return base * _OFFENSE_STYLE_SAME_DIRECTION_DAMP
        return base
    if cr == "pick_and_roll":
        base = _OFFENSE_CREATION_T1_PICK_ROLL_ASSIST
        if s in ("three_point", "inside"):
            return base * _OFFENSE_STYLE_SAME_DIRECTION_DAMP
        return base
    if cr == "iso":
        base = _OFFENSE_CREATION_T1_ISO_ASSIST
        if s in ("run_and_gun", "defense"):
            return base * _OFFENSE_STYLE_SAME_DIRECTION_DAMP
        return base
    # post: 意図的に 0。ポスト主導の出方は Team.strategy inside / offense_style / ラインアップ項 / PF-C 等の
    # 既存補正に吸収されやすく、未実装の取りこぼしではない。独立デルタを入れるなら二重掛けを再設計してから。
    return 0.0


def get_playbook_assist_delta(team: Any) -> float:
    """
    team_tactics.playbook の一部キーを _get_assist_chance へ極小加算する初回接続。

    対象は pick_and_roll / spain_pick_and_roll / handoff / off_ball_screen のみ。
    standard は 0、high/low のみ微調整し、最終値は安全域でクランプする。
    """
    try:
        safe = get_safe_team_tactics(team)
        pb = safe.get("playbook") if isinstance(safe.get("playbook"), dict) else {}
    except Exception:
        return 0.0

    delta = 0.0
    for key, by_level in _PLAYBOOK_ASSIST_LEVEL_DELTA.items():
        lv = str(pb.get(key) or "standard").strip()
        delta += float(by_level.get(lv, 0.0))
    return max(_PLAYBOOK_ASSIST_DELTA_MIN, min(_PLAYBOOK_ASSIST_DELTA_MAX, delta))


# 第7弾: rebound_style → _get_offense_rebound_rate。inside +0.04 等より必ず小さい
_REBOUND_STYLE_T1_CRASH_OFFENSE: float = 0.008
_REBOUND_STYLE_T1_GET_BACK: float = -0.006
# T2: inside 戦略は既にオフェリバ寄り → crash_offense と同方向なので減衰（他詳細戦術と同オーダー 0.3）
_REBOUND_STYLE_CRASH_WITH_INSIDE_STRAT_DAMP: float = 0.3


def get_rebound_style_offense_oreb_delta(
    offense_team: Any, offense_strategy: str
) -> float:
    """
    team_tactics.team_strategy.rebound_style を攻撃チームの offense reb 率への極小オーバーレイとして返す。

    crash_offense: 正 / get_back: 負 / balanced は 0。既存 big_count / inside 本流より小さい T1。
    T2: 戦略 inside かつ crash_offense のときだけ同方向減衰。
    """
    try:
        ensure_team_tactics_on_team(offense_team)
        raw = getattr(offense_team, "team_tactics", None)
        if not isinstance(raw, dict):
            return 0.0
        ts = raw.get("team_strategy")
        if not isinstance(ts, dict):
            return 0.0
        rs = str(ts.get("rebound_style") or "balanced").strip()
    except Exception:
        return 0.0

    if rs == "balanced":
        return 0.0
    if rs == "crash_offense":
        base = _REBOUND_STYLE_T1_CRASH_OFFENSE
    elif rs == "get_back":
        return _REBOUND_STYLE_T1_GET_BACK
    else:
        return 0.0

    s = str(offense_strategy or "balanced").strip()
    if s == "inside":
        return base * _REBOUND_STYLE_CRASH_WITH_INSIDE_STRAT_DAMP
    return base


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


def apply_playstyle_preset(team: Any, preset_id: str) -> None:
    """
    PLAYSTYLE_PRESET_DEFS を Team.strategy と team_tactics（team_strategy / playbook）へ反映する。
    preset_meta / coach_style / Team.usage_policy / roles は触らない。
    """
    if preset_id not in PLAYSTYLE_PRESET_DEFS:
        raise KeyError(f"unknown playstyle preset: {preset_id!r}")
    ensure_team_tactics_on_team(team)
    defn = PLAYSTYLE_PRESET_DEFS[preset_id]
    sk = defn["team"].get("strategy")
    if sk is not None:
        setattr(team, "strategy", str(sk))
    raw = dict(getattr(team, "team_tactics", {}) or {})
    raw["team_strategy"] = dict(defn["team_strategy"])
    raw["playbook"] = dict(defn["playbook"])
    valid = _roster_player_ids(team)
    setattr(team, "team_tactics", normalize_team_tactics(raw, valid_player_ids=valid if valid else None))


def apply_playstyle_preset_with_preset_meta(team: Any, preset_id: str) -> None:
    """
    apply_playstyle_preset の後に preset_meta['playstyle_preset_id'] のみを更新し再正規化する。
    rotation_preset_id など preset_meta の他キーは維持する。未知 preset_id は apply 側で KeyError。
    """
    apply_playstyle_preset(team, preset_id)
    raw = dict(getattr(team, "team_tactics", {}) or {})
    pm = dict(raw.get("preset_meta") or {})
    pm["playstyle_preset_id"] = _preset_meta_id_or_none(preset_id)
    raw["preset_meta"] = pm
    valid = _roster_player_ids(team)
    setattr(team, "team_tactics", normalize_team_tactics(raw, valid_player_ids=valid if valid else None))


def apply_rotation_preset(team: Any, preset_id: str) -> None:
    """
    ROTATION_PRESET_DEFS を Team.usage_policy と team_tactics（usage_policy / rotation）へ反映する。
    preset_meta・Team 先発/6th/ベンチ・roles は触らない。rotation は正典どおり（starters は {} 等）。
    """
    if preset_id not in ROTATION_PRESET_DEFS:
        raise KeyError(f"unknown rotation preset: {preset_id!r}")
    ensure_team_tactics_on_team(team)
    defn = ROTATION_PRESET_DEFS[preset_id]
    uk = defn["team"].get("usage_policy")
    if uk is not None:
        if hasattr(team, "set_usage_policy") and callable(getattr(team, "set_usage_policy")):
            team.set_usage_policy(str(uk))
        else:
            setattr(team, "usage_policy", str(uk))
    raw = dict(getattr(team, "team_tactics", {}) or {})
    raw["usage_policy"] = dict(defn["usage_policy"])
    raw["rotation"] = dict(defn["rotation"])
    valid = _roster_player_ids(team)
    setattr(team, "team_tactics", normalize_team_tactics(raw, valid_player_ids=valid if valid else None))


def apply_rotation_preset_with_preset_meta(team: Any, preset_id: str) -> None:
    """
    apply_rotation_preset の後に preset_meta['rotation_preset_id'] のみを更新し再正規化する。
    playstyle_preset_id など preset_meta の他キーは維持する。未知 preset_id は apply 側で KeyError。
    """
    apply_rotation_preset(team, preset_id)
    raw = dict(getattr(team, "team_tactics", {}) or {})
    pm = dict(raw.get("preset_meta") or {})
    pm["rotation_preset_id"] = _preset_meta_id_or_none(preset_id)
    raw["preset_meta"] = pm
    valid = _roster_player_ids(team)
    setattr(team, "team_tactics", normalize_team_tactics(raw, valid_player_ids=valid if valid else None))


def _team_tactics_dict_copy(team: Any) -> Dict[str, Any]:
    cur = getattr(team, "team_tactics", None)
    return dict(cur) if isinstance(cur, dict) else {}


def get_current_playstyle_preset_state(team: Any) -> Dict[str, Any]:
    """
    preset_meta.playstyle_preset_id を基準に、Team.strategy / team_strategy / playbook が
    正規化後に正典と一致するか判定する。team を変更しない。
    """
    raw_tt = _team_tactics_dict_copy(team)
    pm = raw_tt.get("preset_meta")
    pid: Optional[str] = None
    if isinstance(pm, dict):
        pid = _preset_meta_id_or_none(pm.get("playstyle_preset_id"))
    if not pid:
        return {"preset_id": None, "label_ja": "未設定", "is_custom": False}
    if pid not in PLAYSTYLE_PRESET_DEFS:
        return {"preset_id": pid, "label_ja": "カスタム", "is_custom": True}
    valid = _roster_player_ids(team)
    vp = valid if valid else None
    norm_current = normalize_team_tactics(raw_tt, valid_player_ids=vp)
    defn = PLAYSTYLE_PRESET_DEFS[pid]
    raw_exp = get_default_team_tactics()
    raw_exp["team_strategy"] = dict(defn["team_strategy"])
    raw_exp["playbook"] = dict(defn["playbook"])
    norm_exp = normalize_team_tactics(raw_exp, valid_player_ids=vp)
    exp_sk = str(defn["team"].get("strategy", "") or "").strip()
    cur_sk = str(getattr(team, "strategy", "") or "").strip()
    if (
        cur_sk == exp_sk
        and norm_current["team_strategy"] == norm_exp["team_strategy"]
        and norm_current["playbook"] == norm_exp["playbook"]
    ):
        return {"preset_id": pid, "label_ja": str(defn.get("label_ja", pid)), "is_custom": False}
    return {"preset_id": pid, "label_ja": "カスタム", "is_custom": True}


def get_current_rotation_preset_state(team: Any) -> Dict[str, Any]:
    """
    preset_meta.rotation_preset_id を基準に、Team.usage_policy / usage_policy / rotation が
    正規化後に正典と一致するか判定する。team を変更しない。
    """
    raw_tt = _team_tactics_dict_copy(team)
    pm = raw_tt.get("preset_meta")
    pid: Optional[str] = None
    if isinstance(pm, dict):
        pid = _preset_meta_id_or_none(pm.get("rotation_preset_id"))
    if not pid:
        return {"preset_id": None, "label_ja": "未設定", "is_custom": False}
    if pid not in ROTATION_PRESET_DEFS:
        return {"preset_id": pid, "label_ja": "カスタム", "is_custom": True}
    valid = _roster_player_ids(team)
    vp = valid if valid else None
    norm_current = normalize_team_tactics(raw_tt, valid_player_ids=vp)
    defn = ROTATION_PRESET_DEFS[pid]
    raw_exp = get_default_team_tactics()
    raw_exp["usage_policy"] = dict(defn["usage_policy"])
    raw_exp["rotation"] = dict(defn["rotation"])
    norm_exp = normalize_team_tactics(raw_exp, valid_player_ids=vp)
    exp_up = str(defn["team"].get("usage_policy", "") or "").strip()
    cur_up = str(getattr(team, "usage_policy", "") or "").strip()
    if (
        cur_up == exp_up
        and norm_current["usage_policy"] == norm_exp["usage_policy"]
        and norm_current["rotation"] == norm_exp["rotation"]
    ):
        return {"preset_id": pid, "label_ja": str(defn.get("label_ja", pid)), "is_custom": False}
    return {"preset_id": pid, "label_ja": "カスタム", "is_custom": True}