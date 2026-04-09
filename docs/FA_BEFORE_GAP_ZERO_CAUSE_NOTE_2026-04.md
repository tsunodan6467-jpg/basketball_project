# FA：`before` の `gap` が 10 人ロスター save でも `0` 一色になりうる理由（原因整理）

**作成日**: 2026-04-08  
**文書の性質**: **原因分析メモ（コード変更なし）**。関連: `docs/FA_BEFORE_AXIS_SAVE_PLAYCHECK_2026-04.md`、`docs/FA_ROOM_UNIQUE_ONE_CAUSE_NOTE_2026-04.md`、`docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`。実装参照: `tools/fa_offer_real_distribution_observer.py`（`_teams_payroll_gap_stats` / `_team_payroll_room`）、`basketball_sim/models/offseason.py`（シーズン締め付近の `payroll_budget` 再設定）。

---

## 1. 文書の目的

**10 人までロスターを薄くした save** を複数作っても、`sync_observation` の **`before` で `gap_unique=1` かつ `gap_min=gap_max=0`** が続く現象を、**人数操作だけでは before の多様性が出ない理由**として整理する。**7 人ルール変更や clip 改修に進む前に**、何を事実として押さえるべきかを固定する。

---

## 2. before の `gap` が意味するもの

- **定義（observer 実装）**: `tools/fa_offer_real_distribution_observer.py` の `_team_payroll_room` により、チームごとに  
  **`gap = max(0, payroll_budget − roster_payroll)`**  
  とみなす。ここで **`roster_payroll`** は **`team.players` の `salary` 合算**（`_team_roster_payroll`）。本番の同期 `_sync_payroll_budget_with_roster_payroll` が使う `get_team_payroll(team)` も、通常は同じロスターに対する給与合計であり、**before 統計の解釈上は「ロスター給与との差」**でよい。
- **意味**: **「人件費目安（`payroll_budget`）が、いまのロスター年俸総額よりどれだけ上にあるか」**の非負クリップ。**キャップ room／診断の `room_to_budget` と同型の読み**（符号は「予算 − 実ペイロール」）。
- **`money` ではない**: **所持金 `money` はこの式に入らない**。before の `gap` は **給与ガイドライン用フィールドとロスター契約額の関係**だけで決まる。
- **追記（2026-04-08）**: **`payroll_budget` が小さく見えても即「バグ」と短絡しないこと。** 当該フィールドは **現行オフ後式の結果**（`roster_payroll` と**別軸**）。観測上の `gap` は **room の比較**用で、式の是非は **`docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`**（式変更は別決裁）。
- **別論点**: ゲーム進行のどこかで `money` が間接的に `payroll_budget` の更新経路に関与しうるかは **このメモの主題外**だが、**一般に「金は潤沢＝ gap が開く」とは限らない**。

---

## 3. 10 人 save でも `gap=0` になりうる理由

**観測済み（ユーザー報告）**: 10 人ロスターの save を複数作成しても、`before` で **`gap_min=gap_max=0`**（`gap_unique=1`）。`sync1`／`sync2` は従来どおり **buffer 相当で均一化**。

**コードから読めること（仮説の土台）**:

1. **`gap=0` の2通り**  
   - **`payroll_budget == roster_payroll`**（ちょうど同額）  
   - **`payroll_budget < roster_payroll`** でも **`max(0, …)` で 0 に丸められる**（目安が実ペイロールより低い「負の余地」は 0 表示）。

2. **人数を減らすだけでは `payroll_budget` が自動では動かない**わけではない  
   - シーズン締め・オフ処理などで **`payroll_budget` がロスター状況と無関係な式で再設定**されたり、プレイ中に **目安と実ペイロールが近い値に張り付く**局面がありうる（例: `offseason.py` 内の **`team.payroll_budget = max(base_budget, …)`** 系の再計算は **市場規模・人気等ベース**で、**人数削減そのものを直接入力にしていない**が、**結果として実ペイロールと近い帯に収まりうる**）。

3. **「10 人にした」のに gap が開かない**読み  
   - **保存時点の `payroll_budget` が、すでにそのロスターの給与合計と同程度（以下）**なら、**人数を減らしても**（給与総額が下がっても）**目安も同時に下がる経路**に乗るか、**もともと差が無い**なら **`before` は引き続き `gap=0` 一色**になりうる。  
   - 逆に、**目安だけが高く残りロスターだけ薄い**なら **`gap>0`** が期待されるため、**観測が 0 一色なら「save に書かれた `payroll_budget` と roster 合計の関係」側を疑う**のが筋がよい。

