from __future__ import annotations

"""
Play Structure Layer for Basketball Project.

Purpose
-------
Safely inserts a tactical-structure layer between play_sequence and
presentation_layer.

Current design goals
--------------------
- Do NOT break existing match / presentation / spectate flow
- Add structure metadata only
- Keep the API simple so presentation_layer can adopt it incrementally
- Start with safe structure types:
    - half_court
    - fast_break
    - second_chance
    - pick_and_roll
    - off_ball_screen
    - post_up
    - handoff

Expected flow
-------------
match
 ↓
play_sequence_log
 ↓
play_structure
 ↓
presentation_layer
 ↓
spectate_view
"""

from dataclasses import dataclass
from collections import Counter
from typing import Any, Optional
import random


STRUCTURE_HALF_COURT = "half_court"
STRUCTURE_FAST_BREAK = "fast_break"
STRUCTURE_SECOND_CHANCE = "second_chance"
STRUCTURE_PICK_AND_ROLL = "pick_and_roll"
STRUCTURE_SPAIN_PICK_AND_ROLL = "spain_pick_and_roll"
STRUCTURE_OFF_BALL_SCREEN = "off_ball_screen"
STRUCTURE_POST_UP = "post_up"
STRUCTURE_HANDOFF = "handoff"
STRUCTURE_ISOLATION = "isolation"

TRANSITION_ACTION_PRIMARY = "primary_break"
TRANSITION_ACTION_COUNTER = "counter"

DIRECTION_LEFT_TO_RIGHT = "left_to_right"
DIRECTION_RIGHT_TO_LEFT = "right_to_left"

SPACING_STANDARD = "standard"
SPACING_WIDE = "wide"
SPACING_COLLAPSE = "collapse"

FORMATION_4_OUT_1_IN = "4_out_1_in"
FORMATION_TRANSITION_LANES = "transition_lanes"
FORMATION_REBOUND_RESET = "rebound_reset"
FORMATION_PICK_AND_ROLL = "pick_and_roll_spacing"
FORMATION_SPAIN_PICK_AND_ROLL = "spain_pick_and_roll_spacing"
FORMATION_OFF_BALL_SCREEN = "off_ball_screen_spacing"
FORMATION_POST_UP = "post_up_spacing"
FORMATION_HANDOFF = "handoff_spacing"
FORMATION_ISOLATION = "isolation_spacing"

PNR_ACTION_SETUP = "setup"
PNR_ACTION_DRIVE = "drive"
PNR_ACTION_ROLL = "roll"
PNR_ACTION_DIVE = "dive"
PNR_ACTION_POP = "pop"
PNR_ACTION_KICKOUT = "kickout"
PNR_ACTION_PULLUP = "pullup"

SPAIN_ACTION_SETUP = "setup"
SPAIN_ACTION_ROLL = "roll"
SPAIN_ACTION_KICKOUT = "kickout"
SPAIN_ACTION_PULLUP = "pullup"

SCREEN_ACTION_SETUP = "screen_setup"
SCREEN_ACTION_CUT = "cut"
SCREEN_ACTION_CATCH = "catch"
SCREEN_ACTION_CATCH_SHOOT = "catch_shoot"

POST_ACTION_SEAL = "seal"
POST_ACTION_BACK_DOWN = "back_down"
POST_ACTION_TURN_SHOOT = "turn_shoot"
POST_ACTION_KICKOUT = "kickout"

HANDOFF_ACTION_SETUP = "setup"
HANDOFF_ACTION_RECEIVE = "receive"
HANDOFF_ACTION_DRIVE = "drive"
HANDOFF_ACTION_PULLUP = "pullup"
HANDOFF_ACTION_KICKOUT = "kickout"


@dataclass(slots=True)
class PlayStructureEvent:
    """Safe normalized tactical-structure event.

    This object intentionally keeps only stable, presentation-friendly data.
    It does not contain UI logic.
    """

    play_index: int
    structure_type: str
    offense_team_side: Optional[str]
    defense_team_side: Optional[str]
    offense_direction: Optional[str]
    formation_name: str
    spacing_profile: str
    tempo_profile: str
    focus_player_name: Optional[str]
    support_player_name: Optional[str]
    ball_handler_name: Optional[str]
    lane_map: dict[str, str]
    raw_play: dict[str, Any]
    transition_action: Optional[str] = None
    pnr_action: Optional[str] = None
    screener_name: Optional[str] = None
    roller_name: Optional[str] = None
    pop_target_name: Optional[str] = None
    kickout_target_name: Optional[str] = None
    screen_side: Optional[str] = None
    drive_lane: Optional[str] = None
    screen_action: Optional[str] = None
    target_name: Optional[str] = None
    cut_lane: Optional[str] = None
    post_action: Optional[str] = None
    post_player_name: Optional[str] = None
    entry_passer_name: Optional[str] = None
    post_side: Optional[str] = None
    post_depth: Optional[str] = None
    handoff_action: Optional[str] = None
    handoff_giver_name: Optional[str] = None
    handoff_receiver_name: Optional[str] = None
    handoff_side: Optional[str] = None
    handoff_lane: Optional[str] = None
    handoff_kickout_target_name: Optional[str] = None
    spain_action: Optional[str] = None
    back_screener_name: Optional[str] = None
    back_screen_target_name: Optional[str] = None
    spain_kickout_target_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "play_index": self.play_index,
            "structure_type": self.structure_type,
            "offense_team_side": self.offense_team_side,
            "defense_team_side": self.defense_team_side,
            "offense_direction": self.offense_direction,
            "formation_name": self.formation_name,
            "spacing_profile": self.spacing_profile,
            "tempo_profile": self.tempo_profile,
            "focus_player_name": self.focus_player_name,
            "support_player_name": self.support_player_name,
            "ball_handler_name": self.ball_handler_name,
            "transition_action": self.transition_action,
            "lane_map": dict(self.lane_map),
            "raw_play": self.raw_play,
            "pnr_action": self.pnr_action,
            "screener_name": self.screener_name,
            "roller_name": self.roller_name,
            "pop_target_name": self.pop_target_name,
            "kickout_target_name": self.kickout_target_name,
            "screen_side": self.screen_side,
            "drive_lane": self.drive_lane,
            "screen_action": self.screen_action,
            "target_name": self.target_name,
            "cut_lane": self.cut_lane,
            "post_action": self.post_action,
            "post_player_name": self.post_player_name,
            "entry_passer_name": self.entry_passer_name,
            "post_side": self.post_side,
            "post_depth": self.post_depth,
            "handoff_action": self.handoff_action,
            "handoff_giver_name": self.handoff_giver_name,
            "handoff_receiver_name": self.handoff_receiver_name,
            "handoff_side": self.handoff_side,
            "handoff_lane": self.handoff_lane,
            "handoff_kickout_target_name": self.handoff_kickout_target_name,
            "spain_action": self.spain_action,
            "back_screener_name": self.back_screener_name,
            "back_screen_target_name": self.back_screen_target_name,
            "spain_kickout_target_name": self.spain_kickout_target_name,
        }


