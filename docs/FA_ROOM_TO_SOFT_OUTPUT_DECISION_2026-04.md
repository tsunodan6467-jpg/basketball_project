# `room_to_soft` — observer への観測追加要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。照合: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。コードパス: `docs/FA_HARD_CAP_OVER_CODE_PATH_NOTE_2026-04.md`。**`soft_cap` 出力判断**: `docs/FA_SOFT_CAP_OUTPUT_DECISION_2026-04.md`。実装参照: `tools/fa_offer_real_distribution_observer.py`、**`basketball_sim/systems/free_agency.py`**。

---

## 1. 目的

- **`room_to_soft = max(0, soft_cap - payroll_before)` 相当**を **observer に足す必要があるか**、**既存の `pre_le_pop` 系行だけで足りるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`payroll_before`**: **`pre_le_pop` ブロック**で **min / max / 分位**（**`n_pb` 注記**あり）。
- **`soft_cap`**: **同一ブロック**で **1 行要約**（**`FA_SOFT_CAP_OUTPUT_DECISION` 実装済み想定**）。
- **`payroll_after_pre_soft_pushback`**: **ゲート母集団**の **分布要約**（**`n_gate`**）。
- **`offer_after_hard_cap_over`**: **hard 前段後 offer** の **分布要約**。

**よって** **`soft_cap - payroll_before`** は **観測者が数値を突き合わせれば** **理論上は復元できる**。**合成 payroll** と **cap との関係**も **既に読める**。

---

## 3. 既存出力でまだ弱いこと

- **`room_to_soft` そのもの**は **stdout に直接出ていない**。
- **`offer_after_hard_cap_over <= room_to_soft`** を **同じブロックの連続行だけで即確認**しにくい（**差分や不等号を手計算・別画面**に **寄せがち**）。
- **`FA_ROOM_TO_SOFT_MATCH_NOTE` が指摘した pair 単位の直接突合**は **未実施**のまま **しにくい**。

---

## 4. 追加候補（1 のみ）

### 候補A: `room_to_soft` の要約

- **意味**: **`max(0, soft_cap - payroll_before)`** と **同一の量**を **母集団で要約**する **1 行**（**`soft_cap` 行と同様の出し分け**: **実質固定なら `value=`**、**複数なら `min` / `max` / `unique` 程度**）。**分位や長い分布は増やさない**。
- **母集団**: **`pre_le_pop` かつ `n_gate` と揃える**のが **解釈上一貫**（**実装指示で確定**）。

---

## 5. 今回の判断（1 案）

**既存出力だけでも `soft_cap - payroll_before` を推測し、`room_to_soft` 読みとの整合性はかなり読める。一方、bridge / over 段の「上限＝`room_to_soft`」をその名で一行に載せると、`offer_after_hard_cap_over` との関係を直接確認しやすくなる。したがって、次段で `room_to_soft` を 1 行だけ最小追加する価値はある。**

- **必須ではないが有益**（**手計算の負荷と突合の明示性**のトレードオフ）。
- **追加するなら `room_to_soft`（相当）の 1 項目に限定**する。

---

## 6. 非目的

- **今回のメモ段階でのコード変更**。
- **pushback 側へ主軸を戻すこと**。
- **`final_offer` 側まで広げること**。
- **2 項目以上を主軸にすること**。
- **修正案の決定**。
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`room_to_soft` だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_ROOM_TO_SOFT_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`room_to_soft` 観測追加要否・1 行追加価値あり）。
