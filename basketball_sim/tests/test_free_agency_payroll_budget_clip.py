"""`_clip_offer_to_payroll_budget` の挙動固定（`_calculate_offer` から切り出し）。"""

from unittest.mock import patch

from basketball_sim.systems import free_agency as fa_mod


def test_payroll_budget_clip_lambda_first_trial_value():
    assert fa_mod._PAYROLL_BUDGET_CLIP_LAMBDA == 0.1


def test_clip_skips_when_payroll_budget_nonpositive():
    o, r = fa_mod._clip_offer_to_payroll_budget(5_000_000, 100, 0)
    assert o == 5_000_000
    assert r is None
    o2, r2 = fa_mod._clip_offer_to_payroll_budget(5_000_000, 100, -5)
    assert o2 == 5_000_000
    assert r2 is None


def test_clip_zero_room_yields_zero_offer():
    o, r = fa_mod._clip_offer_to_payroll_budget(5_000_000, 10_000_000, 10_000_000)
    assert r == 0
    assert o == 0


def test_clip_when_offer_exceeds_room():
    offer, before, budget = 10_000_000, 0, 5_000_000
    room = 5_000_000
    o, r = fa_mod._clip_offer_to_payroll_budget(offer, before, budget)
    assert r == room
    assert o == room + round(fa_mod._PAYROLL_BUDGET_CLIP_LAMBDA * (offer - room))
    assert o == 5_500_000


def test_clip_passes_through_when_room_large():
    o, r = fa_mod._clip_offer_to_payroll_budget(5_000_000, 0, 100_000_000)
    assert r == 100_000_000
    assert o == 5_000_000


def test_clip_lambda_zero_monkeypatch_matches_legacy_min():
    """λ=0 に戻すと offer>room>0 は min(offer, room) と同値（回帰用）。"""
    offer, before, budget = 10_000_000, 0, 5_000_000
    room = max(0, budget - before)
    with patch.object(fa_mod, "_PAYROLL_BUDGET_CLIP_LAMBDA", 0.0):
        clipped, _ = fa_mod._clip_offer_to_payroll_budget(offer, before, budget)
    assert clipped == min(offer, room)
