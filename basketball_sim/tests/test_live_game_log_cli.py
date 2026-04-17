"""live_game_log_cli（試合中ログ補助）。"""

from basketball_sim.systems.live_game_log_cli import build_live_game_momentum_note


def test_momentum_reversal():
    s = {"last_score_team_key": None, "streak_pts": 0}
    _, line = build_live_game_momentum_note(
        s,
        prev_home=20,
        prev_away=23,
        new_home=24,
        new_away=23,
        home_name="東京",
        away_name="大阪",
        scoring_team_key=1,
        home_team_key=1,
        away_team_key=2,
        points=3,
        quarter=2,
        clock_seconds=400,
    )
    assert line is not None
    assert "逆転" in line


def test_momentum_tie_only():
    s = {"last_score_team_key": None, "streak_pts": 0}
    _, line = build_live_game_momentum_note(
        s,
        prev_home=40,
        prev_away=42,
        new_home=42,
        new_away=42,
        home_name="H",
        away_name="A",
        scoring_team_key=9,
        home_team_key=9,
        away_team_key=8,
        points=2,
        quarter=3,
        clock_seconds=300,
    )
    assert line is not None
    assert "同点" in line


def test_momentum_double_digit_lead():
    s = {"last_score_team_key": None, "streak_pts": 0}
    _, line = build_live_game_momentum_note(
        s,
        prev_home=62,
        prev_away=54,
        new_home=65,
        new_away=54,
        home_name="H",
        away_name="A",
        scoring_team_key=1,
        home_team_key=1,
        away_team_key=2,
        points=3,
        quarter=4,
        clock_seconds=400,
    )
    assert line is not None
    assert "2桁リード" in line


def test_momentum_run_six_zero():
    s = {"last_score_team_key": 1, "streak_pts": 3}
    _, line = build_live_game_momentum_note(
        s,
        prev_home=10,
        prev_away=20,
        new_home=13,
        new_away=20,
        home_name="東京",
        away_name="大阪",
        scoring_team_key=1,
        home_team_key=1,
        away_team_key=2,
        points=3,
        quarter=2,
        clock_seconds=500,
    )
    assert line is not None
    assert "6-0ラン" in line


def test_momentum_zero_points_returns_none():
    s = {"last_score_team_key": None, "streak_pts": 0}
    _, line = build_live_game_momentum_note(
        s,
        prev_home=1,
        prev_away=0,
        new_home=1,
        new_away=0,
        home_name="H",
        away_name="A",
        scoring_team_key=1,
        home_team_key=1,
        away_team_key=2,
        points=0,
        quarter=1,
        clock_seconds=600,
    )
    assert line is None
