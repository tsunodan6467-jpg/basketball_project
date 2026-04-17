"""オークション指名: 正本帯の基準額・落札年俸固定3年・移籍/再契約除外。"""

import pickle

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import (
    advance_contract_years,
    apply_contract_extension,
    apply_resign,
    clear_auction_rookie_contract_for_market_entry,
    is_auction_rookie_contract_active,
)
from basketball_sim.systems.draft_auction import (
    TIER_CONFIGS,
    _add_player_to_team_and_trim,
    _compute_charge_increment,
    _max_affordable_bid,
    _set_drafted_player_contract,
)
from basketball_sim.systems.trade import _is_tradeable_player
from basketball_sim.systems.trade_logic import TradeSystem


def _player(pid: int) -> Player:
    return Player(
        player_id=pid,
        name=f"P{pid}",
        age=19,
        nationality="Japan",
        position="PG",
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
        ovr=72,
        potential="A",
        archetype="guard",
        usage_base=20,
        salary=0,
        contract_years_left=0,
        contract_total_years=0,
        team_id=None,
    )


def test_tier_min_prices_v11_order():
    assert TIER_CONFIGS["T1"].min_price_low >= 25_000_000
    assert TIER_CONFIGS["T2"].min_price_high <= 20_000_000
    assert TIER_CONFIGS["T3"].min_price_high <= 11_000_000
    assert TIER_CONFIGS["T1"].min_price_low > TIER_CONFIGS["T2"].min_price_high
    assert TIER_CONFIGS["T2"].min_price_low > TIER_CONFIGS["T3"].min_price_high


def test_set_drafted_contract_uses_bid_and_locks_three_years():
    p = _player(9001)
    _set_drafted_player_contract(p, "A", 45_000_000)
    assert p.salary == 45_000_000
    assert p.draft_rookie_locked_salary == 45_000_000
    assert p.contract_years_left == 3
    assert p.is_draft_rookie_contract
    assert "rookie_lock_3y" in p.acquisition_note


def test_high_hammer_55m_affordable_with_tax():
    t = Team(team_id=1, name="T", league_level=1, money=5_000_000_000, players=[])
    t.rookie_budget = 120_000_000
    t.rookie_budget_remaining = 120_000_000
    cap = 120_000_000
    ch55, _ = _compute_charge_increment(t, 55_000_000, cap)
    assert ch55 == 55_000_000
    ch130, _ = _compute_charge_increment(t, 130_000_000, cap)
    assert ch130 > 130_000_000
    assert ch130 <= 120_000_000 + 30_000_000 + 20_000_000
    max_b = _max_affordable_bid(t, cap, 27_000_000)
    assert max_b >= 55_000_000


def test_advance_three_years_then_fa_clears_rookie_flags():
    t = Team(team_id=2, name="T2", league_level=2, money=1_000_000_000, players=[])
    p = _player(9002)
    _set_drafted_player_contract(p, "B", 8_000_000)
    t.players = [p]
    p.team_id = t.team_id
    fa: list = []
    advance_contract_years([t], fa)
    assert p.contract_years_left == 2
    assert p.salary == 8_000_000
    advance_contract_years([t], fa)
    assert p.contract_years_left == 1
    assert p.salary == 8_000_000
    advance_contract_years([t], fa)
    assert p not in t.players
    assert p in fa
    assert not p.is_draft_rookie_contract
    assert int(getattr(p, "draft_rookie_locked_salary", 0) or 0) == 0


def test_trade_blocked_for_draft_rookie():
    t = Team(team_id=3, name="T3", league_level=3, money=1_000_000_000, players=[])
    p = _player(9003)
    _set_drafted_player_contract(p, "A", 30_000_000)
    t.players = [p]
    assert _is_tradeable_player(p, t) is False


def test_trade_system_rejects_sending_draft_rookie():
    ta = Team(team_id=10, name="A", league_level=1, money=1_000_000_000, players=[])
    tb = Team(team_id=11, name="B", league_level=1, money=1_000_000_000, players=[])
    pa = _player(9010)
    pb = _player(9011)
    _set_drafted_player_contract(pa, "A", 12_000_000)
    pa.salary = 12_000_000
    pb.salary = 8_000_000
    pb.contract_years_left = 2
    ta.players = [pa]
    tb.players = [pb]
    ts = TradeSystem()
    ev = ts.evaluate_trade_for_team(ta, pa, pb)
    assert ev.accepts is False
    assert "draft_rookie_locked" in ev.reasons


