"""FA 交渉スコア: 希望条件・fa_priority の反映。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems import free_agency as fa
from basketball_sim.systems.contract_logic import calculate_fa_retention_bonus, fa_roll_accept_offer


def _player(pid: int, desired_salary: int, **kwargs) -> Player:
    p = Player(
        player_id=pid,
        name=f"P{pid}",
        age=27,
        nationality="Japan",
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
        ovr=72,
        potential="B",
        archetype="wing",
        usage_base=20,
        salary=4_000_000,
        desired_salary=desired_salary,
        desired_years=2,
    )
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


def _team() -> Team:
    return Team(team_id=1, name="T", league_level=2, popularity=55, market_size=1.0)


def test_salary_score_penalizes_below_desired():
    p = _player(1, 8_000_000)
    high = fa._estimate_salary_score(p, 8_000_000)
    low = fa._estimate_salary_score(p, 4_000_000)
    assert high > low


def test_negotiation_weights_blend_priorities():
    p = _player(2, 5_000_000, fa_priority_money=90, fa_priority_winning=30)
    profile = {"money": 50, "role": 50, "winning": 50, "fit": 50, "security": 50}
    w = fa._negotiation_weights(p, profile)
    assert w["money"] > w["winning"]


def test_offer_score_respects_money_priority():
    team = _team()
    hi_money = _player(3, 5_000_000, fa_priority_money=95, fa_priority_winning=20)
    hi_win = _player(4, 5_000_000, fa_priority_money=20, fa_priority_winning=95)
    s1 = fa._offer_score(hi_money, team, 5_000_000, 2)
    s2 = fa._offer_score(hi_win, team, 5_000_000, 2)
    # 同条件でも金志向の方が年俸スコア寄与が強い（極端な重み差）
    assert s1 != s2


def test_retention_bonus_same_last_team():
    team = _team()
    p = _player(5, 4_000_000, last_contract_team_id=1, league_years=4, loyalty=70)
    b = calculate_fa_retention_bonus(p, team)
    assert b > 0


def test_retention_bonus_other_team():
    team = _team()
    p = _player(6, 4_000_000, last_contract_team_id=999)
    assert calculate_fa_retention_bonus(p, team) == 0.0


def test_fa_roll_rejects_low_score():
    assert fa_roll_accept_offer(20) is False


def test_calculate_offer_respects_payroll_budget_room():
    team = _team()
    # 既存年俸 7.6M + 予算 8.0M -> room 0.4M。芯 5M 超過時は線形緩和で room よりわずかに上げうる
    team.players = [_player(101, 4_000_000, salary=7_600_000)]
    team.payroll_budget = 8_000_000
    cand = _player(102, 9_000_000, salary=4_000_000, ovr=76)
    d = fa._calculate_offer_diagnostic(team, cand)
    room = d["room_to_budget"]
    assert room == 400_000
    pre = d["offer_after_soft_cap_pushback"]
    assert pre == 5_000_000
    lam = float(fa._PAYROLL_BUDGET_CLIP_LAMBDA)
    assert pre > room
    expected = room + round(lam * (pre - room))
    offer = fa._calculate_offer(team, cand)
    assert offer == expected
    assert offer == d["final_offer"]


def test_cap_status_is_aligned_with_shared_budget_module():
    team = Team(team_id=1, name="T", league_level=1)
    hard = fa._hard_cap(team)
    soft = fa._soft_cap(team)
    assert hard == soft
    assert fa._cap_status(hard - 1, team) == "under_cap"
    assert fa._cap_status(hard + 1, team) == "over_soft_cap"
    assert fa._cap_status(soft + 1, team) == "over_soft_cap"
