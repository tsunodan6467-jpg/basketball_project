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


def test_pre_le_population_summary_lines_empty():
    lines = _ob._pre_le_population_summary_lines([])
    assert len(lines) == 1
    assert "pre_le_pop: n=0" in lines[0]


def test_pre_le_population_summary_lines_counts_and_keywords():
    rows = [
        {"soft_cap_early": True, "room_to_budget": None, "diag": {}},
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 50,
                "room_to_budget": 100,
                "offer_after_hard_cap_over": 200,
                "soft_cap_pushback_applied": False,
                "payroll_after_pre_soft_pushback": 50,
                "soft_cap": 100,
                "payroll_before": 1_000_000,
            },
        },
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 100,
                "room_to_budget": 100,
                "offer_after_hard_cap_over": 100,
                "soft_cap_pushback_applied": True,
                "payroll_after_pre_soft_pushback": 150,
                "soft_cap": 100,
                "payroll_before": 2_000_000,
            },
        },
        {
            "soft_cap_early": False,
            "room_to_budget": 1_000_000,
            "diag": {
                "offer_after_soft_cap_pushback": 7_000_000,
                "room_to_budget": 1_000_000,
                "offer_after_hard_cap_over": 9_000_000,
                "soft_cap_pushback_applied": True,
                "payroll_after_pre_soft_pushback": 100,
                "soft_cap": 120,
                "payroll_before": 3_000_000,
            },
        },
    ]
    lines = _ob._pre_le_population_summary_lines(rows)
    assert len(lines) == 11
    assert "pre_le_pop: n=3" in lines[0]
    assert "room_to_budget min=100" in lines[0]
    assert "payroll_before" in lines[1]
    assert "min=1000000" in lines[1]
    assert "max=3000000" in lines[1]
    assert "offer_after_hard_cap_over" in lines[2]
    assert "min=100" in lines[2]
    assert "max=9000000" in lines[2]
    assert "offer_after_soft_cap_pushback" in lines[3]
    assert "le0=2" in lines[4]
    assert "gt0=1" in lines[4]
    assert "gt_temp=1" in lines[4]
    assert "TEMP_PRE_LE_DIFF_LARGE_THRESHOLD=" in lines[4]
    assert "soft_cap_pushback_applied" in lines[5]
    assert "true=2" in lines[5]
    assert "false=1" in lines[5]
    assert "hard_over_minus_soft_pushback" in lines[6]
    assert "eq0=1" in lines[6]
    assert "gt0=2" in lines[6]
    assert "n_cmp=3" in lines[6]
    assert "payroll_after_pre_soft_pushback" in lines[7]
    assert "n_gate=3" in lines[7]
    assert "min=50" in lines[7]
    assert "max=150" in lines[7]
    assert "payroll_after_pre_vs_soft_cap" in lines[8]
    assert "gt=1" in lines[8]
    assert "le_eq=2" in lines[8]
    assert "soft_cap" in lines[9]
    assert "min=100" in lines[9]
    assert "max=120" in lines[9]
    assert "unique=2" in lines[9]
    assert "n_gate=3" in lines[9]
    assert "room_to_soft value=0 (n_gate=3)" in lines[10]


def test_pre_le_population_summary_lines_hard_cap_over_all_missing():
    rows = [
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 50,
                "room_to_budget": 100,
                "soft_cap_pushback_applied": False,
                "payroll_after_pre_soft_pushback": 40,
                "soft_cap": 100,
                "payroll_before": 999,
            },
        },
    ]
    lines = _ob._pre_le_population_summary_lines(rows)
    assert len(lines) == 11
    assert "n=1" in lines[0]
    assert "payroll_before" in lines[1]
    assert "min=999" in lines[1]
    assert "offer_after_hard_cap_over n_hard=0" in lines[2]
    assert "false=1" in lines[5]
    assert "true=0" in lines[5]
    assert "eq0=0" in lines[6]
    assert "gt0=0" in lines[6]
    assert "n_cmp=0" in lines[6]
    assert "n_gate=1" in lines[7]
    assert "min=40" in lines[7]
    assert "le_eq=1" in lines[8]
    assert "gt=0" in lines[8]
    assert "soft_cap value=100 (n_gate=1)" in lines[9]
    assert "room_to_soft value=0 (n_gate=1)" in lines[10]


