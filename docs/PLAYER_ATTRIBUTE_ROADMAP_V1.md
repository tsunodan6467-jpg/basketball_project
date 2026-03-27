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

## Risk Controls

- いきなり既存確率式の主変数にしない
- 1フェーズごとに `tests` と簡易シムで回帰確認
- 変更理由と係数をドキュメント化して追跡可能にする
