# soft cap pushback — `soft_cap_pushback_applied` / 前後差分件数の追加要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **observer 最小追加の要否判断（コード変更なし）**。観測順: `docs/FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE_2026-04.md`。キー対応: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。出力状況: `docs/FA_PUSHBACK_KEY_OUTPUT_SUFFICIENCY_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`（**`pre_le_pop`**）、`basketball_sim/systems/free_agency.py`（**診断キー**）。

---

## 1. 目的

- **`soft_cap_pushback_applied` の件数**と **pushback 前後差分の件数要約**を、**observer に最小追加すべきか**を **1 案として切る**。
- **実装はしない**（**次段の実装指示書**に委ねる）。

---

## 2. 既存出力で分かること

- **`pre_le_pop`** で **`offer_after_hard_cap_over`** と **`offer_after_soft_cap_pushback`** の **min / p25 / p50 / p75 / max** が **並ぶ**。
- **両者の要約が一致**すれば、**少なくともその母集団では前後に分布差が見えない**ことまでは分かる（**Cell B 実 save での観測どおり**）。
- **ただし** **要約一致だけ**では、
  - **`soft_cap_pushback_applied` が偽で分岐に入っていない（不発）**のか、
  - **真だが前後 offer が同値（発火しているが無差分）**なのか、
  を **標準出力上では直接は切れない**（**diag 内にはあるが件数化されていない**）。

---

## 3. 追加候補（2 のみ）

### 候補A: `soft_cap_pushback_applied`

- **件数 / 比率**（**母集団は `pre_le_pop` と揃える**か **行列全体**かは **実装指示で 1 本に固定**）。
- **見ること**: **真の pair が 0 か**、**一部か**。

### 候補B: pushback 前後差分の件数要約

- **`delta = offer_after_hard_cap_over - offer_after_soft_cap_pushback`**（**同一 pair**）について:
  - **`delta == 0`**
  - **`delta > 0`**
- **`>> 0`（大きめ閾値超）**は **主軸に含めない**。**必要なら補足**として **実装指示で任意**。

---

## 4. 今回の判断（1 案）

**既存出力だけでは「不発」か「発火しているが無差分」かを切り分けにくいため、次段では (1) `soft_cap_pushback_applied` 件数、(2) pushback 前後差分件数の 2 項目だけを observer に最小追加する価値が高い。**

- **追加するならこの 2 つで足りる**（**3 項目目以降は広げない**）。
- **目的は** **`FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE` の観測点A/B を ASCII で先に潰す**こと。
- **pushback 修正式や係数の確定はしない**。

---

## 5. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **`final_offer` 側まで広げる**。
- **3 項目以上を主軸にすること**。
- **Cell B の再比較**。

---

## 6. 次に続く実務（1つだけ）

**上記 2 項目だけを observer に足す最小差分の実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PUSHBACK_MIN_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（2 項目追加の価値判断）。
