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
- This file is intentionally read-mostly. The only mutating action is an optional
  callback such as on_advance, which is injected from outside.
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
    FACILITY_MAX_LEVEL,
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
    get_facility_upgrade_cost,
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
from basketball_sim.systems.competition_display import competition_display_name
from basketball_sim.systems.schedule_display import (
    detail_text_for_upcoming_row,
    format_season_event_matchup_line,
    information_panel_schedule_lines,
    next_round_schedule_lines,
    past_league_result_rows,
    round_month_label,
    upcoming_rows_for_user_team,
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
AdvanceCallback = Callable[[], None]
SystemMenuCallback = Callable[["MainMenuView"], None]


class MainMenuView:
    """Phase 4 minimal main menu / dashboard view."""

    MENU_ITEMS = [
        "日程",
        "人事",
        "GM",
        "経営",
        "強化",
        "戦術",
        "情報",
        "歴史",
        "システム",
    ]

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
    ) -> None:
        self.team = team
        self.season = season
        self.on_advance = on_advance
        self.menu_callbacks = menu_callbacks or {}
        self.on_system_menu = on_system_menu
        self.on_main_window_close = on_main_window_close
        self.external_news_items = news_items
        self.external_tasks = tasks

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
        self.style.configure(
            "Primary.TButton",
            font=("Yu Gothic UI", 12, "bold"),
            padding=(18, 12),
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

        for label in self.MENU_ITEMS:
            ttk.Button(
                left_panel,
                text=label,
                style="Menu.TButton",
                command=lambda key=label: self._on_menu(key),
            ).pack(fill="x", pady=5)

        # Center / right layout
        content = ttk.Frame(body, style="Root.TFrame")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=5)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self.next_game_panel = self._create_panel(content, "次の試合")
        self.next_game_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))

        self.club_summary_panel = self._create_panel(content, "クラブ状況サマリー")
        self.club_summary_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        self.tasks_panel = self._create_panel(content, "要対応案件")
        self.tasks_panel.grid(row=0, column=1, sticky="nsew", pady=(0, 12))

        right_bottom = ttk.Frame(content, style="Root.TFrame")
        right_bottom.grid(row=1, column=1, sticky="nsew")
        right_bottom.rowconfigure(0, weight=1)
        right_bottom.rowconfigure(1, weight=0)

        self.news_panel = self._create_panel(right_bottom, "ニュース")
        self.news_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        advance_wrap = ttk.Frame(right_bottom, style="Panel.TFrame", padding=12)
        advance_wrap.grid(row=1, column=0, sticky="ew")
        advance_wrap.columnconfigure(0, weight=1)

        self.advance_hint_var = tk.StringVar(value="")
        self.advance_hint_label = ttk.Label(
            advance_wrap,
            textvariable=self.advance_hint_var,
            background="#1d2129",
            foreground="#ffd38a",
            font=("Yu Gothic UI", 10),
            anchor="w",
        )
        self.advance_hint_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.advance_button = ttk.Button(
            advance_wrap,
            text="次へ進む",
            style="Primary.TButton",
            command=self._on_advance,
        )
        self.advance_button.grid(row=1, column=0, sticky="ew")

        debug_skip_cb = self.menu_callbacks.get("DEBUG_SKIP_TO_OFFSEASON")
        self.debug_skip_button: Optional[ttk.Button] = None
        if callable(debug_skip_cb):
            self.debug_skip_button = ttk.Button(
                advance_wrap,
                text="デバッグ: オフシーズンまで飛ばす",
                style="Menu.TButton",
                command=debug_skip_cb,
            )
            self.debug_skip_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        # Holders updated by refresh()
        self.top_bar_var = tk.StringVar(value="読み込み中...")
        ttk.Label(
            self.top_bar,
            textvariable=self.top_bar_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        self.next_game_lines = self._make_line_vars(self.next_game_panel, 5)
        self.club_summary_lines = self._make_line_vars(self.club_summary_panel, 6)
        self.task_lines = self._make_bullet_vars(self.tasks_panel, 3, prefix="! ")
        self.news_lines = self._make_bullet_vars(self.news_panel, 4, prefix="・")

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

    def _make_line_vars(self, panel: ttk.Frame, count: int) -> List[tk.StringVar]:
        content_parent = self._resolve_content_parent(panel)
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

    def _make_bullet_vars(self, panel: ttk.Frame, count: int, prefix: str) -> List[tk.StringVar]:
        content_parent = self._resolve_content_parent(panel)
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
        self._refresh_top_bar()
        self._refresh_season_status()
        self._refresh_next_game()
        self._refresh_club_summary()
        self._refresh_tasks()
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
                INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
                parent=p,
            )
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------
    def _refresh_top_bar(self) -> None:
        current_date = self._format_date(self._get_current_date())
        season_year = self._get_season_year()
        league_level = self._safe_get(self.team, "league_level", "-")
        rank = self._compute_rank_text()
        wins = self._safe_get(self.team, "regular_wins", 0)
        losses = self._safe_get(self.team, "regular_losses", 0)
        money = self._safe_get(self.team, "money", 0)
        owner_trust = self._get_owner_trust_text()
        task_count = len(self._get_tasks())

        text = (
            f"日付: {current_date}    "
            f"年度: {season_year}    "
            f"リーグ: D{league_level}    "
            f"順位: {rank}    "
            f"戦績: {wins}勝{losses}敗    "
            f"資金: {self._format_money(money)}    "
            f"オーナー信頼: {owner_trust}    "
            f"要対応: {task_count}件"
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
            self.season_status_var.set(
                "シーズン: 終了  |  トレード／インシーズンFA: オフシーズン（『次へ進む』でオフ処理）"
            )
            return
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        unlocked = self.inseason_roster_moves_allowed()
        tx = "可（ラウンド22消化後まで）" if unlocked else "期限切れ（シーズン終了まで不可）"
        self.season_status_var.set(f"消化ラウンド: {cr}/{tr}  |  トレード／インシーズンFA: {tx}")

    def _roster_transaction_status_text(self) -> str:
        """情報画面用の短い文言。"""
        if self.season is None:
            return "—"
        if bool(self._safe_get(self.season, "season_finished", False)):
            return "オフシーズン（制限なし）"
        if self.inseason_roster_moves_allowed():
            return "可（ラウンド22消化後まで）"
        return "期限切れ（シーズン終了まで不可）"

    def _refresh_next_game(self) -> None:
        info = self._build_next_game_info()
        for var, line in zip(self.next_game_lines, info):
            var.set(line)

    def _refresh_club_summary(self) -> None:
        info = self._build_club_summary_info()
        for var, line in zip(self.club_summary_lines, info):
            var.set(line)

    def _refresh_tasks(self) -> None:
        tasks = self._get_tasks()
        count = len(tasks)
        shown = tasks[:3]

        for i, var in enumerate(self.task_lines):
            if i < len(shown):
                var.set(f"! {shown[i]}")
            else:
                var.set("")

        season_finished = bool(self._safe_get(self.season, "season_finished", False))
        if season_finished:
            self.advance_hint_var.set(
                "レギュラーシーズン終了。『オフシーズンを実行』で契約・ドラフト等を進めます（数分かかる場合があります）。"
            )
        elif count > 0:
            self.advance_hint_var.set(f"未処理案件が {count} 件あります。必要なら先に確認してください。")
        else:
            self.advance_hint_var.set("")

    def _refresh_advance_button(self) -> None:
        fin = bool(self._safe_get(self.season, "season_finished", False))
        self.advance_button.configure(text="オフシーズンを実行" if fin else "次へ進む")

    def _refresh_news(self) -> None:
        news = self._get_news_items()[:4]
        for i, var in enumerate(self.news_lines):
            if i < len(news):
                var.set(f"・{news[i]}")
            else:
                var.set("")

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------
    def _build_next_game_info(self) -> List[str]:
        next_game = self._find_next_game()
        if next_game is None:
            return [
                "次の試合情報なし",
                "リーグ日程（SeasonEvent）も参照できませんでした",
                "ホーム/アウェイ: -",
                "相手情報: -",
                "補足: 左メニュー「日程」で一覧を確認できます",
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

        return [
            f"{game_round} / {game_type} / {game_date}",
            f"{home_team} vs {away_team}",
            f"{venue_text} / 相手順位: {opponent_rank} / 相手戦績: {opponent_record}",
            meaning,
            compare,
        ]

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
                get_hard_cap,
                get_payroll_floor,
                get_soft_cap,
                league_level_for_team,
            )

            payroll = int(get_team_payroll(team))
            lv = league_level_for_team(team)
            hard = int(get_hard_cap(league_level=lv))
            soft = int(get_soft_cap(league_level=lv))
            st = cap_status(payroll, league_level=lv)
            status_ja = {
                "under_cap": "キャップ内",
                "over_cap": "ハード超過",
                "over_soft_cap": "ソフト超過",
            }.get(st, st)
            room_soft = soft - payroll
            if room_soft >= 0:
                room_str = f"ソフト余裕 {room_soft:,}円"
            else:
                room_str = f"ソフト超過 {abs(room_soft):,}円"
            tax = int(compute_luxury_tax(payroll, league_level=lv))
            tax_str = f" / 贅沢税 {tax:,}円" if tax > 0 else ""
            bud = int(self._safe_get(team, "payroll_budget", 0) or 0)
            bud_str = ""
            if bud > 0:
                mark = " ⚠" if payroll > bud else ""
                bud_str = f" | クラブ目安 {bud:,}円{mark}"
            floor = int(get_payroll_floor(lv))
            floor_str = ""
            if floor > 0 and payroll < floor:
                floor_str = f" | ⚠ ペイロール下限未満（要 {floor:,}円以上・シーズン終了時は降格の対象）"
            return (
                f"給与合計 {payroll:,}円（ハード {hard:,}円 / ソフト {soft:,}円 / 全D共通ソフト12億）"
                f" | {status_ja} | {room_str}{tax_str}{bud_str}{floor_str}"
            )
        except Exception:
            return "給与・キャップ: 計算不可"



    def open_roster_window(self) -> None:
        """Open a safe read-only roster subwindow."""
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
        window.title(f"ロスター一覧 - {self._team_name()}")
        window.geometry("980x620")
        window.minsize(860, 520)
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

        columns = ("role", "name", "pos", "ovr", "pot", "age", "fatigue", "morale", "salary", "years")
        tree_wrap = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        tree_wrap.pack(fill="both", expand=True)

        self.roster_tree = ttk.Treeview(
            tree_wrap,
            columns=columns,
            show="headings",
            height=18,
        )
        headings = {
            "role": "役割",
            "name": "選手名",
            "pos": "POS",
            "ovr": "OVR",
            "pot": "POT",
            "age": "年齢",
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
            "fatigue": 70,
            "morale": 70,
            "salary": 130,
            "years": 80,
        }

        for key in columns:
            self.roster_tree.heading(key, text=headings[key])
            anchor = "center" if key != "name" else "w"
            self.roster_tree.column(key, width=widths[key], anchor=anchor, stretch=(key == "name"))

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.roster_tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.roster_tree.xview)
        self.roster_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.roster_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)

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

        ttk.Button(
            bottom,
            text="閉じる",
            style="Menu.TButton",
            command=window.destroy,
        ).pack(anchor="e", pady=(8, 0))

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

    def _refresh_roster_window(self) -> None:
        tree = getattr(self, "roster_tree", None)
        if tree is None:
            return

        try:
            for item in tree.get_children():
                tree.delete(item)
        except Exception:
            return

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

            tree.insert(
                "",
                "end",
                values=(role, name, pos, ovr, pot, age, fatigue, morale, salary, years),
            )

        team_name = self._team_name()
        count = len(players_sorted)
        avg_ovr = 0.0
        if count > 0:
            avg_ovr = sum(int(self._safe_get(p, "ovr", 0) or 0) for p in players_sorted) / count

        self.roster_header_var.set(
            f"{team_name} ロスター一覧    人数: {count}    平均OVR: {avg_ovr:.1f}"
        )
        self.roster_hint_var.set(
            "並び: ポジション順(PG→C)→同ポジ内OVR降順（docs/GM_ROSTER_DISPLAY_RULES.md と共通）。"
            "先発・6th・控え番号は Team の起用ロジックに基づきます。読み取り専用。"
        )

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

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.finance_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.finance_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        content = ttk.Frame(outer, style="Root.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=0)
        content.rowconfigure(1, weight=1)
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

        self.finance_summary_lines = self._make_line_vars(self.finance_summary_panel, 6)
        self.facility_lines = self._make_line_vars(self.facility_panel, 6)
        fac_content = self._resolve_content_parent(self.facility_panel)
        btn_row = ttk.Frame(fac_content, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(12, 0))
        self._facility_upgrade_buttons: Dict[str, ttk.Button] = {}
        for i, fk in enumerate(FACILITY_ORDER):
            label = FACILITY_LABELS.get(fk, fk)
            b = ttk.Button(
                btn_row,
                text=f"{label}を強化",
                style="Menu.TButton",
                command=lambda k=fk: self._on_facility_upgrade_click(k),
            )
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)
            self._facility_upgrade_buttons[fk] = b
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        owner_parent = self._resolve_content_parent(self.owner_panel)
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
            textvariable=self._sponsor_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 11),
            wraplength=900,
            padx=2,
            pady=(0, 8),
        ).pack(fill="x")
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
        self._sponsor_apply_btn = ttk.Button(
            sponsor_row,
            text="メイン契約を反映",
            style="Menu.TButton",
            command=self._on_sponsor_contract_apply,
        )
        self._sponsor_apply_btn.pack(side="left")
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
            textvariable=self._pr_status_var,
            bg="#222834",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 11),
            wraplength=900,
            padx=2,
            pady=(0, 8),
        ).pack(fill="x")
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
        self._pr_run_btn = ttk.Button(
            pr_row,
            text="施策を実行",
            style="Menu.TButton",
            command=self._on_pr_campaign_run,
        )
        self._pr_run_btn.pack(side="left")
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
            pady=(0, 8),
        ).pack(fill="x")
        merch_lines_fr = ttk.Frame(merch_inner, style="Card.TFrame")
        merch_lines_fr.pack(fill="x", pady=(0, 8))
        self._merch_rows: List[Tuple[str, tk.StringVar, ttk.Button]] = []
        for tmpl in MERCH_PRODUCTS:
            pid = str(tmpl["id"])
            var = tk.StringVar(value="")
            row_fr = ttk.Frame(merch_lines_fr, style="Card.TFrame")
            row_fr.pack(fill="x", pady=3)
            tk.Label(
                row_fr,
                textvariable=var,
                bg="#222834",
                fg="#d6dbe3",
                anchor="w",
                justify="left",
                font=("Yu Gothic UI", 10),
                wraplength=620,
            ).pack(side="left", fill="x", expand=True, padx=(0, 8))
            btn = ttk.Button(
                row_fr,
                text="開発を進める",
                style="Menu.TButton",
                command=lambda p=pid: self._on_merch_advance(p),
            )
            btn.pack(side="right")
            self._merch_rows.append((pid, var, btn))
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

        self.finance_hint_var = tk.StringVar(value="")
        tk.Label(
            bottom,
            textvariable=self.finance_hint_var,
            bg="#1d2129",
            fg="#d6dbe3",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 10),
            padx=2,
            pady=2,
        ).pack(fill="x", anchor="w")

        ttk.Button(
            bottom,
            text="閉じる",
            style="Menu.TButton",
            command=self._on_close_finance_window,
        ).pack(anchor="e", pady=(8, 0))

        self._finance_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_finance_window)
        self._refresh_finance_window()

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

    def _on_pr_campaign_run(self) -> None:
        team = self.team
        if team is None:
            return
        combo = getattr(self, "_pr_combo", None)
        ids = getattr(self, "_pr_campaign_ids", [])
        if combo is None or not ids:
            return
        idx = combo.current()
        if idx < 0 or idx >= len(ids):
            messagebox.showwarning("広報・ファン", "施策を選択してください。")
            return
        ok, msg = commit_pr_campaign(team, ids[idx], self.season)
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
        if combo is None or status_var is None or self.team is None:
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
        if combo is None or status_var is None or self.team is None:
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
        if self.team is None or not rows:
            return
        ensure_merchandise_on_team(self.team)
        is_user = bool(getattr(self.team, "is_user_team", False))
        for pid, var, btn in rows:
            item = get_merchandise_item(self.team, pid)
            if item is not None:
                var.set(format_merchandise_row_display(item))
            try:
                if not is_user or (item is not None and str(item.get("phase")) == "on_sale"):
                    btn.state(["disabled"])
                else:
                    btn.state(["!disabled"])
            except tk.TclError:
                pass
        if dummy_tw is not None:
            dtext = "\n".join(estimate_dummy_merch_sales_lines(self.team))
            try:
                dummy_tw.configure(state="normal")
                dummy_tw.delete("1.0", tk.END)
                dummy_tw.insert("1.0", dtext)
                dummy_tw.configure(state="disabled")
            except tk.TclError:
                pass
        if hist_tw is not None:
            htext = "\n".join(format_merchandise_history_lines(self.team))
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
        budget = self._safe_get(self.team, "payroll_budget", profile.get("payroll_budget", 0))
        popularity = self._safe_get(self.team, "popularity", profile.get("popularity", 0))
        revenue = self._safe_get(self.team, "revenue_last_season", profile.get("revenue_last_season", 0))
        expense = self._safe_get(self.team, "expense_last_season", profile.get("expense_last_season", 0))
        cashflow = self._safe_get(self.team, "cashflow_last_season", profile.get("cashflow_last_season", 0))

        self.finance_header_var.set(
            f"{team_name} 経営画面    所持金: {self._format_money(money)}    前季収支: {self._format_signed_money(cashflow)}"
        )

        summary_lines = [
            f"所持金: {self._format_money(money)}",
            f"年俸予算: {self._format_money(budget)}",
            f"人気: {self._safe_int_text(popularity)}",
            f"前季収入: {self._format_money(revenue)}",
            f"前季支出: {self._format_money(expense)}",
            f"前季収支: {self._format_signed_money(cashflow)}",
        ]
        for var, line in zip(self.finance_summary_lines, summary_lines):
            var.set(line)

        market_size = self._safe_get(self.team, "market_size", profile.get("market_size", 1.0))
        fan_base = self._safe_get(self.team, "fan_base", profile.get("fan_base", 0))
        season_tickets = self._safe_get(self.team, "season_ticket_base", profile.get("season_ticket_base", 0))
        sponsor_power = self._safe_get(self.team, "sponsor_power", profile.get("sponsor_power", 0))

        facility_lines: List[str] = []
        for fk in FACILITY_ORDER:
            lv = int(self._safe_get(self.team, fk, profile.get(fk, 1)))
            flabel = FACILITY_LABELS.get(fk, fk)
            if lv >= FACILITY_MAX_LEVEL:
                facility_lines.append(f"{flabel}: Lv{lv}（最大）")
            else:
                nxt = get_facility_upgrade_cost(self.team, fk)
                facility_lines.append(f"{flabel}: Lv{lv} → 次回 {self._format_money(nxt)}")
        facility_lines.append(f"市場規模: {market_size}")
        facility_lines.append(
            f"ファン基盤: {self._safe_int_text(fan_base)} / シーズン券: {self._safe_int_text(season_tickets)} / スポンサー力: {self._safe_int_text(sponsor_power)}"
        )
        for var, line in zip(self.facility_lines, facility_lines):
            var.set(line)

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
        om_getter = getattr(self.team, "get_owner_mission_report_text", None)
        if callable(om_getter):
            try:
                owner_body = str(om_getter() or "")
            except Exception:
                owner_body = ""
        if not owner_body.strip():
            owner_expectation = self._safe_get(self.team, "owner_expectation", profile.get("owner_expectation", "-"))
            owner_trust = self._safe_get(self.team, "owner_trust", profile.get("owner_trust", "-"))
            owner_body = (
                f"オーナー期待値: {owner_expectation}\n"
                f"オーナー信頼: {self._safe_int_text(owner_trust)} / 100\n"
                "（詳細テキストを取得できませんでした）"
            )
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

        self.finance_hint_var.set(
            "「グッズ開発」はフェーズ保存＋開発費（売上表示はダミー）。"
            "広報はラウンド上限あり。スポンサー・施設・オーナー・財務は各パネル。"
        )

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
        ttk.Label(nav, text="戦術設定（各画面で保存）", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 6))
        row_a = ttk.Frame(nav, style="Panel.TFrame")
        row_a.pack(fill="x")
        row_b = ttk.Frame(nav, style="Panel.TFrame")
        row_b.pack(fill="x", pady=(4, 0))
        hub_ref = window

        def _nav_btn(fr: ttk.Frame, label: str, opener: Any) -> None:
            ttk.Button(fr, text=label, style="Menu.TButton", command=opener, width=20).pack(
                side="left", padx=4, pady=2
            )

        _nav_btn(
            row_a,
            "チーム戦術",
            lambda: self._open_tactics_team_strategy_window(hub_ref),
        )
        _nav_btn(
            row_a,
            "ローテーション管理",
            lambda: self._open_tactics_rotation_window(hub_ref),
        )
        _nav_btn(
            row_a,
            "起用方針",
            lambda: self._open_tactics_usage_policy_window(hub_ref),
        )
        _nav_btn(
            row_b,
            "役割設定",
            lambda: self._open_tactics_roles_window(hub_ref),
        )
        _nav_btn(
            row_b,
            "セットプレー方針",
            lambda: self._open_tactics_playbook_window(hub_ref),
        )

        content = ttk.Frame(outer, style="Root.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=0)
        content.rowconfigure(1, weight=1)

        strategy_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        strategy_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        lineup_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        lineup_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        notes_panel = ttk.Frame(content, style="Panel.TFrame", padding=12)
        notes_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")

        ttk.Label(strategy_panel, text="戦術設定", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(lineup_panel, text="起用状況", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(notes_panel, text="補足", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 8))

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

        self.strategy_hint_var = tk.StringVar(value="")
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

        self.strategy_header_var.set(f"{self._team_name()} 戦術メニュー（概要）")

        strategy_lines = [
            f"試合反映中の戦術 (Team.strategy): {strategy_text}",
            f"HCスタイル: {coach_text}",
            f"起用方針 (Team.usage_policy): {usage_text}",
            f"ロスター人数: {len(list(self._safe_get(self.team, 'players', []) or []))}",
            f"先発人数: {len(starters)} / ベンチ序列人数: {len(bench_order)}",
            "詳細戦術 (team_tactics): 上のボタンから編集・保存（Phase A は試合未連携）",
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
            "概要は読み取り専用です。GMタブの「戦術・HC・起用」で試合に効く strategy / usage_policy を変更できます。"
            " team_tactics の細かい設定は Phase B 以降でシミュへ接続予定です。"
        )

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
        w.title("チーム戦術")
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
            messagebox.showinfo("保存", "チーム戦術を保存しました。", parent=w)
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
        w.title("ローテーション管理")
        w.geometry("640x620")
        w.configure(bg="#15171c")
        wrap = ttk.Frame(w, style="Root.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="先発（ポジション別・Phase A は team_tactics のみ保存）", font=("Yu Gothic UI", 10, "bold")).pack(
            anchor="w"
        )
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
            text="控え順: Phase A では一覧編集は未実装（保存時は既存の team_tactics の値を維持）",
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
            messagebox.showinfo("保存", "ローテーション設定を保存しました。", parent=w)
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

        btn = ttk.Frame(wrap, style="Panel.TFrame")
        btn.pack(fill="x", pady=(8, 0))
        ttk.Button(btn, text="保存", style="Primary.TButton", command=_save).pack(side="left", padx=4)
        ttk.Button(btn, text="標準に戻す", style="Menu.TButton", command=_reset).pack(side="left", padx=4)
        ttk.Button(btn, text="閉じる", style="Menu.TButton", command=w.destroy).pack(side="right", padx=4)

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
        w.title("起用方針（詳細・保存のみ）")
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
            messagebox.showinfo("保存", "起用方針（詳細）を保存しました。", parent=w)

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
        w.title("セットプレー方針")
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
            messagebox.showinfo("保存", "セットプレー方針を保存しました。", parent=w)

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
        w.title("役割設定")
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
            messagebox.showinfo("保存", "役割設定を保存しました。", parent=w)

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
        """Open a safe read-only development / growth subwindow."""
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

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.development_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.development_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        top = ttk.Frame(outer, style="Root.TFrame")
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

        table_wrap = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        table_wrap.pack(fill="both", expand=True)
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(0, weight=1)

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
        self.development_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

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
            pady=(8, 2),
        ).pack(fill="x", anchor="w")
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

        self._development_window = window
        window.protocol("WM_DELETE_WINDOW", self._on_close_development_window)
        self._refresh_development_window()

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

        self.development_header_var.set(
            f"{self._team_name()} 強化・育成状況    育成有望株: {top_name} (POT {top_pot})"
        )

        summary_lines = [
            f"ロスター人数: {len(players_sorted)}",
            f"若手(23歳以下): {young_count}",
            f"全盛期(24-31歳): {prime_count}",
            f"ベテラン(32歳以上): {veteran_count}",
            f"平均育成値: {avg_dev:.1f}",
            f"育成有望株: {top_name}",
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
        while len(special_lines) < len(self.development_special_lines):
            special_lines.append("")
        for var, line in zip(self.development_special_lines, special_lines[: len(self.development_special_lines)]):
            var.set(line)

        tree = getattr(self, "development_tree", None)
        if tree is not None:
            for item in tree.get_children():
                tree.delete(item)
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
            "読み取り専用の強化画面です。potential / development / 年齢 / 試合数 / 戦術相性を確認できます。"
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
        tab_overview.rowconfigure(0, weight=1)

        top_ov = ttk.Frame(tab_overview, style="Root.TFrame")
        top_ov.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        top_ov.columnconfigure(0, weight=1)
        top_ov.columnconfigure(1, weight=1)

        self.info_progress_panel = self._create_panel(top_ov, "シーズン進行")
        self.info_progress_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info_schedule_panel = self._create_panel(top_ov, "次ラウンド予定")
        self.info_schedule_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.info_comp_panel = self._create_panel(tab_overview, "大会進行状況")
        self.info_comp_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")

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

        ttk.Button(
            bottom,
            text="閉じる",
            style="Menu.TButton",
            command=window.destroy,
        ).pack(anchor="e", pady=(8, 0))

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
            text="読み取り専用です。一覧は主に日本リーグの SeasonEvent 由来。過去結果は上が新しい順。カップ戦は大会進行（情報ウィンドウ）も併せて確認してください。",
            bg="#1d2129",
            fg="#9aa3af",
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x")
        ttk.Button(bottom, text="閉じる", style="Menu.TButton", command=self._on_close_schedule_window).pack(
            anchor="e", pady=(8, 0)
        )

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
            hdr.set(
                f"{self._team_name()} 日程    消化ラウンド {cr}/{tr}    "
                f"{'シーズン終了' if fin else 'シーズン進行中'}"
            )

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

        past = past_league_result_rows(self.season, self.team)
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
            return information_panel_schedule_lines(self.season, max_events=7)
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
        ttk.Button(
            hist_bottom,
            text="閉じる",
            style="Menu.TButton",
            command=self._close_history_window,
        ).pack(anchor="e")

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
        """シーズン状況＋CLI 案内（GM ウィンドウ上部）。"""
        cr = int(self._safe_get(self.season, "current_round", 0) or 0)
        tr = int(self._safe_get(self.season, "total_rounds", 0) or 0)
        fin = self.season is not None and bool(self._safe_get(self.season, "season_finished", False))
        unlocked = self.inseason_roster_moves_allowed()
        if self.season is None:
            lock_line = "シーズンが未接続です。"
        elif fin:
            lock_line = (
                "現在はオフシーズンです。トレード・FA はオフシーズン処理（再契約・FA・ドラフト等）で行います。"
            )
        elif unlocked:
            lock_line = (
                "レギュラー中のトレード／インシーズンFA は「ラウンド22消化後」まで可能です（3月第2週終了相当）。"
            )
        else:
            lock_line = (
                "レギュラー中のトレード／インシーズンFA は期限切れです。シーズン終了まで人事の強化はできません。"
            )
        return (
            f"消化ラウンド: {cr}/{tr}\n"
            f"{lock_line}\n\n"
            "「スタメン・ベンチ」タブでスタメン1枠・6th・ベンチ入替を反映できます（確認ダイアログ付き）。"
            "「戦術・HC・起用」タブで戦術・HCスタイル・起用方針を変更できます。"
            "トレード・インシーズンFAはウィンドウ下の「トレード・FA（ターミナル案内）」で可否を確認できます。"
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
        self._gm_set_readonly_text(self._gm_text_team, format_team_identity_text(self.team))
        self._gm_set_readonly_text(self._gm_text_cap, format_salary_cap_text(self.team))
        self._gm_set_readonly_text(self._gm_text_roster, format_gm_roster_text(self.team))
        self._gm_set_readonly_text(self._gm_text_lineup, format_lineup_snapshot_text(self.team))
        self._sync_gm_lineup_edit()
        self._sync_gm_sixth_edit()
        self._sync_gm_bench_edit()
        self._sync_gm_strategy_combos()

    def _sync_gm_strategy_combos(self) -> None:
        if self.team is None or not hasattr(self, "_combo_strategy"):
            return

        def _set(combo: ttk.Combobox, options, current_key: str) -> None:
            cur = str(current_key)
            for k, lab in options:
                if k == cur:
                    combo.set(lab)
                    return
            combo.set(options[0][1])

        _set(self._combo_strategy, STRATEGY_OPTIONS, getattr(self.team, "strategy", "balanced"))
        _set(self._combo_coach, COACH_STYLE_OPTIONS, getattr(self.team, "coach_style", "balanced"))
        _set(self._combo_usage, USAGE_POLICY_OPTIONS, getattr(self.team, "usage_policy", "balanced"))
        self._refresh_gm_coach_preview()

    def _refresh_gm_coach_preview(self) -> None:
        text_widget = getattr(self, "_gm_coach_preview_text", None)
        if text_widget is None or self.team is None:
            return
        try:
            selected_label = self._combo_coach.get()
            selected_key = self._gm_label_to_key_coach.get(
                selected_label,
                getattr(self.team, "coach_style", "balanced"),
            )
        except Exception:
            selected_key = getattr(self.team, "coach_style", "balanced")
        old_key = str(getattr(self.team, "coach_style", "balanced") or "balanced")
        lines = self._build_coach_unlock_diff_lines(old_key, str(selected_key))
        self._gm_set_readonly_text(text_widget, "\n".join(lines))

    def _on_gm_coach_selection_changed(self, _event: Any = None) -> None:
        self._refresh_gm_coach_preview()

    def _gm_slot_label_to_index(self, label: str) -> int:
        try:
            return self._gm_slot_labels.index(label)
        except (ValueError, AttributeError):
            return 0

    def _gm_candidate_label_for_player(self, p: Any) -> str:
        return (
            f"{getattr(p, 'name', '-')} ({getattr(p, 'position', '-')}) "
            f"OVR{int(getattr(p, 'ovr', 0))} id={getattr(p, 'player_id', '')}"
        )

    def _sync_gm_lineup_candidates(self) -> None:
        if self.team is None or not hasattr(self, "_gm_combo_lineup_slot"):
            return
        starters = get_current_starting_five(self.team)
        if len(starters) < 5:
            self._gm_candidate_players = []
            self._gm_combo_lineup_candidate.configure(values=[])
            self._gm_combo_lineup_candidate.set("")
            return
        try:
            lab = self._gm_combo_lineup_slot.get()
        except tk.TclError:
            lab = self._gm_slot_labels[0]
        slot_index = self._gm_slot_label_to_index(lab)
        cands = get_available_starting_candidates(self.team, starters, slot_index)
        self._gm_candidate_players = list(cands)
        values = [self._gm_candidate_label_for_player(p) for p in cands]
        self._gm_combo_lineup_candidate.configure(values=values)
        if values:
            self._gm_combo_lineup_candidate.set(values[0])
        else:
            self._gm_combo_lineup_candidate.set("")

    def _sync_gm_lineup_edit(self) -> None:
        if self.team is None or not hasattr(self, "_gm_combo_lineup_slot"):
            return
        starters = get_current_starting_five(self.team)
        ok = len(starters) >= 5
        state = "readonly" if ok else "disabled"
        self._gm_combo_lineup_slot.configure(state=state)
        self._gm_combo_lineup_candidate.configure(state=state)
        self._gm_btn_apply_lineup_slot.configure(state="normal" if ok else "disabled")
        if not ok:
            self._gm_candidate_players = []
            self._gm_combo_lineup_candidate.configure(values=[])
            self._gm_combo_lineup_candidate.set("")
            return
        try:
            cur = self._gm_combo_lineup_slot.get()
        except tk.TclError:
            cur = ""
        if not cur or cur not in getattr(self, "_gm_slot_labels", ()):
            self._gm_combo_lineup_slot.set(self._gm_slot_labels[0])
        self._sync_gm_lineup_candidates()

    def _on_gm_slot_lineup_changed(self) -> None:
        self._sync_gm_lineup_candidates()

    def _on_apply_gm_starting_slot(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        starters = get_current_starting_five(self.team)
        if len(starters) < 5:
            messagebox.showwarning("スタメン", "スタメンが5人未満のため変更できません。", parent=parent)
            return
        try:
            lab = self._gm_combo_lineup_slot.get()
        except tk.TclError:
            lab = self._gm_slot_labels[0]
        slot_index = self._gm_slot_label_to_index(lab)
        try:
            sel = self._gm_combo_lineup_candidate.get()
        except tk.TclError:
            sel = ""
        values = [self._gm_candidate_label_for_player(p) for p in self._gm_candidate_players]
        try:
            idx = values.index(sel)
        except ValueError:
            messagebox.showwarning("スタメン", "候補を選択してください。", parent=parent)
            return
        player = self._gm_candidate_players[idx]
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

    def _bench_slot_labels(self) -> List[str]:
        return [
            f"{i + 1}. {self._gm_candidate_label_for_player(p)}"
            for i, p in enumerate(self._gm_bench_players)
        ]

    def _sync_gm_sixth_edit(self) -> None:
        if self.team is None or not hasattr(self, "_gm_combo_sixth"):
            return
        cands = get_sixth_man_candidates(self.team)
        self._gm_sixth_candidate_players = list(cands)
        values = [self._gm_candidate_label_for_player(p) for p in cands]
        self._gm_combo_sixth.configure(values=values)
        if values:
            self._gm_combo_sixth.set(values[0])
        else:
            self._gm_combo_sixth.set("")
        self._gm_btn_apply_sixth.configure(state="normal" if values else "disabled")

    def _sync_gm_bench_edit(self) -> None:
        if self.team is None or not hasattr(self, "_gm_combo_bench_a"):
            return
        bench = get_current_bench_order(self.team)
        self._gm_bench_players = list(bench)
        labels = self._bench_slot_labels()
        if len(bench) < 2:
            self._gm_combo_bench_a.configure(values=[], state="disabled")
            self._gm_combo_bench_b.configure(values=[], state="disabled")
            self._gm_combo_bench_a.set("")
            self._gm_combo_bench_b.set("")
            self._gm_btn_bench_swap.configure(state="disabled")
            return
        for combo in (self._gm_combo_bench_a, self._gm_combo_bench_b):
            combo.configure(values=labels, state="readonly")
        self._gm_combo_bench_a.set(labels[0])
        self._gm_combo_bench_b.set(labels[1])
        self._gm_btn_bench_swap.configure(state="normal")

    def _on_apply_gm_sixth_man(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        values = [self._gm_candidate_label_for_player(p) for p in self._gm_sixth_candidate_players]
        try:
            sel = self._gm_combo_sixth.get()
        except tk.TclError:
            sel = ""
        try:
            idx = values.index(sel)
        except ValueError:
            messagebox.showwarning("6thマン", "候補を選択してください。", parent=parent)
            return
        player = self._gm_sixth_candidate_players[idx]
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

    def _on_reset_sixth_man_gui(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
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

    def _on_apply_gm_bench_swap(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        self._gm_bench_players = list(get_current_bench_order(self.team))
        labels = self._bench_slot_labels()
        if len(self._gm_bench_players) < 2:
            messagebox.showwarning("ベンチ", "ベンチが2人未満のため入れ替えできません。", parent=parent)
            return
        try:
            sa = self._gm_combo_bench_a.get()
            sb = self._gm_combo_bench_b.get()
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
        pa = self._gm_bench_players[idx_a]
        pb = self._gm_bench_players[idx_b]
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

    def _on_reset_bench_order_gui(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
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

    def _on_apply_gm_strategy(self) -> None:
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        try:
            sk = self._gm_label_to_key_strategy[self._combo_strategy.get()]
            ck = self._gm_label_to_key_coach[self._combo_coach.get()]
            uk = self._gm_label_to_key_usage[self._combo_usage.get()]
        except (KeyError, tk.TclError):
            messagebox.showerror("エラー", "選択値を取得できませんでした。", parent=parent)
            return
        old_coach = str(getattr(self.team, "coach_style", "balanced") or "balanced")
        ok, msg = apply_team_gm_settings(self.team, sk, ck, uk)
        if not ok:
            messagebox.showerror("反映できません", msg, parent=parent)
            return
        self._refresh_gm_dashboard_window()
        lines = ["戦術・HC・起用方針を反映しました。"]
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
            tk.Label(
                frame,
                text="  なし",
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

    def _on_reset_starting_lineup_gui(self) -> None:
        """カスタムスタメン解除（Team.clear_starting_lineup）。確認ダイアログ付き。"""
        if self.team is None:
            return
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        try:
            ok = messagebox.askokcancel(
                "自動スタメンに戻す",
                "カスタムスタメン（手動設定）を解除し、チームの自動選出に戻しますか？\n\n"
                "※ 6thマンの設定はそのままです。変更はCLIのGMメニューから行えます。",
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
        """トレード／インシーズンFA 相当の可否を CLI と同じガードで確認し、ターミナル操作を案内する。"""
        w = getattr(self, "_gm_window", None)
        try:
            parent = w if w is not None and w.winfo_exists() else self.root
        except Exception:
            parent = self.root
        if not self.ensure_inseason_roster_moves_allowed(parent):
            return
        messagebox.showinfo(
            "ターミナルでトレード・FA",
            "シーズンメニューで「8. GMメニュー」→「10. トレード」から操作します。\n"
            "（レギュラー中のトレード・インシーズンFAは期限後は同じくメニュー側でブロックされます。）",
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
        """GM: チーム情報／キャップ／ロスターは閲覧。戦術・HC・起用とスタメン／6th／ベンチはタブ内で反映。トレード等は CLI。"""
        if self.team is None:
            messagebox.showwarning("GM", "チームが未接続です。", parent=self.root)
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
        window.title(f"GM - {self._team_name()}")
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
            height=5,
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

        def _make_lineup_tab() -> None:
            tab = ttk.Frame(nb, style="Root.TFrame", padding=6)
            nb.add(tab, text="スタメン・ベンチ")
            tab.rowconfigure(3, weight=1)
            tab.columnconfigure(0, weight=1)

            self._gm_slot_labels = ("PG枠", "SG枠", "SF枠", "PF枠", "C枠")
            edit_row = ttk.Frame(tab, style="Panel.TFrame", padding=(4, 6))
            edit_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
            ttk.Label(edit_row, text="差し替え枠", font=("Yu Gothic UI", 9)).pack(
                side="left", padx=(0, 6)
            )
            self._gm_combo_lineup_slot = ttk.Combobox(
                edit_row,
                state="readonly",
                width=10,
                values=list(self._gm_slot_labels),
            )
            self._gm_combo_lineup_slot.pack(side="left", padx=(0, 12))
            self._gm_combo_lineup_slot.bind(
                "<<ComboboxSelected>>",
                lambda _e: self._on_gm_slot_lineup_changed(),
            )
            ttk.Label(edit_row, text="候補", font=("Yu Gothic UI", 9)).pack(
                side="left", padx=(0, 6)
            )
            self._gm_combo_lineup_candidate = ttk.Combobox(
                edit_row,
                state="readonly",
                width=42,
            )
            self._gm_combo_lineup_candidate.pack(side="left", padx=(0, 12))
            self._gm_candidate_players: List[Any] = []
            self._gm_btn_apply_lineup_slot = ttk.Button(
                edit_row,
                text="反映（確認）",
                style="Primary.TButton",
                command=self._on_apply_gm_starting_slot,
            )
            self._gm_btn_apply_lineup_slot.pack(side="left")

            sixth_row = ttk.Frame(tab, style="Panel.TFrame", padding=(4, 6))
            sixth_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
            ttk.Label(sixth_row, text="6thマン", font=("Yu Gothic UI", 9)).pack(
                side="left", padx=(0, 6)
            )
            self._gm_combo_sixth = ttk.Combobox(sixth_row, state="readonly", width=44)
            self._gm_combo_sixth.pack(side="left", padx=(0, 10))
            self._gm_sixth_candidate_players: List[Any] = []
            self._gm_btn_apply_sixth = ttk.Button(
                sixth_row,
                text="6thを反映（確認）",
                style="Primary.TButton",
                command=self._on_apply_gm_sixth_man,
            )
            self._gm_btn_apply_sixth.pack(side="left", padx=(0, 8))
            ttk.Button(
                sixth_row,
                text="自動6thに戻す（確認）",
                style="Menu.TButton",
                command=self._on_reset_sixth_man_gui,
            ).pack(side="left")

            bench_row = ttk.Frame(tab, style="Panel.TFrame", padding=(4, 6))
            bench_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            ttk.Label(bench_row, text="ベンチ入替", font=("Yu Gothic UI", 9)).pack(
                side="left", padx=(0, 6)
            )
            self._gm_combo_bench_a = ttk.Combobox(bench_row, state="readonly", width=28)
            self._gm_combo_bench_a.pack(side="left", padx=(0, 6))
            ttk.Label(bench_row, text="⇔", font=("Yu Gothic UI", 9)).pack(side="left", padx=4)
            self._gm_combo_bench_b = ttk.Combobox(bench_row, state="readonly", width=28)
            self._gm_combo_bench_b.pack(side="left", padx=(0, 10))
            self._gm_bench_players: List[Any] = []
            self._gm_btn_bench_swap = ttk.Button(
                bench_row,
                text="入替（確認）",
                style="Primary.TButton",
                command=self._on_apply_gm_bench_swap,
            )
            self._gm_btn_bench_swap.pack(side="left", padx=(0, 8))
            ttk.Button(
                bench_row,
                text="自動ベンチに戻す（確認）",
                style="Menu.TButton",
                command=self._on_reset_bench_order_gui,
            ).pack(side="left")

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
            txt.grid(row=3, column=0, sticky="nsew")
            vsb.grid(row=3, column=1, sticky="ns")
            hsb.grid(row=4, column=0, columnspan=2, sticky="ew")

            btn_row = ttk.Frame(tab, style="Panel.TFrame", padding=(8, 4))
            btn_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))
            ttk.Button(
                btn_row,
                text="自動スタメンに戻す（確認）",
                style="Menu.TButton",
                command=self._on_reset_starting_lineup_gui,
            ).pack(side="left", padx=(0, 8))
            ttk.Label(
                btn_row,
                text="スタメン／6th／ベンチは上段。解除ボタンはカスタム設定のリセット。トレード等はCLI。",
                font=("Yu Gothic UI", 9),
            ).pack(side="left")

            self._gm_text_lineup = txt

        self._gm_text_team = _make_tab("チーム情報")
        self._gm_text_cap = _make_tab("サラリーキャップ")
        self._gm_text_roster = _make_tab("ロスター")
        _make_lineup_tab()

        tab_st = ttk.Frame(nb, style="Root.TFrame", padding=14)
        nb.add(tab_st, text="戦術・HC・起用")
        tab_st.columnconfigure(1, weight=1)

        self._gm_label_to_key_strategy = {lab: k for k, lab in STRATEGY_OPTIONS}
        self._gm_label_to_key_coach = {lab: k for k, lab in COACH_STYLE_OPTIONS}
        self._gm_label_to_key_usage = {lab: k for k, lab in USAGE_POLICY_OPTIONS}

        def _strategy_row(row: int, label: str, combo: ttk.Combobox) -> None:
            ttk.Label(tab_st, text=label).grid(row=row, column=0, sticky="w", pady=6)
            combo.grid(row=row, column=1, sticky="ew", pady=6, padx=(12, 0))

        self._combo_strategy = ttk.Combobox(
            tab_st,
            state="readonly",
            width=34,
            values=[lab for _, lab in STRATEGY_OPTIONS],
        )
        _strategy_row(0, "戦術", self._combo_strategy)

        self._combo_coach = ttk.Combobox(
            tab_st,
            state="readonly",
            width=34,
            values=[lab for _, lab in COACH_STYLE_OPTIONS],
        )
        _strategy_row(1, "HCスタイル", self._combo_coach)
        self._combo_coach.bind("<<ComboboxSelected>>", self._on_gm_coach_selection_changed)

        self._combo_usage = ttk.Combobox(
            tab_st,
            state="readonly",
            width=34,
            values=[lab for _, lab in USAGE_POLICY_OPTIONS],
        )
        _strategy_row(2, "起用方針", self._combo_usage)

        self._gm_coach_preview_text = tk.Text(
            tab_st,
            wrap="word",
            bg="#222834",
            fg="#e8ecf0",
            insertbackground="#e8ecf0",
            font=("Consolas", 10),
            relief="flat",
            height=9,
            padx=10,
            pady=10,
        )
        self._gm_coach_preview_text.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        tab_st.rowconfigure(3, weight=1)

        ttk.Button(
            tab_st,
            text="設定を反映",
            style="Primary.TButton",
            command=self._on_apply_gm_strategy,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(
            bottom,
            text="トレード・FA（ターミナル案内）",
            style="Menu.TButton",
            command=self._on_gm_cli_trade_fa_hint,
        ).pack(side="left")
        ttk.Button(bottom, text="閉じる", style="Menu.TButton", command=self._on_close_gm_window).pack(
            side="right"
        )

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
        if key == "GM":
            cb = self.menu_callbacks.get("GM")
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
            self.on_advance()
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
            number = int(value)
            return f"¥{number:,}"
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
            number = int(value)
            return f"{number:+,}円"
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
            hint = round_month_label(self.season, nxt)
            return {
                "home_team": ht,
                "away_team": at,
                "round_name": f"ラウンド{nxt}",
                "game_type": competition_display_name(ct),
                "schedule_date_hint": hint,
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
        task_count = len(self._get_tasks())
        if money is not None:
            return f"補足: 資金 {self._format_money(money)} / オーナー信頼 {trust} / 要対応 {task_count}件"
        return f"補足: オーナー信頼 {trust} / 要対応 {task_count}件"

    # ------------------------------------------------------------------
    # Right column helpers
    # ------------------------------------------------------------------
    def _get_tasks(self) -> List[str]:
        if self.external_tasks is not None:
            return list(self.external_tasks)

        tasks: List[str] = []

        count = self._safe_get(self.team, "facility_upgrade_points", None)
        if isinstance(count, (int, float)) and count > 0:
            tasks.append(f"施設投資ポイントが {int(count)} 点あります")

        fa_targets = self._safe_get(self.team, "fa_shortlist", None)
        if isinstance(fa_targets, list) and fa_targets:
            tasks.append(f"FA候補が {len(fa_targets)} 件あります")

        mission = self._safe_get(self.team, "owner_mission", None)
        if mission:
            tasks.append(f"オーナーミッション確認: {mission}")

        injured = [p for p in self._safe_get(self.team, "players", []) if self._is_injured_player(p)]
        if injured:
            tasks.append(f"負傷者が {len(injured)} 名います")

        if not tasks:
            tasks.append("特に緊急案件はありません")
        return tasks

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
) -> MainMenuView:
    """
    Convenience launcher used by future main.py wiring.
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
