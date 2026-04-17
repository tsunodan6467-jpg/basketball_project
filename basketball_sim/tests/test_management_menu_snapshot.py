"""management_menu_snapshot: 経営メニュー表示用スナップショット。"""

from types import SimpleNamespace

from basketball_sim.systems.management_menu_snapshot import (
    PR_FILTER_EXECUTABLE,
    PR_SORT_COST_ASC,
    build_action_affordance_summary_line,
    build_finance_history_note_summary_line,
    build_finance_pressure_summary_line,
    build_payroll_capacity_summary_line,
    build_soft_cap_headroom_summary_line,
    build_round_cash_memo_summary_line,
    build_owner_action_guidance_summary_line,
    build_management_menu_snapshot,
    _payroll_capacity_cap_align_suffix,
    _clamp_finance_dashboard_line,
    build_facility_affordance_summary_line,
    build_merchandise_affordance_summary_line,
    build_pr_affordance_summary_line,
    build_sponsor_affordance_summary_line,
    build_pr_campaign_comparison_entries,
    build_pr_dashboard_summary_line,
    build_pr_round_remaining_summary,
    count_executable_pr_campaigns,
)


def _fmt_money(n: int) -> str:
    return f"{int(n):,}円"


def _fmt_signed(n: int) -> str:
    s = "+" if int(n) > 0 else ""
    return f"{s}{int(n):,}円"


def _finance_block_body_from_dashboard(dashboard_text: str) -> str:
    start = dashboard_text.index("■ 財務\n") + len("■ 財務\n")
    end = dashboard_text.index("\n\n■ 施設")
    return dashboard_text[start:end]


def _facility_block_body_from_dashboard(dashboard_text: str) -> str:
    start = dashboard_text.index("\n\n■ 施設\n") + len("\n\n■ 施設\n")
    end = dashboard_text.index("\n\n■ 広報")
    return dashboard_text[start:end]


