"""
Test launcher for Presentation Layer.

Recommended location:
basketball_sim/tests/run_presentation_layer_test.py

Purpose
-------
- Safely verify presentation_layer.py in isolation
- Does not modify main.py
- Does not modify season.py
- Simulates one match, builds presentation events, and prints preview
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]        # .../basketball_project
PACKAGE_ROOT = CURRENT_FILE.parents[1]        # .../basketball_project/basketball_sim

for path in (PROJECT_ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

from basketball_sim.models.match import Match
from basketball_sim.systems.generator import generate_teams
from basketball_sim.systems.presentation_layer import PresentationLayer


def _pick_two_teams():
    teams = generate_teams()
    if not teams or len(teams) < 2:
        raise RuntimeError("チーム生成に失敗しました。2チーム以上必要です。")
    return teams[0], teams[1]


def main() -> None:
    configure_console_encoding()
    print("[Presentation Test] 開始")

    home_team, away_team = _pick_two_teams()
    print(f"[Presentation Test] HOME: {getattr(home_team, 'name', 'HOME')}")
    print(f"[Presentation Test] AWAY: {getattr(away_team, 'name', 'AWAY')}")

    match = Match(home_team=home_team, away_team=away_team)
    match.simulate()

    if not hasattr(match, "get_play_sequence_log"):
        raise RuntimeError("match.py に get_play_sequence_log() が見つかりません。")

    plays = match.get_play_sequence_log()
    play_count = len(plays) if plays is not None else 0
    print(f"[Presentation Test] play_count={play_count}")

    if play_count == 0:
        raise RuntimeError("play_sequence_log が空です。match.py 側の実装を確認してください。")

    layer = PresentationLayer(match)
    events = layer.build()

    print(f"[Presentation Test] presentation_count={len(events)}")

    if len(events) == 0:
        raise RuntimeError("presentation_events が空です。presentation_layer.py を確認してください。")

    layer.print_preview(limit=5)

    first_event = layer.get_event_at(0)
    last_event = layer.get_event_at(len(events) - 1)

    print("[Presentation Test] first_event")
    print(first_event)
    print("[Presentation Test] last_event")
    print(last_event)

    print("[Presentation Test] 正常終了")


if __name__ == "__main__":
    main()
