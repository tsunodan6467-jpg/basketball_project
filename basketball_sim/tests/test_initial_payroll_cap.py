"""開幕時ペイロールがリーグ年俸上限（12億）を原則超えないこと（PR2）。"""

import random
import statistics

from basketball_sim.config.game_constants import LEAGUE_ROSTER_FOREIGN_CAP
from basketball_sim.systems.club_profile import get_initial_team_money_cpu
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


def test_user_team_opening_payroll_v11_after_simulated_auto_draft():
    """ユーザー自動編成相当の後に v11 再配分で D3 bottom 帯の総年俸に近づく。"""
    from basketball_sim.main import (
        auto_draft_players,
        choose_icon_player_auto_from_league,
        create_icon_player,
    )
    from basketball_sim.systems.contract_logic import get_team_payroll
    from basketball_sim.systems.generator import generate_fictional_player_pool, generate_teams
    from basketball_sim.systems.opening_roster_salary_v11 import (
        apply_user_team_opening_payroll_v11_if_roster_complete,
    )
    from basketball_sim.utils.sim_rng import init_simulation_random

    init_simulation_random(424242)
    teams = generate_teams()
    user_team = next(t for t in teams if int(getattr(t, "league_level", 0) or 0) == 3)
    assert str(getattr(user_team, "initial_payroll_tier", "")).lower() == "bottom"

    icon_data = choose_icon_player_auto_from_league(teams)
    st = icon_data.get("team")
    sp = icon_data.get("player")
    if st is not None and sp is not None and sp in getattr(st, "players", []):
        st.remove_player(sp)
    icon_player = create_icon_player(icon_data)
    pool = list(generate_fictional_player_pool(180))
    auto_draft_players(pool, user_team, icon_player)

    before = get_team_payroll(user_team)
    assert apply_user_team_opening_payroll_v11_if_roster_complete(user_team) is True
    after = get_team_payroll(user_team)

    assert before > 500_000_000, (before,)
    assert 360_000_000 <= after <= 450_000_000, (before, after)

    icons = [p for p in user_team.players if bool(getattr(p, "is_icon", False))]
    assert icons, "expected an icon player on user roster"
    for ip in icons:
        assert int(getattr(ip, "salary", 0) or 0) == 0, (getattr(ip, "name", ""), getattr(ip, "salary", None))
    non_icon_sals = [
        int(getattr(p, "salary", 0) or 0) for p in user_team.players if not bool(getattr(p, "is_icon", False))
    ]
    assert non_icon_sals
    assert max(non_icon_sals) - min(non_icon_sals) >= 15_000_000, (
        "expected staircase-like spread, not flat ~equal salaries",
        non_icon_sals,
    )

    n_foreign = sum(1 for p in user_team.players if getattr(p, "nationality", "") == "Foreign")
    assert n_foreign == LEAGUE_ROSTER_FOREIGN_CAP, (n_foreign, [getattr(p, "nationality", "") for p in user_team.players])
    assert int(getattr(user_team, "money", 0) or 0) == int(get_initial_team_money_cpu(user_team))


def test_normalize_initial_payrolls_for_teams_counts_adjustments():
    class _P:
        salary = 5_000_000

    class _T:
        league_level = 1
        team_id = 9998
        players = [_P()]

    teams = [_T()]
    assert normalize_initial_payrolls_for_teams(teams) == 0
