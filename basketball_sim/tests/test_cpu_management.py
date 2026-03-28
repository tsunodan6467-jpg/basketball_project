"""CPU 裏経営（ラウンドフック）。"""

import random

from basketball_sim.models.team import Team
from basketball_sim.systems.cpu_management import (
    apply_cpu_management_to_team,
    run_cpu_management_after_round,
)


def test_apply_cpu_management_skips_user_team():
    rng = random.Random(0)
    u = Team(team_id=1, name="User", league_level=1, is_user_team=True, money=10_000_000)
    before = int(u.money)
    apply_cpu_management_to_team(u, rng)
    assert int(u.money) == before


def test_run_cpu_after_round_smoke():
    cpu = Team(team_id=2, name="CPU", league_level=2, is_user_team=False, money=80_000_000)
    user = Team(team_id=3, name="You", league_level=1, is_user_team=True, money=10_000_000)

    class _S:
        season_finished = False
        current_round = 4
        game_count = 20
        all_teams = [user, cpu]

    run_cpu_management_after_round(_S())


def test_cpu_team_stays_within_bounds_many_ticks():
    t = Team(
        team_id=10,
        name="Bot",
        league_level=1,
        is_user_team=False,
        money=200_000_000,
        arena_level=1,
        sponsor_power=50,
        popularity=50,
        fan_base=1000,
    )
    for seed in range(60):
        apply_cpu_management_to_team(t, random.Random(seed))
        assert int(t.money) >= 0
        assert 1 <= int(t.sponsor_power) <= 100
        assert 0 <= int(t.popularity) <= 100
        assert int(t.fan_base) >= 0
