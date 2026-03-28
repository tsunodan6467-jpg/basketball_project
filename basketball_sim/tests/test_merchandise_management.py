"""グッズ開発（management・フェーズ進行）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.merchandise_management import (
    advance_merchandise_phase,
    ensure_merchandise_on_team,
    estimate_dummy_merch_sales_lines,
    get_merchandise_item,
)


def test_ensure_builds_three_lines():
    t = Team(team_id=1, name="M", league_level=1)
    ensure_merchandise_on_team(t)
    items = t.management["merchandise"]["items"]
    assert len(items) == 3
    assert all(x.get("phase") == "concept" for x in items)


def test_advance_user_pays_and_moves_phase():
    t = Team(team_id=2, name="U", league_level=1, is_user_team=True, money=2_000_000)
    ok, msg = advance_merchandise_phase(t, "jersey_alt")
    assert ok is True
    assert t.money < 2_000_000
    item = get_merchandise_item(t, "jersey_alt")
    assert item is not None
    assert item["phase"] == "design"
    assert "進めました" in msg


def test_advance_to_on_sale_then_stop():
    t = Team(team_id=3, name="V", league_level=1, is_user_team=True, money=50_000_000)
    for _ in range(4):
        item = get_merchandise_item(t, "fan_towel")
        if item and item["phase"] == "on_sale":
            break
        ok, _ = advance_merchandise_phase(t, "fan_towel")
        assert ok is True
    ok, msg = advance_merchandise_phase(t, "fan_towel")
    assert ok is False
    assert "発売中" in msg


def test_cpu_rejected():
    t = Team(team_id=4, name="C", league_level=1, is_user_team=False, money=5_000_000)
    ok, msg = advance_merchandise_phase(t, "jersey_alt")
    assert ok is False


def test_dummy_sales_contains_estimate():
    t = Team(team_id=5, name="D", league_level=1, fan_base=3000, popularity=55)
    lines = estimate_dummy_merch_sales_lines(t)
    text = "\n".join(lines)
    assert "ダミー" in text or "簡易" in text
    assert "推定" in text
