# S6 極小オファー：当面の扱いと buffer 増額の決裁メモ

**作成日**: 2026-04-06  
**文書の性質**: **意思決定メモ（コード変更なし）**。設計の土台: `docs/FA_S6_TINY_OFFER_POLICY_NOTE_2026-04.md`、観測: `docs/FA_CALCULATE_OFFER_CAUSE_PLAYCHECK_2026-04.md`、`docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAYCHECK_2026-04.md`。S1 決裁: `docs/FA_SOFT_CAP_POLICY_DECISION_MEMO_2026-04.md`。buffer 設計: `docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAN_2026-04.md`。合成再現: `tools/fa_offer_diagnostic_observer.py`。実装参照: `basketball_sim/systems/free_agency.py`（`room_to_budget`）、`basketball_sim/models/offseason.py`（`_sync_payroll_budget_with_roster_payroll`）。

---

## 1. 文書の目的

**S1** は FA 新規オファー芯 **完全不可**で固定済み。**S6** は `payroll_budget` 同期＋`MIN_SALARY_DEFAULT` buffer により **0 オファーを減らした**一方、**`room_to_budget` が小さいときは高額 FA でも final が 300,000 円程度に張り付く**ことが **合成行列で再現済み**（`tools/fa_offer_diagnostic_observer.py`）。  
本メモは、**S6 極小を当面仕様として許容するか**、**次の最小差分として buffer 増額に進むか**を **二択で決裁**し、次チャット・次コミットの **1行判断**に落とす。

---

## 2. 現状維持案

- **評価**: S6 極小は **`payroll_budget - payroll_before` が小さいときの `min(offer, room_to_budget)` の自然な帰結**であり、第2弾 buffer（`roster + MIN_SALARY_DEFAULT`）の **意図したサイズの直接結果**でもある（`FA_S6_TINY_OFFER_POLICY_NOTE` §2）。  
- **長所**: **実装変更ゼロ**。**CPU／手動とも同一 `_calculate_offer`** のまま対称性を崩さない。**S1 決裁**とも独立に説明できる。  
- **短所**: **高額 FA × 極小 final** はプレイ感・説明コストで **違和感が残る**。オフ手動は estimate／floor 側で見え方が救われうるため、**CPU とのギャップ**が目立つ局面は残りうる（buffer プレイチェック §4）。

---

## 3. buffer 増額案

- **内容**: `MIN_SALARY_DEFAULT`（300,000）**より大きい**固定余地を、**`basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll`** の `buffer`（または同等の名前付き定数）として引き上げる（`OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAN` の段階ノブ）。**`_calculate_offer` の式は増やさず**試せる可能性が高い。  
- **長所**: **局所変更**で `room_to_budget` の上限が上がり、**極小張り付きの「額」**を一気に緩めうる。**手動／CPU 対称**は維持しやすい。  
- **短所**: **経営ガイドライン・オーナーミッション**と「意図的にタイトな guideline」の物語が **どこまで許容か**の確認が要る。**実プレイ・CPU 分布が未計測のまま**上げると、**稀な合成エッジへの過大対応**や **意図しない補強余地の拡大**のリスクがある（設計メモ §4・buffer プレイチェック §5 と同趣旨）。

---

## 4. 推奨判断

- **第一候補: 当面は現状維持（S6 極小を仕様として許容）し、buffer 増額は即実装しない。**  
- **理由**: (1) 合成観測は **`tools/fa_offer_diagnostic_observer.py` で再現可能**だが、**実セーブ／CPU FA 通過後の頻度・影響はまだ数値化されていない**。(2) buffer 増は **経営ルール全体への波及**があり、**「どれだけ多い問題か」が無いままノブを回すとロールバックが重い**。(3) **S1 固定**の直後に **S6 だけを大きく動かす**と、プレイヤー体験の変化要因の切り分けが難しくなる。  
- **もう1段観測が必要か**: **必要**。合成行列は **挙動の説明と回帰の土台**まで。**実分布（または長期シミュ後のリーグ状態）**で **S6 極小が稀か／CPU 分布を歪めるか**を見てから、**buffer 増額を「次の最小差分」として採るか**を再判断するのが安全。  
- **buffer 増額の位置づけ**: **観測後に「効く」と判断した場合の、本体を触らない第一候補**として保留（設計メモ §4 終盤と整合）。

---

## 5. 決裁用の1行結論

**S6 極小オファーは当面許容し、buffer 増額は実セーブまたは CPU FA 分布の観測後に再判断する。**

---

## 6. 今回はまだやらないこと

- **`_calculate_offer` 本体の改造**（budget クリップ式の変更含む）  
- **`MIN_SALARY_DEFAULT` を超える buffer の増額実装**（本決裁は「当面据え置き」）  
- **`offseason_manual_fa_offer_and_years` の floor 条件・倍率変更**  
- **オフ手動FAの全面再設計**  
- **`_calculate_offer_diagnostic` のロジック変更**  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**実セーブのロード、または CPU FA／オフ進行後に得られる `Team` 集合を入力に、`soft_cap_early` が偽かつ `room_to_budget` が極小（例: 現行 buffer 程度〜数百万以下）のケースにおける `_calculate_offer_diagnostic`（または同等）の **件数・比率を集計する観測**を1本追加する**（`tools/` の拡張または別スクリプト、**本体ロジックは変更しない**）。合成行列は `tools/fa_offer_diagnostic_observer.py` で済んでいるため、**次は実データまたはシミュ済み状態**を対象にする。

- **なぜその1手が今もっとも妥当か**  
  決裁 §5 どおり **buffer は観測後に再判断**する。**実分布が無いまま buffer を上げる／上げないの議論が空転**するのを防ぎ、**「増やすならいくつ」**の根拠を後続コミットに残せる。  

- **何はまだ残るか**  
  **観測結果を踏まえた buffer 定数の更新**、**それでも不十分な場合の `_calculate_offer` 側下限ルール**、**オフ手動と CPU の説明整合**、**guideline とオーナー目標の長期一貫性**。

---

## 改訂履歴

- 2026-04-06: 初版（当面許容＋観測後 buffer 再判断の決裁）。
