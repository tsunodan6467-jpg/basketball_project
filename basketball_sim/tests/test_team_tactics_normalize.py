"""team_tactics 正規化・旧セーブ互換の最小テスト。"""

from types import SimpleNamespace

import pytest

from basketball_sim.systems.team_tactics import (
    PLAYBOOK_DEFAULTS,
    PLAYSTYLE_PRESET_DEFS,
    ROTATION_DEFAULTS,
    ROTATION_PRESET_DEFS,
    TEAM_STRATEGY_DEFAULTS,
    USAGE_POLICY_DEFAULTS,
    apply_playstyle_preset,
    apply_playstyle_preset_with_preset_meta,
    apply_rotation_preset,
    apply_rotation_preset_with_preset_meta,
    ensure_team_tactics_on_team,
    get_current_playstyle_preset_state,
    get_current_rotation_preset_state,
    get_default_team_tactics,
    normalize_team_tactics,
)


def test_rotation_preset_balanced_v1_canonical_shape():
    p = ROTATION_PRESET_DEFS["balanced_v1"]
    assert p["label_ja"] == "バランス型"
    assert p["team"] == {"usage_policy": "balanced"}
    assert set(p["usage_policy"].keys()) == set(USAGE_POLICY_DEFAULTS.keys())
    assert p["usage_policy"] == USAGE_POLICY_DEFAULTS
    assert set(p["rotation"].keys()) == set(ROTATION_DEFAULTS.keys())
    assert p["rotation"]["starters"] == {}
    assert p["rotation"]["bench_order"] == ROTATION_DEFAULTS["bench_order"]
    assert p["rotation"]["sub_policy"] == ROTATION_DEFAULTS["sub_policy"]


def test_rotation_preset_win_now_v1_canonical_shape():
    assert "win_now_v1" in ROTATION_PRESET_DEFS
    p = ROTATION_PRESET_DEFS["win_now_v1"]
    assert p["label_ja"] == "勝利優先型"
    assert p["team"] == {"usage_policy": "win_now"}
    assert set(p["usage_policy"].keys()) == set(USAGE_POLICY_DEFAULTS.keys())
    assert set(p["rotation"].keys()) == set(ROTATION_DEFAULTS.keys())
    assert p["rotation"]["starters"] == {}
    base = get_default_team_tactics()
    merged = dict(base)
    merged["usage_policy"] = dict(p["usage_policy"])
    merged["rotation"] = dict(p["rotation"])
    normalize_team_tactics(merged, valid_player_ids=set())


def test_apply_rotation_preset_win_now_v1_smoke_and_lineup_unchanged():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="balanced",
        players=[],
        team_tactics={"rotation": {"starters": {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}}},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    apply_rotation_preset(team, "win_now_v1")
    assert team.usage_policy == "win_now"
    assert team.team_tactics["usage_policy"] == ROTATION_PRESET_DEFS["win_now_v1"]["usage_policy"]
    r = team.team_tactics["rotation"]
    assert r["sub_policy"] == ROTATION_PRESET_DEFS["win_now_v1"]["rotation"]["sub_policy"]
    assert r["fatigue_policy"] == ROTATION_PRESET_DEFS["win_now_v1"]["rotation"]["fatigue_policy"]
    assert r["foul_policy"] == ROTATION_PRESET_DEFS["win_now_v1"]["rotation"]["foul_policy"]
    assert r["clutch_policy"] == ROTATION_PRESET_DEFS["win_now_v1"]["rotation"]["clutch_policy"]
    assert r["bench_order"] == ROTATION_DEFAULTS["bench_order"]
    st = team.team_tactics["rotation"]["starters"]
    assert isinstance(st, dict)
    assert all(st.get(p) is None for p in ("PG", "SG", "SF", "PF", "C"))
    assert list(team.starting_lineup) == [10, 11, 12, 13, 14]
    assert team.sixth_man_id == 20
    assert team.bench_order == [21, 22]
    normalize_team_tactics(team.team_tactics, valid_player_ids=None)


def test_apply_rotation_preset_win_now_v1_with_preset_meta_preserves_playstyle_id():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="balanced",
        players=[],
        team_tactics={},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": "defense_first_v1",
        "rotation_preset_id": None,
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_rotation_preset_with_preset_meta(team, "win_now_v1")
    assert team.usage_policy == "win_now"
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "win_now_v1"
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "defense_first_v1"


