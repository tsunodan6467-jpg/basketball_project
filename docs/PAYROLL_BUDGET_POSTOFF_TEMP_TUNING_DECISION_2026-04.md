# postfloor 観測（D2/D1）と `TEMP_POSTOFF_*` 再調整方針（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。実装の形: `docs/PAYROLL_BUDGET_POSTOFF_INLINE_FLOW_MEMO_2026-04.md`、`floor_expr` 記号: `docs/PAYROLL_BUDGET_POSTOFF_FLOOR_EXPR_CANDIDATES_2026-04.md`。変更要否の前段: `docs/PAYROLL_BUDGET_POSTOFF_CHANGE_NEED_DECISION_2026-04.md`。代表表・読み方: `docs/FA_BEFORE_GAP_REPRESENTATIVE_SAVE_TABLE_2026-04.md`。

---

## 1. 目的

- **今回の postfloor 観測結果**（D2 / D1）を **docs に固定**し、**`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO` / `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`** の **再調整方針**を **1 本に決める**。
- **本メモはコード変更ではない**。**次の tuning の方向**を絞る **決裁**である（**最終数値の確定ではない**）。

---

## 2. 確定事実（今回の観測）

以下は **`debug_user_boost_d2_user_postfloor.sav`** と **`debug_user_boost_d1_user_postfloor.sav`** に基づく **観測の固定**である。

| 項目 | D2 save | D1 save |
|------|---------|---------|
| **`league_level`** | 2 | 1 |
| **`payroll_budget`** | 993,010,000 | 918,190,000 |
| **`roster_payroll`** | 990,010,000 | 915,190,000 |
| **`gap`**（当該観測での定義どおり） | 3,000,000 | 3,000,000 |
| **`before`** | `gap_unique=1`, `gap_min=3,000,000`, `gap_max=3,000,000` | 同左 |
| **`summary`** | `room_unique=1`, `pre_le_room=0` | 同左 |
| **`final_offer > buffer`** | 1920/1920 | 1920/1920 |

**読み取り（観測レベル）**

- **`α=1.0`, `β=3,000,000`** の実装下では、**before で `gap=0` 一色固定**は **解消**している（**両断面で `gap=3,000,000`**）。
- 一方、**`gap_unique=1`** および **`room_unique=1` / `pre_le_room=0`** は **従来どおり潰れたまま**。**`final_offer > buffer` の飽和**も **継続**。
- つまり **3M の gap** では、**観測分布はまだ「開いていない」**（**1 値に固定**の構造が残る）。

---

## 3. 今回の判断（1 案）

**現行の `TEMP_POSTOFF_*`（`α=1.0`, `β=3,000,000`）は、「roster 非参照だったオフ後 budget」に対する **最初の改善**としては **有効**だが、**before 主軸で見たい「潰れの解消」にはまだ弱い**。**

**次段の tuning では、次を採る。**

1. **`clip` / `λ` /（FA 経路の）`buffer` には触れない**（**別トラック維持**）。
2. **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER`（β 相当）を、第1の調整レバー**とし、**段階的に見直す**。
3. **`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`（α 相当）は、今回の次段ではすぐに主軸にしない**（**第2優先**。必要になった段階で別メモで切る）。

**観測上の狙い（次段）**

- **before の `gap` がどの程度まで広がると**、`gap_unique=1` や **`room_unique=1` / `pre_le_room=0`** が **崩れ始めるか**を **切り分ける**こと。**最終の目標値は本メモでは確定しない**。

---

## 4. この判断の理由

- **`α=1.0`** のとき **`floor_expr = roster_payroll + β`** となり、**`max(現行式, floor)` が floor 側**なら **`gap ≈ β`** になりやすい。**今回の `gap=3,000,000` は、観測上 `β` がそのまま表に出ている**と読める。
- よって **効き方を一段ずつ見る**には、**まず `BUFFER`（β）を動かす**のが **直感的で切り分けしやすい**。
- **`RATIO`（α）を先に大きく動かす**と、**ロスター規模差まで同時に強く効き**、**今回の観測軸との対応づけがやや鈍る**。
- **安全第一・最小差分**の流れに合わせ、**単一レバー優先**で進める。

---

## 5. 非目的

- **本メモによるコード変更**。
- **`clip` / `λ` / FA 側 `buffer` の変更**。
- **`RATIO` を主調整対象として `BUFFER` と同格で同時に振る**こと（**本決裁ではしない**）。
- **`TEMP_POSTOFF_*` の最終確定**。
- **D3 / D2 / D1 全断面の再取得を、本メモの必須条件とすること**（**あれば精度は上がるが、本メモの決裁条件とはしない**）。

---

## 6. 次に続く実務（1つだけ）

**`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER` だけ**を **段階的に引き上げる** **tuning 用の実装・観測指示書**を **`docs/` に 1 本**作成する（**例**: 現状 3M から、**いくつかの段階**で比較観測する。**具体段階の数値は指示書側で置き、本メモでは断定しない**）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_TEMP_TUNING_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（D2/D1 postfloor 観測の固定・BUFFER 優先の次段方針）。
