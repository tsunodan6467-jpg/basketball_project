from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.roster_readonly import (
    ROSTER_COLUMNS,
    _sort_rosters_for_readonly_display,
    build_roster_readonly_dict,
    export_roster_json_from_world,
    write_roster_json,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world
from basketball_sim.systems.gm_dashboard_text import sort_roster_for_gm_view


REQUIRED_TOP_KEYS = (
    "screen_title",
    "team_name",
    "league_level",
    "summary",
    "columns",
    "players",
    "notes",
)


def _player(
    pid: int,
    *,
    name: str,
    position: str,
    ovr: int,
    age: int = 24,
    nationality: str = "Japan",
    salary: int = 5_000_000,
    contract_years_left: int = 2,
    fatigue: int = 0,
    injury_games_left: int = 0,
) -> Player:
    return Player(
        player_id=pid,
        name=name,
        age=age,
        nationality=nationality,
        position=position,
        height_cm=185.0,
        weight_kg=80.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=ovr,
        potential="C",
        archetype="guard",
        usage_base=20,
        salary=salary,
        contract_years_left=contract_years_left,
        contract_total_years=2,
        team_id=1,
        fatigue=fatigue,
        injury_games_left=injury_games_left,
    )


def test_build_roster_readonly_dict_has_required_keys() -> None:
    team = Team(team_id=1, name="テストFC", league_level=2, players=[])
    d = build_roster_readonly_dict(team)
    for k in REQUIRED_TOP_KEYS:
        assert k in d
    assert d["columns"] == ROSTER_COLUMNS
    assert isinstance(d["players"], list)


def test_empty_roster() -> None:
    team = Team(team_id=1, name="空", league_level=1, players=[])
    d = build_roster_readonly_dict(team)
    assert d["players"] == []
    assert d["summary"]["roster_count"] == 0


def test_utf8_json_roundtrip(tmp_path: Path) -> None:
    p = _player(1, name="日本語選手", position="C", ovr=55)
    team = Team(team_id=1, name="日本語クラブ", league_level=1, players=[p])
    d = build_roster_readonly_dict(team)
    out = tmp_path / "roster.json"
    write_roster_json(d, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語選手" in text
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["players"][0]["name"] == "日本語選手"


def test_order_starts_at_one_and_max_players() -> None:
    players = [
        _player(1, name="A", position="PG", ovr=50),
        _player(2, name="B", position="PG", ovr=60),
        _player(3, name="C", position="SF", ovr=70),
    ]
    team = Team(team_id=1, name="T", league_level=1, players=players)
    d = build_roster_readonly_dict(team, max_players=2)
    assert len(d["players"]) == 2
    assert d["players"][0]["order"] == 1
    assert d["players"][1]["order"] == 2
    assert d["summary"]["roster_count"] == 3


def test_readonly_sort_matches_gm_dashboard_sort_for_players() -> None:
    players = [
        _player(1, name="Z", position="PG", ovr=70),
        _player(2, name="A", position="PG", ovr=80),
        _player(3, name="M", position="SF", ovr=99),
    ]
    a = [p.player_id for p in sort_roster_for_gm_view(list(players))]
    b = [p.player_id for p in _sort_rosters_for_readonly_display(list(players))]
    assert a == b


def test_sort_position_ovr_name() -> None:
    """PG→C 順、同一ポジは OVR 降順、同 OVR は名前昇順（sort_roster_for_gm_view と一致）。"""
    players = [
        _player(1, name="Zebra", position="PG", ovr=70),
        _player(2, name="Alpha", position="PG", ovr=80),
        _player(3, name="Mido", position="SF", ovr=99),
    ]
    team = Team(team_id=1, name="T", league_level=1, players=players)
    d = build_roster_readonly_dict(team)
    names = [row["name"] for row in d["players"]]
    assert names == ["Alpha", "Zebra", "Mido"]


def test_minimal_player_like_objects_do_not_crash() -> None:
    p = SimpleNamespace(
        name=None,
        position=None,
        age=None,
        ovr=None,
        salary=None,
        contract_years_left=None,
        nationality=None,
        is_injured=lambda: False,
        injured=False,
        injury_games_left=0,
        fatigue=0,
    )
    team = SimpleNamespace(name=None, league_level=None, players=[p], get_nationality_slot_summary=None)
    d = build_roster_readonly_dict(team)
    row = d["players"][0]
    assert row["name"] == "無名選手"
    assert row["position"] == "-"
    assert row["contract_label"] == "-"
    assert row["nationality_slot"]  # フォールバックで何かしら入る
    assert row["status"] == "良好"


def test_injured_and_fatigue_status() -> None:
    p1 = _player(1, name="H", position="C", ovr=60, injury_games_left=3)
    p2 = _player(2, name="F", position="PF", ovr=61, fatigue=65)
    p3 = _player(3, name="Ok", position="SG", ovr=62, fatigue=10)
    team = Team(team_id=1, name="T", league_level=1, players=[p1, p2, p3])
    d = build_roster_readonly_dict(team)
    by_name = {r["name"]: r["status"] for r in d["players"]}
    assert "負傷" in by_name["H"]
    assert by_name["F"] == "疲労高"
    assert by_name["Ok"] == "良好"


def test_export_roster_json_from_world_roundtrip(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1)
    team.players = [_player(99, name="出口子", position="PG", ovr=66)]
    payload = {
        "teams": [team],
        "free_agents": [],
        "user_team_id": 42,
        "season_count": 1,
        "at_annual_menu": True,
        "tracked_player_name": None,
        "resume_season": None,
    }
    save_world(sav, payload)
    out = tmp_path / "roster_from_py.json"
    snap = export_roster_json_from_world(sav, out)
    assert out.is_file()
    assert snap["team_name"] == "セーブ出口FC"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["players"][0]["name"] == "出口子"
    assert "domestic_count" in body["summary"] or "roster_count" in body["summary"]


def test_summary_has_slot_counts_for_real_team() -> None:
    players = [
        _player(1, name="J1", position="PG", ovr=60, nationality="Japan"),
        _player(2, name="F1", position="SG", ovr=61, nationality="USA"),
    ]
    team = Team(team_id=1, name="T", league_level=1, players=players)
    d = build_roster_readonly_dict(team)
    s = d["summary"]
    assert s["roster_count"] == 2
    assert "domestic_count" in s
    assert "foreign_count" in s
    assert "asia_or_naturalized_count" in s