def test_dashboard_finance_lines_matches_dashboard_text():
    snap = build_management_menu_snapshot(
        None, None, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    assert len(snap.dashboard_finance_lines) == 17
    assert _finance_block_body_from_dashboard(snap.dashboard_text) == "\n".join(
        snap.dashboard_finance_lines
    )


def test_dashboard_facility_lines_match_dashboard_text():
    snap = build_management_menu_snapshot(
        None, None, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    assert _facility_block_body_from_dashboard(snap.dashboard_text) == "\n".join(
        snap.facility_lines
    )


def test_dashboard_pr_block_matches_pr_dashboard_summary():
    snap = build_management_menu_snapshot(
        None, None, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    start = snap.dashboard_text.index("\n\n■ 広報") + len("\n\n■ 広報")
    end = snap.dashboard_text.index("\n\n■ オーナー")
    tail = snap.dashboard_text[start:end].strip("\n")
    assert "■ 広報" + tail == snap.pr_dashboard_summary.strip()


def test_dashboard_owner_block_matches_owner_preamble():
    snap = build_management_menu_snapshot(
        None, None, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    start = snap.dashboard_text.index("\n\n■ オーナー\n") + len("\n\n■ オーナー\n")
    end = snap.dashboard_text.index("\n\n■ 実行履歴 / 直近アクション\n")
    body = snap.dashboard_text[start:end].rstrip("\n")
    assert body == snap.owner_preamble.strip()


def test_dashboard_history_block_body_has_expected_prefix_lines():
    snap = build_management_menu_snapshot(
        None, None, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    sep = "\n\n■ 実行履歴 / 直近アクション\n"
    start = snap.dashboard_text.index(sep) + len(sep)
    tail = snap.dashboard_text[start:]
    lines = [ln for ln in tail.rstrip("\n").split("\n") if ln != ""]
    assert len(lines) == 3
    assert lines[0].startswith("前回施策:")
    assert lines[1].startswith("結果:")
    assert lines[2].startswith("実行タイミング:")


def test_snapshot_team_none_no_empty_strings():
    snap = build_management_menu_snapshot(
        None,
        None,
        format_money=_fmt_money,
        format_signed_money=_fmt_signed,
    )
    assert len(snap.finance_lines) == 6
    assert len(snap.facility_lines) == 6
    assert "未設定" in snap.dashboard_text or "未実行" in snap.dashboard_text
    assert "履歴なし" in snap.dashboard_text
    assert "■ 広報: チーム未接続" in snap.dashboard_text
    assert snap.pr_dashboard_summary == "■ 広報: チーム未接続"
    assert snap.pr_affordance_summary == "広報余力: チーム未接続"
    assert snap.sponsor_affordance_summary == "スポンサー余力: チーム未接続"
    assert snap.dashboard_text.index("■ 財務") < snap.dashboard_text.index("総合アクション余力:")
    assert snap.dashboard_text.index("総合アクション余力:") < snap.dashboard_text.index("行動判断:")
    assert snap.dashboard_text.index("行動判断:") < snap.dashboard_text.index("財務圧力:")
    assert snap.dashboard_text.index("財務圧力:") < snap.dashboard_text.index("年俸枠メモ:")
    assert snap.dashboard_text.index("年俸枠メモ:") < snap.dashboard_text.index("キャップ余白:")
    assert snap.dashboard_text.index("キャップ余白:") < snap.dashboard_text.index("今ラウンド収支メモ:")
    assert snap.dashboard_text.index("今ラウンド収支メモ:") < snap.dashboard_text.index("直近財務メモ:")
    assert snap.dashboard_text.index("直近財務メモ:") < snap.dashboard_text.index("広報余力:")
    assert snap.dashboard_text.index("広報余力:") < snap.dashboard_text.index("スポンサー余力:")
    assert snap.dashboard_text.index("スポンサー余力:") < snap.dashboard_text.index("グッズ余力:")
    assert snap.dashboard_text.index("グッズ余力:") < snap.dashboard_text.index("施設余力:")
    assert snap.dashboard_text.index("施設余力:") < snap.dashboard_text.index("■ 施設")
    assert snap.merch_affordance_summary == "グッズ余力: チーム未接続"
    assert snap.facility_affordance_summary == "施設余力: チーム未接続"
    assert snap.action_affordance_summary == "総合アクション余力: チーム未接続"
    assert snap.owner_action_guidance_summary == "行動判断: チーム未接続"
    assert snap.finance_pressure_summary == "財務圧力: チーム未接続"
    assert snap.payroll_capacity_summary == "年俸枠メモ: チーム未接続"
    assert snap.soft_cap_headroom_summary == "キャップ余白: チーム未接続"
    assert snap.round_cash_memo_summary == "今ラウンド収支メモ: チーム未接続"
    assert snap.finance_history_note_summary == "直近財務メモ: チーム未接続"
    assert len(snap.dashboard_finance_lines) == 17
    assert _finance_block_body_from_dashboard(snap.dashboard_text) == "\n".join(
        snap.dashboard_finance_lines
    )
    assert "広報（今ラウンド）" in snap.pr_remaining_summary
    assert len(snap.pr_comparison_entries) >= 1


def test_pr_comparison_sort_and_filter():
    team = SimpleNamespace(
        money=800_000,
        is_user_team=True,
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 0, "history": []}},
    )

    class _S:
        current_round = 1
        total_rounds = 10
        season_finished = False

    rows_all = build_pr_campaign_comparison_entries(
        team, _S(), _fmt_money, sort_mode=PR_SORT_COST_ASC, filter_mode="all"
    )
    assert len(rows_all) == 3
    cids_asc = [cid for cid, _ in rows_all]
    assert cids_asc == ["sns_buzz", "community_day", "fan_festival"]

    rows_exe = build_pr_campaign_comparison_entries(
        team, _S(), _fmt_money, sort_mode=PR_SORT_COST_ASC, filter_mode=PR_FILTER_EXECUTABLE
    )
    assert len(rows_exe) == 1
    assert rows_exe[0][0] == "sns_buzz"


def test_snapshot_minimal_team_covers_blocks():
    team = SimpleNamespace(
        money=50_000_000,
        players=[],
        payroll_budget=80_000_000,
        cashflow_last_season=1_000_000,
        revenue_last_season=0,
        expense_last_season=0,
        market_size=1.0,
        fan_base=1000,
        season_ticket_base=0,
        sponsor_power=50,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
        regular_wins=5,
        regular_losses=3,
        owner_trust=55,
        owner_expectation="playoff_race",
        history_seasons=[],
        management={},
        finance_history=[],
        inseason_cash_round_log=[],
        is_user_team=True,
    )

    def _gf():
        return {
            "money": int(team.money),
            "payroll_budget": int(team.payroll_budget),
            "cashflow_last_season": int(team.cashflow_last_season),
            "market_size": float(team.market_size),
            "fan_base": int(team.fan_base),
            "season_ticket_base": int(team.season_ticket_base),
            "sponsor_power": int(team.sponsor_power),
        }

    team.get_financial_profile = _gf

    season = SimpleNamespace(current_round=10, total_rounds=40, season_finished=False)

    team.management = {"pr_campaigns": {"week_key": "round_10", "count_this_round": 1, "history": []}}
    assert "残り" in build_pr_round_remaining_summary(team, season)

    snap = build_management_menu_snapshot(
        team,
        season,
        format_money=_fmt_money,
        format_signed_money=_fmt_signed,
    )
    assert "■ 財務" in snap.dashboard_text
    assert len(snap.dashboard_finance_lines) == 17
    assert _finance_block_body_from_dashboard(snap.dashboard_text) == "\n".join(
        snap.dashboard_finance_lines
    )
    assert "■ 施設" in snap.dashboard_text
    assert "■ オーナー" in snap.dashboard_text
    assert "■ 実行履歴" in snap.dashboard_text
    assert "■ 広報:" in snap.dashboard_text
    assert "実行可候補" in snap.pr_dashboard_summary
    assert "広報余力:" in snap.dashboard_text
    assert "最安広報なら余裕あり" in snap.pr_affordance_summary
    assert "スポンサー余力:" in snap.dashboard_text
    assert "申込コストなし" in snap.sponsor_affordance_summary
    assert "グッズ余力:" in snap.dashboard_text
    assert "次工程" in snap.merch_affordance_summary
    assert "今なら進行可" in snap.merch_affordance_summary
    assert "施設余力:" in snap.dashboard_text
    assert "最安アップグレード" in snap.facility_affordance_summary
    assert "今なら投資可" in snap.facility_affordance_summary
    assert snap.action_affordance_summary.startswith("総合アクション余力:")
    assert "広報" in snap.action_affordance_summary and "件" in snap.action_affordance_summary
    assert "グッズ1件" in snap.action_affordance_summary
    assert "施設1件" in snap.action_affordance_summary
    assert "ミッション情報なし" in snap.owner_action_guidance_summary
    assert snap.finance_pressure_summary.startswith("財務圧力:")
    assert snap.payroll_capacity_summary == "年俸枠メモ: ロスター情報なし"
    assert snap.soft_cap_headroom_summary == "キャップ余白: ロスター情報なし"
    assert "直近記録なし" in snap.round_cash_memo_summary
    assert snap.finance_history_note_summary == "直近財務メモ: 直近 note なし"
    assert any("人件費" in x for x in snap.finance_lines)
    assert len(snap.facility_action_previews) == 4
    assert snap.pr_selection_preview.startswith("広報")
    assert "スポンサー力" in snap.sponsor_apply_preview or "費用なし" in snap.sponsor_apply_preview
    assert len(snap.merch_line_previews) >= 1
    assert "広報（今ラウンド）" in snap.pr_remaining_summary
    assert len(snap.pr_comparison_entries) >= 1


def test_pr_dashboard_and_executable_count():
    team = SimpleNamespace(
        money=10_000_000,
        is_user_team=True,
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 2, "history": []}},
    )
    season = SimpleNamespace(current_round=1, total_rounds=20, season_finished=False)
    line = build_pr_dashboard_summary_line(team, season)
    assert "■ 広報:" in line
    assert "残り 0 / 2 回" in line
    assert "実行可候補 0 件" in line
    assert count_executable_pr_campaigns(team, season) == 0

    team2 = SimpleNamespace(
        money=10_000_000,
        is_user_team=True,
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 0, "history": []}},
    )
    assert count_executable_pr_campaigns(team2, season) == 3