def test_apply_resign_does_not_override_rookie():
    t = Team(team_id=4, name="T4", league_level=1, money=1_000_000_000, players=[])
    p = _player(9004)
    _set_drafted_player_contract(p, "A", 31_000_000)
    t.players = [p]
    apply_resign(t, p, 80_000_000, 2)
    assert p.salary == 31_000_000
    assert p.contract_years_left == 3


def test_apply_contract_extension_false_for_rookie():
    t = Team(team_id=5, name="T5", league_level=1, money=1_000_000_000, players=[])
    p = _player(9005)
    _set_drafted_player_contract(p, "A", 20_000_000)
    t.players = [p]
    assert apply_contract_extension(t, p, add_years=1) is False
    assert p.contract_years_left == 3


def test_legacy_property_setters_mirror_draft_fields():
    p = _player(9402)
    p.is_auction_rookie_contract = True
    p.auction_rookie_locked_salary = 5_000_000
    assert p.is_draft_rookie_contract
    assert p.draft_rookie_locked_salary == 5_000_000


def test_legacy_auction_rookie_contract_helpers_delegate_to_draft():
    p = _player(9503)
    _set_drafted_player_contract(p, "A", 12_000_000)
    assert is_auction_rookie_contract_active(p) is True
    clear_auction_rookie_contract_for_market_entry(p)
    assert not p.is_draft_rookie_contract
    assert int(getattr(p, "draft_rookie_locked_salary", 0) or 0) == 0


def test_legacy___dict___old_save_rookie_keys_migrate_on_post_init():
    p = _player(9401)
    p.__dict__["is_auction_rookie_contract"] = True
    p.__dict__["auction_rookie_locked_salary"] = 8_888_000
    Player.__post_init__(p)
    assert p.is_draft_rookie_contract
    assert p.draft_rookie_locked_salary == 8_888_000


def test_snake_draft_contract_same_rookie_flags_and_three_years():
    import random

    from basketball_sim.systems.draft import _add_drafted_player_contract

    random.seed(42)
    p = _player(9201)
    _add_drafted_player_contract(p, 3)
    assert p.contract_years_left == 3
    assert p.is_draft_rookie_contract
    assert 25_000_000 <= p.salary <= 35_000_000
    assert p.draft_rookie_locked_salary == p.salary


def test_snake_draft_mid_pick_band():
    import random

    from basketball_sim.systems.draft import _add_drafted_player_contract

    random.seed(7)
    p = _player(9204)
    _add_drafted_player_contract(p, 18)
    assert 12_000_000 <= p.salary <= 20_000_000


def test_snake_draft_late_pick_band():
    import random

    from basketball_sim.systems.draft import _add_drafted_player_contract

    random.seed(11)
    p = _player(9205)
    _add_drafted_player_contract(p, 30)
    assert 5_000_000 <= p.salary <= 10_000_000


def test_snake_draft_advance_years_preserves_salary():
    import random

    from basketball_sim.systems.draft import _add_drafted_player_contract

    random.seed(1)
    t = Team(team_id=21, name="S", league_level=1, money=1_000_000_000, players=[])
    p = _player(9202)
    _add_drafted_player_contract(p, 10)
    sal = p.salary
    t.players = [p]
    fa: list = []
    advance_contract_years([t], fa)
    assert p.contract_years_left == 2
    assert p.salary == sal
    assert p in t.players


def test_snake_rookie_not_tradeable():
    import random

    from basketball_sim.systems.draft import _add_drafted_player_contract

    random.seed(3)
    t = Team(team_id=22, name="S2", league_level=2, money=1_000_000_000, players=[])
    p = _player(9203)
    _add_drafted_player_contract(p, 20)
    t.players = [p]
    assert _is_tradeable_player(p, t) is False


