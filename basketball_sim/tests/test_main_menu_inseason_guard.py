"""主画面 GUI のレギュラー中トレード／インシーズンFA ガード（CLI と整合）。"""

from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock, patch

from basketball_sim.config.game_constants import REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND
from basketball_sim.systems.main_menu_view import MainMenuView, wrap_menu_callback_with_inseason_transaction_guard


def _bare_view() -> MainMenuView:
    view = MainMenuView.__new__(MainMenuView)
    view._safe_get = MethodType(MainMenuView._safe_get, view)
    return view


def test_inseason_roster_moves_allowed_unlocked_before_cutoff():
    view = _bare_view()
    view.season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND - 1,
        season_finished=False,
    )
    assert view.inseason_roster_moves_allowed() is True


def test_inseason_roster_moves_allowed_locked_at_cutoff():
    view = _bare_view()
    view.season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND,
        season_finished=False,
    )
    assert view.inseason_roster_moves_allowed() is False


def test_inseason_roster_moves_allowed_offseason():
    view = _bare_view()
    view.season = SimpleNamespace(current_round=99, season_finished=True)
    assert view.inseason_roster_moves_allowed() is True


def test_ensure_inseason_shows_warning_when_locked():
    view = _bare_view()
    view.root = MagicMock()
    view.season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND,
        season_finished=False,
    )
    with patch("basketball_sim.systems.main_menu_view.messagebox.showwarning") as mock_warn:
        assert view.ensure_inseason_roster_moves_allowed(view.root) is False
        mock_warn.assert_called_once()


def test_wrap_menu_callback_blocks_when_locked():
    view = _bare_view()
    view.root = MagicMock()
    view.season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND,
        season_finished=False,
    )
    called: list[int] = []

    def cb() -> None:
        called.append(1)

    with patch("basketball_sim.systems.main_menu_view.messagebox.showwarning"):
        wrapped = wrap_menu_callback_with_inseason_transaction_guard(view, cb)
        wrapped()
    assert called == []


def test_wrap_menu_callback_runs_when_allowed():
    view = _bare_view()
    view.season = SimpleNamespace(
        current_round=REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND - 1,
        season_finished=False,
    )
    called: list[int] = []

    def cb() -> None:
        called.append(1)

    wrapped = wrap_menu_callback_with_inseason_transaction_guard(view, cb)
    wrapped()
    assert called == [1]
