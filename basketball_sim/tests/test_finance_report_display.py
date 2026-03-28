"""財務レポート表示・record_financial_result の内訳整合。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.finance_report_display import (
    breakdown_matches_total,
    format_finance_report_detail_lines,
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
