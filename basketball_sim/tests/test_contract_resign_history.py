"""apply_resign が team.history_transactions に "resign" 行を追加する小PRテスト。

save 構造は変更しない。Player.career_history の Re-sign 既存記録は壊さない。
draft rookie の早期 return では履歴を残さない（誤記録なし）。
"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import apply_resign
from basketball_sim.systems.draft_auction import _set_drafted_player_contract


def _player(pid: int, age: int = 26) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=age,
        nationality="Japan",
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
        ovr=70,
        potential="B",
        archetype="wing",
        usage_base=20,
        contract_years_left=1,
        contract_total_years=1,
        salary=5_000_000,
    )


def test_apply_resign_appends_resign_transaction_to_team_history():
    t = Team(team_id=1, name="再契約T", league_level=1)
    p = _player(101)
    t.add_player(p)
    before = list(getattr(t, "history_transactions", []) or [])

    apply_resign(t, p, 8_000_000, 2)

    after = list(getattr(t, "history_transactions", []) or [])
    added = after[len(before):]
    assert len(added) == 1
    row = added[0]
    assert row["transaction_type"] == "resign"
    assert row["player_id"] == p.player_id
    assert row["player_name"] == p.name
    note = str(row.get("note", ""))
    assert note.startswith("resign")
    assert "salary=8,000,000" in note
    assert "years=2" in note


def test_apply_resign_keeps_existing_career_history_resign():
    """team.history_transactions に行が増えても player.career_history の Re-sign は維持される。"""
    t = Team(team_id=2, name="併存T", league_level=1)
    p = _player(102)
    t.add_player(p)

    apply_resign(t, p, 6_000_000, 3)

    ch = list(getattr(p, "career_history", []) or [])
    assert ch, "player.career_history に Re-sign が記録されること"
    re_sign_rows = [row for row in ch if isinstance(row, dict) and row.get("event") == "Re-sign"]
    assert len(re_sign_rows) == 1
    assert "3Y" in str(re_sign_rows[0].get("note", ""))


def test_apply_resign_does_not_record_history_for_draft_rookie():
    """draft rookie 期間中は apply_resign が早期 return するため history も残さない。"""
    t = Team(team_id=3, name="ルーキーT", league_level=1)
    p = _player(103, age=19)
    _set_drafted_player_contract(p, "A", 30_000_000)
    t.add_player(p)
    before_len = len(getattr(t, "history_transactions", []) or [])

    apply_resign(t, p, 80_000_000, 2)

    after_len = len(getattr(t, "history_transactions", []) or [])
    assert after_len == before_len
    assert p.salary == 30_000_000
    assert p.contract_years_left == 3


def test_apply_resign_handles_team_without_add_history_transaction_gracefully():
    """add_history_transaction を持たないオブジェクトでも例外を出さない（互換）。"""

    class _MinimalTeam:
        team_id = 9
        name = "互換T"

    p = _player(104)
    fake_team = _MinimalTeam()

    apply_resign(fake_team, p, 5_000_000, 1)

    assert p.contract_last_action == "resign"
    assert p.contract_years_left == 1
