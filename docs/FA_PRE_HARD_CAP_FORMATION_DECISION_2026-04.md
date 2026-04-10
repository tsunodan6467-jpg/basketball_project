# hard cap 前段 — offer 形成を次の本命に置く（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **読み優先度の決裁（コード変更なし）**。bridge vs over: `docs/FA_BRIDGE_VS_OVER_DECISION_2026-04.md`。bridge 照合: `docs/FA_BRIDGE_GATE_MATCH_NOTE_2026-04.md`。`low_cost_limit` パス: `docs/FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`**）。

---

## 1. 目的

- **Cell B 実 save の観測**を踏まえ、**hard cap bridge / over より前**の **offer 形成段**を **次の第1焦点として読むか**を **1 案で固定**する。
- **コード変更・修正案・単一原因の断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・`pre_le_pop` 母集団に整合する範囲）**

- **`soft_cap_pushback_applied`**: **全件偽**。**`payroll_after_pre_soft_pushback > soft_cap`**: **0 件**（**ゲート未到達**は **維持**）。
- **`cap_base`**・**`soft_cap`**: **観測上いずれも 1.2B 固定**（**`value=1200000000`** 等）。
- **`payroll_before`**: **D2 / D1 ともに常に 1.2B 未満**。**`payroll_after_pre_soft_pushback`**: **全件 1.2B 以下**（**max は cap に一致しうる**）。

**bridge 条件との関係（読み）**

- **bridge 条件**（**`payroll_before <= cap_base < payroll_after`**、**`payroll_after` は base+bonus 直後**）は **`cap_base` が `soft_cap` と同水準**のとき、**`payroll_before < cap_base`** なら **左端は満たしやすい**が、**中点**は **`payroll_before + offer_after_base_bonus > cap_base`** でなければ **偽**。**今回の母集団**では **`payroll_after_pre` が cap 以下**かつ **`cap_base = soft_cap`** の **観測**から、**「bridge が主因で大きく削っている」読み**は **かなり弱まる**（**`FA_BRIDGE_GATE_MATCH_NOTE` の第1候補**は **相対的に後退**）。

**over / `low_cost_limit`**

- **`low_cost_limit`（≤900k）**と **観測の 100M 台 `offer_after_hard_cap_over`** の **乖離**は **従来どおり大きい**（**後順位**の **まま**）。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は、hard cap 系の前段で offer がどのように 100M 台へ形成されているかに置く。具体的には `offer_after_base_bonus` を中心に、base / bonus 系の形成段を本命として読む。**

- **pushback**・**bridge**・**over** を **永久否定はしない**（**優先度の入れ替え**）。  
- **100M 台 offer** は **hard cap 前の `base + bonus`（およびその前提）**が **主に作っている可能性**を **第1候補**とする。  
- **断定**は **観測・コード突合の後**に **委ねる**。

---

## 4. 理由

- **観測上**、**hard cap 後**の offer は **`room_to_soft` 等と整合**しうるが、**bridge 条件が主因**という **読みは今回の `cap_base` / payroll 関係で弱い**。  
- **over / `low_cost_limit`** は **観測レンジと噛み合いにくい**。  
- **残る説明軸**として **前段形成**（**`offer_after_base_bonus`**）に **自然に寄る**。

---

## 5. 非目的

- **コード変更**。  
- **pushback / bridge / over の恒久的否定**。  
- **`final_offer` 側まで同時に主軸を広げること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。  
- **hard cap 系の恒久的否定**（**優先度の移動にとどめる**）。

---

## 6. 次に続く実務（1つだけ）

**`basketball_sim/systems/free_agency.py` で `offer_after_base_bonus` とその直前直後の代入順を拾う短いコード読解メモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（hard cap 前段形成を第1焦点に移す決裁）。
