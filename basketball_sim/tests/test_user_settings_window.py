"""user_settings のウィンドウ寸法解決（tk なし）。"""

from basketball_sim.utils.user_settings import resolve_window_geometry


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
