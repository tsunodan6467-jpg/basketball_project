"""RegSlot: Season → Match → Rotation 受け渡し基盤（schedule_care ロジック本体は未搭載）。"""

from __future__ import annotations

from unittest import mock

from basketball_sim.main import generate_teams
from basketball_sim.models.match import Match
from basketball_sim.models.reg_slot import RegSlot
from basketball_sim.models.season import Season, SeasonEvent


def test_simulate_next_round_two_regular_games_same_team_increments_round_index_and_dow() -> None:
    """同一 round に同一 team のレギュラー2試合: round_index 1→2、dow は各 event に一致。"""
    teams = generate_teams()
    season = Season(teams, [])
    a, b, c = teams[0], teams[1], teams[2]
    rnd = 1
    season.events_by_round[rnd] = [
        SeasonEvent(
            event_id="r1g1",
            week=rnd,
            day_of_week="Wed",
            event_type="game",
            competition_id="regular_season",
            competition_type="regular_season",
            stage="regular_season",
            home_team=a,
            away_team=b,
            round_number=rnd,
            label="g1",
        ),
        SeasonEvent(
            event_id="r1g2",
            week=rnd,
            day_of_week="Sat",
            event_type="game",
            competition_id="regular_season",
            competition_type="regular_season",
            stage="regular_season",
            home_team=c,
            away_team=a,
            round_number=rnd,
            label="g2",
        ),
    ]

    captured: list[dict] = []

    def _fake_match(*args, **kwargs):
        captured.append(
            {
                "reg_slot_home": kwargs.get("reg_slot_home"),
                "reg_slot_away": kwargs.get("reg_slot_away"),
            }
        )
        m = mock.MagicMock()
        m.simulate = mock.MagicMock(return_value=(a, 70, 70))
        return m

    with mock.patch("basketball_sim.models.season.Match", side_effect=_fake_match):
        season.simulate_next_round()

    assert len(captured) == 2
    assert captured[0]["reg_slot_home"].round_index == 1
    assert captured[0]["reg_slot_away"].round_index == 1
    assert captured[0]["reg_slot_home"].dow == "Wed"
    assert captured[0]["reg_slot_away"].dow == "Wed"
    # team a: 2 試合目
    assert captured[1]["reg_slot_home"].round_index == 1
    assert captured[1]["reg_slot_away"].round_index == 2
    assert captured[1]["reg_slot_away"].dow == "Sat"
    assert captured[1]["reg_slot_home"].dow == "Sat"


def test_playoff_match_reg_slots_none_rotation_matches() -> None:
    """非レギュラー（playoff）では reg_slot_* が None、Rotation も None。"""
    teams = generate_teams()
    home, away = teams[0], teams[1]
    m = Match(
        home_team=home,
        away_team=away,
        is_playoff=True,
        competition_type="playoff",
    )
    assert m.reg_slot_home is None
    assert m.reg_slot_away is None
    assert m.home_rotation.reg_slot is None
    assert m.away_rotation.reg_slot is None


def test_match_passes_reg_slot_to_rotations() -> None:
    """レギュラー用 RegSlot を RotationSystem.reg_slot へ受け渡し。"""
    teams = generate_teams()
    home, away = teams[0], teams[1]
    m = Match(
        home_team=home,
        away_team=away,
        competition_type="regular_season",
        reg_slot_home=RegSlot(round_index=1, dow="Tue"),
        reg_slot_away=RegSlot(round_index=1, dow="Tue"),
    )
    assert m.reg_slot_home == m.home_rotation.reg_slot
    assert m.reg_slot_away == m.away_rotation.reg_slot
    assert m.home_rotation.reg_slot.round_index == 1
    assert m.away_rotation.reg_slot.dow == "Tue"
