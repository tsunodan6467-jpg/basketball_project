# `offer_after_base_bonus` — base / bonus 形成とその直後（コードパス固定）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。次焦点の決裁: `docs/FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md`。bridge / over: `docs/FA_BRIDGE_VS_OVER_DECISION_2026-04.md`。`low_cost_limit`: `docs/FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **hard cap 前**の **offer 形成**を読むために、**`offer_after_base_bonus`** が **どの変数から作られ**、**その直後に何が続くか**を **`_calculate_offer_diagnostic` / `_calculate_offer` 上で固定**する。
- **支配要因の断定・修正案はしない**。

---

## 2. 対象関数

| 優先度 | 関数 | 役割 |
|--------|------|------|
| **主** | **`_calculate_offer_diagnostic`** | **`snap["base"]`**, **`surplus`**, **`bonus`**, **`offer_after_base_bonus`**, **`payroll_after_initial`** 等を **取得**（**約 L292–L308**）。 |
| **対照** | **`_calculate_offer`** | **本番 offer**。**`base`〜`offer = base + bonus` まで同一**（**約 L222–L231**）。**snap なし**。 |

**前提**: **`payroll_before >= soft_cap`** のとき **早期終了**（diagnostic は **`soft_cap_early`** で return、**`offer_after_base_bonus` は記録されない**）。

---

## 3. コードパスの読み先（3 のみ）

### 読み先A: `offer_after_base_bonus` の直前

- **`base`**: **`int(player.salary)`**。**`<= 0`** のとき **`max(ovr * 10_000, 300_000)`** に置換（**`ovr` デフォルト 60**）。  
- **diagnostic**: 確定後 **`snap["base"] = base`**（**約 L292–L295**）。  
- **`surplus`**: **`max(0, team.money - base)`**（**`money` は `getattr(..., 0)`**）。  
- **`bonus`**: **`int(surplus * 0.05)`**、続けて **`max_bonus = int(base * 0.25)`**、**`bonus = min(bonus, max_bonus)`**。  
- **diagnostic**: **`snap["surplus"]`**, **`snap["bonus"]`**（**約 L297–L302**）。  
- **合成**: **`offer = base + bonus`**。  
- **記録**: **`snap["offer_after_base_bonus"] = offer`**（**約 L304–L305**）。**これが hard cap 前の「芯＋ボーナス」1 点**。

### 読み先B: `offer_after_base_bonus` の直後（hard cap 手前まで）

- **`payroll_after = payroll_before + offer`**（**局所 `offer` は直前の `base + bonus`**）。  
- **diagnostic**: **`snap["payroll_after_initial"] = payroll_after`**（**約 L307–L308**）。  
- **続く**: **hard cap bridge**（**`if payroll_before <= cap_base < payroll_after:`**）→ **`offer` 更新** → **`offer_after_hard_cap_bridge`**（**約 L310–L318**）。  
- **その次**: **hard cap over**（**`if payroll_before > cap_base:`**）→ **`offer_after_hard_cap_over`**（**約 L320–L331**）。  
- **補助**: bridge / over に入るまで **局所 `offer` はいずれも「直前段の `offer`」を引き継ぐ**。

### 読み先C: diagnostic と本体の一致・記録位置

- **`_calculate_offer`**: **`base` 確定 → surplus → bonus → `offer = base + bonus`** の **順序は diagnostic と同じ**（**L222–L231** vs **L292–L305**）。**snap 相当の行は無い**。  
- **`snap["offer_after_base_bonus"]`** は **`offer = base + bonus` の直後**（**bridge の前**）**にだけ入る**。  
- **bridge 以降**は **両関数とも同一の `if` 順**（**`FA_HARD_CAP_OVER_CODE_PATH_NOTE` 系と整合**）。

---

## 4. 今回の整理

**100M 台の offer が「いつ確定するか」を追うときは、(A) `base`・`surplus`・`bonus`・`offer = base + bonus` と `offer_after_base_bonus` の記録、(B) 続く `payroll_after_initial` と bridge / over への入り、(C) 本体との同順を `_calculate_offer` で突き合わせる。A→B→C で足りる。どの項が観測レンジを支配するかはこのメモでは断定しない。**

---

## 5. 非目的

- **コード変更**。  
- **hard cap 系の恒久的否定**。  
- **pushback 側へ主軸を戻すこと**。  
- **`final_offer`・税・clip まで同時に片付けること**。  
- **修正案の決定**・**単一原因の断定**。

---

## 6. 次に続く実務（1つだけ）

**`offer_after_base_bonus` の値を observer に最小追加する必要があるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_BONUS_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`offer_after_base_bonus` 前後・代入順の固定）。