def test_get_current_rotation_preset_state_win_now_v1_custom_roundtrip():
    team = SimpleNamespace(strategy="balanced", usage_policy="balanced", players=[], team_tactics={})
    apply_rotation_preset_with_preset_meta(team, "win_now_v1")
    s = get_current_rotation_preset_state(team)
    assert s["is_custom"] is False
    assert s["label_ja"] == "勝利優先型"
    raw = dict(team.team_tactics)
    up = dict(raw["usage_policy"])
    up["priority"] = "balanced"
    raw["usage_policy"] = up
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    assert get_current_rotation_preset_state(team)["is_custom"] is True
    assert get_current_rotation_preset_state(team)["label_ja"] == "カスタム"
    apply_rotation_preset_with_preset_meta(team, "win_now_v1")
    s2 = get_current_rotation_preset_state(team)
    assert s2["is_custom"] is False
    assert s2["label_ja"] == "勝利優先型"


def test_rotation_preset_development_v1_canonical_shape():
    assert "development_v1" in ROTATION_PRESET_DEFS
    p = ROTATION_PRESET_DEFS["development_v1"]
    assert p["label_ja"] == "育成優先型"
    assert p["team"] == {"usage_policy": "development"}
    assert set(p["usage_policy"].keys()) == set(USAGE_POLICY_DEFAULTS.keys())
    assert set(p["rotation"].keys()) == set(ROTATION_DEFAULTS.keys())
    assert p["rotation"]["starters"] == {}
    base = get_default_team_tactics()
    merged = dict(base)
    merged["usage_policy"] = dict(p["usage_policy"])
    merged["rotation"] = dict(p["rotation"])
    normalize_team_tactics(merged, valid_player_ids=set())


def test_apply_rotation_preset_development_v1_smoke_and_lineup_unchanged():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="win_now",
        players=[],
        team_tactics={"rotation": {"starters": {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}}},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    apply_rotation_preset(team, "development_v1")
    assert team.usage_policy == "development"
    assert team.team_tactics["usage_policy"] == ROTATION_PRESET_DEFS["development_v1"]["usage_policy"]
    r = team.team_tactics["rotation"]
    assert r["sub_policy"] == ROTATION_PRESET_DEFS["development_v1"]["rotation"]["sub_policy"]
    assert r["fatigue_policy"] == ROTATION_PRESET_DEFS["development_v1"]["rotation"]["fatigue_policy"]
    assert r["foul_policy"] == ROTATION_PRESET_DEFS["development_v1"]["rotation"]["foul_policy"]
    assert r["clutch_policy"] == ROTATION_PRESET_DEFS["development_v1"]["rotation"]["clutch_policy"]
    assert r["bench_order"] == ROTATION_DEFAULTS["bench_order"]
    st = team.team_tactics["rotation"]["starters"]
    assert isinstance(st, dict)
    assert all(st.get(p) is None for p in ("PG", "SG", "SF", "PF", "C"))
    assert list(team.starting_lineup) == [10, 11, 12, 13, 14]
    assert team.sixth_man_id == 20
    assert team.bench_order == [21, 22]
    normalize_team_tactics(team.team_tactics, valid_player_ids=None)


def test_apply_rotation_preset_development_v1_with_preset_meta_preserves_playstyle_id():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="balanced",
        players=[],
        team_tactics={},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": "run_and_gun_3p_v1",
        "rotation_preset_id": None,
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_rotation_preset_with_preset_meta(team, "development_v1")
    assert team.usage_policy == "development"
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "development_v1"
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "run_and_gun_3p_v1"


def test_get_current_rotation_preset_state_development_v1_custom_roundtrip():
    team = SimpleNamespace(strategy="balanced", usage_policy="balanced", players=[], team_tactics={})
    apply_rotation_preset_with_preset_meta(team, "development_v1")
    s = get_current_rotation_preset_state(team)
    assert s["is_custom"] is False
    assert s["label_ja"] == "育成優先型"
    raw = dict(team.team_tactics)
    up = dict(raw["usage_policy"])
    up["priority"] = "win"
    raw["usage_policy"] = up
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    assert get_current_rotation_preset_state(team)["is_custom"] is True
    assert get_current_rotation_preset_state(team)["label_ja"] == "カスタム"
    apply_rotation_preset_with_preset_meta(team, "development_v1")
    s2 = get_current_rotation_preset_state(team)
    assert s2["is_custom"] is False
    assert s2["label_ja"] == "育成優先型"


