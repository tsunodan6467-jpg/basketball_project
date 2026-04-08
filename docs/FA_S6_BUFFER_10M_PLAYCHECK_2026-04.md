# S6：`payroll_budget` buffer 1000万円適用後の「1000万円張り付き」観測メモ

**作成日**: 2026-04-06  
**文書の性質**: **観測メモ（コード変更なし）**。第二試行決裁: `docs/FA_S6_BUFFER_10M_DECISION_MEMO_2026-04.md`。第一試行観測: `docs/FA_S6_BUFFER_3M_PLAYCHECK_2026-04.md`。第一試行決裁: `docs/FA_S6_BUFFER_INCREASE_DECISION_MEMO_2026-04.md`。buffer 実装: `basketball_sim/models/offseason.py` の `_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER`・`_sync_payroll_budget_with_roster_payroll`。観測スクリプト: `tools/fa_offer_real_distribution_observer.py`、`tools/fa_offer_diagnostic_observer.py`。

---

## 1. 文書の目的

**1000万円 buffer 第二試行**適用後、S6（`room_to_budget` 起因）で **`final_offer` が 1000万円に張り付く現象がどの程度残るか**を数値化し、**10M の当面維持**／**次段（例: 3000万円 buffer）の検討**／**追加観測で止める**のどれに進むか判断する材料にする。

---

## 2. 観測方法

- **主**: `tools/fa_offer_real_distribution_observer.py` を **既定引数**（`--save` なし、`--seasons 0`、`--seed 42`、`--fa-cap 40`）で実行。リポジトリルートで `python tools/fa_offer_real_distribution_observer.py`。  
  - 処理内容: クイック生成ワールド → **`_sync_payroll_budget_with_roster_payroll` を2回**（本番 `Offseason.run` と同順）→ 全 `Team` × **年俸上位40名の FA** で `_calculate_offer_diagnostic` を走らせる（実装は当該スクリプト参照）。  
  - stdout では **`0 < final <= 3_000_000`**、**`0 < final <= buffer（10,000,000）`**、**`soft_cap_early False` かつ上記** 等が既に出る。  
- **補助**: `tools/fa_offer_diagnostic_observer.py`（合成9ケース。S6b は `payroll_budget = roster + _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` ＝10M 同期想定）。  
- **張り付き件数（`final_offer == 10_000_000`）**: スクリプト stdout に **厳密一致件数は無い**ため、**同一手順の行列**に対し、リポジトリ改変なしの **`python -c`** で `tools.fa_offer_real_distribution_observer` の `_build_simulated_world` → 同期2回 → `_run_matrix` と同じ経路を再実行し集計した（再現手順は §3 脚注）。  
- **再現コマンド（最低限）**  
  - `python -m basketball_sim --smoke`  
  - `python tools/fa_offer_real_distribution_observer.py`  
  - `python tools/fa_offer_diagnostic_observer.py`  

---

## 3. 1000万円張り付きの観測結果

### 3.1 分布観測（クイック生成・既定・seed 42）

| 指標 | 件数 | 比率（総サンプル比） |
|------|------|----------------------|
| **総サンプル**（team × FA） | **1920** | 100% |
| **`final_offer == 0`** | **0** | 0% |
| **`soft_cap_early == True`（S1）** | **0** | 0% |
| **`0 < final_offer <= 10_000_000`** | **1920** | **100%** |
| **`soft_cap_early == False` かつ上記** | **1920** | **100%** |
| **`room_to_budget` not None かつ `<= 10_000_000`** | **1920** | **100%** |
| **`final_offer == 10_000_000`（1000万円張り付き）** | **1920** | **100%** |
| **`soft_cap_early == False` かつ `final_offer == 10_000_000`** | **1920** | **100%** |
| **高額 FA（`salary >= 50_000_000`）かつ `final_offer == 10_000_000`** | **1920** | **100%** |
| **`soft_cap_early == False` かつ `0 < final_offer < 10_000_000`** | **0** | 0% |
| **`final_offer > 10_000_000`** | **0** | 0% |

**D1 / D2 / D3**: 全サンプル・**`final == 10M`** ともに **各 640 件**（33.33%）。**偏りなし**。

**3M 第一試行との対比**（同一観測系・`FA_S6_BUFFER_3M_PLAYCHECK`）: 当時は **`final == 3_000_000` が 1920/1920**。今回は **`final == 10_000_000` が 1920/1920**＝**天井は buffer 額に追従し、行列全体の「全面張り付き」パターンは維持**。

**30万円・300万円帯（参考）**: 同一条件下 **`0 < final <= 300_000` は 0**、**`0 < final <= 3_000_000` は 0**（いずれも解消済み）。

### 3.2 合成観測（`fa_offer_diagnostic_observer.py`）

- S6b（`room_to_budget = 10_000_000`）: **中額 FA は `final_offer = 5_000_000`**、**高額 FA は `final_offer = 10_000_000`**（高額のみ buffer 天井クリップ）。  
- `matrix_D1_empty_ovr65`（812,500）・`matrix_D2_roomy`（7,500,000）・healthy 系は **10M 未満または帯外**で、**クイック生成の「全ペア同型」ではない多様性**を示す。

