# FA：`--save-list` 複数 save 観測メモ（save 間差と比較装置候補）

**作成日**: 2026-04-08  
**文書の性質**: **観測メモ（コード変更なし）**。population / 単一 save playcheck: `docs/FA_OBSERVER_MATRIX_MODE_PLAYCHECK_2026-04.md`。行列設計: `docs/FA_OBSERVER_MATRIX_REDESIGN_PLAN_2026-04.md`。gap: `docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md`。実装参照: `tools/fa_offer_real_distribution_observer.py`（本メモでは未改修）。

---

## 1. 文書の目的

**`--save-list`** で複数 `.sav` を順に観測し、**save ごとに** `room_to_budget` の多様性、**クリップ前**の **`offer_after_soft_cap_pushback ≤ room_to_budget`（以下 `pre≤room`）**、**`final` と buffer の三帯**がどう違うかを整理する。  
**次に clip／λ 比較装置として使う save／条件の第一候補**と、**比較実験に進めるか／観測を続けるか**を1本にまとめる。

---

## 2. 観測条件

- **ルート**: `c:\Users\tsuno\Desktop\basketball_project`  
- **save ディレクトリ**: `C:\Users\tsuno\.basketball_sim\saves\` を **`*.sav` で glob** し、次の **5 ファイル**を対象（ファイル名は環境のコードページで表示が化ける場合あり）。  
  - **`quicksave.sav`**  
  - **`0330確認.sav`**（glob 上は `0330` 始まりの `.sav`）  
  - **`kakunin2.sav`**  
  - **`kakunin3.sav`**  
  - **`確認１.sav`**（glob 上は `確認` を含む1件）  
- **集計**: observer と同一手順（`_load_teams_fas_from_save` → `_sync_payroll_budget_with_roster_payroll` ×2 → FA／チーム抽出 → `_run_matrix`）。**`pre≤room`** は **`soft_cap_early` が False** の行のみ、`diag` の **`offer_after_soft_cap_pushback`** と **`room_to_budget`** を比較。buffer は **`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` = 30,000,000**。  
- **コマンド（再現・既定・複数 save）**

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke

python tools\fa_offer_real_distribution_observer.py --save-list `
  "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin2.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin3.sav"
```

（日本語ファイル名はエクスプローラでパスをコピーするか、上記と同じ **`saves` で glob** して列挙する。）

- **コマンド（再現・mixed・複数 save）**

```powershell
python tools\fa_offer_real_distribution_observer.py --save-list `
  "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin2.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin3.sav" `
  --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
