"""GUI経由オフシーズンの特別指定選手招待が input() に落ちず、callback で選択できることを確認する。"""

from types import SimpleNamespace

import builtins

from basketball_sim.models.offseason import Offseason


def _fail_input(*_args, **_kwargs):
    raise AssertionError("input() must not be called when UI prompt is injected")


def _candidate(name: str, ovr: int) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        ovr=ovr,
        potential="C",
        age=20,
        position="PG",
        draft_market_grade="",
        is_draft_prospect=False,
    )


def _make_holder_and_user(pool):
    """ holder は招待ループをスキップするが league_future_draft_pool を保持する。"""
    holder = SimpleNamespace(
        team_id=1,
        name="LeagueHolder",
        league_future_draft_pool=list(pool),
        special_designation_players=[object()],
        is_user_team=False,
        popularity=50,
        league_level=1,
    )
    user = SimpleNamespace(
        team_id=2,
        name="UserClub",
        league_future_draft_pool=[],
        special_designation_players=[],
        is_user_team=True,
        popularity=50,
        league_level=1,
        scout_level=50,
    )
    return holder, user


def test_special_designation_callback_skips_input_and_returns_none(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    lo = _candidate("Lo", 50)
    holder, user = _make_holder_and_user([hi, lo])
    captured = []

    def cb(team, shortlist):
        captured.append((team, list(shortlist)))
        return None

    off = Offseason([holder, user], [], special_designation_ui_prompt=cb)
    off._run_special_designation_invitations()

    assert captured and captured[0][0] is user
    assert {p.name for p in captured[0][1]} == {"Hi", "Lo"}
    assert user.special_designation_players == []


def test_special_designation_callback_zero_skips(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    holder, user = _make_holder_and_user([hi])

    off = Offseason([holder, user], [], special_designation_ui_prompt=lambda t, sl: 0)
    off._run_special_designation_invitations()
    assert user.special_designation_players == []


def test_special_designation_callback_one_picks_first(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    lo = _candidate("Lo", 50)
    holder, user = _make_holder_and_user([hi, lo])

    off = Offseason([holder, user], [], special_designation_ui_prompt=lambda t, sl: 1)
    off._run_special_designation_invitations()

    assert len(user.special_designation_players) == 1
    assert user.special_designation_players[0].name == "Hi"
    assert hi not in holder.league_future_draft_pool


def test_special_designation_callback_invalid_skips(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    holder, user = _make_holder_and_user([hi])

    off = Offseason([holder, user], [], special_designation_ui_prompt=lambda t, sl: 99)
    off._run_special_designation_invitations()
    assert user.special_designation_players == []


def test_special_designation_callback_non_int_skips(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    holder, user = _make_holder_and_user([hi])

    off = Offseason(
        [holder, user],
        [],
        special_designation_ui_prompt=lambda t, sl: "bogus",
    )
    off._run_special_designation_invitations()
    assert user.special_designation_players == []


def test_special_designation_callback_exception_skips(monkeypatch):
    monkeypatch.setattr(builtins, "input", _fail_input)
    hi = _candidate("Hi", 80)
    holder, user = _make_holder_and_user([hi])

    def raising(_t, _sl):
        raise RuntimeError("can't re-enter readline")

    off = Offseason([holder, user], [], special_designation_ui_prompt=raising)
    off._run_special_designation_invitations()
    assert user.special_designation_players == []


def test_offseason_init_keeps_special_designation_prompt_none_for_cli():
    off = Offseason(teams=[], free_agents=[])
    assert off._special_designation_ui_prompt is None
