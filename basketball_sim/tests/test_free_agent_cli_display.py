"""free_agent_cli_display（FA プール CLI 補助）。"""

import io
import contextlib

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_cli_display import (
    build_free_agent_slot_label,
    build_free_agent_value_label,
    format_free_agent_cli_hint,
    print_free_agent_pool_cli,
)


def _p(**kw) -> Player:
    base = dict(
        player_id=kw.get("player_id", 1),
        name=kw.get("name", "TFA"),
        age=kw.get("age", 25),
        nationality="Japan",
        position=kw.get("position", "SG"),
        height_cm=195.0,
        weight_kg=90.0,
        shoot=55,
        three=55,
        drive=55,
        passing=55,
        handling=55,
        rebound=55,
        power=55,
        defense=55,
        ft=55,
        stamina=60,
        ovr=kw.get("ovr", 60),
        potential=kw.get("potential", "B"),
        archetype="wing",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=1,
    )
    base.update({k: v for k, v in kw.items() if k in base})
    return Player(**base)


def test_slot_veteran():
    p = _p(age=33, ovr=62)
    assert build_free_agent_slot_label(p) == "ベテラン"


def test_slot_immediate():
    p = _p(age=27, ovr=68)
    assert build_free_agent_slot_label(p) == "即戦力"


def test_format_hint_has_shape_and_sw():
    p = _p(three=78, shoot=74, passing=40, handling=38, position="SG")
    line = format_free_agent_cli_hint(p, user_team=None)
    assert "ガード型" in line
    assert "強み:" in line


def test_print_pool_smoke():
    u = Team(team_id=1, name="UFA", league_level=1, players=[_p(player_id=10, name="R1")])
    fa = [_p(player_id=2, name="FA1", ovr=63)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_free_agent_pool_cli(u, fa, season=None)
    out = buf.getvalue()
    assert "FA候補プール" in out
    assert "FA1" in out
