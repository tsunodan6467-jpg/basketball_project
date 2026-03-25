"""
ユーザー設定ファイル（JSON）の読み書き。

目的（初心者向け）:
- ログの詳しさ・将来の画面サイズなどを、ゲームの外から変えられるようにする。
- セーブデータ（.sav）とは別。こちらは「ゲーム全体の好み」用。

ファイルの場所:
- %USERPROFILE%\\.basketball_sim\\settings.json
  （エクスプローラーで %USERPROFILE%\\.basketball_sim と入力すると開けます）

操作方法:
- ゲームを終了したあと、メモ帳で settings.json を編集して保存 → 次回起動で反映。
- ログの詳しさ: log_level に "DEBUG" / "INFO" / "WARNING" / "ERROR"
  （環境変数 BASKETBALL_SIM_LOG_LEVEL がある場合はそちらが優先）
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from basketball_sim.utils.paths import settings_path

LOG = logging.getLogger("basketball_sim.settings")

SETTINGS_VERSION = 1

_DEFAULTS: Dict[str, Any] = {
    "schema_version": SETTINGS_VERSION,
    "log_level": "INFO",
    "window": {
        "width": 1280,
        "height": 720,
    },
    "fullscreen": False,
    "key_bindings": {},
}


def _clamp_window(w: Dict[str, Any]) -> None:
    try:
        width = int(w.get("width", 1280))
        height = int(w.get("height", 720))
    except (TypeError, ValueError):
        width, height = 1280, 720
    w["width"] = max(640, min(7680, width))
    w["height"] = max(480, min(4320, height))


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(_DEFAULTS)
    if not isinstance(data, dict):
        return out
    out["schema_version"] = int(data.get("schema_version", SETTINGS_VERSION) or SETTINGS_VERSION)
    lvl = str(data.get("log_level", "INFO")).upper()
    if lvl in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        out["log_level"] = lvl
    win = data.get("window")
    if isinstance(win, dict):
        out["window"] = {"width": win.get("width", 1280), "height": win.get("height", 720)}
        _clamp_window(out["window"])
    out["fullscreen"] = bool(data.get("fullscreen", False))
    kb = data.get("key_bindings")
    out["key_bindings"] = kb if isinstance(kb, dict) else {}
    return out


def load_user_settings(path: Path | None = None) -> Dict[str, Any]:
    """設定ファイルがなければ既定値。壊れていれば既定値にフォールバック。"""
    p = path or settings_path()
    if not p.is_file():
        return deepcopy(_DEFAULTS)
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("設定ファイルを読めませんでした。既定値を使います: %s (%s)", p, exc)
        return deepcopy(_DEFAULTS)
    return _normalize(data)


def save_user_settings(data: Dict[str, Any], path: Path | None = None) -> None:
    """検証・正規化のうえで保存。"""
    p = path or settings_path()
    merged = _normalize(data)
    merged["schema_version"] = SETTINGS_VERSION
    tmp = p.with_suffix(".json.tmp")
    text = json.dumps(merged, ensure_ascii=False, indent=2)
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(p)
    LOG.info("設定を保存しました: %s", p)


def ensure_settings_file_exists(path: Path | None = None) -> Dict[str, Any]:
    """初回起動時など、ファイルが無ければ既定内容で作成。"""
    p = path or settings_path()
    if p.is_file():
        return load_user_settings(p)
    data = deepcopy(_DEFAULTS)
    try:
        save_user_settings(data, p)
    except OSError as exc:
        LOG.warning("設定ファイルを作成できませんでした: %s (%s)", p, exc)
    return data


def apply_settings_to_environment(settings: Dict[str, Any]) -> None:
    """
    ログレベルなど、環境変数へ反映する。
    既に BASKETBALL_SIM_LOG_LEVEL が設定されていれば上書きしない。
    """
    if os.environ.get("BASKETBALL_SIM_LOG_LEVEL", "").strip():
        return
    lvl = str(settings.get("log_level", "INFO")).upper()
    if lvl in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        os.environ["BASKETBALL_SIM_LOG_LEVEL"] = lvl
