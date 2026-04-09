# `payroll_after_pre_soft_pushback` / `soft_cap` — observer 最小追加の要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。照合: `docs/FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE_2026-04.md`。コードパス: `docs/FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE_2026-04.md`。先行の最小出力判断（pushback 件数）: `docs/FA_SOFT_CAP_PUSHBACK_MIN_OUTPUT_DECISION_2026-04.md`。診断: `basketball_sim/systems/free_agency.py`。出力: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **ゲート未到達仮説**（**`payroll_after_pre_soft_pushback <= soft_cap` が支配的**）を **進める**ために、**`payroll_after_pre_soft_pushback` と `soft_cap` を observer に足す必要があるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`soft_cap_pushback_applied true=0 false=1920`**（**`pre_le_pop` 母集団**）— **フラグ上は pushback 真枝に入っていない**。
- **`hard_over_minus_soft_pushback eq0=1920 gt0=0`** — **pushback 前後 offer は数値上一致**。
- **コード**（**`FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE` どおり**）では **`payroll_after > soft_cap`** のときだけ **真枝**。**よって** **ゲート未到達**が **第1仮説**として **自然**（**`FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE`**）。
- **ただし** **`payroll_after_pre_soft_pushback` の実数値**と **`soft_cap` の実数値**は **標準出力ではまだ並んでいない**（**`diag` キーは存在**。**仮説の数値確認は未了**）。

---

## 3. 追加候補（2 のみ）

### 候補A: `payroll_after_pre_soft_pushback` の要約

- **min / max** と **少数分位**（例: **p25 / p50 / p75**）。**母集団は `pre_le_pop` と揃える**（**実装指示で固定**）。

### 候補B: ゲート越え件数

- **`payroll_after_pre_soft_pushback > soft_cap`** の **件数**（および **`n` に対する比率**）。**対比**として **`<= soft_cap`** を **暗算または 1 行に併記**してよい（**主軸は 2 本のうち「越え」側の件数**でよい）。

**`soft_cap` の扱い**: **診断ではチーム／リーグに依存する値**（**行ごとに `diag["soft_cap"]` あり**）。**行列内でユニークが少ない**場合は **1 行注記**や **`soft_cap` の min=max** で **十分**なことが多い。**別途 `soft_cap` 専用の長い分布出力**は **主軸にしない**（**候補A/B でゲート比較ができれば足りる**）。

---

## 4. 今回の判断（1 案）

**ゲート未到達仮説を確認するには、(1) `payroll_after_pre_soft_pushback` の要約、(2) `> soft_cap` 件数 / 比率の 2 項目だけを observer に最小追加する価値が高い。**

- **追加するならこの 2 つで十分**（**3 項目目以降は広げない**）。
- **`soft_cap` は行ごとに diag で揃えて比較**し、**全行同一なら出力は簡潔**にできる。
- **目的は仮説確認の最小観測**。**pushback 修正式の議論にはまだ進めない**。

---

## 5. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **`final_offer` 側まで広げる**。
- **3 項目以上を主軸にすること**。
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**上記 2 項目だけを observer に足す最小差分の実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_GATE_MIN_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（ゲート仮説検証用 2 項目の価値判断）。
