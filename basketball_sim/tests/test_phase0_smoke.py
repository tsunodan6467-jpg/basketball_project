"""
Phase 0 スモーク: セーブ・乱数・選手ID同期の回帰防止（pytest）。
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from basketball_sim.config.game_constants import GAME_ID, PAYLOAD_SCHEMA_VERSION
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import (
    SAVE_FORMAT_VERSION,
    find_user_team,
    load_world,
    migrate_blob_to_current,
    normalize_payload,
    save_world,
    validate_payload,
)
from basketball_sim.main import (
    _apply_next_season_from_annual_gate,
    _hydrate_resume_for_main_menu_ui,
    _main_menu_advance_button_and_hint,
    _starting_season_count_for_interactive_loop,
)
from basketball_sim.persistence.save_payload import build_save_payload, rebind_resume_season_to_world
from basketball_sim.systems import generator as generator_mod
from basketball_sim.utils import sim_rng as sim_rng_mod


def test_normalize_payload_fills_missing_keys() -> None:
    p: dict = {"teams": [], "free_agents": [], "user_team_id": 1, "season_count": 1}
    normalize_payload(p)
    assert p["tracked_player_name"] is None
    assert p["at_annual_menu"] is False
    assert p["payload_schema_version"] == PAYLOAD_SCHEMA_VERSION
    assert p["simulation_seed"] is None
    assert p.get("resume_season") is None


def test_validate_payload_requires_core_keys() -> None:
    with pytest.raises(ValueError, match="不足"):
        validate_payload({"teams": [], "free_agents": []})


def test_find_user_team() -> None:
    t1 = Team(team_id=1, name="A", league_level=1)
    t2 = Team(team_id=2, name="B", league_level=1)
    assert find_user_team([t1, t2], 2) is t2
    with pytest.raises(ValueError, match="見つかりません"):
        find_user_team([t1, t2], 99)


def test_save_load_roundtrip_minimal_team(tmp_path: Path) -> None:
    path = tmp_path / "t.sav"
    team = Team(team_id=7, name="Roundtrip FC", league_level=1)
    payload_in = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 7,
        "season_count": 2,
        "at_annual_menu": True,
        "tracked_player_name": None,
    }
    save_world(path, payload_in)
    out = load_world(path)
    validate_payload(out)
    assert out["user_team_id"] == 7
    assert out["season_count"] == 2
    assert isinstance(out["teams"], list)
    assert len(out["teams"]) == 1
    loaded = out["teams"][0]
    assert isinstance(loaded, Team)
    assert loaded.team_id == 7
    assert loaded.name == "Roundtrip FC"


def test_starting_season_count_resume_overrides_initial() -> None:
    resume = {
        "teams": [],
        "free_agents": [],
        "user_team_id": 1,
        "season_count": 3,
        "at_annual_menu": True,
    }
    assert _starting_season_count_for_interactive_loop(resume, 99) == 3


def test_starting_season_count_initial_when_no_resume() -> None:
    assert _starting_season_count_for_interactive_loop(None, None) == 1
    assert _starting_season_count_for_interactive_loop(None, 5) == 5
    assert _starting_season_count_for_interactive_loop(None, 0) == 1


def test_main_menu_advance_ui_prevents_double_off_label() -> None:
    assert _main_menu_advance_button_and_hint(False, False)[0] == "次へ進む"
    assert _main_menu_advance_button_and_hint(True, False)[0] == "オフシーズンを実行"
    lbl, hint = _main_menu_advance_button_and_hint(True, True)
    assert lbl == "次のシーズンへ…"
    assert "オフシーズンは完了" in hint


def test_apply_next_season_from_annual_gate_matches_cli_annual_choice_one() -> None:
    """年度ゲートで season_count が 1 だけ増え、新 Season に差し替わる（CLI「次のシーズンへ進む」と同義）。"""
    from basketball_sim.main import generate_teams
    from basketball_sim.models.season import Season

    teams = generate_teams()
    fa: list = []
    season = Season(teams, fa)
    # 全ラウンドシミュは重く環境依存のため、年度ゲート直後の状態のみを直接再現する
    season.season_finished = True
    game_state = {
        "teams": teams,
        "free_agents": fa,
        "user_team": teams[0],
        "season": season,
        "season_count": 7,
        "tracked_player_name": None,
    }
    ui_flow = {"offseason_completed": True, "dirty": False}
    _apply_next_season_from_annual_gate(game_state, ui_flow)
    assert game_state["season_count"] == 8
    assert ui_flow["offseason_completed"] is False
    assert ui_flow["dirty"] is True
    assert game_state["season"] is not season
    assert not game_state["season"].season_finished


def test_hydrate_resume_for_main_menu_ui_midseason(tmp_path: Path) -> None:
    from basketball_sim.main import generate_teams
    from basketball_sim.models.season import Season
    from basketball_sim.utils import sim_rng as sim_rng_mod

    sim_rng_mod.init_simulation_random(11_223_344)
    teams = generate_teams()
    fa: list = []
    season = Season(teams, fa)
    season.simulate_next_round()
    mid_round = int(season.current_round)

    path = tmp_path / "mid_gui.sav"
    payload_in = build_save_payload(
        teams=teams,
        free_agents=fa,
        user_team_id=int(teams[0].team_id),
        season_count=1,
        tracked_player_name=None,
        at_annual_menu=False,
        simulation_seed=sim_rng_mod.get_last_simulation_seed(),
        resume_season=season,
    )
    save_world(path, payload_in)
    out = load_world(path)
    tms, fa2, ut, seas, sc, tp, off_done = _hydrate_resume_for_main_menu_ui(out)
    assert sc == 1
    assert off_done is False
    assert tp is None
    assert int(seas.current_round) == mid_round
    assert seas.all_teams is tms
    assert ut is tms[0]


def test_hydrate_resume_for_main_menu_ui_at_annual_menu(tmp_path: Path) -> None:
    from basketball_sim.main import generate_teams

    teams = generate_teams()
    fa: list = []
    path = tmp_path / "annual_gui.sav"
    payload_in = build_save_payload(
        teams=teams,
        free_agents=fa,
        user_team_id=int(teams[0].team_id),
        season_count=4,
        tracked_player_name="X",
        at_annual_menu=True,
        simulation_seed=None,
        resume_season=None,
    )
    save_world(path, payload_in)
    out = load_world(path)
    _, _, _, seas, sc, tp, off_done = _hydrate_resume_for_main_menu_ui(out)
    assert sc == 4
    assert tp == "X"
    assert off_done is True
    assert seas.all_teams is out["teams"]


def test_save_load_midseason_season_roundtrip(tmp_path: Path) -> None:
    from basketball_sim.main import generate_teams
    from basketball_sim.models.season import Season
    from basketball_sim.utils import sim_rng as sim_rng_mod

    sim_rng_mod.init_simulation_random(11_223_344)
    teams = generate_teams()
    fa: list = []
    season = Season(teams, fa)
    season.simulate_next_round()
    mid_round = int(season.current_round)

    path = tmp_path / "mid.sav"
    payload_in = build_save_payload(
        teams=teams,
        free_agents=fa,
        user_team_id=int(teams[0].team_id),
        season_count=1,
        tracked_player_name=None,
        at_annual_menu=False,
        simulation_seed=sim_rng_mod.get_last_simulation_seed(),
        resume_season=season,
    )
    save_world(path, payload_in)
    out = load_world(path)
    validate_payload(out)
    rebind_resume_season_to_world(out)
    rs = out.get("resume_season")
    assert rs is not None
    assert int(rs.current_round) == mid_round
    assert rs.all_teams is out["teams"]


def test_load_rejects_future_format_version(tmp_path: Path) -> None:
    path = tmp_path / "future.sav"
    blob = {
        "format_version": SAVE_FORMAT_VERSION + 10,
        "game_id": GAME_ID,
        "saved_at_unix": 0,
        "payload": {"teams": [], "free_agents": [], "user_team_id": 1, "season_count": 1},
    }
    path.write_bytes(pickle.dumps(blob))
    with pytest.raises(ValueError, match="未対応"):
        load_world(path)


def test_migrate_blob_rejects_too_old() -> None:
    with pytest.raises(ValueError, match="古すぎ"):
        migrate_blob_to_current({"format_version": 0})


def test_sim_rng_reproducible() -> None:
    import random

    s = sim_rng_mod.init_simulation_random(999_888_777)
    assert s == (999_888_777 & 0xFFFFFFFF)
    a = [random.random() for _ in range(5)]
    sim_rng_mod.init_simulation_random(999_888_777)
    b = [random.random() for _ in range(5)]
    assert a == b


def test_sync_player_id_counter_from_world() -> None:
    old = generator_mod._player_id_counter

    class _P:
        def __init__(self, pid: int) -> None:
            self.player_id = pid

    class _T:
        def __init__(self, players: list) -> None:
            self.players = players

    try:
        generator_mod._player_id_counter = 1
        fa = [_P(200)]
        teams = [_T([_P(5), _P(50)])]
        n = generator_mod.sync_player_id_counter_from_world(teams, fa)
        assert n == 201
        assert generator_mod._player_id_counter == 201
    finally:
        generator_mod._player_id_counter = old