def _pr_team(money: int, *, used_round: int = 0, is_user: bool = True):
    return SimpleNamespace(
        money=money,
        is_user_team=is_user,
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": used_round, "history": []}},
    )


def test_pr_affordance_summary_tiers_and_edges():
    season = SimpleNamespace(current_round=1, total_rounds=20, season_finished=False)

    assert "チーム未接続" in build_pr_affordance_summary_line(None, season)
    assert "最安広報でも厳しい" in build_pr_affordance_summary_line(_pr_team(500_000), season)
    assert "最安広報でもぎりぎり" in build_pr_affordance_summary_line(_pr_team(650_000), season)
    assert "最安広報でもぎりぎり" in build_pr_affordance_summary_line(_pr_team(700_000), season)
    assert "最安広報なら実行可能" in build_pr_affordance_summary_line(_pr_team(900_000), season)
    assert "最安広報なら余裕あり" in build_pr_affordance_summary_line(_pr_team(2_000_000), season)

    finished = SimpleNamespace(current_round=1, total_rounds=20, season_finished=True)
    assert "今は広報不可" in build_pr_affordance_summary_line(_pr_team(50_000_000), finished)

    assert "今は広報不可" in build_pr_affordance_summary_line(
        _pr_team(50_000_000, used_round=2), season
    )

    no_money = SimpleNamespace(
        is_user_team=True,
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 0, "history": []}},
    )
    assert "所持金不明" in build_pr_affordance_summary_line(no_money, season)

    assert "今は広報不可" in build_pr_affordance_summary_line(
        _pr_team(2_000_000, is_user=False), season
    )


