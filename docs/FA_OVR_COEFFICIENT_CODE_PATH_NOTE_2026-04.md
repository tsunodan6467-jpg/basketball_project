# `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` — 定義と FA 主水準での効き方（コードパスメモ）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。疑う順序の決裁: `docs/FA_OVR_BAND_DRIVER_DECISION_2026-04.md`。`ovr` 帯照合: `docs/FA_OVR_BAND_MATCH_NOTE_2026-04.md`。項の読み分け: `docs/FA_MARKET_VALUE_DRIVER_READ_NOTE_2026-04.md`。

---

## 1. 目的

- **salary 高止まりの第1候補**である **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** について、**定義場所**と **`estimate_fa_market_value` における効き方**を **固定**する。  
- **第2候補の `legacy_floor`** は **比較位置まで**触れる。**修正案・原因断定はしない**。

---

## 2. 対象箇所（明記）

| 種別 | ファイル | シンボル |
|------|----------|----------|
| **定数定義** | **`basketball_sim/config/game_constants.py`** | **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**現値 `1_220_000`**） |
| **FA 見積本体** | **`basketball_sim/systems/free_agent_market.py`** | **`estimate_fa_market_value`**、**`_scale_fa_estimate_bonus`** |
| **参照（同一定数）** | **`basketball_sim/systems/generator.py`** | **`calculate_initial_salary`**（**開幕単価**。**FA メモの主筋は `estimate` 側**） |

**`estimate_fa_market_value` 内の骨格**

- **`raw_linear = int(ovr) * int(GENERATOR_INITIAL_SALARY_BASE_PER_OVR)`**  
- **`legacy_floor = _scale_fa_estimate_bonus(400_000)`**（**内部で同じ定数を使ってレガシー円額をスケール**）  
- **`base = max(raw_linear, legacy_floor)`**（**ここで床との比較**）

---

## 3. コードパスの読み先（3 のみ）

### 読み先A — 定数の宣言

- **`basketball_sim/config/game_constants.py`** の **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**。  
- **コメント上**は **開幕ロスター・架空プール・国際 FA 生成など generator 系**と **FA 見積の寄せ先**が **同じオーダー**として **共有**されている（**ファイル内コメント参照**）。

### 読み先B — `estimate_fa_market_value` での線形項

- **`free_agent_market.estimate_fa_market_value`**：**`ovr` 全点に **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR` を掛けた **`raw_linear`** が主水準の芯**。  
- **この値が `legacy_floor` との **`max` の左側**になり、**以降の `potential` / 年齢 / FA 待機はこの `base` に加減算**される（**`FA_MARKET_VALUE_DRIVER_READ_NOTE` どおり**）。

### 読み先C — `legacy_floor` の比較

- **同関数内**：**`legacy_floor = _scale_fa_estimate_bonus(400_000)`** → **`base = max(raw_linear, legacy_floor)`**。  
- **`raw_linear` が床未満のときだけ** **`floor` が下支え**。**高 `ovr` 帯では `raw_linear` が床を上回りやすく**、**観測レンジの桁は係数側が主軸**、**`floor` は補助**という **読みが立ちやすい**（**断定しない**。**`FA_OVR_BAND_DRIVER_DECISION` どおり**）。

---

## 4. 今回の整理

- **「係数が高すぎる可能性」**を **最短で追う**なら **`game_constants` の定義（A）→ `estimate_fa_market_value` の `raw_linear`（B）→ `max` と `_scale_fa_estimate_bonus`（C）** の順で十分。  
- **まだ** **ゲームバランス上の正否は断定しない**。

---

## 5. 非目的

- **コード変更**。  
- **係数の具体的な調整案**。  
- **`legacy_floor` を永久に第2候補と断定すること**。  
- **`potential` 側**への **読みの拡張**（**別タスク**）。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`GENERATOR_INITIAL_SALARY_BASE_PER_OVR` の現在値で、どの `ovr` 帯から 85M〜115M 級が出やすくなるかを短く読むメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OVR_COEFFICIENT_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象箇所|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（定義・`raw_linear`・`max(floor)` の3点を固定）。
