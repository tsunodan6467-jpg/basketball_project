# オフ後 `payroll_budget` 再設定式の扱い（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。原因・式の正本: `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`。時系列: `docs/PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md`。保存経路: `docs/PAYROLL_BUDGET_PERSISTENCE_CAUSE_NOTE_2026-04.md`。before gap: `docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`。観測軸: `docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`。実装: `basketball_sim/models/offseason.py` の `_process_team_finances`。

---

## 1. 目的

- **なぜ今決裁が必要か**  
  FA clip／room 観測では **`payroll_budget` と `roster_payroll`（実契約合計）** が材料になるが、オフ後は **`payroll_budget` が経営指標式だけで再設定**され、**高額ロスターと数値が乖離しうる**ことが確定している。**式をすぐ変える前に**、観測・検証で**どう読むか**を固定しないと、clip／λ の議論と**入力の解釈**が混線する。

- **FA 観測の前段として**  
  **入力側 `payroll_budget` の意味**（ゲーム内の「目安」フィールド vs ロスター実態）を決裁で切り分け、**既決の観測軸**（`docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md` の **before 主軸**）と整合させる。

---

## 2. 確定事実（再掲・既決を濁さない）

以下は **本件では動かさない前提**（詳細は各正本 doc）。

| 事実 | 整理 |
|------|------|
| **実 save の `payroll_budget=24,018,800`** | **`_process_team_finances` の式と厳密一致**（属性は `user_team_snapshot` 等で検算可能）。 |
| **save/load** | **`payroll_budget` を壊していない**（round-trip 等で確認済み）。 |
| **`money`** | **before `gap=0` の主因ではない**（`gap` 定義に `money` は入らない）。 |
| **before で gap が開きにくい主因** | **オフ後再設定式が `roster_payroll` を入力に含まない**ため、**`payroll_budget << roster_payroll`** になり **`max(0, budget − roster)=0`** になりやすい（`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md` と整合）。 |
| **観測の読み** | **主軸は `sync_observation` の `before`**、**同期後は補助軸**（既決）。 |
| **その他の既決** | user team の **インシーズン CPU FA 除外**、**CLI 契約解除と GUI の同ルール接続**は本メモの対象外として**維持**（`docs/INSEASON_CPU_FA_USER_TEAM_EXCLUSION_DECISION_2026-04.md` 等）。 |

---

## 3. 今回の決裁（1案のみ）

**現時点では、オフ後 `payroll_budget` 再設定式は変更しない。**

代わりに、次の**解釈上の前提**を正とする。

1. **現行式の出力**は、コード上 **「来季人件費目安」としての経営指標**（`league_level`・`market_size`・`popularity`・`sponsor_power`・`fan_base` の関数）であり、**ロスター契約総額の写像ではない**。
2. **FA 観測・検証**では、**「`team.payroll_budget` に保存されている値（現行式の結果）」**と **「`roster_payroll` が示す契約実態」**を**同一視しない**。**差（実質的なショート／クリップの土台）**を読むときは、**両方を併記したうえで** before 主軸の `gap` 等を解釈する。
3. **式本体の変更**（roster 連動の導入、係数・`base_budget` の全面見直し等）は**別決裁**とし、**ゲームデザイン上の必要性が明示された段階**で扱う。**本決裁は式改修の許可ではない**。

**要約**: **今すぐ式をいじる決裁ではない**。**まず観測解釈を固定する**。将来必要なら式変更は分離して決める。

---

## 4. 非目的（今回やらないこと）

- **clip 式の本格改修**
- **λ（`_PAYROLL_BUDGET_CLIP_LAMBDA`）／buffer の再調整**
- **D1/D2/D3 横断の経済・予算の再設計**
- **7 人ルールの変更**
- **本メモに基づくコード変更**（`offseason.py`・observer・`free_agency.py` 等の実装差分は出さない）

---

## 5. 次に続く実務（1つだけ）

**observer 出力および関連 `docs` 上で、「現行式の `payroll_budget`」と「ロスター給与実態（`roster_payroll`）」をどう併記・ラベルして読むかを、軽く一段だけ揃える**（例: `reading_guide` 近傍の一文、`FA_BEFORE_GAP_ZERO` 系との相互参照の1行追加など）。

- **今回の決裁の直後の作業**としては、**ドキュメント上の読み方の整合**から入り、**必要になったら**最小の表示・文言差分に進む。**本メモ単体ではコード変更しない**。

---

## 抽出・参照用

- 式の詳細: `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`  
- 引き継ぎ一覧: `docs/PROJECT_HANDOFF_MASTER_2026-04-08.md`。**オフ後再設定式を「変えるか／読むか」分けた扱いの正本は本ファイル**。

---

## 改訂履歴

- 2026-04-08: 初版（オフ後式は現状維持、観測解釈を分離する決裁）。
