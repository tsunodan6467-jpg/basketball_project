"""user_settings のウィンドウ寸法・キーバインド解決（tk なし）。"""

from basketball_sim.utils.user_settings import (
    KEY_ACTION_CLOSE_SUBWINDOW,
    fresh_default_settings,
    is_valid_tk_binding_sequence,
    load_user_settings,
    resolve_window_geometry,
    tk_binding_for,
)


def test_load_user_settings_steam_require_license(tmp_path) -> None:
    p = tmp_path / "settings.json"
    p.write_text('{"steam_require_license": 1}', encoding="utf-8")
    assert load_user_settings(p)["steam_require_license"] is True
    p.write_text('{"steam_require_license": false}', encoding="utf-8")
    assert load_user_settings(p)["steam_require_license"] is False


def test_resolve_window_geometry_clamps() -> None:
    s = {
        "window": {"width": 800, "height": 600},
        "fullscreen": False,
    }
    w, h, mw, mh = resolve_window_geometry(s)
    assert w == 800 and h == 600
    assert mw <= w and mh <= h


def test_resolve_window_geometry_defaults_inside() -> None:
    s = {"window": {}, "fullscreen": False}
    w, h, _, _ = resolve_window_geometry(s)
    assert w == 1420 and h == 860


def test_tk_binding_for_custom_and_fallback() -> None:
    default = "<Escape>"
    assert tk_binding_for({}, KEY_ACTION_CLOSE_SUBWINDOW, default) == default
    assert (
        tk_binding_for(
            {"key_bindings": {KEY_ACTION_CLOSE_SUBWINDOW: "<F1>"}},
            KEY_ACTION_CLOSE_SUBWINDOW,
            default,
        )
        == "<F1>"
    )
    assert (
        tk_binding_for(
            {"key_bindings": {KEY_ACTION_CLOSE_SUBWINDOW: "bogus"}},
            KEY_ACTION_CLOSE_SUBWINDOW,
            default,
        )
        == default
    )
    assert (
        tk_binding_for(
            {"key_bindings": {KEY_ACTION_CLOSE_SUBWINDOW: "<<bad>>"}},
            KEY_ACTION_CLOSE_SUBWINDOW,
            default,
        )
        == default
    )


def test_is_valid_tk_binding_sequence() -> None:
    assert is_valid_tk_binding_sequence("<Escape>") is True
    assert is_valid_tk_binding_sequence("<F1>") is True
    assert is_valid_tk_binding_sequence("Escape") is False
    assert is_valid_tk_binding_sequence("") is False


def test_fresh_default_settings_has_schema() -> None:
    d = fresh_default_settings()
    assert d["schema_version"] >= 1
    assert "window" in d and "width" in d["window"]
