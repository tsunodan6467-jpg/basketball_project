# `room_to_budget` と `offer_after_soft_cap_pushback` — 分布・大小の最小観測メモ

**作成日**: 2026-04-08  
**性質**: **観測ポイントの固定（コード変更なし）**。読み順の前段: `docs/FA_PRE_LE_ROOM_CAUSE_READ_ORDER_NOTE_2026-04.md`。定義の正本: `docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`。文脈: `docs/FA_OFFER_SIDE_OBSERVATION_NOTE_2026-04.md`。

---

## 1. 目的

- **`room_to_budget`** と **`offer_after_soft_cap_pushback`** を、**observer / diagnostic 上でどう読めばよいか**を **分布・大小関係の観測単位**まで **最小限で固定**する。
- **本メモは観測の置き場**であり、**原因断定・改修方針の確定はしない**。

---

## 2. 観測対象

| 対象 | 読むこと |
|------|----------|
| **`room_to_budget`** | **予算 clip 呼び出しと同時に diagnostic に入る room**（`FA_PRE_LE_ROOM_MAPPING_NOTE` のとおり **payroll clip より前の offer 段とは別キー**だが **`pre_le_room` 集計ではここと比較する**）。 |
| **`offer_after_soft_cap_pushback`** | **soft cap 押し戻し適用直後**の offer（**同 clip より前**のスナップショット）。 |
| **両者の大小関係** | **`soft_cap_early` が偽**かつ **両キー non-None** の行だけが **`pre_le_room` の母集団**。**`offer <= room` の件数**が **`pre_le_room`**。 |
| **差分（任意だが推奨）** | **`offer_after_soft_cap_pushback - room_to_budget`**。**正なら room 未満足**、**幅の分布**で **tail か全体か**を切る材料にする。 |

**実装の出所**: 行列は `tools/fa_offer_real_distribution_observer.py` の **`_run_matrix`**（各行 **`diag`** に `_calculate_offer_diagnostic` 全キー）、**`summary:`** 行は **`_matrix_summary_line`**（**`room_unique`・`pre_le_room`**）。

---

## 3. `room_to_budget` の見方

- **分布**: **ユニーク数**は **`summary:` の `room_unique`**。**値のばらつき**は **ヒストグラム前の集計**や **サンプル行**（例: S6-tiny 例示で **`room_to_budget=`** が出る）から **目安**を取る。
- **最小値 / 最大値**: **行列全体**に対して **None 除外**で **min / max**（**手元スクリプト・1 回の grep 抽出**でも可。**確定事実としてコードに依存**）。
- **代表例**: **同じ `room_to_budget` を持つ (team, FA) を数件**、**`payroll_budget` / `payroll_before` と並べて**読む（**before 主軸との混同は `summary` 注記どおり避ける**）。
- **0 付近**: **`room_to_budget not None & <= TINY_MAX`** の行数（**`_aggregate` 出力**）と **`room_unique`** を **併読**し、**極端に低い room に張り付いていないか**を見る。

---

## 4. `offer_after_soft_cap_pushback` の見方

- **分布**: **既定の ASCII 出力では専用ヒストはない**。**各行 `diag["offer_after_soft_cap_pushback"]`** が **正本**（**分布を見るには抽出が必要**な場合がある — **次メモで既存十分か切る**）。
- **最小値 / 最大値**: **`soft_cap_early` 偽**に **絞ったうえで** **None 除外 min/max**。
- **代表例**: **`pre_le_room` 集計対象行**から **数件**、**`room_to_budget` と並べて**記録する。
- **高すぎか**: **pushback 後でも** **`int(offer) > int(room_to_budget)` が支配的**なら **`pre_le_room` が伸びにくい**。**`final_offer` や clip 後**は **この段階では広げない**。

---

## 5. 大小関係の見方

- **`offer_after_soft_cap_pushback <= room_to_budget` の件数**: **`summary:` の `pre_le_room`**（**`soft_cap_early` 真は除外**、**欠損 pair はカウントに入らない**）。
- **`offer_after_soft_cap_pushback > room_to_budget` の広がり**: **母集団**は **上と同じ条件の「比較可能 pair」**。**件数差**で **`pre_le_room` と整合**するか確認する。
- **差分の読み方**: **`offer - room`**。**小さい正の多数**＝ **わずかに超えている全体傾向**。**大きい正の少数**＝ **tail**。**どちらか**で **候補A/B/C**（前メモ）への **当たり**を付けるだけに留める（**断定しない**）。
- **極端値 vs 全体**: **差分の分位数**または **ヒスト**が取れれば理想。**取れなければ** **最大超過幅・件数比率**と **代表行**の **セット**で **暫定**する。

---

## 6. 今回の判断（1 案）

**次の最小観測では、まず `room_to_budget` の分布を押さえ、その後 `offer_after_soft_cap_pushback` と重ねて大小関係を読む。  
この段階では `final_offer` や clip 後挙動までは広げず、`pre_le_room=0` の直前段（**mapping メモの 2 キー比較**）に観測を絞る。**

- **手順の固定**（前メモと同じ）: **(1) `room_to_budget` → (2) `offer_after_soft_cap_pushback` → (3) 大小・差分**。

---

## 7. 非目的

- **コード変更**。
- **`final_offer` / `final_offer > buffer` まで同時に片付けること**。
- **Cell B の再比較**。
- **解決策・原因の断定**。

---

## 8. 次に続く実務（1つだけ）

**`room_to_budget` と `offer_after_soft_cap_pushback` を observer 上で見える形にする必要があるか、まず既存出力で足りるかを確認する短いメモを作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_ROOM_TO_BUDGET_AND_PUSHBACK_OBSERVE_NOTE_2026-04.md -Pattern "目的|観測対象|room_to_budget の見方|offer_after_soft_cap_pushback の見方|大小関係の見方|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（2 キー・大小・差分の最小観測）。
