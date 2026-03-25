"""
Minimal 2D spectate UI for Basketball Project.

Safe improvements in this version
---------------------------------
- Keeps all previously working spectate features
- Adds safe player slide animation between plays
- Players move slightly from previous layout to current layout instead of popping
- Animation is intentionally short and simple to avoid breaking the current structure
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from basketball_sim.systems.presentation_layer import PresentationLayer
from basketball_sim.systems.highlight_camera_system import HighlightCameraSystem


class SpectateView:
    def __init__(
        self,
        match: Any,
        width: int = 1100,
        height: int = 760,
        autoplay_interval_ms: int = 1150,
        override_events: Optional[list[dict]] = None,
        spectate_mode: str = "full",
    ) -> None:
        self.match = match
        self.width = width
        self.height = height
        self.autoplay_interval_ms = autoplay_interval_ms
        self.spectate_mode = str(spectate_mode or "full").strip().lower()

        self.root = tk.Tk()
        self.root.title("Basketball Project - Spectate View")
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(980, 680)

        self.is_autoplay = self.spectate_mode == "result_only"
        self.finished = False

        self.current_play: Optional[dict] = None
        self.current_commentary: str = "観戦を開始してください。"
        self.current_play_index: int = -1

        self.top_play_overlay_frames_remaining: int = 0
        self.top_play_overlay_default_frames: int = 28
        self.top_play_slow_frames_remaining: int = 0
        self.top_play_slow_default_frames: int = 14
        self.top_play_flash_frames_remaining: int = 0
        self.top_play_flash_default_frames: int = 3

        self.score_flash_frames_remaining: int = 0
        self.score_flash_default_frames: int = 5
        self.score_flash_team_side: Optional[str] = None

        self.period_flash_frames_remaining: int = 0
        self.period_flash_default_frames: int = 10
        self.period_flash_text: str = ""

        self.presentation_layer: Optional[PresentationLayer]
        self.presentation_event_index: int = 0
        if override_events is not None:
            self.presentation_layer = None
            self.presentation_events = [dict(event) for event in override_events if isinstance(event, dict)]
        else:
            self.presentation_layer = PresentationLayer(match)
            self.presentation_events = self.presentation_layer.build()
        self.current_presentation_event: Optional[dict] = None

        self.camera_system = HighlightCameraSystem(self.presentation_events)
        self.camera_events = self.camera_system.build()
        self.current_camera_event: Optional[dict] = None
        self.locked_camera_focus_name: Optional[str] = None
        self.locked_camera_track_mode: str = "team_shape"

        self.total_plays: int = self._get_total_plays()

        # Ball pass animation state
        self.ball_anim_active = False
        self.ball_anim_from_name: Optional[str] = None
        self.ball_anim_to_name: Optional[str] = None
        self.ball_anim_progress: float = 0.0
        self.ball_anim_steps: int = 10
        self.ball_anim_step_index: int = 0
        self.ball_anim_interval_ms: int = 38
        self.pending_shot_event_after_pass: Optional[dict] = None

        # Shot animation state
        self.shot_anim_active = False
        self.shot_anim_from_name: Optional[str] = None
        self.shot_anim_team_side: Optional[str] = None
        self.shot_anim_progress: float = 0.0
        self.shot_anim_steps: int = 12
        self.shot_anim_step_index: int = 0
        self.shot_anim_interval_ms: int = 34
        self.shot_anim_result: Optional[str] = None
        self.shot_anim_presentation_type: Optional[str] = None
        self.pending_rebound_after_shot: bool = False
        self.pending_rebound_to_name: Optional[str] = None

        # Rebound animation state
        self.rebound_anim_active = False
        self.rebound_anim_team_side: Optional[str] = None
        self.rebound_anim_progress: float = 0.0
        self.rebound_anim_steps: int = 10
        self.rebound_anim_step_index: int = 0
        self.rebound_anim_interval_ms: int = 36
        self.rebound_anim_to_name: Optional[str] = None
        self.rebound_anim_presentation_type: Optional[str] = None
        self.rebound_hold_owner_name: Optional[str] = None

        # Made-shot ball hold state (keep ball at rim/net area and do not snap back to shooter)
        self.made_shot_hold_active = False
        self.made_shot_hold_team_side: Optional[str] = None
        self.made_shot_hold_camera_dx: Optional[float] = None
        self.last_camera_focus_dx: float = 0.0
        self.last_court_bounds: Optional[tuple[float, float, float, float]] = None

        # Player slide animation state
        self.player_anim_active = False
        self.player_anim_progress: float = 0.0
        self.player_anim_steps: int = 8
        self.player_anim_step_index: int = 0
        self.player_anim_interval_ms: int = 32
        self.prev_player_positions: dict[str, tuple[float, float]] = {}
        self.current_player_positions: dict[str, tuple[float, float]] = {}
        self.special_package_button_rect: Optional[tuple[float, float, float, float]] = None

        # Dribble animation state
        self.dribble_phase: float = 0.0
        self.dribble_direction: int = 1
        self.dribble_step: float = 0.18
        self.dribble_max_phase: float = 1.0

        self._reset_match_cursors()
        self._build_ui()
        self._bind_keys()
        self._schedule_idle_animation()
        self._refresh_view()

    # =========================================================
    # Mode helpers
    # =========================================================
    def _is_result_only_mode(self) -> bool:
        return self.spectate_mode == "result_only"

    def _is_score_make_presentation(self, event: Optional[dict]) -> bool:
        if not isinstance(event, dict):
            return False
        ptype = str(event.get("presentation_type") or "")
        return ptype in {"score_make_2", "score_make_3", "score_make_ft"}

    def _extract_event_team_side(self, event: Optional[dict]) -> Optional[str]:
        if not isinstance(event, dict):
            return None
        team_side = event.get("team_side")
        if team_side in {"home", "away"}:
            return team_side
        raw_play = event.get("raw_play")
        if isinstance(raw_play, dict):
            for key in ("scoring_team", "team", "offense_team_side", "defense_team_side"):
                value = raw_play.get(key)
                if value in {"home", "away"}:
                    return value
        for key in ("offense_team_side", "defense_team_side"):
            value = event.get(key)
            if value in {"home", "away"}:
                return value
        return None

    def _trigger_score_flash_from_event(self, event: Optional[dict]) -> None:
        if not self._is_score_make_presentation(event):
            return
        self.score_flash_frames_remaining = self.score_flash_default_frames
        self.score_flash_team_side = self._extract_event_team_side(event)

    def _is_period_boundary_presentation(self, event: Optional[dict]) -> bool:
        if not isinstance(event, dict):
            return False
        ptype = str(event.get("presentation_type") or "")
        return ptype in {"quarter_start", "quarter_end"}

    def _build_period_flash_text(self, event: Optional[dict]) -> str:
        if not isinstance(event, dict):
            return ""
        ptype = str(event.get("presentation_type") or "")
        quarter = event.get("quarter")
        if ptype == "quarter_start":
            if isinstance(quarter, int) and quarter <= 4:
                return f"第{quarter}クォーター"
            if isinstance(quarter, int) and quarter >= 5:
                return "延長戦"
            return "試合再開"
        if ptype == "quarter_end":
            if isinstance(quarter, int) and quarter <= 4:
                return f"第{quarter}クォーター終了"
            if isinstance(quarter, int) and quarter >= 5:
                return "延長終了"
            return "クォーター終了"
        return ""

    def _trigger_period_flash_from_event(self, event: Optional[dict]) -> None:
        if not self._is_period_boundary_presentation(event):
            return
        text = self._build_period_flash_text(event)
        if not text:
            return
        self.period_flash_frames_remaining = self.period_flash_default_frames
        self.period_flash_text = text

    # =========================================================
    # Public API
    # =========================================================
    def run(self) -> None:
        self.root.mainloop()

    # =========================================================
    # UI build
    # =========================================================
    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top_frame = ttk.Frame(self.root, padding=12)
        top_frame.grid(row=0, column=0, sticky="ew")
        for i in range(3):
            top_frame.columnconfigure(i, weight=1)

        self.home_team_var = tk.StringVar(value="HOME")
        self.away_team_var = tk.StringVar(value="AWAY")
        self.score_var = tk.StringVar(value="0 - 0")
        self.period_var = tk.StringVar(value="Q1 10:00")
        self.play_info_var = tk.StringVar(value="Play 0 / 0")
        self.status_var = tk.StringVar(value="MANUAL")

        ttk.Label(
            top_frame, textvariable=self.home_team_var, anchor="center",
            font=("Yu Gothic UI", 20, "bold")
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            top_frame, textvariable=self.score_var, anchor="center",
            font=("Yu Gothic UI", 24, "bold")
        ).grid(row=0, column=1, sticky="ew")
        ttk.Label(
            top_frame, textvariable=self.away_team_var, anchor="center",
            font=("Yu Gothic UI", 20, "bold")
        ).grid(row=0, column=2, sticky="ew")

        info_frame = ttk.Frame(top_frame)
        info_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        for i in range(3):
            info_frame.columnconfigure(i, weight=1)

        ttk.Label(
            info_frame, textvariable=self.period_var, anchor="center",
            font=("Yu Gothic UI", 13)
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            info_frame, textvariable=self.play_info_var, anchor="center",
            font=("Yu Gothic UI", 13)
        ).grid(row=0, column=1, sticky="ew")
        ttk.Label(
            info_frame, textvariable=self.status_var, anchor="center",
            font=("Yu Gothic UI", 13)
        ).grid(row=0, column=2, sticky="ew")

        center_frame = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        center_frame.grid(row=1, column=0, sticky="nsew")
        center_frame.columnconfigure(0, weight=1)
        center_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(center_frame, bg="#dcb27d", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        bottom_frame = ttk.Frame(self.root, padding=12)
        bottom_frame.grid(row=2, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        ttk.Label(bottom_frame, text="実況", font=("Yu Gothic UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        self.commentary_var = tk.StringVar(value=self.current_commentary)
        ttk.Label(
            bottom_frame,
            textvariable=self.commentary_var,
            wraplength=max(700, self.width - 120),
            justify="left",
            font=("Yu Gothic UI", 13),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

        controls = ttk.Frame(bottom_frame)
        controls.grid(row=2, column=0, sticky="ew")
        for i in range(4):
            controls.columnconfigure(i, weight=1)

        ttk.Button(controls, text="次のプレー (N)", command=self._advance_one_play).grid(row=0, column=0, padx=4, sticky="ew")
        ttk.Button(controls, text="自動再生 ON/OFF (A)", command=self._toggle_autoplay).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(controls, text="リセット (R)", command=self._reset_view_state).grid(row=0, column=2, padx=4, sticky="ew")
        ttk.Button(controls, text="閉じる (Esc)", command=self.root.destroy).grid(row=0, column=3, padx=4, sticky="ew")

        ttk.Label(
            bottom_frame,
            text="操作: N=次のプレー / A=自動再生ON-OFF / R=リセット / Esc=閉じる",
            font=("Yu Gothic UI", 10),
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))

        self.root.bind("<Configure>", self._on_resize)

    def _bind_keys(self) -> None:
        self.root.bind("<n>", lambda _e: self._advance_one_play())
        self.root.bind("<N>", lambda _e: self._advance_one_play())
        self.root.bind("<a>", lambda _e: self._toggle_autoplay())
        self.root.bind("<A>", lambda _e: self._toggle_autoplay())
        self.root.bind("<r>", lambda _e: self._reset_view_state())
        self.root.bind("<R>", lambda _e: self._reset_view_state())
        self.root.bind("<Escape>", lambda _e: self.root.destroy())

    def _on_canvas_click(self, event: tk.Event) -> None:
        if not self._is_special_package_event():
            return
        if self.special_package_button_rect is None:
            return

        x1, y1, x2, y2 = self.special_package_button_rect
        if not (x1 <= event.x <= x2 and y1 <= event.y <= y2):
            return

        current_ptype = ""
        if isinstance(self.current_presentation_event, dict):
            current_ptype = str(self.current_presentation_event.get("presentation_type") or "")

        if current_ptype == "highlight_outro":
            self.root.destroy()
            return

        self._advance_one_play()

    def _reset_presentation_cursor(self) -> None:
        self.presentation_event_index = 0
        if self.presentation_layer is not None:
            self.presentation_layer.reset_cursor()

    def _get_next_presentation_event(self) -> Optional[dict]:
        if self.presentation_layer is not None:
            return self.presentation_layer.get_next_event()

        if self.presentation_event_index < 0 or self.presentation_event_index >= len(self.presentation_events):
            return None

        event = self.presentation_events[self.presentation_event_index]
        self.presentation_event_index += 1
        return event


    # =========================================================
    # Match / presentation integration
    # =========================================================
    def _reset_match_cursors(self) -> None:
        if hasattr(self.match, "reset_play_cursor"):
            self.match.reset_play_cursor()
        if hasattr(self.match, "reset_commentary_cursor"):
            self.match.reset_commentary_cursor()
        self._reset_presentation_cursor()
        self.current_camera_event = None
        self.top_play_overlay_frames_remaining = 0
        self.top_play_slow_frames_remaining = 0
        self.top_play_flash_frames_remaining = 0
        self.score_flash_frames_remaining = 0
        self.score_flash_team_side = None
        self.period_flash_frames_remaining = 0
        self.period_flash_text = ""
        self._reset_ball_animation()
        self._reset_shot_animation()
        self._reset_rebound_animation()
        self.rebound_hold_owner_name = None
        self._reset_player_animation()
        self._reset_dribble_animation()

    def _get_total_plays(self) -> int:
        if self.presentation_events:
            return len(self.presentation_events)
        if hasattr(self.match, "get_play_sequence_log"):
            try:
                plays = self.match.get_play_sequence_log()
                return len(plays) if plays is not None else 0
            except Exception:
                return 0
        return 0

    def _advance_one_play(self) -> None:
        if self.finished:
            return

        previous_ball_owner = self._get_ball_owner_name()
        self.rebound_hold_owner_name = None
        self._reset_made_shot_hold()

        next_event = self._get_next_presentation_event()
        next_play = None
        next_commentary = None

        if next_event is not None:
            self.current_presentation_event = next_event
            self.current_play_index += 1

            if 0 <= self.current_play_index < len(self.camera_events):
                self.current_camera_event = self.camera_events[self.current_play_index]
            else:
                self.current_camera_event = None

            if isinstance(self.current_camera_event, dict):
                level = str(self.current_camera_event.get("camera_level", "normal"))
                if level == "top_play":
                    self.top_play_overlay_frames_remaining = self.top_play_overlay_default_frames
                    self.top_play_slow_frames_remaining = self.top_play_slow_default_frames
                    self.top_play_flash_frames_remaining = self.top_play_flash_default_frames
                else:
                    if self.top_play_overlay_frames_remaining > 0:
                        self.top_play_overlay_frames_remaining -= 1
                    if self.top_play_slow_frames_remaining > 0:
                        self.top_play_slow_frames_remaining -= 1
                    if self.top_play_flash_frames_remaining > 0:
                        self.top_play_flash_frames_remaining -= 1
            else:
                if self.top_play_overlay_frames_remaining > 0:
                    self.top_play_overlay_frames_remaining -= 1
                if self.top_play_slow_frames_remaining > 0:
                    self.top_play_slow_frames_remaining -= 1
                if self.top_play_flash_frames_remaining > 0:
                    self.top_play_flash_frames_remaining -= 1

            raw_play = next_event.get("raw_play")
            if isinstance(raw_play, dict):
                self.current_play = raw_play
            self.current_commentary = self._build_commentary_from_presentation(next_event)
            self._update_camera_lock_from_current_event()
            if self._is_result_only_mode():
                self._trigger_score_flash_from_event(next_event)
                self._trigger_period_flash_from_event(next_event)
        else:
            if hasattr(self.match, "get_next_play"):
                next_play = self.match.get_next_play()
            if hasattr(self.match, "get_next_commentary_entry"):
                next_commentary = self.match.get_next_commentary_entry()

            if next_play is None:
                self.finished = True
                self.is_autoplay = False
                self.status_var.set("END")
                if not next_commentary:
                    next_commentary = "試合の最後まで再生しました。"
            else:
                self.current_play = next_play
                self.current_play_index += 1

            if next_commentary:
                self.current_commentary = self._coerce_commentary_text(next_commentary)
            elif next_play is not None:
                self.current_commentary = self._fallback_commentary_from_play(next_play)
            elif self.finished:
                self.current_commentary = "試合の最後まで再生しました。"

            self.locked_camera_focus_name = None
            self.locked_camera_track_mode = "team_shape"

        if next_event is None and next_play is None:
            self.finished = True
            self.is_autoplay = False
            self.current_camera_event = None
            self.locked_camera_focus_name = None
            self.locked_camera_track_mode = "team_shape"
            self.top_play_overlay_frames_remaining = 0
            self.top_play_slow_frames_remaining = 0
            self.top_play_flash_frames_remaining = 0

        current_ball_owner = self._get_ball_owner_name()

        if self._is_result_only_mode():
            self._clear_pending_pass_shot()
            self._reset_ball_animation()
            self._reset_shot_animation()
            self._reset_rebound_animation()
            self._reset_player_animation()
        else:
            # Start player slide first from newly computed positions
            new_positions = self._compute_player_positions()
            self._maybe_start_player_animation(new_positions)

        if self._is_result_only_mode():
            pass
        elif next_event is not None and self._is_rebound_presentation(next_event):
            self._clear_pending_pass_shot()
            self._start_rebound_animation(next_event)
        elif next_event is not None and self._is_shot_presentation(next_event):
            if self._should_start_assist_pass_animation(next_event):
                self._start_assist_pass_animation(next_event)
            else:
                self._clear_pending_pass_shot()
                self._start_shot_animation(next_event)
        elif next_event is not None and self._is_block_or_steal_turnover_presentation(next_event):
            self._clear_pending_pass_shot()
            self._reset_ball_animation()
            self._reset_shot_animation()
            self._reset_rebound_animation()
        else:
            self._maybe_start_ball_animation(previous_ball_owner, current_ball_owner)

        self._refresh_view()

        if self.is_autoplay and not self.finished:
            self.root.after(self._get_current_autoplay_delay_ms(), self._autoplay_tick)

    def _autoplay_tick(self) -> None:
        if self.is_autoplay and not self.finished:
            self._advance_one_play()

    # =========================================================
    # Special package screens (highlight intro / outro)
    # =========================================================
    def _is_special_package_event(self) -> bool:
        if not isinstance(self.current_presentation_event, dict):
            return False
        ptype = str(self.current_presentation_event.get("presentation_type") or "")
        return ptype in {"highlight_intro", "highlight_outro"}

    def _draw_highlight_package_screen(self) -> None:
        event = self.current_presentation_event or {}
        ptype = str(event.get("presentation_type") or "")

        self.canvas.delete("all")
        self.special_package_button_rect = None

        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)

        # background
        self.canvas.create_rectangle(0, 0, w, h, width=0, fill="#0f172a")
        self.canvas.create_rectangle(24, 24, w - 24, h - 24, width=3, outline="#facc15")

        # soft panel bands
        self.canvas.create_rectangle(50, 80, w - 50, 170, width=0, fill="#1e293b")
        self.canvas.create_rectangle(70, 210, w - 70, h - 120, width=0, fill="#111827")

        home_name = self.home_team_var.get() or "HOME"
        away_name = self.away_team_var.get() or "AWAY"
        score_text = self.score_var.get() or "0 - 0"
        headline = str(event.get("headline") or "")
        main_text = str(event.get("main_text") or "")
        sub_text = str(event.get("sub_text") or "")

        if ptype == "highlight_intro":
            top_label = "HIGHLIGHT MODE"
            center_label = "VS"

            self.canvas.create_text(
                w / 2, 62,
                text=top_label,
                font=("Yu Gothic UI", 16, "bold"),
                fill="#facc15",
            )
            self.canvas.create_text(
                w / 2, 124,
                text=headline,
                font=("Yu Gothic UI", 28, "bold"),
                fill="#f8fafc",
            )

            left_x1, left_y1, left_x2, left_y2 = 95, 245, w / 2 - 80, h - 165
            right_x1, right_y1, right_x2, right_y2 = w / 2 + 80, 245, w - 95, h - 165

            self.canvas.create_rectangle(left_x1, left_y1, left_x2, left_y2, width=2, outline="#60a5fa")
            self.canvas.create_rectangle(right_x1, right_y1, right_x2, right_y2, width=2, outline="#f87171")

            self.canvas.create_oval(left_x1 + 35, left_y1 + 35, left_x1 + 135, left_y1 + 135, width=3, outline="#60a5fa")
            self.canvas.create_oval(right_x2 - 135, right_y1 + 35, right_x2 - 35, right_y1 + 135, width=3, outline="#f87171")

            self.canvas.create_text(
                left_x1 + 85, left_y1 + 85,
                text="HOME",
                font=("Yu Gothic UI", 14, "bold"),
                fill="#93c5fd",
            )
            self.canvas.create_text(
                right_x2 - 85, right_y1 + 85,
                text="AWAY",
                font=("Yu Gothic UI", 14, "bold"),
                fill="#fca5a5",
            )

            self.canvas.create_text(
                (left_x1 + left_x2) / 2, left_y1 + 185,
                text=home_name,
                font=("Yu Gothic UI", 24, "bold"),
                fill="#f8fafc",
            )
            self.canvas.create_text(
                (right_x1 + right_x2) / 2, right_y1 + 185,
                text=away_name,
                font=("Yu Gothic UI", 24, "bold"),
                fill="#f8fafc",
            )

            self.canvas.create_text(
                w / 2, h / 2 - 18,
                text=center_label,
                font=("Yu Gothic UI", 34, "bold"),
                fill="#facc15",
            )
            self.canvas.create_text(
                w / 2, h / 2 + 34,
                text="MATCHUP",
                font=("Yu Gothic UI", 20, "bold"),
                fill="#cbd5e1",
            )

        elif ptype == "highlight_outro":
            result_title_y = 56
            score_y = 110

            result_box_x1 = w / 2 - 170
            result_box_x2 = w / 2 + 170
            result_box_y1 = 44
            result_box_y2 = 144
            self.canvas.create_rectangle(
                result_box_x1, result_box_y1, result_box_x2, result_box_y2,
                width=0, fill="#1e293b"
            )

            self.canvas.create_text(
                w / 2, result_title_y,
                text="RESULT",
                font=("Yu Gothic UI", 30, "bold"),
                fill="#facc15",
            )
            self.canvas.create_text(
                w / 2, score_y,
                text=score_text,
                font=("Yu Gothic UI", 34, "bold"),
                fill="#f8fafc",
            )

            left_team_x = 220
            right_team_x = w - 220
            team_name_y = 96
            logo_center_y = 220

            self.canvas.create_text(
                left_team_x, team_name_y,
                text=home_name,
                font=("Yu Gothic UI", 23, "bold"),
                fill="#f8fafc",
            )
            self.canvas.create_text(
                right_team_x, team_name_y,
                text=away_name,
                font=("Yu Gothic UI", 23, "bold"),
                fill="#f8fafc",
            )

            left_logo_size = 124
            right_logo_size = 124
            self.canvas.create_rectangle(
                left_team_x - 90, logo_center_y - 62, left_team_x + 90, logo_center_y + 62,
                width=2, outline="#60a5fa"
            )
            self.canvas.create_oval(
                left_team_x - left_logo_size / 2, logo_center_y - left_logo_size / 2,
                left_team_x + left_logo_size / 2, logo_center_y + left_logo_size / 2,
                width=3, outline="#60a5fa"
            )
            self.canvas.create_text(
                left_team_x, logo_center_y,
                text="HOME",
                font=("Yu Gothic UI", 15, "bold"),
                fill="#93c5fd",
            )

            self.canvas.create_rectangle(
                right_team_x - 90, logo_center_y - 62, right_team_x + 90, logo_center_y + 62,
                width=2, outline="#f87171"
            )
            self.canvas.create_oval(
                right_team_x - right_logo_size / 2, logo_center_y - right_logo_size / 2,
                right_team_x + right_logo_size / 2, logo_center_y + right_logo_size / 2,
                width=3, outline="#f87171"
            )
            self.canvas.create_text(
                right_team_x, logo_center_y,
                text="AWAY",
                font=("Yu Gothic UI", 15, "bold"),
                fill="#fca5a5",
            )

            quarter_title_y = 174
            row_start_y = 210
            row_h = 27
            quarter_summary = event.get("quarter_score_summary")

            self.canvas.create_text(
                w / 2, quarter_title_y,
                text="クォーター内容",
                font=("Yu Gothic UI", 16, "bold"),
                fill="#e5e7eb",
            )

            if isinstance(quarter_summary, list) and quarter_summary:
                for idx, row in enumerate(quarter_summary[:6]):
                    q = row.get("quarter", "-")
                    home_q = row.get("home", 0)
                    away_q = row.get("away", 0)
                    q_label = f"Q{q}" if isinstance(q, int) and q <= 4 else ("OT" if isinstance(q, int) else str(q))
                    y = row_start_y + row_h * idx

                    self.canvas.create_text(
                        w / 2 - 66, y,
                        text=q_label,
                        font=("Yu Gothic UI", 13, "bold"),
                        fill="#cbd5e1",
                    )
                    self.canvas.create_text(
                        w / 2 + 18, y,
                        text=f"{home_q}-{away_q}",
                        font=("Yu Gothic UI", 16, "bold"),
                        fill="#f8fafc",
                    )

            summary_y = 336
            if main_text:
                self.canvas.create_text(
                    w / 2, summary_y,
                    text=main_text,
                    font=("Yu Gothic UI", 16, "bold"),
                    fill="#f8fafc",
                    width=w - 220,
                )

            if sub_text:
                self.canvas.create_text(
                    w / 2, 366,
                    text=sub_text,
                    font=("Yu Gothic UI", 12),
                    fill="#cbd5e1",
                    width=w - 220,
                )

        button_w = 190
        button_h = 42
        button_y2 = h - 34
        button_y1 = button_y2 - button_h
        button_x1 = w / 2 - button_w / 2
        button_x2 = w / 2 + button_w / 2
        self.special_package_button_rect = (button_x1, button_y1, button_x2, button_y2)

        self.canvas.create_rectangle(
            button_x1,
            button_y1,
            button_x2,
            button_y2,
            width=2,
            outline="#facc15",
            fill="#111827",
        )
        self.canvas.create_text(
            w / 2,
            (button_y1 + button_y2) / 2,
            text="次へ進む",
            font=("Yu Gothic UI", 13, "bold"),
            fill="#facc15",
        )

    # =========================================================
    # Drawing / view refresh
    # =========================================================
    def _refresh_view(self) -> None:
        self.home_team_var.set(self._extract_team_name("home"))
        self.away_team_var.set(self._extract_team_name("away"))
        self.score_var.set(self._extract_score_text())
        self.period_var.set(self._extract_period_text())
        self.play_info_var.set(f"Play {max(self.current_play_index, 0)} / {max(self.total_plays - 1, 0)}")
        self.status_var.set("AUTO" if self.is_autoplay else ("END" if self.finished else "MANUAL"))
        self.commentary_var.set(self.current_commentary)
        self._draw_court()

    def _draw_court(self) -> None:
        if self._is_special_package_event():
            self._draw_highlight_package_screen()
            return

        self.canvas.delete("all")

        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)

        margin = 40
        left = margin
        top = margin
        right = w - margin
        bottom = h - margin

        camera_dx = self._get_camera_focus_dx(left, right)
        zoom = self._get_camera_zoom_scale()

        base_center_x = (left + right) / 2
        center_y = (top + bottom) / 2

        court_w = (right - left) * zoom
        court_h = (bottom - top) * zoom

        left = base_center_x - court_w / 2 + camera_dx
        right = base_center_x + court_w / 2 + camera_dx
        top = center_y - court_h / 2
        bottom = center_y + court_h / 2
        self.last_court_bounds = (left, top, right, bottom)

        import math

        court_line_width = 2
        court_length_m = 28.0
        court_width_m = 15.0

        def to_canvas(x_m: float, y_m: float) -> tuple[float, float]:
            x = left + (right - left) * (x_m / court_length_m)
            y = top + (bottom - top) * (y_m / court_width_m)
            return x, y

        def x_to_canvas(x_m: float) -> float:
            return left + (right - left) * (x_m / court_length_m)

        def y_to_canvas(y_m: float) -> float:
            return top + (bottom - top) * (y_m / court_width_m)

        def draw_circle(cx: float, cy: float, r_px: float, *, width: int = 2, outline: str = "#111111") -> None:
            self.canvas.create_oval(cx - r_px, cy - r_px, cx + r_px, cy + r_px, width=width, outline=outline)

        def draw_arc_points(points: list[float], *, width: int = 2, smooth: bool = True, fill: str = "#111111") -> None:
            if len(points) >= 4:
                self.canvas.create_line(*points, width=width, smooth=smooth, fill=fill)

        def build_circle_arc_points(
            cx_m: float,
            cy_m: float,
            r_m: float,
            start_deg: float,
            end_deg: float,
            *,
            steps: int = 72,
        ) -> list[float]:
            if end_deg < start_deg:
                end_deg += 360.0
            points: list[float] = []
            for i in range(steps + 1):
                t = i / steps
                deg = start_deg + (end_deg - start_deg) * t
                rad = math.radians(deg)
                x_m = cx_m + r_m * math.cos(rad)
                y_m = cy_m + r_m * math.sin(rad)
                x, y = to_canvas(x_m, y_m)
                points.extend([x, y])
            return points

        # =========================================================
        # コート塗り（通常リーグ用）
        # =========================================================
        outer_color = "#caa06a"
        main_wood = "#d7b07a"
        wood_dark = "#c9955b"
        wood_light = "#e1bc8d"
        paint_fill = "#c79a66"
        key_fill = "#c18d5a"
        line_color = "#111111"

        self.canvas.create_rectangle(left, top, right, bottom, width=0, fill=outer_color)

        # 木目感（軽量な横帯）
        stripe_count = 14
        stripe_h = max((bottom - top) / stripe_count, 1)
        for i in range(stripe_count):
            y1 = top + i * stripe_h
            y2 = min(bottom, y1 + stripe_h)
            fill = wood_light if i % 2 == 0 else main_wood
            self.canvas.create_rectangle(left, y1, right, y2, width=0, fill=fill)

            # うっすら木目ライン
            grain_y = (y1 + y2) / 2
            grain_segments = 12
            segment_w = (right - left) / grain_segments
            for j in range(grain_segments):
                gx1 = left + j * segment_w + (4 if (i + j) % 2 == 0 else 10)
                gx2 = min(right, gx1 + segment_w * 0.55)
                self.canvas.create_line(gx1, grain_y, gx2, grain_y, fill=wood_dark, width=1)

        # 実寸→画面の代表スケール
        scale_x = (right - left) / court_length_m
        scale_y = (bottom - top) / court_width_m
        uniform_scale = min(scale_x, scale_y)

        # 制限区域（ペイント）塗り
        lane_length = 5.80  # FIBA
        lane_width = 4.90  # FIBA
        lane_top_y = (court_width_m - lane_width) / 2.0
        lane_bottom_y = lane_top_y + lane_width

        lx1, ly1 = to_canvas(0.0, lane_top_y)
        lx2, ly2 = to_canvas(lane_length, lane_bottom_y)
        rx1, ry1 = to_canvas(court_length_m - lane_length, lane_top_y)
        rx2, ry2 = to_canvas(court_length_m, lane_bottom_y)

        self.canvas.create_rectangle(lx1, ly1, lx2, ly2, width=0, fill=paint_fill)
        self.canvas.create_rectangle(rx1, ry1, rx2, ry2, width=0, fill=paint_fill)

        # ゴール下の濃い色帯
        restricted_band_length = 2.40
        rlx1, rly1 = to_canvas(0.0, (court_width_m / 2.0) - 1.80)
        rlx2, rly2 = to_canvas(restricted_band_length, (court_width_m / 2.0) + 1.80)
        rrx1, rry1 = to_canvas(court_length_m - restricted_band_length, (court_width_m / 2.0) - 1.80)
        rrx2, rry2 = to_canvas(court_length_m, (court_width_m / 2.0) + 1.80)
        self.canvas.create_rectangle(rlx1, rly1, rlx2, rly2, width=0, fill=key_fill)
        self.canvas.create_rectangle(rrx1, rry1, rrx2, rry2, width=0, fill=key_fill)

        # 外枠
        self.canvas.create_rectangle(left, top, right, bottom, width=3, outline=line_color)

        # センターライン / センターサークル（真円）
        mid_x = x_to_canvas(court_length_m / 2.0)
        mid_y = y_to_canvas(court_width_m / 2.0)
        self.canvas.create_line(mid_x, top, mid_x, bottom, width=court_line_width, fill=line_color)

        center_circle_r_px = 1.80 * uniform_scale
        draw_circle(mid_x, mid_y, center_circle_r_px, width=court_line_width, outline=line_color)

        # 制限区域（ペイント）線
        self.canvas.create_rectangle(lx1, ly1, lx2, ly2, width=court_line_width, outline=line_color)
        self.canvas.create_rectangle(rx1, ry1, rx2, ry2, width=court_line_width, outline=line_color)

        # フリースローサークル（真円、ペイント外側の半円のみ）
        ft_circle_r_m = 1.80
        left_ft_x_m = lane_length
        right_ft_x_m = court_length_m - lane_length
        left_ft_x = x_to_canvas(left_ft_x_m)
        right_ft_x = x_to_canvas(right_ft_x_m)
        ft_r_px = ft_circle_r_m * uniform_scale

        self.canvas.create_arc(
            left_ft_x - ft_r_px,
            mid_y - ft_r_px,
            left_ft_x + ft_r_px,
            mid_y + ft_r_px,
            start=270,
            extent=180,
            style="arc",
            width=court_line_width,
            outline=line_color,
        )
        self.canvas.create_arc(
            right_ft_x - ft_r_px,
            mid_y - ft_r_px,
            right_ft_x + ft_r_px,
            mid_y + ft_r_px,
            start=90,
            extent=180,
            style="arc",
            width=court_line_width,
            outline=line_color,
        )

        # バックボード / リム
        rim_center_from_baseline = 1.575
        backboard_from_baseline = 1.20  # approx
        backboard_half_h = 0.90
        rim_r_m = 0.23

        left_rim = to_canvas(rim_center_from_baseline, court_width_m / 2.0)
        right_rim = to_canvas(court_length_m - rim_center_from_baseline, court_width_m / 2.0)

        lbbx = x_to_canvas(backboard_from_baseline)
        bby_top = y_to_canvas((court_width_m / 2.0) - backboard_half_h)
        bby_bottom = y_to_canvas((court_width_m / 2.0) + backboard_half_h)
        self.canvas.create_line(lbbx, bby_top, lbbx, bby_bottom, width=3, fill="#ffffff")
        # バックボード内枠
        bb_w = 0.60 * uniform_scale
        bb_h = 0.45 * uniform_scale
        self.canvas.create_rectangle(lbbx - bb_w, mid_y - bb_h, lbbx + bb_w, mid_y + bb_h, outline="#ffffff", width=2)

        rbbx = x_to_canvas(court_length_m - backboard_from_baseline)
        self.canvas.create_line(rbbx, bby_top, rbbx, bby_bottom, width=3, fill="#ffffff")
        bb_w = 0.60 * uniform_scale
        bb_h = 0.45 * uniform_scale
        self.canvas.create_rectangle(rbbx - bb_w, mid_y - bb_h, rbbx + bb_w, mid_y + bb_h, outline="#ffffff", width=2)

        rim_r_px = rim_r_m * uniform_scale
        draw_circle(left_rim[0], left_rim[1], rim_r_px, width=3, outline="#ff7a00")
        draw_circle(right_rim[0], right_rim[1], rim_r_px, width=3, outline="#ff7a00")

        # ゴール下ノーチャージエリア（真半円）
        restricted_r_m = 1.25
        restricted_r_px = restricted_r_m * uniform_scale
        self.canvas.create_arc(
            left_rim[0] - restricted_r_px,
            left_rim[1] - restricted_r_px,
            left_rim[0] + restricted_r_px,
            left_rim[1] + restricted_r_px,
            start=270,
            extent=180,
            style="arc",
            width=court_line_width,
            outline=line_color,
        )
        self.canvas.create_arc(
            right_rim[0] - restricted_r_px,
            right_rim[1] - restricted_r_px,
            right_rim[0] + restricted_r_px,
            right_rim[1] + restricted_r_px,
            start=90,
            extent=180,
            style="arc",
            width=court_line_width,
            outline=line_color,
        )

        # 3Pライン（サイドラインと並行のコーナー直線 + アーチ）
        three_r_m = 6.75  # 3P radius
        corner_side_offset_m = 0.90  # corner 3P
        corner_top_y_m = corner_side_offset_m
        corner_bottom_y_m = court_width_m - corner_side_offset_m

        three_join_dx_m = math.sqrt(
            max(three_r_m * three_r_m - ((court_width_m / 2.0) - corner_top_y_m) ** 2, 0.0)
        )
        left_three_x_m = rim_center_from_baseline + three_join_dx_m
        right_three_x_m = court_length_m - left_three_x_m

        self.canvas.create_line(
            left,
            y_to_canvas(corner_top_y_m),
            x_to_canvas(left_three_x_m),
            y_to_canvas(corner_top_y_m),
            width=court_line_width,
            fill=line_color,
        )
        self.canvas.create_line(
            left,
            y_to_canvas(corner_bottom_y_m),
            x_to_canvas(left_three_x_m),
            y_to_canvas(corner_bottom_y_m),
            width=court_line_width,
            fill=line_color,
        )
        self.canvas.create_line(
            x_to_canvas(right_three_x_m),
            y_to_canvas(corner_top_y_m),
            right,
            y_to_canvas(corner_top_y_m),
            width=court_line_width,
            fill=line_color,
        )
        self.canvas.create_line(
            x_to_canvas(right_three_x_m),
            y_to_canvas(corner_bottom_y_m),
            right,
            y_to_canvas(corner_bottom_y_m),
            width=court_line_width,
            fill=line_color,
        )

        theta_top = math.degrees(
            math.atan2(corner_top_y_m - (court_width_m / 2.0), three_join_dx_m)
        )
        theta_bottom = -theta_top

        left_three_points = build_circle_arc_points(
            rim_center_from_baseline,
            court_width_m / 2.0,
            three_r_m,
            theta_top,
            theta_bottom,
            steps=72,
        )
        right_three_points = build_circle_arc_points(
            court_length_m - rim_center_from_baseline,
            court_width_m / 2.0,
            three_r_m,
            180.0 - theta_bottom,
            180.0 - theta_top,
            steps=72,
        )

        draw_arc_points(left_three_points, width=court_line_width, smooth=True, fill=line_color)
        draw_arc_points(right_three_points, width=court_line_width, smooth=True, fill=line_color)

        target_positions = self._compute_player_positions()
        if self.player_anim_active:
            player_positions = self._get_interpolated_player_positions()
        else:
            player_positions = target_positions
            self.current_player_positions = dict(target_positions)
            if not self.prev_player_positions:
                self.prev_player_positions = dict(target_positions)

        self._draw_players_from_positions(player_positions)
        self._draw_ball_icon(player_positions, left_rim, right_rim)

        title = self._court_overlay_title()
        sub = self._court_overlay_subtitle()
        self.canvas.create_text(w / 2, top + 28, text=title, font=("Yu Gothic UI", 18, "bold"))
        self.canvas.create_text(w / 2, bottom - 26, text=sub, font=("Yu Gothic UI", 12))

        self._draw_camera_overlay(left, top, right, bottom)
        self._draw_result_only_score_flash(left, top, right, bottom)
        self._draw_result_only_period_flash(left, top, right, bottom)

        importance = self._extract_importance()
        if importance == "high":
            self.canvas.create_rectangle(left, top, right, top + 10, width=0, fill="#cc3333")
        elif importance == "normal":
            self.canvas.create_rectangle(left, top, right, top + 10, width=0, fill="#3366cc")

        self._draw_big_play_overlay(left, top, right, bottom)


    def _should_show_big_play_overlay(self) -> bool:
        if self._is_result_only_mode():
            return False

        if not isinstance(self.current_presentation_event, dict):
            return False

        ptype = str(self.current_presentation_event.get("presentation_type") or "")
        if ptype in {"highlight_intro", "highlight_outro"}:
            return False

        highlight_score = int(self.current_presentation_event.get("highlight_score", 0) or 0)
        if highlight_score >= 55:
            return True

        if isinstance(self.current_camera_event, dict):
            if str(self.current_camera_event.get("camera_level") or "") == "top_play":
                return True

        return False

    def _build_big_play_label(self) -> str:
        event = self.current_presentation_event or {}
        ptype = str(event.get("presentation_type") or "")
        score = int(event.get("highlight_score", 0) or 0)

        if ptype == "steal":
            return "BIG STEAL"
        if ptype == "block":
            return "BIG BLOCK"
        if ptype == "score_make_3":
            return "BIG 3"
        if ptype == "score_make_2" and score >= 65:
            return "CLUTCH BUCKET"
        if score >= 70:
            return "TOP PLAY"
        return "BIG PLAY"

    def _draw_big_play_overlay(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> None:
        if not self._should_show_big_play_overlay():
            return

        label = self._build_big_play_label()

        camera_level = "normal"
        if isinstance(self.current_camera_event, dict):
            camera_level = str(self.current_camera_event.get("camera_level", "normal"))

        panel_x1 = left + 20
        panel_x2 = panel_x1 + 168
        panel_y1 = top + 58 if camera_level in {"highlight", "replay", "top_play"} else top + 20
        panel_y2 = panel_y1 + 34

        self.canvas.create_rectangle(
            panel_x1,
            panel_y1,
            panel_x2,
            panel_y2,
            width=2,
            outline="#facc15",
            fill="#111827",
        )
        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            (panel_y1 + panel_y2) / 2,
            text=label,
            font=("Yu Gothic UI", 13, "bold"),
            fill="#facc15",
        )

    def _draw_result_only_score_flash(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> None:
        if not self._is_result_only_mode():
            return
        if self.score_flash_frames_remaining <= 0:
            return

        if self.score_flash_team_side == "home":
            fill = "#1d4ed8"
            label = "HOME SCORE"
        elif self.score_flash_team_side == "away":
            fill = "#b91c1c"
            label = "AWAY SCORE"
        else:
            fill = "#facc15"
            label = "SCORE"

        panel_w = 240
        panel_h = 54
        panel_x1 = (left + right) / 2 - panel_w / 2
        panel_x2 = panel_x1 + panel_w
        panel_y1 = top + 22
        panel_y2 = panel_y1 + panel_h

        self.canvas.create_rectangle(
            panel_x1, panel_y1, panel_x2, panel_y2,
            width=3, outline="#f8fafc", fill=fill,
        )
        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            (panel_y1 + panel_y2) / 2,
            text=label,
            font=("Yu Gothic UI", 18, "bold"),
            fill="#ffffff",
        )

    def _draw_result_only_period_flash(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> None:
        if not self._is_result_only_mode():
            return
        if self.period_flash_frames_remaining <= 0:
            return
        if not self.period_flash_text:
            return

        panel_w = 300
        panel_h = 58
        panel_x1 = (left + right) / 2 - panel_w / 2
        panel_x2 = panel_x1 + panel_w
        panel_y1 = top + 88
        panel_y2 = panel_y1 + panel_h

        self.canvas.create_rectangle(
            panel_x1, panel_y1, panel_x2, panel_y2,
            width=3, outline="#facc15", fill="#111827",
        )
        self.canvas.create_text(
            (panel_x1 + panel_x2) / 2,
            (panel_y1 + panel_y2) / 2,
            text=self.period_flash_text,
            font=("Yu Gothic UI", 20, "bold"),
            fill="#facc15",
        )

    def _compute_player_positions(self) -> dict[str, tuple[float, float]]:
        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)

        margin = 40
        left = margin
        top = margin
        right = w - margin
        bottom = h - margin

        camera_dx = self._get_camera_focus_dx(left, right)
        zoom = self._get_camera_zoom_scale()

        base_center_x = (left + right) / 2
        center_y = (top + bottom) / 2

        court_w = (right - left) * zoom
        court_h = (bottom - top) * zoom

        left = base_center_x - court_w / 2 + camera_dx
        right = base_center_x + court_w / 2 + camera_dx
        top = center_y - court_h / 2
        bottom = center_y + court_h / 2

        structured_positions = self._compute_structured_player_positions(left, top, right, bottom)
        if structured_positions:
            return structured_positions

        return self._compute_legacy_player_positions(left, top, right, bottom)

    def _zone_rect_to_canvas(
        self,
        zone: dict[str, float],
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> tuple[float, float, float, float]:
        zx1 = left + (right - left) * zone["x1"]
        zx2 = left + (right - left) * zone["x2"]
        zy1 = top + (bottom - top) * zone["y1"]
        zy2 = top + (bottom - top) * zone["y2"]
        return zx1, zy1, zx2, zy2

    def _zone_anchor(
        self,
        zone: dict[str, float],
        left: float,
        top: float,
        right: float,
        bottom: float,
        x_ratio: float = 0.5,
        y_ratio: float = 0.5,
    ) -> tuple[float, float]:
        zx1, zy1, zx2, zy2 = self._zone_rect_to_canvas(zone, left, top, right, bottom)
        x = zx1 + (zx2 - zx1) * x_ratio
        y = zy1 + (zy2 - zy1) * y_ratio
        return x, y

    def _get_event_anchor_ratios(
        self,
        ptype: str,
        focus_name: Optional[str],
    ) -> tuple[float, float]:
        # 3Pは絶対にライン外、2Pは絶対にライン内、FTは所定位置
        if ptype in {"score_make_3", "miss_jump_3"}:
            wing_side = 0
            if isinstance(focus_name, str):
                wing_side = sum(ord(c) for c in focus_name) % 3
            if wing_side == 0:
                return 0.98, 0.18
            if wing_side == 1:
                return 0.98, 0.82
            return 0.98, 0.50

        if ptype in {"score_make_2", "miss_jump_2"}:
            lane_side = 0
            if isinstance(focus_name, str):
                lane_side = sum(ord(c) for c in focus_name) % 3
            if lane_side == 0:
                return 0.86, 0.34
            if lane_side == 1:
                return 0.86, 0.66
            return 0.90, 0.50

        if ptype in {"score_make_ft", "miss_free_throw"}:
            return 0.50, 0.50


        if ptype in {"def_rebound", "off_rebound", "off_rebound_keep"}:
            return 0.78, 0.50

        return 0.60, 0.50

    def _mirror_normalized_point(
        self,
        nx: float,
        ny: float,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if offense_direction == "right_to_left":
            return 1.0 - nx, ny
        return nx, ny

    def _canvas_from_offense_point(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        nx: float,
        ny: float,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        mx, my = self._mirror_normalized_point(nx, ny, offense_direction)
        return self._normalized_to_canvas(mx, my, left, top, right, bottom)

    def _clamp_canvas_point_to_court(
        self,
        x: float,
        y: float,
        left: float,
        top: float,
        right: float,
        bottom: float,
        margin_x: float = 20.0,
        margin_y: float = 16.0,
    ) -> tuple[float, float]:
        min_x = left + margin_x
        max_x = right - margin_x
        min_y = top + margin_y
        max_y = bottom - margin_y
        if min_x > max_x:
            mid_x = (left + right) / 2.0
            min_x = max_x = mid_x
        if min_y > max_y:
            mid_y = (top + bottom) / 2.0
            min_y = max_y = mid_y
        return max(min_x, min(max_x, x)), max(min_y, min(max_y, y))

    def _is_kickout_play(self) -> bool:
        if not self.current_presentation_event:
            return False
        candidates = [
            self._get_pnr_action(),
            self._get_spain_action(),
            self._get_off_ball_screen_action(),
            self._get_post_up_action(),
            self._get_handoff_action(),
        ]
        if any(value == "kickout" for value in candidates):
            return True
        raw_tags = self.current_presentation_event.get("highlight_tags", []) or []
        if isinstance(raw_tags, list) and any(str(tag).lower() == "kickout" for tag in raw_tags):
            return True
        return False

    def _get_event_special_positions(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> dict[str, tuple[float, float]]:
        if not self.current_presentation_event:
            return {}

        ptype = str(self.current_presentation_event.get("presentation_type") or "")
        if ptype not in {
            "score_make_2", "score_make_3", "miss_jump_2", "miss_jump_3",
            "score_make_ft", "miss_free_throw", "def_rebound", "off_rebound", "off_rebound_keep", "block"
        }:
            return {}

        offense_side = self._get_offense_team_side()
        offense_direction = self._get_offense_direction()
        if offense_side not in {"home", "away"} or offense_direction not in {"left_to_right", "right_to_left"}:
            return {}

        focus = self.current_presentation_event.get("focus_player_name")
        support = self.current_presentation_event.get("support_player_name")

        home_names = [n for n in self._get_team_display_players("home", 5) if isinstance(n, str)]
        away_names = [n for n in self._get_team_display_players("away", 5) if isinstance(n, str)]
        offense_names = home_names if offense_side == "home" else away_names
        defense_names = away_names if offense_side == "home" else home_names

        positions: dict[str, tuple[float, float]] = {}

        def place(player_name: Optional[str], nx: float, ny: float) -> None:
            if isinstance(player_name, str) and player_name.strip():
                px, py = self._canvas_from_offense_point(
                    left, top, right, bottom, nx, ny, offense_direction
                )
                positions[player_name] = self._clamp_canvas_point_to_court(px, py, left, top, right, bottom)

        def ordered_offense_names() -> list[str]:
            ordered: list[str] = []
            for candidate in [focus, support]:
                if isinstance(candidate, str) and candidate in offense_names and candidate not in ordered:
                    ordered.append(candidate)
            for name in offense_names:
                if name not in ordered:
                    ordered.append(name)
            return ordered[:5]

        def ordered_defense_names(anchor_count: int = 5) -> list[str]:
            ordered = [name for name in defense_names if isinstance(name, str)]
            return ordered[:anchor_count]

        def build_man_to_man_defense(offense_slots: list[tuple[float, float]], mode: str) -> list[tuple[float, float]]:
            defense_slots: list[tuple[float, float]] = []
            for idx, (ox, oy) in enumerate(offense_slots[:5]):
                if mode == "three":
                    inward = 0.045 if idx == 0 else 0.035
                    lateral = 0.028 if idx % 2 == 0 else -0.028
                elif mode == "two":
                    inward = 0.035
                    lateral = 0.022 if idx % 2 == 0 else -0.022
                elif mode == "ft":
                    inward = 0.020
                    lateral = 0.0
                else:  # rebound
                    inward = 0.022
                    lateral = 0.018 if idx % 2 == 0 else -0.018

                dx = -inward if offense_direction == "left_to_right" else inward
                dnx = ox + dx
                dny = oy + lateral
                dnx = max(0.52, min(0.97, dnx))
                dny = max(0.08, min(0.92, dny))
                defense_slots.append((dnx, dny))
            return defense_slots

        def is_corner_three() -> bool:
            raw = self.current_presentation_event or {}
            texts = [
                str(raw.get("headline") or ""),
                str(raw.get("main_text") or ""),
                str(raw.get("sub_text") or ""),
            ]
            tags = raw.get("highlight_tags") or []
            joined = " ".join(texts).lower()
            if "corner" in joined or "コーナー" in joined:
                return True
            if isinstance(tags, list) and any("corner" in str(tag).lower() for tag in tags):
                return True
            seed = sum(ord(c) for c in focus) % 3 if isinstance(focus, str) else 0
            return seed in {0, 1}

        def is_inside_finish() -> bool:
            raw = self.current_presentation_event or {}
            texts = [
                str(raw.get("headline") or ""),
                str(raw.get("main_text") or ""),
                str(raw.get("sub_text") or ""),
            ]
            joined = " ".join(texts)
            if any(keyword in joined for keyword in ["ダンク", "アリウープ", "インサイド", "押し込み", "ゴール下", "ローポスト", "ポスト", "体をぶつけ", "ねじ込み", "押し込", "ぶつかり"]):
                return True
            tags = raw.get("highlight_tags") or []
            if isinstance(tags, list) and any(str(tag).lower() in {"dunk", "alley_oop", "inside", "post_up", "post", "roll", "close_range", "rim_pressure", "power_finish"} for tag in tags):
                return True
            return False

        if ptype in {"score_make_3", "miss_jump_3"}:
            wing_seed = sum(ord(c) for c in focus) % 3 if isinstance(focus, str) else 0
            is_kickout = self._is_kickout_play()
            corner_three = is_corner_three()

            if is_kickout:
                # 明確に「中→外」を作る。パサーはペイント、シューターは3Pライン外固定。
                if corner_three:
                    if wing_seed == 0:
                        shooter_xy = (0.935, 0.045)
                        support_xy = (0.875, 0.56)
                        rest_slots = [(0.84, 0.42), (0.72, 0.78), (0.66, 0.24)]
                        defense_slots = [(0.91, 0.18), (0.89, 0.50), (0.86, 0.64), (0.80, 0.36), (0.76, 0.54)]
                    else:
                        shooter_xy = (0.935, 0.955)
                        support_xy = (0.875, 0.44)
                        rest_slots = [(0.84, 0.58), (0.72, 0.22), (0.66, 0.76)]
                        defense_slots = [(0.91, 0.82), (0.89, 0.50), (0.86, 0.36), (0.80, 0.64), (0.76, 0.46)]
                else:
                    if wing_seed == 0:
                        shooter_xy = (0.705, 0.22)
                        support_xy = (0.875, 0.56)
                        rest_slots = [(0.82, 0.44), (0.74, 0.74), (0.66, 0.28)]
                        defense_slots = [(0.78, 0.24), (0.88, 0.50), (0.84, 0.66), (0.78, 0.38), (0.74, 0.56)]
                    elif wing_seed == 1:
                        shooter_xy = (0.705, 0.78)
                        support_xy = (0.875, 0.44)
                        rest_slots = [(0.82, 0.56), (0.74, 0.26), (0.66, 0.72)]
                        defense_slots = [(0.78, 0.76), (0.88, 0.50), (0.84, 0.34), (0.78, 0.62), (0.74, 0.44)]
                    else:
                        shooter_xy = (0.690, 0.50)
                        support_xy = (0.875, 0.52)
                        rest_slots = [(0.82, 0.68), (0.82, 0.32), (0.70, 0.24)]
                        defense_slots = [(0.76, 0.50), (0.88, 0.36), (0.88, 0.64), (0.80, 0.28), (0.80, 0.72)]
            else:
                if corner_three:
                    if wing_seed == 0:
                        shooter_xy = (0.935, 0.045)
                        support_xy = (0.82, 0.48)
                        rest_slots = [(0.88, 0.62), (0.74, 0.30), (0.66, 0.74)]
                    else:
                        shooter_xy = (0.935, 0.955)
                        support_xy = (0.82, 0.52)
                        rest_slots = [(0.88, 0.38), (0.74, 0.70), (0.66, 0.26)]
                elif wing_seed == 0:
                    shooter_xy = (0.705, 0.22)
                    support_xy = (0.80, 0.52)
                    rest_slots = [(0.84, 0.64), (0.72, 0.36), (0.62, 0.78)]
                elif wing_seed == 1:
                    shooter_xy = (0.705, 0.78)
                    support_xy = (0.80, 0.48)
                    rest_slots = [(0.84, 0.36), (0.72, 0.64), (0.62, 0.22)]
                else:
                    shooter_xy = (0.680, 0.50)
                    support_xy = (0.78, 0.50)
                    rest_slots = [(0.84, 0.36), (0.84, 0.64), (0.66, 0.24)]
                defense_slots = build_man_to_man_defense([shooter_xy, support_xy] + rest_slots, "three")

            offense_order = ordered_offense_names()
            offense_slots = [shooter_xy, support_xy] + rest_slots
            for name, (nx, ny) in zip(offense_order, offense_slots):
                place(name, nx, ny)

            defense_order = ordered_defense_names(len(offense_slots))
            for name, (nx, ny) in zip(defense_order, defense_slots):
                place(name, nx, ny)
            return positions

        if ptype in {"score_make_2", "miss_jump_2"}:
            lane_seed = sum(ord(c) for c in focus) % 3 if isinstance(focus, str) else 0
            if is_inside_finish():
                if lane_seed == 0:
                    shooter_xy = (0.955, 0.44)
                    support_xy = (0.84, 0.58)
                    rest_slots = [(0.92, 0.66), (0.78, 0.34), (0.68, 0.72)]
                elif lane_seed == 1:
                    shooter_xy = (0.955, 0.56)
                    support_xy = (0.84, 0.42)
                    rest_slots = [(0.92, 0.34), (0.78, 0.66), (0.68, 0.28)]
                else:
                    shooter_xy = (0.94, 0.50)
                    support_xy = (0.82, 0.50)
                    rest_slots = [(0.90, 0.36), (0.90, 0.64), (0.70, 0.28)]
                defense_slots = [(0.93, 0.50), (0.90, 0.40), (0.90, 0.60), (0.82, 0.34), (0.82, 0.66)]
            else:
                if lane_seed == 0:
                    shooter_xy = (0.82, 0.36)
                    support_xy = (0.66, 0.55)
                    rest_slots = [(0.93, 0.43), (0.88, 0.60), (0.74, 0.70)]
                elif lane_seed == 1:
                    shooter_xy = (0.82, 0.64)
                    support_xy = (0.66, 0.45)
                    rest_slots = [(0.93, 0.57), (0.88, 0.40), (0.74, 0.30)]
                else:
                    shooter_xy = (0.90, 0.50)
                    support_xy = (0.70, 0.50)
                    rest_slots = [(0.94, 0.42), (0.94, 0.58), (0.74, 0.30)]
                defense_slots = build_man_to_man_defense([shooter_xy, support_xy] + rest_slots, "two")

            offense_order = ordered_offense_names()
            offense_slots = [shooter_xy, support_xy] + rest_slots
            for name, (nx, ny) in zip(offense_order, offense_slots):
                place(name, nx, ny)

            defense_order = ordered_defense_names(len(offense_slots))
            for name, (nx, ny) in zip(defense_order, defense_slots):
                place(name, nx, ny)
            return positions

        if ptype in {"score_make_ft", "miss_free_throw"}:
            offense_order = ordered_offense_names()
            defense_order = ordered_defense_names(5)

            # FT:
            # - shooter is fixed inside FT semicircle
            # - lane rebounders are moved farther up/down so they sit just outside the paint
            # - defense lane rebounders stand OUTSIDE (farther from rim side in current view)
            # - offense lane rebounders stand INSIDE (closer to rim side in current view)
            # - remaining players wait outside 3P
            shooter_slot = (0.77, 0.50)

            offense_slots = [
                shooter_slot,
                (0.845, 0.31),  # lane upper, offense inner
                (0.845, 0.69),  # lane lower, offense inner
                (0.58, 0.20),   # outside 3P upper
                (0.58, 0.80),   # outside 3P lower
            ]
            defense_slots = [
                (0.895, 0.31),  # lane upper, defense outer
                (0.895, 0.69),  # lane lower, defense outer
                (0.66, 0.28),   # perimeter upper
                (0.66, 0.72),   # perimeter lower
                (0.54, 0.50),   # top safety
            ]

            for name, (nx, ny) in zip(offense_order, offense_slots):
                place(name, nx, ny)
            for name, (nx, ny) in zip(defense_order, defense_slots):
                place(name, nx, ny)
            return positions

        if ptype in {"def_rebound", "off_rebound", "off_rebound_keep"}:
            offense_order = ordered_offense_names()
            defense_order = ordered_defense_names(5)

            offense_slots = [
                (0.95, 0.50),
                (0.90, 0.42),
                (0.90, 0.58),
                (0.82, 0.34),
                (0.82, 0.66),
            ]
            defense_slots = [
                (0.87, 0.50),
                (0.86, 0.42),
                (0.86, 0.58),
                (0.78, 0.34),
                (0.78, 0.66),
            ]

            for name, (nx, ny) in zip(offense_order, offense_slots):
                place(name, nx, ny)
            for name, (nx, ny) in zip(defense_order, defense_slots):
                place(name, nx, ny)
            return positions

        if ptype == "block":
            offense_order = ordered_offense_names()
            defense_order = ordered_defense_names(5)
            shooter_xy = (0.955, 0.50)
            blocker_xy = (0.942, 0.50)
            support_xy = (0.89, 0.42)
            rest_offense = [(0.87, 0.60), (0.78, 0.34), (0.72, 0.68)]
            rest_defense = [(0.90, 0.60), (0.82, 0.34), (0.76, 0.68)]
            offense_slots = [shooter_xy, support_xy] + rest_offense
            defense_slots = [blocker_xy] + rest_defense
            for name, (nx, ny) in zip(offense_order, offense_slots):
                place(name, nx, ny)
            for name, (nx, ny) in zip(defense_order, defense_slots):
                place(name, nx, ny)
            return positions

        return positions


    def _compute_structured_player_positions(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> dict[str, tuple[float, float]]:
        offense_side = self._get_offense_team_side()
        offense_direction = self._get_offense_direction()
        lane_map = self._get_lane_map()

        if offense_side not in {"home", "away"}:
            return {}
        if offense_direction not in {"left_to_right", "right_to_left"}:
            return {}
        if not lane_map:
            return {}

        home_players = self._get_team_display_players("home", 5)
        away_players = self._get_team_display_players("away", 5)
        positions: dict[str, tuple[float, float]] = {}
        special_positions = self._get_event_special_positions(left, top, right, bottom)

        offense_players = home_players if offense_side == "home" else away_players
        defense_players = away_players if offense_side == "home" else home_players

        structure_type = self._get_structure_type()
        offense_norm_positions = self._build_offense_normalized_positions(lane_map, offense_direction)
        defense_norm_positions = self._build_defense_normalized_positions(offense_direction, structure_type)

        if not offense_norm_positions or not defense_norm_positions:
            return {}

        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None
        shot_play = bool(self.current_presentation_event and self._is_shot_presentation(self.current_presentation_event))
        spacing_profile = self._get_spacing_profile()

        for idx, name in enumerate(offense_players[:5]):
            nx, ny = offense_norm_positions[idx]
            nx, ny = self._apply_spacing_profile_to_normalized(nx, ny, spacing_profile, is_offense=True)
            nx, ny = self._apply_archetype_adjustment(
                nx,
                ny,
                player_name=name,
                team_side=offense_side,
                offense_side=offense_side,
                structure_type=structure_type,
                offense_direction=offense_direction,
                is_offense=True,
            )
            nx, ny = self._apply_pick_and_roll_offense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_off_ball_screen_offense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_post_up_offense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_spain_pick_and_roll_offense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_handoff_offense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            x, y = self._normalized_to_canvas(nx, ny, left, top, right, bottom)
            if name in special_positions:
                positions[name] = special_positions[name]
            else:
                x, y = self._apply_situation_offset(
                    x, y,
                    team_side=offense_side,
                    offense_side=offense_side,
                    player_name=name,
                    focus=focus,
                    support=support,
                    shot_play=shot_play,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
                positions[name] = self._clamp_canvas_point_to_court(x, y, left, top, right, bottom)

        defense_side = "away" if offense_side == "home" else "home"
        for idx, name in enumerate(defense_players[:5]):
            nx, ny = defense_norm_positions[idx]
            nx, ny = self._apply_spacing_profile_to_normalized(nx, ny, spacing_profile, is_offense=False)
            nx, ny = self._apply_defense_structure_pressure(
                nx,
                ny,
                idx=idx,
                structure_type=structure_type,
                offense_direction=offense_direction,
                shot_play=shot_play,
                player_name=name,
                focus=focus,
                support=support,
            )
            nx, ny = self._apply_archetype_adjustment(
                nx,
                ny,
                player_name=name,
                team_side=defense_side,
                offense_side=offense_side,
                structure_type=structure_type,
                offense_direction=offense_direction,
                is_offense=False,
            )
            nx, ny = self._apply_pick_and_roll_defense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_off_ball_screen_defense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_post_up_defense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_spain_pick_and_roll_defense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            nx, ny = self._apply_handoff_defense_adjustment(
                nx,
                ny,
                player_name=name,
                offense_direction=offense_direction,
            )
            x, y = self._normalized_to_canvas(nx, ny, left, top, right, bottom)
            if name in special_positions:
                positions[name] = special_positions[name]
            else:
                x, y = self._apply_situation_offset(
                    x, y,
                    team_side=defense_side,
                    offense_side=offense_side,
                    player_name=name,
                    focus=focus,
                    support=support,
                    shot_play=shot_play,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
                positions[name] = self._clamp_canvas_point_to_court(x, y, left, top, right, bottom)

        return positions

    def _compute_legacy_player_positions(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> dict[str, tuple[float, float]]:
        court_w = right - left
        court_h = bottom - top
        cy = (top + bottom) / 2

        base_home_positions = [
            (left + court_w * 0.18, cy),
            (left + court_w * 0.28, top + court_h * 0.28),
            (left + court_w * 0.28, bottom - court_h * 0.28),
            (left + court_w * 0.40, top + court_h * 0.36),
            (left + court_w * 0.40, bottom - court_h * 0.36),
        ]
        base_away_positions = [
            (right - court_w * 0.18, cy),
            (right - court_w * 0.28, top + court_h * 0.28),
            (right - court_w * 0.28, bottom - court_h * 0.28),
            (right - court_w * 0.40, top + court_h * 0.36),
            (right - court_w * 0.40, bottom - court_h * 0.36),
        ]

        home_players = self._get_team_display_players("home", 5)
        away_players = self._get_team_display_players("away", 5)

        offense_side = self._get_offense_team_side()
        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None
        shot_play = bool(self.current_presentation_event and self._is_shot_presentation(self.current_presentation_event))

        positions: dict[str, tuple[float, float]] = {}

        structure_type = self._get_structure_type()
        offense_direction = self._get_offense_direction()

        for idx, (x, y) in enumerate(base_home_positions):
            name = home_players[idx] if idx < len(home_players) else f"H{idx+1}"
            nx, ny = self._canvas_to_normalized(x, y, left, top, right, bottom)
            nx, ny = self._apply_archetype_adjustment(
                nx,
                ny,
                player_name=name,
                team_side="home",
                offense_side=offense_side,
                structure_type=structure_type,
                offense_direction=offense_direction,
                is_offense=(offense_side == "home"),
            )
            x, y = self._normalized_to_canvas(nx, ny, left, top, right, bottom)
            hx, hy = self._apply_situation_offset(
                x, y, team_side="home", offense_side=offense_side,
                player_name=name, focus=focus, support=support, shot_play=shot_play,
                left=left, top=top, right=right, bottom=bottom
            )
            positions[name] = self._clamp_canvas_point_to_court(hx, hy, left, top, right, bottom)

        for idx, (x, y) in enumerate(base_away_positions):
            name = away_players[idx] if idx < len(away_players) else f"A{idx+1}"
            nx, ny = self._canvas_to_normalized(x, y, left, top, right, bottom)
            nx, ny = self._apply_archetype_adjustment(
                nx,
                ny,
                player_name=name,
                team_side="away",
                offense_side=offense_side,
                structure_type=structure_type,
                offense_direction=offense_direction,
                is_offense=(offense_side == "away"),
            )
            x, y = self._normalized_to_canvas(nx, ny, left, top, right, bottom)
            ax, ay = self._apply_situation_offset(
                x, y, team_side="away", offense_side=offense_side,
                player_name=name, focus=focus, support=support, shot_play=shot_play,
                left=left, top=top, right=right, bottom=bottom
            )
            positions[name] = self._clamp_canvas_point_to_court(ax, ay, left, top, right, bottom)

        return positions

    def _build_offense_normalized_positions(
        self,
        lane_map: dict[str, str],
        offense_direction: str,
    ) -> list[tuple[float, float]]:
        role_order = ["PG", "SG", "SF", "PF", "C"]
        positions: list[tuple[float, float]] = []
        for role in role_order:
            lane_name = lane_map.get(role, "top")
            positions.append(self._lane_name_to_normalized(lane_name, offense_direction))
        return positions

    def _build_defense_normalized_positions(
        self,
        offense_direction: str,
        structure_type: Optional[str] = None,
    ) -> list[tuple[float, float]]:
        if structure_type == "fast_break":
            lane_names = [
                "guard_ball_transition",
                "left_transition_wall",
                "right_transition_wall",
                "left_rim_help",
                "right_rim_help",
            ]
        elif structure_type == "second_chance":
            lane_names = [
                "guard_ball_reset",
                "left_lane_tag",
                "right_lane_tag",
                "left_rim_help_tight",
                "right_rim_help_tight",
            ]
        else:
            lane_names = [
                "guard_ball",
                "left_perimeter",
                "right_perimeter",
                "left_paint",
                "right_paint",
            ]
        return [self._lane_name_to_normalized(name, offense_direction) for name in lane_names]

    def _lane_name_to_normalized(self, lane_name: str, offense_direction: str) -> tuple[float, float]:
        base_map = {
            "top": (0.36, 0.50),
            "left_wing": (0.28, 0.25),
            "right_wing": (0.28, 0.75),
            "left_elbow": (0.54, 0.38),
            "right_low_post": (0.69, 0.62),
            "center_push": (0.64, 0.50),
            "left_lane": (0.56, 0.21),
            "right_lane": (0.56, 0.79),
            "trailer_left": (0.36, 0.36),
            "trailer_right": (0.36, 0.64),
            "reset_top": (0.35, 0.50),
            "left_slot": (0.31, 0.30),
            "right_slot": (0.31, 0.70),
            "dunker_left": (0.74, 0.39),
            "dunker_right": (0.74, 0.61),
            "guard_ball": (0.44, 0.50),
            "left_perimeter": (0.38, 0.29),
            "right_perimeter": (0.38, 0.71),
            "left_paint": (0.24, 0.40),
            "right_paint": (0.24, 0.60),
            "guard_ball_transition": (0.47, 0.50),
            "left_transition_wall": (0.42, 0.25),
            "right_transition_wall": (0.42, 0.75),
            "left_rim_help": (0.29, 0.38),
            "right_rim_help": (0.29, 0.62),
            "guard_ball_reset": (0.43, 0.50),
            "left_lane_tag": (0.41, 0.37),
            "right_lane_tag": (0.41, 0.63),
            "left_rim_help_tight": (0.30, 0.43),
            "right_rim_help_tight": (0.30, 0.57),
        }
        nx, ny = base_map.get(lane_name, (0.38, 0.50))
        if offense_direction == "right_to_left":
            nx = 1.0 - nx
        return nx, ny

    def _apply_spacing_profile_to_normalized(
        self,
        nx: float,
        ny: float,
        spacing_profile: str,
        is_offense: bool,
    ) -> tuple[float, float]:
        if spacing_profile == "wide":
            ny = 0.5 + (ny - 0.5) * 1.36
            if is_offense:
                nx = nx + 0.05 if nx >= 0.5 else nx + 0.01
            else:
                nx = nx - 0.02 if nx < 0.5 else nx - 0.01
        elif spacing_profile == "collapse":
            ny = 0.5 + (ny - 0.5) * 0.62
            if is_offense:
                nx = nx + 0.05 if nx >= 0.5 else nx + 0.06
            else:
                nx = nx + 0.03 if nx < 0.5 else nx - 0.03
        else:
            if is_offense:
                ny = 0.5 + (ny - 0.5) * 1.05

        nx = max(0.10, min(0.90, nx))
        ny = max(0.14, min(0.86, ny))
        return nx, ny

    def _apply_defense_structure_pressure(
        self,
        nx: float,
        ny: float,
        idx: int,
        structure_type: Optional[str],
        offense_direction: str,
        shot_play: bool,
        player_name: Optional[str],
        focus: Optional[str],
        support: Optional[str],
    ) -> tuple[float, float]:
        defense_front_x = 0.46 if offense_direction == "left_to_right" else 0.54
        defense_back_x = 0.32 if offense_direction == "left_to_right" else 0.68

        if structure_type == "fast_break":
            if idx == 0:
                nx = defense_front_x
                ny = 0.50
            elif idx in {1, 2}:
                nx = max(min(nx, 0.45), 0.35) if offense_direction == "left_to_right" else min(max(nx, 0.55), 0.65)
                ny = 0.30 if idx == 1 else 0.70
            else:
                nx = defense_back_x
                ny = 0.40 if idx == 3 else 0.60
        elif structure_type == "second_chance":
            collapse_front_x = 0.26 if offense_direction == "left_to_right" else 0.74
            collapse_back_x = 0.34 if offense_direction == "left_to_right" else 0.66
            if idx == 0:
                nx = collapse_back_x
                ny = 0.50
            elif idx in {1, 2}:
                nx = collapse_back_x
                ny = 0.42 if idx == 1 else 0.58
            else:
                nx = collapse_front_x
                ny = 0.46 if idx == 3 else 0.54
        else:
            if idx == 0:
                nx = 0.42 if offense_direction == "left_to_right" else 0.58
                ny = 0.50
            elif idx in {3, 4}:
                nx = 0.28 if offense_direction == "left_to_right" else 0.72
                ny = 0.42 if idx == 3 else 0.58

        if shot_play:
            if idx in {3, 4}:
                nx = nx - 0.03 if offense_direction == "left_to_right" else nx + 0.03
                ny = 0.44 if idx == 3 else 0.56
            elif idx == 0:
                nx = nx + 0.02 if offense_direction == "left_to_right" else nx - 0.02

        if player_name and player_name == focus:
            nx = nx + 0.01 if offense_direction == "left_to_right" else nx - 0.01
        if player_name and player_name == support:
            ny = ny - 0.02 if ny <= 0.5 else ny + 0.02

        nx = max(0.12, min(0.88, nx))
        ny = max(0.16, min(0.84, ny))
        return nx, ny

    def _canvas_to_normalized(
        self,
        x: float,
        y: float,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> tuple[float, float]:
        width = max(right - left, 1.0)
        height = max(bottom - top, 1.0)
        nx = (x - left) / width
        ny = (y - top) / height
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        return nx, ny

    def _normalized_to_canvas(
        self,
        nx: float,
        ny: float,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> tuple[float, float]:
        x = left + (right - left) * nx
        y = top + (bottom - top) * ny
        return x, y

    def _get_structure_type(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("structure_type")
            if isinstance(value, str) and value.strip():
                return value
        return None

    def _get_offense_direction(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("offense_direction")
            if value in {"left_to_right", "right_to_left"}:
                return value

        offense_side = self._get_offense_team_side()
        if offense_side == "home":
            return "left_to_right"
        if offense_side == "away":
            return "right_to_left"
        return None

    def _get_spacing_profile(self) -> str:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("spacing_profile")
            if isinstance(value, str) and value.strip():
                return value

        structure_type = self._get_structure_type()
        if structure_type == "fast_break":
            return "wide"
        if structure_type == "second_chance":
            return "collapse"
        return "standard"

    def _get_lane_map(self) -> dict[str, str]:
        if self.current_presentation_event:
            lane_map = self.current_presentation_event.get("lane_map")
            if isinstance(lane_map, dict) and lane_map:
                safe_map: dict[str, str] = {}
                for key, value in lane_map.items():
                    if isinstance(key, str) and isinstance(value, str):
                        safe_map[key] = value
                if safe_map:
                    return safe_map

        structure_type = self._get_structure_type()
        if structure_type == "fast_break":
            return {
                "PG": "center_push",
                "SG": "left_lane",
                "SF": "right_lane",
                "PF": "trailer_left",
                "C": "trailer_right",
            }
        if structure_type == "second_chance":
            return {
                "PG": "reset_top",
                "SG": "left_slot",
                "SF": "right_slot",
                "PF": "dunker_left",
                "C": "dunker_right",
            }
        if structure_type == "off_ball_screen":
            return {
                "PG": "top",
                "SG": "left_wing",
                "SF": "right_wing",
                "PF": "left_elbow",
                "C": "right_low_post",
            }
        if structure_type == "post_up":
            return {
                "PG": "top",
                "SG": "left_wing",
                "SF": "right_wing",
                "PF": "left_elbow",
                "C": "right_low_post",
            }
        if structure_type == "pick_and_roll":
            return {
                "PG": "top",
                "SG": "left_wing",
                "SF": "right_wing",
                "PF": "left_elbow",
                "C": "right_low_post",
            }
        if structure_type == "spain_pick_and_roll":
            return {
                "PG": "top",
                "SG": "left_slot",
                "SF": "right_wing",
                "PF": "left_elbow",
                "C": "right_low_post",
            }
        if structure_type == "handoff":
            return {
                "PG": "top",
                "SG": "left_slot",
                "SF": "right_wing",
                "PF": "left_elbow",
                "C": "dunker_right",
            }
        return {
            "PG": "top",
            "SG": "left_wing",
            "SF": "right_wing",
            "PF": "left_elbow",
            "C": "right_low_post",
        }


    # =========================================================
    # Shot / rebound zone definition (design foundation)
    # =========================================================
    def _get_court_zone_templates(self) -> dict[str, dict[str, float]]:
        """
        観戦描画用の簡易ゾーン定義。
        値はすべてコート正規化座標（0.0〜1.0）。
        x は攻撃方向が left_to_right のときの値で、
        right_to_left のときは後段で左右反転する前提。
        """
        return {
            "free_throw": {"x1": 0.66, "x2": 0.71, "y1": 0.46, "y2": 0.54},
            "rim": {"x1": 0.90, "x2": 0.98, "y1": 0.40, "y2": 0.60},
            "short_mid": {"x1": 0.78, "x2": 0.88, "y1": 0.28, "y2": 0.72},
            "long_mid": {"x1": 0.66, "x2": 0.78, "y1": 0.22, "y2": 0.78},
            "arc_three": {"x1": 0.86, "x2": 0.98, "y1": 0.06, "y2": 0.94},
            "corner_three_left": {"x1": 0.92, "x2": 0.99, "y1": 0.05, "y2": 0.16},
            "corner_three_right": {"x1": 0.92, "x2": 0.99, "y1": 0.84, "y2": 0.95},
            "rebound_near_rim": {"x1": 0.92, "x2": 0.99, "y1": 0.40, "y2": 0.60},
            "rebound_mid_lane": {"x1": 0.84, "x2": 0.93, "y1": 0.30, "y2": 0.70},
            "turnover_high": {"x1": 0.42, "x2": 0.62, "y1": 0.20, "y2": 0.80},
        }

    def _mirror_zone_for_direction(
        self,
        zone: dict[str, float],
        offense_direction: Optional[str],
    ) -> dict[str, float]:
        if offense_direction != "right_to_left":
            return dict(zone)

        x1 = 1.0 - zone["x2"]
        x2 = 1.0 - zone["x1"]
        return {
            "x1": x1,
            "x2": x2,
            "y1": zone["y1"],
            "y2": zone["y2"],
        }

    def _get_shot_zone_key(self, presentation_type: Optional[str]) -> str:
        ptype = presentation_type or ""
        structure_type = self._get_structure_type() or ""
        shot_action = self._get_pnr_action() or self._get_spain_action() or self._get_off_ball_screen_action() or ""

        if ptype in {"score_make_3", "miss_jump_3"}:
            return "arc_three"

        if ptype in {"score_make_ft", "miss_free_throw"}:
            return "free_throw"

        if structure_type in {"pick_and_roll", "spain_pick_and_roll"} and shot_action in {"roll", "drive"}:
            return "rim"

        if structure_type == "off_ball_screen" and shot_action == "cut":
            return "rim"

        if structure_type == "post_up":
            post_action = self._get_post_up_action() or ""
            if post_action in {"turn_shoot", "back_down"}:
                return "short_mid"

        if ptype in {"score_make_2", "miss_jump_2"}:
            return "short_mid"

        return "short_mid"

    def _get_rebound_zone_key(self, is_offense_rebound: bool) -> str:
        if is_offense_rebound:
            return "rebound_near_rim"
        return "rebound_mid_lane"

    def _get_event_zone_definition(self) -> Optional[dict[str, float]]:
        """
        次段階で「実際のプレー位置」に使うための設計用ヘルパー。
        この段階ではまだ描画座標へ強制反映しない。
        """
        if not self.current_presentation_event:
            return None

        offense_direction = self._get_offense_direction()
        templates = self._get_court_zone_templates()
        ptype = self.current_presentation_event.get("presentation_type")

        if ptype in {"score_make_2", "score_make_3", "miss_jump_2", "miss_jump_3", "score_make_ft", "miss_free_throw"}:
            key = self._get_shot_zone_key(ptype)
            return self._mirror_zone_for_direction(templates[key], offense_direction)

        if ptype == "def_rebound":
            key = self._get_rebound_zone_key(is_offense_rebound=False)
            return self._mirror_zone_for_direction(templates[key], offense_direction)

        if ptype in {"off_rebound", "off_rebound_keep"}:
            key = self._get_rebound_zone_key(is_offense_rebound=True)
            return self._mirror_zone_for_direction(templates[key], offense_direction)

        if ptype == "block":
            return self._mirror_zone_for_direction(templates["rim"], offense_direction)

        if ptype in {"turnover", "steal"}:
            return self._mirror_zone_for_direction(templates["turnover_high"], offense_direction)

        return None


    def _get_structure_raw(self) -> dict[str, Any]:
        if self.current_presentation_event:
            raw = self.current_presentation_event.get("structure_raw")
            if isinstance(raw, dict):
                return raw
        return {}

    def _get_pnr_action(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("pnr_action")
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get("pnr_action")
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _get_pnr_role_name(self, key: str) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _apply_pick_and_roll_offense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "pick_and_roll":
            return nx, ny

        action = self._get_pnr_action() or "setup"
        ball_handler = self._get_pnr_role_name("ball_handler_name") or self._get_ball_owner_name()
        screener = self._get_pnr_role_name("screener_name")
        roller = self._get_pnr_role_name("roller_name")
        kickout_target = self._get_pnr_role_name("kickout_target_name")
        screen_side = self._get_pnr_role_name("screen_side") or "middle"
        drive_lane = self._get_pnr_role_name("drive_lane") or "middle"

        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        side_shift = 0.0
        if screen_side == "left":
            side_shift = -0.05
        elif screen_side == "right":
            side_shift = 0.05

        drive_shift = 0.0
        if drive_lane == "left":
            drive_shift = -0.08
        elif drive_lane == "right":
            drive_shift = 0.08

        dx = 0.0
        dy = 0.0

        if player_name == ball_handler:
            if action == "setup":
                dx += 0.020 * forward
                dy += side_shift * 0.4
                dy += (0.5 - ny) * 0.14
            elif action == "drive":
                dx += 0.060 * forward
                dy += drive_shift
            elif action == "roll":
                dx += 0.028 * forward
                dy += (-side_shift) * 0.3
            elif action == "kickout":
                dx += 0.012 * forward
                dy += (-side_shift) * 0.9
            elif action == "pullup":
                dx += 0.040 * forward
                dy += drive_shift * 0.35

        elif player_name == screener:
            if action == "setup":
                dx += 0.018 * forward
                dy += side_shift
                dy += (0.5 - ny) * 0.10
            elif action == "drive":
                dx += 0.010 * forward
                dy += side_shift * 0.35
            elif action == "roll":
                dx += 0.090 * forward
                dy += (0.5 - ny) * 0.34
            elif action == "kickout":
                dx += 0.040 * forward
                dy += (0.5 - ny) * 0.20
            elif action == "pullup":
                dx += 0.018 * forward
                dy += side_shift * 0.4

        elif player_name == roller:
            dx += 0.075 * forward
            dy += (0.5 - ny) * 0.30

        elif player_name == kickout_target:
            if action == "kickout":
                dx += 0.022 * forward
                dy += 0.10 if ny >= 0.5 else -0.10
            else:
                dy += 0.04 if ny >= 0.5 else -0.04

        else:
            if action in {"setup", "drive"}:
                dy += 0.03 if ny >= 0.5 else -0.03
            elif action == "roll":
                dy += 0.05 if ny >= 0.5 else -0.05
            elif action == "kickout":
                dy += 0.08 if ny >= 0.5 else -0.08

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _apply_pick_and_roll_defense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "pick_and_roll":
            return nx, ny

        action = self._get_pnr_action() or "setup"
        ball_handler = self._get_pnr_role_name("ball_handler_name") or self._get_ball_owner_name()
        screener = self._get_pnr_role_name("screener_name")
        screen_side = self._get_pnr_role_name("screen_side") or "middle"
        drive_lane = self._get_pnr_role_name("drive_lane") or "middle"

        offense_side = self._get_offense_team_side()
        defense_side = "away" if offense_side == "home" else "home"
        if self._infer_player_team_side(player_name) != defense_side:
            return nx, ny

        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None
        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        wall_x = 0.46 if offense_direction == "left_to_right" else 0.54
        help_x = 0.32 if offense_direction == "left_to_right" else 0.68

        dx = 0.0
        dy = 0.0

        if player_name == focus or player_name == ball_handler:
            if action == "setup":
                nx = wall_x
                dy += 0.03 if screen_side == "right" else (-0.03 if screen_side == "left" else 0.0)
            elif action in {"drive", "pullup"}:
                nx = wall_x + (0.02 * forward)
                dy += 0.05 if drive_lane == "right" else (-0.05 if drive_lane == "left" else 0.0)
            elif action == "kickout":
                nx = wall_x
        elif player_name == support or player_name == screener:
            nx = help_x
            dy += (0.5 - ny) * 0.10
            if action == "roll":
                dy += (0.5 - ny) * 0.18
        else:
            if action in {"drive", "roll"}:
                nx = nx - 0.03 if offense_direction == "left_to_right" else nx + 0.03
                dy += (0.5 - ny) * 0.10
            elif action == "kickout":
                dy += 0.06 if ny >= 0.5 else -0.06

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _get_off_ball_screen_action(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("screen_action")
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get("screen_action")
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _get_off_ball_role_name(self, key: str) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _apply_off_ball_screen_offense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "off_ball_screen":
            return nx, ny
        action = self._get_off_ball_screen_action() or "screen_setup"
        screener = self._get_off_ball_role_name("screener_name")
        target = self._get_off_ball_role_name("target_name") or self._get_ball_owner_name()
        screen_side = self._get_off_ball_role_name("screen_side") or "left"
        cut_lane = self._get_off_ball_role_name("cut_lane") or "wing"
        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        side = -1.0 if screen_side == "left" else 1.0
        dx = dy = 0.0
        if player_name == screener:
            if action == "screen_setup":
                dx += 0.015 * forward
                dy += 0.06 * side
            elif action == "cut":
                dx += 0.008 * forward
                dy += 0.04 * side
            elif action == "catch":
                dx += 0.010 * forward
            elif action == "catch_shoot":
                dx += 0.014 * forward
                dy += 0.05 * side
        elif player_name == target:
            if action == "screen_setup":
                dx += 0.030 * forward
                dy += 0.03 * side
            elif action == "cut":
                dx += 0.070 * forward
                if cut_lane == "baseline":
                    dy += 0.10 * side
                elif cut_lane == "middle":
                    dy += (0.5 - ny) * 0.28
                else:
                    dy += 0.06 * side
            elif action == "catch":
                dx += 0.040 * forward
                dy += 0.06 * side
            elif action == "catch_shoot":
                dx += 0.028 * forward
                dy += 0.11 * side
        else:
            if action == "catch_shoot":
                dy += 0.05 if ny >= 0.5 else -0.05
            elif action == "cut":
                dy += 0.03 if ny >= 0.5 else -0.03
        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _apply_off_ball_screen_defense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "off_ball_screen":
            return nx, ny
        offense_side = self._get_offense_team_side()
        defense_side = "away" if offense_side == "home" else "home"
        if self._infer_player_team_side(player_name) != defense_side:
            return nx, ny
        action = self._get_off_ball_screen_action() or "screen_setup"
        screener = self._get_off_ball_role_name("screener_name")
        target = self._get_off_ball_role_name("target_name") or self._get_ball_owner_name()
        side = -1.0 if (self._get_off_ball_role_name("screen_side") or "left") == "left" else 1.0
        dx = dy = 0.0
        if player_name == target:
            dx += (-0.015 if offense_direction == "left_to_right" else 0.015)
            if action in {"cut", "catch_shoot"}:
                dy += 0.05 * side
        elif player_name == screener:
            dx += (-0.010 if offense_direction == "left_to_right" else 0.010)
            dy += 0.03 * side
        else:
            if action == "cut":
                dy += (0.5 - ny) * 0.10
            elif action == "catch_shoot":
                dy += 0.05 if ny >= 0.5 else -0.05
        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _get_post_up_action(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("post_action")
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get("post_action")
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _get_post_up_role_name(self, key: str) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _apply_post_up_offense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "post_up":
            return nx, ny
        action = self._get_post_up_action() or "seal"
        post_player = self._get_post_up_role_name("post_player_name") or self._get_ball_owner_name()
        entry_passer = self._get_post_up_role_name("entry_passer_name")
        kickout_target = self._get_post_up_role_name("post_kickout_target_name") or self._get_post_up_role_name("kickout_target_name")
        post_side = self._get_post_up_role_name("post_side") or "right"
        side = -1.0 if post_side == "left" else 1.0
        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        dx = dy = 0.0
        if player_name == post_player:
            if action == "seal":
                dx += 0.055 * forward
                dy += 0.08 * side
            elif action == "back_down":
                dx += 0.080 * forward
                dy += 0.06 * side
            elif action == "turn_shoot":
                dx += 0.095 * forward
                dy += 0.04 * side
            elif action == "kickout":
                dx += 0.060 * forward
                dy += 0.04 * side
        elif player_name == entry_passer:
            dx += 0.010 * forward
            dy += -0.05 * side
        elif player_name == kickout_target:
            if action == "kickout":
                dx += 0.020 * forward
                dy += 0.10 if ny >= 0.5 else -0.10
            else:
                dy += 0.05 if ny >= 0.5 else -0.05
        else:
            dy += 0.03 if ny >= 0.5 else -0.03
        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _apply_post_up_defense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "post_up":
            return nx, ny
        offense_side = self._get_offense_team_side()
        defense_side = "away" if offense_side == "home" else "home"
        if self._infer_player_team_side(player_name) != defense_side:
            return nx, ny
        action = self._get_post_up_action() or "seal"
        post_player = self._get_post_up_role_name("post_player_name") or self._get_ball_owner_name()
        post_side = self._get_post_up_role_name("post_side") or "right"
        side = -1.0 if post_side == "left" else 1.0
        dx = dy = 0.0
        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None
        if player_name == focus or player_name == post_player:
            dx += (-0.020 if offense_direction == "left_to_right" else 0.020)
            dy += 0.06 * side
        elif player_name == support:
            dx += (-0.010 if offense_direction == "left_to_right" else 0.010)
            dy += (0.5 - ny) * 0.12
        else:
            if action in {"back_down", "turn_shoot"}:
                dx += (-0.015 if offense_direction == "left_to_right" else 0.015)
                dy += (0.5 - ny) * 0.10
            elif action == "kickout":
                dy += 0.06 if ny >= 0.5 else -0.06
        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny



    def _get_spain_action(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("spain_action")
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get("spain_action")
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _get_spain_role_name(self, key: str) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _apply_spain_pick_and_roll_offense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "spain_pick_and_roll":
            return nx, ny

        action = self._get_spain_action() or "setup"
        handler = self._get_spain_role_name("ball_handler_name") or self._get_ball_owner_name()
        screener = self._get_spain_role_name("screener_name")
        roller = self._get_spain_role_name("roller_name") or screener
        back_screener = self._get_spain_role_name("back_screener_name")
        back_target = self._get_spain_role_name("back_screen_target_name") or roller
        kickout_target = self._get_spain_role_name("spain_kickout_target_name")
        screen_side = self._get_spain_role_name("screen_side") or "middle"

        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        strong_side = -1.0 if screen_side == "left" else (1.0 if screen_side == "right" else (1.0 if ny >= 0.5 else -1.0))
        dx = 0.0
        dy = 0.0

        if player_name == handler:
            if action == "setup":
                dx += 0.026 * forward
                dy += strong_side * 0.05
                dy += (0.5 - ny) * 0.12
            elif action == "roll":
                dx += 0.052 * forward
                dy += strong_side * 0.04
            elif action == "kickout":
                dx += 0.030 * forward
                dy += -strong_side * 0.07
            elif action == "pullup":
                dx += 0.060 * forward
                dy += strong_side * 0.03

        elif player_name == screener or player_name == roller:
            if action == "setup":
                dx += 0.036 * forward
                dy += strong_side * 0.12
            elif action == "roll":
                dx += 0.135 * forward
                dy += (0.5 - ny) * 0.40
            elif action == "kickout":
                dx += 0.088 * forward
                dy += (0.5 - ny) * 0.26
            elif action == "pullup":
                dx += 0.096 * forward
                dy += (0.5 - ny) * 0.20

        elif player_name == back_screener:
            if action == "setup":
                dx += 0.048 * forward
                dy += strong_side * 0.15
            elif action == "roll":
                dx += 0.064 * forward
                dy += strong_side * 0.14
            elif action == "kickout":
                dx += 0.040 * forward
                dy += 0.18 if ny >= 0.5 else -0.18
            elif action == "pullup":
                dx += 0.048 * forward
                dy += strong_side * 0.14

            if back_target and player_name == back_screener:
                dy += strong_side * 0.03

        elif player_name == kickout_target:
            if action == "kickout":
                dx += 0.048 * forward
                dy += 0.20 if ny >= 0.5 else -0.20
            else:
                dy += 0.09 if ny >= 0.5 else -0.09

        else:
            if action in {"roll", "kickout"}:
                dy += 0.08 if ny >= 0.5 else -0.08
            elif action == "pullup":
                dy += 0.05 if ny >= 0.5 else -0.05

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _apply_spain_pick_and_roll_defense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "spain_pick_and_roll":
            return nx, ny

        offense_side = self._get_offense_team_side()
        defense_side = "away" if offense_side == "home" else "home"
        if self._infer_player_team_side(player_name) != defense_side:
            return nx, ny

        action = self._get_spain_action() or "setup"
        handler = self._get_spain_role_name("ball_handler_name") or self._get_ball_owner_name()
        screener = self._get_spain_role_name("screener_name")
        back_screener = self._get_spain_role_name("back_screener_name")
        kickout_target = self._get_spain_role_name("spain_kickout_target_name")
        screen_side = self._get_spain_role_name("screen_side") or "middle"

        side = -1.0 if screen_side == "left" else (1.0 if screen_side == "right" else 0.0)
        dx = 0.0
        dy = 0.0

        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None

        if player_name in {focus, handler}:
            dx += (-0.025 if offense_direction == "left_to_right" else 0.025)
            dy += side * 0.05
            if action in {"roll", "pullup"}:
                dx += (-0.015 if offense_direction == "left_to_right" else 0.015)
        elif player_name in {support, screener}:
            dx += (-0.022 if offense_direction == "left_to_right" else 0.022)
            dy += (0.5 - ny) * 0.15
        elif player_name == back_screener:
            dx += (-0.014 if offense_direction == "left_to_right" else 0.014)
            dy += side * 0.06
        elif player_name == kickout_target:
            if action == "kickout":
                dy += 0.10 if ny >= 0.5 else -0.10
        else:
            if action == "roll":
                dy += (0.5 - ny) * 0.13
            elif action == "kickout":
                dy += 0.07 if ny >= 0.5 else -0.07

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _get_handoff_action(self) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("handoff_action")
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get("handoff_action")
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _get_handoff_role_name(self, key: str) -> Optional[str]:
        if self.current_presentation_event:
            value = self.current_presentation_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = self._get_structure_raw()
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _apply_handoff_offense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "handoff":
            return nx, ny

        action = self._get_handoff_action() or "setup"
        giver = self._get_handoff_role_name("handoff_giver_name")
        receiver = self._get_handoff_role_name("handoff_receiver_name") or self._get_ball_owner_name()
        handoff_side = self._get_handoff_role_name("handoff_side") or "left"

        forward = 1.0 if offense_direction != "right_to_left" else -1.0
        side = -1.0 if handoff_side == "left" else 1.0
        dx = 0.0
        dy = 0.0

        if player_name == giver:
            if action in {"setup", "bring", "approach"}:
                dx += 0.022 * forward
                dy += 0.04 * side
            elif action in {"exchange", "turn_corner", "reject"}:
                dx += 0.014 * forward
                dy += 0.07 * side
        elif player_name == receiver:
            if action in {"setup", "bring", "approach"}:
                dx += 0.036 * forward
                dy += 0.08 * side
            elif action == "exchange":
                dx += 0.058 * forward
                dy += 0.06 * side
            elif action == "turn_corner":
                dx += 0.078 * forward
                dy += (0.5 - ny) * 0.20
            elif action == "reject":
                dx += 0.052 * forward
                dy += -0.10 * side
        else:
            if action in {"exchange", "turn_corner"}:
                dy += 0.04 if ny >= 0.5 else -0.04
            elif action == "reject":
                dy += 0.06 if ny >= 0.5 else -0.06

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _apply_handoff_defense_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        offense_direction: Optional[str],
    ) -> tuple[float, float]:
        if self._get_structure_type() != "handoff":
            return nx, ny

        offense_side = self._get_offense_team_side()
        defense_side = "away" if offense_side == "home" else "home"
        if self._infer_player_team_side(player_name) != defense_side:
            return nx, ny

        action = self._get_handoff_action() or "setup"
        giver = self._get_handoff_role_name("handoff_giver_name")
        receiver = self._get_handoff_role_name("handoff_receiver_name") or self._get_ball_owner_name()
        handoff_side = self._get_handoff_role_name("handoff_side") or "left"

        side = -1.0 if handoff_side == "left" else 1.0
        dx = 0.0
        dy = 0.0

        focus = self.current_presentation_event.get("focus_player_name") if self.current_presentation_event else None
        support = self.current_presentation_event.get("support_player_name") if self.current_presentation_event else None

        if player_name in {focus, receiver}:
            dx += (-0.018 if offense_direction == "left_to_right" else 0.018)
            dy += 0.04 * side
            if action in {"exchange", "turn_corner"}:
                dx += (-0.014 if offense_direction == "left_to_right" else 0.014)
        elif player_name in {support, giver}:
            dx += (-0.010 if offense_direction == "left_to_right" else 0.010)
            dy += 0.02 * side
        else:
            if action == "turn_corner":
                dy += (0.5 - ny) * 0.10
            elif action == "reject":
                dy += -0.05 * side

        nx = max(0.08, min(0.92, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _draw_players_from_positions(self, positions: dict[str, tuple[float, float]]) -> None:
        for name, (x, y) in positions.items():
            side = self._infer_player_team_side(name)
            team_side = side if side in {"home", "away"} else "home"
            self._draw_single_player(x, y, name, team_side=team_side, is_focus=self._is_focus_player(name))

    def _get_interpolated_player_positions(self) -> dict[str, tuple[float, float]]:
        positions: dict[str, tuple[float, float]] = {}
        p = self.player_anim_progress

        all_names = list(dict.fromkeys(list(self.prev_player_positions.keys()) + list(self.current_player_positions.keys())))
        for name in all_names:
            prev_pos = self.prev_player_positions.get(name, self.current_player_positions.get(name))
            curr_pos = self.current_player_positions.get(name, prev_pos)
            if prev_pos is None or curr_pos is None:
                continue
            x = prev_pos[0] + (curr_pos[0] - prev_pos[0]) * p
            y = prev_pos[1] + (curr_pos[1] - prev_pos[1]) * p
            if self.last_court_bounds is not None:
                left, top, right, bottom = self.last_court_bounds
                x, y = self._clamp_canvas_point_to_court(x, y, left, top, right, bottom)
            positions[name] = (x, y)
        return positions

    def _maybe_start_player_animation(self, new_positions: dict[str, tuple[float, float]]) -> None:
        if self._is_result_only_mode():
            self.player_anim_active = False
            self.prev_player_positions = dict(new_positions)
            self.current_player_positions = dict(new_positions)
            return

        if not self.prev_player_positions:
            self.prev_player_positions = dict(new_positions)
            self.current_player_positions = dict(new_positions)
            self.player_anim_active = False
            return

        changed = False
        for name, pos in new_positions.items():
            old = self.prev_player_positions.get(name)
            if old is None:
                changed = True
                break
            if abs(old[0] - pos[0]) > 0.5 or abs(old[1] - pos[1]) > 0.5:
                changed = True
                break

        self.current_player_positions = dict(new_positions)

        if not changed:
            self.prev_player_positions = dict(new_positions)
            self.player_anim_active = False
            return

        self.player_anim_active = True
        self.player_anim_progress = 0.0
        self.player_anim_step_index = 0
        self.root.after(self.player_anim_interval_ms, self._animate_player_step)

    def _animate_player_step(self) -> None:
        if not self.player_anim_active:
            return

        self.player_anim_step_index += 1
        self.player_anim_progress = min(1.0, self.player_anim_step_index / self.player_anim_steps)
        self._refresh_view()

        if self.player_anim_step_index >= self.player_anim_steps:
            self.player_anim_active = False
            self.prev_player_positions = dict(self.current_player_positions)
            self._refresh_view()
            return

        self.root.after(self.player_anim_interval_ms, self._animate_player_step)

    def _reset_player_animation(self) -> None:
        self.player_anim_active = False
        self.player_anim_progress = 0.0
        self.player_anim_step_index = 0
        self.prev_player_positions = {}
        self.current_player_positions = {}

    def _update_camera_lock_from_current_event(self) -> None:
        camera_event = self.current_camera_event if isinstance(self.current_camera_event, dict) else {}
        presentation_event = self.current_presentation_event if isinstance(self.current_presentation_event, dict) else {}
        current_play = self.current_play if isinstance(self.current_play, dict) else {}

        raw_track_mode = camera_event.get("track_mode")
        if isinstance(raw_track_mode, str) and raw_track_mode.strip():
            track_mode = raw_track_mode.strip().lower()
        else:
            focus_target = camera_event.get("focus_target")
            if isinstance(focus_target, str) and focus_target.strip().lower() in {"ball", "team_shape", "player"}:
                track_mode = focus_target.strip().lower()
            else:
                track_mode = "player"

        focus_name = None
        for source in (camera_event, presentation_event, current_play):
            for key in ("focus_player_name", "primary_player_name", "secondary_player_name"):
                value = source.get(key)
                if isinstance(value, str) and value.strip() and value not in {"ball", "team_shape"}:
                    focus_name = value.strip()
                    break
            if focus_name:
                break

        if track_mode == "player" and not focus_name:
            track_mode = "team_shape"

        self.locked_camera_focus_name = focus_name
        self.locked_camera_track_mode = track_mode

    def _get_camera_focus_name(self) -> Optional[str]:
        if self.current_camera_event:
            camera_level = str(self.current_camera_event.get("camera_level", "normal"))
            if camera_level == "top_play":
                if self.current_presentation_event:
                    focus_player = self.current_presentation_event.get("focus_player_name")
                    if isinstance(focus_player, str) and focus_player.strip():
                        return focus_player
                if self.current_play:
                    primary_name = self.current_play.get("primary_player_name")
                    if isinstance(primary_name, str) and primary_name.strip():
                        return primary_name

            focus_player = self.current_camera_event.get("focus_player_name")
            if isinstance(focus_player, str) and focus_player.strip():
                return focus_player

            focus_target = self.current_camera_event.get("focus_target")
            if isinstance(focus_target, str) and focus_target.strip() and focus_target not in {"ball", "team_shape"}:
                return focus_target

        if self.current_presentation_event:
            focus_player = self.current_presentation_event.get("focus_player_name")
            if isinstance(focus_player, str) and focus_player.strip():
                return focus_player

        if self.current_play:
            primary_name = self.current_play.get("primary_player_name")
            if isinstance(primary_name, str) and primary_name.strip():
                return primary_name

        return None

    def _is_goal_pressure_play(self) -> bool:
        event = self.current_presentation_event if isinstance(self.current_presentation_event, dict) else {}
        camera_event = self.current_camera_event if isinstance(self.current_camera_event, dict) else {}

        structure_type = str(event.get("structure_type") or camera_event.get("structure_type") or "")
        transition_action = str(event.get("transition_action") or camera_event.get("transition_action") or "")
        if structure_type == "fast_break" or transition_action in {"primary_break", "counter"}:
            return True

        headline = str(event.get("headline") or "")
        main_text = str(event.get("main_text") or "")
        joined = f"{headline} {main_text}"
        if any(keyword in joined for keyword in ["ダンク", "アリウープ", "速攻", "カウンター"]):
            return True

        tags = event.get("highlight_tags") or camera_event.get("highlight_tags") or []
        if isinstance(tags, list) and any(str(tag) in {"dunk", "alley_oop", "primary_break", "counter", "fast_break"} for tag in tags):
            return True

        return False

    def _get_current_shot_target_team_side(self) -> Optional[str]:
        if self.current_presentation_event:
            offense_side = self._get_offense_team_side()
            if offense_side in {"home", "away"}:
                return offense_side
        if self.shot_anim_team_side in {"home", "away"}:
            return self.shot_anim_team_side
        return None

    def _get_camera_focus_dx(self, left: float, right: float) -> float:
        result = 0.0

        if self._is_result_only_mode():
            self.last_camera_focus_dx = result
            return result

        focus = self._get_camera_focus_name()
        camera_level = "normal"

        if self.current_camera_event:
            camera_level = str(self.current_camera_event.get("camera_level", "normal"))

        court_w = right - left

        if self.shot_anim_active:
            # 追従精度に確信がない場面では寄せすぎない
            shot_target_side = self._get_current_shot_target_team_side()
            if shot_target_side in {"home", "away"}:
                shot_strength_map = {
                    "normal": 0.05,
                    "light": 0.06,
                    "highlight": 0.08,
                    "replay": 0.10,
                    "top_play": 0.12,
                }
                shift = court_w * shot_strength_map.get(camera_level, 0.06)
                result = -shift if shot_target_side == "home" else shift
            self.last_camera_focus_dx = result
            return result

        if self.made_shot_hold_active:
            if self.made_shot_hold_camera_dx is not None:
                result = self.made_shot_hold_camera_dx
                self.last_camera_focus_dx = result
                return result

            hold_side = self.made_shot_hold_team_side or self._get_current_shot_target_team_side()
            if hold_side in {"home", "away"}:
                hold_strength_map = {
                    "normal": 0.04,
                    "light": 0.05,
                    "highlight": 0.06,
                    "replay": 0.07,
                    "top_play": 0.08,
                }
                shift = court_w * hold_strength_map.get(camera_level, 0.05)
                result = -shift if hold_side == "home" else shift
            self.last_camera_focus_dx = result
            return result

        goal_pressure_play = self._is_goal_pressure_play()
        goal_side = self._get_current_shot_target_team_side() or self._get_offense_team_side()
        if goal_pressure_play and goal_side in {"home", "away"}:
            strength_map = {
                "normal": 0.05,
                "light": 0.07,
                "highlight": 0.09,
                "replay": 0.11,
                "top_play": 0.14,
            }
            shift = court_w * strength_map.get(camera_level, 0.08)
            result = -shift if goal_side == "home" else shift
            self.last_camera_focus_dx = result
            return result

        if not isinstance(focus, str) or not focus.strip():
            self.last_camera_focus_dx = result
            return result

        side = self._infer_player_team_side(focus)
        if side not in {"home", "away"}:
            self.last_camera_focus_dx = result
            return result

        strength_map = {
            "normal": 0.00,
            "light": 0.04,
            "highlight": 0.06,
            "replay": 0.08,
            "top_play": 0.10,
        }
        shift = court_w * strength_map.get(camera_level, 0.0)

        if side == "home":
            result = shift
        elif side == "away":
            result = -shift

        self.last_camera_focus_dx = result
        return result

    def _get_camera_zoom_scale(self) -> float:
        if self._is_result_only_mode():
            return 1.0

        camera_level = "normal"
        ptype = None
        structure_type = None
        highlight_tags: list[str] = []

        if self.current_camera_event:
            camera_level = str(self.current_camera_event.get("camera_level", "normal"))
            ptype = self.current_camera_event.get("presentation_type")
            structure_type = self.current_camera_event.get("structure_type")
            raw_tags = self.current_camera_event.get("highlight_tags", []) or []
            if isinstance(raw_tags, list):
                highlight_tags = [str(tag) for tag in raw_tags]
        elif self.current_presentation_event:
            ptype = self.current_presentation_event.get("presentation_type")
            structure_type = self.current_presentation_event.get("structure_type")
        else:
            return 1.0

        if ptype in {"quarter_start", "quarter_end", "game_end"}:
            return 1.0

        # 見失いやすさを減らすため、全体的に寄りをかなり抑える
        zoom_map = {
            "normal": 1.00,
            "light": 1.03,
            "highlight": 1.06,
            "replay": 1.09,
            "top_play": 1.12,
        }
        zoom = zoom_map.get(camera_level, 1.0)

        if structure_type in {"spain_pick_and_roll", "fast_break"} and camera_level in {"highlight", "replay", "top_play"}:
            zoom += 0.01
        if ptype in {"block", "steal", "score_make_3"} and camera_level in {"light", "highlight", "replay", "top_play"}:
            zoom += 0.01
        if "clutch" in highlight_tags and camera_level in {"highlight", "replay", "top_play"}:
            zoom += 0.01

        if self.shot_anim_active:
            shot_zoom = 1.04
            if ptype in {"score_make_3", "miss_jump_3"}:
                shot_zoom = 1.06
            if camera_level in {"highlight", "replay", "top_play"}:
                shot_zoom += 0.01
            zoom = max(zoom, shot_zoom)

        return min(zoom, 1.16)

    def _get_current_autoplay_delay_ms(self) -> int:
        if self._is_result_only_mode():
            return 35

        delay = int(self.autoplay_interval_ms)

        if self.top_play_slow_frames_remaining > 0:
            return delay + 1200

        if not self.current_camera_event:
            return delay

        level = str(self.current_camera_event.get("camera_level", "normal"))
        if level == "top_play":
            return delay + 700
        if level == "replay":
            return delay + 350
        if level == "highlight":
            return delay + 120
        return delay

    def _draw_camera_overlay(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> None:
        camera_event = self.current_camera_event
        overlay_level = "normal"

        if isinstance(camera_event, dict):
            overlay_level = str(camera_event.get("camera_level", "normal"))

        if self.top_play_overlay_frames_remaining > 0:
            overlay_level = "top_play"
            self.top_play_overlay_frames_remaining -= 1

        if self.top_play_slow_frames_remaining > 0:
            self.top_play_slow_frames_remaining -= 1

        if overlay_level == "normal":
            return

        if self.top_play_flash_frames_remaining > 0:
            flash_alpha_level = self.top_play_flash_frames_remaining
            flash_color = "#fff7cc" if flash_alpha_level >= 2 else "#ffe58f"
            self.canvas.create_rectangle(
                0,
                0,
                self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else self.width,
                self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else self.height,
                width=0,
                fill=flash_color,
                stipple="gray50" if flash_alpha_level >= 2 else "gray75",
            )
            self.top_play_flash_frames_remaining -= 1

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = self.width
            canvas_h = self.height

        label_map = {
            "light": "LIGHT",
            "highlight": "HIGHLIGHT",
            "replay": "REPLAY",
            "top_play": "TOP PLAY",
        }
        color_map = {
            "light": "#2563eb",
            "highlight": "#ea580c",
            "replay": "#b91c1c",
            "top_play": "#7c0000",
        }
        glow_map = {
            "light": "#93c5fd",
            "highlight": "#fdba74",
            "replay": "#fecaca",
            "top_play": "#facc15",
        }

        label = label_map.get(overlay_level, "PLAY")
        color = color_map.get(overlay_level, "#444444")
        glow = glow_map.get(overlay_level, "#dddddd")

        if overlay_level == "light":
            banner_width = 148
            banner_height = 30
            font_size = 12
        elif overlay_level == "highlight":
            banner_width = 180
            banner_height = 34
            font_size = 14
        elif overlay_level == "replay":
            banner_width = 180
            banner_height = 34
            font_size = 14
        else:
            banner_width = 210
            banner_height = 38
            font_size = 15

        banner_left = left + 20
        banner_top = top + 16
        banner_right = banner_left + banner_width
        banner_bottom = banner_top + banner_height

        if overlay_level == "top_play":
            self.canvas.create_rectangle(
                left + 6,
                top + 6,
                right - 6,
                bottom - 6,
                width=3,
                outline=glow,
            )

        self.canvas.create_rectangle(
            banner_left,
            banner_top,
            banner_right,
            banner_bottom,
            width=2,
            outline=glow if overlay_level in {"replay", "top_play"} else "",
            fill=color,
        )
        self.canvas.create_text(
            (banner_left + banner_right) / 2,
            (banner_top + banner_bottom) / 2,
            text=label,
            font=("Yu Gothic UI", font_size, "bold"),
            fill="white",
        )

        focus_name = self._get_camera_focus_name()
        if overlay_level in {"replay", "top_play"} and isinstance(focus_name, str) and focus_name.strip():
            info_text = f"FOCUS: {focus_name}"
            chip_w = min(220, max(130, 12 * len(info_text)))
            chip_h = 26
            chip_x2 = right - 20
            chip_x1 = chip_x2 - chip_w
            chip_y1 = top + 18
            chip_y2 = chip_y1 + chip_h
            self.canvas.create_rectangle(
                chip_x1,
                chip_y1,
                chip_x2,
                chip_y2,
                width=1,
                outline="#dbeafe",
                fill="#0f2557",
            )
            self.canvas.create_text(
                (chip_x1 + chip_x2) / 2,
                (chip_y1 + chip_y2) / 2,
                text=info_text,
                font=("Yu Gothic UI", 9, "bold"),
                fill="#eff6ff",
            )

    def _apply_situation_offset(
        self,
        x: float,
        y: float,
        team_side: str,
        offense_side: Optional[str],
        player_name: Optional[str],
        focus: Optional[str],
        support: Optional[str],
        shot_play: bool,
        left: Optional[float] = None,
        top: Optional[float] = None,
        right: Optional[float] = None,
        bottom: Optional[float] = None,
    ) -> tuple[float, float]:
        dx = 0.0
        dy = 0.0

        structure_type = self._get_structure_type()
        if structure_type == "fast_break":
            offense_push = 30
            defense_drop = 24
        elif structure_type == "second_chance":
            offense_push = 12
            defense_drop = 2
        else:
            offense_push = 18
            defense_drop = 12

        if offense_side == "home":
            if team_side == "home":
                dx += offense_push
            elif team_side == "away":
                dx -= defense_drop
        elif offense_side == "away":
            if team_side == "away":
                dx -= offense_push
            elif team_side == "home":
                dx += defense_drop

        if player_name and player_name == focus:
            if offense_side == "home":
                dx += 14
            elif offense_side == "away":
                dx -= 14
            dy -= 4

        if player_name and player_name == support:
            if offense_side == "home":
                dx += 8
            elif offense_side == "away":
                dx -= 8

        if structure_type == "fast_break" and offense_side is not None and team_side != offense_side:
            dy += -10 if player_name and player_name == focus else (8 if (player_name and player_name == support) else 0)
        elif structure_type == "second_chance" and offense_side is not None and team_side != offense_side:
            dy += -6 if y <= 0 else 6

        if shot_play and player_name and player_name == focus:
            if offense_side == "home":
                dx += 14
            elif offense_side == "away":
                dx -= 14
            dy -= 8

        # =========================================================
        # プレー内容と発生ゾーンの整合性補正
        # =========================================================
        zone = self._get_event_zone_definition()
        ptype = self.current_presentation_event.get("presentation_type") if self.current_presentation_event else None
        has_bounds = None not in (left, top, right, bottom)
        if zone is not None and has_bounds:
            zx = left + (right - left) * ((zone["x1"] + zone["x2"]) / 2.0)
            zy = top + (bottom - top) * ((zone["y1"] + zone["y2"]) / 2.0)

            # シュート系:
            # focus(シューター)を発生ゾーンへ寄せる
            # supportは少しだけ近づける
            if ptype in {"score_make_2", "score_make_3", "miss_jump_2", "miss_jump_3", "score_make_ft", "miss_free_throw"}:
                if player_name and player_name == focus:
                    dx += (zx - x) * 0.72
                    dy += (zy - y) * 0.72
                elif player_name and player_name == support:
                    dx += (zx - x) * 0.28
                    dy += (zy - y) * 0.18

            # リバウンド系:
            # rebounder(focus)をゴール下寄りへ強めに補正
            elif ptype in {"def_rebound", "off_rebound", "off_rebound_keep"}:
                if player_name and player_name == focus:
                    dx += (zx - x) * 0.78
                    dy += (zy - y) * 0.78
                elif player_name and offense_side and team_side == offense_side:
                    dx += (zx - x) * 0.12
                    dy += (zy - y) * 0.10
                else:
                    dx += (zx - x) * 0.06
                    dy += (zy - y) * 0.06

            # ブロック:
            # リム周辺で blocker / shooter をはっきり近づける
            elif ptype == "block":
                if player_name and player_name == focus:
                    dx += (zx - x) * 0.82
                    dy += (zy - y) * 0.82
                elif player_name and player_name == support:
                    dx += (zx - x) * 0.70
                    dy += (zy - y) * 0.70
                elif offense_side and team_side == offense_side:
                    dx += (zx - x) * 0.18
                    dy += (zy - y) * 0.14
                else:
                    dx += (zx - x) * 0.12
                    dy += (zy - y) * 0.10

            # ターンオーバー / スティール:
            # 発生位置へ軽く寄せる
            elif ptype in {"turnover", "steal"}:
                if player_name and player_name == focus:
                    dx += (zx - x) * 0.45
                    dy += (zy - y) * 0.45
                elif player_name and player_name == support:
                    dx += (zx - x) * 0.18
                    dy += (zy - y) * 0.18

        return x + dx, y + dy

    def _draw_single_player(self, x: float, y: float, name: str, team_side: str, is_focus: bool = False) -> None:
        body_r = 16 if is_focus else 13
        outline = 3 if is_focus else 2
        fill = "#4a78d1" if team_side == "home" else "#d14a4a"
        text_fill = "#ffffff"

        if is_focus:
            self.canvas.create_oval(
                x - body_r - 6, y - body_r - 6, x + body_r + 6, y + body_r + 6,
                outline="#ffcc00", width=3
            )

        self.canvas.create_oval(
            x - body_r, y - body_r, x + body_r, y + body_r,
            fill=fill, outline="black", width=outline
        )
        self.canvas.create_text(x, y, text=self._short_player_name(name), fill=text_fill, font=("Yu Gothic UI", 9, "bold"))
        self.canvas.create_text(x, y + 24, text=name, fill="black", font=("Yu Gothic UI", 8))

    def _draw_ball_icon(
        self,
        player_positions: dict[str, tuple[float, float]],
        left_rim: tuple[float, float],
        right_rim: tuple[float, float],
    ) -> None:
        current_presentation_type = self._get_current_presentation_type()

        if current_presentation_type == "block":
            return

        if current_presentation_type in {"steal", "turnover"}:
            ball_owner = self._get_ball_owner_name()
            if not ball_owner:
                return
            pos = player_positions.get(ball_owner)
            if pos is None:
                return
            x, y = pos
            self._draw_single_ball(x + 22, y - 22)
            return

        if self.rebound_anim_active:
            to_pos = player_positions.get(self.rebound_anim_to_name or "")
            if to_pos is not None:
                rx, ry = self._get_rebound_start(left_rim, right_rim)
                tx, ty = to_pos
                p = self.rebound_anim_progress
                x = rx + (tx - rx) * p
                y_linear = ry + (ty - ry) * p
                bounce_height = 35
                y = y_linear - (4 * bounce_height * p * (1 - p))
                self._draw_single_ball(x + 2, y - 6)
                return

        if self.shot_anim_active:
            from_pos = player_positions.get(self.shot_anim_from_name or "")
            if from_pos is not None:
                tx, ty = self._get_shot_target(left_rim, right_rim)
                fx, fy = from_pos
                p = self.shot_anim_progress
                x = fx + (tx - fx) * p
                y_linear = fy + (ty - fy) * p
                arc_height = 55
                y = y_linear - (4 * arc_height * p * (1 - p))
                self._draw_single_ball(x + 4, y - 10)
                return

        if self.made_shot_hold_active:
            hold_side = self.made_shot_hold_team_side or self._get_current_shot_target_team_side()
            hx, hy = self._get_made_shot_hold_position(left_rim, right_rim, hold_side)
            self._draw_single_ball(hx, hy)
            return

        if self.ball_anim_active:
            from_pos = player_positions.get(self.ball_anim_from_name or "")
            to_pos = player_positions.get(self.ball_anim_to_name or "")
            if from_pos and to_pos:
                fx, fy = from_pos
                tx, ty = to_pos
                p = self.ball_anim_progress
                x = fx + (tx - fx) * p
                y = fy + (ty - fy) * p
                self._draw_single_ball(x, y)
                return

        ball_owner = self._get_ball_owner_name()
        if not ball_owner:
            return

        pos = player_positions.get(ball_owner)
        if pos is None:
            return

        x, y = pos
        self._draw_single_ball(x + 22, y - 22 + self._get_dribble_offset_y())

    def _draw_single_ball(self, x: float, y: float) -> None:
        r = 7
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill="#d07a2d", outline="black", width=2
        )
        self.canvas.create_line(x - r, y, x + r, y, fill="black", width=1)
        self.canvas.create_line(x, y - r, x, y + r, fill="black", width=1)

    def _on_resize(self, _event: tk.Event) -> None:
        self._draw_court()

    # =========================================================
    # Dribble animation
    # =========================================================
    def _schedule_idle_animation(self) -> None:
        self.root.after(60, self._idle_animation_tick)

    def _idle_animation_tick(self) -> None:
        self._advance_dribble_phase()
        if not self.finished:
            self._refresh_view()
        self._schedule_idle_animation()

    def _advance_dribble_phase(self) -> None:
        if self._is_ball_motion_active():
            self.dribble_phase = 0.0
            self.dribble_direction = 1
            return

        self.dribble_phase += self.dribble_step * self.dribble_direction
        if self.dribble_phase >= self.dribble_max_phase:
            self.dribble_phase = self.dribble_max_phase
            self.dribble_direction = -1
        elif self.dribble_phase <= 0.0:
            self.dribble_phase = 0.0
            self.dribble_direction = 1

    def _reset_dribble_animation(self) -> None:
        self.dribble_phase = 0.0
        self.dribble_direction = 1

    def _is_ball_motion_active(self) -> bool:
        return (
            self.ball_anim_active
            or self.shot_anim_active
            or self.rebound_anim_active
            or self.made_shot_hold_active
        )

    def _get_dribble_offset_y(self) -> float:
        if self._is_ball_motion_active():
            return 0.0
        return self.dribble_phase * 16.0

    # =========================================================
    # Animation helpers
    # =========================================================
    def _reset_ball_animation(self) -> None:
        self.ball_anim_active = False
        self.ball_anim_from_name = None
        self.ball_anim_to_name = None
        self.ball_anim_progress = 0.0
        self.ball_anim_step_index = 0
        self.ball_anim_steps = 10

    def _clear_pending_pass_shot(self) -> None:
        self.pending_shot_event_after_pass = None

    def _maybe_start_ball_animation(self, previous_owner: Optional[str], current_owner: Optional[str]) -> None:
        if self._is_result_only_mode():
            self._clear_pending_pass_shot()
            self._reset_ball_animation()
            return

        self._clear_pending_pass_shot()
        if self.shot_anim_active or self.rebound_anim_active:
            return
        if self.current_presentation_event and self._is_block_or_steal_turnover_presentation(self.current_presentation_event):
            self._reset_ball_animation()
            return
        if not previous_owner or not current_owner or previous_owner == current_owner:
            self._reset_ball_animation()
            return
        self.ball_anim_active = True
        self.ball_anim_from_name = previous_owner
        self.ball_anim_to_name = current_owner
        self.ball_anim_progress = 0.0
        self.ball_anim_step_index = 0
        self.root.after(self.ball_anim_interval_ms, self._animate_ball_step)

    def _animate_ball_step(self) -> None:
        if not self.ball_anim_active:
            return
        self.ball_anim_step_index += 1
        self.ball_anim_progress = min(1.0, self.ball_anim_step_index / self.ball_anim_steps)
        self._refresh_view()
        if self.ball_anim_step_index >= self.ball_anim_steps:
            pending_shot_event = self.pending_shot_event_after_pass
            self._reset_ball_animation()
            self._refresh_view()
            if isinstance(pending_shot_event, dict):
                self._clear_pending_pass_shot()
                self._start_shot_animation(pending_shot_event)
            return
        self.root.after(self.ball_anim_interval_ms, self._animate_ball_step)

    def _reset_shot_animation(self) -> None:
        self.shot_anim_active = False
        self.shot_anim_from_name = None
        self.shot_anim_team_side = None
        self.shot_anim_progress = 0.0
        self.shot_anim_step_index = 0
        self.shot_anim_result = None
        self.shot_anim_presentation_type = None
        self.pending_rebound_after_shot = False
        self.pending_rebound_to_name = None

    def _reset_made_shot_hold(self) -> None:
        self.made_shot_hold_active = False
        self.made_shot_hold_team_side = None
        self.made_shot_hold_camera_dx = None

    def _start_made_shot_hold(self, team_side: Optional[str], frozen_camera_dx: Optional[float] = None) -> None:
        self.made_shot_hold_active = True
        self.made_shot_hold_team_side = team_side if team_side in {"home", "away"} else self._get_current_shot_target_team_side()
        self.made_shot_hold_camera_dx = frozen_camera_dx

    def _is_shot_presentation(self, event: dict) -> bool:
        return event.get("presentation_type") in {
            "score_make_2", "score_make_3", "score_make_ft",
            "miss_jump_2", "miss_jump_3", "miss_free_throw",
        }

    def _is_block_or_steal_turnover_presentation(self, event: Optional[dict]) -> bool:
        if not isinstance(event, dict):
            return False
        return event.get("presentation_type") in {"block", "steal", "turnover"}

    def _extract_assister_name_from_event(self, event: Optional[dict]) -> Optional[str]:
        if not isinstance(event, dict):
            return None

        for key in (
            "assister_name",
            "support_player_name",
            "secondary_player_name",
        ):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value

        raw_play = event.get("raw_play")
        if isinstance(raw_play, dict):
            for key in (
                "assister_name",
                "support_player_name",
                "secondary_player_name",
            ):
                value = raw_play.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return None

    def _should_start_assist_pass_animation(self, event: Optional[dict]) -> bool:
        if not isinstance(event, dict):
            return False

        presentation_type = event.get("presentation_type")
        if presentation_type not in {"score_make_2", "score_make_3"}:
            return False

        assister = self._extract_assister_name_from_event(event)
        shooter = event.get("focus_player_name")
        if not isinstance(shooter, str) or not shooter.strip():
            return False
        if not isinstance(assister, str) or not assister.strip():
            return False
        if assister == shooter:
            return False

        return True

    def _start_assist_pass_animation(self, event: dict) -> None:
        if self._is_result_only_mode():
            self._clear_pending_pass_shot()
            self._reset_ball_animation()
            self._start_shot_animation(event)
            return

        assister = self._extract_assister_name_from_event(event)
        shooter = event.get("focus_player_name")

        if not isinstance(assister, str) or not assister.strip():
            self._clear_pending_pass_shot()
            self._start_shot_animation(event)
            return
        if not isinstance(shooter, str) or not shooter.strip():
            self._clear_pending_pass_shot()
            self._start_shot_animation(event)
            return
        if assister == shooter:
            self._clear_pending_pass_shot()
            self._start_shot_animation(event)
            return

        self._reset_shot_animation()
        self._reset_rebound_animation()
        self._reset_ball_animation()

        self.pending_shot_event_after_pass = event
        self.ball_anim_active = True
        self.ball_anim_from_name = assister
        self.ball_anim_to_name = shooter
        self.ball_anim_progress = 0.0
        self.ball_anim_step_index = 0
        self.ball_anim_steps = 14
        self.root.after(self.ball_anim_interval_ms, self._animate_ball_step)

    def _get_current_presentation_type(self) -> Optional[str]:
        if isinstance(self.current_presentation_event, dict):
            presentation_type = self.current_presentation_event.get("presentation_type")
            if isinstance(presentation_type, str) and presentation_type.strip():
                return presentation_type
        if isinstance(self.current_play, dict):
            result_type = self.current_play.get("result_type")
            mapping = {
                "steal": "steal",
                "turnover": "turnover",
                "block_def_rebound": "block",
            }
            mapped = mapping.get(str(result_type or ""))
            if mapped:
                return mapped
        return None

    def _start_shot_animation(self, event: dict) -> None:
        if self._is_result_only_mode():
            self._reset_shot_animation()
            return

        shooter = event.get("focus_player_name")
        if not isinstance(shooter, str) or not shooter.strip():
            self._reset_shot_animation()
            return

        self._clear_pending_pass_shot()
        self._reset_ball_animation()
        self._reset_rebound_animation()

        self.shot_anim_active = True
        self.shot_anim_from_name = shooter
        self.shot_anim_team_side = self._infer_player_team_side(shooter)
        self.shot_anim_progress = 0.0
        self.shot_anim_step_index = 0
        self.shot_anim_presentation_type = event.get("presentation_type")
        ptype = event.get("presentation_type")
        self.shot_anim_result = "make" if ptype in {"score_make_2", "score_make_3", "score_make_ft"} else "miss"

        support = event.get("support_player_name")
        self.pending_rebound_after_shot = self.shot_anim_result == "miss" and isinstance(support, str) and bool(support.strip())
        self.pending_rebound_to_name = support if self.pending_rebound_after_shot else None

        self.root.after(self.shot_anim_interval_ms, self._animate_shot_step)

    def _animate_shot_step(self) -> None:
        if not self.shot_anim_active:
            return

        self.shot_anim_step_index += 1
        self.shot_anim_progress = min(1.0, self.shot_anim_step_index / self.shot_anim_steps)
        self._refresh_view()

        if self.shot_anim_step_index >= self.shot_anim_steps:
            rebound_to = self.pending_rebound_to_name
            shot_result = self.shot_anim_result
            hold_side = self.shot_anim_team_side or self._get_current_shot_target_team_side()
            self._reset_shot_animation()

            if shot_result == "make":
                self._start_made_shot_hold(hold_side, frozen_camera_dx=self.last_camera_focus_dx)

            self._refresh_view()

            if rebound_to:
                self._start_rebound_animation_direct(rebound_to)
            return

        self.root.after(self.shot_anim_interval_ms, self._animate_shot_step)

    def _get_shot_target(self, left_rim: tuple[float, float], right_rim: tuple[float, float]) -> tuple[float, float]:
        shot_target_side = self._get_current_shot_target_team_side()
        if shot_target_side == "home":
            tx, ty = right_rim
        elif shot_target_side == "away":
            tx, ty = left_rim
        else:
            tx, ty = right_rim

        if self.shot_anim_result == "miss":
            tx = tx + 18 if shot_target_side == "home" else tx - 18
            ty = ty - 12

        return tx, ty

    def _get_made_shot_hold_position(
        self,
        left_rim: tuple[float, float],
        right_rim: tuple[float, float],
        hold_side: Optional[str],
    ) -> tuple[float, float]:
        if hold_side == "home":
            rx, ry = right_rim
        elif hold_side == "away":
            rx, ry = left_rim
        else:
            rx, ry = right_rim

        # 成功後はリング下/ネット下に静かに収め、シューターへ戻さない
        return rx, ry + 18

    def _reset_rebound_animation(self) -> None:
        self.rebound_anim_active = False
        self.rebound_anim_team_side = None
        self.rebound_anim_progress = 0.0
        self.rebound_anim_step_index = 0
        self.rebound_anim_to_name = None
        self.rebound_anim_presentation_type = None

    def _is_rebound_presentation_type(self, presentation_type: Optional[str]) -> bool:
        return presentation_type in {"def_rebound", "off_rebound", "off_rebound_keep"}

    def _extract_rebounder_name_from_event(self, event: Optional[dict]) -> Optional[str]:
        if not isinstance(event, dict):
            return None

        for key in (
            "focus_player_name",
            "primary_player_name",
            "rebounder_name",
            "final_rebounder_name",
            "off_rebounder_name",
            "def_rebounder_name",
            "support_player_name",
        ):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value

        raw_play = event.get("raw_play")
        if isinstance(raw_play, dict):
            for key in (
                "rebounder_name",
                "final_rebounder_name",
                "off_rebounder_name",
                "def_rebounder_name",
                "primary_player_name",
                "secondary_player_name",
            ):
                value = raw_play.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return None

    def _is_rebound_presentation(self, event: dict) -> bool:
        return self._is_rebound_presentation_type(event.get("presentation_type"))

    def _start_rebound_animation(self, event: dict) -> None:
        if self._is_result_only_mode():
            rebounder = self._extract_rebounder_name_from_event(event)
            self.rebound_hold_owner_name = rebounder if isinstance(rebounder, str) else None
            self._reset_rebound_animation()
            return

        rebounder = self._extract_rebounder_name_from_event(event)
        if not isinstance(rebounder, str) or not rebounder.strip():
            self._reset_rebound_animation()
            return
        self._start_rebound_animation_direct(rebounder, event.get("presentation_type"))

    def _start_rebound_animation_direct(self, rebounder: str, presentation_type: Optional[str] = None) -> None:
        self._reset_ball_animation()
        self.rebound_hold_owner_name = rebounder
        self.rebound_anim_active = True
        self.rebound_anim_team_side = self._infer_player_team_side(rebounder)
        self.rebound_anim_progress = 0.0
        self.rebound_anim_step_index = 0
        self.rebound_anim_to_name = rebounder
        self.rebound_anim_presentation_type = presentation_type
        self.root.after(self.rebound_anim_interval_ms, self._animate_rebound_step)

    def _animate_rebound_step(self) -> None:
        if not self.rebound_anim_active:
            return

        self.rebound_anim_step_index += 1
        self.rebound_anim_progress = min(1.0, self.rebound_anim_step_index / self.rebound_anim_steps)
        self._refresh_view()

        if self.rebound_anim_step_index >= self.rebound_anim_steps:
            self._reset_rebound_animation()
            self._refresh_view()
            return

        self.root.after(self.rebound_anim_interval_ms, self._animate_rebound_step)

    def _get_rebound_start(self, left_rim: tuple[float, float], right_rim: tuple[float, float]) -> tuple[float, float]:
        # Rebound starts from the rim that the immediately preceding shot targeted.
        shot_target_side = self.shot_anim_team_side
        if shot_target_side == "home":
            return right_rim
        if shot_target_side == "away":
            return left_rim

        offense_side = self._get_offense_team_side()
        if offense_side == "home":
            return right_rim
        if offense_side == "away":
            return left_rim
        return right_rim

    # =========================================================
    # Actions
    # =========================================================
    def _toggle_autoplay(self) -> None:
        if self.finished:
            return
        self.is_autoplay = not self.is_autoplay
        self._refresh_view()
        if self.is_autoplay:
            self.root.after(self.autoplay_interval_ms, self._autoplay_tick)

    def _reset_view_state(self) -> None:
        self.is_autoplay = False
        self.finished = False
        self.current_play = None
        self.current_presentation_event = None
        self.current_commentary = "観戦を開始してください。"
        self.current_play_index = -1
        self.rebound_hold_owner_name = None
        self._reset_match_cursors()
        self._refresh_view()

    # =========================================================
    # Safe data extraction
    # =========================================================
    def _coerce_commentary_text(self, entry: Any) -> str:
        if isinstance(entry, str):
            return entry
        if isinstance(entry, dict):
            for key in ("text", "commentary_text", "commentary", "description"):
                value = entry.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return str(entry)

    def _fallback_commentary_from_play(self, play: dict) -> str:
        if not isinstance(play, dict):
            return "プレーが進行しました。"
        for key in ("commentary_text", "summary_text", "description"):
            value = play.get(key)
            if isinstance(value, str) and value.strip():
                return value
        result_type = play.get("result_type", "play")
        primary = play.get("primary_player_name", "-")
        secondary = play.get("secondary_player_name", "-")
        return f"{result_type} | primary={primary} | secondary={secondary}"

    def _build_commentary_from_presentation(self, event: dict) -> str:
        main_text = event.get("main_text")
        sub_text = event.get("sub_text")
        if isinstance(main_text, str) and main_text.strip():
            if isinstance(sub_text, str) and sub_text.strip():
                return f"{main_text} {sub_text}"
            return main_text
        return self._fallback_commentary_from_play(event.get("raw_play", {}))

    def _extract_team_name(self, side: str) -> str:
        team_obj = getattr(self.match, "home_team" if side == "home" else "away_team", None)
        if team_obj is None:
            return side.upper()
        for attr in ("name", "team_name", "full_name"):
            value = getattr(team_obj, attr, None)
            if isinstance(value, str) and value.strip():
                return value
        return str(team_obj)

    def _extract_score_text(self) -> str:
        if self.current_presentation_event is None and self.current_play is None:
            return "0 - 0"

        if self.current_presentation_event:
            home_score = self.current_presentation_event.get("home_score")
            away_score = self.current_presentation_event.get("away_score")
            if home_score is not None and away_score is not None:
                return f"{home_score} - {away_score}"

        if self.current_play:
            home_score = self.current_play.get("home_score")
            away_score = self.current_play.get("away_score")
            if home_score is not None and away_score is not None:
                return f"{home_score} - {away_score}"

        return "0 - 0"

    def _extract_period_text(self) -> str:
        if self.current_presentation_event is None and self.current_play is None:
            return "Q1 10:00"

        quarter = None
        clock_seconds = None

        if self.current_presentation_event:
            quarter = self.current_presentation_event.get("quarter")
            clock_seconds = self.current_presentation_event.get("clock_seconds")

        if quarter is None and self.current_play:
            quarter = self.current_play.get("quarter", 1)

        if clock_seconds is None and self.current_play:
            clock_seconds = self.current_play.get("clock_seconds")
            if clock_seconds is None:
                clock_seconds = self.current_play.get("start_clock_seconds")
            if clock_seconds is None:
                clock_seconds = self.current_play.get("end_clock_seconds")

        if quarter is None:
            quarter = 1

        if clock_seconds is None:
            return f"Q{quarter} 10:00" if quarter == 1 else f"Q{quarter} --:--"

        mm = int(clock_seconds) // 60
        ss = int(clock_seconds) % 60
        return f"Q{quarter} {mm:02d}:{ss:02d}"

    def _extract_importance(self) -> str:
        if self.current_presentation_event:
            value = self.current_presentation_event.get("importance")
            if isinstance(value, str):
                return value
        return "low"

    def _court_overlay_title(self) -> str:
        if self.current_presentation_event:
            headline = self.current_presentation_event.get("headline")
            if isinstance(headline, str) and headline.strip():
                return headline

            ptype = str(self.current_presentation_event.get("presentation_type") or "")
            title_map = {
                "score_make_2": "2ポイント成功",
                "score_make_3": "3ポイント成功",
                "score_make_ft": "フリースロー成功",
                "miss_jump_2": "2ポイント失敗",
                "miss_jump_3": "3ポイント失敗",
                "miss_free_throw": "フリースロー失敗",
                "def_rebound": "ディフェンスリバウンド",
                "off_rebound_keep": "オフェンスリバウンド",
                "turnover": "ターンオーバー",
                "steal": "スティール",
                "block": "ブロック",
                "quarter_start": "クォーター開始",
                "quarter_end": "クォーター終了",
                "game_end": "試合終了",
            }
            if ptype in title_map:
                return title_map[ptype]

        if not self.current_play:
            return "試合開始前"

        result_type = str(self.current_play.get("result_type") or "")
        title_map = {
            "made_2": "2ポイント成功",
            "made_3": "3ポイント成功",
            "made_ft": "フリースロー成功",
            "miss_2": "2ポイント失敗",
            "miss_3": "3ポイント失敗",
            "miss_ft": "フリースロー失敗",
            "def_rebound": "ディフェンスリバウンド",
            "off_rebound": "オフェンスリバウンド",
            "turnover": "ターンオーバー",
            "steal": "スティール",
            "block": "ブロック",
            "quarter_start": "クォーター開始",
            "quarter_end": "クォーター終了",
            "game_end": "試合終了",
        }
        return title_map.get(result_type, "プレー")

    def _court_overlay_subtitle(self) -> str:
        period_text = self._extract_period_text()
        score_text = self._extract_score_text()

        short_parts: list[str] = []
        if period_text:
            short_parts.append(period_text)
        if score_text:
            short_parts.append(f"スコアは{score_text}")

        return " | ".join([part for part in short_parts if part])

    def _get_team_display_players(self, side: str, limit: int = 5) -> list[str]:
        team_obj = getattr(self.match, "home_team" if side == "home" else "away_team", None)
        if team_obj is None:
            return []

        candidates: list[Any] = []
        for attr in ("active_players", "rotation_players", "players"):
            value = getattr(team_obj, attr, None)
            if isinstance(value, list) and value:
                candidates = value
                break

        ordered_players = self._sort_players_for_display(candidates)
        base_names: list[str] = []
        for player in ordered_players:
            name = self._extract_player_name(player)
            if name and name != "-" and name not in base_names:
                base_names.append(name)

        key_names = self._get_key_players_for_side(side)
        names: list[str] = []
        for name in key_names + base_names:
            if name and name != "-" and name not in names:
                names.append(name)

        while len(names) < limit:
            prefix = "H" if side == "home" else "A"
            names.append(f"{prefix}{len(names)+1}")

        return names[:limit]

    def _sort_players_for_display(self, players: list[Any]) -> list[Any]:
        if not players:
            return []

        grouped: dict[str, list[Any]] = {pos: [] for pos in ("PG", "SG", "SF", "PF", "C")}
        others: list[Any] = []

        for player in players:
            position = self._extract_player_position(player)
            if position in grouped:
                grouped[position].append(player)
            else:
                others.append(player)

        ordered: list[Any] = []
        for pos in ("PG", "SG", "SF", "PF", "C"):
            ordered.extend(grouped[pos])
        ordered.extend(others)
        return ordered

    def _get_key_players_for_side(self, side: str) -> list[str]:
        if not self.current_presentation_event:
            return []

        focus = self.current_presentation_event.get("focus_player_name")
        support = self.current_presentation_event.get("support_player_name")
        handoff_giver = self.current_presentation_event.get("handoff_giver_name")
        handoff_receiver = self.current_presentation_event.get("handoff_receiver_name")
        back_screener = self.current_presentation_event.get("back_screener_name")
        back_target = self.current_presentation_event.get("back_screen_target_name")
        names = []

        for name in (focus, support, handoff_giver, handoff_receiver, back_screener, back_target):
            if isinstance(name, str) and name.strip():
                inferred = self._infer_player_team_side_from_rosters(name)
                if inferred == side and name not in names:
                    names.append(name)

        return names

    def _infer_player_team_side_from_rosters(self, player_name: str) -> Optional[str]:
        home_all = self._get_team_all_player_names("home")
        away_all = self._get_team_all_player_names("away")
        if player_name in home_all:
            return "home"
        if player_name in away_all:
            return "away"
        return None

    def _get_team_all_player_names(self, side: str) -> list[str]:
        team_obj = getattr(self.match, "home_team" if side == "home" else "away_team", None)
        if team_obj is None:
            return []

        names: list[str] = []
        for attr in ("active_players", "rotation_players", "players"):
            value = getattr(team_obj, attr, None)
            if isinstance(value, list):
                for player in value:
                    name = self._extract_player_name(player)
                    if name and name != "-" and name not in names:
                        names.append(name)
        return names

    def _extract_player_name(self, player: Any) -> str:
        if player is None:
            return "-"
        if isinstance(player, str):
            return player
        for attr in ("name", "full_name", "player_name"):
            value = getattr(player, attr, None)
            if isinstance(value, str) and value.strip():
                return value
        return str(player)

    def _extract_player_position(self, player: Any) -> Optional[str]:
        if player is None or isinstance(player, str):
            return None
        value = getattr(player, "position", None)
        if not isinstance(value, str):
            return None
        normalized = value.strip().upper()
        if normalized in {"PG", "SG", "SF", "PF", "C"}:
            return normalized
        return None

    def _extract_player_archetype(self, player: Any) -> str:
        if player is None or isinstance(player, str):
            return ""
        value = getattr(player, "archetype", None)
        if not isinstance(value, str):
            return ""
        return value.strip().lower()

    def _extract_player_archetype_by_name(self, player_name: str) -> str:
        player = self._find_player_object_by_name(player_name)
        return self._extract_player_archetype(player)

    def _find_player_object_by_name(self, player_name: str) -> Optional[Any]:
        if not player_name or player_name == "-":
            return None

        for side in ("home", "away"):
            team_obj = getattr(self.match, "home_team" if side == "home" else "away_team", None)
            if team_obj is None:
                continue
            for attr in ("active_players", "rotation_players", "players"):
                value = getattr(team_obj, attr, None)
                if not isinstance(value, list):
                    continue
                for player in value:
                    if self._extract_player_name(player) == player_name:
                        return player
        return None


    def _apply_archetype_adjustment(
        self,
        nx: float,
        ny: float,
        player_name: str,
        team_side: str,
        offense_side: Optional[str],
        structure_type: Optional[str],
        offense_direction: Optional[str],
        is_offense: bool,
    ) -> tuple[float, float]:
        """Apply small, safe archetype-based offsets in normalized court space.

        This intentionally preserves structure/position as the primary driver and only
        adds mild flavor so the layout does not break.
        """
        archetype = self._extract_player_archetype_by_name(player_name)
        if not archetype:
            return nx, ny

        # Direction: offense moves toward basket direction on x-axis.
        # left_to_right => positive x is forward, right_to_left => negative x is forward.
        forward_sign = 1.0 if offense_direction != 'right_to_left' else -1.0
        if team_side != offense_side:
            # Defensive pressure should mirror relative to offensive flow.
            forward_sign *= -1.0

        dx = 0.0
        dy = 0.0

        # Small defaults by role. Positive |dy| means more spread; sign chosen from side.
        side_sign = -1.0 if ny < 0.5 else 1.0

        if is_offense:
            if archetype in {'playmaker', 'floor_general'}:
                dx += 0.010 * forward_sign
                dy += 0.020 * (-1 if abs(ny - 0.5) < 0.08 else (-side_sign))
                # Nudge toward middle a bit
                dy += (0.5 - ny) * 0.12
            elif archetype == 'scoring_guard':
                dx += 0.008 * forward_sign
                dy += 0.022 * side_sign
            elif archetype == 'slasher':
                dx += 0.016 * forward_sign
                dy += (0.5 - ny) * 0.18
            elif archetype == 'two_way_wing':
                dx += 0.004 * forward_sign
                dy += 0.010 * side_sign
            elif archetype == 'stretch_big':
                dx += 0.006 * forward_sign
                dy += 0.020 * side_sign
            elif archetype in {'rim_protector', 'rebounder'}:
                dx += 0.004 * forward_sign
                dy += (0.5 - ny) * 0.22

            if structure_type == 'fast_break':
                if archetype in {'slasher', 'playmaker', 'floor_general'}:
                    dx += 0.010 * forward_sign
                if archetype in {'scoring_guard', 'two_way_wing', 'stretch_big'}:
                    dy += 0.008 * side_sign
            elif structure_type == 'second_chance':
                if archetype in {'rim_protector', 'rebounder'}:
                    dy += (0.5 - ny) * 0.18
                elif archetype in {'scoring_guard', 'stretch_big'}:
                    dy += 0.006 * side_sign
        else:
            # Defense: lighter influence than offense.
            if archetype in {'rim_protector', 'rebounder'}:
                dy += (0.5 - ny) * 0.14
            elif archetype in {'playmaker', 'floor_general'}:
                dx += 0.004 * forward_sign
                dy += (0.5 - ny) * 0.06
            elif archetype in {'scoring_guard', 'two_way_wing', 'stretch_big'}:
                dy += 0.006 * side_sign
            elif archetype == 'slasher':
                dy += (0.5 - ny) * 0.08

            if structure_type == 'fast_break':
                dx += 0.004 * forward_sign
            elif structure_type == 'second_chance' and archetype in {'rim_protector', 'rebounder'}:
                dy += (0.5 - ny) * 0.10

        nx = max(0.06, min(0.94, nx + dx))
        ny = max(0.08, min(0.92, ny + dy))
        return nx, ny

    def _short_player_name(self, name: str) -> str:
        if not name or name == "-":
            return "?"
        if name.startswith("Player_"):
            return name.replace("Player_", "P")
        if name.startswith("Fictional_"):
            return name.replace("Fictional_", "F")
        return name[:3]

    def _is_focus_player(self, player_name: str) -> bool:
        if not player_name or player_name == "-":
            return False
        if self.current_presentation_event:
            focus = self.current_presentation_event.get("focus_player_name")
            support = self.current_presentation_event.get("support_player_name")
            handoff_giver = self.current_presentation_event.get("handoff_giver_name")
            handoff_receiver = self.current_presentation_event.get("handoff_receiver_name")
            back_screener = self.current_presentation_event.get("back_screener_name")
            back_target = self.current_presentation_event.get("back_screen_target_name")
            return player_name in {focus, support, handoff_giver, handoff_receiver, back_screener, back_target}
        if self.current_play:
            return (
                player_name == self.current_play.get("primary_player_name")
                or player_name == self.current_play.get("secondary_player_name")
            )
        return False

    def _extract_stealer_name_from_event(self, event: Optional[dict]) -> Optional[str]:
        if not isinstance(event, dict):
            return None

        # presentation event では
        # focus_player_name = 奪った側
        # support_player_name = 奪われた側
        # なので focus を support より優先する
        for key in (
            "stealer_name",
            "focus_player_name",
            "secondary_player_name",
            "support_player_name",
        ):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value

        raw_play = event.get("raw_play")
        if isinstance(raw_play, dict):
            for key in (
                "stealer_name",
                "focus_player_name",
                "secondary_player_name",
                "support_player_name",
            ):
                value = raw_play.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return None

    def _extract_blocker_name_from_event(self, event: Optional[dict]) -> Optional[str]:
        if not isinstance(event, dict):
            return None

        # presentation event では
        # focus_player_name = ブロックした側
        # support_player_name = 打たれた側
        # なので focus を support より優先する
        for key in (
            "blocker_name",
            "focus_player_name",
            "secondary_player_name",
            "support_player_name",
        ):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value

        raw_play = event.get("raw_play")
        if isinstance(raw_play, dict):
            for key in (
                "blocker_name",
                "focus_player_name",
                "secondary_player_name",
                "support_player_name",
            ):
                value = raw_play.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return None

    def _resolve_current_event_ball_owner_name(self) -> Optional[str]:
        if self.rebound_anim_active:
            rebound_target = self.rebound_anim_to_name
            if isinstance(rebound_target, str) and rebound_target.strip():
                return rebound_target

        if isinstance(self.rebound_hold_owner_name, str) and self.rebound_hold_owner_name.strip():
            return self.rebound_hold_owner_name

        if self.current_presentation_event:
            presentation_type = self.current_presentation_event.get("presentation_type")

            if self._is_rebound_presentation_type(presentation_type):
                rebounder = self._extract_rebounder_name_from_event(self.current_presentation_event)
                if isinstance(rebounder, str) and rebounder.strip():
                    return rebounder

            if presentation_type == "steal":
                stealer = self._extract_stealer_name_from_event(self.current_presentation_event)
                if isinstance(stealer, str) and stealer.strip():
                    return stealer
                return ""

            if presentation_type == "turnover":
                stealer = self._extract_stealer_name_from_event(self.current_presentation_event)
                if isinstance(stealer, str) and stealer.strip():
                    return stealer
                return ""

            if presentation_type == "block":
                rebounder = self._extract_rebounder_name_from_event(self.current_presentation_event)
                if isinstance(rebounder, str) and rebounder.strip():
                    return rebounder
                return ""

            structure_type = self.current_presentation_event.get("structure_type")
            if structure_type == "spain_pick_and_roll":
                action = self._get_spain_action() or "setup"
                handler = self._get_spain_role_name("ball_handler_name")
                kickout_target = self._get_spain_role_name("spain_kickout_target_name")
                if action == "kickout" and isinstance(kickout_target, str) and kickout_target.strip():
                    return kickout_target
                if isinstance(handler, str) and handler.strip():
                    return handler

            if structure_type == "handoff":
                action = self._get_handoff_action() or "setup"
                receiver = self._get_handoff_role_name("handoff_receiver_name")
                giver = self._get_handoff_role_name("handoff_giver_name")
                if action in {"exchange", "turn_corner", "reject"} and isinstance(receiver, str) and receiver.strip():
                    return receiver
                if isinstance(giver, str) and giver.strip():
                    return giver
                if isinstance(receiver, str) and receiver.strip():
                    return receiver

            focus = self.current_presentation_event.get("focus_player_name")
            if isinstance(focus, str) and focus.strip():
                return focus
            support = self.current_presentation_event.get("support_player_name")
            if isinstance(support, str) and support.strip():
                return support

        return None

    def _resolve_current_play_ball_owner_name(self) -> Optional[str]:
        if not self.current_play:
            return None

        result_type = self.current_play.get("result_type")

        if result_type == "steal":
            stealer = self._extract_stealer_name_from_event(self.current_play)
            if isinstance(stealer, str) and stealer.strip():
                return stealer
            return ""

        if result_type == "turnover":
            stealer = self._extract_stealer_name_from_event(self.current_play)
            if isinstance(stealer, str) and stealer.strip():
                return stealer
            return ""

        if result_type == "block_def_rebound":
            rebounder = self._extract_rebounder_name_from_event(self.current_play)
            if isinstance(rebounder, str) and rebounder.strip():
                return rebounder
            return ""

        rebounder = self._extract_rebounder_name_from_event(self.current_play)
        if isinstance(rebounder, str) and rebounder.strip():
            return rebounder

        primary = self.current_play.get("primary_player_name")
        if isinstance(primary, str) and primary.strip():
            return primary
        secondary = self.current_play.get("secondary_player_name")
        if isinstance(secondary, str) and secondary.strip():
            return secondary
        return None

    def _get_ball_owner_name(self) -> Optional[str]:
        if self.made_shot_hold_active:
            return ""

        event_owner = self._resolve_current_event_ball_owner_name()
        if event_owner is not None:
            return event_owner

        play_owner = self._resolve_current_play_ball_owner_name()
        if play_owner is not None:
            return play_owner

        return None

    def _infer_player_team_side(self, player_name: str) -> Optional[str]:
        return self._infer_player_team_side_from_rosters(player_name)

    def _get_offense_team_side(self) -> Optional[str]:
        if self.current_presentation_event:
            team_side = self.current_presentation_event.get("team_side")
            if team_side in {"home", "away"}:
                return team_side

            focus = self.current_presentation_event.get("focus_player_name")
            if isinstance(focus, str) and focus.strip():
                return self._infer_player_team_side(focus)

        if self.current_play:
            for key in ("offense_team_side", "scoring_team"):
                value = self.current_play.get(key)
                if value in {"home", "away"}:
                    return value

            primary = self.current_play.get("primary_player_name")
            if isinstance(primary, str) and primary.strip():
                return self._infer_player_team_side(primary)

        return None


def run_spectate_view(
    match: Any,
    override_events: Optional[list[dict]] = None,
    spectate_mode: str = "full",
) -> None:
    view = SpectateView(
        match=match,
        override_events=override_events,
        spectate_mode=spectate_mode,
    )
    view.run()


if __name__ == "__main__":
    print("This file is a UI module. Import it and call run_spectate_view(match).")
