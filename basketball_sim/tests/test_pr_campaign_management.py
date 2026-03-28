"""広報・ファン施策（週次ガード・management）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.pr_campaign_management import (
    MAX_ACTIONS_PER_ROUND,
    commit_pr_campaign,
    format_pr_status_line,
    sync_pr_round_quota,
)


class _Season:
    def __init__(self, cr: int, finished: bool = False) -> None:
        self.current_round = cr
        self.season_finished = finished


def test_commit_success_user_in_season():
    t = Team(team_id=1, name="P", league_level=1, is_user_team=True, money=5_000_000, popularity=50, fan_base=1000)
    s = _Season(4)
    ok, msg = commit_pr_campaign(t, "sns_buzz", s)
    assert ok is True
    assert t.money < 5_000_000
    assert t.popularity >= 50
    assert t.fan_base > 1000
    assert t.management["pr_campaigns"]["count_this_round"] == 1
    assert "実施" in msg


def test_weekly_cap():
    t = Team(team_id=2, name="Q", league_level=1, is_user_team=True, money=20_000_000)
    s = _Season(5)
    for _ in range(MAX_ACTIONS_PER_ROUND):
        ok, _ = commit_pr_campaign(t, "sns_buzz", s)
        assert ok is True
    ok, msg = commit_pr_campaign(t, "sns_buzz", s)
    assert ok is False
    assert "上限" in msg


def test_round_change_resets_count():
    t = Team(team_id=3, name="R", league_level=1, is_user_team=True, money=20_000_000)
    s = _Season(1)
    commit_pr_campaign(t, "sns_buzz", s)
    commit_pr_campaign(t, "sns_buzz", s)
    s.current_round = 2
    sync_pr_round_quota(t, s)
    assert t.management["pr_campaigns"]["count_this_round"] == 0


def test_blocks_when_finished():
    t = Team(team_id=4, name="S", league_level=1, is_user_team=True, money=5_000_000)
    s = _Season(3, finished=True)
    ok, msg = commit_pr_campaign(t, "sns_buzz", s)
    assert ok is False
    assert "終了" in msg


def test_cpu_rejected():
    t = Team(team_id=5, name="C", league_level=1, is_user_team=False, money=5_000_000)
    s = _Season(2)
    ok, msg = commit_pr_campaign(t, "sns_buzz", s)
    assert ok is False


def test_format_status_shows_remaining():
    t = Team(team_id=6, name="U", league_level=1, is_user_team=True, money=5_000_000)
    s = _Season(7)
    text = format_pr_status_line(t, s)
    assert "ラウンド" in text or "round" in text
    assert "2" in text or "回" in text
