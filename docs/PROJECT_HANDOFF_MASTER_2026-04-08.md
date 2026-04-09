# プロジェクト引き継ぎ正本（ChatGPT / 新 Cursor chat 用）

**作成日**: 2026-04-08  
**用途**: このファイルを新しいチャットに**そのまま貼る**ことで、固定ルール・現状・決裁・未確定・次の1手まで**意図をずらさず**再開する。  
**性質**: 整理済み手引き。**会話ログの貼り付けではない**。事実／仮説／決裁／未確定を区別する。

---

## 1. 文書の目的

- **何のため**: バスケシミュレーション開発案件（特に **FA と `payroll_budget` 観測ライン**）の**単一の正本**。
- **次 chat での使い方**
  1. まず本ファイルを通読（§2・§5・§13）。
  2. 数式・タイムラインの詳細は `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md` 等の**リンク先正本**を参照。
  3. 実装に入る前に **§13 の「次にやるタスク」は1つだけ**を実行する（並行で別テーマに逸れない）。

---

## 2. この案件の固定ルール（Cursor / 開発運用）

| ルール | 内容 |
|--------|------|
| 編集方針 | `.py` は**全文書き換え前提**（当該ファイルを**全体として**読み・整合させる前提。断片推測で壊さない）。**差分の大きさはタスク必要最小限**（ついで修正禁止と併せる）。 |
| 説明 | **簡潔な日本語**。 |
| 回答の締め | 可能なら末尾に**次にやるタスクを1つ**（本正本 §13 と整合）。 |
| 品質 | **安定性最優先**。 |
| ついで修正 | **禁止**（スコープ外のリファクタ・整形連鎖をしない）。 |
| コミット | **1コミット1目的**。 |
| チャットでのコード | **長文のコード直書きは不要**。変更ファイル名・要点・実行コマンド・抽出コマンド・差分要約を優先。 |
| ユーザー環境 | **実環境**想定。可能ならコマンドはエージェント側で実行し、手順だけ押し付けない。 |

---

## 3. プロジェクトの全体像

- **何を作っているか**: 日本を舞台にしたバスケットボールクラブ経営・シミュレーション（`basketball_sim`）。チーム・選手・シーズン・オフシーズン・FA・経済・GUI などを含む。
- **最終目標**: 一貫したシミュレーション体験と、整合した経済／契約／FA 挙動（開発段階では観測可能性・再現性も重視）。
- **開発方針**: 正本ドキュメント（`docs/`）で決裁・原因を固定し、**テストとスモーク**で回帰を守る。**ついで修正しない**。
- **作品の核**: クラブ運営とシーズン進行の一体感、および内部ルールの説明可能性。
- **CLI / GUI**: CLI は開発・検証・一部プレイ導線。GUI（`main_menu_view` 等）は本プレイ寄り。**観測ツール**（`tools/fa_offer_real_distribution_observer.py`）は本番経路に直結しない診断用。

---

## 4. 現在の調査テーマの要約（FA × `payroll_budget` clip 観測）

- **主題**: **FA における `payroll_budget` と clip（room／`room_to_budget`）の観測**。`soft_cap_early` や S6 微小オファー行の分布を、**save 実体**と**行列 observer**で読むライン。
- **before / sync 後の読み方（決裁済み）**
  - **主比較軸**: 同期**前**の `sync_observation` の **`before`**（`payroll_budget`／`roster_payroll`／`gap` のばらつきが残りやすい）。
  - **補助軸**: **`sync1`／`sync2`** および同期後の行列・`summary`（本番寄せの挙動確認用）。  
  - 正本: `docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`
