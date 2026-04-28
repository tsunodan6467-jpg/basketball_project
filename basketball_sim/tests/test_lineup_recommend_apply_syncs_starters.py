"""起用序列反映相当の merge が rotation.starters のみ変え、他 rotation 欄を維持するか。"""

import pytest

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import (
    STARTER_POSITIONS,
    ensure_team_tactics_on_team,
    get_safe_team_tactics,
    normalize_team_tactics,
)


def _player(pid: int, position: str, ovr: int = 68) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=190.0,
        weight_kg=85.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def test_merge_rotation_starters_preserves_target_minutes_and_policies():
    """main_menu_view の反映後 merge と同形。starters だけ上書きしても target_minutes 等は保持される。"""
    t = Team(team_id=1, name="Home", league_level=1)
    positions = ["PG", "SG", "SF", "PF", "C", "PG"]
    for i, pos in enumerate(positions):
        t.add_player(_player(500 + i, pos, ovr=70))
    ensure_team_tactics_on_team(t)
    pids = {500 + i for i in range(6)}

    raw = dict(get_safe_team_tactics(t))
    rot = dict(raw.get("rotation") or {})
    rot["target_minutes"] = {"500": 31.0, "501": 29.5}
    rot["sub_policy"] = "starters_long"
    rot["fatigue_policy"] = "strict"
    rot["foul_policy"] = "early_pull"
    rot["clutch_policy"] = "hot_hand"
    rot["bench_order"] = [505, 504]
    raw["rotation"] = rot
    t.team_tactics = normalize_team_tactics(raw, valid_player_ids=pids)

    raw2 = dict(get_safe_team_tactics(t))
    rot2 = dict(raw2.get("rotation") or {})
    starters_map = {pos: 500 + i for i, pos in enumerate(STARTER_POSITIONS)}
    rot2["starters"] = starters_map
    raw2["rotation"] = rot2
    t.team_tactics = normalize_team_tactics(raw2, valid_player_ids=pids)

    out = get_safe_team_tactics(t)
    r = out["rotation"]
    assert r["target_minutes"]["500"] == pytest.approx(31.0)
    assert r["target_minutes"]["501"] == pytest.approx(29.5)
    assert r["sub_policy"] == "starters_long"
    assert r["fatigue_policy"] == "strict"
    assert r["foul_policy"] == "early_pull"
    assert r["clutch_policy"] == "hot_hand"
    assert r["bench_order"] == [505, 504]
    for i, pos in enumerate(STARTER_POSITIONS):
        assert r["starters"][pos] == 500 + i
