# observer 既存出力の十分性 — `room_to_budget` / `offer_after_soft_cap_pushback`

**作成日**: 2026-04-08  
**性質**: **ASCII 出力だけで 2 キーが読めるかの判断メモ（コード変更なし）**。観測手順: `docs/FA_ROOM_TO_BUDGET_AND_PUSHBACK_OBSERVE_NOTE_2026-04.md`。読み順: `docs/FA_PRE_LE_ROOM_CAUSE_READ_ORDER_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **`room_to_budget`** と **`offer_after_soft_cap_pushback`** を読むうえで、**既定の observer / diagnostic 出力（標準出力に出るもの）だけで足りるか**を **1 案として切る**。
- **追加実装はしない**（**要るなら次段で項目を絞って決める**）。

---

## 2. 既存出力で読めるもの

| 出力 | 読めること |
|------|------------|
| **`summary:` 行**（`_matrix_summary_line`） | **`soft_cap_early` の件数比率**、**`room_unique`**（`room_to_budget` のユニーク数）、**`pre_le_room`**（`soft_cap_early` 偽・両キー non-None で **`offer <= room`** の件数）。**`pre_le_room=0` の定義そのもの**はここで確認できる。 |
| **`_aggregate` ブロック** | **`final_offer` 帯別件数**（主軸は clip 後）、**`room_to_budget not None & <= TINY_MAX`** の件数・割合、**リーグレベル別件数**。 |
| **代表行（S6-tiny 最大 5 件）** | **`room_to_budget`・`payroll_before`・`payroll_budget`・`final_offer` 等**。**`soft_cap_early` 偽かつ tiny `final_offer`** に限定されるため **母集団は狭い**。 |
| **（参考）`diag` と標準出力** | 行列構築時、各行の **`diag`** に診断キーは載るが、**既定の print ではキーごとの列挙はしない**。**「見える出力」としての `offer_after_soft_cap_pushback` は標準出力にない**。 |

**現状でも追える範囲（標準出力ベース）**: **`pre_le_room` の意味・ゼロか否か**、**`room_unique` と低 room 件数の目安**、**S6-tiny に落ちたケースの一部**、**sync ブロックとの併読（post-sync 注記どおり）**。

---

## 3. 既存出力で読みにくいもの

| 観点 | 内容 |
|------|------|
| **`room_to_budget` の分布そのもの** | **ユニーク数と閾値以下件数**までは出るが、**ヒスト・分位数・全体 min/max は標準出力にない**（手計算・別スクリプトなら可だが **「既定出力だけ」では弱い**）。 |
| **`offer_after_soft_cap_pushback` の分布そのもの** | **専用の集計行・ヒストはない**。**代表行も `final_offer` 主軸**で **pushback 後 offer は印字されない**。 |
| **大小関係・差分の全体傾向** | **`pre_le_room` は「`<=` 側の件数」1 本**。**`>` 側の件数・超過幅の分布・欠損で落ちた pair 数**は **同じ行から暗算はできるが、明示されていない**。 |
| **代表例と全体** | **数件の S6-tiny**は **tail の手がかり**にはなるが、**`pre_le_room=0` の原因を候補A/B/C（前メモ）として **全体傾向**まで言い切るには **標本が偏り、2 キー比較の横断が足りない**。 |

---

## 4. 今回の判断（1 案）

**既存出力だけでも `pre_le_room=0` の意味と一部代表例までは読めるが、`room_to_budget` と `offer_after_soft_cap_pushback` の分布・大小関係を全体傾向として判断するには不十分である可能性が高い。したがって、次段では observer に最小限の追加出力を検討する価値がある。**

- **ゼロではない**（**`summary`・`pre_le_room`・`room_unique`・低 room 件数・代表行**）。
- **ただし** **2 キーの分布と差分の形**は **既定 ASCII だけでは弱く**、**前向きに「最小追加」を設計する段階に入ってよい**。
- **このメモでは実装しない**。

---

## 5. 追加出力が必要なら何を最小限ほしいか

**必要になった場合の候補（2〜3 項目に絞る）**:

1. **`room_to_budget`**: **比較可能行に限った min / max**、および **代表分位**（例: p50 / p90 など **少数**）。
2. **`offer_after_soft_cap_pushback`**: **同条件の min / max** と **代表分位**（同上）。
3. **差分 `offer_after_soft_cap_pushback - room_to_budget`**（**`soft_cap_early` 偽・両キー non-None** に限定）: **件数要約**（例: **`<= 0`・`> 0`・大きめ閾値超え `>> 0`** のざっくり内訳）。

※ **閾値や本数は次メモで確定**。**ここでは列挙のみ**。

---

## 6. 非目的

- **今回はコード変更しない**。
- **追加出力の実装を始めない**。
- **`final_offer` 飽和まで同時に片付けない**。
- **Cell B の再比較**。

---

## 7. 次に続く実務（1つだけ）

**observer に追加するなら何を最小限出すべきかを、項目数を絞って決める短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OBSERVER_OUTPUT_SUFFICIENCY_NOTE_2026-04.md -Pattern "目的|既存出力で読めるもの|既存出力で読みにくいもの|今回の判断|追加出力が必要なら何を最小限ほしいか|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（十分性の 1 案・最小追加候補）。
