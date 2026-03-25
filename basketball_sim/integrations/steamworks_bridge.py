"""
Steam / Steamworks 連携の受け皿（Phase 0: スタブ）。

目的（初心者向け）:
- 本番で Steam を使うとき、初期化や実績・クラウドセーブをここに集約する。
- いまは DLL も SDK も入れていないため、何もせず「未接続」とログに出すだけ。

操作方法:
- 開発中はそのままでよい。
- Steam 対応するとき: Steam パートナー向け SDK を取得し、このモジュールから API を呼ぶ。

ファイルの場所:
- コード: basketball_sim/integrations/steamworks_bridge.py
- ユーザーが触るファイルは特になし（Steam クライアント側の設定）。
"""

from __future__ import annotations

import logging

LOG = logging.getLogger("basketball_sim.steam")


def try_init_steam() -> bool:
    """
    Steam API を初期化する。成功なら True。

    現状: 常に False（未統合）。クラッシュさせない。
    """
    LOG.info("Steam: 未接続（Steamworks 統合は今後ここに接続）")
    return False