class PlayStructureLayer:
    """Builds tactical-structure data from play_sequence_log.

    Safe usage pattern:
        layer = PlayStructureLayer(match)
        structure_events = layer.build()

    Optional cursor API is provided for future step-by-step playback.
    """

    def __init__(self, match: Any) -> None:
        self.match = match
        self.resolver = PlayStructureResolver(match=match)
        self.formation_factory = FormationFactory()
        self.structure_events: list[dict[str, Any]] = []
        self.cursor: int = 0

    def build(self) -> list[dict[str, Any]]:
        plays = self._get_play_sequence_log()
        results: list[dict[str, Any]] = []

        prev_play: Optional[dict[str, Any]] = None
        for play_index, play in enumerate(plays):
            structure_type = self.resolver.resolve_structure_type(
                play=play,
                prev_play=prev_play,
            )
            offense_team_side = self.resolver.resolve_offense_team_side(play)
            defense_team_side = self._resolve_defense_team_side(offense_team_side)
            offense_direction = self.resolver.resolve_offense_direction(
                play=play,
                offense_team_side=offense_team_side,
            )

            formation_name = self.formation_factory.resolve_formation_name(structure_type)
            spacing_profile = self.formation_factory.resolve_spacing_profile(structure_type)
            tempo_profile = self.formation_factory.resolve_tempo_profile(structure_type)

            focus_player_name = self.resolver.resolve_focus_player_name(play)
            support_player_name = self.resolver.resolve_support_player_name(play)
            ball_handler_name = self.resolver.resolve_ball_handler_name(play)

            pnr_meta = self.resolver.resolve_pick_and_roll_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )
            spain_meta = self.resolver.resolve_spain_pick_and_roll_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )
            offball_meta = self.resolver.resolve_off_ball_screen_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )
            post_meta = self.resolver.resolve_post_up_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )
            handoff_meta = self.resolver.resolve_handoff_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )
            transition_meta = self.resolver.resolve_transition_metadata(
                play=play,
                prev_play=prev_play,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
            )

            lane_map = self.formation_factory.build_lane_map(
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                offense_direction=offense_direction,
                pnr_action=pnr_meta.get("pnr_action"),
                spain_action=spain_meta.get("spain_action"),
                screen_side=pnr_meta.get("screen_side") or spain_meta.get("screen_side") or offball_meta.get("screen_side"),
                screen_action=offball_meta.get("screen_action"),
                cut_lane=offball_meta.get("cut_lane"),
                post_action=post_meta.get("post_action"),
                post_side=post_meta.get("post_side"),
                handoff_action=handoff_meta.get("handoff_action"),
                handoff_side=handoff_meta.get("handoff_side"),
                handoff_lane=handoff_meta.get("handoff_lane"),
                spain_screen_side=spain_meta.get("screen_side"),
                transition_action=transition_meta.get("transition_action"),
            )

            event = PlayStructureEvent(
                play_index=play_index,
                structure_type=structure_type,
                offense_team_side=offense_team_side,
                defense_team_side=defense_team_side,
                offense_direction=offense_direction,
                formation_name=formation_name,
                spacing_profile=spacing_profile,
                tempo_profile=tempo_profile,
                focus_player_name=focus_player_name,
                support_player_name=support_player_name,
                ball_handler_name=ball_handler_name,
                transition_action=transition_meta.get("transition_action"),
                lane_map=lane_map,
                raw_play=play,
                pnr_action=pnr_meta.get("pnr_action"),
                screener_name=pnr_meta.get("screener_name") or spain_meta.get("screener_name") or offball_meta.get("screener_name"),
                roller_name=pnr_meta.get("roller_name") or spain_meta.get("roller_name"),
                pop_target_name=pnr_meta.get("pop_target_name"),
                kickout_target_name=pnr_meta.get("kickout_target_name"),
                screen_side=pnr_meta.get("screen_side") or spain_meta.get("screen_side") or offball_meta.get("screen_side"),
                drive_lane=pnr_meta.get("drive_lane"),
                screen_action=offball_meta.get("screen_action"),
                target_name=offball_meta.get("target_name"),
                cut_lane=offball_meta.get("cut_lane"),
                post_action=post_meta.get("post_action"),
                post_player_name=post_meta.get("post_player_name"),
                entry_passer_name=post_meta.get("entry_passer_name"),
                post_side=post_meta.get("post_side"),
                post_depth=post_meta.get("post_depth"),
                handoff_action=handoff_meta.get("handoff_action"),
                handoff_giver_name=handoff_meta.get("handoff_giver_name"),
                handoff_receiver_name=handoff_meta.get("handoff_receiver_name"),
                handoff_side=handoff_meta.get("handoff_side"),
                handoff_lane=handoff_meta.get("handoff_lane"),
                handoff_kickout_target_name=handoff_meta.get("handoff_kickout_target_name"),
                spain_action=spain_meta.get("spain_action"),
                back_screener_name=spain_meta.get("back_screener_name"),
                back_screen_target_name=spain_meta.get("back_screen_target_name"),
                spain_kickout_target_name=spain_meta.get("spain_kickout_target_name"),
            )
            results.append(event.to_dict())
            prev_play = play

        self.structure_events = results
        self.reset_cursor()
        return results

    def reset_cursor(self) -> None:
        self.cursor = 0

    def get_next_structure_event(self) -> Optional[dict[str, Any]]:
        if self.cursor >= len(self.structure_events):
            return None
        event = self.structure_events[self.cursor]
        self.cursor += 1
        return event

    def get_structure_type_counts(self) -> dict[str, int]:
        if not self.structure_events:
            self.build()
        counts = Counter(
            event.get("structure_type", "unknown")
            for event in self.structure_events
            if isinstance(event, dict)
        )
        return dict(counts)

    def get_structure_action_counts(self) -> dict[str, dict[str, int]]:
        if not self.structure_events:
            self.build()

        buckets: dict[str, Counter] = {
            STRUCTURE_PICK_AND_ROLL: Counter(),
            STRUCTURE_SPAIN_PICK_AND_ROLL: Counter(),
            STRUCTURE_OFF_BALL_SCREEN: Counter(),
            STRUCTURE_POST_UP: Counter(),
            STRUCTURE_HANDOFF: Counter(),
        }

        key_map = {
            STRUCTURE_PICK_AND_ROLL: "pnr_action",
            STRUCTURE_SPAIN_PICK_AND_ROLL: "spain_action",
            STRUCTURE_OFF_BALL_SCREEN: "screen_action",
            STRUCTURE_POST_UP: "post_action",
            STRUCTURE_HANDOFF: "handoff_action",
        }

        for event in self.structure_events:
            if not isinstance(event, dict):
                continue
            structure_type = event.get("structure_type")
            if structure_type not in buckets:
                continue
            action_key = key_map[structure_type]
            action_value = event.get(action_key) or "none"
            buckets[structure_type][str(action_value)] += 1

        return {key: dict(counter) for key, counter in buckets.items()}

    def print_action_preview(self) -> None:
        if not self.structure_events:
            self.build()

        grouped = self.get_structure_action_counts()
        print("[STRUCTURE][ACTIONS] Preview")

        order = [
            STRUCTURE_PICK_AND_ROLL,
            STRUCTURE_SPAIN_PICK_AND_ROLL,
            STRUCTURE_OFF_BALL_SCREEN,
            STRUCTURE_POST_UP,
            STRUCTURE_HANDOFF,
        ]

        for structure_type in order:
            action_counts = grouped.get(structure_type, {})
            total = sum(action_counts.values())
            print(f"[STRUCTURE][ACTIONS] {structure_type} total={total}")
            if not action_counts:
                print("  - none")
                continue
            for action_name in sorted(action_counts.keys()):
                print(f"  - {action_name:<16}: {action_counts[action_name]}")

    def print_preview(self, limit: int = 5) -> None:
        if not self.structure_events:
            self.build()

        counts = self.get_structure_type_counts()
        print("[STRUCTURE] Preview")
        print(f"[STRUCTURE] total_events={len(self.structure_events)}")
        print("[STRUCTURE] structure_type_counts")
        for key in sorted(counts.keys()):
            print(f"  - {key:<20}: {counts[key]}")

        print(f"[STRUCTURE] first_{limit}")
        for event in self.structure_events[:limit]:
            print(
                f"  Play#{event.get('play_index', '-'):<3} | "
                f"structure={event.get('structure_type', '-'):<18} | "
                f"team={event.get('offense_team_side', '-')} | "
                f"focus={event.get('focus_player_name', '-')} | "
                f"support={event.get('support_player_name', '-')} | "
                f"pnr={event.get('pnr_action', '-')} | "
                f"offball={event.get('screen_action', '-')} | "
                f"post={event.get('post_action', '-')} | "
                f"handoff={event.get('handoff_action', '-')} | "
                f"spain={event.get('spain_action', '-')}"
            )

        print(f"[STRUCTURE] last_{limit}")
        for event in self.structure_events[-limit:]:
            print(
                f"  Play#{event.get('play_index', '-'):<3} | "
                f"structure={event.get('structure_type', '-'):<18} | "
                f"team={event.get('offense_team_side', '-')} | "
                f"focus={event.get('focus_player_name', '-')} | "
                f"support={event.get('support_player_name', '-')} | "
                f"pnr={event.get('pnr_action', '-')} | "
                f"offball={event.get('screen_action', '-')} | "
                f"post={event.get('post_action', '-')} | "
                f"handoff={event.get('handoff_action', '-')} | "
                f"spain={event.get('spain_action', '-')}"
            )

    def print_handoff_preview(self) -> None:
        if not self.structure_events:
            self.build()

        handoff_events = [
            event for event in self.structure_events
            if isinstance(event, dict) and event.get("structure_type") == STRUCTURE_HANDOFF
        ]

        print("[STRUCTURE][HANDOFF] Preview")
        print(f"[STRUCTURE][HANDOFF] total_events={len(handoff_events)}")

        if not handoff_events:
            print("[STRUCTURE][HANDOFF] no handoff events found")
            return

        for event in handoff_events:
            print(
                f"  Play#{event.get('play_index', '-'):<3} | "
                f"team={event.get('offense_team_side', '-')} | "
                f"focus={event.get('focus_player_name', '-')} | "
                f"support={event.get('support_player_name', '-')} | "
                f"giver={event.get('handoff_giver_name', '-')} | "
                f"receiver={event.get('handoff_receiver_name', '-')} | "
                f"action={event.get('handoff_action', '-')} | "
                f"side={event.get('handoff_side', '-')} | "
                f"lane={event.get('handoff_lane', '-')}"
            )

    def _get_play_sequence_log(self) -> list[dict[str, Any]]:
        if hasattr(self.match, "get_play_sequence_log"):
            try:
                plays = self.match.get_play_sequence_log()
                if isinstance(plays, list):
                    return [p for p in plays if isinstance(p, dict)]
            except Exception:
                return []
        return []

    def _resolve_defense_team_side(self, offense_team_side: Optional[str]) -> Optional[str]:
        if offense_team_side == "home":
            return "away"
        if offense_team_side == "away":
            return "home"
        return None


