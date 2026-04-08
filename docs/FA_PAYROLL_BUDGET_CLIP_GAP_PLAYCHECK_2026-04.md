# FA：クリップ前 `offer` と `room_to_budget` の乖離規模（観測メモ）

**作成日**: 2026-04-08  
**文書の性質**: **観測メモ（コード変更なし）**。クリップ式・λ 試行の文脈: `docs/FA_PAYROLL_BUDGET_CLIP_FORMULA_OPTIONS_NOTE_2026-04.md`、`docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_01_PLAYCHECK_2026-04.md`、`docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_SECOND_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py` の `_calculate_offer_diagnostic`（クリップ直前の芯は **`offer_after_soft_cap_pushback`**）、`_clip_offer_to_payroll_budget`。

---

## 1. 文書の目的

観測行列で **`final_offer > buffer` が λ=0.1 / 0.05 のいずれでも全面化**する要因が、**λ 単体**なのか、**クリップ前の `offer` が `room_to_budget` をどれだけ上回っているか**に起因するのかを切り分ける。次の判断（λ 微調整 vs 観測の見方変更）の**入力**とする。

---

## 2. 観測方法

- **行列**: `tools/fa_offer_real_distribution_observer.py` と**同一**（`_build_simulated_world` seed=42、fa-cap=40、seasons=0、または quicksave 読込後 `_sync_payroll_budget_with_roster_payroll` ×2、`_run_matrix`）。**総ペア 1920**。  
- **クリップ前の offer**: 診断辞書の **`offer_after_soft_cap_pushback`**（`_clip_offer_to_payroll_budget` 直前。`payroll_budget` 未設定時は soft cap 由来の room だが、本行列では `room_to_budget` が整数で入る条件のみ集計）。  
- **room**: 診断の **`room_to_budget`**（`payroll_budget - payroll_before` の非負クリップ）。  
- **補助集計**: リポジトリルートで **変更なしの `python -c`**（上記モジュールを `importlib` で読み、1920 行を走査）。既存 observer の stdout（`final > buffer` 等）は **従来どおり参照**。  
- **合成**: `python tools/fa_offer_diagnostic_observer.py` の **S6b 中額／高額**（代表例の対比用）。

**再現用（行列＋集計のイメージ）**

```text
python tools/fa_offer_real_distribution_observer.py
python tools/fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav"
python tools/fa_offer_diagnostic_observer.py
```

（乖離の min/med/max は、本メモ作成時に **`python -c`** で `offer_after_soft_cap_pushback` と `room_to_budget` を走査して算出。）

---

## 3. `offer` と `room_to_budget` の乖離観測

### 3.1 観測行列（quick 既定・seed=42・fa-cap=40）

| 項目 | 結果 |
|------|------|
| **対象ペア** | **1920**（`soft_cap_early` なし・`room_to_budget` ありは **1920/1920**） |
| **`room_to_budget` の値** | **すべて `30,000,000`**（一意。buffer 同期後の典型パターン） |
| **`offer_after_soft_cap_pushback <= room`** | **0** |
| **`offer_after_soft_cap_pushback > room`** | **1920（100%）** |
| **ギャップ `offer - room`（最小／中央値／最大）** | 約 **41,744,961／55,400,000／72,175,000** |
| **ギャップ 近似 p10／p90** | 約 **52,350,000／63,025,000** |
| **`offer / room`（最小／中央値／最大）** | 約 **2.39／2.85／3.41** |
| **クリップ前 offer の種類数** | **17 通り**（上位 FA 年俸×チーム金残りの組合せに集約） |

**代表（ギャップ最大付近）**: `offer` 約 **102,175,000**、`room` **30,000,000**（`offer / room` 約 **3.41**）。  
**代表（ギャップ最小付近）**: `offer` 約 **71,744,961**、`room` **30,000,000**（ギャップ 約 **41.7M**）。

### 3.2 quicksave（同一スクリプト・1920 ペア）

- **`pre <= room`**: **0**、**`pre > room`**: **1920**。  
- **`room_to_budget`**: **すべて 30,000,000**。  
- **ギャップ min／中央／max**: 約 **40,278,856／55,400,000／70,650,000**。  
- **`offer/room` min／中央／max**: 約 **2.34／2.85／3.36**。  

→ **quick と同型**（全面 **`offer ≫ room`**）。

### 3.3 合成 diagnostic（対比）

- **S6b 中額**（`room_to_budget = 30M`）: クリップ前芯は **room 未満**（`final_offer = 5,000,000`）。**`offer ≤ room` 帯の代表**。  
- **S6b 高額**: 芯は **room を大きく超える**（λ=0.05 時 `final` **33,930,000** 等）。**観測行列はこちら側の人口だけで埋まっている**イメージに近い。

### 3.4 「行列は `offer ≫ room` 支配か」

**はい。** 本装置の **1920 ペアでは `room` は常に 30M、クリップ前 `offer` はすべて 30M 超**。**中央値で offer が room の約 **2.85 倍**、最小でも約 **2.34 倍**。  
このとき `final = room + round(λ * (offer - room))` では、**最小ギャップでも** `round(0.05 × 約 4.17×10^7) ≈ 2.09×10^6` → **`final` は約 32.1M > buffer（30M）**。**λ を 0.05→0.025 に半分しても**同様に **> 30M** が続くのは、**入力ギャップが一様に大きい**ためと整合的。

---

## 4. 今回の観測から分かること

- **λ 感度だけの問題ではない**: λ は合成高額例で **効いている**（37.86M→33.93M）が、**本行列ではクリップ前から `offer - room` が数十 M オーダーで一様に正**のため、**正の λ では `final > buffer` が構造的に出やすい**。  
- **次の優先**: **λ の細かい第三試行（0.025 等）だけでは、この行列では「`> buffer` 全面化が解ける」見込みは低い**（ギャップ最小でも buffer 超えが残る）。**観測対象の再設計**（例: room が大きいチーム、中額 FA 中心、シーズン後ロスター）か、**別指標**（ギャップ分布・`offer/room`）を**常設で見る実装の決裁**の方が情報価値が高い。  
- **第三試行 λ の価値**: **「まだ λ を動かす」なら、目的を「全面化解消」ではなく「絶対額の感度確認」に限定**するのが正直。全面化の有無は **本行列ではほぼ判別不能**に近い。

---

## 5. 今回はまだやらないこと

- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の無決裁変更**  
- **`_clip_offer_to_payroll_budget` の式タイプ変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の全面改造**  
- **floor 条件の変更**  
- **オフ手動 FA の全面再設計**  
- **低額例外ルールの本体追加**  
- **観測スクリプトの改修**（本メモは `python -c` のみ）

---

## 6. 次に実装で触るべき対象（1つだけ）

**`docs/` に「第三試行を λ=0.025 にするか、観測行列を差し替えるか」を1行で決める短文決裁メモを1本追加する**（本観測を根拠に、**第三試行 λ を打つなら目的を感度確認に限定する**旨を明記できるとよい）。

- **なぜその1手が今もっとも妥当か**  
  **コードを動かす前に**、本メモの事実（**1920 件すべて `offer_after_soft_cap_pushback > room`、room は 30M 固定**）を**決裁に取り込む**と、**λ 連打の打ち止め**と**観測投資の向き先**が揃う。  

- **何はまだ残るか**  
  **新しい観測行列の具体仕様**、**observer への集計1行追加するか否か**、**別式クリップの比較**、**プレイヤー向け説明**。

---

## 改訂履歴

- 2026-04-08: 初版（クリップ前 offer と room の乖離集計）。
