"""Team.record_season_history と division 行のマージ（二重行防止）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


def _minimal_player(pid: int = 1) -> Player:
    return Player(
        player_id=pid,
        name="Test",
        age=24,
        nationality="Japan",
        position="PG",
        height_cm=180.0,
        weight_kg=75.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=70,
        potential="B",
        archetype="scoring_guard",
        usage_base=20,
        is_retired=False,
        season_points=100,
    )


def test_record_season_history_merges_top_players_into_last_row():
    t = Team(team_id=1, name="MergeClub", league_level=1)
    t.players = [_minimal_player()]
    t.regular_wins = 30
    t.regular_losses = 10
    t.regular_points_for = 3000
    t.regular_points_against = 2800
    t.history_seasons.append(
        {
            "season_index": 1,
            "league_level": 1,
            "rank": 2,
            "wins": 30,
            "losses": 10,
            "win_pct": 0.75,
            "points_for": 3000,
            "points_against": 2800,
            "point_diff": 200,
        }
    )
    t.record_season_history()
    assert len(t.history_seasons) == 1
    tops = t.history_seasons[0].get("top_players") or []
    assert len(tops) >= 1
    assert tops[0].get("player_name") == "Test"


def test_record_season_history_appends_when_last_already_has_top_players():
    t = Team(team_id=2, name="AppendClub", league_level=1)
    t.players = [_minimal_player(2)]
    t.regular_wins = 5
    t.regular_losses = 5
    t.history_seasons.append(
        {
            "season_index": 1,
            "top_players": [{"player_name": "Old", "ovr": 50}],
        }
    )
    t.record_season_history()
    assert len(t.history_seasons) == 2
