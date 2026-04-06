"""トレード現金を history_transactions 上で機械可読に残すこと（TRADE_CASH_ACCOUNTING_POLICY）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.trade_logic import MultiTradeOffer, TradeSystem


def _jp_player(pid: int, name: str, team_id: int) -> Player:
    return Player(
        player_id=pid,
        name=name,
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=180.0,
        weight_kg=75.0,
        shoot=50,
        three=50,
        drive=50,
        passing=50,
        rebound=50,
        defense=50,
        ft=50,
        stamina=50,
        ovr=50,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=800_000,
        contract_years_left=1,
        contract_total_years=1,
        team_id=team_id,
    )


def _cash_rows(team: Team) -> list:
    return [r for r in getattr(team, "history_transactions", []) if "trade_cash_delta" in r]


def test_multi_trade_with_cash_writes_structured_fields():
    pa = _jp_player(91001, "P_A", 1)
    pb = _jp_player(91002, "P_B", 2)
    team_a = Team(team_id=1, name="Alpha", league_level=3, money=100_000_000, players=[pa])
    team_b = Team(team_id=2, name="Beta", league_level=3, money=100_000_000, players=[pb])
    cash_amt = 4_500_000
    offer = MultiTradeOffer(
        team_a_gives_players=[pa],
        team_a_receives_players=[pb],
        cash_a_to_b=cash_amt,
        rookie_budget_a_to_b=0,
    )
    ts = TradeSystem()
    assert ts.execute_multi_trade(team_a, team_b, offer, free_agents=[])

    rows_a = _cash_rows(team_a)
    rows_b = _cash_rows(team_b)
    assert len(rows_a) == 1
    assert len(rows_b) == 1
    assert rows_a[0]["trade_cash_delta"] == -cash_amt
    assert rows_a[0]["trade_counterparty_team_id"] == 2
    assert rows_a[0]["trade_counterparty_name"] == "Beta"
    assert rows_b[0]["trade_cash_delta"] == cash_amt
    assert rows_b[0]["trade_counterparty_team_id"] == 1
    assert rows_b[0]["trade_counterparty_name"] == "Alpha"

    assert team_a.money == 100_000_000 - cash_amt
    assert team_b.money == 100_000_000 + cash_amt


def test_multi_trade_zero_cash_has_no_trade_cash_delta_rows():
    pa = _jp_player(92001, "Q_A", 1)
    pb = _jp_player(92002, "Q_B", 2)
    team_a = Team(team_id=1, name="A2", league_level=3, money=50_000_000, players=[pa])
    team_b = Team(team_id=2, name="B2", league_level=3, money=50_000_000, players=[pb])
    offer = MultiTradeOffer(
        team_a_gives_players=[pa],
        team_a_receives_players=[pb],
        cash_a_to_b=0,
        rookie_budget_a_to_b=0,
    )
    ts = TradeSystem()
    assert ts.execute_multi_trade(team_a, team_b, offer, free_agents=[])
    assert _cash_rows(team_a) == []
    assert _cash_rows(team_b) == []


def test_structured_cash_readable_without_parsing_note():
    """note に依存せず trade_cash_delta / counterparty で復元できる。"""
    pa = _jp_player(93001, "R_A", 1)
    pb = _jp_player(93002, "R_B", 2)
    team_a = Team(team_id=10, name="TeeA", league_level=3, money=80_000_000, players=[pa])
    team_b = Team(team_id=20, name="TeeB", league_level=3, money=80_000_000, players=[pb])
    offer = MultiTradeOffer(
        team_a_gives_players=[pa],
        team_a_receives_players=[pb],
        cash_a_to_b=1_000_000,
        rookie_budget_a_to_b=0,
    )
    TradeSystem().execute_multi_trade(team_a, team_b, offer, free_agents=[])
    for row in team_a.history_transactions:
        if "trade_cash_delta" in row:
            assert int(row["trade_cash_delta"]) == -1_000_000
            assert int(row["trade_counterparty_team_id"]) == 20
            assert row["trade_counterparty_name"] == "TeeB"
            break
    else:
        raise AssertionError("expected structured cash row on team_a")
