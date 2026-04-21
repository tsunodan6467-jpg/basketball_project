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
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

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
    STARTER_POSITIONS,
    ensure_team_tactics_on_team,
    get_default_team_tactics,
    get_safe_team_tactics,
    normalize_team_tactics,
)
from basketball_sim.systems.facility_investment import (
    FACILITY_LABELS,
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
    get_facility_upgrade_cost,
)
from basketball_sim.systems.contract_logic import (
    MAX_CONTRACT_YEARS_DEFAULT,
    apply_contract_extension,
    is_draft_rookie_contract_active,
)
from basketball_sim.systems.roster_fa_release import (
    apply_release_player_to_fa,
    postcheck_release_player_to_fa_season,
    precheck_release_player_to_fa,
)
from basketball_sim.systems.sponsor_management import (
    MAIN_SPONSOR_TYPES,
    commit_main_sponsor_contract,
    ensure_sponsor_management_on_team,
    format_sponsor_history_lines,
    label_for_main_sponsor_type,
)
from basketball_sim.systems.pr_campaign_management import (
    PR_CAMPAIGNS,
    commit_pr_campaign,
    format_pr_history_lines,
    format_pr_status_line,
    resolve_pr_round_context,
)
from basketball_sim.systems.merchandise_management import (
    ADVANCE_COST,
    MERCH_PRODUCTS,
    advance_merchandise_phase,
    ensure_merchandise_on_team,
    estimate_dummy_merch_sales_lines,
    format_merchandise_history_lines,
    format_merchandise_row_display,
    get_merchandise_item,
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

        debug_skip_cb = self.menu_callbacks.get("DEBUG_SKIP_TO_OFFSEASON")
        self.debug_skip_button: Optional[ttk.Button] = None
        if callable(debug_skip_cb):
            self.debug_skip_button = ttk.Button(
                advance_wrap,
                text="デバッグ: オフシーズンまで飛ばす",
                style="DebugSkip.TButton",
                command=debug_skip_cb,
            )
            self.debug_skip_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))

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
            "・選手のみの 1対1 トレードは、本ウィンドウの「1対1トレード（選手のみ）」からも実行できます"
            "（インシーズンの可否は CLI のトレードと同一ルール）。\n"
            "・multi は人事の「multi（複数人）」で複数選手＋現金・RB（自分→相手）まで可能（CLI multi と同じ実行経路）。\n"
            "CLI のトレードメニューからも同様の multi が実行できます（シーズンメニュー「8. GMメニュー」→「10. トレード」）。\n"
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
            "・multi は人事で「multi（複数人）」または CLI（シーズンメニュー「8. GMメニュー」→「10. トレード」）。\n"
            "・レギュラー中のトレード期限切れ後は、CLI のトレードもブロックされます（上部の可否表示と同じルール）。\n\n"
            "【その他】施設投資などもターミナルの「8. GMメニュー」から行います。"
        )

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
        """人事・ロスター: トレード／FA 案内（正本）、表、詳細ロスター。＋1年延長・FA 解除は条件付き。"""
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

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.roster_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.roster_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        self.roster_jp_header_var = tk.StringVar(value="")
        tk.Label(
            outer,
            textvariable=self.roster_jp_header_var,
            bg="#1d2129",
            fg="#c8d0dc",
            justify="left",
            anchor="w",
            font=("Yu Gothic UI", 9),
            padx=14,
            pady=4,
            wraplength=900,
        ).pack(fill="x", pady=(0, 6))

        trade_fa_wrap = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 8))
        trade_fa_wrap.pack(fill="x", pady=(0, 8))
        ttk.Label(
            trade_fa_wrap,
            text="トレード・FA（表で選手選択→解除。1対1／multi（複数人＋現金・RB可）／インシーズンFAは横ボタン）",
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x", anchor="w", pady=(0, 6))
        tf_btn_row = ttk.Frame(trade_fa_wrap, style="Panel.TFrame")
        tf_btn_row.pack(fill="x", anchor="w", pady=(0, 6))
        self._jpn_text_button(
            tf_btn_row,
            "1対1トレード（選手のみ）",
            self._on_roster_one_for_one_trade,
            side="left",
        )
        self._jpn_text_button(
            tf_btn_row,
            "multi（複数人）",
            self._on_roster_multi_trade_players_only,
            side="left",
            padx=(10, 0),
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
        tf_row = ttk.Frame(trade_fa_wrap, style="Panel.TFrame")
        tf_row.pack(fill="both", expand=False)
        tf_row.columnconfigure(0, weight=1)
        tf_row.rowconfigure(0, weight=1)
        self.roster_trade_fa_text = tk.Text(
            tf_row,
            wrap="word",
            height=2,
            bg="#1d2129",
            fg="#d6dbe3",
            insertbackground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            relief="flat",
            padx=8,
            pady=8,
        )
        tf_vsb = ttk.Scrollbar(tf_row, orient="vertical", command=self.roster_trade_fa_text.yview)
        self.roster_trade_fa_text.configure(yscrollcommand=tf_vsb.set)
        self.roster_trade_fa_text.grid(row=0, column=0, sticky="nsew")
        tf_vsb.grid(row=0, column=1, sticky="ns")

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

        roster_paned = ttk.Panedwindow(outer, orient="vertical")
        roster_paned.pack(fill="both", expand=True)

        tree_wrap = ttk.Frame(roster_paned, style="Panel.TFrame", padding=10)
        roster_paned.add(tree_wrap, weight=10)

        self.roster_tree = ttk.Treeview(
            tree_wrap,
            columns=columns,
            show="headings",
            height=16,
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
            "role": 110,
            "name": 170,
            "pos": 70,
            "ovr": 70,
            "pot": 70,
            "age": 70,
            "nat_bucket": 100,
            "fatigue": 70,
            "morale": 70,
            "salary": 130,
            "years": 80,
        }

        for key in columns:
            self.roster_tree.heading(key, text=headings[key])
            anchor = "center" if key not in ("name", "nat_bucket") else "w"
            self.roster_tree.column(key, width=widths[key], anchor=anchor, stretch=(key == "name"))

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.roster_tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.roster_tree.xview)
        self.roster_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.roster_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)

        detail_outer = ttk.Frame(roster_paned, style="Panel.TFrame", padding=(10, 6, 10, 10))
        roster_paned.add(detail_outer, weight=2)
        try:
            roster_paned.pane(tree_wrap, minsize=180)
            roster_paned.pane(detail_outer, minsize=96)
        except tk.TclError:
            pass
        detail_outer.columnconfigure(0, weight=1)
        ttk.Label(
            detail_outer,
            text="詳細ロスター（テキスト一覧・閲覧専用）",
            style="TopBar.TLabel",
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(
            detail_outer,
            text="表と同一ロスターです。並び・体裁は GM 表示ルール（docs/GM_ROSTER_DISPLAY_RULES.md）に沿います。",
            wraplength=900,
            font=("Yu Gothic UI", 9),
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        text_host = ttk.Frame(detail_outer, style="Panel.TFrame", padding=0)
        text_host.grid(row=2, column=0, columnspan=2, sticky="nsew")
        detail_outer.rowconfigure(2, weight=1)
        text_host.rowconfigure(0, weight=1)
        text_host.columnconfigure(0, weight=1)
        self.roster_detail_text = tk.Text(
            text_host,
            wrap="none",
            height=3,
            bg="#222834",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=8,
        )
        rdt_vsb = ttk.Scrollbar(text_host, orient="vertical", command=self.roster_detail_text.yview)
        rdt_hsb = ttk.Scrollbar(text_host, orient="horizontal", command=self.roster_detail_text.xview)
        self.roster_detail_text.configure(yscrollcommand=rdt_vsb.set, xscrollcommand=rdt_hsb.set)
        self.roster_detail_text.grid(row=0, column=0, sticky="nsew")
        rdt_vsb.grid(row=0, column=1, sticky="ns")
        rdt_hsb.grid(row=1, column=0, sticky="ew")

        self._roster_vert_split_done = False

        def _apply_roster_vertical_split(_event: Any = None) -> None:
            if self._roster_vert_split_done:
                return
            try:
                ph = int(roster_paned.winfo_height())
                if ph < 200:
                    return
                roster_paned.sashpos(0, max(160, int(ph * 0.82)))
                self._roster_vert_split_done = True
            except tk.TclError:
                pass

        roster_paned.bind("<Map>", _apply_roster_vertical_split)
        window.after_idle(_apply_roster_vertical_split)
        window.after(200, _apply_roster_vertical_split)

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

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
        btn_row.pack(fill="x", pady=(8, 0))
        self._jpn_text_button(
            btn_row,
            "＋1年延長",
            self._on_roster_extend_one_year_selected,
            side="left",
        )
        self._jpn_text_button(
            btn_row,
            "契約解除（FA送り）",
            self._on_roster_release_selected,
            side="left",
            padx=(8, 0),
        )
        self._jpn_text_button(btn_row, "閉じる", self._on_close_roster_window, side="right")

        self._roster_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_roster_window)
        self._refresh_roster_window()

    def _on_close_roster_window(self) -> None:
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
        """人事ウィンドウから GUI 1対1トレード（選手のみ）。評価・実行は main / TradeSystem の既存経路。"""
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
        top.title("1対1トレード（選手のみ）")
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
            text="選手のみの 1 対 1 です。現金・RB を伴うトレードは CLI の multi 導線を使ってください。",
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
        """人事から multi 第1弾: 複数選手のみ（現金・RB なし）。評価・実行は `TradeSystem` 既存経路。"""
        parent = getattr(self, "_roster_window", None) or self.root
        if self.team is None:
            messagebox.showwarning("トレード", "チームが未接続です。", parent=parent)
            return
        if self.season is None:
            messagebox.showwarning(
                "トレード",
                "シーズン未接続のため FA プールを参照できず、multi トレードを実行できません。",
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
                "FA プールが未初期化のため multi トレードを実行できません。",
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
        from basketball_sim.systems.trade_logic import MultiTradeOffer, TradeSystem

        user_team = self.team
        top = tk.Toplevel(parent)
        top.title("multi トレード（複数人＋現金・RB）")
        top.configure(bg="#15171c")
        try:
            top.transient(parent)
        except Exception:
            pass
        top.geometry("640x480")
        top.minsize(520, 400)

        outer = ttk.Frame(top, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=(
                "複数選手の入替に加え、自分→相手への現金・RB（ルーキー予算）移転を指定できます。"
                "評価・成立は `TradeSystem` の multi 経路（CLI のトレード提案と同系）です。"
            ),
            wraplength=600,
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
        tk.Label(
            money_rb_frame,
            text="現金・RB はいずれも「自分のクラブ → 相手クラブ」への移転です（CLI STEP 5/6 と同趣旨）。",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 9),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 10))
        cash_limit_var = tk.StringVar(value="")
        rb_limit_var = tk.StringVar(value="")
        tk.Label(
            money_rb_frame,
            textvariable=cash_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(0, 4))
        row_cash = tk.Frame(money_rb_frame, bg="#222834")
        row_cash.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_cash,
            text="現金（円）:",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10),
            width=14,
            anchor="w",
        ).pack(side="left")
        cash_entry = tk.Entry(
            row_cash,
            width=18,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
        )
        cash_entry.pack(side="left", padx=(0, 8))
        tk.Label(
            row_cash,
            text="カンマ可・空欄は0",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")
        tk.Label(
            money_rb_frame,
            textvariable=rb_limit_var,
            bg="#222834",
            fg="#c8d0dc",
            font=("Yu Gothic UI", 9),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))
        row_rb = tk.Frame(money_rb_frame, bg="#222834")
        row_rb.pack(fill="x", padx=8, pady=4)
        tk.Label(
            row_rb,
            text="RB 移転:",
            bg="#222834",
            fg="#e8ecf0",
            font=("Yu Gothic UI", 10),
            width=14,
            anchor="w",
        ).pack(side="left")
        rb_entry = tk.Entry(
            row_rb,
            width=18,
            font=("Yu Gothic UI", 10),
            bg="#2a3140",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
        )
        rb_entry.pack(side="left", padx=(0, 8))
        tk.Label(
            row_rb,
            text="空欄は0",
            bg="#222834",
            fg="#8899aa",
            font=("Yu Gothic UI", 8),
        ).pack(side="left")
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
            "rookie_budget_a_to_b": 0,
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
            rb_amt = int(state.get("rookie_budget_a_to_b", 0) or 0)
            offer = MultiTradeOffer(
                team_a_gives_players=user_gives,
                team_a_receives_players=ai_receives,
                cash_a_to_b=cash_amt,
                rookie_budget_a_to_b=rb_amt,
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
            if not messagebox.askyesno(
                "トレード成立",
                "この内容で multi トレードを成立させますか？",
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
                if rb_amt > 0:
                    pay_lines += f"\nRB（自分→相手）: {format_money_yen_ja_readable(rb_amt)}"
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
                max_cash = max(0, int(getattr(user_team, "money", 0) or 0))
                max_rb = max(0, int(getattr(user_team, "rookie_budget_remaining", 0) or 0))
                cash_limit_var.set(
                    f"現金: 0〜{format_money_yen_ja_readable(max_cash)}（空欄は送金なし）"
                )
                rb_limit_var.set(f"RB: 0〜{format_money_yen_ja_readable(max_rb)}（空欄は移転なし）")
                cash_entry.delete(0, tk.END)
                rb_entry.delete(0, tk.END)
                state["step"] = 4
                set_center_pane("cash_rb")
                hint_var.set("現金・RB を入力し、「評価する」を押してください（空欄は 0）。")
                next_caption_var.set("評価する")
                return
            if step == 4:
                max_cash = max(0, int(getattr(user_team, "money", 0) or 0))
                max_rb = max(0, int(getattr(user_team, "rookie_budget_remaining", 0) or 0))
                ok_c, cash_v, msg_c = bs_main.parse_multi_trade_side_payment(
                    cash_entry.get(),
                    max_cash,
                    is_cash=True,
                )
                if not ok_c:
                    messagebox.showwarning("トレード", msg_c, parent=top)
                    return
                ok_r, rb_v, msg_r = bs_main.parse_multi_trade_side_payment(
                    rb_entry.get(),
                    max_rb,
                    is_cash=False,
                )
                if not ok_r:
                    messagebox.showwarning("トレード", msg_r, parent=top)
                    return
                state["cash_a_to_b"] = cash_v
                state["rookie_budget_a_to_b"] = rb_v
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

        self.roster_header_var.set(
            f"{team_name} ロスター一覧    人数: {count}    平均OVR: {avg_ovr:.1f}"
        )
        jp_h = getattr(self, "roster_jp_header_var", None)
        if jp_h is not None and self.team is not None:
            try:
                jp_h.set(jp_reg_display.format_roster_window_jp_header(self.season, self.team))
            except Exception:
                jp_h.set("")
        unlocked = self.inseason_roster_moves_allowed()
        lock_line_release = (
            "契約解除: 実行可（要選手選択）。"
            if unlocked
            else "契約解除: レギュラー後半はロック（トレード／インシーズンFA と同じ期限）。"
        )
        self.roster_hint_var.set(
            "【詳細ロスター】下のペインは全文テキスト一覧（閲覧専用）。表と同一メンバーで、並びは GM 表示ルールに準拠します。\n"
            "並び: ポジション順(PG→C)→同ポジ内OVR降順（docs/GM_ROSTER_DISPLAY_RULES.md と共通）。"
            "先発・6th・控え番号は Team の起用ロジックに基づきます。\n"
            "【今できる操作（人事画面）】閲覧。＋1年延長（年俸据え置き・残年数が 1 年以上かつ"
            f" {MAX_CONTRACT_YEARS_DEFAULT} 年未満のときのみ）。{lock_line_release}\n"
            "【トレード】1対1・multi（複数人・現金・RB）はウィンドウ上部のボタンから。"
            " CLI からも同様のトレードメニューで実行できます（「8. GMメニュー」→「10. トレード」）。"
            "【インシーズンFA】FA プールから 1 人だけ獲得する場合は「インシーズンFA（1人）」ボタンから。"
            "期限はトレードと同じルールです（上部の案内を参照）。\n"
            "【契約解除（FA送り）】表で選手を選び、上部トレード行または下部の同ボタンから実行（最低人数・ロックは上記）。"
        )

        trade_txt = getattr(self, "roster_trade_fa_text", None)
        if trade_txt is not None:
            self._gm_set_readonly_text(trade_txt, self._format_hr_trade_fa_guidance_text())

        detail_txt = getattr(self, "roster_detail_text", None)
        if detail_txt is not None:
            if self.team is not None:
                self._gm_set_readonly_text(detail_txt, format_gm_roster_text(self.team))
            else:
                self._gm_set_readonly_text(detail_txt, "チームが未接続です。")

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
        window.geometry("980x1100")
        window.minsize(880, 800)
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
                "【経営メニュー】この画面は、現状確認・一部投資操作・案内を行う画面です。"
                "財務/施設/オーナーの計算・評価の正本は共通ロジック側で処理されます。"
                "シーズン収支の正本反映はオフシーズンの財務締めで行われます。"
                "（施設投資など一部支出は実行時に反映されます）"
                "財務サマリー・キャップ閲覧、施設投資、オーナー方針、"
                "収支の詳細レポート、スポンサー・広報・グッズ開発をまとめて扱う画面です。"
                "下にスクロールすると各ブロックが続きます。"
                "開いた時点で各欄に現在値、または「履歴なし・未実行・未設定・対象なし」に相当する説明が入ります。"
                "操作で増えるのは主に履歴や確定メッセージです。"
                "画面上部の「現況ダッシュボード」に、財務・施設・オーナー・直近施策の要約を常時表示します。"
            ),
            wraplength=1020,
            font=("Yu Gothic UI", 10),
            justify="left",
        ).pack(anchor="w")

        dash_board = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 8))
        dash_board.pack(fill="x", pady=(0, 10))
        ttk.Label(
            dash_board,
            text="現況ダッシュボード（財務 / 施設 / オーナー / 直近施策）",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        self._management_dashboard_text = tk.Text(
            dash_board,
            height=20,
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
        self._management_dashboard_text.pack(fill="both", expand=False)
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

        fin_scroll_wrap = ttk.Frame(outer, style="Root.TFrame")
        fin_scroll_wrap.pack(fill="both", expand=True)

        fin_canvas = tk.Canvas(
            fin_scroll_wrap,
            bg="#15171c",
            highlightthickness=0,
        )
        fin_vsb = ttk.Scrollbar(fin_scroll_wrap, orient="vertical", command=fin_canvas.yview)
        fin_canvas.configure(yscrollcommand=fin_vsb.set)

        content = ttk.Frame(fin_canvas, style="Root.TFrame")
        fin_canvas_win = fin_canvas.create_window((0, 0), window=content, anchor="nw")

        def _finance_scrollregion(_event: Any = None) -> None:
            fin_canvas.update_idletasks()
            bbox = fin_canvas.bbox("all")
            if bbox:
                fin_canvas.configure(scrollregion=bbox)

        def _finance_canvas_inner_width(event: Any) -> None:
            try:
                fin_canvas.itemconfigure(fin_canvas_win, width=event.width)
            except tk.TclError:
                pass

        content.bind("<Configure>", lambda _e: _finance_scrollregion())
        fin_canvas.bind("<Configure>", _finance_canvas_inner_width)

        def _finance_hub_mousewheel(event: Any) -> None:
            if getattr(event, "delta", 0):
                fin_canvas.yview_scroll(int(-event.delta / 120), "units")

        window.bind("<MouseWheel>", _finance_hub_mousewheel)
        window.bind("<Button-4>", lambda _e: fin_canvas.yview_scroll(-1, "units"))
        window.bind("<Button-5>", lambda _e: fin_canvas.yview_scroll(1, "units"))

        fin_canvas.pack(side="left", fill="both", expand=True)
        fin_vsb.pack(side="right", fill="y")
        self._finance_scroll_canvas = fin_canvas

        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=0)
        content.rowconfigure(1, weight=0)
        content.rowconfigure(2, weight=0)
        content.rowconfigure(3, weight=0)
        content.rowconfigure(4, weight=0)

        self.finance_summary_panel = self._create_panel(content, "財務サマリー")
        self.finance_summary_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        self.facility_panel = self._create_panel(content, "施設・基盤")
        self.facility_panel.grid(row=0, column=1, sticky="nsew", pady=(0, 10))

        self.owner_panel = self._create_panel(content, "オーナー・方針")
        self.owner_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.finance_report_panel = self._create_panel(content, "詳細レポート")
        self.finance_report_panel.grid(row=1, column=1, sticky="nsew")

        fin_sum_inner = self._resolve_content_parent(self.finance_summary_panel)
        ttk.Label(
            fin_sum_inner,
            text="資金・今季（記録）シーズン中入金・前季収支・人件費・状態の要約（詳細は下の各欄）",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self.finance_summary_lines = self._make_line_vars(self.finance_summary_panel, 6)
        ttk.Separator(fin_sum_inner, orient="horizontal").pack(fill="x", pady=(14, 8))
        ttk.Label(
            fin_sum_inner,
            text="サラリーキャップ（閲覧）",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            fin_sum_inner,
            text="リーグキャップ・ペイロール・契約の読み取り専用です（編集は人事・CLI等の従来導線）。"
            "収支の本格締めはオフシーズン処理で反映されます。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self._finance_cap_text = scrolledtext.ScrolledText(
            fin_sum_inner,
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
        self._finance_cap_text.pack(fill="both", expand=False, pady=(0, 4))
        self._finance_cap_text.configure(state="disabled")

        ttk.Separator(fin_sum_inner, orient="horizontal").pack(fill="x", pady=(14, 8))
        ttk.Label(
            fin_sum_inner,
            text="シーズン中収益（本シーズン・記録）",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            fin_sum_inner,
            text="ラウンドごとのリーグ分配等の入金メモ（所持金には反映済み。年次の財務正本・詳細レポートとは別枠）。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self._finance_inseason_log_text = scrolledtext.ScrolledText(
            fin_sum_inner,
            height=8,
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
        self._finance_inseason_log_text.pack(fill="both", expand=False, pady=(0, 4))
        self._finance_inseason_log_text.configure(state="disabled")
        ttk.Label(
            fin_sum_inner,
            text="※ 広報・グッズの支出詳細は、経営メニュー内の各パネル履歴を参照してください。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        fac_content = self._resolve_content_parent(self.facility_panel)
        ttk.Label(
            fac_content,
            text="稼働状態・レベル概要・次投資の目安・市場／ファン指標（下のボタンで段階強化）。"
            "投資時に費用が反映され、施設レベルと関連指標が更新されます。",
            font=("Yu Gothic UI", 9),
        ).pack(anchor="w", pady=(0, 6))
        self.facility_lines = self._make_line_vars(self.facility_panel, 6)
        btn_row = ttk.Frame(fac_content, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(12, 0))
        self._facility_upgrade_buttons: Dict[str, ttk.Button] = {}
        self._facility_preview_vars: Dict[str, tk.StringVar] = {}
        for i, fk in enumerate(FACILITY_ORDER):
            label = FACILITY_LABELS.get(fk, fk)
            cell = ttk.Frame(btn_row, style="Card.TFrame")
            cell.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            b = ttk.Button(
                cell,
                text=f"{label}を強化",
                style="Menu.TButton",
                command=lambda k=fk: self._on_facility_upgrade_click(k),
            )
            b.pack(fill="x")
            self._facility_upgrade_buttons[fk] = b
            pv = tk.StringVar(value="")
            self._facility_preview_vars[fk] = pv
            tk.Label(
                cell,
                textvariable=pv,
                bg="#222834",
                fg="#9aa4b2",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=300,
            ).pack(fill="x", pady=(4, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
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

        self.sponsor_panel = self._create_panel(content, "スポンサー（メイン契約）")
        self.sponsor_panel.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        sponsor_inner = self._resolve_content_parent(self.sponsor_panel)
        self._sponsor_status_var = tk.StringVar(value="")
        tk.Label(
            sponsor_inner,
            text="メインスポンサー契約の種類を選び「反映」で確定します。下は契約変更の直近履歴です。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            sponsor_inner,
            textvariable=self._sponsor_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 11),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))
        sponsor_row = ttk.Frame(sponsor_inner, style="Card.TFrame")
        sponsor_row.pack(fill="x", pady=(0, 8))
        self._sponsor_type_ids = [str(x["id"]) for x in MAIN_SPONSOR_TYPES]
        combo_labels = [str(x["label"]) for x in MAIN_SPONSOR_TYPES]
        self._sponsor_combo = ttk.Combobox(
            sponsor_row,
            values=combo_labels,
            state="readonly",
            width=36,
            font=("Yu Gothic UI", 10),
        )
        self._sponsor_combo.pack(side="left", padx=(0, 10))
        try:
            self._sponsor_combo.current(0)
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
            text="契約変更履歴（直近）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10),
        ).pack(fill="x", pady=(4, 2))
        self._sponsor_history_text = scrolledtext.ScrolledText(
            sponsor_inner,
            height=5,
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

        self.pr_panel = self._create_panel(content, "広報・ファン施策")
        self.pr_panel.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        pr_inner = self._resolve_content_parent(self.pr_panel)
        self._pr_status_var = tk.StringVar(value="")
        tk.Label(
            pr_inner,
            text="シーズン中の実行回数に上限があるファン向け施策です。下は実行履歴です。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            pr_inner,
            textvariable=self._pr_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 11),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))
        self._pr_remaining_var = tk.StringVar(value="")
        tk.Label(
            pr_inner,
            textvariable=self._pr_remaining_var,
            bg="#222834",
            fg="#e8ecf2",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10, "bold"),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 6))
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
            text="候補一覧（比較・行を選ぶと下のコンボと実行対象が連動）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 9),
            padx=2,
        ).pack(fill="x", pady=(0, 4))
        pr_lb_fr = tk.Frame(pr_inner, bg="#222834")
        pr_lb_fr.pack(fill="x", pady=(0, 8))
        self._pr_comparison_listbox = tk.Listbox(
            pr_lb_fr,
            height=5,
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
        self._pr_comparison_ids: List[str] = []
        pr_row = ttk.Frame(pr_inner, style="Card.TFrame")
        pr_row.pack(fill="x", pady=(0, 8))
        self._pr_campaign_ids = [str(x["id"]) for x in PR_CAMPAIGNS]
        pr_labels = [str(x["label"]) for x in PR_CAMPAIGNS]
        self._pr_combo = ttk.Combobox(
            pr_row,
            values=pr_labels,
            state="readonly",
            width=32,
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
        tk.Label(
            pr_inner,
            text="実行履歴（直近）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10),
        ).pack(fill="x", pady=(4, 2))
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

        self.merch_panel = self._create_panel(content, "グッズ開発")
        self.merch_panel.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        merch_inner = self._resolve_content_parent(self.merch_panel)
        tk.Label(
            merch_inner,
            text="各ラインのフェーズを進めます（開発費は所持金から差し引き）。売上表示は簡易ダミーで、本番の収支・内訳とは未連携です。",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            wraplength=900,
            padx=2,
        ).pack(fill="x", pady=(0, 8))
        merch_lines_fr = ttk.Frame(merch_inner, style="Card.TFrame")
        merch_lines_fr.pack(fill="x", pady=(0, 8))
        self._merch_rows: List[Tuple[str, tk.StringVar, tk.StringVar, ttk.Button]] = []
        for tmpl in MERCH_PRODUCTS:
            pid = str(tmpl["id"])
            var = tk.StringVar(value="")
            pvar = tk.StringVar(value="")
            row_fr = ttk.Frame(merch_lines_fr, style="Card.TFrame")
            row_fr.pack(fill="x", pady=3)
            left_col = tk.Frame(row_fr, bg="#222834")
            left_col.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(
                left_col,
                textvariable=var,
                bg="#222834",
                fg="#d6dbe3",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 10),
                wraplength=620,
            ).pack(anchor="w", fill="x")
            tk.Label(
                left_col,
                textvariable=pvar,
                bg="#222834",
                fg="#9aa4b2",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 9),
                wraplength=620,
            ).pack(anchor="w", fill="x", pady=(2, 0))
            btn = ttk.Button(
                row_fr,
                text="開発を進める",
                style="Menu.TButton",
                command=lambda p=pid: self._on_merch_advance(p),
            )
            btn.pack(side="right")
            self._merch_rows.append((pid, var, pvar, btn))
        tk.Label(
            merch_inner,
            text="売上・ランキング（ダミー）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10),
        ).pack(fill="x", pady=(6, 2))
        self._merch_dummy_text = scrolledtext.ScrolledText(
            merch_inner,
            height=5,
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
            text="開発履歴（直近）",
            bg="#222834",
            fg="#b8c0cc",
            anchor="w",
            font=("Yu Gothic UI", 10),
        ).pack(fill="x", pady=(4, 2))
        self._merch_hist_text = scrolledtext.ScrolledText(
            merch_inner,
            height=3,
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

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

        tk.Label(
            bottom,
            text=(
                "レイアウト: 上段＝財務・施設 ／ 中段＝オーナー・詳細レポート ／ 下段＝スポンサー・広報・グッズ。"
                " 右端の縦バーで全体をスクロールできます。"
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
        window = getattr(self, "_finance_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._finance_window = None
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
            self._management_dashboard_text = None
            self._facility_preview_vars = {}
            self._sponsor_preview_var = None
            self._pr_selection_preview_var = None
            self._pr_remaining_var = None
            self._pr_sort_combo = None
            self._pr_filter_combo = None
            self._pr_comparison_listbox = None
            self._pr_comparison_ids = []
            self._finance_scroll_canvas = None
            self._finance_inseason_log_text = None

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
                "（チーム未接続）メイン契約・スポンサー力は表示できません。メインでチームに接続してください。"
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
        for i, tid in enumerate(ids):
            if tid == cur:
                try:
                    combo.current(i)
                except tk.TclError:
                    pass
                break
        sp = int(self._safe_get(self.team, "sponsor_power", 0))
        status_var.set(
            f"現在のメイン契約: {label_for_main_sponsor_type(cur)} ｜ スポンサー力 {sp}／100 "
            "（次回オフシーズン締めのスポンサー収入内訳に反映）"
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
            status_var.set("（チーム未接続）広報・ファン施策の状態は表示できません。")
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
        status_var.set(f"{line_a}\n人気: {pop} ／ ファン基盤: {fb:,}")
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
        ph = str(item.get("phase", "concept"))
        if ph == "on_sale":
            messagebox.showinfo("グッズ開発", "すでに発売中です。")
            return
        cost = int(ADVANCE_COST.get(ph, 0) or 0)
        if cost <= 0:
            return
        if not messagebox.askyesno(
            "グッズ開発",
            f"次の工程に進みますか？\n必要資金: {self._format_money(cost)}",
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
        if not rows:
            return
        if self.team is None:
            for _pid, var, _pvar, btn in rows:
                var.set("（チーム未接続）ライン状態は表示できません。")
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
        for pid, var, _pvar, btn in rows:
            item = get_merchandise_item(self.team, pid)
            if item is not None:
                var.set(format_merchandise_row_display(item))
            else:
                var.set("（ライン未取得）接続とデータを確認してください。")
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

        dash_tw = getattr(self, "_management_dashboard_text", None)
        if dash_tw is not None:
            try:
                dash_tw.configure(state="normal")
                dash_tw.delete("1.0", tk.END)
                fin_lines = getattr(snap, "dashboard_finance_lines", None)
                if fin_lines:
                    parts = snap.dashboard_text.split(
                        _MANAGEMENT_FINANCE_BLOCK_SEPARATOR, 1
                    )
                    if len(parts) == 2:
                        dash_tw.insert(
                            "end",
                            "■ 財務\n",
                            ("finance_block_header",),
                        )
                        for ln in fin_lines:
                            dash_tw.insert(
                                "end",
                                ln + "\n",
                                _management_finance_dashboard_row_tags(ln),
                            )
                        sub_after_fin = parts[1]
                        fac_lines_snap = getattr(snap, "facility_lines", None)
                        fac_tail = sub_after_fin.split(
                            _MANAGEMENT_FACILITY_PR_SEPARATOR, 1
                        )
                        if fac_lines_snap and len(fac_tail) == 2:
                            dash_tw.insert(
                                "end",
                                "\n\n■ 施設\n",
                                ("facility_block_header",),
                            )
                            for fln in fac_lines_snap:
                                dash_tw.insert(
                                    "end",
                                    fln + "\n",
                                    _management_facility_dashboard_row_tags(fln),
                                )
                            pr_owner = fac_tail[1].split(
                                _MANAGEMENT_PR_OWNER_SEPARATOR, 1
                            )
                            if len(pr_owner) == 2:
                                dash_tw.insert("end", "\n\n")
                                pr_block = ("■ 広報" + pr_owner[0]).rstrip("\n")
                                for pln in pr_block.split("\n"):
                                    if pln == "":
                                        continue
                                    dash_tw.insert(
                                        "end",
                                        pln + "\n",
                                        _management_pr_dashboard_row_tags(pln),
                                    )
                                oh_hist = pr_owner[1].split(
                                    _MANAGEMENT_OWNER_HISTORY_SEPARATOR, 1
                                )
                                if len(oh_hist) == 2:
                                    dash_tw.insert(
                                        "end",
                                        _MANAGEMENT_PR_OWNER_SEPARATOR + "\n",
                                        ("owner_block_header",),
                                    )
                                    owner_body = oh_hist[0].lstrip("\n")
                                    for oln in owner_body.split("\n"):
                                        if oln == "":
                                            continue
                                        dash_tw.insert(
                                            "end",
                                            oln + "\n",
                                            _management_owner_dashboard_row_tags(oln),
                                        )
                                    hist_body = oh_hist[1]
                                    _hsep = _MANAGEMENT_OWNER_HISTORY_SEPARATOR
                                    if hist_body == "":
                                        dash_tw.insert("end", _hsep)
                                    else:
                                        dash_tw.insert(
                                            "end",
                                            _hsep,
                                            ("history_block_header",),
                                        )
                                        for hln in hist_body.split("\n"):
                                            if hln == "":
                                                continue
                                            dash_tw.insert(
                                                "end",
                                                hln + "\n",
                                                _management_history_dashboard_row_tags(
                                                    hln
                                                ),
                                            )
                                else:
                                    dash_tw.insert(
                                        "end",
                                        _MANAGEMENT_PR_OWNER_SEPARATOR + pr_owner[1],
                                    )
                            else:
                                dash_tw.insert(
                                    "end",
                                    _MANAGEMENT_FACILITY_PR_SEPARATOR + fac_tail[1],
                                )
                        else:
                            dash_tw.insert(
                                "end",
                                _MANAGEMENT_FINANCE_BLOCK_SEPARATOR + sub_after_fin,
                            )
                    else:
                        dash_tw.insert("1.0", snap.dashboard_text)
                else:
                    dash_tw.insert("1.0", snap.dashboard_text)
                dash_tw.configure(state="disabled")
            except tk.TclError:
                pass

        for var, line in zip(self.finance_summary_lines, snap.finance_lines):
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

        for var, line in zip(self.facility_lines, snap.facility_lines):
            var.set(line)

        fp_vars = getattr(self, "_facility_preview_vars", None)
        if isinstance(fp_vars, dict) and fp_vars:
            fac_prev_map = dict(snap.facility_action_previews)
            for fk, pv in fp_vars.items():
                try:
                    pv.set(fac_prev_map.get(fk, "—"))
                except tk.TclError:
                    pass

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

        pr_rem_v = getattr(self, "_pr_remaining_var", None)
        if pr_rem_v is not None:
            try:
                pr_rem_v.set(snap.pr_remaining_summary)
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
            for pid, _v, mpv, _btn in mrows:
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
                "【この画面】上のボタンから team_tactics の各詳細を開き、サブ画面で保存します。"
                "下段は現在の Team 状態の確認のみです（基本三本柱・スタメンの編集UIはこのハブでは表示していません）。"
            ),
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        row_a = ttk.Frame(nav, style="Panel.TFrame")
        row_a.pack(fill="x")
        row_b = ttk.Frame(nav, style="Panel.TFrame")
        row_b.pack(fill="x", pady=(4, 0))
        hub_ref = window

        def _strat_parent() -> tk.Misc:
            try:
                if hub_ref is not None and hub_ref.winfo_exists():
                    return hub_ref
            except Exception:
                pass
            return self.root

        def _nav_btn(fr: ttk.Frame, label: str, opener: Any) -> None:
            ttk.Button(fr, text=label, style="Menu.TButton", command=opener, width=20).pack(
                side="left", padx=4, pady=2
            )

        _nav_btn(
            row_a,
            "攻守詳細",
            lambda: self._open_tactics_team_strategy_window(hub_ref),
        )
        _nav_btn(
            row_a,
            "ローテ詳細",
            lambda: self._open_tactics_rotation_window(hub_ref),
        )
        _nav_btn(
            row_a,
            "起用テンプレ",
            lambda: self._open_tactics_usage_policy_window(hub_ref),
        )
        _nav_btn(
            row_b,
            "役割詳細",
            lambda: self._open_tactics_roles_window(hub_ref),
        )
        _nav_btn(
            row_b,
            "セット詳細",
            lambda: self._open_tactics_playbook_window(hub_ref),
        )

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
                "Team.strategy / coach_style / Team.usage_policy の変更は、このハブでは行いません。"
                "上段の「攻守詳細」など team_tactics の各画面で編集できる項目と別物です。"
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
                "Team の先発・6th・ベンチの変更は、このハブでは行いません。"
                "上段「ローテ詳細」「起用テンプレ」は team_tactics 側です（Team の起用手順とは別データ）。"
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
            "詳細 (team_tactics): 上のボタンのみから編集。試合で参照される項目と参照が限定的な項目が混在します。",
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
            "このハブは上段ボタンから team_tactics の各詳細を開くための画面です。"
            "左右の一覧は Team の現在値の確認のみです（編集UIは表示していません）。"
            "試合で参照される team_tactics のキーは限定的です。"
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

        if hasattr(self, "_strat_combo_strategy"):
            self._sync_strategy_policy_combos(
                self._strat_combo_strategy,
                self._strat_combo_coach,
                self._strat_combo_usage,
            )
            self._refresh_policy_coach_preview(self._strat_combo_coach, self._strat_coach_preview_text)
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
        self.team.team_tactics = normalize_team_tactics(payload, valid_player_ids=pids if pids else None)

    def _open_tactics_team_strategy_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        data = get_safe_team_tactics(self.team)["team_strategy"]
        pairs_map = {
            "offense_tempo": [("slow", "遅め"), ("standard", "標準"), ("fast", "速め")],
            "offense_style": [
                ("balanced", "バランス"),
                ("inside", "インサイド重視"),
                ("three_point", "3P重視"),
                ("drive", "ドライブ重視"),
            ],
            "offense_creation": [
                ("ball_move", "ボールムーブ重視"),
                ("pick_and_roll", "Pick & Roll重視"),
                ("iso", "アイソ重視"),
                ("post", "ポスト活用"),
            ],
            "defense_style": [
                ("balanced", "バランス"),
                ("protect_paint", "ペイント保護"),
                ("protect_three", "3P警戒"),
                ("pressure", "プレッシャー強め"),
            ],
            "rebound_style": [
                ("get_back", "戻り優先"),
                ("balanced", "バランス"),
                ("crash_offense", "攻撃リバウンド重視"),
            ],
            "transition_style": [
                ("push", "速攻を狙う"),
                ("situational", "状況次第"),
                ("half_court", "ハーフコート優先"),
            ],
        }
        labels = {
            "offense_tempo": "オフェンステンポ",
            "offense_style": "攻撃スタイル",
            "offense_creation": "攻撃組み立て",
            "defense_style": "ディフェンス方針",
            "rebound_style": "リバウンド方針",
            "transition_style": "トランジション方針",
        }
        w = tk.Toplevel(parent)
        w.title("攻守詳細")
        w.geometry("520x420")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        combos: Dict[str, ttk.Combobox] = {}

        def _set_combo(combo: ttk.Combobox, pairs: List[Tuple[str, str]], cur: str) -> None:
            vals = [b for _, b in pairs]
            combo["values"] = vals
            internals = [a for a, _ in pairs]
            combo.set(vals[internals.index(cur)] if cur in internals else vals[0])

        for key in (
            "offense_tempo",
            "offense_style",
            "offense_creation",
            "defense_style",
            "rebound_style",
            "transition_style",
        ):
            row = ttk.Frame(wrap, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=labels[key], width=18).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=28)
            cb.pack(side="left", padx=6)
            _set_combo(cb, pairs_map[key], str(data.get(key, "")))
            combos[key] = cb

        def _collect() -> Dict[str, str]:
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

        def _save() -> None:
            raw = dict(get_safe_team_tactics(self.team))
            raw["team_strategy"] = _collect()
            self._tactics_commit_payload(raw)
            messagebox.showinfo("保存", "攻守詳細を保存しました。", parent=w)
            self._refresh_strategy_window()

        def _reset() -> None:
            d = get_default_team_tactics()["team_strategy"]
            for k, cb in combos.items():
                _set_combo(cb, pairs_map[k], str(d.get(k, "")))

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
        w.title("ローテ詳細")
        w.geometry("640x620")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)

        ttk.Label(
            wrap,
            text="先発（ポジション別・team_tactics.rotation へ保存。本ハブ右パネルの Team 先発とは別）",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(anchor="w")
        starter_combos: Dict[str, ttk.Combobox] = {}
        starters_state = rot.get("starters") or {}
        for pos in STARTER_POSITIONS:
            row = ttk.Frame(wrap, style="Panel.TFrame")
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
            wrap,
            text="控え順: 一覧からの編集は未実装です（保存時は既存の team_tactics.rotation の値を維持します）",
            font=("Yu Gothic UI", 9),
            foreground="#9aa3b2",
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(wrap, text="交代・終盤方針", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w", pady=(10, 4))

        def _policy_combo(
            row_parent: ttk.Frame, label: str, pairs: List[Tuple[str, str]], cur: str
        ) -> ttk.Combobox:
            r = ttk.Frame(row_parent, style="Panel.TFrame")
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=label, width=18).pack(side="left")
            cb = ttk.Combobox(r, state="readonly", width=28)
            vals = [b for _, b in pairs]
            cb["values"] = vals
            ints = [a for a, _ in pairs]
            cb.set(vals[ints.index(cur)] if cur in ints else vals[0])
            cb.pack(side="left", padx=6)
            return cb

        pol_frame = ttk.Frame(wrap, style="Panel.TFrame")
        pol_frame.pack(fill="x")
        cb_sub = _policy_combo(pol_frame, "交代方針", sub_pairs, str(rot.get("sub_policy", "standard")))
        cb_fat = _policy_combo(pol_frame, "疲労対応", fat_pairs, str(rot.get("fatigue_policy", "standard")))
        cb_foul = _policy_combo(pol_frame, "ファウル対応", foul_pairs, str(rot.get("foul_policy", "standard")))
        cb_clutch = _policy_combo(pol_frame, "終盤起用", clutch_pairs, str(rot.get("clutch_policy", "stars")))

        ttk.Label(wrap, text="目標出場時間（分・0〜40）", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w", pady=(10, 4))
        minutes_frame = ttk.Frame(wrap, style="Panel.TFrame")
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
            messagebox.showinfo("保存", "ローテ詳細を保存しました。", parent=w)
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
        u = get_safe_team_tactics(self.team)["usage_policy"]
        pairs_map = {
            "priority": [("win", "勝利優先"), ("balanced", "バランス"), ("development", "育成優先")],
            "evaluation_focus": [
                ("overall", "総合力重視"),
                ("offense", "攻撃力重視"),
                ("defense", "守備力重視"),
                ("potential", "将来性重視"),
            ],
            "form_weight": [("high", "調子を強く反映"), ("standard", "標準"), ("skill", "実力を優先")],
            "age_balance": [("veteran", "ベテラン優先"), ("balanced", "バランス"), ("youth", "若手優先")],
            "injury_care": [("high", "ケガ配慮・強め"), ("standard", "標準"), ("low", "多少は無視")],
            "schedule_care": [("rest", "休養重視"), ("standard", "標準"), ("win", "勝利優先")],
            "foreign_player_usage": [
                ("stars", "主力として最大活用"),
                ("balanced", "バランス運用"),
                ("japan_core", "日本人中心"),
            ],
        }
        labels_j = {
            "priority": "起用の基本方針",
            "evaluation_focus": "評価基準",
            "form_weight": "調子の反映度",
            "age_balance": "年齢バランス",
            "injury_care": "ケガリスク配慮",
            "schedule_care": "連戦時運用",
            "foreign_player_usage": "外国籍起用方針",
        }
        w = tk.Toplevel(parent)
        w.title("起用テンプレ（保存）")
        w.geometry("560x400")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        combos: Dict[str, ttk.Combobox] = {}

        def _set_combo(cb: ttk.Combobox, pairs: List[Tuple[str, str]], cur: str) -> None:
            vals = [b for _, b in pairs]
            cb["values"] = vals
            ints = [a for a, _ in pairs]
            cb.set(vals[ints.index(cur)] if cur in ints else vals[0])

        for key in pairs_map:
            row = ttk.Frame(wrap, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=labels_j[key], width=20).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=26)
            _set_combo(cb, pairs_map[key], str(u.get(key, "")))
            cb.pack(side="left", padx=6)
            combos[key] = cb

        def _collect() -> Dict[str, str]:
            out: Dict[str, str] = {}
            for key, cb in combos.items():
                d = cb.get()
                for a, b in pairs_map[key]:
                    if b == d:
                        out[key] = a
                        break
                else:
                    out[key] = pairs_map[key][0][0]
            return out

        def _save() -> None:
            raw = dict(get_safe_team_tactics(self.team))
            raw["usage_policy"] = _collect()
            self._tactics_commit_payload(raw)
            messagebox.showinfo("保存", "起用テンプレを保存しました。", parent=w)

        def _reset() -> None:
            d = get_default_team_tactics()["usage_policy"]
            for k, cb in combos.items():
                _set_combo(cb, pairs_map[k], str(d.get(k, "")))

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x", pady=(12, 0))
        ttk.Button(btn, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn, text="標準に戻す", style="Menu.TButton", command=_reset).pack(side="left", padx=4)
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

    def _open_tactics_playbook_window(self, parent: tk.Toplevel) -> None:
        if self.team is None:
            return
        ensure_team_tactics_on_team(self.team)
        pb = get_safe_team_tactics(self.team)["playbook"]
        keys = [
            ("pick_and_roll", "Pick & Roll 頻度"),
            ("spain_pick_and_roll", "Spain P&R 頻度"),
            ("handoff", "ハンドオフ頻度"),
            ("off_ball_screen", "オフボールスクリーン頻度"),
            ("post_up", "ポストアップ頻度"),
            ("transition", "速攻頻度"),
        ]
        level_pairs = [("low", "少ない"), ("standard", "標準"), ("high", "多い")]
        w = tk.Toplevel(parent)
        w.title("セット詳細")
        w.geometry("480x360")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        combos: Dict[str, ttk.Combobox] = {}
        for key, jlabel in keys:
            row = ttk.Frame(wrap, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=jlabel, width=22).pack(side="left")
            cb = ttk.Combobox(row, state="readonly", width=12)
            vals = [b for _, b in level_pairs]
            cb["values"] = vals
            ints = [a for a, _ in level_pairs]
            cur = str(pb.get(key, "standard"))
            cb.set(vals[ints.index(cur)] if cur in ints else vals[1])
            cb.pack(side="left", padx=6)
            combos[key] = cb

        def _collect() -> Dict[str, str]:
            out: Dict[str, str] = {}
            for key, cb in combos.items():
                d = cb.get()
                for a, b in level_pairs:
                    if b == d:
                        out[key] = a
                        break
                else:
                    out[key] = "standard"
            return out

        def _save() -> None:
            raw = dict(get_safe_team_tactics(self.team))
            raw["playbook"] = _collect()
            self._tactics_commit_payload(raw)
            messagebox.showinfo("保存", "セット詳細を保存しました。", parent=w)

        def _reset() -> None:
            d = get_default_team_tactics()["playbook"]
            for k, cb in combos.items():
                cur = str(d.get(k, "standard"))
                vals = [b for _, b in level_pairs]
                ints = [a for a, _ in level_pairs]
                cb.set(vals[ints.index(cur)] if cur in ints else vals[1])

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
        main_pairs = [
            ("none", "未設定"),
            ("ace", "エース"),
            ("second_scorer", "セカンドスコアラー"),
            ("playmaker", "司令塔"),
            ("shooter", "シューター"),
            ("post_scorer", "ポスト得点役"),
            ("defense_ace", "守備エース"),
            ("rebounder", "リバウンド役"),
            ("sixth_man", "シックスマン"),
            ("energy", "エナジー役"),
        ]
        inv_pairs = [("high", "高い"), ("standard", "標準"), ("low", "低い")]
        shot_pairs = [("aggressive", "積極的"), ("standard", "標準"), ("passive", "控えめ")]
        clutch_pairs_r = [("go_to", "クラッチで任せる"), ("standard", "標準"), ("limited", "終盤は控えめ")]
        pm_pairs = [("primary", "主担当"), ("secondary", "補助"), ("minimal", "ほぼ任せない")]
        def_pairs = [("stopper", "相手主力担当"), ("standard", "標準"), ("light", "負担軽め")]

        w = tk.Toplevel(parent)
        w.title("役割詳細")
        w.geometry("720x460")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
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
            ttk.Label(r, text=label, width=18).pack(side="left")
            cb = ttk.Combobox(r, state="readonly", width=22)
            vals = [b for _, b in pairs]
            cb["values"] = vals
            ints = [a for a, _ in pairs]
            cb.set(vals[ints.index(cur)] if cur in ints else vals[0])
            cb.pack(side="left", padx=4)
            return cb

        editors: Dict[str, ttk.Combobox] = {}
        editors["main_role"] = _mk_combo(right, "メイン役割", main_pairs, "none")
        editors["offense_involvement"] = _mk_combo(right, "攻撃関与度", inv_pairs, "standard")
        editors["shot_priority"] = _mk_combo(right, "シュート優先度", shot_pairs, "standard")
        editors["clutch_priority"] = _mk_combo(right, "終盤優先度", clutch_pairs_r, "standard")
        editors["playmaking_role"] = _mk_combo(right, "プレメイク関与", pm_pairs, "secondary")
        editors["defense_assignment"] = _mk_combo(right, "守備担当度", def_pairs, "standard")

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
            messagebox.showinfo("保存", "役割詳細を保存しました。", parent=w)

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
        ).pack(fill="x", anchor="w")
        tk.Label(
            bottom,
            text="直近変更:",
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
            padx=2,
        ).pack(fill="x", anchor="w", pady=(8, 2))
        self._development_log_frame = tk.Frame(bottom, bg="#1d2129")
        self._development_log_frame.pack(fill="x", anchor="w")

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
            command=window.destroy,
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
                "【強化メニュー】チーム練習・個別練習の方針、スペシャル練習の解放条件、"
                "選手ごとの育成指標と見立てを確認します。上段の3パネルとロスター一覧は閲覧です。"
                "練習内容の変更だけ、ウィンドウ最下部（直近変更ログの下）の"
                "「チーム練習を変更」「個別練習を変更」から行えます。"
                "メイン画面でチーム未接続のときは変更ボタンは使えません。"
            ),
            wraplength=1020,
            font=("Yu Gothic UI", 10),
            justify="left",
        ).pack(anchor="w")

        top = ttk.Frame(dev_center, style="Root.TFrame")
        top.pack(fill="x", pady=(0, 12))
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
        self.development_effect_lines = self._make_line_vars(self.development_effect_panel, 6)
        self.development_special_lines = self._make_line_vars(self.development_special_panel, 7)

        table_wrap = ttk.Frame(dev_center, style="Panel.TFrame", padding=10)
        table_wrap.pack(fill="both", expand=True)
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(1, weight=1)

        ttk.Label(
            table_wrap,
            text="ロスター別の育成一覧（POT・development・年齢帯・見立て）",
            style="TopBar.TLabel",
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        columns = ("name", "pos", "age", "ovr", "pot", "dev", "games", "stage", "outlook")
        self.development_tree = ttk.Treeview(
            table_wrap,
            columns=columns,
            show="headings",
            height=18,
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
            "outlook": "育成見立て",
        }
        widths = {
            "name": 170,
            "pos": 70,
            "age": 70,
            "ovr": 70,
            "pot": 70,
            "dev": 80,
            "games": 80,
            "stage": 110,
            "outlook": 260,
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
        window = getattr(self, "_development_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._development_window = None

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
            f"チーム練習方針: {team_tf_label}",
            f"若手(23歳以下): {young_count}",
            f"全盛期(24-31歳): {prime_count}",
            f"ベテラン(32歳以上): {veteran_count}",
            f"平均育成値(development): {avg_dev:.1f}",
        ]
        for var, line in zip(self.development_summary_lines, summary_lines):
            var.set(line)

        effect_lines = [
            f"HCスタイル: {coach_text}",
            f"戦術: {strategy_text}",
            self._build_development_coach_note(coach_key),
            self._build_development_strategy_note(strategy_key),
            "若手は伸びやすく、32歳以上は衰退しやすい傾向です",
            "試合出場数も育成量に影響します",
        ]
        for var, line in zip(self.development_effect_lines, effect_lines):
            var.set(line)

        special_lines = self._build_current_special_training_lines(self.team)
        slot_n = len(self.development_special_lines)
        while len(special_lines) < slot_n:
            special_lines.append("（この行は予備／表示項目なし）")
        for i, var in enumerate(self.development_special_lines):
            var.set(special_lines[i] if i < len(special_lines) else "（表示なし）")

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
                    values=(pname, "—", "—", "—", "—", "—", "—", "—", outlook),
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
                            outlook,
                        ),
                    )

        self.development_hint_intro_var.set(
            "上段パネル: 人数・練習方針・HC/戦術の育成への効き方・スペシャル練習。"
            "下表: 選手ごとの POT / development / 試合出場 / 年齢帯 / 見立て（閲覧）。"
            "練習の編集は、この下の履歴のさらに下にある2ボタンから。"
        )
        self._refresh_development_training_log_widgets()

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
            "【トレード・FA】1対1（選手のみ）は左メニュー「人事」から実行できます。\n"
            "multi（複数人＋現金・RB）は人事または CLI（シーズンメニュー「8. GMメニュー」→「10. トレード」）。\n"
            "レギュラー中の FA プールからの手動獲得は、人事の「インシーズンFA（1人）」から 1 名まで。"
            "期限・可否の詳細は「人事」ウィンドウ上部の案内を参照してください。\n"
            "再契約の確認は、GUIモードでオフシーズン処理の実行中にダイアログで表示されます。\n"
            f"消化ラウンド: {cr}/{tr}\n"
            "ウィンドウ下のボタンはターミナル（CLI）へのショートカットです。\n\n"
            "先発・6th・ベンチの編集は左メニュー「戦術」（起用の編集）。"
            "当窓の「スタメン・ベンチ」は参照のみです。"
            "戦術メニューでは上段の詳細ボタンから team_tactics を編集します（Team 三本柱の編集UIは省略）。"
            "当窓の「戦術・HC・起用」は参照のみです。"
            "サラリーキャップの数値は左メニュー「経営」の「財務サマリー」下部。当窓の「サラリーキャップ」は案内のみです。"
            "チーム属性は左メニュー「情報」の「概要」上部。当窓の「チーム情報」は案内のみです。"
            "ロスター全文テキストは左メニュー「人事」の「詳細ロスター」。当窓の「ロスター」は案内のみです。"
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
                "ウィンドウ下部の「詳細ロスター（テキスト一覧）」を参照してください。"
            )
        return (
            "ロスター全員のテキスト一覧（並び・体裁は docs/GM_ROSTER_DISPLAY_RULES.md）の参照は、"
            "左メニュー「人事」を開き、表の下のペイン「詳細ロスター（テキスト一覧）」にまとめました。\n\n"
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
            "編集は左メニュー「戦術」ウィンドウの上段ボタン（各詳細）から行ってください。",
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

    def _refresh_policy_coach_preview(
        self,
        coach_combo: ttk.Combobox,
        text_widget: tk.Text,
    ) -> None:
        if text_widget is None or self.team is None:
            return
        try:
            selected_label = coach_combo.get()
            selected_key = self._gm_label_to_key_coach.get(
                selected_label,
                getattr(self.team, "coach_style", "balanced"),
            )
        except Exception:
            selected_key = getattr(self.team, "coach_style", "balanced")
        old_key = str(getattr(self.team, "coach_style", "balanced") or "balanced")
        lines = self._build_coach_unlock_diff_lines(old_key, str(selected_key))
        self._gm_set_readonly_text(text_widget, "\n".join(lines))

    def _on_strat_coach_selection_changed(self, _event: Any = None) -> None:
        if hasattr(self, "_strat_combo_coach") and hasattr(self, "_strat_coach_preview_text"):
            self._refresh_policy_coach_preview(
                self._strat_combo_coach,
                self._strat_coach_preview_text,
            )

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

    def _on_apply_strat_team_policy(self, parent: tk.Misc) -> None:
        if self.team is None:
            return
        try:
            sk = self._gm_label_to_key_strategy[self._strat_combo_strategy.get()]
            ck = self._gm_label_to_key_coach[self._strat_combo_coach.get()]
            uk = self._gm_label_to_key_usage[self._strat_combo_usage.get()]
        except (KeyError, tk.TclError, AttributeError):
            messagebox.showerror("エラー", "選択値を取得できませんでした。", parent=parent)
            return
        old_coach = str(getattr(self.team, "coach_style", "balanced") or "balanced")
        ok, msg = apply_team_gm_settings(self.team, sk, ck, uk)
        if not ok:
            messagebox.showerror("反映できません", msg, parent=parent)
            return
        self.refresh()
        lines = ["基本戦術・HC・基本起用を反映しました。"]
        if old_coach != ck:
            lines.append("")
            lines.extend(self._build_coach_unlock_diff_lines(old_coach, ck))
        messagebox.showinfo("保存", "\n".join(lines), parent=parent)

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

    def _build_current_special_training_lines(self, team: Any) -> List[str]:
        coach = str(getattr(team, "coach_style", "balanced") or "balanced")
        items = self._build_special_training_catalog_items(team, coach_override=coach)
        unlocked = [f"{c}:{n}" for c, n, ok, _ in items if ok]
        lines = [
            f"現在HC: {self._coach_style_label(coach)}",
            f"解放数: {len(unlocked)}/{len(items)}",
            "解放中: " + (" / ".join(unlocked) if unlocked else "なし"),
        ]
        return lines + self._build_coach_unlock_count_rows(team)

    def _build_coach_unlock_count_rows(self, team: Any) -> List[str]:
        rows: List[str] = []
        for style_key, style_label in COACH_STYLE_OPTIONS:
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

    def _refresh_development_training_log_widgets(self) -> None:
        frame = getattr(self, "_development_log_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        team = getattr(self, "team", None)
        logs = list(getattr(team, "training_change_log", []) or []) if team is not None else []
        if not logs:
            empty_msg = (
                "（直近の練習変更履歴はありません）"
                if team is not None
                else "（チーム未接続のため履歴を表示できません）"
            )
            tk.Label(
                frame,
                text=f"  {empty_msg}",
                bg="#1d2129",
                fg="#9aa3b2",
                anchor="w",
                font=("Yu Gothic UI", 10),
                padx=2,
                pady=0,
            ).pack(fill="x", anchor="w")
            return
        limit = 5
        colors = {"team": "#7ec8ff", "player": "#e8c07a", "other": "#9aa3b2"}
        for entry in logs[-limit:]:
            kind = self._training_log_entry_kind(entry)
            fg = colors.get(kind, colors["other"])
            tk.Label(
                frame,
                text=f"- {entry}",
                bg="#1d2129",
                fg=fg,
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 10),
                padx=2,
                pady=0,
            ).pack(fill="x", anchor="w")

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
        w.geometry("780x420")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)

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
        player_labels = [
            f"{getattr(p, 'name', '-'):<16} {getattr(p, 'position', 'SF')} OVR:{int(getattr(p, 'ovr', 0))}"
            for p in roster
        ]
        drill_label_to_key = {label: (key, focus) for key, label, focus in drills}

        ttk.Label(wrap, text="選手", font=("Yu Gothic UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        player_combo = ttk.Combobox(wrap, state="readonly", values=player_labels, width=42)
        player_combo.grid(row=1, column=0, sticky="ew", pady=(4, 10), padx=(0, 12))
        player_combo.set(player_labels[0])

        ttk.Label(wrap, text="練習", font=("Yu Gothic UI", 10, "bold")).grid(row=0, column=1, sticky="w")
        drill_combo = ttk.Combobox(wrap, state="readonly", values=[label for _, label, _ in drills], width=32)
        drill_combo.grid(row=1, column=1, sticky="ew", pady=(4, 10))
        drill_combo.set(drills[0][1])

        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)

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
            wraplength=740,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        def _selected_player() -> Any:
            idx = max(0, player_combo.current())
            return roster[idx]

        def _refresh_note(_event: Any = None) -> None:
            key_focus = drill_label_to_key.get(drill_combo.get(), ("balanced", "balanced"))
            key = key_focus[0]
            reason = self._player_drill_lock_reason(self.team, key)
            p = _selected_player()
            current_drill = str(getattr(p, "training_drill", "balanced") or "balanced")
            if reason:
                note_var.set(f"現在ドリル: {current_drill} / 未解放（条件）: {reason}")
            else:
                note_var.set(f"現在ドリル: {current_drill} / 選択可能です。")

        player_combo.bind("<<ComboboxSelected>>", _refresh_note)
        drill_combo.bind("<<ComboboxSelected>>", _refresh_note)
        _refresh_note()

        def _apply() -> None:
            p = _selected_player()
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
            messagebox.showinfo("完了", f"{getattr(p, 'name', '-') } の個別練習を更新しました。", parent=w)
            w.destroy()

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.grid(row=3, column=0, columnspan=2, sticky="ew")
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
            "1対1（選手のみ）・multi（複数人・現金・RB）は左メニュー「人事」から実行できます。\n"
            "同じ multi はシーズンメニュー「8. GMメニュー」→「10. トレード」からも実行できます。\n"
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
                text="先発・6th・ベンチの編集は、左メニュー「戦術」を開き、右パネル「起用の編集（試合に反映）」から行ってください。",
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
                text="（閲覧・案内のみ／正本は人事「詳細ロスター」）",
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
            text="戦術メニューでは上段の詳細ボタンから team_tactics を編集してください（Team 三本柱の編集UIは当該画面から外しています）。",
            wraplength=820,
            font=("Yu Gothic UI", 10),
        ).pack(anchor="w")
        ttk.Label(
            notice_st,
            text="このタブは閲覧・参照のみです（編集は左メニュー「戦術」）。",
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
            text="トレード・FAの案内（1対1・multiは人事／CLIでも可）",
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
            "・戦術メニュー（左「戦術①」）… 先発・6th・ベンチ順と「目標出場時間」を見直し、負傷者に負荷がかからないローテに組み替える。\n"
            "・人事メニュー（左「人事①」）… ロスター表で選手の状態を確認する。\n"
            "・team_tactics 側の起用テンプレ（例: injury_care）や交代方針は、戦術メニュー上部の詳細ボタンから調整できます。\n\n"
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
