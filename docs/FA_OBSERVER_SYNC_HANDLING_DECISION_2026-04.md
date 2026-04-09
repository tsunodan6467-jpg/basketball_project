# FA：`fa_offer_real_distribution_observer` における payroll_budget 同期の扱い（比較用観測の決裁）

**作成日**: 2026-04-08  
**文書の性質**: **意思決定メモ（コード変更なし）**。原因整理: `docs/FA_ROOM_UNIQUE_ONE_CAUSE_NOTE_2026-04.md`。同期前後の数値: `tools/fa_offer_real_distribution_observer.py` の `sync_observation`。gap／行列: `docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md`。実装参照: `basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll`。

---

## 1. 文書の目的

比較用観測で **`_sync_payroll_budget_with_roster_payroll` を今後どう扱うか**（本番同様維持／同期前主軸／観測専用スキップ）を整理し、**第一候補**と**1行結論**を固定する。次チャット・次実装の入力とする。

---

## 2. 本番同様に同期を維持する案

| 長所 | 短所 |
|------|------|
| **本番寄せ**: オフ FA 直前に近い `payroll_budget` と `room` の入力になる。 | **観測装置として**、同期後 **`gap`（room 相当）が `buffer` に収斂**しやすく、`sync_observation` でも **sync1 以降 `gap_unique=1`・`gap_min=max=buffer`** が続きやすい。 |
| **再現性**: 手順が単純で、save 間の差分解釈が揃う。 | **`room_unique=1`・`pre_le_room=0`・`final>buffer` 全面化**が崩れにくく、**clip／λ の差分が行列上で見えにくい**（これまでの playcheck と整合）。 |
| **実ゲーム挙動との一致**: 本番が同期後に FA 計算するなら、因果の語り口が一致する。 | **比較実験**では「式や λ の良し悪し」と「同期による入力単一化」が**分離しにくい**。 |

**観測が示したこと**: `sync_observation` で **before は gap 0 一色寄り**、**sync1 で gap が 30M 一色**になり、**sync2 は sync1 とほぼ同型**の例が出ている。**同期後行列は clip 評価用スクリーンとして偏りやすい**。

---

## 3. 観測用に同期前を主比較軸にする案

| 長所 | 短所 |
|------|------|
| **同期前の `payroll_budget`／ロスター給与／`gap` のばらつき**を主に読める（既に `sync_observation` の `before` 行がある）。 | **本番の最終 offer 経路**は同期後を前提とするため、**「バグの有無」ではなく「入力構造の分析」**に近い読みになる。 |
| **clip 式以前の入力差**（なぜ行列が飽和するか）を評価しやすい。 | ドキュメント・レポートで **「before 主軸／sync 後は本番整合用」** とラベルを**明示しないと誤読**されうる。 |
| **`_sync_payroll_budget_with_roster_payroll` や buffer 定数をいま変えず**、観測軸だけ増やせる。 | |

---

## 4. 観測用に同期スキップを検討する案

| 長所 | 短所 |
|------|------|
| **同期をかけない**ことで、`room`／`gap` の**より自然な分布**が行列に載る**可能性**があり、**clip／λ 比較装置**として改善しうる。 | **本番寄せが崩れる**。観測結果を**本番挙動の予測に直結**させにくい。 |
| | **`--skip-sync` 等の専用フラグ**と、**既定（同期あり）との二系統運用**の説明・テストが要る。 |
| | **before 時点で既に gap が 0 一色**の save もあり（`sync_observation`）、**スキップだけでは必ずしも多様化しない**。この段階で**主路線にするには早い**。 |

---

## 5. 推奨判断

**第一候補: いきなり同期スキップモードを主路線にせず、「比較用の第一読み取り軸は同期前（`before`）とし、本番同様の同期後（sync1／sync2 後の行列・`summary:`）は併記・補助軸として維持する」。**

- **理由**  
  - **sync_observation** で **同期が `gap` を buffer に揃える仮説**が強く裏づけられた。**比較で見たい「入力のばらつき」は before 側に残る情報が多い**可能性がある。  
  - **本番整合の同期後行列**は引き続き **「実装が効いている世界での挙動」**として必要。  
  - **同期スキップ**は設計・説明コストが大きく、**before 主軸で足りないと判断してから**入れる方が安全。  

- **他案を今は主路線にしない理由**  
  - **同期のみ維持**: 既に示されたとおり **比較装置として偏り**が残る。  
  - **同期スキップ**: **本番との対応関係が弱まり**、**効果も save 依存で不確実**。

---

## 6. 決裁用の1行結論

**比較用観測の第一読み取り軸は `sync_observation` の `before`（同期前）とし、本番同様の同期後（現行どおり2回同期したうえでの行列・`summary:`）は併記の補助軸として維持する；観測専用の同期スキップは、before 主軸で不足が確認されるまで主路線にしない。**

---

## 7. 今回はまだやらないこと

- **`_sync_payroll_budget_with_roster_payroll` の改造**  
- **`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` の変更**  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**  
- **観測専用の同期スキップ実装**（本決裁の **Go 後・別決裁**で検討）

---

## 8. 次に実装で触るべき対象（1つだけ）

**`tools/fa_offer_real_distribution_observer.py` に、出力上で「第一読み取り軸 = before（同期前）／補助 = 同期後行列」を一文または短いラベルで明示する（例: `sync_observation` ブロック直後の1行注記、または `before` 行の接頭辞）。**

- **なぜその1手が今もっとも妥当か**  
  本決裁は **手順の解釈**を変えるもので、**コードの意味を変えない**。誤って「同期後だけを見て clip を判断する」を防ぐコストが最小。  
- **何はまだ残るか**  
  **任意**: **同期前状態だけで `_run_matrix` を回すオプション**（重い・別決裁）、**同期スキップフラグ**、**本メモの追随改訂**（before 主軸で十分か検証後）。

---

## 実行コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

---

## 改訂履歴

- 2026-04-08: 初版（observer 同期の比較用扱いの決裁）。