def test_sponsor_affordance_summary_line():
    assert "チーム未接続" in build_sponsor_affordance_summary_line(None, "standard")
    assert build_sponsor_affordance_summary_line(
        SimpleNamespace(
            money=1,
            is_user_team=True,
            management={"sponsors": {"main_contract_type": "standard", "history": []}},
        ),
        "not_a_sponsor_type",
    ).endswith("スポンサー候補なし")

    base = SimpleNamespace(
        money=10_000_000,
        is_user_team=True,
        sponsor_power=50,
        management={"sponsors": {"main_contract_type": "local", "history": []}},
    )
    assert "切替を検討可" in build_sponsor_affordance_summary_line(base, "title")

    same = SimpleNamespace(
        money=10_000_000,
        is_user_team=True,
        sponsor_power=50,
        management={"sponsors": {"main_contract_type": "standard", "history": []}},
    )
    assert "急がなくてよい" in build_sponsor_affordance_summary_line(same, "standard")

    assert "今は変更不可" in build_sponsor_affordance_summary_line(
        SimpleNamespace(
            money=10_000_000,
            is_user_team=False,
            sponsor_power=50,
            management={"sponsors": {"main_contract_type": "standard", "history": []}},
        ),
        "national",
    )

    no_money = SimpleNamespace(
        is_user_team=True,
        sponsor_power=50,
        management={"sponsors": {"main_contract_type": "local", "history": []}},
    )
    assert "所持金不明" in build_sponsor_affordance_summary_line(no_money, "title")


def _merch_mgmt_all_on_sale():
    return {
        "merchandise": {
            "items": [
                {
                    "id": "jersey_alt",
                    "category": "ユニフォーム",
                    "name": "オルタネイトジャージ",
                    "phase": "on_sale",
                },
                {
                    "id": "fan_towel",
                    "category": "観戦グッズ",
                    "name": "チーム応援タオル",
                    "phase": "on_sale",
                },
                {
                    "id": "acrylic_keychain",
                    "category": "小物",
                    "name": "アクリルキーホルダー",
                    "phase": "on_sale",
                },
            ],
            "history": [],
        }
    }


def test_merchandise_affordance_summary_line():
    assert "チーム未接続" in build_merchandise_affordance_summary_line(None, format_money=_fmt_money)

    user_m = SimpleNamespace(
        money=50_000_000,
        is_user_team=True,
        management={},
    )
    assert "420,000円" in build_merchandise_affordance_summary_line(user_m, format_money=_fmt_money)
    assert "今なら進行可" in build_merchandise_affordance_summary_line(user_m, format_money=_fmt_money)

    tight = SimpleNamespace(money=430_000, is_user_team=True, management={})
    assert "ぎりぎり" in build_merchandise_affordance_summary_line(tight, format_money=_fmt_money)

    poor = SimpleNamespace(money=100_000, is_user_team=True, management={})
    assert "今は厳しい" in build_merchandise_affordance_summary_line(poor, format_money=_fmt_money)

    released = SimpleNamespace(
        money=1,
        is_user_team=True,
        management=_merch_mgmt_all_on_sale(),
    )
    assert "発売中のため追加工程なし" in build_merchandise_affordance_summary_line(
        released, format_money=_fmt_money
    )

    assert "今は進行不可" in build_merchandise_affordance_summary_line(
        SimpleNamespace(money=10_000_000, is_user_team=False, management={}),
        format_money=_fmt_money,
    )

    no_money = SimpleNamespace(is_user_team=True, management={})
    assert "所持金不明" in build_merchandise_affordance_summary_line(no_money, format_money=_fmt_money)


def test_facility_affordance_summary_line():
    assert "チーム未接続" in build_facility_affordance_summary_line(None, format_money=_fmt_money)

    rich = SimpleNamespace(
        money=50_000_000,
        is_user_team=True,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
    )
    line = build_facility_affordance_summary_line(rich, format_money=_fmt_money)
    assert "最安アップグレード" in line
    assert "今なら投資可" in line

    tight = SimpleNamespace(
        money=950_000,
        is_user_team=True,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
    )
    assert "ぎりぎり" in build_facility_affordance_summary_line(tight, format_money=_fmt_money)

    poor = SimpleNamespace(
        money=100_000,
        is_user_team=True,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
    )
    assert "今は厳しい" in build_facility_affordance_summary_line(poor, format_money=_fmt_money)

    all_max = SimpleNamespace(
        money=1,
        is_user_team=True,
        arena_level=10,
        training_facility_level=10,
        medical_facility_level=10,
        front_office_level=10,
    )
    assert "全施設が最大レベル" in build_facility_affordance_summary_line(all_max, format_money=_fmt_money)

    assert "今は投資不可" in build_facility_affordance_summary_line(
        SimpleNamespace(
            money=50_000_000,
            is_user_team=False,
            arena_level=1,
            training_facility_level=1,
            medical_facility_level=1,
            front_office_level=1,
        ),
        format_money=_fmt_money,
    )

    no_money = SimpleNamespace(
        is_user_team=True,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
    )
    assert "所持金不明" in build_facility_affordance_summary_line(no_money, format_money=_fmt_money)


