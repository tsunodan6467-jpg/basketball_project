"""負傷後の起用自動整合（試合終了フック用）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.injury_lineup_autorepair import auto_repair_lineup_for_injuries
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team


def _player(pid: int, position: str = "PG", ovr: int = 70) -> Player:
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
        archetype="guard",
        usage_base=20,
        contract_years_left=2,
        contract_total_years=2,
        salary=4_000_000,
    )


def test_autorepair_zeros_target_minutes_and_removes_injured_starter():
    t = Team(team_id=1, name="T", league_level=1)
    t.is_user_team = True
    pg_inj = _player(1, "PG", ovr=80)
    pg_inj.injury_games_left = 4
    sg = _player(2, "SG", ovr=72)
    sf = _player(3, "SF", ovr=71)
    pf = _player(4, "PF", ovr=70)
    c = _player(5, "C", ovr=69)
    b6 = _player(6, "PG", ovr=65)
    b7 = _player(7, "SG", ovr=64)
    for p in (pg_inj, sg, sf, pf, c, b6, b7):
        t.add_player(p)
    # セーブ互換の「IDだけ残って負傷者が先発に残る」ケースを模擬
    t.starting_lineup = [1, 2, 3, 4, 5]
    t.sixth_man_id = 6
    ensure_team_tactics_on_team(t)
    rot = t.team_tactics["rotation"]
    rot["target_minutes"]["1"] = 32.0
    rot["starters"] = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
    rot["bench_order"] = [6, 7]

    assert auto_repair_lineup_for_injuries(t) is True

    rot_after = t.team_tactics["rotation"]
    assert float(rot_after["target_minutes"].get("1", 0)) == 0.0
    assert 1 not in t.starting_lineup
    assert 1 not in (rot_after["bench_order"] or [])
    notice = getattr(t, "_injury_autorepair_notice_jp", "")
    assert "手動で再構築" in notice


def test_no_injury_returns_false():
    t = Team(team_id=1, name="T", league_level=1)
    t.add_player(_player(1, "PG"))
    ensure_team_tactics_on_team(t)
    assert auto_repair_lineup_for_injuries(t) is False
