# Cell B を第1候補として固定する（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。仮採用: `docs/PAYROLL_BUDGET_POSTOFF_CANDIDATE_CELL_DECISION_2026-04.md`。実 save 手順: `docs/PAYROLL_BUDGET_POSTOFF_CELL_B_REAL_SAVE_STEPS_2026-04.md`。4 セル結果: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`。

---

## 1. 目的

- **Cell B（α=1.05, β=10M）**を、**実 save 再現確認済み**の **第1候補**として **現時点で固定**する。
- **本メモは最終 α/β の完全確定ではない**。**post-off budget 側の暫定基準**の **置き場**を決める。

---

## 2. 確定事実

- **4 セル比較**で **Cell B** は **中間候補**として **有望**（`docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`）。
- **`--apply-temp-postoff-floor` なし**の **D2 / D1 実 save（cellb 系）**でも次が **再現**した。

| 断面 | before `gap_unique` | before `gap_min` | before `gap_max` | user `gap` | `room_unique` | `pre_le_room` |
|------|---------------------|------------------|------------------|------------|---------------|---------------|
| **D2 cellb** | 48 | 39,382,943 | 64,580,985 | 52,465,250 | 48 | 0 |
| **D1 cellb** | 48 | 44,860,710 | 62,396,122 | 55,944,025 | 48 | 0 |

- **読み取り**: **before の gap 分布が開く**こと、**`room_unique=48` まで開く**ことは、**一時的な再計算フラグ観測だけでなく**、**⑦が save に書き込んだ状態**でも **再現**している。
- **一方**: **`pre_le_room=0`** のまま、**`final_offer > buffer = 1920/1920`** も **引き続き残る**（**offer 側は別論点**）。

---

## 3. 今回の判断（1 案）

**Cell B（α=1.05, β=10,000,000）を、現時点の「実 save 再現確認済みの第1候補」として固定する。**

- **以後**、**post-off `payroll_budget` 床まわりの暫定基準候補**は **まず Cell B を基準**に扱う（**文書・検証のデフォルト置き場**）。
- **格上げの意味**: **「仮採用候補」から一段進め**、**実 save で裏取りできた候補**として **第1候補**に置く。
- **断定しないこと**: **最終確定**、**永久固定**、**C / D の排除**、**offer 側の解決済み**。

---

## 4. この判断の理由

- **A より効きがはっきり**あり、**C / D ほど強くない** — **最小差分・安全第一**に **合う**。
- **D2 / D1 の実 save** で **意図した before / room 側の開き**が **再現**した — **格子観測だけに依存しない**。
- **残論点（`pre_le_room` / final_offer）は別メモ**に **切り出せる**。

---

## 5. 非目的

- **本メモによる最終 α/β の完全確定**。
- **Cell B の永久固定**の **断定**。
- **C / D の永久否定**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **offer 側の未解決まで本決裁で片付いた**との **記述**。

---

## 6. 次に続く実務（1つだけ）

**Cell B を基準に、** **`pre_le_room=0`** および **`final_offer > buffer` が残る件**を **別論点**として切る **短い決裁メモ**を **`docs/` に 1 本**作成する。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_CELL_B_LOCK_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（Cell B＝実 save 再現済み第1候補の固定）。
