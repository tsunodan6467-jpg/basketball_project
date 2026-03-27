import contextlib
import io

from basketball_sim.models.match import Match
from basketball_sim.models.season import Season
from basketball_sim.systems.generator import generate_teams
from basketball_sim.utils.sim_rng import init_simulation_random


def _collect_regular_season_metrics(seed: int) -> dict:
    init_simulation_random(seed)
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        teams = generate_teams()
        season = Season(teams, free_agents=[])

    score_totals = []
    score_diffs = []
    total_three_made = 0
    total_three_attempts = 0
    total_turnovers = 0
    wins = {t.name: 0 for t in teams}
    losses = {t.name: 0 for t in teams}
    game_count = 0

    for round_no in range(1, season.total_rounds + 1):
        for event in season.get_events_for_round(round_no):
            if event.event_type != "game":
                continue
            if event.competition_type != "regular_season":
                continue
            if event.home_team is None or event.away_team is None:
                continue

            with contextlib.redirect_stdout(sink):
                match = Match(
                    home_team=event.home_team,
                    away_team=event.away_team,
                    is_playoff=False,
                    competition_type="regular_season",
                )
                _, home_score, away_score = match.simulate()

            game_count += 1
            score_totals.append(home_score + away_score)
            score_diffs.append(abs(home_score - away_score))

            if home_score > away_score:
                wins[event.home_team.name] += 1
                losses[event.away_team.name] += 1
            else:
                wins[event.away_team.name] += 1
                losses[event.home_team.name] += 1

            for row in match.play_by_play_log:
                r = row.get("event_type")
                if r in {"made_3", "miss_3"}:
                    total_three_attempts += 1
                    if r == "made_3":
                        total_three_made += 1
                elif r == "turnover":
                    total_turnovers += 1

    win_pcts = []
    for team in teams:
        w = wins.get(team.name, 0)
        l = losses.get(team.name, 0)
        g = w + l
        if g > 0:
            win_pcts.append(w / g)

    return {
        "game_count": game_count,
        "avg_total_score": sum(score_totals) / max(1, len(score_totals)),
        "avg_score_diff": sum(score_diffs) / max(1, len(score_diffs)),
        "three_pt_rate": total_three_made / max(1, total_three_attempts),
        "turnovers_per_team_game": total_turnovers / max(1, game_count * 2),
        "win_pct_gap": (max(win_pcts) - min(win_pcts)) if win_pcts else 0.0,
    }


def test_regular_season_balance_guard_multi_season():
    seeds = [20260327, 20260328, 20260329]
    metrics = [_collect_regular_season_metrics(seed) for seed in seeds]

    total_games = sum(m["game_count"] for m in metrics)
    avg_total_score = sum(m["avg_total_score"] * m["game_count"] for m in metrics) / max(1, total_games)
    avg_score_diff = sum(m["avg_score_diff"] * m["game_count"] for m in metrics) / max(1, total_games)
    three_pt_rate = sum(m["three_pt_rate"] * m["game_count"] for m in metrics) / max(1, total_games)
    turnovers_per_team_game = (
        sum(m["turnovers_per_team_game"] * m["game_count"] for m in metrics) / max(1, total_games)
    )
    max_win_pct_gap = max(m["win_pct_gap"] for m in metrics)

    assert total_games >= 1800
    assert 130.0 <= avg_total_score <= 210.0
    assert 5.0 <= avg_score_diff <= 35.0
    assert 0.20 <= three_pt_rate <= 0.50
    assert 3.0 <= turnovers_per_team_game <= 25.0
    assert max_win_pct_gap <= 0.75
