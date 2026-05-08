"""O-4a 来年ドラフト候補（閲覧専用）窓: 本文生成関数の文字列テスト。

Tk root を立てずに、`MainMenuView._format_future_draft_pool_overview_text` を
非バインドメソッドとして呼び出し、本文がプール内容を反映していることを確認する。
ドラフト本番処理 / `draft_pool` / `future_draft_pool` / 候補生成ロジック等は
一切呼び出さず、与えた候補リストの読み取りだけで完結する。
"""

from types import SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def _candidate(**kwargs) -> SimpleNamespace:
    base = dict(
        name="候補太郎",
        position="SG",
        age=20,
        ovr=60,
        potential="B",
        nationality="Japan",
        draft_origin_type="college",
        draft_profile_label="",
        is_featured_prospect=False,
        is_reborn=False,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _format(pool) -> str:
    fake_self = SimpleNamespace()
    return MainMenuView._format_future_draft_pool_overview_text(
        fake_self, pool=pool
    )


def test_text_when_pool_is_empty_explains_no_candidates():
    body = _format([])
    assert "来年ドラフト候補（閲覧専用）" in body
    assert "現在、表示できる来年ドラフト候補はいません。" in body
    assert "閲覧専用" in body


def test_text_when_pool_is_none_uses_self_collector_and_returns_empty_message():
    fake_self = SimpleNamespace(team=None, season=None)
    body = MainMenuView._format_future_draft_pool_overview_text(fake_self)
    assert "現在、表示できる来年ドラフト候補はいません。" in body


def test_collector_reads_team_pool_first_without_mutation():
    pool = [
        _candidate(name="自チームA", potential="A", ovr=64),
        _candidate(name="自チームB", potential="C", ovr=58),
    ]
    fake_team = SimpleNamespace(league_future_draft_pool=pool)
    fake_self = SimpleNamespace(team=fake_team, season=None)
    got = MainMenuView._collect_future_draft_pool_candidates(fake_self)
    assert got == pool
    # 元リストの順序は破壊されていない
    assert pool[0].name == "自チームA"
    assert pool[1].name == "自チームB"


def test_collector_falls_back_to_other_team_via_season_all_teams():
    pool = [_candidate(name="他クラブ候補", potential="S", ovr=66)]
    holder_team = SimpleNamespace(league_future_draft_pool=pool)
    user_team = SimpleNamespace(league_future_draft_pool=[])
    season = SimpleNamespace(all_teams=[user_team, holder_team])
    fake_self = SimpleNamespace(team=user_team, season=season)
    got = MainMenuView._collect_future_draft_pool_candidates(fake_self)
    assert got == pool


def test_text_with_candidates_lists_count_and_basic_attrs():
    pool = [
        _candidate(name="山田 太郎", position="SG", age=18, ovr=62, potential="A"),
        _candidate(name="佐藤 次郎", position="PF", age=19, ovr=58, potential="B"),
    ]
    body = _format(pool)
    assert "候補数：2人" in body
    for kw in ("山田 太郎", "SG", "18歳", "OVR 62", "POT A"):
        assert kw in body, f"missing keyword in body: {kw}"
    for kw in ("佐藤 次郎", "PF", "19歳", "OVR 58", "POT B"):
        assert kw in body, f"missing keyword in body: {kw}"


def test_text_includes_origin_label_and_featured_flag():
    pool = [
        _candidate(
            name="注目王",
            potential="S",
            ovr=70,
            draft_origin_type="highschool",
            is_featured_prospect=True,
            draft_profile_label="3&Dウイング",
        )
    ]
    body = _format(pool)
    assert "高校" in body
    assert "注目" in body
    assert "3&Dウイング" in body


def test_text_omits_japan_nationality_label_but_shows_foreign():
    pool_jp = [_candidate(name="ジャパン君", nationality="Japan")]
    body_jp = _format(pool_jp)
    assert "日本" not in body_jp.split("ジャパン君", 1)[1].split("\n", 1)[0]

    pool_fg = [_candidate(name="フォーリン君", nationality="Foreign")]
    body_fg = _format(pool_fg)
    line = body_fg.split("フォーリン君", 1)[1].split("\n", 1)[0]
    assert "外国籍" in line


def test_display_sort_does_not_mutate_input_list():
    p1 = _candidate(name="P1", potential="C", ovr=55, age=22)
    p2 = _candidate(name="P2", potential="S", ovr=70, age=19)
    p3 = _candidate(name="P3", potential="A", ovr=64, age=20)
    original = [p1, p2, p3]
    snapshot = list(original)
    body = _format(original)
    # 元リストの順序は破壊されない
    assert original == snapshot
    # 表示は POT 降順 → OVR 降順 → 年齢昇順 → 名前 で並ぶ想定
    idx_p1 = body.index("P1")
    idx_p2 = body.index("P2")
    idx_p3 = body.index("P3")
    assert idx_p2 < idx_p3 < idx_p1


def test_text_is_generated_without_tk_root():
    body = _format([_candidate(name="単独")])
    assert isinstance(body, str)
    assert len(body) > 0


def test_unknown_attributes_do_not_crash():
    plain = SimpleNamespace(name="最低限", position="C")
    body = _format([plain])
    assert "最低限" in body
    assert "C" in body
    assert "候補数：1人" in body