class PlayStructureResolver:
    """Resolves structure metadata from raw play_sequence events."""

    def __init__(self, match: Any) -> None:
        self.match = match
        self.random = random.Random(11)

    def resolve_structure_type(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]] = None,
    ) -> str:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return STRUCTURE_SECOND_CHANCE
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return STRUCTURE_FAST_BREAK
        if self._is_spain_pick_and_roll_play(play=play, prev_play=prev_play):
            return STRUCTURE_SPAIN_PICK_AND_ROLL

        # For 3pt outcomes, prefer to preserve explicit screen-ball structure before
        # falling back to isolation. This helps pull-up / pop 3s survive instead of
        # being swallowed by broad creator-driven isolation classification.
        result_type = self._get_result_type(play)
        is_three_point_result = result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}
        if is_three_point_result and self._is_pick_and_roll_play(play=play, prev_play=prev_play):
            return STRUCTURE_PICK_AND_ROLL

        # Isolation should be decided before broader half-court actions for most
        # non-3pt actions so it is not swallowed by generic PnR / off-ball /
        # handoff classification.
        if self._is_isolation_play(play=play, prev_play=prev_play):
            return STRUCTURE_ISOLATION
        if self._is_pick_and_roll_play(play=play, prev_play=prev_play):
            return STRUCTURE_PICK_AND_ROLL
        if self._is_off_ball_screen_play(play=play, prev_play=prev_play):
            return STRUCTURE_OFF_BALL_SCREEN
        if self._is_post_up_play(play=play, prev_play=prev_play):
            return STRUCTURE_POST_UP
        if self._is_handoff_play(play=play, prev_play=prev_play):
            return STRUCTURE_HANDOFF
        return STRUCTURE_HALF_COURT

    def resolve_offense_team_side(self, play: dict[str, Any]) -> Optional[str]:
        for key in (
            "offense_team_side",
            "team_side",
            "possession_team_side",
            "scoring_team",
        ):
            value = play.get(key)
            if value in {"home", "away"}:
                return value

        primary = self.resolve_focus_player_name(play)
        if isinstance(primary, str) and primary.strip():
            inferred = self._infer_player_team_side(primary)
            if inferred in {"home", "away"}:
                return inferred

        secondary = self.resolve_support_player_name(play)
        if isinstance(secondary, str) and secondary.strip():
            inferred = self._infer_player_team_side(secondary)
            if inferred in {"home", "away"}:
                return inferred
        return None

    def resolve_offense_direction(
        self,
        play: dict[str, Any],
        offense_team_side: Optional[str],
    ) -> Optional[str]:
        explicit = play.get("offense_direction")
        if explicit in {DIRECTION_LEFT_TO_RIGHT, DIRECTION_RIGHT_TO_LEFT}:
            return explicit
        if offense_team_side == "home":
            return DIRECTION_LEFT_TO_RIGHT
        if offense_team_side == "away":
            return DIRECTION_RIGHT_TO_LEFT
        return None

    def resolve_focus_player_name(self, play: dict[str, Any]) -> Optional[str]:
        for key in (
            "primary_player_name",
            "focus_player_name",
            "player_name",
            "shooter_name",
            "rebounder_name",
        ):
            value = play.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    def resolve_support_player_name(self, play: dict[str, Any]) -> Optional[str]:
        for key in (
            "secondary_player_name",
            "support_player_name",
            "passer_name",
            "assister_name",
        ):
            value = play.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    def resolve_ball_handler_name(self, play: dict[str, Any]) -> Optional[str]:
        explicit = play.get("ball_handler_name")
        if isinstance(explicit, str) and explicit.strip():
            return explicit
        focus = self.resolve_focus_player_name(play)
        if isinstance(focus, str) and focus.strip():
            return focus
        support = self.resolve_support_player_name(play)
        if isinstance(support, str) and support.strip():
            return support
        return None

    def resolve_transition_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_FAST_BREAK:
            return {
                "transition_action": None,
                "lead_runner_name": None,
                "trail_runner_name": None,
            }

        action = self.resolve_transition_action(play=play, prev_play=prev_play)
        lead_runner_name = ball_handler_name or focus_player_name or support_player_name
        trail_runner_name = None
        if action == TRANSITION_ACTION_COUNTER:
            trail_runner_name = support_player_name
        return {
            "transition_action": action,
            "lead_runner_name": lead_runner_name,
            "trail_runner_name": trail_runner_name,
        }

    def resolve_transition_action(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> str:
        result_type = self._get_result_type(play)
        prev_result_type = self._get_result_type(prev_play)
        if result_type in {"counter_attack", "counter", "fastbreak_counter"}:
            return TRANSITION_ACTION_COUNTER
        if prev_result_type in {"steal", "turnover", "block", "def_rebound", "long_rebound"}:
            return TRANSITION_ACTION_COUNTER
        return TRANSITION_ACTION_PRIMARY

    def resolve_pick_and_roll_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_PICK_AND_ROLL:
            return {
                "pnr_action": None,
                "screener_name": None,
                "roller_name": None,
                "pop_target_name": None,
                "kickout_target_name": None,
                "screen_side": None,
                "drive_lane": None,
            }

        handler = ball_handler_name or focus_player_name or support_player_name
        action = self.resolve_pick_and_roll_action(play)
        screener = self.choose_screener(
            offense_team_side=offense_team_side,
            ball_handler_name=handler,
            support_player_name=support_player_name,
        )
        if screener == handler:
            screener = None

        screen_side = self.resolve_screen_side(handler, screener, offense_direction)
        drive_lane = self.resolve_drive_lane(screen_side)

        roller_name: Optional[str] = None
        pop_target_name: Optional[str] = None
        kickout_target_name: Optional[str] = None

        if action in {PNR_ACTION_ROLL, PNR_ACTION_DIVE}:
            roller_name = screener
        elif action == PNR_ACTION_POP:
            pop_target_name = screener
        elif action == PNR_ACTION_KICKOUT:
            kickout_target_name = self.choose_kickout_target(
                offense_team_side=offense_team_side,
                ball_handler_name=handler,
                screener_name=screener,
            )
        elif action == PNR_ACTION_DRIVE and self._result_type_is_drive_like(play):
            roller_name = screener

        return {
            "pnr_action": action,
            "screener_name": screener,
            "roller_name": roller_name,
            "pop_target_name": pop_target_name,
            "kickout_target_name": kickout_target_name,
            "screen_side": screen_side,
            "drive_lane": drive_lane,
        }


    def resolve_spain_pick_and_roll_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_SPAIN_PICK_AND_ROLL:
            return {
                "spain_action": None,
                "screener_name": None,
                "roller_name": None,
                "back_screener_name": None,
                "back_screen_target_name": None,
                "spain_kickout_target_name": None,
                "screen_side": None,
            }

        handler = ball_handler_name or focus_player_name or support_player_name
        screener_name = self.choose_screener(
            offense_team_side=offense_team_side,
            ball_handler_name=handler,
            support_player_name=support_player_name,
        )
        if not handler or not screener_name or screener_name == handler:
            return {
                "spain_action": None,
                "screener_name": None,
                "roller_name": None,
                "back_screener_name": None,
                "back_screen_target_name": None,
                "spain_kickout_target_name": None,
                "screen_side": None,
            }

        back_screener_name = self.choose_spain_back_screener(
            offense_team_side=offense_team_side,
            handler_name=handler,
            screener_name=screener_name,
            focus_player_name=focus_player_name,
            support_player_name=support_player_name,
        )
        if not back_screener_name or back_screener_name in {handler, screener_name}:
            return {
                "spain_action": None,
                "screener_name": None,
                "roller_name": None,
                "back_screener_name": None,
                "back_screen_target_name": None,
                "spain_kickout_target_name": None,
                "screen_side": None,
            }

        spain_action = self.resolve_spain_pick_and_roll_action(play=play, handler_name=handler)
        roller_name = screener_name
        back_screen_target_name = roller_name
        screen_side = self.resolve_screen_side(handler, screener_name, offense_direction)

        spain_kickout_target_name = None
        if spain_action == SPAIN_ACTION_KICKOUT:
            spain_kickout_target_name = self.choose_spain_kickout_target(
                offense_team_side=offense_team_side,
                handler_name=handler,
                screener_name=screener_name,
                back_screener_name=back_screener_name,
            )

        return {
            "spain_action": spain_action,
            "screener_name": screener_name,
            "roller_name": roller_name,
            "back_screener_name": back_screener_name,
            "back_screen_target_name": back_screen_target_name,
            "spain_kickout_target_name": spain_kickout_target_name,
            "screen_side": screen_side,
        }

    def _is_spain_pick_and_roll_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        handler = self.resolve_ball_handler_name(play)
        if not handler:
            return False

        handler_pos = self._extract_player_position_by_name(handler)
        handler_arch = self._extract_player_archetype_by_name(handler)
        if handler_pos not in {"PG", "SG"} and handler_arch not in {
            "playmaker", "floor_general", "scoring_guard", "slasher"
        }:
            return False

        screener_name = self.choose_screener(
            offense_team_side=offense_team_side,
            ball_handler_name=handler,
            support_player_name=self.resolve_support_player_name(play),
        )
        if not screener_name or screener_name == handler:
            return False

        back_screener_name = self.choose_spain_back_screener(
            offense_team_side=offense_team_side,
            handler_name=handler,
            screener_name=screener_name,
            focus_player_name=self.resolve_focus_player_name(play),
            support_player_name=self.resolve_support_player_name(play),
        )
        if not back_screener_name or back_screener_name in {handler, screener_name}:
            return False

        score = 0.0
        if handler_pos == "PG":
            score += 0.18
        if handler_arch in {"playmaker", "floor_general"}:
            score += 0.20
        elif handler_arch in {"scoring_guard", "slasher"}:
            score += 0.10

        screener_pos = self._extract_player_position_by_name(screener_name)
        screener_arch = self._extract_player_archetype_by_name(screener_name)
        if screener_pos in {"PF", "C"}:
            score += 0.16
        if screener_arch in {"rim_protector", "rebounder", "stretch_big"}:
            score += 0.14

        back_pos = self._extract_player_position_by_name(back_screener_name)
        back_arch = self._extract_player_archetype_by_name(back_screener_name)
        if back_pos in {"SG", "SF"}:
            score += 0.16
        elif back_pos == "PG":
            score += 0.08
        if back_arch in {"scoring_guard", "two_way_wing", "playmaker"}:
            score += 0.16

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.10
        elif result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.06
        elif result_type == "turnover":
            score += 0.03

        # Safe tuning:
        # - Spain PnR should appear, but not overpower normal pick_and_roll
        # - keep it as a clearly rarer subset of pick_and_roll
        spain_threshold = min(0.22, max(0.08, score))
        hashed_roll = self._stable_roll(play)
        return hashed_roll < spain_threshold

    def resolve_spain_pick_and_roll_action(self, play: dict[str, Any], handler_name: Optional[str]) -> str:
        result_type = self._get_result_type(play)

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            weights = [
                (SPAIN_ACTION_KICKOUT, 0.54),
                (SPAIN_ACTION_PULLUP, 0.28),
                (SPAIN_ACTION_SETUP, 0.18),
            ]
            weights = self._apply_handler_archetype_weights(weights, handler_name)
            return self._weighted_choice(weights, play, "spain_3pt")

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            weights = [
                (SPAIN_ACTION_ROLL, 0.58),
                (SPAIN_ACTION_KICKOUT, 0.24),
                (SPAIN_ACTION_SETUP, 0.18),
            ]
            weights = self._apply_handler_archetype_weights(weights, handler_name)
            return self._weighted_choice(weights, play, "spain_2pt")

        if result_type == "turnover":
            weights = [
                (SPAIN_ACTION_SETUP, 0.34),
                (SPAIN_ACTION_ROLL, 0.32),
                (SPAIN_ACTION_KICKOUT, 0.34),
            ]
            weights = self._apply_handler_archetype_weights(weights, handler_name)
            return self._weighted_choice(weights, play, "spain_turnover")

        return SPAIN_ACTION_SETUP

    def choose_spain_back_screener(
        self,
        offense_team_side: Optional[str],
        handler_name: Optional[str],
        screener_name: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        for candidate in (focus_player_name, support_player_name):
            if not candidate or candidate in {handler_name, screener_name}:
                continue
            pos = self._extract_player_position_by_name(candidate)
            arch = self._extract_player_archetype_by_name(candidate)
            if pos in {"SG", "SF"} or arch in {"scoring_guard", "two_way_wing", "playmaker"}:
                return candidate

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name in {handler_name, screener_name}:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "SG":
                score += 28
            elif pos == "SF":
                score += 24
            elif pos == "PG":
                score += 14
            if arch == "scoring_guard":
                score += 18
            elif arch == "two_way_wing":
                score += 16
            elif arch == "playmaker":
                score += 14
            if score > 0:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_spain_kickout_target(
        self,
        offense_team_side: Optional[str],
        handler_name: Optional[str],
        screener_name: Optional[str],
        back_screener_name: Optional[str],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name in {handler_name, screener_name, back_screener_name}:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos in {"SG", "SF"}:
                score += 22
            elif pos == "PF":
                score += 10
            if arch == "scoring_guard":
                score += 18
            elif arch == "two_way_wing":
                score += 16
            elif arch == "stretch_big":
                score += 14
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def resolve_off_ball_screen_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_OFF_BALL_SCREEN:
            return {
                "screen_action": None,
                "screener_name": None,
                "target_name": None,
                "screen_side": None,
                "cut_lane": None,
            }

        target_name = self.choose_off_ball_target(
            offense_team_side=offense_team_side,
            focus_player_name=focus_player_name,
            support_player_name=support_player_name,
            ball_handler_name=ball_handler_name,
            play=play,
        )
        screener_name = self.choose_off_ball_screener(
            offense_team_side=offense_team_side,
            target_name=target_name,
            support_player_name=support_player_name,
        )
        if not screener_name or screener_name == target_name:
            return {
                "screen_action": None,
                "screener_name": None,
                "target_name": None,
                "screen_side": None,
                "cut_lane": None,
            }

        screen_side = self.resolve_screen_side(target_name, screener_name, offense_direction)
        screen_action = self.resolve_off_ball_screen_action(play=play, target_name=target_name)
        cut_lane = self.resolve_cut_lane(target_name=target_name, screen_side=screen_side, screen_action=screen_action)

        return {
            "screen_action": screen_action,
            "screener_name": screener_name,
            "target_name": target_name,
            "screen_side": screen_side,
            "cut_lane": cut_lane,
        }

    def _is_second_chance_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        result_type = self._get_result_type(play)
        prev_result_type = self._get_result_type(prev_play)
        if result_type in {"off_rebound", "off_rebound_keep"}:
            return True
        if prev_result_type in {"off_rebound", "off_rebound_keep"}:
            current_offense = self.resolve_offense_team_side(play)
            prev_offense = self.resolve_offense_team_side(prev_play or {})
            if current_offense is not None and current_offense == prev_offense:
                return True
        return False

    def _is_fast_break_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        result_type = self._get_result_type(play)
        prev_result_type = self._get_result_type(prev_play)

        if result_type in {"fast_break", "transition_attack", "counter_attack", "counter", "fastbreak_counter"}:
            return True

        transition_finish_types = {
            "made_2", "miss_2", "made_3", "miss_3", "made_ft", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }
        if result_type not in transition_finish_types:
            return False

        trigger_types = {"steal", "turnover", "def_rebound", "block", "long_rebound"}
        if prev_result_type not in trigger_types:
            return False

        current_offense = self.resolve_offense_team_side(play)
        prev_focus = self.resolve_focus_player_name(prev_play or {})
        prev_support = self.resolve_support_player_name(prev_play or {})
        prev_side = self._infer_player_team_side(prev_focus) if prev_focus else None
        if prev_side is None and prev_support:
            prev_side = self._infer_player_team_side(prev_support)

        # Prefer grounded team-side confirmation when available.
        if current_offense is not None and prev_side is not None:
            if current_offense != prev_side:
                return False

        score = 0.52
        if prev_result_type in {"steal", "turnover"}:
            score += 0.28
        elif prev_result_type == "block":
            score += 0.18
        elif prev_result_type in {"def_rebound", "long_rebound"}:
            score += 0.16

        if result_type in {"made_2", "made_3"}:
            score += 0.08
        if result_type == "made_3":
            score -= 0.04

        handler = self.resolve_ball_handler_name(play)
        handler_pos = self._extract_player_position_by_name(handler) if handler else None
        if handler_pos in {"PG", "SG", "SF"}:
            score += 0.06

        hashed_roll = self._stable_roll(play)
        return hashed_roll < max(0.18, min(0.90, score))

    def _is_isolation_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        handler = self.resolve_ball_handler_name(play)
        if not handler:
            return False

        support = self.resolve_support_player_name(play)
        handler_pos = self._extract_player_position_by_name(handler)
        handler_arch = self._extract_player_archetype_by_name(handler)

        # Isolation should be a scorer/creator-centric half-court action.
        if handler_pos not in {"PG", "SG", "SF", "PF"}:
            return False
        if handler_arch not in {
            "scoring_guard", "slasher", "shot_creator", "two_way_wing",
            "playmaker", "point_forward", "three_level_scorer", "iso_scorer"
        }:
            # Allow some SG/SF/PG actions to still become isolation, but at lower odds.
            base_creator_bonus = 0.0
        else:
            base_creator_bonus = 0.18

        score = 0.18
        if handler_pos in {"SG", "SF"}:
            score += 0.10
        elif handler_pos == "PG":
            score += 0.08
        elif handler_pos == "PF":
            score += 0.04

        score += base_creator_bonus

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.14
        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.18
        if result_type == "turnover":
            score += 0.06

        # If a support player is explicitly involved, isolation should still be possible
        # but noticeably less likely.
        if support:
            # For 3pt outcomes, an explicit support/screener is often a clue that the
            # action should resolve to PnR / off-ball instead of isolation.
            penalty = 0.16 if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"} else 0.12
            score -= penalty

        # Avoid swallowing very clear screen-heavy actions.
        prev_result = self._get_result_type(prev_play) if prev_play else None
        if prev_result in {"screen", "handoff", "off_ball_screen"}:
            score -= 0.08

        hashed_roll = self._stable_roll(play)
        return hashed_roll < min(0.58, max(0.20, score))

    def _is_pick_and_roll_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        handler = self.resolve_ball_handler_name(play)
        if not handler:
            return False

        handler_pos = self._extract_player_position_by_name(handler)
        handler_arch = self._extract_player_archetype_by_name(handler)
        if handler_pos not in {"PG", "SG"} and handler_arch not in {
            "playmaker", "floor_general", "scoring_guard", "slasher"
        }:
            return False

        screener = self.choose_screener(
            offense_team_side=offense_team_side,
            ball_handler_name=handler,
            support_player_name=self.resolve_support_player_name(play),
        )
        if not screener:
            return False

        score = 0.0
        if handler_pos == "PG":
            score += 0.20
        if handler_arch in {"playmaker", "floor_general"}:
            score += 0.25
        elif handler_arch in {"scoring_guard", "slasher"}:
            score += 0.12

        screener_pos = self._extract_player_position_by_name(screener)
        screener_arch = self._extract_player_archetype_by_name(screener)
        if screener_pos in {"PF", "C"}:
            score += 0.20
        if screener_arch in {"rim_protector", "rebounder", "stretch_big"}:
            score += 0.20

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.18
        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.10
        if result_type == "turnover":
            score += 0.04

        hashed_roll = self._stable_roll(play)
        return hashed_roll < min(0.72, max(0.28, score))

    def _is_off_ball_screen_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False
        if self._is_pick_and_roll_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        target_name = self.choose_off_ball_target(
            offense_team_side=offense_team_side,
            focus_player_name=self.resolve_focus_player_name(play),
            support_player_name=self.resolve_support_player_name(play),
            ball_handler_name=self.resolve_ball_handler_name(play),
            play=play,
        )
        screener_name = self.choose_off_ball_screener(
            offense_team_side=offense_team_side,
            target_name=target_name,
            support_player_name=self.resolve_support_player_name(play),
        )
        if not target_name or not screener_name:
            return False

        target_pos = self._extract_player_position_by_name(target_name)
        target_arch = self._extract_player_archetype_by_name(target_name)
        screener_pos = self._extract_player_position_by_name(screener_name)
        screener_arch = self._extract_player_archetype_by_name(screener_name)

        score = 0.0
        if target_pos in {"SG", "SF"}:
            score += 0.22
        if target_arch in {"scoring_guard", "two_way_wing", "stretch_big"}:
            score += 0.20
        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.18
        elif result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.08

        if screener_pos in {"PF", "C", "SF"}:
            score += 0.18
        if screener_arch in {"rebounder", "rim_protector", "two_way_wing", "stretch_big"}:
            score += 0.16

        hashed_roll = self._stable_roll(play)
        return hashed_roll < min(0.58, max(0.18, score))

    def resolve_pick_and_roll_action(self, play: dict[str, Any]) -> str:
        result_type = self._get_result_type(play)
        handler_name = self.resolve_ball_handler_name(play)
        offense_team_side = self.resolve_offense_team_side(play)
        support_name = self.resolve_support_player_name(play)
        screener_name = self.choose_screener(
            offense_team_side=offense_team_side,
            ball_handler_name=handler_name,
            support_player_name=support_name,
        )

        handler_arch = self._extract_player_archetype_by_name(handler_name)
        screener_arch = self._extract_player_archetype_by_name(screener_name)
        screener_pos = self._extract_player_position_by_name(screener_name)

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            # Pull-up 3s were too rare in live runs, so bias more strongly toward pull-up
            # when the handler is a creator/scorer. Pop and kickout still remain available.
            weights = [
                (PNR_ACTION_PULLUP, 0.50),
                (PNR_ACTION_POP, 0.24),
                (PNR_ACTION_KICKOUT, 0.18),
                (PNR_ACTION_SETUP, 0.08),
            ]
            if screener_arch == "stretch_big":
                weights = [(action, weight + (0.12 if action == PNR_ACTION_POP else 0.0)) for action, weight in weights]
            if screener_pos == "C":
                weights = [(action, weight - (0.04 if action == PNR_ACTION_POP else 0.0)) for action, weight in weights]
            if handler_arch in {"playmaker", "floor_general"}:
                weights = [(action, weight + (0.06 if action == PNR_ACTION_KICKOUT else 0.0)) for action, weight in weights]
            if handler_arch in {"scoring_guard", "slasher", "shot_creator", "three_level_scorer", "iso_scorer"}:
                weights = [(action, weight + (0.18 if action == PNR_ACTION_PULLUP else 0.0)) for action, weight in weights]
            if handler_arch in {"shooter", "movement_shooter"}:
                weights = [(action, weight + (0.10 if action == PNR_ACTION_PULLUP else 0.0)) for action, weight in weights]
            return self._weighted_choice(weights, play, "pnr_3pt")

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            weights = [
                (PNR_ACTION_DRIVE, 0.36),
                (PNR_ACTION_DIVE, 0.40),
                (PNR_ACTION_SETUP, 0.24),
            ]
            if screener_pos in {"PF", "C"} or screener_arch in {"rim_protector", "rebounder"}:
                weights = [(action, weight + (0.10 if action == PNR_ACTION_DIVE else 0.0)) for action, weight in weights]
            if handler_arch in {"slasher", "playmaker"}:
                weights = [(action, weight + (0.05 if action == PNR_ACTION_DRIVE else 0.0)) for action, weight in weights]
            return self._weighted_choice(weights, play, "pnr_2pt")

        if result_type == "turnover":
            weights = [
                (PNR_ACTION_SETUP, 0.50),
                (PNR_ACTION_DRIVE, 0.22),
                (PNR_ACTION_DIVE, 0.28),
            ]
            return self._weighted_choice(weights, play, "pnr_turnover")

        return PNR_ACTION_SETUP

    def resolve_off_ball_screen_action(self, play: dict[str, Any], target_name: Optional[str]) -> str:
        result_type = self._get_result_type(play)

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            weights = [
                (SCREEN_ACTION_CATCH_SHOOT, 0.56),
                (SCREEN_ACTION_CATCH, 0.30),
                (SCREEN_ACTION_SETUP, 0.14),
            ]
            weights = self._apply_handler_archetype_weights(weights, target_name)
            return self._weighted_choice(weights, play, "offball_3pt")

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            weights = [
                (SCREEN_ACTION_CUT, 0.42),
                (SCREEN_ACTION_CATCH, 0.34),
                (SCREEN_ACTION_SETUP, 0.24),
            ]
            weights = self._apply_handler_archetype_weights(weights, target_name)
            return self._weighted_choice(weights, play, "offball_2pt")

        return SCREEN_ACTION_SETUP

    def choose_screener(self, offense_team_side: Optional[str], ball_handler_name: Optional[str], support_player_name: Optional[str] = None) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        if support_player_name:
            pos = self._extract_player_position_by_name(support_player_name)
            arch = self._extract_player_archetype_by_name(support_player_name)
            if pos in {"PF", "C"} or arch in {"rim_protector", "rebounder", "stretch_big"}:
                return support_player_name

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name == ball_handler_name:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "C":
                score += 40
            elif pos == "PF":
                score += 35
            elif pos == "SF":
                score += 10
            if arch == "rim_protector":
                score += 18
            elif arch == "rebounder":
                score += 16
            elif arch == "stretch_big":
                score += 14
            if pos in {"PF", "C"} or arch in {"rim_protector", "rebounder", "stretch_big"}:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_kickout_target(self, offense_team_side: Optional[str], ball_handler_name: Optional[str], screener_name: Optional[str]) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name in {ball_handler_name, screener_name}:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos in {"SG", "SF"}:
                score += 20
            elif pos == "PG":
                score += 10
            if arch == "scoring_guard":
                score += 22
            elif arch == "two_way_wing":
                score += 18
            elif arch == "stretch_big":
                score += 15
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_off_ball_screener(self, offense_team_side: Optional[str], target_name: Optional[str], support_player_name: Optional[str] = None) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        if support_player_name and support_player_name != target_name:
            pos = self._extract_player_position_by_name(support_player_name)
            arch = self._extract_player_archetype_by_name(support_player_name)
            if pos in {"PF", "C", "SF"} or arch in {"rebounder", "rim_protector", "two_way_wing", "stretch_big"}:
                return support_player_name

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name == target_name:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "PF":
                score += 30
            elif pos == "C":
                score += 28
            elif pos == "SF":
                score += 20
            if arch == "two_way_wing":
                score += 16
            elif arch == "rebounder":
                score += 15
            elif arch == "rim_protector":
                score += 14
            elif arch == "stretch_big":
                score += 12
            if score > 0:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_off_ball_target(
        self,
        offense_team_side: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
        play: dict[str, Any],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        focus_pos = self._extract_player_position_by_name(focus_player_name)
        focus_arch = self._extract_player_archetype_by_name(focus_player_name)
        if focus_player_name and focus_player_name != ball_handler_name:
            if focus_pos in {"SG", "SF"} or focus_arch in {"scoring_guard", "two_way_wing", "stretch_big"}:
                return focus_player_name

        support_pos = self._extract_player_position_by_name(support_player_name)
        support_arch = self._extract_player_archetype_by_name(support_player_name)
        if support_player_name and support_player_name != ball_handler_name:
            if support_pos in {"SG", "SF"} or support_arch in {"scoring_guard", "two_way_wing", "stretch_big"}:
                return support_player_name

        result_type = self._get_result_type(play)
        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name == ball_handler_name:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "SG":
                score += 30
            elif pos == "SF":
                score += 28
            elif pos == "PF":
                score += 8
            if arch == "scoring_guard":
                score += 20
            elif arch == "two_way_wing":
                score += 18
            elif arch == "stretch_big":
                score += 14
            if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
                if arch in {"scoring_guard", "two_way_wing", "stretch_big"}:
                    score += 10
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def resolve_screen_side(self, primary_name: Optional[str], secondary_name: Optional[str], offense_direction: Optional[str]) -> str:
        seed_parts = [primary_name or "", secondary_name or "", offense_direction or ""]
        total = sum(ord(ch) for ch in "|".join(seed_parts))
        mod = total % 3
        if mod == 0:
            return "left"
        if mod == 1:
            return "right"
        return "middle"

    def resolve_drive_lane(self, screen_side: Optional[str]) -> str:
        if screen_side == "left":
            return "right"
        if screen_side == "right":
            return "left"
        return "middle"

    def resolve_cut_lane(self, target_name: Optional[str], screen_side: Optional[str], screen_action: Optional[str]) -> str:
        target_pos = self._extract_player_position_by_name(target_name)
        target_arch = self._extract_player_archetype_by_name(target_name)
        if screen_action == SCREEN_ACTION_CATCH_SHOOT:
            return "wing"
        if target_arch in {"scoring_guard", "two_way_wing"} and target_pos in {"SG", "SF"}:
            return "baseline"
        if screen_side == "middle":
            return "middle"
        return "wing"

    def resolve_post_up_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_POST_UP:
            return {
                "post_action": None,
                "post_player_name": None,
                "entry_passer_name": None,
                "kickout_target_name": None,
                "post_side": None,
                "post_depth": None,
            }

        post_player_name = self.choose_post_player(
            offense_team_side=offense_team_side,
            focus_player_name=focus_player_name,
            support_player_name=support_player_name,
        )
        if not post_player_name:
            return {
                "post_action": None,
                "post_player_name": None,
                "entry_passer_name": None,
                "kickout_target_name": None,
                "post_side": None,
                "post_depth": None,
            }

        entry_passer_name = self.choose_entry_passer(
            offense_team_side=offense_team_side,
            post_player_name=post_player_name,
            ball_handler_name=ball_handler_name,
        )
        post_action = self.resolve_post_up_action(play=play, post_player_name=post_player_name)
        kickout_target_name = None
        if post_action == POST_ACTION_KICKOUT:
            kickout_target_name = self.choose_post_kickout_target(
                offense_team_side=offense_team_side,
                post_player_name=post_player_name,
                entry_passer_name=entry_passer_name,
            )

        post_side = self.resolve_post_side(
            post_player_name=post_player_name,
            entry_passer_name=entry_passer_name,
            offense_direction=offense_direction,
        )
        post_depth = self.resolve_post_depth(post_player_name=post_player_name, post_action=post_action)
        return {
            "post_action": post_action,
            "post_player_name": post_player_name,
            "entry_passer_name": entry_passer_name,
            "kickout_target_name": kickout_target_name,
            "post_side": post_side,
            "post_depth": post_depth,
        }

    def _is_post_up_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False
        if self._is_pick_and_roll_play(play=play, prev_play=prev_play):
            return False
        if self._is_off_ball_screen_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        post_player = self.choose_post_player(
            offense_team_side=offense_team_side,
            focus_player_name=self.resolve_focus_player_name(play),
            support_player_name=self.resolve_support_player_name(play),
        )
        if not post_player:
            return False

        post_pos = self._extract_player_position_by_name(post_player)
        post_arch = self._extract_player_archetype_by_name(post_player)
        score = 0.0
        if post_pos == "C":
            score += 0.28
        elif post_pos == "PF":
            score += 0.22
        if post_arch in {"rim_protector", "rebounder", "stretch_big"}:
            score += 0.20
        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.18
        elif result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.06
        elif result_type == "turnover":
            score += 0.04

        hashed_roll = self._stable_roll(play)
        return hashed_roll < min(0.46, max(0.16, score))

    def resolve_post_up_action(self, play: dict[str, Any], post_player_name: Optional[str]) -> str:
        result_type = self._get_result_type(play)

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            weights = [
                (POST_ACTION_KICKOUT, 0.58),
                (POST_ACTION_SEAL, 0.22),
                (POST_ACTION_BACK_DOWN, 0.20),
            ]
            weights = self._apply_big_archetype_weights(weights, post_player_name)
            return self._weighted_choice(weights, play, "post_3pt")

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            weights = [
                (POST_ACTION_TURN_SHOOT, 0.38),
                (POST_ACTION_BACK_DOWN, 0.36),
                (POST_ACTION_SEAL, 0.26),
            ]
            weights = self._apply_big_archetype_weights(weights, post_player_name)
            return self._weighted_choice(weights, play, "post_2pt")

        if result_type == "turnover":
            weights = [
                (POST_ACTION_BACK_DOWN, 0.48),
                (POST_ACTION_SEAL, 0.32),
                (POST_ACTION_KICKOUT, 0.20),
            ]
            weights = self._apply_big_archetype_weights(weights, post_player_name)
            return self._weighted_choice(weights, play, "post_turnover")

        return POST_ACTION_SEAL

    def choose_post_player(self, offense_team_side: Optional[str], focus_player_name: Optional[str], support_player_name: Optional[str]) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        for candidate in (focus_player_name, support_player_name):
            pos = self._extract_player_position_by_name(candidate)
            arch = self._extract_player_archetype_by_name(candidate)
            if candidate and (pos in {"PF", "C"} or arch in {"rim_protector", "rebounder", "stretch_big"}):
                return candidate

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "C":
                score += 38
            elif pos == "PF":
                score += 30
            elif pos == "SF":
                score += 8
            if arch == "rim_protector":
                score += 18
            elif arch == "rebounder":
                score += 16
            elif arch == "stretch_big":
                score += 12
            if score > 0:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_entry_passer(self, offense_team_side: Optional[str], post_player_name: Optional[str], ball_handler_name: Optional[str]) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        if ball_handler_name and ball_handler_name != post_player_name:
            return ball_handler_name
        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name == post_player_name:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "PG":
                score += 30
            elif pos == "SG":
                score += 18
            elif pos == "SF":
                score += 14
            if arch == "floor_general":
                score += 18
            elif arch == "playmaker":
                score += 16
            elif arch == "two_way_wing":
                score += 8
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_post_kickout_target(self, offense_team_side: Optional[str], post_player_name: Optional[str], entry_passer_name: Optional[str]) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None
        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name in {post_player_name, entry_passer_name}:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "SG":
                score += 24
            elif pos == "SF":
                score += 20
            elif pos == "PF":
                score += 10
            if arch == "scoring_guard":
                score += 18
            elif arch == "two_way_wing":
                score += 16
            elif arch == "stretch_big":
                score += 14
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def resolve_post_side(self, post_player_name: Optional[str], entry_passer_name: Optional[str], offense_direction: Optional[str]) -> str:
        seed_parts = [post_player_name or "", entry_passer_name or "", offense_direction or ""]
        total = sum(ord(ch) for ch in "|".join(seed_parts))
        return "left" if total % 2 == 0 else "right"

    def resolve_post_depth(self, post_player_name: Optional[str], post_action: Optional[str]) -> str:
        pos = self._extract_player_position_by_name(post_player_name)
        if post_action == POST_ACTION_SEAL:
            return "low"
        if pos == "PF" and post_action == POST_ACTION_KICKOUT:
            return "mid"
        return "low"


    def resolve_handoff_metadata(
        self,
        play: dict[str, Any],
        prev_play: Optional[dict[str, Any]],
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> dict[str, Optional[str]]:
        if structure_type != STRUCTURE_HANDOFF:
            return {
                "handoff_action": None,
                "handoff_giver_name": None,
                "handoff_receiver_name": None,
                "handoff_side": None,
                "handoff_lane": None,
                "handoff_kickout_target_name": None,
            }

        giver_name = self.choose_handoff_giver(
            offense_team_side=offense_team_side,
            focus_player_name=focus_player_name,
            support_player_name=support_player_name,
            ball_handler_name=ball_handler_name,
        )
        receiver_name = self.choose_handoff_receiver(
            offense_team_side=offense_team_side,
            giver_name=giver_name,
            focus_player_name=focus_player_name,
            support_player_name=support_player_name,
        )
        if not giver_name or not receiver_name or giver_name == receiver_name:
            return {
                "handoff_action": None,
                "handoff_giver_name": None,
                "handoff_receiver_name": None,
                "handoff_side": None,
                "handoff_lane": None,
                "handoff_kickout_target_name": None,
            }

        handoff_action = self.resolve_handoff_action(play=play, receiver_name=receiver_name)
        handoff_side = self.resolve_screen_side(
            primary_name=giver_name,
            secondary_name=receiver_name,
            offense_direction=offense_direction,
        )
        handoff_lane = self.resolve_handoff_lane(
            receiver_name=receiver_name,
            handoff_side=handoff_side,
            handoff_action=handoff_action,
        )
        handoff_kickout_target_name = None
        if handoff_action == HANDOFF_ACTION_KICKOUT:
            handoff_kickout_target_name = self.choose_handoff_kickout_target(
                offense_team_side=offense_team_side,
                giver_name=giver_name,
                receiver_name=receiver_name,
            )

        return {
            "handoff_action": handoff_action,
            "handoff_giver_name": giver_name,
            "handoff_receiver_name": receiver_name,
            "handoff_side": handoff_side,
            "handoff_lane": handoff_lane,
            "handoff_kickout_target_name": handoff_kickout_target_name,
        }

    def _is_handoff_play(self, play: dict[str, Any], prev_play: Optional[dict[str, Any]]) -> bool:
        if self._is_second_chance_play(play=play, prev_play=prev_play):
            return False
        if self._is_fast_break_play(play=play, prev_play=prev_play):
            return False
        if self._is_pick_and_roll_play(play=play, prev_play=prev_play):
            return False
        if self._is_off_ball_screen_play(play=play, prev_play=prev_play):
            return False
        if self._is_post_up_play(play=play, prev_play=prev_play):
            return False

        result_type = self._get_result_type(play)
        if result_type not in {
            "made_2", "miss_2", "made_3", "miss_3", "turnover",
            "miss_2_def_rebound", "miss_3_def_rebound",
            "miss_2_off_rebound", "miss_3_off_rebound",
        }:
            return False

        offense_team_side = self.resolve_offense_team_side(play)
        if offense_team_side not in {"home", "away"}:
            return False

        giver_name = self.choose_handoff_giver(
            offense_team_side=offense_team_side,
            focus_player_name=self.resolve_focus_player_name(play),
            support_player_name=self.resolve_support_player_name(play),
            ball_handler_name=self.resolve_ball_handler_name(play),
        )
        receiver_name = self.choose_handoff_receiver(
            offense_team_side=offense_team_side,
            giver_name=giver_name,
            focus_player_name=self.resolve_focus_player_name(play),
            support_player_name=self.resolve_support_player_name(play),
        )
        if not giver_name or not receiver_name or giver_name == receiver_name:
            return False

        giver_pos = self._extract_player_position_by_name(giver_name)
        giver_arch = self._extract_player_archetype_by_name(giver_name)
        receiver_pos = self._extract_player_position_by_name(receiver_name)
        receiver_arch = self._extract_player_archetype_by_name(receiver_name)

        score = 0.0
        if giver_pos in {"PG", "SF", "PF"}:
            score += 0.14
        if giver_arch in {"playmaker", "floor_general", "two_way_wing", "stretch_big"}:
            score += 0.16
        if receiver_pos in {"SG", "SF", "PG"}:
            score += 0.18
        if receiver_arch in {"scoring_guard", "slasher", "playmaker", "two_way_wing"}:
            score += 0.20

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            score += 0.10
        elif result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            score += 0.10
        elif result_type == "turnover":
            score += 0.04

        hashed_roll = self._stable_roll(play)
        return hashed_roll < min(0.42, max(0.14, score))

    def resolve_handoff_action(self, play: dict[str, Any], receiver_name: Optional[str]) -> str:
        result_type = self._get_result_type(play)

        if result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            weights = [
                (HANDOFF_ACTION_PULLUP, 0.42),
                (HANDOFF_ACTION_KICKOUT, 0.34),
                (HANDOFF_ACTION_RECEIVE, 0.24),
            ]
            weights = self._apply_handler_archetype_weights(weights, receiver_name)
            return self._weighted_choice(weights, play, "handoff_3pt")

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            weights = [
                (HANDOFF_ACTION_DRIVE, 0.42),
                (HANDOFF_ACTION_RECEIVE, 0.34),
                (HANDOFF_ACTION_SETUP, 0.24),
            ]
            weights = self._apply_handler_archetype_weights(weights, receiver_name)
            return self._weighted_choice(weights, play, "handoff_2pt")

        if result_type == "turnover":
            weights = [
                (HANDOFF_ACTION_RECEIVE, 0.46),
                (HANDOFF_ACTION_SETUP, 0.32),
                (HANDOFF_ACTION_DRIVE, 0.22),
            ]
            weights = self._apply_handler_archetype_weights(weights, receiver_name)
            return self._weighted_choice(weights, play, "handoff_turnover")

        return HANDOFF_ACTION_SETUP

    def choose_handoff_giver(
        self,
        offense_team_side: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
        ball_handler_name: Optional[str],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        for candidate in (ball_handler_name, support_player_name, focus_player_name):
            pos = self._extract_player_position_by_name(candidate)
            arch = self._extract_player_archetype_by_name(candidate)
            if candidate and (pos in {"PG", "SF", "PF"} or arch in {"playmaker", "floor_general", "two_way_wing", "stretch_big"}):
                return candidate

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "PG":
                score += 28
            elif pos == "SF":
                score += 18
            elif pos == "PF":
                score += 14
            if arch == "floor_general":
                score += 18
            elif arch == "playmaker":
                score += 16
            elif arch == "two_way_wing":
                score += 12
            elif arch == "stretch_big":
                score += 10
            if score > 0:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_handoff_receiver(
        self,
        offense_team_side: Optional[str],
        giver_name: Optional[str],
        focus_player_name: Optional[str],
        support_player_name: Optional[str],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        for candidate in (focus_player_name, support_player_name):
            if not candidate or candidate == giver_name:
                continue
            pos = self._extract_player_position_by_name(candidate)
            arch = self._extract_player_archetype_by_name(candidate)
            if pos in {"SG", "SF", "PG"} or arch in {"scoring_guard", "slasher", "playmaker", "two_way_wing"}:
                return candidate

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name == giver_name:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos == "SG":
                score += 28
            elif pos == "SF":
                score += 22
            elif pos == "PG":
                score += 16
            if arch == "scoring_guard":
                score += 18
            elif arch == "slasher":
                score += 16
            elif arch == "playmaker":
                score += 14
            elif arch == "two_way_wing":
                score += 12
            if score > 0:
                ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def choose_handoff_kickout_target(
        self,
        offense_team_side: Optional[str],
        giver_name: Optional[str],
        receiver_name: Optional[str],
    ) -> Optional[str]:
        if offense_team_side not in {"home", "away"}:
            return None

        ranked: list[tuple[int, str]] = []
        for player in self._get_team_player_objects(offense_team_side):
            name = self._extract_player_name(player)
            if not name or name in {giver_name, receiver_name}:
                continue
            pos = self._extract_player_position(player)
            arch = self._extract_player_archetype(player)
            score = 0
            if pos in {"SG", "SF"}:
                score += 20
            elif pos == "PF":
                score += 10
            if arch == "scoring_guard":
                score += 18
            elif arch == "two_way_wing":
                score += 16
            elif arch == "stretch_big":
                score += 14
            ranked.append((score, name))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def resolve_handoff_lane(
        self,
        receiver_name: Optional[str],
        handoff_side: Optional[str],
        handoff_action: Optional[str],
    ) -> str:
        receiver_pos = self._extract_player_position_by_name(receiver_name)
        receiver_arch = self._extract_player_archetype_by_name(receiver_name)

        if handoff_action == HANDOFF_ACTION_PULLUP:
            return "wing"
        if handoff_action == HANDOFF_ACTION_DRIVE:
            return "middle"
        if receiver_pos == "PG":
            return "slot"
        if receiver_arch in {"scoring_guard", "two_way_wing"}:
            return "wing"
        return "slot"


    def _weighted_choice(
        self,
        weighted_items: list[tuple[str, float]],
        play: dict[str, Any],
        salt: str,
    ) -> str:
        valid_items = [(name, max(0.0, float(weight))) for name, weight in weighted_items if weight > 0]
        if not valid_items:
            return weighted_items[0][0] if weighted_items else ""

        total_weight = sum(weight for _, weight in valid_items)
        if total_weight <= 0:
            return valid_items[0][0]

        raw = "|".join([
            salt,
            str(play.get("quarter", "")),
            str(play.get("clock_seconds", play.get("start_clock_seconds", ""))),
            str(play.get("result_type", "")),
            str(play.get("primary_player_name", "")),
            str(play.get("secondary_player_name", "")),
        ])
        threshold = (sum(ord(ch) for ch in raw) % 10000) / 10000.0 * total_weight

        running = 0.0
        for name, weight in valid_items:
            running += weight
            if threshold <= running:
                return name
        return valid_items[-1][0]

    def _apply_handler_archetype_weights(
        self,
        weighted_items: list[tuple[str, float]],
        handler_name: Optional[str],
    ) -> list[tuple[str, float]]:
        arch = self._extract_player_archetype_by_name(handler_name)
        adjusted: list[tuple[str, float]] = []
        for action, weight in weighted_items:
            new_weight = weight
            if arch in {"playmaker", "floor_general"}:
                if action in {"setup", "kickout"}:
                    new_weight += 0.22
                if action in {"drive", "pullup", "roll"}:
                    new_weight -= 0.04
            elif arch == "scoring_guard":
                if action in {"pullup", "catch_shoot", "receive"}:
                    new_weight += 0.22
                if action in {"setup"}:
                    new_weight -= 0.03
            elif arch == "slasher":
                if action in {"drive", "cut", "roll"}:
                    new_weight += 0.22
                if action in {"kickout", "pullup"}:
                    new_weight -= 0.03
            elif arch == "two_way_wing":
                if action in {"catch", "catch_shoot", "kickout", "receive"}:
                    new_weight += 0.14
            adjusted.append((action, max(0.01, new_weight)))
        return adjusted

    def _apply_big_archetype_weights(
        self,
        weighted_items: list[tuple[str, float]],
        big_name: Optional[str],
    ) -> list[tuple[str, float]]:
        arch = self._extract_player_archetype_by_name(big_name)
        adjusted: list[tuple[str, float]] = []
        for action, weight in weighted_items:
            new_weight = weight
            if arch in {"rim_protector", "rebounder"}:
                if action in {"roll", "seal", "back_down"}:
                    new_weight += 0.22
                if action in {"kickout", "pullup"}:
                    new_weight -= 0.04
            elif arch == "stretch_big":
                if action in {"kickout", "catch_shoot"}:
                    new_weight += 0.22
                if action in {"roll", "seal"}:
                    new_weight -= 0.03
            adjusted.append((action, max(0.01, new_weight)))
        return adjusted

    def _get_result_type(self, play: Optional[dict[str, Any]]) -> str:
        if not isinstance(play, dict):
            return ""
        value = play.get("result_type")
        return value if isinstance(value, str) else ""

    def _stable_roll(self, play: dict[str, Any]) -> float:
        raw = "|".join([
            str(play.get("quarter", "")),
            str(play.get("clock_seconds", play.get("start_clock_seconds", ""))),
            str(play.get("result_type", "")),
            str(play.get("primary_player_name", "")),
            str(play.get("secondary_player_name", "")),
        ])
        total = sum(ord(ch) for ch in raw)
        return (total % 100) / 100.0

    def _result_type_is_drive_like(self, play: dict[str, Any]) -> bool:
        return self._get_result_type(play) in {"made_2", "miss_2", "turnover", "miss_2_def_rebound", "miss_2_off_rebound"}

    def _infer_player_team_side(self, player_name: str) -> Optional[str]:
        if not isinstance(player_name, str) or not player_name.strip():
            return None
        home_names = self._get_team_all_player_names("home")
        away_names = self._get_team_all_player_names("away")
        if player_name in home_names:
            return "home"
        if player_name in away_names:
            return "away"
        return None

    def _get_team_all_player_names(self, side: str) -> list[str]:
        names: list[str] = []
        for player in self._get_team_player_objects(side):
            name = self._extract_player_name(player)
            if name and name != "-" and name not in names:
                names.append(name)
        return names

    def _get_team_player_objects(self, side: str) -> list[Any]:
        team_obj = getattr(self.match, "home_team" if side == "home" else "away_team", None)
        if team_obj is None:
            return []
        for attr in ("active_players", "rotation_players", "players"):
            players = getattr(team_obj, attr, None)
            if isinstance(players, list) and players:
                return players
        return []

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

    def _extract_player_position(self, player: Any) -> str:
        if player is None or isinstance(player, str):
            return ""
        value = getattr(player, "position", "")
        return value if isinstance(value, str) else ""

    def _extract_player_archetype(self, player: Any) -> str:
        if player is None or isinstance(player, str):
            return ""
        value = getattr(player, "archetype", "")
        return value if isinstance(value, str) else ""

    def _find_player_object_by_name(self, player_name: Optional[str]) -> Optional[Any]:
        if not player_name:
            return None
        for side in ("home", "away"):
            for player in self._get_team_player_objects(side):
                if self._extract_player_name(player) == player_name:
                    return player
        return None

    def _extract_player_position_by_name(self, player_name: Optional[str]) -> str:
        return self._extract_player_position(self._find_player_object_by_name(player_name))

    def _extract_player_archetype_by_name(self, player_name: Optional[str]) -> str:
        return self._extract_player_archetype(self._find_player_object_by_name(player_name))


class FormationFactory:
    """Provides safe initial formation / spacing metadata."""

    def resolve_formation_name(self, structure_type: str) -> str:
        if structure_type == STRUCTURE_FAST_BREAK:
            return FORMATION_TRANSITION_LANES
        if structure_type == STRUCTURE_SECOND_CHANCE:
            return FORMATION_REBOUND_RESET
        if structure_type == STRUCTURE_PICK_AND_ROLL:
            return FORMATION_PICK_AND_ROLL
        if structure_type == STRUCTURE_SPAIN_PICK_AND_ROLL:
            return FORMATION_SPAIN_PICK_AND_ROLL
        if structure_type == STRUCTURE_OFF_BALL_SCREEN:
            return FORMATION_OFF_BALL_SCREEN
        if structure_type == STRUCTURE_POST_UP:
            return FORMATION_POST_UP
        if structure_type == STRUCTURE_HANDOFF:
            return FORMATION_HANDOFF
        if structure_type == STRUCTURE_ISOLATION:
            return FORMATION_ISOLATION
        return FORMATION_4_OUT_1_IN

    def resolve_spacing_profile(self, structure_type: str) -> str:
        if structure_type == STRUCTURE_FAST_BREAK:
            return SPACING_WIDE
        if structure_type == STRUCTURE_SECOND_CHANCE:
            return SPACING_COLLAPSE
        if structure_type == STRUCTURE_SPAIN_PICK_AND_ROLL:
            return SPACING_WIDE
        if structure_type == STRUCTURE_OFF_BALL_SCREEN:
            return SPACING_WIDE
        if structure_type == STRUCTURE_POST_UP:
            return SPACING_STANDARD
        if structure_type == STRUCTURE_HANDOFF:
            return SPACING_STANDARD
        if structure_type == STRUCTURE_ISOLATION:
            return SPACING_WIDE
        return SPACING_STANDARD

    def resolve_tempo_profile(self, structure_type: str) -> str:
        if structure_type == STRUCTURE_FAST_BREAK:
            return "push"
        if structure_type == STRUCTURE_SECOND_CHANCE:
            return "scramble"
        if structure_type == STRUCTURE_PICK_AND_ROLL:
            return "probe"
        if structure_type == STRUCTURE_SPAIN_PICK_AND_ROLL:
            return "layered_probe"
        if structure_type == STRUCTURE_OFF_BALL_SCREEN:
            return "flow"
        if structure_type == STRUCTURE_POST_UP:
            return "grind"
        if structure_type == STRUCTURE_HANDOFF:
            return "flow"
        if structure_type == STRUCTURE_ISOLATION:
            return "deliberate"
        return "normal"

    def build_lane_map(
        self,
        structure_type: str,
        offense_team_side: Optional[str],
        offense_direction: Optional[str],
        pnr_action: Optional[str] = None,
        spain_action: Optional[str] = None,
        screen_side: Optional[str] = None,
        screen_action: Optional[str] = None,
        cut_lane: Optional[str] = None,
        post_action: Optional[str] = None,
        post_side: Optional[str] = None,
        handoff_action: Optional[str] = None,
        handoff_side: Optional[str] = None,
        handoff_lane: Optional[str] = None,
        spain_screen_side: Optional[str] = None,
        transition_action: Optional[str] = None,
    ) -> dict[str, str]:
        _ = offense_team_side
        _ = offense_direction
        if structure_type == STRUCTURE_FAST_BREAK:
            return self._build_fast_break_lane_map(transition_action=transition_action)
        if structure_type == STRUCTURE_SECOND_CHANCE:
            return self._build_second_chance_lane_map()
        if structure_type == STRUCTURE_PICK_AND_ROLL:
            return self._build_pick_and_roll_lane_map(pnr_action=pnr_action, screen_side=screen_side)
        if structure_type == STRUCTURE_SPAIN_PICK_AND_ROLL:
            return self._build_spain_pick_and_roll_lane_map(spain_action=spain_action, screen_side=spain_screen_side or screen_side)
        if structure_type == STRUCTURE_OFF_BALL_SCREEN:
            return self._build_off_ball_screen_lane_map(screen_action=screen_action, screen_side=screen_side, cut_lane=cut_lane)
        if structure_type == STRUCTURE_POST_UP:
            return self._build_post_up_lane_map(post_action=post_action, post_side=post_side)
        if structure_type == STRUCTURE_HANDOFF:
            return self._build_handoff_lane_map(handoff_action=handoff_action, handoff_side=handoff_side, handoff_lane=handoff_lane)
        if structure_type == STRUCTURE_ISOLATION:
            return self._build_isolation_lane_map()
        return self._build_half_court_lane_map()

    def _build_half_court_lane_map(self) -> dict[str, str]:
        return {
            "PG": "top",
            "SG": "left_wing",
            "SF": "right_wing",
            "PF": "left_elbow",
            "C": "right_low_post",
        }

    def _build_fast_break_lane_map(self, transition_action: Optional[str] = None) -> dict[str, str]:
        if transition_action == TRANSITION_ACTION_COUNTER:
            return {
                "PG": "center_burst",
                "SG": "left_lane_fill",
                "SF": "right_lane_fill",
                "PF": "rim_runner",
                "C": "deep_trailer",
            }
        return {
            "PG": "center_push",
            "SG": "left_lane",
            "SF": "right_lane",
            "PF": "trailer_left",
            "C": "trailer_right",
        }

    def _build_second_chance_lane_map(self) -> dict[str, str]:
        return {
            "PG": "reset_top",
            "SG": "left_slot",
            "SF": "right_slot",
            "PF": "dunker_left",
            "C": "dunker_right",
        }

    def _build_pick_and_roll_lane_map(self, pnr_action: Optional[str], screen_side: Optional[str]) -> dict[str, str]:
        side = screen_side or "middle"
        if pnr_action == PNR_ACTION_DRIVE:
            return {
                "PG": "top_drive",
                "SG": "weakside_wing",
                "SF": "corner_space",
                "PF": "screen_slot_left" if side != "right" else "screen_slot_right",
                "C": "roll_lane",
            }
        if pnr_action in {PNR_ACTION_ROLL, PNR_ACTION_DIVE}:
            return {
                "PG": "top_probe",
                "SG": "lift_left",
                "SF": "lift_right",
                "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
                "C": "deep_roll",
            }
        if pnr_action == PNR_ACTION_KICKOUT:
            return {
                "PG": "top_probe",
                "SG": "kickout_left",
                "SF": "kickout_right",
                "PF": "short_roll",
                "C": "dunker_right",
            }
        if pnr_action == PNR_ACTION_PULLUP:
            return {
                "PG": "pullup_top",
                "SG": "left_space",
                "SF": "right_space",
                "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
                "C": "roll_hold",
            }
        if pnr_action == PNR_ACTION_POP:
            return {
                "PG": "top_probe",
                "SG": "weakside_wing",
                "SF": "corner_space",
                "PF": "pop_window_left" if side != "right" else "pop_window_right",
                "C": "dunker_right" if side != "right" else "dunker_left",
            }
        return {
            "PG": "top_probe",
            "SG": "left_space",
            "SF": "right_space",
            "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
            "C": "weakside_dunker",
        }


    def _build_isolation_lane_map(self) -> dict[str, str]:
        return {
            "PG": "top_hold",
            "SG": "left_corner_space",
            "SF": "right_corner_space",
            "PF": "left_wing_space",
            "C": "right_wing_space",
        }

    def _build_spain_pick_and_roll_lane_map(self, spain_action: Optional[str], screen_side: Optional[str]) -> dict[str, str]:
        side = screen_side or "middle"
        if spain_action == SPAIN_ACTION_ROLL:
            return {
                "PG": "top_probe",
                "SG": "back_screen_left" if side != "right" else "back_screen_right",
                "SF": "weakside_space",
                "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
                "C": "deep_roll",
            }
        if spain_action == SPAIN_ACTION_KICKOUT:
            return {
                "PG": "top_probe",
                "SG": "kickout_window_left" if side != "right" else "kickout_window_right",
                "SF": "weakside_corner_space",
                "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
                "C": "roll_hold",
            }
        if spain_action == SPAIN_ACTION_PULLUP:
            return {
                "PG": "pullup_top",
                "SG": "back_screen_left" if side != "right" else "back_screen_right",
                "SF": "weakside_space",
                "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
                "C": "roll_hold",
            }
        return {
            "PG": "top_probe",
            "SG": "back_screen_left" if side != "right" else "back_screen_right",
            "SF": "weakside_space",
            "PF": "screen_contact_left" if side != "right" else "screen_contact_right",
            "C": "deep_roll",
        }

    def _build_off_ball_screen_lane_map(self, screen_action: Optional[str], screen_side: Optional[str], cut_lane: Optional[str]) -> dict[str, str]:
        side = screen_side or "left"
        lane = cut_lane or "wing"
        if screen_action == SCREEN_ACTION_CATCH_SHOOT:
            return {
                "PG": "top_hold",
                "SG": "screen_target_left" if side != "right" else "screen_target_right",
                "SF": "catch_shoot_left" if side != "right" else "catch_shoot_right",
                "PF": "screen_set_left" if side != "right" else "screen_set_right",
                "C": "dunker_right" if side != "right" else "dunker_left",
            }
        if screen_action == SCREEN_ACTION_CUT:
            return {
                "PG": "top_hold",
                "SG": "screen_target_left" if side != "right" else "screen_target_right",
                "SF": "baseline_cut" if lane == "baseline" else "middle_cut",
                "PF": "screen_set_left" if side != "right" else "screen_set_right",
                "C": "weakside_dunker",
            }
        if screen_action == SCREEN_ACTION_CATCH:
            return {
                "PG": "top_hold",
                "SG": "catch_window_left" if side != "right" else "catch_window_right",
                "SF": "lift_right" if side != "right" else "lift_left",
                "PF": "screen_set_left" if side != "right" else "screen_set_right",
                "C": "low_anchor",
            }
        return {
            "PG": "top_hold",
            "SG": "screen_target_left" if side != "right" else "screen_target_right",
            "SF": "wing_hold_right" if side != "right" else "wing_hold_left",
            "PF": "screen_set_left" if side != "right" else "screen_set_right",
            "C": "low_anchor",
        }

    def _build_post_up_lane_map(self, post_action: Optional[str], post_side: Optional[str]) -> dict[str, str]:
        side = post_side or "left"
        strong_low = "left_low_post" if side != "right" else "right_low_post"
        strong_mid = "left_mid_post" if side != "right" else "right_mid_post"
        weak_corner = "right_corner_space" if side != "right" else "left_corner_space"
        strong_wing = "left_wing_entry" if side != "right" else "right_wing_entry"
        weak_wing = "right_wing_space" if side != "right" else "left_wing_space"
        if post_action == POST_ACTION_KICKOUT:
            return {
                "PG": "top_hold",
                "SG": strong_wing,
                "SF": weak_corner,
                "PF": strong_mid,
                "C": strong_low,
            }
        if post_action == POST_ACTION_TURN_SHOOT:
            return {
                "PG": "top_hold",
                "SG": strong_wing,
                "SF": weak_wing,
                "PF": strong_mid,
                "C": strong_low,
            }
        if post_action == POST_ACTION_BACK_DOWN:
            return {
                "PG": "top_hold",
                "SG": strong_wing,
                "SF": weak_corner,
                "PF": strong_mid,
                "C": strong_low,
            }
        return {
            "PG": "top_hold",
            "SG": strong_wing,
            "SF": weak_wing,
            "PF": strong_mid,
            "C": strong_low,
        }




    def _build_handoff_lane_map(
        self,
        handoff_action: Optional[str],
        handoff_side: Optional[str],
        handoff_lane: Optional[str],
    ) -> dict[str, str]:
        side = handoff_side or "left"
        lane = handoff_lane or "slot"
        giver_slot = "left_slot" if side != "right" else "right_slot"
        receiver_wing = "left_wing" if side != "right" else "right_wing"
        receiver_slot = "left_slot" if side != "right" else "right_slot"
        weak_wing = "right_wing" if side != "right" else "left_wing"
        weak_corner = "right_corner_space" if side != "right" else "left_corner_space"
        strong_corner = "left_corner_space" if side != "right" else "right_corner_space"

        if handoff_action == HANDOFF_ACTION_DRIVE:
            return {
                "PG": giver_slot,
                "SG": "drive_lane",
                "SF": weak_wing,
                "PF": strong_corner,
                "C": "dunker_right" if side != "right" else "dunker_left",
            }
        if handoff_action == HANDOFF_ACTION_PULLUP:
            return {
                "PG": giver_slot,
                "SG": "pullup_left" if side != "right" else "pullup_right",
                "SF": weak_corner,
                "PF": strong_corner,
                "C": "low_anchor",
            }
        if handoff_action == HANDOFF_ACTION_KICKOUT:
            return {
                "PG": giver_slot,
                "SG": receiver_wing,
                "SF": weak_corner,
                "PF": "kickout_slot_right" if side != "right" else "kickout_slot_left",
                "C": "low_anchor",
            }
        if handoff_action == HANDOFF_ACTION_RECEIVE:
            return {
                "PG": giver_slot,
                "SG": receiver_slot if lane == "slot" else receiver_wing,
                "SF": weak_wing,
                "PF": strong_corner,
                "C": "low_anchor",
            }
        return {
            "PG": giver_slot,
            "SG": receiver_slot if lane == "slot" else receiver_wing,
            "SF": weak_wing,
            "PF": strong_corner,
            "C": "low_anchor",
        }


def build_play_structure_events(match: Any) -> list[dict[str, Any]]:
    return PlayStructureLayer(match=match).build()


if __name__ == "__main__":
    print(
        "This module is a systems layer. Import PlayStructureLayer or "
        "build_play_structure_events(match)."
    )
