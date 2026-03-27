"""
オフシーズン処理の順序（正本）。

順序を変える場合は、本モジュールの OFFSEASON_PHASES と
models/offseason.py の Offseason.run() を同じ意図で更新すること。
（ドラフト後に FA、満了処理の前に再契約、など依存関係が絡む）

シーズン中のトレード／FA は別エントリ（将来: SeasonPhase や main の週次）で扱う想定。
"""

from __future__ import annotations

from typing import List, Tuple

# (phase_id, 短い説明) — run() の実行ブロックと 1:1 で対応
OFFSEASON_PHASES: List[Tuple[str, str]] = [
    ("O01", "準備: 前年ドラフトプール取り込み・ルーキー予算リセット"),
    ("O02", "オフ杯・国際・イベント（年齢前の大会帯）"),
    ("O03", "年齢・成長・帰化・引退"),
    ("O04", "ユース（卒業・補充・ドラフト送り）"),
    ("O05", "契約: CPU 延長 → 再契約交渉"),
    ("O06", "スカウト派遣・来期ドラフト候補生成"),
    ("O07", "スタッツリセット（前シーズン実績クリア）"),
    ("O08", "契約年数減算・満了（再契約済みはスキップ）"),
    ("O09", "国際マーケット更新"),
    ("O10", "特別指定離脱 → 当年ドラフトプールへ"),
    ("O11", "ドラフト: プール生成・コンバイン・オークション指名"),
    ("O12", "トレード"),
    ("O13", "FA"),
    ("O14", "FA プール維持（待機選手）"),
    ("O15", "財務決算・オーナーミッション"),
    ("O16", "治療・監督レビュー・来季戦術・9月プレシーズン特別指定招待"),
    ("O17", "本契約ロスター整合性ログ"),
]


def print_phase_banner(step_index: int, phase_id: str, title: str) -> None:
    """1 始まりの step_index を想定。"""
    print(f"\n{'=' * 14} OFFSEASON {step_index:02d} [{phase_id}] {'=' * 14}")
    print(f"{title}\n")
