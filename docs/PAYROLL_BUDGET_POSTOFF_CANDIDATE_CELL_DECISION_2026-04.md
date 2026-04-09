# 仮採用候補セル: Cell B（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。根拠: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`。計画: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_PLAN_2026-04.md`。前段: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_DECISION_2026-04.md`。

---

## 1. 目的

- **4 セル（A〜D）観測**の後、**次段の仮採用候補を 1 つ**置き、**実 save 再作成・再観測**に進むかを **1 本に決める**。
- **本メモは最終 α/β の確定ではない**。

---

## 2. 確定事実（観測の要約）

- **A→B**（**α=1.05 固定、β 3M→10M**）で **user `gap` 増加**、**D2 の `room_unique` が 46→48**、**D2 の `pre_le_room` が 0→40** — **β 併用の効果が明示的に見えた**（`docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`）。
- **C / D**（**α=1.10**）は **gap・`pre_le_room` がさらに強く動く**。
- **全セル**で **`final_offer > buffer = 1920/1920`** は **不変** — **budget／room 側の改善と、最終 offer 分布はまだ別論点**。
- **読み取り**: **現段階では before／補助 matrix 側の改善**を **主な根拠**に **仮候補を置く**のが **自然**である。

---

## 3. 今回の判断（1 案）

**次段の仮採用候補は Cell B（α=1.05, β=10,000,000）とする。**

- **もう 1 段の軽い格子比較は増やさない**。**まずこの候補で実 save 再作成と再観測**に進む。
- **位置づけ**: **Cell A** は **やや弱い**。**C / D** は **効きが強め**。**B** は **「動くが C/D ほど攻めすぎない」中間**として **扱いやすい**。
- **断定しないこと**: **最終 α/β**。**C / D の永久排除**ではない（**再観測の結果で見直しうる**）。

---

## 4. この判断の理由

- **B は A より改善が明確**で、**それでいて C/D より控えめ** — **最小差分・安全第一**の流れに **合う**。
- **格子を広げるより**、**実 save 上で⑦が書き込んだ `payroll_budget`** を **`--apply-temp-postoff-floor` なし**でも **突き合わせる**方が **次に進む**。
- **final offer 側**は **別トラック**として **残す**（**本決裁で解決済みとはしない**）。

---

## 5. 非目的

- **本メモによる最終 α/β の確定**。
- **C / D の否定**（**仮採用は B**、**他は温存**）。
- **5 セル目の追加**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **最終 offer 分布まで解決した**との **記述**。

---

## 6. 次に続く実務（1つだけ）

**Cell B（α=1.05, β=10M）を **コード上で一時適用**した状態で **D2/D1 の実 save を再作成**し、**observer を `--apply-temp-postoff-floor` なし**でも **突き合わせる**手順を **`docs/` に 1 本**まとめる（**再作成の具体 UI／シナリオはそのメモで固定**）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_CANDIDATE_CELL_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（仮採用＝Cell B、格子追加せず実 save へ）。
