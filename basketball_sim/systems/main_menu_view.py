"""
Minimal main menu / dashboard UI for Basketball Project.

Recommended location:
    basketball_sim/systems/main_menu_view.py

Design goals
------------
- Safe first implementation for Phase 4.
- Does not modify game state by itself.
- Can run even when some team / season attributes are missing.
- Keeps existing CLI flow intact until main.py is explicitly wired.

What this file provides
-----------------------
- MainMenuView: Tkinter based minimal dashboard.
- launch_main_menu(...): small helper to open the window.

Notes
-----
- This file is intentionally read-mostly. Mutations: optional on_advance (injected),
  and 人事ウィンドウの契約＋1年延長・契約解除（FA）（条件付き）。
- The UI tolerates partial data. Missing values fall back to safe placeholders.
- Detailed screen transitions are not implemented yet; each left menu item is a
  safe callback hook point.
"""

from __future__ import annotations

from copy import deepcopy

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from datetime import datetime, date
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from basketball_sim.systems.gm_dashboard_text import (
    apply_bench_order_swap,
    apply_sixth_man_selection,
    apply_starting_slot_change,
    format_gm_roster_text,
    format_lineup_snapshot_text,
    format_salary_cap_text,
    format_team_identity_text,
    get_available_starting_candidates,
    get_current_bench_order,
    get_current_sixth_man,
    get_current_starting_five,
    get_sixth_man_candidates,
    sort_roster_for_gm_view,
)
from basketball_sim.systems.gm_ui_constants import (
    COACH_STYLE_OPTIONS,
    STRATEGY_OPTIONS,
    USAGE_POLICY_OPTIONS,
    apply_team_gm_settings,
)
from basketball_sim.systems.season_transaction_rules import (
    INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
    inseason_roster_moves_unlocked,
)
from basketball_sim.systems.money_display import (
    format_money_yen_ja_readable,
    format_signed_money_yen_ja_readable,
)
from basketball_sim.systems.training_unlocks import player_drill_lock_reason
from basketball_sim.systems.team_tactics import (
    MAIN_ROLE_COMBO_OPTIONS,
    PLAYSTYLE_PRESET_DEFS,
    ROTATION_PRESET_DEFS,
    STARTER_POSITIONS,
    apply_playstyle_preset_with_preset_meta,
    apply_rotation_preset_with_preset_meta,
    ensure_team_tactics_on_team,
    get_current_playstyle_preset_state,
    get_current_rotation_preset_state,
    get_default_team_tactics,
    get_safe_team_tactics,
    normalize_team_tactics,
)

# 戦術メニュー用: preset_id ベースの短い説明（label_ja 重複に依存しない）
_PLAYSTYLE_PRESET_DESC_JA: Dict[str, str] = {
    "balanced_v1": "攻守のバランスを重視する標準型。迷ったときの基本設定。",
    "run_and_gun_3p_v1": "速い展開と3Pを重視する攻撃型。得点力を狙うが、試合は荒れやすい。",
    "defense_first_v1": "守備と失点抑制を重視する型。得点は伸びにくいが、粘り強く戦う。",
}
_PLAYSTYLE_PRESET_TOOLTIP_JA: Dict[str, str] = {
    "balanced_v1": "標準的な攻守・起用バランス。",
    "run_and_gun_3p_v1": "速攻と3Pを増やす攻撃型。",
    "defense_first_v1": "ペースを落として守備を重視。",
}
_ROTATION_PRESET_DESC_JA: Dict[str, str] = {
    "balanced_v1": "勝利と育成のバランスを取る標準型。極端に偏らない起用。",
    "win_now_v1": "主力をやや長めに起用する型。短期的な勝ち星を狙う。",
    "development_v1": "若手や控えの出場機会をやや重視する型。長期育成に向く。",
    "condition_care_v1": "疲労・ケガ・連戦を重視し、主力の酷使を避ける起用方針です。",
}
_ROTATION_PRESET_TOOLTIP_JA: Dict[str, str] = {
    "balanced_v1": "標準的な攻守・起用バランス。",
    "win_now_v1": "主力をやや長めに起用。",
    "development_v1": "若手・控えをやや使いやすくする。",
    "condition_care_v1": "ケガ配慮と連戦時運用を強め、疲労時の交代判断をやや早めます。先発・6th・ベンチ順は自動変更せず、必要に応じて手動で調整します。",
}


def _tactics_preset_desc_ui_text(
    preset_id: Optional[str],
    desc_map: Dict[str, str],
    tip_map: Dict[str, str],
    valid_ids: Tuple[str, ...],
    fallback_id: str = "balanced_v1",
) -> str:
    """未知ID・未設定時はバランス型の説明にフォールバック。"""
    pid = (preset_id or "").strip() if isinstance(preset_id, str) else None
    if not pid or pid not in valid_ids:
        pid = fallback_id
    desc = desc_map.get(pid) or desc_map.get(fallback_id, "プリセットの説明がありません。")
    tip = tip_map.get(pid) or tip_map.get(fallback_id, "")
    if tip:
        return f"{desc}\n（{tip}）"
    return desc


from basketball_sim.systems.facility_investment import (
    FACILITY_LABELS,
    FACILITY_MAX_LEVEL,
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
    get_facility_upgrade_cost,
)

# 施設ウィンドウ用の短文（ロジックは変えず表示のみ）
_FACILITY_MANAGEMENT_EFFECT_BLURB_JA: Dict[str, str] = {
    "arena_level": "効果（目安）: 集客・ファン基盤・収支（ゲート収入等）に関係します。",
    "training_facility_level": "効果（目安）: 育成・練習の効き方（強化メニュー側の条件）に関係します。",
    "medical_facility_level": "効果（目安）: 疲労・ケア・一部練習解放（強化メニュー側の条件）に関係します。",
    "front_office_level": "効果（目安）: スカウト水準・経営補助に関係します。",
}
from basketball_sim.systems.contract_logic import (
    MAX_CONTRACT_YEARS_DEFAULT,
    apply_contract_extension,
    get_expiring_players,
    is_draft_rookie_contract_active,
)
from basketball_sim.systems.roster_fa_release import (
    apply_release_player_to_fa,
    postcheck_release_player_to_fa_season,
    precheck_release_player_to_fa,
)
from basketball_sim.systems.sponsor_management import (
    MAIN_SPONSOR_CLI_COMPARISON_HINTS,
    MAIN_SPONSOR_IDS,
    MAIN_SPONSOR_TYPES,
    commit_main_sponsor_contract,
    ensure_sponsor_management_on_team,
    format_sponsor_history_lines,
    label_for_main_sponsor_type,
)
from basketball_sim.systems.pr_campaign_management import (
    MAX_ACTIONS_PER_ROUND,
    PR_CAMPAIGN_CLI_COMPARISON_HINTS,
    PR_CAMPAIGNS,
    can_commit_pr_campaign,
    commit_pr_campaign,
    format_pr_history_lines,
    format_pr_status_line,
    resolve_pr_round_context,
    sync_pr_round_quota,
)
from basketball_sim.systems.merchandise_management import (
    ADVANCE_COST,
    MERCH_PRODUCTS,
    PHASE_LABEL_JA,
    advance_merchandise_phase,
    can_advance_merchandise_phase,
    ensure_merchandise_on_team,
    estimate_dummy_merch_sales_lines,
    format_merchandise_advance_cost_yen_display,
    format_merchandise_history_lines,
    format_merchandise_row_display,
    get_merchandise_item,
    normalize_merchandise_phase_value,
)
from basketball_sim.systems.management_menu_snapshot import (
    PR_FILTER_AFFORDABLE,
    PR_FILTER_ALL,
    PR_FILTER_EXECUTABLE,
    PR_FILTER_FAN_HEAVY,
    PR_FILTER_POP_HEAVY,
    PR_SORT_COST_ASC,
    PR_SORT_COST_DESC,
    PR_SORT_DEFAULT,
    build_management_menu_snapshot,
    build_merchandise_affordance_summary_line,
    build_pr_selection_preview_line,
)

_PR_FINANCE_SORT_ORDER = (PR_SORT_DEFAULT, PR_SORT_COST_ASC, PR_SORT_COST_DESC)
_PR_FINANCE_SORT_LABELS_JA = ("表示順（既定）", "コスト昇順", "コスト降順")
_PR_FINANCE_FILTER_ORDER = (
    PR_FILTER_ALL,
    PR_FILTER_EXECUTABLE,
    PR_FILTER_AFFORDABLE,
    PR_FILTER_POP_HEAVY,
    PR_FILTER_FAN_HEAVY,
)
_PR_FINANCE_FILTER_LABELS_JA = (
    "すべて",
    "実行可のみ",
    "予算内のみ（所持金で支払可）",
    "人気効果大（人気+2以上）",
    "ファン基盤寄り（ファン+240以上）",
)

# Management dashboard: split finance block from the rest for line-by-line Text insert.
_MANAGEMENT_FINANCE_BLOCK_SEPARATOR = "\n\n■ 施設"
# After 施設 body, PR summary line starts with this (matches `build_pr_dashboard_summary_line`).
_MANAGEMENT_FACILITY_PR_SEPARATOR = "\n\n■ 広報"
_MANAGEMENT_PR_OWNER_SEPARATOR = "\n\n■ オーナー"
_MANAGEMENT_OWNER_HISTORY_SEPARATOR = "\n\n■ 実行履歴 / 直近アクション\n"

# Management dashboard Text widget base: bg #222834, fg #d6dbe3 — keep highlights subtle.
_MGMT_DASH_CAP_BG = "#2a3346"
_MGMT_DASH_CAP_FG = "#e2e8f2"
_MGMT_DASH_WARN_BG = "#383226"
_MGMT_DASH_WARN_FG = "#ebe2cf"
_MGMT_DASH_RESULT_BG = "#2c3038"
_MGMT_DASH_RESULT_FG = "#e4e8ef"
_MGMT_DASH_INVEST_BG = "#2a3634"
_MGMT_DASH_INVEST_FG = "#dfe8e4"


def _management_finance_dashboard_line_looks_warny(s: str) -> bool:
    """Prefix + substring heuristics on existing dashboard copy (no new semantics)."""
    if s.startswith("財務圧力:"):
        return any(k in s for k in ("赤字傾向", "注意", "圧迫"))
    if s.startswith("年俸枠メモ:"):
        return any(k in s for k in ("圧迫", "注意"))
    if s.startswith("行動判断:"):
        return any(k in s for k in ("未達リスク", "急ぎたい", "温存"))
    return False


def _management_finance_dashboard_row_tags(line: str) -> Tuple[str, ...]:
    """Tk Text tags per finance row; reserved for future styling (colors, binds)."""
    s = str(line)
    if s.startswith("キャップ余白:"):
        return ("finance_row_cap",)
    if _management_finance_dashboard_line_looks_warny(s):
        return ("finance_row_warning",)
    return ("finance_row_default",)


def _management_facility_dashboard_row_tags(line: str) -> Tuple[str, ...]:
    """Prefix-based tags for 施設 block lines (snapshot copy unchanged)."""
    s = str(line)
    if s.startswith("状態:"):
        return ("facility_row_state",)
    if s.startswith("レベル概要:") or s.startswith("レベル:"):
        return ("facility_row_levels",)
    if "次の投資コスト" in s:
        return ("facility_row_invest",)
    if s.startswith("建設中:"):
        return ("facility_row_build",)
    if s.startswith("補足:"):
        return ("facility_row_note",)
    if s.startswith("市場規模:") or s.startswith("市場・ファン:"):
        return ("facility_row_market",)
    return ("facility_row_default",)


def _management_pr_dashboard_row_tags(line: str) -> Tuple[str, ...]:
    """Prefix / substring tags for 広報 block lines (dashboard copy unchanged)."""
    s = str(line)
    if s.startswith("■ 広報:") or s.startswith("広報（今ラウンド）:"):
        return ("pr_row_status",)
    if "実行不可" in s:
        return ("pr_row_warning",)
    if "残り" in s:
        return ("pr_row_warning",)
    if "比較" in s or "候補" in s:
        return ("pr_row_candidates",)
    return ("pr_row_default",)


def _management_owner_line_warn_body(s: str) -> bool:
    """Value-side hints (exclude `危険度の目安:` label matching `危険` alone)."""
    _pfx, _sep, val = s.partition(":")
    body = val if val else s
    return any(k in body for k in ("危険", "未達", "要注意", "厳しい"))


def _management_owner_dashboard_row_tags(line: str) -> Tuple[str, ...]:
    """Prefix-based tags for オーナー block lines; optional second tag for hot bodies."""
    s = str(line)
    if s.startswith("【ミッション現況】"):
        base: Tuple[str, ...] = ("owner_row_header",)
    elif s.startswith("現在ミッション:"):
        base = ("owner_row_mission",)
    elif s.startswith("達成状況:") or s.startswith("達成率:"):
        base = ("owner_row_progress",)
    elif s.startswith("残り期限:"):
        base = ("owner_row_deadline",)
    elif s.startswith("危険度の目安:"):
        base = ("owner_row_danger",)
    else:
        base = ("owner_row_default",)
    if _management_owner_line_warn_body(s):
        return base + ("owner_row_warning",)
    return base


def _management_history_dashboard_row_tags(line: str) -> Tuple[str, ...]:
    """Prefix-based tags for 実行履歴 / 直近アクション body lines."""
    s = str(line)
    if s.startswith("前回施策:"):
        return ("history_row_action",)
    if s.startswith("結果:"):
        return ("history_row_result",)
    if s.startswith("実行タイミング:"):
        return ("history_row_timing",)
    return ("history_row_default",)
from basketball_sim.systems.competition_display import competition_display_name
from basketball_sim.systems import japan_regulation_display as jp_reg_display
from basketball_sim.systems.schedule_display import (
    build_division_playoff_main_next_lines,
    build_emperor_cup_main_next_lines,
    count_user_games_in_sim_round,
    detail_text_for_upcoming_row,
    division_playoff_pending_note_lines,
    division_playoff_results_prominent_lines,
    emperor_cup_log_digest_lines,
    main_top_bar_progress_label,
    schedule_month_week_label,
    next_advance_display_hints,
    format_season_event_matchup_line,
    information_panel_schedule_lines,
    next_round_schedule_lines,
    past_league_and_emperor_result_rows,
    upcoming_rows_for_user_team,
    user_team_division_playoff_projection_lines,
    user_team_division_playoff_result_parts,
)
from basketball_sim.systems.information_display import (
    build_information_news_lines,
    build_player_leaderboard_rows,
    build_standings_rows,
    build_team_summary_rows,
    format_awards_lines_for_division,
    player_stat_options,
)
from basketball_sim.systems.history_display import (
    build_culture_lines,
    build_episode_lines,
    build_journey_lines,
    fetch_legend_table_rows,
    fetch_timeline_rows,
    legend_view_options,
    timeline_selection_detail_lines,
)
from basketball_sim.utils.user_settings import (
    KEY_ACTION_CLOSE_SUBWINDOW,
    apply_tk_window_settings,
    load_user_settings,
    normalize_user_settings,
    tk_binding_for,
)
from basketball_sim.utils.game_logging import install_tk_callback_excepthook


MenuCallback = Callable[[], None]
AdvanceCallback = Callable[["MainMenuView"], None]
SystemMenuCallback = Callable[["MainMenuView"], None]


class MainMenuView:
    """Phase 4 minimal main menu / dashboard view."""

    # 左メニュー表示名: 閲覧・各メニューへの案内・CLI ショートカット（編集の正本は人事・戦術・経営・情報）
    CLUB_GUIDE_MENU_LABEL = "クラブ案内"

    MENU_ITEMS = [
        "日程",
        "人事",
        CLUB_GUIDE_MENU_LABEL,
        "経営",
        "強化",
        "戦術",
        "情報",
        "歴史",
        "システム",
    ]

    # ホーム「やること」0件時の1行（算出・表示のみ。セーブ対象外）
    HOME_TASKS_EMPTY_LINE = (
        "（ホーム上の「やること」はありません。各メニューから随時確認できます）"
    )

    _LINEUP_SLOT_LABELS = ("PG枠", "SG枠", "SF枠", "PF枠", "C枠")

    STRATEGY_LABELS = {
        "balanced": "バランス",
        "run_and_gun": "ラン＆ガン",
        "three_point": "3P重視",
        "defense": "守備重視",
        "inside": "インサイド重視",
    }

    COACH_STYLE_LABELS = {
        "balanced": "バランス",
        "offense": "オフェンス型",
        "defense": "ディフェンス型",
        "development": "育成型",
    }

    # 強化メニュー本表の「個別練習」列（短縮）。個別練習変更ウィンドのツリー略称と揃える。
    _DEV_ROSTER_DRILL_LABEL_JA: Dict[str, str] = {
        "balanced": "バランス",
        "dribble": "ドリブル",
        "rebound": "リバ",
        "stamina_run": "走り込み",
        "shoot_form": "シュート",
        "three_point": "3P",
        "free_throw": "FT",
        "drive_finish": "ドライブ",
        "passing_read": "パス",
        "defense_footwork": "守備Fw",
        "strength": "筋力",
        "speed_agility": "俊敏",
        "iq_film": "IQ映像",
    }
    # 強化メニュー本表の「育成方針」列（選手個人・個別練習に連動する方針）。C-3 の個別練習編集と揃える。
    _DEV_ROSTER_FOCUS_LABEL_JA: Dict[str, str] = {
        "balanced": "バランス",
        "shooting": "シュート",
        "playmaking": "プレメイク",
        "defense": "守備",
        "physical": "フィジカル",
        "iq_handling": "IQ・判断",
    }

    USAGE_POLICY_LABELS = {
        "balanced": "バランス",
        "win_now": "勝利優先",
        "development": "育成優先",
    }

    def __init__(
        self,
        team: Any = None,
        season: Any = None,
        root: Optional[tk.Tk] = None,
        on_advance: Optional[AdvanceCallback] = None,
        menu_callbacks: Optional[Dict[str, MenuCallback]] = None,
        news_items: Optional[List[str]] = None,
        tasks: Optional[List[str]] = None,
        title: str = "国内バスケGM - 主画面",
        user_settings: Optional[Dict[str, Any]] = None,
        on_system_menu: Optional[SystemMenuCallback] = None,
        on_main_window_close: Optional[Callable[[], bool]] = None,
        advance_primary_ui_fn: Optional[Callable[[], Tuple[str, str]]] = None,
    ) -> None:
        self.team = team
        self.season = season
        self.on_advance = on_advance
        self.menu_callbacks = menu_callbacks or {}
        self.on_system_menu = on_system_menu
        self.on_main_window_close = on_main_window_close
        self.advance_primary_ui_fn = advance_primary_ui_fn
        self.external_news_items = news_items
        self.external_tasks = tasks
        self._roster_item_to_player: Dict[str, Any] = {}
        self._injury_autorepair_task_supplement: str = ""

        self.root = root or tk.Tk()
        install_tk_callback_excepthook(self.root)
        self.root.title(title)
        cfg = user_settings if user_settings is not None else load_user_settings()
        self.user_settings = deepcopy(normalize_user_settings(cfg))
        apply_tk_window_settings(self.root, self.user_settings)
        self.root.configure(bg="#15171c")

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._configure_styles()
        self._build_ui()
        self.refresh()
        self._close_subwindow_bind_seq = tk_binding_for(
            self.user_settings, KEY_ACTION_CLOSE_SUBWINDOW, "<Escape>"
        )
        self.root.bind(self._close_subwindow_bind_seq, self._on_close_subwindow_hotkey)
        if self.on_main_window_close is not None:
            self.root.protocol("WM_DELETE_WINDOW", self._on_user_request_close_root)

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------
    def _configure_styles(self) -> None:
        self.style.configure("Root.TFrame", background="#15171c")
        self.style.configure("Panel.TFrame", background="#1d2129")
        self.style.configure("Card.TFrame", background="#222834")
        self.style.configure(
            "SectionTitle.TLabel",
            background="#1d2129",
            foreground="#f3f5f7",
            font=("Yu Gothic UI", 16, "bold"),
        )
        self.style.configure(
            "TopBar.TLabel",
            background="#0f1116",
            foreground="#f4f7fb",
            font=("Yu Gothic UI", 11, "bold"),
        )
        self.style.configure(
            "Menu.TButton",
            font=("Yu Gothic UI", 11, "bold"),
            padding=(12, 10),
        )
        # 主画面右下デバッグ用（長文が右ペイン幅で切れないよう Menu よりやや詰める）
        self.style.configure(
            "DebugSkip.TButton",
            font=("Yu Gothic UI", 10, "bold"),
            padding=(10, 9),
        )
        self.style.configure(
            "Primary.TButton",
            font=("Yu Gothic UI", 12, "bold"),
            padding=(18, 12),
            foreground="#f8fafc",
            background="#2f4f9e",
        )
        self.style.map(
            "Primary.TButton",
            foreground=[("disabled", "#8892a0"), ("pressed", "#f8fafc"), ("active", "#f8fafc")],
            background=[("disabled", "#3a4150"), ("pressed", "#243a78"), ("active", "#3a5fc4")],
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        self.top_bar = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        self.top_bar.pack(fill="x", pady=(0, 6))

        self.season_status_var = tk.StringVar(value="")
        season_strip = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 6))
        season_strip.pack(fill="x", pady=(0, 12))
        ttk.Label(
            season_strip,
            textvariable=self.season_status_var,
            background="#1d2129",
            foreground="#a8b8d0",
            font=("Yu Gothic UI", 10),
            anchor="w",
        ).pack(fill="x")

        body = ttk.Frame(outer, style="Root.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Left menu
        left_panel = ttk.Frame(body, style="Panel.TFrame", padding=12)
        left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left_panel.configure(width=210)
        left_panel.grid_propagate(False)

        ttk.Label(left_panel, text="メニュー", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(0, 10)
        )

        self._menu_buttons: Dict[str, ttk.Button] = {}
        for label in self.MENU_ITEMS:
            btn = ttk.Button(
                left_panel,
                text=label,
                style="Menu.TButton",
                command=lambda key=label: self._on_menu(key),
            )
            btn.pack(fill="x", pady=5)
            self._menu_buttons[label] = btn

        # 補助: 閲覧専用窓・デバッグ補助の置き場（既存 MENU_ITEMS は変更せず別枠で追加する）
        ttk.Label(left_panel, text="補助", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(18, 6)
        )

        aux_buttons_frame = ttk.Frame(left_panel, style="Root.TFrame")
        aux_buttons_frame.pack(fill="x", pady=(0, 2))
        aux_buttons_frame.columnconfigure(0, weight=1)
        aux_buttons_frame.columnconfigure(1, weight=1)
        _aux_pad = {"padx": 3, "pady": 3}

        self.offseason_flow_overview_button = ttk.Button(
            aux_buttons_frame,
            text="オフの流れ",
            style="Menu.TButton",
            command=self._open_offseason_flow_overview_window,
        )
        self.offseason_flow_overview_button.grid(
            row=0, column=0, sticky="ew", **_aux_pad
        )

        self.future_draft_pool_overview_button = ttk.Button(
            aux_buttons_frame,
            text="来年候補",
            style="Menu.TButton",
            command=self._open_future_draft_pool_overview_window,
        )
        self.future_draft_pool_overview_button.grid(
            row=0, column=1, sticky="ew", **_aux_pad
        )

        self.fa_market_overview_button = ttk.Button(
            aux_buttons_frame,
            text="FA市場",
            style="Menu.TButton",
            command=self._open_fa_market_overview_window,
        )
        self.fa_market_overview_button.grid(
            row=1, column=0, sticky="ew", **_aux_pad
        )

        self.offseason_result_recap_button = ttk.Button(
            aux_buttons_frame,
            text="直近オフ",
            style="Menu.TButton",
            command=self._open_offseason_result_recap_window,
        )
        self.offseason_result_recap_button.grid(
            row=1, column=1, sticky="ew", **_aux_pad
        )

        debug_skip_cb = self.menu_callbacks.get("DEBUG_SKIP_TO_OFFSEASON")
        self.debug_skip_button: Optional[ttk.Button] = None
        if callable(debug_skip_cb):
            self.debug_skip_button = ttk.Button(
                aux_buttons_frame,
                text="デバッグ: オフシーズンまで飛ばす",
                style="DebugSkip.TButton",
                command=debug_skip_cb,
            )
            self.debug_skip_button.grid(
                row=2, column=0, columnspan=2, sticky="ew", **_aux_pad
            )

        # Center / right: 行高は各列フレーム内で独立。横は Panedwindow＋初期サッシュで
        # 「次の試合・クラブ状況」を広く、「今やること・ニュース・次へ」を狭く固定（weight だけだと
        # ScrolledText 既定幅などで列の最小幅が釣り合い、半々に見えやすい）。
        content = ttk.Frame(body, style="Root.TFrame")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        self._home_center_right_paned = ttk.Panedwindow(content, orient=tk.HORIZONTAL)
        self._home_center_right_paned.grid(row=0, column=0, sticky="nsew")

        center_col = ttk.Frame(self._home_center_right_paned, style="Root.TFrame", padding=(0, 0, 12, 0))
        center_col.columnconfigure(0, weight=1)
        center_col.rowconfigure(0, weight=4, uniform="home_center")
        center_col.rowconfigure(1, weight=6, uniform="home_center")

        right_col = ttk.Frame(self._home_center_right_paned, style="Root.TFrame")
        right_col.columnconfigure(0, weight=1)
        right_col.rowconfigure(0, weight=4, uniform="home_right")
        right_col.rowconfigure(1, weight=4, uniform="home_right")
        right_col.rowconfigure(2, weight=2, uniform="home_right")

        self._home_center_right_paned.add(center_col, weight=5)
        self._home_center_right_paned.add(right_col, weight=3)

        self._home_cr_split_done = False

        def _apply_home_center_right_split(_event: Any = None) -> None:
            if self._home_cr_split_done:
                return
            pw = getattr(self, "_home_center_right_paned", None)
            if pw is None:
                return
            try:
                total = int(pw.winfo_width())
                # 初期レイアウト前の小さい幅で確定しない（Configure 連打は使わない）
                if total < 520:
                    return
                # 左メニュー外のこのペイン内で、中央:右 ≒ 5:3（中央 62.5%）
                pw.sashpos(0, max(240, int(total * 5 / 8)))
                self._home_cr_split_done = True
            except tk.TclError:
                pass

        self._home_center_right_paned.bind("<Map>", _apply_home_center_right_split)
        self.root.after_idle(_apply_home_center_right_split)
        self.root.after(200, _apply_home_center_right_split)

        self.next_game_panel = self._create_panel(center_col, "次の試合")
        self.next_game_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self.club_summary_panel = self._create_panel(center_col, "クラブ状況サマリー")
        self.club_summary_panel.grid(row=1, column=0, sticky="nsew")

        ng_inner = self._resolve_content_parent(self.next_game_panel)
        ng_inner.columnconfigure(0, weight=1)
        ng_inner.rowconfigure(0, weight=1)
        _, self._next_game_scroll_inner = self._home_embed_vertical_scroll(
            ng_inner, grid_row=0, bg="#222834"
        )

        cs_inner = self._resolve_content_parent(self.club_summary_panel)
        cs_inner.columnconfigure(0, weight=1)
        cs_inner.rowconfigure(0, weight=1)
        _, self._club_scroll_inner = self._home_embed_vertical_scroll(
            cs_inner, grid_row=0, bg="#222834"
        )

        self.tasks_panel = self._create_panel(right_col, "今やること")
        self.tasks_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        tasks_content = self._resolve_content_parent(self.tasks_panel)
        tasks_content.columnconfigure(0, weight=1)
        tasks_content.rowconfigure(0, weight=0)
        tasks_content.rowconfigure(1, weight=1)
        self.tasks_summary_var = tk.StringVar(value="")
        tk.Label(
            tasks_content,
            textvariable=self.tasks_summary_var,
            bg="#222834",
            fg="#a8b4c8",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=360,
            padx=2,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        _, self._tasks_scroll_inner = self._home_embed_vertical_scroll(
            tasks_content, grid_row=1, bg="#222834"
        )

        self.news_panel = self._create_panel(right_col, "ニュース")
        self.news_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        news_content = self._resolve_content_parent(self.news_panel)
        news_content.columnconfigure(0, weight=1)
        news_content.rowconfigure(0, weight=1)
        self.news_text = scrolledtext.ScrolledText(
            news_content,
            height=4,
            width=36,
            wrap="word",
            bg="#222834",
            fg="#eef3f8",
            insertbackground="#eef3f8",
            font=("Yu Gothic UI", 11),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self.news_text.grid(row=0, column=0, sticky="nsew")
        self.news_text.configure(state="disabled")

        advance_wrap = ttk.Frame(right_col, style="Panel.TFrame", padding=(12, 10))
        advance_wrap.grid(row=2, column=0, sticky="nsew")
        # 右ペインが極端に狭いと ttk ボタン文言が切れるため、進行ブロックの最小幅だけ確保
        advance_wrap.columnconfigure(0, weight=1, minsize=288)
        advance_wrap.rowconfigure(0, weight=0)
        advance_wrap.rowconfigure(1, weight=1)
        advance_wrap.rowconfigure(2, weight=0)
        advance_wrap.rowconfigure(3, weight=0)

        tk.Label(
            advance_wrap,
            text="シーズン進行は下のボタン、人事・経営・戦術・情報などの確認は左メニューから。",
            bg="#1d2129",
            fg="#a8b4c8",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=320,
            padx=2,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self._advance_hint_text = scrolledtext.ScrolledText(
            advance_wrap,
            height=3,
            width=36,
            wrap="word",
            bg="#1d2129",
            fg="#ffd38a",
            insertbackground="#ffd38a",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=4,
        )
        self._advance_hint_text.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self._advance_hint_text.configure(state="disabled")

        self.advance_button = ttk.Button(
            advance_wrap,
            text="次へ進む",
            style="Primary.TButton",
            command=self._on_advance,
        )
        self.advance_button.grid(row=2, column=0, sticky="ew")

        # Holders updated by refresh()
        self.top_bar_var = tk.StringVar(value="読み込み中...")
        ttk.Label(
            self.top_bar,
            textvariable=self.top_bar_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        self.next_game_lines = self._make_line_vars(
            self.next_game_panel, 6, content_parent=self._next_game_scroll_inner
        )
        self.club_summary_lines = self._make_line_vars(
            self.club_summary_panel, 6, content_parent=self._club_scroll_inner
        )
        self.task_lines = self._make_bullet_vars(
            self.tasks_panel, 3, prefix="• ", content_parent=self._tasks_scroll_inner
        )
        self._task_injury_detail_button = ttk.Button(
            self._tasks_scroll_inner,
            text="負傷者の詳細・行動ガイド",
            style="Menu.TButton",
            command=self._on_home_injury_detail_click,
        )

    def _create_panel(self, parent: tk.Misc, title: str) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        header = ttk.Label(panel, text=title, style="SectionTitle.TLabel")
        header.grid(row=0, column=0, sticky="w", pady=(0, 10))

        inner = ttk.Frame(panel, style="Card.TFrame", padding=14)
        inner.grid(row=1, column=0, sticky="nsew")

        setattr(panel, "content_frame", inner)
        return panel

    def _resolve_content_parent(self, panel: ttk.Frame) -> tk.Misc:
        return getattr(panel, "content_frame", panel)

    def _home_embed_vertical_scroll(
        self,
        parent: tk.Misc,
        *,
        grid_row: int,
        bg: str = "#222834",
    ) -> Tuple[tk.Canvas, tk.Frame]:
        """ホーム各パネル用: 親の grid_row に Canvas＋縦スクロールを置き、内側 Frame を返す。"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(grid_row, weight=1)
        canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        inner = tk.Frame(canvas, bg=bg)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event: Any = None) -> None:
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(event: Any) -> None:
            try:
                canvas.itemconfigure(win_id, width=event.width)
            except tk.TclError:
                pass

        canvas.bind("<Configure>", _on_canvas_configure)

        def _wheel(event: Any) -> str:
            if getattr(event, "delta", 0):
                canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        canvas.bind("<MouseWheel>", _wheel)
        inner.bind("<MouseWheel>", _wheel)
        canvas.bind("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))
        inner.bind("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        inner.bind("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

        canvas.grid(row=grid_row, column=0, sticky="nsew")
        vsb.grid(row=grid_row, column=1, sticky="ns")
        return canvas, inner

    @staticmethod
    def _shorten_home_advance_hint(text: str, max_len: int = 220) -> str:
        s = str(text or "").strip()
        if len(s) <= max_len:
            return s
        return s[: max(1, max_len - 1)] + "…"

    def _set_home_advance_hint(self, text: str) -> None:
        tw = getattr(self, "_advance_hint_text", None)
        if tw is None:
            return
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", self._shorten_home_advance_hint(text))
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _jpn_text_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Any,
        *,
        primary: bool = False,
        side: str = "right",
        padx: int = 0,
        pady: int = 0,
    ) -> tk.Button:
        """ttk が環境によって日本語ラベルを欠落させる場合のフォールバック用 tk.Button。"""
        bg = "#2f4f9e" if primary else "#3a4558"
        fg = "#f4f7fb"
        active_bg = "#3a5fc4" if primary else "#4a5568"
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Yu Gothic UI", 10, "bold" if primary else "normal"),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
        )
        btn.pack(side=side, padx=padx, pady=pady)
        return btn

    def _make_line_vars(
        self,
        panel: ttk.Frame,
        count: int,
        *,
        content_parent: Optional[tk.Misc] = None,
    ) -> List[tk.StringVar]:
        content_parent = content_parent or self._resolve_content_parent(panel)
        vars_: List[tk.StringVar] = []
        for i in range(count):
            var = tk.StringVar(value="")
            label = tk.Label(
                content_parent,
                textvariable=var,
                bg="#222834",
                fg="#eef3f8" if i == 0 else "#d6dbe3",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 13 if i == 1 else 11, "bold" if i in (0, 1) else "normal"),
                wraplength=560,
                padx=2,
                pady=4,
            )
            label.pack(fill="x", anchor="w")
            vars_.append(var)
        return vars_

    def _make_bullet_vars(
        self,
        panel: ttk.Frame,
        count: int,
        prefix: str,
        *,
        content_parent: Optional[tk.Misc] = None,
    ) -> List[tk.StringVar]:
        content_parent = content_parent or self._resolve_content_parent(panel)
        vars_: List[tk.StringVar] = []
        for _ in range(count):
            var = tk.StringVar(value="")
            label = tk.Label(
                content_parent,
                textvariable=var,
                bg="#222834",
                fg="#eef3f8",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 11),
                wraplength=360,
                padx=2,
                pady=4,
            )
            label.pack(fill="x", anchor="w")
            vars_.append(var)
        self._bullet_prefix = prefix
        return vars_

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def apply_runtime_user_settings(self, settings: Dict[str, Any]) -> None:
        """settings.json 保存後など、幾何・フルスクリーン・サブウィンドウ閉じるキーを即時反映する。"""
        merged = normalize_user_settings(settings)
        try:
            self.root.unbind(self._close_subwindow_bind_seq)
        except tk.TclError:
            pass
        self.user_settings = deepcopy(merged)
        apply_tk_window_settings(self.root, self.user_settings)
        self._close_subwindow_bind_seq = tk_binding_for(
            self.user_settings, KEY_ACTION_CLOSE_SUBWINDOW, "<Escape>"
        )
        self.root.bind(self._close_subwindow_bind_seq, self._on_close_subwindow_hotkey)

    def close_all_subwindows(self) -> None:
        """ロード等で世界を差し替える前に、開いている Toplevel をまとめて閉じる。"""
        for closer in (
            self._on_close_roster_window,
            self._on_close_finance_window,
            self._on_close_strategy_window,
            self._on_close_development_window,
            self._on_close_information_window,
            self._on_close_schedule_window,
            self._close_history_window,
            self._on_close_gm_window,
        ):
            try:
                closer()
            except Exception:
                pass
        sysw = getattr(self, "_system_menu_window", None)
        if sysw is not None:
            try:
                if sysw.winfo_exists():
                    sysw.destroy()
            except Exception:
                pass
            self._system_menu_window = None

    def refresh(self) -> None:
        self._injury_autorepair_task_supplement = ""
        if self.team is not None:
            note = getattr(self.team, "_injury_autorepair_notice_jp", None)
            if isinstance(note, str) and note.strip():
                self._injury_autorepair_task_supplement = note.strip()
                try:
                    delattr(self.team, "_injury_autorepair_notice_jp")
                except Exception:
                    pass
        self._refresh_top_bar()
        self._refresh_season_status()
        self._refresh_next_game()
        self._refresh_club_summary()
        self._refresh_tasks()
        self._refresh_menu_injury_badges()
        self._refresh_news()
        try:
            if getattr(self, "_roster_window", None) is not None and self._roster_window.winfo_exists():
                self._refresh_roster_window()
        except Exception:
            pass
        try:
            if getattr(self, "_finance_window", None) is not None and self._finance_window.winfo_exists():
                self._refresh_finance_window()
        except Exception:
            pass
        try:
            if getattr(self, "_strategy_window", None) is not None and self._strategy_window.winfo_exists():
                self._refresh_strategy_window()
        except Exception:
            pass
        try:
            if getattr(self, "_development_window", None) is not None and self._development_window.winfo_exists():
                self._refresh_development_window()
        except Exception:
            pass
        try:
            if getattr(self, "_information_window", None) is not None and self._information_window.winfo_exists():
                self._refresh_information_window()
        except Exception:
            pass
        try:
            if getattr(self, "_history_window", None) is not None and self._history_window.winfo_exists():
                self._refresh_history_window()
        except Exception:
            pass
        try:
            if getattr(self, "_gm_window", None) is not None and self._gm_window.winfo_exists():
                self._refresh_gm_dashboard_window()
        except Exception:
            pass
        try:
            if getattr(self, "_schedule_window", None) is not None and self._schedule_window.winfo_exists():
                self._refresh_schedule_window()
        except Exception:
            pass
        self._refresh_advance_button()

    def _on_user_request_close_root(self) -> None:
        if self.on_main_window_close is not None:
            try:
                if not self.on_main_window_close():
                    return
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        self._schedule_steam_callback_pump()
        self.root.mainloop()

    def _schedule_steam_callback_pump(self) -> None:
        """ネイティブ Steam 接続時のみ RunCallbacks を定期実行する。"""
        try:
            from basketball_sim.integrations.steamworks_bridge import (
                pump_steam_callbacks,
                steam_native_loaded,
            )

            if not steam_native_loaded():
                return
            pump_steam_callbacks()
        except Exception:
            pass
        try:
            self.root.after(100, self._schedule_steam_callback_pump)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # In-season trade / FA (same guard as CLI: season_transaction_rules)
    # ------------------------------------------------------------------
    def inseason_roster_moves_allowed(self) -> bool:
        """
        CLI の inseason_roster_moves_unlocked(season) と同じ可否。
        シーズン未接続・レギュラー終了後は期限ロックの対象外（True）。
        """
        if self.season is None:
            return True
        if bool(self._safe_get(self.season, "season_finished", False)):
            return True
        try:
            return inseason_roster_moves_unlocked(self.season)
        except Exception:
            return True

    def ensure_inseason_roster_moves_allowed(self, parent: Optional[Any] = None) -> bool:
        """
        トレード／インシーズンFA に相当する操作の直前に呼ぶ。
        不可なら CLI と同じロック文言を表示し False。
        """
        if self.inseason_roster_moves_allowed():
            return True
        p = parent if parent is not None else self.root
        try:
            messagebox.showwarning(
                "トレード・インシーズンFAは不可",
                "期限ルールにより、現在は実行できません。\n"
                "（オフシーズンは別処理で進行します）\n\n"
                + INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
                parent=p,
            )
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------
    def _game_progress_summary(self) -> str:
        if self.season is None:
            return "—"
        sn = int(self._safe_get(self.season, "season_no", 1) or 1)
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        fin = bool(self._safe_get(self.season, "season_finished", False))
        return main_top_bar_progress_label(
            self.season,
            season_year=sn,
            current_round=cr,
            total_rounds=tr,
            season_finished=fin,
        )

    @staticmethod
    def _is_home_tasks_empty_line(line: str) -> bool:
        s = str(line)
        return s.startswith("（要確認の項目はありません") or s.startswith(
            "（ホーム上の「やること」はありません"
        )

    def _home_task_urgent_normal_counts(self, lines: List[str]) -> Optional[Tuple[int, int]]:
        if not lines:
            return None
        if len(lines) == 1 and self._is_home_tasks_empty_line(lines[0]):
            return None
        urgent = sum(1 for x in lines if str(x).startswith("[優先]"))
        normal = len(lines) - urgent
        return (urgent, normal)

    @staticmethod
    def _format_task_line_for_display(line: str) -> str:
        s = str(line)
        if s.startswith("[優先] "):
            return "【急ぎ】" + s[5:]
        if s.startswith("[任意] "):
            return "【あとで】" + s[5:]
        return s

    def _task_status_short(self) -> str:
        lines = self._get_task_lines()
        counts = self._home_task_urgent_normal_counts(lines)
        if counts is None:
            return "なし"
        urgent, normal = counts
        total = urgent + normal
        if urgent and normal:
            return f"急ぎ{urgent}・あとで{normal}（計{total}）"
        if urgent:
            return f"急ぎ{urgent}（計{total}）"
        return f"あとで{normal}（計{total}）"

    def _refresh_top_bar(self) -> None:
        progress = self._game_progress_summary()
        league_level = self._safe_get(self.team, "league_level", "-")
        rank = self._compute_rank_text()
        wins = self._safe_get(self.team, "regular_wins", 0)
        losses = self._safe_get(self.team, "regular_losses", 0)
        money = self._safe_get(self.team, "money", 0)
        owner_trust = self._get_owner_trust_text()
        task_short = self._task_status_short()

        text = (
            f"進行: {progress}    "
            f"リーグ: D{league_level}    "
            f"順位: {rank}    "
            f"戦績: {wins}勝{losses}敗    "
            f"資金: {self._format_money(money)}    "
            f"オーナー信頼: {owner_trust}    "
            f"やること: {task_short}"
        )
        self.top_bar_var.set(text)

    def _refresh_season_status(self) -> None:
        """消化ラウンドとレギュラー中トレード／インシーズンFA可否を表示。"""
        if not hasattr(self, "season_status_var"):
            return
        if self.season is None:
            self.season_status_var.set(
                "シーズン: —  |  トレード／インシーズンFA: （シーズン未接続）"
            )
            return
        if bool(self._safe_get(self.season, "season_finished", False)):
            lbl = None
            if self.advance_primary_ui_fn is not None:
                try:
                    lbl, _ = self.advance_primary_ui_fn()
                except Exception:
                    lbl = None
            if lbl == "次のシーズンへ…":
                self.season_status_var.set(
                    "進行: オフ完了・次年度開始待ち（年度進行ゲート）  |  "
                    "シーズン: 終了  |  トレード／インシーズンFA: オフシーズン（制限なし）"
                )
                return
            if lbl == "オフシーズンを実行":
                self.season_status_var.set(
                    "進行: シーズン終了（オフ未実行）  |  "
                    "シーズン: 終了  |  トレード／インシーズンFA: オフシーズン（『オフシーズンを実行』で進める）"
                )
                return
            self.season_status_var.set(
                "シーズン: 終了  |  トレード／インシーズンFA: オフシーズン（『次へ進む』でオフ処理）"
            )
            return
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        unlocked = self.inseason_roster_moves_allowed()
        tx = "可（ラウンド22消化後まで）" if unlocked else "期限切れ（シーズン終了まで不可）"
        phase = ""
        if self.advance_primary_ui_fn is not None:
            try:
                plbl, _ = self.advance_primary_ui_fn()
                if plbl == "次へ進む":
                    phase = "進行: レギュラー中  |  "
            except Exception:
                pass
        self.season_status_var.set(
            f"{phase}消化ラウンド: {cr}/{tr}  |  トレード／インシーズンFA: {tx}"
        )

    def _roster_transaction_status_text(self) -> str:
        """情報画面用の短い文言。"""
        if self.season is None:
            return "—"
        if bool(self._safe_get(self.season, "season_finished", False)):
            return "オフシーズン（制限なし）"
        if self.inseason_roster_moves_allowed():
            return "可（ラウンド22消化後まで）"
        return "期限切れ（シーズン終了まで不可）"

    def _format_hr_trade_fa_guidance_text(self) -> str:
        """人事ウィンドウ用: トレード／インシーズンFA 可否の案内（ロックは main.py トレードと同一ルール）。"""
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        fin = self.season is not None and bool(self._safe_get(self.season, "season_finished", False))
        if self.season is None:
            sched = "消化ラウンド: —（シーズン未接続）\n"
            lock_line = "シーズンに接続すると、レギュラー中のトレード／インシーズンFA の期限表示が更新されます。"
        elif fin:
            sched = f"消化ラウンド: {cr}/{tr}（シーズン終了・オフシーズン）\n"
            lock_line = (
                "現在はオフシーズンです。トレード・FA はオフシーズン処理（再契約・FA・ドラフト等）を"
                "メインの進行から進めてください。"
            )
        else:
            sched = f"消化ラウンド: {cr}/{tr}\n"
            if self.inseason_roster_moves_allowed():
                lock_line = (
                    "レギュラー中のトレード／インシーズンFA は「ラウンド22消化後」まで可能です"
                    "（3月第2週終了相当）。"
                )
            else:
                lock_line = INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA
        tx = self._roster_transaction_status_text()
        return (
            "【当面の運用】\n"
            "・トレードは本ウィンドウの「トレード」から（1〜3名の入替、現金・RB は双方向。1対1相当は人数を1対1にすれば同じウィザードで可）。"
            "インシーズンの可否は CLI のトレードと同一ルールです。\n"
            "・同じトレードはシーズンメニュー「8. GMメニュー」→「10. トレード」（CLI）からも実行できます。\n"
            "・FA プールからの手動契約は、人事の「インシーズンFA（1人）」で 1 名まで（交渉・金額入力なし）。"
            "レギュラー中の CPU 補強はシーズン進行に連動した自動処理が中心です。\n"
            "・人事画面は「閲覧・一部操作（契約＋1年、契約解除）」と、上記・CLI の案内を担当します。\n"
            "・再契約の確認は、オフシーズン処理の実行中にダイアログで表示されます（GUIモード）。\n\n"
            "【現在の条件】\n"
            f"{sched}"
            f"{lock_line}\n"
            f"レギュラー中のトレード／インシーズンFA（可否の要約）: {tx}\n\n"
            "【このウィンドウ（GUI）でできること】\n"
            "・ロスター表での閲覧、契約の＋1年延長（条件あり）、契約解除による FA 送り（インシーズンは"
            "トレード／インシーズンFA と同じ期限でロック）。\n\n"
            "【まだターミナル（CLI）で行うこと】\n"
            "・トレードは CLI（シーズンメニュー「8. GMメニュー」→「10. トレード」）でも実行できます。\n"
            "・レギュラー中のトレード期限切れ後は、CLI のトレードもブロックされます（上部の可否表示と同じルール）。\n\n"
            "【その他】施設投資などもターミナルの「8. GMメニュー」から行います。"
        )

    def _build_roster_trade_fa_guidance_summary_text(self) -> str:
        """人事本体のトレード／FA帯用の短い要約（全文は別窓の _format_hr_trade_fa_guidance_text）。"""
        tx = self._roster_transaction_status_text()
        return (
            "トレード／インシーズンFA／契約解除／＋1年延長ができます。重要な操作は確認のうえ反映されます。\n"
            f"トレード／インシーズンFA（可否の要約）: {tx}\n"
            "詳細な注意点・CLIとの役割分担は下の「トレード・FA案内を表示」から確認できます。"
        )

    def _count_display_nationality_raw(self, players: List[Any]) -> Tuple[int, int, int, int, int]:
        """表示用：Player.nationality の値（Japan/Foreign/Asia/Naturalized）で人数化。ロジックは変更しない。"""
        jp_n = fr_n = asia_n = nat_n = other_n = 0
        for p in players:
            raw = getattr(p, "nationality", None)
            s = str(raw).strip() if raw is not None else ""
            if s == "Japan":
                jp_n += 1
            elif s == "Foreign":
                fr_n += 1
            elif s == "Asia":
                asia_n += 1
            elif s == "Naturalized":
                nat_n += 1
            else:
                other_n += 1
        return jp_n, fr_n, asia_n, nat_n, other_n

    def _roster_situation_finance_stats(
        self, players: List[Any]
    ) -> Tuple[int, int, str, int, int, int]:
        """年俸・契約残年の単純集計。(合計, 平均, 最高年俸選手名, 最高年俸額, 残1年, 残2年以上)"""
        total = 0
        y1 = y2p = 0
        n = len(players)
        best_name = "—"
        best_sal = 0
        first_best: Any = None
        for p in players:
            try:
                total += int(self._safe_get(p, "salary", 0) or 0)
            except Exception:
                pass
            try:
                sal = int(self._safe_get(p, "salary", 0) or 0)
                if first_best is None or sal > best_sal:
                    best_sal = sal
                    first_best = p
            except Exception:
                pass
            try:
                cy = self._safe_get(p, "contract_years_left", None)
                if cy is None:
                    continue
                ci = int(cy)
                if ci == 1:
                    y1 += 1
                elif ci >= 2:
                    y2p += 1
            except Exception:
                pass
        if first_best is not None:
            best_name = str(self._safe_get(first_best, "name", "—"))
        avg = int(round(total / n)) if n > 0 else 0
        return total, avg, best_name, best_sal, y1, y2p

    def _build_roster_situation_block_text(
        self, team_name: str, count: int, players_sorted: List[Any], avg_ovr: float
    ) -> str:
        """人事ウィンドウ上部「ロスター状況」本文（箇条書き・単純集計のみ）。"""
        lines: List[str] = [f"・チーム：{team_name}"]
        if count <= 0:
            lines.append("・ロスター：0人")
            lines.append("・平均OVR：—")
            lines.append("・年俸合計：—　年俸平均：—　最高年俸：—")
            lines.append("・契約：残1年 0人　残2年以上 0人")
            return "\n".join(lines)
        jp_n, fr_n, asia_n, nat_n, oth = self._count_display_nationality_raw(players_sorted)
        l1 = (
            f"・ロスター：{count}人　日本人：{jp_n}人　外国籍：{fr_n}人　"
            f"アジア：{asia_n}人　帰化：{nat_n}人"
        )
        if oth > 0:
            l1 += f"　（国籍未設定等：{oth}人）"
        lines.append(l1)
        lines.append(f"・平均OVR：{avg_ovr:.0f}")
        tot, avg_m, bnm, bsal, y1, y2p = self._roster_situation_finance_stats(players_sorted)
        lines.append(
            f"・年俸合計：{self._format_money(tot)}　年俸平均：{self._format_money(avg_m)}　"
            f"最高年俸：{bnm} {self._format_money(bsal)}"
        )
        lines.append(f"・契約：残1年 {y1}人　残2年以上 {y2p}人")
        return "\n".join(lines)

    def _on_close_roster_trade_fa_guidance_detail_window(self) -> None:
        w = getattr(self, "_roster_trade_fa_guidance_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._roster_trade_fa_guidance_detail_window = None
            self._roster_trade_fa_guidance_detail_text = None

    def _refresh_roster_trade_fa_guidance_detail_body(self) -> None:
        tw = getattr(self, "_roster_trade_fa_guidance_detail_text", None)
        if tw is None:
            return
        body = self._format_hr_trade_fa_guidance_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_roster_trade_fa_guidance_detail_window(self) -> None:
        """トレード／インシーズンFA／契約解除の案内全文（閲覧専用）。本文は _format_hr_trade_fa_guidance_text に委譲。"""
        parent = getattr(self, "_roster_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_roster_trade_fa_guidance_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_roster_trade_fa_guidance_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("トレード・FA案内")
        w.geometry("720x520")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="トレード・FA案内", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            outer,
            text="トレード、インシーズンFA、契約解除に関する注意点です。（閲覧のみ・実行は人事画面の各ボタンから行います）",
            wraplength=680,
            font=("Yu Gothic UI", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=22,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=2, column=0, sticky="nsew")
        self._roster_trade_fa_guidance_detail_window = w
        self._roster_trade_fa_guidance_detail_text = tw
        self._refresh_roster_trade_fa_guidance_detail_body()
        tw.configure(state="disabled")

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_roster_trade_fa_guidance_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_roster_trade_fa_guidance_detail_window)

    def _on_close_roster_gm_text_list_detail_window(self) -> None:
        w = getattr(self, "_roster_gm_text_list_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._roster_gm_text_list_detail_window = None
            self._roster_gm_text_list_detail_text = None

    def _refresh_roster_gm_text_list_detail_body(self) -> None:
        tw = getattr(self, "_roster_gm_text_list_detail_text", None)
        if tw is None:
            return
        if self.team is not None:
            body = format_gm_roster_text(self.team)
        else:
            body = "チームが未接続です。"
        try:
            self._gm_set_readonly_text(tw, body)
        except tk.TclError:
            pass

    def _open_roster_gm_text_list_detail_window(self) -> None:
        """詳細ロスター全文（閲覧専用・別窓）。本文は format_gm_roster_text に委譲。"""
        parent = getattr(self, "_roster_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_roster_gm_text_list_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_roster_gm_text_list_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("詳細ロスター")
        w.geometry("760x560")
        w.minsize(520, 380)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="詳細ロスター", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            outer,
            text="表と同じメンバーを、GM表示ルールに沿ったテキスト一覧で確認できます。（閲覧専用）",
            wraplength=700,
            font=("Yu Gothic UI", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        text_host = ttk.Frame(outer, style="Panel.TFrame", padding=0)
        text_host.grid(row=2, column=0, sticky="nsew")
        text_host.rowconfigure(0, weight=1)
        text_host.columnconfigure(0, weight=1)
        tw = tk.Text(
            text_host,
            wrap="none",
            height=22,
            bg="#222834",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=8,
        )
        vsb = ttk.Scrollbar(text_host, orient="vertical", command=tw.yview)
        hsb = ttk.Scrollbar(text_host, orient="horizontal", command=tw.xview)
        tw.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tw.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._roster_gm_text_list_detail_window = w
        self._roster_gm_text_list_detail_text = tw
        self._refresh_roster_gm_text_list_detail_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_roster_gm_text_list_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_roster_gm_text_list_detail_window)

    def _format_roster_hr_rules_detail_body(self) -> str:
        """人事「編成ルールの詳細」窓：ルール説明が中心（数値は本体「ロスター状況」を参照）。"""
        if self.team is None:
            return "チームが未接続です。"
        team = self.team
        lines: List[str] = []
        lines.append("編成ルールの詳細（閲覧専用）")
        lines.append("")
        lines.append(
            "現在の契約・年俸の集計は、ウィンドウ上部の「ロスター状況」を参照してください。"
            "（この窓ではルールの考え方と大会別の参考情報をまとめます。）"
        )
        lines.append("")
        lines.append("■ 用語の整理（別々のルールです）")
        lines.append(
            "・「契約ロスター（本契約枠）」… チームに登録できる外国籍／アジア・帰化の人数上限です。"
            " 上部の人数（日本人／外国籍／アジア／帰化）は nationality の表示用集計です。"
        )
        lines.append(
            "・「試合登録」… その大会にエントリーできる人数上限です（契約ロスター枠とは別です）。"
        )
        lines.append(
            "・「オンザコート制限」… コート上に同時に置ける外国籍などの上限です（試合登録とも別です）。"
        )
        lines.append("")
        try:
            lines.append(jp_reg_display.format_contract_roster_summary(team))
        except Exception:
            pass
        lines.append("")
        lines.append("■ 直近の大会想定とレギュレーション（参考）")
        try:
            ct = jp_reg_display.gui_next_competition_type(self.season, team)
            nm = competition_display_name(ct)
            lines.append(f"直近の大会想定：{nm}")
            lines.append("")
            lines.append("【参考】試合登録・オンザコート上限（大会により異なります。契約ロスター枠とは別概念です）")
            lines.append(jp_reg_display.format_competition_rules_brief(ct))
        except Exception:
            lines.append("直近の大会想定を取得できませんでした。")
        lines.append("")
        lines.append(
            "※トレード／FA／解除／延長の実行やルール変更はこの窓では行えません。"
            " 運用上の注意は「トレード・FA案内を表示」も参照してください。"
        )
        return "\n".join(lines)

    def _on_close_roster_hr_rules_detail_window(self) -> None:
        w = getattr(self, "_roster_hr_rules_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._roster_hr_rules_detail_window = None
            self._roster_hr_rules_detail_text = None

    def _refresh_roster_hr_rules_detail_body(self) -> None:
        tw = getattr(self, "_roster_hr_rules_detail_text", None)
        if tw is None:
            return
        body = self._format_roster_hr_rules_detail_body()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_roster_hr_rules_detail_window(self) -> None:
        """編成ルールの詳細（閲覧専用）。本文は _format_roster_hr_rules_detail_body に委譲。"""
        parent = getattr(self, "_roster_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_roster_hr_rules_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_roster_hr_rules_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("編成ルールの詳細")
        w.geometry("720x540")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="編成ルールの詳細", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._roster_hr_rules_detail_window = w
        self._roster_hr_rules_detail_text = tw
        self._refresh_roster_hr_rules_detail_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_roster_hr_rules_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_roster_hr_rules_detail_window)

    def _get_user_team_expiring_players(self) -> List[Any]:
        """今オフ契約満了候補（残1年）。読み取り専用、人事画面の事前警告表示用。"""
        if self.team is None:
            return []
        players: List[Any] = []
        try:
            infos = get_expiring_players([self.team])
            players = [info.player for info in infos if getattr(info, "player", None) is not None]
        except Exception:
            try:
                players = [
                    p
                    for p in (self._safe_get(self.team, "players", []) or [])
                    if int(self._safe_get(p, "contract_years_left", 0) or 0) == 1
                ]
            except Exception:
                players = []
        try:
            players.sort(
                key=lambda p: int(self._safe_get(p, "ovr", 0) or 0),
                reverse=True,
            )
        except Exception:
            pass
        return players

    def _format_expiring_contracts_summary_text(self) -> str:
        """人事本体に出す1行：今オフ契約満了候補：N人（A、B、C ほかX人）。"""
        if self.team is None:
            return "今オフ契約満了候補：—"
        players = self._get_user_team_expiring_players()
        if not players:
            return "今オフ契約満了候補：なし"
        n = len(players)
        visible = 3
        names = [str(self._safe_get(p, "name", "-")) for p in players[:visible]]
        head = "、".join(names)
        if n <= visible:
            return f"今オフ契約満了候補：{n}人（{head}）"
        rest = n - visible
        return f"今オフ契約満了候補：{n}人（{head} ほか{rest}人）"

    def _format_expiring_contracts_detail_text(self) -> str:
        """契約満了候補の詳細本文（閲覧専用）。"""
        lines: List[str] = []
        lines.append("契約満了候補（閲覧専用）")
        lines.append("")
        lines.append(
            "この一覧は、現在の契約残年数が1年の選手です。"
            "オフシーズンでは再契約／FA化の判断対象になります。"
        )
        lines.append(
            "今のうちに人事画面の「＋1年延長」で延長するか、"
            "オフの再契約判断に備えてください。"
            f"（残上限は {MAX_CONTRACT_YEARS_DEFAULT} 年・年俸据え置きで延長します）"
        )
        lines.append("")
        if self.team is None:
            lines.append("チームが未接続です。")
            return "\n".join(lines)
        players = self._get_user_team_expiring_players()
        if not players:
            lines.append("該当する選手はいません。")
            return "\n".join(lines)
        lines.append(f"該当：{len(players)}人（OVR降順で表示）")
        lines.append("")
        for player in players:
            name = str(self._safe_get(player, "name", "-"))
            pos = str(self._safe_get(player, "position", "-"))
            ovr = str(self._safe_get(player, "ovr", "-"))
            age = str(self._safe_get(player, "age", "-"))
            salary = self._format_money(self._safe_get(player, "salary", 0))
            lines.append(
                f"・{name} / {pos} / OVR {ovr} / 年齢 {age} / 年俸 {salary} / 契約残1年"
            )
        return "\n".join(lines)

    def _refresh_roster_expiring_contracts_detail_body(self) -> None:
        tw = getattr(self, "_roster_expiring_contracts_detail_text", None)
        if tw is None:
            return
        body = self._format_expiring_contracts_detail_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_roster_expiring_contracts_detail_window(self) -> None:
        """今オフ契約満了候補の詳細（閲覧専用・別窓）。本文は _format_expiring_contracts_detail_text に委譲。"""
        parent = getattr(self, "_roster_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_roster_expiring_contracts_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_roster_expiring_contracts_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("契約満了候補の詳細")
        w.geometry("680x500")
        w.minsize(480, 320)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="契約満了候補", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        tw = scrolledtext.ScrolledText(
            outer,
            height=22,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._roster_expiring_contracts_detail_window = w
        self._roster_expiring_contracts_detail_text = tw
        self._refresh_roster_expiring_contracts_detail_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_roster_expiring_contracts_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_roster_expiring_contracts_detail_window)

    def _on_close_roster_expiring_contracts_detail_window(self) -> None:
        w = getattr(self, "_roster_expiring_contracts_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        finally:
            self._roster_expiring_contracts_detail_window = None
            self._roster_expiring_contracts_detail_text = None

    def _format_offseason_flow_overview_text(self) -> str:
        """オフシーズン流れ説明窓の本文（閲覧専用・Tk非依存）。
        正本データ（OFFSEASON_PHASES / build_offseason_focus_summary）を読み取り利用するだけ。
        """
        from basketball_sim.systems.offseason_phases import OFFSEASON_PHASES
        from basketball_sim.systems.offseason_progress_cli_display import (
            build_offseason_focus_summary,
        )

        lines: List[str] = []
        lines.append("オフシーズンの流れ（閲覧専用）")
        lines.append("")
        lines.append(
            "オフシーズンでは、再契約・契約満了・FA・ドラフト・財務決算などが順に進みます。"
        )
        lines.append(
            "一部のフェーズでは、再契約・ドラフト・FAの選択ダイアログが表示される場合があります。"
        )
        lines.append("処理中は数分ほどウィンドウが応答しないことがあります。")
        lines.append("")
        lines.append("実行前のおすすめ：")
        lines.append("・人事メニューで「今オフ契約満了候補」を確認")
        lines.append("・期待ロスター／予算余力を把握しておく")
        lines.append("")
        lines.append("──────────────────────────────────")
        try:
            phases = list(OFFSEASON_PHASES or [])
        except Exception:
            phases = []
        for idx, row in enumerate(phases, start=1):
            try:
                pid, title = row[0], row[1]
            except Exception:
                continue
            summary = build_offseason_focus_summary(None, idx)
            main_j = str(summary.get("main_judgment") or "情報なし")
            next_f = str(summary.get("next_focus") or "情報なし")
            lines.append(f"[{pid}] {title}")
            lines.append(f"  主な判断：{main_j}")
            lines.append(f"  次に見る：{next_f}")
            lines.append("")
        lines.append("──────────────────────────────────")
        lines.append("※ この窓は閲覧専用です。実行はホームの「オフシーズンを実行」から。")
        return "\n".join(lines)

    def _refresh_offseason_flow_overview_body(self) -> None:
        tw = getattr(self, "_offseason_flow_overview_text", None)
        if tw is None:
            return
        body = self._format_offseason_flow_overview_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_offseason_flow_overview_window(self) -> None:
        """オフシーズンの流れ（閲覧専用・別窓）。本文は _format_offseason_flow_overview_text に委譲。"""
        parent = getattr(self, "root", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_offseason_flow_overview_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_offseason_flow_overview_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("オフシーズンの流れ")
        w.geometry("720x560")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer, text="オフシーズンの流れ", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._offseason_flow_overview_window = w
        self._offseason_flow_overview_text = tw
        self._refresh_offseason_flow_overview_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_offseason_flow_overview_window,
        ).pack(side="right")

        w.protocol(
            "WM_DELETE_WINDOW", self._on_close_offseason_flow_overview_window
        )

    def _on_close_offseason_flow_overview_window(self) -> None:
        w = getattr(self, "_offseason_flow_overview_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        finally:
            self._offseason_flow_overview_window = None
            self._offseason_flow_overview_text = None

    def _collect_future_draft_pool_candidates(self) -> List[Any]:
        """来年ドラフト候補（閲覧専用）の読み取り。
        正本は `team.league_future_draft_pool`（team_id 最小のチームに保持される設計）。
        self.team に無い場合は Season 経由で他クラブを横断的に確認する。
        破壊・生成はせず、見つけたリストをそのまま返す（呼び出し側で `list()` 化済）。
        """
        team = getattr(self, "team", None)
        if team is not None:
            try:
                pool = list(getattr(team, "league_future_draft_pool", []) or [])
                if pool:
                    return pool
            except Exception:
                pass

        candidates_teams: List[Any] = []
        season = getattr(self, "season", None)
        if season is not None:
            try:
                at = getattr(season, "all_teams", None)
                if isinstance(at, list):
                    candidates_teams.extend(at)
            except Exception:
                pass
            if not candidates_teams:
                try:
                    leagues = getattr(season, "leagues", None)
                    if isinstance(leagues, dict):
                        seen: set = set()
                        for _lvl_key in sorted(
                            leagues.keys(),
                            key=lambda k: (not isinstance(k, int), k),
                        ):
                            for t in leagues.get(_lvl_key) or []:
                                if id(t) in seen:
                                    continue
                                seen.add(id(t))
                                candidates_teams.append(t)
                except Exception:
                    pass

        if not candidates_teams:
            try:
                candidates_teams = list(self._iter_league_teams())
            except Exception:
                candidates_teams = []

        for t in candidates_teams:
            try:
                pool = list(getattr(t, "league_future_draft_pool", []) or [])
                if pool:
                    return pool
            except Exception:
                continue
        return []

    def _format_future_draft_pool_overview_text(
        self, pool: Optional[List[Any]] = None
    ) -> str:
        """来年ドラフト候補の閲覧専用本文（Tk非依存）。
        - pool が None の場合は `_collect_future_draft_pool_candidates()` から取得。
        - 元リストは破壊せず、表示用にコピーしてソートする。
        - スカウト精度・隠し能力など新規公開ルールは導入しない（既存属性のみ参照）。
        """
        if pool is None:
            try:
                pool = self._collect_future_draft_pool_candidates()
            except Exception:
                pool = []
        pool_list: List[Any] = list(pool or [])

        lines: List[str] = []
        lines.append("来年ドラフト候補（閲覧専用）")
        lines.append("")

        if not pool_list:
            lines.append("現在、表示できる来年ドラフト候補はいません。")
            lines.append(
                "オフシーズンのスカウト派遣後に候補が生成される場合があります。"
            )
            lines.append("")
            lines.append(
                "※ この窓は閲覧専用です。指名・入札はドラフト本番で行います。"
            )
            return "\n".join(lines)

        lines.append(
            "この一覧は、来年以降のドラフト候補として保持されている選手です。"
        )
        lines.append(
            "候補情報はスカウト・コンバイン・オフシーズン進行で更新される場合があります。"
        )
        lines.append(
            "指名・入札はドラフト本番で行います。この窓では操作できません。"
        )
        lines.append("")

        _pot_rank = {"SS": 6, "S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        _nat_ja = {
            "Japan": "日本",
            "Foreign": "外国籍",
            "Asia": "アジア",
            "Naturalized": "帰化",
        }
        _origin_ja = {
            "college": "大学",
            "highschool": "高校",
            "overseas": "海外",
            "special": "特別枠",
        }

        def _pot_rank_of(p: Any) -> int:
            s = str(getattr(p, "potential", "") or "").upper().strip()
            if not s:
                return 0
            head = s[0:2] if s.startswith("SS") else s[0:1]
            return _pot_rank.get(head, 0)

        def _safe_int(v: Any) -> int:
            try:
                return int(v or 0)
            except Exception:
                return 0

        try:
            sorted_pool = sorted(
                pool_list,
                key=lambda p: (
                    -_pot_rank_of(p),
                    -_safe_int(getattr(p, "ovr", 0)),
                    _safe_int(getattr(p, "age", 0)),
                    str(getattr(p, "name", "")),
                ),
            )
        except Exception:
            sorted_pool = list(pool_list)

        lines.append(f"候補数：{len(sorted_pool)}人")
        lines.append("")
        lines.append("──────────────────────────────────")

        for i, p in enumerate(sorted_pool, start=1):
            name = str(getattr(p, "name", "?"))
            pos = str(getattr(p, "position", "?") or "?")
            age = _safe_int(getattr(p, "age", 0))
            ovr = _safe_int(getattr(p, "ovr", 0))
            pot = str(getattr(p, "potential", "?") or "?")
            nat_key = str(getattr(p, "nationality", "") or "")
            nat_text = _nat_ja.get(nat_key, nat_key) if nat_key else ""
            origin_key = str(getattr(p, "draft_origin_type", "") or "")
            origin_text = (
                _origin_ja.get(origin_key, origin_key) if origin_key else ""
            )
            label = str(getattr(p, "draft_profile_label", "") or "")
            featured = bool(getattr(p, "is_featured_prospect", False))
            reborn = bool(getattr(p, "is_reborn", False))

            base_parts = [
                f"{i:>2}. {name}",
                pos,
                f"{age}歳",
                f"OVR {ovr}",
                f"POT {pot}",
            ]
            extras: List[str] = []
            if origin_text:
                extras.append(origin_text)
            if nat_text and nat_key and nat_key != "Japan":
                extras.append(nat_text)
            if label:
                extras.append(label)
            flag_parts: List[str] = []
            if featured:
                flag_parts.append("注目")
            if reborn:
                flag_parts.append("再生")
            if flag_parts:
                extras.append(" / ".join(flag_parts))

            row = " / ".join(base_parts)
            if extras:
                row = row + " / " + " / ".join(extras)
            lines.append(row)

        lines.append("──────────────────────────────────")
        lines.append(
            "※ この窓は閲覧専用です。指名・入札はドラフト本番で行います。"
        )
        return "\n".join(lines)

    def _refresh_future_draft_pool_overview_body(self) -> None:
        tw = getattr(self, "_future_draft_pool_overview_text", None)
        if tw is None:
            return
        body = self._format_future_draft_pool_overview_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_future_draft_pool_overview_window(self) -> None:
        """来年ドラフト候補（閲覧専用・別窓）。本文は `_format_future_draft_pool_overview_text` に委譲。"""
        parent = getattr(self, "root", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_future_draft_pool_overview_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_future_draft_pool_overview_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("来年ドラフト候補")
        w.geometry("760x560")
        w.minsize(560, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer, text="来年ドラフト候補", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._future_draft_pool_overview_window = w
        self._future_draft_pool_overview_text = tw
        self._refresh_future_draft_pool_overview_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_future_draft_pool_overview_window,
        ).pack(side="right")

        w.protocol(
            "WM_DELETE_WINDOW", self._on_close_future_draft_pool_overview_window
        )

    def _on_close_future_draft_pool_overview_window(self) -> None:
        w = getattr(self, "_future_draft_pool_overview_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        finally:
            self._future_draft_pool_overview_window = None
            self._future_draft_pool_overview_text = None

    def _collect_fa_market_candidates(self) -> List[Any]:
        """FA市場（閲覧専用）の読み取り。
        正本は `Season.free_agents`。`self.season.free_agents` を最優先で読み取り、
        無ければ `self.free_agents` / `self.team.free_agents` の順にフォールバック。
        破壊・生成はせず、見つけたリストを `list(...)` でコピーして返す。
        """
        season = getattr(self, "season", None)
        if season is not None:
            try:
                fa_attr = getattr(season, "free_agents", None)
                if isinstance(fa_attr, list):
                    return list(fa_attr)
            except Exception:
                pass
        try:
            fa_attr = getattr(self, "free_agents", None)
            if isinstance(fa_attr, list):
                return list(fa_attr)
        except Exception:
            pass
        team = getattr(self, "team", None)
        if team is not None:
            try:
                fa_attr = getattr(team, "free_agents", None)
                if isinstance(fa_attr, list):
                    return list(fa_attr)
            except Exception:
                pass
        return []

    def _format_fa_market_overview_text(
        self, pool: Optional[List[Any]] = None
    ) -> str:
        """FA市場の閲覧専用本文（Tk非依存）。
        - pool が None の場合は `_collect_fa_market_candidates()` から取得。
        - 元リストは破壊せず、表示用にコピーしてソートする。
        - FA 市場ロジック・獲得処理・契約年俸ロジックには一切干渉しない。
          属性参照のみで、`ensure_fa_market_fields` 等の副作用がある関数は呼ばない。
        """
        if pool is None:
            try:
                pool = self._collect_fa_market_candidates()
            except Exception:
                pool = []
        pool_list: List[Any] = list(pool or [])

        lines: List[str] = []
        lines.append("FA市場（閲覧専用）")
        lines.append("")

        if not pool_list:
            lines.append("現在、表示できるFA候補はいません。")
            lines.append(
                "契約解除やオフシーズンの契約満了後にFA候補が増える場合があります。"
            )
            lines.append("")
            lines.append(
                "※ この窓は閲覧専用です。獲得は人事メニューの「インシーズンFA」または"
            )
            lines.append("　オフシーズン中のFA選択から行います。")
            return "\n".join(lines)

        lines.append(
            "この一覧は、現在FA市場にいる選手です。"
        )
        lines.append("この窓では獲得・契約は行えません。")
        lines.append(
            "獲得は、人事メニューの「インシーズンFA」または"
            "オフシーズン中のFA選択から行います。"
        )
        lines.append("")

        _pot_rank = {"SS": 6, "S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        _nat_ja = {
            "Japan": "日本",
            "Foreign": "外国籍",
            "Asia": "アジア",
            "Naturalized": "帰化",
        }

        def _pot_rank_of(p: Any) -> int:
            s = str(getattr(p, "potential", "") or "").upper().strip()
            if not s:
                return 0
            head = s[0:2] if s.startswith("SS") else s[0:1]
            return _pot_rank.get(head, 0)

        def _safe_int(v: Any) -> int:
            try:
                return int(v or 0)
            except Exception:
                return 0

        def _salary_estimate(p: Any) -> int:
            """`fa_pool_market_salary` を最優先、なければ `salary` を使う。
            どちらも 0 / 取得失敗時は 0（行から省略する側で扱う）。
            """
            for key in ("fa_pool_market_salary", "salary"):
                try:
                    v = int(getattr(p, key, 0) or 0)
                    if v > 0:
                        return v
                except Exception:
                    continue
            return 0

        try:
            sorted_pool = sorted(
                pool_list,
                key=lambda p: (
                    -_safe_int(getattr(p, "ovr", 0)),
                    -_pot_rank_of(p),
                    _safe_int(getattr(p, "age", 0)),
                    str(getattr(p, "name", "")),
                ),
            )
        except Exception:
            sorted_pool = list(pool_list)

        lines.append(f"候補数：{len(sorted_pool)}人")
        lines.append("")
        lines.append("──────────────────────────────────")

        for i, p in enumerate(sorted_pool, start=1):
            name = str(getattr(p, "name", "?"))
            pos = str(getattr(p, "position", "?") or "?")
            age = _safe_int(getattr(p, "age", 0))
            ovr = _safe_int(getattr(p, "ovr", 0))
            pot = str(getattr(p, "potential", "?") or "?")
            nat_key = str(getattr(p, "nationality", "") or "")
            nat_text = _nat_ja.get(nat_key, nat_key) if nat_key else ""
            sal = _salary_estimate(p)

            base_parts = [
                f"{i:>2}. {name}",
                pos,
                f"{age}歳",
                f"OVR {ovr}",
                f"POT {pot}",
            ]
            extras: List[str] = []
            if nat_text:
                extras.append(nat_text)
            if sal > 0:
                try:
                    money_text = format_money_yen_ja_readable(sal)
                except Exception:
                    money_text = f"{sal:,}円"
                extras.append(f"年俸目安 {money_text}")

            row = " / ".join(base_parts)
            if extras:
                row = row + " / " + " / ".join(extras)
            lines.append(row)

        lines.append("──────────────────────────────────")
        lines.append(
            "※ この窓は閲覧専用です。獲得は人事メニューの「インシーズンFA」または"
        )
        lines.append("　オフシーズン中のFA選択から行います。")
        return "\n".join(lines)

    def _refresh_fa_market_overview_body(self) -> None:
        tw = getattr(self, "_fa_market_overview_text", None)
        if tw is None:
            return
        body = self._format_fa_market_overview_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_fa_market_overview_window(self) -> None:
        """FA市場（閲覧専用・別窓）。本文は `_format_fa_market_overview_text` に委譲。"""
        parent = getattr(self, "root", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_fa_market_overview_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_fa_market_overview_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("FA市場")
        w.geometry("760x560")
        w.minsize(560, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer, text="FA市場", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._fa_market_overview_window = w
        self._fa_market_overview_text = tw
        self._refresh_fa_market_overview_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_fa_market_overview_window,
        ).pack(side="right")

        w.protocol(
            "WM_DELETE_WINDOW", self._on_close_fa_market_overview_window
        )

    def _on_close_fa_market_overview_window(self) -> None:
        w = getattr(self, "_fa_market_overview_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        finally:
            self._fa_market_overview_window = None
            self._fa_market_overview_text = None

    def _format_offseason_result_recap_text(
        self, team: Any = None, season: Any = None
    ) -> str:
        """直近オフの振り返り本文（閲覧専用・Tk非依存）。

        `team` / `season` はテスト用に差し替え可能。未指定時は `self.team` を参照する。
        永続データの読み取りのみ。リストは破壊しない。
        """
        _ = season  # 将来: シーズン文脈での絞り込み用に予約
        t = team if team is not None else getattr(self, "team", None)

        lines: List[str] = []
        lines.append("直近オフシーズンの振り返り（閲覧専用）")
        lines.append("")
        lines.append(
            "この画面は、現在保存されているクラブ履歴・取引履歴・財務履歴・昇降格記録から"
            "確認できる範囲をまとめたものです。"
        )
        lines.append(
            "再契約やオークションドラフト指名など、一部の出来事は現状の履歴データだけでは"
            "詳細表示できない場合があります。"
        )
        lines.append("")

        if t is None:
            lines.append("【クラブ】（チーム未設定）")
            lines.append("")
            lines.append("【主な人事・移籍】")
            lines.append("・確認できる取引履歴はまだありません（チーム未設定）。")
            lines.append("")
            lines.append("【ドラフト・新人】")
            lines.append(
                "・現状の履歴データだけでは、オークションドラフト指名結果の詳細は限定的です。"
            )
            lines.append("")
            lines.append("【財務決算】")
            lines.append("・直近の財務履歴はまだ確認できません。")
            lines.append("")
            lines.append("【昇降格・クラブ史】")
            lines.append("・直近の昇降格記録は確認できません。")
            lines.append("")
            lines.append("【注記】")
            lines.append(
                "・再契約の詳細は、チーム取引履歴（history_transactions）からは限定的です。"
            )
            lines.append(
                "・オークション形式のドラフト指名は、チームの draft 取引行が無い場合が多く、"
                "ロスター上の新人フラグで分かる範囲に留まります。"
            )
            lines.append("・この窓は閲覧専用です。結果の保存方式や処理ロジックは変更していません。")
            return "\n".join(lines)

        club_name = str(getattr(t, "name", "") or "").strip() or "（名称不明）"
        lines.append(f"【クラブ】{club_name}")
        lines.append("")

        # --- 人事・移籍（history_transactions） ---
        tx_rows = list(getattr(t, "history_transactions", None) or [])
        wanted_types = {"free_agent", "trade", "release", "draft", "resign"}
        type_label = {
            "free_agent": "FA",
            "trade": "トレード",
            "release": "解雇/離脱",
            "draft": "ドラフト",
            "resign": "再契約",
        }
        picked: List[dict] = []
        for row in reversed(tx_rows):
            if not isinstance(row, dict):
                continue
            tt = str(row.get("transaction_type", "") or "").strip().lower()
            if tt in wanted_types:
                picked.append(row)
            if len(picked) >= 12:
                break

        lines.append("【主な人事・移籍】")
        if picked:
            for row in picked:
                tt = str(row.get("transaction_type", "") or "").strip().lower()
                lab = type_label.get(tt, tt or "取引")
                pname = str(row.get("player_name", "") or "").strip() or "（選手名不明）"
                note = str(row.get("note", "") or "").strip()
                if len(note) > 140:
                    note = note[:137] + "..."
                if tt == "free_agent":
                    line = f"・{lab}: {pname} を獲得"
                    if note:
                        line += f"（{note}）"
                    lines.append(line)
                elif tt == "resign":
                    line = f"・{lab}: {pname} と再契約"
                    if note:
                        line += f"（{note}）"
                    lines.append(line)
                else:
                    frag = f"・{lab}: {pname}"
                    if note:
                        frag += f" — {note}"
                    lines.append(frag)
        else:
            lines.append("・該当する取引履歴はまだありません。")

        # 選手キャリアから再契約・延長の痕跡（読める場合のみ）
        resign_lines: List[str] = []
        players = list(getattr(t, "players", None) or [])
        for p in players:
            ch = getattr(p, "career_history", None) or []
            if not isinstance(ch, list) or not ch:
                continue
            for row in ch[-2:]:
                if not isinstance(row, dict):
                    continue
                ev = str(row.get("event", "") or "").strip()
                if ev not in ("Re-sign", "Contract Extension"):
                    continue
                note = str(row.get("note", "") or "").strip()
                tail = f" — {note}" if note else ""
                resign_lines.append(
                    f"・（選手キャリア）{getattr(p, 'name', '?')} : {ev}{tail}"
                )
                if len(resign_lines) >= 5:
                    break
            if len(resign_lines) >= 5:
                break
        if resign_lines:
            lines.append("・再契約・延長の記録（選手キャリアから読み取れる範囲）:")
            lines.extend(resign_lines[:5])
        else:
            lines.append(
                "・再契約の詳細は、現状のチーム取引履歴からは限定的です。"
                "（選手キャリアに Re-sign / Contract Extension があれば上に表示されます）"
            )
        lines.append("")

        # --- ドラフト・新人 ---
        lines.append("【ドラフト・新人】")
        has_draft_tx = any(
            isinstance(r, dict)
            and str(r.get("transaction_type", "") or "").strip().lower() == "draft"
            for r in tx_rows
        )
        if not has_draft_tx:
            lines.append(
                "・現状の履歴データだけでは、オークションドラフト指名結果の詳細は限定的です。"
            )
        else:
            lines.append("・取引履歴にドラフト（draft）行があります（上の人事・移籍を参照）。")

        rookie_rows: List[str] = []
        seen_players: set[int] = set()
        for p in players:
            acq = str(getattr(p, "acquisition_type", "") or "").strip().lower()
            is_rookie = bool(getattr(p, "is_draft_rookie_contract", False))
            if not (acq == "draft" or is_rookie):
                continue
            oid = id(p)
            if oid in seen_players:
                continue
            seen_players.add(oid)
            nm = str(getattr(p, "name", "") or "?")
            note = str(getattr(p, "acquisition_note", "") or "").strip()
            lock = getattr(p, "draft_rookie_locked_salary", None)
            bits = []
            if note:
                bits.append(note)
            if lock is not None:
                try:
                    bits.append(f"ルーキー年俸ロック: {int(lock):,}円")
                except (TypeError, ValueError):
                    bits.append(f"ルーキー年俸ロック: {lock}")
            tail = " / ".join(bits) if bits else "（詳細ノートなし）"
            rookie_rows.append(f"・{nm} — {tail}")

        if rookie_rows:
            lines.append("・ロスター上の新人契約フラグから確認できる範囲:")
            lines.extend(rookie_rows[:10])
        else:
            if not has_draft_tx:
                lines.append(
                    "・ロスターから新人ドラフト扱いと判定できる選手は見つかりませんでした。"
                )
        lines.append("")

        # --- 財務 ---
        lines.append("【財務決算】")
        fh = list(getattr(t, "finance_history", None) or [])
        if fh:
            latest = fh[-1]
            if isinstance(latest, dict):
                rev = latest.get("revenue")
                exp = latest.get("expense")
                cf = latest.get("cashflow")
                end_m = latest.get("ending_money")
                try:
                    cf_int = int(cf) if cf is not None else None
                except (TypeError, ValueError):
                    cf_int = None
                if cf_int is None and rev is not None and exp is not None:
                    try:
                        cf_int = int(rev) - int(exp)
                    except (TypeError, ValueError):
                        pass
                if cf_int is not None:
                    if cf_int > 0:
                        cf_label = "黒字"
                    elif cf_int < 0:
                        cf_label = "赤字"
                    else:
                        cf_label = "収支ゼロ"
                    lines.append(f"・直近決算（finance_history 最新）: {cf_label}（収支 {cf_int:+,} 円）")
                else:
                    lines.append("・直近決算: 収支の数値は finance_history から読み取れませんでした。")
                parts = []
                if rev is not None:
                    try:
                        parts.append(f"売上 {int(rev):,} 円")
                    except (TypeError, ValueError):
                        parts.append(f"売上 {rev}")
                if exp is not None:
                    try:
                        parts.append(f"支出 {int(exp):,} 円")
                    except (TypeError, ValueError):
                        parts.append(f"支出 {exp}")
                if end_m is not None:
                    try:
                        parts.append(f"締め後所持金 {int(end_m):,} 円")
                    except (TypeError, ValueError):
                        parts.append(f"締め後所持金 {end_m}")
                if parts:
                    lines.append("・" + " / ".join(parts))
                nnote = str(latest.get("note", "") or "").strip()
                if nnote and len(nnote) <= 200:
                    lines.append(f"・メモ: {nnote}")
            else:
                lines.append("・財務履歴の最新要素の形式が想定外です。")
        else:
            rev_ls = getattr(t, "revenue_last_season", None)
            exp_ls = getattr(t, "expense_last_season", None)
            cf_ls = getattr(t, "cashflow_last_season", None)
            money = getattr(t, "money", None)
            if any(x is not None for x in (rev_ls, exp_ls, cf_ls, money)):
                try:
                    cf_int = int(cf_ls) if cf_ls is not None else None
                except (TypeError, ValueError):
                    cf_int = None
                if cf_int is not None:
                    cf_label = "黒字" if cf_int > 0 else ("赤字" if cf_int < 0 else "収支ゼロ")
                    lines.append(
                        f"・直近シーズン締め（チーム集計フィールド）: {cf_label} "
                        f"（収支 {cf_int:+,} 円）"
                    )
                else:
                    lines.append("・直近シーズン締め: 収支は数値として確認できませんでした。")
                frag = []
                if rev_ls is not None:
                    try:
                        frag.append(f"売上 {int(rev_ls):,} 円")
                    except (TypeError, ValueError):
                        frag.append(f"売上 {rev_ls}")
                if exp_ls is not None:
                    try:
                        frag.append(f"支出 {int(exp_ls):,} 円")
                    except (TypeError, ValueError):
                        frag.append(f"支出 {exp_ls}")
                if money is not None:
                    try:
                        frag.append(f"現在資金 {int(money):,} 円")
                    except (TypeError, ValueError):
                        frag.append(f"現在資金 {money}")
                if frag:
                    lines.append("・" + " / ".join(frag))
            else:
                lines.append("・直近の財務履歴はまだ確認できません。")
        lines.append("")

        # --- 昇降格 ---
        lines.append("【昇降格・クラブ史】")
        ms = list(getattr(t, "history_milestones", None) or [])
        pr_rows: List[dict] = []
        for row in reversed(ms):
            if not isinstance(row, dict):
                continue
            mt = str(row.get("milestone_type") or row.get("type") or "").strip().lower()
            if mt in ("promoted", "relegated"):
                pr_rows.append(row)
            if len(pr_rows) >= 6:
                break
        if pr_rows:
            for row in pr_rows:
                mt = str(row.get("milestone_type") or row.get("type") or "").strip().lower()
                title = str(row.get("title", "") or "").strip()
                detail = str(row.get("detail", "") or "").strip()
                if mt == "promoted":
                    head = "昇格"
                elif mt == "relegated":
                    head = "降格"
                else:
                    head = mt or "記録"
                body = " / ".join(x for x in (title, detail) if x) or "（詳細なし）"
                lines.append(f"・{head}: {body}")
        else:
            lines.append("・直近の昇降格記録は確認できません。")
        lines.append("")

        lines.append("【注記】")
        lines.append(
            "・再契約の詳細は、チーム取引履歴（history_transactions）からは限定的です。"
        )
        lines.append(
            "・オークション形式のドラフト指名は、チームの draft 取引行が無い場合が多く、"
            "ロスター上の新人フラグで分かる範囲に留まります。"
        )
        lines.append("・この窓は閲覧専用です。結果の保存方式や処理ロジックは変更していません。")
        return "\n".join(lines)

    def _refresh_offseason_result_recap_body(self) -> None:
        tw = getattr(self, "_offseason_result_recap_text", None)
        if tw is None:
            return
        body = self._format_offseason_result_recap_text()
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_offseason_result_recap_window(self) -> None:
        """直近オフの振り返り（閲覧専用・別窓）。本文は `_format_offseason_result_recap_text` に委譲。"""
        parent = getattr(self, "root", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_offseason_result_recap_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_offseason_result_recap_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("直近オフシーズンの振り返り")
        w.geometry("780x580")
        w.minsize(560, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer, text="直近オフシーズンの振り返り", style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._offseason_result_recap_window = w
        self._offseason_result_recap_text = tw
        self._refresh_offseason_result_recap_body()

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_offseason_result_recap_window,
        ).pack(side="right")

        w.protocol(
            "WM_DELETE_WINDOW", self._on_close_offseason_result_recap_window
        )

    def _on_close_offseason_result_recap_window(self) -> None:
        w = getattr(self, "_offseason_result_recap_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        finally:
            self._offseason_result_recap_window = None
            self._offseason_result_recap_text = None

    def _refresh_next_game(self) -> None:
        info = self._build_next_game_info()
        for i, var in enumerate(self.next_game_lines):
            var.set(info[i] if i < len(info) else "")

    def _refresh_club_summary(self) -> None:
        info = self._build_club_summary_info()
        for var, line in zip(self.club_summary_lines, info):
            var.set(line)

    def _refresh_tasks(self) -> None:
        tasks = self._get_task_lines()
        count = len(tasks)
        empty_placeholder = len(tasks) == 1 and self._is_home_tasks_empty_line(tasks[0])
        shown = [] if empty_placeholder else tasks[:3]

        counts = self._home_task_urgent_normal_counts(tasks)
        if counts is None:
            self.tasks_summary_var.set(
                "いま対応が必要な項目はありません（状況は各メニューで確認できます）。"
            )
        else:
            urgent, normal = counts
            overflow = max(0, count - len(shown))
            summary = (
                f"内訳: 急ぎ {urgent} 件・あとで確認 {normal} 件（計 {urgent + normal} 件）"
            )
            if overflow:
                summary += f" ※この欄は最大 {len(shown)} 件まで表示（ほか {overflow} 件）"
            self.tasks_summary_var.set(summary)

        for i, var in enumerate(self.task_lines):
            if i < len(shown):
                var.set(f"• {self._format_task_line_for_display(shown[i])}")
            else:
                var.set("")

        season_finished = bool(self._safe_get(self.season, "season_finished", False))
        progress_hint = ""
        if not season_finished and self.season is not None and self.team is not None:
            progress_hint, _ = next_advance_display_hints(self.season, self.team)
        if season_finished:
            fin_msg = (
                "レギュラーシーズン終了。ディビジョンPOは内部で処理済みです。"
                "『情報』『日程』で結果確認後、『オフシーズンを実行』で契約・ドラフト等を進めます"
                "（数分かかる場合があります）。"
            )
            if self.advance_primary_ui_fn is not None:
                try:
                    _, hint = self.advance_primary_ui_fn()
                    self._set_home_advance_hint(hint or fin_msg)
                except Exception:
                    self._set_home_advance_hint(fin_msg)
            else:
                self._set_home_advance_hint(fin_msg)
        elif not empty_placeholder and count > 0:
            task_line = (
                f"未対応 {count} 件。上の「今やること」で確認（急ぎ／あとで）。"
            )
            if self._injured_players_on_user_team():
                task_line += " 負傷は「負傷者の詳細・行動ガイド」。"
            if progress_hint:
                self._set_home_advance_hint(f"{progress_hint}\n{task_line}")
            else:
                self._set_home_advance_hint(task_line)
        else:
            self._set_home_advance_hint(progress_hint)

        inj_btn = getattr(self, "_task_injury_detail_button", None)
        if inj_btn is not None:
            injured_here = bool(self._injured_players_on_user_team())
            show_inj = (
                injured_here
                and self.external_tasks is None
                and not empty_placeholder
            )
            try:
                if show_inj:
                    inj_btn.pack(fill="x", pady=(8, 0))
                else:
                    inj_btn.pack_forget()
            except tk.TclError:
                pass

    def _refresh_advance_button(self) -> None:
        if self.advance_primary_ui_fn is not None:
            try:
                label, _ = self.advance_primary_ui_fn()
                self.advance_button.configure(text=label)
                return
            except Exception:
                pass
        fin = bool(self._safe_get(self.season, "season_finished", False))
        self.advance_button.configure(text="オフシーズンを実行" if fin else "次へ進む")

    def _refresh_news(self) -> None:
        news = self._get_news_items()[:4]
        tw = getattr(self, "news_text", None)
        if tw is None:
            return
        lines = [f"・{n}" for n in news]
        body = "\n".join(lines) if lines else ""
        if not body.strip():
            body = "（表示できるニュースがありません）"
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------
    def _build_next_game_info(self) -> List[str]:
        _, panel_hint = next_advance_display_hints(self.season, self.team)
        sn = int(self._safe_get(self.season, "season_no", 1) or 1)
        if self.season is not None and self.team is not None:
            cup_lines = build_emperor_cup_main_next_lines(
                self.season, self.team, season_year=sn
            )
            if cup_lines is not None:
                out = list(cup_lines)
                while len(out) < 5:
                    out.append("")
                out.append(panel_hint or "")
                return out[:6]

        next_game = self._find_next_game()
        if next_game is None:
            if self.season is not None and self.team is not None:
                po_lines = build_division_playoff_main_next_lines(
                    self.season, self.team, season_year=sn
                )
                if po_lines is not None:
                    out = list(po_lines)
                    while len(out) < 5:
                        out.append("")
                    out.append(panel_hint or "")
                    return out[:6]
            return [
                "次の試合情報なし",
                "リーグ日程（SeasonEvent）も参照できませんでした",
                "ホーム/アウェイ: -",
                "相手情報: -",
                "補足: 左メニュー「日程」で一覧を確認できます",
                panel_hint or "",
            ]

        game_type = self._first_non_empty(
            self._safe_get(next_game, "game_type", None),
            self._safe_get(next_game, "match_type", None),
            competition_display_name("regular_season"),
        )
        game_round = self._first_non_empty(
            self._safe_get(next_game, "round_name", None),
            self._safe_get(next_game, "round", None),
            self._safe_get(next_game, "section", None),
            "-",
        )
        nxt_round = self._safe_get(next_game, "sim_round", None)
        if nxt_round is not None and self.season is not None:
            game_date = schedule_month_week_label(self.season, int(nxt_round))
        else:
            hint = self._safe_get(next_game, "schedule_date_hint", None)
            if hint:
                game_date = str(hint)
            else:
                game_date = self._format_date(
                    self._first_non_empty(
                        self._safe_get(next_game, "date", None),
                        self._safe_get(next_game, "game_date", None),
                        self._safe_get(next_game, "scheduled_date", None),
                        self._get_current_date(),
                    )
                )

        home_team = self._resolve_team_name(self._safe_get(next_game, "home_team", None))
        away_team = self._resolve_team_name(self._safe_get(next_game, "away_team", None))
        user_is_home = self._is_user_home(next_game)
        opponent = away_team if user_is_home else home_team

        venue_text = "ホーム" if user_is_home else "アウェイ"
        opponent_rank = self._lookup_team_rank(opponent)
        opponent_record = self._lookup_team_record(opponent)

        meaning = self._build_next_game_meaning(opponent_rank, venue_text)
        compare = self._build_next_game_compare(opponent_rank, opponent_record)

        lines = [
            f"{game_round} / {game_type} / {game_date}",
            f"{home_team} vs {away_team}",
            f"{venue_text} / 相手順位: {opponent_rank} / 相手戦績: {opponent_record}",
            meaning,
            compare,
            panel_hint or "",
        ]
        return lines

    def _build_club_summary_info(self) -> List[str]:
        rank = self._compute_rank_text()
        wins = int(self._safe_get(self.team, "regular_wins", 0) or 0)
        losses = int(self._safe_get(self.team, "regular_losses", 0) or 0)
        total = wins + losses
        win_pct = (wins / total) if total > 0 else 0.0

        recent5_text = self._build_recent5_text()
        streak_text = self._build_streak_text()
        mission_text = self._build_owner_progress_text()
        team_comment = self._build_team_comment(win_pct)
        supplement = self._build_club_supplement()

        return [
            f"順位: {rank} / {wins}勝{losses}敗 / 勝率 {win_pct:.3f}",
            self._build_payroll_cap_summary_line(),
            recent5_text,
            mission_text,
            team_comment if streak_text == "-" else f"{team_comment}（{streak_text}）",
            supplement,
        ]

    def _build_payroll_cap_summary_line(self) -> str:
        """クラブサマリー用: ペイロールとリーグキャップ（読み取り専用）。"""
        team = self.team
        if team is None:
            return "給与・キャップ: チーム情報なし"
        try:
            from basketball_sim.systems.contract_logic import get_team_payroll
            from basketball_sim.systems.salary_cap_budget import (
                cap_status,
                compute_luxury_tax,
                get_payroll_floor,
                get_soft_cap,
                league_level_for_team,
            )

            payroll = int(get_team_payroll(team))
            lv = league_level_for_team(team)
            league_cap = int(get_soft_cap(league_level=lv))
            st = cap_status(payroll, league_level=lv)
            status_ja = {
                "under_cap": "キャップ内",
                "over_soft_cap": "キャップ超過",
            }.get(st, st)
            room_soft = league_cap - payroll
            if room_soft >= 0:
                room_str = f"キャップ余裕 {format_money_yen_ja_readable(room_soft)}"
            else:
                room_str = f"キャップ超過 {format_money_yen_ja_readable(abs(room_soft))}"
            tax = int(compute_luxury_tax(payroll, league_level=lv))
            tax_str = f" / 贅沢税 {format_money_yen_ja_readable(tax)}" if tax > 0 else ""
            bud = int(self._safe_get(team, "payroll_budget", 0) or 0)
            bud_str = ""
            if bud > 0:
                mark = " ⚠" if payroll > bud else ""
                bud_str = f" | クラブ目安 {format_money_yen_ja_readable(bud)}{mark}"
            floor = int(get_payroll_floor(lv))
            floor_str = ""
            if floor > 0 and payroll < floor:
                floor_str = (
                    f" | ⚠ ペイロール下限未満（要 {format_money_yen_ja_readable(floor)}以上・"
                    "シーズン終了時は降格の対象）"
                )
            return (
                f"給与合計 {format_money_yen_ja_readable(payroll)}（サラリーキャップ "
                f"{format_money_yen_ja_readable(league_cap)}・全D共通12億）"
                f" | {status_ja} | {room_str}{tax_str}{bud_str}{floor_str}"
            )
        except Exception:
            return "給与・キャップ: 計算不可"



    def open_roster_window(self) -> None:
        """人事・ロスター: トレード／FA 案内、表、詳細ロスター（テキスト一覧は別窓）。＋1年延長・FA 解除は条件付き。"""
        existing = getattr(self, "_roster_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_roster_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"人事・ロスター - {self._team_name()}")
        window.geometry("980x840")
        window.minsize(860, 620)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=10)
        outer.pack(fill="both", expand=True)

        # 下部（補足＋閉じる）を先に bottom へ固定し、ロスター帯の伸縮で画面外に押し出されないようにする
        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=8)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))

        self.roster_hint_var = tk.StringVar(value="")
        tk.Label(
            bottom,
            textvariable=self.roster_hint_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=2,
        ).pack(fill="x", anchor="w")

        btn_row = tk.Frame(bottom, bg="#1d2129")
        btn_row.pack(fill="x", pady=(4, 0))
        self._jpn_text_button(btn_row, "閉じる", self._on_close_roster_window, side="right")

        roster_main = ttk.Frame(outer, style="Root.TFrame", padding=0)
        roster_main.pack(side="top", fill="both", expand=True)

        summary_wrap = ttk.Frame(roster_main, style="Panel.TFrame", padding=(10, 6))
        summary_wrap.pack(fill="x", pady=(0, 6))

        summary_header = ttk.Frame(summary_wrap, style="Panel.TFrame")
        summary_header.pack(fill="x", pady=(0, 2))
        ttk.Label(
            summary_header,
            text="ロスター状況",
            style="SectionTitle.TLabel",
        ).pack(side="left", anchor="w")
        ttk.Button(
            summary_header,
            text="編成ルールの詳細",
            style="Menu.TButton",
            command=self._open_roster_hr_rules_detail_window,
        ).pack(side="right", anchor="e")

        self.roster_situation_var = tk.StringVar(value="")
        tk.Label(
            summary_wrap,
            textvariable=self.roster_situation_var,
            bg="#1d2129",
            fg="#d6dbe3",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 10),
            padx=0,
            pady=0,
            wraplength=900,
        ).pack(fill="x", anchor="w", pady=(0, 0))

        expiring_wrap = ttk.Frame(roster_main, style="Panel.TFrame", padding=(10, 4))
        expiring_wrap.pack(fill="x", pady=(0, 6))
        expiring_row = ttk.Frame(expiring_wrap, style="Panel.TFrame")
        expiring_row.pack(fill="x", anchor="w")
        self.roster_expiring_var = tk.StringVar(value="今オフ契約満了候補：—")
        tk.Label(
            expiring_row,
            textvariable=self.roster_expiring_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=0,
            pady=0,
        ).pack(side="left", anchor="w", fill="x", expand=True)
        ttk.Button(
            expiring_row,
            text="契約満了候補の詳細",
            style="Menu.TButton",
            command=self._open_roster_expiring_contracts_detail_window,
        ).pack(side="right", anchor="e")

        trade_fa_wrap = ttk.Frame(roster_main, style="Panel.TFrame", padding=(10, 4))
        trade_fa_wrap.pack(fill="x", pady=(0, 6))
        tf_header = ttk.Frame(trade_fa_wrap, style="Panel.TFrame")
        tf_header.pack(fill="x", anchor="w", pady=(0, 4))
        ttk.Label(
            tf_header,
            text="編成操作：表で選手を選び、補強・整理・延長を行います。",
            style="TopBar.TLabel",
            anchor="w",
        ).pack(side="left", anchor="w")
        ttk.Button(
            tf_header,
            text="トレード・FA案内を表示",
            style="Menu.TButton",
            command=self._open_roster_trade_fa_guidance_detail_window,
        ).pack(side="right", anchor="e")
        tf_btn_row = ttk.Frame(trade_fa_wrap, style="Panel.TFrame")
        tf_btn_row.pack(fill="x", anchor="w", pady=(0, 2))
        self._jpn_text_button(
            tf_btn_row,
            "トレード",
            self._on_roster_multi_trade_players_only,
            side="left",
        )
        self._jpn_text_button(
            tf_btn_row,
            "インシーズンFA（1人）",
            self._on_roster_inseason_fa_one,
            side="left",
            padx=(10, 0),
        )
        self._jpn_text_button(
            tf_btn_row,
            "契約解除（FA送り）",
            self._on_roster_release_selected,
            side="left",
            padx=(10, 0),
        )
        self._jpn_text_button(
            tf_btn_row,
            "＋1年延長",
            self._on_roster_extend_one_year_selected,
            side="left",
            padx=(10, 0),
        )
        tf_summary = ttk.Frame(trade_fa_wrap, style="Panel.TFrame")
        tf_summary.pack(fill="x", anchor="w", pady=(2, 0))
        self.roster_trade_fa_summary_var = tk.StringVar(value="")
        tk.Label(
            tf_summary,
            textvariable=self.roster_trade_fa_summary_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=8,
            pady=0,
            wraplength=900,
        ).pack(fill="x", anchor="w", pady=(0, 0))

        columns = (
            "role",
            "name",
            "pos",
            "ovr",
            "pot",
            "age",
            "nat_bucket",
            "fatigue",
            "morale",
            "salary",
            "years",
        )

        tree_wrap = ttk.Frame(roster_main, style="Panel.TFrame", padding=(8, 6))
        # 縦は表の行数＋帯の自然高さに抑え、余白は roster_main 側で吸収（閉じる行は outer の bottom で固定）
        tree_wrap.pack(fill="x", expand=False)

        roster_header = ttk.Frame(tree_wrap, style="Panel.TFrame")
        roster_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(
            roster_header,
            text="ロスター",
            style="SectionTitle.TLabel",
        ).pack(side="left", anchor="w")
        ttk.Button(
            roster_header,
            text="詳細ロスターを表示",
            style="Menu.TButton",
            command=self._open_roster_gm_text_list_detail_window,
        ).pack(side="right", anchor="e")

        self.roster_tree = ttk.Treeview(
            tree_wrap,
            columns=columns,
            show="headings",
            height=15,
        )
        headings = {
            "role": "役割",
            "name": "選手名",
            "pos": "POS",
            "ovr": "OVR",
            "pot": "POT",
            "age": "年齢",
            "nat_bucket": "国籍区分",
            "fatigue": "疲労",
            "morale": "士気",
            "salary": "年俸",
            "years": "残年数",
        }
        widths = {
            "role": 85,
            "name": 190,
            "pos": 52,
            "ovr": 55,
            "pot": 52,
            "age": 52,
            "nat_bucket": 98,
            "fatigue": 56,
            "morale": 56,
            "salary": 115,
            "years": 65,
        }
        minwidths = {
            "role": 65,
            "name": 150,
            "pos": 40,
            "ovr": 48,
            "pot": 45,
            "age": 45,
            "nat_bucket": 85,
            "fatigue": 48,
            "morale": 48,
            "salary": 95,
            "years": 58,
        }

        for key in columns:
            self.roster_tree.heading(key, text=headings[key])
            anchor = "center" if key not in ("name", "nat_bucket") else "w"
            self.roster_tree.column(
                key,
                width=widths[key],
                minwidth=minwidths[key],
                anchor=anchor,
                stretch=(key == "name"),
            )

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.roster_tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.roster_tree.xview)
        self.roster_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.roster_tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, columnspan=2, sticky="ew")
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(1, weight=0)

        self._roster_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_roster_window)
        self._refresh_roster_window()

    def _on_close_roster_window(self) -> None:
        try:
            gd = getattr(self, "_roster_trade_fa_guidance_detail_window", None)
            if gd is not None and gd.winfo_exists():
                gd.destroy()
        except Exception:
            pass
        finally:
            self._roster_trade_fa_guidance_detail_window = None
            self._roster_trade_fa_guidance_detail_text = None
        try:
            ld = getattr(self, "_roster_gm_text_list_detail_window", None)
            if ld is not None and ld.winfo_exists():
                ld.destroy()
        except Exception:
            pass
        finally:
            self._roster_gm_text_list_detail_window = None
            self._roster_gm_text_list_detail_text = None
        try:
            hr = getattr(self, "_roster_hr_rules_detail_window", None)
            if hr is not None and hr.winfo_exists():
                hr.destroy()
        except Exception:
            pass
        finally:
            self._roster_hr_rules_detail_window = None
            self._roster_hr_rules_detail_text = None
        try:
            ew = getattr(self, "_roster_expiring_contracts_detail_window", None)
            if ew is not None and ew.winfo_exists():
                ew.destroy()
        except Exception:
            pass
        finally:
            self._roster_expiring_contracts_detail_window = None
            self._roster_expiring_contracts_detail_text = None
        window = getattr(self, "_roster_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._roster_window = None
            self._roster_item_to_player.clear()

    def _all_teams_for_trade_gui(self) -> List[Any]:
        """
        CLI の propose_trade に渡す all_teams と同じ母集団を返す。
        Season.all_teams を最優先し、無ければ leagues 全レベルを併合、最後に _iter_league_teams。
        """
        season = getattr(self, "season", None)
        if season is not None:
            at = getattr(season, "all_teams", None)
            if isinstance(at, list) and at:
                return list(at)
            leagues = self._safe_get(season, "leagues", None)
            if isinstance(leagues, dict) and leagues:
                out: List[Any] = []
                seen: set[int] = set()
                for _lvl in sorted(leagues.keys(), key=lambda k: (not isinstance(k, int), k)):
                    for t in leagues.get(_lvl) or []:
                        tid = id(t)
                        if tid in seen:
                            continue
                        seen.add(tid)
                        out.append(t)
                if out:
                    return out
        return list(self._iter_league_teams())

    def _on_roster_one_for_one_trade(self) -> None:
        """人事用の補助ウィザード（選手のみ1対1）。本線は人事の「トレード」ボタン（同系の評価・実行経路）。"""
        parent = getattr(self, "_roster_window", None) or self.root
        if self.team is None:
            messagebox.showwarning("トレード", "チームが未接続です。", parent=parent)
            return
        if not inseason_roster_moves_unlocked(self.season):
            messagebox.showwarning(
                "トレード",
                INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
                parent=parent,
            )
            return
        all_teams = self._all_teams_for_trade_gui()
        if not all_teams:
            messagebox.showwarning(
                "トレード",
                "リーグのチーム一覧を取得できませんでした。",
                parent=parent,
            )
            return
        from basketball_sim import main as bs_main

        candidates = bs_main.get_trade_candidate_teams(all_teams, self.team)
        if not candidates:
            messagebox.showinfo(
                "トレード",
                "トレード相手となる他クラブがありません。",
                parent=parent,
            )
            return
        self._run_one_for_one_trade_wizard(parent, candidates)

    def _run_one_for_one_trade_wizard(self, parent: Any, trade_candidate_teams: List[Any]) -> None:
        from basketball_sim import main as bs_main
        from basketball_sim.systems.trade_logic import TradeSystem

        user_team = self.team
        top = tk.Toplevel(parent)
        top.title("選手のみ1対1（補助）")
        top.configure(bg="#15171c")
        try:
            top.transient(parent)
        except Exception:
            pass
        top.geometry("520x420")
        top.minsize(440, 360)

        outer = ttk.Frame(top, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="選手のみの 1 対 1（補助）です。現金・RB を伴うトレードは、人事の「トレード」ボタンから同じウィザードで行ってください。",
            wraplength=480,
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 8))

        hint_var = tk.StringVar(value="相手クラブを選び、「次へ」を押してください。")
        ttk.Label(outer, textvariable=hint_var, wraplength=480).pack(fill="x", pady=(0, 6))

        lb_frame = ttk.Frame(outer, style="Panel.TFrame")
        lb_frame.pack(fill="both", expand=True, pady=(0, 8))
        lb_frame.rowconfigure(0, weight=1)
        lb_frame.columnconfigure(0, weight=1)
        listbox = tk.Listbox(
            lb_frame,
            height=12,
            bg="#222834",
            fg="#e8ecf0",
            selectbackground="#3d4f6f",
            font=("Yu Gothic UI", 10),
        )
        vsb = ttk.Scrollbar(lb_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=vsb.set)
        listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        state: Dict[str, Any] = {
            "step": 0,
            "ai_team": None,
            "ai_player": None,
            "user_player": None,
            "items": [],
            "player_source": [],
        }

        _trade_nat_ja = {
            "Japan": "日本",
            "Foreign": "外国籍",
            "Asia": "アジア",
            "Naturalized": "帰化",
        }

        def _one_for_one_trade_player_line(p: Any) -> str:
            nat_key = str(getattr(p, "nationality", "Japan") or "Japan")
            nat_j = _trade_nat_ja.get(nat_key, nat_key)
            sal = int(getattr(p, "salary", 0) or 0)
            return (
                f"{getattr(p, 'name', '?')}  {getattr(p, 'position', '?')}  "
                f"OVR {int(getattr(p, 'ovr', 0) or 0)}  年齢 {int(getattr(p, 'age', 0) or 0)}  "
                f"{nat_j}  年俸 {format_money_yen_ja_readable(sal)}"
            )

        def refresh_list() -> None:
            listbox.delete(0, tk.END)
            state["items"] = []
            state["player_source"] = []
            step = int(state["step"])
            if step == 0:
                for t in trade_candidate_teams:
                    ll = int(self._safe_get(t, "league_level", 0) or 0)
                    w = int(self._safe_get(t, "regular_wins", 0) or 0)
                    l = int(self._safe_get(t, "regular_losses", 0) or 0)
                    nm = str(self._safe_get(t, "name", "?"))
                    listbox.insert(tk.END, f"{nm}  D{ll}  {w}勝{l}敗")
                    state["items"].append(t)
            elif step == 1:
                ai_t = state["ai_team"]
                players = bs_main.get_tradeable_players(ai_t)
                state["player_source"] = players
                for p in players:
                    listbox.insert(tk.END, _one_for_one_trade_player_line(p))
            elif step == 2:
                players = bs_main.get_tradeable_players(user_team)
                state["player_source"] = players
                for p in players:
                    listbox.insert(tk.END, _one_for_one_trade_player_line(p))

        def do_evaluate_and_finish() -> None:
            ts = TradeSystem()
            ut = state["user_player"]
            ap = state["ai_player"]
            at = state["ai_team"]
            user_eval, ai_eval, accepted, reason, _detail = bs_main.one_for_one_trade_evaluate_and_ai_gate(
                ts,
                user_team,
                at,
                ut,
                ap,
            )
            summary = bs_main.format_one_for_one_trade_evaluation_text(user_eval, ai_eval)
            messagebox.showinfo("トレード評価", summary, parent=top)
            if not accepted:
                messagebox.showinfo(
                    "トレード",
                    f"相手クラブが拒否しました。\n{reason}",
                    parent=top,
                )
                top.destroy()
                return
            if not messagebox.askyesno(
                "トレード成立",
                "この内容でトレードを成立させますか？",
                parent=top,
            ):
                top.destroy()
                return
            ok = ts.execute_one_for_one_trade(
                team_a=user_team,
                team_b=at,
                player_a=ut,
                player_b=ap,
            )
            if ok:
                messagebox.showinfo(
                    "トレード",
                    f"成立: {getattr(ut, 'name', '?')} ⇄ {getattr(ap, 'name', '?')}",
                    parent=top,
                )
            else:
                messagebox.showwarning("トレード", "トレード実行に失敗しました。", parent=top)
            top.destroy()
            self._refresh_roster_window()
            try:
                self.refresh()
            except Exception:
                pass

        next_caption_var = tk.StringVar(value="次へ")

        def on_next() -> None:
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("トレード", "一覧から選択してください。", parent=top)
                return
            idx = int(sel[0])
            step = int(state["step"])
            if step == 0:
                state["ai_team"] = state["items"][idx]
                state["step"] = 1
                an = str(getattr(state["ai_team"], "name", "?"))
                hint_var.set(f"「{an}」から獲得する選手を選んでください。")
                next_caption_var.set("次へ")
                refresh_list()
                if not state["player_source"]:
                    messagebox.showinfo(
                        "トレード",
                        f"「{an}」にトレード可能な選手がいません。別のクラブを選んでください。",
                        parent=top,
                    )
                    state["step"] = 0
                    state["ai_team"] = None
                    hint_var.set("相手クラブを選び、「次へ」を押してください。")
                    refresh_list()
                return
            elif step == 1:
                ps = state["player_source"]
                if not ps:
                    messagebox.showinfo("トレード", "相手チームにトレード可能な選手がいません。", parent=top)
                    return
                state["ai_player"] = ps[idx]
                state["step"] = 2
                hint_var.set("自チームから放出する選手を選び、「評価する」を押してください。")
                next_caption_var.set("評価する")
                refresh_list()
                if not state["player_source"]:
                    messagebox.showinfo(
                        "トレード",
                        "自チームにトレード可能な選手がいません。",
                        parent=top,
                    )
                    top.destroy()
                return
            elif step == 2:
                ps = state["player_source"]
                if not ps:
                    messagebox.showinfo("トレード", "自チームにトレード可能な選手がいません。", parent=top)
                    return
                state["user_player"] = ps[idx]
                do_evaluate_and_finish()

        btn_row = ttk.Frame(outer, style="Panel.TFrame")
        btn_row.pack(fill="x")

        def on_cancel() -> None:
            top.destroy()

        self._jpn_text_button(btn_row, "キャンセル", on_cancel, side="left")
        next_btn = tk.Button(
            btn_row,
            textvariable=next_caption_var,
            command=on_next,
            font=("Yu Gothic UI", 10),
            bg="#2d3d52",
            fg="#e8ecf0",
            activebackground="#3d4d62",
            activeforeground="#e8ecf0",
            relief="flat",
            padx=14,
            pady=6,
        )
        next_btn.pack(side="right")

        refresh_list()

    def _on_roster_multi_trade_players_only(self) -> None:
        """人事の「トレード」ボタン: 1〜3名の入替＋現金・RB（双方向）。評価・実行は `TradeSystem` 既存経路。"""
        parent = getattr(self, "_roster_window", None) or self.root
        if self.team is None:
            messagebox.showwarning("トレード", "チームが未接続です。", parent=parent)
            return
        if self.season is None:
            messagebox.showwarning(
                "トレード",
                "シーズン未接続のため FA プールを参照できず、トレードを実行できません。",
                parent=parent,
            )
            return
        if not inseason_roster_moves_unlocked(self.season):
            messagebox.showwarning(
                "トレード",
                INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
                parent=parent,
            )
            return
        fa_list = getattr(self.season, "free_agents", None)
        if fa_list is None:
            messagebox.showwarning(
                "トレード",
                "FA プールが未初期化のためトレードを実行できません。",
                parent=parent,
            )
            return
        all_teams = self._all_teams_for_trade_gui()
        if not all_teams:
            messagebox.showwarning(
                "トレード",
                "リーグのチーム一覧を取得できませんでした。",
                parent=parent,
            )
            return
        from basketball_sim import main as bs_main

        candidates = bs_main.get_trade_candidate_teams(all_teams, self.team)
        if not candidates:
            messagebox.showinfo(
                "トレード",
                "トレード相手となる他クラブがありません。",
                parent=parent,
            )
            return
        self._run_multi_trade_players_only_wizard(parent, candidates, fa_list)

    def _run_multi_trade_players_only_wizard(
        self,
        parent: Any,
        trade_candidate_teams: List[Any],
        free_agents: List[Any],
    ) -> None:
        from basketball_sim import main as bs_main
        from basketball_sim.systems.trade_input_helpers import (
            compose_cash_yen_from_oku_man,
            max_oku_for_cash,
            rb_man_choice_values_filtered,
            rb_yen_from_man,
            valid_cash_man_values_for_oku,
        )
        from basketball_sim.systems.trade_logic import (
            TRADE_RB_TRANSFER_MAX_LEG_YEN,
            TRADE_RB_TRANSFER_STEP_YEN,
            MultiTradeOffer,
            TradeSystem,
        )

        user_team = self.team
        top = tk.Toplevel(parent)
        top.title("トレード（複数人＋現金・RB）")
        top.configure(bg="#15171c")
        try:
            top.transient(parent)
        except Exception:
            pass
        top.geometry("780x620")
        top.minsize(620, 500)

        outer = ttk.Frame(top, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=(
                "複数選手の入替に加え、現金・RB（ルーキー予算）を方向ごとに指定できます（自分→相手／相手→自分）。"
                "現金は「億」＋「万円」、RB はプルダウン（万の数・CLI と同じ刻み）で入力します。"
                f"RB は {format_money_yen_ja_readable(TRADE_RB_TRANSFER_STEP_YEN)} 刻み・"
                f"片道最大 {format_money_yen_ja_readable(TRADE_RB_TRANSFER_MAX_LEG_YEN)}。"
                "評価・成立は `TradeSystem` のトレード処理経路です。"
            ),
            wraplength=640,
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 8))

        hint_var = tk.StringVar(value="相手クラブを選び、「次へ」を押してください。")
        ttk.Label(outer, textvariable=hint_var, wraplength=600).pack(fill="x", pady=(0, 6))

        lb_frame = ttk.Frame(outer, style="Panel.TFrame")
        lb_frame.pack(fill="both", expand=True, pady=(0, 8))
        lb_frame.rowconfigure(0, weight=1)
        lb_frame.columnconfigure(0, weight=1)

        listbox = tk.Listbox(
            lb_frame,
            height=14,
            bg="#222834",
            fg="#e8ecf0",
            selectbackground="#3d4f6f",
            font=("Yu Gothic UI", 10),
            selectmode=tk.BROWSE,
        )
        vsb = ttk.Scrollbar(lb_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=vsb.set)
        listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        count_frame = tk.Frame(lb_frame, bg="#222834")
        tk.Label(
            count_frame,
            text="人数ルール: 自分が出す人数・受け取る人数はそれぞれ 1〜3、差は最大 1（CLI と同一）。",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 9),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 12))
        row_n = tk.Frame(count_frame, bg="#222834")
        row_n.pack(fill="x", padx=8, pady=4)
        tk.Label(row_n, text="自分が出す人数:", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(
            side="left"
        )
        n_out_var = tk.StringVar(value="1")
        sp_out = tk.Spinbox(
            row_n,
            from_=1,
            to=3,
            width=4,
            textvariable=n_out_var,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            buttonbackground="#3d4f6f",
        )
        sp_out.pack(side="left", padx=(8, 24))
        tk.Label(row_n, text="自分が受け取る人数:", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(
            side="left"
        )
        n_in_var = tk.StringVar(value="1")
        sp_in = tk.Spinbox(
            row_n,
            from_=1,
            to=3,
            width=4,
            textvariable=n_in_var,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            buttonbackground="#3d4f6f",
        )
        sp_in.pack(side="left", padx=(8, 0))
        count_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        count_frame.grid_remove()

        money_rb_frame = tk.Frame(lb_frame, bg="#222834")
        _trade_cash_max = {"a": 0, "b": 0}
        tk.Label(
            money_rb_frame,
            text=(
                "現金は「億」＋「万円」（万は 0/1000/…/9000 の 1000万円刻み）。"
                f"RB は万の数で {format_money_yen_ja_readable(TRADE_RB_TRANSFER_STEP_YEN)} 刻み（プルダウン）。"
                "各方向の上限はクラブの所持金・RB 残高です。"
            ),
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 9),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 6))
        cash_limit_var = tk.StringVar(value="")
        cash_b_limit_var = tk.StringVar(value="")
        rb_limit_var = tk.StringVar(value="")
        rb_b_limit_var = tk.StringVar(value="")
        tk.Label(
            money_rb_frame,
            textvariable=cash_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(0, 2))
        row_cash = tk.Frame(money_rb_frame, bg="#222834")
        row_cash.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_cash,
            text="現金（自分→相手）",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10, "bold"),
            width=16,
            anchor="w",
        ).pack(side="left")
        cash_a_oku_var = tk.StringVar(value="0")
        tk.Label(row_cash, text="億", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(
            side="left", padx=(8, 2)
        )
        cash_a_oku_sp = tk.Spinbox(
            row_cash,
            from_=0,
            to=0,
            width=4,
            textvariable=cash_a_oku_var,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            buttonbackground="#3d4f6f",
        )
        cash_a_oku_sp.pack(side="left", padx=(0, 6))
        tk.Label(row_cash, text="万円", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(side="left")
        cash_a_man_cb = ttk.Combobox(
            row_cash,
            width=10,
            state="readonly",
            font=("Yu Gothic UI", 10),
            values=("0",),
        )
        cash_a_man_cb.set("0")
        cash_a_man_cb.pack(side="left", padx=(6, 8))
        tk.Label(
            row_cash,
            text="（0/1000/…/9000）",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")

        def _sync_cash_a_side(*_args: Any) -> None:
            max_y = int(_trade_cash_max["a"] or 0)
            mo = max_oku_for_cash(max_y)
            try:
                oku = int(float(str(cash_a_oku_var.get()).strip() or "0"))
            except (TypeError, ValueError):
                oku = 0
            oku = max(0, min(oku, mo))
            if str(oku) != str(cash_a_oku_var.get()).strip():
                cash_a_oku_var.set(str(oku))
                return
            cash_a_oku_sp.config(from_=0, to=mo)
            ch = valid_cash_man_values_for_oku(max_y, oku)
            vals = [str(x) for x in ch]
            cash_a_man_cb["values"] = tuple(vals)
            cur = str(cash_a_man_cb.get()).strip()
            if cur not in vals and vals:
                cash_a_man_cb.set(vals[0])

        cash_a_oku_var.trace_add("write", lambda *_a: _sync_cash_a_side())
        cash_a_oku_sp.bind("<FocusOut>", _sync_cash_a_side)
        cash_a_oku_sp.bind("<ButtonRelease-1>", _sync_cash_a_side)

        tk.Label(
            money_rb_frame,
            textvariable=cash_b_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(6, 2))
        row_cash_b = tk.Frame(money_rb_frame, bg="#222834")
        row_cash_b.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_cash_b,
            text="現金（相手→自分）",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10, "bold"),
            width=16,
            anchor="w",
        ).pack(side="left")
        cash_b_oku_var = tk.StringVar(value="0")
        tk.Label(row_cash_b, text="億", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(
            side="left", padx=(8, 2)
        )
        cash_b_oku_sp = tk.Spinbox(
            row_cash_b,
            from_=0,
            to=0,
            width=4,
            textvariable=cash_b_oku_var,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            buttonbackground="#3d4f6f",
        )
        cash_b_oku_sp.pack(side="left", padx=(0, 6))
        tk.Label(row_cash_b, text="万円", bg="#222834", fg="#e8ecf0", font=("Yu Gothic UI", 10)).pack(side="left")
        cash_b_man_cb = ttk.Combobox(
            row_cash_b,
            width=10,
            state="readonly",
            font=("Yu Gothic UI", 10),
            values=("0",),
        )
        cash_b_man_cb.set("0")
        cash_b_man_cb.pack(side="left", padx=(6, 8))
        tk.Label(
            row_cash_b,
            text="（0/1000/…/9000）",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")

        def _sync_cash_b_side(*_args: Any) -> None:
            max_y = int(_trade_cash_max["b"] or 0)
            mo = max_oku_for_cash(max_y)
            try:
                oku = int(float(str(cash_b_oku_var.get()).strip() or "0"))
            except (TypeError, ValueError):
                oku = 0
            oku = max(0, min(oku, mo))
            if str(oku) != str(cash_b_oku_var.get()).strip():
                cash_b_oku_var.set(str(oku))
                return
            cash_b_oku_sp.config(from_=0, to=mo)
            ch = valid_cash_man_values_for_oku(max_y, oku)
            vals = [str(x) for x in ch]
            cash_b_man_cb["values"] = tuple(vals)
            cur = str(cash_b_man_cb.get()).strip()
            if cur not in vals and vals:
                cash_b_man_cb.set(vals[0])

        cash_b_oku_var.trace_add("write", lambda *_a: _sync_cash_b_side())
        cash_b_oku_sp.bind("<FocusOut>", _sync_cash_b_side)
        cash_b_oku_sp.bind("<ButtonRelease-1>", _sync_cash_b_side)

        tk.Label(
            money_rb_frame,
            textvariable=rb_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 2))
        row_rb = tk.Frame(money_rb_frame, bg="#222834")
        row_rb.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_rb,
            text="RB（自分→相手） 万の数",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10),
            width=22,
            anchor="w",
        ).pack(side="left")
        rb_a_cb = ttk.Combobox(
            row_rb,
            width=12,
            state="readonly",
            font=("Yu Gothic UI", 10),
            values=("0",),
        )
        rb_a_cb.set("0")
        rb_a_cb.pack(side="left", padx=(0, 8))
        tk.Label(
            row_rb,
            text="（500万円刻み）",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")

        tk.Label(
            money_rb_frame,
            textvariable=rb_b_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(6, 2))
        row_rb_b = tk.Frame(money_rb_frame, bg="#222834")
        row_rb_b.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_rb_b,
            text="RB（相手→自分） 万の数",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10),
            width=22,
            anchor="w",
        ).pack(side="left")
        rb_b_cb = ttk.Combobox(
            row_rb_b,
            width=12,
            state="readonly",
            font=("Yu Gothic UI", 10),
            values=("0",),
        )
        rb_b_cb.set("0")
        rb_b_cb.pack(side="left", padx=(0, 8))
        tk.Label(
            row_rb_b,
            text="（500万円刻み）",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")

        def _rebuild_rb_combo(cb: ttk.Combobox, max_rb_yen: int) -> None:
            mans = rb_man_choice_values_filtered(max_rb_yen)
            vals = tuple(str(m) for m in mans)
            cb["values"] = vals
            cur = str(cb.get()).strip()
            if cur not in vals and vals:
                cb.set(vals[0])

        money_rb_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        money_rb_frame.grid_remove()

        state: Dict[str, Any] = {
            "step": 0,
            "ai_team": None,
            "n_out": 1,
            "n_in": 1,
            "ai_receives": [],
            "user_gives": [],
            "cash_a_to_b": 0,
            "cash_b_to_a": 0,
            "rookie_budget_a_to_b": 0,
            "rookie_budget_b_to_a": 0,
            "items": [],
            "player_source": [],
        }

        _trade_nat_ja = {
            "Japan": "日本",
            "Foreign": "外国籍",
            "Asia": "アジア",
            "Naturalized": "帰化",
        }

        def _multi_trade_player_line(p: Any) -> str:
            nat_key = str(getattr(p, "nationality", "Japan") or "Japan")
            nat_j = _trade_nat_ja.get(nat_key, nat_key)
            sal = int(getattr(p, "salary", 0) or 0)
            return (
                f"{getattr(p, 'name', '?')}  {getattr(p, 'position', '?')}  "
                f"OVR {int(getattr(p, 'ovr', 0) or 0)}  年齢 {int(getattr(p, 'age', 0) or 0)}  "
                f"{nat_j}  年俸 {format_money_yen_ja_readable(sal)}"
            )

        def set_center_pane(mode: str) -> None:
            count_frame.grid_remove()
            money_rb_frame.grid_remove()
            listbox.grid_remove()
            vsb.grid_remove()
            if mode == "list":
                listbox.grid(row=0, column=0, sticky="nsew")
                vsb.grid(row=0, column=1, sticky="ns")
            elif mode == "count":
                count_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
            elif mode == "cash_rb":
                money_rb_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

        def refresh_list() -> None:
            step = int(state["step"])
            if step in (1, 4):
                return
            listbox.delete(0, tk.END)
            state["items"] = []
            state["player_source"] = []
            if step <= 1:
                listbox.configure(selectmode=tk.BROWSE)
            else:
                listbox.configure(selectmode=tk.EXTENDED)
            if step == 0:
                for t in trade_candidate_teams:
                    ll = int(self._safe_get(t, "league_level", 0) or 0)
                    w = int(self._safe_get(t, "regular_wins", 0) or 0)
                    lo = int(self._safe_get(t, "regular_losses", 0) or 0)
                    nm = str(self._safe_get(t, "name", "?"))
                    listbox.insert(tk.END, f"{nm}  D{ll}  {w}勝{lo}敗")
                    state["items"].append(t)
            elif step == 2:
                ai_t = state["ai_team"]
                players = bs_main.get_tradeable_players(ai_t)
                state["player_source"] = players
                for p in players:
                    listbox.insert(tk.END, _multi_trade_player_line(p))
            elif step == 3:
                players = bs_main.get_tradeable_players(user_team)
                state["player_source"] = players
                for p in players:
                    listbox.insert(tk.END, _multi_trade_player_line(p))

        def pick_multi(required: int) -> Optional[List[Any]]:
            sel = listbox.curselection()
            if len(sel) != required:
                messagebox.showinfo(
                    "トレード",
                    f"ちょうど {required} 名を選んでください（Ctrl+クリックで複数選択）。",
                    parent=top,
                )
                return None
            ps = state["player_source"]
            return [ps[int(i)] for i in sel]

        def do_evaluate_and_finish_multi() -> None:
            at = state["ai_team"]
            user_gives: List[Any] = list(state["user_gives"])
            ai_receives: List[Any] = list(state["ai_receives"])
            cash_amt = int(state.get("cash_a_to_b", 0) or 0)
            cash_b_amt = int(state.get("cash_b_to_a", 0) or 0)
            rb_amt = int(state.get("rookie_budget_a_to_b", 0) or 0)
            rb_b_amt = int(state.get("rookie_budget_b_to_a", 0) or 0)
            offer = MultiTradeOffer(
                team_a_gives_players=user_gives,
                team_a_receives_players=ai_receives,
                cash_a_to_b=cash_amt,
                cash_b_to_a=cash_b_amt,
                rookie_budget_a_to_b=rb_amt,
                rookie_budget_b_to_a=rb_b_amt,
            )
            ts = TradeSystem()
            user_eval, ai_eval = ts.evaluate_multi_trade(user_team, at, offer)
            summary = bs_main.format_one_for_one_trade_evaluation_text(user_eval, ai_eval)
            messagebox.showinfo("トレード評価", summary, parent=top)
            accepted, reason, _ae2 = ts.should_ai_accept_multi_trade(user_team, at, offer)
            if not accepted:
                messagebox.showinfo(
                    "トレード",
                    f"相手クラブが拒否しました。\n{reason}",
                    parent=top,
                )
                top.destroy()
                return
            pay_preview = ""
            if cash_amt > 0:
                pay_preview += f"\n現金（自分→相手）: {format_money_yen_ja_readable(cash_amt)}"
            if cash_b_amt > 0:
                pay_preview += f"\n現金（相手→自分）: {format_money_yen_ja_readable(cash_b_amt)}"
            if rb_amt > 0:
                pay_preview += f"\nRB（自分→相手）: {format_money_yen_ja_readable(rb_amt)}"
            if rb_b_amt > 0:
                pay_preview += f"\nRB（相手→自分）: {format_money_yen_ja_readable(rb_b_amt)}"
            if not messagebox.askyesno(
                "トレード成立",
                "この内容でトレードを成立させますか？" + pay_preview,
                parent=top,
            ):
                top.destroy()
                return
            ok = ts.execute_multi_trade(
                team_a=user_team,
                team_b=at,
                offer=offer,
                free_agents=free_agents,
            )
            if ok:
                ug = ", ".join(getattr(p, "name", "?") for p in user_gives)
                ar = ", ".join(getattr(p, "name", "?") for p in ai_receives)
                pay_lines = ""
                if cash_amt > 0:
                    pay_lines += f"\n現金（自分→相手）: {format_money_yen_ja_readable(cash_amt)}"
                if cash_b_amt > 0:
                    pay_lines += f"\n現金（相手→自分）: {format_money_yen_ja_readable(cash_b_amt)}"
                if rb_amt > 0:
                    pay_lines += f"\nRB（自分→相手）: {format_money_yen_ja_readable(rb_amt)}"
                if rb_b_amt > 0:
                    pay_lines += f"\nRB（相手→自分）: {format_money_yen_ja_readable(rb_b_amt)}"
                messagebox.showinfo(
                    "トレード",
                    f"成立: {ug} を放出 / {ar} を獲得{pay_lines}",
                    parent=top,
                )
            else:
                messagebox.showwarning(
                    "トレード",
                    "トレード実行に失敗しました（ロスター・上限・国籍等の制約）。",
                    parent=top,
                )
            top.destroy()
            self._refresh_roster_window()
            try:
                self.refresh()
            except Exception:
                pass

        next_caption_var = tk.StringVar(value="次へ")

        def on_next() -> None:
            step = int(state["step"])
            if step == 0:
                sel = listbox.curselection()
                if not sel:
                    messagebox.showinfo("トレード", "一覧から選択してください。", parent=top)
                    return
                idx = int(sel[0])
                state["ai_team"] = state["items"][idx]
                state["step"] = 1
                an = str(getattr(state["ai_team"], "name", "?"))
                hint_var.set(f"「{an}」との人数を指定してください。")
                set_center_pane("count")
                next_caption_var.set("次へ")
                return
            if step == 1:
                try:
                    n_out = int(str(n_out_var.get()).strip())
                    n_in = int(str(n_in_var.get()).strip())
                except ValueError:
                    messagebox.showinfo("トレード", "人数は 1〜3 の整数で指定してください。", parent=top)
                    return
                okc, cmsg = bs_main.validate_multi_trade_player_counts(n_out, n_in)
                if not okc:
                    messagebox.showwarning("トレード", cmsg, parent=top)
                    return
                user_players = bs_main.get_tradeable_players(user_team)
                ai_players = bs_main.get_tradeable_players(state["ai_team"])
                if len(user_players) < n_out:
                    messagebox.showwarning(
                        "トレード",
                        f"放出候補が足りません（必要: {n_out} 名、候補: {len(user_players)} 名）。",
                        parent=top,
                    )
                    return
                if len(ai_players) < n_in:
                    messagebox.showwarning(
                        "トレード",
                        f"相手のトレード候補が足りません（必要: {n_in} 名、候補: {len(ai_players)} 名）。",
                        parent=top,
                    )
                    return
                state["n_out"] = n_out
                state["n_in"] = n_in
                state["step"] = 2
                set_center_pane("list")
                hint_var.set(
                    f"相手から {n_in} 名を、Ctrl+クリックで選んで「次へ」してください。"
                )
                next_caption_var.set("次へ")
                refresh_list()
                return
            if step == 2:
                picked = pick_multi(int(state["n_in"]))
                if picked is None:
                    return
                state["ai_receives"] = picked
                state["step"] = 3
                hint_var.set(
                    f"自チームから {int(state['n_out'])} 名を選び、「次へ」を押してください。"
                )
                next_caption_var.set("次へ")
                refresh_list()
                return
            if step == 3:
                picked = pick_multi(int(state["n_out"]))
                if picked is None:
                    return
                state["user_gives"] = picked
                at = state["ai_team"]
                max_cash = max(0, int(getattr(user_team, "money", 0) or 0))
                max_rb = max(0, int(getattr(user_team, "rookie_budget_remaining", 0) or 0))
                max_cash_b = max(0, int(getattr(at, "money", 0) or 0))
                max_rb_b = max(0, int(getattr(at, "rookie_budget_remaining", 0) or 0))
                _trade_cash_max["a"] = max_cash
                _trade_cash_max["b"] = max_cash_b
                cash_limit_var.set(
                    f"自分側 現金上限: 0〜{format_money_yen_ja_readable(max_cash)}"
                )
                cash_b_limit_var.set(
                    f"相手側 現金上限: 0〜{format_money_yen_ja_readable(max_cash_b)}（相手→自分）"
                )
                rb_limit_var.set(f"自分側 RB 上限: 0〜{format_money_yen_ja_readable(max_rb)}")
                rb_b_limit_var.set(f"相手側 RB 上限: 0〜{format_money_yen_ja_readable(max_rb_b)}（相手→自分）")
                cash_a_oku_var.set("0")
                cash_b_oku_var.set("0")
                _sync_cash_a_side()
                _sync_cash_b_side()
                _rebuild_rb_combo(rb_a_cb, max_rb)
                _rebuild_rb_combo(rb_b_cb, max_rb_b)
                rb_a_cb.set("0")
                rb_b_cb.set("0")
                state["step"] = 4
                set_center_pane("cash_rb")
                hint_var.set(
                    "現金は億＋万円、RB はプルダウン（万の数）で指定し、「評価する」を押してください。"
                )
                next_caption_var.set("評価する")
                return
            if step == 4:
                at = state["ai_team"]
                max_cash = max(0, int(getattr(user_team, "money", 0) or 0))
                max_rb = max(0, int(getattr(user_team, "rookie_budget_remaining", 0) or 0))
                max_cash_b = max(0, int(getattr(at, "money", 0) or 0))
                max_rb_b = max(0, int(getattr(at, "rookie_budget_remaining", 0) or 0))
                try:
                    oku_a = int(float(str(cash_a_oku_var.get()).strip() or "0"))
                except (TypeError, ValueError):
                    oku_a = 0
                try:
                    man_a = int(float(str(cash_a_man_cb.get()).strip() or "0"))
                except (TypeError, ValueError):
                    man_a = 0
                yen_a = compose_cash_yen_from_oku_man(oku_a, man_a)
                ok_c, cash_v, msg_c = bs_main.parse_multi_trade_side_payment(
                    str(yen_a),
                    max_cash,
                    is_cash=True,
                )
                if not ok_c:
                    messagebox.showwarning("トレード", msg_c, parent=top)
                    return
                try:
                    oku_b = int(float(str(cash_b_oku_var.get()).strip() or "0"))
                except (TypeError, ValueError):
                    oku_b = 0
                try:
                    man_b = int(float(str(cash_b_man_cb.get()).strip() or "0"))
                except (TypeError, ValueError):
                    man_b = 0
                yen_b = compose_cash_yen_from_oku_man(oku_b, man_b)
                ok_cb, cash_b_v, msg_cb = bs_main.parse_multi_trade_side_payment(
                    str(yen_b),
                    max_cash_b,
                    is_cash=True,
                )
                if not ok_cb:
                    messagebox.showwarning("トレード", msg_cb, parent=top)
                    return
                try:
                    rb_man_a = int(float(str(rb_a_cb.get()).strip() or "0"))
                except (TypeError, ValueError):
                    rb_man_a = 0
                yen_rb_a = rb_yen_from_man(rb_man_a)
                ok_r, rb_v, msg_r = bs_main.parse_multi_trade_side_payment(
                    str(yen_rb_a),
                    max_rb,
                    is_cash=False,
                )
                if not ok_r:
                    messagebox.showwarning("トレード", msg_r, parent=top)
                    return
                try:
                    rb_man_b = int(float(str(rb_b_cb.get()).strip() or "0"))
                except (TypeError, ValueError):
                    rb_man_b = 0
                yen_rb_b = rb_yen_from_man(rb_man_b)
                ok_rb, rb_b_v, msg_rb = bs_main.parse_multi_trade_side_payment(
                    str(yen_rb_b),
                    max_rb_b,
                    is_cash=False,
                )
                if not ok_rb:
                    messagebox.showwarning("トレード", msg_rb, parent=top)
                    return
                state["cash_a_to_b"] = cash_v
                state["cash_b_to_a"] = cash_b_v
                state["rookie_budget_a_to_b"] = rb_v
                state["rookie_budget_b_to_a"] = rb_b_v
                do_evaluate_and_finish_multi()
                return

        btn_row = ttk.Frame(outer, style="Panel.TFrame")
        btn_row.pack(fill="x")

        def on_cancel() -> None:
            top.destroy()

        self._jpn_text_button(btn_row, "キャンセル", on_cancel, side="left")
        next_btn = tk.Button(
            btn_row,
            textvariable=next_caption_var,
            command=on_next,
            font=("Yu Gothic UI", 10),
            bg="#2d3d52",
            fg="#e8ecf0",
            activebackground="#3d4d62",
            activeforeground="#e8ecf0",
            relief="flat",
            padx=14,
            pady=6,
        )
        next_btn.pack(side="right")

        refresh_list()

    def _on_roster_inseason_fa_one(self) -> None:
        """人事から FA プールを一覧し、1 人だけ `sign_free_agent` で獲得する最小ウィザード。"""
        parent = getattr(self, "_roster_window", None) or self.root
        if self.team is None:
            messagebox.showwarning("インシーズンFA", "チームが未接続です。", parent=parent)
            return
        if self.season is None:
            messagebox.showwarning(
                "インシーズンFA",
                "シーズン未接続のため FA プールを参照できません。",
                parent=parent,
            )
            return
        if not inseason_roster_moves_unlocked(self.season):
            messagebox.showwarning(
                "インシーズンFA",
                INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
                parent=parent,
            )
            return
        self._run_inseason_fa_one_wizard(parent)

    def _run_inseason_fa_one_wizard(self, parent: Any) -> None:
        from basketball_sim.systems.free_agent_market import (
            ensure_fa_market_fields,
            ensure_team_fa_market_fields,
            estimate_fa_contract_years,
            get_team_fa_signing_limit,
            inseason_fa_contract_salary,
            normalize_free_agents,
            precheck_user_fa_sign,
            sign_free_agent,
        )
        from basketball_sim.systems.roster_rules import RosterViolationError
        from basketball_sim.systems.salary_cap_budget import league_level_for_team

        team = self.team
        season = self.season
        assert team is not None and season is not None

        _league_market_division = int(league_level_for_team(team))

        raw = list(getattr(season, "free_agents", []) or [])
        candidates = normalize_free_agents(
            raw, league_market_division=_league_market_division
        )
        candidates.sort(
            key=lambda p: (-int(getattr(p, "ovr", 0) or 0), str(getattr(p, "name", "")))
        )

        _fa_nat_ja = {
            "Japan": "日本",
            "Foreign": "外国籍",
            "Asia": "アジア",
            "Naturalized": "帰化",
        }

        top = tk.Toplevel(parent)
        top.title("インシーズンFA（1人）")
        top.configure(bg="#15171c")
        try:
            top.transient(parent)
        except Exception:
            pass
        top.geometry("780x460")
        top.minsize(640, 380)

        outer = ttk.Frame(top, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="FA プールから 1 人を選び契約します。年俸は市場目安が自動適用されます（交渉・金額入力なし）。",
            wraplength=720,
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 6))

        hint_var = tk.StringVar(value="一覧から選手を選び、「制限を確認」→ 問題なければ「契約する」。")
        ttk.Label(outer, textvariable=hint_var, wraplength=720).pack(fill="x", pady=(0, 6))

        tree_fr = ttk.Frame(outer, style="Panel.TFrame")
        tree_fr.pack(fill="both", expand=True, pady=(0, 8))
        tree_fr.rowconfigure(0, weight=1)
        tree_fr.columnconfigure(0, weight=1)

        cols = ("name", "pos", "ovr", "age", "nat", "salary")
        tv = ttk.Treeview(
            tree_fr,
            columns=cols,
            show="headings",
            height=12,
            selectmode="browse",
        )
        tv.heading("name", text="選手名")
        tv.heading("pos", text="POS")
        tv.heading("ovr", text="OVR")
        tv.heading("age", text="年齢")
        tv.heading("nat", text="国籍区分")
        tv.heading("salary", text="年俸目安")
        tv.column("name", width=200, stretch=True)
        tv.column("pos", width=44, stretch=False)
        tv.column("ovr", width=48, stretch=False)
        tv.column("age", width=48, stretch=False)
        tv.column("nat", width=72, stretch=False)
        tv.column("salary", width=120, stretch=False)

        vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        item_to_player: Dict[str, Any] = {}
        for p in candidates:
            ensure_fa_market_fields(p, league_market_division=_league_market_division)
            pid = getattr(p, "player_id", None)
            iid = str(pid) if pid is not None else f"id_{id(p)}"
            item_to_player[iid] = p
            nat_key = str(getattr(p, "nationality", "Japan") or "Japan")
            nat_j = _fa_nat_ja.get(nat_key, nat_key)
            est = int(inseason_fa_contract_salary(team, p))
            tv.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    str(getattr(p, "name", "?")),
                    str(getattr(p, "position", "?")),
                    int(getattr(p, "ovr", 0) or 0),
                    int(getattr(p, "age", 0) or 0),
                    nat_j,
                    format_money_yen_ja_readable(est),
                ),
            )

        status_var = tk.StringVar(value="")
        ttk.Label(outer, textvariable=status_var, wraplength=720).pack(fill="x", pady=(0, 4))

        if not candidates:
            hint_var.set("FA プールに契約可能な選手がいません。")

        def _selected_player() -> Optional[Any]:
            sel = tv.selection()
            if not sel:
                return None
            return item_to_player.get(str(sel[0]))

        def on_check() -> None:
            player = _selected_player()
            if player is None:
                messagebox.showinfo("インシーズンFA", "一覧から選手を選択してください。", parent=top)
                return
            ensure_team_fa_market_fields(team)
            ensure_fa_market_fields(player, league_market_division=_league_market_division)
            sal = int(inseason_fa_contract_salary(team, player))
            yrs = int(estimate_fa_contract_years(player))
            room = int(get_team_fa_signing_limit(team))
            money = int(getattr(team, "money", 0) or 0)
            ok, reason = precheck_user_fa_sign(team, player)
            nm = str(getattr(player, "name", "?"))
            if ok:
                status_var.set(f"「{nm}」: 契約可能（確認済み）。")
                messagebox.showinfo(
                    "インシーズンFA（制限確認）",
                    f"選手: {nm}\n"
                    f"年俸目安: {format_money_yen_ja_readable(sal)}\n"
                    f"契約年数: {yrs} 年\n"
                    f"サラリー契約余地: {format_money_yen_ja_readable(room)}\n"
                    f"所持金: {format_money_yen_ja_readable(money)}\n\n"
                    "上記条件で契約できます。「契約する」で確定してください。",
                    parent=top,
                )
            else:
                status_var.set(f"「{nm}」: 契約不可 — {reason}")
                messagebox.showwarning(
                    "インシーズンFA（制限確認）",
                    f"選手: {nm}\n"
                    f"年俸目安: {format_money_yen_ja_readable(sal)}\n"
                    f"サラリー契約余地: {format_money_yen_ja_readable(room)}\n"
                    f"所持金: {format_money_yen_ja_readable(money)}\n\n"
                    f"契約できません: {reason}",
                    parent=top,
                )

        def on_sign() -> None:
            player = _selected_player()
            if player is None:
                messagebox.showinfo("インシーズンFA", "一覧から選手を選択してください。", parent=top)
                return
            ok, reason = precheck_user_fa_sign(team, player)
            nm = str(getattr(player, "name", "?"))
            if not ok:
                messagebox.showwarning("インシーズンFA", reason, parent=top)
                return
            sal = int(inseason_fa_contract_salary(team, player))
            yrs = int(estimate_fa_contract_years(player))
            if not messagebox.askyesno(
                "インシーズンFA（最終確認）",
                f"{nm} と契約しますか？\n\n年俸目安 {format_money_yen_ja_readable(sal)} / {yrs} 年\n"
                "（標準の FA 契約処理で反映。所持金の即時減算はありません。）",
                parent=top,
            ):
                return
            try:
                sign_free_agent(team, player)
            except RosterViolationError as exc:
                messagebox.showwarning("インシーズンFA", str(exc), parent=top)
                return
            roster = list(getattr(team, "players", []) or [])
            if player not in roster:
                messagebox.showwarning(
                    "インシーズンFA",
                    "契約の反映に失敗しました（ルールにより見送られた可能性があります）。",
                    parent=top,
                )
                return
            fa_list = getattr(season, "free_agents", None)
            if fa_list is not None:
                if player in fa_list:
                    fa_list.remove(player)
                else:
                    pid = getattr(player, "player_id", None)
                    if pid is not None:
                        for fp in list(fa_list):
                            if getattr(fp, "player_id", None) == pid:
                                fa_list.remove(fp)
                                break
            messagebox.showinfo(
                "インシーズンFA",
                f"{nm} を獲得しました。ロスターに反映済みです。",
                parent=top,
            )
            top.destroy()
            self._refresh_roster_window()
            try:
                self.refresh()
            except Exception:
                pass

        btn_row = ttk.Frame(outer, style="Panel.TFrame")
        btn_row.pack(fill="x")

        def on_close() -> None:
            top.destroy()

        self._jpn_text_button(btn_row, "閉じる", on_close, side="left")
        self._jpn_text_button(btn_row, "制限を確認", on_check, side="right", padx=(8, 0))
        self._jpn_text_button(btn_row, "契約する", on_sign, side="right", primary=True)

    def _on_roster_extend_one_year_selected(self) -> None:
        """contract_logic.apply_contract_extension を GUI から1回だけ適用（年俸据え置き）。"""
        parent = getattr(self, "_roster_window", None) or self.root
        tree = getattr(self, "roster_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("人事", "一覧から選手を選択してください。", parent=parent)
            return
        player = self._roster_item_to_player.get(sel[0])
        if player is None:
            messagebox.showwarning(
                "人事",
                "選択の解決に失敗しました。一度閉じて開き直してください。",
                parent=parent,
            )
            return
        team = self.team
        if team is None:
            messagebox.showwarning("人事", "チームが未接続です。", parent=parent)
            return
        roster = list(self._safe_get(team, "players", []) or [])
        if player not in roster:
            messagebox.showwarning("人事", "当チームのロスターにいない選手です。", parent=parent)
            return
        cur = int(getattr(player, "contract_years_left", 0) or 0)
        if cur <= 0:
            messagebox.showwarning(
                "人事",
                "残契約年数がないため延長できません。",
                parent=parent,
            )
            return
        if is_draft_rookie_contract_active(player):
            messagebox.showwarning(
                "人事",
                "オークション指名の固定3年契約中は、ここから契約年数の延長はできません。",
                parent=parent,
            )
            return
        if cur >= MAX_CONTRACT_YEARS_DEFAULT:
            messagebox.showwarning(
                "人事",
                f"残年数が上限（{MAX_CONTRACT_YEARS_DEFAULT} 年）に達しているため、これ以上の延長はできません。",
                parent=parent,
            )
            return
        name = str(getattr(player, "name", "選手"))
        if not messagebox.askyesno(
            "人事",
            f"{name} の契約を 1 年延長しますか？（年俸・役割は据え置き）",
            parent=parent,
        ):
            return
        apply_contract_extension(team, player, add_years=1)
        add_hist = getattr(team, "add_history_transaction", None)
        if callable(add_hist):
            try:
                add_hist("gui_extension", player, "GUI人事：契約＋1年")
            except Exception:
                pass
        messagebox.showinfo("人事", f"{name} の契約を 1 年延長しました。", parent=parent)
        self._refresh_roster_window()
        try:
            self.refresh()
        except Exception:
            pass

    def _on_roster_release_selected(self) -> None:
        parent = getattr(self, "_roster_window", None) or self.root
        tree = getattr(self, "roster_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("人事", "一覧から選手を選択してください。", parent=parent)
            return
        player = self._roster_item_to_player.get(sel[0])
        if player is None:
            messagebox.showwarning(
                "人事",
                "選択の解決に失敗しました。一度閉じて開き直してください。",
                parent=parent,
            )
            return
        block = precheck_release_player_to_fa(self.team, player, self.season)
        if block:
            messagebox.showwarning(block[0], block[1], parent=parent)
            return
        name = str(getattr(player, "name", "選手"))
        if not messagebox.askyesno(
            "人事",
            f"{name} を契約解除し、フリーエージェントに送りますか？",
            parent=parent,
        ):
            return
        block2 = postcheck_release_player_to_fa_season(self.season)
        if block2:
            messagebox.showwarning(block2[0], block2[1], parent=parent)
            return
        fa_list = getattr(self.season, "free_agents", [])
        apply_release_player_to_fa(self.team, player, fa_list)
        messagebox.showinfo(
            "人事",
            f"{name} を契約解除しました。\nロスターから外れ、FAプールに追加しました。",
            parent=parent,
        )
        self._refresh_roster_window()
        try:
            self.refresh()
        except Exception:
            pass

    def _refresh_roster_window(self) -> None:
        tree = getattr(self, "roster_tree", None)
        if tree is None:
            return

        try:
            for item in tree.get_children():
                tree.delete(item)
        except Exception:
            return

        self._roster_item_to_player.clear()

        players = list(self._safe_get(self.team, "players", []) or [])
        players_sorted = sort_roster_for_gm_view(players)

        starters = self._get_starting_five_players()
        sixth_man = self._get_sixth_man_player()
        bench_order = self._get_bench_order_players()

        starter_ids = {getattr(p, "player_id", None) for p in starters}
        starter_ids.discard(None)
        sixth_id = getattr(sixth_man, "player_id", None) if sixth_man is not None else None
        bench_order_rank = {
            getattr(p, "player_id", None): idx + 1
            for idx, p in enumerate(bench_order)
            if getattr(p, "player_id", None) is not None
        }

        for player in players_sorted:
            pid = getattr(player, "player_id", None)
            role = "控え"
            if pid is not None and pid in starter_ids:
                role = "先発"
            elif sixth_id is not None and pid == sixth_id:
                role = "6th"
            elif pid is not None and pid in bench_order_rank:
                role = f"控え{bench_order_rank[pid]}"

            name = str(self._safe_get(player, "name", "-"))
            pos = str(self._safe_get(player, "position", "-"))
            ovr = str(self._safe_get(player, "ovr", "-"))
            pot = str(self._safe_get(player, "potential", "-"))
            age = str(self._safe_get(player, "age", "-"))
            fatigue = str(self._safe_get(player, "fatigue", "-"))
            morale = str(self._safe_get(player, "morale", "-"))
            salary = self._format_money(self._safe_get(player, "salary", 0))
            years = str(self._safe_get(player, "contract_years_left", "-"))
            nat_lbl = jp_reg_display.get_player_nationality_bucket_label(player)

            iid = tree.insert(
                "",
                "end",
                values=(role, name, pos, ovr, pot, age, nat_lbl, fatigue, morale, salary, years),
            )
            self._roster_item_to_player[iid] = player

        team_name = self._team_name()
        count = len(players_sorted)
        avg_ovr = 0.0
        if count > 0:
            avg_ovr = sum(int(self._safe_get(p, "ovr", 0) or 0) for p in players_sorted) / count

        rs = getattr(self, "roster_situation_var", None)
        if rs is not None:
            if self.team is not None:
                try:
                    rs.set(
                        self._build_roster_situation_block_text(
                            team_name, count, players_sorted, avg_ovr
                        )
                    )
                except Exception:
                    rs.set("")
            else:
                rs.set("")
        self.roster_hint_var.set("補足：詳細説明は各詳細ボタンから確認できます。")

        exp_var = getattr(self, "roster_expiring_var", None)
        if exp_var is not None:
            try:
                exp_var.set(self._format_expiring_contracts_summary_text())
            except Exception:
                exp_var.set("今オフ契約満了候補：—")

        summary_var = getattr(self, "roster_trade_fa_summary_var", None)
        if summary_var is not None:
            summary_var.set(self._build_roster_trade_fa_guidance_summary_text())
        try:
            if getattr(self, "_roster_trade_fa_guidance_detail_window", None) is not None:
                gw = self._roster_trade_fa_guidance_detail_window
                if gw is not None and gw.winfo_exists():
                    self._refresh_roster_trade_fa_guidance_detail_body()
        except Exception:
            pass
        try:
            if getattr(self, "_roster_gm_text_list_detail_window", None) is not None:
                dl = self._roster_gm_text_list_detail_window
                if dl is not None and dl.winfo_exists():
                    self._refresh_roster_gm_text_list_detail_body()
        except Exception:
            pass
        try:
            if getattr(self, "_roster_hr_rules_detail_window", None) is not None:
                hr = self._roster_hr_rules_detail_window
                if hr is not None and hr.winfo_exists():
                    self._refresh_roster_hr_rules_detail_body()
        except Exception:
            pass
        try:
            if getattr(self, "_roster_expiring_contracts_detail_window", None) is not None:
                ew = self._roster_expiring_contracts_detail_window
                if ew is not None and ew.winfo_exists():
                    self._refresh_roster_expiring_contracts_detail_body()
        except Exception:
            pass

    def open_finance_window(self) -> None:
        """Open a safe read-only finance / management subwindow."""
        existing = getattr(self, "_finance_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_finance_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"経営情報 - {self._team_name()}")
        window.geometry("980x760")
        window.minsize(860, 620)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass
        try:
            window.withdraw()
        except tk.TclError:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.finance_header_var = tk.StringVar(value="経営メニュー")
        ttk.Label(
            header,
            textvariable=self.finance_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        fin_purpose = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 8))
        fin_purpose.pack(fill="x", pady=(0, 10))
        ttk.Label(
            fin_purpose,
            text=(
                "【経営メニュー】状況は右のダッシュボード、施設・スポンサー等は左のボタンから別ウィンドウで開きます。"
                "数値の正本・締め処理は共通ロジック／オフシーズン財務締めに依存します。"
            ),
            wraplength=1020,
            font=("Yu Gothic UI", 10),
            justify="left",
        ).pack(anchor="w")

        fin_top = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 8))
        hub_actions = ttk.Frame(fin_top, style="Card.TFrame", padding=(0, 0, 10, 0))
        hub_actions.pack(side="left", fill="y", anchor="nw")
        ttk.Label(
            hub_actions,
            text="経営アクション",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        self._finance_hub_buttons = ttk.Frame(hub_actions, style="Card.TFrame")
        self._finance_hub_buttons.pack(anchor="nw")

        dash_board = ttk.Frame(fin_top, style="Card.TFrame", padding=(0, 0, 0, 0))
        dash_board.pack(side="right", fill="both", expand=True)
        ttk.Label(
            dash_board,
            text="現況ダッシュボード",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        self._management_dashboard_text = tk.Text(
            dash_board,
            height=14,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._management_dashboard_text.pack(fill="both", expand=True)
        for _tag in (
            "finance_block_header",
            "finance_row_default",
        ):
            self._management_dashboard_text.tag_configure(_tag)
        self._management_dashboard_text.tag_configure(
            "finance_row_cap",
            background=_MGMT_DASH_CAP_BG,
            foreground=_MGMT_DASH_CAP_FG,
        )
        self._management_dashboard_text.tag_configure(
            "finance_row_warning",
            background=_MGMT_DASH_WARN_BG,
            foreground=_MGMT_DASH_WARN_FG,
        )
        for _ftag in (
            "facility_block_header",
            "facility_row_default",
            "facility_row_state",
            "facility_row_levels",
            "facility_row_build",
            "facility_row_note",
            "facility_row_market",
        ):
            self._management_dashboard_text.tag_configure(_ftag)
        self._management_dashboard_text.tag_configure(
            "facility_row_invest",
            background=_MGMT_DASH_INVEST_BG,
            foreground=_MGMT_DASH_INVEST_FG,
        )
        for _ptag in (
            "pr_row_default",
            "pr_row_status",
            "pr_row_candidates",
        ):
            self._management_dashboard_text.tag_configure(_ptag)
        self._management_dashboard_text.tag_configure(
            "pr_row_warning",
            background=_MGMT_DASH_WARN_BG,
            foreground=_MGMT_DASH_WARN_FG,
        )
        for _otag in (
            "owner_block_header",
            "owner_row_default",
            "owner_row_header",
            "owner_row_mission",
            "owner_row_progress",
            "owner_row_deadline",
            "owner_row_danger",
        ):
            self._management_dashboard_text.tag_configure(_otag)
        self._management_dashboard_text.tag_configure(
            "owner_row_warning",
            background=_MGMT_DASH_WARN_BG,
            foreground=_MGMT_DASH_WARN_FG,
        )
        for _htag in (
            "history_block_header",
            "history_row_default",
            "history_row_action",
            "history_row_timing",
        ):
            self._management_dashboard_text.tag_configure(_htag)
        self._management_dashboard_text.tag_configure(
            "history_row_result",
            background=_MGMT_DASH_RESULT_BG,
            foreground=_MGMT_DASH_RESULT_FG,
        )
        self._management_dashboard_text.configure(state="disabled")


        # メインはサマリー＋導線のみ（施設等は別 Toplevel）
        self._management_action_toplevels = {}
        self._finance_scroll_canvas = None
        self._finance_scroll_content = None
        self._finance_detail_shell = None
        self._finance_detail_host = None
        self._finance_detail_selection_var = None
        self._finance_detail_page_key = None
        self.finance_summary_panel = None
        self.finance_summary_lines = []
        self._finance_cap_text = None
        self._finance_inseason_log_text = None
        self.facility_panel = None
        self.facility_lines = []
        self._facility_upgrade_buttons = {}
        self._facility_preview_vars = {}
        self._facility_card_level_vars = {}
        self._facility_card_cost_vars = {}
        self._facility_card_status_vars = {}
        self._facility_market_summary_var = None
        self.owner_panel = None
        self.owner_report_text = None
        self.finance_report_panel = None
        self.finance_report_text = None
        self.sponsor_panel = None
        self.pr_panel = None
        self.merch_panel = None
        self._merch_rows = []
        self._sponsor_type_ids = []
        self._sponsor_combo = None
        self._sponsor_apply_btn = None
        self._sponsor_history_text = None
        self._sponsor_status_var = None
        self._sponsor_preview_var = None
        self._sponsor_finance_combo_sig = None
        self._pr_combo = None
        self._pr_run_btn = None
        self._pr_history_text = None
        self._pr_status_var = None
        self._pr_remaining_var = None
        self._pr_sort_combo = None
        self._pr_filter_combo = None
        self._pr_comparison_listbox = None
        self._pr_comparison_ids = []
        self._pr_campaign_ids = []
        self._merch_dummy_text = None
        self._merch_hist_text = None
        self._merch_summary_var = None

        hub_fr = self._finance_hub_buttons
        for _w in hub_fr.winfo_children():
            try:
                _w.destroy()
            except tk.TclError:
                pass
        for _txt, akey in (
            ("施設", "facility"),
            ("スポンサー", "sponsor"),
            ("広報", "pr"),
            ("グッズ", "merch"),
            ("詳細レポート", "report"),
        ):
            ttk.Button(
                hub_fr,
                text=_txt,
                style="Menu.TButton",
                width=18,
                command=lambda k=akey: self._open_finance_action_window(k),
            ).pack(fill="x", pady=4)

        fin_top.pack(fill="both", expand=True, pady=(0, 10))


        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

        tk.Label(
            bottom,
            text=(
                "左のボタンから施設・スポンサー・広報・グッズ・詳細レポートを別ウィンドウで開けます。"
                " 状況の要約は右のダッシュボードに集約しています。"
            ),
            bg="#1d2129",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=1020,
            padx=2,
        ).pack(fill="x", anchor="w", pady=(0, 4))

        self.finance_hint_var = tk.StringVar(value="")
        tk.Label(
            bottom,
            textvariable=self.finance_hint_var,
            bg="#1d2129",
            fg="#c5cad3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            padx=2,
            pady=2,
        ).pack(fill="x", anchor="w")

        bf = tk.Frame(bottom, bg="#1d2129")
        bf.pack(anchor="e", pady=(8, 0))
        self._jpn_text_button(bf, "閉じる", self._on_close_finance_window, side="right")

        self._finance_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_finance_window)
        try:
            self._refresh_finance_window()
        finally:
            try:
                window.update_idletasks()
                window.deiconify()
                window.lift()
            except tk.TclError:
                pass

    def _on_close_finance_window(self) -> None:
        self._finance_destroy_all_action_subwindows()
        window = getattr(self, "_finance_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._finance_window = None
            self.finance_summary_panel = None
            self.finance_summary_lines = []
            self._finance_cap_text = None
            self.facility_panel = None
            self.facility_lines = []
            self.owner_panel = None
            self.finance_report_panel = None
            self.sponsor_panel = None
            self.pr_panel = None
            self.merch_panel = None
            self._management_action_toplevels = {}
            self._facility_upgrade_buttons = {}
            self.finance_report_text = None
            self.owner_report_text = None
            self._sponsor_combo = None
            self._sponsor_apply_btn = None
            self._sponsor_history_text = None
            self._sponsor_status_var = None
            self._pr_combo = None
            self._pr_run_btn = None
            self._pr_history_text = None
            self._pr_status_var = None
            self._merch_rows = []
            self._merch_dummy_text = None
            self._merch_hist_text = None
            self._merch_summary_var = None
            self._management_dashboard_text = None
            self._facility_preview_vars = {}
            self._facility_card_level_vars = {}
            self._facility_card_cost_vars = {}
            self._facility_card_status_vars = {}
            self._facility_market_summary_var = None
            self._sponsor_preview_var = None
            self._pr_selection_preview_var = None
            self._pr_remaining_var = None
            self._pr_sort_combo = None
            self._pr_filter_combo = None
            self._pr_comparison_listbox = None
            self._pr_comparison_ids = []
            self._finance_scroll_canvas = None
            self._finance_scroll_content = None
            self._finance_hub_buttons = None
            self._finance_detail_shell = None
            self._finance_detail_host = None
            self._finance_detail_selection_var = None
            self._finance_detail_page_key = None
            self._finance_inseason_log_text = None


    def _finance_destroy_all_action_subwindows(self) -> None:
        tws = getattr(self, "_management_action_toplevels", None)
        if not isinstance(tws, dict) or not tws:
            return
        for key in list(tws.keys()):
            tw = tws.pop(key, None)
            self._finance_clear_action_widgets_for_key(key)
            if tw is not None:
                try:
                    tw.destroy()
                except tk.TclError:
                    pass

    def _finance_clear_action_widgets_for_key(self, key: str) -> None:
        if key == "facility":
            self.facility_panel = None
            self.facility_lines = []
            self._facility_upgrade_buttons = {}
            self._facility_preview_vars = {}
            self._facility_card_level_vars = {}
            self._facility_card_cost_vars = {}
            self._facility_card_status_vars = {}
            self._facility_market_summary_var = None
        elif key == "sponsor":
            self.sponsor_panel = None
            self._sponsor_combo = None
            self._sponsor_apply_btn = None
            self._sponsor_history_text = None
            self._sponsor_status_var = None
            self._sponsor_preview_var = None
            self._sponsor_type_ids = []
            self._sponsor_finance_combo_sig = None
        elif key == "pr":
            self.pr_panel = None
            self._pr_combo = None
            self._pr_run_btn = None
            self._pr_history_text = None
            self._pr_status_var = None
            self._pr_remaining_var = None
            self._pr_sort_combo = None
            self._pr_filter_combo = None
            self._pr_comparison_listbox = None
            self._pr_comparison_ids = []
            self._pr_campaign_ids = []
            self._pr_selection_preview_var = None
        elif key == "merch":
            self.merch_panel = None
            self._merch_rows = []
            self._merch_dummy_text = None
            self._merch_hist_text = None
            self._merch_summary_var = None
        elif key == "report":
            self.owner_panel = None
            self.owner_report_text = None
            self.finance_report_panel = None
            self.finance_report_text = None

    def _on_management_action_window_close(self, key: str) -> None:
        tws = getattr(self, "_management_action_toplevels", None)
        tw = None
        if isinstance(tws, dict):
            tw = tws.pop(key, None)
        self._finance_clear_action_widgets_for_key(key)
        if tw is not None:
            try:
                tw.destroy()
            except tk.TclError:
                pass

    def _open_finance_action_window(self, key: str) -> None:
        parent_win = getattr(self, "_finance_window", None)
        if parent_win is None:
            return
        try:
            if not parent_win.winfo_exists():
                return
        except tk.TclError:
            return
        tws = getattr(self, "_management_action_toplevels", None)
        if not isinstance(tws, dict):
            self._management_action_toplevels = {}
            tws = self._management_action_toplevels
        exist = tws.get(key)
        if exist is not None:
            try:
                if exist.winfo_exists():
                    exist.lift()
                    exist.focus_force()
                    return
            except tk.TclError:
                pass
            tws.pop(key, None)
        titles = {
            "facility": "施設投資",
            "sponsor": "スポンサー契約",
            "pr": "広報・ファン施策",
            "merch": "グッズ開発",
            "report": "詳細レポート・オーナー",
        }
        tw = tk.Toplevel(parent_win)
        tw.title(str(titles.get(key, "経営")))
        tw.geometry("760x680")
        tw.configure(bg="#15171c")
        try:
            tw.transient(parent_win)
        except Exception:
            pass
        outer = ttk.Frame(tw, style="Root.TFrame", padding=10)
        outer.pack(fill="both", expand=True)

        def _close() -> None:
            self._on_management_action_window_close(key)

        tw.protocol("WM_DELETE_WINDOW", _close)

        if key == "facility":
            self._finance_populate_facility_panel(outer)
        elif key == "sponsor":
            self._finance_populate_sponsor_panel(outer)
        elif key == "pr":
            self._finance_populate_pr_panel(outer)
        elif key == "merch":
            self._finance_populate_merch_panel(outer)
        elif key == "report":
            self._finance_populate_report_panels(outer)
        else:
            try:
                tw.destroy()
            except tk.TclError:
                pass
            return

        tws[key] = tw
        self._refresh_finance_window()

    def _finance_populate_facility_panel(self, host: tk.Misc) -> None:
        self.facility_panel = self._create_panel(host, "施設・基盤")
        self.facility_panel.pack(fill="both", expand=True)
        fac_content = self._resolve_content_parent(self.facility_panel)
        ttk.Label(
            fac_content,
            text=(
                "各施設は1段階ずつ強化できます。投資は所持金から即時に差し引かれ、レベルと一部指標が更新されます。"
                "収支の本格反映はオフシーズン締めもあわせて参照してください。（反映: 即時）"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            fac_content,
            text=(
                "※トレーニング／メディカル／フロントのLvは、強化・育成メニュー内のスペシャル練習解放条件などでも参照されます。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=700,
            foreground="#b8c0cc",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # 旧6行サマリーはカード内に集約し、ここでは重複表示しない
        self.facility_lines = []
        self._facility_preview_vars = {}
        self._facility_card_level_vars = {}
        self._facility_card_cost_vars = {}
        self._facility_card_status_vars = {}
        self._facility_upgrade_buttons = {}

        cards = ttk.Frame(fac_content, style="Card.TFrame")
        cards.pack(fill="both", expand=True)
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        for i, fk in enumerate(FACILITY_ORDER):
            r, c = divmod(i, 2)
            title = FACILITY_LABELS.get(fk, fk)
            cell = ttk.Frame(cards, style="Card.TFrame", padding=8)
            cell.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            inner = tk.Frame(cell, bg="#222834", padx=8, pady=8)
            inner.pack(fill="both", expand=True)

            tk.Label(
                inner,
                text=title,
                bg="#222834",
                fg="#eef3f8",
                anchor="w",
                font=("Yu Gothic UI", 12, "bold"),
            ).pack(anchor="w", pady=(0, 6))

            lv_v = tk.StringVar(value="")
            co_v = tk.StringVar(value="")
            st_v = tk.StringVar(value="")
            self._facility_card_level_vars[fk] = lv_v
            self._facility_card_cost_vars[fk] = co_v
            self._facility_card_status_vars[fk] = st_v

            tk.Label(
                inner,
                textvariable=lv_v,
                bg="#222834",
                fg="#eef3f8",
                anchor="w",
                font=("Yu Gothic UI", 11, "bold"),
                wraplength=320,
            ).pack(anchor="w")
            tk.Label(
                inner,
                textvariable=co_v,
                bg="#222834",
                fg="#d6dbe3",
                anchor="w",
                font=("Yu Gothic UI", 10),
                wraplength=320,
            ).pack(anchor="w", pady=(2, 0))
            tk.Label(
                inner,
                textvariable=st_v,
                bg="#222834",
                fg="#c5cad3",
                anchor="w",
                font=("Yu Gothic UI", 10),
                wraplength=320,
            ).pack(anchor="w", pady=(2, 0))

            eff = _FACILITY_MANAGEMENT_EFFECT_BLURB_JA.get(fk, "効果（目安）: 関連指標が更新されます。")
            tk.Label(
                inner,
                text=eff,
                bg="#222834",
                fg="#9aa4b2",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=320,
            ).pack(anchor="w", pady=(6, 8))

            b = ttk.Button(
                inner,
                text="投資する",
                style="Menu.TButton",
                command=lambda k=fk: self._on_facility_upgrade_click(k),
            )
            b.pack(fill="x")
            self._facility_upgrade_buttons[fk] = b

        self._facility_market_summary_var = tk.StringVar(value="")
        tk.Label(
            fac_content,
            text="チーム指標（参考）",
            font=("Yu Gothic UI", 9, "bold"),
            foreground="#b8c0cc",
        ).pack(anchor="w", pady=(10, 2))
        tk.Label(
            fac_content,
            textvariable=self._facility_market_summary_var,
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=700,
        ).pack(fill="x", anchor="w")

    def _finance_populate_sponsor_panel(self, host: tk.Misc) -> None:
        self._sponsor_finance_combo_sig = None
        self.sponsor_panel = self._create_panel(host, "スポンサー（メイン契約）")
        self.sponsor_panel.pack(fill="both", expand=True)
        sponsor_inner = self._resolve_content_parent(self.sponsor_panel)
        tk.Label(
            sponsor_inner,
            text="メイン契約の種類を選び「メイン契約を反映」で確定します。上から順に現状・候補・履歴です。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))

        tk.Label(
            sponsor_inner,
            text="【現在のスポンサー】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        self._sponsor_status_var = tk.StringVar(value="")
        tk.Label(
            sponsor_inner,
            textvariable=self._sponsor_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))

        ttk.Separator(sponsor_inner, orient="horizontal").pack(fill="x", pady=(0, 6))

        tk.Label(
            sponsor_inner,
            text="【契約候補】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        sponsor_row = ttk.Frame(sponsor_inner, style="Card.TFrame")
        sponsor_row.pack(fill="x", pady=(0, 6))
        tk.Label(
            sponsor_row,
            text="候補：",
            bg="#222834",
            fg="#b8c0cc",
            font=("Yu Gothic UI", 10),
        ).pack(side="left", padx=(0, 6))
        self._sponsor_type_ids = [str(x["id"]) for x in MAIN_SPONSOR_TYPES]
        combo_labels = [str(x["label"]) for x in MAIN_SPONSOR_TYPES]
        self._sponsor_combo = ttk.Combobox(
            sponsor_row,
            values=combo_labels,
            state="readonly",
            width=32,
            font=("Yu Gothic UI", 10),
        )
        self._sponsor_combo.pack(side="left", padx=(0, 10))
        init_ix = 0
        if self.team is not None:
            try:
                ensure_sponsor_management_on_team(self.team)
                icur = str(self.team.management.get("sponsors", {}).get("main_contract_type", "standard"))
                for j, tid in enumerate(self._sponsor_type_ids):
                    if tid == icur:
                        init_ix = j
                        break
            except (TypeError, ValueError, AttributeError, KeyError):
                init_ix = 0
        try:
            self._sponsor_combo.current(init_ix)
        except tk.TclError:
            pass
        self._sponsor_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_finance_window())
        self._sponsor_apply_btn = ttk.Button(
            sponsor_row,
            text="メイン契約を反映",
            style="Menu.TButton",
            command=self._on_sponsor_contract_apply,
        )
        self._sponsor_apply_btn.pack(side="left")
        tk.Label(
            sponsor_inner,
            text="プレビュー（選択中の候補）",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 2))
        self._sponsor_preview_var = tk.StringVar(value="")
        tk.Label(
            sponsor_inner,
            textvariable=self._sponsor_preview_var,
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))
        tk.Label(
            sponsor_inner,
            text="スポンサー契約はその場で現金を増やすものではなく、主に次オフ収入へ反映されます。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 4))
        _hint_lines = "\n".join(
            f"・{str(spec.get('label', ''))}：{MAIN_SPONSOR_CLI_COMPARISON_HINTS.get(str(spec.get('id', '')), '')}"
            for spec in MAIN_SPONSOR_TYPES
        )
        tk.Label(
            sponsor_inner,
            text="候補の目安（表示のみ・数値ロジックは変更しません）",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(2, 2))
        tk.Label(
            sponsor_inner,
            text=_hint_lines,
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))

        tk.Label(
            sponsor_inner,
            text="【次オフ収入について】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        tk.Label(
            sponsor_inner,
            text=(
                "スポンサー収入はオフシーズン財務締めで確定します。\n"
                "sponsor_power・人気・勝ち越しなどが収入に関係します。\n"
                "契約変更時の即時の現金増加はありません。"
            ),
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))

        ttk.Separator(sponsor_inner, orient="horizontal").pack(fill="x", pady=(0, 6))

        tk.Label(
            sponsor_inner,
            text="【契約履歴】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        tk.Label(
            sponsor_inner,
            text="直近のメインスポンサー契約変更を表示します。",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 4))
        self._sponsor_history_text = scrolledtext.ScrolledText(
            sponsor_inner,
            height=4,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=4,
        )
        self._sponsor_history_text.pack(fill="both", expand=True)
        self._sponsor_history_text.configure(state="disabled")

    def _finance_populate_pr_panel(self, host: tk.Misc) -> None:
        self.pr_panel = self._create_panel(host, "広報・ファン施策")
        self.pr_panel.pack(fill="both", expand=True)
        pr_inner = self._resolve_content_parent(self.pr_panel)
        tk.Label(
            pr_inner,
            text="ファン向け施策です。上から順に現状・候補・効果の説明・履歴です。実行はシーズン中の枠と所持金に依存します。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))

        tk.Label(
            pr_inner,
            text="【現在の広報状況】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        self._pr_status_var = tk.StringVar(value="")
        tk.Label(
            pr_inner,
            textvariable=self._pr_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))

        ttk.Separator(pr_inner, orient="horizontal").pack(fill="x", pady=(0, 6))

        tk.Label(
            pr_inner,
            text="【施策候補】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        pr_cmp_row = ttk.Frame(pr_inner, style="Card.TFrame")
        pr_cmp_row.pack(fill="x", pady=(0, 6))
        ttk.Label(pr_cmp_row, text="並べ替え:", font=("Yu Gothic UI", 9)).pack(side="left", padx=(0, 6))
        self._pr_sort_combo = ttk.Combobox(
            pr_cmp_row,
            values=list(_PR_FINANCE_SORT_LABELS_JA),
            state="readonly",
            width=16,
            font=("Yu Gothic UI", 9),
        )
        self._pr_sort_combo.pack(side="left", padx=(0, 14))
        try:
            self._pr_sort_combo.current(0)
        except tk.TclError:
            pass
        self._pr_sort_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_finance_window())
        ttk.Label(pr_cmp_row, text="絞り込み:", font=("Yu Gothic UI", 9)).pack(side="left", padx=(0, 6))
        self._pr_filter_combo = ttk.Combobox(
            pr_cmp_row,
            values=list(_PR_FINANCE_FILTER_LABELS_JA),
            state="readonly",
            width=30,
            font=("Yu Gothic UI", 9),
        )
        self._pr_filter_combo.pack(side="left", padx=(0, 0))
        try:
            self._pr_filter_combo.current(0)
        except tk.TclError:
            pass
        self._pr_filter_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_finance_window())
        tk.Label(
            pr_inner,
            text="候補一覧（行を選ぶと下のコンボと実行対象が連動）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 9),
            padx=2,
        ).pack(fill="x", pady=(0, 4))
        pr_lb_fr = tk.Frame(pr_inner, bg="#222834")
        pr_lb_fr.pack(fill="x", pady=(0, 6))
        self._pr_comparison_listbox = tk.Listbox(
            pr_lb_fr,
            height=4,
            bg="#222834",
            fg="#d6dbe3",
            selectbackground="#3d4a60",
            selectforeground="#ffffff",
            font=("Yu Gothic UI", 9),
            activestyle="dotbox",
            highlightthickness=0,
            borderwidth=1,
            relief="flat",
        )
        self._pr_comparison_listbox.pack(side="left", fill="both", expand=True)
        pr_sb = ttk.Scrollbar(pr_lb_fr, orient="vertical", command=self._pr_comparison_listbox.yview)
        pr_sb.pack(side="right", fill="y")
        self._pr_comparison_listbox.configure(yscrollcommand=pr_sb.set)
        self._pr_comparison_listbox.bind("<<ListboxSelect>>", self._on_pr_comparison_pick)
        self._pr_comparison_ids = []
        pr_row = ttk.Frame(pr_inner, style="Card.TFrame")
        pr_row.pack(fill="x", pady=(0, 6))
        tk.Label(
            pr_row,
            text="実行する施策：",
            bg="#222834",
            fg="#b8c0cc",
            font=("Yu Gothic UI", 10),
        ).pack(side="left", padx=(0, 6))
        self._pr_campaign_ids = [str(x["id"]) for x in PR_CAMPAIGNS]
        pr_labels = [str(x["label"]) for x in PR_CAMPAIGNS]
        self._pr_combo = ttk.Combobox(
            pr_row,
            values=pr_labels,
            state="readonly",
            width=28,
            font=("Yu Gothic UI", 10),
        )
        self._pr_combo.pack(side="left", padx=(0, 10))
        try:
            self._pr_combo.current(0)
        except tk.TclError:
            pass
        self._pr_combo.bind("<<ComboboxSelected>>", self._on_pr_combo_pick_light)
        self._pr_run_btn = ttk.Button(
            pr_row,
            text="施策を実行",
            style="Menu.TButton",
            command=self._on_pr_campaign_run,
        )
        self._pr_run_btn.pack(side="left")
        tk.Label(
            pr_inner,
            text="プレビュー（選択中の候補）",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 2))
        self._pr_selection_preview_var = tk.StringVar(value="")
        tk.Label(
            pr_inner,
            textvariable=self._pr_selection_preview_var,
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))
        _pr_hint_lines = "\n".join(
            f"・{str(spec.get('label', ''))}：{PR_CAMPAIGN_CLI_COMPARISON_HINTS.get(str(spec.get('id', '')), '')}"
            for spec in PR_CAMPAIGNS
        )
        tk.Label(
            pr_inner,
            text="候補の目安（表示のみ・数値ロジックは変更しません）",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(2, 2))
        tk.Label(
            pr_inner,
            text=_pr_hint_lines,
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))

        ttk.Separator(pr_inner, orient="horizontal").pack(fill="x", pady=(0, 6))

        tk.Label(
            pr_inner,
            text="【効果と反映タイミング】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        tk.Label(
            pr_inner,
            text=(
                "PR施策は実行時に費用を支払い、人気・ファン基盤へ即時反映されます。\n"
                "人気・ファン基盤は、将来の集客・グッズ・スポンサー収入の土台に関係します。\n"
                "収入式への本格接続は段階実装中です（試合収入式への本接続は後段）。"
            ),
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))

        ttk.Separator(pr_inner, orient="horizontal").pack(fill="x", pady=(0, 6))

        tk.Label(
            pr_inner,
            text="【広報履歴】",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", anchor="w", pady=(0, 2))
        tk.Label(
            pr_inner,
            text="直近のPR施策実行履歴を表示します。",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 4))
        self._pr_history_text = scrolledtext.ScrolledText(
            pr_inner,
            height=4,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=4,
        )
        self._pr_history_text.pack(fill="both", expand=True)
        self._pr_history_text.configure(state="disabled")

    def _merch_next_action_tag(self, affordance_line: str) -> str:
        aff = str(affordance_line or "")
        if "今なら進行可" in aff or "ぎりぎり" in aff:
            return "進行可"
        if "今は厳しい" in aff:
            return "資金不足"
        if "発売中のため追加工程なし" in aff:
            return "発売済み"
        return "詳細で確認"

    def _build_merch_panel_summary_text(self, team: Any) -> str:
        n = len(MERCH_PRODUCTS)
        if n <= 0:
            return "【現在のグッズ開発】\n商品ラインが未設定です。"
        if team is None:
            return (
                "【現在のグッズ開発】\n"
                "発売中ライン：— / —\n"
                "開発中ライン：—\n"
                "次アクション：詳細で確認\n"
                "チーム未接続のため内訳を表示できません。"
            )
        ensure_merchandise_on_team(team)
        block = team.management.get("merchandise")
        items: List[Any] = []
        if isinstance(block, dict):
            raw = block.get("items")
            if isinstance(raw, list):
                items = raw
        on_sale = sum(
            1 for r in items if isinstance(r, dict) and str(r.get("phase", "")) == "on_sale"
        )
        developing = max(0, n - on_sale)
        try:
            aff = build_merchandise_affordance_summary_line(team, format_money=self._format_money)
        except Exception:
            aff = "グッズ余力: 詳細で確認"
        tag = self._merch_next_action_tag(aff)
        return (
            f"【現在のグッズ開発】\n"
            f"発売中ライン：{on_sale} / {n}\n"
            f"開発中ライン：{developing}\n"
            f"次アクション：{tag}\n"
            f"{aff}\n"
            "反映：段階進行は「開発を進める」実行時。発売中ラインが増えると、将来の物販収入内訳の改善に関係しやすくなります。"
        )

    def _merch_row_judgment_line(
        self, team: Any, product_id: str, item: Any, is_user: bool
    ) -> str:
        if item is None:
            return "段階：— ｜ 次費用：— ｜ 状態：詳細で確認"
        ph = normalize_merchandise_phase_value(item.get("phase"))
        lab = PHASE_LABEL_JA.get(ph, ph)
        if ph == "on_sale":
            return f"段階：{lab} ｜ 次費用：— ｜ 状態：発売済み"
        cost = int(ADVANCE_COST.get(ph, 0) or 0)
        cost_s = f"{cost:,} 円" if cost > 0 else "—"
        if not is_user:
            return f"段階：{lab} ｜ 次費用：{cost_s} ｜ 状態：詳細で確認（自チームのみ操作可）"
        ok, reason = can_advance_merchandise_phase(team, product_id)
        if ok:
            status = "進行可"
        else:
            rs = str(reason or "")
            if "資金" in rs:
                status = "資金不足"
            elif "発売" in rs:
                status = "発売済み"
            else:
                status = "詳細で確認"
        return f"段階：{lab} ｜ 次費用：{cost_s} ｜ 状態：{status}"

    def _finance_populate_merch_panel(self, host: tk.Misc) -> None:
        self.merch_panel = self._create_panel(host, "グッズ開発")
        self.merch_panel.pack(fill="both", expand=True)
        merch_inner = self._resolve_content_parent(self.merch_panel)
        tk.Label(
            merch_inner,
            text="各ラインを段階で進めます（開発費は「開発を進める」実行時に所持金から差し引き）。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))
        self._merch_summary_var = tk.StringVar(value="")
        tk.Label(
            merch_inner,
            textvariable=self._merch_summary_var,
            bg="#1a1f28",
            fg="#c5cad3",
            anchor="nw",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=8,
            pady=6,
        ).pack(fill="x", pady=(0, 8))
        tk.Label(
            merch_inner,
            text="【商品ライン】",
            bg="#222834",
            fg="#e8ecf1",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", pady=(0, 4))
        merch_lines_fr = ttk.Frame(merch_inner, style="Card.TFrame")
        merch_lines_fr.pack(fill="x", pady=(0, 8))
        self._merch_rows = []
        for tmpl in MERCH_PRODUCTS:
            pid = str(tmpl["id"])
            var = tk.StringVar(value="")
            dvar = tk.StringVar(value="")
            pvar = tk.StringVar(value="")
            row_fr = ttk.Frame(merch_lines_fr, style="Card.TFrame")
            row_fr.pack(fill="x", pady=4)
            btn = ttk.Button(
                row_fr,
                text="開発を進める",
                style="Menu.TButton",
                command=lambda p=pid: self._on_merch_advance(p),
            )
            btn.pack(side="right", anchor="n", pady=(2, 0))
            left_col = tk.Frame(row_fr, bg="#222834")
            left_col.pack(side="left", fill="x", expand=True, padx=(0, 8))
            nm = str(tmpl.get("name", pid))
            cat = str(tmpl.get("category", ""))
            head = f"{nm}（{cat}）" if cat else nm
            tk.Label(
                left_col,
                text=head,
                bg="#222834",
                fg="#e8ecf1",
                anchor="w",
                font=("Yu Gothic UI", 10, "bold"),
                wraplength=560,
            ).pack(anchor="w", fill="x")
            tk.Label(
                left_col,
                textvariable=var,
                bg="#222834",
                fg="#d6dbe3",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=560,
            ).pack(anchor="w", fill="x", pady=(2, 0))
            tk.Label(
                left_col,
                textvariable=dvar,
                bg="#222834",
                fg="#a8b4c4",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=560,
            ).pack(anchor="w", fill="x", pady=(1, 0))
            tk.Label(
                left_col,
                text="プレビュー",
                bg="#222834",
                fg="#7d8a9a",
                anchor="w",
                font=("Yu Gothic UI", 8),
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                left_col,
                textvariable=pvar,
                bg="#222834",
                fg="#9aa4b2",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=560,
            ).pack(anchor="w", fill="x", pady=(0, 2))
            self._merch_rows.append((pid, var, pvar, btn, dvar))
        tk.Label(
            merch_inner,
            text="【効果と反映】",
            bg="#222834",
            fg="#e8ecf1",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", pady=(4, 2))
        tk.Label(
            merch_inner,
            text=(
                "グッズ開発は段階進行です。発売済みラインは将来の物販収入に関係します。\n"
                "物販収入は人気・ファン基盤・成績などの影響も受けます。\n"
                "下の売上目安は参考表示であり、本番収支の確定値ではありません。"
            ),
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
        ).pack(fill="x", pady=(0, 8))
        tk.Label(
            merch_inner,
            text="【売上目安（参考）】",
            bg="#222834",
            fg="#e8ecf1",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", pady=(0, 2))
        self._merch_dummy_text = scrolledtext.ScrolledText(
            merch_inner,
            height=4,
            wrap="word",
            bg="#222834",
            fg="#c5cad3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=4,
        )
        self._merch_dummy_text.pack(fill="x", pady=(0, 6))
        self._merch_dummy_text.configure(state="disabled")
        tk.Label(
            merch_inner,
            text="【開発履歴】",
            bg="#222834",
            fg="#e8ecf1",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(fill="x", pady=(4, 0))
        tk.Label(
            merch_inner,
            text="直近のグッズ開発進行を表示します。",
            bg="#222834",
            fg="#9aa4b2",
            anchor="w",
            font=("Yu Gothic UI", 8),
        ).pack(fill="x", pady=(0, 2))
        self._merch_hist_text = scrolledtext.ScrolledText(
            merch_inner,
            height=4,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=4,
        )
        self._merch_hist_text.pack(fill="both", expand=True)
        self._merch_hist_text.configure(state="disabled")

    def _finance_populate_report_panels(self, host: tk.Misc) -> None:
        wrap = ttk.Frame(host, style="Root.TFrame")
        wrap.pack(fill="both", expand=True)
        self.owner_panel = self._create_panel(wrap, "オーナー・方針")
        self.owner_panel.pack(fill="both", expand=False)
        owner_parent = self._resolve_content_parent(self.owner_panel)
        ttk.Label(
            owner_parent,
            text="オーナーからの期待・信頼・ミッション（チームデータに依存）。"
            "ミッションは主にオフシーズンに評価・更新されます。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self.owner_report_text = scrolledtext.ScrolledText(
            owner_parent,
            height=14,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self.owner_report_text.pack(fill="both", expand=True)
        self.owner_report_text.configure(state="disabled")
        self.finance_report_panel = self._create_panel(wrap, "詳細レポート")
        self.finance_report_panel.pack(fill="both", expand=True)
        report_parent = self._resolve_content_parent(self.finance_report_panel)
        ttk.Label(
            report_parent,
            text="前季までの収入内訳・支出内訳・財務履歴（記録ベース）。"
            "シーズン収支の正本反映はオフシーズンの財務締めです。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self.finance_report_text = scrolledtext.ScrolledText(
            report_parent,
            height=16,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self.finance_report_text.pack(fill="both", expand=True)
        self.finance_report_text.configure(state="disabled")

    def _apply_compact_management_dashboard_text(
        self,
        dash_tw: tk.Text,
        snap: Any,
        quick_summary_lines: List[str],
    ) -> bool:
        """Fill the management dashboard Text with a short hub view (詳細は別 Toplevel)."""
        fin_lines = getattr(snap, "dashboard_finance_lines", None)
        if not fin_lines:
            return False
        try:
            parts = str(getattr(snap, "dashboard_text", "") or "").split(
                _MANAGEMENT_FINANCE_BLOCK_SEPARATOR, 1
            )
        except Exception:
            return False
        if len(parts) != 2:
            return False
        sub_after_fin = parts[1]
        fac_lines_snap = getattr(snap, "facility_lines", None) or ()
        fac_tail = sub_after_fin.split(_MANAGEMENT_FACILITY_PR_SEPARATOR, 1)
        if not fac_lines_snap or len(fac_tail) != 2:
            return False
        dash_tw.insert("end", "■ 現況サマリー\n", ("finance_block_header",))
        if quick_summary_lines:
            for qln in quick_summary_lines:
                dash_tw.insert("end", qln + "\n", ("finance_row_default",))
            dash_tw.insert("end", "\n")
        dash_tw.insert("end", "■ 施策可否\n", ("finance_block_header",))
        for aln in getattr(snap, "action_availability_lines", ()):
            dash_tw.insert("end", aln + "\n", ("finance_row_default",))
        if getattr(snap, "action_availability_lines", ()):
            dash_tw.insert("end", "\n")
        cap_ln = str(getattr(snap, "payroll_capacity_summary", "") or "").strip()
        if cap_ln:
            if len(cap_ln) > 96:
                cap_ln = cap_ln[:93] + "…"
            dash_tw.insert("end", cap_ln + "\n", ("finance_row_cap",))
            dash_tw.insert("end", "\n")
        dash_tw.insert("end", "\n■ 施設\n", ("facility_block_header",))
        for fln in list(fac_lines_snap)[:2]:
            dash_tw.insert(
                "end",
                fln + "\n",
                _management_facility_dashboard_row_tags(fln),
            )
        dash_tw.insert("end", "\n■ 広報・スポンサー・グッズ\n", ("finance_block_header",))
        pr_summary = str(getattr(snap, "pr_dashboard_summary", "") or "").strip()
        if pr_summary:
            for pln in pr_summary.split("\n")[:2]:
                if pln.strip():
                    dash_tw.insert(
                        "end",
                        pln + "\n",
                        _management_pr_dashboard_row_tags(pln),
                    )
        for _aff_key in ("sponsor_affordance_summary", "merch_affordance_summary"):
            aln2 = str(getattr(snap, _aff_key, "") or "").strip()
            if aln2:
                if len(aln2) > 100:
                    aln2 = aln2[:97] + "…"
                dash_tw.insert("end", aln2 + "\n", ("pr_row_default",))
        own_prev = str(getattr(snap, "owner_preamble", "") or "").strip()
        own_kept = [x for x in own_prev.split("\n") if x.strip()][:2]
        dash_tw.insert("end", "\n■ オーナー\n", ("owner_block_header",))
        for oln in own_kept:
            dash_tw.insert(
                "end",
                oln + "\n",
                _management_owner_dashboard_row_tags(oln),
            )
        hist_marker = _MANAGEMENT_OWNER_HISTORY_SEPARATOR
        dt = str(getattr(snap, "dashboard_text", "") or "")
        dash_tw.insert("end", "\n", ())
        dash_tw.insert("end", "■ 直近アクション（要約）\n", ("history_block_header",))
        if hist_marker in dt:
            htail = [x for x in dt.split(hist_marker, 1)[1].strip().split("\n") if x.strip()]
            if htail:
                dash_tw.insert("end", htail[0] + "\n", ("history_row_default",))
        dash_tw.insert(
            "end",
            "（詳細は左のボタンから各ウィンドウで確認）\n",
            ("history_row_default",),
        )
        return True

    def _refresh_facility_management_card_vars(self, snap: Any) -> None:
        """施設別ウィンドウのカード表示のみ更新（投資ロジックは触らない）。"""
        lv_map = getattr(self, "_facility_card_level_vars", None)
        cost_map = getattr(self, "_facility_card_cost_vars", None)
        st_map = getattr(self, "_facility_card_status_vars", None)
        if not (isinstance(lv_map, dict) and lv_map and isinstance(cost_map, dict) and isinstance(st_map, dict)):
            return
        team = self.team
        max_lv = int(FACILITY_MAX_LEVEL)
        for fk in FACILITY_ORDER:
            lv_v = lv_map.get(fk)
            c_v = cost_map.get(fk)
            s_v = st_map.get(fk)
            if lv_v is None or c_v is None or s_v is None:
                continue
            try:
                if team is None:
                    lv_v.set("現在Lv: — / —")
                    c_v.set("次Lv費用: —")
                    s_v.set("状態: チーム未接続")
                    continue
                lv = int(self._safe_get(team, fk, 1))
                lv_v.set(f"現在Lv: {lv} / {max_lv}")
                if lv >= max_lv:
                    c_v.set("次Lv費用: —（最大）")
                else:
                    c_v.set(f"次Lv費用: {self._format_money(get_facility_upgrade_cost(team, fk))}")
                if not bool(getattr(team, "is_user_team", False)):
                    s_v.set("状態: 自チームのみ操作可")
                    continue
                ok, msg = can_commit_facility_upgrade(team, fk)
                if ok:
                    s_v.set("状態: 実行可")
                elif "最大" in str(msg or ""):
                    s_v.set("状態: 最大Lv到達")
                elif "不足" in str(msg or ""):
                    s_v.set("状態: 資金不足")
                else:
                    m = str(msg or "実行不可").strip()
                    if len(m) > 44:
                        m = m[:41] + "…"
                    s_v.set(f"状態: {m}")
            except tk.TclError:
                pass

        foot = getattr(self, "_facility_market_summary_var", None)
        if foot is not None:
            try:
                if team is None:
                    foot.set("")
                else:
                    fl = tuple(getattr(snap, "facility_lines", ()) or ())
                    if len(fl) > 4:
                        foot.set(str(fl[4]))
                    else:
                        foot.set("")
            except tk.TclError:
                pass

    def _on_facility_upgrade_click(self, facility_key: str) -> None:
        team = self.team
        if team is None:
            return
        if not bool(getattr(team, "is_user_team", False)):
            messagebox.showinfo("施設投資", "自チームのみ施設投資できます。")
            return
        ok, msg = can_commit_facility_upgrade(team, facility_key)
        if not ok:
            messagebox.showwarning("施設投資", msg or "投資できません。")
            return
        label = FACILITY_LABELS.get(facility_key, facility_key)
        cost = get_facility_upgrade_cost(team, facility_key)
        if not messagebox.askyesno(
            "施設投資の確認",
            f"{label} を 1 段階強化しますか？\n必要資金: {self._format_money(cost)}",
        ):
            return
        ok2, msg2 = commit_facility_upgrade(team, facility_key)
        if ok2:
            messagebox.showinfo("施設投資", msg2)
            self._refresh_finance_window()
            self.refresh()
        else:
            messagebox.showwarning("施設投資", msg2)

    def _on_sponsor_contract_apply(self) -> None:
        team = self.team
        if team is None:
            return
        combo = getattr(self, "_sponsor_combo", None)
        ids = getattr(self, "_sponsor_type_ids", [])
        if combo is None or not ids:
            return
        idx = combo.current()
        if idx < 0 or idx >= len(ids):
            messagebox.showwarning("スポンサー", "契約タイプを選択してください。")
            return
        ok, msg = commit_main_sponsor_contract(team, ids[idx])
        if ok:
            messagebox.showinfo("スポンサー", msg)
        else:
            messagebox.showwarning("スポンサー", msg)
        self._refresh_finance_window()
        self.refresh()

    @staticmethod
    def _sponsor_finance_panel_state_label(team: Any, cur_id: str) -> str:
        """施策サマリーと同系の安全な文言（契約ロジックは持たない）。"""
        if team is None:
            return "詳細で確認"
        if not bool(getattr(team, "is_user_team", False)):
            return "今は変更不可"
        tid = str(cur_id or "").strip()
        if not tid:
            return "未設定"
        if tid not in MAIN_SPONSOR_IDS:
            return "詳細で確認"
        if any(str(x.get("id")) != tid for x in MAIN_SPONSOR_TYPES):
            return "変更可"
        return "契約済み"

    @staticmethod
    def _pr_finance_panel_state_label(team: Any, season: Any) -> str:
        """施策可否サマリーと同系の文言（PR ロジックは持たない）。"""
        if team is None:
            return "詳細で確認"
        if not bool(getattr(team, "is_user_team", False)):
            return "詳細で確認"
        if not PR_CAMPAIGNS:
            return "未設定"
        try:
            results = [can_commit_pr_campaign(team, str(spec["id"]), season) for spec in PR_CAMPAIGNS]
            if any(ok for ok, _reason in results):
                return "実行可"
            _wk, allowed, _reason = sync_pr_round_quota(team, season)
            if not allowed:
                return "詳細で確認"
            block = team.management.get("pr_campaigns") if isinstance(getattr(team, "management", None), dict) else None
            used = int((block or {}).get("count_this_round", 0) or 0)
            if allowed and used >= int(MAX_ACTIONS_PER_ROUND):
                return "今ラウンド上限"
            costs = [int(spec.get("cost", 0) or 0) for spec in PR_CAMPAIGNS]
            money = int(getattr(team, "money", 0) or 0)
            if costs and money < min(costs):
                return "資金不足"
            return "未実行"
        except (TypeError, ValueError, AttributeError, KeyError):
            return "詳細で確認"

    def _sync_pr_comparison_row_to_chrome(self, index: int) -> None:
        combo = getattr(self, "_pr_combo", None)
        row_ids = getattr(self, "_pr_comparison_ids", [])
        campaign_ids = getattr(self, "_pr_campaign_ids", [])
        if combo is None or index < 0 or index >= len(row_ids):
            return
        cid = row_ids[index]
        if not cid:
            self._pr_comparison_selected_id = None
            return
        self._pr_comparison_selected_id = str(cid)
        try:
            j = campaign_ids.index(str(cid))
            cur = combo.current()
            if int(cur) != int(j):
                combo.current(j)
        except (ValueError, tk.TclError, TypeError):
            pass
        pv = getattr(self, "_pr_selection_preview_var", None)
        if pv is not None:
            pv.set(
                build_pr_selection_preview_line(
                    self.team,
                    self.season,
                    str(cid),
                    format_money=self._format_money,
                )
            )

    def _on_pr_comparison_pick(self, _event: Any = None) -> None:
        lb = getattr(self, "_pr_comparison_listbox", None)
        if lb is None:
            return
        sel = lb.curselection()
        if not sel:
            return
        self._sync_pr_comparison_row_to_chrome(int(sel[0]))

    def _on_pr_combo_pick_light(self, _event: Any = None) -> None:
        combo = getattr(self, "_pr_combo", None)
        campaign_ids = getattr(self, "_pr_campaign_ids", [])
        if combo is None or not campaign_ids:
            return
        try:
            ix = int(combo.current())
            if ix < 0 or ix >= len(campaign_ids):
                return
        except (tk.TclError, ValueError, TypeError):
            return
        want = str(campaign_ids[ix])
        self._pr_comparison_selected_id = want
        lb = getattr(self, "_pr_comparison_listbox", None)
        row_ids = getattr(self, "_pr_comparison_ids", [])
        if lb is not None and row_ids:
            for i, rid in enumerate(row_ids):
                if rid == want:
                    try:
                        lb.selection_clear(0, tk.END)
                        lb.selection_set(i)
                        lb.see(i)
                    except tk.TclError:
                        pass
                    break
        pv = getattr(self, "_pr_selection_preview_var", None)
        if pv is not None:
            pv.set(
                build_pr_selection_preview_line(
                    self.team,
                    self.season,
                    want,
                    format_money=self._format_money,
                )
            )

    def _on_pr_campaign_run(self) -> None:
        team = self.team
        if team is None:
            return
        combo = getattr(self, "_pr_combo", None)
        ids = getattr(self, "_pr_campaign_ids", [])
        if combo is None or not ids:
            return
        run_cid: Optional[str] = None
        lb = getattr(self, "_pr_comparison_listbox", None)
        comp_ids = getattr(self, "_pr_comparison_ids", [])
        if lb is not None and comp_ids:
            sel = lb.curselection()
            if sel:
                i = int(sel[0])
                if 0 <= i < len(comp_ids) and comp_ids[i]:
                    run_cid = str(comp_ids[i])
        if not run_cid:
            idx = combo.current()
            if idx < 0 or idx >= len(ids):
                messagebox.showwarning("広報・ファン", "施策を選択してください。")
                return
            run_cid = str(ids[idx])
        ok, msg = commit_pr_campaign(team, run_cid, self.season)
        if ok:
            messagebox.showinfo("広報・ファン", msg)
        else:
            messagebox.showwarning("広報・ファン", msg)
        self._refresh_finance_window()
        self.refresh()

    def _refresh_sponsor_finance_block(self) -> None:
        combo = getattr(self, "_sponsor_combo", None)
        hist_tw = getattr(self, "_sponsor_history_text", None)
        status_var = getattr(self, "_sponsor_status_var", None)
        apply_btn = getattr(self, "_sponsor_apply_btn", None)
        if combo is None or status_var is None:
            return
        if self.team is None:
            status_var.set(
                "契約：—\n"
                "スポンサー力：—\n"
                "反映：主に次オフ収入\n"
                "状態：詳細で確認\n"
                "\n"
                "（チーム未接続のため上記は表示できません。メイン画面でチームに接続してください。）"
            )
            try:
                combo.configure(state="disabled")
                if apply_btn is not None:
                    apply_btn.state(["disabled"])
            except tk.TclError:
                pass
            if hist_tw is not None:
                try:
                    hist_tw.configure(state="normal")
                    hist_tw.delete("1.0", tk.END)
                    hist_tw.insert("1.0", "（チーム未接続のため履歴はありません）")
                    hist_tw.configure(state="disabled")
                except tk.TclError:
                    pass
            return
        ensure_sponsor_management_on_team(self.team)
        cur = str(self.team.management.get("sponsors", {}).get("main_contract_type", "standard"))
        ids = getattr(self, "_sponsor_type_ids", [])
        team_id = int(getattr(self.team, "team_id", -1))
        sig = (team_id, cur)
        prev_sig = getattr(self, "_sponsor_finance_combo_sig", None)
        force_combo = prev_sig != sig
        if force_combo:
            for i, tid in enumerate(ids):
                if tid == cur:
                    try:
                        combo.current(i)
                    except tk.TclError:
                        pass
                    break
            self._sponsor_finance_combo_sig = sig
        else:
            try:
                sel_i = int(combo.current())
            except (tk.TclError, TypeError, ValueError):
                sel_i = -1
            if sel_i < 0 or sel_i >= len(ids):
                for i, tid in enumerate(ids):
                    if tid == cur:
                        try:
                            combo.current(i)
                        except tk.TclError:
                            pass
                        break
        sp = int(self._safe_get(self.team, "sponsor_power", 0))
        state_lbl = self._sponsor_finance_panel_state_label(self.team, cur)
        status_var.set(
            f"契約：{label_for_main_sponsor_type(cur)}\n"
            f"スポンサー力：{sp} ／ 100\n"
            "反映：主に次オフ収入\n"
            f"状態：{state_lbl}"
        )
        is_user = bool(getattr(self.team, "is_user_team", False))
        try:
            if is_user:
                combo.configure(state="readonly")
                if apply_btn is not None:
                    apply_btn.state(["!disabled"])
            else:
                combo.configure(state="disabled")
                if apply_btn is not None:
                    apply_btn.state(["disabled"])
        except tk.TclError:
            pass
        if hist_tw is not None:
            htext = "\n".join(format_sponsor_history_lines(self.team))
            if not str(htext).strip():
                htext = "履歴なし（メイン契約の変更履歴はまだありません）。"
            try:
                hist_tw.configure(state="normal")
                hist_tw.delete("1.0", tk.END)
                hist_tw.insert("1.0", htext)
                hist_tw.configure(state="disabled")
            except tk.TclError:
                pass

    def _refresh_pr_finance_block(self) -> None:
        combo = getattr(self, "_pr_combo", None)
        hist_tw = getattr(self, "_pr_history_text", None)
        status_var = getattr(self, "_pr_status_var", None)
        run_btn = getattr(self, "_pr_run_btn", None)
        if combo is None or status_var is None:
            return
        if self.team is None:
            status_var.set(
                "人気：—\n"
                "ファン基盤：—\n"
                "今ラウンド消化：— ／ —\n"
                "状態：詳細で確認\n"
                "\n"
                "（チーム未接続のため上記は表示できません。メイン画面でチームに接続してください。）"
            )
            try:
                combo.configure(state="disabled")
                if run_btn is not None:
                    run_btn.state(["disabled"])
            except tk.TclError:
                pass
            if hist_tw is not None:
                try:
                    hist_tw.configure(state="normal")
                    hist_tw.delete("1.0", tk.END)
                    hist_tw.insert("1.0", "（チーム未接続のため履歴はありません）")
                    hist_tw.configure(state="disabled")
                except tk.TclError:
                    pass
            return
        season = self.season
        line_a = format_pr_status_line(self.team, season)
        pop = int(self._safe_get(self.team, "popularity", 0))
        fb = int(self._safe_get(self.team, "fan_base", 0))
        sync_pr_round_quota(self.team, season)
        block = self.team.management.get("pr_campaigns") if isinstance(getattr(self.team, "management", None), dict) else {}
        used = int((block or {}).get("count_this_round", 0) or 0)
        state_lbl = self._pr_finance_panel_state_label(self.team, season)
        status_var.set(
            f"{line_a}\n"
            f"人気：{pop} ／ 100\n"
            f"ファン基盤：{fb:,}\n"
            f"今ラウンド消化：{used} ／ {MAX_ACTIONS_PER_ROUND} 回\n"
            f"状態：{state_lbl}"
        )
        is_user = bool(getattr(self.team, "is_user_team", False))
        _, allowed, _ = resolve_pr_round_context(season)
        try:
            if is_user and allowed:
                combo.configure(state="readonly")
                if run_btn is not None:
                    run_btn.state(["!disabled"])
            else:
                combo.configure(state="disabled")
                if run_btn is not None:
                    run_btn.state(["disabled"])
        except tk.TclError:
            pass
        if hist_tw is not None:
            htext = "\n".join(format_pr_history_lines(self.team))
            if not str(htext).strip():
                htext = "履歴なし（広報施策の実行履歴はまだありません）。"
            try:
                hist_tw.configure(state="normal")
                hist_tw.delete("1.0", tk.END)
                hist_tw.insert("1.0", htext)
                hist_tw.configure(state="disabled")
            except tk.TclError:
                pass

    def _on_merch_advance(self, product_id: str) -> None:
        team = self.team
        if team is None:
            return
        item = get_merchandise_item(team, product_id)
        if item is None:
            return
        ph = normalize_merchandise_phase_value(item.get("phase"))
        if ph == "on_sale":
            messagebox.showinfo("グッズ開発", "すでに発売中です。")
            return
        cost = int(ADVANCE_COST.get(ph, 0) or 0)
        if cost <= 0:
            return
        if not messagebox.askyesno(
            "グッズ開発",
            f"次の工程に進みますか？\n必要資金: {format_merchandise_advance_cost_yen_display(cost)}",
        ):
            return
        ok, msg = advance_merchandise_phase(team, product_id)
        if ok:
            messagebox.showinfo("グッズ開発", msg)
        else:
            messagebox.showwarning("グッズ開発", msg)
        self._refresh_finance_window()
        self.refresh()

    def _refresh_merchandise_finance_block(self) -> None:
        dummy_tw = getattr(self, "_merch_dummy_text", None)
        hist_tw = getattr(self, "_merch_hist_text", None)
        rows = getattr(self, "_merch_rows", None)
        sum_var = getattr(self, "_merch_summary_var", None)
        if not rows:
            return
        if self.team is None:
            if sum_var is not None:
                try:
                    sum_var.set(self._build_merch_panel_summary_text(None))
                except tk.TclError:
                    pass
            for row in rows:
                if len(row) >= 5:
                    _pid, var, _pvar, btn, dvar = row[:5]
                else:
                    _pid, var, _pvar, btn = row[:4]
                    dvar = None
                var.set("（チーム未接続）ライン状態は表示できません。")
                if dvar is not None:
                    try:
                        dvar.set("段階：— ｜ 次費用：— ｜ 状態：詳細で確認")
                    except tk.TclError:
                        pass
                try:
                    btn.state(["disabled"])
                except tk.TclError:
                    pass
            if dummy_tw is not None:
                try:
                    dummy_tw.configure(state="normal")
                    dummy_tw.delete("1.0", tk.END)
                    dummy_tw.insert("1.0", "（チーム未接続・ダミー売上は表示しません）")
                    dummy_tw.configure(state="disabled")
                except tk.TclError:
                    pass
            if hist_tw is not None:
                try:
                    hist_tw.configure(state="normal")
                    hist_tw.delete("1.0", tk.END)
                    hist_tw.insert("1.0", "（チーム未接続のため開発履歴はありません）")
                    hist_tw.configure(state="disabled")
                except tk.TclError:
                    pass
            return
        ensure_merchandise_on_team(self.team)
        is_user = bool(getattr(self.team, "is_user_team", False))
        if sum_var is not None:
            try:
                sum_var.set(self._build_merch_panel_summary_text(self.team))
            except tk.TclError:
                pass
        for row in rows:
            if len(row) >= 5:
                pid, var, _pvar, btn, dvar = row[:5]
            else:
                pid, var, _pvar, btn = row[:4]
                dvar = None
            item = get_merchandise_item(self.team, pid)
            if item is not None:
                var.set(format_merchandise_row_display(item))
            else:
                var.set("（ライン未取得）接続とデータを確認してください。")
            if dvar is not None:
                try:
                    dvar.set(self._merch_row_judgment_line(self.team, pid, item, is_user))
                except tk.TclError:
                    pass
            try:
                if not is_user or (item is not None and str(item.get("phase")) == "on_sale"):
                    btn.state(["disabled"])
                else:
                    btn.state(["!disabled"])
            except tk.TclError:
                pass
        if dummy_tw is not None:
            dtext = "\n".join(estimate_dummy_merch_sales_lines(self.team))
            if not str(dtext).strip():
                dtext = "ダミー売上の目安を算出できません（データ不足）。発売ラインができると表示されます。"
            try:
                dummy_tw.configure(state="normal")
                dummy_tw.delete("1.0", tk.END)
                dummy_tw.insert("1.0", dtext)
                dummy_tw.configure(state="disabled")
            except tk.TclError:
                pass
        if hist_tw is not None:
            htext = "\n".join(format_merchandise_history_lines(self.team))
            if not str(htext).strip():
                htext = "履歴なし（グッズ開発の履歴はまだありません）。"
            try:
                hist_tw.configure(state="normal")
                hist_tw.delete("1.0", tk.END)
                hist_tw.insert("1.0", htext)
                hist_tw.configure(state="disabled")
            except tk.TclError:
                pass

    def _refresh_finance_window(self) -> None:
        if getattr(self, "finance_header_var", None) is None:
            return

        profile = {}
        getter = getattr(self.team, "get_financial_profile", None)
        if callable(getter):
            try:
                profile = getter() or {}
            except Exception:
                profile = {}

        team_name = self._team_name()
        money = self._safe_get(self.team, "money", profile.get("money", 0))
        cashflow = self._safe_get(self.team, "cashflow_last_season", profile.get("cashflow_last_season", 0))

        if self.team is None:
            self.finance_header_var.set(
                "（チーム未接続）経営画面 — 下記は参照用のプレースホルダです"
            )
        else:
            self.finance_header_var.set(
                f"{team_name} 経営画面    所持金: {self._format_money(money)}    前季収支: {self._format_signed_money(cashflow)}"
            )

        pr_sel: Optional[str] = None
        pr_combo = getattr(self, "_pr_combo", None)
        pr_ids = getattr(self, "_pr_campaign_ids", None)
        if pr_combo is not None and pr_ids:
            try:
                pix = pr_combo.current()
                if 0 <= int(pix) < len(pr_ids):
                    pr_sel = str(pr_ids[int(pix)])
            except (tk.TclError, TypeError, ValueError):
                pr_sel = None

        sp_sel: Optional[str] = None
        sp_combo = getattr(self, "_sponsor_combo", None)
        sp_ids = getattr(self, "_sponsor_type_ids", None)
        if sp_combo is not None and sp_ids:
            try:
                six = sp_combo.current()
                if 0 <= int(six) < len(sp_ids):
                    sp_sel = str(sp_ids[int(six)])
            except (tk.TclError, TypeError, ValueError):
                sp_sel = None

        pr_sort_key = _PR_FINANCE_SORT_ORDER[0]
        psc = getattr(self, "_pr_sort_combo", None)
        if psc is not None:
            try:
                sxi = int(psc.current())
                if 0 <= sxi < len(_PR_FINANCE_SORT_ORDER):
                    pr_sort_key = _PR_FINANCE_SORT_ORDER[sxi]
            except (tk.TclError, TypeError, ValueError):
                pass
        pr_filter_key = _PR_FINANCE_FILTER_ORDER[0]
        pfc = getattr(self, "_pr_filter_combo", None)
        if pfc is not None:
            try:
                fxi = int(pfc.current())
                if 0 <= fxi < len(_PR_FINANCE_FILTER_ORDER):
                    pr_filter_key = _PR_FINANCE_FILTER_ORDER[fxi]
            except (tk.TclError, TypeError, ValueError):
                pass

        snap = build_management_menu_snapshot(
            self.team,
            self.season,
            format_money=self._format_money,
            format_signed_money=self._format_signed_money,
            selected_pr_campaign_id=pr_sel,
            selected_sponsor_type_id=sp_sel,
            pr_sort_mode=pr_sort_key,
            pr_filter_mode=pr_filter_key,
        )

        quick_summary_lines: List[str] = []
        if self.team is None:
            quick_summary_lines = [
                "【経営サマリー】",
                "・現在資金: 未設定（チーム未接続）",
                "・今季入金: 未設定（チーム未接続）",
                "・直近収支: 未設定（チーム未接続）",
                "・前季収支: 未設定（チーム未接続）",
            ]
        else:
            money_i = self._safe_int(self._safe_get(self.team, "money", profile.get("money", 0)))
            inseason_total_i = 0
            inseason_logs = self._safe_get(self.team, "inseason_cash_round_log", [])
            if isinstance(inseason_logs, list):
                for _entry in inseason_logs:
                    if isinstance(_entry, dict):
                        inseason_total_i += self._safe_int(_entry.get("amount", 0))
            cashflow_i = self._safe_int(
                self._safe_get(self.team, "cashflow_last_season", profile.get("cashflow_last_season", 0))
            )

            history = self._safe_get(self.team, "finance_history", [])
            latest_rev: Optional[int] = None
            latest_exp: Optional[int] = None
            latest_cf: Optional[int] = None
            if isinstance(history, list):
                for _row in reversed(history):
                    if isinstance(_row, dict):
                        latest_rev = self._safe_int(_row.get("revenue", 0))
                        latest_exp = self._safe_int(_row.get("expense", 0))
                        latest_cf = self._safe_int(_row.get("cashflow", latest_rev - latest_exp))
                        break

            inseason_line = (
                f"・今季入金: {self._format_money(inseason_total_i)}"
                if inseason_total_i > 0
                else "・今季入金: 記録なし"
            )
            if latest_rev is None or latest_exp is None or latest_cf is None:
                latest_line = "・直近収支: 履歴なし"
            else:
                latest_line = (
                    f"・直近収支: 収入 {self._format_money(latest_rev)} / "
                    f"支出 {self._format_money(latest_exp)} / "
                    f"差引 {self._format_signed_money(latest_cf)}"
                )

            quick_summary_lines = [
                "【経営サマリー】",
                f"・現在資金: {self._format_money(money_i)}",
                inseason_line,
                latest_line,
                f"・前季収支: {self._format_signed_money(cashflow_i)}",
            ]

        dash_tw = getattr(self, "_management_dashboard_text", None)
        if dash_tw is not None:
            try:
                dash_tw.configure(state="normal")
                dash_tw.delete("1.0", tk.END)
                fin_lines = getattr(snap, "dashboard_finance_lines", None)
                if not (
                    fin_lines
                    and self._apply_compact_management_dashboard_text(
                        dash_tw, snap, quick_summary_lines
                    )
                ):
                    dash_tw.insert("1.0", snap.dashboard_text)
                dash_tw.configure(state="disabled")
            except tk.TclError:
                pass

        fsum_lines = getattr(self, "finance_summary_lines", None) or []
        for var, line in zip(fsum_lines, snap.finance_lines):
            var.set(line)

        cap_tw = getattr(self, "_finance_cap_text", None)
        if cap_tw is not None:
            if self.team is not None:
                try:
                    cap_body = format_salary_cap_text(self.team)
                except Exception:
                    cap_body = "サラリーキャップ情報を取得できませんでした。"
            else:
                cap_body = "チームが未接続です。"
            try:
                cap_tw.configure(state="normal")
                cap_tw.delete("1.0", tk.END)
                cap_tw.insert("1.0", cap_body)
                cap_tw.configure(state="disabled")
            except tk.TclError:
                pass

        in_tw = getattr(self, "_finance_inseason_log_text", None)
        if in_tw is not None:
            if self.team is None:
                in_body = (
                    "（チーム未接続）\n"
                    "シーズン中の記録は、チーム接続後にここに表示されます。"
                )
            else:
                from basketball_sim.systems.finance_report_display import format_inseason_cash_round_log_lines

                in_body = "\n".join(format_inseason_cash_round_log_lines(self.team))
            try:
                in_tw.configure(state="normal")
                in_tw.delete("1.0", tk.END)
                in_tw.insert("1.0", in_body)
                in_tw.configure(state="disabled")
            except tk.TclError:
                pass

        fac_line_widgets = getattr(self, "facility_lines", None) or []
        for var, line in zip(fac_line_widgets, snap.facility_lines):
            var.set(line)

        fp_vars = getattr(self, "_facility_preview_vars", None)
        if isinstance(fp_vars, dict) and fp_vars:
            fac_prev_map = dict(snap.facility_action_previews)
            for fk, pv in fp_vars.items():
                try:
                    pv.set(fac_prev_map.get(fk, "—"))
                except tk.TclError:
                    pass

        self._refresh_facility_management_card_vars(snap)

        sp_preview = getattr(self, "_sponsor_preview_var", None)
        if sp_preview is not None:
            try:
                sp_preview.set(snap.sponsor_apply_preview)
            except tk.TclError:
                pass

        pr_preview = getattr(self, "_pr_selection_preview_var", None)
        if pr_preview is not None:
            try:
                pr_preview.set(snap.pr_selection_preview)
            except tk.TclError:
                pass

        lb = getattr(self, "_pr_comparison_listbox", None)
        if lb is not None:
            prev_pick = getattr(self, "_pr_comparison_selected_id", None)
            try:
                lb.delete(0, tk.END)
            except tk.TclError:
                pass
            self._pr_comparison_ids = [c for c, _ in snap.pr_comparison_entries]
            for _cid, line in snap.pr_comparison_entries:
                try:
                    lb.insert(tk.END, line)
                except tk.TclError:
                    pass
            sel_i = -1
            if prev_pick:
                for i, cid in enumerate(self._pr_comparison_ids):
                    if cid and cid == prev_pick:
                        sel_i = i
                        break
            if sel_i < 0:
                for i, cid in enumerate(self._pr_comparison_ids):
                    if cid:
                        sel_i = i
                        break
            if sel_i >= 0:
                try:
                    lb.selection_set(sel_i)
                    lb.see(sel_i)
                except tk.TclError:
                    pass
                self._sync_pr_comparison_row_to_chrome(sel_i)
            if self.team is None:
                try:
                    psc2 = getattr(self, "_pr_sort_combo", None)
                    pfc2 = getattr(self, "_pr_filter_combo", None)
                    if psc2 is not None:
                        psc2.configure(state="disabled")
                    if pfc2 is not None:
                        pfc2.configure(state="disabled")
                except tk.TclError:
                    pass
            else:
                try:
                    psc2 = getattr(self, "_pr_sort_combo", None)
                    pfc2 = getattr(self, "_pr_filter_combo", None)
                    if psc2 is not None:
                        psc2.configure(state="readonly")
                    if pfc2 is not None:
                        pfc2.configure(state="readonly")
                except tk.TclError:
                    pass

        btns = getattr(self, "_facility_upgrade_buttons", None)
        if isinstance(btns, dict) and btns:
            is_user = self.team is not None and bool(getattr(self.team, "is_user_team", False))
            for fk, b in btns.items():
                try:
                    if not is_user:
                        b.state(["disabled"])
                    else:
                        can_do, _ = can_commit_facility_upgrade(self.team, fk)
                        b.state(["!disabled"] if can_do else ["disabled"])
                except tk.TclError:
                    pass

        owner_body = ""
        if self.team is None:
            owner_body = (
                snap.owner_preamble
                + "\n\n"
                "（チームがメイン画面から未接続です）\n"
                "オーナー期待・信頼・ミッションは、チーム接続後にここに表示されます。"
            )
        else:
            om_getter = getattr(self.team, "get_owner_mission_report_text", None)
            core = ""
            if callable(om_getter):
                try:
                    core = str(om_getter() or "")
                except Exception:
                    core = ""
            if not core.strip():
                owner_expectation = self._safe_get(
                    self.team, "owner_expectation", profile.get("owner_expectation", "-")
                )
                owner_trust = self._safe_get(self.team, "owner_trust", profile.get("owner_trust", "-"))
                core = (
                    f"オーナー期待値: {owner_expectation}\n"
                    f"オーナー信頼: {self._safe_int_text(owner_trust)} / 100\n"
                    "（詳細テキストを取得できませんでした）"
                )
            owner_body = snap.owner_preamble + "\n" + core
        ow = getattr(self, "owner_report_text", None)
        if ow is not None:
            try:
                ow.configure(state="normal")
                ow.delete("1.0", tk.END)
                ow.insert("1.0", owner_body)
                ow.configure(state="disabled")
            except tk.TclError:
                pass

        report_body = ""
        if self.team is None:
            report_body = (
                "（チーム未接続）\n"
                "接続後は、前季までの収入内訳・支出内訳・財務推移が表示されます。\n"
                "オフシーズン締め後に内訳スナップショットが記録されている場合は、その内容がここに出ます。"
            )
        else:
            detail_getter = getattr(self.team, "get_finance_report_detail_text", None)
            if callable(detail_getter):
                try:
                    report_body = str(detail_getter() or "")
                except Exception:
                    report_body = ""
            if not report_body.strip():
                from basketball_sim.systems.finance_report_display import format_finance_report_detail_lines

                report_body = "\n".join(format_finance_report_detail_lines(self.team))
        tw = getattr(self, "finance_report_text", None)
        if tw is not None:
            try:
                tw.configure(state="normal")
                tw.delete("1.0", tk.END)
                tw.insert("1.0", report_body)
                tw.configure(state="disabled")
            except tk.TclError:
                pass

        self._refresh_sponsor_finance_block()
        self._refresh_pr_finance_block()
        self._refresh_merchandise_finance_block()

        merch_prev_map = dict(snap.merch_line_previews)
        mrows = getattr(self, "_merch_rows", None)
        if mrows:
            for row in mrows:
                pid = row[0]
                mpv = row[2]
                try:
                    mpv.set(merch_prev_map.get(pid, "—"))
                except tk.TclError:
                    pass

        self.finance_hint_var.set(
            "※この画面は現状確認・一部投資操作・案内を担当します。"
            "収支の正本反映はオフシーズン財務締め、施設投資の支出は実行時に反映されます。"
            "グッズ売上表示は簡易ダミーです。"
        )

        self._update_finance_window_scrollregion()

    def open_strategy_window(self) -> None:
        """Open a safe read-only strategy / rotation subwindow."""
        existing = getattr(self, "_strategy_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_strategy_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"戦術メニュー - {self._team_name()}")
        window.geometry("980x720")
        window.minsize(860, 580)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.strategy_header_var = tk.StringVar(value="")
        self.strategy_hint_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.strategy_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        if self.team is not None:
            try:
                ensure_team_tactics_on_team(self.team)
            except Exception:
                pass

        nav = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 0, 0, 8))
        nav.pack(fill="x")
        ttk.Label(
            nav,
            text=(
                "戦術は大きく「プレイスタイル」と「ローテーション」に分けて設定します。\n"
                "プレイスタイルは試合の戦い方、ローテーションは起用と役割を調整します。\n"
                "下段は Team 状態の参照のみです。詳細編集は上の2ボタンから開きます。"
            ),
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        hub_ref = window

        def _strat_parent() -> tk.Misc:
            try:
                if hub_ref is not None and hub_ref.winfo_exists():
                    return hub_ref
            except Exception:
                pass
            return self.root

        row_hub = ttk.Frame(nav, style="Panel.TFrame")
        row_hub.pack(fill="x", pady=(0, 4))
        ttk.Button(
            row_hub,
            text="プレイスタイル",
            style="Menu.TButton",
            width=22,
            command=lambda: self._open_tactics_playstyle_overview_window(hub_ref),
        ).pack(side="left", padx=(0, 8), pady=2)
        ttk.Button(
            row_hub,
            text="ローテーション",
            style="Menu.TButton",
            width=22,
            command=lambda: self._open_tactics_rotation_overview_window(hub_ref),
        ).pack(side="left", padx=0, pady=2)

        scroll_wrap = ttk.Frame(outer, style="Root.TFrame")
        scroll_wrap.pack(fill="both", expand=True)

        strat_canvas = tk.Canvas(
            scroll_wrap,
            bg="#15171c",
            highlightthickness=0,
        )
        strat_vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=strat_canvas.yview)
        strat_canvas.configure(yscrollcommand=strat_vsb.set)

        content = ttk.Frame(strat_canvas, style="Root.TFrame")
        strat_canvas_win = strat_canvas.create_window((0, 0), window=content, anchor="nw")

        def _strategy_scrollregion(_event: Any = None) -> None:
            strat_canvas.update_idletasks()
            bbox = strat_canvas.bbox("all")
            if bbox:
                strat_canvas.configure(scrollregion=bbox)

        def _strategy_canvas_inner_width(event: Any) -> None:
            try:
                strat_canvas.itemconfigure(strat_canvas_win, width=event.width)
            except tk.TclError:
                pass

        content.bind("<Configure>", lambda _e: _strategy_scrollregion())
        strat_canvas.bind("<Configure>", _strategy_canvas_inner_width)

        def _strategy_hub_mousewheel(event: Any) -> None:
            if getattr(event, "delta", 0):
                strat_canvas.yview_scroll(int(-event.delta / 120), "units")

        window.bind("<MouseWheel>", _strategy_hub_mousewheel)
        window.bind("<Button-4>", lambda _e: strat_canvas.yview_scroll(-1, "units"))
        window.bind("<Button-5>", lambda _e: strat_canvas.yview_scroll(1, "units"))

        strat_canvas.pack(side="left", fill="both", expand=True)
        strat_vsb.pack(side="right", fill="y")
        self._strategy_scroll_canvas = strat_canvas

        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=0)
        content.rowconfigure(1, weight=0)

        strategy_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        strategy_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        lineup_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        lineup_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        notes_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        notes_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")

        ttk.Label(strategy_panel, text="チーム概要（参照のみ）", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Label(lineup_panel, text="スタメン・控え（参照のみ）", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Label(notes_panel, text="案内", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 8))

        self.strategy_lines = []
        for _ in range(6):
            var = tk.StringVar(value="")
            self.strategy_lines.append(var)
            tk.Label(
                strategy_panel,
                textvariable=var,
                bg="#1d2129",
                fg="#eef2f7",
                justify="left",
                anchor="w",
                font=("Yu Gothic UI", 10),
                padx=2,
                pady=2,
            ).pack(fill="x", anchor="w")

        ttk.Separator(strategy_panel, orient="horizontal").pack(fill="x", pady=(12, 8))
        ttk.Label(
            strategy_panel,
            text=(
                "Team.strategy / coach_style / Team.usage_policy（試合・ローテに反映）は、"
                "「プレイスタイル」統合画面の補助ボタン「補助設定を開く（Team基本方針・HC）」から。"
                "攻守の傾向・セット傾向は team_tactics（同統合画面の 1〜6・7 で直接編集、別設定）。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=440,
        ).pack(anchor="w", pady=(0, 6))

        self.lineup_lines = []
        for _ in range(10):
            var = tk.StringVar(value="")
            self.lineup_lines.append(var)
            tk.Label(
                lineup_panel,
                textvariable=var,
                bg="#1d2129",
                fg="#eef2f7",
                justify="left",
                anchor="w",
                font=("Yu Gothic UI", 10),
                padx=2,
                pady=2,
            ).pack(fill="x", anchor="w")

        ttk.Separator(lineup_panel, orient="horizontal").pack(fill="x", pady=(10, 8))

        self.strat_jp_block_var = tk.StringVar(value="")
        tk.Label(
            lineup_panel,
            textvariable=self.strat_jp_block_var,
            bg="#1d2129",
            fg="#c8d0dc",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 9),
            padx=2,
            pady=4,
            wraplength=420,
        ).pack(fill="x", anchor="w")
        self.strat_starter_warn_var = tk.StringVar(value="")
        tk.Label(
            lineup_panel,
            textvariable=self.strat_starter_warn_var,
            bg="#1d2129",
            fg="#e8a035",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 9),
            padx=2,
            wraplength=420,
        ).pack(fill="x", anchor="w", pady=(0, 6))

        ttk.Label(
            lineup_panel,
            text=(
                "Team の先発・6th・ベンチは、「ローテーション」統合画面の「2. 起用序列」で編集します。"
                "交代・疲労・終盤・戦術先発・目標出場などの細部は、同画面の補助ボタン「ローテ詳細」から"
                "（team_tactics、Team 先発と分離のまま）。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=440,
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            notes_panel,
            textvariable=self.strategy_hint_var,
            bg="#1d2129",
            fg="#d6dbe3",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=2,
        ).pack(fill="x", anchor="w")

        ttk.Button(
            outer,
            text="閉じる",
            style="Menu.TButton",
            command=window.destroy,
        ).pack(anchor="e", pady=(12, 0))

        self._strategy_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_strategy_window)
        self._refresh_strategy_window()

    def _on_close_strategy_window(self) -> None:
        window = getattr(self, "_strategy_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._strategy_window = None
            self._strategy_scroll_canvas = None

    def _update_strategy_window_scrollregion(self) -> None:
        canvas = getattr(self, "_strategy_scroll_canvas", None)
        if canvas is None:
            return
        try:
            if not canvas.winfo_exists():
                return
        except tk.TclError:
            return
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    def _update_finance_window_scrollregion(self) -> None:
        canvas = getattr(self, "_finance_scroll_canvas", None)
        if canvas is None:
            return
        try:
            if not canvas.winfo_exists():
                return
        except tk.TclError:
            return
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    def _refresh_strategy_window(self) -> None:
        if not hasattr(self, "strategy_header_var"):
            return

        strategy_key = self._safe_get(self.team, "strategy", None)
        coach_key = self._safe_get(self.team, "coach_style", None)
        usage_key = self._safe_get(self.team, "usage_policy", None)

        strategy_text = self.STRATEGY_LABELS.get(str(strategy_key), str(strategy_key or "-"))
        coach_text = self.COACH_STYLE_LABELS.get(str(coach_key), str(coach_key or "-"))
        usage_text = self.USAGE_POLICY_LABELS.get(str(usage_key), str(usage_key or "-"))

        starters = self._get_starting_five_players()
        sixth_man = self._get_sixth_man_player()
        bench_order = self._get_bench_order_players()

        self.strategy_header_var.set(f"{self._team_name()} 戦術メニュー（詳細ハブ）")

        strategy_lines = [
            f"基本戦術 (Team.strategy): {strategy_text}",
            f"HCスタイル: {coach_text}",
            f"基本起用 (Team.usage_policy): {usage_text}",
            f"ロスター人数: {len(list(self._safe_get(self.team, 'players', []) or []))}",
            f"先発人数: {len(starters)} / ベンチ序列人数: {len(bench_order)}",
            "team_tactics: 「プレイスタイル」「ローテーション」統合画面のボタンから（試合参照は項目による）。"
            "人事「タグ:」は自動役割タグ。",
        ]
        for var, line in zip(self.strategy_lines, strategy_lines):
            var.set(line)

        lineup_lines = ["先発:"]
        if starters:
            for idx, player in enumerate(starters, 1):
                lineup_lines.append(f"  {idx}. {self._format_player_brief(player)}")
        else:
            lineup_lines.append("  未設定")

        lineup_lines.append("")
        lineup_lines.append("6thマン:")
        lineup_lines.append(f"  {self._format_player_brief(sixth_man)}" if sixth_man is not None else "  未設定")

        lineup_lines.append("")
        lineup_lines.append("ベンチ序列:")
        if bench_order:
            for idx, player in enumerate(bench_order, 1):
                lineup_lines.append(f"  {idx}. {self._format_player_brief(player)}")
        else:
            lineup_lines.append("  未設定")

        while len(lineup_lines) < len(self.lineup_lines):
            lineup_lines.append("")
        for var, line in zip(self.lineup_lines, lineup_lines[: len(self.lineup_lines)]):
            var.set(line)

        self.strategy_hint_var.set(
            "プレイスタイル… 統合画面内で 0〜7 を編集。Team 側の補助は「補助設定を開く（Team基本方針・HC）」から。"
            "ローテーション… 統合画面内で起用プリセット・起用方針・起用序列を編集。"
            "人事の自動「タグ:」ではない。下段は参照のみ。"
        )

        jp_blk = getattr(self, "strat_jp_block_var", None)
        jp_warn = getattr(self, "strat_starter_warn_var", None)
        if jp_blk is not None and self.team is not None:
            try:
                ct = jp_reg_display.gui_next_competition_type(self.season, self.team)
                jp_blk.set(
                    jp_reg_display.format_contract_roster_summary(self.team)
                    + "\n\n"
                    + jp_reg_display.format_competition_rules_brief(ct)
                )
            except Exception:
                jp_blk.set("")
        if jp_warn is not None and self.team is not None:
            try:
                ct = jp_reg_display.gui_next_competition_type(self.season, self.team)
                jp_warn.set(jp_reg_display.format_starting_lineup_caution(self.team, ct))
            except Exception:
                jp_warn.set("")

        if hasattr(self, "_strat_combo_lineup_slot"):
            self._sync_strat_lineup_edit()
            self._sync_strat_sixth_edit()
            self._sync_strat_bench_edit()

        self._update_strategy_window_scrollregion()

    def _tactics_roster_player_ids(self) -> set:
        ids: set = set()
        for p in self._safe_get(self.team, "players", []) or []:
            pid = getattr(p, "player_id", None)
            if pid is None:
                continue
            try:
                ids.add(int(pid))
            except (TypeError, ValueError):
                continue
        return ids

    def _tactics_commit_payload(self, payload: Dict[str, Any]) -> None:
        if self.team is None:
            return
        pids = self._tactics_roster_player_ids()
        merged = dict(payload)
        # preset_meta は team_tactics["version"]（スキーマ版）とは別ブロック。payload に無い経路でも落とさない。
        if "preset_meta" not in merged:
            prev = getattr(self.team, "team_tactics", None)
            if isinstance(prev, dict) and isinstance(prev.get("preset_meta"), dict):
                merged["preset_meta"] = dict(prev["preset_meta"])
        self.team.team_tactics = normalize_team_tactics(merged, valid_player_ids=pids if pids else None)

    _TEAM_STRATEGY_EDITOR_KEYS: Tuple[str, ...] = (
        "offense_tempo",
        "offense_style",
        "offense_creation",
        "defense_style",
        "rebound_style",
        "transition_style",
    )

    _PLAYBOOK_LEVEL_PAIRS: Tuple[Tuple[str, str], ...] = (
        ("low", "少ない"),
        ("standard", "標準"),
        ("high", "多い"),
    )
    _PLAYBOOK_EDITOR_KEYS: Tuple[Tuple[str, str], ...] = (
        ("pick_and_roll", "P&R"),
        ("handoff", "ハンドオフ"),
        ("off_ball_screen", "オフボールスクリーン"),
        ("post_up", "ポストアップ"),
        ("spain_pick_and_roll", "Spain P&R"),
        ("transition", "速攻頻度"),
    )

    def _team_strategy_pairs_map_and_labels(
        self,
    ) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, str]]:
        pairs_map: Dict[str, List[Tuple[str, str]]] = {
            "offense_tempo": [("slow", "スロー"), ("standard", "標準"), ("fast", "アップテンポ")],
            "offense_style": [
                ("balanced", "バランス"),
                ("inside", "ペイント重視"),
                ("three_point", "3P重視"),
                ("drive", "ドライブ重視"),
            ],
            "offense_creation": [
                ("ball_move", "ボールムーブ"),
                ("pick_and_roll", "P&R中心"),
                ("iso", "アイソレーション中心"),
                ("post", "ポスト起点"),
            ],
            "defense_style": [
                ("balanced", "バランス"),
                ("protect_three", "3P警戒"),
                ("protect_paint", "ペイント保護"),
                ("pressure", "プレッシャー強め"),
            ],
            "rebound_style": [
                ("get_back", "戻り優先"),
                ("balanced", "バランス"),
                ("crash_offense", "積極参加"),
            ],
            "transition_style": [
                ("push", "速攻重視"),
                ("situational", "状況判断"),
                ("half_court", "ハーフコート優先"),
            ],
        }
        labels: Dict[str, str] = {
            "offense_tempo": "1. 試合テンポ",
            "offense_style": "2. 攻撃の狙い",
            "offense_creation": "3. 攻撃の起点",
            "defense_style": "4. 守備の狙い",
            "rebound_style": "5. オフェンスリバウンド",
            "transition_style": "6. トランジション",
        }
        return pairs_map, labels

    def _team_strategy_editor_set_combo(
        self, combo: ttk.Combobox, pairs: List[Tuple[str, str]], cur: str
    ) -> None:
        vals = [b for _, b in pairs]
        combo["values"] = vals
        internals = [a for a, _ in pairs]
        combo.set(vals[internals.index(cur)] if cur in internals else vals[0])

    def _team_strategy_editor_build_row_combos(
        self,
        parent: ttk.Frame,
        data: Dict[str, str],
        pairs_map: Dict[str, List[Tuple[str, str]]],
        labels: Dict[str, str],
    ) -> Dict[str, ttk.Combobox]:
        combos: Dict[str, ttk.Combobox] = {}
        for key in self._TEAM_STRATEGY_EDITOR_KEYS:
            row = ttk.Frame(parent, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=labels[key], width=24).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=28)
            cb.pack(side="left", padx=6)
            self._team_strategy_editor_set_combo(cb, pairs_map[key], str(data.get(key, "")))
            combos[key] = cb
        return combos

    def _team_strategy_editor_collect(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for key, cb in combos.items():
            pairs = pairs_map[key]
            disp = cb.get()
            for a, b in pairs:
                if b == disp:
                    out[key] = a
                    break
            else:
                out[key] = pairs[0][0]
        return out

    def _team_strategy_editor_reset_display(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        d = get_default_team_tactics()["team_strategy"]
        for k, cb in combos.items():
            self._team_strategy_editor_set_combo(cb, pairs_map[k], str(d.get(k, "")))

    def _team_strategy_editor_reload_from_team(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        if self.team is None:
            return
        data = get_safe_team_tactics(self.team)["team_strategy"]
        for k, cb in combos.items():
            self._team_strategy_editor_set_combo(cb, pairs_map[k], str(data.get(k, "")))

    def _team_strategy_editor_save(
        self,
        combos: Dict[str, ttk.Combobox],
        pairs_map: Dict[str, List[Tuple[str, str]]],
        *,
        message_parent: tk.Misc,
        message_title: str = "保存",
        message_body: str = "プレイスタイル（攻守の傾向）を保存しました。",
    ) -> None:
        if self.team is None:
            return
        raw = dict(get_safe_team_tactics(self.team))
        raw["team_strategy"] = self._team_strategy_editor_collect(combos, pairs_map)
        self._tactics_commit_payload(raw)
        messagebox.showinfo(message_title, message_body, parent=message_parent)
        self._refresh_strategy_window()

    _USAGE_POLICY_EDITOR_KEYS: Tuple[str, ...] = (
        "priority",
        "evaluation_focus",
        "form_weight",
        "age_balance",
        "injury_care",
        "schedule_care",
        "foreign_player_usage",
    )
    # foreign_player_usage は GUI に出さない。保存時に既存 team_tactics.usage_policy をマージし維持。
    # evaluation_focus の potential は候補から外し、表示上は overall に寄せる（保存で overall として確定可）。
    _USAGE_POLICY_EDITOR_DISPLAY_KEYS: Tuple[str, ...] = (
        "priority",
        "evaluation_focus",
        "form_weight",
        "age_balance",
        "injury_care",
        "schedule_care",
    )

    @staticmethod
    def _usage_policy_value_for_combo_display(data: Dict[str, str], key: str) -> str:
        """候補にない内部値（例: potential）は表示用に置き換える。"""
        v = str(data.get(key, "") or "")
        if key == "evaluation_focus" and v == "potential":
            return "overall"
        return v

    def _usage_policy_pairs_map_and_labels(
        self,
    ) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, str]]:
        pairs_map: Dict[str, List[Tuple[str, str]]] = {
            "priority": [("win", "勝利優先"), ("balanced", "バランス"), ("development", "育成優先")],
            "evaluation_focus": [
                ("overall", "総合力重視"),
                ("offense", "攻撃力重視"),
                ("defense", "守備力重視"),
            ],
            "form_weight": [("high", "調子を強く反映"), ("standard", "標準"), ("skill", "実力を優先")],
            "age_balance": [("veteran", "ベテラン優先"), ("balanced", "バランス"), ("youth", "若手優先")],
            "injury_care": [
                ("high", "無理を避けやすい"),
                ("standard", "標準"),
                ("low", "やや踏み込む"),
            ],
            "schedule_care": [("rest", "休養重視"), ("standard", "標準"), ("win", "勝利優先")],
            "foreign_player_usage": [
                ("stars", "主力として最大活用"),
                ("balanced", "バランス運用"),
                ("japan_core", "日本人中心"),
            ],
        }
        labels: Dict[str, str] = {
            "priority": "起用方針",
            "evaluation_focus": "評価基準",
            "form_weight": "調子の反映",
            "age_balance": "年齢/育成寄り補助",
            "injury_care": "ケガ配慮",
            "schedule_care": "連戦配慮",
            "foreign_player_usage": "外国籍起用補助",
        }
        return pairs_map, labels

    def _usage_policy_editor_set_combo(
        self, combo: ttk.Combobox, pairs: List[Tuple[str, str]], cur: str
    ) -> None:
        vals = [b for _, b in pairs]
        combo["values"] = vals
        internals = [a for a, _ in pairs]
        combo.set(vals[internals.index(cur)] if cur in internals else vals[0])

    def _usage_policy_editor_add_notes(
        self,
        parent: ttk.Frame,
        key: str,
        *,
        wraplength: int,
    ) -> None:
        if key == "form_weight":
            note = ttk.Frame(parent, style="Panel.TFrame")
            note.pack(fill="x", pady=(4, 0))
            ttk.Label(
                note,
                text="好不調の独立した数値は使わず、疲労の見方をベースにします。",
                wraplength=wraplength,
            ).pack(anchor="w")
            ttk.Label(
                note,
                text="出番・交代の判断で、疲労をどれだけ重く見るかの微調整です（v1）。",
                wraplength=wraplength,
            ).pack(anchor="w", pady=(2, 0))
        if key == "age_balance":
            note = ttk.Frame(parent, style="Panel.TFrame")
            note.pack(fill="x", pady=(4, 0))
            ttk.Label(
                note,
                text="若手・中堅・ベテラン三帯に、出番の薄い補正をかけます。プレイスタイル基本方針（Team起用）を上書きせず、年齢の寄せを微調整します。",
                wraplength=wraplength,
            ).pack(anchor="w")
        if key == "injury_care":
            note = ttk.Frame(parent, style="Panel.TFrame")
            note.pack(fill="x", pady=(4, 0))
            ttk.Label(
                note,
                text="負傷の発生率を直接変える設定ではありません。疲労と体力の状態に応じ、起用の無理の度合いを少し調整します。",
                wraplength=wraplength,
            ).pack(anchor="w")
        if key == "foreign_player_usage":
            note = ttk.Frame(parent, style="Panel.TFrame")
            note.pack(fill="x", pady=(4, 0))
            ttk.Label(
                note,
                text="大会の登録枠・コート上の枠数そのものは変えません。",
                wraplength=wraplength,
            ).pack(anchor="w")
            ttk.Label(
                note,
                text="ルール上最も出せる範囲のなかで、起用をどのくらい外国籍寄りにするかの補正です。",
                wraplength=wraplength,
            ).pack(anchor="w", pady=(2, 0))
        if key == "evaluation_focus":
            note = ttk.Frame(parent, style="Panel.TFrame")
            note.pack(fill="x", pady=(4, 0))
            ttk.Label(
                note,
                text="総合力の本流評価を置き換えるのではなく、候補同士の見方を少しだけ寄せます。",
                wraplength=wraplength,
            ).pack(anchor="w")
            ttk.Label(
                note,
                text="攻撃寄り / 守備寄り / 平均の好み補正で、OVRそのものを上書きするものではありません。",
                wraplength=wraplength,
            ).pack(anchor="w", pady=(2, 0))

    def _usage_policy_editor_build_row_combos(
        self,
        parent: ttk.Frame,
        data: Dict[str, str],
        pairs_map: Dict[str, List[Tuple[str, str]]],
        labels: Dict[str, str],
        *,
        include_notes: bool,
        note_wraplength: int,
        label_width: int = 20,
    ) -> Dict[str, ttk.Combobox]:
        combos: Dict[str, ttk.Combobox] = {}
        for key in self._USAGE_POLICY_EDITOR_DISPLAY_KEYS:
            if include_notes:
                self._usage_policy_editor_add_notes(parent, key, wraplength=note_wraplength)
            row = ttk.Frame(parent, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=labels[key], width=label_width).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=28)
            cb.pack(side="left", padx=6)
            self._usage_policy_editor_set_combo(
                cb, pairs_map[key], self._usage_policy_value_for_combo_display(data, key)
            )
            combos[key] = cb
        return combos

    def _usage_policy_editor_collect(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for key, cb in combos.items():
            disp = cb.get()
            for a, b in pairs_map[key]:
                if b == disp:
                    out[key] = a
                    break
            else:
                out[key] = pairs_map[key][0][0]
        return out

    def _usage_policy_editor_reload_from_team(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        if self.team is None:
            return
        data = get_safe_team_tactics(self.team)["usage_policy"]
        for key, cb in combos.items():
            self._usage_policy_editor_set_combo(
                cb, pairs_map[key], self._usage_policy_value_for_combo_display(data, key)
            )

    def _usage_policy_editor_reset_display(
        self, combos: Dict[str, ttk.Combobox], pairs_map: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        d = get_default_team_tactics()["usage_policy"]
        for key, cb in combos.items():
            self._usage_policy_editor_set_combo(cb, pairs_map[key], str(d.get(key, "")))

    def _usage_policy_editor_save(
        self,
        combos: Dict[str, ttk.Combobox],
        pairs_map: Dict[str, List[Tuple[str, str]]],
        *,
        message_parent: tk.Misc,
        message_title: str = "保存",
        message_body: str = "起用方針テンプレ（usage_policy）を保存しました。",
        after_save: Optional[Callable[[], None]] = None,
    ) -> None:
        if self.team is None:
            return
        # GUI 非表示のキー（foreign_player_usage 等）を消さないよう、既存 usage_policy に上書きマージする。
        # evaluation_focus=potential は候補にないため表示は overall 寄せ、保存内容はコンボ通り（通常 overall）。
        raw = dict(get_safe_team_tactics(self.team))
        base_up: Dict[str, str] = dict((raw.get("usage_policy") or {}))
        collected = self._usage_policy_editor_collect(combos, pairs_map)
        base_up.update(collected)
        raw["usage_policy"] = base_up
        self._tactics_commit_payload(raw)
        messagebox.showinfo(message_title, message_body, parent=message_parent)
        if after_save is not None:
            after_save()

    def _playbook_editor_set_combo(
        self, cb: ttk.Combobox, level_pairs: Sequence[Tuple[str, str]], cur: str
    ) -> None:
        vals = [b for _, b in level_pairs]
        internals = [a for a, _ in level_pairs]
        cb["values"] = vals
        cb.set(vals[internals.index(cur)] if cur in internals else vals[1])

    def _playbook_editor_build_row_combos(
        self, parent: ttk.Frame, data_pb: Dict[str, Any]
    ) -> Dict[str, ttk.Combobox]:
        level_pairs = self._PLAYBOOK_LEVEL_PAIRS
        combos: Dict[str, ttk.Combobox] = {}
        for key, jlabel in self._PLAYBOOK_EDITOR_KEYS:
            row = ttk.Frame(parent, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=jlabel, width=24).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=12)
            cb.pack(side="left", padx=6)
            self._playbook_editor_set_combo(cb, level_pairs, str(data_pb.get(key, "standard")))
            combos[key] = cb
        return combos

    def _playbook_editor_collect(
        self, combos: Dict[str, ttk.Combobox], level_pairs: Sequence[Tuple[str, str]]
    ) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for key, cb in combos.items():
            disp = cb.get()
            for a, b in level_pairs:
                if b == disp:
                    out[key] = a
                    break
            else:
                out[key] = "standard"
        return out

    def _playbook_editor_reload_from_team(
        self, combos: Dict[str, ttk.Combobox], level_pairs: Sequence[Tuple[str, str]]
    ) -> None:
        if self.team is None:
            return
        pb = get_safe_team_tactics(self.team)["playbook"]
        for k, cb in combos.items():
            self._playbook_editor_set_combo(cb, level_pairs, str(pb.get(k, "standard")))

    def _playbook_editor_reset_display(
        self, combos: Dict[str, ttk.Combobox], level_pairs: Sequence[Tuple[str, str]]
    ) -> None:
        d = get_default_team_tactics()["playbook"]
        for k, cb in combos.items():
            self._playbook_editor_set_combo(cb, level_pairs, str(d.get(k, "standard")))

    def _playbook_editor_save(
        self,
        combos: Dict[str, ttk.Combobox],
        level_pairs: Sequence[Tuple[str, str]],
        *,
        message_parent: tk.Misc,
    ) -> None:
        if self.team is None:
            return
        raw = dict(get_safe_team_tactics(self.team))
        raw["playbook"] = self._playbook_editor_collect(combos, level_pairs)
        self._tactics_commit_payload(raw)
        messagebox.showinfo("保存", "セット傾向（playbook）を保存しました。", parent=message_parent)

    def _rotation_effect_summary_text(self) -> str:
        """起用プリセット適用後の読み取り専用サマリー（ローテ画面 0 用）。"""
        if self.team is None:
            return ""
        try:
            ensure_team_tactics_on_team(self.team)
        except Exception:
            pass
        st = get_current_rotation_preset_state(self.team)
        preset_name = str(st.get("label_ja") or "—")
        if st.get("is_custom"):
            preset_name = "カスタム（プリセットと一致しません）"

        tc = str(getattr(self.team, "usage_policy", "balanced") or "balanced").strip()
        team_coarse_ja = {"balanced": "バランス", "win_now": "勝利優先", "development": "育成優先"}.get(
            tc, tc
        )

        up = dict((get_safe_team_tactics(self.team).get("usage_policy") or {}))
        pairs_map, _labels = self._usage_policy_pairs_map_and_labels()

        def _disp(key: str) -> str:
            raw_v = str(up.get(key, "") or "")
            v = raw_v
            if key == "evaluation_focus" and v == "potential":
                v = "overall"
            for a, b in pairs_map.get(key, []):
                if a == v:
                    return b
            return raw_v or "—"

        rot = get_safe_team_tactics(self.team).get("rotation")
        if not isinstance(rot, dict):
            rot = {}
        sp = str(rot.get("sub_policy") or "standard").strip()
        fp = str(rot.get("fatigue_policy") or "standard").strip()
        fop = str(rot.get("foul_policy") or "standard").strip()
        cp = str(rot.get("clutch_policy") or "stars").strip()
        sub_ja = {
            "standard": "標準",
            "starters_long": "主力長め",
            "bench_deep": "ベンチ厚め",
            "youth_dev": "若手育成",
        }.get(sp, sp)
        fat_ja = {
            "strict": "疲労に厳格（無理を避けやすい）",
            "standard": "標準",
            "push": "多少無理をさせる",
        }.get(fp, fp)
        foul_ja = {
            "early_pull": "早めに下げる",
            "standard": "標準",
            "ride": "我慢する",
        }.get(fop, fop)
        clutch_ja = {
            "stars": "主力固定",
            "hot_hand": "好調優先",
            "defense": "守備重視",
            "offense": "攻撃重視",
        }.get(cp, cp)

        return (
            "【現在の反映内容】\n"
            f"・ローテプリセット：{preset_name}\n"
            f"・チーム基本起用（粗い）：{team_coarse_ja}\n"
            f"・起用の基本方針：{_disp('priority')}\n"
            f"・評価基準：{_disp('evaluation_focus')}\n"
            f"・調子の反映：{_disp('form_weight')}\n"
            f"・年齢バランス：{_disp('age_balance')}\n"
            f"・ケガ配慮：{_disp('injury_care')}\n"
            f"・連戦時運用：{_disp('schedule_care')}\n"
            "【ローテの細部（交代・疲労など）】\n"
            f"・交代の幅：{sub_ja}\n"
            f"・疲労方針：{fat_ja}\n"
            f"・ファウル配慮：{foul_ja}（個人ファウル数に応じた交代補正として一部反映）\n"
            f"・終盤方針：{clutch_ja}\n"
            "※ 先発・6th・ベンチ順は自動では変わりません。\n"
            "※ 目標出場時間はこのプリセットでは自動入力されません。\n"
            "※ 必要に応じて下の「2. 起用序列」や「ローテ詳細」で調整してください。"
        )

    def _rotation_target_minutes_recommendation_rows(
        self,
    ) -> Tuple[str, str, str, List[Dict[str, Any]], Optional[str]]:
        """
        起用序列とローテプリセットに基づく目標出場目安（最大12人分の構造化行）。
        Returns:
            (head, table_header_line, foot, rows, extra_line)
            rows 空＝先発5人未満等で表なし。extra_line はベンチ省略時のみ。
        row keys: player_id, player_name, role_label, current_minutes_label,
                  recommended_minutes, recommended_label, memo
        """
        if self.team is None:
            return ("", "", "", [], None)

        try:
            ensure_team_tactics_on_team(self.team)
        except Exception:
            pass

        st = get_current_rotation_preset_state(self.team)
        pmeta = st.get("preset_id")
        is_custom = bool(st.get("is_custom"))
        if (not pmeta) or is_custom or (pmeta not in ROTATION_PRESET_DEFS):
            eff = "balanced_v1"
            head = "※ プリセットが未設定、または手動で変えた「カスタム」状態のときは、目安をバランス基準で表示しています。\n\n"
        else:
            eff = str(pmeta)
            head = ""

        def _cur_tm(tm_raw: Any, p_id: int) -> str:
            if not isinstance(tm_raw, dict):
                return "未設定"
            for k, v in tm_raw.items():
                try:
                    if int(k) != int(p_id):
                        continue
                except (TypeError, ValueError):
                    continue
                try:
                    return f"{float(v):.0f}分"
                except (TypeError, ValueError):
                    return "未設定"
            return "未設定"

        def _ovr(p: Any) -> int:
            try:
                if hasattr(p, "get_effective_ovr") and callable(getattr(p, "get_effective_ovr")):
                    return int(p.get_effective_ovr())
            except (TypeError, ValueError, AttributeError):
                pass
            try:
                return int(getattr(p, "ovr", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _age(p: Any) -> Optional[int]:
            try:
                a = getattr(p, "age", None)
                if a is None:
                    return None
                return int(a)
            except (TypeError, ValueError):
                return None

        def _fat(p: Any) -> int:
            try:
                return int(getattr(p, "fatigue", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _development_preview_memo(p: Any, _slot: str) -> str:
            bits: List[str] = []
            a = _age(p)
            if a is not None and a <= 22:
                bits.append("若手は時間を取りやすい目安")
            if a is not None and a >= 30:
                bits.append("ベテランは抑えめ目安")
            return " ".join(bits)

        def _condition_preview_memo(p: Any) -> str:
            bits: List[str] = []
            if hasattr(p, "is_injured") and callable(getattr(p, "is_injured")):
                try:
                    if p.is_injured():
                        bits.append("負傷中は実際短めになりやすい")
                except Exception:
                    pass
            if _fat(p) >= 60:
                bits.append("疲労高め：交代を意識")
            return " ".join(bits)

        def _one_row(
            p_id: int,
            name: str,
            role: str,
            cur_lbl: str,
            rec_lbl: str,
            rmin: float,
            memo: str,
        ) -> Dict[str, Any]:
            m = max(0.0, min(40.0, float(rmin)))
            return {
                "player_id": p_id,
                "player_name": name,
                "role_label": role,
                "current_minutes_label": cur_lbl,
                "recommended_minutes": m,
                "recommended_label": rec_lbl,
                "memo": memo,
            }

        rot = get_safe_team_tactics(self.team).get("rotation")
        if not isinstance(rot, dict):
            rot = {}
        tm = rot.get("target_minutes") if isinstance(rot.get("target_minutes"), dict) else {}

        foot = (
            "\n"
            "※ 上の「このおすすめを目標出場時間に反映」は、押したときだけ上書き保存します。\n"
            "※ 上書きしない限り、目標出場（team_tactics）には自動で書き込みません。\n"
            "※ 下の「ローテ詳細」スライダーで微調整することもできます。\n"
            "※ 先発・6th・ベンチ順の Team 正本は、ここからは変わりません（下の2で手動）。"
        )
        no_table_msg = (
            head
            + "先発登録が5人に満たないため、目安一覧は出せません。\n"
            + "（契約中の選手で先発5人を揃えてから見てください。）\n\n"
            "※ 上書き反映もできません。ローテ詳細で手動の目標出場を設定できます。"
        )
        table_hdr = "（列）選手 / 序列 / 保存 / おすすめ / メモ"

        starters = list(get_current_starting_five(self.team) or [])
        if len(starters) < 5:
            return (no_table_msg, "", foot, [], None)

        st_rows: List[Tuple[int, int]] = []
        for p in starters:
            try:
                p_id = int(getattr(p, "player_id", -1) or -1)
            except (TypeError, ValueError):
                p_id = -1
            st_rows.append((p_id, _ovr(p)))
        sorted_pids = {
            t[0] for t in sorted([x for x in st_rows if x[0] >= 0], key=lambda t: t[1], reverse=True)[:2]
        }

        rows: List[Dict[str, Any]] = []
        n_shown = 0
        for pos, p in zip(STARTER_POSITIONS, starters):
            if n_shown >= 12:
                break
            try:
                p_id = int(getattr(p, "player_id", -1) or -1)
            except (TypeError, ValueError):
                p_id = -1
            name = str(getattr(p, "name", "?"))[:14]
            role = f"先発{pos}"
            cur = _cur_tm(tm, p_id) if p_id >= 0 else "未設定"
            is_top2 = p_id in sorted_pids and p_id >= 0
            rmin: float
            if eff == "win_now_v1" and is_top2:
                rec, memo, rmin = ("32分前後", "主力寄り（勝利優先）", 32.0)
            elif eff == "win_now_v1" and not is_top2:
                rec, memo, rmin = ("28分前後", "先発枠", 28.0)
            elif eff == "balanced_v1":
                rec, memo, rmin = ("28分前後", "バランス先発", 28.0)
            elif eff == "development_v1":
                rec, memo, rmin = ("27分前後", "先発枠", 27.0)
                a = _age(p)
                if a is not None and a <= 22:
                    memo = "先発枠（若手は目安やや上）"
                elif a is not None and a >= 30:
                    memo = "先発枠（ベテランは目安やさめ）"
            elif eff == "condition_care_v1":
                rec, memo, rmin = ("27分前後", "休養意識の先発枠", 27.0)
            else:
                rec, memo, rmin = ("28分前後", "標準的な目安", 28.0)
            ex = _condition_preview_memo(p) if eff == "condition_care_v1" else ""
            if ex:
                memo = f"{memo} {ex}".strip()
            if p_id >= 0:
                rows.append(_one_row(p_id, name, role, cur, rec, rmin, memo))
            n_shown += 1

        sm = get_current_sixth_man(self.team)
        if sm is not None and n_shown < 12:
            try:
                p_id = int(getattr(sm, "player_id", -1) or -1)
            except (TypeError, ValueError):
                p_id = -1
            name = str(getattr(sm, "name", "?"))[:14]
            cur = _cur_tm(tm, p_id) if p_id >= 0 else "未設定"
            if eff == "win_now_v1":
                rec, memo, rmin = ("22分前後", "控えの柱", 22.0)
            elif eff == "balanced_v1":
                rec, memo, rmin = ("22分前後", "6th 起用", 22.0)
            elif eff == "development_v1":
                rec, memo, rmin = ("21分前後", "6th 起用", 21.0)
                a = _age(sm)
                if a is not None and a <= 22:
                    memo = "6th 起用（育成枠）"
            elif eff == "condition_care_v1":
                rec, memo, rmin = ("21分前後", "無理を避けたい枠", 21.0)
            else:
                rec, memo, rmin = ("22分前後", "6th 起用", 22.0)
            ex = _condition_preview_memo(sm) if eff == "condition_care_v1" else (
                _development_preview_memo(sm, "sixth") if eff == "development_v1" else ""
            )
            if ex:
                memo = f"{memo} {ex}".strip()
            if p_id >= 0:
                rows.append(_one_row(p_id, name, "6th", cur, rec, rmin, memo))
            n_shown += 1

        bench = [b for b in (get_current_bench_order(self.team) or []) if b is not None]
        n_b = len(bench)
        extra_line: Optional[str] = None
        for bi, p in enumerate(bench):
            if n_shown >= 12:
                rem = n_b - bi
                if rem > 0:
                    extra_line = f"… 他 {rem} 名（ベンチ以降は省略）"
                break
            try:
                p_id = int(getattr(p, "player_id", -1) or -1)
            except (TypeError, ValueError):
                p_id = -1
            name = str(getattr(p, "name", "?"))[:14]
            is_hi = bi < 2
            role = "ベンチ上位" if is_hi else "ベンチ下位"
            pos_label = f"{bi + 1}番手" if n_b else ""
            if pos_label and role.startswith("ベンチ"):
                role = f"{role}（{pos_label}）"
            cur = _cur_tm(tm, p_id) if p_id >= 0 else "未設定"
            if eff == "win_now_v1":
                rec, memo, rmin = (
                    ("11分前後", "控え短め", 11.0) if is_hi else ("4分前後", "出番は限定的", 4.0)
                )
            elif eff == "balanced_v1":
                rec, memo, rmin = (
                    ("15分前後", "ローテ寄与", 15.0) if is_hi else ("7分前後", "短い出番", 7.0)
                )
            elif eff == "development_v1":
                rec, memo, rmin = (
                    ("18分前後", "育成枠", 18.0) if is_hi else ("11分前後", "出番を重視しやすい", 11.0)
                )
                a = _age(p)
                if a is not None and a <= 22 and is_hi:
                    memo = "育成枠（若手に時間を割きやすい）"
            elif eff == "condition_care_v1":
                rec, memo, rmin = (
                    ("15分前後", "深めのローテ", 15.0) if is_hi else ("9分前後", "省エネ起用目安", 9.0)
                )
            else:
                rec, memo, rmin = ("12分前後", "控え目安", 12.0)
            ex = _condition_preview_memo(p) if eff == "condition_care_v1" else _development_preview_memo(
                p, "bench"
            ) if eff == "development_v1" else ""
            if ex:
                memo = f"{memo} {ex}".strip()
            if p_id >= 0:
                rows.append(_one_row(p_id, name, role, cur, rec, rmin, memo))
            n_shown += 1

        return (head, table_hdr, foot, rows, extra_line)

    def _rotation_target_minutes_preview_text(self) -> str:
        """起用序列とローテプリセットに基づく目標出場の目安（行データの文字列化）。"""
        if self.team is None:
            return ""
        head, table_hdr, foot, rows, extra_line = self._rotation_target_minutes_recommendation_rows()
        if not rows:
            return (head or "") + (foot or "")
        hpre = head or ""
        first = (hpre + table_hdr) if hpre else table_hdr
        lines: List[str] = [first]
        for r in rows:
            lines.append(
                f'{r["player_name"]} / {r["role_label"]} / {r["current_minutes_label"]} / '
                f'{r["recommended_label"]} / {r["memo"]}'
            )
        if extra_line:
            lines.append(extra_line)
        return "\n".join(lines) + foot

    def _apply_rotation_recommended_target_minutes(self, message_parent: tk.Misc) -> None:
        """おすすめ行（最大12人）の分数だけ target_minutes に手動反映。Team正本は変更しない。"""
        if self.team is None:
            return
        _head, _th, _ft, rows, _ex = self._rotation_target_minutes_recommendation_rows()
        if not rows:
            messagebox.showinfo(
                "目標出場",
                "先発5人が揃っていないか、反映できるおすすめ行がありません。",
                parent=message_parent,
            )
            return
        q = messagebox.askyesno(
            "目標出場の上書き確認",
            "現在の目標出場時間を、おすすめ値で上書きします。\n"
            "この操作を行うと、ローテプリセット状態は「カスタム」と表示される場合があります。\n"
            "先発・6th・ベンチ順は変更しません。\n"
            "よろしいですか？",
            parent=message_parent,
        )
        if not q:
            return
        raw = dict(get_safe_team_tactics(self.team))
        rot = dict(raw.get("rotation") or {})
        tm: Dict[str, float] = {}
        prev = rot.get("target_minutes")
        if isinstance(prev, dict):
            for k, v in prev.items():
                try:
                    ik = int(k)
                except (TypeError, ValueError):
                    continue
                try:
                    tm[str(ik)] = max(0.0, min(40.0, float(v)))
                except (TypeError, ValueError):
                    continue
        for r in rows:
            try:
                pid = int(r["player_id"])
            except (TypeError, ValueError, KeyError):
                continue
            if pid < 0:
                continue
            m = r.get("recommended_minutes", 0.0)
            try:
                m = max(0.0, min(40.0, float(m)))
            except (TypeError, ValueError):
                m = 0.0
            tm[str(pid)] = m
        rot["target_minutes"] = tm
        raw["rotation"] = rot
        self._tactics_commit_payload(raw)
        self._refresh_strategy_window()
        fn = getattr(self, "_rotation_overview_lf0_readouts", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
        messagebox.showinfo("目標出場", "目標出場時間を反映しました。", parent=message_parent)

    def _compute_rotation_lineup_recommendation(self) -> Dict[str, Any]:
        """
        ローテプリセットに基づく起用のおすすめ（先発5・6th・ベンチ）。
        Team 正本は変更しない。表示と手動反映で同一データ源にする。
        戻り: status, eff, label_ja, head_note, starters(5), sixth, bench, ほか
        status: "ok" | "no_team" | "too_few" | "incomplete"
        """
        out: Dict[str, Any] = {
            "status": "no_team",
            "eff": "balanced_v1",
            "label_ja": "—",
            "head_note": "",
            "raw_pid": None,
            "is_custom": False,
            "starters": [],
            "bench": [],
        }
        if self.team is None:
            out["status"] = "no_team"
            return out

        try:
            ensure_team_tactics_on_team(self.team)
        except Exception:
            pass

        st = get_current_rotation_preset_state(self.team)
        raw_pid = st.get("preset_id")
        is_custom = bool(st.get("is_custom"))
        label_ja = str(st.get("label_ja", "") or "—")
        out["raw_pid"] = raw_pid
        out["is_custom"] = is_custom
        out["label_ja"] = label_ja
        if (not raw_pid) or is_custom or (raw_pid not in ROTATION_PRESET_DEFS):
            eff = "balanced_v1"
            out["head_note"] = (
                "※ プリセット未設定、または「カスタム」表示のときは、"
                "おすすめをバランス基準（balanced_v1）で計算しています。\n"
            )
        else:
            eff = str(raw_pid)
            out["head_note"] = ""
        out["eff"] = eff

        def _pid(p: Any) -> Optional[int]:
            try:
                v = getattr(p, "player_id", None)
                if v is None:
                    return None
                return int(v)
            except (TypeError, ValueError):
                return None

        def _eligible(p: Any) -> bool:
            if bool(getattr(p, "is_retired", False)):
                return False
            if hasattr(p, "is_injured") and callable(getattr(p, "is_injured")):
                try:
                    if p.is_injured():
                        return False
                except Exception:
                    return False
            return True

        def _eff_ovr(p: Any) -> int:
            if hasattr(p, "get_effective_ovr") and callable(getattr(p, "get_effective_ovr")):
                try:
                    return int(p.get_effective_ovr())
                except (TypeError, ValueError, AttributeError):
                    pass
            try:
                return int(getattr(p, "ovr", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _age(p: Any) -> Optional[int]:
            try:
                a = getattr(p, "age", None)
                if a is None:
                    return None
                return int(a)
            except (TypeError, ValueError):
                return None

        def _pot_points(p: Any) -> float:
            raw = getattr(p, "potential", None)
            s = str(raw or "").strip().upper()
            return {
                "S": 5.0,
                "A": 4.0,
                "B": 3.0,
                "C": 2.0,
                "D": 1.0,
            }.get(s[:1] if s else "", 0.0)

        def _fatigue(p: Any) -> int:
            try:
                return int(getattr(p, "fatigue", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _score(p: Any) -> float:
            eo = float(_eff_ovr(p))
            ag = _age(p)
            if eff == "balanced_v1":
                return eo
            if eff == "win_now_v1":
                bonus = 0.0
                if ag is not None:
                    if 26 <= ag <= 32:
                        bonus += 2.0
                    elif ag >= 33:
                        bonus += 0.5
                    elif ag <= 22:
                        bonus -= 1.0
                return eo + bonus
            if eff == "development_v1":
                bonus = 0.0
                if ag is not None:
                    if ag <= 22:
                        bonus += 4.0
                    elif ag <= 24:
                        bonus += 2.0
                    if ag >= 32:
                        bonus -= 3.0
                bonus += _pot_points(p) * 1.2
                raw = eo + bonus
                if eo < 42.0:
                    raw = min(raw, eo + 8.0)
                return raw
            if eff == "condition_care_v1":
                f = _fatigue(p)
                pen = 0.0
                if f >= 80:
                    pen += 8.0
                elif f >= 60:
                    pen += 5.0
                elif f >= 40:
                    pen += 2.0
                return eo - pen
            return eo

        roster: List[Any] = [p for p in (getattr(self.team, "players", None) or []) if _eligible(p)]
        if len(roster) < 5:
            out["status"] = "too_few"
            return out

        starters: List[Optional[Any]] = [None, None, None, None, None]
        used: set = set()

        for i, pos in enumerate(STARTER_POSITIONS):
            pool = [
                p
                for p in roster
                if str(getattr(p, "position", "SF") or "SF") == pos and _pid(p) not in used
            ]
            if pool:
                b = max(pool, key=_score)
                starters[i] = b
                ip = _pid(b)
                if ip is not None:
                    used.add(ip)

        for i in range(5):
            if starters[i] is not None:
                continue
            pool = [p for p in roster if _pid(p) is not None and _pid(p) not in used]
            if not pool:
                break
            b = max(pool, key=_score)
            starters[i] = b
            ip = _pid(b)
            if ip is not None:
                used.add(ip)

        if any(s is None for s in starters):
            out["status"] = "incomplete"
            return out

        rest = [p for p in roster if _pid(p) not in used]
        sixth: Optional[Any] = None
        if rest:
            sixth = max(rest, key=_score)
            sip = _pid(sixth)
            if sip is not None:
                used.add(sip)

        bench: List[Any] = [p for p in rest if p is not sixth]
        bench.sort(key=_score, reverse=True)

        out["status"] = "ok"
        out["starters"] = [s for s in starters if s is not None]
        out["sixth"] = sixth
        out["bench"] = bench
        return out

    def _rotation_lineup_recommendation_text(self) -> str:
        """
        ローテプリセットに応じた起用序列のおすすめ案（読み取り専用の文字列）。
        Team 正本・target_minutes は変更しない。
        """
        if self.team is None:
            return ""
        data = self._compute_rotation_lineup_recommendation()
        eff = str(data.get("eff") or "balanced_v1")
        label_ja = str(data.get("label_ja", "") or "—")
        head_note = str(data.get("head_note", "") or "")
        raw_pid = data.get("raw_pid")
        is_custom = bool(data.get("is_custom", False))
        stt = str(data.get("status") or "")

        def _pid(p: Any) -> Optional[int]:
            try:
                v = getattr(p, "player_id", None)
                if v is None:
                    return None
                return int(v)
            except (TypeError, ValueError):
                return None

        def _eff_ovr(p: Any) -> int:
            if hasattr(p, "get_effective_ovr") and callable(getattr(p, "get_effective_ovr")):
                try:
                    return int(p.get_effective_ovr())
                except (TypeError, ValueError, AttributeError):
                    pass
            try:
                return int(getattr(p, "ovr", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _line(p: Any) -> str:
            pid = _pid(p)
            nm = str(getattr(p, "name", "?"))[:16]
            pos = str(getattr(p, "position", "?"))
            o = _eff_ovr(p)
            return f"{nm}  ({pos})  実効OVR {o}  id={pid}"

        if stt == "too_few":
            return (
                "【ローテプリセット（表示用）】\n"
                f"・状態: {label_ja}\n"
                f"{head_note}\n"
                "おすすめ先発を作るには登録選手（負傷・引退を除く）が5人未満です。\n"
                "ロスターを揃えてからご確認ください。\n\n"
                "【方針メモ（参照）】\n"
                f"{_ROTATION_PRESET_DESC_JA.get(eff, '')}\n"
            )
        if stt == "incomplete":
            return (
                "【ローテプリセット（表示用）】\n"
                f"・状態: {label_ja}\n"
                f"{head_note}\n"
                "おすすめ先発を5人揃えられませんでした（同時に起用できる選手が足りない状態）。\n\n"
                "【方針メモ（参照）】\n"
                f"{_ROTATION_PRESET_DESC_JA.get(eff, '')}\n"
            )
        if stt != "ok":
            return ""

        starters: List[Any] = list(data.get("starters") or [])
        sixth: Any = data.get("sixth")
        bench: List[Any] = list(data.get("bench") or [])

        lines_st: List[str] = []
        for i, pos in enumerate(STARTER_POSITIONS):
            sp = starters[i] if i < len(starters) else None
            lines_st.append(f"  {pos}: {_line(sp) if sp else '—'}")

        lines_s6 = f"  {_line(sixth) if sixth else '（該当なし）'}"
        lines_bn: List[str] = []
        for j, p in enumerate(bench, start=1):
            lines_bn.append(f"  {j + 6}番手: {_line(p)}")

        eff_memo = {
            "balanced_v1": "ポジションを埋めたうえで不足分をスコア順補完。6thは非先発の最高スコア、ベンチは残りをスコア順。",
            "win_now_v1": "実効OVRを主軸に、即戦力年齢帯をやや加点。",
            "development_v1": "若年・潜在格付けを加点しつつ、極端に低い実効OVRの押し上げに上限。",
            "condition_care_v1": "負傷者は除外。疲労が高い選手はスコアを少し下げ、バランスに寄せます。",
        }.get(eff, "")

        pid_show = eff if (raw_pid and str(raw_pid) in ROTATION_PRESET_DEFS and not is_custom) else f"計算: {eff}"
        body = (
            f"【ローテプリセット（表示用）】\n"
            f"・状態: {label_ja}  /  おすすめ計算: {pid_show}\n"
            f"{head_note}"
            f"【先発（おすすめ・{', '.join(STARTER_POSITIONS)}）】\n"
            + "\n".join(lines_st)
            + "\n\n"
            "【6th（おすすめ）】\n"
            f"{lines_s6}\n\n"
            "【ベンチ順（おすすめ・7番手〜）】\n"
        )
        if lines_bn:
            body += "\n".join(lines_bn) + "\n"
        else:
            body += "  （なし）\n"
        body += (
            f"\n【方針メモ】\n{eff_memo}\n"
            f"（プリセット説明）{_ROTATION_PRESET_DESC_JA.get(eff, '')}\n"
        )
        return body

    def _apply_recommended_lineup_to_team(
        self,
        message_parent: tk.Misc,
    ) -> None:
        """
        おすすめ起用序列（計算と同一）を Team 正本へ反映。確認後のみ。
        team_tactics["rotation"]["starters"] のみ同期（試合開始先発の差し替え元）。
        target_minutes / sub_policy 等の既存 rotation 欄は変更しない。
        """
        if self.team is None:
            return
        team = self.team
        data = self._compute_rotation_lineup_recommendation()
        stt = str(data.get("status") or "")
        if stt in ("no_team", "too_few", "incomplete"):
            messagebox.showwarning(
                "起用序列",
                "おすすめ先発を揃えられないため、反映できません。",
                parent=message_parent,
            )
            return
        if stt != "ok":
            return

        starters: List[Any] = list(data.get("starters") or [])
        sixth: Any = data.get("sixth")
        bench: List[Any] = list(data.get("bench") or [])

        if len(starters) != 5 or any(s is None for s in starters):
            messagebox.showwarning(
                "起用序列",
                "おすすめ先発のデータが不正のため、反映できません。",
                parent=message_parent,
            )
            return

        def _pid(p: Any) -> Optional[int]:
            try:
                v = getattr(p, "player_id", None)
                if v is None:
                    return None
                return int(v)
            except (TypeError, ValueError):
                return None

        sids = [_pid(s) for s in starters]
        if any(x is None for x in sids) or len(set(sids)) != 5:
            messagebox.showerror("起用序列", "先発に重複がない必要があります。", parent=message_parent)
            return
        sset = {int(x) for x in sids}
        pids_roster = {
            int(getattr(p, "player_id", -1))
            for p in (getattr(team, "players", None) or [])
        }
        for sid in sset:
            if sid < 0 or sid not in pids_roster:
                messagebox.showerror("起用序列", "ロスター外の選手が含まれています。", parent=message_parent)
                return
        for s in starters:
            if s is None or s not in (getattr(team, "players", None) or []):
                messagebox.showerror("起用序列", "チームに所属する選手だけ反映できます。", parent=message_parent)
                return
        s6 = _pid(sixth) if sixth is not None else None
        if s6 is not None and (s6 in sset or sixth not in (getattr(team, "players", None) or [])):
            messagebox.showerror("起用序列", "6th候補が不正です。", parent=message_parent)
            return
        bset: set = set()
        for p in bench:
            bpid = _pid(p)
            if bpid is None or p not in (getattr(team, "players", None) or []):
                messagebox.showerror("起用序列", "ベンチ候補に不正な選手が含まれています。", parent=message_parent)
                return
            if bpid in sset or bpid == s6 or bpid in bset:
                messagebox.showerror("起用序列", "ベンチに先発・6thと重複があってはいけません。", parent=message_parent)
                return
            bset.add(bpid)

        q = messagebox.askyesno(
            "起用序列の上書き確認",
            "現在の先発・6th・ベンチ順を、おすすめ起用序列で上書きします。\n"
            "あわせて、試合開始先発に使われる戦術先発にも反映します。\n"
            "目標出場時間は変更しません。\n"
            "\n"
            "なお、試合では外国籍枠・ポジション・OVR差などの安全ルールにより、"
            "必ず完全一致しない場合があります。\n"
            "よろしいですか？",
            parent=message_parent,
        )
        if not q:
            return

        s_set = getattr(team, "set_starting_lineup_by_players", None)
        if not callable(s_set):
            messagebox.showerror("起用序列", "先発の設定に対応していません。", parent=message_parent)
            return
        try:
            s_set(starters)
        except Exception as exc:
            messagebox.showerror("起用序列", str(exc), parent=message_parent)
            return

        clr6 = getattr(team, "clear_sixth_man", None)
        s_six = getattr(team, "set_sixth_man", None)
        if sixth is not None:
            if not callable(s_six):
                messagebox.showerror("起用序列", "6thの設定に対応していません。", parent=message_parent)
                return
            try:
                s_six(sixth)
            except Exception as exc:
                messagebox.showerror("起用序列", str(exc), parent=message_parent)
                return
        else:
            if callable(clr6):
                try:
                    clr6()
                except Exception:
                    pass

        s_b = getattr(team, "set_bench_order_by_players", None)
        if not callable(s_b):
            messagebox.showerror("起用序列", "ベンチ序列の設定に対応していません。", parent=message_parent)
            return
        try:
            s_b(bench)
        except Exception as exc:
            messagebox.showerror("起用序列", str(exc), parent=message_parent)
            return

        try:
            raw = dict(get_safe_team_tactics(self.team))
            rot = dict(raw.get("rotation") or {})
            starters_map: Dict[str, int] = {}
            for i, pos in enumerate(STARTER_POSITIONS):
                if i >= len(starters):
                    break
                spid = _pid(starters[i])
                if spid is not None:
                    starters_map[pos] = int(spid)
            rot["starters"] = starters_map
            raw["rotation"] = rot
            self._tactics_commit_payload(raw)
        except Exception as exc:
            messagebox.showerror(
                "起用序列",
                f"戦術先発（rotation.starters）の保存に失敗しました: {exc}",
                parent=message_parent,
            )
            self.refresh()
            self._refresh_strategy_window()
            lrel = getattr(self, "_tactics_rotation_lineup_reload", None)
            if callable(lrel):
                try:
                    lrel()
                except Exception:
                    pass
            rfn = getattr(self, "_rotation_overview_lf0_readouts", None)
            if callable(rfn):
                try:
                    rfn()
                except Exception:
                    pass
            return

        self.refresh()
        self._refresh_strategy_window()
        lrel = getattr(self, "_tactics_rotation_lineup_reload", None)
        if callable(lrel):
            try:
                lrel()
            except Exception:
                pass
        rfn = getattr(self, "_rotation_overview_lf0_readouts", None)
        if callable(rfn):
            try:
                rfn()
            except Exception:
                pass
        messagebox.showinfo("起用序列", "おすすめ起用序列を反映しました。", parent=message_parent)

    def _build_rotation_preset_editor_ui(
        self,
        parent: ttk.Frame,
        *,
        message_parent: tk.Misc,
        after_apply: Optional[Callable[[], None]] = None,
        usage_policy_resync: Optional[Callable[[], None]] = None,
    ) -> Tuple[Callable[[], None], Callable[[], None]]:
        """
        0. 起用プリセット（ROTATION_PRESET_DEFS）の共通 UI。
        戻り値: (状態ラベル更新, preset_meta からコンボ同期) 用コールバック。
        """
        lbl_rot_state = ttk.Label(
            parent,
            text="",
            wraplength=520,
            font=("Yu Gothic UI", 9),
            foreground="#111111",
        )

        def _sync_rot_state() -> None:
            if self.team is None:
                return
            st = get_current_rotation_preset_state(self.team)
            lbl_rot_state.configure(text=f"現在のローテプリセット状態: {st['label_ja']}")

        lbl_rot_state.pack(anchor="w", pady=(4, 0))
        _sync_rot_state()

        row_rp = ttk.Frame(parent, style="Panel.TFrame")
        row_rp.pack(fill="x", pady=(2, 4))
        ttk.Label(row_rp, text="候補", width=8).pack(side="left")
        combo_rp = ttk.Combobox(row_rp, state="readonly", width=28)
        _ui_rotation_preset_order: Tuple[str, ...] = (
            "balanced_v1",
            "win_now_v1",
            "development_v1",
            "condition_care_v1",
        )
        _rotation_preset_ids: Tuple[str, ...] = tuple(
            pid for pid in _ui_rotation_preset_order if pid in ROTATION_PRESET_DEFS
        )
        _rotation_label_by_id = {
            pid: str(ROTATION_PRESET_DEFS[pid].get("label_ja", pid)) for pid in _rotation_preset_ids
        }
        _rotation_id_by_label = {lab: pid for pid, lab in _rotation_label_by_id.items()}
        combo_rp["values"] = tuple(_rotation_label_by_id[pid] for pid in _rotation_preset_ids)

        lbl_rp_desc = ttk.Label(
            parent,
            text="",
            wraplength=520,
            justify="left",
            font=("Yu Gothic UI", 9),
            foreground="#333333",
        )

        def _refresh_rotation_preset_desc() -> None:
            lab = ""
            try:
                lab = combo_rp.get()
            except tk.TclError:
                pass
            pid = _rotation_id_by_label.get(lab, "balanced_v1")
            lbl_rp_desc.configure(
                text=_tactics_preset_desc_ui_text(
                    pid,
                    _ROTATION_PRESET_DESC_JA,
                    _ROTATION_PRESET_TOOLTIP_JA,
                    _rotation_preset_ids,
                )
            )

        def _sync_rotation_combo_from_meta() -> None:
            if self.team is None:
                return
            ensure_team_tactics_on_team(self.team)
            pm = (self.team.team_tactics or {}).get("preset_meta") or {}
            raw_pid = pm.get("rotation_preset_id")
            pid = raw_pid.strip() if isinstance(raw_pid, str) and raw_pid.strip() else None
            if pid not in ROTATION_PRESET_DEFS:
                pid = "balanced_v1"
            if pid not in _rotation_label_by_id:
                pid = _rotation_preset_ids[0] if _rotation_preset_ids else "balanced_v1"
            lab = _rotation_label_by_id.get(pid, _rotation_label_by_id["balanced_v1"])
            try:
                combo_rp.set(lab)
            except tk.TclError:
                combo_rp.current(0)
            _refresh_rotation_preset_desc()

        def _on_apply_rotation_preset() -> None:
            if self.team is None:
                return
            lab = combo_rp.get()
            preset_id = _rotation_id_by_label.get(lab, "balanced_v1")
            try:
                apply_rotation_preset_with_preset_meta(self.team, preset_id)
            except KeyError as e:
                messagebox.showerror("エラー", str(e), parent=message_parent)
                return
            self.refresh()
            self._refresh_strategy_window()
            if usage_policy_resync is not None:
                usage_policy_resync()
            _sync_rotation_combo_from_meta()
            _sync_rot_state()
            messagebox.showinfo(
                "適用",
                "ローテーションプリセットを反映しました（usage_policy / rotation / Team.usage_policy）。\n"
                f"preset_meta.rotation_preset_id = {preset_id!r}",
                parent=message_parent,
            )
            if after_apply is not None:
                after_apply()

        _sync_rotation_combo_from_meta()
        combo_rp.pack(side="left", padx=6)
        ttk.Button(
            row_rp,
            text="プリセット適用",
            style="Menu.TButton",
            command=_on_apply_rotation_preset,
            width=14,
        ).pack(side="left", padx=4)
        combo_rp.bind("<<ComboboxSelected>>", lambda _e: _refresh_rotation_preset_desc())
        lbl_rp_desc.pack(anchor="w", pady=(2, 0))

        return _sync_rot_state, _sync_rotation_combo_from_meta

    def _build_playstyle_preset_editor_ui(
        self,
        parent: ttk.Frame,
        *,
        message_parent: tk.Misc,
        after_apply: Optional[Callable[[], None]] = None,
        strategy_policy_combos: Optional[Tuple[ttk.Combobox, ttk.Combobox, ttk.Combobox]] = None,
    ) -> Tuple[Callable[[], None], Callable[[], None]]:
        """
        0. 戦術プリセット（PLAYSTYLE_PRESET_DEFS 3種）の共通 UI。
        戻り値: (状態ラベル更新, preset_meta からコンボ同期) 用コールバック。
        """
        row_ps_stat = ttk.Frame(parent, style="Panel.TFrame")
        row_ps_stat.pack(fill="x", pady=(0, 2))
        lbl_ps_state = ttk.Label(row_ps_stat, text="", wraplength=480)

        def _sync_ps_state() -> None:
            if self.team is None:
                return
            st = get_current_playstyle_preset_state(self.team)
            lbl_ps_state.configure(text=f"現在の戦術プリセット状態: {st['label_ja']}")

        lbl_ps_state.pack(anchor="w")
        _sync_ps_state()

        row_preset = ttk.Frame(parent, style="Panel.TFrame")
        row_preset.pack(fill="x", pady=(4, 4))
        combo_ps = ttk.Combobox(row_preset, state="readonly", width=28)
        # UI は実装済み v1 の3種のみ（将来 defs が増えても候補に自動で増やさない）
        _ui_playstyle_preset_order: Tuple[str, ...] = (
            "balanced_v1",
            "run_and_gun_3p_v1",
            "defense_first_v1",
        )
        _playstyle_preset_ids: Tuple[str, ...] = tuple(
            pid for pid in _ui_playstyle_preset_order if pid in PLAYSTYLE_PRESET_DEFS
        )
        _playstyle_label_by_id = {
            pid: str(PLAYSTYLE_PRESET_DEFS[pid].get("label_ja", pid)) for pid in _playstyle_preset_ids
        }
        _playstyle_id_by_label = {lab: pid for pid, lab in _playstyle_label_by_id.items()}
        combo_ps["values"] = tuple(_playstyle_label_by_id[pid] for pid in _playstyle_preset_ids)

        lbl_ps_desc = ttk.Label(parent, text="", wraplength=500, justify="left")

        def _refresh_playstyle_preset_desc() -> None:
            lab = ""
            try:
                lab = combo_ps.get()
            except tk.TclError:
                pass
            pid = _playstyle_id_by_label.get(lab, "balanced_v1")
            lbl_ps_desc.configure(
                text=_tactics_preset_desc_ui_text(
                    pid,
                    _PLAYSTYLE_PRESET_DESC_JA,
                    _PLAYSTYLE_PRESET_TOOLTIP_JA,
                    _playstyle_preset_ids,
                )
            )

        def _sync_playstyle_combo_from_meta() -> None:
            if self.team is None:
                return
            ensure_team_tactics_on_team(self.team)
            pm = (self.team.team_tactics or {}).get("preset_meta") or {}
            raw_pid = pm.get("playstyle_preset_id")
            pid = raw_pid.strip() if isinstance(raw_pid, str) and raw_pid.strip() else None
            if pid not in PLAYSTYLE_PRESET_DEFS:
                pid = "balanced_v1"
            if pid not in _playstyle_label_by_id:
                pid = _playstyle_preset_ids[0] if _playstyle_preset_ids else "balanced_v1"
            lab = _playstyle_label_by_id.get(pid, _playstyle_label_by_id["balanced_v1"])
            try:
                combo_ps.set(lab)
            except tk.TclError:
                combo_ps.current(0)
            _refresh_playstyle_preset_desc()

        def _on_apply_playstyle_preset() -> None:
            if self.team is None:
                return
            lab = combo_ps.get()
            preset_id = _playstyle_id_by_label.get(lab, "balanced_v1")
            try:
                apply_playstyle_preset_with_preset_meta(self.team, preset_id)
            except KeyError as e:
                messagebox.showerror("エラー", str(e), parent=message_parent)
                return
            if strategy_policy_combos is not None:
                cs, cc, cu = strategy_policy_combos
                self._sync_strategy_policy_combos(cs, cc, cu)
            self.refresh()
            self._refresh_strategy_window()
            _sync_playstyle_combo_from_meta()
            _sync_ps_state()
            messagebox.showinfo(
                "適用",
                "戦術プリセットを反映しました（team_strategy / playbook / Team.strategy）。\n"
                f"preset_meta.playstyle_preset_id = {preset_id!r}",
                parent=message_parent,
            )
            if after_apply is not None:
                after_apply()

        _sync_playstyle_combo_from_meta()
        combo_ps.pack(side="left", padx=6)
        ttk.Button(
            row_preset,
            text="プリセット適用",
            style="Menu.TButton",
            command=_on_apply_playstyle_preset,
            width=14,
        ).pack(side="left", padx=4)
        lbl_ps_desc.pack(anchor="w", pady=(2, 0))
        combo_ps.bind("<<ComboboxSelected>>", lambda _e: _refresh_playstyle_preset_desc())

        return _sync_ps_state, _sync_playstyle_combo_from_meta

    def _open_tactics_playstyle_overview_window(self, parent: tk.Misc) -> None:
        """プレイスタイル統合画面の土台（0〜7の見出し・説明・補助導線）。"""
        if self.team is None:
            return
        try:
            ensure_team_tactics_on_team(self.team)
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("戦術：プレイスタイル")
        w.geometry("760x840")
        w.minsize(720, 600)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame")
        outer.pack(fill="both", expand=True)

        bf = ttk.Frame(outer, style="Root.TFrame", padding=(12, 8, 12, 12))
        bf.pack(side="bottom", fill="x")
        ttk.Button(bf, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right")

        intro_fr = ttk.Frame(outer, style="Root.TFrame", padding=(12, 12, 12, 0))
        intro_fr.pack(side="top", fill="x")
        ttk.Label(
            intro_fr,
            text=(
                "完成形に向けた統合画面。0 のプリセット設定と 1〜6 の攻守の傾向・7 のセット傾向は"
                "この画面で直接操作できます（1〜6・7 は保存で確定）。\n"
                "Team の基本戦術・HCスタイル・基本起用（粗い3項目）は、0〜7 の主設定とは別系統の補助です。"
                "必要なときは下の「補助設定を開く（Team基本方針・HC）」から変更します。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=660,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        scroll_wrap = ttk.Frame(outer, style="Root.TFrame")
        scroll_wrap.pack(fill="both", expand=True)

        ps_canvas = tk.Canvas(scroll_wrap, bg="#15171c", highlightthickness=0)
        ps_vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=ps_canvas.yview)
        ps_canvas.configure(yscrollcommand=ps_vsb.set)
        scroll_content = ttk.Frame(ps_canvas, style="Root.TFrame", padding=12)
        ps_win_id = ps_canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _playstyle_scrollregion(_event: Any = None) -> None:
            ps_canvas.update_idletasks()
            bbox = ps_canvas.bbox("all")
            if bbox:
                ps_canvas.configure(scrollregion=bbox)

        def _playstyle_canvas_width(event: Any) -> None:
            try:
                ps_canvas.itemconfigure(ps_win_id, width=event.width)
            except tk.TclError:
                pass

        scroll_content.bind("<Configure>", lambda _e: _playstyle_scrollregion())

        ps_canvas.bind("<Configure>", _playstyle_canvas_width)

        def _playstyle_wheel(event: Any) -> None:
            if getattr(event, "delta", 0):
                ps_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        for _mw_target in (w, ps_canvas, scroll_content):
            _mw_target.bind("<MouseWheel>", _playstyle_wheel)
            _mw_target.bind("<Button-4>", lambda _e: ps_canvas.yview_scroll(-1, "units"))
            _mw_target.bind("<Button-5>", lambda _e: ps_canvas.yview_scroll(1, "units"))

        ps_canvas.pack(side="left", fill="both", expand=True)
        ps_vsb.pack(side="right", fill="y")

        pairs_ov, labels_ov = self._team_strategy_pairs_map_and_labels()
        combos_holder: Dict[str, Any] = {}
        playbook_combos_holder: Dict[str, Any] = {}
        level_pairs_pb = self._PLAYBOOK_LEVEL_PAIRS

        def _after_playstyle_preset_apply() -> None:
            c = combos_holder.get("combos")
            if isinstance(c, dict):
                self._team_strategy_editor_reload_from_team(c, pairs_ov)
            pb_c = playbook_combos_holder.get("combos")
            if isinstance(pb_c, dict):
                self._playbook_editor_reload_from_team(pb_c, level_pairs_pb)

        lf0 = ttk.LabelFrame(scroll_content, text="0. プリセット設定", padding=10)
        lf0.pack(fill="x", pady=(0, 8))
        ttk.Label(
            lf0,
            text=(
                "プリセットを選んで「プリセット適用」すると、1〜6（攻守の傾向）と 7（セット傾向）の"
                "おすすめ設定が team_tactics に反映されます（HCスタイル・Team基本起用は変わりません）。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            lf0,
            text=(
                "※ 「カスタム」はプリセットのコンボ候補には出しません。"
                "現在の戦術プリセット状態の表示としてのみ使います。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            lf0,
            text=(
                "※ プリセット適用時はセット傾向（playbook）も更新されます。"
                "この画面のブロック 7 でも確認・編集できます。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        self._build_playstyle_preset_editor_ui(
            lf0,
            message_parent=w,
            after_apply=_after_playstyle_preset_apply,
            strategy_policy_combos=None,
        )
        ttk.Button(
            lf0,
            text="補助設定を開く（Team基本方針・HC）",
            style="Menu.TButton",
            command=lambda: self._open_tactics_core_policy_window(w),
        ).pack(anchor="w", pady=(8, 0))

        lf16 = ttk.LabelFrame(scroll_content, text="1〜6. 攻守の傾向", padding=10)
        lf16.pack(fill="x", pady=(0, 8))
        ttk.Label(
            lf16,
            text=(
                "保存先は team_tactics[\"team_strategy\"]。セット傾向（playbook）は別ブロックです。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        data_ov = get_safe_team_tactics(self.team)["team_strategy"]
        combos_ov = self._team_strategy_editor_build_row_combos(lf16, data_ov, pairs_ov, labels_ov)
        combos_holder["combos"] = combos_ov
        ttk.Label(
            lf16,
            text="※ 「標準に戻す」は表示だけ戻します。保存を押すと確定します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            lf16,
            text=(
                "※ ブロック0でプリセット適用すると、この 1〜6 の表示も自動で更新されます。"
                "別画面から手動変更した場合は「最新状態を読み込み」を押してください。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        btn_ov = ttk.Frame(lf16, style="Panel.TFrame")
        btn_ov.pack(fill="x", pady=(0, 6))

        def _save_ov() -> None:
            self._team_strategy_editor_save(
                combos_ov,
                pairs_ov,
                message_parent=w,
                message_title="保存",
                message_body="プレイスタイル（攻守の傾向）を保存しました。",
            )

        def _reset_ov() -> None:
            self._team_strategy_editor_reset_display(combos_ov, pairs_ov)

        def _reload_ov() -> None:
            self._team_strategy_editor_reload_from_team(combos_ov, pairs_ov)

        ttk.Button(btn_ov, text="保存", style="Primary.TButton", command=_save_ov).pack(side="left", padx=(0, 6))
        ttk.Button(btn_ov, text="標準に戻す", style="Menu.TButton", command=_reset_ov).pack(side="left", padx=(0, 6))
        ttk.Button(btn_ov, text="最新状態を読み込み", style="Menu.TButton", command=_reload_ov).pack(side="left", padx=0)

        lf7 = ttk.LabelFrame(scroll_content, text="7. セット傾向", padding=10)
        lf7.pack(fill="x", pady=(0, 8))
        hdr7 = ttk.Frame(lf7, style="Panel.TFrame")
        hdr7.pack(fill="x", anchor="w")
        inner7 = ttk.Frame(lf7, style="Panel.TFrame")
        ttk.Label(
            inner7,
            text=(
                "※ P&R / ハンドオフ / オフボールスクリーン / ポストアップ / Spain P&R / 速攻頻度を調整します。\n"
                "※ 「速攻頻度」は 6. トランジション方針とは別の playbook 項目です。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        pb_data_ov = get_safe_team_tactics(self.team)["playbook"]
        combos_pb_ov = self._playbook_editor_build_row_combos(inner7, pb_data_ov)
        playbook_combos_holder["combos"] = combos_pb_ov
        ttk.Label(
            inner7,
            text="※ 「標準に戻す」は表示だけ戻します。保存を押すと確定します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            inner7,
            text=(
                "※ ブロック0でプリセット適用すると、この 7 の表示も自動で更新されます。"
                "別画面から手動変更した場合は「最新状態を読み込み」を押してください。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        btn_pb_ov = ttk.Frame(inner7, style="Panel.TFrame")
        btn_pb_ov.pack(fill="x", pady=(0, 6))

        def _save_pb_ov() -> None:
            self._playbook_editor_save(combos_pb_ov, level_pairs_pb, message_parent=w)

        def _reset_pb_ov() -> None:
            self._playbook_editor_reset_display(combos_pb_ov, level_pairs_pb)

        def _reload_pb_ov() -> None:
            self._playbook_editor_reload_from_team(combos_pb_ov, level_pairs_pb)

        ttk.Button(btn_pb_ov, text="保存", style="Primary.TButton", command=_save_pb_ov).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_pb_ov, text="標準に戻す", style="Menu.TButton", command=_reset_pb_ov).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_pb_ov, text="最新状態を読み込み", style="Menu.TButton", command=_reload_pb_ov).pack(
            side="left", padx=0
        )

        def _toggle_pb_inner() -> None:
            if inner7.winfo_manager():
                inner7.pack_forget()
                toggle_pb.configure(text="開く")
            else:
                inner7.pack(fill="x", pady=(8, 0))
                toggle_pb.configure(text="閉じる")
            _playstyle_scrollregion()

        toggle_pb = ttk.Button(
            hdr7,
            text="開く",
            style="Menu.TButton",
            command=_toggle_pb_inner,
        )
        toggle_pb.pack(anchor="w")

        for _mw_host in (scroll_content, lf0, lf16, lf7, hdr7, inner7):
            _mw_host.bind("<MouseWheel>", _playstyle_wheel)
            _mw_host.bind("<Button-4>", lambda _e: ps_canvas.yview_scroll(-1, "units"))
            _mw_host.bind("<Button-5>", lambda _e: ps_canvas.yview_scroll(1, "units"))

    def _open_tactics_rotation_overview_window(self, parent: tk.Misc) -> None:
        """ローテーション統合画面の土台（0〜2の見出し・説明・補助導線）。"""
        if self.team is None:
            return
        try:
            ensure_team_tactics_on_team(self.team)
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("戦術：ローテーション")
        w.geometry("720x720")
        w.minsize(560, 560)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame")
        outer.pack(fill="both", expand=True)

        bf = ttk.Frame(outer, style="Root.TFrame", padding=(12, 8, 12, 12))
        bf.pack(side="bottom", fill="x")
        ttk.Button(bf, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right")

        intro_fr = ttk.Frame(outer, style="Root.TFrame", padding=(12, 12, 12, 0))
        intro_fr.pack(side="top", fill="x")
        ttk.Label(
            intro_fr,
            text=(
                "ローテーションは 0.起用プリセット / 1.チーム起用方針 / 2.起用序列 を中心に調整します。"
                "個別役割は自動タグ側で扱うため、この画面では手動設定しません。"
                "0 のプリセットはこの画面で直接適用できます。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=660,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        scroll_wrap = ttk.Frame(outer, style="Root.TFrame")
        scroll_wrap.pack(fill="both", expand=True)

        rot_canvas = tk.Canvas(scroll_wrap, bg="#15171c", highlightthickness=0)
        rot_vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=rot_canvas.yview)
        rot_canvas.configure(yscrollcommand=rot_vsb.set)
        scroll_content = ttk.Frame(rot_canvas, style="Root.TFrame", padding=12)
        rot_win_id = rot_canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _rot_scrollregion(_event: Any = None) -> None:
            rot_canvas.update_idletasks()
            bbox = rot_canvas.bbox("all")
            if bbox:
                rot_canvas.configure(scrollregion=bbox)

        def _rot_canvas_width(event: Any) -> None:
            try:
                rot_canvas.itemconfigure(rot_win_id, width=event.width)
            except tk.TclError:
                pass

        scroll_content.bind("<Configure>", lambda _e: _rot_scrollregion())

        rot_canvas.bind("<Configure>", _rot_canvas_width)

        def _rot_wheel(event: Any) -> None:
            if getattr(event, "delta", 0):
                rot_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _rot_bind_wheel(widget: tk.Misc) -> None:
            widget.bind("<MouseWheel>", _rot_wheel)
            widget.bind("<Button-4>", lambda _e: rot_canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda _e: rot_canvas.yview_scroll(1, "units"))
            try:
                for ch in widget.winfo_children():
                    _rot_bind_wheel(ch)
            except tk.TclError:
                pass

        for _mw_target in (w, rot_canvas, intro_fr):
            _mw_target.bind("<MouseWheel>", _rot_wheel)
            _mw_target.bind("<Button-4>", lambda _e: rot_canvas.yview_scroll(-1, "units"))
            _mw_target.bind("<Button-5>", lambda _e: rot_canvas.yview_scroll(1, "units"))

        rot_canvas.pack(side="left", fill="both", expand=True)
        rot_vsb.pack(side="right", fill="y")

        lf0 = ttk.LabelFrame(scroll_content, text="0. 起用プリセット", padding=10)
        lf0.pack(fill="x", pady=(0, 8))
        ttk.Label(
            lf0,
            text="プリセットを選んで「プリセット適用」すると、起用方針テンプレとローテ詳細のおすすめ設定が反映されます。",
            font=("Yu Gothic UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        usage_pairs_ov, usage_labels_ov = self._usage_policy_pairs_map_and_labels()
        usage_resync_holder: Dict[str, Optional[Callable[[], None]]] = {"fn": None}
        usage_resync_extras: List[Callable[[], None]] = []

        def _resync_usage_policy_from_preset() -> None:
            fn = usage_resync_holder.get("fn")
            if fn is not None:
                fn()
            for ex in usage_resync_extras:
                ex()

        self._build_rotation_preset_editor_ui(
            lf0,
            message_parent=w,
            after_apply=None,
            usage_policy_resync=_resync_usage_policy_from_preset,
        )
        ttk.Label(
            lf0,
            text="▼ いま入っているおすすめ（読み取り）",
            font=("Yu Gothic UI", 9, "bold"),
            foreground="#1a1d23",
        ).pack(anchor="w", pady=(8, 2))
        summary_lbl = ttk.Label(
            lf0,
            text="",
            font=("Yu Gothic UI", 9),
            foreground="#111111",
            wraplength=640,
            justify="left",
        )
        summary_lbl.pack(anchor="w", pady=(0, 6))

        rotation_lf0_readout_extras: List[Callable[[], None]] = []

        def _refresh_rotation_lf0_readouts() -> None:
            if self.team is None:
                return
            summary_lbl.configure(text=self._rotation_effect_summary_text())
            preview_lbl.configure(text=self._rotation_target_minutes_preview_text())
            for ex in rotation_lf0_readout_extras:
                try:
                    ex()
                except Exception:
                    pass

        self._rotation_overview_lf0_readouts = _refresh_rotation_lf0_readouts

        def _clear_rotation_overview_lf0_readouts(e: Any) -> None:
            if getattr(e, "widget", None) is not w:
                return
            self._rotation_overview_lf0_readouts = None  # type: ignore[assignment]

        try:
            w.bind("<Destroy>", _clear_rotation_overview_lf0_readouts, add=True)
        except Exception:
            pass

        ttk.Label(
            lf0,
            text="▼ 目標出場時間のおすすめ（読み取り）",
            font=("Yu Gothic UI", 9, "bold"),
            foreground="#1a1d23",
        ).pack(anchor="w", pady=(10, 2))
        preview_lbl = ttk.Label(
            lf0,
            text="",
            font=("Yu Gothic UI", 9),
            foreground="#111111",
            wraplength=640,
            justify="left",
        )
        preview_lbl.pack(anchor="w", pady=(0, 6))
        ttk.Button(
            lf0,
            text="このおすすめを目標出場時間に反映",
            style="Menu.TButton",
            command=lambda: self._apply_rotation_recommended_target_minutes(w),
        ).pack(anchor="w", pady=(0, 4))
        usage_resync_extras.append(_refresh_rotation_lf0_readouts)
        _refresh_rotation_lf0_readouts()
        ttk.Label(
            lf0,
            text=(
                "※ 反映先は team_tactics[\"usage_policy\"] と \"rotation\"、および Team.usage_policy です。"
                "1.チーム起用方針（テンプレ）と 2.ローテ補助設定のおすすめに相当します。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(6, 2))
        ttk.Label(
            lf0,
            text="※ 先発・6th・ベンチ順の Team 正本は変わりません。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            lf0,
            text="※ 「カスタム」はプリセットのコンボ候補には出しません。現在のローテプリセット状態の表示としてのみ使います。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        lf1 = ttk.LabelFrame(scroll_content, text="1. チーム起用方針", padding=10)
        lf1.pack(fill="x", pady=(0, 8))
        ttk.Label(
            lf1,
            text=(
                "この画面では、起用方針・評価・調子・コンディションなどの基本方針（usage_policy）を調整します。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            lf1,
            text="※ 外国籍枠や細かな国籍起用の微調整は、現在の主操作からは外しています（既存値は保存時に維持）。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        usage_data_ov = get_safe_team_tactics(self.team)["usage_policy"]
        combos_usage_ov = self._usage_policy_editor_build_row_combos(
            lf1,
            usage_data_ov,
            usage_pairs_ov,
            usage_labels_ov,
            include_notes=False,
            note_wraplength=640,
        )
        ttk.Label(
            lf1,
            text="※ 交代幅・疲労・終盤などの細部は、ローテ詳細で調整します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            lf1,
            text="※ 「標準に戻す」は表示だけ戻します。保存を押すと確定します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        def _save_usage_ov() -> None:
            def _after_save_usage() -> None:
                self._refresh_strategy_window()
                _refresh_rotation_lf0_readouts()

            self._usage_policy_editor_save(
                combos_usage_ov,
                usage_pairs_ov,
                message_parent=w,
                message_title="保存",
                message_body="起用方針テンプレ（usage_policy）を保存しました。",
                after_save=_after_save_usage,
            )

        def _reset_usage_ov() -> None:
            self._usage_policy_editor_reset_display(combos_usage_ov, usage_pairs_ov)
            _refresh_rotation_lf0_readouts()

        def _reload_usage_combos_only() -> None:
            self._usage_policy_editor_reload_from_team(combos_usage_ov, usage_pairs_ov)

        def _reload_usage_ov() -> None:
            _reload_usage_combos_only()
            _refresh_rotation_lf0_readouts()

        usage_resync_holder["fn"] = _reload_usage_combos_only

        r1a = ttk.Frame(lf1, style="Panel.TFrame")
        r1a.pack(fill="x", pady=(0, 4))
        ttk.Button(r1a, text="保存", style="Primary.TButton", command=_save_usage_ov).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(r1a, text="標準に戻す", style="Menu.TButton", command=_reset_usage_ov).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(r1a, text="最新状態を読み込み", style="Menu.TButton", command=_reload_usage_ov).pack(
            side="left"
        )

        r1 = ttk.Frame(lf1, style="Panel.TFrame")
        r1.pack(fill="x")
        ttk.Button(
            r1,
            text="ローテ詳細を別窓で開く（交代・疲労・終盤）",
            style="Menu.TButton",
            command=lambda: self._open_tactics_rotation_window(w),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            r1,
            text="ローテ詳細を別窓で開く（戦術先発・目標出場）",
            style="Menu.TButton",
            command=lambda: self._open_tactics_rotation_window(w),
        ).pack(side="left")

        lf2 = ttk.LabelFrame(scroll_content, text="2. 起用序列（Team正本）", padding=10)
        lf2.pack(fill="x", pady=(0, 8))
        ttk.Label(
            lf2,
            text=(
                "試合起用の正本は Team の先発・6th・ベンチ。目標出場やローテ方針は team_tactics の rotation。"
                "「おすすめを起用序列に反映」では、あわせて戦術先発（rotation.starters）も更新されます。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            lf2,
            text="▼ おすすめ起用序列（読み取り）",
            font=("Yu Gothic UI", 9, "bold"),
            foreground="#1a1d23",
        ).pack(anchor="w", pady=(4, 2))
        lineup_rec_lbl = ttk.Label(
            lf2,
            text="",
            font=("Yu Gothic UI", 9),
            foreground="#111111",
            wraplength=640,
            justify="left",
        )
        lineup_rec_lbl.pack(anchor="w", pady=(0, 4))
        ttk.Button(
            lf2,
            text="このおすすめを起用序列に反映",
            style="Menu.TButton",
            command=lambda: self._apply_recommended_lineup_to_team(w),
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            lf2,
            text=(
                "※ この一覧はおすすめ表示のみです。自動では反映されません。\n"
                "※ 先発・6th・ベンチ順を変更する場合は、下の起用序列で手動調整してください。\n"
                "※ 反映すると、Team正本の先発・6th・ベンチ順に加え、"
                "試合開始先発用の戦術先発にも同期します。\n"
                "※ 試合では外国籍枠やポジション条件により、最終先発が一部調整される場合があります。\n"
                "※ 目標出場時間は変更されません。\n"
                "※ 外国籍枠の制限はこのおすすめでは考慮していません。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        def _extra_lineup_recommendation_readout() -> None:
            lineup_rec_lbl.configure(text=self._rotation_lineup_recommendation_text())

        rotation_lf0_readout_extras.append(_extra_lineup_recommendation_readout)

        def _register_lineup_reload(fn: Callable[[], None]) -> None:
            self._tactics_rotation_lineup_reload = fn

        lf2_edit = ttk.Frame(lf2, style="Panel.TFrame")
        lf2_edit.pack(fill="x", pady=(0, 6))
        self._build_team_lineup_editor_ui(
            lf2_edit,
            message_parent=w,
            bench_cache_host=w,
            layout="collapsed",
            scroll_update=_rot_scrollregion,
            after_lineup_change=_refresh_rotation_lf0_readouts,
            register_lineup_reload=_register_lineup_reload,
        )
        ttk.Label(
            lf2,
            text="※ 目標出場時間・戦術先発などの補助設定は、ローテ詳細で調整します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            lf2,
            text="※ ローテ詳細窓は、上の「1. チーム起用方針」内のボタンから開けます（同一窓）。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(0, 0))

        _refresh_rotation_lf0_readouts()

        _rot_bind_wheel(scroll_content)

    def _open_tactics_core_policy_window(self, parent: tk.Misc) -> None:
        """プレイスタイル 0.戦術プリセット、および Team 側（strategy / coach / usage）の手動方針を扱う。"""
        if self.team is None:
            return
        lab_to_s = {lab: k for k, lab in STRATEGY_OPTIONS}
        lab_to_c = {lab: k for k, lab in COACH_STYLE_OPTIONS}
        lab_to_u = {lab: k for k, lab in USAGE_POLICY_OPTIONS}

        w = tk.Toplevel(parent)
        w.title("プレイスタイル：基本方針（Team）")
        w.geometry("540x520")
        w.minsize(480, 400)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        ttk.Label(
            wrap,
            text=(
                "プリセット適用：Team.strategy と team_tactics（攻守・セット等）をまとめて更新します"
                "（HCスタイル・基本起用はプリセットからは変わりません）。\n"
                "Team保存：基本戦術・HCスタイル・基本起用を手動で Team に保存します。 "
                "攻守の傾向・セット傾向など他窓と併用します。"
            ),
            wraplength=500,
        ).pack(anchor="w", pady=(0, 8))

        lf_team = ttk.LabelFrame(wrap, text="補助: Team基本方針（手動）", padding=8)
        row_s = ttk.Frame(lf_team, style="Panel.TFrame")
        row_s.pack(fill="x", pady=4)
        ttk.Label(row_s, text="基本戦術 (Team.strategy)", width=26).pack(side="left")
        combo_s = ttk.Combobox(row_s, state="readonly", width=28)
        combo_s["values"] = [lab for _, lab in STRATEGY_OPTIONS]
        combo_s.pack(side="left", padx=6)

        row_c = ttk.Frame(lf_team, style="Panel.TFrame")
        row_c.pack(fill="x", pady=4)
        ttk.Label(row_c, text="HCスタイル (coach_style)", width=26).pack(side="left")
        combo_c = ttk.Combobox(row_c, state="readonly", width=28)
        combo_c["values"] = [lab for _, lab in COACH_STYLE_OPTIONS]
        combo_c.pack(side="left", padx=6)

        row_u = ttk.Frame(lf_team, style="Panel.TFrame")
        row_u.pack(fill="x", pady=4)
        ttk.Label(row_u, text="基本起用 (Team.usage_policy)", width=26).pack(side="left")
        combo_u = ttk.Combobox(row_u, state="readonly", width=28)
        combo_u["values"] = [lab for _, lab in USAGE_POLICY_OPTIONS]
        combo_u.pack(side="left", padx=6)

        lf_ps = ttk.LabelFrame(wrap, text="0. 戦術プリセット", padding=8)
        sync_ps, sync_combo = self._build_playstyle_preset_editor_ui(
            lf_ps,
            message_parent=w,
            after_apply=None,
            strategy_policy_combos=(combo_s, combo_c, combo_u),
        )

        def _on_save() -> None:
            if self.team is None:
                return
            try:
                sk = lab_to_s[combo_s.get()]
                ck = lab_to_c[combo_c.get()]
                uk = lab_to_u[combo_u.get()]
            except (KeyError, tk.TclError):
                messagebox.showerror("エラー", "選択値を取得できませんでした。", parent=w)
                return
            old_coach = str(getattr(self.team, "coach_style", "balanced") or "balanced")
            ok, msg = apply_team_gm_settings(self.team, sk, ck, uk)
            if not ok:
                messagebox.showerror("反映できません", msg, parent=w)
                return
            self.refresh()
            self._refresh_strategy_window()
            lines = ["基本戦術・HC・基本起用を反映しました。"]
            if old_coach != ck:
                lines.append("")
                lines.extend(self._build_coach_unlock_diff_lines(old_coach, ck))
            messagebox.showinfo("保存", "\n".join(lines), parent=w)
            sync_ps()

        # 表示順：上段 0.戦術プリセット → 下段 Team 補助
        lf_ps.pack(fill="x", pady=(0, 8))
        lf_team.pack(fill="x", pady=(0, 8))
        self._sync_strategy_policy_combos(combo_s, combo_c, combo_u)
        sync_ps()
        sync_combo()

        team_btn_row = ttk.Frame(lf_team, style="Panel.TFrame")
        team_btn_row.pack(fill="x", pady=(8, 0))
        ttk.Button(team_btn_row, text="保存", style="Menu.TButton", command=_on_save, width=16).pack(
            side="right", padx=4
        )
        btn_row = ttk.Frame(wrap, style="Panel.TFrame")
        btn_row.pack(fill="x", pady=(0, 0))
        ttk.Button(btn_row, text="閉じる", style="Menu.TButton", command=w.destroy, width=16).pack(
            side="right", padx=4
        )
        try:
            close_key = getattr(self, "_close_subwindow_bind_seq", None)
            if close_key:
                w.bind(close_key, lambda _e: w.destroy())
        except Exception:
            pass

    def _build_team_lineup_editor_ui(
        self,
        parent: ttk.Frame,
        *,
        message_parent: tk.Misc,
        bench_cache_host: Any,
        layout: str = "flat",
        scroll_update: Optional[Callable[[], None]] = None,
        after_lineup_change: Optional[Callable[[], None]] = None,
        register_lineup_reload: Optional[Callable[[Callable[[], None]], None]] = None,
    ) -> None:
        """
        Team 正本: 先発5 / 6th / ベンチ順（7〜12）。gm_dashboard_text の apply / 候補生成をそのまま利用。
        layout: \"flat\"（子窓）または \"collapsed\"（統合画面用・初期は各サブブロック閉じる）。
        register_lineup_reload: 内蔵の _reload_all を登録するコールバック（おすすめ反映後の再表示用）。
        """
        if self.team is None:
            return

        mp = message_parent
        bch = bench_cache_host

        starter_combos: List[ttk.Combobox] = []
        starter_btns: List[ttk.Button] = []
        slot_labels: List[Tuple[ttk.Label, ttk.Combobox]] = []
        six_combo: Optional[ttk.Combobox] = None
        six_apply: Optional[ttk.Button] = None
        bench_a: Optional[ttk.Combobox] = None
        bench_b: Optional[ttk.Combobox] = None
        bench_swap: Optional[ttk.Button] = None
        bench_order_list_lbl: Optional[ttk.Label] = None

        def _maybe_scroll() -> None:
            if scroll_update is not None:
                try:
                    scroll_update()
                except Exception:
                    pass

        def _reload_all() -> None:
            _reload_starters()
            _reload_sixth()
            _reload_bench()
            _maybe_scroll()

        def _after_mutation() -> None:
            self.refresh()
            self._refresh_strategy_window()
            _reload_all()
            if after_lineup_change is not None:
                try:
                    after_lineup_change()
                except Exception:
                    pass

        def _reload_starters() -> None:
            starters = get_current_starting_five(self.team)
            if len(starters) < 5:
                for it in slot_labels:
                    it[0].configure(text="（5人未満のため先発枠の編集はできません）")
                for _i, cbo in enumerate(starter_combos):
                    cbo.configure(values=[], state="disabled")
                for btn in starter_btns:
                    btn.configure(state="disabled")
                return
            for btn in starter_btns:
                btn.configure(state="normal")
            for i in range(5):
                p_cur = starters[i]
                cands = get_available_starting_candidates(self.team, starters, i)
                labels = [self._gm_candidate_label_for_player(p) for p in cands]
                cb = starter_combos[i]
                if not labels:
                    cb.configure(values=[], state="disabled")
                else:
                    cb.configure(values=labels, state="readonly")
                    prefer = self._gm_candidate_label_for_player(p_cur)
                    cb.set(prefer if prefer in labels else labels[0])
                slot_labels[i][0].configure(
                    text=f"枠{i + 1} 現在: {getattr(p_cur, 'name', '-')} ({getattr(p_cur, 'position', '?')})",
                )

        def _on_apply_slot(idx: int) -> None:
            starters = get_current_starting_five(self.team)
            if len(starters) < 5:
                return
            cands = get_available_starting_candidates(self.team, starters, idx)
            sel = starter_combos[idx].get()
            picked = next(
                (p for p in cands if self._gm_candidate_label_for_player(p) == sel),
                None,
            )
            if picked is None:
                messagebox.showerror("エラー", "候補を選択してください。", parent=mp)
                return
            ok, msg = apply_starting_slot_change(self.team, idx, picked)
            if not ok:
                messagebox.showerror("反映できません", msg, parent=mp)
                return
            _after_mutation()

        def _on_reset_starting() -> None:
            try:
                ok = messagebox.askokcancel(
                    "自動スタメンに戻す",
                    "カスタム先発（Team.starting_lineup）を解除し、自動選出に戻しますか？\n\n"
                    "※ 6th の指定はそのままです。",
                    parent=mp,
                )
            except Exception:
                return
            if not ok:
                return
            clr = getattr(self.team, "clear_starting_lineup", None)
            if not callable(clr):
                messagebox.showinfo("未対応", "このチームでは解除できません。", parent=mp)
                return
            try:
                clr()
            except Exception as exc:
                messagebox.showerror("エラー", str(exc), parent=mp)
                return
            _after_mutation()
            messagebox.showinfo("完了", "先発を自動選出に戻しました。", parent=mp)

        def _reload_sixth() -> None:
            nonlocal six_combo, six_apply
            if six_combo is None or six_apply is None:
                return
            cands = get_sixth_man_candidates(self.team)
            labels = [self._gm_candidate_label_for_player(p) for p in cands]
            if not labels:
                six_combo.configure(values=[], state="disabled")
                six_apply.configure(state="disabled")
            else:
                six_combo.configure(values=labels, state="readonly")
                sm = get_current_sixth_man(self.team)
                if sm is not None:
                    t = self._gm_candidate_label_for_player(sm)
                    six_combo.set(t if t in labels else labels[0])
                else:
                    six_combo.set(labels[0])
                six_apply.configure(state="normal")

        def _on_apply_sixth() -> None:
            if six_combo is None:
                return
            cands = get_sixth_man_candidates(self.team)
            labels = {self._gm_candidate_label_for_player(p): p for p in cands}
            sel = six_combo.get()
            p = labels.get(sel)
            if p is None:
                messagebox.showerror("エラー", "6th候補を選んでください。", parent=mp)
                return
            ok, msg = apply_sixth_man_selection(self.team, p)
            if not ok:
                messagebox.showerror("反映できません", msg, parent=mp)
                return
            _after_mutation()
            messagebox.showinfo("完了", "6thを更新しました。", parent=mp)

        def _on_reset_sixth() -> None:
            try:
                ok = messagebox.askokcancel(
                    "自動6thに戻す",
                    "手動の6thを解除し、自動選出に戻しますか？",
                    parent=mp,
                )
            except Exception:
                return
            if not ok:
                return
            clr = getattr(self.team, "clear_sixth_man", None)
            if not callable(clr):
                messagebox.showinfo("未対応", "このチームでは解除できません。", parent=mp)
                return
            try:
                clr()
            except Exception as exc:
                messagebox.showerror("エラー", str(exc), parent=mp)
                return
            _after_mutation()
            messagebox.showinfo("完了", "6thを自動選出に戻しました。", parent=mp)

        def _bench_slot_labels(players: List[Any]) -> List[str]:
            return [f"{i + 7}番手 {self._gm_candidate_label_for_player(p)}" for i, p in enumerate(players)]

        def _player_ovr_for_bench_list(p: Any) -> int:
            if hasattr(p, "get_effective_ovr") and callable(getattr(p, "get_effective_ovr")):
                try:
                    return int(p.get_effective_ovr())
                except (TypeError, ValueError, AttributeError):
                    pass
            try:
                return int(getattr(p, "ovr", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _format_bench_order_list_text(bench_players: List[Any]) -> str:
            """7番手〜の読み取り表示（先発・6thは含めない。get_current_bench_order 由来）。"""
            if not bench_players:
                return "ベンチ順は未設定です。\n（先発・6thを除く控えに、表示できる選手がいません。）"
            max_rows = 6
            lines: List[str] = []
            for i, p in enumerate(bench_players[:max_rows]):
                slot = i + 7
                nm = str(getattr(p, "name", "?"))
                pos = str(getattr(p, "position", "?"))
                ovr = _player_ovr_for_bench_list(p)
                lines.append(f"{slot}番手　{nm}　{pos}　OVR {ovr}")
            if len(bench_players) > max_rows:
                rest = len(bench_players) - max_rows
                lines.append(f"… 他 {rest} 名（表示は12番手まで）")
            return "\n".join(lines)

        def _reload_bench() -> None:
            nonlocal bench_a, bench_b, bench_swap
            if bench_a is None or bench_b is None or bench_swap is None:
                return
            bench = list(get_current_bench_order(self.team) or [])
            setattr(bch, "_tactics_bench_players_cache", bench)
            if bench_order_list_lbl is not None:
                try:
                    bench_order_list_lbl.configure(text=_format_bench_order_list_text(bench))
                except tk.TclError:
                    pass
            labels = _bench_slot_labels(bench)
            if len(bench) < 2:
                bench_a.configure(values=[], state="disabled")
                bench_b.configure(values=[], state="disabled")
                bench_swap.configure(state="disabled")
            else:
                for c in (bench_a, bench_b):
                    c.configure(values=labels, state="readonly")
                bench_a.set(labels[0])
                bench_b.set(labels[1] if len(labels) > 1 else labels[0])
                bench_swap.configure(state="normal")

        def _on_bench_swap() -> None:
            if bench_a is None or bench_b is None:
                return
            bench = list(getattr(bch, "_tactics_bench_players_cache", None) or [])
            labels = _bench_slot_labels(bench)
            if len(bench) < 2:
                messagebox.showwarning("ベンチ", "ベンチが2人未満です。", parent=mp)
                return
            try:
                sa = bench_a.get()
                sb = bench_b.get()
            except tk.TclError:
                return
            try:
                idx_a = labels.index(sa)
                idx_b = labels.index(sb)
            except ValueError:
                messagebox.showwarning("ベンチ", "控えを選択してください。", parent=mp)
                return
            if idx_a == idx_b:
                messagebox.showwarning("ベンチ", "異なる2つを選んでください。", parent=mp)
                return
            pa, pb = bench[idx_a], bench[idx_b]
            try:
                ok = messagebox.askokcancel(
                    "ベンチ入替",
                    f"{idx_a + 7}番手（{getattr(pa, 'name', '')}）と "
                    f"{idx_b + 7}番手（{getattr(pb, 'name', '')}）の順序を入れ替えますか？",
                    parent=mp,
                )
            except Exception:
                return
            if not ok:
                return
            success, bmsg = apply_bench_order_swap(self.team, idx_a, idx_b)
            if not success:
                messagebox.showerror("反映できません", bmsg, parent=mp)
                return
            _after_mutation()
            messagebox.showinfo("完了", "ベンチ序列を更新しました。", parent=mp)

        def _on_reset_bench() -> None:
            try:
                ok = messagebox.askokcancel(
                    "自動ベンチに戻す",
                    "手動のベンチ序列を解除し、自動（OVR順等）に戻しますか？",
                    parent=mp,
                )
            except Exception:
                return
            if not ok:
                return
            clr = getattr(self.team, "clear_bench_order", None)
            if not callable(clr):
                messagebox.showinfo("未対応", "このチームでは解除できません。", parent=mp)
                return
            try:
                clr()
            except Exception as exc:
                messagebox.showerror("エラー", str(exc), parent=mp)
                return
            _after_mutation()
            messagebox.showinfo("完了", "ベンチ序列を自動に戻しました。", parent=mp)

        def _build_starters_block(into: ttk.Frame) -> None:
            lf_s = ttk.LabelFrame(into, text="2-1. 先発（枠1〜5）", padding=8)
            lf_s.pack(fill="x", pady=(0, 8))
            ttk.Label(
                lf_s,
                text="※ 枠1〜5は現在の先発順です。ポジション固定ではありません。",
                font=("Yu Gothic UI", 9),
                foreground="#9aa3b2",
                wraplength=640,
            ).pack(anchor="w", pady=(0, 6))
            starter_combos.clear()
            starter_btns.clear()
            slot_labels.clear()
            for i in range(5):
                row = ttk.Frame(lf_s, style="Panel.TFrame")
                row.pack(fill="x", pady=2)
                lab = ttk.Label(row, text="", width=40)
                lab.pack(side="left", anchor="w")
                cb = ttk.Combobox(row, state="readonly", width=38)
                cb.pack(side="left", padx=4)
                btn = ttk.Button(
                    row, text="反映", style="Menu.TButton", width=8, command=lambda j=i: _on_apply_slot(j)
                )
                btn.pack(side="left", padx=4)
                slot_labels.append((lab, cb))
                starter_combos.append(cb)
                starter_btns.append(btn)
            ttk.Button(
                lf_s,
                text="自動スタメンに戻す（clear_starting_lineup）",
                style="Menu.TButton",
                command=_on_reset_starting,
            ).pack(anchor="e", pady=(8, 0))

        def _build_sixth_block(into: ttk.Frame) -> None:
            nonlocal six_combo, six_apply
            lf_6 = ttk.LabelFrame(into, text="2-2. 6thマン", padding=8)
            lf_6.pack(fill="x", pady=(0, 8))
            r6 = ttk.Frame(lf_6, style="Panel.TFrame")
            r6.pack(fill="x")
            six_combo = ttk.Combobox(r6, state="readonly", width=50)
            six_combo.pack(side="left", padx=4)
            six_apply = ttk.Button(r6, text="6thに反映", style="Menu.TButton", width=12, command=_on_apply_sixth)
            six_apply.pack(side="left", padx=4)
            ttk.Button(r6, text="自動6thに戻す", style="Menu.TButton", command=_on_reset_sixth).pack(
                side="left", padx=4
            )

        def _build_bench_block(into: ttk.Frame) -> None:
            nonlocal bench_a, bench_b, bench_swap, bench_order_list_lbl
            lf_b = ttk.LabelFrame(into, text="2-3. ベンチ順（7〜12番手）", padding=8)
            lf_b.pack(fill="x", pady=(0, 8))
            ttk.Label(
                lf_b,
                text="現在のベンチ順",
                font=("Yu Gothic UI", 9, "bold"),
                foreground="#1a1d23",
            ).pack(anchor="w", pady=(0, 2))
            bench_order_list_lbl = ttk.Label(
                lf_b,
                text="",
                font=("Yu Gothic UI", 9),
                foreground="#111111",
                wraplength=640,
                justify="left",
            )
            bench_order_list_lbl.pack(anchor="w", pady=(0, 8))
            rb = ttk.Frame(lf_b, style="Panel.TFrame")
            rb.pack(fill="x", pady=2)
            ttk.Label(rb, text="枠A", width=4).pack(side="left")
            bench_a = ttk.Combobox(rb, state="readonly", width=42)
            bench_a.pack(side="left", padx=4)
            ttk.Label(rb, text="枠B", width=4).pack(side="left")
            bench_b = ttk.Combobox(rb, state="readonly", width=42)
            bench_b.pack(side="left", padx=4)
            rbb = ttk.Frame(lf_b, style="Panel.TFrame")
            rbb.pack(fill="x", pady=6)
            bench_swap = ttk.Button(
                rbb, text="選択2人の順序を入れ替え", style="Menu.TButton", command=_on_bench_swap
            )
            bench_swap.pack(side="left", padx=4)
            ttk.Button(
                rbb, text="自動ベンチに戻す（clear_bench_order）", style="Menu.TButton", command=_on_reset_bench
            ).pack(side="left", padx=4)

        if layout == "collapsed":

            def _add_collapsible(title_open: str, title_close: str, build_fn: Callable[[ttk.Frame], None]) -> None:
                wrap = ttk.Frame(parent, style="Panel.TFrame")
                wrap.pack(fill="x", pady=(0, 6))
                hdr = ttk.Frame(wrap, style="Panel.TFrame")
                hdr.pack(fill="x")
                inner = ttk.Frame(wrap, style="Panel.TFrame")
                build_fn(inner)

                def _toggle() -> None:
                    if inner.winfo_manager():
                        inner.pack_forget()
                        btn.configure(text=title_open)
                    else:
                        inner.pack(fill="x", pady=(4, 0))
                        btn.configure(text=title_close)
                    _maybe_scroll()

                btn = ttk.Button(hdr, text=title_open, style="Menu.TButton", command=_toggle)
                btn.pack(side="left", anchor="w")

            _add_collapsible("先発を開く", "先発を閉じる", _build_starters_block)
            _add_collapsible("6thマンを開く", "6thマンを閉じる", _build_sixth_block)
            _add_collapsible("ベンチ順を開く", "ベンチ順を閉じる", _build_bench_block)
        else:
            body = ttk.Frame(parent, style="Panel.TFrame")
            body.pack(fill="x")
            _build_starters_block(body)
            _build_sixth_block(body)
            _build_bench_block(body)

        _reload_all()
        if register_lineup_reload is not None:
            try:
                register_lineup_reload(_reload_all)
            except Exception:
                pass

    def _open_tactics_team_lineup_window(self, parent: tk.Misc) -> None:
        """Team.starting_lineup / sixth_man_id / bench_order を編集（gm_dashboard_text 経路。CLI と整合）。"""
        if self.team is None:
            return

        w = tk.Toplevel(parent)
        w.title("ローテーション：先発・6th・ベンチ（Team）")
        w.geometry("720x780")
        w.minsize(640, 580)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="2. 起用序列（Team正本）",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            outer,
            text=(
                "Team正本の先発・6th・ベンチ順を編集します（試合起用の基本）。"
                " 「ローテ詳細」の team_tactics.rotation（戦術用先発・目標出場など）とは別データです。\n"
                "※ 目標出場時間（0〜40分）は「ローテ詳細」で調整します。"
                " チーム寄りの補正は「起用テンプレ」、選手の役割表示は能力・起用・成績などから自動タグとして扱います。"
            ),
            wraplength=680,
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 10))

        body = ttk.Frame(outer, style="Panel.TFrame")
        body.pack(fill="both", expand=True)
        self._build_team_lineup_editor_ui(
            body,
            message_parent=w,
            bench_cache_host=w,
            layout="flat",
            scroll_update=None,
        )

        bot = ttk.Frame(outer, style="Panel.TFrame")
        bot.pack(fill="x", pady=(12, 0))
        ttk.Button(bot, text="閉じる", style="Menu.TButton", command=w.destroy, width=14).pack(
            side="right"
        )
        try:
            close_key = getattr(self, "_close_subwindow_bind_seq", None)
            if close_key:
                w.bind(close_key, lambda _e: w.destroy())
        except Exception:
            pass

    def _open_tactics_team_strategy_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        pairs_map, labels = self._team_strategy_pairs_map_and_labels()
        data = get_safe_team_tactics(self.team)["team_strategy"]
        w = tk.Toplevel(parent)
        w.title("プレイスタイル：攻守の傾向（team_tactics）")
        w.geometry("520x420")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        ttk.Label(
            wrap,
            text=(
                "1〜6のプレイスタイル項目を調整します。保存先は team_tactics[\"team_strategy\"] です。\n"
                "セット傾向（playbook）は別画面。トランジションは全体の速攻姿勢で、"
                "playbook の速攻頻度とは別です。※ 一部候補は今後の拡張対象です。"
            ),
            wraplength=480,
        ).pack(anchor="w", pady=(0, 10))
        combos = self._team_strategy_editor_build_row_combos(wrap, data, pairs_map, labels)
        ttk.Label(
            wrap,
            text="※ 「標準に戻す」は表示だけ戻します。保存を押すと確定します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        def _save() -> None:
            self._team_strategy_editor_save(
                combos,
                pairs_map,
                message_parent=w,
                message_title="保存",
                message_body="プレイスタイル（攻守の傾向）を保存しました。",
            )

        def _reset() -> None:
            self._team_strategy_editor_reset_display(combos, pairs_map)

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x", pady=(12, 0))
        ttk.Button(btn, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn, text="標準に戻す", style="Menu.TButton", command=_reset).pack(side="left", padx=4)
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

    def _open_tactics_rotation_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        rot = get_safe_team_tactics(self.team)["rotation"]
        roster = list(self._safe_get(self.team, "players", []) or [])
        roster_sorted = sorted(
            roster,
            key=lambda p: (-int(getattr(p, "ovr", 0)), str(getattr(p, "name", ""))),
        )
        slot_labels = [("未設定", None)] + [
            (f"{getattr(p, 'name', '-')} ({getattr(p, 'position', '?')})", int(getattr(p, "player_id", 0)))
            for p in roster_sorted
            if getattr(p, "player_id", None) is not None
        ]

        sub_pairs = [
            ("standard", "標準"),
            ("starters_long", "主力長め"),
            ("bench_deep", "ベンチ厚め"),
            ("youth_dev", "若手育成"),
        ]
        fat_pairs = [("strict", "疲労に厳格"), ("standard", "標準"), ("push", "多少無理をさせる")]
        foul_pairs = [("early_pull", "早めに下げる"), ("standard", "標準"), ("ride", "我慢する")]
        clutch_pairs = [
            ("stars", "主力固定"),
            ("hot_hand", "好調優先"),
            ("defense", "守備重視"),
            ("offense", "攻撃重視"),
        ]

        w = tk.Toplevel(parent)
        w.title("ローテーション：交代・目標出場（team_tactics）")
        w.geometry("640x700")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        ttk.Label(
            wrap,
            text=(
                "この窓では team_tactics[\"rotation\"] の細部を保存します。"
                " 1は交代・疲労/ファウル配慮・終盤、2は戦術用先発と目標出場です。\n"
                "本流の先発/6th/ベンチ（Team）とは別データです。"
            ),
            wraplength=600,
        ).pack(anchor="w", pady=(0, 6))

        def _policy_combo(
            row_parent: ttk.Frame, label: str, pairs: List[Tuple[str, str]], cur: str
        ) -> ttk.Combobox:
            r = ttk.Frame(row_parent, style="Panel.TFrame")
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=label, width=24).pack(side="left")
            cb = ttk.Combobox(r, state="readonly", width=28)
            vals = [b for _, b in pairs]
            cb["values"] = vals
            ints = [a for a, _ in pairs]
            cb.set(vals[ints.index(cur)] if cur in ints else vals[0])
            cb.pack(side="left", padx=6)
            return cb

        lf1 = ttk.LabelFrame(wrap, text="1. チーム起用方針（rotation・細部）", padding=8)
        pol_frame = ttk.Frame(lf1, style="Panel.TFrame")
        pol_frame.pack(fill="x")
        cb_sub = _policy_combo(pol_frame, "選手起用の幅（交代・ローテ）", sub_pairs, str(rot.get("sub_policy", "standard")))
        cb_fat = _policy_combo(pol_frame, "疲労・スタミナ配慮", fat_pairs, str(rot.get("fatigue_policy", "standard")))
        foul_note_fr = ttk.Frame(pol_frame, style="Panel.TFrame")
        foul_note_fr.pack(fill="x", pady=(2, 0))
        ttk.Label(
            foul_note_fr,
            text=(
                "※ ファウル配慮は、個人ファウル数に応じた交代補正として一部反映されます。\n"
                "※ 5ファウル退場、チームファウル、非FTファウル、ボーナスFTは最小実装済みです。\n"
                "※ 非FT後の本格的なサイド再開処理は未実装です。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=520,
        ).pack(anchor="w", pady=(0, 2))
        cb_foul = _policy_combo(pol_frame, "ファウル配慮", foul_pairs, str(rot.get("foul_policy", "standard")))
        cb_clutch = _policy_combo(pol_frame, "終盤起用方針", clutch_pairs, str(rot.get("clutch_policy", "stars")))

        lf2 = ttk.LabelFrame(wrap, text="2. 起用序列（rotation・補助）", padding=8)
        ttk.Label(
            lf2,
            text=(
                "本流の先発・6th・ベンチ順は「先発・6th・ベンチ」窓で編集します。"
                " この窓では戦術用先発と目標出場時間を調整します。"
            ),
            font=("Yu Gothic UI", 9),
            wraplength=560,
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            lf2,
            text="戦術用先発（ポジション別・rotation へ保存）",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(anchor="w")
        starter_combos: Dict[str, ttk.Combobox] = {}
        starters_state = rot.get("starters") or {}
        for pos in STARTER_POSITIONS:
            row = ttk.Frame(lf2, style="Panel.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=pos, width=4).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=42)
            displays = [t[0] for t in slot_labels]
            cb["values"] = displays
            cur_id = starters_state.get(pos) if isinstance(starters_state, dict) else None
            sel = 0
            for i, (_, pid) in enumerate(slot_labels):
                if pid == cur_id:
                    sel = i
                    break
            cb.current(sel)
            cb.pack(side="left", padx=6)
            starter_combos[pos] = cb
        ttk.Label(
            lf2,
            text="控え順は現在この窓では編集せず、既存値を保存時に維持します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=520,
        ).pack(anchor="w", pady=(8, 4))
        ttk.Label(
            lf2,
            text="目標出場時間（分・0〜40）",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(anchor="w", pady=(4, 4))
        minutes_frame = ttk.Frame(lf2, style="Panel.TFrame")
        minutes_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(minutes_frame, bg="#1d2129", highlightthickness=0, height=220)
        vsb = ttk.Scrollbar(minutes_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Panel.TFrame")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        scales: Dict[int, tk.Scale] = {}
        tm = rot.get("target_minutes") if isinstance(rot.get("target_minutes"), dict) else {}
        for p in roster_sorted:
            pid = getattr(p, "player_id", None)
            if pid is None:
                continue
            pid = int(pid)
            row = ttk.Frame(inner, style="Panel.TFrame")
            row.pack(fill="x", pady=2)
            nm = str(getattr(p, "name", "-"))[:14]
            ttk.Label(row, text=f"{nm}", width=16).pack(side="left")
            try:
                init_v = float(tm.get(str(pid), tm.get(pid, 20.0)))
            except (TypeError, ValueError):
                init_v = 20.0
            init_v = max(0.0, min(40.0, init_v))
            sc = tk.Scale(
                row,
                from_=0,
                to=40,
                orient="horizontal",
                length=180,
                showvalue=True,
                resolution=1,
            )
            sc.set(init_v)
            sc.pack(side="left", padx=8)
            scales[pid] = sc

        lf1.pack(fill="x", pady=(0, 8))
        lf2.pack(fill="both", expand=True, pady=(0, 8))

        def _collect_rotation() -> Dict[str, Any]:
            starters: Dict[str, Any] = {}
            for pos, cb in starter_combos.items():
                idx = cb.current()
                if idx is None or idx < 0:
                    idx = 0
                _label, pid = slot_labels[idx]
                starters[pos] = pid

            def _read_pol(cb: ttk.Combobox, pairs: List[Tuple[str, str]]) -> str:
                d = cb.get()
                for a, b in pairs:
                    if b == d:
                        return a
                return pairs[0][0]

            target_minutes: Dict[str, float] = {}
            for pid, sc in scales.items():
                target_minutes[str(pid)] = float(sc.get())

            return {
                "starters": starters,
                "bench_order": list(rot.get("bench_order") or []),
                "target_minutes": target_minutes,
                "sub_policy": _read_pol(cb_sub, sub_pairs),
                "fatigue_policy": _read_pol(cb_fat, fat_pairs),
                "foul_policy": _read_pol(cb_foul, foul_pairs),
                "clutch_policy": _read_pol(cb_clutch, clutch_pairs),
            }

        def _save() -> None:
            raw = dict(get_safe_team_tactics(self.team))
            raw["rotation"] = _collect_rotation()
            self._tactics_commit_payload(raw)
            messagebox.showinfo("保存", "ローテーション（rotation）を保存しました。", parent=w)
            self._refresh_strategy_window()

        def _reset() -> None:
            d = get_default_team_tactics()["rotation"]
            for pos, cb in starter_combos.items():
                cb.current(0)
            cb_sub.set(sub_pairs[0][1])
            cb_fat.set(fat_pairs[1][1])
            cb_foul.set(foul_pairs[1][1])
            cb_clutch.set(clutch_pairs[0][1])
            for pid, sc in scales.items():
                sc.set(20.0)

        btn = tk.Frame(wrap, bg="#1d2129")
        btn.pack(fill="x", pady=(8, 0))
        self._jpn_text_button(btn, "保存", _save, primary=True, side="left", padx=4)
        self._jpn_text_button(btn, "標準に戻す", _reset, side="left", padx=4)
        self._jpn_text_button(btn, "閉じる", w.destroy, side="right", padx=4)

    def _open_tactics_usage_policy_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        usage_pairs, usage_labels = self._usage_policy_pairs_map_and_labels()
        w = tk.Toplevel(parent)
        w.title("ローテーション：起用方針テンプレ（team_tactics）")
        w.geometry("560x860")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)

        help_fr = ttk.Frame(wrap, style="Panel.TFrame")
        ttk.Label(
            help_fr,
            text=(
                "プリセット適用：Team.usage_policy・起用方針（usage_policy）・ローテ詳細（rotation）をまとめて更新します。"
                " 手動保存：下段のチーム起用方針だけを team_tactics[\"usage_policy\"] として保存します（rotation 本体は更新しません）。\n"
                "プレイスタイル基本方針（Team）とは別レーンです。"
                " 先発・6th・ベンチの並びは「先発・6th・ベンチ」窓の Team で決めます。\n"
                "※ 起用幅・疲労/ファウル・終盤方針の細かい数値は「ローテ詳細」で扱います。"
            ),
            wraplength=500,
        ).pack(anchor="w")
        help_fr.pack(fill="x", pady=(0, 8))

        lf_up = ttk.LabelFrame(wrap, text="1. チーム起用方針（手動）", padding=8)
        ttk.Label(
            lf_up,
            text="この画面では、起用方針・評価・調子・コンディションなどの基本方針を調整します。",
            wraplength=500,
        ).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            lf_up,
            text="※ 外国籍枠や細かな国籍起用の微調整は、現在の主操作からは外しています（既存値は保存時に維持）。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=500,
        ).pack(anchor="w", pady=(0, 6))
        usage_data = get_safe_team_tactics(self.team)["usage_policy"]
        combos = self._usage_policy_editor_build_row_combos(
            lf_up,
            usage_data,
            usage_pairs,
            usage_labels,
            include_notes=True,
            note_wraplength=500,
        )

        def _save() -> None:
            self._usage_policy_editor_save(
                combos,
                usage_pairs,
                message_parent=w,
                message_title="保存",
                message_body="起用方針テンプレ（usage_policy）を保存しました。",
                after_save=sync_rs,
            )

        def _reset() -> None:
            self._usage_policy_editor_reset_display(combos, usage_pairs)

        btn_up = ttk.Frame(lf_up, style="Panel.TFrame")
        btn_up.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_up, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn_up, text="標準に戻す", style="Menu.TButton", command=_reset).pack(side="left", padx=4)

        def _resync_usage_combos_from_team() -> None:
            self._usage_policy_editor_reload_from_team(combos, usage_pairs)

        lf_ps = ttk.LabelFrame(wrap, text="0. 起用プリセット", padding=8)
        preset_top = ttk.Frame(lf_ps, style="Panel.TFrame")
        preset_top.pack(fill="x", pady=(0, 4))
        ttk.Label(
            preset_top,
            text="正典プリセット3種。適用で Team 起用・起用方針・ローテ詳細を一括反映。Team 先発・6th・ベンチ順は変えません。",
            wraplength=500,
        ).pack(anchor="w")
        sync_rs, sync_rc = self._build_rotation_preset_editor_ui(
            lf_ps,
            message_parent=w,
            after_apply=None,
            usage_policy_resync=_resync_usage_combos_from_team,
        )

        lf_ps.pack(fill="x", pady=(0, 8))
        lf_up.pack(fill="both", expand=True, pady=(0, 8))
        btn_close = ttk.Frame(wrap, style="Panel.TFrame")
        btn_close.pack(fill="x", pady=(0, 0))
        ttk.Button(btn_close, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

    def _open_tactics_playbook_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        level_pairs = self._PLAYBOOK_LEVEL_PAIRS
        pb = get_safe_team_tactics(self.team)["playbook"]
        w = tk.Toplevel(parent)
        w.title("プレイスタイル：セット傾向（playbook）")
        w.geometry("480x390")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        pb_note_fr = ttk.Frame(wrap, style="Panel.TFrame")
        pb_note_fr.pack(fill="x", pady=(0, 8))
        ttk.Label(
            pb_note_fr,
            text=(
                "7. セット傾向（各項目の頻度）。保存先は team_tactics[\"playbook\"] です。\n"
                "速攻頻度（playbook）は試合全体のトランジション方針（team_strategy.transition_style）"
                "とは別です。現状、一部は試合シミュレーションに未反映です。\n"
                "※ アイソレーションは攻撃の起点、カッティングは今後の拡張対象です。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=440,
        ).pack(anchor="w")
        combos = self._playbook_editor_build_row_combos(wrap, pb)

        def _save() -> None:
            self._playbook_editor_save(combos, level_pairs, message_parent=w)

        def _reset() -> None:
            self._playbook_editor_reset_display(combos, level_pairs)

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x", pady=(12, 0))
        ttk.Button(btn, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn, text="標準に戻す", style="Menu.TButton", command=_reset).pack(side="left", padx=4)
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

    def _open_tactics_roles_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        tactics = get_safe_team_tactics(self.team)
        roles = dict(tactics.get("roles") or {})
        roster = list(self._safe_get(self.team, "players", []) or [])
        roster_sorted = sorted(
            roster,
            key=lambda p: (str(getattr(p, "position", "SF")), -int(getattr(p, "ovr", 0))),
        )
        main_pairs = list(MAIN_ROLE_COMBO_OPTIONS)
        inv_pairs = [("high", "高い"), ("standard", "標準"), ("low", "低い")]
        shot_pairs = [("aggressive", "積極的"), ("standard", "標準"), ("passive", "控えめ")]
        clutch_pairs_r = [("go_to", "クラッチで任せる"), ("standard", "標準"), ("limited", "終盤は控えめ")]
        pm_pairs = [("primary", "主担当"), ("secondary", "補助"), ("minimal", "ほぼ任せない")]
        def_pairs = [("stopper", "相手主力担当"), ("standard", "標準"), ("light", "負担軽め")]

        w = tk.Toplevel(parent)
        w.title("ローテーション：3. 個別役割（手動）")
        w.geometry("720x580")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        roles_note_fr = ttk.Frame(wrap, style="Panel.TFrame")
        roles_note_fr.pack(fill="x", pady=(0, 8))
        ttk.Label(
            roles_note_fr,
            text="3. 個別役割（手動）",
            font=("Yu Gothic UI", 10, "bold"),
            foreground="#eef2f7",
        ).pack(anchor="w")
        ttk.Label(
            roles_note_fr,
            text=(
                "3. 個別役割（手動）を選手ごとに設定します。\n"
                "人事画面の「タグ:」は自動分類、ここは戦術用の手動設定です。\n"
                "試合では主に交代候補の弱い補正として使います。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=620,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            roles_note_fr,
            text="※ 人事の「タグ:」は自動分類、ここは手動の戦術役割です。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=620,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            roles_note_fr,
            text="※ 攻撃での優先度は「関与度」と「シュート」の2軸で保存します。",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=620,
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            roles_note_fr,
            text=(
                "保存先は team_tactics[\"roles\"]。起用の正本は「先発・6th・ベンチ」（Team）、"
                "人事の「タグ:」や自動タグの代替ではありません。"
            ),
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
            wraplength=620,
        ).pack(anchor="w", pady=(4, 0))
        body = ttk.Frame(wrap, style="Panel.TFrame")
        body.pack(fill="both", expand=True)
        lb_frame = ttk.Frame(body, style="Panel.TFrame", width=220)
        lb_frame.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(lb_frame, text="選手", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        lb = tk.Listbox(lb_frame, height=16, bg="#1d2129", fg="#eef2f7", selectmode="browse")
        lb.pack(fill="both", expand=True)
        players_list: List[Any] = []
        for p in roster_sorted:
            pid = getattr(p, "player_id", None)
            if pid is None:
                continue
            players_list.append(p)
            lb.insert("end", f"{getattr(p, 'name', '-')} ({getattr(p, 'position', '?')})")

        right = ttk.Frame(body, style="Panel.TFrame")
        right.pack(side="left", fill="both", expand=True)

        def _mk_combo(parent_f: ttk.Frame, label: str, pairs: List[Tuple[str, str]], cur: str) -> ttk.Combobox:
            r = ttk.Frame(parent_f, style="Panel.TFrame")
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=label, width=34).pack(side="left")
            cb = ttk.Combobox(r, state="readonly", width=22)
            vals = [b for _, b in pairs]
            cb["values"] = vals
            ints = [a for a, _ in pairs]
            cb.set(vals[ints.index(cur)] if cur in ints else vals[0])
            cb.pack(side="left", padx=4)
            return cb

        editors: Dict[str, ttk.Combobox] = {}
        editors["main_role"] = _mk_combo(right, "メイン役割（手動・参考）", main_pairs, "none")
        editors["offense_involvement"] = _mk_combo(right, "攻撃での優先度：関与度", inv_pairs, "standard")
        editors["shot_priority"] = _mk_combo(right, "攻撃での優先度：シュート", shot_pairs, "standard")
        editors["clutch_priority"] = _mk_combo(right, "終盤優先度", clutch_pairs_r, "standard")
        editors["playmaking_role"] = _mk_combo(right, "ボール保持（プレーメイク）", pm_pairs, "secondary")
        editors["defense_assignment"] = _mk_combo(right, "守備負担", def_pairs, "standard")

        role_defaults = {
            "main_role": "none",
            "offense_involvement": "standard",
            "shot_priority": "standard",
            "clutch_priority": "standard",
            "playmaking_role": "secondary",
            "defense_assignment": "standard",
        }

        def _load_player_row(idx: int) -> None:
            if idx < 0 or idx >= len(players_list):
                return
            p = players_list[idx]
            pid = int(getattr(p, "player_id", 0))
            row = roles.get(str(pid)) or {}
            pairs_for = {
                "main_role": main_pairs,
                "offense_involvement": inv_pairs,
                "shot_priority": shot_pairs,
                "clutch_priority": clutch_pairs_r,
                "playmaking_role": pm_pairs,
                "defense_assignment": def_pairs,
            }
            for ek, cb in editors.items():
                cur = str(row.get(ek, role_defaults[ek]))
                if ek == "main_role" and cur not in {a for a, _ in main_pairs}:
                    cur = "none"
                pairs = pairs_for[ek]
                vals = [b for _, b in pairs]
                ints = [a for a, _ in pairs]
                cb.set(vals[ints.index(cur)] if cur in ints else vals[0])

        def _read_combo(cb: ttk.Combobox, pairs: List[Tuple[str, str]]) -> str:
            d = cb.get()
            for a, b in pairs:
                if b == d:
                    return a
            return pairs[0][0]

        def _save_current_to_memory(idx: int) -> None:
            if idx < 0 or idx >= len(players_list):
                return
            p = players_list[idx]
            pid = int(getattr(p, "player_id", 0))
            roles[str(pid)] = {
                "main_role": _read_combo(editors["main_role"], main_pairs),
                "offense_involvement": _read_combo(editors["offense_involvement"], inv_pairs),
                "shot_priority": _read_combo(editors["shot_priority"], shot_pairs),
                "clutch_priority": _read_combo(editors["clutch_priority"], clutch_pairs_r),
                "playmaking_role": _read_combo(editors["playmaking_role"], pm_pairs),
                "defense_assignment": _read_combo(editors["defense_assignment"], def_pairs),
            }

        last_sel: List[int] = [-1]

        def _on_select(_evt: Any = None) -> None:
            sel = lb.curselection()
            if not sel:
                return
            if last_sel[0] >= 0:
                _save_current_to_memory(last_sel[0])
            idx = int(sel[0])
            last_sel[0] = idx
            _load_player_row(idx)

        lb.bind("<<ListboxSelect>>", _on_select)

        if players_list:
            lb.selection_set(0)
            last_sel[0] = 0
            _load_player_row(0)

        def _save() -> None:
            sel = lb.curselection()
            if sel:
                _save_current_to_memory(int(sel[0]))
            raw = dict(get_safe_team_tactics(self.team))
            raw["roles"] = dict(roles)
            self._tactics_commit_payload(raw)
            messagebox.showinfo("保存", "3. 個別役割（roles）を保存しました。", parent=w)

        def _reset_player() -> None:
            sel = lb.curselection()
            if not sel:
                return
            idx = int(sel[0])
            p = players_list[idx]
            pid = int(getattr(p, "player_id", 0))
            roles.pop(str(pid), None)
            _load_player_row(idx)

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x", pady=(8, 0))
        ttk.Button(btn, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn, text="この選手を標準に戻す", style="Menu.TButton", command=_reset_player).pack(
            side="left", padx=4
        )
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

    def _development_window_embed_top_panels_with_scroll(
        self, parent: tk.Misc, *, canvas_height_px: int
    ) -> Tuple[ttk.Frame, ttk.Frame]:
        """育成影響要因・スペシャル練習など上段3パネルが縦に長いとき、本表を潰さないよう縦スクロールで包む。"""
        host = ttk.Frame(parent, style="Root.TFrame")
        bar = ttk.Frame(host, style="Root.TFrame")
        bar.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            bar,
            height=int(canvas_height_px),
            bg="#15171c",
            highlightthickness=0,
            borderwidth=0,
        )
        vsb = ttk.Scrollbar(bar, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        inner = ttk.Frame(canvas, style="Root.TFrame")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event: Any = None) -> None:
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        def _on_canvas_configure(event: Any) -> None:
            try:
                canvas.itemconfigure(win_id, width=event.width)
            except tk.TclError:
                pass

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _wheel(event: Any) -> str:
            if getattr(event, "delta", 0):
                canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        canvas.bind("<MouseWheel>", _wheel)
        inner.bind("<MouseWheel>", _wheel)
        canvas.bind("<Enter>", lambda _e: canvas.focus_set())
        canvas.bind("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))
        inner.bind("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        inner.bind("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return host, inner

    def open_development_window(self) -> None:
        """強化・育成の閲覧ウィンドウ。最下部ボタンからチーム練習・個別練習を変更可能。"""
        existing = getattr(self, "_development_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_development_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"強化・育成状況 - {self._team_name()}")
        window.geometry("1080x700")
        window.minsize(920, 600)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        # 下の変更ボタン行を常に表示するため、先に bottom を side=bottom で確保し、
        # 上段〜一覧は dev_center 内だけで expand させる（pack 順だけの不具合で下部が画面外に落ちるのを防ぐ）
        dev_center = ttk.Frame(outer, style="Root.TFrame")

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        # 直近変更は長い補足ラベルより先に pack する（補足の折返しでログ行が画面外に落ちないようにする）
        self.development_training_log_summary_var = tk.StringVar(value="")
        self._development_log_frame = tk.Frame(bottom, bg="#1d2129")
        self._development_log_frame.pack(fill="x", anchor="w", pady=(0, 8))

        self.development_hint_intro_var = tk.StringVar(value="")
        tk.Label(
            bottom,
            textvariable=self.development_hint_intro_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=2,
            wraplength=980,
        ).pack(fill="x", anchor="w", pady=(0, 4))

        action_row = ttk.Frame(bottom, style="Panel.TFrame", padding=(0, 8, 0, 0))
        action_row.pack(fill="x")
        ttk.Button(
            action_row,
            text="チーム練習を変更",
            style="Menu.TButton",
            command=self._open_team_training_editor_window,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            action_row,
            text="個別練習を変更",
            style="Menu.TButton",
            command=self._open_player_training_editor_window,
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_development_window,
        ).pack(anchor="e", pady=(8, 0))

        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        dev_center.pack(side="top", fill="both", expand=True)

        header = ttk.Frame(dev_center, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.development_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.development_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        purpose = ttk.Frame(dev_center, style="Panel.TFrame", padding=(12, 8))
        purpose.pack(fill="x", pady=(0, 10))
        ttk.Label(
            purpose,
            text=(
                "【強化メニュー】育成方針（チーム練習）・個別練習・スペシャル練習の解放、"
                "育成に効く施設のLv、選手ごとの見立てをまとめて確認します。"
                "上段3パネルとロスター表は閲覧のみです。"
                "育成方針・個別練習の変更は、ウィンドウ最下部の「直近変更」の下にある"
                "「チーム練習を変更」「個別練習を変更」から行えます。"
                "メイン画面でチーム未接続のときは変更ボタンは使えません。"
            ),
            wraplength=1020,
            font=("Yu Gothic UI", 10),
            justify="left",
        ).pack(anchor="w")

        top_scroll_host, top_outer = self._development_window_embed_top_panels_with_scroll(
            dev_center, canvas_height_px=240
        )
        top_scroll_host.pack(fill="x", pady=(0, 10))

        top = ttk.Frame(top_outer, style="Root.TFrame")
        top.pack(fill="both", expand=True)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        top.columnconfigure(2, weight=1)

        self.development_summary_panel = self._create_panel(top, "育成サマリー")
        self.development_summary_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.development_effect_panel = self._create_panel(top, "育成影響要因")
        self.development_effect_panel.grid(row=0, column=1, sticky="nsew", padx=8)
        self.development_special_panel = self._create_panel(top, "スペシャル練習解放状況")
        self.development_special_panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        self.development_summary_lines = self._make_line_vars(self.development_summary_panel, 6)
        self.development_effect_lines = self._make_line_vars(self.development_effect_panel, 4)
        effect_content = self._resolve_content_parent(self.development_effect_panel)
        ttk.Button(
            effect_content,
            text="育成影響の詳細",
            style="Menu.TButton",
            command=self._open_development_effect_detail_window,
        ).pack(anchor="w", pady=(6, 0))
        self.development_special_lines = self._make_line_vars(self.development_special_panel, 4)
        special_content = self._resolve_content_parent(self.development_special_panel)
        ttk.Button(
            special_content,
            text="スペシャル練習の詳細",
            style="Menu.TButton",
            command=self._open_development_special_detail_window,
        ).pack(anchor="w", pady=(6, 0))

        table_wrap = ttk.Frame(dev_center, style="Panel.TFrame", padding=10)
        table_wrap.pack(fill="both", expand=True)
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(1, weight=1)

        ttk.Label(
            table_wrap,
            text="ロスター別の育成一覧（POT・育成指標・年齢帯・個別練習・育成方針・見立て）※上段は要約＋詳細ボタン。縦スクロールで上段全体を表示",
            style="TopBar.TLabel",
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        columns = (
            "name",
            "pos",
            "age",
            "ovr",
            "pot",
            "dev",
            "games",
            "stage",
            "training_drill",
            "training_focus",
            "outlook",
        )
        self.development_tree = ttk.Treeview(
            table_wrap,
            columns=columns,
            show="headings",
            height=12,
        )
        headings = {
            "name": "選手名",
            "pos": "POS",
            "age": "年齢",
            "ovr": "OVR",
            "pot": "POT",
            "dev": "育成値",
            "games": "試合数",
            "stage": "年齢帯",
            "training_drill": "個別練習",
            "training_focus": "育成方針",
            "outlook": "育成見立て",
        }
        # L-4: 列幅は指示レンジに寄せ、POS/年齢など短い列を詰めて左寄せの主要列を確保。見立ては右端・横スクロールで追う想定。
        widths = {
            "name": 170,
            "pos": 50,
            "age": 50,
            "ovr": 56,
            "pot": 50,
            "dev": 70,
            "games": 62,
            "stage": 72,
            "training_drill": 88,
            "training_focus": 84,
            "outlook": 252,
        }
        for key in columns:
            self.development_tree.heading(key, text=headings[key])
            anchor = "w" if key in ("name", "outlook") else "center"
            self.development_tree.column(key, width=widths[key], anchor=anchor, stretch=(key in ("name", "outlook")))

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.development_tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.development_tree.xview)
        self.development_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.development_tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        self._development_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_development_window)
        self.development_hint_intro_var.set(
            "補足: 数値はセーブ済みの選手データに依存します。列が足りない項目は今後の拡張で表示される場合があります。"
        )
        self._refresh_development_window()
        try:
            window.update_idletasks()
        except tk.TclError:
            pass

    def _on_close_development_window(self) -> None:
        try:
            sd = getattr(self, "_development_special_detail_window", None)
            if sd is not None and sd.winfo_exists():
                sd.destroy()
        except Exception:
            pass
        finally:
            self._development_special_detail_window = None
            self._development_special_detail_text = None
        try:
            ed = getattr(self, "_development_effect_detail_window", None)
            if ed is not None and ed.winfo_exists():
                ed.destroy()
        except Exception:
            pass
        finally:
            self._development_effect_detail_window = None
            self._development_effect_detail_text = None
        try:
            ld = getattr(self, "_development_training_log_detail_window", None)
            if ld is not None and ld.winfo_exists():
                ld.destroy()
        except Exception:
            pass
        finally:
            self._development_training_log_detail_window = None
            self._development_training_log_detail_text = None
        window = getattr(self, "_development_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._development_window = None

    def _build_development_special_panel_summary_lines(self, team: Any) -> List[str]:
        """強化メニュー本体のスペシャル練習パネル用の短い要約（詳細は別窓）。"""
        if team is None:
            coach = "balanced"
            items: List[tuple] = []
        else:
            coach = str(getattr(team, "coach_style", "balanced") or "balanced")
            items = self._build_special_training_catalog_items(team, coach_override=coach)
        unlocked = [f"{c}:{n}" for c, n, ok, _ in items if ok]
        joined = " / ".join(unlocked) if unlocked else ("なし" if team is not None else "チーム未接続")
        if len(joined) > 70:
            joined = joined[:67] + "…"
        return [
            f"現在HC：{self._coach_style_label(coach) if team is not None else '（チーム未接続）'}",
            f"解放数：{len(unlocked)}/{len(items) if items else 0}",
            f"解放中：{joined}",
            "詳細は下の「スペシャル練習の詳細」から確認できます。",
        ]

    def _on_close_development_special_detail_window(self) -> None:
        w = getattr(self, "_development_special_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._development_special_detail_window = None
            self._development_special_detail_text = None

    def _refresh_development_special_detail_body(self) -> None:
        tw = getattr(self, "_development_special_detail_text", None)
        if tw is None:
            return
        lines = self._build_current_special_training_lines(self.team)
        body = "\n".join(lines)
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_development_special_detail_window(self) -> None:
        """スペシャル練習解放の全文（閲覧専用）。判定は _build_current_special_training_lines に委譲。"""
        parent = getattr(self, "_development_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_development_special_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_development_special_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("スペシャル練習の詳細")
        w.geometry("720x560")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="スペシャル練習の解放状況（閲覧のみ・変更はチーム練習／HC／施設投資などから行います）",
            style="SectionTitle.TLabel",
            wraplength=680,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._development_special_detail_window = w
        self._development_special_detail_text = tw
        self._refresh_development_special_detail_body()
        tw.configure(state="disabled")

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(btn_row, text="閉じる", style="Menu.TButton", command=self._on_close_development_special_detail_window).pack(
            side="right"
        )

        w.protocol("WM_DELETE_WINDOW", self._on_close_development_special_detail_window)

    def _on_close_development_effect_detail_window(self) -> None:
        w = getattr(self, "_development_effect_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._development_effect_detail_window = None
            self._development_effect_detail_text = None

    def _refresh_development_effect_detail_body(self) -> None:
        tw = getattr(self, "_development_effect_detail_text", None)
        if tw is None:
            return
        lines = self._build_development_effect_detail_lines(self.team)
        body = "\n".join(lines)
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_development_effect_detail_window(self) -> None:
        """育成影響要因・施設効果の全文（閲覧専用）。本文は _build_development_effect_detail_lines に委譲。"""
        parent = getattr(self, "_development_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_development_effect_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_development_effect_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("育成影響の詳細")
        w.geometry("720x560")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="育成影響要因・施設効果（閲覧のみ・施設やHCの変更は経営メニュー等から行います）",
            style="SectionTitle.TLabel",
            wraplength=680,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=1, column=0, sticky="nsew")
        self._development_effect_detail_window = w
        self._development_effect_detail_text = tw
        self._refresh_development_effect_detail_body()
        tw.configure(state="disabled")

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_development_effect_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_development_effect_detail_window)

    def _on_close_development_training_log_detail_window(self) -> None:
        w = getattr(self, "_development_training_log_detail_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._development_training_log_detail_window = None
            self._development_training_log_detail_text = None

    def _refresh_development_training_log_detail_body(self) -> None:
        tw = getattr(self, "_development_training_log_detail_text", None)
        if tw is None:
            return
        body = self._build_development_training_log_detail_body_text(getattr(self, "team", None))
        try:
            tw.configure(state="normal")
            tw.delete("1.0", tk.END)
            tw.insert("1.0", body)
            tw.configure(state="disabled")
        except tk.TclError:
            pass

    def _open_development_training_log_detail_window(self) -> None:
        """チーム練習・個別練習の変更履歴（閲覧専用）。本文は Team の既存リスト表示のみ。"""
        parent = getattr(self, "_development_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = self.root
        except Exception:
            parent = self.root

        existing = getattr(self, "_development_training_log_detail_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_development_training_log_detail_body()
                return
        except Exception:
            pass

        w = tk.Toplevel(parent)
        w.title("直近変更ログ")
        w.geometry("720x520")
        w.minsize(520, 360)
        w.configure(bg="#15171c")
        try:
            w.transient(parent)
        except Exception:
            pass

        outer = ttk.Frame(w, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="直近変更ログ", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            outer,
            text="チーム練習・個別練習の最近の変更履歴です。（閲覧のみ）",
            wraplength=680,
            font=("Yu Gothic UI", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        tw = scrolledtext.ScrolledText(
            outer,
            height=22,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        tw.grid(row=2, column=0, sticky="nsew")
        self._development_training_log_detail_window = w
        self._development_training_log_detail_text = tw
        self._refresh_development_training_log_detail_body()
        tw.configure(state="disabled")

        btn_row = ttk.Frame(outer, style="Panel.TFrame", padding=(0, 8, 0, 0))
        btn_row.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            btn_row,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_development_training_log_detail_window,
        ).pack(side="right")

        w.protocol("WM_DELETE_WINDOW", self._on_close_development_training_log_detail_window)

    def _development_tree_drill_label(self, player: Any) -> str:
        k = str(self._safe_get(player, "training_drill", "balanced") or "balanced")
        return self._DEV_ROSTER_DRILL_LABEL_JA.get(k, "バランス")

    def _development_tree_focus_label(self, player: Any) -> str:
        k = str(self._safe_get(player, "training_focus", "balanced") or "balanced")
        return self._DEV_ROSTER_FOCUS_LABEL_JA.get(k, "バランス")

    def _refresh_development_window(self) -> None:
        if getattr(self, "development_header_var", None) is None:
            return

        players = list(self._safe_get(self.team, "players", []) or [])
        players_sorted = sorted(
            players,
            key=lambda p: (
                -self._potential_sort_value(self._safe_get(p, "potential", 0)),
                -self._safe_float(self._safe_get(p, "development", 0)),
                -self._safe_int(self._safe_get(p, "ovr", 0)),
                str(self._safe_get(p, "name", "")),
            ),
        )

        strategy_key = self._safe_get(self.team, "strategy", None)
        coach_key = self._safe_get(self.team, "coach_style", None)
        strategy_text = self.STRATEGY_LABELS.get(str(strategy_key), str(strategy_key or "-"))
        coach_text = self.COACH_STYLE_LABELS.get(str(coach_key), str(coach_key or "-"))

        top_prospect = players_sorted[0] if players_sorted else None
        top_name = self._safe_get(top_prospect, "name", "-") if top_prospect is not None else "-"
        top_pot = self._safe_get(top_prospect, "potential", "-") if top_prospect is not None else "-"

        young_count = sum(1 for p in players_sorted if self._safe_int(self._safe_get(p, "age", 0)) <= 23)
        prime_count = sum(1 for p in players_sorted if 24 <= self._safe_int(self._safe_get(p, "age", 0)) <= 31)
        veteran_count = sum(1 for p in players_sorted if self._safe_int(self._safe_get(p, "age", 0)) >= 32)
        avg_dev = 0.0
        if players_sorted:
            avg_dev = sum(self._safe_float(self._safe_get(p, "development", 0)) for p in players_sorted) / len(players_sorted)

        team_tf_key = str(self._safe_get(self.team, "team_training_focus", "balanced") or "balanced")
        team_tf_label = self._get_team_training_label(team_tf_key)

        if self.team is None:
            self.development_header_var.set(
                "（チーム未接続）強化・育成状況 — 下記は参照用プレースホルダです"
            )
        else:
            self.development_header_var.set(
                f"{self._team_name()} 強化・育成状況    育成有望株: {top_name} (POT {top_pot})"
            )

        summary_lines = [
            f"ロスター人数: {len(players_sorted)}",
            f"育成方針（チーム練習）: {team_tf_label}",
            f"若手(23歳以下): {young_count}",
            f"全盛期(24-31歳): {prime_count}",
            f"ベテラン(32歳以上): {veteran_count}",
            f"平均育成値(development): {avg_dev:.1f}",
        ]
        for var, line in zip(self.development_summary_lines, summary_lines):
            var.set(line)

        effect_summary = self._build_development_effect_panel_summary_lines(self.team)
        for i, var in enumerate(self.development_effect_lines):
            var.set(effect_summary[i] if i < len(effect_summary) else "")

        special_lines = self._build_development_special_panel_summary_lines(self.team)
        for i, var in enumerate(self.development_special_lines):
            var.set(special_lines[i] if i < len(special_lines) else "")
        try:
            if getattr(self, "_development_special_detail_window", None) is not None:
                dw = self._development_special_detail_window
                if dw is not None and dw.winfo_exists():
                    self._refresh_development_special_detail_body()
        except Exception:
            pass
        try:
            if getattr(self, "_development_effect_detail_window", None) is not None:
                ew = self._development_effect_detail_window
                if ew is not None and ew.winfo_exists():
                    self._refresh_development_effect_detail_body()
        except Exception:
            pass

        tree = getattr(self, "development_tree", None)
        if tree is not None:
            for item in tree.get_children():
                tree.delete(item)
            if not players_sorted:
                if self.team is None:
                    pname = "（チーム未接続）"
                    outlook = "メイン画面でチームに接続するとロスターが表示されます。"
                else:
                    pname = "（ロスターに選手がいません）"
                    outlook = "選手が所属すると自動で行が追加されます。"
                tree.insert(
                    "",
                    "end",
                    values=(
                        pname,
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        outlook,
                    ),
                )
            else:
                for player in players_sorted:
                    age = self._safe_int(self._safe_get(player, "age", 0))
                    stage = self._get_age_stage_text(age)
                    outlook = self._build_player_development_outlook(player)
                    tree.insert(
                        "",
                        "end",
                        values=(
                            str(self._safe_get(player, "name", "-")),
                            str(self._safe_get(player, "position", "-")),
                            str(self._safe_get(player, "age", "-")),
                            str(self._safe_get(player, "ovr", "-")),
                            str(self._safe_get(player, "potential", "-")),
                            str(self._safe_get(player, "development", "-")),
                            str(self._safe_get(player, "games_played", 0)),
                            stage,
                            self._development_tree_drill_label(player),
                            self._development_tree_focus_label(player),
                            outlook,
                        ),
                    )

        self.development_hint_intro_var.set(
            "上段は要約＋各「詳細」ボタン、下表は選手別の育成状況です。"
            "練習の変更は「直近変更」の下のボタンから行えます。"
        )
        self._refresh_development_training_log_widgets()
        try:
            if getattr(self, "_development_training_log_detail_window", None) is not None:
                lw = self._development_training_log_detail_window
                if lw is not None and lw.winfo_exists():
                    self._refresh_development_training_log_detail_body()
        except Exception:
            pass

    def _build_development_coach_note(self, coach_key: Any) -> str:
        key = str(coach_key or "")
        if key == "development":
            return "HCスタイル補足: 育成型なので若手成長に追い風です"
        if key == "offense":
            return "HCスタイル補足: オフェンス志向で得点型選手の伸びを見極めたいです"
        if key == "defense":
            return "HCスタイル補足: 守備型でロールプレイヤー育成を見極めたいです"
        return "HCスタイル補足: バランス型で全体を均等に伸ばす方針です"

    def _build_development_strategy_note(self, strategy_key: Any) -> str:
        key = str(strategy_key or "")
        if key == "run_and_gun":
            return "戦術補足: テンポ重視なのでガードやウイングの育成相性を確認しましょう"
        if key == "three_point":
            return "戦術補足: 外角志向なのでシューター育成の伸びが重要です"
        if key == "inside":
            return "戦術補足: インサイド志向なのでPF/Cの成長を重視したいです"
        if key == "defense":
            return "戦術補足: 守備重視なのでフィジカルと守備役割の成長を確認しましょう"
        return "戦術補足: バランス型で全ポジションを横断的に育てやすいです"

    def _build_development_facility_block_lines(self, team: Any) -> List[str]:
        """強化メニュー用。施設投資ロジックは触らず、Lvと効き方の目安のみ表示する。"""
        if team is None:
            return [
                "■ 育成・スペシャル練習へ効く施設（現在Lv）",
                "トレーニング施設Lv: —（チーム未接続）",
                "メディカル施設Lv: —",
                "フロントLv: —",
                "※アリーナは主に集客・収支（育成計算とは直接は結び付けていません）。",
                "■ HC・戦術・年齢・出場",
            ]
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        fo = int(getattr(team, "front_office_level", 1) or 1)
        return [
            "■ 育成・スペシャル練習へ効く施設（現在Lv）",
            (
                f"トレーニング施設Lv{tf}："
                "個別練習の追加成長の発生率の目安に関係します。"
                "一部のスペシャル練習の解放条件にも使われます。"
            ),
            (
                f"メディカル施設Lv{med}："
                "フィジカル系のスペシャル練習（筋力強化など）の解放条件に関係します。"
            ),
            (
                f"フロントLv{fo}："
                "IQ・映像分析系の個別練習（映像分析など）の解放条件に関係します。"
            ),
            "※アリーナは主に集客・収支（育成計算とは直接は結び付けていません）。",
            "■ HC・戦術・年齢・出場",
        ]

    def _build_development_effect_detail_lines(self, team: Any) -> List[str]:
        """強化メニュー別窓用。従来本体パネルに出していた施設＋HC/戦術/補足の全文（ロジック追加なし）。"""
        facility_lines = self._build_development_facility_block_lines(team)
        strategy_key = self._safe_get(team, "strategy", None)
        coach_key = self._safe_get(team, "coach_style", None)
        strategy_text = self.STRATEGY_LABELS.get(str(strategy_key), str(strategy_key or "-"))
        coach_text = self.COACH_STYLE_LABELS.get(str(coach_key), str(coach_key or "-"))
        other_effect_lines = [
            f"HCスタイル: {coach_text}",
            f"戦術: {strategy_text}",
            self._build_development_coach_note(coach_key),
            self._build_development_strategy_note(strategy_key),
            "若手は伸びやすく、32歳以上は衰退しやすい傾向です",
            "試合出場数も育成量に影響します",
        ]
        return facility_lines + other_effect_lines

    def _build_development_effect_panel_summary_lines(self, team: Any) -> List[str]:
        """強化メニュー本体の育成影響要因パネル用の短い要約（詳細は別窓）。"""
        if team is None:
            return [
                "施設：トレーニングLv— / メディカルLv— / フロントLv—（チーム未接続）",
                "方針：HC— / 戦術—",
                "補足：年齢・出場機会・個別練習が成長に影響します。",
                "詳細は下の「育成影響の詳細」から確認できます。",
            ]
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        fo = int(getattr(team, "front_office_level", 1) or 1)
        strategy_key = self._safe_get(team, "strategy", None)
        coach_key = self._safe_get(team, "coach_style", None)
        strategy_text = self.STRATEGY_LABELS.get(str(strategy_key), str(strategy_key or "-"))
        coach_text = self.COACH_STYLE_LABELS.get(str(coach_key), str(coach_key or "-"))
        return [
            f"施設：トレーニングLv{tf} / メディカルLv{med} / フロントLv{fo}",
            f"方針：HC＝{coach_text} / 戦術＝{strategy_text}",
            "補足：年齢・出場機会・個別練習が成長に影響します。",
            "詳細は下の「育成影響の詳細」から確認できます。",
        ]

    def _get_age_stage_text(self, age: int) -> str:
        if age <= 23:
            return "若手"
        if age <= 31:
            return "全盛期"
        return "ベテラン"

    def _build_player_development_outlook(self, player: Any) -> str:
        age = self._safe_int(self._safe_get(player, "age", 0))
        ovr = self._safe_int(self._safe_get(player, "ovr", 0))
        pot = self._potential_sort_value(self._safe_get(player, "potential", 0))
        dev = self._safe_float(self._safe_get(player, "development", 0))
        games = self._safe_int(self._safe_get(player, "games_played", 0))

        if age <= 23 and pot >= ovr + 5:
            return "将来性大。優先育成候補"
        if age <= 23:
            return "若手。出場機会で成長期待"
        if 24 <= age <= 31 and dev >= 60:
            return "主力伸長期。即戦力運用向き"
        if 24 <= age <= 31:
            return "全盛期。安定運用を優先"
        if age >= 32 and games >= 20:
            return "ベテラン。負荷管理に注意"
        return "育成状況を継続確認"

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _potential_sort_value(self, value: Any) -> int:
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            try:
                return int(value)
            except Exception:
                return 0

        text = str(value).strip().upper()
        if not text:
            return 0

        grade_map = {
            "SS": 95,
            "S": 90,
            "A": 80,
            "B": 70,
            "C": 60,
            "D": 50,
            "E": 40,
            "F": 30,
        }
        if text in grade_map:
            return grade_map[text]

        try:
            return int(float(text))
        except Exception:
            return 0

    def _get_starting_five_players(self) -> List[Any]:
        """gm_dashboard_text と同一の先発判定（人事ロスターと GM 表示の整合用）。"""
        if self.team is None:
            return []
        try:
            return [p for p in (get_current_starting_five(self.team) or []) if p is not None]
        except Exception:
            return []

    def _get_sixth_man_player(self) -> Any:
        if self.team is None:
            return None
        try:
            return get_current_sixth_man(self.team)
        except Exception:
            return None

    def _get_bench_order_players(self) -> List[Any]:
        if self.team is None:
            return []
        try:
            return [p for p in (get_current_bench_order(self.team) or []) if p is not None]
        except Exception:
            return []

    def _format_player_brief(self, player: Any) -> str:
        if player is None:
            return "-"
        name = str(self._safe_get(player, "name", "-"))
        pos = str(self._safe_get(player, "position", "-"))
        ovr = self._safe_get(player, "ovr", "-")
        return f"{name} {pos} OVR:{ovr}"

    def _default_information_division(self) -> int:
        lv = self._safe_int(self._safe_get(self.team, "league_level", 1))
        if lv < 1:
            lv = 1
        if lv > 3:
            lv = 3
        return lv

    def _information_division_level(self) -> int:
        var = getattr(self, "information_division_var", None)
        v = str(var.get() if var is not None else "D1")
        try:
            if v.startswith("D") and v[1:].isdigit():
                return max(1, min(3, int(v[1:])))
        except (TypeError, ValueError):
            pass
        return self._default_information_division()

    def _information_player_stat_key(self) -> str:
        lab = ""
        try:
            var = getattr(self, "information_player_stat_var", None)
            if var is not None:
                lab = str(var.get())
        except Exception:
            pass
        m = getattr(self, "_information_stat_label_to_key", None)
        if isinstance(m, dict) and lab in m:
            return str(m[lab])
        return "points"

    def open_information_window(self) -> None:
        """Open a safe read-only season information subwindow (docs/INFORMATION_MENU_SPEC_V1.md)."""
        existing = getattr(self, "_information_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_information_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"情報 ({self._team_name()})")
        window.geometry("1180x820")
        window.minsize(980, 660)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="順位表・個人スタッツ・チーム概要など、集計データを確認する画面です。",
            bg="#15171c",
            fg="#a8b4c8",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=1120,
        ).pack(fill="x", pady=(0, 8))

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 10))

        self.information_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.information_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        div_default = f"D{self._default_information_division()}"
        self.information_division_var = tk.StringVar(value=div_default)

        stat_opts = player_stat_options()
        self._information_stat_label_to_key = {lab: key for lab, key in stat_opts}
        default_stat_label = next((lab for lab, key in stat_opts if key == "points"), stat_opts[0][0] if stat_opts else "")
        self.information_player_stat_var = tk.StringVar(value=default_stat_label)

        def _on_info_filter_change(_event: Any = None) -> None:
            self._refresh_information_window()

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True, pady=(0, 10))

        # --- 概要 ---
        tab_overview = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_overview, text="概要")
        tab_overview.columnconfigure(0, weight=1)
        tab_overview.columnconfigure(1, weight=1)
        tab_overview.rowconfigure(0, weight=0)
        tab_overview.rowconfigure(1, weight=1)
        tab_overview.rowconfigure(2, weight=0)

        self.info_team_profile_panel = self._create_panel(tab_overview, "チーム情報（閲覧）")
        self.info_team_profile_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        tprof_inner = self._resolve_content_parent(self.info_team_profile_panel)
        tk.Label(
            tprof_inner,
            text="クラブ属性の正本です（ホーム・愛称等）。左メニュー「クラブ案内」の同名タブは案内のみです。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=960,
            padx=2,
        ).pack(fill="x", pady=(0, 6))
        self._information_team_identity_text = scrolledtext.ScrolledText(
            tprof_inner,
            height=10,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self._information_team_identity_text.pack(fill="both", expand=False, pady=(0, 4))
        self._information_team_identity_text.configure(state="disabled")

        top_ov = ttk.Frame(tab_overview, style="Root.TFrame")
        top_ov.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        top_ov.columnconfigure(0, weight=1)
        top_ov.columnconfigure(1, weight=1)

        self.info_progress_panel = self._create_panel(top_ov, "シーズン進行")
        self.info_progress_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info_schedule_panel = self._create_panel(top_ov, "次ラウンド予定")
        self.info_schedule_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.info_comp_panel = self._create_panel(tab_overview, "大会進行状況")
        self.info_comp_panel.grid(row=2, column=0, columnspan=2, sticky="nsew")

        self.info_progress_lines = self._make_line_vars(self.info_progress_panel, 7)
        self.info_schedule_lines = self._make_line_vars(self.info_schedule_panel, 8)
        self.info_comp_lines = self._make_line_vars(self.info_comp_panel, 8)

        # --- 順位表 ---
        tab_stand = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_stand, text="順位表")
        st_tool = ttk.Frame(tab_stand, style="Root.TFrame")
        st_tool.pack(fill="x", pady=(0, 8))
        ttk.Label(st_tool, text="区分:", style="TopBar.TLabel").pack(side="left", padx=(0, 6))
        st_div = ttk.Combobox(
            st_tool,
            textvariable=self.information_division_var,
            values=("D1", "D2", "D3"),
            state="readonly",
            width=5,
        )
        st_div.pack(side="left")
        st_div.bind("<<ComboboxSelected>>", _on_info_filter_change)

        st_fr = ttk.Frame(tab_stand, style="Card.TFrame")
        st_fr.pack(fill="both", expand=True)
        cols_st = ("rk", "team", "w", "l", "pct", "pf", "pa", "diff", "mk")
        self._information_standings_tree = ttk.Treeview(
            st_fr,
            columns=cols_st,
            show="headings",
            height=16,
            selectmode="browse",
        )
        st_tree = self._information_standings_tree
        st_tree.heading("rk", text="順位")
        st_tree.heading("team", text="チーム")
        st_tree.heading("w", text="勝")
        st_tree.heading("l", text="敗")
        st_tree.heading("pct", text="勝率")
        st_tree.heading("pf", text="得点")
        st_tree.heading("pa", text="失点")
        st_tree.heading("diff", text="得失差")
        st_tree.heading("mk", text="")
        st_tree.column("rk", width=40, anchor="center")
        st_tree.column("team", width=200, anchor="w")
        st_tree.column("w", width=36, anchor="center")
        st_tree.column("l", width=36, anchor="center")
        st_tree.column("pct", width=52, anchor="e")
        st_tree.column("pf", width=52, anchor="e")
        st_tree.column("pa", width=52, anchor="e")
        st_tree.column("diff", width=56, anchor="e")
        st_tree.column("mk", width=40, anchor="center")
        st_vsb = ttk.Scrollbar(st_fr, orient="vertical", command=st_tree.yview)
        st_tree.configure(yscrollcommand=st_vsb.set)
        st_tree.pack(side="left", fill="both", expand=True)
        st_vsb.pack(side="right", fill="y")

        # --- 個人成績（順位表の次 / INFORMATION_MENU_SPEC_V1） ---
        tab_pl = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_pl, text="個人成績")
        pl_tool = ttk.Frame(tab_pl, style="Root.TFrame")
        pl_tool.pack(fill="x", pady=(0, 8))
        ttk.Label(pl_tool, text="区分:", style="TopBar.TLabel").pack(side="left", padx=(0, 6))
        pl_div = ttk.Combobox(
            pl_tool,
            textvariable=self.information_division_var,
            values=("D1", "D2", "D3"),
            state="readonly",
            width=5,
        )
        pl_div.pack(side="left", padx=(0, 14))
        pl_div.bind("<<ComboboxSelected>>", _on_info_filter_change)
        ttk.Label(pl_tool, text="項目:", style="TopBar.TLabel").pack(side="left", padx=(0, 6))
        pl_stat = ttk.Combobox(
            pl_tool,
            textvariable=self.information_player_stat_var,
            values=tuple(lab for lab, _k in stat_opts),
            state="readonly",
            width=14,
        )
        pl_stat.pack(side="left")
        pl_stat.bind("<<ComboboxSelected>>", _on_info_filter_change)

        pl_note = ttk.Frame(tab_pl, style="Root.TFrame")
        pl_note.pack(fill="x", pady=(0, 6))
        tk.Label(
            pl_note,
            text="※ 出場1試合以上の選手のみ表示します。表彰・各タイトルの規定試合数とは別です。",
            bg="#15171c",
            fg="#9aa3af",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=960,
        ).pack(fill="x", anchor="w")

        pl_fr = ttk.Frame(tab_pl, style="Card.TFrame")
        pl_fr.pack(fill="both", expand=True)
        cols_pl = ("rk", "name", "tm", "pos", "ovr", "avg", "tot", "gp")
        self._information_player_tree = ttk.Treeview(
            pl_fr,
            columns=cols_pl,
            show="headings",
            height=16,
            selectmode="browse",
        )
        pl_tree = self._information_player_tree
        pl_tree.heading("rk", text="順位")
        pl_tree.heading("name", text="選手")
        pl_tree.heading("tm", text="チーム")
        pl_tree.heading("pos", text="Pos")
        pl_tree.heading("ovr", text="OVR")
        pl_tree.heading("avg", text="平均")
        pl_tree.heading("tot", text="合計")
        pl_tree.heading("gp", text="試合")
        pl_tree.column("rk", width=40, anchor="center")
        pl_tree.column("name", width=160, anchor="w")
        pl_tree.column("tm", width=120, anchor="w")
        pl_tree.column("pos", width=40, anchor="center")
        pl_tree.column("ovr", width=44, anchor="center")
        pl_tree.column("avg", width=52, anchor="e")
        pl_tree.column("tot", width=52, anchor="e")
        pl_tree.column("gp", width=44, anchor="center")
        pl_vsb = ttk.Scrollbar(pl_fr, orient="vertical", command=pl_tree.yview)
        pl_tree.configure(yscrollcommand=pl_vsb.set)
        pl_tree.pack(side="left", fill="both", expand=True)
        pl_vsb.pack(side="right", fill="y")

        # --- チーム成績 ---
        tab_team = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_team, text="チーム成績")
        tm_tool = ttk.Frame(tab_team, style="Root.TFrame")
        tm_tool.pack(fill="x", pady=(0, 8))
        ttk.Label(tm_tool, text="区分:", style="TopBar.TLabel").pack(side="left", padx=(0, 6))
        tm_div = ttk.Combobox(
            tm_tool,
            textvariable=self.information_division_var,
            values=("D1", "D2", "D3"),
            state="readonly",
            width=5,
        )
        tm_div.pack(side="left")
        tm_div.bind("<<ComboboxSelected>>", _on_info_filter_change)

        tm_fr = ttk.Frame(tab_team, style="Card.TFrame")
        tm_fr.pack(fill="both", expand=True)
        cols_tm = ("rk", "team", "apf", "apa", "adif", "mk")
        self._information_team_tree = ttk.Treeview(
            tm_fr,
            columns=cols_tm,
            show="headings",
            height=16,
            selectmode="browse",
        )
        tm_tree = self._information_team_tree
        tm_tree.heading("rk", text="順位")
        tm_tree.heading("team", text="チーム")
        tm_tree.heading("apf", text="平均得点")
        tm_tree.heading("apa", text="平均失点")
        tm_tree.heading("adif", text="平均得失差")
        tm_tree.heading("mk", text="")
        tm_tree.column("rk", width=40, anchor="center")
        tm_tree.column("team", width=220, anchor="w")
        tm_tree.column("apf", width=72, anchor="e")
        tm_tree.column("apa", width=72, anchor="e")
        tm_tree.column("adif", width=80, anchor="e")
        tm_tree.column("mk", width=40, anchor="center")
        tm_vsb = ttk.Scrollbar(tm_fr, orient="vertical", command=tm_tree.yview)
        tm_tree.configure(yscrollcommand=tm_vsb.set)
        tm_tree.pack(side="left", fill="both", expand=True)
        tm_vsb.pack(side="right", fill="y")

        # --- リーグニュース ---
        tab_news = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_news, text="リーグニュース")
        self._information_news_text = scrolledtext.ScrolledText(
            tab_news,
            height=18,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._information_news_text.pack(fill="both", expand=True)
        self._information_news_text.configure(state="disabled")

        # --- 表彰 ---
        tab_aw = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_aw, text="表彰")
        aw_tool = ttk.Frame(tab_aw, style="Root.TFrame")
        aw_tool.pack(fill="x", pady=(0, 8))
        ttk.Label(aw_tool, text="区分:", style="TopBar.TLabel").pack(side="left", padx=(0, 6))
        aw_div = ttk.Combobox(
            aw_tool,
            textvariable=self.information_division_var,
            values=("D1", "D2", "D3"),
            state="readonly",
            width=5,
        )
        aw_div.pack(side="left")
        aw_div.bind("<<ComboboxSelected>>", _on_info_filter_change)

        self._information_awards_text = scrolledtext.ScrolledText(
            tab_aw,
            height=18,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._information_awards_text.pack(fill="both", expand=True)
        self._information_awards_text.configure(state="disabled")

        for tr in (self._information_standings_tree, self._information_team_tree):
            try:
                tr.tag_configure("user", background="#2f3542")
            except tk.TclError:
                pass

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(0, 0))

        self.information_hint_var = tk.StringVar(value="")
        tk.Label(
            bottom,
            textvariable=self.information_hint_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=2,
        ).pack(fill="x", anchor="w")

        bf = tk.Frame(bottom, bg="#1d2129")
        bf.pack(anchor="e", pady=(8, 0))
        self._jpn_text_button(bf, "閉じる", window.destroy, side="right")

        self._information_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_information_window)
        self._refresh_information_window()

    def _on_close_information_window(self) -> None:
        window = getattr(self, "_information_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._information_window = None

    def open_schedule_window(self) -> None:
        """読み取り専用の日程ウィンドウ（docs/SCHEDULE_MENU_SPEC_V1.md）。"""
        if self.team is None:
            messagebox.showwarning("日程", "チームが未接続です。", parent=self.root)
            return

        existing = getattr(self, "_schedule_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_schedule_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"日程 - {self._team_name()}")
        window.geometry("1020x720")
        window.minsize(920, 620)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="次戦の内容・今後と過去の試合一覧、大会の進行を確認する画面です。",
            bg="#15171c",
            fg="#a8b4c8",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=960,
        ).pack(fill="x", pady=(0, 8))

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))
        self.schedule_header_var = tk.StringVar(value="")
        ttk.Label(header, textvariable=self.schedule_header_var, style="TopBar.TLabel", anchor="w").pack(
            fill="x"
        )

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)

        tab_next = ttk.Frame(nb, style="Root.TFrame", padding=8)
        tab_up = ttk.Frame(nb, style="Root.TFrame", padding=8)
        tab_past = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_next, text="次戦詳細")
        nb.add(tab_up, text="今後の日程")
        nb.add(tab_past, text="過去結果")

        self._schedule_next_text = scrolledtext.ScrolledText(
            tab_next,
            height=18,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._schedule_next_text.pack(fill="both", expand=True)
        self._schedule_next_text.configure(state="disabled")

        filt_row = ttk.Frame(tab_up, style="Root.TFrame")
        filt_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filt_row, text="表示フィルタ:", style="TopBar.TLabel").pack(side="left", padx=(0, 8))
        self._schedule_filter_combo = ttk.Combobox(
            filt_row,
            state="readonly",
            width=18,
            values=("すべて", "日本リーグのみ"),
        )
        self._schedule_filter_combo.set("すべて")
        self._schedule_filter_combo.pack(side="left")
        self._schedule_filter_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_schedule_window())

        up_paned = ttk.Panedwindow(tab_up, orient=tk.VERTICAL)
        up_paned.pack(fill="both", expand=True)

        tree_fr = ttk.Frame(up_paned, style="Card.TFrame")
        det_fr = ttk.Frame(up_paned, style="Card.TFrame")
        up_paned.add(tree_fr, weight=3)
        up_paned.add(det_fr, weight=1)

        cols = ("until", "rnd", "mon", "cup", "ha", "opp")
        self._schedule_upcoming_tree = ttk.Treeview(
            tree_fr,
            columns=cols,
            show="headings",
            height=14,
            selectmode="browse",
        )
        self._schedule_upcoming_tree.heading("until", text="あと")
        self._schedule_upcoming_tree.heading("rnd", text="R")
        self._schedule_upcoming_tree.heading("mon", text="月目安")
        self._schedule_upcoming_tree.heading("cup", text="大会")
        self._schedule_upcoming_tree.heading("ha", text="H/A")
        self._schedule_upcoming_tree.heading("opp", text="対戦相手")
        self._schedule_upcoming_tree.column("until", width=44, anchor="center")
        self._schedule_upcoming_tree.column("rnd", width=44, anchor="center")
        self._schedule_upcoming_tree.column("mon", width=72, anchor="center")
        self._schedule_upcoming_tree.column("cup", width=120, anchor="w")
        self._schedule_upcoming_tree.column("ha", width=40, anchor="center")
        self._schedule_upcoming_tree.column("opp", width=220, anchor="w")
        vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=self._schedule_upcoming_tree.yview)
        self._schedule_upcoming_tree.configure(yscrollcommand=vsb.set)
        self._schedule_upcoming_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._schedule_upcoming_tree.bind("<<TreeviewSelect>>", self._on_schedule_upcoming_select)

        ttk.Label(det_fr, text="行の詳細", style="SectionTitle.TLabel").pack(anchor="w", padx=4, pady=(0, 4))
        self._schedule_upcoming_detail = scrolledtext.ScrolledText(
            det_fr,
            height=6,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self._schedule_upcoming_detail.pack(fill="both", expand=True)
        self._schedule_upcoming_detail.configure(state="disabled")

        past_paned = ttk.Panedwindow(tab_past, orient=tk.VERTICAL)
        past_paned.pack(fill="both", expand=True)
        pt_fr = ttk.Frame(past_paned, style="Card.TFrame")
        pd_fr = ttk.Frame(past_paned, style="Card.TFrame")
        past_paned.add(pt_fr, weight=3)
        past_paned.add(pd_fr, weight=1)

        pcols = ("no", "opp", "sc", "res", "ha", "rnd", "cup")
        self._schedule_past_tree = ttk.Treeview(
            pt_fr,
            columns=pcols,
            show="headings",
            height=14,
            selectmode="browse",
        )
        self._schedule_past_tree.heading("no", text="#")
        self._schedule_past_tree.heading("opp", text="対戦相手")
        self._schedule_past_tree.heading("sc", text="スコア")
        self._schedule_past_tree.heading("res", text="結果")
        self._schedule_past_tree.heading("ha", text="H/A")
        self._schedule_past_tree.heading("rnd", text="節・R")
        self._schedule_past_tree.heading("cup", text="大会")
        self._schedule_past_tree.column("no", width=36, anchor="center")
        self._schedule_past_tree.column("opp", width=150, anchor="w")
        self._schedule_past_tree.column("sc", width=72, anchor="center")
        self._schedule_past_tree.column("res", width=56, anchor="center")
        self._schedule_past_tree.column("ha", width=40, anchor="center")
        self._schedule_past_tree.column("rnd", width=56, anchor="center")
        self._schedule_past_tree.column("cup", width=110, anchor="w")
        pvsb = ttk.Scrollbar(pt_fr, orient="vertical", command=self._schedule_past_tree.yview)
        self._schedule_past_tree.configure(yscrollcommand=pvsb.set)
        self._schedule_past_tree.pack(side="left", fill="both", expand=True)
        pvsb.pack(side="right", fill="y")
        self._schedule_past_tree.bind("<<TreeviewSelect>>", self._on_schedule_past_select)

        ttk.Label(pd_fr, text="詳細・注記", style="SectionTitle.TLabel").pack(anchor="w", padx=4, pady=(0, 4))
        self._schedule_past_detail = scrolledtext.ScrolledText(
            pd_fr,
            height=6,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self._schedule_past_detail.pack(fill="both", expand=True)
        self._schedule_past_detail.configure(state="disabled")

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))
        tk.Label(
            bottom,
            text="読み取り専用です。一覧は主に日本リーグの SeasonEvent 由来です。「すべて」では全日本カップ・東アジアトップリーグ・代表ウィンドウ等を表示補完しています（行を選ぶと詳細に注記あり）。過去結果は上が新しい順。",
            bg="#1d2129",
            fg="#9aa3af",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x")
        bf = tk.Frame(bottom, bg="#1d2129")
        bf.pack(anchor="e", pady=(8, 0))
        self._jpn_text_button(bf, "閉じる", self._on_close_schedule_window, side="right")

        self._schedule_window = window
        self._schedule_upcoming_rows: List[Dict[str, Any]] = []
        self._schedule_past_rows: List[Dict[str, Any]] = []
        window.protocol("WM_DELETE_WINDOW", self._on_close_schedule_window)
        self._refresh_schedule_window()

    def _on_close_schedule_window(self) -> None:
        w = getattr(self, "_schedule_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        finally:
            self._schedule_window = None
            self._schedule_upcoming_rows = []
            self._schedule_past_rows = []

    def _on_schedule_upcoming_select(self, _event: Any = None) -> None:
        tree = getattr(self, "_schedule_upcoming_tree", None)
        det = getattr(self, "_schedule_upcoming_detail", None)
        if tree is None or det is None:
            return
        sel = tree.selection()
        if not sel:
            return
        tags = tree.item(sel[0], "tags")
        if not tags:
            return
        try:
            idx = int(tags[0])
        except (TypeError, ValueError):
            return
        rows = getattr(self, "_schedule_upcoming_rows", None) or []
        if idx < 0 or idx >= len(rows):
            return
        text = detail_text_for_upcoming_row(rows[idx])
        det.configure(state="normal")
        det.delete("1.0", tk.END)
        det.insert(tk.END, text)
        det.configure(state="disabled")

    def _on_schedule_past_select(self, _event: Any = None) -> None:
        tree = getattr(self, "_schedule_past_tree", None)
        det = getattr(self, "_schedule_past_detail", None)
        if tree is None or det is None:
            return
        sel = tree.selection()
        if not sel:
            return
        tags = tree.item(sel[0], "tags")
        if not tags:
            return
        try:
            idx = int(tags[0])
        except (TypeError, ValueError):
            return
        rows = getattr(self, "_schedule_past_rows", None) or []
        if idx < 0 or idx >= len(rows):
            return
        r = rows[idx]
        lines = [
            f"対戦相手: {r.get('opponent', '—')}",
            f"スコア: {r.get('score', '—')}  /  {r.get('result', '—')}",
            f"H/A: {r.get('ha_long', '—')} ({r.get('ha_short', '—')})",
            f"大会: {r.get('competition_display', '—')}",
            f"節・ラウンド: {r.get('round_label', '—')}",
            f"延長: {r.get('ot_label', '—')}",
            "",
            r.get("note", ""),
        ]
        text = "\n".join(lines)
        det.configure(state="normal")
        det.delete("1.0", tk.END)
        det.insert(tk.END, text)
        det.configure(state="disabled")

    def _refresh_schedule_window(self) -> None:
        if getattr(self, "_schedule_window", None) is None:
            return
        try:
            if not self._schedule_window.winfo_exists():
                return
        except Exception:
            return

        cr = self._safe_int(self._safe_get(self.season, "current_round", 0))
        tr = self._safe_int(self._safe_get(self.season, "total_rounds", 0))
        fin = bool(self._safe_get(self.season, "season_finished", False))
        hdr = getattr(self, "schedule_header_var", None)
        if hdr is not None:
            parts = [
                f"{self._team_name()} 日程",
                f"消化ラウンド {cr}/{tr}",
                "シーズン終了" if fin else "シーズン進行中",
            ]
            if not fin and self.season is not None and self.team is not None:
                nxt = cr + 1
                if nxt <= tr:
                    ng = count_user_games_in_sim_round(self.season, self.team, nxt)
                    parts.append(f"次の進行の自チーム試合: {ng}（1回でまとめてシミュ）")
            hdr.set("    ".join(parts))

        # 次戦詳細
        nt = getattr(self, "_schedule_next_text", None)
        if nt is not None:
            lines = next_round_schedule_lines(self.season, self.team)
            nt.configure(state="normal")
            nt.delete("1.0", tk.END)
            nt.insert(tk.END, "\n".join(lines))
            nt.configure(state="disabled")

        league_only = False
        combo = getattr(self, "_schedule_filter_combo", None)
        if combo is not None:
            try:
                league_only = combo.get() == "日本リーグのみ"
            except Exception:
                league_only = False

        rows = upcoming_rows_for_user_team(self.season, self.team, league_only=league_only)
        self._schedule_upcoming_rows = rows

        ut = getattr(self, "_schedule_upcoming_tree", None)
        if ut is not None:
            ut.delete(*ut.get_children())
            for i, row in enumerate(rows):
                ut.insert(
                    "",
                    "end",
                    iid=f"u{i}",
                    values=(
                        row.get("rounds_until", ""),
                        row.get("round", ""),
                        row.get("month_label", ""),
                        row.get("competition_display", ""),
                        row.get("ha_short", ""),
                        row.get("opponent", ""),
                    ),
                    tags=(str(i),),
                )

        past = past_league_and_emperor_result_rows(self.season, self.team)
        self._schedule_past_rows = past

        pt = getattr(self, "_schedule_past_tree", None)
        if pt is not None:
            pt.delete(*pt.get_children())
            for i, row in enumerate(past):
                pt.insert(
                    "",
                    "end",
                    iid=f"p{i}",
                    values=(
                        row.get("display_order", ""),
                        row.get("opponent", ""),
                        row.get("score", ""),
                        row.get("result", ""),
                        row.get("ha_short", ""),
                        row.get("round_label", ""),
                        row.get("competition_display", ""),
                    ),
                    tags=(str(i),),
                )

    def _refresh_information_window(self) -> None:
        win = getattr(self, "_information_window", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        if getattr(self, "information_header_var", None) is None:
            return

        current_round = self._safe_get(self.season, "current_round", 0)
        total_rounds = self._safe_get(self.season, "total_rounds", 0)
        phase = self._safe_get(self.season, "phase", "-")
        game_count = self._safe_get(self.season, "game_count", 0)
        season_finished = bool(self._safe_get(self.season, "season_finished", False))

        self.information_header_var.set(
            f"{self._team_name()} 情報画面    ラウンド {current_round}/{total_rounds}    phase: {phase}"
        )

        titw = getattr(self, "_information_team_identity_text", None)
        if titw is not None:
            if self.team is not None:
                try:
                    tid_body = format_team_identity_text(self.team)
                except Exception:
                    tid_body = "チーム情報を取得できませんでした。"
            else:
                tid_body = "チームが未接続です。"
            try:
                titw.configure(state="normal")
                titw.delete("1.0", tk.END)
                titw.insert("1.0", tid_body)
                titw.configure(state="disabled")
            except tk.TclError:
                pass

        progress_lines = [
            f"現在ラウンド: {current_round}/{total_rounds}",
            f"トレード／インシーズンFA: {self._roster_transaction_status_text()}",
            f"フェーズ: {phase}",
            f"累計試合数: {game_count}",
            f"シーズン終了: {'はい' if season_finished else 'いいえ'}",
            f"現在日付: {self._format_date(self._get_current_date())}",
            f"年度: {self._get_season_year()}",
        ]
        ipl = getattr(self, "info_progress_lines", None)
        if ipl:
            for var, line in zip(ipl, progress_lines):
                var.set(line)

        schedule_lines = self._build_information_schedule_lines()
        isl = getattr(self, "info_schedule_lines", None)
        if isl:
            while len(schedule_lines) < len(isl):
                schedule_lines.append("")
            for var, line in zip(isl, schedule_lines[: len(isl)]):
                var.set(line)

        comp_lines = self._build_information_competition_lines()
        icl = getattr(self, "info_comp_lines", None)
        if icl:
            while len(comp_lines) < len(icl):
                comp_lines.append("")
            for var, line in zip(icl, comp_lines[: len(icl)]):
                var.set(line)

        level = self._information_division_level()
        ut = self.team

        st_tree = getattr(self, "_information_standings_tree", None)
        if st_tree is not None:
            try:
                st_tree.delete(*st_tree.get_children())
            except Exception:
                pass
            srows = build_standings_rows(self.season, level, user_team=ut)
            if not srows:
                st_tree.insert("", "end", values=("", f"D{level}: データなし", "", "", "", "", "", "", ""))
            else:
                for i, r in enumerate(srows):
                    tags = ("user",) if r.get("is_user_row") else ()
                    wp = float(r.get("win_pct", 0.0) or 0.0)
                    st_tree.insert(
                        "",
                        "end",
                        iid=f"s{i}",
                        values=(
                            r.get("rank", ""),
                            r.get("name", ""),
                            r.get("wins", ""),
                            r.get("losses", ""),
                            f"{wp:.3f}",
                            r.get("pf", ""),
                            r.get("pa", ""),
                            r.get("diff", ""),
                            "自" if r.get("is_user_row") else "",
                        ),
                        tags=tags,
                    )

        tm_tree = getattr(self, "_information_team_tree", None)
        if tm_tree is not None:
            try:
                tm_tree.delete(*tm_tree.get_children())
            except Exception:
                pass
            trows = build_team_summary_rows(self.season, level)
            if not trows:
                tm_tree.insert("", "end", values=("", f"D{level}: データなし", "", "", "", ""))
            else:
                for i, r in enumerate(trows):
                    tags = ("user",) if r.get("is_user_row") else ()
                    tm_tree.insert(
                        "",
                        "end",
                        iid=f"t{i}",
                        values=(
                            r.get("rank", ""),
                            r.get("name", ""),
                            f"{float(r.get('avg_pf', 0.0)):.1f}",
                            f"{float(r.get('avg_pa', 0.0)):.1f}",
                            f"{float(r.get('avg_diff', 0.0)):.1f}",
                            "自" if r.get("is_user_row") else "",
                        ),
                        tags=tags,
                    )

        pl_tree = getattr(self, "_information_player_tree", None)
        if pl_tree is not None:
            try:
                pl_tree.delete(*pl_tree.get_children())
            except Exception:
                pass
            sk = self._information_player_stat_key()
            prows = build_player_leaderboard_rows(
                self.season, level, sk, top_n=50, min_games=1
            )
            if prows:
                sample = prows[0]
                try:
                    pl_tree.heading("avg", text=str(sample.get("per_game_label", "平均")))
                    pl_tree.heading("tot", text=str(sample.get("total_label", "合計")))
                except Exception:
                    pass
            if not prows:
                pl_tree.insert("", "end", values=("", f"D{level}: 該当選手なし", "", "", "", "", "", ""))
            else:
                for i, r in enumerate(prows):
                    pl_tree.insert(
                        "",
                        "end",
                        iid=f"p{i}",
                        values=(
                            r.get("rank", ""),
                            r.get("name", ""),
                            r.get("team_name", ""),
                            r.get("position", ""),
                            r.get("ovr", ""),
                            r.get("per_game", ""),
                            r.get("total", ""),
                            r.get("games_played", ""),
                        ),
                    )

        nt = getattr(self, "_information_news_text", None)
        if nt is not None:
            news_lines = build_information_news_lines(
                team_name=self._team_name(),
                rank_text=self._compute_rank_text(),
                wins=self._safe_int(self._safe_get(self.team, "regular_wins", 0)),
                losses=self._safe_int(self._safe_get(self.team, "regular_losses", 0)),
                external_items=self.external_news_items,
            )
            nt.configure(state="normal")
            nt.delete("1.0", tk.END)
            nt.insert(tk.END, "\n".join(news_lines))
            nt.configure(state="disabled")

        at = getattr(self, "_information_awards_text", None)
        if at is not None:
            aw_lines = format_awards_lines_for_division(self.season, level)
            at.configure(state="normal")
            at.delete("1.0", tk.END)
            at.insert(tk.END, "\n".join(aw_lines))
            at.configure(state="disabled")

        hint = getattr(self, "information_hint_var", None)
        if hint is not None:
            hint.set(
                "読み取り専用です。概要はシーズン進行・次ラウンドの要約と大会状況です。"
                " 試合の一覧・過去結果の詳細は左メニュー「日程」ウィンドウが正本です。"
                " 順位表・チーム／個人成績はタブ上部の区分（D1〜D3）で切り替えます。"
                " トレード／インシーズンFAは消化ラウンド22以降でロック（3月第2週終了相当）。"
            )

    def _build_information_schedule_lines(self) -> List[str]:
        try:
            return information_panel_schedule_lines(
                self.season, max_events=7, user_team=self.team
            )
        except Exception:
            return ["日程表示の生成に失敗しました", "—"]

    def _format_season_event_matchup(self, event: Any) -> str:
        try:
            return format_season_event_matchup_line(event)
        except Exception:
            return ""

    def _build_information_competition_lines(self) -> List[str]:
        lines = []

        emperor_enabled = bool(self._safe_get(self.season, "emperor_cup_enabled", False))
        emperor_logs = self._safe_get(self.season, "emperor_cup_stage_logs", {}) or {}
        emperor_stage = self._latest_stage_name(emperor_logs) if emperor_enabled else "-"
        emperor_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "emperor_cup_results", {}), "champion", None)
        )
        lines.append(
            f"{competition_display_name('emperor_cup')}: "
            f"{'開催中' if emperor_enabled else '未開催'} / 現在段階: {emperor_stage} / 優勝: {emperor_champion}"
        )
        cup_digest = emperor_cup_log_digest_lines(
            self.season, limit=12, user_team=self.team
        )
        if cup_digest:
            lines.append("全日本カップ・試合ログ（抜粋）:")
            lines.extend(cup_digest)

        easl_enabled = bool(self._safe_get(self.season, "easl_enabled", False))
        easl_logs = self._safe_get(self.season, "easl_stage_logs", {}) or {}
        easl_stage = self._latest_stage_name(easl_logs) if easl_enabled else "-"
        easl_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "easl_results", {}), "champion", None)
        )
        lines.append(
            f"{competition_display_name('easl')}: "
            f"{'開催中' if easl_enabled else '未開催'} / 現在段階: {easl_stage} / 優勝: {easl_champion}"
        )

        acl_enabled = bool(self._safe_get(self.season, "acl_enabled", False))
        acl_logs = self._safe_get(self.season, "acl_stage_logs", {}) or {}
        acl_stage = self._latest_stage_name(acl_logs) if acl_enabled else "-"
        acl_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "acl_results", {}), "champion", None)
        )
        lines.append(
            f"{competition_display_name('asia_cl')}: "
            f"{'開催中' if acl_enabled else '未開催'} / 現在段階: {acl_stage} / 優勝: {acl_champion}"
        )

        lines.append(f"{competition_display_name('playoff')}:")
        lines.extend(division_playoff_pending_note_lines(self.season))
        lines.extend(user_team_division_playoff_projection_lines(self.season, self.team))
        lines.extend(division_playoff_results_prominent_lines(self.season))
        if self.team is not None:
            lbl, detail = user_team_division_playoff_result_parts(self.season, self.team)
            lines.append(f"【自クラブ】ディビジョンPO: {lbl} — {detail}")

        competitions = self._safe_get(self.season, "competitions", {}) or {}
        if isinstance(competitions, dict) and competitions:
            lines.append(f"登録大会数: {len(competitions)}")
        else:
            lines.append("登録大会数: -")

        return lines

    def _get_league_teams_for_level(self, level: int) -> List[Any]:
        leagues = self._safe_get(self.season, "leagues", None)
        if isinstance(leagues, dict):
            teams = leagues.get(level, [])
            if teams:
                return list(teams)

        all_teams = list(self._iter_league_teams())
        return [t for t in all_teams if self._safe_int(self._safe_get(t, "league_level", 0)) == level]

    def _latest_stage_name(self, stage_logs: Any) -> str:
        if not isinstance(stage_logs, dict) or not stage_logs:
            return "-"
        keys = list(stage_logs.keys())
        if not keys:
            return "-"
        return str(keys[-1])

    # ------------------------------------------------------------------
    # History window
    # ------------------------------------------------------------------
    def open_history_window(self) -> None:
        """読み取り専用の歴史ウィンドウ（docs/HISTORY_MENU_SPEC_V1.md）。"""
        window = getattr(self, "_history_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.lift()
                self._refresh_history_window()
                return
        except Exception:
            self._history_window = None

        window = tk.Toplevel(self.root)
        window.title(f"{self._team_name()} - 歴史")
        window.geometry("1160x860")
        window.minsize(940, 700)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass
        window.protocol("WM_DELETE_WINDOW", self._close_history_window)
        self._history_window = window

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="シーズンをまたいだ成績の積み重ねやクラブ記録・レジェンドを確認する画面です。",
            bg="#15171c",
            fg="#a8b4c8",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=1100,
        ).pack(fill="x", pady=(0, 6))

        self.history_header_var = tk.StringVar(value="")
        self.history_hint_var = tk.StringVar(value="")

        ttk.Label(
            outer,
            textvariable=self.history_header_var,
            style="SectionTitle.TLabel",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        ttk.Label(
            outer,
            textvariable=self.history_hint_var,
            background="#15171c",
            foreground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True, pady=(0, 8))

        # --- H1 クラブ年表 ---
        tab_tl = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_tl, text="クラブ年表")
        tl_paned = ttk.Panedwindow(tab_tl, orient=tk.VERTICAL)
        tl_paned.pack(fill="both", expand=True)
        tl_top = ttk.Frame(tl_paned, style="Card.TFrame")
        tl_bot = ttk.Frame(tl_paned, style="Card.TFrame")
        tl_paned.add(tl_top, weight=3)
        tl_paned.add(tl_bot, weight=2)

        tcols = ("season", "lg", "rk", "w", "l", "pct", "pf", "pa", "diff")
        self._history_timeline_tree = ttk.Treeview(
            tl_top,
            columns=tcols,
            show="headings",
            height=14,
            selectmode="browse",
        )
        ht = self._history_timeline_tree
        ht.heading("season", text="シーズン")
        ht.heading("lg", text="区分")
        ht.heading("rk", text="順位")
        ht.heading("w", text="勝")
        ht.heading("l", text="敗")
        ht.heading("pct", text="勝率")
        ht.heading("pf", text="得点")
        ht.heading("pa", text="失点")
        ht.heading("diff", text="得失差")
        ht.column("season", width=88, anchor="w")
        ht.column("lg", width=44, anchor="center")
        ht.column("rk", width=44, anchor="center")
        ht.column("w", width=36, anchor="center")
        ht.column("l", width=36, anchor="center")
        ht.column("pct", width=52, anchor="e")
        ht.column("pf", width=52, anchor="e")
        ht.column("pa", width=52, anchor="e")
        ht.column("diff", width=56, anchor="e")
        tlsb = ttk.Scrollbar(tl_top, orient="vertical", command=ht.yview)
        ht.configure(yscrollcommand=tlsb.set)
        ht.pack(side="left", fill="both", expand=True)
        tlsb.pack(side="right", fill="y")
        ht.bind("<<TreeviewSelect>>", self._on_history_timeline_select)

        ttk.Label(tl_bot, text="行の詳細（マイルストーン・表彰・主力抜粋）", style="SectionTitle.TLabel").pack(
            anchor="w", padx=4, pady=(0, 4)
        )
        self._history_timeline_detail = scrolledtext.ScrolledText(
            tl_bot,
            height=8,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._history_timeline_detail.pack(fill="both", expand=True)
        self._history_timeline_detail.configure(state="disabled")

        # --- H2 チームの歩み ---
        tab_j = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_j, text="チームの歩み")
        self._history_journey_text = scrolledtext.ScrolledText(
            tab_j,
            height=22,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._history_journey_text.pack(fill="both", expand=True)
        self._history_journey_text.configure(state="disabled")

        # --- H3 レジェンド ---
        tab_lg = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_lg, text="レジェンド")
        lg_tool = ttk.Frame(tab_lg, style="Root.TFrame")
        lg_tool.pack(fill="x", pady=(0, 8))
        ttk.Label(lg_tool, text="表示:", style="TopBar.TLabel").pack(side="left", padx=(0, 8))
        self._history_legend_label_to_key = {lab: key for lab, key in legend_view_options()}
        default_lg_label = legend_view_options()[0][0] if legend_view_options() else ""
        self.history_legend_view_var = tk.StringVar(value=default_lg_label)
        self._history_legend_combo = ttk.Combobox(
            lg_tool,
            textvariable=self.history_legend_view_var,
            values=tuple(lab for lab, _k in legend_view_options()),
            state="readonly",
            width=26,
        )
        self._history_legend_combo.pack(side="left")
        self._history_legend_combo.bind("<<ComboboxSelected>>", self._on_history_legend_combo_changed)
        tk.Label(
            tab_lg,
            text="※ 通算系はキャリア通算に近い集計です（クラブ在籍のみではありません）。",
            bg="#15171c",
            fg="#9aa3af",
            anchor="w",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", pady=(0, 6))

        lg_fr = ttk.Frame(tab_lg, style="Card.TFrame")
        lg_fr.pack(fill="both", expand=True)
        lgcols = ("rk", "nm", "c1", "c2", "c3")
        self._history_legend_tree = ttk.Treeview(
            lg_fr,
            columns=lgcols,
            show="headings",
            height=16,
            selectmode="browse",
        )
        lgt = self._history_legend_tree
        lgt.heading("rk", text="順位")
        lgt.heading("nm", text="名前")
        lgt.heading("c1", text="")
        lgt.heading("c2", text="")
        lgt.heading("c3", text="")
        lgt.column("rk", width=44, anchor="center")
        lgt.column("nm", width=160, anchor="w")
        lgt.column("c1", width=88, anchor="e")
        lgt.column("c2", width=88, anchor="e")
        lgt.column("c3", width=120, anchor="w")
        lgsb = ttk.Scrollbar(lg_fr, orient="vertical", command=lgt.yview)
        lgt.configure(yscrollcommand=lgsb.set)
        lgt.pack(side="left", fill="both", expand=True)
        lgsb.pack(side="right", fill="y")

        # --- H4 エピソード ---
        tab_ep = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_ep, text="ドラマ・エピソード")
        self._history_episode_text = scrolledtext.ScrolledText(
            tab_ep,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._history_episode_text.pack(fill="both", expand=True)
        self._history_episode_text.configure(state="disabled")

        # --- H5 経営・文化 ---
        tab_cu = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_cu, text="経営・文化")
        self._history_culture_text = scrolledtext.ScrolledText(
            tab_cu,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._history_culture_text.pack(fill="both", expand=True)
        self._history_culture_text.configure(state="disabled")

        # --- 全文レポート（従来の1画面分） ---
        tab_full = ttk.Frame(nb, style="Root.TFrame", padding=8)
        nb.add(tab_full, text="全文レポート")
        self._history_full_text = scrolledtext.ScrolledText(
            tab_full,
            height=24,
            wrap="word",
            bg="#222834",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self._history_full_text.pack(fill="both", expand=True)
        self._history_full_text.configure(state="disabled")

        self._history_timeline_rows = []
        self._history_milestone_cache = []
        self._history_award_cache = []

        hist_bottom = ttk.Frame(outer, style="Panel.TFrame", padding=(8, 4))
        hist_bottom.pack(fill="x", pady=(6, 0))
        hf = tk.Frame(hist_bottom, bg="#1d2129")
        hf.pack(anchor="e")
        self._jpn_text_button(hf, "閉じる", self._close_history_window, side="right")

        self._refresh_history_window()

    def _close_history_window(self) -> None:
        window = getattr(self, "_history_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._history_window = None
            self.history_text = None
            self._history_timeline_tree = None
            self._history_timeline_detail = None
            self._history_journey_text = None
            self._history_legend_tree = None
            self._history_legend_combo = None
            self._history_episode_text = None
            self._history_culture_text = None
            self._history_full_text = None
            self._history_timeline_rows = []
            self._history_milestone_cache = []
            self._history_award_cache = []

    def _on_history_timeline_select(self, _event: Any = None) -> None:
        tree = getattr(self, "_history_timeline_tree", None)
        det = getattr(self, "_history_timeline_detail", None)
        team = getattr(self, "team", None)
        if tree is None or det is None or team is None:
            return
        sel = tree.selection()
        if not sel:
            return
        tags = tree.item(sel[0], "tags")
        if not tags:
            return
        try:
            idx = int(tags[0])
        except (TypeError, ValueError):
            return
        rows = getattr(self, "_history_timeline_rows", None) or []
        if idx < 0 or idx >= len(rows):
            return
        row = rows[idx]
        season_disp = str(row.get("season", "-"))
        lines = timeline_selection_detail_lines(
            season_display=season_disp,
            milestone_rows=list(getattr(self, "_history_milestone_cache", []) or []),
            award_rows=list(getattr(self, "_history_award_cache", []) or []),
            raw_history_seasons=list(getattr(team, "history_seasons", []) or []),
        )
        det.configure(state="normal")
        det.delete("1.0", tk.END)
        det.insert(tk.END, "\n".join(lines))
        det.configure(state="disabled")

    def _on_history_legend_combo_changed(self, _event: Any = None) -> None:
        self._refresh_history_legend_panel()

    def _refresh_history_legend_panel(self) -> None:
        team = getattr(self, "team", None)
        tree = getattr(self, "_history_legend_tree", None)
        if tree is None:
            return
        label = ""
        try:
            label = str(self.history_legend_view_var.get())
        except Exception:
            pass
        key = getattr(self, "_history_legend_label_to_key", {}).get(label, "club_legends")
        rows = fetch_legend_table_rows(team, key, top_n=30)

        h1, h2, h3 = "列1", "列2", "列3"
        if key == "club_legends":
            h1, h2, h3 = "得点", "レガシー", "概要"
        elif key == "all_time_points":
            h1, h2, h3 = "通算得点", "出場", "ピークOVR"
        elif key == "all_time_games":
            h1, h2, h3 = "出場", "通算得点", "ピークOVR"
        elif key == "single_season_points":
            h1, h2, h3 = "シーズン", "得点", "Ast"
        elif key == "single_season_assists":
            h1, h2, h3 = "シーズン", "Ast", "得点"
        tree.heading("c1", text=h1)
        tree.heading("c2", text=h2)
        tree.heading("c3", text=h3)

        try:
            tree.delete(*tree.get_children())
        except Exception:
            pass
        for r in rows:
            tree.insert(
                "",
                "end",
                values=(
                    r.get("rk", ""),
                    r.get("name", ""),
                    r.get("c1", ""),
                    r.get("c2", ""),
                    r.get("c3", ""),
                ),
            )

    def _refresh_history_window(self) -> None:
        win = getattr(self, "_history_window", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        if getattr(self, "history_header_var", None) is None:
            return

        self.history_header_var.set(f"{self._team_name()} 歴史")
        self.history_hint_var.set(
            "読み取り専用です。年表は同一シーズンが複数行ある場合、順位など情報の多い行を優先して表示します。"
            " オフシーズン時の主力スナップショットは、シーズン終了時の順位行へマージして二重化しにくくしています。"
            " 通算記録はキャリア通算に近い集計です。詳細は年表の行を選択してください。全文レポートは従来どおり1本です。"
        )

        team = getattr(self, "team", None)

        # マイルストーン・表彰キャッシュ（年表詳細用）
        self._history_milestone_cache = []
        self._history_award_cache = []
        if team is not None:
            mg = getattr(team, "get_club_history_milestone_rows", None)
            if callable(mg):
                try:
                    self._history_milestone_cache = [
                        x for x in (mg(limit=100) or []) if isinstance(x, dict)
                    ]
                except Exception:
                    self._history_milestone_cache = []
            ag = getattr(team, "get_club_history_award_rows", None)
            if callable(ag):
                try:
                    self._history_award_cache = [x for x in (ag(limit=40) or []) if isinstance(x, dict)]
                except Exception:
                    self._history_award_cache = []

        # H1 年表
        tl_tree = getattr(self, "_history_timeline_tree", None)
        if tl_tree is not None:
            trows = fetch_timeline_rows(team, limit=120) if team is not None else []
            self._history_timeline_rows = trows
            try:
                tl_tree.delete(*tl_tree.get_children())
            except Exception:
                pass
            for i, r in enumerate(trows):
                wp = r.get("win_pct", "-")
                wp_s = f"{float(wp):.3f}" if isinstance(wp, (int, float)) else str(wp)
                pf = r.get("points_for", "-")
                pa = r.get("points_against", "-")
                pd = r.get("point_diff", "-")
                tl_tree.insert(
                    "",
                    "end",
                    iid=f"ht{i}",
                    values=(
                        r.get("season", "-"),
                        r.get("league_level", "-"),
                        r.get("rank", "-"),
                        r.get("wins", "-"),
                        r.get("losses", "-"),
                        wp_s,
                        pf,
                        pa,
                        pd,
                    ),
                    tags=(str(i),),
                )

        det = getattr(self, "_history_timeline_detail", None)
        if det is not None:
            det.configure(state="normal")
            det.delete("1.0", tk.END)
            det.insert(
                tk.END,
                "年表の行を選択すると、このシーズンのマイルストーン・表彰・主力抜粋を表示します。\n"
                "※ 表彰は行にシーズンが無い古いセーブでは空になりやすいです。",
            )
            det.configure(state="disabled")

        jt = getattr(self, "_history_journey_text", None)
        if jt is not None:
            jlines = build_journey_lines(team)
            jt.configure(state="normal")
            jt.delete("1.0", tk.END)
            jt.insert(tk.END, "\n".join(jlines))
            jt.configure(state="disabled")

        self._refresh_history_legend_panel()

        et = getattr(self, "_history_episode_text", None)
        if et is not None:
            elines = build_episode_lines(team)
            et.configure(state="normal")
            et.delete("1.0", tk.END)
            et.insert(tk.END, "\n".join(elines))
            et.configure(state="disabled")

        ct = getattr(self, "_history_culture_text", None)
        if ct is not None:
            clines = build_culture_lines(team)
            ct.configure(state="normal")
            ct.delete("1.0", tk.END)
            ct.insert(tk.END, "\n".join(clines))
            ct.configure(state="disabled")

        ft = getattr(self, "_history_full_text", None)
        if ft is not None:
            flines = self._build_history_report_lines()
            ft.configure(state="normal")
            ft.delete("1.0", tk.END)
            ft.insert(tk.END, "\n".join(flines))
            ft.configure(state="disabled")

    def _build_history_report_lines(self) -> List[str]:
        team = getattr(self, "team", None)
        # team が None でも UI が落ちないよう、骨格だけ返す
        if team is None:
            return [
                "==============================",
                "UNKNOWN クラブ史レポート",
                "==============================",
                "",
                "【最近の流れ】",
                "まだ十分なシーズン履歴がありません。",
                "",
                "【最近のシーズン】",
                "",
                "【マイルストーン（国際）】",
                "- まだ国際大会のマイルストーンはありません。",
                "",
                "【マイルストーン（FINAL BOSS）】",
                "- FINAL BOSS への挑戦履歴はまだありません。",
                "",
                "【マイルストーン（国内・昇降格）】",
                "- まだ国内のマイルストーンはありません。",
                "",
                "【クラブ表彰】",
                "- クラブ表彰はまだありません。",
                "",
                "【クラブレジェンド】",
                "- まだクラブレジェンドは不在。これから歴史を作る段階。",
            ]

        lines: List[str] = []

        summary = {}
        summary_getter = getattr(team, "get_club_history_summary", None)
        if callable(summary_getter):
            try:
                summary = summary_getter() or {}
            except Exception:
                summary = {}

        season_rows: List[dict] = []
        season_getter = getattr(team, "get_club_history_season_rows", None)
        if callable(season_getter):
            try:
                # team.get_club_history_report_text() の season_limit=10 に揃える
                season_rows = list(season_getter(limit=10) or [])
            except Exception:
                season_rows = []

        milestone_rows: List[dict] = []
        milestone_getter = getattr(team, "get_club_history_milestone_rows", None)
        if callable(milestone_getter):
            try:
                # 3ブロック表示（国際/FINAL BOSS/国内）で取りこぼしが出ないよう、
                # 取得は多めに行い、表示側の limit で絞る。
                milestone_rows = list(milestone_getter(limit=60) or [])
            except Exception:
                milestone_rows = []

        award_rows: List[dict] = []
        award_getter = getattr(team, "get_club_history_award_rows", None)
        if callable(award_getter):
            try:
                award_rows = list(award_getter(limit=10) or [])
            except Exception:
                award_rows = []

        legend_rows: List[dict] = []
        legend_getter = getattr(team, "get_club_history_legend_rows", None)
        if callable(legend_getter):
            try:
                legend_rows = list(legend_getter(limit=5) or [])
            except Exception:
                legend_rows = []

        report_text = None
        report_getter = getattr(team, "get_club_history_report_text", None)
        if callable(report_getter):
            try:
                report_text = report_getter(season_limit=10)
            except Exception:
                report_text = None

        club_name = self._team_name()
        lines.append("==============================")
        lines.append(f"{club_name} クラブ史レポート")
        lines.append("==============================")
        # 詳細レポートと同じ並びに寄せる（見出しは置かず本文に統合）
        if isinstance(summary, dict) and summary:
            def _int0(v: Any) -> int:
                try:
                    return int(v)
                except Exception:
                    return 0

            season_count = _int0(summary.get("season_count", 0))
            total_titles = _int0(summary.get("total_titles", summary.get("title_count", 0)))
            league_titles = _int0(summary.get("league_titles", 0))
            cup_titles = _int0(summary.get("cup_titles", 0))
            international_titles = _int0(summary.get("international_titles", 0))
            promotions = _int0(summary.get("promotions", 0))
            relegations = _int0(summary.get("relegations", 0))
            legend_count = _int0(summary.get("legend_count", 0))
            award_count = _int0(summary.get("award_count", 0))

            # 表示名は team 側の整形に合わせる
            league_label = "-"
            try:
                fmt_getter = getattr(team, "_format_league_label_for_history", None)
                if callable(fmt_getter):
                    league_label = fmt_getter(summary.get("current_league_level", 0))
                else:
                    league_label = f"D{summary.get('current_league_level', '-')}"
            except Exception:
                league_label = "-"

            club_identity_line = "-"
            try:
                identity_getter = getattr(team, "_build_club_identity_line", None)
                if callable(identity_getter):
                    club_identity_line = str(identity_getter(summary))
            except Exception:
                club_identity_line = "-"

            lines.append(f"現在所属: {league_label}")
            lines.append(f"通算シーズン数: {season_count}")
            lines.append(club_identity_line)
            lines.append("")
            lines.append(
                f"主要実績: タイトル{total_titles}回 "
                f"(リーグ{league_titles} / カップ{cup_titles} / 国際{international_titles})"
            )
            lines.append(
                f"昇格{promotions}回 / 降格{relegations}回 / "
                f"レジェンド{legend_count}人 / クラブ表彰{award_count}件"
            )
        else:
            # summary が未生成でも、骨格（現在所属/通算シーズン数）は崩さない
            league_label = "-"
            try:
                raw_league = getattr(team, "league_level", None)
                fmt_getter = getattr(team, "_format_league_label_for_history", None)
                if callable(fmt_getter):
                    league_label = fmt_getter(raw_league)
                elif raw_league is not None:
                    league_label = f"D{raw_league}"
            except Exception:
                league_label = "-"

            season_count = 0
            try:
                season_count = len(list(getattr(team, "history_seasons", []) or []))
            except Exception:
                season_count = 0

            lines.append(f"現在所属: {league_label}")
            lines.append(f"通算シーズン数: {season_count}")
            lines.append("クラブ概要データはまだありません")

        lines.append("")
        lines.append("【最近の流れ】")
        build_trend_getter = getattr(team, "_build_recent_trend_line", None)
        trend_line = "まだ十分なシーズン履歴がありません。"
        if season_rows and callable(build_trend_getter):
            try:
                trend_line = str(build_trend_getter(season_rows) or trend_line)
            except Exception:
                pass
        lines.append(trend_line)
        lines.append("")
        lines.append("【最近のシーズン】")
        if season_rows:
            build_tags_getter = getattr(team, "_build_history_status_tags", None)
            for idx, row in enumerate(season_rows, start=1):
                season_label = self._history_pick(
                    row,
                    ["season", "season_label", "year", "season_year"],
                    default=f"Season {idx}",
                )
                league_label = self._history_pick(row, ["league_level", "league", "division"], default="-")
                rank_label = self._history_pick(row, ["rank", "final_rank", "standing", "placement"], default="-")
                wins = self._history_pick(row, ["wins", "regular_wins"], default="-")
                losses = self._history_pick(row, ["losses", "regular_losses"], default="-")

                point_diff = self._history_pick(row, ["point_diff"], default="-")
                diff_text = "-"
                if isinstance(point_diff, (int, float)):
                    diff_text = f"{int(point_diff):+}"

                tags = []
                if callable(build_tags_getter) and isinstance(row, dict):
                    try:
                        tags = list(build_tags_getter(row) or [])
                    except Exception:
                        tags = []
                tag_text = f" [{' / '.join(tags)}]" if tags else ""

                lines.append(
                    f"- {season_label} | {league_label} | {rank_label}位 | "
                    f"{wins}勝{losses}敗 | 得失点差{diff_text}{tag_text}"
                )

                note = self._history_pick(row, ["note"], default="")
                if note not in (None, "", "-"):
                    lines.append(f"  メモ: {note}")
        else:
            # team.get_club_history_report_text() 側は、season_rows が無い場合は
            # 「最近のシーズン」直下にダミー行を入れないため、ここでも同様に空にする
            pass

        lines.append("")
        # ------------------------------------------------------------
        # マイルストーン（詳細レポートと同じ3ブロック表示）
        # ------------------------------------------------------------
        build_headlines_getter = getattr(team, "_build_milestone_headlines", None)

        def _is_final_boss_row(row: dict) -> bool:
            blob = " | ".join([str(row.get("title", "")), str(row.get("detail", "")), str(row.get("category", ""))])
            return "final boss" in blob.lower() or "FINAL BOSS" in blob

        def _is_international_row(row: dict) -> bool:
            blob = " | ".join([str(row.get("title", "")), str(row.get("detail", "")), str(row.get("category", ""))])
            keys = [
                "EASL",
                "ACL",
                "東アジアトップリーグ",
                "オールアジアトーナメント",
                "アジアクラブ選手権",
                "アジアカップ",
                "世界一決定戦",
                "intercontinental",
                "インターコンチネンタル",
            ]
            low = blob.lower()
            return any(k.lower() in low for k in keys)

        final_boss_rows = [r for r in milestone_rows if isinstance(r, dict) and _is_final_boss_row(r)]
        international_rows = [
            r for r in milestone_rows if isinstance(r, dict) and (not _is_final_boss_row(r)) and _is_international_row(r)
        ]
        domestic_rows = [
            r
            for r in milestone_rows
            if isinstance(r, dict) and (not _is_final_boss_row(r)) and (not _is_international_row(r))
        ]

        # 国際（要約表示）
        lines.append("【マイルストーン（国際）】")
        intl_headlines: List[str] = []
        if callable(build_headlines_getter):
            try:
                intl_headlines = list(build_headlines_getter(international_rows, limit=5) or [])
            except Exception:
                intl_headlines = []
        if intl_headlines:
            for line in intl_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- まだ国際大会のマイルストーンはありません。")

        # FINAL BOSS（要約表示）
        lines.append("")
        lines.append("【マイルストーン（FINAL BOSS）】")
        boss_headlines: List[str] = []
        if callable(build_headlines_getter):
            try:
                boss_headlines = list(build_headlines_getter(final_boss_rows, limit=4) or [])
            except Exception:
                boss_headlines = []
        if boss_headlines:
            for line in boss_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- FINAL BOSS への挑戦履歴はまだありません。")

        # 国内・昇降格（要約表示）
        lines.append("")
        lines.append("【マイルストーン（国内・昇降格）】")
        dom_headlines: List[str] = []
        if callable(build_headlines_getter):
            try:
                dom_headlines = list(build_headlines_getter(domestic_rows, limit=5) or [])
            except Exception:
                dom_headlines = []
        if dom_headlines:
            for line in dom_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- まだ国内のマイルストーンはありません。")

        # ------------------------------------------------------------
        # 近年の象徴的トピック（詳細レポートと同じ要約書式）
        # ------------------------------------------------------------
        try:
            season_count = 0
            if isinstance(summary, dict):
                season_count = int(summary.get("season_count") or summary.get("seasons") or 0)
            build_recent_getter = getattr(team, "_build_recent_big_milestone_lines", None)
            recent_big_lines: List[str] = []
            if callable(build_recent_getter) and season_count >= 2:
                recent_big_lines = list(build_recent_getter(milestone_rows, limit=4) or [])
            if recent_big_lines:
                lines.append("【近年の象徴的トピック】")
                lines.extend(recent_big_lines)
                lines.append("")
        except Exception:
            # ここは表示補助なので落とさない
            pass

        # セクション間の空行はちょうど1つに揃える
        lines.append("")
        lines.append("【クラブ表彰】")
        if award_rows:
            for row in award_rows:
                season_label = self._history_pick(row, ["season", "season_label", "year"], default="-")
                award_name = self._history_pick(row, ["award", "award_type", "title", "name"], default="-")
                player_name = self._history_pick(row, ["player", "winner", "recipient", "name"], default="-")
                detail = self._history_pick(row, ["detail", "description", "summary", "note"], default="")
                detail_text = f" | {detail}" if detail not in (None, "", "-") else ""
                lines.append(f"- {season_label} | {award_name} | {player_name}{detail_text}")
        else:
            lines.append("- クラブ表彰はまだありません。")

        lines.append("")
        lines.append("【クラブレジェンド】")
        if legend_rows:
            build_legend_headlines_getter = getattr(team, "_build_legend_headlines", None)
            if callable(build_legend_headlines_getter):
                try:
                    legend_headlines: List[str] = list(build_legend_headlines_getter(legend_rows, limit=5) or [])
                except Exception:
                    legend_headlines = []
            else:
                legend_headlines = []

            if legend_headlines:
                for line in legend_headlines:
                    lines.append(f"- {line}")
            else:
                build_empty_legend_msg_getter = getattr(team, "_build_empty_legend_message", None)
                empty_msg = "まだクラブレジェンドは不在。これから歴史を作る段階。"
                if callable(build_empty_legend_msg_getter):
                    try:
                        empty_msg = str(build_empty_legend_msg_getter())
                    except Exception:
                        pass
                lines.append(f"- {empty_msg}")
        else:
            build_empty_legend_msg_getter = getattr(team, "_build_empty_legend_message", None)
            empty_msg = "まだクラブレジェンドは不在。これから歴史を作る段階。"
            if callable(build_empty_legend_msg_getter):
                try:
                    empty_msg = str(build_empty_legend_msg_getter())
                except Exception:
                    pass
            lines.append(f"- {empty_msg}")

        return lines

    def _history_pick(self, row: Any, keys: List[str], default: Any = "-") -> Any:
        if not isinstance(row, dict):
            return default
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                return row.get(key)
        return default

    # ------------------------------------------------------------------
    # Interaction handlers
    # ------------------------------------------------------------------
    def _format_gm_cli_hint_block(self) -> str:
        """クラブ案内ウィンドウ上部: 閲覧・案内・CLI ショートカット。トレード／FA の詳細は人事案内と同一事実。"""
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        return (
            "【クラブ案内】編集の正本は人事・戦術・経営・情報の各メニューです。"
            "ここは閲覧・案内・ターミナル（CLI）へのショートカットのみです（実行画面ではありません）。\n\n"
            "【トレード・FA】トレードは左メニュー「人事」を開き、上部の「トレード」ボタンから実行できます"
            "（1〜3名の入替、現金・RB 付きも同じ画面）。\n"
            "同じ操作はシーズンメニュー「8. GMメニュー」→「10. トレード」（CLI）からも行えます。\n"
            "レギュラー中の FA プールからの手動獲得は、人事の「インシーズンFA（1人）」から 1 名まで。"
            "期限・可否の詳細は「人事」ウィンドウ上部の案内を参照してください。\n"
            "再契約の確認は、GUIモードでオフシーズン処理の実行中にダイアログで表示されます。\n"
            f"消化ラウンド: {cr}/{tr}\n"
            "ウィンドウ下のボタンはターミナル（CLI）へのショートカットです。\n\n"
            "先発・6th・ベンチ（Team）の編集は、左「戦術」→「ローテーション」→「2. 起用序列」から。"
            "当窓の「スタメン・ベンチ」タブは参照のみです。"
            "戦術・HC・起用（3項目）の補助編集は「戦術」→「プレイスタイル」→「補助設定を開く（Team基本方針・HC）」。"
            "team_tactics 系はプレイスタイル／ローテーションの統合画面から。"
            "当窓の「戦術・HC・起用」タブは参照のみです。"
            "サラリーキャップの数値は左メニュー「経営」の「財務サマリー」下部。当窓の「サラリーキャップ」は案内のみです。"
            "チーム属性は左メニュー「情報」の「概要」上部。当窓の「チーム情報」は案内のみです。"
            "ロスター全文テキストは左メニュー「人事」で「詳細ロスターを表示」から。当窓の「ロスター」は案内のみです。"
            "施設投資もターミナルのシーズンメニュー「8. GMメニュー」から行ってください。"
        )

    @staticmethod
    def _gm_set_readonly_text(widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _refresh_gm_dashboard_window(self) -> None:
        if getattr(self, "_gm_window", None) is None or self.team is None:
            return
        try:
            if not self._gm_window.winfo_exists():
                return
        except Exception:
            return
        self._gm_set_readonly_text(self._gm_hint_text, self._format_gm_cli_hint_block())
        self._gm_set_readonly_text(self._gm_text_team, self._format_gm_team_tab_guidance_text())
        self._gm_set_readonly_text(self._gm_text_cap, self._format_gm_cap_tab_guidance_text())
        self._gm_set_readonly_text(self._gm_text_roster, self._format_gm_roster_tab_guidance_text())
        self._gm_set_readonly_text(self._gm_text_lineup, format_lineup_snapshot_text(self.team))
        if hasattr(self, "_gm_team_policy_text"):
            self._gm_set_readonly_text(
                self._gm_team_policy_text,
                self._format_gm_team_policy_readonly_text(),
            )

    def _format_gm_team_tab_guidance_text(self) -> str:
        if self.team is None:
            return (
                "チームが未接続です。\n\n"
                "チーム情報（クラブ属性）の参照は、左メニュー「情報」→「概要」タブ上部の"
                "「チーム情報（閲覧）」を開いてください。"
            )
        return (
            "チーム名・ホーム球場・愛称などクラブ属性の詳細は、左メニュー「情報」を開き、"
            "「概要」タブ上部の「チーム情報（閲覧）」にまとめました。\n\n"
            "このタブは案内のみです。数値の正は情報画面を参照してください。"
        )

    def _format_gm_cap_tab_guidance_text(self) -> str:
        if self.team is None:
            return (
                "チームが未接続です。\n\n"
                "サラリーキャップの参照は、左メニュー「経営」ウィンドウの"
                "「財務サマリー」下部「サラリーキャップ（閲覧）」を開いてください。"
            )
        return (
            "サラリーキャップ・ペイロールの詳細な参照は、左メニュー「経営」を開き、"
            "「財務サマリー」パネル下部の「サラリーキャップ（閲覧）」にまとめました。\n\n"
            "このタブは案内のみです。数値の正は経営画面と、"
            "ホームのクラブ状況サマリー（給与・キャップ一行）を参照してください。"
        )

    def _format_gm_roster_tab_guidance_text(self) -> str:
        if self.team is None:
            return (
                "チームが未接続です。\n\n"
                "ロスターの全文テキスト一覧は、左メニュー「人事」を開き、"
                "「詳細ロスターを表示」で別窓を開いて参照してください。"
            )
        return (
            "ロスター全員のテキスト一覧（並び・体裁は docs/GM_ROSTER_DISPLAY_RULES.md）の参照は、"
            "左メニュー「人事」を開き、表の下の「詳細ロスターを表示」で別窓にまとめました。\n\n"
            "契約の＋1年延長・FA 解除などの操作は、人事ウィンドウ上部の表から選手を選んで行ってください。\n\n"
            "このタブは案内のみです。"
        )

    def _format_gm_team_policy_readonly_text(self) -> str:
        if self.team is None:
            return "—"
        sk = getattr(self.team, "strategy", "balanced")
        ck = getattr(self.team, "coach_style", "balanced")
        uk = getattr(self.team, "usage_policy", "balanced")
        st = self.STRATEGY_LABELS.get(str(sk), str(sk))
        ct = self.COACH_STYLE_LABELS.get(str(ck), str(ck))
        ut = self.USAGE_POLICY_LABELS.get(str(uk), str(uk))
        lines = [
            "編集は左「戦術」→「プレイスタイル」内「補助設定を開く（Team基本方針・HC）」／"
            "「ローテーション」内「2. 起用序列」（スタメン・6th・ベンチ序列・いずれも従来どおりの保存先）。",
            "",
            f"基本戦術 (Team.strategy): {st}",
            f"HCスタイル: {ct}",
            f"基本起用 (Team.usage_policy): {ut}",
            "",
            "【強化メニューとの関連（現在のHC条件）】",
        ]
        lines.extend(self._build_current_special_training_lines(self.team))
        return "\n".join(lines)

    def _sync_strategy_policy_combos(
        self,
        combo_strategy: ttk.Combobox,
        combo_coach: ttk.Combobox,
        combo_usage: ttk.Combobox,
    ) -> None:
        if self.team is None:
            return

        def _set(combo: ttk.Combobox, options: Any, current_key: str) -> None:
            cur = str(current_key)
            for k, lab in options:
                if k == cur:
                    combo.set(lab)
                    return
            combo.set(options[0][1])

        _set(combo_strategy, STRATEGY_OPTIONS, getattr(self.team, "strategy", "balanced"))
        _set(combo_coach, COACH_STYLE_OPTIONS, getattr(self.team, "coach_style", "balanced"))
        _set(combo_usage, USAGE_POLICY_OPTIONS, getattr(self.team, "usage_policy", "balanced"))

    def _lineup_slot_label_to_index(self, label: str) -> int:
        try:
            return self._LINEUP_SLOT_LABELS.index(label)
        except (ValueError, AttributeError):
            return 0

    def _gm_candidate_label_for_player(self, p: Any) -> str:
        return (
            f"{getattr(p, 'name', '-')} ({getattr(p, 'position', '-')}) "
            f"OVR{int(getattr(p, 'ovr', 0))} id={getattr(p, 'player_id', '')}"
        )

    def _sync_strat_lineup_candidates(self) -> None:
        if self.team is None or not hasattr(self, "_strat_combo_lineup_slot"):
            return
        starters = get_current_starting_five(self.team)
        if len(starters) < 5:
            self._strat_candidate_players = []
            self._strat_combo_lineup_candidate.configure(values=[])
            self._strat_combo_lineup_candidate.set("")
            return
        try:
            lab = self._strat_combo_lineup_slot.get()
        except tk.TclError:
            lab = self._LINEUP_SLOT_LABELS[0]
        slot_index = self._lineup_slot_label_to_index(lab)
        cands = get_available_starting_candidates(self.team, starters, slot_index)
        self._strat_candidate_players = list(cands)
        values = [self._gm_candidate_label_for_player(p) for p in cands]
        self._strat_combo_lineup_candidate.configure(values=values)
        if values:
            self._strat_combo_lineup_candidate.set(values[0])
        else:
            self._strat_combo_lineup_candidate.set("")

    def _sync_strat_lineup_edit(self) -> None:
        if self.team is None or not hasattr(self, "_strat_combo_lineup_slot"):
            return
        starters = get_current_starting_five(self.team)
        ok = len(starters) >= 5
        state = "readonly" if ok else "disabled"
        self._strat_combo_lineup_slot.configure(state=state)
        self._strat_combo_lineup_candidate.configure(state=state)
        self._strat_btn_apply_lineup.configure(state="normal" if ok else "disabled")
        if not ok:
            self._strat_candidate_players = []
            self._strat_combo_lineup_candidate.configure(values=[])
            self._strat_combo_lineup_candidate.set("")
            return
        try:
            cur = self._strat_combo_lineup_slot.get()
        except tk.TclError:
            cur = ""
        if not cur or cur not in self._LINEUP_SLOT_LABELS:
            self._strat_combo_lineup_slot.set(self._LINEUP_SLOT_LABELS[0])
        self._sync_strat_lineup_candidates()

    def _on_apply_strat_starting_slot(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        starters = get_current_starting_five(self.team)
        if len(starters) < 5:
            messagebox.showwarning("スタメン", "スタメンが5人未満のため変更できません。", parent=parent)
            return
        try:
            lab = self._strat_combo_lineup_slot.get()
        except tk.TclError:
            lab = self._LINEUP_SLOT_LABELS[0]
        slot_index = self._lineup_slot_label_to_index(lab)
        try:
            sel = self._strat_combo_lineup_candidate.get()
        except tk.TclError:
            sel = ""
        values = [self._gm_candidate_label_for_player(p) for p in self._strat_candidate_players]
        try:
            idx = values.index(sel)
        except ValueError:
            messagebox.showwarning("スタメン", "候補を選択してください。", parent=parent)
            return
        player = self._strat_candidate_players[idx]
        try:
            ok = messagebox.askokcancel(
                "スタメン差し替え",
                f"{lab} の選手を {getattr(player, 'name', '')} に変更しますか？\n\n"
                "（CLIのGM「スタメン変更」と同じ候補ルールです。）",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        success, msg = apply_starting_slot_change(self.team, slot_index, player)
        if not success:
            messagebox.showerror("反映できません", msg, parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "スタメンを更新しました。", parent=parent)

    def _strat_bench_slot_labels(self) -> List[str]:
        return [
            f"{i + 1}. {self._gm_candidate_label_for_player(p)}"
            for i, p in enumerate(self._strat_bench_players)
        ]

    def _sync_strat_sixth_edit(self) -> None:
        if self.team is None or not hasattr(self, "_strat_combo_sixth"):
            return
        cands = get_sixth_man_candidates(self.team)
        self._strat_sixth_candidate_players = list(cands)
        values = [self._gm_candidate_label_for_player(p) for p in cands]
        self._strat_combo_sixth.configure(values=values)
        if values:
            self._strat_combo_sixth.set(values[0])
        else:
            self._strat_combo_sixth.set("")
        self._strat_btn_apply_sixth.configure(state="normal" if values else "disabled")

    def _sync_strat_bench_edit(self) -> None:
        if self.team is None or not hasattr(self, "_strat_combo_bench_a"):
            return
        bench = get_current_bench_order(self.team)
        self._strat_bench_players = list(bench)
        labels = self._strat_bench_slot_labels()
        if len(bench) < 2:
            self._strat_combo_bench_a.configure(values=[], state="disabled")
            self._strat_combo_bench_b.configure(values=[], state="disabled")
            self._strat_combo_bench_a.set("")
            self._strat_combo_bench_b.set("")
            self._strat_btn_bench_swap.configure(state="disabled")
            return
        for combo in (self._strat_combo_bench_a, self._strat_combo_bench_b):
            combo.configure(values=labels, state="readonly")
        self._strat_combo_bench_a.set(labels[0])
        self._strat_combo_bench_b.set(labels[1])
        self._strat_btn_bench_swap.configure(state="normal")

    def _on_apply_strat_sixth_man(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        values = [self._gm_candidate_label_for_player(p) for p in self._strat_sixth_candidate_players]
        try:
            sel = self._strat_combo_sixth.get()
        except tk.TclError:
            sel = ""
        try:
            idx = values.index(sel)
        except ValueError:
            messagebox.showwarning("6thマン", "候補を選択してください。", parent=parent)
            return
        player = self._strat_sixth_candidate_players[idx]
        try:
            ok = messagebox.askokcancel(
                "6thマン",
                f"6thマンを {getattr(player, 'name', '')} に設定しますか？\n\n"
                "（CLIのGM「6thマン変更」と同じ候補です。）",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        success, msg = apply_sixth_man_selection(self.team, player)
        if not success:
            messagebox.showerror("反映できません", msg, parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "6thマンを更新しました。", parent=parent)

    def _on_reset_sixth_man_gui(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        try:
            ok = messagebox.askokcancel(
                "自動6thに戻す",
                "手動の6thマン設定を解除し、自動選出に戻しますか？",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        clr = getattr(self.team, "clear_sixth_man", None)
        if not callable(clr):
            messagebox.showinfo("未対応", "このチームでは6th解除を実行できません。", parent=parent)
            return
        try:
            clr()
        except Exception as exc:
            messagebox.showerror("エラー", str(exc), parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "6thマンを自動選出に戻しました。", parent=parent)

    def _on_apply_strat_bench_swap(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        self._strat_bench_players = list(get_current_bench_order(self.team))
        labels = self._strat_bench_slot_labels()
        if len(self._strat_bench_players) < 2:
            messagebox.showwarning("ベンチ", "ベンチが2人未満のため入れ替えできません。", parent=parent)
            return
        try:
            sa = self._strat_combo_bench_a.get()
            sb = self._strat_combo_bench_b.get()
        except tk.TclError:
            return
        try:
            idx_a = labels.index(sa)
            idx_b = labels.index(sb)
        except ValueError:
            messagebox.showwarning("ベンチ", "控えを選択してください。", parent=parent)
            return
        if idx_a == idx_b:
            messagebox.showwarning("ベンチ", "異なる2つの番号を選んでください。", parent=parent)
            return
        pa = self._strat_bench_players[idx_a]
        pb = self._strat_bench_players[idx_b]
        try:
            ok = messagebox.askokcancel(
                "ベンチ入替",
                f"控え{idx_a + 1}（{getattr(pa, 'name', '')}）と "
                f"控え{idx_b + 1}（{getattr(pb, 'name', '')}）を入れ替えますか？\n\n"
                "（CLIのGM「ベンチ序列変更」と同じく、2人の順序のみ入れ替えます。）",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        success, msg = apply_bench_order_swap(self.team, idx_a, idx_b)
        if not success:
            messagebox.showerror("反映できません", msg, parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "ベンチ序列を更新しました。", parent=parent)

    def _on_reset_bench_order_gui(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        try:
            ok = messagebox.askokcancel(
                "自動ベンチに戻す",
                "手動のベンチ序列を解除し、自動並び（OVR順）に戻しますか？",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        clr = getattr(self.team, "clear_bench_order", None)
        if not callable(clr):
            messagebox.showinfo("未対応", "このチームではベンチ解除を実行できません。", parent=parent)
            return
        try:
            clr()
        except Exception as exc:
            messagebox.showerror("エラー", str(exc), parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "ベンチ序列を自動に戻しました。", parent=parent)

    def _coach_style_label(self, style_key: str) -> str:
        labels = {k: v for k, v in COACH_STYLE_OPTIONS}
        return labels.get(str(style_key or "balanced"), str(style_key or "balanced"))

    def _build_special_training_catalog_items(self, team: Any, coach_override: Optional[str] = None) -> List[tuple]:
        coach = str(getattr(team, "coach_style", "balanced") or "balanced")
        if coach_override is not None:
            coach = str(coach_override or "balanced")
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        fo = int(getattr(team, "front_office_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        return [
            ("個人", "スピード&アジリティ", tf >= 3, "トレーニング施設Lv3以上"),
            ("個人", "映像分析（IQ）", fo >= 2, "フロントオフィスLv2以上"),
            ("個人", "ディフェンスフットワーク", coach in {"defense", "development"}, "HCが「守備重視」または「育成」"),
            ("個人", "筋力強化", med >= 2, "メディカル施設Lv2以上"),
            ("チーム", "精密オフェンス", coach in {"offense", "development"} and tf >= 3, "HCが「攻撃重視」または「育成」かつ トレーニング施設Lv3以上"),
            ("チーム", "強圧ディフェンス", coach == "defense" and med >= 2, "HCが「守備重視」かつ メディカル施設Lv2以上"),
        ]

    def _build_coach_unlock_diff_lines(self, old_coach: str, new_coach: str) -> List[str]:
        old_items = self._build_special_training_catalog_items(self.team, coach_override=old_coach)
        new_items = self._build_special_training_catalog_items(self.team, coach_override=new_coach)
        old_unlocked = {f"{c}:{n}" for c, n, ok, _ in old_items if ok}
        new_unlocked = {f"{c}:{n}" for c, n, ok, _ in new_items if ok}
        reason_map = {f"{c}:{n}": cond for c, n, _, cond in new_items}

        lines = [
            f"HCスタイル: {self._coach_style_label(old_coach)} → {self._coach_style_label(new_coach)}",
            f"解放数: {len(new_unlocked)}/{len(new_items)}",
        ]

        newly_unlocked = sorted(new_unlocked - old_unlocked)
        if newly_unlocked:
            lines.append("新規解放:")
            for row in newly_unlocked:
                lines.append(f"- {row}（理由: {reason_map.get(row, '条件達成')}）")
        else:
            lines.append("新規解放: なし")

        newly_locked = sorted(old_unlocked - new_unlocked)
        if newly_locked:
            lines.append("今回ロック:")
            for row in newly_locked:
                lines.append(f"- {row}（理由: {reason_map.get(row, '条件未達')}）")

        return lines

    def _format_special_training_unlock_gap_ja(self, team: Any, coach: str, drill_name: str) -> str:
        """カタログ項目名ごとに、未解放時の不足条件を短文で示す（閾値は _build_special_training_catalog_items と一致）。"""
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        fo = int(getattr(team, "front_office_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        cur_lab = self._coach_style_label(coach)
        if drill_name == "スピード&アジリティ":
            return f"トレーニング施設Lv3が必要／現在Lv{tf}"
        if drill_name == "映像分析（IQ）":
            return f"フロントLv2が必要／現在Lv{fo}"
        if drill_name == "ディフェンスフットワーク":
            return f"HCが守備重視または育成が必要／現在は{cur_lab}"
        if drill_name == "筋力強化":
            return f"メディカル施設Lv2が必要／現在Lv{med}"
        if drill_name == "精密オフェンス":
            bits: List[str] = []
            if coach not in {"offense", "development"}:
                bits.append(f"HCが攻撃重視または育成が必要／現在は{cur_lab}")
            if tf < 3:
                bits.append(f"トレーニング施設Lv3が必要／現在Lv{tf}")
            return "・".join(bits) if bits else "条件未達"
        if drill_name == "強圧ディフェンス":
            bits = []
            if coach != "defense":
                bits.append(f"HCが守備重視が必要／現在は{cur_lab}")
            if med < 2:
                bits.append(f"メディカル施設Lv2が必要／現在Lv{med}")
            return "・".join(bits) if bits else "条件未達"
        return "条件未達"

    def _build_current_special_training_lines(self, team: Any) -> List[str]:
        if team is None:
            coach = "balanced"
            items: List[tuple] = []
        else:
            coach = str(getattr(team, "coach_style", "balanced") or "balanced")
            items = self._build_special_training_catalog_items(team, coach_override=coach)
        unlocked = [f"{c}:{n}" for c, n, ok, _ in items if ok]
        lines = [
            f"現在HC: {self._coach_style_label(coach) if team is not None else '（チーム未接続）'}",
            f"解放数: {len(unlocked)}/{len(items) if items else 0}",
            "解放中: " + (" / ".join(unlocked) if unlocked else ("なし" if team is not None else "チーム未接続")),
            "── スペシャル練習（項目別）──",
        ]
        if team is not None and items:
            for c, n, ok, _cond in items:
                if ok:
                    lines.append(f"解放済み：【{c}】{n}")
                else:
                    gap = self._format_special_training_unlock_gap_ja(team, coach, n)
                    lines.append(f"未解放：【{c}】{n}（{gap}）")
        elif team is None:
            lines.append("（チームに接続すると項目別の条件を表示します）")
        lines.append("── HC別の解放数（参考）──")
        lines.extend(self._build_coach_unlock_count_rows(team))
        return lines

    def _build_coach_unlock_count_rows(self, team: Any) -> List[str]:
        rows: List[str] = []
        for style_key, style_label in COACH_STYLE_OPTIONS:
            if team is None:
                rows.append(f"{style_label}: —")
                continue
            items = self._build_special_training_catalog_items(team, coach_override=style_key)
            count = len([1 for _, _, ok, _ in items if ok])
            rows.append(f"{style_label}: {count}/{len(items)}")
        return rows

    def _get_team_training_label(self, key: str) -> str:
        labels = {
            "balanced": "バランス",
            "shooting": "シュート強化",
            "defense": "ディフェンス強化",
            "transition": "速攻強化",
            "precision_offense": "精密オフェンス（特別）",
            "intense_defense": "強圧ディフェンス（特別）",
        }
        return labels.get(str(key or "balanced"), str(key or "balanced"))

    def _build_team_training_change_confirm_text(self, old_key: str, new_key: str) -> str:
        return (
            "チーム練習方針を変更しますか？\n\n"
            f"変更前: {self._get_team_training_label(old_key)}\n"
            f"変更後: {self._get_team_training_label(new_key)}"
        )

    def _build_player_training_change_confirm_text(self, player: Any, old_drill: str, new_drill: str) -> str:
        drill_labels = {
            "balanced": "バランス",
            "dribble": "ドリブル練習",
            "rebound": "リバウンド練習",
            "stamina_run": "走り込み（スタミナ）",
            "shoot_form": "シュートフォーム",
            "three_point": "3P特化",
            "free_throw": "フリースロー",
            "drive_finish": "ドライブ&フィニッシュ",
            "passing_read": "パス判断",
            "defense_footwork": "ディフェンスフットワーク",
            "strength": "筋力強化",
            "speed_agility": "スピード&アジリティ",
            "iq_film": "映像分析（IQ）",
        }
        old_label = drill_labels.get(str(old_drill or "balanced"), str(old_drill or "balanced"))
        new_label = drill_labels.get(str(new_drill or "balanced"), str(new_drill or "balanced"))
        return (
            f"{getattr(player, 'name', '-') } の個別練習を変更しますか？\n\n"
            f"変更前: {old_label}\n"
            f"変更後: {new_label}"
        )

    def _append_training_change_log(self, team: Any, message: str) -> None:
        logs = list(getattr(team, "training_change_log", []) or [])
        logs.append(str(message or "").strip())
        setattr(team, "training_change_log", logs[-20:])

    def _get_latest_training_change_log(self, team: Any) -> str:
        logs = list(getattr(team, "training_change_log", []) or [])
        if not logs:
            return "なし"
        return str(logs[-1])

    def _training_log_entry_kind(self, entry: str) -> str:
        s = str(entry or "").strip()
        if s.startswith("チーム練習:"):
            return "team"
        if s.startswith("個別練習:"):
            return "player"
        return "other"

    def _build_development_training_log_summary_text(self, team: Any) -> str:
        """強化メニュー本体下部の直近変更1行要約（件数・最新のみ）。"""
        if team is None:
            return "直近変更：チーム未接続のため履歴を表示できません"
        logs = list(getattr(team, "training_change_log", []) or [])
        if not logs:
            return "直近変更：履歴なし"
        n = len(logs)
        latest = str(logs[-1]).strip()
        if len(latest) > 72:
            latest = latest[:69] + "…"
        return f"直近変更：{n}件あり / 最新：{latest}"

    def _build_development_training_log_detail_body_text(self, team: Any) -> str:
        """別窓用。既存の training_change_log リストをそのまま列挙（保存仕様は触らない）。"""
        if team is None:
            return "チーム未接続のため変更履歴を表示できません。"
        logs = list(getattr(team, "training_change_log", []) or [])
        if not logs:
            return "履歴はまだありません。"
        return "\n".join(f"- {str(e).strip()}" for e in logs)

    def _refresh_development_training_log_widgets(self) -> None:
        frame = getattr(self, "_development_log_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        if getattr(self, "development_training_log_summary_var", None) is None:
            self.development_training_log_summary_var = tk.StringVar(value="")
        team = getattr(self, "team", None)
        self.development_training_log_summary_var.set(self._build_development_training_log_summary_text(team))
        tk.Label(
            frame,
            textvariable=self.development_training_log_summary_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=0,
            wraplength=980,
        ).pack(fill="x", anchor="w", pady=(0, 6))
        ttk.Button(
            frame,
            text="直近変更ログを表示",
            style="Menu.TButton",
            command=self._open_development_training_log_detail_window,
        ).pack(anchor="w")

    def _build_recent_training_change_log_text(self, team: Any, limit: int = 5) -> str:
        logs = list(getattr(team, "training_change_log", []) or [])
        if not logs:
            return "直近変更: なし"
        rows = [f"- {entry}" for entry in logs[-max(1, int(limit)):]]
        return "直近変更:\n" + "\n".join(rows)

    def _team_training_lock_reason(self, team: Any, focus_key: str) -> str:
        coach = str(getattr(team, "coach_style", "balanced") or "balanced")
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        if focus_key == "precision_offense" and not (coach in {"offense", "development"} and tf >= 3):
            return "HCが「攻撃重視」または「育成」かつ トレーニング施設Lv3以上で解放"
        if focus_key == "intense_defense" and not (coach == "defense" and med >= 2):
            return "HCが「守備重視」かつ メディカル施設Lv2以上で解放"
        return ""

    def _player_drill_lock_reason(self, team: Any, drill_key: str) -> str:
        return player_drill_lock_reason(team, drill_key)

    def _open_team_training_editor_window(self) -> None:
        if self.team is None:
            return
        parent = getattr(self, "_development_window", None) or self.root
        w = tk.Toplevel(parent)
        w.title("チーム練習方針を変更")
        w.geometry("560x320")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        options: List[Tuple[str, str]] = [
            ("balanced", "バランス"),
            ("shooting", "シュート強化"),
            ("defense", "ディフェンス強化"),
            ("transition", "速攻強化"),
            ("precision_offense", "精密オフェンス（特別）"),
            ("intense_defense", "強圧ディフェンス（特別）"),
        ]
        label_to_key = {lab: key for key, lab in options}
        ttk.Label(wrap, text="方針", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        combo = ttk.Combobox(wrap, state="readonly", values=[lab for _, lab in options], width=36)
        current = str(getattr(self.team, "team_training_focus", "balanced") or "balanced")
        combo.set(self._get_team_training_label(current))
        combo.pack(anchor="w", pady=(4, 10))
        note_var = tk.StringVar(value="")
        tk.Label(
            wrap,
            textvariable=note_var,
            bg="#1d2129",
            fg="#d6dbe3",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 10),
            padx=8,
            pady=6,
            wraplength=520,
        ).pack(fill="x", pady=(0, 12))

        def _refresh_note(_event: Any = None) -> None:
            key = label_to_key.get(combo.get(), current)
            reason = self._team_training_lock_reason(self.team, key)
            if reason:
                note_var.set(f"未解放（条件）: {reason}")
            else:
                note_var.set("選択可能です。")

        combo.bind("<<ComboboxSelected>>", _refresh_note)
        _refresh_note()

        def _apply() -> None:
            key = label_to_key.get(combo.get())
            if not key:
                messagebox.showerror("エラー", "方針を選択してください。", parent=w)
                return
            old_key = str(getattr(self.team, "team_training_focus", "balanced") or "balanced")
            reason = self._team_training_lock_reason(self.team, key)
            if reason:
                messagebox.showwarning("未解放", f"この方針は未解放です。\n{reason}", parent=w)
                return
            if old_key != key:
                ok = messagebox.askokcancel(
                    "確認",
                    self._build_team_training_change_confirm_text(old_key, key),
                    parent=w,
                )
                if not ok:
                    return
            setattr(self.team, "team_training_focus", key)
            self._append_training_change_log(
                self.team,
                f"チーム練習: {self._get_team_training_label(old_key)} → {self._get_team_training_label(key)}",
            )
            self._refresh_development_window()
            messagebox.showinfo("完了", f"チーム練習を「{self._get_team_training_label(key)}」に変更しました。", parent=w)
            w.destroy()

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x")
        ttk.Button(btn, text="反映", style="Primary.TButton", command=_apply).pack(side="left")
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right")

    def _open_player_training_editor_window(self) -> None:
        if self.team is None:
            return
        parent = getattr(self, "_development_window", None) or self.root
        w = tk.Toplevel(parent)
        w.title("個別練習を変更")
        w.geometry("980x580")
        w.minsize(720, 480)
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.rowconfigure(1, weight=0)
        wrap.columnconfigure(0, weight=1)
        # 下段は PanedWindow だと Windows 環境で下ペインの高さが潰れ、詳細が画面外に落ちることがある。
        # 上段だけ伸縮し、下段は内容の自然高さを確保する。
        self.style.configure(
            "PlayerTrainSection.TLabel",
            background="#1d2129",
            foreground="#f3f5f7",
            font=("Yu Gothic UI", 10, "bold"),
        )
        self.style.configure(
            "PlayerTrainDetail.TLabel",
            background="#1d2129",
            foreground="#e8ecf0",
            font=("Yu Gothic UI", 10),
        )
        self.style.configure(
            "PlayerTrainHint.TLabel",
            background="#1d2129",
            foreground="#9aa3b2",
            font=("Yu Gothic UI", 9),
        )
        self.style.configure(
            "PlayerTrainNote.TLabel",
            background="#1d2129",
            foreground="#d6dbe3",
            font=("Yu Gothic UI", 9),
        )

        roster = list(getattr(self.team, "players", []) or [])
        roster = sorted(
            roster,
            key=lambda p: (str(getattr(p, "position", "SF")), -int(getattr(p, "ovr", 0)), str(getattr(p, "name", ""))),
        )
        if not roster:
            messagebox.showinfo("個別練習", "ロスターがありません。", parent=w)
            w.destroy()
            return

        drills: List[Tuple[str, str, str]] = [
            ("balanced", "バランス", "balanced"),
            ("dribble", "ドリブル練習", "playmaking"),
            ("rebound", "リバウンド練習", "defense"),
            ("stamina_run", "走り込み（スタミナ）", "physical"),
            ("shoot_form", "シュートフォーム", "shooting"),
            ("three_point", "3P特化", "shooting"),
            ("free_throw", "フリースロー", "shooting"),
            ("drive_finish", "ドライブ&フィニッシュ", "playmaking"),
            ("passing_read", "パス判断", "playmaking"),
            ("defense_footwork", "ディフェンスフットワーク", "defense"),
            ("strength", "筋力強化", "physical"),
            ("speed_agility", "スピード&アジリティ", "physical"),
            ("iq_film", "映像分析（IQ）", "iq_handling"),
        ]
        drill_label_to_key = {label: (key, focus) for key, label, focus in drills}
        key_to_drill_label = {key: label for key, label, _ in drills}
        # 個別練習に紐づく育成方針（Player.training_focus）の表示用。保存値の正は選手オブジェクト。
        _PLAYER_TRAINING_FOCUS_LABEL_JA: Dict[str, str] = {
            "balanced": "バランス",
            "shooting": "シュート",
            "playmaking": "プレーメイク",
            "defense": "ディフェンス",
            "physical": "フィジカル",
            "iq_handling": "IQ・判断",
        }

        def _focus_label_for_key(fk: str) -> str:
            k = str(fk or "balanced")
            return _PLAYER_TRAINING_FOCUS_LABEL_JA.get(k, k)

        from basketball_sim.systems.draft import build_draft_candidate_role_shape_label

        # 一覧の「現在練習」列のみ短縮（詳細・コンボは drills の正式名のまま）
        _DRILL_TREE_SHORT: Dict[str, str] = {
            "balanced": "バランス",
            "dribble": "ドリブル",
            "rebound": "リバ",
            "stamina_run": "走り込み",
            "shoot_form": "シュート",
            "three_point": "3P",
            "free_throw": "FT",
            "drive_finish": "ドライブ",
            "passing_read": "パス",
            "defense_footwork": "守備Fw",
            "strength": "筋力",
            "speed_agility": "俊敏",
            "iq_film": "IQ映像",
        }

        def _drill_label_for_key(dk: str) -> str:
            k = str(dk or "balanced")
            return key_to_drill_label.get(k, k)

        def _drill_short_for_tree(dk: str) -> str:
            k = str(dk or "balanced")
            if k in _DRILL_TREE_SHORT:
                return _DRILL_TREE_SHORT[k]
            full = _drill_label_for_key(k)
            return full if len(full) <= 6 else full[:6] + "…"

        def _role_shape_label(p: Any) -> str:
            try:
                return str(build_draft_candidate_role_shape_label(p))
            except Exception:
                return "—"

        def _row_values(p: Any) -> Tuple[Any, ...]:
            cd = str(getattr(p, "training_drill", "balanced") or "balanced")
            nat_lbl = jp_reg_display.get_player_nationality_bucket_label(p)
            return (
                str(getattr(p, "name", "-")),
                str(getattr(p, "position", "SF")),
                int(getattr(p, "ovr", 0)),
                str(getattr(p, "potential", "-")),
                int(getattr(p, "age", 0)),
                nat_lbl,
                _role_shape_label(p),
                _drill_short_for_tree(cd),
            )

        top_fr = ttk.Frame(wrap, style="Panel.TFrame", padding=(0, 0, 0, 4))
        top_fr.grid(row=0, column=0, sticky="nsew")
        bot_fr = ttk.Frame(wrap, style="Panel.TFrame", padding=(0, 8, 0, 0))
        bot_fr.grid(row=1, column=0, sticky="new")

        ttk.Label(
            top_fr,
            text="ロスター一覧（行を選ぶと下部で個別練習・能力を確認・変更）",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 4))

        tree_fr = ttk.Frame(top_fr)
        tree_fr.pack(fill="both", expand=True)
        tree_fr.rowconfigure(0, weight=1)
        tree_fr.columnconfigure(0, weight=1)
        cols = ("name", "pos", "ovr", "pot", "age", "nat", "role", "drill")
        tree = ttk.Treeview(
            tree_fr,
            columns=cols,
            show="headings",
            selectmode="browse",
            height=12,
        )
        vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree.heading("name", text="選手名")
        tree.heading("pos", text="POS")
        tree.heading("ovr", text="OVR")
        tree.heading("pot", text="POT")
        tree.heading("age", text="年齢")
        tree.heading("nat", text="国籍区分")
        tree.heading("role", text="タイプ")
        tree.heading("drill", text="個別練習")
        tree.column("name", width=140, stretch=True)
        tree.column("pos", width=40, stretch=False)
        tree.column("ovr", width=40, stretch=False)
        tree.column("pot", width=36, stretch=False)
        tree.column("age", width=40, stretch=False)
        tree.column("nat", width=88, stretch=False)
        tree.column("role", width=72, stretch=False)
        tree.column("drill", width=88, stretch=False)

        for i, p in enumerate(roster):
            tree.insert("", "end", iid=str(i), values=_row_values(p))

        ttk.Label(bot_fr, text="選択中の選手", style="PlayerTrainSection.TLabel").pack(anchor="w")
        head_var = tk.StringVar(value="")
        ttk.Label(
            bot_fr,
            textvariable=head_var,
            wraplength=820,
            style="PlayerTrainDetail.TLabel",
        ).pack(anchor="w", pady=(2, 2))
        ttk.Label(
            bot_fr,
            text="育成方針は、選んだ個別練習に合わせて自動設定されます。",
            style="PlayerTrainHint.TLabel",
        ).pack(anchor="w", pady=(0, 4))

        attrs_fr = tk.Frame(bot_fr, bg="#1d2129", highlightthickness=0)
        attrs_fr.pack(fill="x", pady=(0, 6))
        _ATTR_GRID: List[List[Tuple[str, str]]] = [
            [("3P", "three"), ("シュート", "shoot"), ("ドライブ", "drive")],
            [("パス", "passing"), ("ハンドリング", "handling"), ("守備", "defense")],
            [("リバウンド", "rebound"), ("FT", "ft"), ("スピード", "speed")],
            [("パワー", "power"), ("スタミナ", "stamina"), ("IQ", "iq")],
        ]
        attr_value_lbl: Dict[str, tk.Label] = {}
        _lbl_font = ("Yu Gothic UI", 9)
        _val_font = ("Yu Gothic UI", 9, "bold")
        for ri, row in enumerate(_ATTR_GRID):
            for ci, (ja_nm, attr_key) in enumerate(row):
                cell = tk.Frame(attrs_fr, bg="#1d2129")
                cell.grid(row=ri, column=ci, sticky="ew", padx=6, pady=3)
                attrs_fr.columnconfigure(ci, weight=1, uniform="attrcol")
                tk.Label(
                    cell,
                    text=f"{ja_nm}:",
                    width=11,
                    anchor="e",
                    bg="#1d2129",
                    fg="#8899aa",
                    font=_lbl_font,
                ).pack(side="left")
                vl = tk.Label(
                    cell,
                    text="—",
                    width=3,
                    anchor="e",
                    bg="#1d2129",
                    fg="#e8ecf0",
                    font=_val_font,
                )
                vl.pack(side="left", padx=(8, 0))
                attr_value_lbl[attr_key] = vl

        drill_row = ttk.Frame(bot_fr)
        drill_row.pack(fill="x", pady=(0, 4))
        ttk.Label(drill_row, text="個別練習に変更", style="PlayerTrainSection.TLabel").pack(
            side="left", padx=(0, 8)
        )
        drill_combo = ttk.Combobox(
            drill_row,
            state="readonly",
            values=[label for _, label, _ in drills],
            width=30,
        )
        drill_combo.pack(side="left")

        note_var = tk.StringVar(value="")
        ttk.Label(
            bot_fr,
            textvariable=note_var,
            style="PlayerTrainNote.TLabel",
            justify="left",
            wraplength=820,
        ).pack(fill="x", anchor="w", padx=8, pady=6)

        ttk.Label(
            bot_fr,
            text="「反映」でこの選手の個別練習と育成方針が更新されます。",
            style="PlayerTrainHint.TLabel",
        ).pack(fill="x", anchor="w", padx=8, pady=(0, 6))

        def _selected_player() -> Optional[Any]:
            sel = tree.selection()
            if not sel:
                return None
            try:
                idx = int(sel[0])
            except (TypeError, ValueError):
                return None
            if idx < 0 or idx >= len(roster):
                return None
            return roster[idx]

        def _fill_detail_for_player(p: Any) -> None:
            nm = str(getattr(p, "name", "-"))
            pos = str(getattr(p, "position", "SF"))
            ovr = int(getattr(p, "ovr", 0))
            pot = str(getattr(p, "potential", "-"))
            age = int(getattr(p, "age", 0))
            cd = str(getattr(p, "training_drill", "balanced") or "balanced")
            nat_l = jp_reg_display.get_player_nationality_bucket_label(p)
            role_l = _role_shape_label(p)
            cur_fk = str(getattr(p, "training_focus", "balanced") or "balanced")
            head_var.set(
                f"{nm}  /  {pos}  /  OVR {ovr}  /  POT {pot}  /  年齢 {age}  /  "
                f"{nat_l}  /  タイプ: {role_l}\n"
                f"現在：個別練習＝{_drill_label_for_key(cd)} / 育成方針＝{_focus_label_for_key(cur_fk)}"
            )
            for ak, lbl in attr_value_lbl.items():
                lbl.config(text=str(int(getattr(p, ak, 0) or 0)))
            drill_combo.set(_drill_label_for_key(cd))

        def _refresh_note(_event: Any = None) -> None:
            p = _selected_player()
            if p is None:
                note_var.set("一覧から選手を選んでください。")
                return
            key_focus = drill_label_to_key.get(drill_combo.get(), ("balanced", "balanced"))
            key = key_focus[0]
            cand_focus = key_focus[1]
            reason = self._player_drill_lock_reason(self.team, key)
            cand_lab = _drill_label_for_key(key)
            f_lab = _focus_label_for_key(cand_focus)
            if reason:
                note_var.set(f"選択中：{cand_lab} / 育成方針：{f_lab} / 未解放：{reason}")
            else:
                note_var.set(f"選択中：{cand_lab} / 育成方針：{f_lab} / 解放済み")

        def _on_tree_select(_event: Any = None) -> None:
            p = _selected_player()
            if p is None:
                return
            _fill_detail_for_player(p)
            _refresh_note()

        tree.bind("<<TreeviewSelect>>", _on_tree_select)
        drill_combo.bind("<<ComboboxSelected>>", _refresh_note)

        first_iid = "0"
        tree.selection_set(first_iid)
        tree.focus(first_iid)
        tree.see(first_iid)
        _fill_detail_for_player(roster[0])
        _refresh_note()

        def _apply() -> None:
            p = _selected_player()
            if p is None:
                messagebox.showwarning("個別練習", "一覧から選手を選んでください。", parent=w)
                return
            key, focus = drill_label_to_key.get(drill_combo.get(), ("", ""))
            if not key:
                messagebox.showerror("エラー", "練習を選択してください。", parent=w)
                return
            old_drill = str(getattr(p, "training_drill", "balanced") or "balanced")
            reason = self._player_drill_lock_reason(self.team, key)
            if reason:
                messagebox.showwarning("未解放", f"この練習は未解放です。\n{reason}", parent=w)
                return
            if old_drill != key:
                ok = messagebox.askokcancel(
                    "確認",
                    self._build_player_training_change_confirm_text(p, old_drill, key),
                    parent=w,
                )
                if not ok:
                    return
            setattr(p, "training_drill", key)
            setattr(p, "training_focus", focus)
            self._append_training_change_log(
                self.team,
                f"個別練習: {getattr(p, 'name', '-') } {old_drill} → {key}",
            )
            self._refresh_development_window()
            idx = roster.index(p)
            tree.item(str(idx), values=_row_values(p))
            _fill_detail_for_player(p)
            _refresh_note()
            messagebox.showinfo("完了", f"{getattr(p, 'name', '-') } の個別練習を更新しました。", parent=w)

        btn = ttk.Frame(bot_fr, style="Panel.TFrame")
        btn.pack(fill="x")
        ttk.Button(btn, text="反映", style="Primary.TButton", command=_apply).pack(side="left")
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right")

    def _on_reset_starting_lineup_gui(self, parent: tk.Misc) -> None:
        """カスタムスタメン解除（Team.clear_starting_lineup）。確認ダイアログ付き。"""
        if self.team is None:
            return
        try:
            ok = messagebox.askokcancel(
                "自動スタメンに戻す",
                "カスタムスタメン（手動設定）を解除し、チームの自動選出に戻しますか？\n\n"
                "※ 6thマンの設定はそのままです。",
                parent=parent,
            )
        except Exception:
            return
        if not ok:
            return
        clr = getattr(self.team, "clear_starting_lineup", None)
        if not callable(clr):
            messagebox.showinfo("未対応", "このチームではスタメン解除を実行できません。", parent=parent)
            return
        try:
            clr()
        except Exception as exc:
            messagebox.showerror("エラー", str(exc), parent=parent)
            return
        self.refresh()
        messagebox.showinfo("完了", "スタメンを自動選出に戻しました。", parent=parent)

    def _on_gm_cli_trade_fa_hint(self) -> None:
        """クラブ案内: トレード／FA の短い案内。可否ロックは ensure と同一。詳細は人事。"""
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        if not self.ensure_inseason_roster_moves_allowed(parent):
            return
        messagebox.showinfo(
            "トレード・FA の案内",
            "ここは案内用で、編集実行の窓ではありません。\n"
            "トレードは左メニュー「人事」を開き、上部の「トレード」ボタンから実行できます"
            "（1対1相当も同じ画面で人数を1対1に指定。現金・RB 付きも可）。\n"
            "同じトレードはシーズンメニュー「8. GMメニュー」→「10. トレード」（CLI）からも実行できます。\n"
            "インシーズンFA（1人）は人事から。条件・期限は「人事」ウィンドウ上部の案内を参照してください。\n\n"
            "（左メニュー「クラブ案内」は編集窓ではありません。）",
            parent=parent,
        )

    def _on_close_gm_window(self) -> None:
        w = getattr(self, "_gm_window", None)
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except Exception:
            pass
        self._gm_window = None

    def _open_gm_dashboard_window(self) -> None:
        """クラブ案内: 閲覧・案内・CLI ショートカット。正本は人事・戦術・経営・情報。"""
        if self.team is None:
            messagebox.showwarning(self.CLUB_GUIDE_MENU_LABEL, "チームが未接続です。", parent=self.root)
            return

        existing = getattr(self, "_gm_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                self._refresh_gm_dashboard_window()
                return
        except Exception:
            pass

        window = tk.Toplevel(self.root)
        window.title(f"{self.CLUB_GUIDE_MENU_LABEL} - {self._team_name()}")
        window.geometry("920x720")
        window.minsize(800, 560)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        hint_wrap = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        hint_wrap.pack(fill="x", pady=(0, 10))

        self._gm_hint_text = tk.Text(
            hint_wrap,
            height=7,
            wrap="word",
            bg="#1d2129",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            padx=8,
            pady=8,
        )
        self._gm_hint_text.pack(fill="x")

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)

        def _make_tab(title: str) -> tk.Text:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=6)
            nb.add(tab, text=title)
            txt = tk.Text(
                tab,
                wrap="none",
                bg="#222834",
                fg="#e8ecf0",
                insertbackground="#e8ecf0",
                font=("Consolas", 10),
                relief="flat",
                padx=10,
                pady=10,
            )
            vsb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
            hsb = ttk.Scrollbar(tab, orient="horizontal", command=txt.xview)
            txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            txt.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            tab.rowconfigure(0, weight=1)
            tab.columnconfigure(0, weight=1)
            return txt

        def _make_lineup_readonly_tab() -> None:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=10)
            nb.add(tab, text="スタメン・ベンチ")
            tab.rowconfigure(1, weight=1)
            tab.columnconfigure(0, weight=1)
            notice = ttk.Frame(tab, style="Panel.TFrame", padding=(0, 0, 0, 8))
            notice.grid(row=0, column=0, sticky="ew")
            ttk.Label(
                notice,
                text="先発・6th・ベンチ（Team）の編集は、左「戦術」→「ローテーション」→「2. 起用序列」から。",
                wraplength=820,
                font=("Yu Gothic UI", 10),
            ).pack(anchor="w")
            ttk.Label(
                notice,
                text="このタブは参照のみです（ターミナル「8. GMメニュー」からも同様の操作が可能な場合があります）。",
                wraplength=820,
                font=("Yu Gothic UI", 9),
            ).pack(anchor="w", pady=(6, 0))
            txt = tk.Text(
                tab,
                wrap="none",
                bg="#222834",
                fg="#e8ecf0",
                insertbackground="#e8ecf0",
                font=("Consolas", 10),
                relief="flat",
                padx=10,
                pady=10,
            )
            vsb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
            hsb = ttk.Scrollbar(tab, orient="horizontal", command=txt.xview)
            txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            txt.grid(row=1, column=0, sticky="nsew")
            vsb.grid(row=1, column=1, sticky="ns")
            hsb.grid(row=2, column=0, sticky="ew")
            self._gm_text_lineup = txt

        def _make_team_guidance_tab() -> None:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=10)
            nb.add(tab, text="チーム情報")
            tab.rowconfigure(1, weight=1)
            tab.columnconfigure(0, weight=1)
            notice = ttk.Frame(tab, style="Panel.TFrame", padding=(0, 0, 0, 8))
            notice.grid(row=0, column=0, sticky="ew")
            ttk.Label(
                notice,
                text="（閲覧・案内のみ／正本は情報「概要」）",
                font=("Yu Gothic UI", 10, "bold"),
            ).pack(anchor="w")
            txt = tk.Text(
                tab,
                wrap="word",
                bg="#222834",
                fg="#e8ecf0",
                insertbackground="#e8ecf0",
                font=("Yu Gothic UI", 10),
                relief="flat",
                padx=10,
                pady=10,
            )
            vsb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.grid(row=1, column=0, sticky="nsew")
            vsb.grid(row=1, column=1, sticky="ns")
            self._gm_text_team = txt

        _make_team_guidance_tab()

        def _make_cap_guidance_tab() -> None:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=10)
            nb.add(tab, text="サラリーキャップ")
            tab.rowconfigure(1, weight=1)
            tab.columnconfigure(0, weight=1)
            notice = ttk.Frame(tab, style="Panel.TFrame", padding=(0, 0, 0, 8))
            notice.grid(row=0, column=0, sticky="ew")
            ttk.Label(
                notice,
                text="（閲覧・案内のみ／正本は経営「財務サマリー」）",
                font=("Yu Gothic UI", 10, "bold"),
            ).pack(anchor="w")
            txt = tk.Text(
                tab,
                wrap="word",
                bg="#222834",
                fg="#e8ecf0",
                insertbackground="#e8ecf0",
                font=("Yu Gothic UI", 10),
                relief="flat",
                padx=10,
                pady=10,
            )
            vsb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.grid(row=1, column=0, sticky="nsew")
            vsb.grid(row=1, column=1, sticky="ns")
            self._gm_text_cap = txt

        _make_cap_guidance_tab()

        def _make_roster_guidance_tab() -> None:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=10)
            nb.add(tab, text="ロスター")
            tab.rowconfigure(1, weight=1)
            tab.columnconfigure(0, weight=1)
            notice = ttk.Frame(tab, style="Panel.TFrame", padding=(0, 0, 0, 8))
            notice.grid(row=0, column=0, sticky="ew")
            ttk.Label(
                notice,
                text="（閲覧・案内のみ／正本は人事「詳細ロスターを表示」）",
                font=("Yu Gothic UI", 10, "bold"),
            ).pack(anchor="w")
            txt = tk.Text(
                tab,
                wrap="word",
                bg="#222834",
                fg="#e8ecf0",
                insertbackground="#e8ecf0",
                font=("Yu Gothic UI", 10),
                relief="flat",
                padx=10,
                pady=10,
            )
            vsb = ttk.Scrollbar(tab, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.grid(row=1, column=0, sticky="nsew")
            vsb.grid(row=1, column=1, sticky="ns")
            self._gm_text_roster = txt

        _make_roster_guidance_tab()
        _make_lineup_readonly_tab()

        tab_st = ttk.Frame(nb, style="Root.TFrame", padding=12)
        nb.add(tab_st, text="戦術・HC・起用")
        tab_st.rowconfigure(1, weight=1)
        tab_st.columnconfigure(0, weight=1)
        notice_st = ttk.Frame(tab_st, style="Panel.TFrame", padding=(0, 0, 0, 8))
        notice_st.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            notice_st,
            text=(
                "編集は左「戦術」。プレイスタイル＝0〜7 の直接編集と「補助設定を開く（Team基本方針・HC）」。"
                "ローテーション＝起用プリセット・起用方針・起用序列の直接編集と「ローテ詳細」別窓（交代・目標出場など）。"
            ),
            wraplength=820,
            font=("Yu Gothic UI", 10),
        ).pack(anchor="w")
        ttk.Label(
            notice_st,
            text="このタブは閲覧のみ（編集は左「戦術」の該当枠のボタン）。"
            "人事の「タグ:」は能力・起用・成績などから付く自動役割タグです。",
            wraplength=820,
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(6, 0))
        self._gm_team_policy_text = tk.Text(
            tab_st,
            wrap="word",
            bg="#222834",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=10,
        )
        self._gm_team_policy_text.grid(row=1, column=0, sticky="nsew")
        st_vsb = ttk.Scrollbar(tab_st, orient="vertical", command=self._gm_team_policy_text.yview)
        st_vsb.grid(row=1, column=1, sticky="ns")
        self._gm_team_policy_text.configure(yscrollcommand=st_vsb.set)

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(
            bottom,
            text="トレード・FAの案内（人事の「トレード」／CLI）",
            style="Menu.TButton",
            command=self._on_gm_cli_trade_fa_hint,
        ).pack(side="left")
        gf = tk.Frame(bottom, bg="#1d2129")
        gf.pack(side="right")
        self._jpn_text_button(gf, "閉じる", self._on_close_gm_window, side="right")

        self._gm_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_gm_window)
        self._refresh_gm_dashboard_window()

    def _on_menu(self, key: str) -> None:
        if key == "日程":
            self.open_schedule_window()
            return
        callback = self.menu_callbacks.get(key)
        if callback is not None:
            callback()
            return
        if key == "人事":
            self.open_roster_window()
            return
        if key == self.CLUB_GUIDE_MENU_LABEL or key == "GM":
            cb = self.menu_callbacks.get(self.CLUB_GUIDE_MENU_LABEL) or self.menu_callbacks.get("GM")
            if cb is not None:
                cb()
                return
            self._open_gm_dashboard_window()
            return
        if key == "経営":
            self.open_finance_window()
            return
        if key == "戦術":
            self.open_strategy_window()
            return
        if key == "強化":
            self.open_development_window()
            return
        if key == "情報":
            self.open_information_window()
            return
        if key == "歴史":
            self.open_history_window()
            return
        if key == "システム":
            if self.on_system_menu is not None:
                self.on_system_menu(self)
                return
        messagebox.showinfo("未実装", f"{key} 画面はこれから接続します。")

    def _on_advance(self) -> None:
        if self.on_advance is not None:
            self.on_advance(self)
            self.refresh()
            return
        messagebox.showinfo("未接続", "次へ進む処理は main.py 接続時に追加します。")

    def _on_close_subwindow_hotkey(self, event: Any = None) -> str:
        """key_bindings.close_subwindow（既定 Esc）: フォーカスがある Toplevel を閉じる。"""
        try:
            w = self.root.focus_get()
        except Exception:
            return ""
        while w is not None and w != self.root:
            if isinstance(w, tk.Toplevel):
                try:
                    w.destroy()
                except tk.TclError:
                    pass
                return "break"
            w = getattr(w, "master", None)
        return ""

    # ------------------------------------------------------------------
    # Safe data access
    # ------------------------------------------------------------------
    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _first_non_empty(self, *values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], (), {}):
                return value
        return None

    def _get_current_date(self) -> Any:
        return self._first_non_empty(
            self._safe_get(self.season, "current_date", None),
            self._safe_get(self.season, "date", None),
            self._safe_get(self.team, "current_date", None),
            date.today(),
        )

    def _get_season_year(self) -> str:
        value = self._first_non_empty(
            self._safe_get(self.season, "season_year", None),
            self._safe_get(self.season, "year", None),
            self._safe_get(self.season, "current_year", None),
        )
        return str(value) if value is not None else "-"

    def _get_owner_trust_text(self) -> str:
        value = self._first_non_empty(
            self._safe_get(self.team, "owner_trust", None),
            self._safe_get(self.team, "owner_confidence", None),
            self._safe_get(self.team, "chairman_trust", None),
        )
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.1f}"
        return str(value)

    def _format_date(self, value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return str(value)

    def _format_money(self, value: Any) -> str:
        try:
            return format_money_yen_ja_readable(int(value))
        except Exception:
            return str(value)

    def _resolve_team_name(self, team_like: Any) -> str:
        if team_like is None:
            return "-"
        if isinstance(team_like, str):
            return team_like
        return str(self._safe_get(team_like, "name", "-"))

    def _team_name(self) -> str:
        return str(self._safe_get(self.team, "name", "自クラブ"))

    def _safe_int_text(self, value: Any) -> str:
        try:
            return str(int(value))
        except Exception:
            return str(value) if value not in (None, "") else "-"

    def _format_signed_money(self, value: Any) -> str:
        try:
            return format_signed_money_yen_ja_readable(int(value))
        except Exception:
            return str(value)

    # ------------------------------------------------------------------
    # Schedule / standings helpers
    # ------------------------------------------------------------------
    def _find_next_game(self) -> Any:
        candidates = self._first_non_empty(
            self._safe_get(self.season, "schedule", None),
            self._safe_get(self.season, "games", None),
            self._safe_get(self.season, "matches", None),
            self._safe_get(self.team, "schedule", None),
        )
        user_name = self._team_name()
        current_date = self._get_current_date()

        if candidates:
            for game in candidates:
                home_name = self._resolve_team_name(self._safe_get(game, "home_team", None))
                away_name = self._resolve_team_name(self._safe_get(game, "away_team", None))
                if user_name not in (home_name, away_name):
                    continue
                played = self._first_non_empty(
                    self._safe_get(game, "played", None),
                    self._safe_get(game, "is_played", None),
                    False,
                )
                if played:
                    continue
                game_date = self._first_non_empty(
                    self._safe_get(game, "date", None),
                    self._safe_get(game, "game_date", None),
                    self._safe_get(game, "scheduled_date", None),
                )
                if game_date is not None and str(game_date) < str(current_date):
                    continue
                return game

        return self._find_next_game_from_season_events()

    def _find_next_game_from_season_events(self) -> Any:
        """SeasonEvent（次ラウンド）から自チームの次戦を合成 dict で返す。"""
        if self.season is None or self.team is None:
            return None
        if bool(self._safe_get(self.season, "season_finished", False)):
            return None
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        nxt = cr + 1
        if nxt > tr:
            return None
        getter = getattr(self.season, "get_events_for_round", None)
        if not callable(getter):
            return None
        try:
            events = list(getter(nxt) or [])
        except Exception:
            return None
        user_name = self._team_name()
        for ev in events:
            if str(getattr(ev, "event_type", "") or "") != "game":
                continue
            ht = getattr(ev, "home_team", None)
            at = getattr(ev, "away_team", None)
            hn = self._resolve_team_name(ht)
            an = self._resolve_team_name(at)
            if user_name not in (hn, an):
                continue
            ct = str(getattr(ev, "competition_type", "") or "regular_season")
            cal = schedule_month_week_label(self.season, nxt)
            return {
                "home_team": ht,
                "away_team": at,
                "round_name": f"ラウンド{nxt}",
                "game_type": competition_display_name(ct),
                "schedule_date_hint": cal,
                "sim_round": nxt,
            }
        return None

    def _is_user_home(self, game: Any) -> bool:
        user_name = self._team_name()
        home_name = self._resolve_team_name(self._safe_get(game, "home_team", None))
        return user_name == home_name

    def _iter_league_teams(self) -> Iterable[Any]:
        # 1) season.leagues[league_level] があれば最優先（同リーグ順位の母集団）
        if self.season is not None and self.team is not None:
            leagues = self._safe_get(self.season, "leagues", None)
            level = self._safe_get(self.team, "league_level", None)
            try:
                if isinstance(leagues, dict) and level in leagues and leagues[level]:
                    return list(leagues[level])
            except Exception:
                pass

        # 2) 互換フィールド
        teams = self._first_non_empty(
            self._safe_get(self.season, "teams", None),
            self._safe_get(self.season, "league_teams", None),
            self._safe_get(self.team, "league_teams", None),
        )
        if teams:
            return list(teams)
        return [self.team] if self.team is not None else []

    def _compute_rank_text(self) -> str:
        team_name = self._team_name()
        teams = list(self._iter_league_teams())
        ranked = sorted(
            teams,
            key=lambda t: (
                -(int(self._safe_get(t, "regular_wins", 0) or 0)),
                int(self._safe_get(t, "regular_losses", 0) or 0),
                str(self._safe_get(t, "name", "")),
            ),
        )
        for idx, t in enumerate(ranked, start=1):
            if str(self._safe_get(t, "name", "")) == team_name:
                return f"{idx}位"
        return "-"

    def _lookup_team_rank(self, opponent_name: str) -> str:
        teams = list(self._iter_league_teams())
        ranked = sorted(
            teams,
            key=lambda t: (
                -(int(self._safe_get(t, "regular_wins", 0) or 0)),
                int(self._safe_get(t, "regular_losses", 0) or 0),
                str(self._safe_get(t, "name", "")),
            ),
        )
        for idx, t in enumerate(ranked, start=1):
            if str(self._safe_get(t, "name", "")) == str(opponent_name):
                return f"{idx}位"
        return "-"

    def _lookup_team_record(self, opponent_name: str) -> str:
        for t in self._iter_league_teams():
            if str(self._safe_get(t, "name", "")) == str(opponent_name):
                wins = int(self._safe_get(t, "regular_wins", 0) or 0)
                losses = int(self._safe_get(t, "regular_losses", 0) or 0)
                return f"{wins}勝{losses}敗"
        return "-"

    def _build_next_game_meaning(self, opponent_rank: str, venue_text: str) -> str:
        if opponent_rank in ("1位", "2位", "3位"):
            return f"上位相手との重要戦です。{venue_text}で勢いを作りたい試合です。"
        if venue_text == "ホーム":
            return "ホームで確実に取りたい一戦です。"
        return "アウェイで流れを引き寄せたい試合です。"

    def _build_next_game_compare(self, opponent_rank: str, opponent_record: str) -> str:
        return f"補足: 相手 {opponent_rank} / {opponent_record} を確認して準備を進めましょう。"

    # ------------------------------------------------------------------
    # Club summary helpers
    # ------------------------------------------------------------------
    def _build_recent5_text(self) -> str:
        history = self._extract_result_history()
        if not history:
            return "直近5試合: データなし"
        recent = history[-5:]
        mapped = ["○" if x in ("W", "WIN", 1, True) else "●" for x in recent]
        return f"直近5試合: {' '.join(mapped)}"

    def _build_streak_text(self) -> str:
        history = self._extract_result_history()
        if not history:
            return "-"
        last = history[-1]
        is_win = last in ("W", "WIN", 1, True)
        count = 0
        for item in reversed(history):
            item_is_win = item in ("W", "WIN", 1, True)
            if item_is_win == is_win:
                count += 1
            else:
                break
        return f"{count}連勝" if is_win else f"{count}連敗"

    def _extract_result_history(self) -> List[Any]:
        for attr in ("recent_results", "result_history", "match_results", "game_results"):
            value = self._safe_get(self.team, attr, None)
            if isinstance(value, list) and value:
                return value
        return []

    def _build_owner_progress_text(self) -> str:
        report_method = getattr(self.team, "get_owner_mission_report_text", None)
        if callable(report_method):
            try:
                text = str(report_method()).strip()
                first_line = text.splitlines()[0] if text else "オーナー目標: 情報なし"
                return first_line
            except Exception:
                pass

        mission = self._first_non_empty(
            self._safe_get(self.team, "owner_mission", None),
            self._safe_get(self.team, "mission", None),
        )
        progress = self._first_non_empty(
            self._safe_get(self.team, "owner_mission_progress", None),
            self._safe_get(self.team, "mission_progress", None),
        )
        if mission is None and progress is None:
            return "オーナー目標: 情報なし"
        if progress is None:
            return f"オーナー目標: {mission}"
        return f"オーナー目標: {mission}（進捗 {progress}）"

    def _build_team_comment(self, win_pct: float) -> str:
        if win_pct >= 0.700:
            return "チーム状況: 優勝争いを狙える好調さです。"
        if win_pct >= 0.500:
            return "チーム状況: 安定圏を維持できています。"
        return "チーム状況: 立て直しが必要な状況です。"

    def _build_club_supplement(self) -> str:
        money = self._safe_get(self.team, "money", None)
        trust = self._get_owner_trust_text()
        task_count = self._task_status_short()
        if money is not None:
            return f"補足: 資金 {self._format_money(money)} / オーナー信頼 {trust} / やること {task_count}"
        return f"補足: オーナー信頼 {trust} / やること {task_count}"

    # ------------------------------------------------------------------
    # Right column helpers
    # ------------------------------------------------------------------
    def _injured_players_on_user_team(self) -> List[Any]:
        if self.team is None:
            return []
        return [p for p in self._safe_get(self.team, "players", []) if self._is_injured_player(p)]

    def _format_injured_players_priority_line(self, injured: List[Any]) -> str:
        chunks: List[str] = []
        for p in injured[:5]:
            nm = str(self._safe_get(p, "name", "?")).strip() or "?"
            if len(nm) > 14:
                nm = nm[:13] + "…"
            gl = int(self._safe_get(p, "injury_games_left", 0) or 0)
            chunks.append(f"{nm}（残り約{gl}）")
        rest = max(0, len(injured) - len(chunks))
        tail = f"…ほか{rest}名" if rest else ""
        joined = "、".join(chunks) + tail
        return (
            f"[優先] 負傷者{len(injured)}名: {joined} "
            f"— 試合出場は想定しづらい状態です。左「戦術①」で先発・6th・目標出場／ローテを組み直し、「人事①」でロスターを確認。"
        )

    def _on_home_injury_detail_click(self) -> None:
        injured = self._injured_players_on_user_team()
        if not injured:
            messagebox.showinfo("負傷者", "現在、負傷中の選手はいません。")
            return
        win = tk.Toplevel(self.root)
        win.title("負傷者の詳細と行動ガイド")
        win.geometry("520x420")
        win.minsize(420, 320)
        win.configure(bg="#15171c")
        try:
            win.transient(self.root)
        except tk.TclError:
            pass

        header = tk.Label(
            win,
            text="いまの状態と推奨アクション",
            bg="#15171c",
            fg="#ffd38a",
            font=("Yu Gothic UI", 11, "bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=12, pady=(12, 6))

        guide = (
            "【状態】各選手は負傷中（モデル上 injury_games_left > 0）で、試合への登録・出場が制限されやすい状態です。\n\n"
            "【復帰の目安】「残り約N」はチームの試合が消化されるたびに減っていくカウンタです（現実の日数ではありません）。\n\n"
            "【推奨アクション】\n"
            "・左「戦術」→「ローテーション」→「2. 起用序列」でスタメン等。目標出場・戦術先発は「ローテ詳細を別窓で開く」から。\n"
            "・人事メニュー（左「人事」）… ロスター表で選手の状態を確認する。\n"
            "・交代方針や起用の補正は、ローテーション統合画面（起用プリセット・起用方針）やローテ詳細窓を。\n\n"
            "【選手一覧】\n"
        )
        player_lines: List[str] = []
        for p in injured:
            nm = str(self._safe_get(p, "name", "?")).strip() or "?"
            gl = int(self._safe_get(p, "injury_games_left", 0) or 0)
            pos = str(self._safe_get(p, "position", "") or "").strip()
            pos_s = f" {pos}" if pos else ""
            player_lines.append(f"・{nm}{pos_s} … 復帰までおおよそあと {gl}（進行ベース）")

        body = guide + "\n".join(player_lines)
        tw = scrolledtext.ScrolledText(
            win,
            wrap="word",
            bg="#222834",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
            font=("Yu Gothic UI", 10),
            relief="flat",
            height=16,
            padx=10,
            pady=8,
        )
        tw.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        tw.insert("1.0", body)
        tw.configure(state="disabled")

        bf = tk.Frame(win, bg="#15171c")
        bf.pack(fill="x", padx=12, pady=(0, 12))
        self._jpn_text_button(bf, "閉じる", win.destroy, side="right")

    def _refresh_menu_injury_badges(self) -> None:
        buttons = getattr(self, "_menu_buttons", None)
        if not isinstance(buttons, dict):
            return
        injured = bool(self._injured_players_on_user_team())
        suffix = " ①" if injured else ""
        for base, btn in buttons.items():
            try:
                if base in ("戦術", "人事"):
                    btn.configure(text=f"{base}{suffix}")
                else:
                    btn.configure(text=base)
            except tk.TclError:
                pass

    def _get_task_lines(self) -> List[str]:
        if self.external_tasks is not None:
            return list(self.external_tasks)

        urgent: List[str] = []
        normal: List[str] = []

        count = self._safe_get(self.team, "facility_upgrade_points", None)
        if isinstance(count, (int, float)) and int(count) > 0:
            urgent.append(f"[優先] 施設投資ポイント {int(count)} 点（経営メニューで使用可）")

        injured = self._injured_players_on_user_team()
        if injured:
            urgent.append(self._format_injured_players_priority_line(injured))

        sup = getattr(self, "_injury_autorepair_task_supplement", "") or ""
        if isinstance(sup, str) and sup.strip():
            normal.append(f"[任意] {sup.strip()}")

        fa_targets = self._safe_get(self.team, "fa_shortlist", None)
        if isinstance(fa_targets, list) and fa_targets:
            normal.append(
                f"[任意] FA候補 {len(fa_targets)} 件（詳細は左メニュー「人事」のトレード・FA 案内を参照）"
            )

        mission = self._safe_get(self.team, "owner_mission", None)
        if mission:
            normal.append(f"[任意] オーナーミッション: {mission}")

        out = urgent + normal
        if not out:
            return [self.HOME_TASKS_EMPTY_LINE]
        return out

    def _get_tasks(self) -> List[str]:
        """互換: 旧名。ホーム「今やること」行を返す。"""
        return self._get_task_lines()

    def _get_news_items(self) -> List[str]:
        if self.external_news_items is not None:
            return list(self.external_news_items)

        team_name = self._team_name()
        rank = self._compute_rank_text()
        wins = self._safe_get(self.team, "regular_wins", 0)
        losses = self._safe_get(self.team, "regular_losses", 0)
        return [
            f"{team_name} は現在 {rank}、戦績は {wins}勝{losses}敗",
            "リーグ各地でロスター争いが活発化しています",
            "次節へ向けてコンディション管理が注目されています",
            "オーナー評価と財務バランスの両立が今季の鍵です",
        ]

    def _is_injured_player(self, player: Any) -> bool:
        method = getattr(player, "is_injured", None)
        if callable(method):
            try:
                return bool(method())
            except Exception:
                return False
        return bool(self._safe_get(player, "injured", False))


def wrap_menu_callback_with_inseason_transaction_guard(
    view: MainMenuView,
    callback: MenuCallback,
    parent: Optional[Any] = None,
) -> MenuCallback:
    """
    メニューからトレード／インシーズンFA 相当の処理を呼ぶとき用。
    CLI の season_transaction_rules と同じガードを通してから callback を実行する。
    """
    def _wrapped() -> None:
        if not view.ensure_inseason_roster_moves_allowed(parent):
            return
        callback()
    return _wrapped


def launch_main_menu(
    team: Any = None,
    season: Any = None,
    on_advance: Optional[AdvanceCallback] = None,
    menu_callbacks: Optional[Dict[str, MenuCallback]] = None,
    news_items: Optional[List[str]] = None,
    tasks: Optional[List[str]] = None,
    user_settings: Optional[Dict[str, Any]] = None,
    on_system_menu: Optional[SystemMenuCallback] = None,
    on_main_window_close: Optional[Callable[[], bool]] = None,
    advance_primary_ui_fn: Optional[Callable[[], Tuple[str, str]]] = None,
) -> MainMenuView:
    """
    Convenience launcher used by future main.py wiring.
    on_advance は MainMenuView インスタンスを引数に取る（1 ラウンド進行・オフ開始など）。
    advance_primary_ui_fn があれば (主ボタン文言, 終了時ヒント) を返し、オフ済みなどの分岐に使う。
    トレード／インシーズンFA 相当の menu_callbacks は
    wrap_menu_callback_with_inseason_transaction_guard で包むこと。
    """
    view = MainMenuView(
        team=team,
        season=season,
        on_advance=on_advance,
        menu_callbacks=menu_callbacks,
        news_items=news_items,
        tasks=tasks,
        user_settings=user_settings,
        on_system_menu=on_system_menu,
        on_main_window_close=on_main_window_close,
        advance_primary_ui_fn=advance_primary_ui_fn,
    )
    view.run()
    return view


if __name__ == "__main__":
    class _DummyTeam:
        def __init__(self) -> None:
            self.name = "徳島ブルーオーシャンズ"
            self.league_level = 1
            self.regular_wins = 18
            self.regular_losses = 10
            self.money = 7250000
            self.owner_trust = 72
            self.owner_mission = "プレーオフ進出"
            self.owner_mission_progress = "順調"
            self.recent_results = ["W", "L", "W", "W", "W"]
            self.players = []
            self.facility_upgrade_points = 2

        def get_owner_mission_report_text(self) -> str:
            return "オーナー目標: プレーオフ進出（進捗: 順調）"

    class _DummyOpponent:
        def __init__(self, name: str, wins: int, losses: int) -> None:
            self.name = name
            self.regular_wins = wins
            self.regular_losses = losses

    class _DummySeason:
        def __init__(self, team: Any) -> None:
            self.current_date = "2026-10-18"
            self.season_year = 2026
            self.current_round = 5
            self.total_rounds = 30
            self.season_finished = False
            self.phase = "regular_season"
            self.game_count = 20
            self.teams = [
                _DummyOpponent("東京フェニックス", 22, 7),
                team,
                _DummyOpponent("大阪ライトニング", 16, 12),
                _DummyOpponent("仙台クラウンズ", 14, 14),
            ]
            self.schedule = [
                {
                    "date": "2026-10-20",
                    "round_name": "第29節",
                    "game_type": "リーグ戦",
                    "home_team": team.name,
                    "away_team": "東京フェニックス",
                    "played": False,
                }
            ]

    dummy_team = _DummyTeam()
    dummy_season = _DummySeason(dummy_team)
    launch_main_menu(team=dummy_team, season=dummy_season)
