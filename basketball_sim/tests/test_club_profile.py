"""club_profile: クラブ基礎プロファイル共通器（第1段）。"""

from types import SimpleNamespace

from basketball_sim.systems.club_profile import (
    INITIAL_USER_TEAM_MONEY_NEW_GAME,
    ClubBaseProfile,
    _PROFILE_TEMPLATES,
    _TEAM_ID_PROFILE_OVERRIDES,
    _TEAM_ID_PROFILE_TYPE_V1,
    _USER_INDIVIDUAL_V1_9CLUBS,
    _USER_INDIVIDUAL_V1_SECOND_6CLUBS,
    _USER_INDIVIDUAL_V1_THIRD_6CLUBS,
    _USER_INDIVIDUAL_V1_FOURTH_8CLUBS,
    _club_profile_from_user_sheet_1_5,
    _v1_scale_1_to_5,
    get_club_base_profile,
    get_financial_power_band_1_to_5,
    get_initial_team_money_cpu,
    get_initial_user_team_money,
)


def test_get_club_base_profile_none_is_neutral() -> None:
    p = get_club_base_profile(None)
    assert p == ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 1.0)


def test_get_club_base_profile_never_raises_on_garbage() -> None:
    p = get_club_base_profile(object())
    assert isinstance(p, ClubBaseProfile)
    for v in (p.financial_power, p.market_size, p.arena_grade, p.youth_development_bias, p.win_now_pressure):
        assert 0.85 <= float(v) <= 1.15


def test_get_club_base_profile_missing_attrs_still_bounded() -> None:
    p = get_club_base_profile(SimpleNamespace())
    assert isinstance(p, ClubBaseProfile)


def test_financial_power_scales_with_money_vs_league() -> None:
    low = get_club_base_profile(
        SimpleNamespace(
            league_level=3,
            money=5_000_000,
            market_size=1.0,
            popularity=50,
            arena_level=1,
            training_facility_level=1,
            youth_investment={"facility": 50},
            owner_expectation="playoff_race",
            owner_trust=50,
        )
    )
    high = get_club_base_profile(
        SimpleNamespace(
            league_level=3,
            money=80_000_000,
            market_size=1.0,
            popularity=50,
            arena_level=1,
            training_facility_level=1,
            youth_investment={"facility": 50},
            owner_expectation="playoff_race",
            owner_trust=50,
        )
    )
    assert low.financial_power < high.financial_power


