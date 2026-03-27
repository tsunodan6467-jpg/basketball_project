# Player Attribute Roadmap v1 (Safe Expansion)

このドキュメントは、既存バランスを壊さずに能力項目を拡張するための段階計画です。

## Current Stable Core (Do Not Break)

既存シミュレーションの主計算に使うコア能力:

- `shoot`
- `three`
- `ft`
- `drive`
- `passing`
- `rebound`
- `defense`
- `stamina`

補助:

- `ovr`
- `usage_base`
- `fatigue`

上記は既存バランスの土台なので、係数の大幅変更は避ける。

## New Attributes (Phase 1 Definition)

段階導入する追加能力:

- `handling`
- `iq`
- `speed`
- `power`

Phase 1 では、以下のみ実装:

1. `Player` モデルに属性を追加
2. 生成時にポジション別の自然な初期分布を付与
3. セーブ互換を壊さない（既存データでも読み込み可能）

## Rollout Policy

- Phase 1: 定義・初期化のみ（試合計算への影響は最小）
- Phase 2: 小係数で反映（TO/アシスト/ドライブ安定など限定導入）
- Phase 3: 育成UI・強化メニューへの本格接続
- Phase 4: 必要なら係数再調整（統計検証ベース）

## Phase 2 Coefficients (Current)

`models/match.py` への限定反映:

- `offense_ball_security`
  - passing: `0.45`
  - drive: `0.35`
  - handling: `0.12`
  - iq: `0.08`
- `assist_rate`
  - 既存 passing 補正に加えて `iq` を `0.0008` 係数で追加
- `two-shot weight`
  - `handling * 0.12`
  - `iq * 0.08`
- `ft-shot weight`
  - `handling * 0.08`
- `2P success rate`
  - `handling * 0.00012`

注: いずれも既存の主係数より小さい値で、即時のバランス崩壊を避ける設定。

## Phase 3 (Current Scope)

- GMメニューに「個別育成方針」を追加
  - `balanced / shooting / playmaking / defense / physical / iq_handling`
- `DevelopmentSystem` に微小成長を追加
  - 若手〜全盛期（32歳未満）に限定
  - 試合出場率とトレーニング施設Lvに応じた低確率発動
  - 年1回の `+1` のみ（上限99）
  - 対象能力は方針別に限定

このフェーズでは「UIで方針を決められる」ことと「小さく反映される」ことを優先し、
試合内確率式の大幅変更は行わない。

## Phase 4 (Current Scope)

- チーム練習方針（毎週固定）を追加
  - `balanced / shooting / defense / transition`
  - 変更したい時だけ GMメニューで切替
- 反映は薄く限定
  - `shooting`: チーム攻撃に小ボーナス
  - `defense`: チーム守備に小ボーナス、ペース微減
  - `transition`: ペース微増、攻撃にごく小ボーナス

## Phase 5 (Current Scope)

- ユース強化を「固定方針」運用に統一
  - GMメニューから必要時のみ変更
  - `youth_policy_global`
  - `youth_policy_focus`
  - `youth_investment`（facility/coaching/scout/community）
- 変更しない限り設定は維持され、既存の `youth_system` 年次処理に継続適用される

## Phase 6 (Current Scope)

- 個別練習メニューをドリル単位で設定可能に拡張
  - 例: `dribble`, `rebound`, `stamina_run`, `three_point`, `iq_film` など
- 内部的には
  - `training_focus`（カテゴリ）
  - `training_drill`（具体メニュー）
  の2層管理
- 成長は引き続き安全設計
  - 低確率・`+1`のみ
  - ログに `drill:<attr>+1` を表示して可視化

## Risk Controls

- いきなり既存確率式の主変数にしない
- 1フェーズごとに `tests` と簡易シムで回帰確認
- 変更理由と係数をドキュメント化して追跡可能にする
