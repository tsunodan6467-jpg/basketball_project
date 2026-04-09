# offer 側残論点: `pre_le_room=0` と `final_offer > buffer`（観測整理メモ）

**作成日**: 2026-04-08  
**性質**: **観測・切り分け対象の固定（コード変更なし）**。論点分離の決裁: `docs/FA_PRE_LE_ROOM_AND_FINAL_OFFER_DECISION_2026-04.md`。Cell B: `docs/PAYROLL_BUDGET_POSTOFF_CELL_B_LOCK_DECISION_2026-04.md`。格子文脈: `docs/PAYROLL_BUDGET_POSTOFF_ALPHA_BETA_GRID_RESULTS_2026-04.md`。

---

## 1. 目的

- **`pre_le_room=0`** と **`final_offer > buffer` の飽和**に **絞り**、**offer 生成〜clip までの流れ**のうち **どこを観測すべきか**を **短く整理**する。
- **本メモは実装メモではない**。**観測対象の置き場**を固定する。

---

## 2. budget 側で解けたこと / 残ったこと

### 解けたこと

- **Cell B（α=1.05, β=10M）**により、**before の gap 分布**は **開いた**（**実 save でも再現**）。
- **`room_unique=48`**（**行列上の `room_to_budget` のユニーク数**）まで **再現**した。
- **結論（budget 軸）**: **post-off の floor 導入・係数候補**は **一定の効果**を持つ — **第1候補として Cell B を維持**（別決裁）。

### 残ったこと

- **`pre_le_room=0`**（**observer の `summary` 行**）。
- **`final_offer > buffer = 1920/1920`**（**同一観測系のヒストグラム**）。
- **Cell B 実 save でも上記は残存** — **budget 側だけでは説明しきれない**（**前段決裁どおり別論点**）。

---

## 3. 今回切り分ける offer 側論点

**実装の正本はコード**（本メモでは **観測上の読み口**だけ置く）。`tools/fa_offer_real_distribution_observer.py` の **`_calculate_offer_diagnostic` 由来行列**を前提とする。

| 論点 | 整理 |
|------|------|
| **(1) pre-clip 領域の room 判定** | **`pre_le_room`** は **`soft_cap_early` でない行**について、**pre-clip 相当の `offer_after_soft_cap_pushback` と `room_to_budget` を比較**し、**`offer <= room` となる件数**を数えた **集計**（**`summary` 行**）。**`pre_le_room=0`** は **「その条件を満たす pair が 0」**という **読み**。**どの診断フィールドか**は **次メモで observer 出力上の位置に絞って固定**する。 |
| **(2) `room_to_budget` の効き方** | **各 (team, FA) 行**の **`room_to_budget`** が **budget（同期後 `payroll_budget` 等）からどう付くか**。**`room_unique`** は **その値のユニーク数**。**before 主軸とは別**（`summary` 注記: **matrix=post-sync**）。 |
| **(3) clip 後の `final_offer` 飽和** | **`final_offer`** は **診断パイプラインの後段**。**`> buffer` 一色**が **どの段階から起きるか**（**pre-clip ですでに room を超えている**のか、**clip が上げ切っている**のか等）は **未確定** — **段階ごとの値を並べて見る**必要がある。 |

---

## 4. 今回の判断（1 案）

**以後の観測は、budget 側の候補選定（Cell B）とは切り離し、offer 側の次の 3 論点を **順に**見る方針とする。**

1. **pre-clip の room 判定**（**`pre_le_room` の意味と、中身の診断フィールド**）  
2. **`room_to_budget` の分布**（**`room_unique` と併読**）  
3. **`final_offer > buffer` 飽和**（**clip 後と前段の関係**）

- **予算式・⑦の議論は Cell B で一旦固定**し、**残件は offer 側の流れの中**で切る。
- **一気に全部を同時解決しない**。**観測順**を持つ。

---

## 5. 観測順の優先順位

1. **`pre_le_room=0` の確認** — **何を数えているか**を **observer 出力・診断キー**に **紐づけて固定**する。  
2. **`room_to_budget` の分布確認** — **ユニーク数・典型値**と **before 主軸**の **対応**を **混同しない**。  
3. **`final_offer > buffer` 飽和の確認** — **(1)(2) のあと**で **後段の形状**を見る。

---

## 6. 非目的

- **コード変更**。
- **Cell B の再比較**、**α / β の再調整**。
- **`clip` / `λ` / FA `buffer` の最終方針決定**。
- **offer 側の解決策**の **断定**。

---

## 7. 次に続く実務（1つだけ）

**`pre_le_room=0` が、observer 出力上 **どの行・どの診断キー**に対応するかを **`fa_offer_real_distribution_observer.py` の `summary` 生成**に **紐づけて**整理する **短いメモ**を **`docs/` に 1 本**作成する。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_OFFER_SIDE_OBSERVATION_NOTE_2026-04.md -Pattern "目的|budget 側で解けたこと / 残ったこと|今回切り分ける offer 側論点|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（offer 側 3 論点・観測順）。
