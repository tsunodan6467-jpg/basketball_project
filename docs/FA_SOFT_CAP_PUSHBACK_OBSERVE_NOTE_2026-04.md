# soft cap pushback — 不発 / 無効の見分け（観測メモ）

**作成日**: 2026-04-08  
**性質**: **観測順と論点の固定（コード変更なし）**。文脈: `docs/FA_PUSHBACK_OFFER_CAUSE_NOTE_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。出力十分性: `docs/FA_PUSHBACK_KEY_OUTPUT_SUFFICIENCY_NOTE_2026-04.md`。observer 枠: `docs/FA_OBSERVER_MIN_OUTPUT_ADDITIONS_NOTE_2026-04.md`。実装参照: `basketball_sim/systems/free_agency.py` の **`_calculate_offer_diagnostic`**（**`soft_cap_pushback_applied`**・**`payroll_after_pre_soft_pushback`**）。

---

## 1. 目的

- **soft cap pushback** が **「発火していない」**のか **「発火しているが数値差として効いていない」**のかを、**観測だけで切り分ける読み筋**を整理する。
- **修正方針の決定はしない**（**観測メモのみ**）。

---

## 2. 確定事実

- **pushback 前 offer** は **`offer_after_hard_cap_over`**、**pushback 後**は **`offer_after_soft_cap_pushback`** で **固定済み**（**mapping メモ**）。
- **Cell B 実 save 観測（D2 / D1）**では、**`pre_le_pop` 相当の母集団**で **両キーの min / p25 / p50 / p75 / max が一致**した。
- **よって**、**少なくとも今見えている母集団では**、**pushback による押し下げ差は要約上は観測できていない**（**「実質効いていない」読みが強い**。**コードバグの断定はしない**）。

---

## 3. 次に見るべき観測点（2 のみ）

### 観測点A: `soft_cap_pushback_applied`

- **diagnostic 上**、**`payroll_after_pre_soft_pushback > soft_cap`** により **真**になるフラグ（**実装どおり**）。
- **見ること**: **真の pair が存在するか**。**母集団全体で 0 件か**、**一部だけか**。**偽ばかりなら「pushback 分岐に入っていない」**が **第一の疑い**。

### 観測点B: pushback 係数 / 減衰ロジック

- **`soft_cap_pushback_applied` が真**なのに **前後要約が一致**するなら、**式が `max(0, soft_cap - payroll_before)` 等で事実上同値**、**整数丸め**、**別分岐での上書き**など **「差が 0 に潰れる」経路**を **疑う**（**読み先は `free_agency` の pushback ブロックとその直前後**）。

---

## 4. 今回の判断（1 案）

**次の観測は、まず `soft_cap_pushback_applied` の発火有無を確認し、その後で pushback 前後の差分が 0 になる理由を係数 / 丸め / 条件分岐の観点で読む。**

- **先に「発火しているか」**（**観測点A**）。
- **発火していなければ**、**そこが原因候補の手前**（**不発**）。
- **発火しているのに差がない**なら、**観測点B**（**係数・丸め・分岐**）。
- **修正方針はまだ決めない**。

---

## 5. 観測順の優先順位

1. **`soft_cap_pushback_applied` の件数・比率**（**`pre_le_room` 母集団または行列全体**で **定義を揃えて**数える）。
2. **pushback 前後差分の有無**（**既存 `pre_le_pop` の 2 行**、**必要なら pair 単位の件数**）。
3. **差分が 0 のとき**の **係数 / 丸め / 条件分岐**の **読み先**（**コード参照**。**変更はしない**）。

---

## 6. 非目的

- **コード変更**。
- **pushback 式の修正方針決定**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **budget 側（Cell B）へ議論を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。

---

## 7. 次に続く実務（1つだけ）

**`soft_cap_pushback_applied` の件数と、pushback 前後差分の件数を最小限 observer に出す必要があるかを判断する短いメモを作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE_2026-04.md -Pattern "目的|確定事実|次に見るべき観測点|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（発火有無と係数・丸め・分岐の観測順）。
