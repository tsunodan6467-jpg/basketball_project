"""
Presentation Layer for Basketball Project.

Recommended location:
basketball_sim/systems/presentation_layer.py

Purpose
-------
Convert match.play_sequence_log into UI-friendly presentation events.

Design principles
-----------------
- Safe: does NOT modify match simulation logic
- Read-only transform from play_sequence_log
- Easy to extend later for:
    - hotter commentary
    - animation types
    - highlight extraction
    - sound / effects

Safe improvements in this version
---------------------------------
- Adds safe integration with play_structure layer
- Preserves all existing presentation event fields
- Only appends structure metadata when available
- Falls back cleanly if play_structure import/build fails

Current update
--------------
- Steal is now promoted to an independent presentation event
- Live-ball steal is no longer absorbed into turnover presentation
- Defensive events now infer defense team side more safely
- Internal play cache is stabilized for run-expression logic
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

try:
    from basketball_sim.systems.play_structure import PlayStructureLayer
except Exception:  # pragma: no cover - safe fallback for early integration stage
    PlayStructureLayer = None  # type: ignore[assignment]


class PresentationLayer:
    def __init__(self, match: Any) -> None:
        self.match = match
        self.presentation_events: list[dict] = []
        self.presentation_index: int = 0
        self.structure_events: list[dict] = []
        self.structure_by_play_no: dict[int, dict] = {}
        self.play_sequence: list[dict] = []

    # =========================================================
    # Public API
    # =========================================================
    def build(self) -> list[dict]:
        raw_plays = self._get_play_sequence_log()
        self.play_sequence = self._prepare_play_sequence(raw_plays)
        self._build_structure_cache()

        events: list[dict] = []
        for i, play in enumerate(self.play_sequence):
            event = self._build_presentation_event(play_no=i, play=play)
            events.append(event)
            play["presentation_type"] = event.get("presentation_type")

        self.presentation_events = events
        self.presentation_index = 0
        return self.presentation_events

    def get_events(self) -> list[dict]:
        if not self.presentation_events:
            self.build()
        return self.presentation_events

    def get_event_at(self, index: int) -> Optional[dict]:
        events = self.get_events()
        if 0 <= index < len(events):
            return events[index]
        return None

    def get_next_event(self) -> Optional[dict]:
        events = self.get_events()
        if self.presentation_index >= len(events):
            return None
        event = events[self.presentation_index]
        self.presentation_index += 1
        return event

    def peek_next_event(self) -> Optional[dict]:
        events = self.get_events()
        if self.presentation_index >= len(events):
            return None
        return events[self.presentation_index]

    def reset_cursor(self) -> None:
        self.presentation_index = 0

    def get_event_count(self) -> int:
        return len(self.get_events())

    def get_type_counts(self) -> dict[str, int]:
        events = self.get_events()
        counts = Counter(event.get("presentation_type", "unknown") for event in events)
        return dict(counts)

    def print_preview(self, limit: int = 5) -> None:
        events = self.get_events()
        counts = self.get_type_counts()

        print("[PRESENTATION] Preview")
        print(f"[PRESENTATION] total_events={len(events)}")
        print("[PRESENTATION] type_counts")
        for key in sorted(counts.keys()):
            print(f"  - {key:<20}: {counts[key]}")

        print(f"[PRESENTATION] first_{limit}")
        for event in events[:limit]:
            print(
                f"  Play#{event.get('play_no', '-'):<3} | "
                f"Q{event.get('quarter', '-')} {self._format_clock(event.get('clock_seconds'))} | "
                f"{event.get('presentation_type', '-'):<20} | "
                f"{event.get('headline', '-')} | "
                f"structure={event.get('structure_type', '-')}"
                f" | pnr={event.get('pnr_action', '-')}"
                f" | offball={event.get('screen_action', '-')}"
                f" | post={event.get('post_action', '-')}"
                f" | handoff={event.get('handoff_action', '-')}"
                f" | spain={event.get('spain_action', '-')}"
                f" | hl={event.get('highlight_score', 0)}"
                f" | tags={','.join(event.get('highlight_tags', [])) if event.get('highlight_tags') else '-'}"
            )

        print(f"[PRESENTATION] last_{limit}")
        for event in events[-limit:]:
            print(
                f"  Play#{event.get('play_no', '-'):<3} | "
                f"Q{event.get('quarter', '-')} {self._format_clock(event.get('clock_seconds'))} | "
                f"{event.get('presentation_type', '-'):<20} | "
                f"{event.get('headline', '-')} | "
                f"structure={event.get('structure_type', '-')}"
                f" | pnr={event.get('pnr_action', '-')}"
                f" | offball={event.get('screen_action', '-')}"
                f" | post={event.get('post_action', '-')}"
                f" | handoff={event.get('handoff_action', '-')}"
                f" | spain={event.get('spain_action', '-')}"
                f" | hl={event.get('highlight_score', 0)}"
                f" | tags={','.join(event.get('highlight_tags', [])) if event.get('highlight_tags') else '-'}"
            )

    # =========================================================
    # Internal build
    # =========================================================
    def _get_play_sequence_log(self) -> list[dict]:
        if hasattr(self.match, "get_play_sequence_log"):
            plays = self.match.get_play_sequence_log()
            if plays is not None:
                return plays
        return list(getattr(self.match, "play_sequence_log", []) or [])

    def _prepare_play_sequence(self, plays: list[dict]) -> list[dict]:
        prepared: list[dict] = []
        for index, play in enumerate(plays):
            if not isinstance(play, dict):
                continue
            copied_play = dict(play)
            copied_play["_presentation_index"] = index
            result_type = str(copied_play.get("result_type", "unknown"))
            copied_play["presentation_type"] = self._resolve_presentation_type(copied_play, result_type)
            prepared.append(copied_play)
        return prepared

    def _build_structure_cache(self) -> None:
        self.structure_events = []
        self.structure_by_play_no = {}

        if PlayStructureLayer is None:
            return

        try:
            layer = PlayStructureLayer(self.match)
            structure_events = layer.build()
        except Exception:
            return

        if not isinstance(structure_events, list):
            return

        normalized_events: list[dict] = []
        structure_by_play_no: dict[int, dict] = {}

        for index, event in enumerate(structure_events):
            if not isinstance(event, dict):
                continue
            play_index = event.get("play_index")
            if not isinstance(play_index, int):
                play_index = index
            normalized_events.append(event)
            structure_by_play_no[play_index] = event

        self.structure_events = normalized_events
        self.structure_by_play_no = structure_by_play_no

    def _build_presentation_event(self, play_no: int, play: dict) -> dict:
        result_type = str(play.get("result_type", "unknown"))
        presentation_type = self._resolve_presentation_type(play, result_type)

        quarter = play.get("quarter")
        clock_seconds = self._extract_clock(play)
        home_score = play.get("home_score")
        away_score = play.get("away_score")

        focus_player = self._pick_focus_player(play, presentation_type, result_type)
        support_player = self._pick_support_player(play, presentation_type, result_type)
        team_side = self._infer_team_side(play, presentation_type)
        importance = self._infer_importance(presentation_type)

        structure_event = self.structure_by_play_no.get(play_no, {})

        headline = self._build_headline(play, presentation_type, structure_event)
        main_text = self._build_main_text(play, presentation_type, structure_event)
        sub_text = self._build_sub_text(play, presentation_type, structure_event)

        merged_team_side = structure_event.get("offense_team_side") or team_side
        if presentation_type in {"steal", "block", "def_rebound"}:
            defense_side = structure_event.get("defense_team_side")
            if defense_side in {"home", "away"}:
                merged_team_side = defense_side
        merged_focus_player = structure_event.get("focus_player_name") or focus_player
        merged_support_player = structure_event.get("support_player_name") or support_player

        if presentation_type == "steal":
            merged_focus_player = focus_player
            merged_support_player = support_player
        elif presentation_type == "block":
            merged_focus_player = focus_player
            merged_support_player = support_player
        elif presentation_type == "def_rebound":
            merged_focus_player = focus_player

        highlight_score, highlight_tags = self._build_highlight_data(
            play=play,
            presentation_type=presentation_type,
            structure_event=structure_event,
            team_side=merged_team_side,
        )

        return {
            "play_no": play_no,
            "quarter": quarter,
            "clock_seconds": clock_seconds,
            "home_score": home_score,
            "away_score": away_score,
            "presentation_type": presentation_type,
            "source_result_type": result_type,
            "headline": headline,
            "main_text": main_text,
            "sub_text": sub_text,
            "focus_player_name": merged_focus_player,
            "support_player_name": merged_support_player,
            "team_side": merged_team_side,
            "importance": importance,
            "highlight_score": highlight_score,
            "highlight_tags": highlight_tags,
            "raw_play": play,
            "structure_type": structure_event.get("structure_type"),
            "offense_team_side": structure_event.get("offense_team_side"),
            "defense_team_side": structure_event.get("defense_team_side"),
            "offense_direction": structure_event.get("offense_direction"),
            "formation_name": structure_event.get("formation_name"),
            "spacing_profile": structure_event.get("spacing_profile"),
            "tempo_profile": structure_event.get("tempo_profile"),
            "transition_action": play.get("transition_action") or structure_event.get("transition_action"),
            "transition_trigger_type": play.get("transition_trigger_type") or structure_event.get("transition_trigger_type"),
            "ball_handler_name": structure_event.get("ball_handler_name"),
            "pnr_action": structure_event.get("pnr_action"),
            "screener_name": structure_event.get("screener_name"),
            "roller_name": structure_event.get("roller_name"),
            "kickout_target_name": structure_event.get("kickout_target_name"),
            "screen_side": structure_event.get("screen_side"),
            "drive_lane": structure_event.get("drive_lane"),
            "screen_action": structure_event.get("screen_action"),
            "target_name": structure_event.get("target_name"),
            "cut_lane": structure_event.get("cut_lane"),
            "post_action": structure_event.get("post_action"),
            "post_player_name": structure_event.get("post_player_name"),
            "entry_passer_name": structure_event.get("entry_passer_name"),
            "post_kickout_target_name": structure_event.get("kickout_target_name"),
            "post_side": structure_event.get("post_side"),
            "post_depth": structure_event.get("post_depth"),
            "handoff_action": structure_event.get("handoff_action"),
            "handoff_giver_name": structure_event.get("handoff_giver_name"),
            "handoff_receiver_name": structure_event.get("handoff_receiver_name"),
            "handoff_side": structure_event.get("handoff_side"),
            "spain_action": structure_event.get("spain_action"),
            "back_screener_name": structure_event.get("back_screener_name"),
            "back_screen_target_name": structure_event.get("back_screen_target_name"),
            "spain_kickout_target_name": structure_event.get("spain_kickout_target_name"),
            "lane_map": self._safe_copy_lane_map(structure_event.get("lane_map")),
            "structure_raw": structure_event if isinstance(structure_event, dict) else None,
        }

    def _safe_copy_lane_map(self, lane_map: Any) -> dict:
        if not isinstance(lane_map, dict):
            return {}
        safe_map: dict[str, str] = {}
        for key, value in lane_map.items():
            if isinstance(key, str) and isinstance(value, str):
                safe_map[key] = value
        return safe_map

    def _build_highlight_data(
        self,
        play: dict,
        presentation_type: str,
        structure_event: dict,
        team_side: Optional[str],
    ) -> tuple[int, list[str]]:
        score = 0
        tags: list[str] = []

        base_scores = {
            "score_make_3": 30,
            "score_make_2": 18,
            "score_make_ft": 8,
            "block": 24,
            "steal": 18,
            "turnover": 14,
            "off_rebound_keep": 10,
            "quarter_end": 6,
            "game_end": 8,
        }
        score += base_scores.get(presentation_type, 0)
        if presentation_type in base_scores:
            tags.append(presentation_type)

        structure_type = structure_event.get("structure_type")
        structure_bonus = {
            "spain_pick_and_roll": 12,
            "pick_and_roll": 7,
            "handoff": 6,
            "off_ball_screen": 7,
            "post_up": 6,
            "fast_break": 9,
            "isolation": 8,
        }
        if structure_type in structure_bonus:
            score += structure_bonus[structure_type]
            tags.append(str(structure_type))

        transition_action = play.get("transition_action") or structure_event.get("transition_action")
        if transition_action == "primary_break":
            score += 8
            tags.append("primary_break")
        elif transition_action == "counter":
            score += 12
            tags.append("counter")

        if self._is_alley_oop_candidate(play, presentation_type, structure_event):
            score += 16
            tags.append("alley_oop")
            tags.append("dunk")
        elif play.get("finish_type") == "dunk" or (presentation_type == "score_make_2" and self._is_dunk_candidate(play, presentation_type, structure_event)):
            score += 12
            tags.append("dunk")
        elif self._is_pullup_three_candidate(play, presentation_type, structure_event):
            score += 11
            tags.append("pullup_3")

        action_value = (
            structure_event.get("spain_action")
            or structure_event.get("pnr_action")
            or structure_event.get("screen_action")
            or structure_event.get("post_action")
            or structure_event.get("handoff_action")
        )
        action_bonus = {
            "catch_shoot": 6,
            "cut": 6,
            "roll": 7,
            "dive": 9,
            "pop": 9,
            "kickout": 8,
            "pullup": 7,
            "drive": 6,
            "back_down": 5,
            "seal": 4,
            "receive": 4,
        }
        if action_value in action_bonus:
            score += action_bonus[action_value]
            tags.append(str(action_value))

        quarter = play.get("quarter")
        clock_seconds = self._extract_clock(play)
        home_score = play.get("home_score")
        away_score = play.get("away_score")

        if isinstance(quarter, int) and quarter >= 4 and isinstance(clock_seconds, int):
            if clock_seconds <= 60:
                score += 15
                tags.append("clutch")
            elif clock_seconds <= 120:
                score += 8
                tags.append("late_game")

        non_score_state_types = {"quarter_start", "quarter_end", "game_end"}

        if (
            presentation_type not in non_score_state_types
            and isinstance(home_score, int)
            and isinstance(away_score, int)
        ):
            diff_after = abs(home_score - away_score)
            if diff_after <= 5:
                score += 10
                tags.append("close_game")

            points = self._get_points_from_result_type(play.get("result_type"))
            if team_side in {"home", "away"} and points > 0:
                before_home = home_score - points if team_side == "home" else home_score
                before_away = away_score - points if team_side == "away" else away_score
                before_diff = before_home - before_away
                after_diff = home_score - away_score

                if before_diff == 0 and after_diff != 0:
                    score += 14
                    tags.append("go_ahead")
                elif before_diff * after_diff < 0:
                    score += 18
                    tags.append("lead_change")
                elif after_diff == 0:
                    score += 12
                    tags.append("tie_game")

        score = max(0, min(100, score))
        ordered_tags: list[str] = []
        for tag in tags:
            if tag not in ordered_tags:
                ordered_tags.append(tag)

        return score, ordered_tags

    def _get_points_from_result_type(self, result_type: Any) -> int:
        result = str(result_type or "")
        if result == "made_3":
            return 3
        if result == "made_2":
            return 2
        if result == "made_ft":
            return 1
        return 0

    # =========================================================
    # Mapping rules
    # =========================================================
    def _resolve_presentation_type(self, play: dict, result_type: str) -> str:
        has_stealer = self._none_if_dash(
            play.get("stealer_name") or play.get("secondary_player_name")
        )
        turnover_player = self._none_if_dash(
            play.get("turnover_player_name") or play.get("primary_player_name")
        )

        live_ball_steal_result_types = {"turnover", "steal"}

        if result_type in live_ball_steal_result_types and has_stealer and turnover_player:
            return "steal"

        return self._map_presentation_type(result_type)

    def _map_presentation_type(self, result_type: str) -> str:
        mapping = {
            "made_2": "score_make_2",
            "made_3": "score_make_3",
            "made_ft": "score_make_ft",
            "miss_2_def_rebound": "miss_jump_2",
            "miss_3_def_rebound": "miss_jump_3",
            "miss_ft_def_rebound": "miss_free_throw",
            "miss_ft": "miss_free_throw",
            "def_rebound": "def_rebound",
            "miss_2_off_rebound_continue": "off_rebound_keep",
            "miss_3_off_rebound_continue": "off_rebound_keep",
            "off_rebound": "off_rebound_keep",
            "turnover": "turnover",
            "steal": "steal",
            "block_def_rebound": "block",
            "quarter_start": "quarter_start",
            "quarter_end": "quarter_end",
            "game_end": "game_end",
        }
        return mapping.get(result_type, "play_event")

    def _infer_importance(self, presentation_type: str) -> str:
        if presentation_type in {"game_end", "block", "steal", "score_make_3"}:
            return "high"
        if presentation_type in {
            "score_make_2",
            "score_make_ft",
            "turnover",
            "quarter_end",
            "quarter_start",
            "def_rebound",
            "miss_free_throw",
        }:
            return "normal"
        return "low"

    # =========================================================
    # Text building
    # =========================================================
    def _stable_variant(self, play: dict, key: str, choices: list[str]) -> str:
        if not choices:
            return ""
        play_no = play.get("play_no")
        if not isinstance(play_no, int):
            play_no = play.get("play_no", 0) or 0
        seed_text = f"{play_no}:{key}:{play.get('quarter')}:{play.get('clock_seconds')}"
        seed = sum(ord(ch) for ch in seed_text)
        return choices[seed % len(choices)]

    def _score_text(self, play: dict) -> str:
        home_score = play.get("home_score")
        away_score = play.get("away_score")
        if home_score is None or away_score is None:
            return ""
        return f"スコアは{home_score}-{away_score}。"

    def _clock_text(self, play: dict) -> str:
        quarter = play.get("quarter")
        clock_seconds = self._extract_clock(play)
        if quarter is None or clock_seconds is None:
            return ""
        return f"Q{quarter} {self._format_clock(clock_seconds)}"

    def _lead_context_text(self, play: dict) -> str:
        home_score = play.get("home_score")
        away_score = play.get("away_score")
        team_side = self._infer_team_side(play, "play_event")
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            return ""
        diff = home_score - away_score
        if diff == 0:
            return "これで同点です。"
        if team_side == "home":
            if diff > 0:
                return f"ホームが{diff}点リード。"
            return f"ホームは{abs(diff)}点ビハインド。"
        if team_side == "away":
            if diff < 0:
                return f"アウェーが{abs(diff)}点リード。"
            return f"アウェーは{diff}点ビハインド。"
        return ""

    def _score_diff(self, play: dict) -> Optional[int]:
        home_score = play.get("home_score")
        away_score = play.get("away_score")
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            return None
        return abs(home_score - away_score)

    def _is_close_game(self, play: dict) -> bool:
        diff = self._score_diff(play)
        return isinstance(diff, int) and diff <= 5

    def _is_clutch_moment(self, play: dict) -> bool:
        quarter = play.get("quarter")
        clock_seconds = self._extract_clock(play)
        if not isinstance(quarter, int) or clock_seconds is None:
            return False
        if quarter >= 5:
            return True
        return quarter >= 4 and clock_seconds <= 180

    def _clutch_phrase(self, play: dict, key: str, choices: list[str]) -> str:
        if not self._is_clutch_moment(play):
            return ""
        return self._stable_variant(play, key, choices)

    def _flow_phrase(self, play: dict, key: str, choices: list[str]) -> str:
        if not self._is_close_game(play):
            return ""
        return self._stable_variant(play, key, choices)

    def _score_state_flags(self, play: dict) -> dict[str, bool]:
        home_score = play.get("home_score")
        away_score = play.get("away_score")
        prev_home_score = play.get("prev_home_score")
        prev_away_score = play.get("prev_away_score")

        if not all(isinstance(v, int) for v in [home_score, away_score, prev_home_score, prev_away_score]):
            return {
                "tie_now": False,
                "tie_before": False,
                "lead_change": False,
                "go_ahead": False,
                "double_digit_lead": False,
                "run_push": False,
            }

        diff_now = home_score - away_score
        diff_before = prev_home_score - prev_away_score

        return {
            "tie_now": diff_now == 0,
            "tie_before": diff_before == 0,
            "lead_change": (diff_now > 0 and diff_before < 0) or (diff_now < 0 and diff_before > 0),
            "go_ahead": diff_now != 0 and diff_before == 0,
            "double_digit_lead": abs(diff_now) >= 10,
            "run_push": abs(diff_now) >= 8 and abs(diff_now) > abs(diff_before),
        }

    def _swing_phrase(self, play: dict, key: str) -> str:
        flags = self._score_state_flags(play)
        if flags["lead_change"]:
            return self._stable_variant(
                play,
                key + "_lead_change",
                [
                    "ここでリードが入れ替わります。",
                    "ついに試合をひっくり返しました。",
                    "ここで主導権を奪い返しました。",
                ],
            )
        if flags["go_ahead"]:
            return self._stable_variant(
                play,
                key + "_go_ahead",
                [
                    "ここで勝ち越しです。",
                    "この得点で前に出ます。",
                    "大きな勝ち越し点になりました。",
                ],
            )
        if flags["tie_now"]:
            return self._stable_variant(
                play,
                key + "_tie",
                [
                    "これで同点です。",
                    "スコアが並びました。",
                    "振り出しに戻しました。",
                ],
            )
        if flags["double_digit_lead"]:
            return self._stable_variant(
                play,
                key + "_double_digit",
                [
                    "リードは二桁に広がりました。",
                    "点差を大きく広げます。",
                    "試合の流れを引き寄せています。",
                ],
            )
        if flags["run_push"]:
            return self._stable_variant(
                play,
                key + "_run_push",
                [
                    "流れをつかんでいます。",
                    "いい時間帯を作っています。",
                    "ここで一気に押し込みます。",
                ],
            )
        return ""

    def _recent_same_team_points(self, play: dict) -> int:
        current_idx = play.get("_presentation_index")
        if not isinstance(current_idx, int) or current_idx < 0:
            return 0

        current_team = self._infer_team_side(play, "play_event")
        if current_team not in {"home", "away"}:
            return 0

        total = 0
        idx = current_idx
        while idx >= 0:
            prev_play = self.play_sequence[idx] if 0 <= idx < len(self.play_sequence) else None
            if not isinstance(prev_play, dict):
                break

            ptype = str(prev_play.get("presentation_type") or "")
            if ptype not in {"score_make_2", "score_make_3", "score_make_ft"}:
                idx -= 1
                continue

            prev_team = self._infer_team_side(prev_play, "play_event")
            if prev_team != current_team:
                break

            if ptype == "score_make_2":
                total += 2
            elif ptype == "score_make_3":
                total += 3
            elif ptype == "score_make_ft":
                total += 1
            idx -= 1

        return total

    def _run_phrase(self, play: dict, key: str) -> str:
        run_points = self._recent_same_team_points(play)
        if run_points >= 10:
            return self._stable_variant(
                play,
                key + "_run_10",
                [
                    "この時間帯は完全に押し込んでいます。",
                    "一気に流れを引き寄せました。",
                    "相手を突き放しにかかっています。",
                ],
            )
        if run_points >= 6:
            return self._stable_variant(
                play,
                key + "_run_6",
                [
                    "連続得点で流れをつかみます。",
                    "いい形で加点が続いています。",
                    "この数分で主導権を握りました。",
                ],
            )
        return ""

    def _is_dunk_candidate(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> bool:
        if presentation_type != "score_make_2":
            return False

        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")
        post_action = structure_event.get("post_action")
        screen_action = structure_event.get("screen_action")
        transition_action = play.get("transition_action") or structure_event.get("transition_action")
        finish_type = play.get("finish_type") or structure_event.get("finish_type")

        inside_context = False
        if structure_type == "fast_break" or transition_action in {"primary_break", "counter"}:
            inside_context = True
        if structure_type == "pick_and_roll" and pnr_action == "dive":
            inside_context = True
        if structure_type == "post_up" or post_action in {"seal", "back_down", "spin", "drop_step"}:
            inside_context = True
        if structure_type == "off_ball_screen" and screen_action == "cut":
            inside_context = True
        if play.get("is_second_chance") or play.get("second_chance"):
            inside_context = True

        # 安全側に倒す: 明確なリング周辺文脈がないハーフコート2Pは、
        # raw側に finish_type=dunk があってもダンク演出へ昇格させない。
        if not inside_context:
            return False

        scorer_pos = str(play.get("scorer_position") or play.get("primary_player_position") or "").upper()
        scorer_height = int(play.get("scorer_height_cm") or play.get("primary_player_height_cm") or 0)
        scorer_drive = int(play.get("scorer_drive") or play.get("primary_player_drive") or 0)
        scorer_rebound = int(play.get("scorer_rebound") or play.get("primary_player_rebound") or 0)
        scorer_ovr = int(play.get("scorer_ovr") or play.get("primary_player_ovr") or 0)
        archetype_text = str(play.get("scorer_archetype") or play.get("primary_player_archetype") or "").lower()

        score = 0

        if finish_type == "dunk":
            score += 4

        if scorer_pos in {"C", "PF"}:
            score += 4
        elif scorer_pos == "SF":
            score += 1

        if scorer_height >= 205:
            score += 4
        elif scorer_height >= 200:
            score += 3
        elif scorer_height >= 198:
            score += 2

        if scorer_drive >= 80:
            score += 2
        elif scorer_drive >= 74:
            score += 1
        if scorer_rebound >= 76:
            score += 2
        elif scorer_rebound >= 70:
            score += 1
        if scorer_ovr >= 80:
            score += 1

        if any(key in archetype_text for key in ["slasher", "rebound", "rim", "big", "athletic", "dunker"]):
            score += 2

        if pnr_action == "dive":
            score += 3
        if structure_type == "fast_break" or transition_action in {"primary_break", "counter"}:
            score += 2
        if structure_type == "post_up" or post_action in {"seal", "back_down", "spin", "drop_step"}:
            score += 3
        if structure_type == "off_ball_screen" and screen_action == "cut":
            score += 3
        if play.get("is_second_chance") or play.get("second_chance"):
            score += 2
        if play.get("assister_name") or play.get("secondary_player_name"):
            score += 1

        return score >= 12


    def _is_alley_oop_candidate(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> bool:
        if presentation_type != "score_make_2":
            return False

        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")
        screen_action = structure_event.get("screen_action")
        transition_action = play.get("transition_action") or structure_event.get("transition_action")

        support_name = (
            structure_event.get("support_player_name")
            or play.get("assister_name")
            or play.get("secondary_player_name")
        )
        if not support_name or str(support_name).strip() in {"", "-"}:
            return False

        scorer_pos = str(play.get("scorer_position") or play.get("primary_player_position") or "").upper()
        scorer_height = int(play.get("scorer_height_cm") or play.get("primary_player_height_cm") or 0)
        scorer_drive = int(play.get("scorer_drive") or play.get("primary_player_drive") or 0)
        scorer_rebound = int(play.get("scorer_rebound") or play.get("primary_player_rebound") or 0)
        archetype_text = str(play.get("scorer_archetype") or play.get("primary_player_archetype") or "").lower()

        score = 0
        if structure_type == "pick_and_roll" and pnr_action == "dive":
            score += 5
        if structure_type == "fast_break" or transition_action in {"primary_break", "counter"}:
            score += 4
        if structure_type == "off_ball_screen" and screen_action == "cut":
            score += 4

        if scorer_pos in {"C", "PF"}:
            score += 3
        elif scorer_pos == "SF":
            score += 2

        if scorer_height >= 202:
            score += 3
        elif scorer_height >= 196:
            score += 2

        if scorer_drive >= 70:
            score += 2
        if scorer_rebound >= 68:
            score += 1

        if any(key in archetype_text for key in ["slasher", "rim", "rebound", "big", "wing", "athletic", "dunker"]):
            score += 1

        return score >= 8

    def _is_pullup_three_candidate(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> bool:
        if presentation_type not in {"score_make_3", "miss_jump_3"}:
            return False

        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")
        screen_action = structure_event.get("screen_action")
        transition_action = play.get("transition_action") or structure_event.get("transition_action")

        if transition_action in {"primary_break", "counter"} or structure_type == "fast_break":
            return False
        if structure_type == "pick_and_roll" and pnr_action == "pop":
            return False
        if structure_type == "off_ball_screen" and screen_action in {"catch", "catch_shoot"}:
            return False

        scorer_pos = str(play.get("scorer_position") or play.get("primary_player_position") or "").upper()
        scorer_drive = int(play.get("scorer_drive") or play.get("primary_player_drive") or 0)
        scorer_ovr = int(play.get("scorer_ovr") or play.get("primary_player_ovr") or 0)
        archetype_text = str(play.get("scorer_archetype") or play.get("primary_player_archetype") or "").lower()
        assister_name = self._name(play.get("assister_name") or play.get("secondary_player_name"))

        score = 0
        if structure_type == "isolation":
            score += 5
        if structure_type == "pick_and_roll" and pnr_action == "pullup":
            score += 6
        if scorer_pos in {"PG", "SG"}:
            score += 3
        elif scorer_pos == "SF":
            score += 2
        if scorer_drive >= 76:
            score += 2
        elif scorer_drive >= 70:
            score += 1
        if scorer_ovr >= 78:
            score += 1
        if any(key in archetype_text for key in ["shot_creator", "scoring_guard", "playmaker", "slasher", "two_way_wing"]):
            score += 2
        if assister_name != "-":
            score -= 2
        return score >= 6

    def _build_headline(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> str:
        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")
        transition_action = play.get("transition_action") or structure_event.get("transition_action")

        if transition_action == "counter":
            if presentation_type == "score_make_2":
                return "カウンター速攻成功"
            if presentation_type == "score_make_3":
                return "カウンター速攻3成功"
            if presentation_type == "score_make_ft":
                return "カウンターでフリースロー獲得"
            if presentation_type == "miss_jump_2":
                return "カウンター速攻失敗"
            if presentation_type == "miss_jump_3":
                return "カウンター速攻3失敗"
        elif transition_action == "primary_break" or structure_type == "fast_break":
            if presentation_type == "score_make_2":
                return "速攻成功"
            if presentation_type == "score_make_3":
                return "速攻3成功"
            if presentation_type == "score_make_ft":
                return "速攻でフリースロー獲得"
            if presentation_type == "miss_jump_2":
                return "速攻失敗"
            if presentation_type == "miss_jump_3":
                return "速攻3失敗"

        if self._is_alley_oop_candidate(play, presentation_type, structure_event):
            return "アリウープ成功"

        if self._is_dunk_candidate(play, presentation_type, structure_event):
            return "ダンク成功"

        if self._is_pullup_three_candidate(play, presentation_type, structure_event):
            if presentation_type == "score_make_3":
                return "プルアップ3成功"
            if presentation_type == "miss_jump_3":
                return "プルアップ3失敗"

        if structure_type == "pick_and_roll" and pnr_action == "dive":
            if presentation_type == "score_make_2":
                return "PnRダイブ成功"
            if presentation_type == "miss_jump_2":
                return "PnRダイブ失敗"

        if structure_type == "pick_and_roll" and pnr_action == "pop":
            if presentation_type == "score_make_3":
                return "ピックアンドポップ3成功"
            if presentation_type == "miss_jump_3":
                return "ピックアンドポップ3失敗"

        if structure_type == "isolation":
            if presentation_type == "score_make_2":
                return "アイソ1on1成功"
            if presentation_type == "score_make_3":
                return "アイソから3ポイント成功"
            if presentation_type == "miss_jump_2":
                return "アイソ1on1失敗"
            if presentation_type == "miss_jump_3":
                return "アイソ3ポイント失敗"

        if presentation_type == "score_make_2":
            return "2ポイント成功"
        if presentation_type == "score_make_3":
            return "3ポイント成功"
        if presentation_type == "score_make_ft":
            return "フリースロー成功"
        if presentation_type == "miss_jump_2":
            return "2ポイント失敗"
        if presentation_type == "miss_jump_3":
            return "3ポイント失敗"
        if presentation_type == "miss_free_throw":
            return "フリースロー失敗"
        if presentation_type == "def_rebound":
            return "ディフェンスリバウンド"
        if presentation_type == "off_rebound_keep":
            return "オフェンスリバウンド"
        if presentation_type == "turnover":
            return "ターンオーバー"
        if presentation_type == "steal":
            return "スティール"
        if presentation_type == "block":
            return "ブロック"
        if presentation_type == "quarter_start":
            q = play.get("quarter", "-")
            return f"第{q}クォーター開始"
        if presentation_type == "quarter_end":
            q = play.get("quarter", "-")
            return f"第{q}クォーター終了"
        if presentation_type == "game_end":
            return "試合終了"
        return str(play.get("result_type", "play"))

    def _build_main_text(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> str:
        scorer = self._name(play.get("scorer_name") or play.get("primary_player_name"))
        assister = self._name(play.get("assister_name") or play.get("secondary_player_name"))
        final_shooter = self._name(play.get("final_shooter_name") or play.get("primary_player_name"))
        def_rebounder = self._name(
            play.get("def_rebounder_name")
            or play.get("rebounder_name")
            or play.get("primary_player_name")
            or play.get("secondary_player_name")
        )
        off_rebounder = self._name(
            play.get("off_rebounder_name")
            or play.get("rebounder_name")
            or play.get("primary_player_name")
            or play.get("secondary_player_name")
        )
        turnover_player = self._name(play.get("turnover_player_name") or play.get("primary_player_name"))
        stealer = self._name(play.get("stealer_name") or play.get("secondary_player_name"))
        blocker = self._name(play.get("blocker_name") or play.get("secondary_player_name"))
        blocked_player = self._name(play.get("blocked_player_name") or play.get("primary_player_name"))

        close_phrase = self._flow_phrase(
            play,
            "close_game_phrase",
            [
                "接戦が続きます。",
                "一進一退の展開です。",
                "まだ流れはどちらにも転びます。",
            ],
        )
        clutch_phrase = self._clutch_phrase(
            play,
            "clutch_phrase",
            [
                "終盤の大きなプレーです。",
                "ここで会場がざわつきます。",
                "勝負どころで決めてきました。",
            ],
        )

        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")
        transition_action = play.get("transition_action") or structure_event.get("transition_action")

        if transition_action == "counter" and presentation_type == "score_make_2":
            tail = self._stable_variant(
                play,
                "counter_make_2",
                [
                    "奪ってから一気に走り切りました。",
                    "守備が戻る前にそのまま決め切りました。",
                    "カウンターから一気にリングまで持ち込みました。",
                ],
            )
            extra = clutch_phrase or close_phrase
            return f"{scorer}がカウンター速攻を仕上げました。{tail} {extra}".strip()

        if transition_action == "counter" and presentation_type == "score_make_3":
            tail = self._stable_variant(
                play,
                "counter_make_3",
                [
                    "奪ってから外までつないで沈めました。",
                    "カウンターから一気に3ポイントを突き刺しました。",
                    "守備が整う前に外角まで展開して決めました。",
                ],
            )
            extra = clutch_phrase or close_phrase
            return f"{scorer}がカウンターから3ポイントを決めました。{tail} {extra}".strip()

        if transition_action == "counter" and presentation_type == "score_make_ft":
            extra = clutch_phrase or close_phrase
            return f"{scorer}がカウンターからファウルを誘い、フリースローで加点しました。 {extra}".strip()

        if (transition_action == "primary_break" or structure_type == "fast_break") and presentation_type == "score_make_2":
            tail = self._stable_variant(
                play,
                "fastbreak_make_2",
                [
                    "一気に走り切って2点を奪いました。",
                    "トランジションからそのままリングまで持ち込みました。",
                    "速攻の流れを最後までやり切りました。",
                ],
            )
            extra = clutch_phrase or close_phrase
            return f"{scorer}が速攻を決めました。{tail} {extra}".strip()

        if (transition_action == "primary_break" or structure_type == "fast_break") and presentation_type == "score_make_3":
            tail = self._stable_variant(
                play,
                "fastbreak_make_3",
                [
                    "走りながら外までつないで3ポイントです。",
                    "トランジションから外角まで展開して決めました。",
                    "速攻の流れからそのまま3ポイントを沈めました。",
                ],
            )
            extra = clutch_phrase or close_phrase
            return f"{scorer}が速攻から3ポイントを決めました。{tail} {extra}".strip()

        if (transition_action == "primary_break" or structure_type == "fast_break") and presentation_type == "score_make_ft":
            extra = clutch_phrase or close_phrase
            return f"{scorer}が速攻の流れからファウルを受け、フリースローで加点しました。 {extra}".strip()

        if structure_type == "isolation" and presentation_type == "score_make_2":
            swing_phrase = self._swing_phrase(play, "iso_make_2")
            run_phrase = self._run_phrase(play, "iso_make_2")
            tail = self._stable_variant(
                play,
                "iso_make_2",
                [
                    "1対1を制してリングまで持ち込みました。",
                    "ディフェンスを外してそのまま決め切りました。",
                    "アイソレーションから個で打開しました。",
                    "自ら仕掛けて2点をねじ込みました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}がアイソレーションから2ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if structure_type == "isolation" and presentation_type == "score_make_3":
            swing_phrase = self._swing_phrase(play, "iso_make_3")
            run_phrase = self._run_phrase(play, "iso_make_3")
            tail = self._stable_variant(
                play,
                "iso_make_3",
                [
                    "自分でズレを作って外角を沈めました。",
                    "アイソレーションからそのまま打ち切りました。",
                    "1対1からプルアップで決めました。",
                    "個人技で3点をもぎ取ります。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}がアイソレーションから3ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if structure_type == "isolation" and presentation_type == "miss_jump_2":
            if def_rebounder != "-":
                tail = self._stable_variant(
                    play,
                    "iso_miss_2",
                    [
                        "1対1から仕掛けましたが決め切れません。",
                        "個人技で崩しに行きましたが外れました。",
                        "アイソレーションからのフィニッシュは決まりません。",
                    ],
                )
                extra = close_phrase if close_phrase else ""
                return f"{final_shooter}のアイソレーションは決まりません。{def_rebounder}がディフェンスリバウンド。{tail}{(' ' + extra) if extra else ''}"
            return f"{final_shooter}のアイソレーションは決まりません。"

        if structure_type == "isolation" and presentation_type == "miss_jump_3":
            if def_rebounder != "-":
                tail = self._stable_variant(
                    play,
                    "iso_miss_3",
                    [
                        "1対1からのプルアップは外れました。",
                        "アイソレーションから打ちましたが決まりません。",
                        "個人技から3点を狙いましたが外れました。",
                    ],
                )
                extra = close_phrase if close_phrase else ""
                return f"{final_shooter}のアイソレーション3は外れました。{def_rebounder}がディフェンスリバウンド。{tail}{(' ' + extra) if extra else ''}"
            return f"{final_shooter}のアイソレーション3は外れました。"

        if structure_type == "pick_and_roll" and pnr_action == "dive" and presentation_type == "score_make_2":
            swing_phrase = self._swing_phrase(play, "pnr_dive_make_2")
            run_phrase = self._run_phrase(play, "pnr_dive_make_2")
            tail = self._stable_variant(
                play,
                "pnr_dive_make_2",
                [
                    "PnRから一気にダイブして決めました。",
                    "スクリーン後に鋭くリングへ飛び込みました。",
                    "ロールではなくダイブの速さでフィニッシュです。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}がPnRからダイブして2ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if structure_type == "pick_and_roll" and pnr_action == "pop" and presentation_type == "score_make_3":
            swing_phrase = self._swing_phrase(play, "pnr_pop_make_3")
            run_phrase = self._run_phrase(play, "pnr_pop_make_3")
            tail = self._stable_variant(
                play,
                "pnr_pop_make_3",
                [
                    "スクリーン後に外へ開いて3ポイントを沈めました。",
                    "ピックアンドポップから見事に外角を決めます。",
                    "ビッグが外へ開いて仕留めました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}がピックアンドポップから3ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if self._is_pullup_three_candidate(play, presentation_type, structure_event) and presentation_type == "score_make_3":
            swing_phrase = self._swing_phrase(play, "pullup_3_make")
            run_phrase = self._run_phrase(play, "pullup_3_make")
            tail = self._stable_variant(
                play,
                "pullup_3_make",
                [
                    "ドリブルからリズム良く引き上げて沈めました。",
                    "自ら間合いを作ってプルアップを決め切りました。",
                    "1歩のズレを作ってそのまま打ち抜きました。",
                    "止まり際のプルアップがきれいに決まりました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}がプルアップ3を成功。{tail}{(' ' + extra) if extra else ''}"

        if self._is_pullup_three_candidate(play, presentation_type, structure_event) and presentation_type == "miss_jump_3":
            if def_rebounder != "-":
                tail = self._stable_variant(
                    play,
                    "pullup_3_miss",
                    [
                        "ドリブルからのプルアップを狙いましたが外れました。",
                        "間合いを作って打ちましたが決まりません。",
                        "プルアップ3は惜しくもリングに嫌われました。",
                    ],
                )
                extra = close_phrase if close_phrase else ""
                return f"{final_shooter}のプルアップ3は外れました。{def_rebounder}がディフェンスリバウンド。{tail}{(' ' + extra) if extra else ''}"
            return f"{final_shooter}のプルアップ3は外れました。"

        if presentation_type == "score_make_2":
            if self._is_alley_oop_candidate(play, presentation_type, structure_event):
                swing_phrase = self._swing_phrase(play, "score_make_2")
                run_phrase = self._run_phrase(play, "score_make_2")
                tail = self._stable_variant(
                    play,
                    "score_make_2_alley_oop",
                    [
                        "高いロブパスに飛び込んで叩き込みました。",
                        "絶妙な合わせから豪快に沈めました。",
                        "空中で合わせてそのままリングへ押し込みました。",
                        "ロブに合わせた鮮やかなフィニッシュです。",
                    ],
                )
                extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
                if assister != "-":
                    return f"{assister}のロブパスに、{scorer}がアリウープ成功。{tail}{(' ' + extra) if extra else ''}"
                return f"{scorer}がアリウープ成功。{tail}{(' ' + extra) if extra else ''}"
            if self._is_dunk_candidate(play, presentation_type, structure_event):
                swing_phrase = self._swing_phrase(play, "score_make_2")
                run_phrase = self._run_phrase(play, "score_make_2")
                tail = self._stable_variant(
                    play,
                    "score_make_2_dunk",
                    [
                        "豪快に叩き込みました。",
                        "リングへ力強くねじ込みました。",
                        "ゴール下を制してダンクを沈めました。",
                        "会場が沸く豪快なフィニッシュです。",
                    ],
                )
                extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
                if assister != "-":
                    return f"{assister}からつないで、{scorer}がダンク成功。{tail}{(' ' + extra) if extra else ''}"
                return f"{scorer}がダンク成功。{tail}{(' ' + extra) if extra else ''}"
            swing_phrase = self._swing_phrase(play, "score_make_2")
            run_phrase = self._run_phrase(play, "score_make_2")
            if assister != "-":
                tail = self._stable_variant(
                    play,
                    "score_make_2_assist",
                    [
                        "きれいに崩して決めました。",
                        "呼吸の合った連係です。",
                        "落ち着いてリングに沈めました。",
                        "見事に守備を外しています。",
                    ],
                )
                extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
                return f"{assister}からつないで、{scorer}が2ポイント成功。{tail}{(' ' + extra) if extra else ''}"
            tail = self._stable_variant(
                play,
                "score_make_2",
                [
                    "落ち着いて2点を取りました。",
                    "しっかり決め切りました。",
                    "インサイドで押し込みました。",
                    "体をぶつけながらねじ込みました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}が2ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if presentation_type == "score_make_3":
            swing_phrase = self._swing_phrase(play, "score_make_3")
            run_phrase = self._run_phrase(play, "score_make_3")
            if assister != "-":
                tail = self._stable_variant(
                    play,
                    "score_make_3_assist",
                    [
                        "外の連係が決まりました。",
                        "ボールがよく回っています。",
                        "見事なキックアウトです。",
                        "美しいボールムーブからの一撃です。",
                    ],
                )
                extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
                return f"{assister}のアシストから、{scorer}が3ポイント成功。{tail}{(' ' + extra) if extra else ''}"
            tail = self._stable_variant(
                play,
                "score_make_3",
                [
                    "これは大きな3点です。",
                    "外角をしっかり沈めました。",
                    "流れを引き寄せる3ポイントです。",
                    "迷いなく打ち切りました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase or close_phrase
            return f"{scorer}が3ポイント成功。{tail}{(' ' + extra) if extra else ''}"

        if presentation_type == "score_make_ft":
            swing_phrase = self._swing_phrase(play, "score_make_ft")
            run_phrase = self._run_phrase(play, "score_make_ft")
            tail = self._stable_variant(
                play,
                "score_make_ft",
                [
                    "落ち着いて1本決めました。",
                    "確実に加点します。",
                    "フリースローをしっかり沈めました。",
                    "プレッシャーの中で決めました。",
                ],
            )
            extra = clutch_phrase or swing_phrase or run_phrase
            return f"{scorer}がフリースロー成功。{tail}{(' ' + extra) if extra else ''}"

        if presentation_type == "miss_jump_2":
            if def_rebounder != "-":
                tail = self._stable_variant(
                    play,
                    "miss_jump_2",
                    [
                        "守備側がしっかり収めます。",
                        "ここはディフェンスが踏ん張りました。",
                        "リバウンド争いを制しました。",
                        "簡単には得点を許しません。",
                    ],
                )
                extra = close_phrase if close_phrase else ""
                return f"{final_shooter}のシュートは外れました。{def_rebounder}がディフェンスリバウンド。{tail}{(' ' + extra) if extra else ''}"
            return f"{final_shooter}のシュートは外れました。"

        if presentation_type == "miss_jump_3":
            if def_rebounder != "-":
                tail = self._stable_variant(
                    play,
                    "miss_jump_3",
                    [
                        "守備側が確実に回収します。",
                        "ここは一本守り切りました。",
                        "ディフェンスが主導権を渡しません。",
                        "セカンドチャンスを与えません。",
                    ],
                )
                extra = close_phrase if close_phrase else ""
                return f"{final_shooter}の3ポイントは外れました。{def_rebounder}がディフェンスリバウンド。{tail}{(' ' + extra) if extra else ''}"
            return f"{final_shooter}の3ポイントは外れました。"

        if presentation_type == "miss_free_throw":
            tail = self._stable_variant(
                play,
                "miss_free_throw",
                [
                    "惜しくも入りません。",
                    "これは痛いミスです。",
                    "フリースローは決まりませんでした。",
                    "得点を伸ばせません。",
                ],
            )
            return f"{final_shooter}のフリースローは外れました。{tail}"

        if presentation_type == "def_rebound":
            tail = self._stable_variant(
                play,
                "def_rebound",
                [
                    "これで守備側のボールです。",
                    "しっかりマイボールにしました。",
                    "落ち着いて回収しました。",
                    "守備の締めを見せます。",
                ],
            )
            extra = close_phrase if close_phrase else ""
            return f"{def_rebounder}がディフェンスリバウンドを確保。{tail}{(' ' + extra) if extra else ''}"

        if presentation_type == "off_rebound_keep":
            tail = self._stable_variant(
                play,
                "off_rebound_keep",
                [
                    "もう一度攻め直します。",
                    "セカンドチャンスが生まれました。",
                    "攻撃が続きます。",
                    "粘ってポゼッションをつなぎます。",
                ],
            )
            return f"{off_rebounder}がオフェンスリバウンド。{tail}"

        if presentation_type == "turnover":
            tail = self._stable_variant(
                play,
                "turnover",
                [
                    "攻撃がつながりません。",
                    "ここは痛いターンオーバーです。",
                    "リズムを崩してしまいました。",
                    "流れを手放すミスです。",
                ],
            )
            extra = clutch_phrase if clutch_phrase else ""
            return f"{turnover_player}がターンオーバー。{tail}{(' ' + extra) if extra else ''}"

        if presentation_type == "steal":
            if turnover_player != "-" and stealer != "-":
                tail = self._stable_variant(
                    play,
                    "steal",
                    [
                        "鋭い読みでした。",
                        "守備がプレッシャーをかけています。",
                        "見事なディフェンスです。",
                        "一瞬の隙を逃しません。",
                    ],
                )
                extra = clutch_phrase or close_phrase
                return f"{stealer}がスティール。{turnover_player}からボールを奪いました。{tail}{(' ' + extra) if extra else ''}"
            return "スティールが決まりました。"

        if presentation_type == "block":
            if blocker != "-" and blocked_player != "-":
                tail = self._stable_variant(
                    play,
                    "block",
                    [
                        "豪快に叩き落としました。",
                        "リングに近づけさせません。",
                        "守備の存在感を見せます。",
                        "完全にタイミングを合わせました。",
                    ],
                )
                extra = clutch_phrase or close_phrase
                return f"{blocker}がブロック。{blocked_player}のシュートを止めました。{tail}{(' ' + extra) if extra else ''}"
            return "ブロックが決まりました。"

        if presentation_type == "quarter_start":
            q = play.get("quarter", "-")
            if isinstance(q, int) and q >= 5:
                return "延長開始です。勝負はまだ決まりません。"
            if q == 1:
                tail = self._stable_variant(
                    play,
                    "quarter_start_q1",
                    [
                        "ここから10分の攻防が始まります。",
                        "立ち上がりの主導権争いです。",
                        "最初の10分、流れをつかみにいきます。",
                    ],
                )
            elif q == 4:
                tail = self._stable_variant(
                    play,
                    "quarter_start_q4",
                    [
                        "最後の10分、ここからが本番です。",
                        "このクォーターで流れを決めたいところです。",
                        "残り10分、勝負の行方はここからです。",
                    ],
                )
            else:
                tail = self._stable_variant(
                    play,
                    "quarter_start",
                    [
                        "ここから流れをつかみたいところです。",
                        "次の10分が始まります。",
                        "攻防のテンポが上がります。",
                    ],
                )
            return f"第{q}クォーター開始です。{tail}"

        if presentation_type == "quarter_end":
            q = play.get("quarter", "-")
            if isinstance(q, int) and q >= 5:
                return "延長終了。最後までもつれた勝負でした。"
            tail = self._stable_variant(
                play,
                "quarter_end",
                [
                    "ここでひと区切りです。",
                    "クォーター終了です。",
                    "いったん試合が落ち着きます。",
                ],
            )
            return f"第{q}クォーター終了。{tail}"

        if presentation_type == "game_end":
            tail = self._stable_variant(
                play,
                "game_end",
                [
                    "熱戦に幕が下りました。",
                    "このままタイムアップです。",
                    "会場のどよめきが残ります。",
                    "最後まで目が離せない試合でした。",
                ],
            )
            return f"試合終了。{tail}"

        return str(play.get("commentary_text", play.get("result_type", "play")))

    def _build_sub_text(self, play: dict, presentation_type: str, structure_event: Optional[dict] = None) -> str:
        score_text = self._score_text(play)
        clock_text = self._clock_text(play)
        lead_text = self._lead_context_text(play)

        parts: list[str] = []
        if clock_text:
            parts.append(clock_text)
        if score_text:
            parts.append(score_text)
        if self._is_clutch_moment(play) and presentation_type in {
            "score_make_2",
            "score_make_3",
            "score_make_ft",
            "turnover",
            "steal",
            "block",
            "quarter_end",
            "game_end",
        }:
            parts.append("ここは勝負どころ。")
        elif lead_text and presentation_type in {
            "score_make_2",
            "score_make_3",
            "score_make_ft",
            "turnover",
            "steal",
            "block",
            "def_rebound",
            "quarter_end",
            "game_end",
        }:
            parts.append(lead_text)

        structure_event = structure_event or {}
        structure_type = structure_event.get("structure_type")
        pnr_action = structure_event.get("pnr_action")

        transition_action = play.get("transition_action") or structure_event.get("transition_action")
        if transition_action == "counter":
            if presentation_type in {"score_make_2", "miss_jump_2", "score_make_ft"}:
                parts.append("カウンター速攻。")
            elif presentation_type in {"score_make_3", "miss_jump_3"}:
                parts.append("カウンターからの3P。")
        elif transition_action == "primary_break" or structure_type == "fast_break":
            if presentation_type in {"score_make_2", "miss_jump_2", "score_make_ft"}:
                parts.append("速攻。")
            elif presentation_type in {"score_make_3", "miss_jump_3"}:
                parts.append("速攻からの3P。")

        if self._is_alley_oop_candidate(play, presentation_type, structure_event):
            parts.append("アリウープ。")
        elif self._is_dunk_candidate(play, presentation_type, structure_event):
            parts.append("ダンク。")
        elif self._is_pullup_three_candidate(play, presentation_type, structure_event):
            parts.append("プルアップ3。")

        if structure_type == "pick_and_roll" and pnr_action == "dive" and presentation_type in {"score_make_2", "miss_jump_2"}:
            parts.append("PnRダイブ。")
        elif structure_type == "pick_and_roll" and pnr_action == "pop" and presentation_type in {"score_make_3", "miss_jump_3"}:
            parts.append("ピックアンドポップ3。")
        elif structure_type == "isolation":
            if presentation_type in {"score_make_2", "miss_jump_2"}:
                parts.append("アイソ1on1。")
            elif presentation_type in {"score_make_3", "miss_jump_3"}:
                parts.append("アイソからの3P。")

        return " ".join(parts)

    # =========================================================
    # Data helpers
    # =========================================================
    def _pick_focus_player(
        self,
        play: dict,
        presentation_type: str,
        result_type: str,
    ) -> Optional[str]:
        if presentation_type == "steal":
            return self._none_if_dash(play.get("stealer_name") or play.get("secondary_player_name"))
        if presentation_type == "block":
            return self._none_if_dash(play.get("blocker_name") or play.get("secondary_player_name"))
        if presentation_type == "def_rebound":
            return self._none_if_dash(
                play.get("def_rebounder_name") or play.get("rebounder_name") or play.get("primary_player_name")
            )
        if result_type.startswith("made_"):
            return self._none_if_dash(play.get("scorer_name") or play.get("primary_player_name"))
        if result_type in {"miss_ft", "miss_ft_def_rebound"}:
            return self._none_if_dash(play.get("final_shooter_name") or play.get("primary_player_name"))
        if "miss_" in result_type:
            return self._none_if_dash(play.get("final_shooter_name") or play.get("primary_player_name"))
        if result_type == "off_rebound":
            return self._none_if_dash(
                play.get("off_rebounder_name") or play.get("rebounder_name") or play.get("primary_player_name")
            )
        if result_type == "turnover":
            return self._none_if_dash(play.get("turnover_player_name") or play.get("primary_player_name"))
        if result_type == "steal":
            return self._none_if_dash(play.get("stealer_name") or play.get("secondary_player_name"))
        if result_type.startswith("block"):
            return self._none_if_dash(play.get("blocker_name") or play.get("secondary_player_name"))
        return self._none_if_dash(play.get("primary_player_name"))

    def _pick_support_player(
        self,
        play: dict,
        presentation_type: str,
        result_type: str,
    ) -> Optional[str]:
        if presentation_type == "steal":
            return self._none_if_dash(play.get("turnover_player_name") or play.get("primary_player_name"))
        if presentation_type == "block":
            return self._none_if_dash(play.get("blocked_player_name") or play.get("primary_player_name"))
        if result_type in {"made_2", "made_3"}:
            return self._none_if_dash(play.get("assister_name") or play.get("secondary_player_name"))
        if "def_rebound" in result_type:
            return self._none_if_dash(
                play.get("def_rebounder_name") or play.get("rebounder_name") or play.get("secondary_player_name")
            )
        if "off_rebound" in result_type or result_type == "off_rebound":
            return self._none_if_dash(
                play.get("off_rebounder_name") or play.get("rebounder_name") or play.get("secondary_player_name")
            )
        if result_type == "steal":
            return self._none_if_dash(play.get("turnover_player_name") or play.get("primary_player_name"))
        if result_type.startswith("block"):
            return self._none_if_dash(play.get("blocked_player_name") or play.get("primary_player_name"))
        return self._none_if_dash(play.get("secondary_player_name"))

    def _infer_team_side(self, play: dict, presentation_type: str) -> Optional[str]:
        offense_team = play.get("offense_team_side")
        defense_team = play.get("defense_team_side")
        scoring_team = play.get("scoring_team")

        if presentation_type in {"steal", "block", "def_rebound"}:
            if defense_team in {"home", "away"}:
                return defense_team

        if presentation_type in {"score_make_2", "score_make_3", "score_make_ft", "off_rebound_keep", "turnover"}:
            if scoring_team in {"home", "away"}:
                return scoring_team
            if offense_team in {"home", "away"}:
                return offense_team

        if offense_team in {"home", "away"}:
            return offense_team

        if defense_team in {"home", "away"}:
            return defense_team

        return None

    def _extract_clock(self, play: dict) -> Optional[int]:
        for key in ("clock_seconds", "start_clock_seconds", "end_clock_seconds"):
            value = play.get(key)
            if value is not None:
                return int(value)
        return None

    def _format_clock(self, seconds: Optional[int]) -> str:
        if seconds is None:
            return "--:--"
        mm = int(seconds) // 60
        ss = int(seconds) % 60
        return f"{mm:02d}:{ss:02d}"

    def _name(self, value: Any) -> str:
        if value is None:
            return "-"
        text = str(value).strip()
        return text if text else "-"

    def _none_if_dash(self, value: Any) -> Optional[str]:
        text = self._name(value)
        return None if text == "-" else text


def build_presentation_events(match: Any) -> list[dict]:
    layer = PresentationLayer(match)
    return layer.build()
