# `payroll_before` / `offer_after_hard_cap_over` — observer 最小追加の要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。読み順: `docs/FA_SOFT_CAP_PRE_GATE_RELATION_NOTE_2026-04.md`。ゲート出力: `docs/FA_SOFT_CAP_GATE_MIN_OUTPUT_DECISION_2026-04.md`。照合: `docs/FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`（**`pre_le_pop`**）。

---

## 1. 目的

- **ゲート手前の内訳**（**`FA_SOFT_CAP_PRE_GATE_RELATION_NOTE` どおり**）を読むうえで、**`payroll_before` と `offer_after_hard_cap_over` を observer に足す必要があるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`offer_after_hard_cap_over`**: **`pre_le_pop` 内の 1 行**で **min / max / p25 / p50 / p75**（**`n_hard` 注記**あり）。
- **`payroll_after_pre_soft_pushback`**: **同ブロック**で **要約**（**min / max / 分位**）**+ `n_gate`**。
- **`payroll_after_pre_vs_soft_cap`**: **`> soft_cap` と `<=` の件数・比率**。
- **よって** **`payroll_before + offer_after_hard_cap_over`（= `payroll_after_pre_soft_pushback`）の和の結果**と **soft cap との関係**は **既に見える**。

---

## 3. 既存出力でまだ弱いこと

- **`payroll_before` が標準出力に無い**ため、**和が soft cap に届かない**とき **主因が**
  - **元 payroll が低め／余裕が大きい**のか
  - **offer 側が相対的に小さい**のか  
  を **一行ログだけでは直接は切り分けにくい**。
- **`offer_after_hard_cap_over`** は **上記どおり要約済み** — **内訳の「offer 側」はある程度読める**。

---

## 4. 追加候補（2 項目以内）

### 候補A（主軸）

- **`payroll_before`**: **min / max / 少数分位**（例: **p25 / p50 / p75**）。**母集団は `pre_le_pop` の `n_gate` 行と揃える**か **`pre_le_pop` 全体と揃える**かは **実装指示で 1 本に固定**。

### 候補B（任意）

- **`payroll_before + offer_after_hard_cap_over` と `soft_cap` の差**の **件数要約** — **既に `payroll_after_pre_vs_soft_cap` がある**ため **主軸にはしない**。**重複が気になる場合のみ** **省略または 1 行統合**を **実装指示で検討**。

---

## 5. 今回の判断（1 案）

**次段の最小追加は `payroll_before` 要約を第1候補とし、`offer_after_hard_cap_over` は既存出力で足りる。和の成否はすでに `payroll_after_pre_soft_pushback` 側で見えているため、まず不足している内訳の片側として `payroll_before` だけを補う価値が高い。**

- **追加するならまず `payroll_before` のみ**でよい（**`offer_after_hard_cap_over` の重複行は増やさない**）。
- **2 項目目（候補B）は必須ではない**。
- **3 項目以上に広げない**。

---

## 6. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **`final_offer` 側まで広げる**。
- **3 項目以上を主軸にすること**。
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`payroll_before` 要約だけを observer に足す最小差分の実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PRE_GATE_MIN_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`payroll_before` 単独追加の価値判断）。
