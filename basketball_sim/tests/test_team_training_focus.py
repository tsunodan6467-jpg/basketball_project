from basketball_sim.models.team import Team


def test_team_training_focus_default():
    t = Team(team_id=1, name="T", league_level=1)
    assert t.team_training_focus == "balanced"


def test_team_training_focus_normalized():
    t = Team(team_id=1, name="T", league_level=1, team_training_focus="invalid")
    assert t.team_training_focus == "balanced"