def test_facility_affordance_no_targets(monkeypatch):
    import basketball_sim.systems.management_menu_snapshot as mms

    monkeypatch.setattr(mms, "FACILITY_ORDER", ())
    t = SimpleNamespace(
        money=50_000_000,
        is_user_team=True,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
    )
    assert build_facility_affordance_summary_line(t, format_money=_fmt_money).endswith("投資先なし")


def test_action_affordance_summary_line():
    dummy = SimpleNamespace()

    assert build_action_affordance_summary_line(
        None,
        pr_executable_count=3,
        sponsor_affordance_summary="スポンサー余力: 切替を検討可",
        merch_affordance_summary="グッズ余力: 今なら進行可",
        facility_affordance_summary="施設余力: 今なら投資可",
    ).endswith("チーム未接続")

    assert "いま資金を動かせる候補なし" in build_action_affordance_summary_line(
        dummy,
        pr_executable_count=0,
        sponsor_affordance_summary="スポンサー余力: 申込コストなし・今は変更を急がなくてよい",
        merch_affordance_summary="グッズ余力: 発売中のため追加工程なし",
        facility_affordance_summary="施設余力: 全施設が最大レベル",
    )

    combo = build_action_affordance_summary_line(
        dummy,
        pr_executable_count=2,
        sponsor_affordance_summary="スポンサー余力: 申込コストなし・切替を検討可",
        merch_affordance_summary="グッズ余力: 次工程 420,000円・ぎりぎり",
        facility_affordance_summary="施設余力: 最安アップグレード 900,000円・今なら投資可",
    )
    assert "広報2件" in combo
    assert "スポンサー1件" in combo
    assert "グッズ1件" in combo
    assert "施設1件" in combo


def test_owner_action_guidance_summary_line():
    dummy = SimpleNamespace()

    assert build_owner_action_guidance_summary_line(
        None,
        finance_status="安全",
        owner_danger="おおむね安全",
        remaining_rounds=20,
        has_mission=True,
        mission_pct=80.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    ).endswith("チーム未接続")

    assert "ミッション情報なし" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="安全",
        owner_danger="未設定",
        remaining_rounds=10,
        has_mission=False,
        mission_pct=None,
        action_affordance_summary="総合: x",
    )

    assert "短期施策を急ぎたい" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="安全",
        owner_danger="やや危険（残り時間が少なく達成率が低い）",
        remaining_rounds=5,
        has_mission=True,
        mission_pct=20.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    )

    assert "資金温存" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="危険",
        owner_danger="おおむね安全",
        remaining_rounds=20,
        has_mission=True,
        mission_pct=80.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    )

    assert "投資余地あり" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="安全",
        owner_danger="注意",
        remaining_rounds=20,
        has_mission=True,
        mission_pct=60.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    )

    assert "急がなくてよい" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="安全",
        owner_danger="おおむね安全",
        remaining_rounds=20,
        has_mission=True,
        mission_pct=80.0,
        action_affordance_summary="総合アクション余力: いま資金を動かせる候補なし",
    )

    assert "状況確認を優先" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="注意",
        owner_danger="おおむね安全",
        remaining_rounds=0,
        has_mission=True,
        mission_pct=50.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    )

    assert "判定材料不足" in build_owner_action_guidance_summary_line(
        dummy,
        finance_status="注意",
        owner_danger="おおむね安全",
        remaining_rounds=20,
        has_mission=True,
        mission_pct=50.0,
        action_affordance_summary="総合アクション余力: 広報1件",
    )


