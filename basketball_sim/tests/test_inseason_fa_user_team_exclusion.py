"""`_process_inseason_free_agency` がユーザーチームを CPU FA 対象から外すことの確認。"""

from basketball_sim.models.player import Player
from basketball_sim.models.season import Season
from basketball_sim.models.team import Team


class _SeasonStub:
    """`Season.__init__` は最少チーム数で落ちるため、当メソッド検証用の最小スタブ。"""

    def __init__(self, all_teams, free_agents):
        self.all_teams = all_teams
        self.free_agents = free_agents


def _fa_player() -> Player:
    return Player(
        player_id=99002,
        name="FA_UserSkip",
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


def test_process_inseason_free_agency_passes_only_non_user_teams(monkeypatch):
    captured: dict = {}

    def fake_run_cpu_fa_market_cycle(*, teams, free_agents, **kwargs):
        captured["teams"] = list(teams)
        return []

    monkeypatch.setattr(
        "basketball_sim.models.season.run_cpu_fa_market_cycle",
        fake_run_cpu_fa_market_cycle,
    )

    user = Team(team_id=1, name="User FC", league_level=1, is_user_team=True)
    cpu = Team(team_id=2, name="CPU FC", league_level=1, is_user_team=False)
    stub = _SeasonStub([user, cpu], [_fa_player()])
    Season._process_inseason_free_agency(stub, 1)

    assert captured["teams"] == [cpu]
    assert user not in captured["teams"]
