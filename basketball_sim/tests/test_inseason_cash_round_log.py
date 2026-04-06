"""シーズン中リーグ分配ラウンド加算の `inseason_cash_round_log`（正本外）。"""

from basketball_sim.main import generate_teams
from basketball_sim.models.season import (
    INSEASON_LEAGUE_DISTRIBUTION_ROUND_YEN_BY_LEVEL,
    INSEASON_MATCHDAY_ESTIMATE_ROUND_YEN_PER_HOME_GAME,
    Season,
)
from basketball_sim.models.team import (
    INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY,
    INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY,
)


def _expected_income_for_team(team) -> int:
    lv = int(getattr(team, "league_level", 3) or 3)
    default = int(INSEASON_LEAGUE_DISTRIBUTION_ROUND_YEN_BY_LEVEL.get(3, 5_000_000))
    return int(INSEASON_LEAGUE_DISTRIBUTION_ROUND_YEN_BY_LEVEL.get(lv, default))


def test_apply_inseason_league_distribution_writes_log_matching_money() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    rnd = 7
    for t in teams:
        t._ensure_history_fields()
        t.inseason_cash_round_log.clear()

    before = {id(t): int(t.money) for t in teams}
    season._apply_inseason_league_distribution_round(rnd)

    for t in teams:
        exp = _expected_income_for_team(t)
        assert int(t.money) == before[id(t)] + exp
        rows = [e for e in t.inseason_cash_round_log if int(e.get("round_number", -1)) == rnd]
        assert len(rows) == 1
        assert rows[0]["key"] == INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY
        assert int(rows[0]["amount"]) == exp


def test_round_seven_no_matchday_log_when_no_home_games() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    t = teams[0]
    t._ensure_history_fields()
    t.inseason_cash_round_log.clear()
    season._apply_inseason_league_distribution_round(7)
    season._apply_inseason_matchday_estimate_round(7)
    rows = [e for e in t.inseason_cash_round_log if int(e.get("round_number", -1)) == 7]
    assert len(rows) == 1
    assert rows[0]["key"] == INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY


def test_record_inseason_matchday_estimate_round_idempotent_per_round() -> None:
    teams = generate_teams()
    t = teams[0]
    t._ensure_history_fields()
    t.inseason_cash_round_log.clear()
    t.record_inseason_matchday_estimate_round(round_number=4, amount=500_000)
    t.record_inseason_matchday_estimate_round(round_number=4, amount=500_000)
    assert len(t.inseason_cash_round_log) == 1
    assert t.inseason_cash_round_log[0]["amount"] == 500_000
    assert t.inseason_cash_round_log[0]["key"] == INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY


def test_record_inseason_league_distribution_round_idempotent_per_round() -> None:
    teams = generate_teams()
    t = teams[0]
    t._ensure_history_fields()
    t.inseason_cash_round_log.clear()
    t.record_inseason_league_distribution_round(round_number=3, amount=1_234_000)
    t.record_inseason_league_distribution_round(round_number=3, amount=1_234_000)
    assert len(t.inseason_cash_round_log) == 1
    assert t.inseason_cash_round_log[0]["amount"] == 1_234_000


def test_simulate_next_round_appends_both_inseason_keys_when_home_games() -> None:
    teams = generate_teams()
    season = Season(teams, [])
    t0 = teams[0]
    t0._ensure_history_fields()
    t0.inseason_cash_round_log.clear()
    n_before = len(t0.inseason_cash_round_log)
    m_before = int(t0.money)
    season.simulate_next_round()
    assert season.current_round == 1
    homes = season.get_regular_season_home_game_count_for_round(t0, 1)
    unit = int(INSEASON_MATCHDAY_ESTIMATE_ROUND_YEN_PER_HOME_GAME)
    exp_matchday = homes * unit
    exp_league = _expected_income_for_team(t0)
    assert int(t0.money) == m_before + exp_league + exp_matchday
    assert len(t0.inseason_cash_round_log) == n_before + (2 if exp_matchday > 0 else 1)
    r1 = [e for e in t0.inseason_cash_round_log if int(e.get("round_number", -1)) == 1]
    keys = {str(e.get("key")) for e in r1}
    assert INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY in keys
    if exp_matchday > 0:
        assert INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY in keys
        md_rows = [e for e in r1 if e.get("key") == INSEASON_MATCHDAY_ESTIMATE_ROUND_KEY]
        assert len(md_rows) == 1
        assert int(md_rows[0]["amount"]) == exp_matchday
