# FA：1行サマリによる save スクリーニング（clip／λ 比較の対象確定）

**作成日**: 2026-04-08  
**文書の性質**: **観測メモ（コード変更なし）**。複数 save 数表: `docs/FA_OBSERVER_SAVE_LIST_PLAYCHECK_2026-04.md`。population playcheck: `docs/FA_OBSERVER_MATRIX_MODE_PLAYCHECK_2026-04.md`。observer: `tools/fa_offer_real_distribution_observer.py`（1行 `summary:` は本メモ作成時点の出力）。

---

## 1. 文書の目的

`fa_offer_real_distribution_observer` の **1行サマリ**（`soft_cap_early` 比率、`room_unique`、`pre_le_room`）で手元 save をふるい分けし、**payroll_budget clip／λ 比較の母集団として残す save** と **除外する save** を固定する。以後の観測で **毎回迷わない第一候補群**を明示する。

---

## 2. ふるい分けの基準

| 判定 | 条件（目安） | 理由 |
|------|----------------|------|
| **除外** | **`soft_cap_early` が全ペア（100% 近傍）** | 行列が **soft cap 早期**に支配され、**`_clip_offer_to_payroll_budget` が効く帯が観測されない**。今回の clip 比較の主題外。 |
| **除外（補助）** | **`room_unique = 0` かつ `soft_cap_early` 高率** | `room_to_budget` が行列に載らず、**S6／budget clip の土俵に乗らない**。上記除外とセットで起きやすい。 |
| **残す** | **`soft_cap_early = 0%`（非早期が1件以上）** かつ **`room_unique >= 1`** | **S6 経路で `final>buffer` 等が出る**（過去 playcheck と整合）。clip／λ の数値比較の前提が満たせる。 |
| **保留** | **`pre_le_room = 0` だが上記「残す」条件は満たす** | **クリップ前はまだ `offer > room` 一色**でも、**比較装置の母集団としては暫定採用**可（内側帯は別観測）。 |
| **mixed** | 既定と **同じサマリ傾向**なら **判定は既定と同一**とみなす | `docs/FA_OBSERVER_SAVE_LIST_PLAYCHECK_2026-04.md` §3.2 より、手元5本は **既定／mixed で soft_cap・room・pre の型が同型**。 |

---

## 3. save ごとの判定結果

**観測日**: 2026-04-08。**コマンド**: 下記 §「実行コマンド」。**モード**: **既定**（top 40 FA × 全チーム、1920 ペア）。**1行サマリ**は各 save ブロック直後の `summary:` を転記。

| save（論理名） | 実ファイルの目安 | summary（転記） | 判定 | 短い理由 |
|----------------|------------------|-----------------|------|----------|
| **0330確認** | `0330` 始まりの `.sav` | `soft_cap_early=0/1920 (0.0%), room_unique=1, pre_le_room=0` | **残す** | S6 生存、`room` あり。`pre_le_room=0` は保留扱いだが比較対象。 |
| **quicksave** | `quicksave.sav` | `soft_cap_early=0/1920 (0.0%), room_unique=1, pre_le_room=0` | **残す** | 0330 と同型。パスが単純で再現しやすい。 |
| **kakunin2** | `kakunin2.sav` | `soft_cap_early=1920/1920 (100.0%), room_unique=0, pre_le_room=0` | **除外** | 全行早期。clip 比較不能。 |
| **kakunin3** | `kakunin3.sav` | 同上 | **除外** | 同上。 |
| **確認１** | `確認` を含む1件（glob 上5本目） | 同上 | **除外** | 同上。 |

**mixed**（`mixed_mid_fa_roomy`、ranks 25–64、`roomy-team-count 16`）: 過去観測どおり **quicksave／0330 は `soft_cap_early=0`、`room_unique=1`、`pre_le_room=0`**、kakunin 系／確認１は **100% 早期・`room_unique=0`** → **判定は上表と同一**。

---

## 4. 今回の観測から分かること

1. **比較対象として使える save は手元では 2 本**（**quicksave**、**0330確認**）。**3 本は1行サマリだけで除外確定**（全行 `soft_cap_early`）。  
2. **save 差の本体**は、数値上は **`soft_cap_early` が 0 か 100% か**の二極。**S6 が生きるか／早期で全滅するか**がスクリーニングの主軸。  
3. **今後の観測の軸**は **`quicksave` を第一**に **`--save-list` で `0330確認` を並べる**のが最短（同一母集団型の二重化）。  
4. **`pre_le_room` や `room_unique>1` を出す save は未所持**のため、**比較装置の「完成」には至っていない**。**追加 save の採集**がボトルネック。

---

## 5. 比較対象として残す save

| 優先度 | save | 用途 |
|--------|------|------|
| **第一候補** | **`C:\Users\tsuno\.basketball_sim\saves\quicksave.sav`** | ASCII パス・手元標準。**以後の clip／λ 観測のデフォルトアンカー**。 |
| **第二候補** | **`0330確認.sav`**（実パスは環境依存） | **quicksave とサマリ同型**だが、**別プレイセッションのセカンドオピニオン**として `--save-list` に併記。 |

**落とす／除外**: **kakunin2、kakunin3、確認１**（および **1行サマリが `soft_cap_early=100%` の save 全般**）。**理由**: **payroll_budget clip の比較母集団にならない**。

**保留にしないもの**: 上記除外群は **サマリだけで再実行の価値は低い**（毎回100%早期が確認されるまで）。

---

## 6. 今回はまだやらないこと

- **observer の追加改修**  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`docs/` に「clip 比較用 save の採取要件」メモを1本追加する**（例: ロスター・給与枠・オフフェーズの目安、保存タイミング、保存後に `summary:` で期待する最低条件）。

- **なぜその1手が今もっとも妥当か**  
  **残す save は2本でサマリ同型**であり、**`pre_le_room` や `room_unique` を伸ばす新しいデータが無い限り、λ や clip 式のコードを動かしても行列は飽和したまま**の見込みが高い（gap／playcheck と整合）。**次のボトルネックはコードではなく「観測に耐える save の供給」**。

- **何はまだ残るか**  
  **要件付き save が揃ったあとの `--save-list` 再スクリーニング**、**そのうえでの λ 記録用試行または clip 別式の決裁**、**本メモの第一・第二候補の更新**。

---

## 実行コマンド（再現）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke

python tools\fa_offer_real_distribution_observer.py --save-list `
  "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin2.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin3.sav"

# 手元の全 .sav を列挙して一括（Python 推奨・日本語名対策）:
python -c "from pathlib import Path; import subprocess, sys; p=Path(r'C:/Users/tsuno/.basketball_sim/saves'); ps=sorted(p.glob('*.sav')); subprocess.run([sys.executable,'tools/fa_offer_real_distribution_observer.py','--save-list']+[str(x) for x in ps], cwd=r'c:/Users/tsuno/Desktop/basketball_project')"

# mixed 併用（判定が同型であることの再確認用）
python tools\fa_offer_real_distribution_observer.py --save-list `
  "C:\Users\tsuno\.basketball_sim\saves\quicksave.sav" `
  "C:\Users\tsuno\.basketball_sim\saves\kakunin3.sav" `
  --population-mode mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16
```

---

## 改訂履歴

- 2026-04-08: 初版（1行サマリによる save スクリーニング）。
