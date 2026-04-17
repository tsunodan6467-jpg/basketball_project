"""tactics_cli_display（戦術 CLI 相性サマリー）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.tactics_cli_display import (
    build_tactic_cli_fit_summary,
    format_tactic_cli_summary_lines,
)


def _pl(pid: int, pos: str, **attrs) -> Player:
    base = dict(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=pos,
        height_cm=195.0,
        weight_kg=90.0,
        shoot=55,
        three=55,
        drive=55,
        passing=55,
        handling=55,
        rebound=55,
        defense=55,
        ft=55,
        speed=55,
        stamina=60,
        ovr=60,
        potential="B",
        archetype="wing",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=1,
    )
    base.update(attrs)
    return Player(**base)


def test_tactics_summary_full_roster():
    players = [
        _pl(1, "PG", passing=70, handling=68, three=50, defense=52),
        _pl(2, "SG", three=72, shoot=65, defense=50),
        _pl(3, "SF", three=60, rebound=58, defense=55),
        _pl(4, "PF", rebound=70, power=68, defense=58),
        _pl(5, "C", rebound=72, power=70, defense=60),
        _pl(6, "SG", ovr=52),
        _pl(7, "PF", ovr=50),
        _pl(8, "C", ovr=48),
    ]
    t = Team(team_id=1, name="TacT", league_level=1, players=players)
    t.strategy = "three_point"
    text = "\n".join(format_tactic_cli_summary_lines(t))
    assert "【戦術サマリー】" in text
    assert "外角戦術:" in text
    assert "速攻:" in text
    assert "活かしやすい:" in text
    assert "注意点:" in text
    assert "現在の戦術（スリーポイント偏重）" in text


def test_tactics_summary_short_roster():
    players = [_pl(1, "PG"), _pl(2, "SG"), _pl(3, "SF")]
    t = Team(team_id=2, name="TacS", league_level=1, players=players)
    text = "\n".join(format_tactic_cli_summary_lines(t))
    assert "【戦術サマリー】" in text
    assert "情報なし" in text


def test_tactics_summary_guard_shortage_note():
    """PG 不在なら注意点にガード不足が載る想定。"""
    players = [
        _pl(1, "SG", passing=40, handling=40),
        _pl(2, "SG", passing=40, handling=40),
        _pl(3, "SF"),
        _pl(4, "PF"),
        _pl(5, "C"),
        _pl(6, "PF", ovr=50),
    ]
    t = Team(team_id=3, name="TacG", league_level=1, players=players)
    data = build_tactic_cli_fit_summary(t)
    assert data is not None
    assert "ガード不足" in data["caution"]


def test_tactics_build_returns_none_on_empty_team():
    t = Team(team_id=4, name="TacE", league_level=1, players=[])
    assert build_tactic_cli_fit_summary(t) is None
