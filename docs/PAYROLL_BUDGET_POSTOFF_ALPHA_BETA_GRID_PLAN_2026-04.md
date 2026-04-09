# α×β 少数組合せ（4 セル）— 観測計画（実装前）

**作成日**: 2026-04-08  
**性質**: **観測計画の固定（コード変更なし）**。決裁: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_DECISION_2026-04.md`。RATIO 結果: `docs/PAYROLL_BUDGET_POSTOFF_RATIO_TUNING_RESULTS_2026-04.md`。BUFFER 結果: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_RESULTS_2026-04.md`。

---

## 1. 目的

- **`floor_expr = α * roster_payroll + β`** の **α×β を 4 セルだけ**動かし、**before 主軸**の分布と **補助軸**（`summary` 等）が **どう変わるか**の **方向感**を取る。
- **本書は最適化・最終 α/β 確定ではない**。**少数比較の手順と見る項目**を **1 本に固定**する。

---

## 2. 前提整理

| 項目 | 内容 |
|------|------|
| **α（`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`）** | **1.05 / 1.10** のみ |
| **β（`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`）** | **`3_000_000` / `10_000_000`** のみ（**30M は本計画に含めない**） |
| **セル数** | **ちょうど 4**（**5 セル目以降は追加しない**） |
| **観測の主軸** | **`before`**（**`summary` は補助**） |
| **save / observer** | **従来どおり**（**postfloor D2/D1 の 2 本**）。**`--apply-temp-postoff-floor` 必須**（静的 `.sav` 対策）。 |
| **clip / λ / FA buffer** | **別トラック**（**触らない**） |

---

## 3. 比較セル案（4 のみ）

| セル | α | β |
|------|---|-----|
| **A** | 1.05 | 3,000,000 |
| **B** | 1.05 | 10,000,000 |
| **C** | 1.10 | 3,000,000 |
| **D** | 1.10 | 10,000,000 |

- **4 セルで打ち止め**。**β=30M** や **α=1.0 の再掲**は **本格子に含めない**。
- **目的**は **最適解の探索ではない**。**RATIO-only（β=3M 固定）と並べたとき**、**β を上げた併用**に **意味があるか**を **触感で見る**こと。

---

## 4. 各セルで見る項目

**セル × save ごと**に、従来観測と **同一セット**で記録する。

| 項目 | 内容 |
|------|------|
| **before `gap_unique`** | |
| **before `gap_min` / `gap_max`** | |
| **`user_team_snapshot`** | **`payroll_budget` / `roster_payroll` / `gap`** |
| **`summary`** | **`room_unique` / `pre_le_room`** |
| **（任意）`final_offer > buffer`** | FA 30M 基準（**TEMP postoff の β とは別**） |

---

## 5. 観測対象

- **save（2 本のみ）**  
  - `C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav`  
  - `C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav`
- **各 run**: `python tools\fa_offer_real_distribution_observer.py --save "<path>" --apply-temp-postoff-floor`
- **save を増やさない**。

---

## 6. 今回の判断（計画に含める前提）

- **次段の観測**は **上記 4 セル**の **α×β 少数比較**とする。
- **最終 α / β は本計画では決めない**。
- **読み取りの狙い**: **RATIO-only（β 固定 3M）**と比べ、**同じ α で β を 10M にしたとき**・**同じ β で α を上げたとき**の **相対差**（**before / 補助軸**）を **1 表に載せられるか**。

---

## 7. 非目的

- **本書のみでのコード変更**。
- **5 セル以上**への拡張、**β=30M** の追加。
- **`clip` / `λ` / FA `buffer` の変更**。
- **最終値の断定**。

---

## 8. 次に続く実務（1つだけ）

**本 4 セル計画どおりに **`TEMP_POSTOFF_*`** を差し替え、**同一手順**で観測ログを取る **Cursor 向けの実装＋観測指示書**を **`docs/` に 1 本**作成する（**観測後の定数復帰**まで含めてよい）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_PLAN_2026-04.md -Pattern "目的|前提整理|比較セル案|各セルで見る項目|観測対象|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（4 セル A〜D、D2/D1、30M 除外）。
