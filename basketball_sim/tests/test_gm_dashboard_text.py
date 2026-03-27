"""gm_dashboard_text の読み取り専用フォーマット。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.gm_dashboard_text import (
    apply_starting_slot_change,
    format_gm_roster_text,
    format_lineup_snapshot_text,
    format_salary_cap_text,
    format_team_identity_text,
)


def _player(pid: int, position: str = "PG") -> Player:
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
        ovr=68,
        potential="B",
        archetype="guard",
        usage_base=20,
        contract_years_left=2,
        contract_total_years=2,
        salary=4_000_000,
    )


def test_format_team_identity_contains_name():
    t = Team(team_id=1, name="テストクラブ", league_level=1)
    text = format_team_identity_text(t)
    assert "テストクラブ" in text
    assert "戦術" in text


def test_format_salary_cap_contains_payroll():
    t = Team(team_id=1, name="T", league_level=1)
    p = _player(1)
    t.add_player(p)
    text = format_salary_cap_text(t)
    assert "Team Payroll" in text
    assert "Hard Cap" in text


def test_format_gm_roster_lists_player():
    t = Team(team_id=1, name="T", league_level=1)
    p = _player(2)
    t.add_player(p)
    text = format_gm_roster_text(t)
    assert "P2" in text
    assert "スタメン" in text or "★" in text


def test_format_lineup_snapshot_contains_sections():
    t = Team(team_id=1, name="T", league_level=1)
    for i in range(8):
        t.add_player(_player(100 + i))
    snap = format_lineup_snapshot_text(t)
    assert "【スタメン】" in snap
    assert "【ベンチ序列】" in snap
    assert "GMメニュー" in snap or "スタメン・ベンチ" in snap
    assert "自動スタメン" in snap


def test_apply_starting_slot_change_swaps_pg():
    t = Team(team_id=1, name="T", league_level=1)
    pg_a = _player(1, "PG")
    pg_b = _player(2, "PG")
    sg = _player(3, "SG")
    sf = _player(4, "SF")
    pf = _player(5, "PF")
    c = _player(6, "C")
    for p in (pg_a, pg_b, sg, sf, pf, c):
        t.add_player(p)
    t.set_starting_lineup_by_players([pg_a, sg, sf, pf, c])
    ok, msg = apply_starting_slot_change(t, 0, pg_b)
    assert ok and msg == ""
    starters = [getattr(p, "player_id", None) for p in t.get_starting_five()]
    assert starters[0] == 2


def test_apply_starting_slot_change_rejects_invalid_candidate():
    t = Team(team_id=1, name="T", league_level=1)
    pg = _player(1, "PG")
    sg = _player(2, "SG")
    sf = _player(3, "SF")
    pf = _player(4, "PF")
    c = _player(5, "C")
    orphan = _player(99, "PG")
    for p in (pg, sg, sf, pf, c):
        t.add_player(p)
    t.set_starting_lineup_by_players([pg, sg, sf, pf, c])
    ok, msg = apply_starting_slot_change(t, 0, orphan)
    assert not ok
    assert "選べません" in msg