### 3.3 代表例（合成・抜粋）

| ラベル | `room_to_budget` | `final_offer` | 備考 |
|--------|------------------|---------------|------|
| S6b_D1_buffer_midFA | 10,000,000 | 5,000,000 | 芯が room 内 |
| S6b_D1_buffer_highFA | 10,000,000 | 10,000,000 | 高額 → 10M 張り付き |
| S6b_D2_buffer_midFA | 10,000,000 | 5,000,000 | D2 でも同型 |

---

## 4. 今回の観測から分かること

- **10M に上げても**、**クイック生成・既定・同一行列**では **S6 由来の「buffer 天井＝オファー天井」の全面占有は継続**（1920/1920）。**張り付きの「額」だけが 3M → 10M にスケール**した。  
- **3M 時代からの改善**: **300万円以下への張り付きは 0**。オファー下限の桁は上がり、**決裁メモどおり「芯が数百万〜数千万帯に届く余地」は、この合成世界では表れない**（すべて 10M クリップ側に寄せ切り）。  
- **不自然さ**: **経済シミュとして「全チーム×上位FAがすべて同額」**は強いが、**第一試行と同じ「観測装置が示す構造」**であり、**バグ疑いより設計上の天井の見え方**に近い。一方 **合成9件では張り付き以外の芯**も出るため、**世界の作り方次第で分布は開く**。  
- **次に動かすノブ**: 同型の詰まりを緩めるのは **buffer をさらに上げる**のが直線的だが、**経営・CPU FA への影響が累積**する。**`_calculate_offer` の budget クリップ以外**（手動 FA floor 等）は別論点のまま。

---

## 5. 今の 1000万円に対する判断

- **当面の第二試行として 10M 実装を取り消す必要はない**（決裁どおり一段の緩和は入った）。  
- **ただし**、**クイック観測だけを見る限り「第三試行（例: 3000万円）をすぐコードに載せる」根拠は十分**（全面張り付きが続いている）。**経営バランスの最終判断には、もう一段の観測を挟むのが安全**。  
- **推奨の進め方**: **まず `--save`（実セーブ）または `--seasons 1` 等で代表性を増やした同一スクリプト再観測を1本行い**、**10M 全面張り付きがクイック生成特有か**を見る。**それでも同型なら**、**3000万円第三試行の決裁メモ → 定数更新**が自然な次段。  
- **結論（短く）**: **10M は「第二試行の到達点」として当面維持してよいが、「観測上の終着」ではない**。**次は観測拡張を優先**し、**全面張り付きが続くなら 30M 級 buffer を決裁付きで検討**するのが妥当。

---

## 6. 今回はまだやらないこと

- **`_calculate_offer` 本体の改造**（budget クリップ式・下限ルールの再設計）  
- **floor 条件の変更**（`offseason_manual_fa_offer_and_years` 等）  
- **オフ手動FAの全面再設計**  
- **低額／高額例外ルールの本体追加**  
- **`_calculate_offer_diagnostic` のロジック変更**  
- **第三試行 buffer の無決裁コード変更**（本メモは観測のみ）  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**次に取るべき単一の作業**: **`tools/fa_offer_real_distribution_observer.py` を、実セーブ（`--save path/to/file.sav`）または `--seasons 1`（同一 seed のまま）など、クイック生成以外の条件で少なくとも1本再実行し、`final_offer == 10_000_000` 件数・比率・D1/D2/D3 内訳を本メモ同様に記録する（コード変更は不要）。**

- **なぜその1手が今もっとも妥当か**  
  本観測では **1920/1920 が 10M 張り付き**と **3M 時代の 1920/1920 と同型**であり、**buffer をさらに上げる前に、世界の代表性を増やさないと「経営として許容できる張り付き率」が評価できない**。合成9件は既に **10M 未満の芯**を示しており、**クイック行列が最悪ケース寄り**である可能性が高い。  

- **何はまだ残るか**  
  **追加観測でも全面 10M が続く場合**の **`docs/` における第三試行（例: 3000万円）決裁メモ**、および承認後の **`offseason.py` 定数のみの更新**。**億超 FA の本格式芯**・**長期のオーナー目標整合**は、buffer 以外の論点として引き続き残る。

---

## 再現用メモ（`final == 10M` 件数の集計）

リポジトリルートで、上記と同じ `seed=42`・`fa_cap=40`・`seasons=0` の前提のまま、`python -c` から `tools.fa_offer_real_distribution_observer` の `_build_simulated_world` → `_sync_payroll_budget_with_roster_payroll` ×2 → `_select_fa_sample` → `_run_matrix` を呼び、行リストに対して `sum(1 for r in rows if r["final_offer"] == 10_000_000)` 等を数える（**リポジトリへのファイル追加は不要**）。

---

## 改訂履歴

- 2026-04-06: 初版（10M buffer 適用後の 1000万円張り付き観測）。
