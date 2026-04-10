# `player.salary` — observer へ 1 行だけ追加する実装指示（未実装メモ）

**作成日**: 2026-04-08  
**性質**: **実装指示書（このメモ自体はコード変更なし）**。要否判断: `docs/FA_PLAYER_SALARY_OUTPUT_DECISION_2026-04.md`。次焦点: `docs/FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md`。`base` 生成: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。対象ツール: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **`player.salary` を observer の stdout に、既存と同型の要約で 1 行だけ**足すための **最小実装の手順**を固定する。  
- **このメモの段階では実装しない**。

---

## 2. 追加対象（ファイル）

- **主**: `tools/fa_offer_real_distribution_observer.py`  
- **必要最小限**: `basketball_sim/tests/test_fa_offer_real_distribution_observer_population.py`  
- **原則**: **無関係なファイル・リファクタは触らない**。  
- **`diag["player_salary"]` で集計する経路を取る場合**（後述 **方針A**）は、**`basketball_sim/systems/free_agency.py` の `_calculate_offer_diagnostic` にキー 1 つだけ追加**する（**`base` 置換前の raw int**。**`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE` の `base` 初期化と同趣旨**）。**diagnostic を増やさない方針なら**、**`_run_matrix` が組み立てる行 dict に `player_salary` を載せ**、**`pre_le_pop` では `r.get("player_salary")` を参照**する（**値は `int(getattr(fa, "salary", 0))`** で **FA 側の第一代入と揃える**）。

---

## 3. 実装方針（3 点のみ）

### 方針A（集計ループ・母集団）

- **`player.salary` の集計は `pre_le_pop` と同一のループ・同一フィルタ**（**`soft_cap_early` 除外**、**`offer_after_soft_cap_pushback` と `room_to_budget` が両方 non-None** の行のみ）で行う。  
- **diag 経路**: **`d.get("player_salary")` が non-None の行だけ**リストに入れる。  
- **行 dict 経路**: **`r.get("player_salary")` が non-None の行だけ**（**キーを常に入れるなら実質全行**）。

### 方針B（出力形式・件数表示）

- **stdout は `player_salary` について 1 行だけ**追加する。  
- **形式は既存の `base` / `bonus` / `offer_after_base_bonus` と同型**（**min / max / p25 / p50 / p75**）。  
- **0 件**のときは **`player_salary n_salary=0`**。  
- **件数が母集団 `n` 未満のときだけ** **`n_salary=...`** を付ける（**`base` の `n_base` と同じ考え方**）。

### 方針C（出力順）

- **`pre_le_pop` ブロック内**の並びを次に揃える（**`base` と隣接させ、`player.salary ≒ base` を目視しやすくする**）。  
  1. `payroll_before`  
  2. `cap_base`（**既存の gate 行のまま**）  
  3. **`player_salary`**（**新規 1 行**）  
  4. `base`  
  5. `bonus`  
  6. `offer_after_base_bonus`  
- **docstring / 先頭コメント**に **新行の意味**を **1 語レベルで追記**すれば足りる（**長文化しない**）。

---

## 4. テスト方針

- **既存の population テスト**に **最小の追記**でよい。  
- **必須**: **`player_salary` 行が出力に含まれること**、**母集団 `n=0` で落ちないこと**。  
- **閾値・境界の網羅は不要**（**追加しすぎない**）。

---

## 5. 今回の整理

- **実装はこのメモの後続コミットで行う**。  
- **差分は「`player_salary` の要約 1 行」＋テストの必要最小限**に留める。  
- **主目的は `base` と並べたときの一致・乖離の目視確認**（**数式や自動アサートで一致を証明する段階までは書かない**）。

---

## 6. 非目的

- **このメモによるコード変更**。  
- **`player.salary` と `base` の一致の断定**。  
- **`salary <= 0` 例外の有無の先取り結論**。  
- **2 項目以上の同時追加**（**histogram や final_offer ブロックへの拡張など**）。  
- **budget 側への議論の戻し**。

---

## 7. 次に続く実務（1つだけ）

**この指示書どおりに `player.salary` 1 行を実装し、Cell B 実 save で `player_salary` と `base` を並べて確認する。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PLAYER_SALARY_OUTPUT_IMPL_NOTE_2026-04.md -Pattern "目的|追加対象|実装方針|テスト方針|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`player_salary` 1 行追加の最小実装指示）。
