"""FAプール正規化時の player.salary と estimate_fa_market_value の同期。"""

from basketball_sim.models.player import Player
from basketball_sim.systems.free_agent_market import (
    estimate_fa_market_value,
    normalize_free_agents,
    sync_fa_pool_player_salary_to_estimate,
)


def _fa_player(player_id: int, *, ovr: int = 65, salary: int = 1_000_000, **kwargs: object) -> Player:
    d = dict(
        player_id=player_id,
        name=f"P{player_id}",
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    d.update(kwargs)
    return Player(**d)


def test_normalize_free_agents_syncs_salary_to_estimate():
    p = _fa_player(99001, salary=999_999)
    assert p.salary != estimate_fa_market_value(p)
    out = normalize_free_agents([p])
    assert out == [p]
    est = int(estimate_fa_market_value(p))
    assert p.salary == est


def test_sync_fa_pool_player_salary_to_estimate_matches_estimate():
    p = _fa_player(99002, ovr=72, salary=4_000_000)
    sync_fa_pool_player_salary_to_estimate(p)
    assert p.salary == int(estimate_fa_market_value(p))


def test_normalize_excludes_retired_without_syncing():
    p = _fa_player(99003, salary=1)
    p.is_retired = True
    before = p.salary
    out = normalize_free_agents([p])
    assert out == []
    assert p.salary == before
