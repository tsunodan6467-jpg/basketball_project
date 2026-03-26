"""run_cpu_fa_market_cycle のインシーズン締切ラウンド連携。"""

from basketball_sim.config.game_constants import REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND
from basketball_sim.models.player import Player
from basketball_sim.systems.free_agent_market import run_cpu_fa_market_cycle


def _minimal_fa() -> Player:
    return Player(
        player_id=99001,
        name="FA_Test",
        age=26,
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
        ovr=65,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def test_cpu_fa_after_deadline_round_returns_empty_and_preserves_pool():
    """締切後ラウンドでは即 return[]、free_agents を clear しない。"""
    fa = [_minimal_fa()]
    before = len(fa)
    out = run_cpu_fa_market_cycle(
        teams=[],
        free_agents=fa,
        simulated_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND + 1,
    )
    assert out == []
    assert len(fa) == before
