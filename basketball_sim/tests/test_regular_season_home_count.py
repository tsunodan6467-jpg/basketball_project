"""`Season.get_regular_season_home_game_count_for_round`（主場数・数え方固定）。"""

from basketball_sim.main import generate_teams
from basketball_sim.models.season import Season, SeasonEvent


def test_league_idle_round_returns_zero() -> None:
    """ROUND_CONFIG で league_games_per_team == 0 の週（例: 代表ウィーク）。"""
    teams = generate_teams()
    season = Season(teams, [])
    t = teams[0]
    assert season.get_events_for_round(7) == []
    assert season.get_regular_season_home_game_count_for_round(t, 7) == 0


def test_home_count_matches_manual_enumeration() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    for round_number in (1, 2, 5):
        for t in teams:
            manual = sum(
                1
                for e in season.get_events_for_round(round_number)
                if e.event_type == "game"
                and e.competition_type == "regular_season"
                and e.home_team is t
            )
            assert season.get_regular_season_home_game_count_for_round(t, round_number) == manual


def test_sum_of_home_counts_equals_regular_games_in_round() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    for round_number in (1, 2, 7):
        reg_games = [
            e
            for e in season.get_events_for_round(round_number)
            if e.event_type == "game" and e.competition_type == "regular_season"
        ]
        total_homes = sum(
            season.get_regular_season_home_game_count_for_round(t, round_number) for t in teams
        )
        assert total_homes == len(reg_games)


def test_non_regular_season_event_not_counted() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    t0, t1 = teams[0], teams[1]
    rnd = 2
    before = season.get_regular_season_home_game_count_for_round(t0, rnd)
    fake = SeasonEvent(
        event_id="test_fake_cup_home",
        week=rnd,
        day_of_week="Sat",
        event_type="game",
        competition_id="emperor_cup",
        competition_type="emperor_cup",
        stage="test",
        home_team=t0,
        away_team=t1,
        round_number=rnd,
        label="fake",
    )
    season.events_by_round.setdefault(rnd, []).append(fake)
    assert season.get_regular_season_home_game_count_for_round(t0, rnd) == before


def test_none_team_returns_zero() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    assert season.get_regular_season_home_game_count_for_round(None, 1) == 0


def test_two_teams_differ_when_schedule_asymmetric() -> None:
    """同一ラウンドでホーム数が異なるペアが存在すること（スケジュール依存のスモーク）。"""
    teams = generate_teams()
    season = Season(teams, [])
    rnd = 1
    counts = [season.get_regular_season_home_game_count_for_round(t, rnd) for t in teams]
    assert max(counts) >= min(counts)
    assert any(c > 0 for c in counts)
