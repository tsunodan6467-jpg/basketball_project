# `estimate_fa_market_value` — どの項が水準を作るか（読解メモ）

**作成日**: 2026-04-08  
**性質**: **入力・係数の読み分け（コード変更なし）**。照合: `docs/FA_MARKET_VALUE_MATCH_NOTE_2026-04.md`。コードパス: `docs/FA_MARKET_VALUE_CODE_PATH_NOTE_2026-04.md`。設計焦点: `docs/FA_SALARY_DESIGN_FOCUS_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agent_market.py`。

---

## 1. 目的

- **`estimate_fa_market_value` 内部**で、**85M〜115M 級の salary 水準を主に押し上げている入力・係数**を **主項 / 上振れ / 小補正**に **分けて固定**する。  
- **行ごとの再計算・原因断定・修正案はしない**。

---

## 2. 対象式

- **関数**: **`estimate_fa_market_value`**（**`free_agent_market.py`**）。  
- **入力**: **`ovr`**、**`age`**、**`potential`**（**文字列→大文字**）、**`fa_years_waiting`**。  
- **係数・定数**: **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**`game_constants`**）、**`_scale_fa_estimate_bonus` 内の除数 `12_000`**（**旧 ovr 係数との比**）、**`potential_bonus_map` の円ベース加算額**、**`MIN_SALARY_DEFAULT`**。  
- **前処理**: **`ensure_fa_market_fields`**（**本関数の論点外だが** **`salary` 欠損時の仮埋め**あり）。

---

## 3. 読み分け（3 のみ）

### 読み分けA — 主水準を決める項

- **`raw_linear = ovr * GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** と **`legacy_floor = _scale_fa_estimate_bonus(400_000)`** の **`max`**。  
- **OVR が 1 点上がるごとに約 122 万円ずつ総額が動く**ため、**観測の 85M〜115M 級の「帯の位置」**は **まずこの線形項（＋床）で説明しやすい**（**`FA_MARKET_VALUE_MATCH_NOTE` どおり**）。  
- **係数 `1_220_000` が水準のスケールそのもの**。

### 読み分けB — 上振れ要因（同じ `ovr` 帯の中での高め押し上げ）

- **`potential`** による **`_scale_fa_estimate_bonus(potential_bonus_map[...])` の加算**（**S/A/B は正**、**D は負**）。  
- **スケール後は 1 段階あたりおよそ 千万円前半〜2 千万円台前半のオーダー**（**例**: **S は約 2.5 千万円強の加算**。**実装の整数除算どおり**）。  
- **水準の桁を決めるのは A** だが、**同評価帯内で「さらに上へ寄せる」役**になりやすい。

### 読み分けC — 小さめ補正

- **`age`** 分岐（**若年の加算**、**32 歳以上・35 歳以上の減算**）と **`fa_years_waiting` 段階の減算**。  
- **いずれも `_scale_fa_estimate_bonus` 経由で数千万円オーダー**にはなりうるが、**OVR を数十点動かしたときの線形項の変化幅**に比べると **「帯全体を決める軸」ではない**読みが立ちやすい（**減点で下げる方向にも効く**）。

---

## 4. 今回の整理

- **85M〜115M 級を一番強く作っているのは** **`ovr` と `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` の積（読み分けA）**。**その次に効くのは** **`potential`（読み分けB）**。**`age` / `fa_years_waiting`（読み分けC）は補助的**。  
- **まだ** **選手ごとの検算はしていない**ため、**「読み分けとして自然」**で **止める**。

---

## 5. 非目的

- **コード変更**。  
- **行ごとの再計算・検証**。  
- **開幕ロスター**・**選手分布**への **読みの拡張**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**主水準を決めると読んだ項（おそらく `ovr` 線形項）について、観測 salary と突き合わせて「どの `ovr` 帯が高すぎるか」を読む短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_MARKET_VALUE_DRIVER_READ_NOTE_2026-04.md -Pattern "目的|対象式|読み分け|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（主項＝ovr 線形、上振れ＝potential、補正＝年齢・FA 待機に整理）。
