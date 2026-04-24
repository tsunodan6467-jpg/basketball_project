"""自動役割タグ（docs/AUTO_ROLE_TAG_PARAMS.md）。表示専用。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.auto_role_tag import (
    TAG_ACE,
    TAG_BENCH_SCORER,
    TAG_FLOOR_GENERAL,
    TAG_PERIMETER_STOPPER,
    TAG_RIM_PROTECTOR,
    TAG_ROLE_PLAYER,
    TAG_SHOOTER,
    compute_auto_role_tags_for_team,
)
from basketball_sim.systems.gm_dashboard_text import format_gm_roster_text, format_lineup_snapshot_text


def _p(
    pid: int,
    *,
    position: str = "PG",
    ovr: int = 68,
    three: int = 60,
    defense: int = 60,
    passing: int = 60,
    shoot: int = 60,
    drive: int = 60,
    rebound: int = 60,
) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=190.0,
        weight_kg=85.0,
        shoot=shoot,
        three=three,
        drive=drive,
        passing=passing,
        rebound=rebound,
        defense=defense,
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


def test_bench_scorer_when_sixth_and_scoring_bench():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    b6 = _p(6, position="PG", shoot=70, three=70, drive=70)
    b7 = _p(7, position="PG")
    b8 = _p(8, position="PG")
    for p in starters + [b6, b7, b8]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.sixth_man_id = 6
    t.team_tactics = {
        "rotation": {"target_minutes": {"6": 30.0, "7": 10.0, "8": 5.0}},
        "roles": {
            "6": {"offense_involvement": "high", "shot_priority": "standard", "defense_assignment": "standard"},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_BENCH_SCORER


def test_ace_starter_ovr_and_usage():
    t = Team(team_id=1, name="T", league_level=1)
    players = [
        _p(1, ovr=82, position="PG"),
        _p(2, ovr=70, position="SG"),
        _p(3, ovr=69, position="SF"),
        _p(4, ovr=68, position="PF"),
        _p(5, ovr=67, position="C"),
        _p(6, position="PG"),
    ]
    for p in players:
        t.add_player(p)
    t.set_starting_lineup_by_players(players[:5])
    t.team_tactics = {
        "rotation": {"target_minutes": {"1": 35.0}},
        "roles": {"1": {"clutch_priority": "go_to"}},
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(1) == TAG_ACE


def test_floor_general_playmaking_primary():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos, ovr=80 - i) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    # ベンチ2人: 7 の方が得点合成が高く、6 は合成2位 → ベンチスコアラー条件 E を満たさない
    bench_hi = _p(7, position="PG", ovr=52, shoot=80, three=80, drive=80)
    bench_pg = _p(6, position="PG", ovr=51, passing=85, shoot=40, three=40, drive=40)
    for p in starters + [bench_pg, bench_hi]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {
        "roles": {
            "6": {"playmaking_role": "primary", "offense_involvement": "standard", "shot_priority": "passive"},
            "7": {"offense_involvement": "standard", "shot_priority": "standard"},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_FLOOR_GENERAL


def test_shooter_three_threshold_after_higher_priority():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos, ovr=75) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    filler = _p(7, position="PG", ovr=54, shoot=90, three=90, drive=90)
    bench = _p(6, position="PG", ovr=55, three=65, passing=40, shoot=50, drive=40)
    for p in starters + [bench, filler]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {
        "roles": {
            "6": {"shot_priority": "standard", "playmaking_role": "minimal", "offense_involvement": "standard"},
            "7": {"offense_involvement": "standard", "shot_priority": "standard"},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_SHOOTER


def test_rim_protector_pf_stopper():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos, defense=50) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    big = _p(6, position="PF", defense=88, rebound=80, ovr=72, shoot=40, three=40, drive=40)
    bench2 = _p(7, position="PG", defense=40, shoot=85, three=85, drive=85)
    for p in starters + [big, bench2]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {
        "roles": {
            "6": {"defense_assignment": "stopper", "offense_involvement": "standard", "shot_priority": "passive"},
            "7": {"offense_involvement": "standard"},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_RIM_PROTECTOR


def test_perimeter_stopper_sg_stopper():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos, defense=50) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    wing = _p(6, position="SG", defense=90, ovr=73, shoot=40, three=40, drive=40)
    other = _p(7, position="PG", defense=45, shoot=85, three=85, drive=85)
    for p in starters + [wing, other]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {
        "roles": {
            "6": {"defense_assignment": "stopper", "shot_priority": "passive"},
            "7": {},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_PERIMETER_STOPPER


def test_standard_defense_assignment_no_defense_tag():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    b = _p(6, position="SG", defense=95)
    for p in starters + [b]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {"roles": {"6": {"defense_assignment": "standard"}}}
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) not in (TAG_PERIMETER_STOPPER, TAG_RIM_PROTECTOR)


def test_role_player_fallback():
    t = Team(team_id=1, name="T", league_level=1)
    starters = [_p(i, position=pos, ovr=78) for i, pos in zip(range(1, 6), ("PG", "SG", "SF", "PF", "C"))]
    weak = _p(6, position="PG", ovr=40, three=40, passing=20, shoot=40, drive=40, defense=40)
    filler = _p(7, position="PG", ovr=41, shoot=80, three=80, drive=80)
    for p in starters + [weak, filler]:
        t.add_player(p)
    t.set_starting_lineup_by_players(starters)
    t.team_tactics = {
        "roles": {
            "6": {"defense_assignment": "light", "shot_priority": "passive", "offense_involvement": "low"},
            "7": {"offense_involvement": "standard"},
        },
    }
    tags = compute_auto_role_tags_for_team(t)
    assert tags.get(6) == TAG_ROLE_PLAYER


def test_format_gm_roster_and_lineup_use_auto_tags_not_manual_main_role():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(8):
        t.add_player(_p(100 + i))
    t.team_tactics = {"roles": {"107": {"main_role": "ace"}}}
    roster_txt = format_gm_roster_text(t)
    lineup_txt = format_lineup_snapshot_text(t)
    assert roster_txt.count("タグ:") >= 8
    assert lineup_txt.count("タグ:") >= 8
    for line in roster_txt.splitlines():
        if "P107" in line and "Salary" in line:
            assert "ロールプレイヤー" in line or "ベンチスコアラー" in line
            assert "タグ: エース" not in line
            break
    else:
        raise AssertionError("P107 line not found")
