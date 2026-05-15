from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basketball_sim.export.home_dashboard_readonly import (
    build_home_dashboard_readonly_dict,
    export_home_dashboard_json_from_world,
    write_home_dashboard_json,
)
from basketball_sim.models.team import Team
from basketball_sim.persistence.save_load import save_world


REQUIRED_KEYS = (
    "club_name",
    "season_label",
    "division",
    "rank_record",
    "money",
    "owner_trust",
    "salary_cap",
    "recent_form",
    "warnings",
    "next_game",
    "club_summary",
    "tasks",
    "news",
)


def test_season_label_annual_menu_with_season_count() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(
        None, team, at_annual_menu=True, season_count=3
    )
    assert d["season_label"] == "年度メニュー（シーズン 3）"


def test_season_label_annual_menu_without_season_count() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(
        None, team, at_annual_menu=True, season_count=None
    )
    assert d["season_label"] == "年度メニュー"


def test_season_label_season_count_only_not_annual_menu() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(
        None, team, at_annual_menu=False, season_count=5
    )
    assert d["season_label"] == "シーズン 5（進行情報未接続）"


def test_season_label_no_meta_unchanged_fallback() -> None:
    team = SimpleNamespace(
        name="X",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(None, team)
    assert d["season_label"] == "シーズン未接続"


def test_home_dashboard_club_summary_is_situation_note_not_metrics_recap() -> None:
    team = SimpleNamespace(
        name="テストFC",
        league_level=2,
        regular_wins=10,
        regular_losses=5,
        money=1_000_000_000,
        owner_trust=72.5,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    season = SimpleNamespace(
        season_finished=False,
        season_no=1,
        current_round=5,
        total_rounds=30,
        leagues={2: [team]},
    )
    d = build_home_dashboard_readonly_dict(season, team, max_tasks=3, max_news=3)
    summary = d["club_summary"]
    assert isinstance(summary, list)
    assert 1 <= len(summary) <= 3
    joined = "\n".join(str(x) for x in summary)
    assert "順位・戦績:" not in joined
    assert "ディビジョン:" not in joined
    assert d["rank_record"] not in summary
    assert d["division"] not in joined
    assert d["money"] not in joined
    cap = d["salary_cap"]
    assert isinstance(cap, str) and cap
    assert cap not in summary
    assert any("シーズン状態:" in str(line) for line in summary)
    assert d["division"] == "D2"
    assert d["rank_record"]
    assert d["money"]
    assert d["owner_trust"]
    assert d["recent_form"]


def test_home_dashboard_club_summary_when_season_missing() -> None:
    team = SimpleNamespace(
        name="テストFC",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(None, team)
    summary = d["club_summary"]
    assert isinstance(summary, list)
    assert 1 <= len(summary) <= 3
    assert any("シーズン未同梱" in str(line) for line in summary)
    assert "順位・戦績:" not in "\n".join(str(x) for x in summary)


def test_build_home_dashboard_returns_dict_with_required_keys() -> None:
    team = SimpleNamespace(
        name="テストFC",
        league_level=2,
        regular_wins=10,
        regular_losses=5,
        money=1_000_000_000,
        owner_trust=72.5,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    d = build_home_dashboard_readonly_dict(None, team, max_tasks=3, max_news=3)
    assert isinstance(d, dict)
    for k in REQUIRED_KEYS:
        assert k in d
    assert isinstance(d["club_summary"], list)
    assert isinstance(d["tasks"], list)
    assert isinstance(d["news"], list)


def test_tasks_and_news_respect_max_limits() -> None:
    team = SimpleNamespace(
        name="A",
        league_level=1,
        regular_wins=0,
        regular_losses=0,
        money=0,
        owner_trust=None,
        players=[SimpleNamespace(is_injured=lambda: True, injured=False)],
        facility_upgrade_points=3,
        fa_shortlist=[1, 2, 3],
        owner_mission="ミッションX",
    )
    d = build_home_dashboard_readonly_dict(None, team, max_tasks=2, max_news=1)
    assert len(d["tasks"]) <= 2
    assert len(d["news"]) <= 1


def test_write_home_dashboard_json_utf8(tmp_path: Path) -> None:
    team = SimpleNamespace(
        name="日本語クラブ",
        league_level=1,
        regular_wins=1,
        regular_losses=1,
        money=500,
        owner_trust=None,
        players=[],
        facility_upgrade_points=0,
        fa_shortlist=[],
        owner_mission=None,
    )
    snap = build_home_dashboard_readonly_dict(None, team)
    out = tmp_path / "home.json"
    write_home_dashboard_json(snap, out)
    text = out.read_text(encoding="utf-8")
    assert "日本語クラブ" in text
    loaded = json.loads(text)
    assert loaded["club_name"] == "日本語クラブ"


def test_export_home_dashboard_json_from_world_roundtrip_minimal_save(tmp_path: Path) -> None:
    sav = tmp_path / "w.sav"
    team = Team(team_id=42, name="セーブ出口FC", league_level=1)
    team.money = 123456789
    team.regular_wins = 3
    team.regular_losses = 7
    team.owner_trust = 50.0
    team.players = []
    team.facility_upgrade_points = 0
    team.fa_shortlist = []
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
    out = tmp_path / "from_py.json"
    snap = export_home_dashboard_json_from_world(sav, out)
    assert out.is_file()
    assert snap["club_name"] == "セーブ出口FC"
    assert snap["season_label"] == "年度メニュー（シーズン 1）"
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["division"].startswith("D")
    assert body["season_label"] == "年度メニュー（シーズン 1）"
