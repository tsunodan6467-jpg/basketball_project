"""`_calculate_offer_diagnostic` は `_calculate_offer` と最終額が一致すること（観測用・本番未接続）。"""

from basketball_sim.models.offseason import _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems import free_agency as fa_mod
from basketball_sim.systems.salary_cap_budget import get_soft_cap


def _roster_player(pid: int, salary: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=60,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=1,
        contract_total_years=2,
        team_id=1,
    )


def _fa_player(pid: int, *, ovr: int = 72, salary: int = 4_000_000) -> Player:
    return Player(
        player_id=pid,
        name="FA",
        age=25,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def _assert_diagnostic_matches(team: Team, fa: Player) -> None:
    d = fa_mod._calculate_offer_diagnostic(team, fa)
    c = int(fa_mod._calculate_offer(team, fa))
    assert d["final_offer"] == c, (d, c)


def test_diagnostic_matches_calculate_offer_soft_cap_early():
    """S1: payroll_before >= soft_cap → 即 0。"""
    sc = int(get_soft_cap(league_level=1))
    roster = _roster_player(1, sc)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = sc + 50_000_000
    fa = _fa_player(9001)
    d = fa_mod._calculate_offer_diagnostic(team, fa)
    assert d["soft_cap_early"] is True
    assert d["final_offer"] == 0
    _assert_diagnostic_matches(team, fa)


def test_diagnostic_matches_calculate_offer_budget_room_zero():
    """S6: budget == roster → room_to_budget 0 → 0 オファー。"""
    roster = _roster_player(2, 7_600_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 7_600_000
    fa = _fa_player(9002)
    d = fa_mod._calculate_offer_diagnostic(team, fa)
    assert d["soft_cap_early"] is False
    assert d["room_to_budget"] == 0
    assert d["final_offer"] == 0
    _assert_diagnostic_matches(team, fa)


def test_diagnostic_matches_calculate_offer_budget_room_small_positive():
    """S6: roster+buffer 余地 → 中額 FA は budget 内なら芯が通る。"""
    roster = _roster_player(3, 7_600_000)
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[roster])
    team.payroll_budget = 7_600_000 + _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    fa = _fa_player(9003)
    d = fa_mod._calculate_offer_diagnostic(team, fa)
    assert d["soft_cap_early"] is False
    assert d["room_to_budget"] == _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    assert d["final_offer"] == 5_000_000
    _assert_diagnostic_matches(team, fa)


def test_diagnostic_matches_calculate_offer_empty_roster_high_fa():
    """クリップが主因で潰れにくい経路（空ロスター・高額 FA 芯）。"""
    team = Team(team_id=1, name="T", league_level=1, money=500_000_000, players=[])
    team.payroll_budget = 500_000_000
    fa = _fa_player(9004, salary=88_000_000)
    d = fa_mod._calculate_offer_diagnostic(team, fa)
    assert d["soft_cap_early"] is False
    assert d["payroll_before"] == 0
    assert d["final_offer"] > 0
    _assert_diagnostic_matches(team, fa)


def test_diagnostic_matches_calculate_offer_parametrized_matrix():
    """複数合成ケースで final_offer 一致を一括確認。"""
    t1 = Team(team_id=1, name="T", league_level=1, money=300_000_000, players=[])
    t1.payroll_budget = 400_000_000
    fa1 = _fa_player(9101, ovr=65, salary=0)
    _assert_diagnostic_matches(t1, fa1)

    t2 = Team(team_id=2, name="U", league_level=2, money=200_000_000, players=[_roster_player(11, 5_000_000)])
    t2.payroll_budget = 150_000_000
    fa2 = _fa_player(9102, ovr=68, salary=6_000_000)
    _assert_diagnostic_matches(t2, fa2)
