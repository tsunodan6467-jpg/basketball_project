"""foul_policy × 個人ファウル: OUT 候補スコアの弱い補正（Match 未接続・dict 接続口）。"""

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation import (
    RotationSystem,
    foul_trouble_out_candidate_bonus,
)
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_rotation_foul_policy,
    normalize_team_tactics,
)


def _player(pid: int, pos: str = "SF", ovr: int = 70) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=pos,
        height_cm=198.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=70,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team_n(foul_policy: str, n: int = 8) -> Team:
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="balanced")
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"][:n]
    for i, pos in enumerate(positions):
        t.add_player(_player(100 + i, pos=pos, ovr=78 - i))
    t.team_tactics = get_default_team_tactics()
    ensure_team_tactics_on_team(t)
    raw = dict(t.team_tactics)
    rot = dict(raw.get("rotation") or {})
    rot["foul_policy"] = foul_policy
    raw["rotation"] = rot
    t.team_tactics = normalize_team_tactics(
        raw, valid_player_ids={100 + i for i in range(n)}
    )
    t.set_starting_lineup_by_players(list(t.players)[:5])
    return t


def test_foul_trouble_bonus_zero_for_zero_or_one_fouls():
    for pol in ("early_pull", "standard", "ride"):
        assert foul_trouble_out_candidate_bonus(0, pol) == 0.0
        assert foul_trouble_out_candidate_bonus(1, pol) == 0.0


def test_foul_trouble_bonus_early_pull_ge_standard_ge_ride():
    for tier_f in (2, 3, 4, 5):
        ep = foul_trouble_out_candidate_bonus(tier_f, "early_pull")
        st = foul_trouble_out_candidate_bonus(tier_f, "standard")
        ri = foul_trouble_out_candidate_bonus(tier_f, "ride")
        assert ep >= st >= ri
    assert foul_trouble_out_candidate_bonus(3, "early_pull") > foul_trouble_out_candidate_bonus(3, "standard")
    assert foul_trouble_out_candidate_bonus(3, "standard") > foul_trouble_out_candidate_bonus(3, "ride")


def test_foul_trouble_bonus_invalid_policy_falls_back_to_standard():
    assert foul_trouble_out_candidate_bonus(4, "not_a_policy") == foul_trouble_out_candidate_bonus(
        4, "standard"
    )


def test_get_rotation_foul_policy_reads_team_tactics():
    t = _team_n("ride", 8)
    assert get_rotation_foul_policy(t) == "ride"


def test_personal_fouls_none_leaves_out_bonus_zero():
    t = _team_n("early_pull", 8)
    ps = list(t.players)
    r = RotationSystem(t, ps, starters=ps[:5], personal_fouls_by_player_id=None)
    for p in r.current_lineup:
        assert r._foul_trouble_out_score_bonus(p) == 0.0


def test_personal_fouls_str_keys_normalized():
    t = _team_n("early_pull", 8)
    ps = list(t.players)
    r = RotationSystem(
        t,
        ps,
        starters=ps[:5],
        personal_fouls_by_player_id={"100": 2, "101": "3"},  # type: ignore[arg-type]
    )
    p0 = next(p for p in r.current_lineup if p.player_id == 100)
    p1 = next(p for p in r.current_lineup if p.player_id == 101)
    assert r._foul_trouble_out_score_bonus(p0) == pytest.approx(0.8)
    assert r._foul_trouble_out_score_bonus(p1) == pytest.approx(1.6)


def test_early_pull_out_score_exceeds_ride_same_fouls():
    t_ep = _team_n("early_pull", 8)
    t_r = _team_n("ride", 8)
    ps = list(t_ep.players)
    fouls = {100: 4}
    r_ep = RotationSystem(t_ep, ps, starters=ps[:5], personal_fouls_by_player_id=fouls)
    r_r = RotationSystem(t_r, ps, starters=ps[:5], personal_fouls_by_player_id=fouls)
    p0 = next(p for p in r_ep.current_lineup if p.player_id == 100)
    assert r_ep._foul_trouble_out_score_bonus(p0) > r_r._foul_trouble_out_score_bonus(p0)
    assert r_ep._foul_trouble_out_score_bonus(p0) - r_r._foul_trouble_out_score_bonus(p0) == pytest.approx(
        2.6 - 1.2
    )


def test_get_out_candidates_runs_with_and_without_foul_map():
    t = _team_n("standard", 8)
    ps = list(t.players)
    r0 = RotationSystem(t, ps, starters=ps[:5])
    r1 = RotationSystem(
        t,
        ps,
        starters=ps[:5],
        personal_fouls_by_player_id={100: 2, 101: 1, 102: 0, 103: 4, 104: 3},
    )
    pos = 80
    tm0 = r0._build_target_minutes_map()
    tm1 = r1._build_target_minutes_map()
    out0 = r0._get_out_candidates(pos, 160, tm0)
    out1 = r1._get_out_candidates(pos, 160, tm1)
    assert isinstance(out0, list)
    assert isinstance(out1, list)


def test_set_fouled_out_player_ids_normalizes_and_can_sub_in_blocks():
    t = _team_n("standard", 8)
    ps = list(t.players)
    r = RotationSystem(t, ps, starters=ps[:5])
    p0 = ps[0]
    r.set_fouled_out_player_ids({str(p0.player_id), "bad", -1})  # type: ignore[arg-type]
    assert int(p0.player_id) in r._fouled_out_player_ids
    assert r._can_sub_in(p0, possession=40, total_possessions=160) is False


def test_fouled_out_on_court_gets_priority_out_and_bypasses_min_stint():
    t = _team_n("standard", 8)
    ps = list(t.players)
    r = RotationSystem(t, ps, starters=ps[:5])
    p0 = r.current_lineup[0]
    r.set_fouled_out_player_ids({int(p0.player_id)})
    # 入った直後でも foul out は外せる（クラッシュ回避より退場優先）
    r.last_sub_in_possession[r._player_key(p0)] = 80
    assert r._can_sub_out(p0, possession=81, total_possessions=160) is True
    tm = r._build_target_minutes_map()
    outs = r._get_out_candidates(possession=81, total_possessions=160, target_map=tm)
    assert outs
    assert outs[0] is p0