def test_pre_le_population_summary_lines_soft_cap_line_when_n_gate_zero():
    rows = [
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 50,
                "room_to_budget": 100,
            },
        },
    ]
    lines = _ob._pre_le_population_summary_lines(rows)
    assert len(lines) == 11
    assert "n=1" in lines[0]
    assert "soft_cap n_gate=0" in lines[9]
    assert "room_to_soft n_gate=0" in lines[10]


def test_pre_le_population_summary_lines_room_to_soft_quartiles_when_multi_value():
    rows = [
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 10,
                "room_to_budget": 100,
                "offer_after_hard_cap_over": 10,
                "soft_cap_pushback_applied": False,
                "payroll_after_pre_soft_pushback": 110,
                "soft_cap": 200,
                "payroll_before": 100,
            },
        },
        {
            "soft_cap_early": False,
            "room_to_budget": 100,
            "diag": {
                "offer_after_soft_cap_pushback": 20,
                "room_to_budget": 100,
                "offer_after_hard_cap_over": 20,
                "soft_cap_pushback_applied": False,
                "payroll_after_pre_soft_pushback": 120,
                "soft_cap": 200,
                "payroll_before": 50,
            },
        },
    ]
    lines = _ob._pre_le_population_summary_lines(rows)
    assert len(lines) == 11
    assert "room_to_soft" in lines[10]
    assert "min=100" in lines[10]
    assert "max=150" in lines[10]
    assert "p25=" in lines[10]
    assert "n_gate=2" in lines[10]


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


def test_reading_guide_line_documents_compare_axis():
    assert "primary=before" in _ob.READING_GUIDE_LINE
    assert "secondary=" in _ob.READING_GUIDE_LINE
    assert "sync1" in _ob.READING_GUIDE_LINE
    assert "roster_payroll" in _ob.READING_GUIDE_LINE
    assert "現行オフ後式" in _ob.READING_GUIDE_NOTE_JA
    assert "比較主軸" in _ob.READING_GUIDE_NOTE_JA


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


def test_format_pre_sync_user_team_snapshot_prefers_is_user_team():
    cpu = Team(team_id=1, name="CPU", league_level=1, money=0, players=[], payroll_budget=10, is_user_team=False)
    usr = Team(
        team_id=2,
        name="UserSide",
        league_level=3,
        money=9_999,
        players=[],
        payroll_budget=10,
        is_user_team=True,
        market_size=1.2,
        popularity=44,
        sponsor_power=49,
        fan_base=5510,
    )
    line = _ob._format_pre_sync_user_team_snapshot_line([cpu, usr])
    assert line.startswith("user_team_snapshot:")
    assert "[fallback]" not in line
    assert "UserSide" in line
    assert "9,999" in line
    assert "league_level=3" in line
    assert "market_size=1.2" in line
    assert "popularity=44" in line
    assert "sponsor_power=49" in line
    assert "fan_base=5510" in line


def test_format_pre_sync_user_team_snapshot_fallback_first_team():
    t1 = Team(team_id=1, name="FirstOnly", league_level=1, money=500, players=[], payroll_budget=100, is_user_team=False)
    line = _ob._format_pre_sync_user_team_snapshot_line([t1])
    assert "user_team_snapshot[fallback]" in line
    assert "FirstOnly" in line
    assert "500" in line
    assert "league_level=1" in line
    assert "market_size=" in line
    assert "popularity=50" in line
    assert "sponsor_power=50" in line
    assert "fan_base=5000" in line