def test_rotation_preset_condition_care_v1_canonical_shape():
    assert "condition_care_v1" in ROTATION_PRESET_DEFS
    p = ROTATION_PRESET_DEFS["condition_care_v1"]
    assert p["label_ja"] == "コンディション重視型"
    assert p["team"] == {"usage_policy": "balanced"}
    assert set(p["usage_policy"].keys()) == set(USAGE_POLICY_DEFAULTS.keys())
    assert set(p["rotation"].keys()) == set(ROTATION_DEFAULTS.keys())
    assert p["rotation"]["starters"] == {}
    assert p["usage_policy"]["injury_care"] == "high"
    assert p["usage_policy"]["schedule_care"] == "rest"
    assert p["usage_policy"]["form_weight"] == "high"
    assert p["rotation"]["sub_policy"] == "standard"
    assert p["rotation"]["fatigue_policy"] == "strict"
    assert p["rotation"]["foul_policy"] == "standard"
    assert p["rotation"]["clutch_policy"] == "hot_hand"
    base = get_default_team_tactics()
    merged = dict(base)
    merged["usage_policy"] = dict(p["usage_policy"])
    merged["rotation"] = dict(p["rotation"])
    normalize_team_tactics(merged, valid_player_ids=set())


def test_apply_rotation_preset_condition_care_v1_smoke_and_lineup_unchanged():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="win_now",
        players=[],
        team_tactics={"rotation": {"starters": {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}}},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    apply_rotation_preset(team, "condition_care_v1")
    assert team.usage_policy == "balanced"
    assert team.team_tactics["usage_policy"] == ROTATION_PRESET_DEFS["condition_care_v1"]["usage_policy"]
    r = team.team_tactics["rotation"]
    assert r["sub_policy"] == ROTATION_PRESET_DEFS["condition_care_v1"]["rotation"]["sub_policy"]
    assert r["fatigue_policy"] == ROTATION_PRESET_DEFS["condition_care_v1"]["rotation"]["fatigue_policy"]
    assert r["foul_policy"] == ROTATION_PRESET_DEFS["condition_care_v1"]["rotation"]["foul_policy"]
    assert r["clutch_policy"] == ROTATION_PRESET_DEFS["condition_care_v1"]["rotation"]["clutch_policy"]
    assert r.get("target_minutes") in ({},)
    assert r["bench_order"] == ROTATION_DEFAULTS["bench_order"]
    st = team.team_tactics["rotation"]["starters"]
    assert isinstance(st, dict)
    assert all(st.get(p) is None for p in ("PG", "SG", "SF", "PF", "C"))
    assert list(team.starting_lineup) == [10, 11, 12, 13, 14]
    assert team.sixth_man_id == 20
    assert team.bench_order == [21, 22]
    normalize_team_tactics(team.team_tactics, valid_player_ids=None)


def test_get_current_rotation_preset_state_condition_care_v1_not_custom():
    team = SimpleNamespace(strategy="balanced", usage_policy="balanced", players=[], team_tactics={})
    apply_rotation_preset_with_preset_meta(team, "condition_care_v1")
    s = get_current_rotation_preset_state(team)
    assert s["is_custom"] is False
    assert s["label_ja"] == "コンディション重視型"


def test_playstyle_preset_balanced_v1_canonical_shape():
    p = PLAYSTYLE_PRESET_DEFS["balanced_v1"]
    assert p["label_ja"] == "バランス型"
    assert p["team"] == {"strategy": "balanced"}
    assert set(p["team_strategy"].keys()) == set(TEAM_STRATEGY_DEFAULTS.keys())
    assert p["team_strategy"] == TEAM_STRATEGY_DEFAULTS
    assert set(p["playbook"].keys()) == set(PLAYBOOK_DEFAULTS.keys())
    assert p["playbook"] == PLAYBOOK_DEFAULTS