def test_pilot_team_id_override_returns_fixed_profile() -> None:
    """team_id=1 はユーザー確定9クラブの個別値（旧パイロットより優先）。"""
    t1 = SimpleNamespace(
        team_id=1,
        league_level=1,
        money=500_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=5,
        training_facility_level=3,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p1 = get_club_base_profile(t1)
    assert p1 == _USER_INDIVIDUAL_V1_9CLUBS[1]


_TOKYO_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[1]
_OSAKA_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[13]
_UTSUNOMIYA_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[4]
_SHIBUYA_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[12]
_KAWASAKI_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[7]
_FUKUOKA_USER_V1 = _USER_INDIVIDUAL_V1_9CLUBS[29]


def test_osaka_pilot_override_is_team_id_13_not_14() -> None:
    """OPENING_LEAGUE_TEAMS[12] が大阪エビーズ → team_id=13。id=14 は浜松（型テンプレ割当）。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p_osaka = get_club_base_profile(SimpleNamespace(team_id=13, **common))
    p_hamamatsu = get_club_base_profile(SimpleNamespace(team_id=14, **common))
    assert p_osaka == _OSAKA_USER_V1
    assert p_hamamatsu != _OSAKA_USER_V1


def test_phase2_pilot_overrides_team_ids_4_and_12() -> None:
    """宇都宮(4)・渋谷(12): ユーザー確定9クラブの個別値が返る。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p4 = get_club_base_profile(SimpleNamespace(team_id=4, **common))
    p12 = get_club_base_profile(SimpleNamespace(team_id=12, **common))
    assert p4 == _UTSUNOMIYA_USER_V1
    assert p12 == _SHIBUYA_USER_V1


def test_tokyo_user_individual_v1_profile() -> None:
    """東京 team_id=1: ユーザー表ベースの第1版個別。"""
    t1 = SimpleNamespace(
        team_id=1,
        league_level=1,
        money=500_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=5,
        training_facility_level=3,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(t1) == _TOKYO_USER_V1


def test_team_id_7_kawasaki_user_v1_financial_power_is_scale_3() -> None:
    """川崎 team_id=7: financial_power 表3 → 倍率1.0。宇都宮(4)個別と異なる。"""
    assert _v1_scale_1_to_5(3) == 1.0
    assert _KAWASAKI_USER_V1.financial_power == 1.0


def test_team_id_7_non_pilot_same_attrs_differs_from_team_id_4_override() -> None:
    """川崎 team_id=7 はユーザー確定個別。宇都宮(4)個別と一致しない。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p4 = get_club_base_profile(SimpleNamespace(team_id=4, **common))
    p7 = get_club_base_profile(SimpleNamespace(team_id=7, **common))
    assert p4 == _UTSUNOMIYA_USER_V1
    assert p7 == _KAWASAKI_USER_V1
    assert p7 != p4


def test_non_pilot_team_id_uses_estimation_not_override_dict() -> None:
    """同一属性でも team_id=1 はパイロット固定、team_id=2 は別 override で一致しない。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p_pilot = get_club_base_profile(SimpleNamespace(team_id=1, **common))
    p_other = get_club_base_profile(SimpleNamespace(team_id=2, **common))
    assert p_pilot != p_other


def test_opening_league_48_team_ids_all_have_override() -> None:
    """全48クラブに薄い第1版 override（team_id 1..48）。"""
    assert len(_TEAM_ID_PROFILE_OVERRIDES) == 48
    assert set(_TEAM_ID_PROFILE_OVERRIDES.keys()) == set(range(1, 49))
    assert len(_TEAM_ID_PROFILE_TYPE_V1) == 48
    assert set(_TEAM_ID_PROFILE_TYPE_V1.keys()) == set(range(1, 49))
    for p in _TEAM_ID_PROFILE_OVERRIDES.values():
        for v in (p.financial_power, p.market_size, p.arena_grade, p.youth_development_bias, p.win_now_pressure):
            assert 0.94 <= float(v) <= 1.08


def test_profile_type_v1_maps_to_known_templates() -> None:
    for key in _TEAM_ID_PROFILE_TYPE_V1.values():
        assert key in _PROFILE_TEMPLATES


def test_third_priority_team_id_14_hamamatsu_user_sheet_v1() -> None:
    """浜松 team_id=14 は第3優先6のユーザー表個別（旧 regional テンプレではない）。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p14 = get_club_base_profile(SimpleNamespace(team_id=14, **common))
    assert p14 == _USER_INDIVIDUAL_V1_THIRD_6CLUBS[14]
    assert p14 != _PROFILE_TEMPLATES["regional_development"]


def test_user_individual_v1_9_clubs_count_and_fukuoka() -> None:
    assert len(_USER_INDIVIDUAL_V1_9CLUBS) == 9
    assert set(_USER_INDIVIDUAL_V1_9CLUBS.keys()) == {1, 2, 3, 4, 5, 7, 12, 13, 29}
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=29, **common)) == _FUKUOKA_USER_V1


def test_non_pilot_okayama_team_id_48_uses_mid_stable_template() -> None:
    """岡山 team_id=48 は v1 型 mid_stable（非パイロット）。"""
    common = dict(
        league_level=3,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p48 = get_club_base_profile(SimpleNamespace(team_id=48, **common))
    assert p48 == _PROFILE_TEMPLATES["mid_stable"]


def test_team_id_not_in_overrides_falls_back_to_estimation() -> None:
    """team_id が 1..48 外は従来推定（money で fin が動く）。"""
    base = dict(
        league_level=3,
        market_size=1.0,
        popularity=50,
        arena_level=1,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    low = get_club_base_profile(SimpleNamespace(team_id=99, money=5_000_000, **base))
    high = get_club_base_profile(SimpleNamespace(team_id=99, money=80_000_000, **base))
    assert low.financial_power < high.financial_power


def test_initial_user_team_money_fixed_five_hundred_million() -> None:
    """プレイヤー新規開始所持金は帯に依らず 5 億円固定。"""
    assert INITIAL_USER_TEAM_MONEY_NEW_GAME == 500_000_000
    assert get_initial_user_team_money(SimpleNamespace(team_id=1)) == 500_000_000
    assert get_initial_user_team_money(SimpleNamespace(team_id=48)) == 500_000_000


def test_initial_team_money_cpu_band_1_and_5_examples() -> None:
    """CPU 帯テーブル: 帯1=2億・帯5=8億（全48 override のうち該当帯の team_id を探索）。"""
    common = dict(
        league_level=1,
        money=1,
        market_size=1.0,
        popularity=50,
        arena_level=1,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    id1 = id5 = None
    for tid in range(1, 49):
        t = SimpleNamespace(team_id=tid, **common)
        b = get_financial_power_band_1_to_5(t)
        if b == 1 and id1 is None:
            id1 = tid
        if b == 5 and id5 is None:
            id5 = tid
        if id1 is not None and id5 is not None:
            break
    assert id1 is not None and id5 is not None
    assert get_initial_team_money_cpu(SimpleNamespace(team_id=id1, **common)) == 200_000_000
    assert get_initial_team_money_cpu(SimpleNamespace(team_id=id5, **common)) == 800_000_000


def test_win_now_pressure_title_or_bust_high() -> None:
    p = get_club_base_profile(
        SimpleNamespace(
            league_level=1,
            money=100_000_000,
            market_size=1.0,
            popularity=50,
            arena_level=3,
            training_facility_level=2,
            youth_investment={"facility": 50},
            owner_expectation="title_or_bust",
            owner_trust=50,
        )
    )
    assert p.win_now_pressure >= 1.05


def test_user_individual_v1_second_6_clubs_count() -> None:
    assert len(_USER_INDIVIDUAL_V1_SECOND_6CLUBS) == 6
    assert set(_USER_INDIVIDUAL_V1_SECOND_6CLUBS.keys()) == {18, 21, 25, 33, 38, 46}


def test_user_individual_v1_third_6_clubs_count() -> None:
    assert len(_USER_INDIVIDUAL_V1_THIRD_6CLUBS) == 6
    assert set(_USER_INDIVIDUAL_V1_THIRD_6CLUBS.keys()) == {11, 14, 15, 19, 26, 27}


def test_user_individual_v1_fourth_8_clubs_count() -> None:
    assert len(_USER_INDIVIDUAL_V1_FOURTH_8CLUBS) == 8
    assert set(_USER_INDIVIDUAL_V1_FOURTH_8CLUBS.keys()) == {6, 8, 9, 10, 16, 17, 20, 22}


def test_second_priority_sendai_koshigaya_shiga_profiles() -> None:
    """第2優先: 仙台(18)・越谷(21)・滋賀(25) がユーザー表ベースの個別値。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=18, **common)) == _USER_INDIVIDUAL_V1_SECOND_6CLUBS[18]
    assert get_club_base_profile(SimpleNamespace(team_id=21, **common)) == _USER_INDIVIDUAL_V1_SECOND_6CLUBS[21]
    assert get_club_base_profile(SimpleNamespace(team_id=25, **common)) == _USER_INDIVIDUAL_V1_SECOND_6CLUBS[25]


