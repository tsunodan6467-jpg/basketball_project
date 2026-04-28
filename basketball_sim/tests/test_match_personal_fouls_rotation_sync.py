"""Match 個人ファウル正本 → RotationSystem 同期/FT最小加算テスト。"""

from collections import Counter

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


def _pbp_foul_primary_counts_by_player_id(match: Match) -> Counter:
    c: Counter = Counter()
    for ev in match.play_by_play_log:
        if ev.get("event_type") != "foul":
            continue
        pid = ev.get("primary_player_id")
        if pid is None:
            continue
        try:
            c[int(pid)] += 1
        except (TypeError, ValueError):
            continue
    return c


def _pf_dict_counter(match: Match) -> Counter:
    c: Counter = Counter()
    for k, v in match.home_personal_fouls_by_player_id.items():
        c[int(k)] += int(v)
    for k, v in match.away_personal_fouls_by_player_id.items():
        c[int(k)] += int(v)
    return c


def test_match_initializes_empty_personal_foul_dicts():
    m = _build_match()
    assert m.home_personal_fouls_by_player_id == {}
    assert m.away_personal_fouls_by_player_id == {}
    assert m.home_fouled_out_player_ids == set()
    assert m.away_fouled_out_player_ids == set()
    assert m.home_team_fouls_by_quarter == {}
    assert m.away_team_fouls_by_quarter == {}


def test_match_syncs_to_rotation_system_on_maybe_update_rotations():
    m = _build_match()
    m.home_personal_fouls_by_player_id[201] = 4
    m.away_personal_fouls_by_player_id[305] = 2
    m.home_fouled_out_player_ids.add(201)
    m.away_fouled_out_player_ids.add(305)
    m._maybe_update_rotations(0)
    assert m.home_rotation._personal_fouls_by_player_id.get(201) == 4
    assert m.away_rotation._personal_fouls_by_player_id.get(305) == 2
    assert 201 in m.home_rotation._fouled_out_player_ids
    assert 305 in m.away_rotation._fouled_out_player_ids


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
    assert m.home_team_fouls_by_quarter == {}
    assert m.away_team_fouls_by_quarter == {}
    assert not any(e.get("event_type") == "foul" for e in m.play_by_play_log)
    rows = m.get_player_box_score_rows()
    assert len(rows) == len(m.home_active_players) + len(m.away_active_players)
    assert all(r.get("pf") == 0 for r in rows)


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
    assert m.away_team_fouls_by_quarter.get(1) == 1
    assert m.home_team_fouls_by_quarter == {}

    assert _pbp_foul_primary_counts_by_player_id(m) == _pf_dict_counter(m)
    rows = m.get_player_box_score_rows()
    by_id = {r["player_id"]: r for r in rows}
    assert by_id[defender.player_id]["pf"] == 1
    assert by_id[defender.player_id]["team_id"] == m.away_team.team_id
    assert by_id[shooter.player_id]["pf"] == 0

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
    assert meta.get("team_fouls") == 1
    assert meta.get("team_fouls_quarter") == 1
    assert meta.get("team_fouls_team_id") == m.away_team.team_id


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
    assert m.home_team_fouls_by_quarter.get(1) == 1
    assert m.away_team_fouls_by_quarter == {}

    tail_types = [e.get("event_type") for e in m.play_by_play_log[-3:]]
    assert tail_types == ["foul", "miss_ft", "def_rebound"]
    fe = m.play_by_play_log[-3]
    assert fe.get("primary_player_id") == defender.player_id
    assert fe.get("secondary_player_id") == shooter.player_id
    meta = fe.get("meta") or {}
    assert meta.get("second_chance") is False
    assert meta.get("team_fouls") == 1
    assert meta.get("team_fouls_quarter") == 1
    assert meta.get("team_fouls_team_id") == m.home_team.team_id

    assert _pbp_foul_primary_counts_by_player_id(m) == _pf_dict_counter(m)
    rows = m.get_player_box_score_rows()
    by_id = {r["player_id"]: r for r in rows}
    assert by_id[defender.player_id]["pf"] == 1
    assert by_id[defender.player_id]["team_id"] == m.home_team.team_id
    assert by_id[shooter.player_id]["pf"] == 0


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
    assert (fe.get("meta") or {}).get("team_fouls") == 1
    assert (fe.get("meta") or {}).get("team_fouls_quarter") == 1
    assert m.away_team_fouls_by_quarter.get(1) == 1

    assert _pbp_foul_primary_counts_by_player_id(m) == _pf_dict_counter(m)
    rows = m.get_player_box_score_rows()
    by_id = {r["player_id"]: r for r in rows}
    assert by_id[defender.player_id]["pf"] == 1
    assert by_id[defender.player_id]["team_id"] == m.away_team.team_id


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


def test_foul_out_reaches_limit_once_and_records_event():
    m = _build_match()
    defender = m.away_current_lineup[0]
    # direct add path: 5到達で1回だけ foul_out
    for _ in range(7):
        m._add_personal_foul(m.away_team, defender)
    assert m.away_personal_fouls_by_player_id.get(defender.player_id) == 5
    assert defender.player_id in m.away_fouled_out_player_ids
    fout = [
        e for e in m.play_by_play_log
        if e.get("event_type") == "foul_out" and e.get("primary_player_id") == defender.player_id
    ]
    assert len(fout) == 1
    meta = fout[0].get("meta") or {}
    assert meta.get("personal_fouls") == 5
    assert meta.get("foul_out_limit") == 5


def test_pick_fouler_excludes_already_fouled_out_players():
    m = _build_match()
    p0 = m.away_current_lineup[0]
    p1 = m.away_current_lineup[1]
    m.away_fouled_out_player_ids.add(int(p0.player_id))
    picked_ids = {int(m._pick_fouler([p0, p1]).player_id) for _ in range(10)}
    assert int(p0.player_id) not in picked_ids
    assert int(p1.player_id) in picked_ids


def test_ft_team_fouls_are_tracked_by_quarter(monkeypatch: pytest.MonkeyPatch):
    m = _build_match()
    defender = m.away_current_lineup[0]

    monkeypatch.setattr(m, "_get_shot_mix", lambda *_args, **_kwargs: (0.0, 0.0, 0.0))
    monkeypatch.setattr(m, "_select_shooter", lambda _team, lineup, _shot: lineup[0])
    monkeypatch.setattr(m, "_pick_fouler", lambda _lineup: defender)
    random_values = iter([1.0, 0.8, 0.0, 1.0, 0.8, 0.0])  # no steal, ft branch, make x2
    monkeypatch.setattr("basketball_sim.models.match.random.random", lambda: next(random_values))

    _ = m._simulate_possession(
        m.home_team,
        m.away_team,
        m.home_current_lineup,
        m.away_current_lineup,
        70.0,
        70.0,
    )
    m._set_event_context(quarter=2, clock_seconds=500, possession_no=10)
    try:
        _ = m._simulate_possession(
            m.home_team,
            m.away_team,
            m.home_current_lineup,
            m.away_current_lineup,
            70.0,
            70.0,
        )
    finally:
        m._clear_event_context()

    assert m.away_team_fouls_by_quarter.get(1) == 1
    assert m.away_team_fouls_by_quarter.get(2) == 1
