# オフ後 `payroll_budget` 再設定式 — 変更要否の判断メモ

**作成日**: 2026-04-08  
**性質**: **判断メモ（コード変更なし）**。観測の読み方・式の正体: `docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`、`docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`。代表表: `docs/FA_BEFORE_GAP_REPRESENTATIVE_SAVE_TABLE_2026-04.md`。枠: `docs/FA_BEFORE_GAP_SCOPE_OVERVIEW_2026-04.md`。before gap: `docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`。

---

## 1. 目的

- **本メモの位置づけ**  
  **式の実装差し替えではなく**、ここまでの観測を踏まえて **「変更の必要性がどの程度高いか」** を **1 本に固定**し、次に **何を設計論点として切り出すか** を明確にする。

- **前段の決裁との関係**  
  `docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md` で **観測解釈**（before 主軸・budget と roster の別軸・式は即変更しない）を固定済み。**本メモはそれを否定しない**。そのうえで、**ゲームデザイン／検証効率の観点から「式の見直しが妥当になりうるか」** を **別レイヤー**で判断する。

---

## 2. 確定事実（観測・整理）

| 区分 | 内容 |
|------|------|
| **式の説明力** | 例として **`payroll_budget=24,018,800`** は **`_process_team_finances` の式と厳密一致**（`docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`）。 |
| **主因の切り分け** | **`money`** や **save/load** が before `gap=0` の主因ではない（既決・検証）。 |
| **本丸の構造** | オフ後式は **`roster_payroll` を入力に含まない**ため、**`payroll_budget << roster_payroll` → `gap=max(0,·)=0`** になりやすい（既決の整理）。 |
| **10 人 save** | **人数を薄めても** before で **`gap=0` 一色**になりうる（`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`）。 |
| **代表表＋ debug_boost** | **`user_team_snapshot` で observed **D3** と observed **D2**（`league_level` 3 と 2）の両断面**で、**`before`: `gap_unique=1`, `gap_min=gap_max=0`** が同型。**`summary`**: **`room_unique=1`**, **`pre_le_room=0`** も同型。**`final_offer > buffer` が行列全体で飽和しやすい**パターンが続く（`docs/FA_BEFORE_GAP_REPRESENTATIVE_SAVE_TABLE_2026-04.md`）。 |
| **未確定** | **`user_team_snapshot` で observed D1（`league_level=1`）** の行は **まだ表にない**。**全リーグで同一と証明済み**ではない。 |

---

## 3. 今回の判断（1 案）

**現時点では、オフ後 `payroll_budget` 再設定式について「変更の必要性は高い」と判断する（実装着手の合図ではない）。**

- **「変更不要」とはしない**（観測上のボトルネックが **複数断面で繰り返されている**ため）。
- **「いますぐコードを書き換える」**ともしない（**変更対象・`roster_payroll` との関係づけ**を先に狭く定義する）。
- **次段**で、**式を roster 実態とどう関係づけるか**に絞った **短い設計メモ**へ進む。

---

## 4. この判断の理由

- **D3 user だけの偶発**では説明しにくい。**observed D2（level=2）でも** before／summary が **同型**に潰れる。
- **before 主軸**で見た **room／gap の欠如**は、**単発の save 品質**より **入力構造（式が roster を見ない）** と **読みやすく整合**する。
- 一方、**observed D1 は未取得**のため、**「全リーグで完全に同じ結論まで言い切った」**とは **書かない**。

---

## 5. 非目的

- **本メモをもって式・clip・λ・buffer の実装変更を行うこと**（コード変更は別タスク）。
- **observed D1 未取得を**「式変更の絶対禁止条件」**にすること**（必須ゲートにはしない）。
- **代表表・observer の全面改訂**。

---

## 6. 次に続く実務（1つだけ）

**「オフ後 `payroll_budget` 再設定式を、`roster_payroll`（契約実態）とどう関係づけるか」** を論点限定した **短い設計メモを `docs/` に 1 本**作成する（候補: 床／上限制／別フィールド／観測専用との分離などを**列挙せず枠だけ**決める）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_CHANGE_NEED_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（変更要否の判断・次は設計メモ）。
