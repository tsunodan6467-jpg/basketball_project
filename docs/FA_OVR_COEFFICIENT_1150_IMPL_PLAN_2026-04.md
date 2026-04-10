# 主候補 `1_150_000` — 安全な試行の実装方針（メモ・未実装）

**作成日**: 2026-04-08  
**性質**: **試行方針の固定（このメモ自体はコード変更なし）**。仮候補の決裁: `docs/FA_OVR_COEFFICIENT_CANDIDATES_DECISION_2026-04.md`。机上効き: `docs/FA_OVR_COEFFICIENT_EFFECT_NOTE_2026-04.md`。調整優先: `docs/FA_OVR_COEFFICIENT_VS_FLOOR_DECISION_2026-04.md`。

---

## 1. 目的

- **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** の **主候補 `1_150_000`** を、**いちど安全に試す**ための **変更箇所・観測・スコープ**を **短く固定**する。  
- **このメモの段階では実装しない**。

---

## 2. 変更対象（予定）

| 項目 | 内容 |
|------|------|
| **変更箇所** | **`basketball_sim/config/game_constants.py`** の **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** の **宣言値のみ**（**`1_220_000` → `1_150_000`**）。 |
| **観測** | **Cell B 実 save に近い条件**で **`tools/fa_offer_real_distribution_observer.py`** の **`pre_le_pop` 要約**（**`player_salary`・`base`・`offer_after_base_bonus`**）。**変更前後の stdout を並べて比較**する想定。 |
| **触らない方針** | **`legacy_floor` の `400_000`・`potential_bonus_map`・`MIN_SALARY_DEFAULT`** 等 **`free_agent_market.estimate_fa_market_value` 内の他定数**。**同じコミットで複数論点を混ぜない**（**`FA_OVR_COEFFICIENT_VS_FLOOR_DECISION` どおり floor は第2候補**）。 |

**補足**: **定数は `generator.calculate_initial_salary` 等でも参照**されるため、**影響は FA 見積に限らない**。**初回は FA 観測を主にし**、**開幕ロスター総額などは次段**でもよい（**試行スコープを広げすぎない**）。

---

## 3. 試行方針（3 のみ）

### 方針A — 変更の単一性

- **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR` を `1_150_000` に差し替える 1 箇所だけ**（**数値定義の 1 行**）。**`legacy_floor`・`potential` 側は同時に触らない**。

### 方針B — 再観測の最小限

- **まず Cell B 実 save**（**既存の観測手順**）で **`player_salary`・`base`・`offer_after_base_bonus`** の **min/max 分位がどう動くか**を見る。**`bonus` は副次**でよい（**主因読みは維持**）。

### 方針C — 戻し可能・目的の限定

- **Git で 1 コミット 1 目的**（**係数試行のみ**）。**効きが不適なら `1_220_000` へ revert しやすい**。**初回は「係数変更の効き確認」に留め**、**バランス確定まではしない**。

---

## 4. 今回の整理

- **まだ実装しない**。**安全な 1 回試行**の **範囲だけ**を **このメモで決める**。  
- **`1_180_000`** は **効きが弱すぎた場合の保険候補**として **決裁どおり残す**。

---

## 5. 非目的

- **このメモによるコード変更**。  
- **最終係数の確定**。  
- **`legacy_floor` 調整**への **同時着手**。  
- **`bonus` / hard cap** 側への **主軸の戻し**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**この方針どおりに `1_150_000` を一時適用して観測する実装指示書を docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OVR_COEFFICIENT_1150_IMPL_PLAN_2026-04.md -Pattern "目的|変更対象|試行方針|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（主候補 `1_150_000` の単一変更・最小観測・revert 前提）。
