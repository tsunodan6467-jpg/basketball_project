"""`roster_fa_release` のガードと CLI 契約解除（入力モック）。"""

from types import SimpleNamespace
import pytest

from basketball_sim.config.game_constants import CONTRACT_ROSTER_MIN_SEASON, REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND
from basketball_sim.main import run_gm_contract_release_cli
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.gm_dashboard_text import sort_roster_for_gm_view
from basketball_sim.systems.roster_fa_release import precheck_release_player_to_fa


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
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
        salary=1_000_000,
        contract_years_left=1,
        contract_total_years=1,
        team_id=1,
    )


def test_precheck_blocks_when_inseason_locked():
    roster = [_player(i + 1) for i in range(CONTRACT_ROSTER_MIN_SEASON + 1)]
    team = Team(team_id=1, name="T", league_level=1, players=list(roster))
    season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND,
        season_finished=False,
    )
    err = precheck_release_player_to_fa(team, roster[0], season)
    assert err is not None
    assert err[0] == "トレード・インシーズンFAは不可"


def test_precheck_blocks_at_min_roster():
    roster = [_player(i + 1) for i in range(CONTRACT_ROSTER_MIN_SEASON)]
    team = Team(team_id=1, name="T", league_level=1, players=list(roster))
    season = SimpleNamespace(current_round=0, season_finished=False)
    err = precheck_release_player_to_fa(team, roster[0], season)
    assert err is not None
    assert "最低" in err[1]


def test_cli_release_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    roster = [_player(i + 1) for i in range(CONTRACT_ROSTER_MIN_SEASON + 1)]
    team = Team(team_id=1, name="T", league_level=1, players=list(roster))
    fa: list = []
    season = SimpleNamespace(free_agents=fa, current_round=0, season_finished=False)
    ordered = sort_roster_for_gm_view(list(team.players))
    target = ordered[0]
    inputs = iter(["1", "y"])

    def fake_input(_prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr("builtins.input", fake_input)
    run_gm_contract_release_cli(team, season)
    out = capsys.readouterr().out
    assert target.name in out
    assert target not in team.players
    assert target in fa
