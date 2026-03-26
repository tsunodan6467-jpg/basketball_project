"""レギュラー中トレード/インシーズンFA 期限ルール。"""

from types import SimpleNamespace

from basketball_sim.config.game_constants import REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND
from basketball_sim.systems.season_transaction_rules import (
    cpu_inseason_fa_allowed_for_simulated_round,
    inseason_roster_moves_unlocked,
)


def test_unlocked_when_no_season():
    assert inseason_roster_moves_unlocked(None) is True


def test_unlocked_before_cutoff_completed_rounds():
    s = SimpleNamespace(current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND - 1, season_finished=False)
    assert inseason_roster_moves_unlocked(s) is True


def test_locked_at_cutoff_completed_rounds():
    s = SimpleNamespace(current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND, season_finished=False)
    assert inseason_roster_moves_unlocked(s) is False


def test_unlocked_when_season_finished_even_if_round_high():
    s = SimpleNamespace(current_round=30, season_finished=True)
    assert inseason_roster_moves_unlocked(s) is True


def test_cpu_fa_allowed_through_cutoff_round():
    assert cpu_inseason_fa_allowed_for_simulated_round(REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND) is True


def test_cpu_fa_blocked_after_cutoff_round():
    assert cpu_inseason_fa_allowed_for_simulated_round(REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND + 1) is False
