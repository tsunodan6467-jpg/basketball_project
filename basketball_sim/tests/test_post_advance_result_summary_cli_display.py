"""post_advance_result_summary_cli_display: 進行後結果サマリー。"""

from __future__ import annotations

from basketball_sim.systems.post_advance_result_summary_cli_display import (
    format_post_advance_result_summary_lines,
)


def _user(name: str = "User"):
    class _T:
        def __init__(self) -> None:
            self.name = name

    return _T()


def test_home_win_shows_circle_and_scores() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "UserFC", "away_team": "Other", "home_score": 82, "away_score": 76}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "○ UserFC 82 - 76 Other" in text
    assert "自チーム試合: 1 試合" in text


def test_away_loss_shows_filled_circle() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "Other", "away_team": "UserFC", "home_score": 90, "away_score": 70}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "● UserFC 70 - 90 Other" in text


def test_two_user_games_one_win_one_loss() -> None:
    u = _user("UserFC")
    rows = [
        {"home_team": "UserFC", "away_team": "A", "home_score": 67, "away_score": 87},
        {"home_team": "UserFC", "away_team": "B", "home_score": 85, "away_score": 61},
    ]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "自チーム試合: 2 試合" in text
    assert "1勝1敗" in text


def test_no_user_games_in_new_results() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "A", "away_team": "B", "home_score": 80, "away_score": 70}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "自チーム試合: 0 試合" in text
    assert "このラウンドの自チーム試合結果はありません。" in text


def test_empty_new_results() -> None:
    u = _user("UserFC")
    lines = format_post_advance_result_summary_lines(u, [])
    assert isinstance(lines, list)
    assert "自チーム試合: 0 試合" in "\n".join(lines)


def test_invalid_scores_do_not_crash() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "UserFC", "away_team": "Other", "home_score": "x", "away_score": 70}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "？" in text
    assert "結果不明" in text
    assert "1試合の結果を確認できませんでした。" in text
    assert "このラウンドの自チーム試合結果はありません。" not in text


def test_unknown_score_uses_unknown_one_liner() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "UserFC", "away_team": "Other", "home_score": "x", "away_score": 70}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "自チーム試合: 1 試合" in text
    assert "1試合の結果を確認できませんでした。" in text


def test_mixed_result_and_unknown_score_one_liner() -> None:
    u = _user("UserFC")
    rows = [
        {"home_team": "UserFC", "away_team": "A", "home_score": 80, "away_score": 70},
        {"home_team": "UserFC", "away_team": "B", "home_score": "x", "away_score": 60},
    ]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "自チーム試合: 2 試合" in text
    assert "1勝0敗、1試合結果不明" in text
    assert "このラウンドの自チーム試合結果はありません。" not in text


def test_max_games_limits_and_shows_remaining() -> None:
    u = _user("UserFC")
    rows = [
        {"home_team": "UserFC", "away_team": f"O{i}", "home_score": 80, "away_score": 70}
        for i in range(7)
    ]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows, max_games=5))
    assert "自チーム試合: 7 試合" in text
    assert "ほか 2 試合" in text


def test_round_label_in_output() -> None:
    u = _user("UserFC")
    text = "\n".join(
        format_post_advance_result_summary_lines(u, [], round_label="ラウンド 6/33")
    )
    assert "対象: ラウンド 6/33" in text


def test_user_team_none_shows_zero_games() -> None:
    lines = format_post_advance_result_summary_lines(
        None,
        [{"home_team": "A", "away_team": "B", "home_score": 1, "away_score": 2}],
    )
    assert "自チーム試合: 0 試合" in "\n".join(lines)


def test_draw_shows_triangle() -> None:
    u = _user("UserFC")
    rows = [{"home_team": "UserFC", "away_team": "Other", "home_score": 70, "away_score": 70}]
    text = "\n".join(format_post_advance_result_summary_lines(u, rows))
    assert "△ UserFC 70 - 70 Other" in text
    assert "1分" in text
