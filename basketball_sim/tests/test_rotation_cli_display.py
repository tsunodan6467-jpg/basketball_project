"""rotation_cli_display（布陣 CLI サマリー）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.rotation_cli_display import format_rotation_cli_summary_lines


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
        rebound=55,
        defense=55,
        ft=55,
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


def test_rotation_summary_with_full_roster():
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
    t = Team(team_id=1, name="RotT", league_level=1, players=players)
    text = "\n".join(format_rotation_cli_summary_lines(t))
    assert "【布陣サマリー】" in text
    assert "強み:" in text
    assert "弱み:" in text
    assert "注意点:" in text
    assert "ベンチ厚み:" in text


def test_rotation_summary_short_bench():
    players = [
        _pl(1, "PG"),
        _pl(2, "SG"),
        _pl(3, "SF"),
        _pl(4, "PF"),
        _pl(5, "C"),
        _pl(6, "SG", ovr=45),
    ]
    t = Team(team_id=2, name="RotS", league_level=1, players=players)
    text = "\n".join(format_rotation_cli_summary_lines(t))
    assert "薄い" in text or "ベンチ厚み:" in text