def test_playstyle_preset_run_and_gun_3p_v1_canonical_shape():
    assert "run_and_gun_3p_v1" in PLAYSTYLE_PRESET_DEFS
    p = PLAYSTYLE_PRESET_DEFS["run_and_gun_3p_v1"]
    assert p["label_ja"] == "ラン＆ガン3P型"
    assert p["team"] == {"strategy": "run_and_gun"}
    assert set(p["team_strategy"].keys()) == set(TEAM_STRATEGY_DEFAULTS.keys())
    assert set(p["playbook"].keys()) == set(PLAYBOOK_DEFAULTS.keys())
    base = get_default_team_tactics()
    merged = dict(base)
    merged["team_strategy"] = dict(p["team_strategy"])
    merged["playbook"] = dict(p["playbook"])
    normalize_team_tactics(merged, valid_player_ids=set())


def test_apply_playstyle_preset_run_and_gun_3p_v1_smoke():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    apply_playstyle_preset(team, "run_and_gun_3p_v1")
    assert team.strategy == "run_and_gun"
    assert team.team_tactics["team_strategy"] == PLAYSTYLE_PRESET_DEFS["run_and_gun_3p_v1"]["team_strategy"]
    assert team.team_tactics["playbook"] == PLAYSTYLE_PRESET_DEFS["run_and_gun_3p_v1"]["playbook"]
    assert isinstance(team.team_tactics.get("preset_meta"), dict)
    normalize_team_tactics(team.team_tactics, valid_player_ids=None)


def test_apply_playstyle_preset_run_and_gun_3p_v1_with_preset_meta_preserves_rotation_id():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": None,
        "rotation_preset_id": "balanced_v1",
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_playstyle_preset_with_preset_meta(team, "run_and_gun_3p_v1")
    assert team.strategy == "run_and_gun"
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "run_and_gun_3p_v1"
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "balanced_v1"


def test_get_current_playstyle_preset_state_run_and_gun_3p_v1_custom_roundtrip():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    apply_playstyle_preset_with_preset_meta(team, "run_and_gun_3p_v1")
    st = get_current_playstyle_preset_state(team)
    assert st["preset_id"] == "run_and_gun_3p_v1"
    assert st["is_custom"] is False
    assert st["label_ja"] == "ラン＆ガン3P型"
    raw = dict(team.team_tactics)
    ts = dict(raw["team_strategy"])
    ts["offense_tempo"] = "standard"
    raw["team_strategy"] = ts
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    st2 = get_current_playstyle_preset_state(team)
    assert st2["is_custom"] is True
    assert st2["label_ja"] == "カスタム"
    apply_playstyle_preset_with_preset_meta(team, "run_and_gun_3p_v1")
    st3 = get_current_playstyle_preset_state(team)
    assert st3["is_custom"] is False
    assert st3["label_ja"] == "ラン＆ガン3P型"


def test_playstyle_preset_defense_first_v1_canonical_shape():
    assert "defense_first_v1" in PLAYSTYLE_PRESET_DEFS
    p = PLAYSTYLE_PRESET_DEFS["defense_first_v1"]
    assert p["label_ja"] == "堅守型"
    assert p["team"] == {"strategy": "defense"}
    assert set(p["team_strategy"].keys()) == set(TEAM_STRATEGY_DEFAULTS.keys())
    assert set(p["playbook"].keys()) == set(PLAYBOOK_DEFAULTS.keys())
    base = get_default_team_tactics()
    merged = dict(base)
    merged["team_strategy"] = dict(p["team_strategy"])
    merged["playbook"] = dict(p["playbook"])
    normalize_team_tactics(merged, valid_player_ids=set())


def test_apply_playstyle_preset_defense_first_v1_smoke():
    team = SimpleNamespace(strategy="run_and_gun", players=[], team_tactics={})
    apply_playstyle_preset(team, "defense_first_v1")
    assert team.strategy == "defense"
    assert team.team_tactics["team_strategy"] == PLAYSTYLE_PRESET_DEFS["defense_first_v1"]["team_strategy"]
    assert team.team_tactics["playbook"] == PLAYSTYLE_PRESET_DEFS["defense_first_v1"]["playbook"]
    assert isinstance(team.team_tactics.get("preset_meta"), dict)
    normalize_team_tactics(team.team_tactics, valid_player_ids=None)


