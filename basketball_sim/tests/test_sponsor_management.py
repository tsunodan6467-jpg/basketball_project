"""メインスポンサー契約（management・sponsor_power）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.sponsor_management import (
    commit_main_sponsor_contract,
    ensure_sponsor_management_on_team,
    format_sponsor_history_lines,
)


def test_ensure_initializes_sponsors():
    t = Team(team_id=1, name="S", league_level=1)
    ensure_sponsor_management_on_team(t)
    assert isinstance(t.management, dict)
    assert t.management.get("version", 0) >= 1
    sp = t.management["sponsors"]
    assert sp["main_contract_type"] in {"local", "standard", "national", "title"}
    assert isinstance(sp["history"], list)


def test_commit_nudges_sponsor_power_user_only():
    t = Team(team_id=1, name="U", league_level=1, is_user_team=True, sponsor_power=50)
    ok, msg = commit_main_sponsor_contract(t, "title")
    assert ok is True
    assert t.management["sponsors"]["main_contract_type"] == "title"
    assert t.sponsor_power > 50
    assert len(t.management["sponsors"]["history"]) == 1
    assert "反映" in msg or "更新" in msg


def test_commit_rejects_cpu_team():
    t = Team(team_id=2, name="C", league_level=1, is_user_team=False)
    ok, msg = commit_main_sponsor_contract(t, "national")
    assert ok is False
    assert "自チーム" in msg


def test_format_history_empty():
    t = Team(team_id=3, name="H", league_level=1)
    lines = format_sponsor_history_lines(t)
    assert len(lines) == 1
    assert "まだ" in lines[0]
