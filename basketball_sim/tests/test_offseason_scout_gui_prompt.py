"""GUI経由オフシーズンで O06 スカウト派遣 / ドラフトコンバインスカウト方針が
input()/readline を呼ばずに、注入された UI プロンプトコールバックの戻り値を採用することを確認する。"""

from types import SimpleNamespace

import builtins

from basketball_sim.models.offseason import Offseason


def _make_user_team():
    return SimpleNamespace(
        team_id=1,
        name="UserClub",
        is_user_team=True,
        scout_dispatch="college",
        scout_focus="balanced",
    )


def _fail_input(*_args, **_kwargs):
    raise AssertionError("input() must not be called when UI prompt is injected")


def test_choose_user_scout_dispatch_uses_callback_and_skips_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    team = _make_user_team()
    captured = []

    def cb(t):
        captured.append(t)
        return "highschool"

    off = Offseason(teams=[], free_agents=[], scout_dispatch_ui_prompt=cb)
    off._choose_user_scout_dispatch(team)
    assert captured == [team]
    assert team.scout_dispatch == "highschool"


def test_choose_user_scout_dispatch_callback_invalid_falls_back_to_college(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    team = _make_user_team()

    off = Offseason(
        teams=[], free_agents=[],
        scout_dispatch_ui_prompt=lambda t: "INVALID_OPTION",
    )
    off._choose_user_scout_dispatch(team)
    assert team.scout_dispatch == "college"


def test_choose_user_scout_dispatch_callback_exception_uses_default(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    team = _make_user_team()

    def raising_cb(_t):
        raise RuntimeError("can't re-enter readline")

    off = Offseason(
        teams=[], free_agents=[],
        scout_dispatch_ui_prompt=raising_cb,
    )
    off._choose_user_scout_dispatch(team)
    assert team.scout_dispatch == "college"


def test_choose_user_scout_focus_uses_callback_and_skips_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    team = _make_user_team()
    captured = []

    def cb(t):
        captured.append(t)
        return "shooting"

    off = Offseason(teams=[], free_agents=[], scout_focus_ui_prompt=cb)
    off._choose_user_scout_focus(team)
    assert captured == [team]
    assert getattr(team, "scout_focus", None) == "shooting"


def test_choose_user_scout_focus_callback_invalid_falls_back_to_balanced(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    team = _make_user_team()

    off = Offseason(
        teams=[], free_agents=[],
        scout_focus_ui_prompt=lambda t: "INVALID_FOCUS",
    )
    off._choose_user_scout_focus(team)
    assert getattr(team, "scout_focus", None) == "balanced"


def test_offseason_init_accepts_scout_callbacks_without_change_for_cli():
    """コールバック未指定時は既定挙動を壊さない（CLI経路は触らない契約）。"""
    off = Offseason(teams=[], free_agents=[])
    assert off._scout_dispatch_ui_prompt is None
    assert off._scout_focus_ui_prompt is None
