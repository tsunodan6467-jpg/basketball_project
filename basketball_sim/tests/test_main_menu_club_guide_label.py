"""左メニュー「クラブ案内」（旧ラベル GM）の表示名が安定していること。"""

from basketball_sim.systems.main_menu_view import MainMenuView


def test_club_guide_label_in_menu_items():
    assert MainMenuView.CLUB_GUIDE_MENU_LABEL == "クラブ案内"
    assert MainMenuView.CLUB_GUIDE_MENU_LABEL in MainMenuView.MENU_ITEMS


def test_format_club_guide_hint_block_has_role_banner():
    view = MainMenuView.__new__(MainMenuView)
    view.season = None
    view.team = None
    view._safe_get = MainMenuView._safe_get.__get__(view, MainMenuView)
    text = MainMenuView._format_gm_cli_hint_block(view)
    assert "【クラブ案内】" in text
    assert "閲覧" in text
