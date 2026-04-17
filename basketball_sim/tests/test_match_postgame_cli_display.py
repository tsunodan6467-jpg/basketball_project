"""match_postgame_cli_display（試合後 CLI サマリー）。"""

import contextlib
import io

from basketball_sim.models.match import Match
from basketball_sim.systems.generator import generate_teams
from basketball_sim.systems.match_postgame_cli_display import (
    build_postgame_edges_summary,
    format_match_postgame_cli_lines,
)


def test_postgame_summary_after_full_match():
    teams = generate_teams()
    home = teams[0]
    away = teams[1]
    home.is_user_team = True
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        match = Match(home_team=home, away_team=away, is_playoff=False, competition_type="regular_season")
        match.simulate()
    text = "\n".join(format_match_postgame_cli_lines(match, home))
    assert "【試合後サマリー】" in text
    assert "結果:" in text
    assert "外角勝負:" in text
    assert "守備強度:" in text
    assert "勝因:" in text
    assert "敗因:" in text
    assert "分岐点:" in text


def test_build_postgame_edges_from_pbp():
    teams = generate_teams()
    home = teams[2]
    away = teams[3]
    home.is_user_team = True
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        match = Match(home_team=home, away_team=away, is_playoff=False, competition_type="regular_season")
        match.simulate()
    edges = build_postgame_edges_summary(match, home)
    assert edges is not None
    assert edges.get("_source") == "pbp"
    for k in ("outside", "inside", "handler", "bench", "defense"):
        assert edges.get(k) in ("上回った", "下回った", "五分")
