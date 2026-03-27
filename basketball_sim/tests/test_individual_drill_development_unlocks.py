"""個別ドリル解放条件と育成発動率の安全係数（DevelopmentSystem）。"""

from types import SimpleNamespace

import pytest

from basketball_sim.systems.development import DevelopmentSystem
from basketball_sim.systems.training_unlocks import player_drill_lock_reason


def test_player_drill_lock_reason_export_matches_gated_drills() -> None:
    team = SimpleNamespace(
        coach_style="balanced",
        training_facility_level=2,
        front_office_level=1,
        medical_facility_level=1,
    )
    assert player_drill_lock_reason(team, "speed_agility") != ""
    assert player_drill_lock_reason(team, "dribble") == ""


def test_special_gated_drill_proc_multiplier_constant() -> None:
    assert DevelopmentSystem.SPECIAL_GATED_DRILL_PROC_MULTIPLIER == pytest.approx(1.06)
    assert DevelopmentSystem.GATED_DRILLS == frozenset(
        {"speed_agility", "iq_film", "defense_footwork", "strength"}
    )


def test_compute_focus_micro_proc_applies_small_bonus_when_gated_unlocked() -> None:
    # 施設Lvは固定し、iq_film だけが FO Lv で解放されるケース（base_proc を揃える）
    team_locked = SimpleNamespace(
        coach_style="balanced",
        training_facility_level=3,
        front_office_level=1,
        medical_facility_level=1,
    )
    team_unlocked = SimpleNamespace(
        coach_style="balanced",
        training_facility_level=3,
        front_office_level=2,
        medical_facility_level=1,
    )
    proc_locked, flag_locked = DevelopmentSystem._compute_focus_micro_proc(
        team_locked, age=25, games_played=15, total_season_games=30, drill="iq_film"
    )
    proc_unlocked, flag_unlocked = DevelopmentSystem._compute_focus_micro_proc(
        team_unlocked, age=25, games_played=15, total_season_games=30, drill="iq_film"
    )
    assert flag_locked is False
    assert flag_unlocked is True
    assert proc_unlocked == pytest.approx(proc_locked * DevelopmentSystem.SPECIAL_GATED_DRILL_PROC_MULTIPLIER)


def test_compute_focus_micro_proc_skips_bonus_for_non_gated_drill() -> None:
    team = SimpleNamespace(
        coach_style="balanced",
        training_facility_level=3,
        front_office_level=2,
        medical_facility_level=2,
    )
    _, flag = DevelopmentSystem._compute_focus_micro_proc(
        team, age=25, games_played=15, total_season_games=30, drill="dribble"
    )
    assert flag is False


def test_locked_gated_drill_resolves_to_balanced_for_attribute_map() -> None:
    team = SimpleNamespace(
        coach_style="balanced",
        training_facility_level=2,
        front_office_level=1,
        medical_facility_level=1,
    )
    drill = "speed_agility"
    drill_resolved = drill if not player_drill_lock_reason(team, drill) else "balanced"
    assert drill_resolved == "balanced"
