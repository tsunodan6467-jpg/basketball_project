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


class _DummyTkRoot:
    """tk.Tk() を作らずに report_callback_exception を差し替えできる最小スタブ。"""

    def __init__(self) -> None:
        self.original_called_with: list[tuple] = []

    def report_callback_exception(self, exc_type, exc_value, exc_tb) -> None:
        self.original_called_with.append((exc_type, exc_value, exc_tb))


def test_install_tk_callback_excepthook_writes_last_crash_and_logs(
    monkeypatch, tmp_path, caplog
) -> None:
    monkeypatch.setattr(paths_mod, "user_data_root", lambda: tmp_path)
    from basketball_sim.utils import game_logging as gl

    root = _DummyTkRoot()
    gl.install_tk_callback_excepthook(root)

    try:
        raise ValueError("boom-tk-callback")
    except ValueError:
        exc_type, exc_value, tb = sys.exc_info()

    with caplog.at_level(logging.ERROR, logger="basketball_sim"):
        root.report_callback_exception(exc_type, exc_value, tb)

    crash_path = tmp_path / "logs" / "last_crash.txt"
    assert crash_path.is_file()
    body = crash_path.read_text(encoding="utf-8")
    assert "ValueError" in body
    assert "boom-tk-callback" in body
    assert "Traceback" in body

    assert any(
        "Tk callback" in record.getMessage() for record in caplog.records
    ), "Tk callback 例外メッセージが basketball_sim ロガーに出ているはず"

    assert root.original_called_with, "元の report_callback_exception も呼ばれるべき"
    assert root.original_called_with[0][0] is ValueError


def test_install_tk_callback_excepthook_is_idempotent(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths_mod, "user_data_root", lambda: tmp_path)
    from basketball_sim.utils import game_logging as gl

    root = _DummyTkRoot()
    gl.install_tk_callback_excepthook(root)
    first_hook = root.report_callback_exception

    gl.install_tk_callback_excepthook(root)
    second_hook = root.report_callback_exception

    assert first_hook is second_hook
    assert getattr(root, gl._TK_HOOK_FLAG_ATTR, False) is True


def test_install_tk_callback_excepthook_handles_none_safely() -> None:
    from basketball_sim.utils import game_logging as gl

    gl.install_tk_callback_excepthook(None)

    class _NoCallbackAttr:
        pass

    obj = _NoCallbackAttr()
    gl.install_tk_callback_excepthook(obj)
    assert not hasattr(obj, "report_callback_exception")
