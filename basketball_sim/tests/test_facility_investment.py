"""systems.facility_investment の施設投資コア。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.facility_investment import (
    FACILITY_MAX_LEVEL,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
    get_facility_upgrade_cost,
)


def test_commit_arena_upgrade_deducts_money_and_buffs():
    t = Team(team_id=1, name="T", league_level=1, money=10_000_000)
    cost = get_facility_upgrade_cost(t, "arena_level")
    pop0, fb0 = t.popularity, t.fan_base
    ok, msg = commit_facility_upgrade(t, "arena_level")
    assert ok is True
    assert "強化" in msg
    assert t.arena_level == 2
    assert t.money == 10_000_000 - cost
    assert t.popularity == pop0 + 1
    assert t.fan_base == fb0 + 2


def test_can_commit_rejects_insufficient_funds():
    t = Team(team_id=1, name="T", league_level=1, money=0)
    ok, msg = can_commit_facility_upgrade(t, "arena_level")
    assert ok is False
    assert "不足" in msg


def test_can_commit_rejects_at_max_level():
    t = Team(team_id=1, name="T", league_level=1, money=1_000_000_000)
    t.arena_level = FACILITY_MAX_LEVEL
    ok, msg = can_commit_facility_upgrade(t, "arena_level")
    assert ok is False
    assert "最大" in msg


def test_unknown_facility_key_rejected():
    t = Team(team_id=1, name="T", league_level=1, money=1_000_000_000)
    ok, msg = can_commit_facility_upgrade(t, "not_a_facility")
    assert ok is False
    assert "不明" in msg
