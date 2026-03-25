"""game_logging: ログパス・初期化・クラッシュ記録（tk なし）。"""

from __future__ import annotations

import logging
import sys

import pytest

from basketball_sim.utils import paths as paths_mod


def test_log_paths_resolve_under_user_root(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths_mod, "user_data_root", lambda: tmp_path)
    from basketball_sim.utils.game_logging import get_last_crash_path, get_log_file_path

    assert get_log_file_path() == tmp_path / "logs" / "game.log"
    assert get_last_crash_path() == tmp_path / "logs" / "last_crash.txt"


def test_setup_writes_rotating_log_and_respects_settings_level(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths_mod, "user_data_root", lambda: tmp_path)
    monkeypatch.delenv("BASKETBALL_SIM_LOG_LEVEL", raising=False)

    from basketball_sim.utils import game_logging as gl

    gl._reset_application_logging_for_tests()
    try:
        gl.setup_application_logging({"log_level": "WARNING"})
        log = logging.getLogger("basketball_sim")
        log.warning("phase0_log_test_warn")
        log.info("phase0_log_test_info_should_skip")
        log_path = gl.get_log_file_path()
        text = log_path.read_text(encoding="utf-8")
        assert "phase0_log_test_warn" in text
        assert "phase0_log_test_info_should_skip" not in text
    finally:
        gl._reset_application_logging_for_tests()


def test_write_last_crash_creates_utf8_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths_mod, "user_data_root", lambda: tmp_path)
    from basketball_sim.utils import game_logging as gl

    try:
        1 / 0
    except ZeroDivisionError:
        exc_type, exc_value, tb = sys.exc_info()
        gl._write_last_crash(exc_type, exc_value, tb)

    crash_path = tmp_path / "logs" / "last_crash.txt"
    assert crash_path.is_file()
    body = crash_path.read_text(encoding="utf-8")
    assert "ZeroDivisionError" in body
