# `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` 段階比較 — tuning 指示書（実装前）

**作成日**: 2026-04-08  
**性質**: **比較観測計画の固定（コード変更なし）**。前段決裁: `docs/PAYROLL_BUDGET_POSTOFF_TEMP_TUNING_DECISION_2026-04.md`。⑦内フロー: `docs/PAYROLL_BUDGET_POSTOFF_INLINE_FLOW_MEMO_2026-04.md`。観測の読み方・代表表: `docs/FA_BEFORE_GAP_REPRESENTATIVE_SAVE_TABLE_2026-04.md`。

---

## 1. 目的

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`（β 相当）だけ**を **段階的に変え**、**before 主軸**の観測が **どの水準から崩れ始めるか**（**分布が開き始めるか**）の **感触**を取るための **tuning 指示書**である。
- **本書はコード差し替えそのものではない**。**比較観測の手順と見る項目**を **1 本に固定**する文書である（**最適化・最終値確定ではない**）。

---

## 2. 前提整理

- **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO = 1.0` は固定**したまま、**全ステップで変えない**。
- **動かすのは** `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` **のみ**（コード上の定数名は `offseason.py` 参照）。
- **観測の主軸**は **`before`**（同期前の集計）。**`summary`**（同期後由来）は **補助**。
- **`clip` / `λ` / FA 経路の `buffer`** は **触らない**（**別トラック**）。

---

## 3. 比較ステップ案（3 段階のみ）

| Step | `β`（`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`） | 位置づけ |
|------|---------------------------------------------------|----------|
| **Step 1** | `3,000,000` | **現状ベースライン**（既観測の出発点） |
| **Step 2** | `10,000,000` | **中間** |
| **Step 3** | `30,000,000` | **上振れ**（FA 同期側の buffer 額と **別物**。数値が偶然近いだけで **連動変更ではない**） |

- **3 段階で打ち止め**。**4 段階目以降は本計画に含めない**。
- **目的**は **最適な β を決めることではない**。**崩れ始めの地点の感触**を取ること。

---

## 4. 各ステップで見る項目

各 Step ごとに、**同一手順・同一ツール**で **最低限**次を記録する。

| 項目 | 内容 |
|------|------|
| **before `gap_unique`** | 全対象チームで `gap` の **ユニーク数** |
| **before `gap_min` / `gap_max`** | **before** の **最小・最大 gap** |
| **`user_team_snapshot`** | **`payroll_budget` / `roster_payroll` / `gap`**（user の実測行） |
| **`summary`** | **`room_unique` / `pre_le_room`** |
| **（任意）`final_offer > buffer`** | **比率**（飽和が続くかの補助） |

---

## 5. 観測対象

- **優先**: 既存の **postfloor** 用 save（決裁メモの **D2 / D1 2 本**）。  
  - `debug_user_boost_d2_user_postfloor.sav`  
  - `debug_user_boost_d1_user_postfloor.sav`
- **2 本で十分**。**save を増やして母集団を広げることは本計画の必須としない**。

---

## 6. 今回の判断（計画に含める前提）

- **次段は BUFFER 先行**（決裁どおり）。**本計画でも `RATIO` は固定**。
- **3M → 10M → 30M** の **3 段階**で比較し、**各段階で** **`room_unique=1` / `pre_le_room=0` が維持されるか**、あるいは **どの段階から変化の兆しがあるか**を **記録する**。
- **本計画内では最終 β を決めない**。**「効いた／効かない」の断定**も **観測後**に回す。

---

## 7. 非目的

- **本書のみでのコード変更**。
- **`RATIO` の調整**を本ラウンドの主題にすること。
- **`clip` / `λ` / FA `buffer` の変更**。
- **最終値・推奨値の断定**。
- **save の大量追加**。

---

## 8. 次に続く実務（1つだけ）

**本計画に沿い、`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` を **3M / 10M / 30M** で **順に差し替え**、毎回 **同一観測コマンド**でログを取る **Cursor 向けの実装＋観測指示書**を **`docs/` に 1 本**作成する（**1 Step ごとの差し替え・実行・記録テンプレ**まで含めてよい）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_PLAN_2026-04.md -Pattern "目的|前提整理|比較ステップ案|各ステップで見る項目|観測対象|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（BUFFER 3 段階・D2/D1 postfloor・観測項目固定）。
