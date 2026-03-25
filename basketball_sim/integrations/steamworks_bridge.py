"""
Steam / Steamworks 連携の受け皿（Phase 0）。

目的:
- 本番で Steam を使うとき、初期化・実績・クラウドセーブをここに集約する。
- Steam なし / 開発中の PC でも必ずクラッシュしない。

環境変数（任意）:
- BASKETBALL_SIM_DISABLE_STEAM=1 … Steam 初期化を試みない（ログは DEBUG のみ）。
- BASKETBALL_SIM_FAKE_STEAM=1 … 接続成功をシミュレート（CI や UI 分岐のテスト用）。
- BASKETBALL_SIM_STEAM_APPID=480 … 将来の SDK 用の App ID ヒント（未使用でも可）。

Steam リリース時:
- パートナー向け Steamworks SDK を配置し、steam_api64.dll を ctypes または公式バインディングで読み込む。
- 開発時は実行ファイルと同じフォルダに steam_appid.txt（App ID のみ1行）を置くのが一般的。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("basketball_sim.steam")

_initialized: bool = False
_app_id_hint: Optional[int] = None


def _truthy_env(name: str) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    return raw in ("1", "true", "yes", "y", "on")


def _parse_app_id() -> Optional[int]:
    raw = os.environ.get("BASKETBALL_SIM_STEAM_APPID", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        LOG.warning("BASKETBALL_SIM_STEAM_APPID が整数ではありません: %s", raw)
        return None


def _find_steam_appid_txt() -> Optional[Path]:
    """実行ファイル直下またはカレントに steam_appid.txt があればそのパス。"""
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        candidates.append(Path(sys.executable).resolve().parent / "steam_appid.txt")
    candidates.append(Path.cwd() / "steam_appid.txt")
    for p in candidates:
        if p.is_file():
            return p
    return None


def is_steam_initialized() -> bool:
    """try_init_steam が成功したあと True。"""
    return _initialized


def try_init_steam() -> bool:
    """
    Steam API を初期化する。成功なら True。

    - 未統合の環境では False（クラッシュしない）。
    - BASKETBALL_SIM_FAKE_STEAM で True を返せる（テスト用）。
    """
    global _initialized, _app_id_hint

    if _initialized:
        return True

    if _truthy_env("BASKETBALL_SIM_DISABLE_STEAM"):
        LOG.debug("Steam: BASKETBALL_SIM_DISABLE_STEAM によりスキップ")
        return False

    _app_id_hint = _parse_app_id()
    appid_file = _find_steam_appid_txt()
    if appid_file is not None:
        LOG.debug("Steam: steam_appid.txt を検出: %s", appid_file)

    if _truthy_env("BASKETBALL_SIM_FAKE_STEAM"):
        _initialized = True
        LOG.info(
            "Steam: フェイク初期化 OK（BASKETBALL_SIM_FAKE_STEAM）。実 API は未接続。"
        )
        return True

    # 将来: steam_api64.dll の存在確認 → SteamAPI_Init の ctypes 呼び出し
    LOG.debug(
        "Steam: Steamworks 未統合（スタブ）。クライアントの有無に関わらず続行します。"
    )
    return False
