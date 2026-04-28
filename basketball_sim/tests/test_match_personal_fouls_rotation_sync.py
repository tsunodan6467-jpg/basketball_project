"""Match 個人ファウル正本 → RotationSystem 同期/FT最小加算テスト。"""

import pytest

from basketball_sim.models.match import Match
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team


def _player(pid: int, position: str = "SF", ovr: int = 70) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=24,
        nationality="Japan",
        position=position,
        height_cm=198.0,
        weight_kg=90.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=70,
        ovr=ovr,
        potential="B",
        archetype="balanced",
        usage_base=20,
        salary=4_000_000,
        contract_years_left=2,
        contract_total_years=2,
    )


def _build_match() -> Match:
    home = Team(team_id=1, name="Home", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        home.add_player(_player(200 + i, pos, ovr=78 - i))
    home.team_tactics = {
        "version": 1,
        "rotation": {"starters": {}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(home)
    away = Team(team_id=2, name="Away", league_level=1)
    for i, pos in enumerate(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"]):
        away.add_player(_player(300 + i, pos, ovr=68 - i))
    away.team_tactics = {
        "version": 1,
        "rotation": {"starters": {}},
        "team_strategy": {},
        "usage_policy": {},
        "roles": {},
        "playbook": {},
    }
    ensure_team_tactics_on_team(away)
    return Match(home_team=home, away_team=away)


def test_match_initializes_empty_personal_foul_dicts():
    m = _build_match()
    assert m.home_personal_fouls_by_player_id == {}
    assert m.away_personal_fouls_by_player_id == {}


def test_match_syncs_to_rotation_system_on_maybe_update_rotations():
    m = _build_match()
    m.home_personal_fouls_by_player_id[201] = 4
    m.away_personal_fouls_by_player_id[305] = 2
    m._maybe_update_rotations(0)
    assert m.home_rotation._personal_fouls_by_player_id.get(201) == 4
    assert m.away_rotation._personal_fouls_by_player_id.get(305) == 2


def test_set_personal_fouls_by_player_id_none_uses_empty_map():
    from basketball_sim.systems.rotation import RotationSystem

    t = Team(team_id=9, name="T", league_level=1)
    for i in range(8):
        t.add_player(_player(400 + i, "SG" if i == 0 else "SF", ovr=70))
    ps = list(t.players)
    r = RotationSystem(t, ps, starters=ps[:5])
    r.set_personal_fouls_by_player_id(None)
    assert r._personal_fouls_by_player_id == {}


def test_non_ft_possession_does_not_increase_personal_fouls(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (1.0, 1.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    random_values = iter([1.0, 0.0, 0.0, 1.0])  # no steal, 3P branch, make, no assist
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    _ = m._simulate_possession(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
    )
    assert m.home_personal_fouls_by_player_id == {}
    assert m.away_personal_fouls_by_player_id == {}
    assert not any(e.get("event_type") == "foul" for e in m.play_by_play_log)


def test_set_personal_fouls_accepts_string_keys_in_dict():
    m = _build_match()
    r = m.home_rotation
    r.set_personal_fouls_by_player_id({"201": 3, "bad": 1})
    assert r._personal_fouls_by_player_id.get(201) == 3


def test_ft_make_adds_one_personal_foul_to_defense(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    defender = m.away_current_lineup[0]
    shooter = m.home_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    random_values = iter([1.0, 0.8, 0.0])  # no steal, ft branch, make
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    points = m._simulate_possession(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
    )

    assert points == 1
    assert m.away_personal_fouls_by_player_id.get(defender.player_id) == 1
    assert m.home_personal_fouls_by_player_id == {}

    ft_tail = [e for e in m.play_by_play_log if e.get("event_type") in ("foul", "made_ft")]
    assert len(ft_tail) == 2
    assert ft_tail[0].get("event_type") == "foul"
    assert ft_tail[1].get("event_type") == "made_ft"
    fe = ft_tail[0]
    assert fe.get("primary_player_id") == defender.player_id
    assert fe.get("secondary_player_id") == shooter.player_id
    assert fe.get("description_key") == "foul_on_shot"
    meta = fe.get("meta") or {}
    assert meta.get("foul") is True
    assert meta.get("shot_profile") == "ft"
    assert meta.get("second_chance") is False
    assert meta.get("fouler_id") == defender.player_id
    assert meta.get("drawn_by_id") == shooter.player_id


def test_ft_miss_adds_one_personal_foul_to_defense(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    defender = m.home_current_lineup[0]
    shooter = m.away_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    monkeypatch.setattr(m, "_get_offense_rebound_rate", lambda *_args, **_kwargs: 0.0)
    random_values = iter([1.0, 0.8, 0.99, 0.99])  # no steal, ft branch, miss, no oreb
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    points = m._simulate_possession(
        m.away_team,
        m.home_team,
        m.away_current_lineup,
        m.home_current_lineup,
        70.0,
        70.0,
    )

    assert points == 0
    assert m.home_personal_fouls_by_player_id.get(defender.player_id) == 1
    assert m.away_personal_fouls_by_player_id == {}

    tail_types = [e.get("event_type") for e in m.play_by_play_log[-3:]]
    assert tail_types == ["foul", "miss_ft", "def_rebound"]
    fe = m.play_by_play_log[-3]
    assert fe.get("primary_player_id") == defender.player_id
    assert fe.get("secondary_player_id") == shooter.player_id
    meta = fe.get("meta") or {}
    assert meta.get("second_chance") is False


def test_second_chance_ft_records_foul_before_made_ft(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    rebounder = m.home_current_lineup[1]
    defender = m.away_current_lineup[0]
    shooter = m.home_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: shooter)
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    random_values = iter([0.5, 0.0])  # FT branch, make
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    before = len(m.play_by_play_log)
    pts = m._simulate_second_chance(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
        rebounder,
    )
    assert pts == 1
    new_events = m.play_by_play_log[before:]
    types = [e.get("event_type") for e in new_events]
    assert types[0] == "foul"
    assert types[1] == "made_ft"
    fe = new_events[0]
    assert fe.get("primary_player_id") == defender.player_id
    assert fe.get("secondary_player_id") == shooter.player_id
    assert (fe.get("meta") or {}).get("second_chance") is True


def test_ft_make_commentary_includes_foul_line(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    defender = m.away_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    random_values = iter([1.0, 0.8, 0.0])
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    _ = m._simulate_possession(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
    )
    lines = m.get_commentary_lines()
    assert any("ファウル" in ln and "フリースロー" in ln for ln in lines)


def test_foul_addition_syncs_to_rotation_on_next_update(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    defender = m.away_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    random_values = iter([1.0, 0.8, 0.0])  # no steal, ft branch, make
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    _ = m._simulate_possession(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
    )
    m._maybe_update_rotations(1)

    assert m.away_rotation._personal_fouls_by_player_id.get(defender.player_id) == 1
