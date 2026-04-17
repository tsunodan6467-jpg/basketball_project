"""新規開始フロー⑤ `normalize_initial_payrolls_for_teams` 直後も `payroll_budget` が既定のまま（timeline 仮説の固定）。"""

from __future__ import annotations

import contextlib
import io

from basketball_sim.main import CITY_MARKET_SIZE, apply_user_team_to_league
from basketball_sim.systems.club_profile import get_initial_user_team_money
from basketball_sim.systems.contract_logic import normalize_initial_payrolls_for_teams
from basketball_sim.systems.generator import generate_teams
from basketball_sim.utils.sim_rng import init_simulation_random

DEFAULT_PAYROLL_BUDGET = 120_000_000


def test_user_team_payroll_budget_stays_default_after_normalize_initial_payrolls() -> None:
    """
    `docs/PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md` の ②〜⑤ 相当:
    generate → user 差し替え（money 更新）→ normalize は選手年俸のみで budget フィールドは不変。
    """
    init_simulation_random(42)
    silent = io.StringIO()
    with contextlib.redirect_stdout(silent):
        teams = generate_teams()
        user_team = apply_user_team_to_league(
            teams,
            "Timeline FC",
            "東京",
            float(CITY_MARKET_SIZE["東京"]),
        )

    assert user_team.is_user_team is True
    assert int(user_team.money) == int(get_initial_user_team_money(user_team))
    assert user_team.payroll_budget == DEFAULT_PAYROLL_BUDGET
    assert len(getattr(user_team, "players", []) or []) > 0

    normalize_initial_payrolls_for_teams(teams)

    assert user_team.payroll_budget == DEFAULT_PAYROLL_BUDGET
    assert int(user_team.money) == int(get_initial_user_team_money(user_team))
    roster_payroll = sum(int(getattr(p, "salary", 0) or 0) for p in user_team.players)
    assert roster_payroll > 0
