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
LEAGUE_SALARY_CAP = 15_000_000
SALARY_SOFT_LIMIT_MULTIPLIER = 1.20
# ソフトキャップ超過分に掛ける率（v1: 超過ペイロール全体に対する簡易税）
LUXURY_TAX_RATE = 0.50

# レギュラーシーズン中のトレード/FA 期限（将来: 3月第2週終了まで可 → それ以降はシーズン終了までロック）
# 実装時はシーズン週番号またはカレンダーと連動させる
# REGULAR_SEASON_TRANSACTION_DEADLINE_WEEK: int | None = None  # 例: 22 など
