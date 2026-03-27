from types import MethodType, SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def _bare_view_with_team(team) -> MainMenuView:
    view = MainMenuView.__new__(MainMenuView)
    view.team = team
    view._build_special_training_catalog_items = MethodType(MainMenuView._build_special_training_catalog_items, view)
    view._coach_style_label = MethodType(MainMenuView._coach_style_label, view)
    return view


def test_coach_unlock_diff_lines_include_unlock_and_lock_changes():
    team = SimpleNamespace(
        coach_style="offense",
        training_facility_level=3,
        front_office_level=2,
        medical_facility_level=1,
    )
    view = _bare_view_with_team(team)
    lines = MainMenuView._build_coach_unlock_diff_lines(view, "offense", "defense")
    joined = "\n".join(lines)

    assert "HCスタイル: 攻撃重視 → 守備重視" in joined
    assert "解放数:" in joined
    assert "新規解放:" in joined
    assert "個人:ディフェンスフットワーク" in joined
    assert "今回ロック:" in joined
    assert "チーム:精密オフェンス" in joined
