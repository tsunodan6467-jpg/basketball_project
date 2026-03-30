# 人事メニュー（GUI）最小実操作

## 現状（実装）

- **閲覧**: ロスター一覧（先発／6th／控え表示）。
- **＋1年延長**: 選択選手に `contract_logic.apply_contract_extension`（年俸・役割据え置き）。残年数が 1 以上かつ `MAX_CONTRACT_YEARS_DEFAULT` 未満のときのみ。レギュラー後半のトレードロックの**対象外**。
- **契約解除（FA）**: 選択選手を `Team.remove_player` し `season.free_agents` へ。`inseason_roster_moves_unlocked` と同一条件、最低人数、アイコン／`icon_locked` でブロック。

## GUI 未対応（CLI / GM 案内）

- トレード、インシーズン FA、新規契約交渉の本格 GUI。

## セーブ

- 既存 `Player` / `Team` フィールドのみ更新。形式変更なし。
