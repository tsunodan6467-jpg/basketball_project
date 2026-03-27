# シミュレーション・バランス監視ガード（v1）

目的:  
既存バランスを壊さないため、`pytest` で定量指標を継続監視する。

本書は「厳密なゲームデザイン仕様」ではなく、**安全ロールアウト用の退行検知ライン**を定義する。

## 対象テスト

- `basketball_sim/tests/test_simulation_balance_guard.py`
- `basketball_sim/tests/test_special_training_match_effects.py`
- `basketball_sim/tests/test_individual_drill_development_unlocks.py`（育成・個別ドリル／解放条件）

## 現在の監視指標（v1）

`test_simulation_balance_guard.py` は、seed固定の複数シーズン（現在3シーズン）でレギュラー試合のみを集計し、以下を監視する。

- 総試合数: `>= 1800`
- 平均総得点: `130.0 <= x <= 210.0`
- 平均点差: `5.0 <= x <= 35.0`
- 3P成功率: `0.20 <= x <= 0.50`
- TO/チーム1試合: `3.0 <= x <= 25.0`
- 勝率偏り（max win% - min win%）: `<= 0.75`

## スペシャル練習の安全ガード（v1）

`test_special_training_match_effects.py` で次を固定する。

- `precision_offense`: 通常比で攻撃補正が `+0.9`
- `intense_defense`: 通常比で守備補正が `+0.9`
- `intense_defense` は `defense` よりテンポ抑制が強い

## 個別ドリル（育成微小成長）の安全ガード（v1）

重量バランス監視（上記の得点・TO・勝率など）は**試合シミュレーション中心**である。一方、個別練習の「年次の属性+1」系は試合ログに直接出ないため、**別テストで係数と解放条件を固定する**。

`test_individual_drill_development_unlocks.py` および `DevelopmentSystem` で次を意図どおり維持する。

- 施設／HC 条件付きドリル（`speed_agility` / `iq_film` / `defense_footwork` / `strength`）は、**未解放ならドリル特化を育成に使わず**、方針（`training_focus`）ベースにフォールバックする（`training_unlocks.player_drill_lock_reason` と整合）。
- **解放済み**の条件付きドリルに対してのみ、微小成長の発動率へ **`SPECIAL_GATED_DRILL_PROC_MULTIPLIER = 1.06`** を掛ける（上限 `0.24` は維持）。係数変更時は当該テストと本節を更新する。

## 運用ルール

- 新しい係数調整を入れる前に、上記テストを実行する。
- 失敗時は「コード修正」か「閾値更新」のどちらかを必ず明示する。
- 閾値更新を行う場合は、次を同時に更新する。
  - 当ドキュメント
  - 対応するpytest
  - 変更理由（コミットメッセージまたはPR本文）

## 実行コマンド

```bash
python -m pytest "basketball_sim/tests/test_special_training_match_effects.py" "basketball_sim/tests/test_simulation_balance_guard.py"
```

## CI運用（分離）

- 通常CI: `.github/workflows/ci.yml`
  - 日常のpytestから `test_simulation_balance_guard.py` は除外
- 重量バランス監視: `.github/workflows/balance-guard.yml`
  - `workflow_dispatch`（手動実行）と `schedule`（nightly）で実行

## リリース判定ルール（v1）

- 試合係数・育成係数・確率テーブルなど、**バランスへ影響する変更**を含むPRは、
  `Balance Guard (heavy)` の `success` を必須チェックとする。
- `failure` の場合は次のどちらかを必ず行う。
  - 実装を修正して再実行
  - 閾値と根拠を更新して再実行

