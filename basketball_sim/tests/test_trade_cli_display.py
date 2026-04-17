"""trade_cli_display（トレード CLI 得失サマリー）。"""

from basketball_sim.models.player import Player
from basketball_sim.systems.trade_cli_display import format_trade_cli_summary_lines


def _p(pid: int, pos: str, **attrs) -> Player:
    base = dict(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=pos,
        height_cm=200.0,
        weight_kg=100.0,
        shoot=55,
        three=55,
        drive=55,
        passing=55,
        handling=55,
        rebound=55,
        power=55,
        defense=55,
        ft=55,
        stamina=60,
        ovr=60,
        potential="B",
        archetype="big",
        usage_base=20,
        salary=1_000_000,
        contract_years_left=1,
        contract_total_years=1,
        team_id=1,
    )
    base.update(attrs)
    return Player(**base)


def test_trade_summary_one_for_one():
    recv = [_p(1, "C", rebound=78, power=76, defense=68, ovr=66, age=28, potential="C")]
    give = [_p(2, "SG", three=78, shoot=72, passing=55, defense=50, ovr=64, age=22, potential="A")]
    text = "\n".join(format_trade_cli_summary_lines(recv, give))
    assert "【トレード比較】" in text
    assert "受取側:" in text
    assert "放出側:" in text
    assert "方向性:" in text


def test_trade_summary_empty_returns_info():
    assert "情報なし" in "\n".join(format_trade_cli_summary_lines([], [_p(1, "PG")]))