def test_second_priority_nara_38_and_tottori_46_youth_sheet_2_floor() -> None:
    """奈良(38): 勝ち圧表2→1で win_now=0.96。鳥取(46): 下限専用にユーザー表 1,1,1,1,1,2,1。"""
    assert _v1_scale_1_to_5(2) == 0.98
    p38 = _USER_INDIVIDUAL_V1_SECOND_6CLUBS[38]
    p46 = _USER_INDIVIDUAL_V1_SECOND_6CLUBS[46]
    assert p38 == _club_profile_from_user_sheet_1_5(2, 2, 2, 2, 1, 3, 1)
    assert p46 == _club_profile_from_user_sheet_1_5(1, 1, 1, 1, 1, 2, 1)
    assert p38.win_now_pressure == 0.96
    assert p38.youth_development_bias == 1.0
    assert p46.financial_power == 0.96
    assert p46.market_size == 0.96
    assert p46.arena_grade == 0.96
    assert p46.youth_development_bias == 0.98
    assert p46.win_now_pressure == 0.96
    common = dict(
        league_level=3,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=38, **common)) == p38
    assert get_club_base_profile(SimpleNamespace(team_id=46, **common)) == p46


def test_regression_tokyo_1_and_gunma_8_unchanged_after_nara_tottori_youth_tweak() -> None:
    """第2優先の育成微修正が東京(1)・群馬(8)の個別定数に波及していないこと。"""
    assert _TOKYO_USER_V1 == _USER_INDIVIDUAL_V1_9CLUBS[1]
    assert _TOKYO_USER_V1.youth_development_bias == 0.96
    assert _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[8].youth_development_bias == 0.98


