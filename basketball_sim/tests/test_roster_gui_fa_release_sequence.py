"""
人事 GUI の契約解除（FA送り）と同一の状態遷移を検証（MainMenuView 非依存）。

`_on_roster_release_selected` 本体のロジックと揃える。
"""

from basketball_sim.config.game_constants import CONTRACT_ROSTER_MIN_SEASON
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.roster_fa_release import apply_release_player_to_fa


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"R{pid}",
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


def test_release_sequence_removes_from_roster_and_appends_free_agents():
    """最低人数を超えるロスターから 1 人を外し FA リストへ（GUI と同順序）。"""
    roster = [_player(i + 1) for i in range(CONTRACT_ROSTER_MIN_SEASON + 1)]
    team = Team(team_id=1, name="RelT", league_level=1, money=500_000_000, players=list(roster))
    free_agents: list = []
    target = roster[-1]
    assert len(team.players) > CONTRACT_ROSTER_MIN_SEASON

    apply_release_player_to_fa(team, target, free_agents)

    assert target not in team.players
    assert target in free_agents
    assert len(team.players) == CONTRACT_ROSTER_MIN_SEASON