def test_pickle_roundtrip_persists_only_draft_rookie_keys_in_dict():
    p = _player(9301)
    _set_drafted_player_contract(p, "B", 9_000_000)
    st = p.__getstate__()
    assert st.get("is_draft_rookie_contract") is True
    assert st.get("draft_rookie_locked_salary") == 9_000_000
    assert "is_auction_rookie_contract" not in st
    assert "auction_rookie_locked_salary" not in st

    p2 = pickle.loads(pickle.dumps(p))
    assert p2.is_draft_rookie_contract
    assert p2.draft_rookie_locked_salary == 9_000_000
    assert "is_auction_rookie_contract" not in p2.__dict__
    assert "auction_rookie_locked_salary" not in p2.__dict__


def test___setstate___migrates_legacy_saved_rookie_keys_from_dict():
    p = _player(9302)
    _set_drafted_player_contract(p, "A", 15_000_000)
    legacy = dict(p.__dict__)
    legacy.pop("is_draft_rookie_contract", None)
    legacy.pop("draft_rookie_locked_salary", None)
    legacy["is_auction_rookie_contract"] = True
    legacy["auction_rookie_locked_salary"] = 15_000_000

    q = Player.__new__(Player)
    q.__setstate__(legacy)
    assert q.is_draft_rookie_contract
    assert q.draft_rookie_locked_salary == 15_000_000
    assert "is_auction_rookie_contract" not in q.__dict__
    assert "auction_rookie_locked_salary" not in q.__dict__


def _roster_filler(pid: int, *, ovr: int = 80) -> Player:
    p = _player(pid)
    p.ovr = ovr
    p.salary = 5_000_000
    p.contract_years_left = 2
    p.contract_total_years = 2
    return p


def test_auction_rookie_overflow_to_fa_clears_draft_rookie_lock():
    """枠 overflow で落札新人が即 FA へ出るとき、ドラフト固定契約フラグを外す。"""
    team = Team(team_id=77, name="FullRoster", league_level=1, money=2_000_000_000, players=[])
    for i in range(13):
        pl = _roster_filler(7700 + i, ovr=78)
        pl.team_id = team.team_id
        team.players.append(pl)

    rookie = _player(77099)
    _set_drafted_player_contract(rookie, "A", 31_074_194)
    assert rookie.is_draft_rookie_contract
    assert rookie.draft_rookie_locked_salary == 31_074_194

    fa: list = []
    _add_player_to_team_and_trim(team, rookie, fa)

    assert rookie not in team.players
    assert rookie in fa
    assert rookie.is_draft_rookie_contract is False
    assert int(getattr(rookie, "draft_rookie_locked_salary", 0) or 0) == 0


def test_conduct_free_agency_clears_stale_draft_rookie_lock_and_advance_keeps_fa_salary(monkeypatch):
    """オークション相当のロック付き選手が FA にいる状態でオフ FA 成立 → ロック解除。翌 advance で落札額に戻らない。"""
    from basketball_sim.systems import free_agency as fa_mod
    from basketball_sim.systems.free_agency import conduct_free_agency

    monkeypatch.setattr(fa_mod, "fa_roll_accept_offer", lambda score: True)
    monkeypatch.setattr(fa_mod, "_calculate_offer", lambda team, player: 8_555_000)

    fillers = [_roster_filler(8800 + i) for i in range(12)]
    team = Team(team_id=88, name="SignTeam", league_level=3, money=5_000_000_000, players=list(fillers))
    for pl in team.players:
        pl.team_id = team.team_id
    team.payroll_budget = 9_000_000_000

    rookie = _player(88888)
    _set_drafted_player_contract(rookie, "A", 31_074_194)
    rookie.contract_years_left = 0
    rookie.team_id = None

    free_agents = [rookie]
    conduct_free_agency([team], free_agents)

    assert rookie in team.players
    assert rookie.salary == 8_555_000
    assert rookie.is_draft_rookie_contract is False
    assert int(getattr(rookie, "draft_rookie_locked_salary", 0) or 0) == 0
    assert "fa_signed_by_" in str(getattr(rookie, "acquisition_note", "") or "")

    advance_contract_years([team], [])
    assert rookie.salary == 8_555_000
    assert int(getattr(rookie, "draft_rookie_locked_salary", 0) or 0) == 0
