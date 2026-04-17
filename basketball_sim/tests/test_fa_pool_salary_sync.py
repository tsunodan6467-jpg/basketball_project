"""FAプール正規化時の player.salary と市場基準値 `fa_pool_market_salary` の同期。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_market import (
    fa_pool_market_salary,
    inseason_fa_contract_salary,
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


def test_normalize_free_agents_syncs_salary_to_fa_pool_market():
    p = _fa_player(99001, salary=999_999)
    expected = int(fa_pool_market_salary(p, league_division=3))
    out = normalize_free_agents([p], league_market_division=3)
    assert out == [p]
    assert p.salary == expected


def test_sync_fa_pool_player_salary_to_estimate_matches_fa_pool_market():
    p = _fa_player(99002, ovr=72, salary=4_000_000)
    sync_fa_pool_player_salary_to_estimate(p, league_market_division=3)
    assert p.salary == int(fa_pool_market_salary(p, league_division=3))


def test_normalize_excludes_retired_without_syncing():
    p = _fa_player(99003, salary=1)
    p.is_retired = True
    before = p.salary
    out = normalize_free_agents([p], league_market_division=3)
    assert out == []
    assert p.salary == before


def test_young_fa_pool_market_not_excessive_d3():
    p19 = _fa_player(99100, age=19, ovr=70, salary=1, nationality="Japan")
    p22 = _fa_player(99101, age=22, ovr=70, salary=1, nationality="Japan")
    s19 = fa_pool_market_salary(p19, league_division=3)
    s22 = fa_pool_market_salary(p22, league_division=3)
    assert s19 <= s22 + 1
    assert s19 < 120_000_000
    assert s22 < 150_000_000


def test_foreign_pool_salary_premium_same_ovr_d3():
    j = _fa_player(99110, age=27, ovr=74, salary=1, nationality="Japan")
    f = _fa_player(99111, age=27, ovr=74, salary=1, nationality="Foreign")
    assert fa_pool_market_salary(f, league_division=3) > fa_pool_market_salary(j, league_division=3)


def test_naturalized_at_least_foreign_d3_pool():
    n = _fa_player(99112, age=27, ovr=74, salary=1, nationality="Naturalized")
    f = _fa_player(99113, age=27, ovr=74, salary=1, nationality="Foreign")
    assert fa_pool_market_salary(n, league_division=3) >= fa_pool_market_salary(f, league_division=3)


def test_japan_at_least_asia_d3_pool():
    a = _fa_player(99114, age=27, ovr=74, salary=1, nationality="Asia")
    j = _fa_player(99115, age=27, ovr=74, salary=1, nationality="Japan")
    assert fa_pool_market_salary(j, league_division=3) >= fa_pool_market_salary(a, league_division=3)


def test_pool_salary_same_order_of_magnitude_as_inseason_d3():
    team = Team(team_id=1, name="T", league_level=3, money=2_000_000_000, players=[])
    p = _fa_player(99120, age=27, ovr=76, salary=50_000_000, nationality="Foreign")
    pool = fa_pool_market_salary(p, league_division=3)
    ins = inseason_fa_contract_salary(team, p)
    r = max(pool, ins) / max(1, min(pool, ins))
    assert r < 2.8
