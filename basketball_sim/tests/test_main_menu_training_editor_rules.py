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


def test_training_change_confirm_texts_are_human_readable():
    team = SimpleNamespace(
        coach_style="development",
        training_facility_level=3,
        front_office_level=2,
        medical_facility_level=2,
    )
    view = _bare_view_with_team(team)

    team_msg = MainMenuView._build_team_training_change_confirm_text(view, "balanced", "transition")
    assert "変更前: バランス" in team_msg
    assert "変更後: 速攻強化" in team_msg

    player = SimpleNamespace(name="テスト選手")
    player_msg = MainMenuView._build_player_training_change_confirm_text(
        view, player, "dribble", "iq_film"
    )
    assert "テスト選手" in player_msg
    assert "変更前: ドリブル練習" in player_msg
    assert "変更後: 映像分析（IQ）" in player_msg


def test_training_change_log_keeps_latest_entries():
    team = SimpleNamespace()
    view = _bare_view_with_team(team)
    MainMenuView._append_training_change_log(view, team, "A")
    MainMenuView._append_training_change_log(view, team, "B")
    assert MainMenuView._get_latest_training_change_log(view, team) == "B"
