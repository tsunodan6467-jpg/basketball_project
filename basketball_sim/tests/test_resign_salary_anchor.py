"""再契約 anchor（正本 v1.1 帯）のスモークと実測用表。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import calculate_desired_salary
from basketball_sim.systems.resign_salary_anchor import (
    blend_desired_salary_for_resign,
    resign_anchor_debug,
)


def _p(pid: int, ovr: int, age: int, nat: str, salary: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality=nat,
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
        ovr=ovr,
        potential="B",
        archetype="wing",
        usage_base=20,
        contract_years_left=1,
        contract_total_years=2,
        salary=salary,
        popularity=55,
        career_games_played=40,
        peak_ovr=ovr,
    )


def _team13(div: int, focus: Player, filler_ovr: int = 55) -> Team:
    """focus を OVR 順で 6 番手（middle 帯）に置く 13 人チーム。"""
    t = Team(team_id=1, name="T", league_level=div)
    players: list[Player] = []
    for i in range(13):
        if i == 5:
            players.append(focus)
            continue
        o = 90 - i if i < 5 else filler_ovr
        nat = "Japan" if i not in (2, 3) else "Foreign"
        players.append(_p(100 + i, o, 26, nat, 8_000_000))
    for p in players:
        t.add_player(p)
    return t


def _team_focus_top(div: int, focus: Player) -> Team:
    """focus が OVR 1 位（top 帯）になる 13 人チーム。"""
    t = Team(team_id=1, name="T", league_level=div)
    for i in range(12):
        t.add_player(_p(300 + i, 48, 26, "Japan", 5_000_000))
    t.add_player(focus)
    return t


def test_blend_clamps_extreme_raw():
    raw = 400_000_000
    p = _p(1, 78, 28, "Japan", 45_000_000)
    team = _team13(1, p)
    out = blend_desired_salary_for_resign(p, team, raw)
    dbg = resign_anchor_debug(p, team, raw)
    assert dbg["anchor_lo"] <= out <= dbg["anchor_hi_effective"]
    assert out < raw


def test_young_19_capped_below_middle_hi_d1_foreign():
    p = _p(2, 82, 19, "Foreign", 12_000_000)
    team = _team_focus_top(1, p)
    raw = calculate_desired_salary(p)
    out = blend_desired_salary_for_resign(p, team, raw)
    dbg = resign_anchor_debug(p, team, raw)
    assert dbg["age"] == 19
    assert out <= 55_000_000
    assert out <= 135_000_000


def test_naturalized_desired_ge_foreign_d1_middle():
    n = _p(12, 76, 27, "Naturalized", 120_000_000)
    f = _p(13, 76, 27, "Foreign", 100_000_000)
    tn = _team13(1, n, filler_ovr=54)
    tf = _team13(1, f, filler_ovr=54)
    rn = calculate_desired_salary(n)
    rf = calculate_desired_salary(f)
    assert blend_desired_salary_for_resign(n, tn, rn) >= blend_desired_salary_for_resign(f, tf, rf)


def test_foreign_desired_ge_japan_same_slot_d3():
    j = _p(10, 68, 26, "Japan", 14_000_000)
    f = _p(11, 68, 26, "Foreign", 16_000_000)
    tj = _team13(3, j, filler_ovr=52)
    tf = _team13(3, f, filler_ovr=52)
    raw_j = calculate_desired_salary(j)
    raw_f = calculate_desired_salary(f)
    bj = blend_desired_salary_for_resign(j, tj, raw_j)
    bf = blend_desired_salary_for_resign(f, tf, raw_f)
    assert bf >= bj


def test_print_resign_anchor_table(capsys):
    """pytest -s で表を目視する用。"""
    rows = []
    for div, nat, age, ovr, sal in [
        (1, "Japan", 27, 76, 72_000_000),
        (1, "Foreign", 27, 76, 95_000_000),
        (1, "Naturalized", 27, 76, 100_000_000),
        (1, "Asia", 27, 76, 50_000_000),
        (2, "Japan", 26, 70, 28_000_000),
        (2, "Foreign", 26, 70, 45_000_000),
        (3, "Japan", 24, 66, 12_000_000),
        (3, "Foreign", 24, 66, 22_000_000),
        (3, "Japan", 19, 72, 5_000_000),
        (3, "Foreign", 22, 74, 6_000_000),
    ]:
        p = _p(200 + len(rows), ovr, age, nat, sal)
        team = _team13(div, p, filler_ovr=48 if div == 3 else 52)
        raw = calculate_desired_salary(p)
        d = resign_anchor_debug(p, team, raw)
        rows.append((div, nat, age, ovr, raw, d["blended_desired"], d["anchor_lo"], d["anchor_mid"], d["anchor_hi_effective"], d["role_band"]))

    lines = ["div nat age ovr raw new lo mid hi_eff role"]
    for r in rows:
        lines.append(" ".join(str(x) for x in r))
    print("\n" + "\n".join(lines))
    assert rows[1][5] >= rows[0][5]
