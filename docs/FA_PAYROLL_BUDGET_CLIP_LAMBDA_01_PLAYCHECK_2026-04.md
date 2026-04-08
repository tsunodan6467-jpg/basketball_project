# FA：`payroll_budget` クリップ線形緩和 λ=0.1 適用後の観測メモ

**作成日**: 2026-04-06  
**文書の性質**: **観測メモ（コード変更なし）**。第一試行決裁: `docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_FIRST_TRIAL_DECISION_2026-04.md`。式: `docs/FA_PAYROLL_BUDGET_CLIP_FORMULA_OPTIONS_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py` の `_PAYROLL_BUDGET_CLIP_LAMBDA`・`_clip_offer_to_payroll_budget`。観測: `tools/fa_offer_real_distribution_observer.py`、`tools/fa_offer_diagnostic_observer.py`。stdout の **buffer** は `_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER`（現行 **30,000,000**）に連動する表示。

---

## 1. 文書の目的

**λ = 0.1** 第一試行適用後、主要観測系で **`final_offer` が「buffer 表示額（30M）」を超える側に全面化**した事実を整理し、**成功か／効きすぎか**、**λ を下げるか**、**追加観測で止めるか**の判断材料にする。

---

## 2. 観測方法

- **主**: `tools/fa_offer_real_distribution_observer.py`（`_calculate_offer_diagnostic` 行列、観測直前に `_sync_payroll_budget_with_roster_payroll` ×2）。  
  - **既定**（`--save` なし、`--seasons 0`、`--seed 42`、`--fa-cap 40`）  
  - **`--save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav"`**（本環境で実行可能な場合）  
  - **`--seasons 1`**（同一 seed・fa-cap）  
- **補助**: `tools/fa_offer_diagnostic_observer.py`（合成9ケース、高額 S6b の代表値確認）。  
- **本稿の数値**: 上記を **2026-04-06 時点で再実行**し、**quick 既定**および **diagnostic** の stdout を確認。**quicksave / `--seasons 1`** は直近実装直後の記録と **同型**（いずれも **1920 サンプルで `final > buffer` が 100%）であることを前提に整理（再現は上記コマンド）。

**再現コマンド（リポジトリルート）**

```text
python -m basketball_sim --smoke
python tools/fa_offer_real_distribution_observer.py
python tools/fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav"
python tools/fa_offer_real_distribution_observer.py --seasons 1
python tools/fa_offer_diagnostic_observer.py
```

---

## 3. λ=0.1 適用後の観測結果

### 3.1 `fa_offer_real_distribution_observer.py`（team × FA 行列）

| 指標 | 件数 | 比率 |
|------|------|------|
| **総サンプル** | **1920** | 100% |
| **`final_offer == 0`** | **0** | 0% |
| **`final_offer == buffer`（表示 30,000,000）** | **0** | 0% |
| **`0 < final_offer < buffer`** | **0** | 0% |
| **`final_offer > buffer`** | **1920** | **100%** |
| **`soft_cap_early == True`** | **0** | 0% |

**D1 / D2 / D3**: 各 **640**（33.33%）。**quick / quicksave / `--seasons 1`** のいずれでも **上記パターンは同型**（全面 `final > buffer`）。

### 3.2 合成 `fa_offer_diagnostic_observer.py`（抜粋）

- **S6b 高額 FA**（`room_to_budget = 30,000,000`）: **`final_offer` が 30,000,000 → 37,860,000** に変化（第一試行前後の対比で、**buffer 行表示を超える**代表例）。  
- **S6b 中額**（芯が room 内）: **`final_offer = 5,000,000`** のまま（`offer <= room` 帯は線形項が効かない）。  
- **`0 < final <= buffer（30M）` 系の件数**: 合成9件では **従来どおり複数**（高額 S6b のみ帯外に出る）。

---

## 4. 今回の観測から分かること

- **天井張り付き（`final == buffer` 表示の 30M 一致）は崩れた**。λ=0 の **硬い `min(offer, room)`** から、**`offer > room` で必ず room より上に寄る**式へ切り替わった結果として **整合的**。  
- **観測行列（上位年俸 FA × 全チーム）では**、**芯が room（典型的に buffer 幅）を大きく超えるペアが支配的**なため、**`final > buffer` が 1920/1920 と再び「全面同一パターン」**になっている。**別側への全面化**であり、**多様な帯分布が開いた**とは限らない。  
- **「分布が開いた」部分**: **合成9件では room 内／帯内のケースが残り**、**高額クリップ行だけが 30M 超へ移動**＝**式の効き方は状況依存**であることは確認できる。  
- **λ の一次評価**: **0.1 はこの観測装置上では強く**、**行列全体を「名義 buffer 超え」に寄せ切りうる**。**経営説明（`payroll_budget` と提示額）のズレ**がプレイ上目立つリスクは **λ=0 より大きい**。

---

## 5. λ=0.1 に対する現時点の判断

- **単純成功**とは言い切らない: **張り付き解消**という目的には応えるが、**本行列では再び単一パターン化**（`> buffer` 一色）が出ている。  
- **効きすぎの可能性**: **中程度〜高**（観測系依存だが、**第一試行としては想定範囲の上側**）。  
- **当面 λ=0.1 を無決裁でさらに上げるのは推奨しない**。  
- **いきなりコードで λ を弄り直す前に**、**本メモで評価を固定**し、**第二試行（例: λ=0.05）を決裁メモで切る**か、**0.1 据え置きで実セーブ・長期観測を増やす**かを選ぶのがよい。  
- **暫定推奨**: **「0.1 は観測行列では強め。次は λ 下げの決裁か、観測拡張のどちらかを明示してからコードを動かす」**。

---

## 6. 今回はまだやらないこと

- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の無決裁変更**  
- **`_clip_offer_to_payroll_budget` の式タイプ変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の全面改造**  
- **floor 条件の変更**  
- **オフ手動 FA の全面再設計**  
- **低額例外ルールの本体追加**  
- **観測スクリプトの改修**  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`docs/` に、第二試行方針を1行で決める短文決裁メモを1本追加する（例: 「λ を 0.05 に下げる」または「λ=0.1 を当面維持し、実セーブ観測を N 本追加してから再判断」）。そのメモで Go が出た場合に限り、次コミットで `_PAYROLL_BUDGET_CLIP_LAMBDA` を1行更新する。**

- **なぜその1手が今もっとも妥当か**  
  **0.1 は観測上「効いた」が「全面 > buffer」であり、数値の良し悪しは経営文脈に依存**する。**無決裁の定数いじりを連鎖させない**ため、**決裁1本を挟むのが最安**。  

- **何はまだ残るか**  
  **第二試行 λ の具体値**、**`final_offer` の分位数・ヒストグラム**（任意）、**プレイヤー向け説明文**、**手動 FA / CPU の体感レビュー**、**λ=0 回帰の継続方針**。

---

## 改訂履歴

- 2026-04-06: 初版（λ=0.1 適用後の全面 `> buffer` 観測の整理）。