def test_apply_playstyle_preset_defense_first_v1_with_preset_meta_preserves_rotation_id():
    team = SimpleNamespace(strategy="balanced", players=[], team_tactics={})
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": None,
        "rotation_preset_id": "balanced_v1",
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_playstyle_preset_with_preset_meta(team, "defense_first_v1")
    assert team.strategy == "defense"
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "defense_first_v1"
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "balanced_v1"


def test_get_current_playstyle_preset_state_defense_first_v1_custom_roundtrip():
    team = SimpleNamespace(strategy="balanced", players=[], team_tactics={})
    apply_playstyle_preset_with_preset_meta(team, "defense_first_v1")
    st = get_current_playstyle_preset_state(team)
    assert st["preset_id"] == "defense_first_v1"
    assert st["is_custom"] is False
    assert st["label_ja"] == "堅守型"
    raw = dict(team.team_tactics)
    ts = dict(raw["team_strategy"])
    ts["offense_tempo"] = "standard"
    raw["team_strategy"] = ts
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    st2 = get_current_playstyle_preset_state(team)
    assert st2["is_custom"] is True
    assert st2["label_ja"] == "カスタム"
    apply_playstyle_preset_with_preset_meta(team, "defense_first_v1")
    st3 = get_current_playstyle_preset_state(team)
    assert st3["is_custom"] is False
    assert st3["label_ja"] == "堅守型"


def test_normalize_empty_returns_full_defaults():
    out = normalize_team_tactics(None)
    assert out["version"] >= 1
    assert out["team_strategy"]["offense_tempo"] == "standard"
    assert out["playbook"]["pick_and_roll"] == "standard"
    assert out["preset_meta"] == {
        "version": 1,
        "playstyle_preset_id": None,
        "rotation_preset_id": None,
    }


def test_normalize_strips_unknown_and_dedupes_starters():
    raw = {
        "version": 0,
        "team_strategy": {"offense_tempo": "nope", "offense_style": "inside"},
        "rotation": {
            "starters": {"PG": 1, "SG": 1, "SF": 2, "PF": None, "C": 3},
            "bench_order": [2, 2, 5],
            "target_minutes": {"1": 50, "2": -1},
        },
        "usage_policy": {"priority": "invalid"},
        "roles": {"1": {"main_role": "ace"}, "999": {"main_role": "ace"}},
        "playbook": {"pick_and_roll": "high"},
    }
    out = normalize_team_tactics(raw, valid_player_ids={1, 2, 3})
    assert out["team_strategy"]["offense_tempo"] == "standard"
    assert out["team_strategy"]["offense_style"] == "inside"
    assert out["rotation"]["starters"]["PG"] == 1
    assert out["rotation"]["starters"]["SG"] is None
    assert out["rotation"]["bench_order"] == [2, 5]
    assert out["rotation"]["target_minutes"]["1"] == 40.0
    assert out["rotation"]["target_minutes"]["2"] == 0.0
    assert out["usage_policy"]["priority"] == "balanced"
    assert "1" in out["roles"]
    assert "999" not in out["roles"]
    assert out["preset_meta"] == {
        "version": 1,
        "playstyle_preset_id": None,
        "rotation_preset_id": None,
    }


def test_normalize_preset_meta_roundtrip():
    raw = {
        "version": 1,
        "team_strategy": {},
        "rotation": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
        "preset_meta": {
            "version": 1,
            "playstyle_preset_id": "balanced_v1",
            "rotation_preset_id": "win_now_v1",
        },
    }
    out = normalize_team_tactics(raw, valid_player_ids=set())
    assert out["preset_meta"]["version"] == 1
    assert out["preset_meta"]["playstyle_preset_id"] == "balanced_v1"
    assert out["preset_meta"]["rotation_preset_id"] == "win_now_v1"


