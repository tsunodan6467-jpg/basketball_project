"""O-4b FA市場（閲覧専用）窓: 本文生成関数の文字列テスト。

Tk root を立てずに、`MainMenuView._format_fa_market_overview_text` を
非バインドメソッドとして呼び出し、本文がプール内容を反映していることを確認する。
FA 獲得処理 / `sign_free_agent` / `precheck_user_fa_sign` / `conduct_free_agency`
等は一切呼び出さず、与えた候補リストの読み取りだけで完結する。
"""

from types import SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def _candidate(**kwargs) -> SimpleNamespace:
    base = dict(
        name="FA太郎",
        position="SG",
        age=28,
        ovr=70,
        potential="B",
        nationality="Japan",
        salary=30_000_000,
        fa_pool_market_salary=0,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _format(pool) -> str:
    fake_self = SimpleNamespace()
    return MainMenuView._format_fa_market_overview_text(fake_self, pool=pool)


def test_text_when_pool_is_empty_explains_no_candidates():
    body = _format([])
    assert "FA市場（閲覧専用）" in body
    assert "現在、表示できるFA候補はいません。" in body
    assert "閲覧専用" in body
    assert "インシーズンFA" in body


def test_text_when_pool_is_none_uses_self_collector_and_returns_empty_message():
    fake_self = SimpleNamespace(team=None, season=None)
    body = MainMenuView._format_fa_market_overview_text(fake_self)
    assert "現在、表示できるFA候補はいません。" in body


def test_collector_reads_season_free_agents_first_without_mutation():
    pool = [
        _candidate(name="シーズン由来A", ovr=72),
        _candidate(name="シーズン由来B", ovr=66),
    ]
    season = SimpleNamespace(free_agents=pool)
    fake_self = SimpleNamespace(team=None, season=season)
    got = MainMenuView._collect_fa_market_candidates(fake_self)
    assert got == pool
    assert pool[0].name == "シーズン由来A"
    assert pool[1].name == "シーズン由来B"


def test_collector_falls_back_to_self_free_agents_when_season_lacks_attr():
    pool = [_candidate(name="self由来", ovr=68)]
    season = SimpleNamespace()  # free_agents 属性なし
    fake_self = SimpleNamespace(team=None, season=season, free_agents=pool)
    got = MainMenuView._collect_fa_market_candidates(fake_self)
    assert got == pool


def test_collector_returns_empty_when_no_source_available():
    fake_self = SimpleNamespace()
    got = MainMenuView._collect_fa_market_candidates(fake_self)
    assert got == []


def test_text_with_candidates_lists_count_and_basic_attrs():
    pool = [
        _candidate(
            name="山田 太郎",
            position="SG",
            age=28,
            ovr=72,
            potential="B",
            nationality="Japan",
            salary=30_000_000,
        ),
        _candidate(
            name="John Smith",
            position="PF",
            age=30,
            ovr=70,
            potential="C",
            nationality="Foreign",
            salary=45_000_000,
        ),
    ]
    body = _format(pool)
    assert "候補数：2人" in body
    for kw in ("山田 太郎", "SG", "28歳", "OVR 72", "POT B", "日本"):
        assert kw in body, f"missing keyword in body: {kw}"
    for kw in ("John Smith", "PF", "30歳", "OVR 70", "POT C", "外国籍"):
        assert kw in body, f"missing keyword in body: {kw}"


def test_salary_estimate_prefers_fa_pool_market_salary():
    p = _candidate(
        name="目安持ち",
        salary=10_000_000,
        fa_pool_market_salary=99_000_000,
    )
    body = _format([p])
    line = body.split("目安持ち", 1)[1].split("\n", 1)[0]
    assert "年俸目安" in line
    # 99,000,000 → 9900万円 (`format_money_yen_ja_readable` の100万円単位切り捨て)
    assert "9900万円" in line


def test_salary_falls_back_to_salary_when_fa_pool_market_zero():
    p = _candidate(
        name="現年俸のみ",
        salary=20_000_000,
        fa_pool_market_salary=0,
    )
    body = _format([p])
    line = body.split("現年俸のみ", 1)[1].split("\n", 1)[0]
    assert "年俸目安" in line
    assert "2000万円" in line


def test_salary_omitted_when_both_zero():
    p = _candidate(name="年俸不明", salary=0, fa_pool_market_salary=0)
    body = _format([p])
    line = body.split("年俸不明", 1)[1].split("\n", 1)[0]
    assert "年俸目安" not in line


def test_nationality_labels_are_japanese():
    cases = [
        ("日本君", "Japan", "日本"),
        ("外国君", "Foreign", "外国籍"),
        ("アジア君", "Asia", "アジア"),
        ("帰化君", "Naturalized", "帰化"),
    ]
    pool = [_candidate(name=n, nationality=k) for n, k, _ in cases]
    body = _format(pool)
    for n, _k, expected in cases:
        line = body.split(n, 1)[1].split("\n", 1)[0]
        assert expected in line, f"missing '{expected}' for {n}"


def test_display_sort_does_not_mutate_input_list():
    p1 = _candidate(name="LowOvr", ovr=55, potential="C", age=22)
    p2 = _candidate(name="HighOvr", ovr=78, potential="A", age=29)
    p3 = _candidate(name="MidOvr", ovr=66, potential="B", age=24)
    original = [p1, p2, p3]
    snapshot = list(original)
    body = _format(original)
    # 元リストの順序は破壊されない
    assert original == snapshot
    # 表示は OVR 降順 → POT 降順 → 年齢昇順 → 名前 で並ぶ想定
    idx_p1 = body.index("LowOvr")
    idx_p2 = body.index("HighOvr")
    idx_p3 = body.index("MidOvr")
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


def test_no_acquisition_buttons_text_in_body():
    body = _format([_candidate(name="観るだけ太郎")])
    # 閲覧専用なので「契約する」「獲得する」等の操作語は本文に含めない
    forbidden = ("契約する", "獲得する", "FAを獲る", "交渉する")
    for token in forbidden:
        assert token not in body, f"forbidden operation token in body: {token}"
