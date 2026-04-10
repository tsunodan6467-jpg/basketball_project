# `soft_cap` — observer への観測追加要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。決裁: `docs/FA_SOFT_CAP_GATE_UNREACHED_DECISION_2026-04.md`。内訳判断: `docs/FA_PRE_GATE_MIN_OUTPUT_DECISION_2026-04.md`。読み順: `docs/FA_SOFT_CAP_PRE_GATE_RELATION_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`（**`pre_le_pop`**・**`payroll_after_pre_vs_soft_cap`**）。

---

## 1. 目的

- **`soft_cap` 水準**と **`payroll_before + offer_after_hard_cap_over`** の **相対**を読むうえで、**`soft_cap` 自体を observer に足す必要があるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`payroll_before`**: **`pre_le_pop` ブロック**で **min / max / 分位**。
- **`offer_after_hard_cap_over`**: **同ブロック**で **要約**（**`n_hard` 注記**あり）。
- **`payroll_after_pre_soft_pushback`**: **`payroll_after_pre_soft_pushback ... (n_gate=...)`** 行。
- **`payroll_after_pre_vs_soft_cap`**: **`> soft_cap` と `<=` の件数・比率**（**行ごとの比較は内部で実施済み**）。

**よって** **合成 payroll** と **ゲート越えの有無**までは **読める**。

---

## 3. 既存出力でまだ弱いこと

- **`soft_cap` の絶対値**が **標準出力に無い**ため、**「いくつを上限として `le_eq=100%` なのか」** **一目で掴みにくい**（**余裕・ギャップの体感**）。
- **一方**、**D1/D2 等で `soft_cap` が実質一定**なら **長い分布**や **多行**は **不要**。**`unique` 数が 1〜少数**なら **1 行の単純表示**で足りる。

---

## 4. 追加候補（1 のみ）

### 候補A: `soft_cap`

- **母集団**: **`pre_le_pop` の `n_gate` 行**（**`payroll_after_pre_vs_soft_cap` と同じ**）に **揃える**のが **解釈上一貫**。
- **出し方**: **行列内で値が一定**なら **`soft_cap=...` 1 語**。**複数値**なら **`min` / `max`** または **`unique=N`** の **短い要約 1 行**（**実装指示で確定**）。

---

## 5. 今回の判断（1 案）

**次段では、soft_cap 水準との相対を読みやすくするために、observer へ `soft_cap` 自体を最小追加する価値が高い。ただし、soft_cap が実質固定なら 1 行の単純表示で十分であり、長い分布表示は不要とする。**

- **追加するなら `soft_cap` のみ**（**2 項目目以降は広げない**）。
- **目的は相対読みの補助**。**pushback 修正式の議論には進めない**。

---

## 6. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **`final_offer` 側まで広げる**。
- **2 項目以上を主軸にすること**。
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`soft_cap` だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`soft_cap` 単独行の価値判断）。
