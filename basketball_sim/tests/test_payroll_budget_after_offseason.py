"""⑦ `_process_team_finances` 後の user team `payroll_budget` 再設定（timeline 仮説の次段）。"""

from __future__ import annotations

import contextlib
import io

from basketball_sim.models.offseason import Offseason
from basketball_sim.models.team import Team

DEFAULT_PAYROLL_BUDGET = 120_000_000


def _expected_payroll_budget_after_finance_close_d3(
    *,
    market_size: float,
    popularity: int,
    sponsor_power: int,
    fan_base: int,
) -> int:
    """`offseason._process_team_finances` 内の式と同一（D3 / base_budget 分岐）。"""
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


def test_user_team_payroll_budget_recomputed_after_process_team_finances() -> None:
    """
    オフ締め `_process_team_finances`（⑦）で `payroll_budget` が来季目安式に上書きされる。
    事前は新規開始相当の 120M（`apply_user_team_to_league` 後と同型の popularity / market）。
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
        market_size=market_size,
        popularity=popularity,
        sponsor_power=sponsor_power,
        fan_base=fan_base,
    )
    assert expected != DEFAULT_PAYROLL_BUDGET

    off = Offseason(teams=[user], free_agents=[])
    with contextlib.redirect_stdout(io.StringIO()):
        off._process_team_finances()

    assert user.payroll_budget == expected
    assert user.is_user_team is True
