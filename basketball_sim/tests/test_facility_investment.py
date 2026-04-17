"""systems.facility_investment の施設投資コア。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.facility_investment import (
    FACILITY_MAX_LEVEL,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
    format_cli_facility_screen_header_lines,
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


def test_cli_facility_header_flat_levels_placeholders():
    t = Team(team_id=1, name="T", league_level=1)
    text = "\n".join(format_cli_facility_screen_header_lines(t))
    assert "【施設サマリー】" in text
    assert "【施設の見どころ】" in text
    assert "全体水準: 低い" in text
    assert "投資履歴: 履歴なし（未投資）" in text
    assert "強み: 情報なし" in text
    assert "弱み: 情報なし" in text
    assert "次に上げたい候補: 情報なし" in text


def test_cli_facility_header_spread_shows_strength_weakness_next():
    t = Team(team_id=1, name="T", league_level=1)
    t.arena_level = 4
    t.training_facility_level = 2
    t.medical_facility_level = 2
    t.front_office_level = 3
    text = "\n".join(format_cli_facility_screen_header_lines(t))
    assert "強み: アリーナ" in text
    assert "弱み: トレーニング施設 / メディカル施設" in text
    assert "次に上げたい候補: トレーニング施設 / メディカル施設" in text


def test_cli_facility_header_counts_upgrade_notes():
    t = Team(team_id=1, name="T", league_level=1)
    t.finance_history = [
        {"note": "facility_upgrade:arena_level:Lv2", "revenue": 0, "expense": 1, "cashflow": -1},
        {"note": "other", "revenue": 0, "expense": 0, "cashflow": 0},
    ]
    text = "\n".join(format_cli_facility_screen_header_lines(t))
    assert "投資履歴: 1件" in text
