# BUFFER 3 段階観測結果（D2/D1 postfloor）

**作成日**: 2026-04-08  
**性質**: **観測記録（計画: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_PLAN_2026-04.md`、方針: `docs/PAYROLL_BUDGET_POSTOFF_TEMP_TUNING_DECISION_2026-04.md`）**。

---

## 1. 目的

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` を 3M / 10M / 30M** で変えたときの **before 主軸**・**user 断面**・**補助 summary** を **1 本に固定**する。
- **最終 β の決定ではない**。

---

## 2. 条件

| 項目 | 内容 |
|------|------|
| **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`** | **1.0 固定**（全 Step） |
| **観測 save（2 本のみ）** | `C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav` / `...\debug_user_boost_d1_user_postfloor.sav` |
| **Step 1 / 2 / 3 の BUFFER（β）** | `3_000_000` / `10_000_000` / `30_000_000` |
| **ツール** | `tools/fa_offer_real_distribution_observer.py` |
| **静的 save と TEMP の関係** | `.sav` 内の `payroll_budget` は **保存時点の値**のまま。**BUFFER だけ差し替えても before は変わらない**ため、各 run で **`--apply-temp-postoff-floor`** を付け、ロード直後に **⑦と同式**で `payroll_budget` を **上書き**してから従来どおり observer を走らせた（実装: `reapply_temp_postoff_payroll_budget_floor_to_teams`）。 |
| **観測後のコード** | **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` は `3_000_000` に復帰済み**（リポジトリ状態）。 |

---

## 3. 結果表

**凡例**: `final_offer > buffer` の **buffer** は **FA 経路の定数（30M）**（`sync_observation` 行の `buffer_const`）。**TEMP postoff BUFFER とは別物**。

### Step 1 — β = 3,000,000

| save | observed `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` | `final_offer > buffer` |
|------|-------------------------|----------------------|-----------------|-----------------|------------------|------------------|-------|---------------|---------------|-------------------------|
| D2 postfloor | 2 | 1 | 3,000,000 | 3,000,000 | 993,010,000 | 990,010,000 | 3,000,000 | 1 | 0 | 1920/1920 |
| D1 postfloor | 1 | 1 | 3,000,000 | 3,000,000 | 918,190,000 | 915,190,000 | 3,000,000 | 1 | 0 | 1920/1920 |

### Step 2 — β = 10,000,000

| save | observed `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` | `final_offer > buffer` |
|------|-------------------------|----------------------|-----------------|-----------------|------------------|------------------|-------|---------------|---------------|-------------------------|
| D2 postfloor | 2 | 1 | 10,000,000 | 10,000,000 | 1,000,010,000 | 990,010,000 | 10,000,000 | 1 | 0 | 1920/1920 |
| D1 postfloor | 1 | 1 | 10,000,000 | 10,000,000 | 925,190,000 | 915,190,000 | 10,000,000 | 1 | 0 | 1920/1920 |

### Step 3 — β = 30,000,000

| save | observed `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` | `final_offer > buffer` |
|------|-------------------------|----------------------|-----------------|-----------------|------------------|------------------|-------|---------------|---------------|-------------------------|
| D2 postfloor | 2 | 1 | 30,000,000 | 30,000,000 | 1,020,010,000 | 990,010,000 | 30,000,000 | 1 | 0 | 1920/1920 |
| D1 postfloor | 1 | 1 | 30,000,000 | 30,000,000 | 945,190,000 | 915,190,000 | 30,000,000 | 1 | 0 | 1920/1920 |

---

## 4. 暫定読解

- **`α=1.0` のまま β だけ上げる**と、**全 48 チームで `gap` が同じ 1 値**に揃う前提なら、**before `gap_unique=1` は維持**される。本 2 save では **β と同額**で **`gap_min=gap_max`** となっており、**user 断面の `gap` も β と一致**（**floor が効いている読み**で矛盾しない）。
- **`payroll_budget`** は **roster + β**（＋式が上回る場合は式側）に応じて **段階的に増加**している。
- **`summary.room_unique=1` / `pre_le_room=0`** は **3 段階いずれも変化なし**。
- **`final_offer > buffer`（30M 基準）は 1920/1920 のまま**（本観測範囲では **飽和パターンは維持**）。
- **D2 と D1**で **数値は違うが**、**「全員同一 gap・matrix 補助は潰れたまま」という形は同型**。

---

## 5. 今回の暫定判断

- **最終 β は決めない**。ただし **BUFFER だけを上げても、本母集団・本手順では `room_unique` / `pre_le_room` の潰れは解けていない**。
- **次に進む方向**: **BUFFER だけで十分か、RATIO や別レバーが必要か**を **別途短い決裁**で切る（**本結果を入力**とする）。

---

## 6. 非目的

- **本メモは最終 β の確定ではない**。
- **RATIO・clip・λ・FA buffer の変更**は本ラウンドに含めない。

---

## 7. 次に続く実務（1つだけ）

**本結果を踏まえ、BUFFER だけで十分か／次に RATIO も触る必要があるかを判断する **短い決裁メモ**を `docs/` に 1 本作成する**。

---

## 実行コマンド（実施時）

リポジトリルート、`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` を **各 Step の値に合わせたうえで**（観測後 **3M に復帰**）:

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav" --apply-temp-postoff-floor
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav" --apply-temp-postoff-floor
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_RESULTS_2026-04.md -Pattern "目的|条件|結果表|暫定読解|今回の暫定判断|非目的|次に続く実務"
Select-String -Path basketball_sim\models\offseason.py -Pattern "TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER|reapply_temp_postoff"
Select-String -Path tools\fa_offer_real_distribution_observer.py -Pattern "apply-temp-postoff-floor"
```

---

## 改訂履歴

- 2026-04-08: 初版（3M/10M/30M × D2/D1、`--apply-temp-postoff-floor` 付き観測、コード BUFFER 3M 復帰記載）。
