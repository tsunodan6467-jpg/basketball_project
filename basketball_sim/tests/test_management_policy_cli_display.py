"""management_policy_cli_display（CLI 施策サマリー表示）。"""

from basketball_sim.models.team import Team
from basketball_sim.systems.management_policy_cli_display import format_cli_management_policy_header_lines


def test_policy_header_none_team():
    text = "\n".join(format_cli_management_policy_header_lines(None))
    assert "【施策サマリー】" in text
    assert "メインスポンサー: 情報なし" in text
    assert "【施策の見どころ】" in text
    assert "情報なし" in text


def test_policy_header_fresh_team_default_sponsor_from_post_init():
    """Team 生成時に ensure が走り、メイン契約は既定で埋まる（表示のみ確認）。"""
    t = Team(team_id=1, name="T", league_level=1)
    text = "\n".join(format_cli_management_policy_header_lines(t))
    assert "メインスポンサー:" in text
    assert "スタンダード" in text
    assert "スポンサー履歴: 履歴なし" in text
    assert "広報履歴: 履歴なし" in text
    assert "グッズ履歴: 履歴なし" in text
    assert "取引ログ: 履歴なし" in text
    assert "スポンサー: 契約中" in text
    assert "広報: 未実行" in text
    assert "グッズ: 未実行" in text
    assert "取引: 履歴なし" in text


def test_policy_header_fully_empty_highlights_without_ensure_shape():
    class _BareTeam:
        pass

    b = _BareTeam()
    b.management = {}
    b.history_transactions = []
    text = "\n".join(format_cli_management_policy_header_lines(b))
    assert "メインスポンサー: 未設定" in text
    block = text.split("【施策の見どころ】", 1)[1].strip()
    assert block == "情報なし"


def test_policy_header_with_activity():
    t = Team(team_id=1, name="T", league_level=1)
    t.management = {
        "sponsors": {
            "main_contract_type": "local",
            "history": [{"season": 1}],
        },
        "pr_campaigns": {"history": [{"id": "x"}]},
        "merchandise": {"history": []},
    }
    t.history_transactions = [{"transaction_type": "trade"}]
    text = "\n".join(format_cli_management_policy_header_lines(t))
    assert "メインスポンサー: 地域・ローカル企業" in text
    assert "スポンサー履歴: 1件" in text
    assert "広報履歴: 1件" in text
    assert "グッズ履歴: 履歴なし" in text
    assert "取引ログ: 1件" in text
    assert "スポンサー: 契約中" in text
    assert "広報: 実行済み" in text
    assert "グッズ: 未実行" in text
    assert "取引: 履歴あり" in text


def test_policy_header_transactions_only_still_shows_lines():
    t = Team(team_id=1, name="T", league_level=1)
    t.history_transactions = [{"transaction_type": "sign"}]
    text = "\n".join(format_cli_management_policy_header_lines(t))
    assert "取引ログ: 1件" in text
    assert "取引: 履歴あり" in text
    assert "スポンサー: 契約中" in text
