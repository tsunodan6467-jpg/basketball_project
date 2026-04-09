# `pre_le_room=0` / `final_offer > buffer` を post-off budget から分離する（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。Cell B 固定: `docs/PAYROLL_BUDGET_POSTOFF_CELL_B_LOCK_DECISION_2026-04.md`。格子結果: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`。観測文脈: `docs/PAYROLL_BUDGET_POSTOFF_RATIO_TUNING_RESULTS_2026-04.md`、`docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_RESULTS_2026-04.md`。

---

## 1. 目的

- **Cell B 固定後**も **残っている** **`summary` 上の `pre_le_room=0`** および **`final_offer > buffer` の飽和（例: 1920/1920）**を、**post-off `payroll_budget` 床（案A・⑦）**の論点から **切り離し**、**別トラック**として **整理**する。
- **本メモは offer 側の最終方針の確定ではない**。

---

## 2. 確定事実

- **Cell B（α=1.05, β=10M）**により、**実 save でも** **before の gap 分布の開き**と **`room_unique=48`** が **再現**した（`docs/PAYROLL_BUDGET_POSTOFF_CELL_B_LOCK_DECISION_2026-04.md`）。
- **しかし**、**同一観測系**では **`pre_le_room=0`** が **残り**、**`final_offer > buffer = 1920/1920`** も **残った**（**格子観測でも同様の「飽和不変」が繰り返されていた**）。
- **読み取り**: **budget 側（`payroll_budget` 再設定・床）の改善だけでは**、**行列側の `pre_le_room` や最終 offer 分布までは説明しきれていない** — **論点を分けないと混線しやすい**。

---

## 3. 今回の判断（1 案）

**Cell B は post-off budget 側の第1候補として維持する。  
一方で、`pre_le_room=0` と `final_offer > buffer` は別論点とし、今後は offer 側（**clip**、**`room_to_budget`**、**pre-clip 領域**など）の **観測・判断メモ**として扱う。**

- **Cell B を後退させない**。**残件は「Cell B が誤り」という意味ではない**。
- **予算式・⑦の床**の論点と、**FA offer 生成・行列**の論点を **明示的に分離**する。
- **次段**は **offer 側の観測・設計メモ**へ **進む**（**本メモでは中身を決めない**）。

---

## 4. この判断の理由

- **before / room（`room_unique`）**は **実 save で改善が裏取り**できた。
- **それでも `pre_le_room` / final_offer 飽和が残る**なら、**原因仮説を budget だけに閉じるのは不自然**。
- **この段階で Cell B を崩して α/β を振り直す**より、**論点分離**の方が **安全**で **観測も説明しやすい**。

---

## 5. 非目的

- **Cell B の撤回**、**α / β の再格子比較**の **開始**（**本メモの範囲**）。
- **`clip` / `λ` / FA `buffer` の値を本メモで決定**すること。
- **コード変更**。
- **offer 側の最終方針**まで **本決裁で確定**すること。

---

## 6. 次に続く実務（1つだけ）

**`pre_le_room=0`** と **`final_offer > buffer`** を **対象**に、**offer 側の観測論点だけ**を整理する **短いメモ**を **`docs/` に 1 本**作成する（**budget 側の Cell B 決裁は参照しつつ、依存を混ぜない**）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PRE_LE_ROOM_AND_FINAL_OFFER_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（budget 軸と offer 軸の分離）。
