# FA 年俸の市場見積 — コード読解先（メモ）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。優先順位の決裁: `docs/FA_SALARY_DESIGN_FOCUS_DECISION_2026-04.md`。次焦点: `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`。base 主因: `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`。主モジュール: `basketball_sim/systems/free_agent_market.py`。

---

## 1. 目的

- **FA の `player.salary` 土台**を **直接作っている年俸生成（市場見積）**について、**読むべき関数と順序**を **固定**する。  
- **原因断定・修正案はしない**。

---

## 2. 対象関数（モジュール: `free_agent_market.py`）

| 優先度 | 関数名 | 役割 |
|--------|--------|------|
| **主** | **`estimate_fa_market_value`** | **FA 年俸目安の本体**（**戻り値 int**）。 |
| **主** | **`normalize_free_agents`** | **FA リストを正規化し、各選手の `salary` を見積に同期**。 |
| **従** | **`sync_fa_pool_player_salary_to_estimate`** | **`player.salary = int(estimate_fa_market_value(player))` の唯一の意図した代入**（**docstring どおり `normalize_free_agents` 専用**）。 |
| **従** | **`ensure_fa_market_fields`** | **`estimate_fa_market_value` 先頭で呼ばれる補完**（**`salary` 欠損時のみ** `ovr`×`PLAYER_SALARY_BASE_PER_OVR` 下限で仮埋め。**正規化ループでも `normalize_free_agents` が先に呼ぶ**）。 |

**参照定数**: **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**・**`MIN_SALARY_DEFAULT`**・**`PLAYER_SALARY_BASE_PER_OVR`**（**`basketball_sim/config/game_constants.py`** / **`contract_logic`**）。

---

## 3. コードパスの読み先（3 のみ）

### 読み先A: `estimate_fa_market_value` の本体

- **入力（選手属性）**: **`ovr`**、**`age`**、**`potential`**（**文字列・大文字化**）、**`fa_years_waiting`**（**いずれも `getattr` / 既定値あり**）。  
- **骨格**: **`raw_linear = ovr * GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** と **レガシー床のスケール値**の **max** を **`base`** とし、**潜在・年齢・FA 待機年**に応じた **加減算**（**金額は `_scale_fa_estimate_bonus` で係数比スケール**）。  
- **出力**: **`max(MIN_SALARY_DEFAULT, base)`** を **int で返す**（**上限クリップはこの関数内には無い**）。  
- **先頭**で **`ensure_fa_market_fields(player)`** により **欠損属性の補完**（**`salary` 未設定時の仮値**は **ここでのみ** **`PLAYER_SALARY_BASE_PER_OVR` 系**。**最終値は下記 B で上書き**）。

### 読み先B: `normalize_free_agents` 側の `player.salary` 反映

- **ループ**: 各 `player` に対し **`ensure_fa_market_fields(player)`** → **非 retired のみ **`sync_fa_pool_player_salary_to_estimate(player)`**。  
- **代入**: **`sync_fa_pool_player_salary_to_estimate`** が **`player.salary = int(estimate_fa_market_value(player))`**。**追加の丸め・上限は無し**（**`estimate` の戻り値そのまま**）。  
- **retired** は **リストから落ちる**（**`salary` は更新されない**）。

### 読み先C: observer・offer 計算への接続

- **ゲーム側**で **`normalize_free_agents` が掛かった FA プール**が **オフ／メニュー経路で使われる**（**例**: **`offseason_full_fa_tk`**、**`main_menu_view`**、**同一モジュール内の他ヘルパ**）。**セーブ上の FA は当該タイミングで既に同期済みのことが多い**。  
- **`tools/fa_offer_real_distribution_observer.py`**: **`_run_matrix`** が **`int(getattr(fa, "salary", 0))`** を **行 dict の `player_salary`** に載せる。  
- **`basketball_sim/systems/free_agency.py`**: **`_calculate_offer` / `_calculate_offer_diagnostic`** が **`base = int(getattr(player, "salary", 0))`**（**`salary <= 0` 時のみ ovr 下限置換**）。**Cell B 観測では `player_salary ≒ base`** となっており、**この経路と整合**。

---

## 4. 今回の整理

- **「salary がなぜこのオーダーか」**を **最短で追う**なら **`estimate_fa_market_value`（A）→ 正規化での上書き（B）→ observer / diagnostic が同じ `player.salary` を読むこと（C）** の順で十分。  
- **開幕ロスター再配分**や **選手分布そのもの**は **このメモのスコープ外**（**`FA_SALARY_DESIGN_FOCUS_DECISION` どおり後続**）。  
- **高さの原因**（**係数か母集団か**等）は **まだ断定しない**。

---

## 5. 非目的

- **コード変更**。  
- **開幕ロスター側の初期契約**への **読みの拡張**（**第2候補は別タスク**）。  
- **選手分布（候補C）**への **拡張**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`estimate_fa_market_value` の入力と出力の関係を、観測値（salary 85M〜115M 級）と照らす短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_MARKET_VALUE_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`estimate_fa_market_value` → 正規化 → observer/diagnostic の読み順を固定）。
