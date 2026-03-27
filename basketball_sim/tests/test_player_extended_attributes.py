from basketball_sim.models.player import Player


def test_player_extended_attributes_exist_and_clamped():
    p = Player(
        player_id=1,
        name="P1",
        age=22,
        nationality="Japan",
        position="PG",
        height_cm=180.0,
        weight_kg=75.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=70,
        potential="B",
        archetype="playmaker",
        usage_base=20,
        handling=120,
        iq=0,
        speed=-1,
        power=200,
    )
    assert 1 <= p.handling <= 99
    assert 1 <= p.iq <= 99
    assert 1 <= p.speed <= 99
    assert 1 <= p.power <= 99


def test_player_training_focus_default_and_normalization():
    p = Player(
        player_id=2,
        name="P2",
        age=23,
        nationality="Japan",
        position="SG",
        height_cm=188.0,
        weight_kg=82.0,
        shoot=60,
        three=60,
        drive=60,
        passing=60,
        rebound=60,
        defense=60,
        ft=60,
        stamina=60,
        ovr=71,
        potential="B",
        archetype="scoring_guard",
        usage_base=20,
        training_focus="unknown_focus",
        training_drill="unknown_drill",
    )
    assert p.training_focus == "balanced"
    assert p.training_drill == "balanced"
