# soft cap pushback — `free_agency.py` 上の読み先（コードパス）

**作成日**: 2026-04-08  
**性質**: **if / 代入箇所の固定（コード変更なし）**。読み順: `docs/FA_SOFT_CAP_PUSHBACK_GATE_NOTE_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。観測: `docs/FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE_2026-04.md`。

---

## 1. 目的

- **soft cap pushback が発火するか**を決める **条件式・代入**を、`basketball_sim/systems/free_agency.py` 上の **具体箇所**として **固定**する。
- **修正案・原因断定はしない**。

---

## 2. 対象関数

| 優先度 | 関数 | 役割 |
|--------|------|------|
| **主** | **`_calculate_offer_diagnostic`** | **段別 snap**。**`payroll_after_pre_soft_pushback`**・**`soft_cap_pushback_applied`**・**`offer_after_*`** がここで取れる。 |
| **対照** | **`_calculate_offer`** | **本番が返す最終 offer** の計算。**pushback 本体は `if payroll_after > soft_cap:` のみ**（**フラグは無い**）。**ロジックは diagnostic と同一に保つ**（docstring どおり）。 |

**早期リターン**: 両関数とも **`payroll_before >= soft_cap`** のとき **pushback ブロックに入らない**（diagnostic は **`soft_cap_early` 真**で即 return）。

---

## 3. 条件分岐の読み先（3 のみ）

### 読み先A: soft cap pushback ゲート（`payroll_after > soft_cap`）

- **ファイル**: `basketball_sim/systems/free_agency.py`
- **`_calculate_offer_diagnostic`**: **`payroll_after = payroll_before + offer`** の **再計算直後**に **`snap["payroll_after_pre_soft_pushback"] = payroll_after`**。**続く `if payroll_after > soft_cap:`** が **唯一のゲート**。**見る変数**: **`payroll_after`**（**hard cap 前段を通した後の `offer`** で更新済み）、**`soft_cap`**。
- **`_calculate_offer`**: **同じ順序**で **`payroll_after = payroll_before + offer`** のあと **`if payroll_after > soft_cap:`** で **`offer = max(0, soft_cap - payroll_before)`**。

### 読み先B: hard cap 前段（`offer_after_hard_cap_over` に至るまで）

- **`_calculate_offer_diagnostic` 内の流れ**（**変数はいずれも局所 `offer`** が順に更新）:
  1. **`offer = base + bonus`** → **`offer_after_base_bonus`**
  2. **`if payroll_before <= cap_base < payroll_after_initial:`** → **`offer = min(offer, room_to_soft)`**（**`room_to_soft = max(0, soft_cap - payroll_before)`**）→ **`offer_after_hard_cap_bridge`**
  3. **`if payroll_before > cap_base:`** → **`offer = min(offer, room_to_soft, low_cost_limit)`** → **`offer_after_hard_cap_over`**
- **`_calculate_offer`** でも **同じ 2 本の `if`**（**bridge / over**）が **`soft cap pushback より前**にある。**「ゲートに届かない」**ときは **ここで `offer` が既に抑えられ**、**読み先A の条件が偽**になりうる。

### 読み先C: `soft_cap_pushback_applied` の代入

- **`_calculate_offer_diagnostic` のみ**: 上記 **`if payroll_after > soft_cap:`** の **真枝**で **`snap["soft_cap_pushback_applied"] = True`**、**偽枝**で **`False`**。**直後**に **`snap["offer_after_soft_cap_pushback"] = offer`**。
- **`_calculate_offer`**: **フラグなし**。**真偽の対応**は **`if payroll_after > soft_cap:` に入ったか**＝ **offer が `max(0, soft_cap - payroll_before)` に置き換わったか**で **照合**する。

---

## 4. 今回の整理

**「不発」を追うときは、まず diagnostic の `payroll_after_pre_soft_pushback` と `soft_cap`（および同ファイル内の `payroll_before`・`offer` の流れ）でゲート（読み先A）が偽になる理由を見る。次に hard cap bridge/over（読み先B）で offer がどこまで下がっているかを見る。最後に applied 代入（読み先C）がゲートと同じ if にぶら下がっていることを `_calculate_offer` と突き合わせる。**

---

## 5. 非目的

- **コード変更**。
- **修正案の決定**。
- **budget 側へ議論を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。

---

## 6. 次に続く実務（1つだけ）

**上で拾った条件式と diagnostic 値を、Cell B 実 save 観測の値と照合する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|条件分岐の読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`_calculate_offer` / `_calculate_offer_diagnostic` のパス固定）。
