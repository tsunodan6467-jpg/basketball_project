"""⑦ `_process_team_finances` 後の user team `payroll_budget` 再設定（timeline 仮説の次段）。"""

from __future__ import annotations

import contextlib
import io

from basketball_sim.models.offseason import (
    Offseason,
    TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER,
    TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team

DEFAULT_PAYROLL_BUDGET = 120_000_000


def _current_formula_payroll_budget_d3(
    *,
    market_size: float,
    popularity: int,
    sponsor_power: int,
    fan_base: int,
) -> int:
    """`offseason._process_team_finances` 内の現行式（D3 / base_budget 分岐）。"""
    league_level = 3
    base_budget = {1: 7_900_000, 2: 5_450_000, 3: 3_650_000}.get(league_level, 3_650_000)
    return max(
        base_budget,
        int(
            base_budget
            + float(market_size) * 12_500
            + int(popularity) * 6_200
            + int(sponsor_power) * 5_000
            + int(fan_base) * 3_600
        ),
    )


def _expected_payroll_budget_after_finance_close_d3(
    *,
    roster_payroll: int,
    market_size: float,
    popularity: int,
    sponsor_power: int,
    fan_base: int,
) -> int:
    """⑦後の `payroll_budget` = max(現行式, floor_expr)。`offseason.py` と同一式。"""
    current_formula_budget = _current_formula_payroll_budget_d3(
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )
    floor_expr = int(
        int(roster_payroll) * float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO)
        + float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER)
    )
    return int(max(current_formula_budget, floor_expr))


def _player(pid: int, salary: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
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
        ovr=60,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=1,
        contract_total_years=2,
        team_id=1,
    )


def test_user_team_payroll_budget_recomputed_after_process_team_finances() -> None:
    """
    オフ締め `_process_team_finances`（⑦）で `payroll_budget` が来季目安式＋roster 床の max に上書きされる。
    ロスター年俸0では floor が現行式より小さく、現行式が採用される。
    """
    market_size = 1.2
    popularity = 45
    sponsor_power = 50
    fan_base = 5000

    user = Team(
        team_id=1,
        name="UserOffClose",
        league_level=3,
        is_user_team=True,
        payroll_budget=DEFAULT_PAYROLL_BUDGET,
        money=50_000_000,
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
        players=[],
        last_season_wins=15,
    )
    assert user.payroll_budget == DEFAULT_PAYROLL_BUDGET

    expected = _expected_payroll_budget_after_finance_close_d3(
        roster_payroll=0,
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )
    assert expected != DEFAULT_PAYROLL_BUDGET
    assert expected == _current_formula_payroll_budget_d3(
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )

    off = Offseason(teams=[user], free_agents=[])
    with contextlib.redirect_stdout(io.StringIO()):
        off._process_team_finances()

    assert user.payroll_budget == expected
    assert user.is_user_team is True


def test_payroll_budget_uses_roster_floor_when_above_formula() -> None:
    """ロスター年俸が現行式を上回るとき、`max(現行式, α*roster+β)` の大きい方になる。"""
    market_size = 1.2
    popularity = 45
    sponsor_power = 50
    fan_base = 5000
    roster_salary = 80_000_000

    user = Team(
        team_id=1,
        name="UserHighPayroll",
        league_level=3,
        is_user_team=True,
        payroll_budget=DEFAULT_PAYROLL_BUDGET,
        money=50_000_000,
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
        players=[_player(1, roster_salary)],
        last_season_wins=15,
    )

    expected = _expected_payroll_budget_after_finance_close_d3(
        roster_payroll=roster_salary,
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )
    current = _current_formula_payroll_budget_d3(
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )
    assert expected > current
    assert expected == int(
        roster_salary * float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO)
        + float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER)
    )

    off = Offseason(teams=[user], free_agents=[])
    with contextlib.redirect_stdout(io.StringIO()):
        off._process_team_finances()

    assert user.payroll_budget == expected
