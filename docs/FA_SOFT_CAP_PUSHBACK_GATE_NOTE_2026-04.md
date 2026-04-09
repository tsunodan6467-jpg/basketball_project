# `soft_cap_pushback_applied` が偽ばかりになる理由 — 条件分岐の読み先

**作成日**: 2026-04-08  
**性質**: **読み先の固定（コード変更なし）**。観測: `docs/FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE_2026-04.md`、追加出力判断: `docs/FA_SOFT_CAP_PUSHBACK_MIN_OUTPUT_DECISION_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。実装の正本: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`** と同一ロジックの **`_calculate_offer`**）。

---

## 1. 目的

- **`soft_cap_pushback_applied` が観測上ほぼ常に偽**（例: **`true=0 false=1920`**）となるとき、**どの条件分岐を順に読めばよいか**を **3 段に固定**する。
- **修正案・原因断定はしない**。

---

## 2. 確定事実

- **Cell B 実 save 観測**では **`soft_cap_pushback_applied true=0 false=1920`**（**`pre_le_pop` 母集団**）。
- **`hard_over_minus_soft_pushback eq0=1920 gt0=0`** — **pushback 前後 offer は数値上一致**。
- **よって**、**「pushback が弱い」以前に**、**soft cap pushback ブロックが実質発火していない（不発）**読みが **最有力**（**断定はしない**）。

---

## 3. 次に読むべき条件分岐（3 のみ）

### 候補A: soft cap 判定ゲートそのもの

- **読むこと**: **`payroll_after_pre_soft_pushback`（= `payroll_before + offer`、hard cap 系分岐の直後の offer）が `soft_cap` を超えるか**。**超えない限り** **`soft_cap_pushback_applied` は偽**で **offer は置き換わらない**（**実装は単一の `if payroll_after > soft_cap:`**）。
- **疑うこと**: **観測母集団では常に `payroll_after <= soft_cap`** になっているのではないか。**`soft_cap`・`payroll_before`・当該 offer** の **実値レンジ**を **診断キー**（**`payroll_after_pre_soft_pushback`** 等）で **突き合わせる**。

### 候補B: pushback 対象外にする分岐（適用前の offer 縮小）

- **読むこと**: **soft cap 判定より手前**の **hard cap bridge / hard cap over** などで **offer が既に小さく抑えられ**、**結果として** **`payroll_before + offer` が soft cap を超えない**経路が **支配的**でないか。
- **疑うこと**: **「pushback スキップ用の別 if」**より、**前段で room_to_soft 等により offer が頭打ち**になり、**ゲート（候補A）に届かない**パターン。

### 候補C: `soft_cap_pushback_applied` フラグの立て方

- **読むこと**: **上記 `if` の真偽と同じタイミングで** **`snap["soft_cap_pushback_applied"]` が代入されているか**。**別経路で上書き**したり、**本番 `_calculate_offer` と diagnostic で条件が食い違っていないか**（**両関数の同一ブロック**を **突き合わせ**）。

---

## 4. 今回の判断（1 案）

**次の観測・読解は、まず `soft_cap_pushback_applied` を真にする前提条件（soft cap 判定ゲート）を確認し、その次に適用除外に相当する前段分岐、最後に applied フラグの立て方を確認する。**

- **先にゲート**（**候補A**）。
- **次に** **前段による offer 縮小**（**候補B**）。
- **最後に** **フラグと本番経路の一致**（**候補C**）。
- **修正案は出さない**。

---

## 5. 観測順の優先順位

1. **soft cap 判定ゲート**（**`payroll_after_pre_soft_pushback` と `soft_cap`**）。
2. **pushback 適用前の分岐**（**hard cap 系で offer がどこまで下がるか**）。
3. **`soft_cap_pushback_applied` のフラグ代入**（**`_calculate_offer` と `_calculate_offer_diagnostic` の対応**）。

---

## 6. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **budget 側へ議論を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。
- **原因の単一断定**。

---

## 7. 次に続く実務（1つだけ）

**`basketball_sim/systems/free_agency.py` の中で、soft cap pushback 判定に関わる if / 条件式 / フラグ代入箇所を拾う短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PUSHBACK_GATE_NOTE_2026-04.md -Pattern "目的|確定事実|次に読むべき条件分岐|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（ゲート→前段→フラグの読み順）。
