"""cpu_club_strategy: CPU 向け軽量戦略プロファイル（第1段）。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.club_profile import ClubBaseProfile
from basketball_sim.systems.cpu_club_strategy import (
    StrategyProfile,
    _opening_profile_strategy_hint,
    get_cpu_club_strategy,
)
from basketball_sim.systems.free_agent_market import _cpu_fa_cycle_participation_probability
from basketball_sim.systems.trade_logic import TradeSystem


def test_get_cpu_club_strategy_never_raises():
    assert isinstance(get_cpu_club_strategy(None), StrategyProfile)
    assert isinstance(get_cpu_club_strategy(object()), StrategyProfile)


def test_user_team_returns_neutral_default():
    t = SimpleNamespace(is_user_team=True, owner_expectation="title_or_bust", league_level=1)
    s = get_cpu_club_strategy(t)
    assert s.strategy_tag == "hold"
    assert s.fa_aggressiveness == 1.0
    assert s.trade_loss_tolerance == 1.0


def test_rebuild_expectation_tag():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="rebuild",
        league_level=2,
        regular_wins=10,
        regular_losses=10,
        money=50_000_000,
    )
    s = get_cpu_club_strategy(t)
    assert s.strategy_tag == "rebuild"
    assert s.fa_aggressiveness < 1.0
    assert s.trade_loss_tolerance > 1.0
    assert s.future_value_weight > 1.0


def test_title_or_bust_push_tag():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="title_or_bust",
        league_level=1,
        regular_wins=12,
        regular_losses=8,
        money=80_000_000,
    )
    s = get_cpu_club_strategy(t)
    assert s.strategy_tag == "push"
    assert s.fa_aggressiveness > 1.0
    assert s.trade_loss_tolerance < 1.0


def test_low_money_dampens_fa_aggressiveness():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="title_challenge",
        league_level=1,
        regular_wins=12,
        regular_losses=8,
        money=2_000_000,
    )
    s = get_cpu_club_strategy(t)
    s_high = get_cpu_club_strategy(
        SimpleNamespace(
            is_user_team=False,
            owner_expectation="title_challenge",
            league_level=1,
            regular_wins=12,
            regular_losses=8,
            money=80_000_000,
        )
    )
    assert s.fa_aggressiveness <= s_high.fa_aggressiveness


def test_gp0_opening_rank_top_and_rich_money_tilts_push():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=0,
        regular_losses=0,
        money=110_000_000,
        history_seasons=[{"rank": 2, "label": "S0"}],
    )
    assert get_cpu_club_strategy(t).strategy_tag == "push"


def test_gp0_opening_rank_bottom_and_poor_money_tilts_rebuild():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=0,
        regular_losses=0,
        money=3_000_000,
        history_seasons=[{"rank": 15, "label": "S0"}],
    )
    assert get_cpu_club_strategy(t).strategy_tag == "rebuild"


def test_gp0_opening_mid_rank_neutral_hold():
    t = SimpleNamespace(
        is_user_team=False,
        team_id=3,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=0,
        regular_losses=0,
        money=40_000_000,
        history_seasons=[{"rank": 8, "label": "S0"}],
    )
    assert get_cpu_club_strategy(t).strategy_tag == "hold"


def test_early_season_w0_playoff_race_d2_prefers_hold_over_skeleton_rebuild():
    """開幕直後 (GP<4): D2+6勝以下ハードロックと wins<=8 補助が発火せず、中立寄りの hold。"""
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=0,
        regular_losses=0,
        money=40_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "hold"


def test_explicit_rebuild_expectation_still_rebuild_at_w0():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="rebuild",
        league_level=2,
        regular_wins=0,
        regular_losses=0,
        money=40_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "rebuild"


def test_title_challenge_still_push_at_w0():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="title_challenge",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=80_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "push"


def test_d2_weak_hard_rebuild_lock_after_min_gp():
    """GP>=4 かつ勝ち星が弱いときは従来どおり rebuild ハードロック。"""
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=0,
        regular_losses=4,
        money=40_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "rebuild"


def test_playoff_race_d1_strong_record_scores_push():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=1,
        regular_wins=12,
        regular_losses=8,
        money=50_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "push"


def test_playoff_race_d2_weak_record_scores_rebuild():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=8,
        regular_losses=14,
        money=30_000_000,
    )
    assert get_cpu_club_strategy(t).strategy_tag == "rebuild"


def test_history_rank_bottom_tilts_rebuild():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=9,
        regular_losses=9,
        money=40_000_000,
        history_seasons=[{"rank": 14, "label": "S1"}],
    )
    assert get_cpu_club_strategy(t).strategy_tag == "rebuild"


def test_season_arg_ignored_without_error():
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=10,
        regular_losses=10,
        money=40_000_000,
    )
    assert get_cpu_club_strategy(t, season=object()).strategy_tag == "hold"


@pytest.mark.parametrize(
    "bad_exp",
    ["", "unknown", None],
)
def test_invalid_expectation_falls_back_to_playoff_race_logic(bad_exp):
    t = SimpleNamespace(
        is_user_team=False,
        owner_expectation=bad_exp,
        league_level=2,
        regular_wins=10,
        regular_losses=10,
        money=40_000_000,
    )
    s = get_cpu_club_strategy(t)
    assert s.strategy_tag in {"rebuild", "hold", "push"}


def _trade_value_player() -> Player:
    return Player(
        player_id=91001,
        name="FutureGem",
        age=20,
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
        ovr=72,
        potential="S",
        archetype="guard",
        usage_base=20,
    )


def test_cpu_rebuild_trade_value_future_bundle_above_push():
    p = _trade_value_player()
    cpu_rebuild = Team(
        team_id=1,
        name="RB",
        league_level=2,
        money=40_000_000,
        players=[p],
        is_user_team=False,
    )
    cpu_rebuild.owner_expectation = "rebuild"
    cpu_push = Team(
        team_id=2,
        name="PS",
        league_level=1,
        money=80_000_000,
        players=[p],
        is_user_team=False,
    )
    cpu_push.owner_expectation = "title_or_bust"
    ts = TradeSystem()
    v_re = ts.calculate_player_trade_value(p, cpu_rebuild)
    v_pu = ts.calculate_player_trade_value(p, cpu_push)
    assert v_re > v_pu
    assert get_cpu_club_strategy(cpu_rebuild).future_value_weight > get_cpu_club_strategy(
        cpu_push
    ).future_value_weight


def test_fa_participation_probability_rebuild_lt_hold_lt_push():
    rb = SimpleNamespace(
        is_user_team=False,
        owner_expectation="rebuild",
        league_level=3,
        regular_wins=8,
        regular_losses=8,
        money=40_000_000,
    )
    hd = SimpleNamespace(
        is_user_team=False,
        owner_expectation="playoff_race",
        league_level=2,
        regular_wins=10,
        regular_losses=10,
        money=40_000_000,
    )
    ps = SimpleNamespace(
        is_user_team=False,
        owner_expectation="title_or_bust",
        league_level=1,
        regular_wins=14,
        regular_losses=6,
        money=80_000_000,
    )
    pr = _cpu_fa_cycle_participation_probability(rb)
    ph = _cpu_fa_cycle_participation_probability(hd)
    pp = _cpu_fa_cycle_participation_probability(ps)
    assert pr < ph < pp


def test_fa_participation_probability_user_team_always_one():
    u = SimpleNamespace(
        is_user_team=True,
        owner_expectation="rebuild",
        league_level=1,
        regular_wins=0,
        regular_losses=20,
        money=0,
    )
    assert _cpu_fa_cycle_participation_probability(u) == 1.0


def test_user_team_trade_value_matches_cpu_hold_neutral_multiplier():
    p = _trade_value_player()
    user_t = Team(
        team_id=3,
        name="USER",
        league_level=1,
        money=50_000_000,
        players=[p],
        is_user_team=True,
    )
    user_t.owner_expectation = "playoff_race"
    cpu_hold = Team(
        team_id=4,
        name="HOLD",
        league_level=2,
        money=50_000_000,
        players=[p],
        is_user_team=False,
    )
    cpu_hold.owner_expectation = "playoff_race"
    cpu_hold.regular_wins = 10
    cpu_hold.regular_losses = 10
    ts = TradeSystem()
    assert ts.calculate_player_trade_value(p, user_t) == ts.calculate_player_trade_value(
        p, cpu_hold
    )


def _fake_club_prof(**kwargs: float) -> ClubBaseProfile:
    vals = {
        "financial_power": 1.0,
        "market_size": 1.0,
        "arena_grade": 1.0,
        "youth_development_bias": 1.0,
        "win_now_pressure": 1.0,
    }
    vals.update(kwargs)
    return ClubBaseProfile(**vals)


def test_opening_profile_strategy_hint_skipped_when_gp_reaches_min():
    t = SimpleNamespace(regular_wins=2, regular_losses=2, team_id=999)
    with patch("basketball_sim.systems.cpu_club_strategy.get_club_base_profile") as m:
        assert _opening_profile_strategy_hint(t) == (0, 0)
        m.assert_not_called()


def test_opening_profile_strategy_hint_high_win_now_gives_push_cap():
    t = SimpleNamespace(regular_wins=0, regular_losses=1, team_id=999)
    with patch(
        "basketball_sim.systems.cpu_club_strategy.get_club_base_profile",
        return_value=_fake_club_prof(win_now_pressure=1.06, financial_power=1.02),
    ):
        assert _opening_profile_strategy_hint(t) == (1, 0)


def test_opening_profile_strategy_hint_high_youth_gives_rebuild_when_fin_not_strong():
    t = SimpleNamespace(regular_wins=1, regular_losses=1, team_id=999)
    with patch(
        "basketball_sim.systems.cpu_club_strategy.get_club_base_profile",
        return_value=_fake_club_prof(youth_development_bias=1.05),
    ):
        assert _opening_profile_strategy_hint(t) == (0, 1)


def test_opening_profile_strategy_hint_low_financial_gives_rebuild_cap():
    t = SimpleNamespace(regular_wins=0, regular_losses=2, team_id=999)
    with patch(
        "basketball_sim.systems.cpu_club_strategy.get_club_base_profile",
        return_value=_fake_club_prof(financial_power=0.96),
    ):
        assert _opening_profile_strategy_hint(t) == (0, 1)


def test_opening_profile_strategy_hint_fin_strong_suppresses_rebuild_branch():
    t = SimpleNamespace(regular_wins=0, regular_losses=0, team_id=999)
    with patch(
        "basketball_sim.systems.cpu_club_strategy.get_club_base_profile",
        return_value=_fake_club_prof(
            financial_power=1.06,
            youth_development_bias=1.06,
        ),
    ):
        assert _opening_profile_strategy_hint(t) == (0, 0)


def test_opening_profile_strategy_hint_both_axes_prefers_push_when_both_fire():
    t = SimpleNamespace(regular_wins=0, regular_losses=3, team_id=999)
    with patch(
        "basketball_sim.systems.cpu_club_strategy.get_club_base_profile",
        return_value=_fake_club_prof(
            win_now_pressure=1.04,
            financial_power=1.01,
            youth_development_bias=1.05,
        ),
    ):
        assert _opening_profile_strategy_hint(t) == (1, 0)
