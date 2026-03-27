from basketball_sim.systems.highlight_camera_system import build_highlight_camera_events_from_presentation


def test_camera_uses_style_and_emphasis_hints():
    presentation_events = [
        {
            "play_no": 1,
            "quarter": 4,
            "clock_seconds": 20,
            "presentation_type": "score_make_2",
            "highlight_score": 35,
            "highlight_tags": ["clutch", "lead_change"],
            "highlight_tier": "S",
            "force_tier": "S",
            "emphasis_level": "max",
            "clip_role": "climax",
            "recommended_camera_style": "cinematic",
            "focus_player_name": "A",
            "support_player_name": "B",
            "team_side": "home",
            "importance": "high",
        }
    ]
    out = build_highlight_camera_events_from_presentation(presentation_events)
    assert len(out) == 1
    ev = out[0]
    assert ev.get("camera_level") == "top_play"
    assert ev.get("cut_type") == "hero_cut"
    assert ev.get("zoom_level") == "dramatic_close"
    assert ev.get("transition_profile") == "focus_shift"


def test_camera_keeps_boundary_rules_even_with_hints():
    presentation_events = [
        {
            "play_no": 0,
            "quarter": 1,
            "clock_seconds": 600,
            "presentation_type": "synthetic_tipoff",
            "highlight_score": 0,
            "highlight_tags": [],
            "highlight_tier": "B",
            "emphasis_level": "max",
            "recommended_camera_style": "cinematic",
            "clip_role": "opening",
            "importance": "low",
        }
    ]
    out = build_highlight_camera_events_from_presentation(presentation_events)
    assert len(out) == 1
    ev = out[0]
    assert ev.get("camera_level") == "normal"
    assert ev.get("zoom_level") == "scoreboard"
    assert ev.get("cut_type") == "hard_cut"
