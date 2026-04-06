"""大会賞金系がオフ締めの record_financial_result / finance_history に合流すること（R2 タスク1）。"""

from basketball_sim.models.offseason import (
    OFFSEASON_REV_BREAKDOWN_ASIA_CUP,
    OFFSEASON_REV_BREAKDOWN_FINAL_BOSS,
    OFFSEASON_REV_BREAKDOWN_INTERCONTINENTAL,
    Offseason,
)
from basketball_sim.models.team import Team


def test_asia_cup_rewards_accrue_pending_not_money_for_league_teams():
    t1 = Team(team_id=1, name="A", league_level=1, money=5_000_000, players=[], last_season_wins=10)
    t2 = Team(team_id=2, name="B", league_level=1, money=5_000_000, players=[], last_season_wins=10)
    off = Offseason(teams=[t1, t2], free_agents=[])
    off._apply_offseason_asia_cup_rewards(t1, t2)
    assert t1.money == 5_000_000
    assert t2.money == 5_000_000
    assert t1.offseason_competition_revenue_pending == 3_000_000
    assert t2.offseason_competition_revenue_pending == 1_500_000
    assert t1.offseason_competition_revenue_breakdown.get(OFFSEASON_REV_BREAKDOWN_ASIA_CUP) == 3_000_000
    assert t2.offseason_competition_revenue_breakdown.get(OFFSEASON_REV_BREAKDOWN_ASIA_CUP) == 1_500_000


def test_external_team_still_gets_immediate_money():
    league = Team(team_id=1, name="L", league_level=1, money=1_000_000, players=[])
    ext = Team(team_id=-999, name="Ext", league_level=1, money=100_000, players=[])
    off = Offseason(teams=[league], free_agents=[])
    off._apply_competition_cash_prize(ext, 500_000, "external_test_prize")
    assert ext.money == 600_000
    assert int(getattr(ext, "offseason_competition_revenue_pending", 0) or 0) == 0


def test_competition_pending_merged_once_in_finance_close():
    t = Team(team_id=1, name="Solo", league_level=1, money=1_000_000, players=[], last_season_wins=12)
    off = Offseason(teams=[t], free_agents=[])
    off._apply_final_boss_rewards(t, cleared=True)
    assert t.money == 1_000_000
    assert t.offseason_competition_revenue_pending == 10_000_000
    before = len(t.finance_history)
    off._process_team_finances()
    assert t.offseason_competition_revenue_pending == 0
    assert t.offseason_competition_revenue_breakdown == {}
    assert len(t.finance_history) == before + 1
    entry = t.finance_history[-1]
    br = entry.get("breakdown_revenue") or {}
    assert br.get(OFFSEASON_REV_BREAKDOWN_FINAL_BOSS) == 10_000_000
    assert t.money == 1_000_000 + int(entry["cashflow"])
    assert int(entry["revenue"]) - int(entry["expense"]) == int(entry["cashflow"])


def test_intercontinental_and_asia_stack_single_record_no_double_raw_money():
    """賞金は締め1回の revenue に載り、締め前の money は増えない（二重 paths なし）。"""
    champ = Team(team_id=1, name="C", league_level=1, money=2_000_000, players=[], last_season_wins=15)
    runner = Team(team_id=2, name="R", league_level=1, money=2_000_000, players=[], last_season_wins=14)
    off = Offseason(teams=[champ, runner], free_agents=[])
    off._apply_offseason_asia_cup_rewards(champ, runner)
    off._apply_intercontinental_cup_rewards(champ, runner)
    assert champ.money == 2_000_000
    assert runner.money == 2_000_000
    assert champ.offseason_competition_revenue_pending == 3_000_000 + 5_000_000
    m_champ_before = champ.money
    off._process_team_finances()
    assert champ.offseason_competition_revenue_pending == 0
    latest = champ.finance_history[-1]
    br = latest.get("breakdown_revenue") or {}
    assert br.get(OFFSEASON_REV_BREAKDOWN_ASIA_CUP) == 3_000_000
    assert br.get(OFFSEASON_REV_BREAKDOWN_INTERCONTINENTAL) == 5_000_000
    assert champ.money == m_champ_before + int(latest["cashflow"])
