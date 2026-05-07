"""O-3 オフシーズンの流れ（閲覧専用）窓: 本文生成関数の文字列テスト。

Tk root を立てずに、`MainMenuView._format_offseason_flow_overview_text` を
非バインドメソッドとして呼び出し、本文が正本データを反映していることを確認する。
"""

from types import SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView
from basketball_sim.systems.offseason_phases import OFFSEASON_PHASES


def _build_text() -> str:
    fake_self = SimpleNamespace()
    return MainMenuView._format_offseason_flow_overview_text(fake_self)


def test_offseason_phases_has_seventeen_entries():
    assert len(list(OFFSEASON_PHASES)) == 17


def test_overview_text_contains_all_phase_ids():
    body = _build_text()
    for i in range(1, 18):
        assert f"[O{i:02d}]" in body, f"missing phase id O{i:02d}"


def test_overview_text_contains_all_phase_titles():
    body = _build_text()
    for pid, title in OFFSEASON_PHASES:
        assert title in body, f"missing title for {pid}: {title}"


def test_overview_text_includes_main_judgment_and_next_focus_keywords():
    body = _build_text()
    assert body.count("主な判断：") == 17
    assert body.count("次に見る：") == 17


def test_overview_text_includes_recommended_pre_check_and_warning():
    body = _build_text()
    assert "今オフ契約満了候補" in body
    assert "応答" in body
    assert "閲覧専用" in body


def test_overview_text_mentions_core_offseason_processes():
    body = _build_text()
    for keyword in ("再契約", "契約満了", "FA", "ドラフト", "財務決算"):
        assert keyword in body, f"missing keyword: {keyword}"


def test_overview_text_is_generated_without_tk_root():
    body = _build_text()
    assert isinstance(body, str)
    assert len(body) > 0
