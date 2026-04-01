"""大会表示名マッピング（本作固定名）。"""

from basketball_sim.systems.competition_display import (
    competition_category,
    competition_display_name,
)


def test_known_types():
    assert competition_display_name("regular_season") == "日本リーグ"
    assert competition_display_name("emperor_cup") == "全日本カップ"
    assert competition_display_name("easl") == "東アジアトップリーグ"
    assert competition_display_name("asia_cl") == "オールアジアトーナメント"
    assert competition_display_name("intercontinental") == "世界一決定戦"


def test_empty_unknown():
    assert competition_display_name("") == "—"
    assert competition_display_name(None) == "—"
    assert competition_display_name("totally_new_type") == "未分類"


def test_category_buckets():
    assert competition_category("regular_season") == "domestic_league"
    assert competition_category("emperor_cup") == "domestic_cup"
    assert competition_category("easl") == "international_club"
