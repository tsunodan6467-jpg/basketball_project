# FA：`sync_observation` の **before** 主軸で見た save 間比較（budget／roster／gap）

**作成日**: 2026-04-08  
**文書の性質**: **観測メモ（コード変更なし）**。読み方の決裁: `docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`。原因整理: `docs/FA_ROOM_UNIQUE_ONE_CAUSE_NOTE_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py` の `_teams_payroll_gap_stats`（**同期前**のチーム列に対して実行した値＝`sync_observation` の `before` 行と一致）。

---

## 1. 文書の目的

**第一読み取り軸は `before`（同期前）**（決裁どおり）としたとき、**手元 save 間で `payroll_budget`／ロスター給与／`gap`（= `payroll_budget - roster`、room 相当）にどれだけ差があるか**を整理する。**同期後の均一化以前に、before 自体が似通っているか**を切り分け、**before 比較用のアンカー save**を固定する。

---

## 2. 観測条件

- **環境**: `c:\Users\tsuno\Desktop\basketball_project`、Python で observer モジュールを `importlib` 読込。  
- **指標**: save 読込直後（**`_sync_payroll_budget_with_roster_payroll` 未実行**）の全チームについて、observer と同じ **`_teams_payroll_gap_stats(teams)`**（`n`, `budget_unique`, `roster_unique`, `gap_unique`, `gap_min`, `gap_max`）。  
- **モード**: **`before` は population（既定／mixed）に依存しない**（同一 save なら FA サンプル前のチーム状態のみ）。本表は **既定 world 相当の save 読みのみ**（mixed は **before 行は同一**のため未二重掲載）。  
- **対象 save（本観測で実在したファイル）**  
  - シミュレート既定: **seed=42・seasons=0**（引数なし observer と同型の `_build_simulated_world`）  
  - `C:\Users\tsuno\.basketball_sim\saves\fa_clip_test_01.sav` … `fa_clip_test_05.sav`  
  - `fa_clip_var_20260408_01.sav` … `fa_clip_var_20260408_03.sav`  
- **参照（本リポジトリ実行環境では未配置）**: 過去観測で用いた **`quicksave.sav`**, **`0330確認.sav`** — 手元にあれば **同手順で `before` 行を追記**すればよい。  
- **再現（save 列挙は環境に合わせる）**

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\fa_clip_test_01.sav"
python tools\fa_offer_real_distribution_observer.py --save-list "C:\Users\tsuno\.basketball_sim\saves\fa_clip_test_01.sav" "C:\Users\tsuno\.basketball_sim\saves\fa_clip_test_02.sav"
```

（`sync_observation` の **`before:`** 行が本表と一致する。）

---

## 3. before 主軸での save 間比較

| save（論理名） | 条件 | budget_unique | roster_unique | gap_unique | gap_min | gap_max | メモ |
|----------------|------|---------------|---------------|------------|---------|---------|------|
| sim_quick_seed42 | 既定シミュ | 1 | 48 | 1 | 0 | 0 | 引数なし observer と同型。 |
| fa_clip_test_01 | default | 1 | 48 | 1 | 0 | 0 | 全チーム同一 `payroll_budget` 型。 |
| fa_clip_test_02 | default | 48 | 48 | 1 | 0 | 0 | チームごとに `payroll_budget` は異なるが **gap は全域 0**。 |
| fa_clip_test_03 | default | 48 | 48 | 1 | 0 | 0 | test_02 と同型（before）。 |
| fa_clip_test_04 | default | 48 | 48 | 1 | 0 | 0 | 同上。 |
| fa_clip_test_05 | default | 48 | 48 | 1 | 0 | 0 | 同上。 |
| fa_clip_var_20260408_01 | default | 1 | 48 | 1 | 0 | 0 | test_01 型。 |
| fa_clip_var_20260408_02 | default | 48 | 48 | 1 | 0 | 0 | test_02 型。 |
| fa_clip_var_20260408_03 | default | 1 | 48 | 1 | 0 | 0 | test_01 型。 |

**補助（同期後）**: いずれの save も過去どおり **sync1／sync2 で `gap_min=max=30_000_000`**・**`gap_unique=1`** へ収斂（`sync_observation` 既報）。本メモでは **before 主軸**のため詳細は省略。

---

## 4. 今回の観測から分かること

1. **`gap`（room 相当）の before 分布は save 間で同型**:**いずれも `gap_unique=1` かつ `gap_min=gap_max=0`**。つまり **同期前から「全チーム gap=0」一色**。  
2. **save 間で違うのは主に `budget_unique`（1 vs 48）**。**ロスター給与は `roster_unique=48`**（全員異なる年俸合計）で揃っている例が多い。  
3. **ボトルネック**は **同期後の buffer 均一化だけではない**。**before 時点でも gap の多様性は出ていない**（少なくとも本手元 save 群）。  
4. **save を増やしても**、**同じ「budget は変わるが gap=0」パターン**に留まるなら、**before 主軸での clip 用多様化はまだ不足**しやすい。  
5. **quicksave／0330** は本実行環境に無かったが、過去 playcheck 上も **同期後は同型**であり、**before も本表と同じ機構なら gap=0 一色になりうる**（要・手元での同手順確認）。

---

## 5. 推奨する before 比較用アンカー

| 優先 | save | 理由 |
|------|------|------|
| **第一候補** | **`fa_clip_test_02.sav`**（無ければ **`fa_clip_var_20260408_02.sav`**） | **before で `budget_unique=48`** と **`budget_unique=1` の save** を並べたときの **対比軸**が最もはっきりする（**gap はどちらも 0 一色**だが、**予算フィールドのばらつき**は読み分けられる）。 |
| **第二候補** | **`fa_clip_test_01.sav`**（無ければ **`fa_clip_var_20260408_01`** または **`_03`**） | **`budget_unique=1`** の **ベースライン**（全チーム同一予算型）。 |

**`quicksave.sav`**: 手元に存在する場合は **報告・再現のデフォルト名**として **第一候補の代わりに固定**してよいが、**本観測では before の **gap** は上表タイプと同型になりやすい**と想定される。**before で「差」を見る主戦場は現状 **`budget_unique` の 1 vs 48 の対比**。

---

## 6. 今回はまだやらないこと

- **observer の追加改修**  
- **`_sync_payroll_budget_with_roster_payroll` の改造**  
- **`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` の変更**  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`docs/FA_CLIP_COMPARE_SAVE_REQUIREMENTS_2026-04.md` の要件に沿って、before 時点で **`gap_unique > 1`** または **`gap_min < gap_max`** となりうる save を **新規に採取**し、本メモの表を **1 行追記する観測ラウンド**（**コード差分なし**）。**

- **なぜその1手が今もっとも妥当か**  
  手元 save では **before の gap が save 間で全く分かれない**。**λ／clip のコードを動かす前に**、**観測装置が読める入力多様性**をデータ側で確保する必要がある。  
- **何はまだ残るか**  
  **新 save で before が開いた後の**、`--save-list` 再スクリーニング、**同期スキップの別決裁**、**本アンカー表の更新**。

---

## 改訂履歴

- 2026-04-08: 初版（before 主軸の save 間比較）。
