"""player_development_cli_display（個別育成 CLI 補助行）。"""

from basketball_sim.models.player import Player
from basketball_sim.systems.player_development_cli_display import (
    build_player_development_growth_focus_label,
    build_player_development_priority_label,
    format_player_development_cli_hint,
)


def _p(**kwargs) -> Player:
    base = dict(
        player_id=1,
        name="DevTest",
        age=21,
        nationality="Japan",
        position="SG",
        height_cm=192.0,
        weight_kg=85.0,
        shoot=58,
        three=72,
        drive=55,
        passing=54,
        rebound=50,
        defense=48,
        ft=52,
        stamina=60,
        ovr=59,
        potential="A",
        archetype="wing",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )
    base.update(kwargs)
    return Player(**base)


def test_priority_young_high_potential():
    assert build_player_development_priority_label(_p(age=20, ovr=58, potential="A")) == "優先育成"


def test_priority_ready_veteran():
    assert build_player_development_priority_label(_p(age=25, ovr=68, potential="C")) == "即戦力化候補"


def test_growth_focus_second_weakest():
    g = build_player_development_growth_focus_label(_p(defense=30, ft=28, three=75))
    assert g == "守備"


def test_format_hint_contains_sections():
    s = format_player_development_cli_hint(_p())
    assert "強み:" in s and "弱み:" in s
    assert "伸ばしどころ:" in s
    assert "ガード型" in s