def test_finance_pressure_summary_line():
    assert build_finance_pressure_summary_line(
        None,
        finance_status="安全",
        payroll=0,
        budget=0,
        cashflow_last=0,
        inseason_total=0,
    ).endswith("チーム未接続")

    rich = SimpleNamespace(league_level=1)
    s = build_finance_pressure_summary_line(
        rich,
        finance_status="安全",
        payroll=50_000_000,
        budget=80_000_000,
        cashflow_last=1_000_000,
        inseason_total=0,
    )
    assert "キャップ余力" in s or "黒字" in s

    tight = SimpleNamespace(league_level=1)
    cap_amt = 1_200_000_000
    payroll_tight = int(cap_amt * 0.95)
    assert "キャップ接近" in build_finance_pressure_summary_line(
        tight,
        finance_status="注意",
        payroll=payroll_tight,
        budget=payroll_tight,
        cashflow_last=0,
        inseason_total=0,
    )

    assert "赤字傾向" in build_finance_pressure_summary_line(
        SimpleNamespace(league_level=1),
        finance_status="危険",
        payroll=90_000_000,
        budget=70_000_000,
        cashflow_last=-5_000_000,
        inseason_total=0,
    )


def test_round_cash_memo_summary_line():
    assert build_round_cash_memo_summary_line(
        None,
        None,
        format_signed_money=_fmt_signed,
    ).endswith("チーム未接続")

    assert "判定材料不足" in build_round_cash_memo_summary_line(
        SimpleNamespace(inseason_cash_round_log="bad"),
        SimpleNamespace(current_round=1, season_finished=False),
        format_signed_money=_fmt_signed,
    )

    assert "直近記録なし" in build_round_cash_memo_summary_line(
        SimpleNamespace(inseason_cash_round_log=[]),
        SimpleNamespace(current_round=5, season_finished=False),
        format_signed_money=_fmt_signed,
    )

    league_k = "inseason_league_distribution_round"
    day_k = "inseason_matchday_estimate_round"
    team = SimpleNamespace(
        inseason_cash_round_log=[
            {"round_number": 3, "amount": 1_200_000, "key": league_k},
            {"round_number": 3, "amount": 350_000, "key": day_k},
        ]
    )
    season = SimpleNamespace(current_round=3, season_finished=False)
    line = build_round_cash_memo_summary_line(team, season, format_signed_money=_fmt_signed)
    assert "リーグ分配" in line or "主場" in line
    assert "+" in line or "1" in line

    big = SimpleNamespace(
        inseason_cash_round_log=[
            {"round_number": 1, "amount": 100_000, "key": league_k},
            {"round_number": 1, "amount": 200_000, "key": day_k},
            {"round_number": 1, "amount": 300_000, "key": league_k},
            {"round_number": 1, "amount": 400_000, "key": day_k},
        ]
    )
    assert "収入超過" in build_round_cash_memo_summary_line(
        big, SimpleNamespace(current_round=1, season_finished=False), format_signed_money=_fmt_signed
    )

    neg = SimpleNamespace(
        inseason_cash_round_log=[
            {"round_number": 2, "amount": -800_000, "key": "x"},
            {"round_number": 2, "amount": -900_000, "key": "y"},
            {"round_number": 2, "amount": -100_000, "key": "z"},
            {"round_number": 2, "amount": 50_000, "key": league_k},
        ]
    )
    assert "支出超過" in build_round_cash_memo_summary_line(
        neg, SimpleNamespace(current_round=2, season_finished=False), format_signed_money=_fmt_signed
    )


