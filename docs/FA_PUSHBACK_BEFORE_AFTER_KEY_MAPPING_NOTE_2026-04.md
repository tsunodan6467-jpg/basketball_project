# pushback 前後 offer — diagnostic キー対応（実装紐づけ）

**作成日**: 2026-04-08  
**性質**: **キー対応の固定（コード変更なし）**。文脈: `docs/FA_PUSHBACK_OFFER_CAUSE_NOTE_2026-04.md`。`pre_le_room` 比較段階: `docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`。正本: `basketball_sim/systems/free_agency.py` の **`_calculate_offer_diagnostic`**。

---

## 1. 目的

- **soft cap pushback の直前・直後**の **年俸 offer 相当**を、**`_calculate_offer_diagnostic` が返すどのキーで読むか**を **固定**する。
- **解決策・原因断定はしない**（**対応表のみ**）。

---

## 2. 対応候補（返却辞書内）

**pushback 前 offer 候補**（時系列が手前のものほど上）

| キー | 意味（段階の目安） |
|------|-------------------|
| **`offer_after_base_bonus`** | **base + bonus** 直後。 |
| **`offer_after_hard_cap_bridge`** | **hard cap bridge**（`payroll_before <= cap_base < payroll_after_initial` 側）適用後。 |
| **`offer_after_hard_cap_over`** | **hard cap 超え側**の分岐（`low_cost_limit` 等）適用後。**`payroll_after_pre_soft_pushback` を計算する直前**の **`offer`** と一致。 |

**pushback 後 offer 候補**

| キー | 意味（段階の目安） |
|------|-------------------|
| **`offer_after_soft_cap_pushback`** | **`payroll_after_pre_soft_pushback > soft_cap`** のとき **`max(0, soft_cap - payroll_before)`** に置き換えた後の offer。**それ以外は直前の offer をそのまま**。 |

**補助**（offer 額そのものではないが pushback 判定に直結）

| キー | 意味 |
|------|------|
| **`payroll_after_pre_soft_pushback`** | **pushback 判定に使う payroll**（`payroll_before + offer`、**直前の offer** は上表の **`offer_after_hard_cap_over` と同じ変数由来**）。 |
| **`soft_cap_pushback_applied`** | **上記 payroll が soft cap を超えたため offer を置き換えた**とき **真**。 |

**clip 以降（本メモの「pushback 後 offer」ではない）**

- **`offer_after_budget_clip`**、**`offer_after_luxury_tax`**、**`final_offer`** — **mapping メモどおり `pre_le_room` 比較には使わない**。

---

## 3. 今回の対応付け

| 読み | 固定するキー |
|------|----------------|
| **pushback 前 offer** | **`offer_after_hard_cap_over`** |
| **pushback 後 offer** | **`offer_after_soft_cap_pushback`** |

**根拠（実装順）**: **`offer_after_hard_cap_over` を `snap` に入れた直後**に **`payroll_after_pre_soft_pushback`** を計算し、**続く `if payroll_after > soft_cap:` で alone `offer` を更新**し、**その結果が `offer_after_soft_cap_pushback`** として格納される（`free_agency._calculate_offer_diagnostic`）。

**補足**: **`soft_cap_pushback_applied` が偽**の行では **前後の offer 数値は一致**しうる（**pushback 未適用**）。

---

## 4. 注意点

- **`final_offer`** は **贅沢税処理・最終 `int` 化後**。**pushback 後 offer ではない**（**後段**）。
- **`offer_after_budget_clip`** は **`room_to_budget` と同じ `_clip_offer_to_payroll_budget` 通過後**。**pushback 後よりさらに後**。
- **`offer_after_base_bonus` 等**は **pushback より手前の段階**。**「減衰前が高すぎる」全体像**を見るときの **追加の手掛かり**にはなるが、**「pushback 直前1点」**としては **`offer_after_hard_cap_over`** に **揃える**。
- **診断キー以外**に **本番 `_calculate_offer` 内の同名中間変数**はあるが、**観測は辞書キーで統一**する。

---

## 5. 今回の整理

**次の観測では、中心に並べる 2 キーは `offer_after_hard_cap_over`（直前）と `offer_after_soft_cap_pushback`（直後）とする。必要に応じて `soft_cap_pushback_applied` と `payroll_after_pre_soft_pushback` で「本当に pushback が走った行」だけに絞る。**

---

## 6. 非目的

- **コード変更**。
- **原因の断定**・**解決策の決定**。
- **budget 側（Cell B 等）へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**対応付けた 2 キーについて、既存 observer 出力で読めるか / 追加出力が要るかを短く決めるメモを作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md -Pattern "目的|対応候補|今回の対応付け|注意点|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`_calculate_offer_diagnostic` に基づく前後キー固定）。