- **`room_unique=1` 問題（観測）**: 同期をかけた後は `gap` が **buffer 付近に収斂**しやすく、行列上 **多様な room が潰れる**ことがある。before 主軸で切り分ける、という決裁。
- **`gap=0` 問題**: observer 定義では **`gap = max(0, payroll_budget − roster_payroll)`**。オフ後に **`payroll_budget` がロスター年俸に比べ極端に小さい**と、**before でも `gap=0` 一色**になりやすい（クリップの結果）。**主因は `money` でも load でもなく**、**オフ後再設定式が roster に追従しない**こと（決裁済みの整理）。
- **どこまで切り分けたか（確定）**
  - save/load は `payroll_budget` を壊していない（roundtrip テスト）。
  - 新規開始〜初年度オフ前は user の `payroll_budget=120M` が残りやすい（timeline テスト・ドキュメント）。
  - オフ締め後は `_process_team_finances` が式で再設定する（コード・テスト）。
  - 実 save の **24,018,800** は **式と厳密一致**（下 §10）。`user_team_snapshot` に式入力5項目を追加済み（再検算しやすい）。

---

## 5. 重要な決裁・結論（決裁済み）

以下は**この正本では動かさない前提の結論**（詳細は各 doc）。

1. **before を比較観測の主軸**、sync 後は**補助軸**（`docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`）。
2. **user team をインシーズン CPU FA 自動補強から除外**（`Season._process_inseason_free_agency` で `run_cpu_fa_market_cycle` に渡す `teams` を非 user のみに）。決裁: `docs/INSEASON_CPU_FA_USER_TEAM_EXCLUSION_DECISION_2026-04.md`。
3. **CLI に契約解除（FA 送り）**を **`roster_fa_release` 経由で**本番と整合（GUI も同モジュール）。
4. **`money` は**観測していた **before `gap=0` の主因ではない**（切り分け済み）。
5. **save/load は `payroll_budget` を壊していない**（roundtrip 検証）。
6. **新規開始直後〜初年度オフ前**は user の **`payroll_budget=120M` が残りやすい**（⑤まで上書きされにくい）。
7. **オフ後**は **`_process_team_finances()` 内の式**で `payroll_budget` が再設定される。
8. **実 save** での **`payroll_budget=24,018,800`** は、**当該チームの `league_level`・経営4属性**を入れた**同じ式で厳密一致**（§10）。
9. **before で gap が開きにくい**主因の整理: **再設定式が `roster_payroll` を見ない**ため、**高額ロスターでも予算フィールドは低いまま**になり、`max(0, …)` で **0 固定**になりやすい（`docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md` と整合）。

---

## 6. FA / `payroll_budget` 観測ラインの詳細時系列（圧縮版）

時系列は**古い試行から現在**へ。詳細数値は各 `docs/FA_S6_*` / `OFFSEASON_FA_*` を参照。

1. **buffer 10M / 30M 試行**: `_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER` の変更と playcheck（同期後 `gap` の収斂・行列の見え方に影響）。関連: `docs/FA_S6_BUFFER_*`、`docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_*`。
2. **λ 0 / 0.1 / 0.05 試行**: `_PAYROLL_BUDGET_CLIP_LAMBDA` と clip 後オファー分布。関連: `docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_*`。
3. **observer 強化（`tools/fa_offer_real_distribution_observer.py`）**
   - **population mode**（`--population-mode`、既定は従来どおり）。
   - **save-list**（`--save-list`）。
   - **one-line summary**（ヒストグラム前の要約行）。
   - **sync_observation**（before / sync1 / sync2 + buffer 表示）。
   - **reading_guide**（主軸＝before の明示）。
   - **user_team_snapshot**（user または fallback 1 チームの pre-sync 1 行）。
   - **formula 入力追加**（`league_level` / `market_size` / `popularity` / `sponsor_power` / `fan_base`）— **オフ後式の手計算用**。
   - 設計の背景: `docs/FA_OBSERVER_MATRIX_REDESIGN_PLAN_2026-04.md` 等。
