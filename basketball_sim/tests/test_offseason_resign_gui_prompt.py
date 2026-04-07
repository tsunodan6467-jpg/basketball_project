"""Offseason の再契約 GUI プロンプト注入（CLI 非依存の分岐確認）。"""

from types import SimpleNamespace

from basketball_sim.models.offseason import Offseason
from basketball_sim.systems.salary_cap_budget import get_hard_cap


def test_user_team_resign_decision_calls_injected_prompt():
    team = SimpleNamespace(name="UserClub")
    player = SimpleNamespace(name="Yamada", position="PG", age=24, ovr=72, games_played=30, salary=8_000_000)
    calls = []

    def ui_prompt(**kw):
        calls.append(kw)
        return True

    off = Offseason(teams=[], free_agents=[], resign_ui_prompt=ui_prompt)
    cap = int(get_hard_cap(league_level=1))
    ok = off._user_team_resign_decision(
        team=team,
        player=player,
        new_salary=10_000_000,
        desired_years=2,
        resign_score=60.0,
        threshold=50.0,
        current_team_salary=90_000_000,
        salary_cap=cap,
    )
    assert ok is True
    assert len(calls) == 1
    assert calls[0]["player"] is player
    assert calls[0]["new_salary"] == 10_000_000
    assert calls[0]["desired_years"] == 2


def test_user_team_resign_decision_skips_prompt_when_over_soft_cap():
    team = SimpleNamespace(name="UserClub")
    player = SimpleNamespace(name="Yamada", position="PG", age=24, ovr=72, games_played=30, salary=8_000_000)
    calls = []

    def ui_prompt(**kw):
        calls.append(kw)
        return True

    off = Offseason(teams=[], free_agents=[], resign_ui_prompt=ui_prompt)
    cap = int(get_hard_cap(league_level=1))
    ok = off._user_team_resign_decision(
        team=team,
        player=player,
        new_salary=10_000_000,
        desired_years=2,
        resign_score=60.0,
        threshold=50.0,
        current_team_salary=1_300_000_000,
        salary_cap=cap,
    )
    assert ok is False
    assert calls == []
