"""offseason_progress_cli_display: 表示のみ・落ちないことの軽い検証。"""
from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.offseason_progress_cli_display import (
    build_offseason_focus_summary,
    format_offseason_progress_cli_lines,
)


def test_format_returns_lines_for_valid_phases() -> None:
    o = SimpleNamespace(draft_pool=[], free_agents=[], future_draft_pool=[])
    for n in (1, 11, 13, 17):
        lines = format_offseason_progress_cli_lines(o, n)
        assert lines
        assert lines[0] == "【オフシーズン進行】"
        assert lines[1].startswith("現在:")
        assert "主な判断:" in lines[2] and "次に見る:" in lines[2]


def test_format_invalid_phase_empty() -> None:
    o = SimpleNamespace()
    assert format_offseason_progress_cli_lines(o, 0) == []
    assert format_offseason_progress_cli_lines(o, 99) == []


def test_pending_from_state_o11_o13() -> None:
    o = SimpleNamespace(draft_pool=[object()], free_agents=[object(), object()])
    s11 = build_offseason_focus_summary(o, 11)
    assert "ドラフト候補プールあり" in (s11.get("pending") or [])
    s13 = build_offseason_focus_summary(o, 13)
    assert "FA 候補あり" in (s13.get("pending") or [])


def test_build_summary_tolerates_broken_offseason() -> None:
    o = object()
    s = build_offseason_focus_summary(o, 3)
    assert s.get("phase_id") == "O03"
    assert s.get("main_judgment")
