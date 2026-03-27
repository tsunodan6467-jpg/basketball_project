from basketball_sim.systems.development import DevelopmentSystem


def test_focus_age_multiplier_monotonic():
    assert DevelopmentSystem._get_focus_age_multiplier(19) > DevelopmentSystem._get_focus_age_multiplier(25)
    assert DevelopmentSystem._get_focus_age_multiplier(25) > DevelopmentSystem._get_focus_age_multiplier(30)


def test_focus_gp_multiplier_monotonic():
    assert DevelopmentSystem._get_focus_gp_multiplier(0.90) > DevelopmentSystem._get_focus_gp_multiplier(0.70)
    assert DevelopmentSystem._get_focus_gp_multiplier(0.70) >= DevelopmentSystem._get_focus_gp_multiplier(0.45)
