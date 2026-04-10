# `base` / `bonus` の生成と加算順（コードパス固定）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。次焦点の決裁: `docs/FA_BASE_VS_BONUS_DECISION_2026-04.md`。前後関係: `docs/FA_BASE_BONUS_CODE_PATH_NOTE_2026-04.md`。前段形成: `docs/FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **`offer_after_base_bonus` の内訳**を読むために、**`base` がどこで決まり**、**`bonus` がどこで決まり**、**どの順で `offer` に合成されるか**を **`_calculate_offer_diagnostic` / `_calculate_offer` 上で固定**する。
- **base / bonus どちらが観測レンジの主因かの断定はしない**。

---

## 2. 対象関数

| 優先度 | 関数 | 役割 |
|--------|------|------|
| **主** | **`_calculate_offer_diagnostic`** | **`snap["base"]`**, **`surplus`**, **`bonus`**, **`offer_after_base_bonus`** を **取得**（**約 L292–L305**）。 |
| **対照** | **`_calculate_offer`** | **本番 offer**。**`base`〜`offer = base + bonus` まで同一**（**約 L222–L231**）。**中間 snap なし**。 |

**前提**: **`payroll_before >= soft_cap`** のとき **早期終了**（diagnostic は **`base=None`** で return、**以降の base/bonus は走らない**）。

---

## 3. コードパスの読み先（3 のみ）

### 読み先A: `base` の生成

- **初期値**: **`base = int(getattr(player, "salary", 0))`**（**`_calculate_offer` L222** / **diagnostic L292**）。  
- **置換条件**: **`if base <= 0:`** のとき **`base = max(int(getattr(player, "ovr", 60)) * 10_000, 300_000)`**（**L223–L224** / **L293–L294**）。  
- **保持**: 局所変数 **`base`**。**diagnostic のみ** **`snap["base"] = base`**（**L295**、**確定直後**）。

### 読み先B: `bonus` の生成

- **`surplus`**: **`max(0, int(getattr(team, "money", 0)) - base)`**（**L226** / **L297**）— **`money` 未設定は 0 扱い**。  
- **`bonus`（第1段）**: **`int(surplus * 0.05)`**（**L227** / **L298**）。  
- **`max_bonus`**: **`int(base * 0.25)`**（**L228** / **L299**）。  
- **`bonus`（最終）**: **`bonus = min(bonus, max_bonus)`**（**L229** / **L300**）。  
- **保持**: 局所 **`bonus`**。**diagnostic のみ** **`snap["surplus"]`**, **`snap["bonus"]`**（**L301–L302**）。

### 読み先C: 加算と `offer_after_base_bonus` の記録

- **合成**: **`offer = base + bonus`**（**L231** / **L304**）。**この時点で hard cap 前の offer 芯が確定**。  
- **diagnostic**: **直後**に **`snap["offer_after_base_bonus"] = offer`**（**L305**）。  
- **続く**: **`payroll_after = payroll_before + offer`** と **`payroll_after_initial`**（**L307–L308**）→ **hard cap bridge / over**（**`FA_BASE_BONUS_CODE_PATH_NOTE` どおり**）。  
- **`_calculate_offer`**: **`offer = base + bonus` のあと**すぐ **`payroll_after = payroll_before + offer`**（**L233**）→ **bridge**。**代入順は diagnostic と同じ**。

---

## 4. 今回の整理

**100M 台が「主に base か bonus か」を追うときは、(A) `player.salary` / ovr 下限で確定した `base`、(B) `team.money` と `base` から決まる `surplus` と 5%・25% キャップ後の `bonus`、(C) `offer = base + bonus` と `offer_after_base_bonus` の記録を `_calculate_offer` と突き合わせる。A→B→C で足りる。寄与の大小はこのメモでは断定しない。**

---

## 5. 非目的

- **コード変更**。  
- **hard cap 系の恒久的否定**。  
- **pushback 側へ主軸を戻すこと**。  
- **`final_offer`・税・clip まで同時に片付けること**。  
- **修正案の決定**・**base / bonus 主因の断定**。

---

## 6. 次に続く実務（1つだけ）

**`base` と `bonus` のどちらを observer に最小追加すべきかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（base / bonus 生成・加算順の固定）。
