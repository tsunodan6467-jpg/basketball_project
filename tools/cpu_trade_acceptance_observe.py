"""
次段: 1対1（または evaluate_trade_for_team 経由）トレード「成立判断」観測用の準備スタブ。

現状: シムは回さない。本体ロジックは変更しない。
実装予定（コメントのみの設計メモ）:

1. TradeSystem.evaluate_trade_for_team を実行時だけラップし、finally で復元する。
2. 記録する列（1 成立あたり）の例:
   - acquiring_team_id, strategy_tag (get_cpu_club_strategy(acquiring_team))
   - send_player_id, receive_player_id
   - send_value, receive_value  (calculate_player_trade_value)
   - score（evaluate 内の最終 score）
   - position_need_delta（_get_position_need_score）
   - ovr_adj（recv-send の OVR 差分による加減算分）
   - cutoff, accepts
   - reasons（TradeEvaluation.reasons の結合文字列）
   - age_send, age_recv, ovr_send, ovr_recv, pot proxy
   - optional: 「今 vs 将来」proxy 例 (pot_recv - pot_send), (age_send - age_recv)

3. どの呼び出し経路をフックするか要調査:
   - 1対1 CPU トレードが evaluate_trade_for_team を必ず通るか、別ヘルパーがないか。

実行例（未実装時はメッセージのみ）:
  python tools/cpu_trade_acceptance_observe.py --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="Trade acceptance observation (stub)")
    p.parse_args()
    print(
        "cpu_trade_acceptance_observe: stub only. "
        "See docs/trade_value_notes.md and module docstring for planned hooks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
