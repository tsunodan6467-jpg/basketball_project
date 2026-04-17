"""
R1 / 締めのみ方式: FA 成立時は年俸ぶんの `money` を即時減算しない。
年俸はオフ `_process_team_finances` の payroll 合算 → `record_financial_result` に載る。

根拠コード（呼び出し順）:
- offseason.run: conduct_free_agency → _process_team_finances
- offseason._calculate_team_expenses: payroll = sum(player.salary)
- free_agent_market.sign_free_agent / free_agency.conduct_free_agency: money 即時減算なし（R1 対応後）
"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_market import inseason_fa_contract_salary, sign_free_agent


def test_r1_close_only_record_paths_match():
    """
    即時減算をしないなら、同じ revenue / expense_total で record した最終 money は一致する（締めのみモデル）。
    """
    m0 = 500_000_000
    revenue = 80_000_000
    expense_total = 150_000_000

    t_a = Team(team_id=1, name="A", league_level=1, money=m0)
    t_a.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:close_only_a",
    )

    t_b = Team(team_id=2, name="B", league_level=1, money=m0)
    t_b.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:close_only_b",
    )

    assert t_a.money == t_b.money


def test_r1_document_legacy_immediate_deduct_would_gap_by_salary():
    """
    旧挙動（即時減算あり）の代数: 同じ expense に payroll が載る前提で、先に S を引くと最終 money は S だけ少ない。
    実装ではこの経路を止め、二重効きを解消している。
    """
    m0 = 500_000_000
    s = 20_000_000
    revenue = 80_000_000
    payroll_total = 100_000_000
    other_expense = 50_000_000
    expense_total = payroll_total + other_expense

    t_double = Team(team_id=1, name="LegacyDouble", league_level=1, money=m0)
    t_double.money -= s
    t_double.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:legacy_simulated",
    )

    t_single = Team(team_id=2, name="CloseOnly", league_level=1, money=m0)
    t_single.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:close_only",
    )

    assert t_double.money == t_single.money - s


def test_sign_free_agent_does_not_immediately_change_team_money():
    """市場 FA: 契約成立直後も `money` は変えない（年俸は締め payroll 側）。"""
    player = Player(
        player_id=99002,
        name="R1_FA_Sign",
        age=26,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=65,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    team = Team(team_id=101, name="R1Team", league_level=1, money=500_000_000, players=[])
    before = team.money
    sign_free_agent(team, player)
    assert team.money == before
    assert player in team.players
    assert player.salary == inseason_fa_contract_salary(team, player)
    roster_payroll = sum(max(0, int(getattr(p, "salary", 0))) for p in team.players)
    assert roster_payroll == player.salary


def test_r1_offseason_call_order_documented_in_offseason_py():
    """conduct_free_agency が _process_team_finances より先に呼ばれること（静的参照用）。"""
    import inspect

    from basketball_sim.models import offseason as off_mod

    src = inspect.getsource(off_mod.Offseason.run)
    assert "conduct_free_agency" in src
    assert "_process_team_finances" in src
    assert src.index("conduct_free_agency") < src.index("_process_team_finances")
