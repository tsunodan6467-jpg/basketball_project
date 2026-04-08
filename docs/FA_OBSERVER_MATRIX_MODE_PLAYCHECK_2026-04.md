# FA：`fa_offer_real_distribution_observer` population mode 観測メモ（行列条件の当たり所）

**作成日**: 2026-04-08  
**文書の性質**: **観測メモ（コード変更なし）**。設計正本: `docs/FA_OBSERVER_MATRIX_REDESIGN_PLAN_2026-04.md`。既存 gap 整理: `docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md`。行列方針決裁: `docs/FA_PAYROLL_BUDGET_CLIP_THIRD_TRIAL_OR_MATRIX_DECISION_2026-04.md`。実装: `tools/fa_offer_real_distribution_observer.py`（本メモでは未改修）。

---

## 1. 文書の目的

新設の **`--population-mode mixed_mid_fa_roomy`** と **FA ランク帯**／**`--roomy-team-count`** で、**`offer ≲ room`** や **`0 < final < buffer`** が現れ、**clip／λ の比較装置**として使える行列が得られるかを確認する。  
**次に比較実験で「第一候補として固定する実行条件」**と、**まだ観測で止めるべきか／実装に進むべきか**を1本にまとめる。

---

## 2. 観測条件

- **環境**: リポジトリルート `c:\Users\tsuno\Desktop\basketball_project`、**seed=42**（シミュレート世界）、buffer は実装どおり **`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` = 30,000,000**。  
- **集計**: `_calculate_offer_diagnostic` 由来の行列（observer と同一手順）。**クリップ前**は診断の **`offer_after_soft_cap_pushback`**、**room** は **`room_to_budget`**。**`soft_cap_early` は除外**して `offer` と `room` を比較。  
- **実行したコマンド（再現）**

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke

python tools\fa_offer_real_distribution_observer.py
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 11 --fa-rank-end 50 --roomy-team-count 16
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 0
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 40 --fa-rank-end 79 --roomy-team-count 0
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 11 --fa-rank-end 50 --roomy-team-count 0
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 1 --fa-rank-end 40 --roomy-team-count 16

python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav"
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" --population-mode mixed_mid_fa_roomy --fa-rank-start 11 --fa-rank-end 50 --roomy-team-count 0