def test_finance_history_note_summary_line():
    assert build_finance_history_note_summary_line(None) == "直近財務メモ: チーム未接続"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(finance_history="x")
    ) == "直近財務メモ: 判定材料不足"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(finance_history=[])
    ) == "直近財務メモ: 直近 note なし"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(finance_history=[None])
    ) == "直近財務メモ: 判定材料不足"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(finance_history=[{"note": ""}])
    ) == "直近財務メモ: 直近 note なし"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[{"note": "facility_upgrade:arena_level:Lv2", "cashflow": -5_000_000}],
        )
    ) == "直近財務メモ: 施設投資を実施 (-)"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[{"note": "Wins:10 / Payroll:50,000,000 / Facility:1", "cashflow": 2_000_000}],
        )
    ) == "直近財務メモ: 前季の財務締めを記録 (+)"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {"note": "Wins:1 / Payroll:1 / Facility:0", "cashflow": 100},
                {"note": "facility_upgrade:arena_level:Lv2", "cashflow": -50},
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) / 前季の財務締めを記録 (+)"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {"note": "Wins:1 / Payroll:1 / Facility:0", "cashflow": 0},
                {"note": ""},
            ],
        )
    ) == "直近財務メモ: 前季の財務締めを記録 (±0)"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[{"note": "custom note", "cashflow": "nope"}],
        )
    ) == "直近財務メモ: custom note (?)"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {"note": "facility_upgrade:arena_level:Lv2", "cashflow": -1, "season_label": "S3"},
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) [S3]"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {"note": "Wins:1 / Payroll:1 / Facility:0", "cashflow": 100, "season_label": "S2"},
                {"note": "facility_upgrade:arena_level:Lv2", "cashflow": -50, "season_label": "S3"},
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) [S3] / 前季の財務締めを記録 (+) [S2]"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {"note": "Wins:1 / Payroll:1 / Facility:0", "cashflow": 1, "season_label": "S2"},
                {"note": "facility_upgrade:arena_level:Lv2", "cashflow": -1},
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) / 前季の財務締めを記録 (+) [S2]"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -1,
                    "season_label": "Season2028VeryLongTagName",
                },
            ],
        )
    ).startswith("直近財務メモ: 施設投資を実施 (-) [")
    assert "…]" in build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -1,
                    "season_label": "Season2028VeryLongTagName",
                },
            ],
        )
    )
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            payroll_budget=50_000_000,
            finance_history=[
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -1,
                    "season_label": "S3",
                    "ending_money": 380_000_000,
                },
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) [S3] <残高十分・相対余裕>"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            payroll_budget=80_000_000,
            finance_history=[
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -1,
                    "season_label": "S3",
                    "ending_money": 30_000_000,
                },
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) [S3] <残高要警戒・相対タイト>"
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            payroll_budget=100_000_000,
            finance_history=[
                {
                    "note": "Wins:1 / Payroll:1 / Facility:0",
                    "cashflow": 100,
                    "season_label": "S2",
                    "ending_money": 200_000_000,
                },
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -50,
                    "season_label": "S3",
                    "ending_money": 180_000_000,
                },
            ],
        )
    ) == (
        "直近財務メモ: 施設投資を実施 (-) [S3] <残高厚め・相対余裕> / "
        "前季の財務締めを記録 (+) [S2] <残高厚め・相対余裕>"
    )
    assert build_finance_history_note_summary_line(
        SimpleNamespace(
            payroll_budget=100_000_000,
            finance_history=[
                {
                    "note": "facility_upgrade:arena_level:Lv2",
                    "cashflow": -1,
                    "season_label": "S3",
                    "ending_money": 70_000_000,
                },
            ],
        )
    ) == "直近財務メモ: 施設投資を実施 (-) [S3] <残高注意・相対標準>"
    assert "<" not in build_finance_history_note_summary_line(
        SimpleNamespace(
            finance_history=[{"note": "x", "cashflow": 0, "ending_money": "bad"}],
        )
    )
    long_note = (
        "これはとても長い財務メモでダッシュボードでは丸める必要がある説明文です。"
        "追加の文で文字数を確実に超えて省略記号が付くようにします。"
    )
    line = build_finance_history_note_summary_line(
        SimpleNamespace(finance_history=[{"note": long_note}]),
    )
    assert line.startswith("直近財務メモ:")
    assert "…" in line
    assert len(line) < len("直近財務メモ: " + long_note)


def test_payroll_capacity_summary_line():
    assert build_payroll_capacity_summary_line(None) == "年俸枠メモ: チーム未接続"
    assert build_payroll_capacity_summary_line(SimpleNamespace(players=None)) == "年俸枠メモ: ロスター情報なし"
    assert build_payroll_capacity_summary_line(SimpleNamespace(players=[])) == "年俸枠メモ: ロスター情報なし"
    assert build_payroll_capacity_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=50_000_000)],
            payroll_budget=100_000_000,
            league_level=1,
        )
    ) == "年俸枠メモ: 予算に余裕あり（補強余地あり）"
    assert build_payroll_capacity_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=80_000_000)],
            payroll_budget=100_000_000,
            league_level=1,
        )
    ) == "年俸枠メモ: 予算比でやや重い"
    assert build_payroll_capacity_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=98_000_000)],
            payroll_budget=100_000_000,
            league_level=1,
        )
    ) == "年俸枠メモ: 予算近辺で圧迫（大型追加は注意）"
    assert build_payroll_capacity_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=1_300_000_000)],
            payroll_budget=1_200_000_000,
            league_level=1,
        )
    ) == "年俸枠メモ: キャップ近辺で注意"


