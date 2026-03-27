"""
Highlight Camera System for Basketball Project.

Recommended location:
basketball_sim/systems/highlight_camera_system.py

Purpose
-------
PresentationLayer が出力した presentation_event を読み取り、
観戦演出用のカメラ指示データへ安全に変換する。

Design principles
-----------------
- 安全第一: 既存の試合進行ロジックを変更しない
- Read-only: presentation_event を破壊しない
- 段階導入: まずは「演出ルール決定」に専念する
- 将来拡張しやすい構造にする

Current scope
-------------
このバージョンでは以下を決定する:
- 演出レベル
- ズームレベル
- フォーカス対象
- カメラ追尾モード
- カメラカット種別
- リプレイ発火
- ハイライト優先度
- 将来の 2D viewer / replay system が使いやすい補助情報
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

try:
    from basketball_sim.systems.presentation_layer import PresentationLayer
except Exception:  # pragma: no cover - safe fallback for staged integration
    PresentationLayer = None  # type: ignore[assignment]


class HighlightCameraSystem:
    """
    match または presentation_events(list[dict]) のどちらでも受け取れるようにする。
    これにより以下の両方を安全にサポートする。

    1. HighlightCameraSystem(match)
    2. HighlightCameraSystem(presentation_events)
    """

    def __init__(self, source: Any) -> None:
        self.source = source
        self.match = None if isinstance(source, list) else source
        self.camera_events: list[dict] = []
        self.camera_index: int = 0
        self.presentation_events: list[dict] = []

    # =========================================================
    # Public API
    # =========================================================
    def build(self) -> list[dict]:
        self.presentation_events = self._get_presentation_events()
        self.camera_events = [
            self._build_camera_event(event_no=i, presentation_event=event)
            for i, event in enumerate(self.presentation_events)
            if isinstance(event, dict)
        ]
        self.camera_index = 0
        return self.camera_events

    def get_events(self) -> list[dict]:
        if not self.camera_events:
            self.build()
        return self.camera_events

    def get_event_at(self, index: int) -> Optional[dict]:
        events = self.get_events()
        if 0 <= index < len(events):
            return events[index]
        return None

    def get_next_event(self) -> Optional[dict]:
        events = self.get_events()
        if self.camera_index >= len(events):
            return None
        event = events[self.camera_index]
        self.camera_index += 1
        return event

    def peek_next_event(self) -> Optional[dict]:
        events = self.get_events()
        if self.camera_index >= len(events):
            return None
        return events[self.camera_index]

    def reset_cursor(self) -> None:
        self.camera_index = 0

    def get_event_count(self) -> int:
        return len(self.get_events())

    def get_level_counts(self) -> dict[str, int]:
        events = self.get_events()
        counts = Counter(event.get("camera_level", "unknown") for event in events)
        return dict(counts)

    def get_replay_count(self) -> int:
        events = self.get_events()
        return sum(1 for event in events if event.get("replay_flag") is True)

    def print_preview(self, limit: int = 8) -> None:
        events = self.get_events()
        counts = self.get_level_counts()

        print("[CAMERA] Preview")
        print(f"[CAMERA] total_events={len(events)}")
        print(f"[CAMERA] replay_events={self.get_replay_count()}")
        print("[CAMERA] level_counts")
        for key in sorted(counts.keys()):
            print(f"  - {key:<16}: {counts[key]}")

        print(f"[CAMERA] first_{limit}")
        for event in events[:limit]:
            print(self._format_preview_line(event))

        print(f"[CAMERA] last_{limit}")
        for event in events[-limit:]:
            print(self._format_preview_line(event))

    # =========================================================
    # Internal build
    # =========================================================
    def _get_presentation_events(self) -> list[dict]:
        if isinstance(self.source, list):
            return [event for event in self.source if isinstance(event, dict)]

        if hasattr(self.source, "presentation_events"):
            cached = getattr(self.source, "presentation_events", None)
            if isinstance(cached, list) and cached:
                return [event for event in cached if isinstance(event, dict)]

        if PresentationLayer is None:
            return []

        try:
            layer = PresentationLayer(self.source)
            events = layer.build()
        except Exception:
            return []

        if not isinstance(events, list):
            return []

        return [event for event in events if isinstance(event, dict)]

    def _build_camera_event(self, event_no: int, presentation_event: dict) -> dict:
        highlight_score = self._to_int(presentation_event.get("highlight_score"), default=0)
        presentation_type = str(presentation_event.get("presentation_type", "play_event"))
        importance = str(presentation_event.get("importance", "low"))
        structure_type = self._to_optional_str(presentation_event.get("structure_type"))
        focus_player_name = self._to_optional_str(presentation_event.get("focus_player_name"))
        support_player_name = self._to_optional_str(presentation_event.get("support_player_name"))
        team_side = self._to_optional_str(presentation_event.get("team_side"))
        quarter = self._to_optional_int(presentation_event.get("quarter"))
        clock_seconds = self._to_optional_int(presentation_event.get("clock_seconds"))
        highlight_tags = self._safe_str_list(presentation_event.get("highlight_tags"))
        highlight_tier = self._to_optional_str(presentation_event.get("highlight_tier"))
        force_tier = self._to_optional_str(presentation_event.get("force_tier"))
        emphasis_level_hint = self._to_optional_str(presentation_event.get("emphasis_level"))
        camera_style_hint = self._to_optional_str(presentation_event.get("recommended_camera_style"))
        clip_role = self._to_optional_str(presentation_event.get("clip_role"))

        camera_level, camera_level_rank = self._determine_camera_level(
            highlight_score=highlight_score,
            presentation_type=presentation_type,
            importance=importance,
            highlight_tags=highlight_tags,
            structure_type=structure_type,
        )
        camera_level, camera_level_rank = self._apply_camera_level_hint(
            camera_level=camera_level,
            camera_level_rank=camera_level_rank,
            presentation_type=presentation_type,
            camera_style_hint=camera_style_hint,
            emphasis_level_hint=emphasis_level_hint,
            highlight_tier=highlight_tier,
            force_tier=force_tier,
            clip_role=clip_role,
        )
        zoom_level = self._determine_zoom_level(
            camera_level=camera_level,
            presentation_type=presentation_type,
            structure_type=structure_type,
            highlight_tags=highlight_tags,
        )
        zoom_level = self._apply_zoom_hint(
            zoom_level=zoom_level,
            presentation_type=presentation_type,
            camera_style_hint=camera_style_hint,
            emphasis_level_hint=emphasis_level_hint,
        )
        focus_target, focus_targets = self._determine_focus_targets(
            presentation_event=presentation_event,
            presentation_type=presentation_type,
            camera_level=camera_level,
        )
        track_mode = self._determine_track_mode(
            camera_level=camera_level,
            presentation_type=presentation_type,
            structure_type=structure_type,
        )
        cut_type = self._determine_cut_type(
            camera_level=camera_level,
            presentation_type=presentation_type,
            structure_type=structure_type,
            highlight_tags=highlight_tags,
        )
        cut_type = self._apply_cut_type_hint(
            cut_type=cut_type,
            presentation_type=presentation_type,
            camera_style_hint=camera_style_hint,
            emphasis_level_hint=emphasis_level_hint,
        )
        cut_count = self._determine_cut_count(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )
        replay_flag = self._determine_replay_flag(
            camera_level=camera_level,
            presentation_type=presentation_type,
        )
        replay_style = self._determine_replay_style(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )
        replay_priority = self._determine_replay_priority(
            camera_level=camera_level,
            highlight_score=highlight_score,
            highlight_tags=highlight_tags,
        )
        slow_motion = self._determine_slow_motion(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )
        emphasis_strength = self._determine_emphasis_strength(camera_level)
        overlay_preset = self._determine_overlay_preset(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )
        highlight_priority = self._determine_highlight_priority(
            camera_level=camera_level,
            highlight_score=highlight_score,
            highlight_tags=highlight_tags,
            importance=importance,
        )
        camera_anchor = self._determine_camera_anchor(
            presentation_type=presentation_type,
            structure_type=structure_type,
            focus_target=focus_target,
            team_side=team_side,
        )
        shot_outcome = self._infer_shot_outcome(presentation_type)
        score_margin = self._infer_score_margin(presentation_event)
        scoreboard_emphasis = self._determine_scoreboard_emphasis(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )
        transition_profile = self._determine_transition_profile(
            camera_level=camera_level,
            presentation_type=presentation_type,
            structure_type=structure_type,
        )
        transition_profile = self._apply_transition_hint(
            transition_profile=transition_profile,
            presentation_type=presentation_type,
            camera_style_hint=camera_style_hint,
        )
        ui_emphasis = self._determine_ui_emphasis(
            camera_level=camera_level,
            presentation_type=presentation_type,
            highlight_tags=highlight_tags,
        )

        return {
            "camera_event_no": event_no,
            "play_no": presentation_event.get("play_no"),
            "quarter": quarter,
            "clock_seconds": clock_seconds,
            "home_score": presentation_event.get("home_score"),
            "away_score": presentation_event.get("away_score"),
            "presentation_type": presentation_type,
            "headline": presentation_event.get("headline"),
            "main_text": presentation_event.get("main_text"),
            "sub_text": presentation_event.get("sub_text"),
            "importance": importance,
            "highlight_score": highlight_score,
            "highlight_tags": highlight_tags,
            "highlight_tier": highlight_tier,
            "force_tier": force_tier,
            "emphasis_level_hint": emphasis_level_hint,
            "camera_style_hint": camera_style_hint,
            "clip_role": clip_role,
            "structure_type": structure_type,
            "team_side": team_side,
            "focus_player_name": focus_player_name,
            "support_player_name": support_player_name,
            "camera_level": camera_level,
            "camera_level_rank": camera_level_rank,
            "zoom_level": zoom_level,
            "focus_target": focus_target,
            "focus_targets": focus_targets,
            "track_mode": track_mode,
            "cut_type": cut_type,
            "cut_count": cut_count,
            "camera_anchor": camera_anchor,
            "replay_flag": replay_flag,
            "replay_style": replay_style,
            "replay_priority": replay_priority,
            "slow_motion": slow_motion,
            "emphasis_strength": emphasis_strength,
            "overlay_preset": overlay_preset,
            "highlight_priority": highlight_priority,
            "scoreboard_emphasis": scoreboard_emphasis,
            "transition_profile": transition_profile,
            "ui_emphasis": ui_emphasis,
            "shot_outcome": shot_outcome,
            "score_margin": score_margin,
            "is_top_play": camera_level == "top_play",
            "is_clutch": "clutch" in highlight_tags,
            "is_late_game": "late_game" in highlight_tags,
            "has_lead_change": "lead_change" in highlight_tags,
            "has_go_ahead": "go_ahead" in highlight_tags,
            "has_tie_game": "tie_game" in highlight_tags,
            "presentation_event": presentation_event,
        }

    def _apply_camera_level_hint(
        self,
        camera_level: str,
        camera_level_rank: int,
        presentation_type: str,
        camera_style_hint: Optional[str],
        emphasis_level_hint: Optional[str],
        highlight_tier: Optional[str],
        force_tier: Optional[str],
        clip_role: Optional[str],
    ) -> tuple[str, int]:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "normal", 0

        if force_tier == "S" or clip_role == "climax":
            return "top_play", 4

        if camera_style_hint == "cinematic":
            return "top_play", 4
        if camera_style_hint == "replay_focus":
            return "replay", 3
        if camera_style_hint == "highlight_follow":
            return "highlight", 2
        if camera_style_hint == "broadcast":
            return "normal", 0

        if emphasis_level_hint == "max":
            return "top_play", 4
        if emphasis_level_hint == "high":
            if camera_level_rank < 3:
                return "replay", 3
            return camera_level, camera_level_rank
        if emphasis_level_hint == "medium":
            if camera_level_rank < 2:
                return "highlight", 2
            return camera_level, camera_level_rank
        if emphasis_level_hint == "low":
            if camera_level_rank < 1:
                return "light", 1
            return camera_level, camera_level_rank
        if emphasis_level_hint == "none":
            return "normal", 0

        if highlight_tier == "S" and camera_level_rank < 3:
            return "replay", 3
        if highlight_tier == "A" and camera_level_rank < 2:
            return "highlight", 2
        if highlight_tier == "B" and camera_level_rank < 1:
            return "light", 1

        return camera_level, camera_level_rank

    def _apply_zoom_hint(
        self,
        zoom_level: str,
        presentation_type: str,
        camera_style_hint: Optional[str],
        emphasis_level_hint: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "scoreboard"
        if camera_style_hint == "cinematic":
            return "dramatic_close"
        if camera_style_hint == "replay_focus":
            return "close"
        if camera_style_hint == "highlight_follow":
            return "medium"
        if camera_style_hint == "broadcast":
            return "wide"
        if emphasis_level_hint == "max":
            return "dramatic_close"
        if emphasis_level_hint == "high":
            return "close"
        return zoom_level

    def _apply_cut_type_hint(
        self,
        cut_type: str,
        presentation_type: str,
        camera_style_hint: Optional[str],
        emphasis_level_hint: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "hard_cut"
        if camera_style_hint == "cinematic":
            return "hero_cut"
        if camera_style_hint == "replay_focus":
            return "replay_cut"
        if camera_style_hint == "highlight_follow":
            return "impact_cut"
        if emphasis_level_hint == "max":
            return "hero_cut"
        return cut_type

    def _apply_transition_hint(
        self,
        transition_profile: str,
        presentation_type: str,
        camera_style_hint: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "ui_hold"
        if camera_style_hint == "cinematic":
            return "focus_shift"
        if camera_style_hint == "replay_focus":
            return "replay_snap"
        if camera_style_hint == "highlight_follow":
            return "focus_shift"
        if camera_style_hint == "broadcast":
            return "none"
        return transition_profile

    # =========================================================
    # Core rules
    # =========================================================
    def _determine_camera_level(
        self,
        highlight_score: int,
        presentation_type: str,
        importance: str,
        highlight_tags: list[str],
        structure_type: Optional[str],
    ) -> tuple[str, int]:
        forced_normal_types = {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}
        if presentation_type in forced_normal_types:
            return "normal", 0

        adjusted_score = highlight_score

        if presentation_type == "score_make_3":
            adjusted_score += 8
        if presentation_type in {"block", "steal"}:
            adjusted_score += 10
        if presentation_type == "score_make_2" and ("clutch" in highlight_tags or "lead_change" in highlight_tags or "go_ahead" in highlight_tags):
            adjusted_score += 8
        if presentation_type == "score_make_ft" and ("clutch" in highlight_tags or "tie_game" in highlight_tags):
            adjusted_score += 6

        if structure_type in {"spain_pick_and_roll", "fast_break"}:
            adjusted_score += 5
        elif structure_type == "pick_and_roll":
            adjusted_score += 3

        if "clutch" in highlight_tags:
            adjusted_score += 10
        elif "late_game" in highlight_tags:
            adjusted_score += 5

        if "lead_change" in highlight_tags:
            adjusted_score += 10
        if "go_ahead" in highlight_tags:
            adjusted_score += 8
        if "tie_game" in highlight_tags:
            adjusted_score += 6
        if "close_game" in highlight_tags:
            adjusted_score += 3

        if adjusted_score >= 90:
            return "top_play", 4
        if adjusted_score >= 75:
            return "replay", 3
        if adjusted_score >= 60:
            return "highlight", 2
        if adjusted_score >= 45:
            return "light", 1

        if importance == "high" and presentation_type in {"block", "steal", "score_make_3"}:
            return "light", 1

        return "normal", 0

    def _determine_zoom_level(
        self,
        camera_level: str,
        presentation_type: str,
        structure_type: Optional[str],
        highlight_tags: list[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "scoreboard"

        base_zoom_by_level = {
            "normal": "wide",
            "light": "medium_wide",
            "highlight": "medium",
            "replay": "close",
            "top_play": "close",
        }
        zoom = base_zoom_by_level.get(camera_level, "wide")

        if structure_type in {"fast_break", "spain_pick_and_roll"} and camera_level in {"highlight", "replay", "top_play"}:
            return "dynamic_medium"

        if "clutch" in highlight_tags and camera_level in {"replay", "top_play"}:
            return "dramatic_close"

        return zoom

    def _determine_focus_targets(
        self,
        presentation_event: dict,
        presentation_type: str,
        camera_level: str,
    ) -> tuple[str, list[str]]:
        focus_player = self._to_optional_str(presentation_event.get("focus_player_name"))
        support_player = self._to_optional_str(presentation_event.get("support_player_name"))

        special_map = {
            "turnover": [focus_player] if focus_player else ["ball"],
            "steal": [focus_player, support_player],
            "block": [focus_player, support_player],
            "def_rebound": [focus_player] if focus_player else ["ball"],
            "off_rebound_keep": [focus_player] if focus_player else ["ball"],
        }

        if presentation_type in special_map:
            cleaned = self._dedupe_non_empty(special_map[presentation_type])
            if cleaned:
                return cleaned[0], cleaned

        if camera_level == "top_play":
            cleaned = self._dedupe_non_empty([focus_player, support_player, "ball"])
            if cleaned:
                return cleaned[0], cleaned

        if focus_player:
            cleaned = self._dedupe_non_empty([focus_player, support_player])
            return focus_player, cleaned

        if camera_level in {"light", "highlight", "replay", "top_play"}:
            return "ball", ["ball"]

        return "team_shape", ["team_shape"]

    def _determine_track_mode(
        self,
        camera_level: str,
        presentation_type: str,
        structure_type: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "locked"

        if structure_type == "fast_break":
            if camera_level in {"highlight", "replay", "top_play"}:
                return "fast_pan"
            return "follow_ball"

        if camera_level == "top_play":
            if structure_type == "fast_break":
                return "fast_pan"
            return "focus_player_follow"
        if camera_level == "replay":
            return "focus_player_follow"
        if camera_level == "highlight":
            return "follow_ball_to_focus"
        if camera_level == "light":
            return "follow_ball"
        return "broadcast"

    def _determine_cut_type(
        self,
        camera_level: str,
        presentation_type: str,
        structure_type: Optional[str],
        highlight_tags: list[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "hard_cut"

        if camera_level == "top_play":
            return "hero_cut"

        if camera_level == "replay":
            return "replay_cut"

        if camera_level == "highlight":
            if "lead_change" in highlight_tags or "go_ahead" in highlight_tags:
                return "impact_cut"
            return "single_cut"

        if camera_level == "light":
            return "soft_cut"

        return "hold"

    def _determine_cut_count(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> int:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return 1
        if camera_level == "top_play":
            return 1 if "clutch" not in highlight_tags else 2
        if camera_level == "replay":
            return 2
        if camera_level == "highlight":
            return 1
        return 0

    def _determine_replay_flag(self, camera_level: str, presentation_type: str) -> bool:
        if presentation_type in {"quarter_start", "quarter_end", "synthetic_tipoff"}:
            return False
        return camera_level in {"replay", "top_play"}

    def _determine_replay_style(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> Optional[str]:
        if camera_level == "top_play":
            if "clutch" in highlight_tags:
                return "top_play_clutch"
            return "top_play"
        if camera_level == "replay":
            if presentation_type in {"block", "steal"}:
                return "impact_replay"
            return "standard_replay"
        return None

    def _determine_replay_priority(
        self,
        camera_level: str,
        highlight_score: int,
        highlight_tags: list[str],
    ) -> int:
        if camera_level not in {"replay", "top_play"}:
            return 0

        priority = highlight_score
        if "clutch" in highlight_tags:
            priority += 8
        if "lead_change" in highlight_tags:
            priority += 10
        if "go_ahead" in highlight_tags:
            priority += 6
        return min(priority, 120)

    def _determine_slow_motion(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> bool:
        if camera_level == "top_play":
            return presentation_type in {"score_make_2", "score_make_3", "block", "steal"}
        if camera_level == "replay" and presentation_type in {"block", "score_make_3"}:
            return True
        if camera_level == "replay" and "clutch" in highlight_tags:
            return True
        return False

    def _determine_emphasis_strength(self, camera_level: str) -> str:
        mapping = {
            "normal": "none",
            "light": "low",
            "highlight": "medium",
            "replay": "high",
            "top_play": "max",
        }
        return mapping.get(camera_level, "none")

    def _determine_overlay_preset(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> str:
        if presentation_type == "game_end":
            return "final_score"
        if "clutch" in highlight_tags:
            return "clutch"
        if camera_level == "top_play":
            return "top_play"
        if camera_level == "replay":
            return "replay"
        if camera_level == "highlight":
            return "highlight"
        return "standard"

    def _determine_highlight_priority(
        self,
        camera_level: str,
        highlight_score: int,
        highlight_tags: list[str],
        importance: str,
    ) -> str:
        if camera_level == "top_play":
            return "top"
        if camera_level == "replay":
            return "high"
        if camera_level == "highlight":
            return "medium"
        if camera_level == "light":
            return "low"
        if importance == "high" or "close_game" in highlight_tags:
            return "low"
        return "none"

    def _determine_camera_anchor(
        self,
        presentation_type: str,
        structure_type: Optional[str],
        focus_target: str,
        team_side: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "center_court"
        if structure_type == "fast_break":
            return "rim_lane"
        if structure_type in {"pick_and_roll", "spain_pick_and_roll", "handoff"}:
            return "ball_side_halfcourt"
        if structure_type == "post_up":
            return "post_side"
        if focus_target == "ball":
            return "ball_side"
        if team_side in {"home", "away"}:
            return f"{team_side}_offense"
        return "center_play"

    def _determine_scoreboard_emphasis(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> str:
        if presentation_type == "game_end":
            return "full"
        if "lead_change" in highlight_tags or "go_ahead" in highlight_tags or "tie_game" in highlight_tags:
            return "strong"
        if camera_level in {"replay", "top_play"}:
            return "medium"
        return "normal"

    def _determine_transition_profile(
        self,
        camera_level: str,
        presentation_type: str,
        structure_type: Optional[str],
    ) -> str:
        if presentation_type in {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"}:
            return "ui_hold"
        if structure_type == "fast_break":
            return "speed_pan"
        if camera_level == "top_play":
            return "focus_shift"
        if camera_level == "replay":
            return "replay_snap"
        if camera_level == "highlight":
            return "focus_shift"
        if camera_level == "light":
            return "soft_shift"
        return "none"

    def _determine_ui_emphasis(
        self,
        camera_level: str,
        presentation_type: str,
        highlight_tags: list[str],
    ) -> str:
        if presentation_type == "game_end":
            return "final_banner"
        if "clutch" in highlight_tags and camera_level in {"highlight", "replay", "top_play"}:
            return "clutch_banner"
        if camera_level == "top_play":
            return "top_play_banner"
        if camera_level == "replay":
            return "replay_badge"
        if camera_level == "highlight":
            return "highlight_badge"
        return "minimal"

    # =========================================================
    # Helper inference
    # =========================================================
    def _infer_shot_outcome(self, presentation_type: str) -> str:
        if presentation_type in {"score_make_2", "score_make_3", "score_make_ft"}:
            return "made"
        if presentation_type in {"miss_jump_2", "miss_jump_3", "miss_free_throw"}:
            return "missed"
        return "non_shot"

    def _infer_score_margin(self, presentation_event: dict) -> Optional[int]:
        home_score = self._to_optional_int(presentation_event.get("home_score"))
        away_score = self._to_optional_int(presentation_event.get("away_score"))
        if home_score is None or away_score is None:
            return None
        return abs(home_score - away_score)

    def _format_preview_line(self, event: dict) -> str:
        return (
            f"  Play#{event.get('play_no', '-'):<3} | "
            f"Q{event.get('quarter', '-')} {self._format_clock(event.get('clock_seconds'))} | "
            f"{event.get('presentation_type', '-'):<18} | "
            f"lvl={event.get('camera_level', '-'):<9} | "
            f"zoom={event.get('zoom_level', '-'):<14} | "
            f"focus={str(event.get('focus_target', '-') or '-'): <12} | "
            f"cut={event.get('cut_type', '-'):<12} | "
            f"replay={event.get('replay_flag', False)} | "
            f"hl={event.get('highlight_score', 0)}"
        )

    def _format_clock(self, seconds: Optional[int]) -> str:
        if seconds is None:
            return "--:--"
        mm = int(seconds) // 60
        ss = int(seconds) % 60
        return f"{mm:02d}:{ss:02d}"

    def _safe_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                result.append(text)
        return result

    def _dedupe_non_empty(self, values: list[Optional[str]]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            if text not in result:
                result.append(text)
        return result

    def _to_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _to_optional_int(self, value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None

    def _to_optional_str(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


def build_highlight_camera_events(match: Any) -> list[dict]:
    system = HighlightCameraSystem(match)
    return system.build()


def build_highlight_camera_events_from_presentation(presentation_events: list[dict]) -> list[dict]:
    system = HighlightCameraSystem(presentation_events)
    return system.build()
