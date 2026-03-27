from types import MethodType, SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def _bare_view_with_team(team) -> MainMenuView:
    view = MainMenuView.__new__(MainMenuView)
    view.team = team
    view._coach_style_label = MethodType(MainMenuView._coach_style_label, view)
    view._build_special_training_catalog_items = MethodType(MainMenuView._build_special_training_catalog_items, view)
    view._build_coach_unlock_count_rows = MethodType(MainMenuView._build_coach_unlock_count_rows, view)
    return view


def test_team_training_lock_reason_requires_unlock_conditions():
    team = SimpleNamespace(coach_style="balanced", training_facility_level=1, medical_facility_level=1)
    view = _bare_view_with_team(team)
    assert "トレーニング施設Lv3以上" in MainMenuView._team_training_lock_reason(view, team, "precision_offense")
    assert "メディカル施設Lv2以上" in MainMenuView._team_training_lock_reason(view, team, "intense_defense")


def test_player_drill_lock_reason_respects_facility_and_coach():
    team = SimpleNamespace(
        coach_style="offense",
        training_facility_level=2,
        front_office_level=1,
        medical_facility_level=1,
    )
    view = _bare_view_with_team(team)
    assert "トレーニング施設Lv3以上" in MainMenuView._player_drill_lock_reason(view, team, "speed_agility")
    assert "フロントオフィスLv2以上" in MainMenuView._player_drill_lock_reason(view, team, "iq_film")
    assert "守備重視" in MainMenuView._player_drill_lock_reason(view, team, "defense_footwork")


def test_current_special_training_lines_include_summary_header():
    team = SimpleNamespace(
        coach_style="development",
        training_facility_level=3,
        front_office_level=2,
        medical_facility_level=2,
    )
    view = _bare_view_with_team(team)
    lines = MainMenuView._build_current_special_training_lines(view, team)
    joined = "\n".join(lines)
    assert "現在HC: 育成" in joined
    assert "解放数:" in joined
    assert "解放中:" in joined
