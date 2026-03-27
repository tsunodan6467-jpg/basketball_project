"""
試合ルール・セーブ識別など、後から一括変更したい値の単一ソース（Phase 0）。

UI文言や実況テキストは localization / 各モジュールのテンプレに置く。
ここは数値・識別子・バージョン番号中心。
"""

from __future__ import annotations

# セーブ blob 内のペイロード互換用（フィールド追加時に上げる）
PAYLOAD_SCHEMA_VERSION = 1

# save_load.GAME_ID と一致させる（外部インポートで参照する場合用）
GAME_ID = "basketball_sim"

# 規定: 4 クォーター（延長は Match 側で別処理）
REGULATION_QUARTERS = 4

# 試合時計の秒数（10 分＝600 秒）。ポゼッション時計の近似に使用。
CLOCK_SECONDS_PER_REGULATION_QUARTER = 600

# 不戦敗などの規定得点差（勝者側スコア）
FORFEIT_SCORE = 20

# 試合成立に必要なアクティブ登録の最低人数（Match と整合）
MINIMUM_ACTIVE_PLAYERS_FOR_GAME = 7

# 本契約ロスター（Step 1: ユース・特別指定は別リスト）
CONTRACT_ROSTER_MAX = 13
# シーズン開幕時の最低人数（未達は警告・将来の強制用に予約）
CONTRACT_ROSTER_MIN_SEASON = 10

# B リーグ風・国内リーグ基準（試合登録 / オンコート）
# Match.COMPETITION_RULES の regular_season / playoff / final_boss と整合
LEAGUE_ROSTER_FOREIGN_CAP = 3
LEAGUE_ROSTER_ASIA_NATURALIZED_CAP = 1
LEAGUE_ONCOURT_FOREIGN_CAP = 2
LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP = 1

# サラリー（Step 3: リーグキャップ・ソフト上限・贅沢税の単一ソース）
# 金額はすべて円。D1 ソフトキャップ = ハード × SALARY_SOFT_LIMIT_MULTIPLIER（既定 1.2）→ 12億円。
SALARY_SOFT_LIMIT_MULTIPLIER = 1.20
# ディビジョン別「ハードキャップ」（年俸合計の目安上限。ソフトはこれ×乗数）
LEAGUE_SALARY_CAP_BY_DIVISION = {
    1: 1_000_000_000,   # 10億 → ソフト 12億（D1）
    2: 500_000_000,     # 5億 → ソフト 6億（D2）
    3: 250_000_000,     # 2.5億 → ソフト 3億（D3・バランス調整用）
}
# 後方互換・省略時は D1 のハードキャップ
LEAGUE_SALARY_CAP = LEAGUE_SALARY_CAP_BY_DIVISION[1]

# 選手年俸の OVR ベース（contract_logic.calculate_desired_salary の一次項と一致）
PLAYER_SALARY_BASE_PER_OVR = 1_800_000

# ペイロール下限（円）。0 は「下限なし」（違反・降格ペナルティなし）
PAYROLL_FLOOR_BY_DIVISION = {
    1: 600_000_000,   # 6億（D1）
    2: 400_000_000,   # 4億（D2）
    3: 0,
}

# ソフトキャップ超過分に対する段階式ぜいたく税（ドラフト RB の _tax_extra と同型）
# 超過額 over に対し: 最初の幅 w1 に倍率 m1、次の w2 に m2、残りに m3
PAYROLL_LUXURY_TAX_BRACKET_WIDTH_1 = 200_000_000   # 2億円分
PAYROLL_LUXURY_TAX_BRACKET_WIDTH_2 = 500_000_000   # 5億円分
PAYROLL_LUXURY_TAX_BRACKET_MULT_1 = 1
PAYROLL_LUXURY_TAX_BRACKET_MULT_2 = 2
PAYROLL_LUXURY_TAX_BRACKET_MULT_3 = 3

# 旧単一レート（互換用・非推奨）。compute_luxury_tax は段階式を使用。
LUXURY_TAX_RATE = 0.50

# レギュラーシーズン中のトレード/インシーズンFA 期限（ROUND_CONFIG 準拠）
# ラウンド22＝3月第2週相当。消化済み current_round がこの値以上ならロック（ラウンド23〜シーズン終了まで）。
# シミュレーション対象ラウンド番号（1始まり）がこの値以下なら CPU インシーズンFA を実行する。
REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND = 22

# =========================================================
# Highlight mode tuning presets (logic-first)
# =========================================================
# 文脈ごとの既定値。highlight_selector が参照し、明示引数があればそちらを優先する。
HIGHLIGHT_CONTEXT_PRESET_TABLE = {
    "regular": {
        "max_events": 10,
        "min_score": 18,
        "max_total_seconds": 180,
    },
    "playoff": {
        "max_events": 12,
        "min_score": 16,
        "max_total_seconds": 240,
    },
    "big_stage": {
        "max_events": 14,
        "min_score": 14,
        "max_total_seconds": 300,
    },
}

# 大舞台扱いの competition_type。Match.competition_type と照合する。
HIGHLIGHT_BIG_STAGE_COMPETITIONS = {
    "final_boss",
    "emperor_cup",
    "asia_cup",
    "asia_cl",
    "intercontinental",
    "easl",
}
