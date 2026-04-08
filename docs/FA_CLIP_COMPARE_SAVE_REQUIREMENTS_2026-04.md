# FA：clip／λ 比較に向く save の採取要件（設計メモ）

**作成日**: 2026-04-08  
**文書の性質**: **設計メモ（コード変更なし）**。スクリーニング手順: `docs/FA_OBSERVER_SAVE_SCREENING_2026-04.md`。複数 save 観測: `docs/FA_OBSERVER_SAVE_LIST_PLAYCHECK_2026-04.md`。行列・population: `docs/FA_OBSERVER_MATRIX_MODE_PLAYCHECK_2026-04.md`。確認コマンド: `tools/fa_offer_real_distribution_observer.py` の `summary:` 行。

---

## 1. 文書の目的

**payroll_budget clip／λ 比較**に使える **観測母集団**を得るため、**どのゲーム局面で `.sav` を採ればよいか**を短く固定する。  
以後、save を増やすときは **本メモの要件→実務ルール→`summary:` 判定**の順で迷わないようにする。

---

## 2. 今の save が比較装置として弱い理由

- **比較対象として残せたのは実質 2 本**（`quicksave`、`0330確認`）のみ。母集団の **幅がない**。  
- **1行サマリが同型寄り**（いずれも `soft_cap_early=0`、`room_unique=1`、`pre_le_room=0`）。**save を変えても行列の型が変わらない**。  
- **`room_to_budget` のユニークが 1** に張り付き、**チーム間・局面間の room 幅が観測に乗らない**（gap／matrix playcheck と整合）。  
- **`pre_le_room=0`** のため、**クリップ前から `offer ≲ room` が混ざる行列**になっておらず、**λ や式の差が見えにくい**。  
- **soft_cap_early 全行の save が手元に多く**、**そもそも clip 比較の土俵に乗らない**データが混じる。  
- **帰結**: ボトルネックは **observer や clip 式ではなく、比較に向く save の供給不足**。

---

## 3. 今後採りたい save の要件

### 3.1 保存タイミング（優先度の目安）

| 優先 | 局面の例 | 狙い |
|------|-----------|------|
| 高 | **オフシーズン FA 交渉が始まる直前**（声明・リスト確定後〜入札前） | FA プールとチーム予算が揃い、**診断行列の対象世界**に近い。 |
| 高 | **給与総額に明確な余裕がある局面**（ロスターが薄い・大型退団直後など） | **`payroll_budget` 対 roster の差**が大きく、`room` が伸びやすい。 |
| 中 | **シーズン終了直後**（契約更新・退団処理が反映された後） | ロスター／予算のばらつきが出やすい。 |
| 中 | **複数シーズン進行後**（同一リーグで年をまたいだ状態） | 固定 30M 偏重から逃げる**可能性**（保証はしない）。 |

### 3.2 欲しい状態（`summary:` で見たい方向）

- **`soft_cap_early` が 100% でない**（**非0%**）。全行早期の save は比較不能。  
- **`room_unique > 1` が出る可能性**（複数の `room_to_budget` が行列に載る）。  
- **`pre_le_room > 0` が出る余地**（`soft_cap_early=False` 行で `offer_after_soft_cap_pushback ≤ room_to_budget`）。  
- **`room` が 30M 一色でない**局面（buffer 同期パターンの単一値からの逸脱）。

### 3.3 できれば（設計メモ `FA_OBSERVER_MATRIX_REDESIGN_PLAN` と整合）

- **中額 FA 帯がプールに十分残っている**（top 独占だけでない）。  
- **給与余力が大きいチーム**がリーグ内に混在している（observer の `mixed_mid_fa_roomy` と相性がよい）。

---

## 4. save 採取の実務ルール

1. **いつ保存するか**  
   上表 §3.1 の **高優先タイミング**を狙う。**同じ局面を意識して 3〜5 本**、**異なるリーグ進行／異なる手動操作**でばらすとよい。  
2. **何本確保するか**  
   まず **最低 3 本**、目安 **5 本**。うち **1本は「意図的に薄いロスター」**で取るとよい。  
3. **命名ルール**  
   **`fa_clip_YYYYMMDD_番号.sav`** のように **日付＋連番**（ASCII 推奨）。日本語のみの名前は **`--save-list` や glob で事故りやすい**ため避ける。  
4. **保存後の確認**  
   リポジトリルートから **既定モード**で1本ずつ、または **`--save-list`** で一括:

   ```powershell
   Set-Location c:\Users\tsuno\Desktop\basketball_project
   python tools\fa_offer_real_distribution_observer.py --save-list (パス列)
   ```

   各ブロック先頭の **`summary:` を必ず読む**。可能なら **`mixed_mid_fa_roomy --fa-rank-start 25 --fa-rank-end 64 --roomy-team-count 16`** でも1本試す。  
5. **失敗 save の扱い**  
   §5 の **除外**に該当するものは **比較用フォルダから隔離**（サブフォルダ `rejected_soft_cap_only` 等）か、**ファイル名に `_reject` サフィックス**。**削除しなくてよい**が **clip 用 `--save-list` には含めない**。

---

## 5. 採用 / 不採用の判定基準（`summary:` ベース）

`docs/FA_OBSERVER_SAVE_SCREENING_2026-04.md` と整合させる。

| 判定 | 条件 |
|------|------|
| **除外** | **`soft_cap_early` が全ペア（表示上 100%）** → clip／λ 比較の母集団に **使わない**。 |
| **除外** | **`room_unique = 0` かつ `soft_cap_early` が高率**（実質 soft cap 側）→ **room が行列に乗っていない**。 |
| **保留（比較候補の最低ライン）** | **`soft_cap_early = 0%` かつ `room_unique >= 1`** だが **`pre_le_room = 0`** → **現行 quicksave 型**。**比較の「土俵」には乗るが装置は未完成**。既存2本と同型なら **優先度は低い**。 |
| **採用（強）** | 上記最低ラインを満たし、かつ **`room_unique >= 2`** または **`pre_le_room >= 1`** のどちらか → **比較装置として優先的に `--save-list` に入れる**。 |
| **要再観測** | 採用（強）に近いが **mixed だけ変わる**など → **既定・mixed 両方の `summary:` を記録**してから判断。 |

---

## 6. 今回はまだやらないこと

- **observer の改修**  
- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の変更**  
- **`_clip_offer_to_payroll_budget` の式変更**  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の改造**

---

## 7. 次に実装で触るべき対象（1つだけ）

**新規に採取した save を、`--save-list` で一括スクリーニングし、`docs/FA_OBSERVER_SAVE_SCREENING_2026-04.md` の表を更新する（観測のみの1ラウンド）。**

- **なぜその1手が今もっとも妥当か**  
  **要件付き save が無い限りコードを動かしても行列は飽和しやすい**。まず **データが本当に増えたか**を **既存 observer だけで検証**するのが最短。  
- **何はまだ残るか**  
  **採用（強）save が得られたあとの λ 記録試行／clip 別式の決裁**、**スクリーニング結果の本メモ §3・§5 の追随改訂**。

---

## 実行コマンド（確認用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

---

## 改訂履歴

- 2026-04-08: 初版（clip／λ 比較用 save 採取要件）。
