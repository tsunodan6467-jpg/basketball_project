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

import tkinter as tk
from tkinter import ttk, messagebox
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
from basketball_sim.utils.user_settings import (
    KEY_ACTION_CLOSE_SUBWINDOW,
    apply_tk_window_settings,
    load_user_settings,
    tk_binding_for,
)


MenuCallback = Callable[[], None]
AdvanceCallback = Callable[[], None]


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
    ) -> None:
        self.team = team
        self.season = season
        self.on_advance = on_advance
        self.menu_callbacks = menu_callbacks or {}
        self.external_news_items = news_items
        self.external_tasks = tasks

        self.root = root or tk.Tk()
        self.root.title(title)
        cfg = user_settings if user_settings is not None else load_user_settings()
        apply_tk_window_settings(self.root, cfg)
        self.root.configure(bg="#15171c")

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._configure_styles()
        self._build_ui()
        self.refresh()
        _close_seq = tk_binding_for(cfg, KEY_ACTION_CLOSE_SUBWINDOW, "<Escape>")
        self.root.bind(_close_seq, self._on_close_subwindow_hotkey)

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
        self._refresh_advance_button()

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
                "試合日程を読み込めていません",
                "HOME/AWAY: -",
                "相手情報: -",
                "補足: 日程画面実装後に詳細連携予定",
            ]

        game_type = self._first_non_empty(
            self._safe_get(next_game, "game_type", None),
            self._safe_get(next_game, "match_type", None),
            "リーグ戦",
        )
        game_round = self._first_non_empty(
            self._safe_get(next_game, "round_name", None),
            self._safe_get(next_game, "round", None),
            self._safe_get(next_game, "section", None),
            "-",
        )
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

        venue_text = "HOME" if user_is_home else "AWAY"
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
        window.geometry("980x700")
        window.minsize(860, 600)
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
        self.owner_lines = self._make_line_vars(self.owner_panel, 6)
        self.finance_report_lines = self._make_line_vars(self.finance_report_panel, 8)

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
            command=window.destroy,
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

        arena = self._safe_get(self.team, "arena_level", profile.get("arena_level", 1))
        training = self._safe_get(self.team, "training_facility_level", profile.get("training_facility_level", 1))
        medical = self._safe_get(self.team, "medical_facility_level", profile.get("medical_facility_level", 1))
        front = self._safe_get(self.team, "front_office_level", profile.get("front_office_level", 1))
        market_size = self._safe_get(self.team, "market_size", profile.get("market_size", 1.0))
        fan_base = self._safe_get(self.team, "fan_base", profile.get("fan_base", 0))
        season_tickets = self._safe_get(self.team, "season_ticket_base", profile.get("season_ticket_base", 0))
        sponsor_power = self._safe_get(self.team, "sponsor_power", profile.get("sponsor_power", 0))

        facility_lines = [
            f"アリーナ: Lv{self._safe_int_text(arena)}",
            f"育成施設: Lv{self._safe_int_text(training)}",
            f"メディカル: Lv{self._safe_int_text(medical)}",
            f"フロント: Lv{self._safe_int_text(front)}",
            f"市場規模: {market_size}",
            f"ファン基盤: {self._safe_int_text(fan_base)} / シーズン券: {self._safe_int_text(season_tickets)} / スポンサー力: {self._safe_int_text(sponsor_power)}",
        ]
        for var, line in zip(self.facility_lines, facility_lines):
            var.set(line)

        owner_expectation = self._safe_get(self.team, "owner_expectation", profile.get("owner_expectation", "-"))
        owner_trust = self._safe_get(self.team, "owner_trust", profile.get("owner_trust", "-"))
        missions = list(self._safe_get(self.team, "owner_missions", []) or [])
        mission_1 = missions[0].get("title", "-") if len(missions) >= 1 and isinstance(missions[0], dict) else "-"
        mission_2 = missions[1].get("title", "-") if len(missions) >= 2 and isinstance(missions[1], dict) else "-"
        latest_mission_result = "-"
        mission_history = list(self._safe_get(self.team, "owner_mission_history", []) or [])
        if mission_history and isinstance(mission_history[-1], dict):
            latest_mission_result = str(mission_history[-1].get("result_summary", "-"))

        owner_lines = [
            f"オーナー期待値: {owner_expectation}",
            f"オーナー信頼: {self._safe_int_text(owner_trust)} / 100",
            f"アクティブ案件1: {mission_1}",
            f"アクティブ案件2: {mission_2}",
            f"直近評価: {latest_mission_result}",
            f"補足: 財務・施設・成績が信頼度に影響します",
        ]
        for var, line in zip(self.owner_lines, owner_lines):
            var.set(line)

        report_text = ""
        report_getter = getattr(self.team, "get_finance_report_text", None)
        if callable(report_getter):
            try:
                report_text = str(report_getter() or "")
            except Exception:
                report_text = ""

        report_lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        if not report_lines:
            report_lines = [
                "詳細レポート未生成",
                f"所持金: {self._format_money(money)}",
                f"年俸予算: {self._format_money(budget)}",
                f"人気: {self._safe_int_text(popularity)}",
                f"前季収支: {self._format_signed_money(cashflow)}",
            ]
        while len(report_lines) < len(self.finance_report_lines):
            report_lines.append("")
        for var, line in zip(self.finance_report_lines, report_lines[: len(self.finance_report_lines)]):
            var.set(line)

        self.finance_hint_var.set(
            "読み取り専用の経営画面です。施設投資や予算操作は後続フェーズで安全に接続します。"
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
        window.title(f"戦術・起用 - {self._team_name()}")
        window.geometry("980x680")
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

        self.strategy_header_var.set(f"{self._team_name()} 戦術・起用状況")

        strategy_lines = [
            f"チーム戦術: {strategy_text}",
            f"HCスタイル: {coach_text}",
            f"起用方針: {usage_text}",
            f"ロスター人数: {len(list(self._safe_get(self.team, 'players', []) or []))}",
            f"先発人数: {len(starters)} / ベンチ序列人数: {len(bench_order)}",
            f"補足: 現在は読み取り専用です",
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
            "strategy / coach_style / usage_policy / get_starting_five() / get_sixth_man() / get_bench_order_players() を表示しています。"
        )

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


    def open_information_window(self) -> None:
        """Open a safe read-only season information subwindow."""
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
        window.title(f"情報 - シーズン進行 / 順位表 / 日程 ({self._team_name()})")
        window.geometry("1180x760")
        window.minsize(980, 660)
        window.configure(bg="#15171c")
        try:
            window.transient(self.root)
        except Exception:
            pass

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 12))

        self.information_header_var = tk.StringVar(value="")
        ttk.Label(
            header,
            textvariable=self.information_header_var,
            style="TopBar.TLabel",
            anchor="w",
        ).pack(fill="x")

        top = ttk.Frame(outer, style="Root.TFrame")
        top.pack(fill="x", pady=(0, 12))
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        self.info_progress_panel = self._create_panel(top, "シーズン進行")
        self.info_progress_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info_schedule_panel = self._create_panel(top, "次ラウンド予定")
        self.info_schedule_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        middle = ttk.Frame(outer, style="Root.TFrame")
        middle.pack(fill="x", pady=(0, 12))
        middle.columnconfigure(0, weight=1)
        middle.columnconfigure(1, weight=1)
        middle.columnconfigure(2, weight=1)

        self.info_d1_panel = self._create_panel(middle, "D1順位表")
        self.info_d1_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info_d2_panel = self._create_panel(middle, "D2順位表")
        self.info_d2_panel.grid(row=0, column=1, sticky="nsew", padx=8)
        self.info_d3_panel = self._create_panel(middle, "D3順位表")
        self.info_d3_panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        self.info_comp_panel = self._create_panel(outer, "大会進行状況")
        self.info_comp_panel.pack(fill="x")

        self.info_progress_lines = self._make_line_vars(self.info_progress_panel, 7)
        self.info_schedule_lines = self._make_line_vars(self.info_schedule_panel, 8)
        self.info_d1_lines = self._make_line_vars(self.info_d1_panel, 10)
        self.info_d2_lines = self._make_line_vars(self.info_d2_panel, 10)
        self.info_d3_lines = self._make_line_vars(self.info_d3_panel, 10)
        self.info_comp_lines = self._make_line_vars(self.info_comp_panel, 8)

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

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

    def _refresh_information_window(self) -> None:
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
        for var, line in zip(self.info_progress_lines, progress_lines):
            var.set(line)

        schedule_lines = self._build_information_schedule_lines()
        while len(schedule_lines) < len(self.info_schedule_lines):
            schedule_lines.append("")
        for var, line in zip(self.info_schedule_lines, schedule_lines[: len(self.info_schedule_lines)]):
            var.set(line)

        d1_lines = self._build_information_standings_lines(1)
        d2_lines = self._build_information_standings_lines(2)
        d3_lines = self._build_information_standings_lines(3)
        for vars_list, lines in (
            (self.info_d1_lines, d1_lines),
            (self.info_d2_lines, d2_lines),
            (self.info_d3_lines, d3_lines),
        ):
            while len(lines) < len(vars_list):
                lines.append("")
            for var, line in zip(vars_list, lines[: len(vars_list)]):
                var.set(line)

        comp_lines = self._build_information_competition_lines()
        while len(comp_lines) < len(self.info_comp_lines):
            comp_lines.append("")
        for var, line in zip(self.info_comp_lines, comp_lines[: len(self.info_comp_lines)]):
            var.set(line)

        self.information_hint_var.set(
            "読み取り専用の情報画面です。シーズン進行 / 順位表 / 次ラウンド予定 / カップ戦進行を確認できます。"
            " トレード／インシーズンFAの期限は消化ラウンド22以降でロック（3月第2週終了相当）。"
        )

    def _build_information_schedule_lines(self) -> List[str]:
        next_round = self._safe_int(self._safe_get(self.season, "current_round", 0)) + 1
        events = []
        getter = getattr(self.season, "get_events_for_round", None)
        if callable(getter):
            try:
                events = list(getter(next_round) or [])
            except Exception:
                events = []

        lines = [f"次ラウンド: {next_round}"]
        if not events:
            lines.append("予定試合は取得できませんでした")
            lines.append("補足: phaseや日程状態により空のことがあります")
            return lines

        added = 0
        for event in events:
            matchup = self._format_season_event_matchup(event)
            if matchup:
                lines.append(matchup)
                added += 1
            if added >= 7:
                break

        if added == 0:
            lines.append("試合予定はあるが対戦カードを整形できませんでした")
        return lines

    def _build_information_standings_lines(self, level: int) -> List[str]:
        teams = self._get_league_teams_for_level(level)
        if not teams:
            return [f"D{level}: データなし"]

        standings = teams
        getter = getattr(self.season, "get_standings", None)
        if callable(getter):
            try:
                standings = list(getter(teams) or teams)
            except Exception:
                standings = teams

        lines = []
        for idx, team in enumerate(standings[:9], start=1):
            name = str(self._safe_get(team, "name", "-"))
            wins = self._safe_int(self._safe_get(team, "regular_wins", 0))
            losses = self._safe_int(self._safe_get(team, "regular_losses", 0))
            marker = " ←自クラブ" if name == self._team_name() else ""
            lines.append(f"{idx}. {name} {wins}勝{losses}敗{marker}")
        return lines

    def _build_information_competition_lines(self) -> List[str]:
        lines = []

        emperor_enabled = bool(self._safe_get(self.season, "emperor_cup_enabled", False))
        emperor_logs = self._safe_get(self.season, "emperor_cup_stage_logs", {}) or {}
        emperor_stage = self._latest_stage_name(emperor_logs) if emperor_enabled else "-"
        emperor_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "emperor_cup_results", {}), "champion", None)
        )
        lines.append(
            f"天皇杯: {'開催中' if emperor_enabled else '未開催'} / 現在段階: {emperor_stage} / 優勝: {emperor_champion}"
        )

        easl_enabled = bool(self._safe_get(self.season, "easl_enabled", False))
        easl_logs = self._safe_get(self.season, "easl_stage_logs", {}) or {}
        easl_stage = self._latest_stage_name(easl_logs) if easl_enabled else "-"
        easl_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "easl_results", {}), "champion", None)
        )
        lines.append(
            f"EASL: {'開催中' if easl_enabled else '未開催'} / 現在段階: {easl_stage} / 優勝: {easl_champion}"
        )

        acl_enabled = bool(self._safe_get(self.season, "acl_enabled", False))
        acl_logs = self._safe_get(self.season, "acl_stage_logs", {}) or {}
        acl_stage = self._latest_stage_name(acl_logs) if acl_enabled else "-"
        acl_champion = self._resolve_team_name(
            self._safe_get(self._safe_get(self.season, "acl_results", {}), "champion", None)
        )
        lines.append(
            f"ACL: {'開催中' if acl_enabled else '未開催'} / 現在段階: {acl_stage} / 優勝: {acl_champion}"
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

    def _format_season_event_matchup(self, event: Any) -> str:
        home = self._resolve_team_name(
            self._first_non_empty(
                self._safe_get(event, "home_team", None),
                self._safe_get(event, "team1", None),
            )
        )
        away = self._resolve_team_name(
            self._first_non_empty(
                self._safe_get(event, "away_team", None),
                self._safe_get(event, "team2", None),
            )
        )
        if home != "-" and away != "-":
            comp = self._first_non_empty(
                self._safe_get(event, "competition_name", None),
                self._safe_get(event, "label", None),
                self._safe_get(event, "event_type", None),
                "",
            )
            prefix = f"[{comp}] " if comp else ""
            return f"{prefix}{home} vs {away}"

        title = self._first_non_empty(
            self._safe_get(event, "title", None),
            self._safe_get(event, "name", None),
            self._safe_get(event, "description", None),
        )
        return str(title) if title is not None else ""

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
        window.geometry("1120x820")
        window.minsize(920, 680)
        window.configure(bg="#15171c")
        window.protocol("WM_DELETE_WINDOW", self._close_history_window)
        self._history_window = window

        outer = ttk.Frame(window, style="Root.TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        self.history_header_var = tk.StringVar(value="")
        self.history_hint_var = tk.StringVar(value="")

        ttk.Label(
            outer,
            textvariable=self.history_header_var,
            style="SectionTitle.TLabel",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(
            outer,
            textvariable=self.history_hint_var,
            background="#15171c",
            foreground="#d6dbe3",
            font=("Yu Gothic UI", 10),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        text_wrap = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        text_wrap.grid(row=2, column=0, sticky="nsew")
        text_wrap.columnconfigure(0, weight=1)
        text_wrap.rowconfigure(0, weight=1)

        self.history_text = tk.Text(
            text_wrap,
            wrap="word",
            bg="#222834",
            fg="#eef3f8",
            insertbackground="#eef3f8",
            relief="flat",
            font=("Yu Gothic UI", 10),
            padx=10,
            pady=10,
        )
        self.history_text.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.history_text.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.history_text.configure(yscrollcommand=yscroll.set)

        self._refresh_history_window()

    def _close_history_window(self) -> None:
        window = getattr(self, "_history_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        finally:
            self._history_window = None
            self.history_text = None

    def _refresh_history_window(self) -> None:
        if getattr(self, "history_header_var", None) is None:
            return

        self.history_header_var.set(f"{self._team_name()} 歴史")
        self.history_hint_var.set(
            "読み取り専用の歴史画面です。クラブ史レポート / 最近の流れ / 最近のシーズン / マイルストーン / 近年の象徴的トピック / クラブ表彰 / クラブレジェンドを確認できます。"
        )

        lines = self._build_history_report_lines()
        history_text = getattr(self, "history_text", None)
        if history_text is None:
            return

        history_text.configure(state="normal")
        history_text.delete("1.0", "end")
        history_text.insert("1.0", "\n".join(lines))
        history_text.configure(state="disabled")

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
        coach = str(getattr(team, "coach_style", "balanced") or "balanced")
        tf = int(getattr(team, "training_facility_level", 1) or 1)
        fo = int(getattr(team, "front_office_level", 1) or 1)
        med = int(getattr(team, "medical_facility_level", 1) or 1)
        if drill_key == "speed_agility" and tf < 3:
            return "トレーニング施設Lv3以上で解放"
        if drill_key == "iq_film" and fo < 2:
            return "フロントオフィスLv2以上で解放"
        if drill_key == "defense_footwork" and coach not in {"defense", "development"}:
            return "HCが「守備重視」または「育成」で解放"
        if drill_key == "strength" and med < 2:
            return "メディカル施設Lv2以上で解放"
        return ""

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
        if not candidates:
            return None

        user_name = self._team_name()
        current_date = self._get_current_date()

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
        if venue_text == "HOME":
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
