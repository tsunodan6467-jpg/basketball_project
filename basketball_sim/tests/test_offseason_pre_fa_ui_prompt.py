"""オフ・本格FA直前の手動1人GUI用フックと FA プール除去の最小テスト。"""

from types import SimpleNamespace

from basketball_sim.models.offseason import Offseason
from basketball_sim.systems.offseason_full_fa_tk import remove_player_from_free_agent_pool


class _P:
    def __init__(self, pid: int):
        self.player_id = pid
        self.name = f"p{pid}"


def test_remove_player_from_free_agent_pool_by_identity():
    a, b = _P(1), _P(2)
    pool = [a, b]
    assert remove_player_from_free_agent_pool(pool, a) is True
    assert pool == [b]


def test_remove_player_from_free_agent_pool_by_player_id():
    a, b = _P(1), _P(2)
    pool = [a, b]
    proxy = _P(1)
    assert remove_player_from_free_agent_pool(pool, proxy) is True
    assert pool == [b]


def test_offseason_accepts_pre_conduct_free_agency_ui_prompt():
    def cb(**kw):
        pass

    o = Offseason([], [], pre_conduct_free_agency_ui_prompt=cb)
    assert o._pre_conduct_free_agency_ui_prompt is cb


def test_maybe_run_pre_conduct_free_agency_ui_calls_when_user_team_present():
    ut = SimpleNamespace(name="U", team_id=99, is_user_team=True)
    other = SimpleNamespace(name="C", team_id=1, is_user_team=False)
    teams = [other, ut]
    fa: list = []
    calls = []

    def cb(*, teams, free_agents, user_team):
        calls.append((teams, free_agents, user_team))

    o = Offseason(teams, fa, pre_conduct_free_agency_ui_prompt=cb)
    o._maybe_run_pre_conduct_free_agency_ui()
    assert len(calls) == 1
    assert calls[0][2] is ut
    assert calls[0][1] is fa


def test_maybe_run_pre_conduct_free_agency_ui_skips_without_callback():
    ut = SimpleNamespace(name="U", team_id=99, is_user_team=True)
    o = Offseason([ut], [], pre_conduct_free_agency_ui_prompt=None)
    o._maybe_run_pre_conduct_free_agency_ui()  # no crash


def test_maybe_run_pre_conduct_free_agency_ui_skips_without_user_team():
    t = SimpleNamespace(name="C", team_id=1, is_user_team=False)
    calls = []

    def cb(**kw):
        calls.append(kw)

    o = Offseason([t], [], pre_conduct_free_agency_ui_prompt=cb)
    o._maybe_run_pre_conduct_free_agency_ui()
    assert calls == []