def test_commit_merge_preserves_preset_meta_when_key_missing():
    """
    main_menu_view._tactics_commit_payload と同趣旨のマージ:
    payload に preset_meta が無いとき、直前の tactics にあった preset_meta を載せてから normalize する。
    """
    base = normalize_team_tactics(
        {
            "version": 1,
            "team_strategy": {},
            "rotation": {},
            "usage_policy": {},
            "roles": {},
            "playbook": {},
            "preset_meta": {
                "version": 1,
                "playstyle_preset_id": "keep_me",
                "rotation_preset_id": None,
            },
        },
        valid_player_ids=set(),
    )
    stale = {k: v for k, v in base.items() if k != "preset_meta"}
    assert "preset_meta" not in stale
    merged = dict(stale)
    prev = base
    if "preset_meta" not in merged and isinstance(prev, dict) and isinstance(prev.get("preset_meta"), dict):
        merged["preset_meta"] = dict(prev["preset_meta"])
    out = normalize_team_tactics(merged, valid_player_ids=set())
    assert out["preset_meta"]["playstyle_preset_id"] == "keep_me"


def test_normalize_preset_meta_invalid_values():
    raw = {
        "version": 1,
        "team_strategy": {},
        "rotation": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
        "preset_meta": {
            "version": "x",
            "playstyle_preset_id": 123,
            "rotation_preset_id": "  ",
        },
    }
    out = normalize_team_tactics(raw, valid_player_ids=set())
    assert out["preset_meta"]["version"] == 1
    assert out["preset_meta"]["playstyle_preset_id"] is None
    assert out["preset_meta"]["rotation_preset_id"] is None


def test_ensure_team_tactics_on_team_mutates_safe():
    team = SimpleNamespace(players=[], team_tactics="bad")
    ensure_team_tactics_on_team(team)
    assert isinstance(team.team_tactics, dict)
    assert team.team_tactics["team_strategy"]["defense_style"] == "balanced"


def test_ensure_filters_roles_by_roster():
    p = SimpleNamespace(player_id=10)
    team = SimpleNamespace(players=[p], team_tactics={"roles": {"10": {"main_role": "ace"}, "99": {"main_role": "ace"}}})
    ensure_team_tactics_on_team(team)
    assert "10" in team.team_tactics["roles"]
    assert "99" not in team.team_tactics["roles"]


def test_default_has_all_playbook_keys():
    d = get_default_team_tactics()
    assert set(d["playbook"].keys()) == {
        "pick_and_roll",
        "spain_pick_and_roll",
        "handoff",
        "off_ball_screen",
        "post_up",
        "transition",
    }


