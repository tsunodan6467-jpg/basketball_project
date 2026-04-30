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
    assert "戦術メモ:" in text
    assert "基本方針:" in text
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
    home_team_fouls_by_quarter: dict | None = None,
    away_team_fouls_by_quarter: dict | None = None,
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

    M.home_team_fouls_by_quarter = dict(home_team_fouls_by_quarter or {})
    M.away_team_fouls_by_quarter = dict(away_team_fouls_by_quarter or {})
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


def test_team_foul_block_shows_quarter_values_and_ot_label():
    rows = [
        {"team_id": 10, "team_name": "HomeX", "player_name": "Yamada", "minutes": 18.5, "pf": 2},
    ]
    m, home, _ = _light_match_stub(
        10,
        20,
        rows,
        home_team_fouls_by_quarter={1: 2, 2: 3, 5: 1},
        away_team_fouls_by_quarter={1: 1, 2: 4, 5: 0},
    )
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "チームファウル:" in text
    assert "HomeX" in text
    assert "AwayX" in text
    assert "Q1 2" in text
    assert "Q2 3" in text
    assert "OT1 1" in text


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


def test_tactics_memo_shows_team_and_team_strategy_and_playbook():
    rows = [{"team_id": 10, "team_name": "HomeX", "player_name": "Yamada", "minutes": 20.0, "pf": 1}]
    m, home, _ = _light_match_stub(10, 20, rows)
    home.players = []
    home.strategy = "run_and_gun"
    home.coach_style = "offense"
    home.usage_policy = "win_now"
    home.team_tactics = {
        "version": 1,
        "team_strategy": {
            "offense_tempo": "fast",
            "offense_style": "three_point",
            "offense_creation": "ball_move",
            "defense_style": "pressure",
            "rebound_style": "balanced",
            "transition_style": "push",
        },
        "playbook": {
            "pick_and_roll": "standard",
            "spain_pick_and_roll": "standard",
            "handoff": "standard",
            "off_ball_screen": "standard",
            "post_up": "low",
            "transition": "high",
        },
    }
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "戦術メモ:" in text
    assert "基本方針:" in text
    assert "ラン＆ガン" in text
    assert "攻撃重視" in text
    assert "勝利優先（今を勝つ）" in text
    assert "攻守詳細:" in text
    assert "セット傾向:" in text
    assert "速攻頻度高" in text or "ポスト低" in text
    assert "ファウル（PF）:" in text
    assert "Yamada" in text


def test_tactics_memo_empty_when_user_team_none():
    m = SimpleNamespace(home_team=None, away_team=None)
    assert mpd._format_tactics_context_lines(m, None) == []


def test_tactics_memo_does_not_break_edges_none_branch():
    rows = [{"team_id": 10, "team_name": "HomeX", "player_name": "A", "minutes": 1.0, "pf": 0}]
    m, home, _ = _light_match_stub(10, 20, rows, hs=50, aws=50)
    home.players = []
    home.strategy = "inside"
    home.coach_style = "defense"
    home.usage_policy = "balanced"
    # 比較不能に近いが戦術メモは出る
    text = "\n".join(format_match_postgame_cli_lines(m, home))
    assert "戦術メモ:" in text
    assert "インサイド" in text
    assert "PF記録なし" in text
