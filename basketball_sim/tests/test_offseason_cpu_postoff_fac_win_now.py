"""⑦ `compute_postoff_payroll_budget_with_temp_floor` の CPU fac に win_now_pressure 極小補正。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from basketball_sim.models.offseason import compute_postoff_payroll_budget_with_temp_floor
from basketball_sim.systems.club_profile import ClubBaseProfile


def _d3_team(**overrides: object) -> SimpleNamespace:
    base = dict(
        team_id=99,
        is_user_team=False,
        league_level=3,
        market_size=1.0,
        popularity=50,
        sponsor_power=50,
        fan_base=50,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _inner_sum_d3(team: SimpleNamespace) -> float:
    league_level = int(getattr(team, "league_level", 3))
    base_budget = {1: 7_900_000, 2: 5_450_000, 3: 3_650_000}.get(league_level, 3_650_000)
    return float(
        base_budget
        + float(getattr(team, "market_size", 1.0)) * 12_500
        + int(getattr(team, "popularity", 50)) * 6_200
        + int(getattr(team, "sponsor_power", 50)) * 5_000
        + int(getattr(team, "fan_base", 50)) * 3_600
    )


def test_cpu_high_win_now_pressure_increases_budget_vs_low() -> None:
    """同じ inner_sum でも win_now 高い CPU は fac +0.005 分だけ予算が上がる。"""
    team = _d3_team()
    inner = _inner_sum_d3(team)
    prof_hi = ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 1.05)
    prof_lo = ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 0.97)
    with patch("basketball_sim.models.offseason.get_club_base_profile", return_value=prof_hi):
        hi = compute_postoff_payroll_budget_with_temp_floor(team, 0)
    with patch("basketball_sim.models.offseason.get_club_base_profile", return_value=prof_lo):
        lo = compute_postoff_payroll_budget_with_temp_floor(team, 0)
    base_budget = 3_650_000
    exp_hi = max(base_budget, int(inner * 1.005))
    exp_lo = max(base_budget, int(inner * 0.995))
    assert hi == exp_hi
    assert lo == exp_lo
    assert hi > lo
    assert hi - lo == exp_hi - exp_lo


def test_user_team_ignores_profile_fac_is_one() -> None:
    """ユーザーチームは fac=1.0 固定。高 win_now の profile を返しても⑦式は中立。"""
    team = _d3_team(team_id=1, is_user_team=True)
    prof_hi = ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 1.06)
    inner = _inner_sum_d3(team)
    base_budget = 3_650_000
    expected = max(base_budget, int(inner * 1.0))
    with patch("basketball_sim.models.offseason.get_club_base_profile", return_value=prof_hi):
        got = compute_postoff_payroll_budget_with_temp_floor(team, 0)
    assert got == expected


def test_cpu_mid_win_now_pressure_no_delta() -> None:
    """1.04 未満かつ 0.98 超は win_now 補正なし（fac=中立プロファイルの fin/mkt/arena のみ）。"""
    team = _d3_team()
    prof = ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 1.0)
    inner = _inner_sum_d3(team)
    base_budget = 3_650_000
    expected = max(base_budget, int(inner * 1.0))
    with patch("basketball_sim.models.offseason.get_club_base_profile", return_value=prof):
        got = compute_postoff_payroll_budget_with_temp_floor(team, 0)
    assert got == expected


def test_cpu_win_now_adjustment_respects_global_fac_clamp() -> None:
    """既存 fac が上限付近でも win_now + 後の clamp で 1.03 を超えない。"""
    team = _d3_team()
    prof = ClubBaseProfile(1.14, 1.08, 1.08, 1.0, 1.06)
    with patch("basketball_sim.models.offseason.get_club_base_profile", return_value=prof):
        got = compute_postoff_payroll_budget_with_temp_floor(team, 0)
    inner = _inner_sum_d3(team)
    raw = (
        1.0
        + 0.022 * (1.14 - 1.0)
        + 0.018 * (1.08 - 1.0)
        + 0.015 * (1.08 - 1.0)
        + 0.005
    )
    fac = max(0.97, min(1.03, float(raw)))
    base_budget = 3_650_000
    assert fac <= 1.03
    assert got == max(base_budget, int(inner * fac))
