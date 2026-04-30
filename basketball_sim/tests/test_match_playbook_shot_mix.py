"""team_tactics.playbook（off_ball_screen / post_up）→ Match._get_shot_mix の極小接続。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    _PLAYBOOK_SHOT_MIX_RATE_MAX,
    _PLAYBOOK_SHOT_MIX_RATE_MIN,
    _PLAYBOOK_SHOT_MIX_THREE_MAX,
    _PLAYBOOK_SHOT_MIX_THREE_MIN,
    _PLAYBOOK_SHOT_MIX_TWO_MAX,
    _PLAYBOOK_SHOT_MIX_TWO_MIN,
    ensure_team_tactics_on_team,
    get_playbook_shot_mix_deltas,
)


def _player(pid: int, position: str) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=190.0,
        weight_kg=85.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=68,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _team(tid: int, name: str) -> Team:
    t = Team(team_id=tid, name=name, league_level=1, team_training_focus="balanced")
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        t.add_player(_player(tid * 100 + i + 1, pos))
    return t


def _with_playbook(t: Team, pb: dict) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "offense_creation": "post",
            "defense_style": "balanced",
            "rebound_style": "balanced",
            "transition_style": "situational",
        },
        "playbook": pb,
    }
    ensure_team_tactics_on_team(t)
    return t


def _shot_mix(m: Match):
    return m._get_shot_mix(
        m.home_team, m.away_team, m.home_starters, m.away_starters
    )


def test_off_ball_screen_high_and_low_affect_three_direction():
    t_hi = _with_playbook(_team(1, "H"), {"off_ball_screen": "high"})
    t_lo = _with_playbook(_team(2, "L"), {"off_ball_screen": "low"})
    d_hi = get_playbook_shot_mix_deltas(t_hi)
    d_lo = get_playbook_shot_mix_deltas(t_lo)
    assert d_hi[0] > 0.0
    assert d_hi[1] < 0.0
    assert d_lo[0] < 0.0
    assert d_lo[1] > 0.0


def test_post_up_high_and_low_affect_two_direction():
    t_hi = _with_playbook(_team(3, "PH"), {"post_up": "high"})
    t_lo = _with_playbook(_team(4, "PL"), {"post_up": "low"})
    d_hi = get_playbook_shot_mix_deltas(t_hi)
    d_lo = get_playbook_shot_mix_deltas(t_lo)
    assert d_hi[1] > 0.0
    assert d_hi[0] < 0.0
    assert d_lo[1] < 0.0
    assert d_lo[0] > 0.0


def test_standard_or_non_target_keys_do_not_add_shot_mix_delta():
    t = _with_playbook(
        _team(5, "S"),
        {
            "pick_and_roll": "high",
            "spain_pick_and_roll": "high",
            "handoff": "high",
            "transition": "high",
            "off_ball_screen": "standard",
            "post_up": "standard",
        },
    )
    assert get_playbook_shot_mix_deltas(t) == (0.0, 0.0, 0.0)


def test_playbook_shot_mix_delta_stays_within_layer_clamps():
    t = _with_playbook(
        _team(6, "C"),
        {"off_ball_screen": "high", "post_up": "high"},
    )
    d3, d2, dsr = get_playbook_shot_mix_deltas(t)
    assert _PLAYBOOK_SHOT_MIX_THREE_MIN <= d3 <= _PLAYBOOK_SHOT_MIX_THREE_MAX
    assert _PLAYBOOK_SHOT_MIX_TWO_MIN <= d2 <= _PLAYBOOK_SHOT_MIX_TWO_MAX
    assert _PLAYBOOK_SHOT_MIX_RATE_MIN <= dsr <= _PLAYBOOK_SHOT_MIX_RATE_MAX


def test_get_shot_mix_reflects_playbook_directions():
    away = _with_playbook(_team(20, "Away"), {"off_ball_screen": "standard", "post_up": "standard"})
    home_std = _with_playbook(_team(10, "Std"), {"off_ball_screen": "standard", "post_up": "standard"})
    home_obs = _with_playbook(_team(11, "Obs"), {"off_ball_screen": "high", "post_up": "standard"})
    home_post = _with_playbook(_team(12, "Post"), {"off_ball_screen": "standard", "post_up": "high"})
    for h in (home_std, home_obs, home_post):
        h.strategy = "balanced"
    m_std = Match(home_team=home_std, away_team=away)
    m_obs = Match(home_team=home_obs, away_team=away)
    m_post = Match(home_team=home_post, away_team=away)
    std = _shot_mix(m_std)
    obs = _shot_mix(m_obs)
    post = _shot_mix(m_post)
    assert obs[0] > std[0]
    assert post[1] > std[1]
    assert post[0] < std[0]

