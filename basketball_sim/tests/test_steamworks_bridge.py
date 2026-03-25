"""steamworks_bridge の環境変数・スタブ動作。"""

import os

import pytest

import basketball_sim.integrations.steamworks_bridge as sw


@pytest.fixture(autouse=True)
def reset_steam_module_state(monkeypatch: pytest.MonkeyPatch):
    """各テストでモジュールのグローバル状態を戻す。"""
    monkeypatch.setattr(sw, "_initialized", False, raising=False)
    monkeypatch.setattr(sw, "_app_id_hint", None, raising=False)
    yield


def test_try_init_stub_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BASKETBALL_SIM_DISABLE_STEAM", raising=False)
    monkeypatch.delenv("BASKETBALL_SIM_FAKE_STEAM", raising=False)
    assert sw.try_init_steam() is False
    assert sw.is_steam_initialized() is False


def test_disable_steam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_DISABLE_STEAM", "1")
    assert sw.try_init_steam() is False
    assert sw.is_steam_initialized() is False


def test_fake_steam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    assert sw.is_steam_initialized() is True
    assert sw.try_init_steam() is True
