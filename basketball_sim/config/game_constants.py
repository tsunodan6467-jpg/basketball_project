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
