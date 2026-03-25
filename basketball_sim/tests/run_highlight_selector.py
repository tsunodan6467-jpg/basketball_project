"""
Highlight Selector Test Runner

配置:
basketball_sim/tests/run_highlight_selector.py

目的:
- 1試合シミュレーション
- presentation_events を生成
- HighlightSelector でハイライト抽出
- コンソール出力

安全設計:
- 既存ロジックを壊さない
- 読み取り専用
"""

from __future__ import annotations

import sys
from pathlib import Path


# =========================================================
# パス調整
# =========================================================
CURRENT_FILE = Path(__file__).resolve()
BASKETBALL_SIM_DIR = CURRENT_FILE.parents[1]
PROJECT_ROOT_DIR = CURRENT_FILE.parents[2]

for path in (str(BASKETBALL_SIM_DIR), str(PROJECT_ROOT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

# =========================================================
# import（既存構造に合わせる）
# =========================================================
from basketball_sim.models.match import Match
from basketball_sim.models.team import Team
from basketball_sim.systems.generator import generate_single_player
from basketball_sim.systems.presentation_layer import PresentationLayer
from basketball_sim.systems.highlight_selector import HighlightSelector


# =========================================================
# チーム生成
# =========================================================
def build_test_team(team_id: int, name: str, league_level: str = "D1") -> Team:
    team = Team(team_id=team_id, name=name, league_level=league_level)

    for _ in range(13):
        player = generate_single_player()
        team.add_player(player)

    return team


# =========================================================
# 表示
# =========================================================
def print_highlights_block(title: str, highlights: list[dict]) -> None:
    print("")
    print(f"[HIGHLIGHTS] {title}")
    print(f"[HIGHLIGHTS] count={len(highlights)}")

    if not highlights:
        print("[HIGHLIGHTS] no highlights")
        return

    for event in highlights:
        play_no = event.get("play_no", "-")
        presentation_type = event.get("presentation_type", "-")
        score = event.get("highlight_score", 0)
        headline = event.get("headline", "-")
        main_text = event.get("main_text", "")
        sub_text = event.get("sub_text", "")
        tags = event.get("highlight_tags", [])

        print(
            f"Play#{play_no:>3} | "
            f"{presentation_type:<18} | "
            f"score={score:>3} | "
            f"{headline}"
        )
        if main_text:
            print(f"  {main_text}")
        if sub_text:
            print(f"  {sub_text}")
        if tags:
            print(f"  tags={', '.join(tags)}")


# =========================================================
# メイン
# =========================================================
def main() -> None:
    configure_console_encoding()
    home_team = build_test_team(team_id=1, name="東京ベイホークス", league_level="D1")
    away_team = build_test_team(team_id=2, name="大阪ライトニング", league_level="D1")

    match = Match(home_team=home_team, away_team=away_team)
    match.simulate()

    presentation_layer = PresentationLayer(match)
    presentation_events = presentation_layer.build()

    print("[PRESENTATION]")
    print(f"total_events={len(presentation_events)}")
    print(f"type_counts={presentation_layer.get_type_counts()}")

    selector = HighlightSelector(presentation_events)

    top_highlights = selector.select_highlights(top_n=15, min_score=20)
    timeline_highlights = selector.select_highlights_timeline(top_n=20, min_score=18)
    clutch_highlights = selector.select_clutch_highlights()

    print_highlights_block("TOP SCORE", top_highlights)
    print_highlights_block("TIMELINE", timeline_highlights)
    print_highlights_block("CLUTCH", clutch_highlights)


if __name__ == "__main__":
    main()
