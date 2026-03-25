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

from basketball_sim.utils.paths import logs_dir

_LOGGER_NAME = "basketball_sim"
_setup_done = False


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


def setup_application_logging() -> None:
    """
    ゲーム起動直後に1回だけ呼ぶ。simulate() の先頭で実行する想定。
    """
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    log_dir = logs_dir()
    log_path = get_log_file_path()

    level_name = os.environ.get("BASKETBALL_SIM_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

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

    root.info("logging ready path=%s level=%s", log_path, logging.getLevelName(level))