def test_apply_rotation_preset_with_preset_meta_preserves_playstyle_id():
    team = SimpleNamespace(
        strategy="inside",
        usage_policy="win_now",
        players=[],
        team_tactics={},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": "balanced_v1",
        "rotation_preset_id": None,
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_rotation_preset_with_preset_meta(team, "balanced_v1")
    assert team.usage_policy == "balanced"
    assert team.team_tactics["usage_policy"] == ROTATION_PRESET_DEFS["balanced_v1"]["usage_policy"]
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "balanced_v1"
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "balanced_v1"
    assert list(team.starting_lineup) == [10, 11, 12, 13, 14]
    assert team.sixth_man_id == 20
    assert team.bench_order == [21, 22]
    st = team.team_tactics["rotation"]["starters"]
    assert all(st.get(p) is None for p in ("PG", "SG", "SF", "PF", "C"))


def test_apply_playstyle_preset_with_preset_meta_preserves_rotation_id():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    ensure_team_tactics_on_team(team)
    raw = dict(team.team_tactics)
    raw["preset_meta"] = {
        "version": 1,
        "playstyle_preset_id": None,
        "rotation_preset_id": "win_now_v1",
    }
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    apply_playstyle_preset_with_preset_meta(team, "balanced_v1")
    assert team.strategy == "balanced"
    assert team.team_tactics["team_strategy"] == PLAYSTYLE_PRESET_DEFS["balanced_v1"]["team_strategy"]
    assert team.team_tactics["playbook"] == PLAYSTYLE_PRESET_DEFS["balanced_v1"]["playbook"]
    assert team.team_tactics["preset_meta"]["playstyle_preset_id"] == "balanced_v1"
    assert team.team_tactics["preset_meta"]["rotation_preset_id"] == "win_now_v1"


def test_apply_playstyle_preset_balanced_v1_smoke():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    apply_playstyle_preset(team, "balanced_v1")
    assert team.strategy == "balanced"
    assert team.team_tactics["team_strategy"] == PLAYSTYLE_PRESET_DEFS["balanced_v1"]["team_strategy"]
    assert team.team_tactics["playbook"] == PLAYSTYLE_PRESET_DEFS["balanced_v1"]["playbook"]
    assert isinstance(team.team_tactics.get("preset_meta"), dict)


def test_apply_rotation_preset_balanced_v1_smoke_and_lineup_unchanged():
    team = SimpleNamespace(
        strategy="balanced",
        usage_policy="win_now",
        players=[],
        team_tactics={"rotation": {"starters": {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}}},
        starting_lineup=[10, 11, 12, 13, 14],
        sixth_man_id=20,
        bench_order=[21, 22],
    )
    apply_rotation_preset(team, "balanced_v1")
    assert team.usage_policy == "balanced"
    assert team.team_tactics["usage_policy"] == ROTATION_PRESET_DEFS["balanced_v1"]["usage_policy"]
    st = team.team_tactics["rotation"]["starters"]
    assert isinstance(st, dict)
    assert all(st.get(p) is None for p in ("PG", "SG", "SF", "PF", "C"))
    assert list(team.starting_lineup) == [10, 11, 12, 13, 14]
    assert team.sixth_man_id == 20
    assert team.bench_order == [21, 22]


def test_get_current_playstyle_preset_state_custom_roundtrip():
    team = SimpleNamespace(strategy="inside", players=[], team_tactics={})
    apply_playstyle_preset_with_preset_meta(team, "balanced_v1")
    st = get_current_playstyle_preset_state(team)
    assert st["preset_id"] == "balanced_v1"
    assert st["is_custom"] is False
    assert st["label_ja"] == "バランス型"
    raw = dict(team.team_tactics)
    ts = dict(raw["team_strategy"])
    ts["offense_tempo"] = "fast"
    raw["team_strategy"] = ts
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    st2 = get_current_playstyle_preset_state(team)
    assert st2["is_custom"] is True
    assert st2["label_ja"] == "カスタム"
    apply_playstyle_preset_with_preset_meta(team, "balanced_v1")
    st3 = get_current_playstyle_preset_state(team)
    assert st3["is_custom"] is False
    assert st3["label_ja"] == "バランス型"


def test_get_current_playstyle_preset_state_unknown_id():
    team = SimpleNamespace(
        strategy="balanced",
        players=[],
        team_tactics={
            "preset_meta": {"version": 1, "playstyle_preset_id": "ghost_v9", "rotation_preset_id": None},
        },
    )
    s = get_current_playstyle_preset_state(team)
    assert s["preset_id"] == "ghost_v9"
    assert s["is_custom"] is True
    assert s["label_ja"] == "カスタム"


def test_get_current_playstyle_preset_state_unset():
    team = SimpleNamespace(strategy="balanced", players=[], team_tactics={})
    ensure_team_tactics_on_team(team)
    s = get_current_playstyle_preset_state(team)
    assert s["preset_id"] is None
    assert s["label_ja"] == "未設定"
    assert s["is_custom"] is False


def test_get_current_rotation_preset_state_custom_roundtrip():
    team = SimpleNamespace(strategy="balanced", usage_policy="win_now", players=[], team_tactics={})
    apply_rotation_preset_with_preset_meta(team, "balanced_v1")
    s = get_current_rotation_preset_state(team)
    assert s["is_custom"] is False
    assert s["label_ja"] == "バランス型"
    raw = dict(team.team_tactics)
    up = dict(raw["usage_policy"])
    up["priority"] = "win"
    raw["usage_policy"] = up
    team.team_tactics = normalize_team_tactics(raw, valid_player_ids=None)
    assert get_current_rotation_preset_state(team)["is_custom"] is True
    apply_rotation_preset_with_preset_meta(team, "balanced_v1")
    assert get_current_rotation_preset_state(team)["is_custom"] is False


def test_apply_playstyle_preset_unknown_raises():
    team = SimpleNamespace(strategy="balanced", players=[], team_tactics={})
    with pytest.raises(KeyError):
        apply_playstyle_preset(team, "nope_v1")
