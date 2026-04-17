"""
クラブ基礎プロファイル（第1段・共通器）。

永続フィールドは増やさず、既存 Team 属性から実行時にのみ推定する。
将来、クラブ固有の上書きを載せるための read-only レイヤ。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Final


@dataclass(frozen=True)
class ClubBaseProfile:
    """倍率中心（1.0=中立）。個別クラブ名ベースの本格値は後段。"""

    financial_power: float
    market_size: float
    arena_grade: float
    youth_development_bias: float
    win_now_pressure: float


_NEUTRAL = ClubBaseProfile(1.0, 1.0, 1.0, 1.0, 1.0)

# 全48: `basketball_sim.systems.generator.OPENING_LEAGUE_TEAMS` の index+1 == team_id（ずらさない）。
# 型ラベル→テンプレ: ①strong_capital ②metro_potential ③regional_development ④mid_stable
# ⑤win_now_pressure ⑥neutral_plain。team_id ∉ [1..48] は従来推定へフォールバック。

_PROFILE_TEMPLATES: Final[Dict[str, ClubBaseProfile]] = {
    # 強豪寄り（東京専用よりやや抑えた汎用）
    "strong_capital": ClubBaseProfile(1.06, 1.04, 1.04, 0.98, 1.04),
    # 大都市ポテンシャル
    "metro_potential": ClubBaseProfile(1.02, 1.04, 1.00, 1.00, 1.02),
    # 地方育成寄り
    "regional_development": ClubBaseProfile(0.98, 0.96, 1.02, 1.04, 0.98),
    # 中堅安定
    "mid_stable": ClubBaseProfile(1.02, 1.00, 1.00, 1.00, 1.02),
    # 勝利圧高め
    "win_now_pressure": ClubBaseProfile(1.00, 1.02, 1.00, 0.98, 1.06),
    # 地味中立
    "neutral_plain": ClubBaseProfile(1.00, 1.00, 1.00, 1.00, 1.00),
}

# 第1段12パイロット（変更禁止・本格味付け前の観測ベースライン）
_PILOT_V1_EXACT: Final[Dict[int, ClubBaseProfile]] = {
    1: ClubBaseProfile(1.06, 1.06, 1.04, 0.98, 1.06),
    4: ClubBaseProfile(1.04, 0.96, 1.0, 1.0, 0.98),
    8: ClubBaseProfile(0.96, 0.96, 1.02, 1.06, 0.96),
    12: ClubBaseProfile(1.0, 1.02, 1.04, 0.98, 1.05),
    13: ClubBaseProfile(1.02, 1.06, 0.94, 0.99, 1.02),
    18: ClubBaseProfile(1.0, 1.0, 0.96, 0.98, 1.04),
    21: ClubBaseProfile(1.02, 1.0, 1.0, 1.0, 1.01),
    25: ClubBaseProfile(0.99, 0.98, 1.05, 1.01, 0.99),
    29: ClubBaseProfile(1.0, 1.04, 1.02, 0.98, 1.04),
    33: ClubBaseProfile(0.98, 0.96, 0.98, 0.98, 0.96),
    38: ClubBaseProfile(0.98, 0.96, 1.0, 1.06, 0.96),
    46: ClubBaseProfile(1.0, 0.97, 0.99, 1.0, 0.99),
}


def _v1_scale_1_to_5(n: int) -> float:
    """ユーザー表 1〜5 を既存倍率レンジへ線形マップ（第1版個別）。"""
    return float({1: 0.96, 2: 0.98, 3: 1.0, 4: 1.03, 5: 1.06}[int(n)])


def _club_profile_from_user_sheet_1_5(
    financial_power: int,
    market_size: int,
    popularity_heat: int,
    arena: int,
    win_now_pressure: int,
    youth_development: int,
    win_now_orientation: int,
) -> ClubBaseProfile:
    """7項目→5フィールド。market_size 列と popularity_heat を market_size に、勝利圧2種を win_now_pressure に平均。"""
    return ClubBaseProfile(
        financial_power=round(_v1_scale_1_to_5(financial_power), 4),
        market_size=round(
            (_v1_scale_1_to_5(market_size) + _v1_scale_1_to_5(popularity_heat)) / 2.0,
            4,
        ),
        arena_grade=round(_v1_scale_1_to_5(arena), 4),
        youth_development_bias=round(_v1_scale_1_to_5(youth_development), 4),
        win_now_pressure=round(
            (_v1_scale_1_to_5(win_now_pressure) + _v1_scale_1_to_5(win_now_orientation)) / 2.0,
            4,
        ),
    )


# ユーザー確定9クラブ（型テンプレ・旧パイロットより優先）
_USER_INDIVIDUAL_V1_9CLUBS: Final[Dict[int, ClubBaseProfile]] = {
    1: _club_profile_from_user_sheet_1_5(5, 5, 4, 5, 5, 1, 5),
    2: _club_profile_from_user_sheet_1_5(5, 4, 5, 5, 5, 2, 4),
    3: _club_profile_from_user_sheet_1_5(4, 3, 5, 5, 5, 3, 4),
    4: _club_profile_from_user_sheet_1_5(4, 2, 5, 3, 5, 4, 4),
    5: _club_profile_from_user_sheet_1_5(4, 4, 3, 5, 4, 2, 4),
    7: _club_profile_from_user_sheet_1_5(3, 4, 3, 3, 4, 3, 3),
    12: _club_profile_from_user_sheet_1_5(3, 5, 3, 2, 4, 2, 4),
    13: _club_profile_from_user_sheet_1_5(3, 4, 3, 3, 4, 2, 2),
    29: _club_profile_from_user_sheet_1_5(2, 4, 2, 2, 4, 3, 3),
}

# ユーザー確定 第2優先6クラブ（第1優先9・旧パイロットより後に上書き）
_USER_INDIVIDUAL_V1_SECOND_6CLUBS: Final[Dict[int, ClubBaseProfile]] = {
    18: _club_profile_from_user_sheet_1_5(3, 4, 3, 3, 3, 3, 4),
    21: _club_profile_from_user_sheet_1_5(3, 3, 3, 3, 3, 3, 2),
    25: _club_profile_from_user_sheet_1_5(3, 2, 3, 4, 2, 3, 3),
    33: _club_profile_from_user_sheet_1_5(2, 1, 2, 2, 1, 4, 1),
    38: _club_profile_from_user_sheet_1_5(2, 2, 2, 2, 1, 3, 1),
    46: _club_profile_from_user_sheet_1_5(1, 1, 1, 1, 1, 2, 1),
}

# ユーザー確定 第3優先6クラブ（第2優先6より後に上書き・旧パイロット含め最終優先）
_USER_INDIVIDUAL_V1_THIRD_6CLUBS: Final[Dict[int, ClubBaseProfile]] = {
    11: _club_profile_from_user_sheet_1_5(4, 3, 3, 3, 4, 2, 4),
    14: _club_profile_from_user_sheet_1_5(3, 3, 3, 3, 4, 4, 3),
    15: _club_profile_from_user_sheet_1_5(4, 2, 4, 3, 3, 3, 4),
    19: _club_profile_from_user_sheet_1_5(2, 1, 4, 3, 3, 4, 2),
    26: _club_profile_from_user_sheet_1_5(3, 4, 2, 3, 3, 3, 3),
    27: _club_profile_from_user_sheet_1_5(3, 4, 2, 4, 2, 3, 3),
}

# ユーザー確定 第4優先8クラブ（第3優先6より後に上書き・旧パイロット含め最終優先）
_USER_INDIVIDUAL_V1_FOURTH_8CLUBS: Final[Dict[int, ClubBaseProfile]] = {
    6: _club_profile_from_user_sheet_1_5(3, 3, 4, 3, 4, 3, 3),
    8: _club_profile_from_user_sheet_1_5(4, 4, 4, 4, 4, 2, 4),
    9: _club_profile_from_user_sheet_1_5(4, 3, 4, 4, 4, 1, 4),
    10: _club_profile_from_user_sheet_1_5(3, 3, 3, 4, 3, 3, 3),
    16: _club_profile_from_user_sheet_1_5(3, 4, 2, 3, 2, 2, 2),
    17: _club_profile_from_user_sheet_1_5(3, 3, 3, 3, 3, 2, 4),
    20: _club_profile_from_user_sheet_1_5(2, 2, 2, 3, 2, 3, 2),
    22: _club_profile_from_user_sheet_1_5(3, 3, 3, 3, 2, 3, 2),
}

# v1 canonical club profile types confirmed with user — 第1版正本（再配分禁止・観測の土台）
_TEAM_ID_PROFILE_TYPE_V1: Final[Dict[int, str]] = {
    # --- D1 league_level=1, team_id 1..16 ---
    1: "strong_capital",  # エルバード東京
    2: "metro_potential",  # 千葉ジャイアンツ
    3: "win_now_pressure",  # 琉球プラチナクラウンズ
    4: "win_now_pressure",  # 宇都宮ブレイバーズ
    5: "mid_stable",  # 名古屋ハートホエールズ
    6: "mid_stable",  # ビーホークス三河
    7: "metro_potential",  # 川崎ブレイクライトニング
    8: "regional_development",  # 群馬ブラックボルツ
    9: "regional_development",  # 長崎パルカンズ
    10: "regional_development",  # 佐賀ブーマーズ
    11: "mid_stable",  # 広島タイガーランズ
    12: "metro_potential",  # シンライダーズ渋谷
    13: "metro_potential",  # 大阪エビーズ
    14: "regional_development",  # 浜松サンダーバーズ
    15: "regional_development",  # 島根カグヅチウィザーズ
    16: "metro_potential",  # 横浜パイレーツ
    # --- D2 league_level=2, team_id 17..32 ---
    17: "mid_stable",  # アペカムイ北海道
    18: "mid_stable",  # 仙台46ers
    19: "regional_development",  # 秋田ノースラッキーズ
    20: "mid_stable",  # 茨城メカニックス
    21: "mid_stable",  # 越谷ガンマズ
    22: "metro_potential",  # エルトゥール千葉
    23: "regional_development",  # 富山グリズリーズ
    24: "mid_stable",  # メタル名古屋
    25: "mid_stable",  # 滋賀リバーズ
    26: "metro_potential",  # 京都ホーネッツ
    27: "metro_potential",  # 神戸スパーズ
    28: "regional_development",  # 信州ブレイクストーンズ
    29: "win_now_pressure",  # 福岡ファルコンズ
    30: "mid_stable",  # 熊本バッテリーズ
    31: "regional_development",  # 福島フレイムボムズ
    32: "neutral_plain",  # 福井ストームズ
    # --- D3 league_level=3, team_id 33..48 ---
    33: "regional_development",  # 青森ワルツ
    34: "regional_development",  # 岩手ベアーズ
    35: "regional_development",  # 山形ドラゴンズ
    36: "metro_potential",  # 横浜マーベラス
    37: "mid_stable",  # サミッツ静岡
    38: "regional_development",  # 奈良ディアーズ
    39: "regional_development",  # 愛媛レッドホークス
    40: "mid_stable",  # 鹿児島ナイツ
    41: "mid_stable",  # 新潟エルトロックス
    42: "mid_stable",  # 金沢ニンジャズ
    43: "regional_development",  # 岐阜フォークス
    44: "regional_development",  # 香川スピアーズ
    45: "regional_development",  # 徳島ファイティングス
    46: "regional_development",  # 鳥取サキューズ
    47: "metro_potential",  # 埼玉ライバルズ
    48: "mid_stable",  # 岡山リングス
}


def _build_team_id_profile_overrides_v1() -> Dict[int, ClubBaseProfile]:
    """全48を型→パイロット→第1優先9→第2優先6→第3優先6→第4優先8の順で埋める（重複は後勝ち）。"""
    out: Dict[int, ClubBaseProfile] = {}
    for tid in range(1, 49):
        key = _TEAM_ID_PROFILE_TYPE_V1[tid]
        out[tid] = _PROFILE_TEMPLATES[key]
    for tid, prof in _PILOT_V1_EXACT.items():
        out[tid] = prof
    for tid, prof in _USER_INDIVIDUAL_V1_9CLUBS.items():
        out[tid] = prof
    for tid, prof in _USER_INDIVIDUAL_V1_SECOND_6CLUBS.items():
        out[tid] = prof
    for tid, prof in _USER_INDIVIDUAL_V1_THIRD_6CLUBS.items():
        out[tid] = prof
    for tid, prof in _USER_INDIVIDUAL_V1_FOURTH_8CLUBS.items():
        out[tid] = prof
    return out


_TEAM_ID_PROFILE_OVERRIDES: Final[Dict[int, ClubBaseProfile]] = _build_team_id_profile_overrides_v1()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_team_id(team: Any) -> int:
    try:
        return int(getattr(team, "team_id", 0) or 0)
    except (TypeError, ValueError):
        return 0


def get_club_base_profile(team: Any) -> ClubBaseProfile:
    """
    既存属性のみから推定。欠損・例外時は中立プロファイル。
    Team.market_size（フィールド）とは別物として、ここではプロファイル用の合成倍率を返す。
    """
    if team is None:
        return _NEUTRAL
    try:
        tid = _safe_team_id(team)
        if tid in _TEAM_ID_PROFILE_OVERRIDES:
            return _TEAM_ID_PROFILE_OVERRIDES[tid]

        ll = max(1, min(3, int(getattr(team, "league_level", 2) or 2)))
        money = max(0, int(getattr(team, "money", 0) or 0))
        baseline = {1: 80_000_000, 2: 40_000_000, 3: 20_000_000}.get(ll, 25_000_000)
        financial_power = _clamp(money / float(max(1, baseline)), 0.90, 1.12)

        tm_ms = float(getattr(team, "market_size", 1.0) or 1.0)
        pop = max(1, int(getattr(team, "popularity", 50) or 50))
        market_size = _clamp(tm_ms * (pop / 50.0) ** 0.12, 0.92, 1.08)

        ar = max(1, int(getattr(team, "arena_level", 1) or 1))
        arena_grade = _clamp(0.94 + (ar - 1) * 0.02, 0.92, 1.08)

        tf = max(1, int(getattr(team, "training_facility_level", 1) or 1))
        yi = getattr(team, "youth_investment", None)
        fac_y = 50
        if isinstance(yi, dict):
            fac_y = int(yi.get("facility", 50) or 50)
        youth_development_bias = _clamp(
            0.96 + (tf - 1) * 0.015 + (fac_y - 50) * 0.001,
            0.92,
            1.08,
        )

        exp = str(getattr(team, "owner_expectation", "playoff_race") or "playoff_race").strip().lower()
        trust = int(getattr(team, "owner_trust", 50) or 50)
        if exp in ("title_or_bust", "title_challenge"):
            win_now_pressure = 1.06
        elif exp == "rebuild":
            win_now_pressure = 0.93
        else:
            win_now_pressure = _clamp(0.97 + (trust - 50) * 0.0012, 0.94, 1.06)

        return ClubBaseProfile(
            financial_power=round(financial_power, 4),
            market_size=round(market_size, 4),
            arena_grade=round(arena_grade, 4),
            youth_development_bias=round(youth_development_bias, 4),
            win_now_pressure=round(win_now_pressure, 4),
        )
    except Exception:
        return _NEUTRAL


# --- 新規開始時の所持金（`get_club_base_profile` の financial_power 倍率を 1〜5 帯に量子化） ---
_FP_TO_BAND_LO = 0.96
_FP_TO_BAND_HI = 1.06

_INITIAL_OPENING_CASH_BY_BAND: Final[Dict[int, int]] = {
    1: 200_000_000,
    2: 280_000_000,
    3: 380_000_000,
    4: 550_000_000,
    5: 800_000_000,
}

# プレイヤークラブのみ（CPU 基準額に上乗せ）
USER_TEAM_OPENING_CASH_BONUS_YEN: Final[int] = 70_000_000


def get_financial_power_band_1_to_5(team: Any) -> int:
    """
    `ClubBaseProfile.financial_power`（0.96〜1.06 前後の倍率）を 1〜5 の帯に写像。
    個別表・型テンプレの既存値を正本とし、線形スケールで帯を決める。
    """
    fp = float(get_club_base_profile(team).financial_power)
    fp = _clamp(fp, _FP_TO_BAND_LO, _FP_TO_BAND_HI)
    span = _FP_TO_BAND_HI - _FP_TO_BAND_LO
    t = (fp - _FP_TO_BAND_LO) / span if span > 0 else 0.5
    band = int(round(1.0 + t * 4.0))
    return max(1, min(5, band))


def get_initial_team_money_cpu(team: Any) -> int:
    """CPU クラブの新規開始所持金（資金力帯テーブル）。"""
    b = get_financial_power_band_1_to_5(team)
    return int(_INITIAL_OPENING_CASH_BY_BAND[b])


def get_initial_user_team_money(team: Any) -> int:
    """プレイヤークラブの新規開始所持金（CPU 基準 + 上積み）。"""
    return int(get_initial_team_money_cpu(team) + USER_TEAM_OPENING_CASH_BONUS_YEN)
