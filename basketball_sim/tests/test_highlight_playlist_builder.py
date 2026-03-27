"""build_highlight_playlist_events / build_highlight_override_events_from_match の安全テスト。"""

from basketball_sim.systems import highlight_selector as highlight_selector_mod
from basketball_sim.systems.highlight_selector import (
    HIGHLIGHT_DEFAULT_MAX_EVENTS,
    HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS,
    SYNTHETIC_TIPOFF_PLAY_NO,
    build_highlight_debug_summary,
    build_highlight_override_events_from_match,
    build_highlight_playlist_events,
)
from basketball_sim.systems.presentation_layer import PresentationLayer


class _MatchStub:
    def __init__(self) -> None:
        self.play_sequence_log = [
            {
                "result_type": "made_2",
                "primary_player_name": "A",
                "quarter": 1,
                "clock_seconds": 600,
                "home_score": 2,
                "away_score": 0,
            },
            {
                "result_type": "made_3",
                "primary_player_name": "B",
                "quarter": 1,
                "clock_seconds": 580,
                "home_score": 2,
                "away_score": 3,
            },
            {
                "result_type": "made_2",
                "primary_player_name": "A",
                "quarter": 2,
                "clock_seconds": 400,
                "home_score": 4,
                "away_score": 3,
            },
        ]
        self.is_playoff = False
        self.competition_type = "regular_season"


def test_build_highlight_playlist_preserves_timeline_order():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    assert len(all_events) >= 3
    short = build_highlight_playlist_events(all_events, max_events=2, min_score=0)
    assert len(short) == 2
    nos = [e.get("play_no", -1) for e in short]
    assert nos == sorted(nos)
    assert short[0].get("presentation_type") == "synthetic_tipoff"
    assert short[0].get("play_no") == SYNTHETIC_TIPOFF_PLAY_NO


def test_build_highlight_from_match_returns_subset():
    out = build_highlight_override_events_from_match(_MatchStub(), max_events=HIGHLIGHT_DEFAULT_MAX_EVENTS)
    layer = PresentationLayer(_MatchStub())
    full = layer.build()
    assert len(out) <= len(full) + 1
    assert len(out) <= HIGHLIGHT_DEFAULT_MAX_EVENTS


def test_highlight_playlist_inserts_synthetic_tipoff_and_two_first_half_plays():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    pl = build_highlight_playlist_events(all_events, max_events=10, min_score=0)
    assert pl[0].get("presentation_type") == "synthetic_tipoff"
    fh = [e for e in pl if e.get("quarter") in (1, 2) and e.get("presentation_type") != "synthetic_tipoff"]
    assert len(fh) >= 2


class _MatchStubWithQ1Start:
    def __init__(self) -> None:
        self.play_sequence_log = [
            {
                "result_type": "quarter_start",
                "quarter": 1,
                "clock_seconds": 600,
                "home_score": 0,
                "away_score": 0,
            },
            {
                "result_type": "made_2",
                "primary_player_name": "A",
                "quarter": 1,
                "clock_seconds": 580,
                "home_score": 2,
                "away_score": 0,
            },
        ]
        self.is_playoff = False
        self.competition_type = "regular_season"