def test_second_priority_overrides_pilot_for_team_id_18() -> None:
    """第2優先6が旧パイロット(18)より最終優先。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p18 = get_club_base_profile(SimpleNamespace(team_id=18, **common))
    assert p18 == _USER_INDIVIDUAL_V1_SECOND_6CLUBS[18]
    assert p18.win_now_pressure == 1.015


def test_fourth_priority_nagasaki_team_id_9_fin_youth() -> None:
    """長崎 team_id=9: 第4優先。financial 表4→1.03、育成 表1→0.96。"""
    p9 = _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[9]
    assert p9.financial_power == 1.03
    assert p9.youth_development_bias == 0.96
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=9, **common)) == p9


def test_third_priority_hiroshima_team_id_11_profile() -> None:
    """広島 team_id=11: 第3優先個別（勝ち圧・資金やや高め）。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p11 = get_club_base_profile(SimpleNamespace(team_id=11, **common))
    assert p11 == _USER_INDIVIDUAL_V1_THIRD_6CLUBS[11]
    assert p11.financial_power == 1.03
    assert p11.win_now_pressure == 1.03


def test_third_priority_kobe_team_id_27_market_and_arena() -> None:
    """神戸 team_id=27: market=(表4+表2)/2、arena=表4→1.03。"""
    p27 = _USER_INDIVIDUAL_V1_THIRD_6CLUBS[27]
    assert p27.market_size == round((_v1_scale_1_to_5(4) + _v1_scale_1_to_5(2)) / 2.0, 4)
    assert p27.market_size == 1.005
    assert p27.arena_grade == 1.03
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=27, **common)) == p27


def test_third_priority_akita_team_id_19_overrides_pilot() -> None:
    """秋田 team_id=19: 第3優先が旧パイロットより最終優先。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p19 = get_club_base_profile(SimpleNamespace(team_id=19, **common))
    assert p19 == _USER_INDIVIDUAL_V1_THIRD_6CLUBS[19]


def test_fourth_priority_mikawa_team_id_6_profile() -> None:
    """三河 team_id=6: 第4優先個別。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=6, **common)) == _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[6]


def test_fourth_priority_gunma_team_id_8_overrides_pilot() -> None:
    """群馬 team_id=8: 第4優先が旧パイロットより最終優先。"""
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p8 = get_club_base_profile(SimpleNamespace(team_id=8, **common))
    assert p8 == _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[8]


def test_fourth_priority_yokohama_team_id_16_market_win_now() -> None:
    """横浜 team_id=16: market=(表4+表2)/2=1.005、win_now=(表2+表2)/2=0.98。"""
    p16 = _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[16]
    assert p16.market_size == 1.005
    assert p16.win_now_pressure == 0.98
    common = dict(
        league_level=1,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=16, **common)) == p16


def test_fourth_priority_chiba_etourd_team_id_22_profile() -> None:
    """エルトゥール千葉 team_id=22: 第4優先（地味中立寄りの表値）。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p22 = _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[22]
    assert get_club_base_profile(SimpleNamespace(team_id=22, **common)) == p22
    assert p22.win_now_pressure == 0.98


def test_fourth_priority_saga_team_id_10_profile() -> None:
    """佐賀 team_id=10: 第4優先個別。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    assert get_club_base_profile(SimpleNamespace(team_id=10, **common)) == _USER_INDIVIDUAL_V1_FOURTH_8CLUBS[10]


def test_non_fourth_priority_team_id_23_still_regional_template() -> None:
    """非対象 team_id=23（富山）: 型テンプレ regional_development。"""
    common = dict(
        league_level=2,
        money=50_000_000,
        market_size=1.0,
        popularity=50,
        arena_level=2,
        training_facility_level=1,
        youth_investment={"facility": 50},
        owner_expectation="playoff_race",
        owner_trust=50,
    )
    p23 = get_club_base_profile(SimpleNamespace(team_id=23, **common))
    assert p23 == _PROFILE_TEMPLATES["regional_development"]
