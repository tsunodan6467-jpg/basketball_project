"""
シミュレーション用乱数の入口（Phase 0）。

現状は標準ライブラリ ``random`` モジュールを ``random.seed`` で初期化する方式。
将来、モジュールごとに独立 RNG を渡す場合はここを拡張する。

環境変数:
- BASKETBALL_SIM_SEED: 整数を指定すると新規ゲーム開始時のシードに使う（デバッグ・再現用）。
"""

from __future__ import annotations

import os
import random
import time
from typing import Optional

_last_seed: Optional[int] = None


def get_last_simulation_seed() -> Optional[int]:
    """直近の init_simulation_random で使ったシード（未初期化なら None）。"""
    return _last_seed


def init_simulation_random(seed: Optional[int] = None) -> int:
    """
    ゲームセッションの乱数を初期化し、使ったシードを返す。

    - ``seed`` 指定時: その値を使う（セーブ再開など）。
    - 未指定かつ環境変数 BASKETBALL_SIM_SEED が整数ならそれを使う。
    - それ以外: 時刻ベースで非固定シード。
    """
    global _last_seed
    if seed is not None:
        s = int(seed) & 0xFFFFFFFF
    else:
        raw = os.environ.get("BASKETBALL_SIM_SEED", "").strip()
        if raw:
            try:
                s = int(raw) & 0xFFFFFFFF
            except ValueError:
                s = int(time.time_ns() % (2**32))
        else:
            s = int(time.time_ns() % (2**32))
    _last_seed = s
    random.seed(s)
    return s