class _LongMatchStub:
    def __init__(self, *, is_playoff: bool, competition_type: str) -> None:
        self.is_playoff = is_playoff
        self.competition_type = competition_type
        self.play_sequence_log = []
        home = 0
        away = 0
        # 16イベント程度確保して、文脈ごとの max_events 差を検証する
        for i in range(16):
            quarter = 1 + (i // 4)
            clock = max(0, 600 - (i * 12))
            if i % 2 == 0:
                home += 2
            else:
                away += 2
            self.play_sequence_log.append(
                {
                    "result_type": "made_2",
                    "primary_player_name": f"P{i}",
                    "quarter": quarter,
                    "clock_seconds": clock,
                    "home_score": home,
                    "away_score": away,
                }
            )


def test_reduce_consecutive_replaces_second_of_duplicate_type_with_between_play():
    presentation = [
        {"play_no": 0, "presentation_type": "score_make_3", "quarter": 1, "highlight_score": 50, "highlight_tags": []},
        {"play_no": 1, "presentation_type": "steal", "quarter": 1, "highlight_score": 20, "highlight_tags": []},
        {"play_no": 2, "presentation_type": "score_make_3", "quarter": 1, "highlight_score": 45, "highlight_tags": []},
    ]
    working = [dict(presentation[0]), dict(presentation[2])]
    out = highlight_selector_mod._reduce_consecutive_same_presentation_type(working, presentation)
    assert len(out) == 2
    assert out[1]["presentation_type"] == "steal"
    assert out[1].get("play_no") == 1


def test_highlight_uses_log_q1_quarter_start_instead_of_synthetic():
    layer = PresentationLayer(_MatchStubWithQ1Start())
    all_events = layer.build()
    pl = build_highlight_playlist_events(all_events, max_events=10, min_score=0)
    assert pl[0].get("presentation_type") == "quarter_start"
    assert pl[0].get("quarter") == 1
    assert not any(e.get("presentation_type") == "synthetic_tipoff" for e in pl)


def test_context_aware_max_events_for_highlight_mode():
    regular_out = build_highlight_override_events_from_match(
        _LongMatchStub(is_playoff=False, competition_type="regular_season"),
        max_events=None,
        min_score=0,
    )
    playoff_out = build_highlight_override_events_from_match(
        _LongMatchStub(is_playoff=True, competition_type="playoff"),
        max_events=None,
        min_score=0,
    )
    cup_out = build_highlight_override_events_from_match(
        _LongMatchStub(is_playoff=False, competition_type="emperor_cup"),
        max_events=None,
        min_score=0,
    )
    assert len(regular_out) == 10
    assert len(playoff_out) == 12
    assert len(cup_out) == 14


def test_playlist_respects_total_seconds_cap():
    layer = PresentationLayer(_LongMatchStub(is_playoff=False, competition_type="regular_season"))
    all_events = layer.build()
    pl = build_highlight_playlist_events(
        all_events,
        max_events=14,
        min_score=0,
        max_total_seconds=HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS,
    )
    total = sum(highlight_selector_mod._estimate_clip_seconds(e) for e in pl)
    assert total <= HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS


def test_override_respects_custom_total_seconds_cap():
    out = build_highlight_override_events_from_match(
        _LongMatchStub(is_playoff=False, competition_type="regular_season"),
        max_events=14,
        min_score=0,
        max_total_seconds=60,
    )
    total = sum(highlight_selector_mod._estimate_clip_seconds(e) for e in out)
    assert total <= 60


def test_dedupe_same_possession_keeps_higher_score():
    working = [
        {"play_no": 10, "highlight_score": 30, "raw_play": {"possession_no": 77}},
        {"play_no": 11, "highlight_score": 55, "raw_play": {"possession_no": 77}},
        {"play_no": 12, "highlight_score": 40, "raw_play": {"possession_no": 78}},
    ]
    out = highlight_selector_mod._dedupe_same_possession_keep_best(working)
    assert len(out) == 2
    assert any(e.get("play_no") == 11 for e in out)
    assert not any(e.get("play_no") == 10 for e in out)


def test_limit_focus_player_concentration_replaces_crowded_player():
    working = [
        {"play_no": 1, "highlight_score": 70, "focus_player_name": "Ace"},
        {"play_no": 2, "highlight_score": 68, "focus_player_name": "Ace"},
        {"play_no": 3, "highlight_score": 66, "focus_player_name": "Ace"},
        {"play_no": 4, "highlight_score": 60, "focus_player_name": "Role"},
    ]
    presentation = [
        *working,
        {"play_no": 5, "highlight_score": 59, "focus_player_name": "BenchA"},
        {"play_no": 6, "highlight_score": 58, "focus_player_name": "BenchB"},
    ]
    out = highlight_selector_mod._limit_focus_player_concentration(working, presentation, max_events=6)
    ace_count = sum(1 for e in out if e.get("focus_player_name") == "Ace")
    assert ace_count <= 2


def test_assign_highlight_tier_and_force_s():
    force_event = {
        "presentation_type": "score_make_2",
        "highlight_score": 28,
        "highlight_tags": ["lead_change", "clutch"],
        "quarter": 4,
        "clock_seconds": 20,
    }
    assert highlight_selector_mod._is_force_s_event(force_event) is True
    assert highlight_selector_mod._assign_highlight_tier(force_event) == "S"

    a_event = {"highlight_score": 35, "highlight_tags": [], "quarter": 2, "clock_seconds": 300}
    b_event = {"highlight_score": 20, "highlight_tags": [], "quarter": 1, "clock_seconds": 500}
    n_event = {"highlight_score": 10, "highlight_tags": [], "quarter": 1, "clock_seconds": 500}
    assert highlight_selector_mod._assign_highlight_tier(a_event) == "A"
    assert highlight_selector_mod._assign_highlight_tier(b_event) == "B"
    assert highlight_selector_mod._assign_highlight_tier(n_event) == "none"


def test_select_tiered_highlights_prioritizes_force_s():
    presentation = [
        {"play_no": 1, "presentation_type": "score_make_2", "highlight_score": 55, "highlight_tags": [], "quarter": 2, "clock_seconds": 200},
        {"play_no": 2, "presentation_type": "score_make_2", "highlight_score": 54, "highlight_tags": [], "quarter": 2, "clock_seconds": 180},
        {"play_no": 3, "presentation_type": "score_make_2", "highlight_score": 22, "highlight_tags": ["lead_change", "clutch"], "quarter": 4, "clock_seconds": 20},
    ]
    out = highlight_selector_mod._select_tiered_highlights_timeline(presentation, top_n=2, min_score=0)
    assert len(out) == 2
    assert any(e.get("play_no") == 3 for e in out)


def test_playlist_contains_plan_metadata_fields():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    out = build_highlight_playlist_events(all_events, max_events=6, min_score=0)
    assert out
    first = out[0]
    assert "clip_order" in first
    assert "estimated_clip_seconds" in first
    assert "emphasis_level" in first
    assert "clip_role" in first
    assert "recommended_camera_style" in first
    assert "selection_reason" in first
    assert "selection_reasons" in first
    assert isinstance(first["selection_reasons"], list)
    # clip_order is sequential
    assert [e.get("clip_order") for e in out] == list(range(len(out)))


def test_playlist_adds_opening_selection_reason():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    out = build_highlight_playlist_events(all_events, max_events=6, min_score=0)
    assert out
    assert out[0].get("selection_reason") in {"opening_synthetic_tipoff", "opening_q1_start"}


def test_build_highlight_debug_summary_contains_core_sections():
    layer = PresentationLayer(_MatchStub())
    all_events = layer.build()
    out = build_highlight_playlist_events(all_events, max_events=6, min_score=0)
    text = build_highlight_debug_summary(out)
    assert "count=" in text
    assert "tiers=" in text
    assert "styles=" in text
    assert "reasons=" in text


def test_context_preset_helper_selects_expected_values():
    regular = highlight_selector_mod._get_context_preset(is_playoff=False, is_big_stage=False)
    playoff = highlight_selector_mod._get_context_preset(is_playoff=True, is_big_stage=False)
    big_stage = highlight_selector_mod._get_context_preset(is_playoff=False, is_big_stage=True)
    assert regular.max_events == 10
    assert playoff.max_events == 12
    assert big_stage.max_events == 14


def test_validate_highlight_context_presets_returns_true_for_current_config():
    assert highlight_selector_mod.validate_highlight_context_presets() is True


def test_build_safe_highlight_context_presets_falls_back_on_invalid_values():
    bad_table = {
        "regular": {"max_events": 0, "min_score": -1, "max_total_seconds": 0},
        "playoff": {"max_events": "x", "min_score": 10, "max_total_seconds": 200},
    }
    safe = highlight_selector_mod._build_safe_highlight_context_presets(bad_table)
    assert safe["regular"].max_events == 10
    assert safe["regular"].min_score == 18
    assert safe["regular"].max_total_seconds == 180
    # missing big_stage should be backfilled
    assert "big_stage" in safe


def test_shape_finale_order_moves_climax_to_last():
    events = [
        {"play_no": 1, "quarter": 1, "clock_seconds": 590, "highlight_score": 25, "highlight_tier": "B"},
        {"play_no": 2, "quarter": 2, "clock_seconds": 420, "highlight_score": 40, "highlight_tier": "A"},
        {"play_no": 3, "quarter": 4, "clock_seconds": 80, "highlight_score": 62, "highlight_tier": "S", "clip_role": "key_play"},
        {"play_no": 4, "quarter": 3, "clock_seconds": 200, "highlight_score": 44, "highlight_tier": "A"},
        {"play_no": 5, "quarter": 4, "clock_seconds": 15, "highlight_score": 38, "highlight_tier": "S", "force_tier": "S"},
    ]
    out = highlight_selector_mod._shape_finale_order(events)
    assert out[-1].get("play_no") == 5
