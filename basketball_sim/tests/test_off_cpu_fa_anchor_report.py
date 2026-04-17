"""オフ CPU 本格 FA の anchor / base / offer 実測表（pytest -s で表示）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems import free_agency as fa
from basketball_sim.systems.free_agent_market import fa_pool_market_salary
from basketball_sim.systems.resign_salary_anchor import (
    fa_anchor_core_for_cpu_offer,
    fa_offer_base_salary,
    get_fa_offer_anchor_band,
    infer_fa_candidate_role_band,
    median_league_level_for_teams,
)


def _p(pid, ovr, age, nat, sal) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality=nat,
        position="SF",
        height_cm=200.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="B",
        archetype="wing",
        usage_base=20,
        salary=sal,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def _team_d1_one_starter() -> Team:
    roster = _p(1, 60, 28, "Japan", 8_000_000)
    t = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    t.payroll_budget = int(fa._soft_cap(t)) + 40_000_000
    return t


def _fill12(t: Team, base_id: int) -> None:
    for i in range(12):
        t.players.append(_p(base_id + i, 52, 26, "Japan", 6_000_000))


def test_off_fa_anchor_table_print(capsys):
    """pytest -s で代表行を確認。"""
    rows = []
    t1 = _team_d1_one_starter()
    _fill12(t1, 2000)
    for nat, age, ovr, sal in [
        ("Japan", 27, 76, 72_000_000),
        ("Foreign", 27, 76, 95_000_000),
        ("Naturalized", 27, 76, 120_000_000),
        ("Asia", 27, 76, 50_000_000),
        ("Japan", 19, 72, 5_000_000),
        ("Foreign", 22, 74, 6_000_000),
    ]:
        fa_p = _p(9000 + len(rows), ovr, age, nat, sal)
        rk = infer_fa_candidate_role_band(t1, fa_p)
        lo, mid, hi = get_fa_offer_anchor_band(fa_p, t1)
        core = fa_anchor_core_for_cpu_offer(fa_p, t1)
        base = fa_offer_base_salary(t1, fa_p)
        off = int(fa._calculate_offer(t1, fa_p))
        rows.append((nat, age, ovr, sal, rk, lo, mid, hi, core, base, off))

    teams_m = [Team(team_id=i, name="x", league_level=lv, players=[]) for i, lv in enumerate([3, 3, 2, 1, 3])]
    div_m = median_league_level_for_teams(teams_m)
    intl_f = _p(9100, 70, 26, "Foreign", 0)
    intl_a = _p(9101, 68, 25, "Asia", 0)
    intl_sal_f = fa_pool_market_salary(intl_f, league_division=div_m)
    intl_sal_a = fa_pool_market_salary(intl_a, league_division=div_m)

    lines = ["nat age ovr save rank lo mid hi fa_core base offer"]
    for r in rows:
        lines.append(" ".join(str(x) for x in r))
    lines.append(f"intl_div_median={div_m} foreign_salary={intl_sal_f} asia_salary={intl_sal_a}")
    print("\n" + "\n".join(lines))
    assert rows[1][9] >= rows[0][9]
    assert intl_sal_f >= intl_sal_a


def test_young_fa_base_capped_vs_prime_d1():
    t = _team_d1_one_starter()
    _fill12(t, 3000)
    young = _p(9200, 74, 19, "Foreign", 8_000_000)
    prime = _p(9201, 74, 28, "Foreign", 80_000_000)
    assert fa_offer_base_salary(t, young) <= fa_offer_base_salary(t, prime)
