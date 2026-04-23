"""team_tactics.team_strategy.defense_style（protect_paint / protect_three）→ Match._get_shot_mix（第3弾A）。"""

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    ensure_team_tactics_on_team,
    get_defense_style_shot_mix_deltas,
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


def _with_defense_style(t: Team, defense_style: str) -> Team:
    t.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "standard",
            "offense_style": "balanced",
            "defense_style": defense_style,
        },
    }
    ensure_team_tactics_on_team(t)
    return t


def _shot_mix(m: Match):
    return m._get_shot_mix(
        m.home_team, m.away_team, m.home_starters, m.away_starters
    )


def test_get_shot_mix_balanced_strategy_protect_paint_small_change():
    """守備: strategy=balanced + defense_style=protect_paint で _get_shot_mix に小さな差が乗る。"""
    home = _with_defense_style(_team(1, "Home"), "balanced")
    away_p = _with_defense_style(_team(2, "AwayP"), "protect_paint")
    away_b = _with_defense_style(_team(2, "AwayB"), "balanced")
    m_p = Match(home_team=home, away_team=away_p)
    m_b = Match(home_team=home, away_team=away_b)
    a, b, c = _shot_mix(m_p)
    a0, b0, c0 = _shot_mix(m_b)
    assert (a, b, c) != (a0, b0, c0)
    # ペイント守り: 相手3割選択がやや増える想定
    assert a > a0


def test_get_defense_style_helper_defense_strategy_dampens_vs_balanced():
    """strategy=defense かつ protect_paint は、balanced 満額より同方向で減衰（小さい）。"""
    t_def = _with_defense_style(_team(1, "TDef"), "protect_paint")
    t_bal = _with_defense_style(_team(2, "TBal"), "protect_paint")
    full = get_defense_style_shot_mix_deltas(t_bal, "balanced")
    damp = get_defense_style_shot_mix_deltas(t_def, "defense")
    k = 0.3
    for i in range(3):
        assert abs(damp[i]) < abs(full[i])
        assert abs(damp[i] - full[i] * k) < 1e-9


def test_protect_paint_vs_protect_three_three_cutoff_opposes():
    """protect_paint は three_cutoff 上向き、protect_three は下向き（相异）。"""
    t_p = _with_defense_style(_team(1, "TP"), "protect_paint")
    t_t = _with_defense_style(_team(2, "TT"), "protect_three")
    p = get_defense_style_shot_mix_deltas(t_p, "balanced")
    q = get_defense_style_shot_mix_deltas(t_t, "balanced")
    assert p[0] > 0.0
    assert q[0] < 0.0
    assert p[0] * q[0] < 0.0
