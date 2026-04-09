# α×β 4 セル観測結果（D2/D1 postfloor）

**作成日**: 2026-04-08  
**性質**: **観測記録**。計画: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_PLAN_2026-04.md`。

---

## 1. 目的

- **Cell A〜D**（**α=1.05/1.10 × β=3M/10M**）の **before 主軸**・**user 断面**・**補助 summary** を **1 本に固定**する。
- **最終 α/β の決定ではない**。

---

## 2. 条件

| 項目 | 内容 |
|------|------|
| **Cell A** | α=1.05, β=3,000,000 |
| **Cell B** | α=1.05, β=10,000,000 |
| **Cell C** | α=1.10, β=3,000,000 |
| **Cell D** | α=1.10, β=10,000,000 |
| **save（2 本）** | `debug_user_boost_d2_user_postfloor.sav` / `debug_user_boost_d1_user_postfloor.sav`（フルパスは計画メモ参照） |
| **ツール** | `tools/fa_offer_real_distribution_observer.py` **`--apply-temp-postoff-floor`** |
| **`final_offer > buffer`** | **FA 30M** 基準（TEMP postoff の β とは別） |
| **観測後のコード** | **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO = 1.0`**、**`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER = 3_000_000`** に **復帰済み** |

---

## 3. 結果表

**凡例**: **`final_offer > buffer`** は **全 Cell・両 save で 1920/1920（100%）**（**本観測範囲では不変**）。

### Cell A — α=1.05, β=3M

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|----------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 | 2 | 48 | 28,764,593 | 59,702,788 | 1,042,510,500 | 990,010,000 | 52,500,500 | 46 | 0 |
| D1 | 1 | 48 | 32,613,748 | 57,352,239 | 963,949,500 | 915,190,000 | 48,759,500 | 48 | 0 |

### Cell B — α=1.05, β=10M

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|----------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 | 2 | 48 | 35,764,593 | 66,702,788 | 1,049,510,500 | 990,010,000 | 59,500,500 | 48 | 40 |
| D1 | 1 | 48 | 39,613,748 | 64,352,239 | 970,949,500 | 915,190,000 | 55,759,500 | 48 | 0 |

### Cell C — α=1.10, β=3M

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|----------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 | 2 | 48 | 54,529,187 | 116,405,577 | 1,092,011,000 | 990,010,000 | 102,001,000 | 48 | 958 |
| D1 | 1 | 48 | 62,227,496 | 111,704,479 | 1,009,709,000 | 915,190,000 | 94,519,000 | 48 | 72 |

### Cell D — α=1.10, β=10M

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|----------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 | 2 | 48 | 61,529,187 | 123,405,577 | 1,099,011,000 | 990,010,000 | 109,001,000 | 48 | 1,148 |
| D1 | 1 | 48 | 69,227,496 | 118,704,479 | 1,016,709,000 | 915,190,000 | 101,519,000 | 48 | 189 |

---

## 4. 暫定読解

- **β を 3M→10M に上げる**（**α 固定**）と、**before の `gap_min`/`gap_max` と user `gap` が約 7M 程度ずつ増加**（**A→B**、**C→D** で同型）。**`room_unique`**: **D2 で A=46 → B=48**。**`pre_le_room`**: **D2 で A=0 → B=40**。**D1 は B でも `pre_le_room=0`**。
- **α を上げる**（**β 固定**）と、**gap レンジと user `gap` が大きく拡大**（**A→C**、**B→D**）。**`pre_le_room`** は **C/D で D2 が特に大きい**（**D > C**）。
- **D2 と D1** は **数値は違うが**、「**β 上げで gap と一部 matrix が動く**」「**α 上げで gap と `pre_le_room` が強く動く**」という **形は概ね同型**。
- **`final_offer > buffer`** は **4 セルとも不変** — **before／matrix の変化と offer 飽和はまだ連動していない**。

---

## 5. 今回の暫定判断

- **最終 α/β は決めない**。**β を足すと**、**同じ α=1.05 でも D2 の `room_unique` が開き、`pre_le_room` が 0 から動き始める** — **RATIO-only（β=3M 固定）だけでは見えなかった差**が **1 セル（B）で出た**。
- **次の論点**: **候補を 1 セルに絞って実 save 再作成まで進むか**、**もう 1 段だけ軽い比較を足すか**を **別決裁**で切る。

---

## 6. 非目的

- **本メモは最終 α/β の確定ではない**。
- **5 セル目・β=30M・clip / λ / FA buffer** は本ラウンドに含めない。

---

## 7. 次に続く実務（1つだけ）

**本結果を踏まえ、** **候補セルを 1 つに絞って実 save 再作成まで進むか**、**もう 1 段だけ軽い比較を足すか**を判断する **短い決裁メモ**を **`docs/` に 1 本**作成する。

---

## 実行コマンド（実施時）

リポジトリルート。**各 Cell で `TEMP_POSTOFF_*` を合わせたうえで**（完了後 **α=1.0, β=3M に復帰**）:

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav" --apply-temp-postoff-floor
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav" --apply-temp-postoff-floor
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md -Pattern "目的|条件|結果表|暫定読解|今回の暫定判断|非目的|次に続く実務"
Select-String -Path basketball_sim\models\offseason.py -Pattern "TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO|TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER"
```

---

## 改訂履歴

- 2026-04-08: 初版（Cell A〜D × D2/D1、観測後 **既定値復帰**記載）。
