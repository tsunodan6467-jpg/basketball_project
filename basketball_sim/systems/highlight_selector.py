"""
Highlight Selector

役割:
presentation_events から「見せる価値のあるプレー」を抽出する

安全設計:
- 既存システムに一切影響を与えない
- presentation_layer の出力を読むだけ
"""

from __future__ import annotations

from typing import Dict, List


class HighlightSelector:
    def __init__(self, presentation_events: List[Dict]):
        self.events = presentation_events

    # =========================================================
    # メイン機能
    # =========================================================
    def select_highlights(
        self,
        top_n: int = 15,
        min_score: int = 20,
    ) -> List[Dict]:
        """
        ハイライト抽出

        top_n: 最大抽出数
        min_score: 最低スコア
        """
        candidates = [
            e for e in self.events
            if e.get("highlight_score", 0) >= min_score
        ]

        candidates.sort(
            key=lambda x: x.get("highlight_score", 0),
            reverse=True,
        )

        return candidates[:top_n]

    # =========================================================
    # 時系列ハイライト（流れ重視）
    # =========================================================
    def select_highlights_timeline(
        self,
        top_n: int = 20,
        min_score: int = 18,
    ) -> List[Dict]:
        """
        時系列を保ったハイライト

        重要:
        - 先に highlight_score 上位を抽出
        - その後で play_no 順に並べ直す

        これにより
        「試合開始から条件を満たしたプレーを先頭から top_n 件取る」
        バグを防ぐ
        """
        candidates = [
            e for e in self.events
            if e.get("highlight_score", 0) >= min_score
        ]

        candidates.sort(
            key=lambda x: x.get("highlight_score", 0),
            reverse=True,
        )
        selected = candidates[:top_n]

        selected.sort(key=lambda x: x.get("play_no", 0))
        return selected

    # =========================================================
    # クラッチ抽出
    # =========================================================
    def select_clutch_highlights(self) -> List[Dict]:
        """
        接戦＋終盤だけ抜き出す
        """
        result = []

        for e in self.events:
            tags = e.get("highlight_tags", [])

            if "clutch" in tags or "lead_change" in tags:
                result.append(e)

        return result

    # =========================================================
    # デバッグ表示
    # =========================================================
    def debug_print(self, highlights: List[Dict]) -> None:
        print("[HIGHLIGHTS]")
        print(f"count={len(highlights)}")

        for e in highlights:
            print(
                f"Play#{e.get('play_no')} | "
                f"{e.get('presentation_type')} | "
                f"score={e.get('highlight_score')} | "
                f"{e.get('headline')}"
            )
