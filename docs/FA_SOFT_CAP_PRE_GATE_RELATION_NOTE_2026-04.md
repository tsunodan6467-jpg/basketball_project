# `payroll_before` / `offer_after_hard_cap_over` / `soft_cap` — ゲート手前の読み順

**作成日**: 2026-04-08  
**性質**: **観測順の固定（コード変更なし）**。ゲート照合: `docs/FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE_2026-04.md`。コードパス: `docs/FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`**）。

---

## 1. 目的

- **soft cap pushback 不発**（**ゲート未到達**）が **固定されたあと**、**`payroll_before`・`offer_after_hard_cap_over`・`soft_cap`** を **どの順で読むか**を **固定**する。
- **修正案・原因断定はしない**。

---

## 2. 確定事実

- **Cell B 実 save 観測**では **`payroll_after_pre_vs_soft_cap gt=0` が 0%**、**`le_eq` が 100%**（**`pre_le_pop` 母集団・`n_gate` 一致**）。**よって** **`payroll_after_pre_soft_pushback > soft_cap` は実質 0 件**。
- **`soft_cap_pushback_applied` 偽一色**・**pushback 前後 offer 一致**と **整合**し、**pushback は発火していない**読みが **最有力**（**`FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE` どおり**）。
- **コード上** **`payroll_after_pre_soft_pushback`** は **`payroll_before + offer`**（**hard cap 前段後の `offer`**）**に対応**（**`FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE` どおり**）。**`offer` の直前スナップショットキー**は **`offer_after_hard_cap_over`**（**mapping メモ**）。
- **よって次段**は、**`payroll_after_pre_soft_pushback <= soft_cap`** を **誰が主に作っているか** — **`payroll_before` 側**か **`offer_after_hard_cap_over` 側**か（**合成**）— を **読む段階**（**単一原因の断定はしない**）。

---

## 3. 今回見る関係（3 のみ）

### 観測点A: `payroll_before` の水準

- **diagnostic キー** **`payroll_before`**（**チームの契約総額ベース**）。
- **読むこと**: **`soft_cap` からの距離**（**絶対差・比率の目安**）。**もともと payroll が cap に近い**と、**小さい offer でも超えうる**し、**逆に十分低い**と **同じ offer でも届かない**余地がある。

### 観測点B: `offer_after_hard_cap_over` の水準

- **hard cap bridge / over を通した後**の **年俸 offer**（**pushback 直前の offer**）。
- **読むこと**: **分布・典型値**。**小さめに抑えられている**と **`payroll_before + offer` が soft cap 未満**に **寄りやすい**。

### 観測点C: `soft_cap` との相対位置

- **`payroll_before + offer_after_hard_cap_over`**（**= `payroll_after_pre_soft_pushback` と同値**）と **`soft_cap`** の **関係**を **相対**で読む（**単独の `soft_cap` 羅列より** **差・余裕**）。

---

## 4. 今回の判断（1 案）

**次の観測は、まず `payroll_before` の分布と `soft_cap` との距離を見て、その後 `offer_after_hard_cap_over` を重ね、`payroll_before + offer_after_hard_cap_over` が soft cap に届かない構図かを確認する。**

- **先に payroll 側**（**観測点A**）。
- **次に offer 側**（**観測点B**）。
- **最後に合成**（**観測点C**）。
- **pushback 修正の議論にはまだ進めない**。

---

## 5. 観測順の優先順位

1. **`payroll_before` と `soft_cap`**（**距離・レンジ**）。
2. **`offer_after_hard_cap_over`**（**ゲート直前 offer**）。
3. **`payroll_before + offer_after_hard_cap_over` と `soft_cap`**（**既存の `payroll_after_pre_soft_pushback` 行と突合**してよい）。

---

## 6. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **budget 側へ議論を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。
- **原因の単一断定**。

---

## 7. 次に続く実務（1つだけ）

**`payroll_before` と `offer_after_hard_cap_over` を observer に最小限出す必要があるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PRE_GATE_RELATION_NOTE_2026-04.md -Pattern "目的|確定事実|今回見る関係|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（ゲート手前 3 キーの読み順）。
