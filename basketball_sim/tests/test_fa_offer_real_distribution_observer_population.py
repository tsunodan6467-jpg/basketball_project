"""fa_offer_real_distribution_observer population helpers (tools/; default CLI unchanged)."""

import importlib.util
from pathlib import Path

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


def _load_observer_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "tools" / "fa_offer_real_distribution_observer.py"
    spec = importlib.util.spec_from_file_location("fa_offer_real_distribution_observer", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ob = _load_observer_module()


def _fa(pid: int, salary: int) -> Player:
    return Player(
        player_id=pid,
        name=f"FA{pid}",
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
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def test_select_fa_sample_by_salary_rank_mid_band():
    fas = [_fa(i, 1_000_000 * (100 - i)) for i in range(1, 61)]
    out = _ob._select_fa_sample_by_salary_rank(fas, 11, 20)
    assert len(out) == 10
    assert _ob._fa_salary(out[0]) == 1_000_000 * 89
    assert _ob._fa_salary(out[-1]) == 1_000_000 * 80


def test_select_fa_sample_by_salary_rank_clamps_to_pool():
    fas = [_fa(1, 5_000_000), _fa(2, 4_000_000)]
    out = _ob._select_fa_sample_by_salary_rank(fas, 1, 100)
    assert len(out) == 2


def test_select_teams_by_room_orders_by_budget_minus_payroll():
    t_low = Team(team_id=1, name="L", league_level=1, money=0, players=[], payroll_budget=100_000_000)
    t_high = Team(team_id=2, name="H", league_level=1, money=0, players=[], payroll_budget=100_000_000)
    t_high.players = [
        Player(
            player_id=10,
            name="P",
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
            salary=10_000_000,
            contract_years_left=1,
            contract_total_years=2,
            team_id=2,
        )
    ]
    t_low.players = [
        Player(
            player_id=11,
            name="Q",
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
            salary=80_000_000,
            contract_years_left=1,
            contract_total_years=2,
            team_id=1,
        )
    ]
    ordered = _ob._select_teams_by_room([t_low, t_high], top_n=2)
    assert ordered[0].team_id == 2
    assert ordered[1].team_id == 1


def test_matrix_summary_line_mixed_soft_cap_and_pre_le():
    rows = [
        {"soft_cap_early": True, "room_to_budget": None, "diag": {}},
        {
            "soft_cap_early": False,
            "room_to_budget": 30_000_000,
            "diag": {
                "offer_after_soft_cap_pushback": 50_000_000,
                "room_to_budget": 30_000_000,
            },
        },
    ]
    s = _ob._matrix_summary_line(rows)
    assert "soft_cap_early=1/2 (50.0%)" in s
    assert "room_unique=1" in s
    assert "pre_le_room=0" in s


def test_matrix_summary_line_pre_le_room_counts():
    rows = [
        {
            "soft_cap_early": False,
            "room_to_budget": 50_000_000,
            "diag": {
                "offer_after_soft_cap_pushback": 40_000_000,
                "room_to_budget": 50_000_000,
            },
        }
    ]
    s = _ob._matrix_summary_line(rows)
    assert "pre_le_room=1" in s
    assert "room_unique=1" in s
    assert "soft_cap_early=0/1 (0.0%)" in s


def test_teams_payroll_gap_stats_empty():
    st = _ob._teams_payroll_gap_stats([])
    assert st["n"] == 0
    assert st["gap_min"] is None


def test_teams_payroll_gap_stats_two_distinct_gaps():
    p = Player(
        player_id=10,
        name="P",
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
        salary=80_000_000,
        contract_years_left=1,
        contract_total_years=2,
        team_id=1,
    )
    t1 = Team(team_id=1, name="A", league_level=1, money=0, players=[p], payroll_budget=100_000_000)
    q = Player(
        player_id=11,
        name="Q",
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
        salary=80_000_000,
        contract_years_left=1,
        contract_total_years=2,
        team_id=2,
    )
    t2 = Team(team_id=2, name="B", league_level=1, money=0, players=[q], payroll_budget=95_000_000)
    st = _ob._teams_payroll_gap_stats([t1, t2])
    assert st["n"] == 2
    assert st["gap_u"] == 2
    assert st["gap_min"] == 15_000_000
    assert st["gap_max"] == 20_000_000


def test_check_save_args_exclusive():
    assert _ob._check_save_args_exclusive("", None) is None
    assert _ob._check_save_args_exclusive("", ["x.sav"]) is None
    assert _ob._check_save_args_exclusive("a.sav", None) is None
    assert _ob._check_save_args_exclusive("a.sav", ["b.sav"]) is not None


def test_select_teams_by_room_zero_means_all():
    t1 = Team(team_id=1, name="A", league_level=1, money=0, players=[], payroll_budget=50_000_000)
    t2 = Team(team_id=2, name="B", league_level=1, money=0, players=[], payroll_budget=60_000_000)
    out = _ob._select_teams_by_room([t1, t2], top_n=0)
    assert len(out) == 2
