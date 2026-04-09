# `_process_team_finances()` 内：実装順序・中間変数（実装前メモ）

**作成日**: 2026-04-08  
**性質**: **実装前整理（コード変更なし）**。適用位置: `docs/PAYROLL_BUDGET_POSTOFF_APPLY_POINT_DESIGN_2026-04.md`（内完結が第1候補）。`floor_expr` 記号: `docs/PAYROLL_BUDGET_POSTOFF_FLOOR_EXPR_CANDIDATES_2026-04.md`（`α * roster_payroll + β`）。合成: `docs/PAYROLL_BUDGET_POSTOFF_HYBRID_COMPOSE_DESIGN_2026-04.md`。⑦の式の正本: `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`。

---

## 1. 目的

- **`_process_team_finances()` 内**で、**`current_formula_budget` → `floor_expr` → `max(...)`** までの **実装順序**と **中間変数の置き方**だけを決める。
- **本メモはコード変更ではない**。**次の最小実装**に渡す **流れの固定**である。

---

## 2. 前提整理

- **現行の経営指標による `payroll_budget` 算出**（⑦の内側式＋`base_budget` の `max` 等）は **残す**。その結果を **`current_formula_budget`** と呼ぶイメージでよい。
- **`roster_payroll` を参照した `floor_expr`**（記号のみ：`α * roster_payroll + β`）を **追加**する。
- **最終形の方向**: `payroll_budget = max(current_formula_budget, floor_expr)`（**数値・係数は本メモでは決めない**）。
- **今回の論点**は **順序と変数名**のみ。

---

## 3. 想定フロー

オフ後再設定の **同一チームブロック内**で、次の順に置く想定とする。

1. **`current_formula_budget` を算出** — いま⑦にある **`max(base_budget, int(…))` 相当**を **そのまま評価**し、**経営式の結果**を **1 つの名前**に収める（既存が **インライン代入**なら、**実装時**に **一度ローカルに抜く**イメージ）。
2. **`roster_payroll` を取得／確認** — **チームの契約実態**に相当する値。**属性名は実装時に既存フィールドに合わせる**（本メモでは **概念名のみ**）。
3. **`floor_expr` を算出** — `α * roster_payroll + β` の **記号どおり**（**α, β は未決**）。
4. **`final_payroll_budget = max(current_formula_budget, floor_expr)`** — **合成はここ 1 行**に集約する想定。
5. **`team.payroll_budget` に代入** — **最終値だけ**を **既存と同じ代入先**に渡す。

---

## 4. 中間変数の置き方

**名前は次の 4 つに収める**のが **読みやすさと追跡**のバランスがよい。

| 変数名（候補） | 意味（短く） |
|----------------|-------------|
| `current_formula_budget` | ⑦の **現行式だけ**の結果（`roster` 未合成）。 |
| `roster_payroll` | **床計算の入力**となるロスター年俸合計（既存属性の読み出し）。 |
| `floor_expr` | **`α * roster_payroll + β`** の評価結果（床）。 |
| `final_payroll_budget` | **`max(current_formula_budget, floor_expr)`** の結果。**`team.payroll_budget` に渡す値**。 |

**既存との関係**

- **既存**が **`team.payroll_budget = int(max(...))` 一行**などなら、**新規ローカルは上記 4 つが上限イメージ**。**`current_formula_budget` は「今右辺に直書きされている塊」を名前付けする**方向が自然。
- **`roster_payroll`** は **すでに同ブロック内で別名を使っている**なら、**重複取得を避ける**ため **その既存の値を流用**してよい（**概念は `roster_payroll` と同じ**であれば **変数名は実装時に既存に合わせる**）。
- **新規は最小限** — **床と合成の意図が読める名前**（`floor_expr`, `final_payroll_budget`）を **優先**。**不要な細分化はしない**。

---

## 5. 現時点の整理

- **実装時**は **`_process_team_finances()` 内**で、上記 **4 変数前後**に **収まるのが自然**（適用位置メモと整合）。
- **まずは読みやすさ優先**で、**1 回の代入連鎖**（式 → 床 → max → `team` 代入）として **縦に並べる**のが **安全**（分岐を増やさない）。
- **helper 化**は **本メモの範囲外**。**必要になった後段**でよい。

---

## 6. 非目的

- **コード変更**、**α, β の決定**、**最終コードの記述**。
- **helper 化**、**テスト追加**。
- **clip／λ／buffer** の変更。

---

## 7. 次に続く実務（1つだけ）

**本メモを前提に、最小差分で `basketball_sim/models/offseason.py`（`_process_team_finances`）を実装する **1 撃用の実装指示書**を `docs/` に 1 本作成する**（**係数の決め方は指示書側の段階で扱う**）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_INLINE_FLOW_MEMO_2026-04.md -Pattern "目的|前提整理|想定フロー|中間変数|現時点の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（内完結フロー・中間変数 4 名）。
