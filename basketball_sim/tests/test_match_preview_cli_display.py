"""match_preview_cli_display（試合前 CLI プレビュー）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.match_preview_cli_display import (
    build_matchup_edges_summary,
    format_match_preview_cli_lines,
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
        power=55,
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


def _full_team(tid: int, name: str, **starter_attrs) -> Team:
    """先発5＋ベンチ3の最低構成。"""
    players = [
        _pl(1, "PG", **starter_attrs.get("pg", {})),
        _pl(2, "SG", **starter_attrs.get("sg", {})),
        _pl(3, "SF", **starter_attrs.get("sf", {})),
        _pl(4, "PF", **starter_attrs.get("pf", {})),
        _pl(5, "C", **starter_attrs.get("c", {})),
        _pl(6, "SG", ovr=52),
        _pl(7, "PF", ovr=50),
        _pl(8, "C", ovr=48),
    ]
    return Team(team_id=tid, name=name, league_level=1, players=players)


def test_match_preview_shows_header_and_axes():
    u = _full_team(1, "UserS", pg={}, sg={"three": 75, "shoot": 72}, sf={}, pf={}, c={})
    o = _full_team(2, "OppS", pg={}, sg={"three": 45, "shoot": 48}, sf={}, pf={}, c={})
    text = "\n".join(format_match_preview_cli_lines(u, o, user_is_home=True))
    assert "【試合プレビュー】" in text
    assert "対戦: OppS（ホーム）" in text
    assert "外角勝負:" in text
    assert "自チーム優位" in text
    assert "見どころ:" in text
    assert "注目点:" in text


def test_match_preview_away_venue_label():
    u = _full_team(1, "U", pg={}, sg={}, sf={}, pf={}, c={})
    o = _full_team(2, "AwayOpp", pg={}, sg={}, sf={}, pf={}, c={})
    text = "\n".join(format_match_preview_cli_lines(u, o, user_is_home=False))
    assert "アウェイ）" in text


def test_match_preview_short_roster_fallback():
    players = [_pl(1, "PG"), _pl(2, "SG")]
    u = Team(team_id=9, name="Short", league_level=1, players=players)
    o = _full_team(10, "Full", pg={}, sg={}, sf={}, pf={}, c={})
    text = "\n".join(format_match_preview_cli_lines(u, o))
    assert "情報なし" in text
    assert build_matchup_edges_summary(u, o) is None


def test_build_edges_inside_advantage():
    u = _full_team(1, "U", c={"rebound": 80, "power": 78})
    o = _full_team(2, "O", c={"rebound": 45, "power": 44})
    edges = build_matchup_edges_summary(u, o)
    assert edges is not None
    assert edges["inside"] == "自チーム優位"
