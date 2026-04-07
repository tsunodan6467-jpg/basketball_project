"""CLI トレード相手候補（全ディビジョン・自チーム除外）。"""

from basketball_sim.main import get_trade_candidate_teams
from basketball_sim.models.team import Team


def test_trade_candidates_include_all_divisions_when_user_in_d1() -> None:
    user = Team(team_id=1, name="UserClub", league_level=1)
    d1b = Team(team_id=2, name="D1B", league_level=1)
    d2a = Team(team_id=3, name="D2A", league_level=2)
    d3a = Team(team_id=4, name="D3A", league_level=3)
    all_teams = [user, d1b, d2a, d3a]
    c = get_trade_candidate_teams(all_teams, user)
    assert len(c) == 3
    assert user not in c
    ids = {t.team_id for t in c}
    assert ids == {2, 3, 4}
    levels = {t.league_level for t in c}
    assert levels == {1, 2, 3}


def test_trade_candidates_exclude_only_user_when_user_in_d3() -> None:
    user = Team(team_id=10, name="UserD3", league_level=3)
    d1a = Team(team_id=11, name="D1X", league_level=1)
    d2a = Team(team_id=12, name="D2X", league_level=2)
    d3b = Team(team_id=13, name="D3Peer", league_level=3)
    all_teams = [d1a, d2a, user, d3b]
    c = get_trade_candidate_teams(all_teams, user)
    assert len(c) == 3
    assert user not in c
    assert {t.team_id for t in c} == {11, 12, 13}


def test_trade_candidates_sorted_by_division_then_name() -> None:
    user = Team(team_id=1, name="U", league_level=2)
    t_d1b = Team(team_id=2, name="B_D1", league_level=1)
    t_d1a = Team(team_id=3, name="A_D1", league_level=1)
    t_d3 = Team(team_id=4, name="Z_D3", league_level=3)
    all_teams = [t_d3, user, t_d1b, t_d1a]
    c = get_trade_candidate_teams(all_teams, user)
    assert [t.name for t in c] == ["A_D1", "B_D1", "Z_D3"]