4. **save 取得戦略**: 観測に使う save の条件整理（`docs/FA_OBSERVER_SAVE_SCREENING_2026-04.md`、`docs/FA_CLIP_COMPARE_SAVE_REQUIREMENTS_2026-04.md`、`docs/FA_BEFORE_AXIS_SAVE_PLAYCHECK_2026-04.md` 等）。
5. **10 人ロスター観測**: 意図的に薄いロスターでも **before `gap=0` 一色**になりうることが確認された（複数 save）。
6. **post-off save 観測**: `fa_gap_20260408_postoff_01.sav` 等。オフ後の **`payroll_budget` 再設定**が効いた状態で、**予算とロスター年俸の乖離**が顕在化。
7. **24,018,800 の式一致**: `user_team_snapshot` の属性を `_process_team_finances` と同じ式に入れると **厳密一致**（D2・下記属性で確認可能）。
8. **ここまでの意味**: clip や λ の前に、**入力側の `payroll_budget` が roster と無関係に低い**と、**観測上 room が出にくい**。**式のゲームデザイン上の扱い**が次のボトルネック。

---

## 7. 変更済みコードの要点（ファイル別）

| 領域 | ファイル | 何のためか（短く） |
|------|----------|-------------------|
| FA オファー・clip・診断 | `basketball_sim/systems/free_agency.py` | `_calculate_offer` / diagnostic、payroll room と clip の本丸ロジック。観測はここを読むが、**最近の「user CPU FA 除外」はここではなく season**。 |
| オフ締め・予算同期 | `basketball_sim/models/offseason.py` | `_process_team_finances` の **`payroll_budget` 再設定式**、`_sync_payroll_budget_with_roster_payroll`、buffer 定数。 |
| FA 観測 CLI | `tools/fa_offer_real_distribution_observer.py` | save／シミュ行列、**sync_observation**、**user_team_snapshot**（式入力5項目含む）、reading_guide。 |
| インシーズン CPU FA | `basketball_sim/models/season.py` | `_process_inseason_free_agency` で **user team を `run_cpu_fa_market_cycle` に渡さない**。 |
| 新規開始・user 差し替え | `basketball_sim/main.py` | `apply_user_team_to_league`、初期 money／市場定数など。 |
| 契約解除（FA 送り） | `basketball_sim/systems/roster_fa_release.py` | GUI/CLI 共通の解除適用・前提チェック。 |

（その他 GUI は `main_menu_view.py` 等。generator はロスター生成・初期年俸正規化。）

---

## 8. 追加済みテストの要約

| テスト（例） | 固定していること |
|--------------|------------------|
| `test_payroll_budget_roundtrip.py` | save→load で user の `payroll_budget`（と `money`）が不変。 |
| `test_payroll_budget_initial_timeline.py` | 新規開始フロー⑤直後も user `payroll_budget=120M` が維持される（normalize は選手年俸側）。 |
| `test_payroll_budget_after_offseason.py` | ⑦ `_process_team_finances` 後に式どおり `payroll_budget` が再計算される（D3 等の式ミラー）。 |
| `test_inseason_fa_user_team_exclusion.py` | CPU FA に **非 user のみ**が渡る。 |
| `test_roster_fa_release.py` / GUI 系 | 契約解除のガードと適用。 |
| `test_fa_offer_real_distribution_observer_population.py` | observer の集計・**user_team_snapshot 行**（式入力キーワード含む）。 |
| その他 | `test_free_agency_payroll_budget_clip.py`、`test_economy_r1_fa_payroll_trace.py`、`test_free_agency_offer_diagnostic.py`、`test_free_agency_negotiation.py` 等で FA 経済・clip・交渉を固定。 |

---

## 9. 現在のコード構造で重要な参照点（優先度順）

1. **`docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`** — オフ後 `payroll_budget` 式の読み下し（**式の正本**）。  
2. **`docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`** — before / sync の読み方（**観測の正本**）。  
3. **`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`** — `gap=0` の整理。  
4. **`basketball_sim/models/offseason.py`** — `_process_team_finances`（式の実装）、`_sync_payroll_budget_with_roster_payroll`。  
5. **`tools/fa_offer_real_distribution_observer.py`** — 実行時観測の入口。  
6. **`basketball_sim/systems/free_agency.py`** — offer / clip / diagnostic。  
7. **`docs/PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md`** / **`docs/PAYROLL_BUDGET_PERSISTENCE_CAUSE_NOTE_2026-04.md`** — 120M が残る経路の整理。  
8. **`docs/INSEASON_CPU_FA_USER_TEAM_EXCLUSION_DECISION_2026-04.md`** — CPU FA 除外の決裁。

