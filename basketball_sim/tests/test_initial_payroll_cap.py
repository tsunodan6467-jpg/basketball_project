"""開幕時ペイロールがリーグ年俸上限（12億）を原則超えないこと（PR2）。"""

import random
import statistics

from basketball_sim.systems.contract_logic import (
    get_team_payroll,
    normalize_initial_payrolls_for_teams,
    normalize_team_payroll_under_hard_cap,
)
from basketball_sim.systems.generator import generate_teams
from basketball_sim.systems.salary_cap_budget import get_hard_cap, get_soft_cap


def test_generate_teams_payroll_under_league_cap_multiple_seeds():
    """main.py と同様に normalize 後は 0.98×上限以下。開幕は D1>D2>D3 の平均総年俸段差を持つ。"""
    league_cap = int(get_hard_cap(league_level=1))
    soft = int(get_soft_cap(league_level=1))
    assert league_cap == soft
    norm_ceiling = int(league_cap * 0.98) + 1
    for seed in (0, 1, 42, 99, 20260329):
        random.seed(seed)
        teams = generate_teams()
        normalize_initial_payrolls_for_teams(teams)
        payrolls = [get_team_payroll(t) for t in teams]
        assert max(payrolls) <= norm_ceiling, (seed, max(payrolls), norm_ceiling)
        assert max(payrolls) <= league_cap, (seed, max(payrolls), league_cap)
        by_lv = {1: [], 2: [], 3: []}
        for t in teams:
            by_lv[int(getattr(t, "league_level", 1))].append(get_team_payroll(t))
        m1 = statistics.mean(by_lv[1])
        m2 = statistics.mean(by_lv[2])
        m3 = statistics.mean(by_lv[3])
        assert m1 > m2 > m3, (seed, m1, m2, m3)


def test_normalize_team_payroll_under_hard_cap_scales_down():
    class _P:
        def __init__(self, salary: int):
            self.salary = salary

    class _T:
        league_level = 1
        team_id = 9999
        players = []

    t = _T()
    t.players = [_P(120_000_000) for _ in range(13)]
    assert get_team_payroll(t) == 13 * 120_000_000
    assert normalize_team_payroll_under_hard_cap(t, margin=0.98) is True
    assert get_team_payroll(t) <= int(get_hard_cap(league_level=1) * 0.98) + 1


def test_normalize_initial_payrolls_for_teams_counts_adjustments():
    class _P:
        salary = 5_000_000

    class _T:
        league_level = 1
        team_id = 9998
        players = [_P()]

    teams = [_T()]
    assert normalize_initial_payrolls_for_teams(teams) == 0
