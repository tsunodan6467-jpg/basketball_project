"""steamworks_bridge の環境変数・スタブ動作。"""

import os

import pytest

import basketball_sim.integrations.steamworks_bridge as sw


@pytest.fixture(autouse=True)
def reset_steam_module_state(monkeypatch: pytest.MonkeyPatch):
    """各テストでモジュールのグローバル状態を戻す。"""
    monkeypatch.setattr(sw, "_initialized", False, raising=False)
    monkeypatch.setattr(sw, "_app_id_hint", None, raising=False)
    monkeypatch.setattr(sw, "_steam_dll", None, raising=False)
    monkeypatch.setattr(sw, "_steam_apps_ptr", None, raising=False)
    monkeypatch.setattr(sw, "_steam_user_stats_ptr", None, raising=False)
    monkeypatch.setattr(sw, "_user_stats_prepared", False, raising=False)
    yield


def test_try_init_stub_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BASKETBALL_SIM_DISABLE_STEAM", raising=False)
    monkeypatch.delenv("BASKETBALL_SIM_FAKE_STEAM", raising=False)
    # リポジトリ直下に steam_api64.dll がある開発環境でも「DLL なし」と同じ結果にする
    monkeypatch.setattr(sw, "_steam_dll_candidate_files", lambda: [])
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
    assert sw.steam_native_loaded() is False
    assert sw.try_init_steam() is True


def test_pump_steam_callbacks_safe_when_inactive() -> None:
    sw.pump_steam_callbacks()


def test_shutdown_clears_fake_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    sw.shutdown_steam()
    assert sw.is_steam_initialized() is False
    assert sw.steam_native_loaded() is False


def test_steam_native_loaded_false_by_default() -> None:
    assert sw.steam_native_loaded() is False


def test_enforce_license_noop_when_disabled() -> None:
    sw.enforce_steam_license({})
    sw.enforce_steam_license({"steam_require_license": False})


def test_enforce_license_skips_with_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", "1")
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    sw.enforce_steam_license({})


def test_enforce_license_exits_when_required_not_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", "1")
    monkeypatch.delenv("BASKETBALL_SIM_FAKE_STEAM", raising=False)
    with pytest.raises(SystemExit) as exc:
        sw.enforce_steam_license({})
    assert exc.value.code == 2


def test_enforce_license_exits_from_settings_without_steam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", raising=False)
    monkeypatch.delenv("BASKETBALL_SIM_FAKE_STEAM", raising=False)
    with pytest.raises(SystemExit) as exc:
        sw.enforce_steam_license({"steam_require_license": True})
    assert exc.value.code == 2


def test_steam_is_subscribed_none_without_native() -> None:
    assert sw.steam_is_subscribed() is None


def test_enforce_license_exits_5_initialized_but_not_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    monkeypatch.delenv("BASKETBALL_SIM_FAKE_STEAM", raising=False)
    monkeypatch.setenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", "1")
    with pytest.raises(SystemExit) as exc:
        sw.enforce_steam_license({})
    assert exc.value.code == 5


def test_enforce_license_exits_3_when_not_subscribed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", "1")
    monkeypatch.setattr(sw, "is_steam_initialized", lambda: True)
    monkeypatch.setattr(sw, "steam_native_loaded", lambda: True)
    monkeypatch.setattr(sw, "steam_is_subscribed", lambda: False)
    with pytest.raises(SystemExit) as exc:
        sw.enforce_steam_license({})
    assert exc.value.code == 3


def test_unlock_achievement_false_without_steam() -> None:
    assert sw.unlock_achievement("ACH_TEST") is False


def test_unlock_achievement_false_empty_name() -> None:
    assert sw.unlock_achievement("") is False
    assert sw.unlock_achievement("   ") is False


def test_unlock_achievement_fake_steam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    assert sw.unlock_achievement("ACH_PHASE0_TEST") is True


def test_unlock_achievement_rejects_unregistered_when_registry_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import basketball_sim.config.steam_achievements as sac

    monkeypatch.setattr(sac, "STEAM_ACHIEVEMENT_API_NAMES", frozenset({"ONLY_THIS"}))
    monkeypatch.setenv("BASKETBALL_SIM_FAKE_STEAM", "1")
    assert sw.try_init_steam() is True
    assert sw.unlock_achievement("OTHER") is False
    assert sw.unlock_achievement("ONLY_THIS") is True


def test_enforce_license_strict_exits_4_when_api_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE", "1")
    monkeypatch.setenv("BASKETBALL_SIM_STEAM_LICENSE_STRICT", "1")
    monkeypatch.setattr(sw, "is_steam_initialized", lambda: True)
    monkeypatch.setattr(sw, "steam_native_loaded", lambda: True)
    monkeypatch.setattr(sw, "steam_is_subscribed", lambda: None)
    with pytest.raises(SystemExit) as exc:
        sw.enforce_steam_license({})
    assert exc.value.code == 4
