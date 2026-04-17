"""インシーズンFA: anchor＋estimate ブレンドの実測表（pytest -s）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_market import (
    estimate_fa_market_value,
    inseason_fa_contract_salary,
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


def _team_d1() -> Team:
    roster = []
    for i in range(13):
        roster.append(
            _p(5000 + i, 52 - (i % 3), 26, "Japan", 8_000_000 + i * 100_000)
        )
    t = Team(team_id=1, name="T", league_level=1, money=800_000_000, players=roster)
    return t


def test_inseason_fa_table_print(capsys):
    t = _team_d1()
    rows = []
    for nat, age, ovr, sal in [
        ("Japan", 27, 76, 72_000_000),
        ("Foreign", 27, 76, 95_000_000),
        ("Naturalized", 27, 76, 120_000_000),
        ("Asia", 27, 76, 50_000_000),
        ("Japan", 19, 72, 5_000_000),
        ("Foreign", 22, 74, 6_000_000),
    ]:
        p = _p(8000 + len(rows), ovr, age, nat, sal)
        est = int(estimate_fa_market_value(p))
        final = int(inseason_fa_contract_salary(t, p))
        rows.append((nat, age, ovr, sal, est, final))

    lines = ["nat age ovr save estimate final_inseason"]
    for r in rows:
        lines.append(" ".join(str(x) for x in r))
    print("\n" + "\n".join(lines))
    assert rows[1][5] >= rows[0][5]


def test_young_inseason_not_above_prime_foreign():
    t = _team_d1()
    y = _p(9100, 74, 19, "Foreign", 7_000_000)
    p = _p(9101, 74, 28, "Foreign", 80_000_000)
    assert inseason_fa_contract_salary(t, y) <= inseason_fa_contract_salary(t, p)


def test_naturalized_ge_japan_inseason():
    t = _team_d1()
    j = _p(9200, 76, 27, "Japan", 70_000_000)
    n = _p(9201, 76, 27, "Naturalized", 100_000_000)
    assert inseason_fa_contract_salary(t, n) >= inseason_fa_contract_salary(t, j)
