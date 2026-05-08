"""直近オフシーズン振り返り（閲覧専用）窓: 本文生成の文字列テスト。

Tk root を立てずに `MainMenuView._format_offseason_result_recap_text` を検証する。
"""

from types import SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def _fmt(team=None, season=None) -> str:
    fake_self = SimpleNamespace(team=None, season=season)
    return MainMenuView._format_offseason_result_recap_text(fake_self, team=team, season=season)


def test_team_none_returns_explanation_without_crash():
    body = _fmt(team=None)
    assert "直近オフシーズンの振り返り（閲覧専用）" in body
    assert "【クラブ】（チーム未設定）" in body
    assert "チーム未設定" in body


def test_empty_history_transactions_shows_placeholder():
    team = SimpleNamespace(
        name="テストクラブ",
        players=[],
        history_transactions=[],
        finance_history=[],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "【主な人事・移籍】" in body
    assert "該当する取引履歴はまだありません" in body


def test_free_agent_transaction_appears():
    team = SimpleNamespace(
        name="FAクラブ",
        players=[],
        history_transactions=[
            {
                "transaction_type": "free_agent",
                "player_name": "山田 太郎",
                "note": "fa_signing | player=山田 太郎",
            }
        ],
        finance_history=[],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "FA: 山田 太郎 を獲得" in body


def test_finance_history_latest_appears():
    team = SimpleNamespace(
        name="財務クラブ",
        players=[],
        history_transactions=[],
        finance_history=[
            {
                "revenue": 100,
                "expense": 40,
                "cashflow": 60,
                "ending_money": 999,
                "note": "memo",
            }
        ],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "【財務決算】" in body
    assert "黒字" in body
    assert "60" in body
    assert "100" in body or "売上" in body


def test_finance_fallback_fields_without_finance_history():
    team = SimpleNamespace(
        name="フィールドのみ",
        players=[],
        history_transactions=[],
        finance_history=[],
        revenue_last_season=50,
        expense_last_season=80,
        cashflow_last_season=-30,
        money=1000,
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "赤字" in body or "-30" in body


def test_promoted_milestone_appears():
    team = SimpleNamespace(
        name="昇格クラブ",
        players=[],
        history_transactions=[],
        finance_history=[],
        history_milestones=[
            {
                "milestone_type": "promoted",
                "title": "昇格",
                "detail": "D2 → D1",
            }
        ],
    )
    body = _fmt(team=team)
    assert "【昇降格・クラブ史】" in body
    assert "昇格" in body
    assert "D2 → D1" in body


def test_relegated_milestone_type_key_alternate():
    team = SimpleNamespace(
        name="降格クラブ",
        players=[],
        history_transactions=[],
        finance_history=[],
        history_milestones=[{"type": "relegated", "title": "降格", "detail": "D1 → D2"}],
    )
    body = _fmt(team=team)
    assert "降格" in body


def test_draft_rookie_on_roster_listed():
    rookie = SimpleNamespace(
        name="新人ドラフト",
        acquisition_type="draft",
        acquisition_note="auction_draft slot=A bid=123",
        is_draft_rookie_contract=True,
        draft_rookie_locked_salary=12_000_000,
    )
    team = SimpleNamespace(
        name="ドラフトクラブ",
        players=[rookie],
        history_transactions=[],
        finance_history=[],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "新人ドラフト" in body
    assert "ロスター上の新人契約フラグ" in body


def test_disclaimer_resign_and_draft_limitations_always_present():
    team = SimpleNamespace(
        name="注記クラブ",
        players=[],
        history_transactions=[],
        finance_history=[],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "【注記】" in body
    assert "history_transactions" in body or "チーム取引履歴" in body
    assert "オークション形式のドラフト" in body or "draft" in body


def test_career_resign_shows_when_present():
    player = SimpleNamespace(
        name="残留選手",
        career_history=[{"event": "Re-sign", "note": "3Y / 1,000"}],
    )
    team = SimpleNamespace(
        name="再契約クラブ",
        players=[player],
        history_transactions=[],
        finance_history=[],
        history_milestones=[],
    )
    body = _fmt(team=team)
    assert "選手キャリア" in body
    assert "Re-sign" in body
    assert "残留選手" in body


def test_does_not_mutate_history_lists():
    tx = [
        {"transaction_type": "free_agent", "player_name": "A", "note": "n"},
    ]
    fh = [{"revenue": 1, "expense": 1, "cashflow": 0, "ending_money": 5, "note": ""}]
    ms = [{"milestone_type": "promoted", "title": "昇格", "detail": "D3→D2"}]
    team = SimpleNamespace(
        name="不変テスト",
        players=[],
        history_transactions=tx,
        finance_history=fh,
        history_milestones=ms,
    )
    tx_before = list(tx)
    fh_before = list(fh)
    ms_before = list(ms)
    _ = _fmt(team=team)
    assert tx == tx_before
    assert fh == fh_before
    assert ms == ms_before
