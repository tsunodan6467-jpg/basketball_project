# Cell B 実 save 再作成 — 手順メモ（`--apply-temp-postoff-floor` なし確認）

**作成日**: 2026-04-08  
**性質**: **実務手順の固定（本ファイルだけではコード変更しない）**。仮採用: `docs/PAYROLL_BUDGET_POSTOFF_CANDIDATE_CELL_DECISION_2026-04.md`。4 セル結果: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`。BUFFER 方針の文脈: `docs/PAYROLL_BUDGET_POSTOFF_TEMP_TUNING_DECISION_2026-04.md`。

---

## 1. 目的

- **Cell B（α=1.05, β=10M）**を **コードに一時適用**したうえで、**⑦ `_process_team_finances` が save に書き込んだ `payroll_budget`** を、**`--apply-temp-postoff-floor` なし**の observer で **突き合わせる**ための **手順**を **1 本に固定**する。
- **本メモは最終 α/β の確定ではない**。**手順メモ**である。

---

## 2. 前提整理

| 項目 | 内容 |
|------|------|
| **仮採用 Cell B** | `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO = 1.05`、`TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER = 10_000_000` |
| **意図** | **再計算フラグなし**でも、**格子観測（`--apply-temp-postoff-floor` あり）**と **大きくズレない**かを見る |
| **作業後の定数** | **既定値（α=1.0, β=3M）へ戻すか**は **別の実装／運用指示**で管理する（**本手順だけでは強制しない**） |

---

## 3. 保存名

**推奨（Cell B がファイル名から分かる）**

| 系統 | 推奨ファイル名 |
|------|----------------|
| D2 postfloor 相当 | `debug_user_boost_d2_user_cellb.sav` |
| D1 postfloor 相当 | `debug_user_boost_d1_user_cellb.sav` |

**補足（日付を付ける場合）**: `debug_user_boost_d2_user_cellb_2026-04-08.sav` のように **日付サフィックス**を足してもよい。**`cellb`**（または同等の明記）を **必ず含める**。

**保存先（例）**: `C:\Users\tsuno\.basketball_sim\saves\`（環境に合わせて読み替え）。

---

## 4. 実施手順

1. **`basketball_sim/models/offseason.py`** の定数を **Cell B** に **一時変更**する。  
   - `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO = 1.05`  
   - `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER = 10_000_000`
2. **ゲームを起動**する（**変更後のコード**が読み込まれる起動方法にする）。
3. **元の postfloor 系 save**（例: `debug_user_boost_d2_user_postfloor.sav` / `..._d1_...`）を **読み込む**。
4. **オフシーズンで⑦ `_process_team_finances`（来季人件費目安の再設定）が実行されるタイミング**を **1 回通す**（**新しい定数で `payroll_budget` が書き込まれる**状態にする）。
5. **§3 の新しい名前**で **保存**する（**D2 用・D1 用で各 1 本**）。
6. **リポジトリルート**で、**`--apply-temp-postoff-floor` を付けず**に observer を実行する（§5）。
7. **`sync_observation`（before）**、**`user_team_snapshot`**、**`summary`** を **§6** の観点で確認する。
8. **必要なら** `offseason.py` の **TEMP を既定値へ戻す**（**次タスクの指示に従う**）。

---

## 5. observer コマンド例（**`--apply-temp-postoff-floor` なし**）

**ポイント**: 本確認では **フラグを付けない**（save 内の `payroll_budget` をそのまま読む）。

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
$saveRoot = "C:\Users\tsuno\.basketball_sim\saves"
$d2 = Join-Path $saveRoot "debug_user_boost_d2_user_cellb.sav"
$d1 = Join-Path $saveRoot "debug_user_boost_d1_user_cellb.sav"
$logD2 = "observer_cellb_d2_no_reapply.log"
$logD1 = "observer_cellb_d1_no_reapply.log"

python tools\fa_offer_real_distribution_observer.py --save $d2 2>&1 | Tee-Object -FilePath $logD2
python tools\fa_offer_real_distribution_observer.py --save $d1 2>&1 | Tee-Object -FilePath $logD1

Select-String -Path $logD2,$logD1 -Pattern "before:|user_team_snapshot:|summary:|final_offer > buffer"
```

**保存名を日付付きにした場合**は `$d2` / `$d1` のパスだけ差し替える。

---

## 6. 確認ポイント

**4 セル観測（Cell B・`--apply-temp-postoff-floor` あり）**の出力と **並べて**見る。

| 項目 | 内容 |
|------|------|
| **before** | `gap_unique` / `gap_min` / `gap_max` |
| **`user_team_snapshot`** | `payroll_budget` / `roster_payroll` / `gap` |
| **`summary`** | `room_unique` / `pre_le_room` |
| **（任意）** | `final_offer > buffer`（**別論点**として **参考**） |

**読み取りの目安**: **数円単位の完全一致**を求めず、**格子 B と同じオーダー・同じ傾向**か（**大きくズレていないか**）を見る。

---

## 7. 非目的

- **本手順だけで最終 α/β を確定**すること。
- **Cell B の恒久採用**の **断定**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **追加の格子比較**の開始。

---

## 8. 次に続く実務（1つだけ）

**本手順に従い、** **Cell B をコードに一時適用した状態で** **D2/D1 の実 save を再作成**し、**`--apply-temp-postoff-floor` なし**の observer で **同傾向が再現するか**を **確認・記録**する（**結果は別メモまたは既存結果表の追記でよい**）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_CELL_B_REAL_SAVE_STEPS_2026-04.md -Pattern "目的|前提整理|保存名|実施手順|observer コマンド例|確認ポイント|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（Cell B・実 save・observer 無フラグ）。
