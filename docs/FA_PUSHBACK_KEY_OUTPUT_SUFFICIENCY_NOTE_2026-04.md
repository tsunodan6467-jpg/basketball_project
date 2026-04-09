# pushback 前後キー — observer 出力の十分性（判断メモ）

**作成日**: 2026-04-08  
**性質**: **標準出力だけで 2 キーが追えるかの判断（コード変更なし）**。キー対応: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。先行の十分性整理: `docs/FA_OBSERVER_OUTPUT_SUFFICIENCY_NOTE_2026-04.md`。最小追加の枠: `docs/FA_OBSERVER_MIN_OUTPUT_ADDITIONS_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **`offer_after_hard_cap_over`（pushback 前）** と **`offer_after_soft_cap_pushback`（pushback 後）** が、**既存 observer の標準出力だけで十分追えるか**を **1 案として切る**。
- **実装はしない**（**次段で最小追加の検討・指示**に回す）。

---

## 2. 既存出力で読めるもの

| 出力 | 内容 |
|------|------|
| **`pre_le_pop`（`summary:` 直後）** | **`pre_le_room` と同じ母集団**（`soft_cap_early` 偽・**`offer_after_soft_cap_pushback` と `room_to_budget` 両方 non-None**）について、**`offer_after_soft_cap_pushback` の min / max / p25 / p50 / p75** が **1 行で出る**。 |
| **`summary:`** | **`pre_le_room`**・**`room_unique`** 等（**pushback 後 offer と room の大小**の **集計結果**）。 |
| **`_aggregate` / 代表行** | **主軸は `final_offer`**。**`offer_after_soft_cap_pushback` や `offer_after_hard_cap_over` は列挙されない**。 |

**`offer_after_soft_cap_pushback`**: **上記 `pre_le_pop` により、母集団限定ではあるが分布の要約は標準出力で読める**（**全行列行ではない**）。

**`offer_after_hard_cap_over`**: **既定の print ではどのブロックにも出ない**（**`diag` 内にのみ存在**）。

**現状で追える範囲**: **pushback 後**の **要約（母集団は pre_le と一致）**、**`pre_le_room` の意味**。**pushback 前**は **ASCII からは読めない**。

---

## 3. 既存出力で読みにくいもの

| 観点 | 内容 |
|------|------|
| **前後ペア比較** | **同一 pair で「減衰前 → 減衰後」**を **標準出力上では並べられない**。**`offer_after_hard_cap_over` が印字されない**ため。 |
| **分布・全体感（前側）** | **`offer_after_hard_cap_over` の min/max/分位は出ない**。 |
| **母集団のずれ** | **`pre_le_pop` の pushback 後**は **欠損 pair 除外済み**。**「全 soft_cap_early 偽行」での pushback 前後**とは **一致しない場合がある**（**解釈に注意**）。 |
| **代表例 vs 全体** | **S6-tiny 代表行**は **`final_offer` 主軸**で **2 キーは出ない**。**全体傾向としての前後関係**は **現状弱い**。 |

---

## 4. 今回の判断（1 案）

**既存 observer 出力だけでは、`offer_after_hard_cap_over` と `offer_after_soft_cap_pushback` の前後比較を全体傾向として読むには不十分である可能性が高い。したがって、次段ではこの 2 キーに限定した最小追加出力を検討する価値がある。**

- **ゼロではない**（**`pre_le_pop` で pushback 後の要約**はある）。
- **ただし pushback 前が見えず、前後を同じ出力上で対照できない**ため、**候補A/B（減衰 vs 入力過大）の切り分け**には **足りないことが多い**。
- **実装はまだ行わない**。

---

## 5. 追加するなら最小限ほしいもの（主軸 2 項目）

1. **`offer_after_hard_cap_over`**: **min / max / 少数分位**（例: **p25 / p50 / p75**）。**母集団は `pre_le_pop` と揃えるか、実装指示で明示**する。
2. **`offer_after_soft_cap_pushback`**: **同じ母集団**での **min / max / 少数分位**（**`pre_le_pop` と重複するなら 1 行に統合・ラベル整理でも可**）。

**第 3 候補（補足）**: **`offer_after_soft_cap_pushback - offer_after_hard_cap_over`** の **件数要約**（**`<=0` / `>0` / 大きめ閾値超** 等）— **主軸は上 2 項目**、**こちらは任意**。

---

## 6. 非目的

- **コード変更**。
- **`final_offer` 飽和まで同時に広げる**。
- **追加項目の大量化**。
- **Cell B の再比較**。

---

## 7. 次に続く実務（1つだけ）

**`offer_after_hard_cap_over` と `offer_after_soft_cap_pushback` の 2 キーだけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PUSHBACK_KEY_OUTPUT_SUFFICIENCY_NOTE_2026-04.md -Pattern "目的|既存出力で読めるもの|既存出力で読みにくいもの|今回の判断|追加するなら最小限ほしいもの|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（pushback 前後キーの十分性 1 案）。
