# RATIO（α）段階比較 — 観測計画（β 固定・実装前）

**作成日**: 2026-04-08  
**性質**: **観測計画の固定（コード変更なし）**。決裁: `docs/PAYROLL_BUDGET_POSTOFF_RATIO_DECISION_2026-04.md`。BUFFER 観測結果: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_RESULTS_2026-04.md`。BUFFER 計画（手順の型）: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_PLAN_2026-04.md`。

---

## 1. 目的

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`（α 相当）**を **段階的に変え**、**BUFFER だけでは崩れなかった**観測分布（**`gap_unique` / `room_unique` / `pre_le_room` / `final_offer` 飽和**など）が **変わり始めるか**の **感触**を取る。
- **本書は α の最終決定ではない**。**比較手順と見る項目**を **1 本に固定**する（**最適化ではない**）。

---

## 2. 前提整理

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`（β）は固定**したまま、**全 Step で変えない**（**リポジトリ現行どおり `3_000_000`** を **本計画の固定 β** とする。別値にしたい場合は **観測前に決裁で明示**し、**本計画と結果表にその β を記載**すること）。
- **観測の主軸**は **`before`**。**`summary`** は **補助**。
- **save 2 本**・**observer**・**`--apply-temp-postoff-floor`** の扱いは **BUFFER 観測結果メモ**と **同型**（静的 `.sav` の `payroll_budget` を **⑦式で上書き**してから観測）。
- **本書はコード差し替えを含まない**（**実装・数値確定は次段**）。

---

## 3. 比較ステップ案（3 段階のみ）

| Step | α（`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`） | 位置づけ |
|------|--------------------------------------------------|----------|
| **Step 1** | `1.0` | **現状ベースライン** |
| **Step 2** | `1.05` | **小幅上振れ** |
| **Step 3** | `1.10` | **さらに上振れ**（**極端値は避ける**） |

- **3 段階で打ち止め**。**4 段階目以降は本計画に含めない**。
- **目的**は **分布が崩れ始めるかの感触**であり、**最適 α の決定ではない**。

---

## 4. 各ステップで見る項目

各 Step × 各 save ごとに、**BUFFER 観測時と同一セット**で記録する。

| 項目 | 内容 |
|------|------|
| **before `gap_unique`** | 全対象チームの `gap` ユニーク数 |
| **before `gap_min` / `gap_max`** | **before** の最小・最大 `gap` |
| **`user_team_snapshot`** | **`payroll_budget` / `roster_payroll` / `gap`**（user 実測行） |
| **`summary`** | **`room_unique` / `pre_le_room`** |
| **（任意）`final_offer > buffer`** | FA 30M 基準との比率（補助） |

---

## 5. 観測対象

- **save（2 本のみ）**  
  - `C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav`  
  - `C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav`
- **各 run** に **`--apply-temp-postoff-floor`** を付与する。
- **save を増やさない**（本計画の範囲外）。

---

## 6. 今回の判断（計画に含める前提）

- **次段の観測主題は α（RATIO）の比較**。**β は固定**。
- **1.0 / 1.05 / 1.10** の **3 段階**で比較する。
- **最終 α は本計画では決めない**。

---

## 7. 非目的

- **本書のみでのコード変更**。
- **β の同時調整**を本ラウンドの主題にすること。
- **`clip` / `λ` / FA `buffer` の変更**。
- **最終値の断定**。
- **観測 save の追加**。

---

## 8. 次に続く実務（1つだけ）

**本計画に沿い、`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO` を **1.0 / 1.05 / 1.10** で **順に差し替え**、**β 固定**のまま **同一手順**で観測ログを取る **Cursor 向けの実装＋観測指示書**を **`docs/` に 1 本**作成する（**各 Step の差し替え・コマンド・記録テンプレ**まで含めてよい）。

---

## 実行コマンド（実施時・型）

リポジトリルート。**各 Step で α を合わせたうえで**（**β は固定**）:

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav" --apply-temp-postoff-floor
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav" --apply-temp-postoff-floor
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_RATIO_TUNING_PLAN_2026-04.md -Pattern "目的|前提整理|比較ステップ案|各ステップで見る項目|観測対象|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（α 1.0 / 1.05 / 1.10・β 固定・D2/D1・`--apply-temp-postoff-floor`）。