def test_soft_cap_headroom_summary_line():
    assert build_soft_cap_headroom_summary_line(None) == "キャップ余白: チーム未接続"
    assert build_soft_cap_headroom_summary_line(SimpleNamespace(players=None)) == "キャップ余白: ロスター情報なし"
    assert build_soft_cap_headroom_summary_line(SimpleNamespace(players=[])) == "キャップ余白: ロスター情報なし"
    # D1 soft cap 12億: ややあり帯（余白比 ~12%）
    assert build_soft_cap_headroom_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=1_056_000_000)],
            league_level=1,
        )
    ) == "キャップ余白: ややあり"
    # 余白比 ~4% 以下 → ほぼなし
    assert build_soft_cap_headroom_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=1_152_000_000)],
            league_level=1,
        )
    ) == "キャップ余白: ほぼなし"
    # 十分な余白
    assert build_soft_cap_headroom_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=500_000_000)],
            league_level=1,
        )
    ) == "キャップ余白: あり"
    assert build_soft_cap_headroom_summary_line(
        SimpleNamespace(
            players=[SimpleNamespace(salary=1_300_000_000)],
            league_level=1,
        )
    ) == "キャップ余白: 超過中"


def test_clamp_finance_dashboard_line():
    assert _clamp_finance_dashboard_line("短い") == "短い"
    long_jp = "あ" * 80
    out = _clamp_finance_dashboard_line(long_jp)
    assert out.endswith("…")
    assert len(out) <= 72


def test_payroll_capacity_cap_align_suffix_unit():
    assert (
        _payroll_capacity_cap_align_suffix(
            "年俸枠メモ: 予算に余裕あり（補強余地あり）",
            "キャップ余白: ほぼなし",
        )
        == "\u3000[cap注意]"
    )
    assert (
        _payroll_capacity_cap_align_suffix(
            "年俸枠メモ: 予算近辺で圧迫（大型追加は注意）",
            "キャップ余白: あり",
        )
        == "\u3000[cap余白]"
    )
    assert _payroll_capacity_cap_align_suffix("年俸枠メモ: 予算に余裕あり（補強余地あり）", "キャップ余白: あり") == ""
    assert _payroll_capacity_cap_align_suffix("年俸枠メモ: チーム未接続", "キャップ余白: チーム未接続") == ""


def test_payroll_capacity_align_hint_on_snapshot_mismatch():
    season = SimpleNamespace(current_round=1, total_rounds=10, season_finished=False)

    def _gf(money, pb):
        return {
            "money": money,
            "payroll_budget": pb,
            "cashflow_last_season": 0,
            "market_size": 1.0,
            "fan_base": 1000,
            "season_ticket_base": 0,
            "sponsor_power": 50,
        }

    team_a = SimpleNamespace(
        money=2_000_000_000,
        players=[SimpleNamespace(salary=1_160_000_000)],
        payroll_budget=2_000_000_000,
        league_level=1,
        cashflow_last_season=0,
        revenue_last_season=0,
        expense_last_season=0,
        market_size=1.0,
        fan_base=1000,
        season_ticket_base=0,
        sponsor_power=50,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
        regular_wins=0,
        regular_losses=0,
        owner_trust=50,
        owner_expectation="playoff_race",
        history_seasons=[],
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 0, "history": []}},
        finance_history=[],
        inseason_cash_round_log=[],
        is_user_team=True,
    )
    team_a.get_financial_profile = lambda: _gf(team_a.money, team_a.payroll_budget)

    snap_a = build_management_menu_snapshot(
        team_a, season, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    assert "予算に余裕あり" in snap_a.payroll_capacity_summary
    assert "\u3000[cap注意]" in snap_a.payroll_capacity_summary
    assert snap_a.soft_cap_headroom_summary == "キャップ余白: ほぼなし"

    team_b = SimpleNamespace(
        money=2_000_000_000,
        players=[SimpleNamespace(salary=980_000_000)],
        payroll_budget=1_000_000_000,
        league_level=1,
        cashflow_last_season=0,
        revenue_last_season=0,
        expense_last_season=0,
        market_size=1.0,
        fan_base=1000,
        season_ticket_base=0,
        sponsor_power=50,
        arena_level=1,
        training_facility_level=1,
        medical_facility_level=1,
        front_office_level=1,
        regular_wins=0,
        regular_losses=0,
        owner_trust=50,
        owner_expectation="playoff_race",
        history_seasons=[],
        management={"pr_campaigns": {"week_key": "round_1", "count_this_round": 0, "history": []}},
        finance_history=[],
        inseason_cash_round_log=[],
        is_user_team=True,
    )
    team_b.get_financial_profile = lambda: _gf(team_b.money, team_b.payroll_budget)

    snap_b = build_management_menu_snapshot(
        team_b, season, format_money=_fmt_money, format_signed_money=_fmt_signed
    )
    assert "圧迫" in snap_b.payroll_capacity_summary
    assert "\u3000[cap余白]" in snap_b.payroll_capacity_summary
    assert snap_b.soft_cap_headroom_summary == "キャップ余白: あり"
