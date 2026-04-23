"""財務レポート表示・record_financial_result の内訳整合。"""

from basketball_sim.models.team import (
    INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY,
    INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY,
    Team,
)
from basketball_sim.systems.finance_report_display import (
    breakdown_matches_total,
    format_cli_finance_screen_header_lines,
    format_finance_report_detail_lines,
    format_inseason_cash_round_log_lines,
    normalize_breakdown_dict,
)


def test_normalize_breakdown_dict():
    assert normalize_breakdown_dict(None) is None
    assert normalize_breakdown_dict({"a": 1, "b": "2"}) == {"a": 1, "b": 2}
    assert normalize_breakdown_dict({}) is None


def test_breakdown_matches_total():
    assert breakdown_matches_total(100, {"x": 40, "y": 60}) is True
    assert breakdown_matches_total(100, {"x": 40}) is False


def test_record_financial_result_keeps_breakdown_when_sums_match():
    t = Team(team_id=1, name="T", league_level=1, money=1_000_000)
    br = {"gate": 600_000, "sponsor": 400_000}
    be = {"payroll": 500_000, "travel": 500_000}
    t.record_financial_result(
        1_000_000,
        1_000_000,
        note="season",
        breakdown_revenue=br,
        breakdown_expense=be,
    )
    last = t.finance_history[-1]
    assert last["breakdown_revenue"] == br
    assert last["breakdown_expense"] == be
    assert t.money == 1_000_000


def test_record_financial_result_drops_mismatched_breakdown():
    t = Team(team_id=1, name="T", league_level=1, money=0)
    t.record_financial_result(
        100,
        50,
        note="x",
        breakdown_revenue={"a": 1},
        breakdown_expense={"b": 50},
    )
    last = t.finance_history[-1]
    assert "breakdown_revenue" not in last
    assert last["breakdown_expense"] == {"b": 50}


def test_format_inseason_cash_round_log_lines_empty():
    t = Team(team_id=1, name="T", league_level=1)
    t._ensure_history_fields()
    t.inseason_cash_round_log.clear()
    lines = format_inseason_cash_round_log_lines(t)
    assert "まだ記録はありません" in "\n".join(lines)


def test_format_inseason_cash_round_log_lines_shows_round_and_amount():
    t = Team(team_id=1, name="T", league_level=1)
    t._ensure_history_fields()
    t.inseason_cash_round_log = [
        {
            "key": INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY,
            "amount": 8_000_000,
            "round_number": 12,
        }
    ]
    text = "\n".join(format_inseason_cash_round_log_lines(t))
    assert "R12" in text
    assert "リーグ分配等" in text
    assert "+800万円" in text


def test_format_inseason_cash_round_log_lines_shows_matchday_label():
    t = Team(team_id=1, name="T", league_level=1)
    t._ensure_history_fields()
    t.inseason_cash_round_log = [
        {
            "key": INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY,
            "amount": 500_000,
            "round_number": 12,
        }
    ]
    text = "\n".join(format_inseason_cash_round_log_lines(t))
    assert "R12" in text
    assert "主場・門前概算" in text
    assert "+0万円" in text


def test_format_cli_finance_screen_header_lines_fresh_team():
    t = Team(team_id=1, name="T", league_level=1)
    t._ensure_history_fields()
    lines = format_cli_finance_screen_header_lines(t)
    text = "\n".join(lines)
    assert "【財務サマリー】" in text
    assert "前季収支: 未更新" in text
    assert "財務履歴: 履歴なし" in text
    assert "【主要内訳】" in text
    assert "情報なし" in text


def test_format_cli_finance_screen_header_lines_with_breakdown_snapshot():
    t = Team(team_id=1, name="T", league_level=1, money=9_000_000)
    t.revenue_last_season = 12_000_000
    t.expense_last_season = 10_000_000
    t.cashflow_last_season = 2_000_000
    t.finance_history = [
        {
            "revenue": 100,
            "expense": 60,
            "cashflow": 40,
            "note": "Wins:10",
            "breakdown_revenue": {"gate": 70, "sponsor": 30},
            "breakdown_expense": {"payroll": 40, "travel": 20},
        }
    ]
    lines = format_cli_finance_screen_header_lines(t)
    text = "\n".join(lines)
    assert "（黒字）" in text
    assert "財務履歴: 1件" in text
    assert "直近収入合計: 0万円" in text
    assert "チケット・興行" in text
    assert "選手給与（年俸）" in text


def test_format_finance_report_detail_lines_with_snapshot():
    t = Team(team_id=1, name="T", league_level=1)
    t.finance_history = [
        {
            "revenue": 100,
            "expense": 60,
            "cashflow": 40,
            "note": "Wins:10",
            "breakdown_revenue": {"gate": 70, "sponsor": 30},
            "breakdown_expense": {"payroll": 40, "travel": 20},
        }
    ]
    lines = format_finance_report_detail_lines(t, history_limit=3)
    text = "\n".join(lines)
    assert "【収入内訳】" in text
    assert "チケット・興行" in text
    assert "【財務推移】" in text
    assert "Wins:10" in text


def test_offseason_revenue_breakdown_sums_to_total():
    from basketball_sim.models.offseason import Offseason

    team = Team(team_id=1, name="X", league_level=1, players=[])

    class _StubOff(Offseason):
        def _get_team_wins(self, t):
            return 15

    stub = _StubOff.__new__(_StubOff)
    total, bd = stub._calculate_team_revenue(team)
    assert sum(bd.values()) == total


def test_offseason_expense_breakdown_sums_to_total():
    from basketball_sim.models.offseason import Offseason

    team = Team(team_id=1, name="X", league_level=1, players=[])

    class _StubOff(Offseason):
        def _get_team_wins(self, t):
            return 12

    stub = _StubOff.__new__(_StubOff)
    total, _pay, _fac, bd = stub._calculate_team_expenses(team)
    assert sum(bd.values()) == total
