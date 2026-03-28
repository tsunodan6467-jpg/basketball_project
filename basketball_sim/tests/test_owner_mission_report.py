"""オーナーミッション表示テキスト（get_owner_mission_report_text）。"""

from basketball_sim.models.team import Team


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


def test_target_summary_payroll_within_budget():
    m = {
        "target_type": "payroll_within_budget",
        "target_value": 120_000_000,
    }
    s = Team._owner_mission_target_summary(m)
    assert "給与総額" in s and "120" in s
