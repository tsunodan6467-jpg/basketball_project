# RATIO（α）3 段階観測結果（D2/D1 postfloor）

**作成日**: 2026-04-08  
**性質**: **観測記録**。計画: `docs/PAYROLL_BUDGET_POSTOFF_RATIO_TUNING_PLAN_2026-04.md`。前段決裁: `docs/PAYROLL_BUDGET_POSTOFF_RATIO_DECISION_2026-04.md`。

---

## 1. 目的

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO` を 1.0 / 1.05 / 1.10** としたときの **before 主軸**・**user 断面**・**補助 summary** を **1 本に固定**する。
- **最終 α の決定ではない**。

---

## 2. 条件

| 項目 | 内容 |
|------|------|
| **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`（β）** | **固定 `3_000_000`**（**本観測で変更なし**） |
| **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`（α）** | Step ごとに **1.0 → 1.05 → 1.10**（観測後 **コードは `1.0` に復帰済み**） |
| **観測 save（2 本）** | `debug_user_boost_d2_user_postfloor.sav` / `debug_user_boost_d1_user_postfloor.sav`（フルパスは計画メモ参照） |
| **ツール** | `tools/fa_offer_real_distribution_observer.py` **`--apply-temp-postoff-floor`** |
| **`final_offer > buffer` の buffer** | **FA 経路 30M**（`TEMP postoff` の β とは別） |

---

## 3. 結果表

**凡例**: `final_offer > buffer` は全 Step・両 save で **1920/1920（100%）**（**本観測範囲では不変**）。

### Step 1 — α = 1.0

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|---------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 postfloor | 2 | 1 | 3,000,000 | 3,000,000 | 993,010,000 | 990,010,000 | 3,000,000 | 1 | 0 |
| D1 postfloor | 1 | 1 | 3,000,000 | 3,000,000 | 918,190,000 | 915,190,000 | 3,000,000 | 1 | 0 |

### Step 2 — α = 1.05

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|---------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 postfloor | 2 | 48 | 28,764,593 | 59,702,788 | 1,042,510,500 | 990,010,000 | 52,500,500 | 46 | 0 |
| D1 postfloor | 1 | 48 | 32,613,748 | 57,352,239 | 963,949,500 | 915,190,000 | 48,759,500 | 48 | 0 |

### Step 3 — α = 1.10

| save | `league_level` | before `gap_unique` | before `gap_min` | before `gap_max` | `payroll_budget` | `roster_payroll` | `gap` | `room_unique` | `pre_le_room` |
|------|----------------|---------------------|------------------|------------------|------------------|------------------|-------|---------------|---------------|
| D2 postfloor | 2 | 48 | 54,529,187 | 116,405,577 | 1,092,011,000 | 990,010,000 | 102,001,000 | 48 | 958 |
| D1 postfloor | 1 | 48 | 62,227,496 | 111,704,479 | 1,009,709,000 | 915,190,000 | 94,519,000 | 48 | 72 |

---

## 4. 暫定読解

- **α=1.0**: **BUFFER-only 観測と同型**（**`gap_unique=1`**、**`room_unique=1`**、**`pre_le_room=0`**）。
- **α=1.05**: **before の `gap` がチームごとに分散**（**`gap_unique=48`**、`gap_min`〜`gap_max` が **数千万円台**）。**user の `gap`** は **D2 52,500,500 / D1 48,759,500**。**`room_unique`** は **D2 で 46**、**D1 で 48**。**`pre_le_room` は両方 0**。
- **α=1.10**: **before の gap レンジはさらに拡大**。**user `gap`** は **D2 102,001,000 / D1 94,519,000**。**`room_unique=48`**（両 save）。**`pre_le_room`** が **0 から離脱**（**D2: 958**、**D1: 72**）。
- **D2 と D1** で **数値は異なるが**、**「α を上げると before が開き、1.10 で `pre_le_room` が動く」**という **傾向は共通**。

---

## 5. 今回の暫定判断

- **最終 α は決めない**。ただし **本母集団・手順では、α を 1.05 以上にすると BUFFER 単独時には崩れなかった before / matrix 側の潰れが緩む**。
- **次の論点**: **RATIO だけで十分か**、**β と α の組合せ**で **どこまで戻せるか**を **別決裁**で切る。

---

## 6. 非目的

- **本メモは最終 α の確定ではない**。
- **β・clip・λ・FA buffer の変更**は本ラウンドに含めない。

---

## 7. 次に続く実務（1つだけ）

**本結果を踏まえ、RATIO だけで十分か／次に **β と α の組合せ比較**へ進むべきかを判断する **短い決裁メモ**を `docs/` に 1 本作成する**。

---

## 実行コマンド（実施時）

リポジトリルート。**各 Step で `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO` を合わせたうえで**（観測後 **`1.0` に復帰**）:

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d2_user_postfloor.sav" --apply-temp-postoff-floor
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\debug_user_boost_d1_user_postfloor.sav" --apply-temp-postoff-floor
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_RATIO_TUNING_RESULTS_2026-04.md -Pattern "目的|条件|結果表|暫定読解|今回の暫定判断|非目的|次に続く実務"
Select-String -Path basketball_sim\models\offseason.py -Pattern "TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO"
```

---

## 改訂履歴

- 2026-04-08: 初版（α 1.0/1.05/1.10 × D2/D1、観測後 **RATIO=1.0 復帰**記載）。
