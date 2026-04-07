"""main.py の 1対1 トレード共用ヘルパ（CLI / GUI）のスモーク。"""

from basketball_sim.main import (
    format_one_for_one_trade_evaluation_text,
    one_for_one_trade_evaluate_and_ai_gate,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.trade_logic import TradeSystem


def _p(pid: int, name: str, tid: int, ovr: int = 60) -> Player:
    return Player(
        player_id=pid,
        name=name,
        age=24,
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
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=500_000,
        contract_years_left=1,
        contract_total_years=1,
        team_id=tid,
    )


def test_format_one_for_one_trade_evaluation_text_smoke() -> None:
    class _E:
        accepts = True
        score = 1
        reasons = ["r1"]

    class _A:
        accepts = False
        score = 2
        reasons = ["r2"]

    s = format_one_for_one_trade_evaluation_text(_E(), _A())
    assert "承認" in s
    assert "拒否" in s
    assert "r1" in s and "r2" in s


def test_one_for_one_trade_evaluate_and_ai_gate_returns_tuple() -> None:
    pa = _p(88001, "GUI_A", 1, ovr=55)
    pb = _p(88002, "GUI_B", 2, ovr=50)
    team_u = Team(team_id=1, name="UserT", league_level=1, money=50_000_000, players=[pa], is_user_team=True)
    team_ai = Team(team_id=2, name="AiT", league_level=1, money=50_000_000, players=[pb])
    ts = TradeSystem()
    out = one_for_one_trade_evaluate_and_ai_gate(ts, team_u, team_ai, pa, pb)
    assert len(out) == 5
    user_eval, ai_eval, accepted, reason, detail = out
    assert hasattr(user_eval, "accepts")
    assert hasattr(ai_eval, "accepts")
    assert isinstance(accepted, bool)
    assert isinstance(reason, str)
