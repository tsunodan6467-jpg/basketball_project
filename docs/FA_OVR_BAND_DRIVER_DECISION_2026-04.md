# 高止まりの原因候補 — 係数か floor か（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **疑う順序の決裁（コード変更なし）**。`ovr` 帯の照合: `docs/FA_OVR_BAND_MATCH_NOTE_2026-04.md`。項の読み分け: `docs/FA_MARKET_VALUE_DRIVER_READ_NOTE_2026-04.md`。観測との整合: `docs/FA_MARKET_VALUE_MATCH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agent_market.py`、`basketball_sim/config/game_constants.py`。

---

## 1. 目的

- **観測 salary 帯（85M〜115M 級）と `ovr` 帯の読み**を踏まえ、**高止まりの原因候補**として **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`（線形係数）**と **`legacy_floor`**、**`potential` 加算**の **どれを先に疑うか**を **1 案で固定**する。  
- **修正案・最終断定はしない**。

---

## 2. 確定事実

- **観測 salary 85M〜115M 級**は **`ovr` 約 70 台前半〜90 台前半**で **線形項だけでも説明しやすい**（**`FA_OVR_BAND_MATCH_NOTE` どおり**）。  
- **主水準**は **`ovr * GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** と **`legacy_floor`** の **max**（**`FA_MARKET_VALUE_DRIVER_READ_NOTE` どおり**）。  
- **`legacy_floor`**（**`_scale_fa_estimate_bonus(400_000)`**）は **帯の下支え**になりうるが、**`raw_linear` が床を超えると効かない**。  
- **`potential`** は **上振れ要因**で **第1主因ではない**という **読みが立ちやすい**（**断定しない**）。

---

## 3. 比較候補（3 のみ）

### 候補A

- **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**`game_constants`**）。**`ovr` 線形係数そのものが高すぎる**可能性。

### 候補B

- **`legacy_floor`**（**`estimate_fa_market_value` 内の `_scale_fa_estimate_bonus(400_000)` と `raw_linear` の max**）。**低 `ovr` 帯や特定レンジ**で **下支えが強すぎる**可能性。

### 候補C

- **`potential` 加算**（**スケール後の `potential_bonus_map`**）。**同じ `ovr` 帯内の上振れ**を **押し上げている**可能性。

---

## 4. 今回の判断（1 案）

**次段で先に疑う第1候補は `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` とする。理由は、観測 salary 帯の主水準を最も直接に決めているのが `ovr` 線形項だから。`legacy_floor` は第2候補、`potential` は第3候補に置く。**

- **コード上**、**観測に対応しやすい `ovr` 帯（おおむね 70 前後〜90 前後）**では **`raw_linear` が `legacy_floor` を大きく上回りやすく**、**Cell B のレンジの「桁」**を **`floor` 単体で説明しにくい**読みが立つ（**低 `ovr` の FA や別母集団では別**。**断定しない**）。  
- **将来**、**調査で `floor` が想定より広く効いている**ことが **示されたら**、**第1・第2の順を入れ替えてよい**（**柔軟性の注記**）。

---

## 5. 理由

- **観測帯を最短で動かす**のは **主水準の係数**（**OVR 全点に一様に掛かる**）。  
- **`floor`** は **下支え候補**だが、**まず主項を疑う**のが **切り分けとして自然**。  
- **上振れ要因（`potential`）**は **主項のあと**でも **遅くない**。

---

## 6. 非目的

- **コード変更**。  
- **修正案の決定**。  
- **開幕ロスター側**への **議論の戻し**。  
- **budget 側へ議論を戻すこと**。  
- **候補を 4 つ目以降に広げること**。

---

## 7. 次に続く実務（1つだけ）

**第1候補にした係数または floor について、実際のコード読解先と効き方を短く整理するメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OVR_BAND_DRIVER_DECISION_2026-04.md -Pattern "目的|確定事実|比較候補|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（第1候補＝線形係数、第2＝`legacy_floor`、第3＝`potential`）。