```

- **本メモの数表**は、上記と同じロジックを **Python で一括実行**して取得（**リポジトリにスクリプトは残していない**）。

---

## 3. save ごとの観測結果

### 3.1 既定モード（top 40 FA × 全チーム、1920 ペア）

| save（短名） | 総ペア | final==buffer | 0<final<buffer | final>buffer | pre≤room | room ユニーク数 | メモ |
|--------------|--------|----------------|----------------|--------------|----------|-----------------|------|
| 0330確認 | 1920 | 0 | 0 | 1920 | 0 | 1 | D1/D2/D3 各 640。S6 経路。 |
| quicksave | 1920 | 0 | 0 | 1920 | 0 | 1 | 同上。 |
| kakunin2 | 1920 | 0 | 0 | **0** | 0 | **0** | **全行 `soft_cap_early`、final=0**。payroll clip 評価対象外。 |
| kakunin3 | 1920 | 0 | 0 | **0** | 0 | **0** | **同上**（全行 soft cap 早期）。 |
| 確認１ | 1920 | 0 | 0 | **0** | 0 | **0** | **同上**。 |

### 3.2 mixed（`mixed_mid_fa_roomy`、ranks 25–64、roomy 16 → 640 ペア）

| save（短名） | 総ペア | final==buffer | 0<final<buffer | final>buffer | pre≤room | room ユニーク数 | メモ |
|--------------|--------|----------------|----------------|--------------|----------|-----------------|------|
| 0330確認 | 640 | 0 | 0 | 640 | 0 | 1 | D2/D3 偏重（例: D2 80 / D3 560）。 |
| quicksave | 640 | 0 | 0 | 640 | 0 | 1 | D1/D2/D3 混在（例: D1 40 / D2 120 / D3 480）。 |
| kakunin2 | 640 | 0 | 0 | **0** | 0 | **0** | **全行 soft_cap_early**。 |
| kakunin3 | 640 | 0 | 0 | **0** | 0 | **0** | **同上**。 |
| 確認１ | 640 | 0 | 0 | **0** | 0 | **0** | **同上**。 |

**まとめ**: **S6 相当で final>buffer が出るのは `quicksave` と `0330確認` のみ**。その2本は **`pre≤room` は 0、`room` はユニーク 1（30M）、内側帯は 0** で、**単一 save playcheck と同型**。**kakunin2／kakunin3／確認１**は **行列全体が soft cap 早期**のため、**今回の payroll_budget clip 比較装置には不向き**。

---

## 4. 今回の観測から分かること

1. **room の多様性**  
   **手元 5 save の範囲では、`room_to_budget` のユニーク数が 1 を超えた save は無かった**（S6 が動いている save でも **30M 固定パターン**）。

2. **`pre≤room`**  
   **いずれの save・いずれの条件でも 0**（`soft_cap_early` 除外後も **クリップ前 offer は常に room 超え**）。

3. **`0 < final < buffer`**  
   **全ケース 0**。save を増やしても **内側帯は出現しなかった**。

4. **save 差分 vs mixed 差分**  
   **save による最大の差は「soft cap 早期で全滅するか否か」**。mixed は **チーム構成と FA 帯**を変えるが、**`quicksave`／`0330確認` では飽和構造は変わらない**。

5. **比較装置として**  
   **clip／λ を見るには「soft_cap_early が主でない save」に限定する必要がある**。その意味で **第一グループは `quicksave` と `0330確認` だけ**だが、**数値上はまだ「装置完成」には至っていない**。

---

## 5. 推奨する第一候補の save／条件

**第一候補（具体コマンド）**

```text
python tools\fa_offer_real_distribution_observer.py --save "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
```

**バッチで他 save と並べる場合**は **`--save-list`** に **`quicksave.sav` を必ず含め**、比較対象は **同じ mixed 引数**で揃える。

- **理由**  
  - **ASCII パスで再現しやすい**。  
  - **S6 経路が生き、final>buffer が観測できる**（kakunin 系・確認１は除外）。  
  - 設計メモの **A+B（中額 FA 帯 + roomy 16）** に合わせ、**640 ペア**で扱いやすい。  
- **`0330確認.sav` を第一にしない理由**  
  - 本観測では **`quicksave` と同型**（1920／640 いずれも **>buffer 一色、pre≤room=0、room 一意**）。**差が付かない**ため、**標準アンカーはパスが単純な `quicksave`** に寄せる。  
- **kakunin2／kakunin3／確認１を第一にしない理由**  
  - **全セル soft cap 早期**で、**今回の clip 比較の主題から外れる**。

---

## 6. 今回はまだやらないこと

- **observer の追加改修**（本メモは観測のみ）  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`tools/fa_offer_real_distribution_observer.py` に、各 save ブロック（または単体実行）の集計の直前に、1行の「行列サマリ」を出す最小追加**（例: **`soft_cap_early` 件数・割合、`room_to_budget` ユニーク数、`pre≤room` 件数**）。

- **なぜその1手が今もっとも妥当か**  
  **`--save-list` で save が増えると、ログだけでは「全行 soft_cap の save」を見落としやすい**。今回、**その種の save が 5 本中 3 本**あった。**比較不能な行列を先頭1行で弁別**できれば、**clip／λ 用の save 選別コストが下がり**、**追加 save を増やす観測ループ**と相性が良い。

- **何はまだ残るか**  
  **第一候補条件でも内側帯は未出のため、λ 比較の本格再開**、**意図的に roster／予算が薄い save の追加収集**、**clip 別式の A/B** は、**サマリ出力後も**別決裁で進める。

---

## 改訂履歴

- 2026-04-08: 初版（`--save-list` 相当の複数 save 観測）。