---

## 10. 実測・観測で重要だった結果

**分類: 観測済み（特定 save／再現手順に依存）**

- **10 人ロスター save 複数本**: **before でも `gap=0` 一色**になりやすいことが確認された（入力構造の問題）。
- **post-off save**（例: `fa_gap_20260408_postoff_01.sav`）の **user_team_snapshot 相当の値**:
  - `league_level=2`
  - `market_size=1.2`
  - `popularity=49`
  - `sponsor_power=50`
  - `fan_base=5000`
  - `payroll_budget=24,018,800`
  - `roster_payroll=832,032,108`
  - `gap=0`
- **厳密一致**: 上記属性と **D2 の `base_budget=5,450,000`** で、`_process_team_finances` と同じ式を手計算すると **`payroll_budget=24,018,800` ちょうど**（`5_450_000 + 15_000 + 303_800 + 250_000 + 18_000_000`）。

**注（事実整理）**: `PAYROLL_BUDGET_FORMULA_CAUSE_NOTE` 内の **D3 の検算例**（同じ金額に届く別の属性の組）は、**「同じ数値の別解」**の例示。**実 save のスナップショットは上記 D2 セットで一致**する。

---

## 11. まだ未着手・未確定の論点

- **オフ後 `payroll_budget` 再設定式を今後どう扱うか**（roster 連動するか／目安のままか／カップ別か）— **未決裁**。**← 次の意思決定の中心**。
- **7 人ルール**変更 — **未着手・未決裁**（この式を直接は動かさない）。
- **clip 式・λ・buffer** の再設計 — **まだ本格手を入れる段階に入っていない**（観測・入力構造の整理が先行）。
- **FA 観測の進め方** — **budget 式の扱い決裁後**に最適化するのが自然。

---

## 12. 今の現在地

- **分かったこと**: 観測上の「before で room が出ない」現象は、**同期だけでなく**、**オフ後の `payroll_budget` が roster 規模と無関係に低い**ことと **`max(0,·)`** で整合する。**24,018,800** はバグではなく**式の出力**として説明できる（属性一致済み）。
- **ボトルネック**: **ゲームデザイン／式の扱い**（現状の式のままでは **D1/D2/D3 いずれも roster に対して予算が極端に低いケース**で gap が開かない）。
- **次の判断に必要なもの**: **式を変えるかどうか**の短い**決裁メモ**（目的・非目的・比較指標）。追加の大規模観測より先に、**方針の1行**が有効。

---

## 13. 次にやるタスク（1つだけ）

**オフ後 `payroll_budget` 再設定式を今後どう扱うかの短い決裁メモを `docs/` に1本作成する**（現状維持／roster 連動の有無／観測指標との関係を1〜2ページで固定）。

---

## 14. 次 chat へ渡す運用指示

| 項目 | 指示 |
|------|------|
| 最初に読むもの | 本ファイル §1–§5、§10、§13 → 必要に応じ §9 のリンク先 doc。 |
| 正本 doc | **観測軸**: `FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`。**式**: `PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md`。**タイムライン**: `PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md`。 |
| 動かしてはいけない結論 | §5 の決裁一覧（特に **before 主軸**、**CPU FA user 除外**、**24,018,800＝式の結果**の整理）。 |
| 再調査不要なこと | save/load が budget を壊す仮説、`money` 単独主因仮説（すでに切り分け済み）。 |
| 次の1手 | **§13 どおり**決裁メモ1本。 |

---

## 実行コマンド（健全性確認）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

## 抽出コマンド

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PROJECT_HANDOFF_MASTER_2026-04-08.md -Pattern "次にやるタスク|決裁|payroll_budget|user_team_snapshot|CPU FA|未確定"
```

---

## 改訂履歴

- 2026-04-08: 初版（引き継ぎ正本）。
