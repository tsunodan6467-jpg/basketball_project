"""CPU 裏経営（ラウンドフック）。"""

import random

from basketball_sim.models.team import Team
from basketball_sim.systems.cpu_management import (
    append_cpu_management_log,
    apply_cpu_management_to_team,
    run_cpu_management_after_round,
)


class _FakeSeason:
    def __init__(self, cr: int = 3) -> None:
        self.current_round = cr
        self.season_finished = False
        self.game_count = 10


def test_apply_cpu_management_skips_user_team():
    rng = random.Random(0)
    u = Team(team_id=1, name="User", league_level=1, is_user_team=True, money=10_000_000)
    before = int(u.money)
    apply_cpu_management_to_team(u, rng, _FakeSeason())
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
    s = _FakeSeason(4)
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
        apply_cpu_management_to_team(t, random.Random(seed), s)
        assert int(t.money) >= 0
        assert 1 <= int(t.sponsor_power) <= 100
        assert 0 <= int(t.popularity) <= 100
        assert int(t.fan_base) >= 0


def test_append_cpu_management_log_trims():
    t = Team(team_id=11, name="L", league_level=1, is_user_team=False)
    s = _FakeSeason(1)
    for i in range(55):
        append_cpu_management_log(t, s, "t", str(i))
    assert len(t.management["cpu_mgmt_log"]) <= 48


def test_pr_core_cpu_marks_actor():
    from basketball_sim.systems.pr_campaign_management import _commit_pr_campaign_core

    t = Team(team_id=12, name="CPU", league_level=1, is_user_team=False, money=20_000_000)
    ok, _ = _commit_pr_campaign_core(t, "sns_buzz", _FakeSeason(2), actor="cpu")
    assert ok is True
    assert t.management["pr_campaigns"]["history"][-1].get("actor") == "cpu"


def test_merch_core_cpu_marks_source():
    from basketball_sim.systems.merchandise_management import _advance_merchandise_phase_core

    t = Team(team_id=13, name="M", league_level=1, is_user_team=False, money=20_000_000)
    ok, _ = _advance_merchandise_phase_core(t, "jersey_alt", source="cpu")
    assert ok is True
    assert t.management["merchandise"]["history"][-1].get("source") == "cpu"
