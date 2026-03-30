"""昇降格処理: Team を set 要素にしない（デバッグ simulate_to_end 等の回帰）。"""

from basketball_sim.models.season import Season
from basketball_sim.models.team import Team


def _make_team(tid: int, name: str, level: int, wins: int) -> Team:
    return Team(
        team_id=tid,
        name=name,
        league_level=level,
        regular_wins=wins,
        regular_losses=10,
        regular_points_for=80,
        regular_points_against=75,
        players=[],
    )


def test_process_promotion_relegation_runs_without_typeerror():
    """旧実装は set(Team) で TypeError。team_id キー集合へ変更後も完走すること。"""
    d1 = [_make_team(100 + i, f"D1T{i}", 1, 30 - i) for i in range(10)]
    d2 = [_make_team(200 + i, f"D2T{i}", 2, 25 - i) for i in range(10)]
    d3 = [_make_team(300 + i, f"D3T{i}", 3, 20 - i) for i in range(10)]
    leagues = {1: d1, 2: d2, 3: d3}

    season = Season.__new__(Season)
    season.leagues = leagues
    season._record_competition_team_result = lambda **kwargs: None

    bottom_two = d1[-2:]

    def fake_floor(leagues_arg, level):
        return list(bottom_two) if level == 1 else []

    season._teams_below_payroll_floor = fake_floor

    def promote(playoff_results, eligible, src_level, needed):
        return eligible[:needed] if needed > 0 else []

    season._promotion_candidates_from_division = promote

    # 以前はここで TypeError: unhashable type: 'Team'
    season._process_promotion_relegation(leagues, {})

    assert all(t.league_level == 2 for t in bottom_two)