4. **既存の save 間比較メモとの整合**  
   - `docs/FA_BEFORE_AXIS_SAVE_PLAYCHECK_2026-04.md` でも、**複数 save で `before` の gap は全域 0 寄り**と整理済み。**10 人化は「薄いロスター」の一種だが、before の gap 多様化には直結しない**と読める。

**断定でない部分**: 手元 3 本の save で **`payroll_budget` と `roster_payroll` の実数値ログ**を取っていない限り、「どの経路で目安が追随したか」は **ケースごとの追跡が必要**。

---

## 4. `money` 多額所持の影響について

- **直接**: **before の `gap` に `money` は入らない**。したがって **「サラリー支払いが苦しくて所持金をかなり増やした」こと自体は、`gap = max(0, payroll_budget − roster)` を大きくする十分条件ではない**。
- **直接影響が強い証拠**: 本リポジトリの観測メモ群では、**所持金と before gap の対応**を切り分けたログは **まだ主線になっていない**（＝**強い証拠は未提示**）。
- **間接経路（ありうるが要確認）**: プレイ操作が **オフ締め・経営イベント・別 UI** を経由して **`payroll_budget` を更新**した場合、**結果として gap が変わる**ことはある。これは **money → gap** ではなく **「その操作が触ったフィールド」→ gap** の話。
- **主因候補の強さ**: **「所持金が多いから gap が開く」は弱い／誤解されやすい**。**主因候補として優先すべきは `payroll_budget` とロスター給与の関係**。

---

## 5. 今回の原因整理から分かること

- **10 人まで減らすだけでは、before の `gap` 多様化には不十分**になりうる（観測どおり）。**薄いロスター save** は **採取要件上は有用**だが、**「gap が開く save」**とは **別次元**。
- **ボトルネックの短い判断**  
  - **人数条件そのもの**より、**save 時点の `payroll_budget` の持ち方**（および **ロスター給与との差**）が **before 一色の主因候補**。  
  - **同期前 observer の仕様**は、`before` をそのまま出しているだけで、**0 一色を「作っている」のではなく「保存データがそうならそのまま見えている」**。
- **7 人ルール変更について**  
  - **今すぐ 7 人ルールに飛ぶより、まず `payroll_budget`／ロスター給与／（必要なら）`money` を同じ断面で観測し、before が 0 になる条件を事実固定する方が安全**（ルール変更は **観測軸を汚しやすい**）。

---

## 6. 今回はまだやらないこと

- **observer 本体のロジック変更**、**同期スキップの新設**  
- **`_sync_payroll_budget_with_roster_payroll` / buffer / λ / `_clip_offer_to_payroll_budget` の変更**  
- **最低ロスター人数（7 人案等）のルール変更**  
- **save 形式の変更**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`tools/fa_offer_real_distribution_observer.py` で、`sync_observation` の `before` 行の直後に、ユーザーチーム（または `is_user_team` が真のチームが無ければ先頭 1 チーム）について、`money`・`payroll_budget`・ロスター給与合計・`max(0, payroll_budget − その合計)` を **1 行で出す観測出力を追加する**（既定 ON でもフラグ付きでもよいが **変更はこの1点に限定**）。**

- **なぜその1手が今もっとも妥当か**  
  **「10 人にしたのに gap=0」**が **(A) 予算=給与、(B) 予算<給与のクリップ、(C) 別フィールドの取り違え**のどれに近いかを、**save を増やす前に**1 本のログで切り分けられる。**所持金多額**との **同時表示**で、**ユーザーの疑問（money と gap）**にもその場で答えられる。
- **何はまだ残るか**  
  **全 48 チームの表形式ダンプ**、**save 採取タイミングの指南改訂**、**7 人ルール・同期スキップの設計決裁**、**before で `gap` が正に開く save の意図的採取**（`docs/FA_CLIP_COMPARE_SAVE_REQUIREMENTS_2026-04.md` 系）。

---

## 実行コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md -Pattern "gap|payroll_budget|money|7人"
```

---

## 改訂履歴

- 2026-04-08: 初版（10 人 save と before `gap=0` の原因整理）。
- 2026-04-08: §2 追記（POSTOFF 決裁との整合・バグ短絡の回避）。
