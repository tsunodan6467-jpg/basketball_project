"""オーナーミッション表示テキスト（get_owner_mission_report_text）。"""

import re

from basketball_sim.models.team import Team, format_cli_owner_mission_screen_header_lines


def test_report_lists_missions_with_category_priority_reward():
    t = Team(team_id=1, name="ReportTeam", league_level=1)
    t.refresh_owner_missions(force=True)
    text = t.get_owner_mission_report_text()
    assert "ReportTeam" in text
    assert "【今季ミッション一覧】" in text
    assert "報酬/ペナルティ" in text
    assert "成績" in text


def test_report_shows_latest_evaluation_detail():
    t = Team(team_id=1, name="HistTeam", league_level=1)
    t.refresh_owner_missions(force=True)
    t.owner_mission_history.append(
        {
            "season_label": "Season 1",
            "owner_expectation": "playoff_race",
            "owner_trust_after": 52,
            "trust_delta_total": 4,
            "results": [
                {
                    "mission_id": "wins_target",
                    "title": "15勝以上を確保",
                    "status": "success",
                    "progress_text": "18勝 / 目標15勝",
                    "trust_delta": 6,
                    "season_label": "Season 1",
                }
            ],
        }
    )
    text = t.get_owner_mission_report_text()
    assert "【直近シーズンの評価】" in text
    assert "Season 1" in text
    assert "達成" in text
    assert "信頼 +6" in text


def test_cli_owner_header_fresh_team_has_placeholders():
    t = Team(team_id=1, name="Fresh", league_level=1)
    lines = format_cli_owner_mission_screen_header_lines(t)
    text = "\n".join(lines)
    assert "【オーナーサマリー】" in text
    assert "【進行状況】" in text
    assert re.search(r"進行中ミッション: (未実行|\d+件)", text)
    assert "履歴なし" in text
    assert "直近評価: 未更新" in text


def test_cli_owner_header_with_history_shows_delta_band():
    t = Team(team_id=1, name="HistTeam2", league_level=1)
    t.refresh_owner_missions(force=True)
    t.owner_mission_history.append(
        {
            "season_label": "Season 2",
            "owner_expectation": "promotion",
            "owner_trust_after": 55,
            "trust_delta_total": -3,
            "results": [
                {
                    "mission_id": "x",
                    "title": "目標A",
                    "status": "fail",
                    "progress_text": "",
                    "trust_delta": -3,
                    "season_label": "Season 2",
                }
            ],
        }
    )
    t.owner_expectation = "promotion"
    text = "\n".join(format_cli_owner_mission_screen_header_lines(t))
    assert "信頼度:" in text and "（" in text
    assert "期待:" in text and "昇格" in text
    assert "評価履歴:" in text and "1件" in text
    assert "直近評価: 悪化" in text
    assert "主な注目点:" in text and "目標A" in text


def test_target_summary_payroll_within_budget():
    m = {
        "target_type": "payroll_within_budget",
        "target_value": 120_000_000,
    }
    s = Team._owner_mission_target_summary(m)
    assert "給与総額" in s and "120" in s
