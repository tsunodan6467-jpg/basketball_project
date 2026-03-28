"""
起動時ログと、落ちたときの記録（Phase 0）。

目的（初心者向け）:
- ゲームが異常終了したとき、原因調べの手がかりをファイルに残す。
- 通常プレイの動きもログに残せる（問題が起きたときの前後が追いやすい）。

保存場所:
- ログ: %USERPROFILE%\\.basketball_sim\\logs\\game.log（ローテーション）
- 直近のクラッシュ全文: 同フォルダの last_crash.txt
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from basketball_sim.utils.paths import logs_dir

_LOGGER_NAME = "basketball_sim"
_setup_done = False
_THREAD_EXCEPTHOOK_ORIGINAL = getattr(threading, "excepthook", None)


def get_log_file_path() -> Path:
    return logs_dir() / "game.log"


def get_last_crash_path() -> Path:
    return logs_dir() / "last_crash.txt"


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    log = logging.getLogger(_LOGGER_NAME)
    log.critical("メインスレッドで未処理の例外が発生しました。", exc_info=(exc_type, exc_value, exc_tb))
    _write_last_crash(exc_type, exc_value, exc_tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _thread_excepthook(args) -> None:
    log = logging.getLogger(_LOGGER_NAME)
    log.error(
        "バックグラウンドスレッドで未処理の例外が発生しました。",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    _write_last_crash(args.exc_type, args.exc_value, args.exc_traceback)


def _write_last_crash(exc_type, exc_value, exc_tb) -> None:
    path = get_last_crash_path()
    try:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        path.write_text(text, encoding="utf-8", errors="replace")
    except OSError:
        pass


def _resolve_log_level(user_settings: Optional[Dict[str, Any]]) -> int:
    """環境変数優先。未設定なら user_settings の log_level、それも無ければ INFO。"""
    env = os.environ.get("BASKETBALL_SIM_LOG_LEVEL", "").strip().upper()
    if env:
        return getattr(logging, env, logging.INFO)
    if isinstance(user_settings, dict):
        lvl = str(user_settings.get("log_level", "INFO")).upper()
        if lvl in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            return getattr(logging, lvl, logging.INFO)
    return logging.INFO


def setup_application_logging(user_settings: Optional[Dict[str, Any]] = None) -> None:
    """
    ゲーム起動直後に1回だけ呼ぶ。simulate() の先頭で実行する想定。
    user_settings は log_level 参照用（環境変数 BASKETBALL_SIM_LOG_LEVEL が空のとき）。
    """
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    logs_dir()
    log_path = get_log_file_path()

    level = _resolve_log_level(user_settings)
    level_name = logging.getLevelName(level)

    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        fh = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
            delay=True,
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as exc:
        sys.stderr.write(f"[logging] ログファイルを開けませんでした: {exc}\n")

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    sys.excepthook = _excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_excepthook

    root.info("logging ready path=%s level=%s", log_path, level_name)


def apply_runtime_log_level_from_settings(user_settings: Optional[Dict[str, Any]]) -> None:
    """
    設定変更直後にログレベルを反映する。
    BASKETBALL_SIM_LOG_LEVEL が環境に設定されている場合は変更しない（起動時方針どおり）。
    """
    if os.environ.get("BASKETBALL_SIM_LOG_LEVEL", "").strip():
        return
    if not _setup_done:
        return
    level = _resolve_log_level(user_settings)
    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(level)
    for h in root.handlers:
        h.setLevel(level)


def _reset_application_logging_for_tests() -> None:
    """pytest 用: ハンドラとフックを戻し、再度 setup できるようにする。"""
    global _setup_done
    _setup_done = False
    log = logging.getLogger(_LOGGER_NAME)
    for h in list(log.handlers):
        log.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    log.setLevel(logging.NOTSET)
    sys.excepthook = sys.__excepthook__
    if hasattr(threading, "excepthook"):
        threading.excepthook = _THREAD_EXCEPTHOOK_ORIGINAL
