"""オークションドラフト指名/落札時の team.history_transactions 1 行追記テスト。

通常ドラフト側 `draft._record_team_draft_history` と同じ transaction_type="draft" で
吸収する。save 構造は変更しない。Player 側 acquisition / rookie 契約フィールドは壊さない。
"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.draft_auction import (
    _record_team_auction_draft_history,
    _set_drafted_player_contract,
)


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"R{pid}",
        age=19,
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
        ovr=72,
        potential="A",
        archetype="guard",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def test_record_team_auction_draft_history_appends_draft_row():
    t = Team(team_id=1, name="ドラフトT", league_level=1)
    p = _player(9101)
    before = list(getattr(t, "history_transactions", []) or [])

    _record_team_auction_draft_history(t, p, slot="A", bid=12_000_000)

    after = list(getattr(t, "history_transactions", []) or [])
    added = after[len(before):]
    assert len(added) == 1
    row = added[0]
    assert row["transaction_type"] == "draft"
    assert row["player_id"] == p.player_id
    assert row["player_name"] == p.name
    note = str(row.get("note", ""))
    assert note.startswith("auction_draft")
    assert "slot=A" in note
    assert "bid=12,000,000" in note
    assert "ovr=" in note
    assert "potential=" in note


def test_record_team_auction_draft_history_does_not_mutate_player_fields():
    """履歴追記は player の既存属性に副作用を起こさない。"""
    t = Team(team_id=2, name="副作用T", league_level=2)
    p = _player(9102)
    _set_drafted_player_contract(p, "B", 8_000_000)

    pre_acq = p.acquisition_type
    pre_note = p.acquisition_note
    pre_salary = p.salary
    pre_locked = p.draft_rookie_locked_salary
    pre_years = p.contract_years_left
    pre_is_rookie = p.is_draft_rookie_contract

    _record_team_auction_draft_history(t, p, slot="B", bid=8_000_000)

    assert p.acquisition_type == pre_acq
    assert p.acquisition_note == pre_note
    assert p.salary == pre_salary
    assert p.draft_rookie_locked_salary == pre_locked
    assert p.contract_years_left == pre_years
    assert p.is_draft_rookie_contract == pre_is_rookie


def test_record_team_auction_draft_history_safe_for_team_without_api():
    """add_history_transaction を持たないチームでも例外を出さない（互換）。"""

    class _MinimalTeam:
        team_id = 9
        name = "互換T"

    fake_team = _MinimalTeam()
    p = _player(9103)

    _record_team_auction_draft_history(fake_team, p, slot="A", bid=1_000_000)


def test_recap_window_picks_up_auction_draft_after_helper():
    """ヘルパー実行後、直近オフ振り返りの「主な人事・移籍」に draft 行が現れる。"""
    from basketball_sim.systems.main_menu_view import MainMenuView
    from types import SimpleNamespace

    t = Team(team_id=3, name="連結T", league_level=1)
    p = _player(9104)
    _set_drafted_player_contract(p, "A", 25_000_000)
    _record_team_auction_draft_history(t, p, slot="A", bid=25_000_000)

    fake_self = SimpleNamespace(team=None, season=None)
    body = MainMenuView._format_offseason_result_recap_text(fake_self, team=t, season=None)

    assert "ドラフト:" in body
    assert "R9104" in body
    assert "auction_draft" in body
