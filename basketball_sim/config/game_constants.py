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
# systems.competition_rules.COMPETITION_RULES の regular_season / playoff / final_boss と整合
LEAGUE_ROSTER_FOREIGN_CAP = 3
LEAGUE_ROSTER_ASIA_NATURALIZED_CAP = 1

# 合成 Team() の既定所持金（資金力帯なしのテスト用）および FA 欠損補完のフォールバック。
# 本番の開幕所持金: CPU は `club_profile.get_initial_team_money_cpu`、ユーザーは `get_initial_user_team_money`（固定額）。
INITIAL_TEAM_MONEY_NEW_GAME = 200_000_000  # 帯1（2億円）相当
LEAGUE_ONCOURT_FOREIGN_CAP = 2
LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP = 1

# 戦術メニュー先発の条件付き差し替え（Match._resolve_match_starters）。正本: docs/MATCH_STARTING_LINEUP_RULES.md
# ベース先発との effective OVR 差がこの値を超える指定は無視する。バランス調整は本定数のみ変える。
TACTICS_STARTER_OVR_MAX_DIFF = 3
# 1 試合あたり、戦術指定で先発に「入れ替えて採用」する回数の上限（成功した swap のみカウント）。
# 既定 3＝ベース先発を崩しすぎないバランス。フルに近づける場合は 5（PG〜C すべてが条件を満てば最大 5 swap）。
TACTICS_STARTER_MAX_SUBSTITUTIONS = 3

# サラリー（Step 3: リーグ年俸上限・贅沢税の単一ソース）
# 金額はすべて円。制度上の基準額は 12 億（全 D 同一）。get_soft_cap は get_hard_cap × 下記乗数（既定 1.0 で同一額）。
SALARY_SOFT_LIMIT_MULTIPLIER = 1.0
# ディビジョン別リーグ年俸上限（salary_cap_budget.get_hard_cap の正本。旧称ハード＝現ソフトと同額）
LEAGUE_SALARY_CAP_BY_DIVISION = {
    1: 1_200_000_000,   # 12億（D1）
    2: 1_200_000_000,   # 12億（D2）
    3: 1_200_000_000,   # 12億（D3）
}
# 後方互換・省略時は D1 のリーグ年俸上限
LEAGUE_SALARY_CAP = LEAGUE_SALARY_CAP_BY_DIVISION[1]

# 選手年俸の OVR ベース（再契約・希望年俸・FA 下限等。開幕ロスター専用は下記ジェネレータ用）
PLAYER_SALARY_BASE_PER_OVR = 1_000_000
# 開幕ロスター・架空プール・国際FA生成など generator 系のみ（PR2: 12 億付近に寄せる）
GENERATOR_INITIAL_SALARY_BASE_PER_OVR = 1_150_000

# ペイロール下限（円）。0 は「下限なし」（違反・降格ペナルティなし）
PAYROLL_FLOOR_BY_DIVISION = {
    1: 600_000_000,   # 6億（D1）
    2: 400_000_000,   # 4億（D2）
    3: 0,
}

# リーグ年俸上限超過分に対する段階式ぜいたく税（ドラフト RB の _tax_extra と同型）
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
