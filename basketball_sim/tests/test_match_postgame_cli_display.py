"""match_postgame_cli_display（試合後 CLI サマリー）。"""

import contextlib
import io
from types import SimpleNamespace

from basketball_sim.models.match import Match
from basketball_sim.systems.generator import generate_teams
from basketball_sim.systems import match_postgame_cli_display as mpd
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
    # PF: 比較材料はあるが、PF>0 選手がいるか全員0かは試合依存
    assert ("ファウル（PF）:" in text) or ("PF記録なし" in text)
    assert "PF" in text


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


def _light_match_stub(
    home_id: int,
    away_id: int,
    rows: list,
    hs: int = 90,
    aws: int = 88,
):
    h = SimpleNamespace(name="HomeX", team_id=home_id)
    a = SimpleNamespace(name="AwayX", team_id=away_id)

    class M:
        home_team = h
        away_team = a
        home_score = hs
        away_score = aws

        def get_player_box_score_rows(self):
            return list(rows)

    return M(), h, a


def test_pf_block_reflects_get_player_box_score_rows():
    rows = [
        {
            "team_id": 10,
            "team_name": "HomeX",
            "player_name": "Yamada",
            "minutes": 18.5,
            "pf": 2,
        },
    ]
    m, home, _ = _light_match_stub(10, 20, rows)
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "ファウル（PF）:" in text
    assert "Yamada" in text
    assert "PF 2" in text
    assert "18.5" in text


def test_pf_all_zero_shows_no_foul_line_only_record():
    rows = [
        {
            "team_id": 10,
            "team_name": "HomeX",
            "player_name": "ZeroOnly",
            "minutes": 24.0,
            "pf": 0,
        },
    ]
    m, home, _ = _light_match_stub(10, 20, rows)
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "PF記録なし" in text
    assert "ファウル（PF）:" not in text
    assert "ZeroOnly" not in text


def test_pf_block_user_side_only():
    rows = [
        {
            "team_id": 20,
            "team_name": "AwayX",
            "player_name": "OppFoul",
            "minutes": 20.0,
            "pf": 3,
        },
        {
            "team_id": 10,
            "team_name": "HomeX",
            "player_name": "UserFoul",
            "minutes": 15.0,
            "pf": 1,
        },
    ]
    m, home, _ = _light_match_stub(10, 20, rows)
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "UserFoul" in text
    assert "OppFoul" not in text


def test_format_pf_summary_lines_safe_without_method():
    m = SimpleNamespace()
    h = SimpleNamespace(name="H", team_id=1)
    assert mpd._format_pf_summary_lines(m, h) == []


def test_format_pf_summary_lines_safe_malformed_rows():
    m = SimpleNamespace(
        get_player_box_score_rows=lambda: [
            {"team_id": 1, "player_name": "X", "pf": "bad", "minutes": None}
        ]
    )
    h = SimpleNamespace(name="H", team_id=1)
    out = mpd._format_pf_summary_lines(m, h)
    assert out == ["PF記録なし"]
