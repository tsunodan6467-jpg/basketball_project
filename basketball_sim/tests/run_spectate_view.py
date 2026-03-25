from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# ------------------------------------------------------------
# Import path fix
# ------------------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
PACKAGE_ROOT = CURRENT_FILE.parents[1]

for path in (PROJECT_ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

from basketball_sim.models.match import Match
from basketball_sim.systems.generator import generate_teams
from basketball_sim.systems.play_structure import PlayStructureLayer
from basketball_sim.systems.presentation_layer import PresentationLayer
from basketball_sim.systems.highlight_camera_system import HighlightCameraSystem
from basketball_sim.systems.highlight_selector import HighlightSelector
from basketball_sim.systems.spectate_view import run_spectate_view


# ------------------------------------------------------------
# Spectate mode settings
# ------------------------------------------------------------
SPECTATE_MODE = "highlight"  # "full" | "highlight" | "result_only"

# highlight mode
HIGHLIGHT_TOP_N = 30
HIGHLIGHT_MIN_SCORE = 20
HIGHLIGHT_TIMELINE_MODE = True
HIGHLIGHT_ADD_INTRO_OUTRO = True

# result only mode
RESULT_ONLY_USE_FALLBACK_FULL = True


def _pick_two_teams():
    teams = generate_teams()
    if not teams or len(teams) < 2:
        raise RuntimeError("チーム生成に失敗しました。2チーム以上必要です。")
    return teams[0], teams[1]


def _print_tempo_shot_summary(match: Match) -> None:
    plays = []
    if hasattr(match, "get_play_sequence_log"):
        got = match.get_play_sequence_log()
        if got is not None:
            plays = list(got)
    if not plays:
        plays = list(getattr(match, "play_sequence_log", []) or [])

    def _infer_team_side_from_name(player_name: object) -> str | None:
        if not isinstance(player_name, str) or not player_name.strip():
            return None

        for player in (getattr(getattr(match, "home_team", None), "active_players", []) or []):
            if getattr(player, "name", None) == player_name:
                return "home"
        for player in (getattr(getattr(match, "away_team", None), "active_players", []) or []):
            if getattr(player, "name", None) == player_name:
                return "away"
        return None

    two_pa = two_pm = 0
    three_pa = three_pm = 0
    fta = ftm = 0
    quarter_points = defaultdict(lambda: {"home": 0, "away": 0, "plays": 0})
    quarter_event_counts = defaultdict(dict)

    for play in plays:
        if not isinstance(play, dict):
            continue

        quarter = play.get("quarter")
        result_type = str(play.get("result_type", ""))
        scoring_team = play.get("scoring_team")
        points = int(play.get("points", 0) or 0)

        if points <= 0:
            if result_type == "made_2":
                points = 2
            elif result_type == "made_3":
                points = 3
            elif result_type == "made_ft":
                points = 1

        if scoring_team not in {"home", "away"}:
            team_side = play.get("team")
            if team_side in {"home", "away"}:
                scoring_team = team_side

        if scoring_team not in {"home", "away"}:
            primary_side = _infer_team_side_from_name(play.get("primary_player_name"))
            secondary_side = _infer_team_side_from_name(play.get("secondary_player_name"))
            scoring_team = primary_side or secondary_side

        if isinstance(quarter, int):
            quarter_points[quarter]["plays"] += 1
            q_events = quarter_event_counts[quarter]
            q_events[result_type] = q_events.get(result_type, 0) + 1
            if scoring_team in {"home", "away"} and points > 0:
                quarter_points[quarter][scoring_team] += points

        if result_type in {"made_2", "miss_2", "miss_2_def_rebound", "miss_2_off_rebound"}:
            two_pa += 1
            if result_type == "made_2":
                two_pm += 1
        elif result_type in {"made_3", "miss_3", "miss_3_def_rebound", "miss_3_off_rebound"}:
            three_pa += 1
            if result_type == "made_3":
                three_pm += 1
        elif result_type in {"made_ft", "miss_ft", "miss_ft_def_rebound"}:
            fta += 1
            if result_type == "made_ft":
                ftm += 1

    def _pct(made: int, att: int) -> str:
        if att <= 0:
            return "0.0%"
        return f"{(made / att) * 100:.1f}%"

    print("[TEMPO] Shot Summary")
    print(f"[TEMPO] 2PA={two_pa} | 2PM={two_pm} | 2P%={_pct(two_pm, two_pa)}")
    print(f"[TEMPO] 3PA={three_pa} | 3PM={three_pm} | 3P%={_pct(three_pm, three_pa)}")
    print(f"[TEMPO] FTA={fta} | FTM={ftm} | FT%={_pct(ftm, fta)}")

    print("[TEMPO] Quarter Summary")
    for quarter in sorted(quarter_points.keys()):
        summary = quarter_points[quarter]
        events = quarter_event_counts.get(quarter, {})
        q2pa = (
            events.get("made_2", 0)
            + events.get("miss_2", 0)
            + events.get("miss_2_def_rebound", 0)
            + events.get("miss_2_off_rebound", 0)
        )
        q3pa = (
            events.get("made_3", 0)
            + events.get("miss_3", 0)
            + events.get("miss_3_def_rebound", 0)
            + events.get("miss_3_off_rebound", 0)
        )
        qto = events.get("turnover", 0)
        print(
            f"[TEMPO] Q{quarter} | "
            f"home={summary['home']} | away={summary['away']} | plays={summary['plays']} | "
            f"2PA={q2pa} | 3PA={q3pa} | TO={qto}"
        )


def _build_quarter_score_summary(match: Match) -> list[dict]:
    plays = []
    if hasattr(match, "get_play_sequence_log"):
        got = match.get_play_sequence_log()
        if got is not None:
            plays = list(got)
    if not plays:
        plays = list(getattr(match, "play_sequence_log", []) or [])

    quarter_points = defaultdict(lambda: {"home": 0, "away": 0})
    prev_home_score = 0
    prev_away_score = 0

    for play in plays:
        if not isinstance(play, dict):
            continue

        quarter = play.get("quarter")
        if not isinstance(quarter, int):
            continue

        home_score = play.get("home_score")
        away_score = play.get("away_score")

        if not isinstance(home_score, int):
            home_score = prev_home_score
        if not isinstance(away_score, int):
            away_score = prev_away_score

        home_delta = max(0, home_score - prev_home_score)
        away_delta = max(0, away_score - prev_away_score)

        prev_home_score = home_score
        prev_away_score = away_score

        quarter_points[quarter]["home"] += home_delta
        quarter_points[quarter]["away"] += away_delta

    summary: list[dict] = []
    for quarter in sorted(quarter_points.keys()):
        summary.append(
            {
                "quarter": quarter,
                "home": quarter_points[quarter]["home"],
                "away": quarter_points[quarter]["away"],
            }
        )
    return summary


def _build_highlight_intro_event(match: Match, highlight_events: list[dict]) -> dict:
    home_name = getattr(getattr(match, "home_team", None), "name", "HOME")
    away_name = getattr(getattr(match, "away_team", None), "name", "AWAY")
    count = len(highlight_events)

    first_event = highlight_events[0] if highlight_events else {}
    quarter = first_event.get("quarter", 1)
    clock_seconds = first_event.get("clock_seconds", 600)

    return {
        "play_no": -2,
        "quarter": quarter,
        "clock_seconds": clock_seconds,
        "home_score": 0,
        "away_score": 0,
        "presentation_type": "highlight_intro",
        "source_result_type": "highlight_intro",
        "headline": "本日のハイライト",
        "main_text": f"{home_name} VS {away_name} の見どころをお届けします。",
        "sub_text": f"注目プレー {count} 本をダイジェストで再生します。",
        "focus_player_name": None,
        "support_player_name": None,
        "team_side": None,
        "importance": "high",
        "highlight_score": 100,
        "highlight_tags": ["highlight_intro"],
        "raw_play": {
            "play_no": -2,
            "result_type": "highlight_intro",
            "quarter": quarter,
            "start_clock_seconds": clock_seconds,
            "end_clock_seconds": clock_seconds,
            "home_score": 0,
            "away_score": 0,
            "commentary_text": f"{home_name} VS {away_name} ハイライト開始",
        },
        "structure_type": "highlight_package",
        "offense_team_side": None,
        "defense_team_side": None,
        "offense_direction": None,
        "formation_name": None,
        "spacing_profile": "standard",
        "tempo_profile": None,
        "ball_handler_name": None,
        "pnr_action": None,
        "screener_name": None,
        "roller_name": None,
        "kickout_target_name": None,
        "screen_side": None,
        "drive_lane": None,
        "screen_action": None,
        "target_name": None,
        "cut_lane": None,
        "post_action": None,
        "post_player_name": None,
        "entry_passer_name": None,
        "post_kickout_target_name": None,
        "post_side": None,
        "post_depth": None,
        "handoff_action": None,
        "handoff_giver_name": None,
        "handoff_receiver_name": None,
        "handoff_side": None,
        "spain_action": None,
        "back_screener_name": None,
        "back_screen_target_name": None,
        "spain_kickout_target_name": None,
        "lane_map": {},
        "structure_raw": None,
    }


def _build_highlight_outro_event(match: Match, highlight_events: list[dict]) -> dict:
    home_name = getattr(getattr(match, "home_team", None), "name", "HOME")
    away_name = getattr(getattr(match, "away_team", None), "name", "AWAY")
    home_score = getattr(match, "home_score", 0)
    away_score = getattr(match, "away_score", 0)
    quarter_score_summary = _build_quarter_score_summary(match)

    if home_score > away_score:
        winner_text = f"{home_name} が勝利しました。"
    elif away_score > home_score:
        winner_text = f"{away_name} が勝利しました。"
    else:
        winner_text = "引き分けです。"

    diff = abs(home_score - away_score)
    if diff == 1:
        result_flavor = "最後まで手に汗握る大接戦でした。"
    elif diff <= 5:
        result_flavor = "僅差の決着となりました。"
    else:
        result_flavor = "終盤まで見どころの多い試合でした。"

    last_event = highlight_events[-1] if highlight_events else {}
    quarter = last_event.get("quarter", 4)
    clock_seconds = last_event.get("clock_seconds", 0)

    return {
        "play_no": 10**9,
        "quarter": quarter,
        "clock_seconds": clock_seconds,
        "home_score": home_score,
        "away_score": away_score,
        "presentation_type": "highlight_outro",
        "source_result_type": "highlight_outro",
        "headline": "ハイライト終了",
        "main_text": f"試合終了。{winner_text}",
        "sub_text": f"最終スコア {home_name} {home_score} - {away_score} {away_name}。{result_flavor}",
        "focus_player_name": None,
        "support_player_name": None,
        "team_side": None,
        "importance": "high",
        "highlight_score": 100,
        "highlight_tags": ["highlight_outro"],
        "quarter_score_summary": quarter_score_summary,
        "raw_play": {
            "play_no": 10**9,
            "result_type": "highlight_outro",
            "quarter": quarter,
            "start_clock_seconds": clock_seconds,
            "end_clock_seconds": clock_seconds,
            "home_score": home_score,
            "away_score": away_score,
            "commentary_text": f"試合終了 {home_name} {home_score}-{away_score} {away_name}",
        },
        "structure_type": "highlight_package",
        "offense_team_side": None,
        "defense_team_side": None,
        "offense_direction": None,
        "formation_name": None,
        "spacing_profile": "standard",
        "tempo_profile": None,
        "ball_handler_name": None,
        "pnr_action": None,
        "screener_name": None,
        "roller_name": None,
        "kickout_target_name": None,
        "screen_side": None,
        "drive_lane": None,
        "screen_action": None,
        "target_name": None,
        "cut_lane": None,
        "post_action": None,
        "post_player_name": None,
        "entry_passer_name": None,
        "post_kickout_target_name": None,
        "post_side": None,
        "post_depth": None,
        "handoff_action": None,
        "handoff_giver_name": None,
        "handoff_receiver_name": None,
        "handoff_side": None,
        "spain_action": None,
        "back_screener_name": None,
        "back_screen_target_name": None,
        "spain_kickout_target_name": None,
        "lane_map": {},
        "structure_raw": None,
    }


def _wrap_highlight_events_with_intro_outro(match: Match, highlight_events: list[dict]) -> list[dict]:
    if not HIGHLIGHT_ADD_INTRO_OUTRO:
        return list(highlight_events)

    if not highlight_events:
        return []

    intro_event = _build_highlight_intro_event(match, highlight_events)
    outro_event = _build_highlight_outro_event(match, highlight_events)

    wrapped = [intro_event]
    wrapped.extend(highlight_events)
    wrapped.append(outro_event)

    print("[Spectate Test] highlight intro/outro を追加しました。")
    return wrapped


def _select_full_events(presentation_events: list[dict]) -> list[dict]:
    print("[Spectate Test] spectate_mode=FULL")
    return list(presentation_events)


def _select_highlight_events(match: Match, presentation_events: list[dict]) -> list[dict]:
    selector = HighlightSelector(presentation_events)

    if HIGHLIGHT_TIMELINE_MODE:
        highlight_events = selector.select_highlights_timeline(
            top_n=HIGHLIGHT_TOP_N,
            min_score=HIGHLIGHT_MIN_SCORE,
        )
        mode_label = "timeline"
    else:
        highlight_events = selector.select_highlights(
            top_n=HIGHLIGHT_TOP_N,
            min_score=HIGHLIGHT_MIN_SCORE,
        )
        mode_label = "top_score"

    print("[Spectate Test] spectate_mode=HIGHLIGHT")
    print(f"[Spectate Test] highlight_mode_type={mode_label}")
    print(f"[Spectate Test] highlight_top_n={HIGHLIGHT_TOP_N}")
    print(f"[Spectate Test] highlight_min_score={HIGHLIGHT_MIN_SCORE}")
    print(f"[Spectate Test] raw_highlight_count={len(highlight_events)}")

    if not highlight_events:
        print("[Spectate Test] ハイライトが0件だったため、フル試合再生にフォールバックします。")
        return list(presentation_events)

    wrapped_events = _wrap_highlight_events_with_intro_outro(match, highlight_events)

    print(f"[Spectate Test] wrapped_highlight_count={len(wrapped_events)}")
    print("[Spectate Test] highlight_preview")
    preview_count = min(12, len(wrapped_events))
    for event in wrapped_events[:preview_count]:
        print(
            f"  Play#{event.get('play_no', '-'):>6} | "
            f"{event.get('presentation_type', '-'):<18} | "
            f"score={event.get('highlight_score', 0):>3} | "
            f"{event.get('headline', '-')}"
        )

    return list(wrapped_events)


def _wrap_result_only_events_with_outro(match: Match, result_events: list[dict]) -> list[dict]:
    if not result_events:
        return []

    outro_event = _build_highlight_outro_event(match, result_events)

    wrapped = list(result_events)
    wrapped.append(outro_event)

    print("[Spectate Test] result_only outro を追加しました。")
    return wrapped


def _select_result_only_events(match: Match, presentation_events: list[dict]) -> list[dict]:
    """
    result_only モード

    - 全プレーを再生対象にする
    - 実際の超高速・簡易描画は spectate_view.py 側で分岐
    - 試合終了後に結果演出へ自動遷移するため、最後に outro を1件追加
    """
    print("[Spectate Test] spectate_mode=RESULT_ONLY")
    print("[Spectate Test] result_only は全プレーを超高速・簡易描画で再生します。")

    wrapped_events = _wrap_result_only_events_with_outro(match, list(presentation_events))
    print(f"[Spectate Test] result_only_count={len(wrapped_events)}")
    return wrapped_events

def _select_spectate_events(match: Match, presentation_events: list[dict]) -> list[dict]:
    mode = str(SPECTATE_MODE).strip().lower()

    if mode == "full":
        return _select_full_events(presentation_events)

    if mode == "highlight":
        return _select_highlight_events(match, presentation_events)

    if mode == "result_only":
        return _select_result_only_events(match, presentation_events)

    raise RuntimeError(f"未知の SPECTATE_MODE です: {SPECTATE_MODE}")


def main() -> None:
    configure_console_encoding()
    print("[Spectate Test] 2D観戦テストを開始します。")

    home_team, away_team = _pick_two_teams()
    print(f"[Spectate Test] HOME: {getattr(home_team, 'name', 'HOME')}")
    print(f"[Spectate Test] AWAY: {getattr(away_team, 'name', 'AWAY')}")

    match = Match(home_team=home_team, away_team=away_team)
    match.simulate()

    # ------------------------------------------------------------
    # Structure Debug
    # ------------------------------------------------------------
    structure_layer = PlayStructureLayer(match)
    structure_layer.build()
    structure_layer.print_preview()
    structure_layer.print_handoff_preview()
    structure_layer.print_action_preview()

    # ------------------------------------------------------------
    # Presentation Debug
    # ------------------------------------------------------------
    presentation_layer = PresentationLayer(match)
    presentation_events = presentation_layer.build()
    presentation_layer.print_preview()

    print(f"[Spectate Test] presentation_event_count={len(presentation_events)}")
    if len(presentation_events) == 0:
        raise RuntimeError("presentation_event_count が 0 です。presentation_layer.py 側を確認してください。")

    spectate_events = _select_spectate_events(match, presentation_events)
    print(f"[Spectate Test] spectate_event_count={len(spectate_events)}")

    # ------------------------------------------------------------
    # Highlight Camera Debug
    # ------------------------------------------------------------
    camera_system = HighlightCameraSystem(spectate_events)
    camera_events = camera_system.build()
    camera_system.print_preview(limit=10)

    print(f"[Spectate Test] camera_event_count={len(camera_events)}")
    if len(camera_events) == 0:
        raise RuntimeError("camera_event_count が 0 です。highlight_camera_system.py 側を確認してください。")

    # ------------------------------------------------------------
    # Tempo Debug
    # ------------------------------------------------------------
    _print_tempo_shot_summary(match)

    play_count = 0
    commentary_count = 0

    if hasattr(match, "get_play_sequence_log"):
        plays = match.get_play_sequence_log()
        play_count = len(plays) if plays is not None else 0

    if hasattr(match, "get_commentary_entries"):
        commentary = match.get_commentary_entries()
        commentary_count = len(commentary) if commentary is not None else 0
    elif hasattr(match, "commentary_log"):
        commentary_count = len(getattr(match, "commentary_log", []))

    print(f"[Spectate Test] play_count={play_count}")
    print(f"[Spectate Test] commentary_count={commentary_count}")

    if play_count == 0:
        raise RuntimeError("play_sequence_log が空です。match.py 側の実装を確認してください。")

    print("[Spectate Test] 観戦ウィンドウを開きます。")
    run_spectate_view(
        match,
        override_events=spectate_events,
        spectate_mode=SPECTATE_MODE,
    )


if __name__ == "__main__":
    main()
