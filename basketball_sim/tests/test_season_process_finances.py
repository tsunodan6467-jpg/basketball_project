"""シーズン末 _process_finances（表示のみ・所持金は触らない）。"""

from basketball_sim.models.season import Season
from basketball_sim.models.team import Team


def test_process_finances_does_not_change_team_money():
    t = Team(
        team_id=1,
        name="T",
        league_level=1,
        regular_wins=15,
        popularity=50,
        money=9_000_000,
        players=[],
    )
    before = int(t.money)

    season = Season.__new__(Season)
    season.all_teams = [t]

    season._process_finances()

    assert int(t.money) == before