python tools\fa_offer_real_distribution_observer.py --seasons 1 --seed 42
python tools\fa_offer_real_distribution_observer.py --seasons 1 --seed 42 --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 0
```

- **比較軸**: **既定モード** vs **mixed（FA ランク帯を変える）** vs **`roomy-team-count` を変える** vs **quicksave** vs **`--seasons 1`**（ワールド進行後）。

---

## 3. 各モード／条件の観測結果

**凡例**: `pre≤room` = `soft_cap_early` でない行のうち **`offer_after_soft_cap_pushback ≤ room_to_budget`** の件数。`room 値種数` = `room_to_budget` のユニーク個数。

| ケース ID | 条件（要約） | 総ペア n | final==buffer | 0<final<buffer | final>buffer | pre≤room | room 値種数 |
|-----------|----------------|----------|----------------|----------------|--------------|-----------|-------------|
| A | 既定（quick, top40×全48） | 1920 | 0 | 0 | 1920 | 0 | 1 |
| B | mixed 11–50, roomy 16 | 640 | 0 | 0 | 640 | 0 | 1 |
| C | mixed 25–64, roomy 0（全チーム） | 1920 | 0 | 0 | 1920 | 0 | 1 |
| D | mixed 25–64, roomy 16 | 640 | 0 | 0 | 640 | 0 | 1 |
| E | mixed 11–50, roomy 0 | 1920 | 0 | 0 | 1920 | 0 | 1 |
| F | mixed 40–79, roomy 0（下位帯寄り、ペア数はプール長依存で 1824） | 1824 | 0 | 0 | 1824 | 0 | 1 |
| G | mixed 1–40（上位帯）, roomy 16 | 640 | 0 | 0 | 640 | 0 | 1 |
| H | quicksave 既定 | 1920 | 0 | 0 | 1920 | 0 | 1 |
| I | quicksave mixed 25–64, roomy 16 | 640 | 0 | 0 | 640 | 0 | 1 |
| J | quicksave mixed 11–50, roomy 0 | 1920 | 0 | 0 | 1920 | 0 | 1 |
| K | quick, **seasons=1**, mixed 25–64, roomy 0 | 1920 | 0 | 0 | 1920 | 0 | 1 |
| L | quick, **seasons=1**, 既定 | 1920 | 0 | 0 | 1920 | 0 | 1 |

**observer の標準出力**でも、いずれも **`final_offer > buffer` が 100%**（内側帯・`final==buffer` は 0）で、**既定と同型**。

---

## 4. 今回の観測から分かること

1. **`offer ≫ room` の緩み（クリップ前）**  
   **今回試した population の摺り足しでは緩まない。** 全ケースで **`pre≤room = 0`**（`soft_cap_early` 除外後も **`offer_after_soft_cap_pushback > room_to_budget` が全行**）。gap メモの **「1920/1920 で pre>room」** と **同型**が続いた。

2. **中額 FA 帯（ランクを下げる）**  
   **総ペア数や FA 年俸の帯は変わる**が、**`final` の三区分（==buffer / 内側 / >buffer）と `pre≤room` は改善しなかった**。

3. **`roomy-team-count`（給与余力上位チームに限定）**  
   **チーム集合とリーグ内訳は変わる**（例: quick 世界で roomy 16 は **D3 のみ**など）が、**`room_to_budget` のユニーク値は 1 のまま**（本観測では **30,000,000 固定**）。**内側帯は出ない**。

4. **quicksave／`--seasons 1`**  
   **別 save・1 シーズン後**でも **指標は上表どおり変わらず**、**比較装置としての十分条件は未達**。

5. **総合**  
   **population mode は「母集団を変えるノブ」として有効**だが、**今回のパラメータ空間だけでは clip／λ を分離する行列はまだ得られていない**。**第一候補は「手続きの標準化」には使えるが、「装置完成」ではない**。

---

## 5. 推奨する第一候補の行列条件

**固定する第一候補（手続き）**（※**内側帯は未達**だが、設計メモの **A+B** に最も近い **再現可能な1本**）:

```text
python tools\fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
```

- **理由**: **中額寄り FA 帯（25–64 位）**と **給与余力上位 16 チーム**を**同時に**指定でき、**640 ペア**でログが扱いやすい。**quicksave でも同コマンドを再掛け**できる。  
- **他条件を第一にしない理由**  
  - **既定／全チーム mid 帯**（例: 25–64, roomy 0）は **比較対象としては必須**だが、「標準 B」としては **ペア数が大きく** A+B の**意図（広いチームを必ず混ぜる）**が弱い。  
  - **roomy 16 + 上位 FA 1–40**（ケース G）は **設計上の「中額混ぜ」から外れる**。  
  - **40–79** はプール長により **n が 1920 未満**になり、**横並び比較がやや遠い**。

---

## 6. 今回はまだやらないこと

- **observer の追加改修**（本メモは観測のみ）  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`tools/fa_offer_real_distribution_observer.py` に、複数 save パスを順に観測する最小オプション**（例: **`--save-list path1 path2 ...`** または **1 行1パスのファイルを受け取る `--save-batch`**）。

- **なぜその1手が今もっとも妥当か**  
  今回の **rank／roomy／seasons=1／手元 quicksave** の範囲では **`room` 一意・`pre≤room` ゼロ**が続き、**偏りは「単一ワールド形状」側に残っている**可能性が高い。**母集団ノブだけでは飽和が解けなかった**ため、**次はデータ源（複数 save）を増やす機構**が、設計メモの **「別 save／シーズン後」** に直結する **最小の次コミット**になる。

- **何はまだ残るか**  
  **内側帯が出た後の λ 比較再開**、**clip 別式 A/B**、**D1/D2/D3 別行列**、**診断出力への pre≤room 要約の常設化**（任意）は、**複数 save でも飽和が続くかを見てから**決裁する。

---

## 改訂履歴

- 2026-04-08: 初版（population mode 条件の playcheck）。
