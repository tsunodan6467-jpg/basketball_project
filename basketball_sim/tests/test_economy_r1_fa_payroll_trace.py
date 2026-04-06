"""
R1 検証: FA 署名時の即時 money 減算と、オフ締め record の expense（ペイロール含む）の関係。

本番ロジックは変更しない。代数モデルで「同じ年俸 S が二重に money を押す」ことを固定する。
根拠コード:
- free_agency.conduct_free_agency: team.money -= offer（年俸相当）
- offseason._calculate_team_expenses: payroll = sum(player.salary)
- offseason.run 順序: conduct_free_agency の直後に _process_team_finances
- team.record_financial_result: money += revenue - expense
"""

from basketball_sim.models.team import Team


def test_r1_algebra_same_salary_in_immediate_deduct_and_record_expense():
    """
    オフ締めが算出する expense_total に、その年の roster ペイロール（新規 FA の年俸 S を含む）が
    一度入り、かつ FA 成立時に既に money から S を引いている場合、
    「record のみで締める」場合と比べて最終 money はちょうど S だけ少ない（= 年俸 S が二重効き）。
    """
    m0 = 500_000_000
    s = 20_000_000
    revenue = 80_000_000
    # expense_total は _calculate_team_expenses 風に「ペイロール + その他」
    payroll_total = 100_000_000  # 新規 FA 含む前提の合計
    other_expense = 50_000_000
    expense_total = payroll_total + other_expense

    t_double = Team(team_id=1, name="DoublePath", league_level=1, money=m0)
    t_double.money -= s
    t_double.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:FA_deduct_then_close",
    )
    money_double_path = t_double.money

    t_single = Team(team_id=2, name="SinglePath", league_level=1, money=m0)
    t_single.record_financial_result(
        revenue=revenue,
        expense=expense_total,
        note="R1_trace:close_only",
    )
    money_single_path = t_single.money

    assert money_double_path == money_single_path - s


def test_r1_offseason_call_order_documented_in_offseason_py():
    """conduct_free_agency が _process_team_finances より先に呼ばれること（静的参照用）。"""
    import inspect

    from basketball_sim.models import offseason as off_mod

    src = inspect.getsource(off_mod.Offseason.run)
    assert "conduct_free_agency" in src
    assert "_process_team_finances" in src
    assert src.index("conduct_free_agency") < src.index("_process_team_finances")
