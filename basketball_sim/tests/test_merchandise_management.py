"""グッズ開発（management・フェーズ進行）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.merchandise_management import (
    advance_merchandise_phase,
    ensure_merchandise_on_team,
    estimate_dummy_merch_sales_lines,
    format_cli_merchandise_management_screen_lines,
    get_merchandise_item,
    management_merchandise_revenue_bonus,
)


def test_format_cli_merch_screen_fresh():
    t = Team(team_id=50, name="CliMer", league_level=1, is_user_team=True, money=5_000_000)
    text = "\n".join(format_cli_merchandise_management_screen_lines(t))
    assert "【グッズサマリー】" in text
    assert "【候補比較】" in text
    assert "直近施策: 未実行" in text
    assert "履歴: 履歴なし" in text
    assert "オルタネイトジャージ" in text
    assert "ユニフォーム系" in text


def test_format_cli_merch_screen_after_advance_marks_latest():
    t = Team(team_id=51, name="CliMer2", league_level=1, is_user_team=True, money=5_000_000)
    ok, _ = advance_merchandise_phase(t, "fan_towel")
    assert ok is True
    text = "\n".join(format_cli_merchandise_management_screen_lines(t))
    assert "履歴: 1件" in text
    assert "（直近）" in text
    assert "チーム応援タオル" in text


def test_format_cli_merch_screen_none_team():
    text = "\n".join(format_cli_merchandise_management_screen_lines(None))
    assert "情報なし" in text


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
    assert "簡易" in text or "目安" in text
    assert "推定" in text


def test_management_merch_bonus_zero_without_on_sale():
    t = Team(team_id=6, name="N", league_level=1, popularity=50)
    ensure_merchandise_on_team(t)
    assert management_merchandise_revenue_bonus(t, league_level=1) == 0


def test_management_merch_bonus_positive_with_on_sale():
    t = Team(team_id=7, name="O", league_level=1, popularity=50)
    ensure_merchandise_on_team(t)
    for row in t.management["merchandise"]["items"]:
        if row.get("id") == "jersey_alt":
            row["phase"] = "on_sale"
            break
    b = management_merchandise_revenue_bonus(t, league_level=1)
    assert b >= 150_000


def test_offseason_merchandise_includes_management_bonus():
    from basketball_sim.models.offseason import Offseason

    base_team = Team(team_id=8, name="B", league_level=1, players=[], popularity=50)
    ensure_merchandise_on_team(base_team)

    boosted = Team(team_id=9, name="S", league_level=1, players=[], popularity=50)
    ensure_merchandise_on_team(boosted)
    for row in boosted.management["merchandise"]["items"]:
        row["phase"] = "on_sale"

    class _StubOff(Offseason):
        def _get_team_wins(self, t):
            return 15

    stub = _StubOff.__new__(_StubOff)
    tb, bbd = stub._calculate_team_revenue(base_team)
    ts, sbd = stub._calculate_team_revenue(boosted)
    assert sbd["merchandise"] == bbd["merchandise"] + management_merchandise_revenue_bonus(boosted, league_level=1)
    assert ts - tb == management_merchandise_revenue_bonus(boosted, league_level=1)
