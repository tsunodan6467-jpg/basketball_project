"""ドラフト候補 CLI 補助行（表示のみ）。"""

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.draft import (
    build_draft_candidate_readiness_label,
    build_draft_candidate_role_shape_label,
    build_draft_candidate_strength_weakness_line,
    format_draft_candidate_cli_hint,
)


def _make_player(**kwargs) -> Player:
    base = dict(
        player_id=1,
        name="候補テスト",
        age=20,
        nationality="Japan",
        position="PG",
        height_cm=185.0,
        weight_kg=80.0,
        shoot=55,
        three=55,
        drive=55,
        passing=55,
        rebound=55,
        defense=55,
        ft=55,
        stamina=55,
        ovr=60,
        potential="B",
        archetype="guard",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    base.update(kwargs)
    return Player(**base)


def test_role_shape_labels():
    assert build_draft_candidate_role_shape_label(_make_player(position="SG")) == "ガード型"
    assert build_draft_candidate_role_shape_label(_make_player(position="SF")) == "ウイング型"
    assert build_draft_candidate_role_shape_label(_make_player(position="C")) == "ビッグ型"


def test_strength_weakness_uses_raw_attrs():
    p = _make_player(three=80, defense=40, rebound=35)
    line = build_draft_candidate_strength_weakness_line(p)
    assert "3P" in line
    assert "弱み" in line


def test_readiness_future_type_young_high_potential():
    t = Team(team_id=1, name="U", league_level=1, is_user_team=True)
    p = _make_player(age=19, ovr=58, potential="A", passing=50)
    assert build_draft_candidate_readiness_label(t, p) == "将来型"


def test_readiness_nba_ready_high_ovr():
    t = Team(team_id=1, name="U", league_level=1, is_user_team=True)
    p = _make_player(age=23, ovr=68, potential="C")
    assert build_draft_candidate_readiness_label(t, p) == "即戦力"


def test_format_cli_hint_combined():
    t = Team(team_id=1, name="U", league_level=1, is_user_team=True)
    p = _make_player(age=22, ovr=66, potential="B", three=72, defense=48)
    s = format_draft_candidate_cli_hint(t, p)
    assert "ガード型" in s
    assert "強み:" in s and "弱み:" in s
