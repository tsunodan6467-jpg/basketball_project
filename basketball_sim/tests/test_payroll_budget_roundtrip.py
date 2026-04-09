"""save→load round-trip で user team の payroll_budget が不変であることの最小検証。"""

from __future__ import annotations

from pathlib import Path

from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import find_user_team, load_world, save_world, validate_payload


def test_user_team_payroll_budget_roundtrip_unchanged(tmp_path: Path) -> None:
    """load が payroll_budget を変えていないことの切り分け（原因整理メモの次手）。"""
    path = tmp_path / "payroll_budget_rt.sav"
    uid = 42
    expected_budget = 123_456_789
    expected_money = 2_000_000_000
    team = Team(
        team_id=uid,
        name="Budget RT FC",
        league_level=1,
        is_user_team=True,
        money=expected_money,
        payroll_budget=expected_budget,
    )
    payload_in = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": uid,
        "season_count": 1,
        "at_annual_menu": True,
        "tracked_player_name": None,
    }
    save_world(path, payload_in)
    out = load_world(path)
    validate_payload(out)
    user = find_user_team(out["teams"], uid)
    assert user.payroll_budget == expected_budget
    assert int(getattr(user, "money", 0)) == expected_money
    assert bool(getattr(user, "is_user_team", False)) is True
