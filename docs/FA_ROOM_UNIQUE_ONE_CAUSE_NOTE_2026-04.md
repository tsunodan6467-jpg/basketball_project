# FA：`room_unique=1` が観測で固定されやすい理由（同期・roomy・リーグ分布）

**作成日**: 2026-04-08  
**文書の性質**: **原因分析メモ（コード変更なし）**。観測の事実: `docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md`、`docs/FA_OBSERVER_MATRIX_MODE_PLAYCHECK_2026-04.md`、`docs/FA_OBSERVER_SAVE_LIST_PLAYCHECK_2026-04.md`。採取要件: `docs/FA_CLIP_COMPARE_SAVE_REQUIREMENTS_2026-04.md`。

---

## 1. 文書の目的

複数 save・population・`--seasons 1`・手動 var save まで観測しても **`room_unique=1`**・**`pre_le_room=0`**・**`final_offer > buffer` 全面化**が崩れにくい理由を、**payroll_budget 同期**・**roomy-team 選定**・**D3 偏重**の観点で整理する。  
**save 不足だけでは説明しきれない**、**observer に入る前の入力構造**側の仮説を、**観測済み**と**コードから読める仮説**に分けて書く。

---

## 2. `room_unique=1` が起きる構造仮説（要約）

**観測済み**: 多くの条件下で行列上の `room_to_budget` のユニーク数が **1**（典型値 **30,000,000**）。`docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md` 等。

**コードから読める仮説（主線）**:

1. `fa_offer_real_distribution_observer` は save 読込後 **`_sync_payroll_budget_with_roster_payroll(teams)` を2回**呼ぶ（本番オフに近い手順）。  
2. 同期は各チームで **`payroll_budget = max(既存, roster_payroll + buffer)`**（`buffer = _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER`）。実装: `basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll`。  
3. **`既存 payroll_budget` がしばしば `roster + buffer` 以下**だと、同期後は **`payroll_budget = roster_payroll + buffer`** に張り付く（床で一致）。  
4. 診断上の **`room_to_budget`** は `_calculate_offer_diagnostic` 内で **`max(0, payroll_budget - payroll_before)`**（`payroll_before` はロスター給与相当）。床が効いていれば **`room_to_budget = buffer` 定数**になりやすい。  
5. したがって **save や FA 帯を変えても**、**同期後に床が支配的な限り**、行列全体で **`room_to_budget` が単一値**に寄る。これは **clip 式以前の入力（予算同期の帰結）**として読める。

**断定でない部分**: 「全チームが必ず床に張り付く」ことは save により異なりうる。観測では **単一値が続いた**＝**手元データでは床支配が強い**という帰結。

---

## 3. 各要因の整理

### A. payroll_budget 同期

| 区分 | 内容 |
|------|------|
| **コード** | `team.payroll_budget = max(0, max(existing, roster_payroll + buffer))`（`buffer=30M`）。 |
| **なぜ room 固定化しやすいか（仮説）** | `existing <= roster+buffer` のとき **同期後 `payroll_budget - roster = buffer` ちょうど**。多チームが同条件だと **`room_to_budget` がすべて buffer** になり、**`room_unique=1`**。 |
| **2回呼ぶ意味** | 本番に寄せた手順。**同じ床ロジックが再適用**され、**床張り付きが安定**しやすい（観測上の再現性は上がる）。 |
| **観測済み** | 複数条件で **`room_unique=1` が継続**（各 playcheck）。 |

### B. roomy-team 選定

