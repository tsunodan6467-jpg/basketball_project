"""generate_teams 経路の開幕総年俸: D1 > D2 > D3 の段差（第1弾）。"""

import random
import statistics

from basketball_sim.systems.contract_logic import get_team_payroll
from basketball_sim.systems.generator import generate_teams


def test_generate_teams_division_mean_payroll_ordering():
    """複数 seed でディビジョン平均が D1 > D2 > D3。正の差は緩めに検証。"""
    for seed in (0, 42, 99, 20260329):
        random.seed(seed)
        teams = generate_teams()
        by_lv = {1: [], 2: [], 3: []}
        for t in teams:
            by_lv[int(getattr(t, "league_level", 1))].append(get_team_payroll(t))
        m1 = statistics.mean(by_lv[1])
        m2 = statistics.mean(by_lv[2])
        m3 = statistics.mean(by_lv[3])
        assert m1 > m2 > m3, (seed, m1, m2, m3)
        assert m1 - m2 > 200_000_000, (seed, m1 - m2)
        assert m2 - m3 > 150_000_000, (seed, m2 - m3)


def test_generate_teams_salary_rank_mostly_follows_ovr_seed42():
    """代表 seed で上位 OVR が低 OVR より高年俸になりやすい（緩い検証）。"""
    random.seed(42)
    teams = generate_teams()
    t0 = teams[0]
    assert int(getattr(t0, "league_level", 0)) == 1
    roster = sorted(getattr(t0, "players", []), key=lambda p: int(getattr(p, "ovr", 0)), reverse=True)
    assert len(roster) == 13
    salaries_by_ovr = [int(getattr(p, "salary", 0)) for p in roster]
    assert salaries_by_ovr[0] >= salaries_by_ovr[-1]
    # 上位5人の最小が下位より高い（同率タイは許容）
    top5_min = min(salaries_by_ovr[:5])
    bottom_min = min(salaries_by_ovr[8:])
    assert top5_min >= bottom_min
