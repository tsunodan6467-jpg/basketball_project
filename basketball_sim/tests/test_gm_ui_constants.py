"""gm_ui_constants.apply_team_gm_settings の検証。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.gm_ui_constants import apply_team_gm_settings


def test_apply_team_gm_settings_ok():
    t = Team(team_id=1, name="T", league_level=1)
    ok, msg = apply_team_gm_settings(t, "run_and_gun", "offense", "win_now")
    assert ok is True
    assert msg == ""
    assert t.strategy == "run_and_gun"
    assert t.coach_style == "offense"
    assert t.usage_policy == "win_now"


def test_apply_team_gm_settings_rejects_bad_strategy():
    t = Team(team_id=1, name="T", league_level=1)
    ok, msg = apply_team_gm_settings(t, "invalid_key", "balanced", "balanced")
    assert ok is False
    assert "戦術" in msg
