# hard cap **over** 枝 — `low_cost_limit` と `min(...)` のコードパス（読み先固定）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。次焦点の決裁: `docs/FA_HARD_CAP_OTHER_LIMITS_DECISION_2026-04.md`。bridge/over 全体: `docs/FA_HARD_CAP_OVER_CODE_PATH_NOTE_2026-04.md`。`room_to_soft` 照合: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **hard cap over 枝**で **`offer_after_hard_cap_over` を実際に抑えうる候補**として、**`low_cost_limit` を含む `min(...)`** と **代入順**を **`free_agency.py` 上で読み先として固定**する。
- **支配要因の断定・修正案はしない**。

---

## 2. 対象関数

| 優先度 | 関数 | 役割 |
|--------|------|------|
| **主** | **`_calculate_offer_diagnostic`** | **`low_cost_limit`**・**`room_to_soft_over`**・**`hard_cap_over_applied`**・**`offer_after_hard_cap_over`** を **snap で取得**できる。行番号は **本メモ記載時点**（**約 L320–L331**）。 |
| **対照** | **`_calculate_offer`** | **本番 offer**。**over 枝の `if`・`low_cost_limit`・`min(...)` は diagnostic と同一**（**約 L240–L244**）。**snap キーは無い**。 |

---

## 3. コードパスの読み先（3 のみ）

### 読み先A: over 枝に入る条件

- **条件**: **`if payroll_before > cap_base:`**  
  - **`payroll_before`**: **`_team_salary(team)`**（**診断・本体とも関数先頭で取得**）。  
  - **`cap_base`**: **`_hard_cap(team)`**（**変数名は `cap_base`**）。  
- **意味（コメント意図）**: **ロスター給与が既に hard cap を超えている**とき **over 側**へ入る。  
- **bridge 枝**（**`payroll_before <= cap_base < payroll_after`**）とは **別の `if`**。**評価順**は **先に bridge**、**続けて over**（**両方真になりうるか**は **入力次第**だが、**通常は状況が分かれやすい**）。

### 読み先B: `low_cost_limit` の生成と `min(...)` への入り方

- **生成**（**over 真枝内・`room_to_soft` の直後**）: **`low_cost_limit = min(max(base, 0), 900_000)`**  
  - **`base`**: **この関数内で確定した FA オファー芯**（**`player.salary` 由来、0 以下なら `ovr` ベースの下限あり** — **詳細は同ファイル先頭付近の `base` 確定ロジック**）。  
  - **上限定数**: **`900_000`**（**ハードコード**）。  
- **`room_to_soft`（over 枝）**: **`max(0, soft_cap - payroll_before)`** を **同じ真枝内で再計算**（**bridge を通していても通していなくても**、**over に入ればここで上書き参照**）。  
- **`min` への入り**: **`offer = min(offer, room_to_soft, low_cost_limit)`** — **3 引数の単一回の `min`**。**実効上限**は **三つの最小**。

### 読み先C: 代入順と `offer_after_hard_cap_over` の記録

- **順序（diagnostic）**:  
  1. **`offer_after_hard_cap_bridge`** 記録（**約 L318**）まで **bridge 通過後の `offer`**。  
  2. **over 真枝**: **`room_to_soft` 算出** → **`low_cost_limit` 算出** → **`offer = min(offer, room_to_soft, low_cost_limit)`**（**約 L321–L323**）。  
  3. **`snap["hard_cap_over_applied"]`** 等をセット（**約 L324–L326**）。  
  4. **`snap["offer_after_hard_cap_over"] = offer`**（**約 L331**）— **この時点の局所 `offer`** が **キー値**。  
- **続く流れ**: **直後**に **`payroll_after = payroll_before + offer`** と **`payroll_after_pre_soft_pushback`**（**約 L333–L334**）。**soft cap pushback** は **そのさらに後**。  
- **本体 `_calculate_offer`**: **同じ順**（**bridge → over の `min`** → **`payroll_after` 再計算** → **`if payroll_after > soft_cap`**）。**`offer_after_hard_cap_over` に相当する snap は無い**が **式は一致**（**docstring どおり**）。

---

## 4. 今回の整理

**`offer_after_hard_cap_over` の実効上限を追うときは、(A) `payroll_before > cap_base` で over に入ったか、(B) その枝での `low_cost_limit`（`base` と 900k キャップ）と `room_to_soft` のどちらが小さいか、(C) 単一の `min(offer, room_to_soft, low_cost_limit)` のあと L331（diagnostic）で snap される順序を `_calculate_offer` と突き合わせる。A→B→C で足りる。どちらの引数が支配的かはこのメモでは断定しない。**

---

## 5. 非目的

- **コード変更**。
- **`room_to_soft` 第1軸の撤回**。
- **pushback 側へ主軸を戻すこと**。
- **`final_offer`・budget clip・贅沢税まで同時に片付けること**。
- **修正案の決定**・**単一原因の断定**。

---

## 6. 次に続く実務（1つだけ）

**`low_cost_limit` と `room_to_soft` のどちらが over 枝の実支配要因かを、Cell B 実観測とコード上の式から照合する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（over 条件・`low_cost_limit`・`min`・`offer_after_hard_cap_over` 記録順の固定）。
