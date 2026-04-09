# observer 最小追加出力項目の決定（`room_to_budget` / `offer_after_soft_cap_pushback`）

**作成日**: 2026-04-08  
**性質**: **追加する行の決裁メモ（コード変更なし）**。十分性: `docs/FA_OBSERVER_OUTPUT_SUFFICIENCY_NOTE_2026-04.md`。観測手順: `docs/FA_ROOM_TO_BUDGET_AND_PUSHBACK_OBSERVE_NOTE_2026-04.md`。`pre_le_room` 定義: `docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`。実装先: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **`pre_le_room=0`** の切り分け（**候補A〜C**: room 小さめ / offer 大きめ / 相対・差分）を進めるうえで、**observer に最小限何を追加出力すればよいか**を **項目ベースで決める**。
- **実装・閾値の最終値は置かない**（**次段の実装指示書に委ねる**）。

---

## 2. 既存出力で足りるもの

| 出力 | 足りている範囲 |
|------|----------------|
| **`summary:`** | **`soft_cap_early` 比率**、**`room_unique`**、**`pre_le_room`**（**`offer <= room` の件数**の定義確認）。 |
| **`_aggregate`** | **`final_offer` 帯**（clip 後）、**`room_to_budget <= TINY_MAX`** 件数、**リーグレベル別件数**。 |
| **S6-tiny 代表行（最大 5）** | **`room_to_budget` 等の片鱗**（**母集団は狭い**）。 |

**読み順 (1)→(2)→(3)** のうち、**(1)(2) の「全体の形」**は **上だけでは弱い**（十分性メモどおり）。**差分の明示**も **ない**。

---

## 3. 追加出力が必要なもの

**以下 3 項目に限定する**（**代表行の大量追加は主軸にしない**）。

### 候補1 — `room_to_budget` の要約

- **`soft_cap_early` 偽**かつ **`room_to_budget` が non-None** の行（**必要なら `offer_after_soft_cap_pushback` も non-None** に **pre_le と同じ母集団**へ揃える）について、**min / max** と **少数分位**（例: **p50・p90** など **1〜2 本**。**本数は実装段で確定**）。

### 候補2 — `offer_after_soft_cap_pushback` の要約

- **上と同じ母集団**で **min / max** と **少数分位**（同上）。

### 候補3 — 差分の件数要約

- **`diff = offer_after_soft_cap_pushback - room_to_budget`**（**整数**想定）について、**同一母集団**で:
  - **`diff <= 0`**（**`pre_le_room` と整合する帯**）
  - **`diff > 0`**
  - **`diff >> 0`**（**大きめ閾値超**。**閾値は実装段で決める**）

---

## 4. 今回の判断（1 案）

**次段の observer 追加出力は、(1) `room_to_budget` 要約、(2) `offer_after_soft_cap_pushback` 要約、(3) 両者差分の件数要約の 3 つに限定する。**

- **代表行を増やすのではなく要約を足す**。
- **分布と大小関係の全体感**が掴める **最小セット**にする。
- **4 項目目以降は広げない**。

---

## 5. 非目的

- **今回はコード変更しない**。
- **項目の大量追加**。
- **`final_offer` 飽和まで一気に広げる**。
- **`>> 0` の閾値の最終決定**（**実装前に別途でよい**）。

---

## 6. 次に続く実務（1つだけ）

**上記 3 項目だけを observer に足す最小差分の実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OBSERVER_MIN_OUTPUT_ADDITIONS_NOTE_2026-04.md -Pattern "目的|既存出力で足りるもの|追加出力が必要なもの|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（3 項目限定の決定メモ）。
