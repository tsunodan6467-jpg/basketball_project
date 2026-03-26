"""Step 2: 契約年数進行・満了・再契約/延長API。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import (
    advance_contract_years,
    apply_contract_extension,
    apply_resign,
    calculate_resign_score,
    evaluate_resign_offer,
)


def _p(pid: int, years: int, nat: str = "Japan") -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=26,
        nationality=nat,
        position="SF",
        height_cm=200.0,
        weight_kg=90.0,
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
        archetype="wing",
        usage_base=20,
        contract_years_left=years,
        contract_total_years=years,
        salary=5_000_000,
    )


def test_advance_contract_years_expires_and_fa():
    t = Team(team_id=1, name="T", league_level=1)
    p = _p(1, 1)
    t.add_player(p)
    fa: list = []
    moved = advance_contract_years([t], fa, skip_player_ids=set())
    assert len(t.players) == 0
    assert p in fa
    assert moved and moved[0][0] is p
    assert getattr(p, "contract_years_left", 1) <= 0


def test_advance_skips_re_signed_ids():
    t = Team(team_id=1, name="T", league_level=1)
    p = _p(2, 3)
    t.add_player(p)
    fa: list = []
    advance_contract_years([t], fa, skip_player_ids={2})
    assert len(t.players) == 1
    assert p.contract_years_left == 3


def test_apply_contract_extension_adds_years():
    t = Team(team_id=1, name="T", league_level=1)
    p = _p(3, 1)
    t.add_player(p)
    apply_contract_extension(t, p, add_years=1)
    assert p.contract_years_left == 2
    assert p.contract_last_action == "extension"


def test_evaluate_resign_offer_returns_dict():
    t = Team(team_id=1, name="T", league_level=1)
    p = _p(4, 1)
    t.add_player(p)
    r = evaluate_resign_offer(
        player=p,
        team=t,
        offered_salary=max(getattr(p, "salary", 0), 1_000_000),
        offered_years=2,
    )
    assert "score" in r and "threshold" in r and "accepted" in r


def test_apply_resign_sets_action():
    t = Team(team_id=1, name="T", league_level=1)
    p = _p(5, 1)
    t.add_player(p)
    apply_resign(t, p, 6_000_000, 2)
    assert p.contract_years_left == 2
    assert p.contract_last_action == "resign"


def test_resign_score_higher_with_longer_tenure():
    """同一条件で在籍年が長いほど再契約スコアが上がる（引き留めボーナス）。"""
    team = Team(team_id=1, name="T", league_level=2, last_season_wins=15, regular_wins=15)
    short = _p(10, 1)
    short.team_id = 1
    short.last_contract_team_id = 1
    short.league_years = 1
    short.loyalty = 60
    short.desired_salary = 5_000_000
    short.desired_years = 2

    long = _p(11, 1)
    long.team_id = 1
    long.last_contract_team_id = 1
    long.league_years = 6
    long.loyalty = 60
    long.desired_salary = 5_000_000
    long.desired_years = 2

    offer = 5_000_000
    years = 2
    s_short = calculate_resign_score(team, short, offer, years)
    s_long = calculate_resign_score(team, long, offer, years)
    assert s_long > s_short
