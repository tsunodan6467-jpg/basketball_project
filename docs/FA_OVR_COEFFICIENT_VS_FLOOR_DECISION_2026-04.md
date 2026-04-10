# 係数か `legacy_floor` か — 先に触る順（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **調整対象の優先決裁（コード変更なし）**。OVR 仮線引き: `docs/FA_OVR_THRESHOLD_DECISION_2026-04.md`。係数のコードパス: `docs/FA_OVR_COEFFICIENT_CODE_PATH_NOTE_2026-04.md`。疑う順序（旧）: `docs/FA_OVR_BAND_DRIVER_DECISION_2026-04.md`。

---

## 1. 目的

- **OVR 危険帯・注意帯の仮線引き**を **前提**に、**是正の次段**として **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** と **`legacy_floor`** の **どちらを先に調整対象として疑うか**を **1 案で固定**する。  
- **新しい係数値・floor 値・実装はしない**。

---

## 2. 確定事実

- **仮線引き**（**`FA_OVR_THRESHOLD_DECISION` どおり**）: **OVR 90 前後＝危険帯**、**OVR 80 前後＝注意帯**、**OVR 70 台＝自然帯寄り**。  
- **主水準**は **`ovr × GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**。  
- **`legacy_floor`** は **`base = max(raw_linear, legacy_floor)`** の **下支え候補**。  
- **高 OVR 帯**では **`raw_linear` が `floor` を超えやすく**、**観測の 85M〜115M 級**は **線形項と整合しやすい**（**既存観測メモどおり**）。

---

## 3. 比較候補（2 のみ）

### 候補A

- **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**`game_constants`**）。**危険帯・注意帯の salary を最も直接に上下**させやすい（**OVR 全点に一様に掛かる**）。

### 候補B

- **`legacy_floor`**（**`estimate_fa_market_value` 内の `_scale_fa_estimate_bonus(400_000)` と `max`**）。**`raw_linear` が床未満の帯**の **底上げ**に効く可能性がある（**高 OVR では効きにくい**読みが立ちやすい）。

---

## 4. 今回の判断（1 案）

**先に触る第1候補は `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` とする。理由は、今回問題化しているのが主に OVR 80〜90 前後の高め帯であり、その主水準を最も直接に動かすのが線形係数だから。`legacy_floor` は第2候補として残す。**

- **断定ではない**。**調査で `floor` の効きが想定より広い**と分かったら **順位を見直してよい**。

---

## 5. 理由

- **危険帯の主軸**は **高 OVR 側**の **線形項**。  
- **そのレンジでは `raw_linear` が `floor` を上回りやすい**ため、**まず主項（係数）を疑う**のが **切り分けとして自然**（**`FA_OVR_BAND_DRIVER_DECISION` と同趣旨**）。

---

## 6. 非目的

- **コード変更**。  
- **係数・floor の具体的な新値の決定**。  
- **budget 側へ議論を戻すこと**。  
- **修正案の本文まで書くこと**。

---

## 7. 次に続く実務（1つだけ）

**第1候補にした `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` をどの程度下げると OVR 80〜90 帯へどう効くかを読む短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OVR_COEFFICIENT_VS_FLOOR_DECISION_2026-04.md -Pattern "目的|確定事実|比較候補|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（第1＝線形係数、第2＝`legacy_floor`）。