| 区分 | 内容 |
|------|------|
| **コード** | observer は **`payroll_budget - roster_payroll`**（実装では `_team_payroll_room`）でチームを並べ、上位 N を採る。 |
| **仮説** | 同期後 **ほぼ全チームで `payroll_budget - roster` が同じ（= buffer）** なら、**「大きい room 上位」はタイブレークに近く**、**チーム集合は変わっても `room_to_budget` の値の種類は増えない**。 |
| **観測との整合** | mixed + roomy 16 で **D3 偏重**など **リーグ構成は変わる**報告があっても **`room_unique=1` が続く**なら、**「選んだチームが違う」ことと「room の多様性」は別**と説明しやすい。 |
| **断定でない部分** | 一部チームだけ `existing` が大きく **`room` が buffer 超**なら `room_unique>1` になりうる。手元では起きにくかった、という位置づけ。 |

### C. D3 偏重 / リーグ差

| 区分 | 内容 |
|------|------|
| **観測済み** | roomy 絞りで **D3 100% や D2/D3 混在**など **リーグレベル構成は変わりうる**（matrix／save playcheck の記述）。 |
| **仮説** | **リーグ差（soft cap 等）は `soft_cap_early` や offer 形状に効く**一方、**`room_to_budget` は `payroll_budget - payroll_before` で決まり**、**同期床が一律ならリーグを混ぜても room のユニーク数は増えない**。 |
| **何が仮説か** | 「D3 だから room が単一」ではなく、**「同期後の予算—ロスター差がリーグ横断で同型」だから単一**、が主線。 |
| **観測との関係** | **リーグ分布の変化だけでは `room_unique` が解放されない**例が、上記と整合的。 |

---

## 4. 今回の原因整理から分かること

- **次のボトルネック**は、**save の本数不足だけではなく**、**同期後に `room_to_budget` が buffer に揃いやすい構造**にある可能性が高い（**観測 + コードの組合せ**）。  
- その場合、**λ を動かしても**行列入力の **`offer ≫ room` 型**が残りやすく、**比較装置としての改善は限定的**になりやすい（過去 gap 整理と同型の読み）。  
- **いきなり clip 式・同期式を変える前に**、**「同期前後で `payroll_budget` / roster / 合成 room がどう分布するか」**を1段観測するのが妥当（**仮説の検証**と **どこを変えるべきかの特定**）。  
- **ユーザー感覚の「observer 上で同期前後を見る」**は、この段階の **最もリスクの低い次手**として優先度が高い。

---

## 5. 今回はまだやらないこと

- **`_sync_payroll_budget_with_roster_payroll` の改造**  
- **`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` の変更**  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**

---

## 6. 次に実装で触るべき対象（1つだけ）

**`tools/fa_offer_real_distribution_observer.py` に、同期の直前／直後（または1回目／2回目のあいだ）で、各チームの `payroll_budget`・ロスター給与合計・その差分の分布（最低: ユニーク数・min／max）を出す軽い観測ブロックを1つ追加する。**

- **なぜその1手が今もっとも妥当か**  
  本メモの主線は **「床 `roster+buffer` で room が buffer に揃うか」**の検証。**コードを変えずに**、**実データで床支配の有無を確かめられる**。誤って clip や λ だけを先に動かすコストを避けられる。  
- **何はまだ残るか**  
  **床が確認されたあとの設計決裁**（同期条件の見直し・buffer 方針・観測専用フラグで同期をスキップするか等）、**`get_team_payroll` と診断の `payroll_before` の完全一致確認**、**採取要件メモに「同期を避けた比較用スナップショット」を書くか**の判断。

---

## 実行コマンド（確認用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

---

## 参照コード（読み取り用）

- `basketball_sim/models/offseason.py`: `_sync_payroll_budget_with_roster_payroll`（`max(existing, roster_payroll + buffer)`）。  
- `basketball_sim/systems/free_agency.py`: `_calculate_offer_diagnostic` → `room_to_budget` は `payroll_budget - payroll_before` 由来（`_clip_offer_to_payroll_budget`）。  
- `tools/fa_offer_real_distribution_observer.py`: 同期2回・`_team_payroll_room` による roomy 選定。

---

## 改訂履歴

- 2026-04-08: 初版（`room_unique=1` 固定の原因整理）。
