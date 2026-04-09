# FA：`before` 主軸での gap／room の潰れ具合（整理メモ）

**作成日**: 2026-04-08  
**性質**: **整理メモ（コード変更なし）**。観測の読み方の正本: `docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`、`docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`。before gap の原因整理: `docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`。式: `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`。出力: `tools/fa_offer_real_distribution_observer.py`（`sync_observation` の `before`、行列の `summary:`）。

---

## 1. 目的

- **before 主軸で何を判断したいか**  
  **同期前**の全チーム（または対象 save）について、**`gap`／`gap_unique` がどの程度「潰れているか」**（0 一色に近いか、幅があるか）を、**リーグ段階（D1／D2／D3）と save 種別**の軸で**軽く並べる**ための**一枚の土台**を置く。行列側の **`room_unique`／`pre_le_room`** は **同期後入力**に依存するため、**補助**として参照する（下 §2）。

- **本メモの位置づけ**  
  **オフ後 `payroll_budget` 式の変更決裁ではない**。式変更が**検討に値する範囲感**（どの断面で構造的に潰れているか）を**次の判断の前段**で見える化するだけである。

---

## 2. 読み方（固定済み）

| 用語 | 読み |
|------|------|
| **`payroll_budget`** | **現行式**（オフ後は `_process_team_finances`）が `Team` に書いた**経営目安フィールド**。**ロスター合計の写像ではない**（`docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`）。 |
| **`roster_payroll`** | **契約実態**（選手 `salary` 合算、observer 定義）。 |
| **`gap`（before 統計）** | 観測指標 **`max(0, payroll_budget − roster_payroll)`** のチーム集合から取った **min／max／unique**（`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`）。 |
| **主軸** | **`sync_observation` の `before`**（同期前）。比較観測の第一読み取り軸（`docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`）。 |
| **補助** | **`sync1`／`sync2`** および **行列後の `summary:`**（`room_unique`／`pre_le_room` 等）。**本番整合・clip 入力後**の世界の確認用。 |
| **`money`** | **before gap の主因ではない**（既決）。 |

---

## 3. 現時点で既に言えること（確定に近い観測・整理）

- **10 人ロスター save を複数作っても**、`before` で **`gap` が 0 一色**（`gap_unique=1`、`gap_min=gap_max=0`）になりうる（`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`、ユーザー報告ベースの観測）。
- **post-off 系 save** では、**`payroll_budget` が式どおり低く**出り、**`roster_payroll` と大きく乖離**し、**before でも `gap=0`** と整合する例がある（例: `payroll_budget=24,018,800` は式と厳密一致、`docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`）。
- よって、**「ごく一部の変な save だけ」**というより、**現行式と `gap` 定義の組合せとして**、**before が潰れやすい条件が繰り返し説明できる**段階にある。**ただし**、これを **D1／D2／D3 横断で表形式に揃え切った状態ではない**（下 §4）。

---

## 4. 次に見るべき最小単位

- **リーグ**: **D1／D2／D3**（`league_level`）。式の **`base_budget` が段階別**のため、**同じ「潰れ」でも水準の見え方が変わる**。
- **save 種別**（例）  
  - **新規開始直後系**（⑦未到達で `payroll_budget=120M` 残りやすい経路、`docs/PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md`）。  
  - **post-off 系**（⑦通過後、式による再設定が載った save）。
- **save 数**は**少数でよい**。代表点を並べるだけの段階。
- **「どこまで潰れていれば式変更検討に進むか」**の閾値は **未決裁**（本メモでは固定しない）。

---

## 5. 今回の暫定整理

- **確認できている範囲**: **post-off 条件付き**では、**before の `gap`／room が構造的に潰れうる**（式が `roster_payroll` を見ず、かつ `max(0,·)` であることと整合）。
- **未整理の範囲**: **D 横断**で同型の表にした**十分な一覧**は、**まだこのリポジトリの docs 上では揃っていない**。
- **次の段階**: **リーグ横断でどの程度普遍的か**を**軽く揃えたうえで**、**式変更要否**は別途決裁・判断へ進む（本メモはその**前段**）。

---

## 6. 非目的

- **オフ後 `payroll_budget` 式の変更**（別決裁）。
- **clip／λ／buffer** の変更。
- **`tools/fa_offer_real_distribution_observer.py` のコード変更**。
- **新規の大規模調査の開始**（本メモは整理のみ）。

---

## 7. 次に続く実務（1つだけ）

**before 主軸で、D1／D2／D3 の代表 save を少数選び、`fa_offer_real_distribution_observer.py` を当てたときの `sync_observation` の `before`（`gap_min`／`gap_max`／`gap_unique`）と、行列の `summary:`（`room_unique`／`pre_le_room`）だけを表形式で一覧化する**（手元メモまたは `docs` の短い playcheck 1 本。コード変更は不要）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BEFORE_GAP_SCOPE_OVERVIEW_2026-04.md -Pattern "目的|読み方|現時点で既に言えること|暫定整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（before 主軸の gap／room 潰れの整理枠）。
