# Cursor 新Chat移行用 完全現状引き継ぎ書（2026-05-08）

**作成日**: 2026-05-08  
**最終本文同期**: **2026-05-11**（commit `a650444 ライセンス強制実機テスト結果を記録` 反映。**Phase 0 必須項目はすべて完了**）  
**用途**: ChatGPT 会話を新 Chat に切り替える際、Cursor 側から見たプロジェクトの**現在地・固定方針・コード構造・直近修正履歴・次にやるべきタスク**を 1 本で再現するための引き継ぎ正本。  
**位置づけ**: 既存の `docs/CURSOR_CHAT_HANDOFF_LATEST_2026-04.md` / `docs/PROJECT_HANDOFF_MASTER_2026-04-08.md` の系譜を引き継ぐ最新版。本文書は実装決定書ではなく、**新 Chat が同じ前提で 1 手目を踏み出すための地図**。  
**新 Chat への一言**: いきなり実装に飛ばず、§12 の「次にやるべきタスク」から **現状確認指示書** を切り出すこと。Phase 0 必須項目は 2026-05-11 までに完了済みなので、次は **Phase 4 / Godot 本番 GUI 実装準備**フェーズ（実コード着手前の docs 整合・情報設計メモのレビュー）から始める。

---

## 1. 冒頭サマリー

- 本文書は **新 Chat 移行用の Cursor 視点引き継ぎ書**である。
- 最新コミットは **`a650444 ライセンス強制実機テスト結果を記録`**（2026-05-11、**Phase 0 必須項目の最終完了 commit**）。
- `basketball_sim/` および `docs/` 配下の **追跡ファイル差分はない**想定（本文書のコミット直後）。
- `reports/*.txt` は **未追跡のまま**残っている（既知）。`.gitignore` 化はしておらず、運用ルールで「原則コミット対象外」。
- **Phase 0 必須項目は 2026-05-11 までに完了**（旧 Phase 0 残 5 項目：① ライセンス強制実機テスト ② セーブ README ③ ストア説明文への「セーブはローカル」明記 ④ クラッシュログ判断＋ Tk callback 例外フック ⑤ GHA 継続判断、すべて完了）。**継続管理項目**（v1 出荷判断の必須項目ではない）として `docs/PHASE0_COMPLETION_TEMPLATE.md` §5「ストア説明文への実績の有無明記」`[ ]` のみ残るが、Phase 0 必須残件ではなく別管理。詳細は `docs/PHASE0_COMPLETION_TEMPLATE.md` §2 冒頭 2026-05-11 追記・§4.2 残作業表・改訂履歴 2026-05-11。
- 次工程候補は **「Phase 4 / Godot 本番 GUI 実装準備」**（`docs/IMPLEMENTATION_PLAN_MASTER.md` §5.1 §11 ステップ 3、`docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` §0 が 2026-05-11 に着手前提を満たした旨を反映済み）。**Godot プロジェクトの実コード着手はまだしない**：実装着手判定はユーザー側の意思決定が別途必要。
- 仮 GUI（Tkinter）上の「リアリティ強化」一区切り＋**再契約・オークションドラフト履歴強化 小 PR** ＋ **Phase 0 必須項目すべて完了** まで終了。
- 直近の `python -m basketball_sim --smoke` は **`smoke ok`**。直近の全テスト（939+件）も all passed（Tk callback 例外フックの 3 件追加後も pass）。

---

## 2. 固定方針（新 Chat も継続）

- 会話とゲーム内表示は基本 **日本語**（コード・識別子・コミットメッセージは英語可）。
- ユーザーは初心者寄りなので、説明は **簡潔・丁寧**。
- 回答末尾に **「次に行うべき具体的タスク」を 1 つだけ**提示する（複数羅列しない）。
- **安定性・既存構造保護**を最優先（クラッシュ・セーブ破損・再現不能を最も恐れる）。
- 目標は **Steam で単価 1500 円・1 万本以上**を狙える高品質な国内バスケ GM ゲーム。
- Cursor 向け指示は **「1 撃最強指示書」形式**（コピー 1 回で完結）を優先。
- **`git add .` は使わない**（必ずファイル単位で `git add <file>`）。
- **`reports/*.txt` は原則コミット対象外**（`reports/` を `git add` しない）。
- ログ確認時は「**実行コマンド・出力先・抽出コマンド**」を 3 点セットで添える。
- **知ったかぶり禁止**。不明点は実装に飛ばず、まず現状確認指示書で事実確認する。
- **1 コミット 1 目的**。中規模以上の変更は調査→計画→完了条件→実装の順。
- ついで修正禁止（依頼されていない箇所を「ついでに」直さない）。
- **Cursor は実装役、ChatGPT は第二の開発統括、ユーザーは開発トップ**という三者役割。

---

## 3. プロジェクトの基本仕様

- **ジャンル**: 日本プロバスケを参考にした**実名ではない独自リーグ**の GM シミュレーション。
- **規模**: **48 クラブ** / **D1 / D2 / D3 の 3 部制** / **昇降格あり**。
- **進行**: **週次ラウンド進行**（1 チーム年間 60 試合目標）／代表ウィーク・天皇杯週・東アジアトップリーグ ノックアウト週はリーグ試合 0。
- **長期運営**: マルチシーズン周回が前提（CLI で長期周回確認可能、smoke あり）。
- **日本独自ルール**: 外国籍 3 枠 + アジア／帰化 1 枠、試合中外国籍オンザコート最大 2・アジア／帰化最大 1。`config/game_constants.py` の `LEAGUE_*_CAP` と `Match` / `RotationSystem` で運用。
- **試合先発**: `docs/MATCH_STARTING_LINEUP_RULES.md` 正本、`Match._resolve_match_starters` 実装。
- **GM 判断の核**: 契約・FA・トレード・ロスター・先発／ローテ・戦術・期限付き判断（regular_season_transaction_cutoff_round = R22 以降ロック）。
- **経営の核**: 財務・施設・スポンサー・広報・グッズ。施設プロジェクト制は将来課題。
- **長期プレイ要素**: クラブ史・引退・転生・ドラフト供給循環・アイコンプレイヤー基礎。
- **ドラフト**: Rookie Budget ドラフト（同時指名 + 競合時オークション）。最大 2 人（0 可）。基準上限 4000 万円、段階式ぜいたく税。`docs/DRAFT_AUCTION_SYSTEM.md` 正本。
- **オフシーズン**: 6 月第 1 週開始、6〜7 月を W1〜W8（`docs/OFFSEASON_WEEK_MODEL.md` 正）。8 月完全休養、9 月プレシーズン、10 月開幕。
- **最終到達点**: Steam 販売品質の **Godot 本番 GUI**。CLI / Tk は開発・確認用として残す。

---

## 4. 現在のロードマップ位置

### 仮 GUI（Tkinter）スコープでの進捗

```txt
◎ 基盤完成

★ リアリティ強化
  ◎ 経営メニュー改善
  ◎ 強化メニュー改善
  ◎ 人事・ロスター改善
  ◎ オフシーズン導線改善
  ◎ O-4：FA市場／ドラフト候補の閲覧専用整理
    ◎ O-4a：来年ドラフト候補の閲覧専用窓
    ◎ O-4b：FA市場の閲覧専用窓
  ◎ オフシーズン結果ハイライト
  ◎ Godot本番GUI向け情報設計メモ
  ◎ 最終ロードマップ／Steam配布前提／Phase 4着手条件の現状確認
  ◎ 再契約・オークションドラフト履歴強化 小PR
  ◎ Phase 0残の1件化（PRODUCT/Steam系docsとの整合確認を兼ねる）

★ Phase 0実作業（2026-05-08〜2026-05-11、すべて完了）
  ◎ セーブREADME（commit 48ecbaa）
  ◎ クラッシュログ判断（commit 4b2401b → b0a8f75 で Tk callback 例外フック追加）
  ◎ GHA継続判断（commit 44910f1、判定A：継続）
  ◎ ストア説明文への「セーブはローカル」明記（commit 7c0d7d6 → 8dec1f1 で実反映）
  ◎ ライセンス強制実機テスト（commit 1bce4c9 手順書 → a650444 実機結果記録）

★ 次工程
  ★ Phase 4 / Godot本番GUI実装準備（情報設計メモのレビュー、データ正本化の境界整理、Tk並走ルール再確認）
  □ Godot本番GUI実装（着手判定はユーザー意思決定が別途必要）
  □ グラフィック・音楽などの演出実装
  □ 完成・ブラッシュアップ・公開準備
  □ リリース・販売展開

☆ 継続管理項目（v1出荷判断の必須項目ではない／Phase 0必須残件ではない）
  □ ストア説明文（日本語）への「実績の有無」明記（パートナー画面）
```

### `docs/PRODUCT_ROADMAP_AND_VISION.md` 上の Phase 表との関係

- PRODUCT 上の **Phase 0 必須項目は 2026-05-11 に完了**（`docs/PRODUCT_ROADMAP_AND_VISION.md` Phase 0 節「◎ 必須項目は 2026-05-11 までに完了」、`docs/PHASE0_COMPLETION_TEMPLATE.md` §2 冒頭 2026-05-11 追記、commit `a650444` まで）。**Phase 0 ★ の現在地表示は外れた**。
- 仮 GUI スコープの「リアリティ強化」一区切りは、PRODUCT の Phase 1〜3 領域での読み取り導線を埋めた段階。
- 直近完了した **再契約・オークションドラフト履歴強化 小 PR**（commit `a807988`）は、`team.history_transactions` の正本データを 2 種類（`resign` / auction `draft`）追加し、Godot 移行時の正本表（GODOT メモ §10）を埋めた中間タスク。
- `docs/IMPLEMENTATION_PLAN_MASTER.md` §3 は「**Godot 全面移行を計画の主戦場にしない**／データ正本化のみ中間タスクで可」と明記。**この方針は維持**したまま、§5.1 / §11 ステップ 3 が **Phase 4 / Godot 本番 GUI 実装準備**（実コード着手前の docs 整合・情報設計メモのレビュー）に移行した（2026-05-11 同期）。
- 従って **Phase 4 / Godot 本実装の着手判定**はユーザー側の意思決定が別途必要だが、**前提条件としての Phase 0 必須項目はすべて満たされた**。次工程候補は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` §0「本実装着手の前提」（2026-05-11 時点で前提を満たした旨を反映済み）と §10「データ正本一覧」のレビュー、または **継続管理項目**（実績の有無表記）の別タスク化を推奨。

---

## 5. 最新実装状態：補助枠と閲覧窓

### 補助枠は 2 列グリッド（左メニュー下）

```txt
[オフの流れ]    [来年候補]
[FA市場]        [直近オフ]
[デバッグ: オフシーズンまで飛ばす]   ※デバッグ有効時のみ2列幅
```

- 実装: `basketball_sim/systems/main_menu_view.py` の `aux_buttons_frame`（`columnconfigure(0/1, weight=1)`、`grid` レイアウト）。
- ボタンテキストは省略形（「オフシーズンの流れを見る」→「オフの流れ」など）。
- デバッグボタンは `columnspan=2` で 2 列幅、有効時のみ表示。
- `MENU_ITEMS` は 9 項目（`["日程", "人事", "クラブ案内", "経営", "強化", "戦術", "情報", "歴史", "システム"]`）。

### ボタンごとの内容

#### オフの流れ（O-3）

- **目的**: オフシーズンの流れ説明窓。
- **データ源**: `OFFSEASON_PHASES`（`basketball_sim/systems/offseason_phases.py`）+ `build_offseason_focus_summary`（`offseason_progress_cli_display.py`）。
- **形式**: 閲覧専用 Toplevel + ScrolledText、「閉じる」ボタン、`WM_DELETE_WINDOW` ハンドラ。

#### 来年候補（O-4a）

- **目的**: 来年ドラフト候補の閲覧専用窓。
- **データ源優先順**:
  1. `team.league_future_draft_pool`
  2. `season.all_teams` / `season.leagues` / `_iter_league_teams` からのフォールバック
- **表示用ソート**: POT → OVR → 年齢 → 名前。
- **不変性**: 元リストは非破壊（コピーしてからソート）。
- **テスト**: `basketball_sim/tests/test_future_draft_pool_readonly_window.py`。

#### FA 市場（O-4b）

- **目的**: FA 市場の閲覧専用窓（**獲得・契約操作ボタンなし**）。
- **データ源優先順**:
  1. `Season.free_agents`
  2. `self.free_agents` / `self.team.free_agents` フォールバック
- **表示用ソート**: OVR → POT → 年齢 → 名前。
- **不変性**: 元リスト非破壊。
- **テスト**: `basketball_sim/tests/test_fa_market_readonly_window.py`。

#### 直近オフ（オフシーズン結果ハイライト）

- **目的**: ユーザーチームの**既存データだけ**を読み取り表示する閲覧専用窓。
- **データ源**:
  - `team.history_transactions`（FA / 解除 / トレード / **再契約**(`resign`) / **ドラフト**(通常 + auction)）
  - `team.finance_history` + フォールバックで `revenue_last_season` / `expense_last_season` / `cashflow_last_season` / `money`
  - `team.history_milestones`（昇降格・受賞）
  - `team.players` の `acquisition_type` / `acquisition_note` / `is_draft_rookie_contract` / `draft_rookie_locked_salary`
  - `player.career_history` の Re-sign / Contract Extension / Contract Expired
- **`wanted_types`（recap 表示対象 type）**: `{"free_agent", "trade", "release", "draft", "resign"}`。`type_label` には `"resign": "再契約"` を含む。
- **過去の弱点と直近の解消（commit `a807988`）**:
  - 旧: `apply_resign` は `player.career_history` に Re-sign を残すが、**`team.history_transactions` には行を残していなかった**。  
    → 解消: `apply_resign` 末尾で `_record_team_resign_history` を呼び、`transaction_type="resign"` 行を 1 件追加するようにした。
  - 旧: `draft_auction.py` の `conduct_auction_draft` は `_set_drafted_player_contract` で player 側 acquisition のみ設定し、**`team.history_transactions` 行を残していなかった**。通常ドラフト（`draft.py` の `_record_team_draft_history`）と非対称だった。  
    → 解消: 一本釣り（`[DRAFT-ONEPICK]`）と競合落札（`[DRAFT-WIN]`）の 2 箇所で `_record_team_auction_draft_history` を呼び、`transaction_type="draft"` で通常ドラフトと同型の行を残すようにした。
  - **save 構造変更なし**（既存スキーマで吸収）。`Offseason.run()` 順序変更なし。既存ロジック変更なし。
- **テスト**: `basketball_sim/tests/test_offseason_result_recap_readonly_window.py`（13 件、`_format_offseason_result_recap_text` の Tk 非依存テスト。新規 2 件: resign / auction draft の表示確認）。

### 閲覧窓パターンの共通設計

- Tk 非依存の `_format_*_text(team=..., season=...) -> str` を分離。
- `_open_*_window` は Toplevel + ScrolledText + 「閉じる」ボタンに徹し、テキスト生成は委譲。
- **元リスト非破壊**（コピーしてソート）。
- Godot 移行時は `_format_*_text` のロジックを Godot 側 UI のデータ整形に流用しやすい設計。

---

## 6. 直近コミット履歴

```txt
a807988 再契約とオークションドラフトの履歴記録を追加
f8898a7 Godot本番GUI向け情報設計メモを追加
154c114 直近オフ振り返り窓と補助ボタン配置を整理
daef1e2 FA市場の閲覧専用窓を追加
f350859 来年ドラフト候補窓と補助ボタン配置を整理
ac45948 オフシーズンの流れ説明窓を追加
2698dae 特別指定選手のGUI既定選択を追加
db72d5b オフシーズン進行ヒントとスカウトGUI既定選択を整理
330bf9a 人事メニューに契約満了候補を表示
756f9f6 人事メニューのロスター表表示を整理
```

これより古いコミットは、フェーズ要約として §4 ロードマップ位置の「リアリティ強化」配下にまとめている（経営メニュー改善・強化メニュー改善・人事/ロスター改善・オフシーズン導線改善 など）。詳細は `git log --oneline` を参照。

### 直近コミット `a807988` の中身（再契約・オークションドラフト履歴強化 小 PR）

- **目的**: `team.history_transactions` の正本データに 2 種類の欠落履歴を追加し、Godot 移行時の正本表（GODOT メモ §10）を埋める。
- **変更ファイル（6 件）**:
  - `basketball_sim/systems/contract_logic.py`：`_record_team_resign_history` 追加。`apply_resign` 末尾で呼び、ドラフトルーキー早期 return 時を除き `transaction_type="resign"` を 1 行記録。
  - `basketball_sim/systems/draft_auction.py`：`_record_team_auction_draft_history` 追加。一本釣り（`[DRAFT-ONEPICK]`）と競合落札（`[DRAFT-WIN]`）の 2 箇所で `transaction_type="draft"` を 1 行記録。`note` に "auction_draft / slot / OVR / POT / 落札額" を含めて通常ドラフトと同型化。
  - `basketball_sim/systems/main_menu_view.py`：`_format_offseason_result_recap_text` の `wanted_types` に `"resign"` を追加、`type_label` に `"resign": "再契約"` を追加し、再契約行を「・再契約: <名前> と再契約（<note>）」形式で表示。
  - `basketball_sim/tests/test_offseason_result_recap_readonly_window.py`：再契約 / オークションドラフトが recap に表示されることを 2 件追加。
  - `basketball_sim/tests/test_contract_resign_history.py`（新規）：`apply_resign` が `team.history_transactions` に 1 行追加すること、ドラフトルーキー時は追加しないこと等 4 件。
  - `basketball_sim/tests/test_draft_auction_team_history.py`（新規）：`_record_team_auction_draft_history` の単体動作と recap 連携 4 件。
- **不変条件**: save 構造変更なし。`Offseason.run()` 順序変更なし。既存ロジック変更なし。
- **検証**:
  - 焦点テスト 79 passed
  - 全テスト 939 passed
  - `python -m basketball_sim --smoke` → `smoke ok`
  - 自動 CLI スクリプトでフルオフシーズンを走らせ、`[RE-SIGN]` ログ・`team.history_transactions` 内 `resign` 行・recap 表示まで実データで確認

---

## 7. 重要ファイル一覧

### コード（`basketball_sim/`）

| パス | 役割 |
|------|------|
| `basketball_sim/systems/main_menu_view.py` | Tk 仮 GUI のメインメニュー本体。補助枠 2 列・閲覧窓 4 種・各メニュータブを保有。 |
| `basketball_sim/main.py` | エントリポイント。`advance_one_round` でシーズン／オフシーズンを駆動。 |
| `basketball_sim/models/offseason.py` | `Offseason.run()` がオフ全フェーズを駆動。`re_signed_player_ids` で再契約追跡、`_decrease_contracts` で契約満了→FA、`_offer_cpu_contract_extensions`、`conduct_auction_draft` 呼び出し。 |
| `basketball_sim/models/season.py` | シーズン進行と `_process_promotion_relegation`。昇降格は `_record_competition_team_result` 経由で `team.history_milestones` に記録。 |
| `basketball_sim/models/team.py` | `history_transactions` / `finance_history` / `history_milestones` の API（`add_history_transaction` / `record_financial_result` / `add_history_milestone`）。`cashflow_last_season` / `money` 等の財務フィールド。`print_history()`（CLI）。 |
| `basketball_sim/models/player.py` | `career_history`（`add_career_entry`）。`acquisition_type` / `acquisition_note` / `is_draft_rookie_contract` / `draft_rookie_locked_salary`。 |
| `basketball_sim/systems/free_agency.py` | `conduct_free_agency` 内で `_record_team_fa_history` → `team.add_history_transaction("free_agent", ...)` を実行（FA 側は履歴記録あり）。 |
| `basketball_sim/systems/free_agent_market.py` | FA 市場側のデータ管理／FA プール構築。 |
| `basketball_sim/systems/draft.py` | 通常ドラフト本体。`_record_team_draft_history` で `team.history_transactions` に "draft" 行を記録。 |
| `basketball_sim/systems/draft_auction.py` | オークションドラフト本体。`_set_drafted_player_contract` で player 側 acquisition 系を設定し、`_record_team_auction_draft_history` で `team.history_transactions` に "draft"（note に "auction_draft" を含む）行を記録（commit `a807988` で対称化済み）。 |
| `basketball_sim/systems/contract_logic.py` | `apply_resign` / `apply_contract_extension` / `release_expired_players_to_fa` / `get_expiring_players`。`apply_resign` は player.career_history に Re-sign を残し、さらに `_record_team_resign_history` で `team.history_transactions` に "resign" 行も記録（commit `a807988` で追加）。 |
| `basketball_sim/systems/team_tactics.py` | 戦術系の正本。`team.tactics` を介する。 |
| `basketball_sim/systems/offseason_phases.py` | `OFFSEASON_PHASES` 定義。 |
| `basketball_sim/systems/offseason_progress_cli_display.py` | `build_offseason_focus_summary` 等、オフ説明用ビルダ。 |

### ドキュメント（`docs/`）

| パス | 役割 |
|------|------|
| `docs/PRODUCT_ROADMAP_AND_VISION.md` | Phase 0〜6 ・ドラフト・日程・製品ビジョンの正本。Phase 0 ★ 現在地。 |
| `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md` | Steamworks 再開状況・最終本文同期 2026-04-06。`--steam-diag` 初期化成功確認、SteamPipe default、実績 ACH_PHASE0_TEST 解除確認。 |
| `docs/PHASE0_COMPLETION_TEMPLATE.md` | Phase 0 完了チェックリスト。配布・SDK 系は `[x]`、**ライセンス強制実機テスト・セーブ README・ストア「セーブはローカル」明記・クラッシュログ判定・GHA 継続が `[ ]`** 残。 |
| `docs/IMPLEMENTATION_PLAN_MASTER.md` | Phase A〜D の実装順正本。**直近最優先は §5.1「Phase 0 残の 1 件化（実作業候補 5 項目の整理）」**（2026-05-08 同期）。旧「Steam 関連正本 docs の同期確定」は §11 ステップ 0 へ「2026-04-06 完了済み」として移動。Godot は主戦場外と明記。 |
| `docs/CURRENT_STATE_ANALYSIS_MASTER.md` | 現状分析正本。Phase 0 ★ 現在地、tk 主画面 △、`.py` 約 120 本。 |
| `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` | Godot 移行に向けた情報設計メモ（前タスクで追加）。13 章＋付録 A/B。データ正本表、画面優先順、後工程、移行時に壊さないもの等。 |
| `docs/TACTICS_MENU_FULL_HANDOFF_2026-04.md` | 戦術メニュー引き継ぎ書。 |
| `docs/HIGHLIGHT_MODE_SPEC.md` | ハイライト／結果だけモードの正本（Phase 4 関連）。 |
| `docs/MATCH_STARTING_LINEUP_RULES.md` | 試合先発ルール正本。 |
| `docs/DRAFT_AUCTION_SYSTEM.md` | ドラフト制度正本。 |
| `docs/OFFSEASON_WEEK_MODEL.md` | オフシーズン週モデル正本。 |
| `docs/PLAYER_GRAPHICS_DESIGN.md` | 2D 選手グラフィック正本。 |
| `docs/GUI_*_ENTRY_POLICY.md`（複数） | 1 対 1 / multi / インシーズン FA / FA 契約 / 本格 FA 市場の入口ポリシー。 |

### テスト（参考）

| パス | 範囲 |
|------|------|
| `basketball_sim/tests/test_offseason_result_recap_readonly_window.py` | 直近オフ振り返り窓のテキスト生成 13 件（commit `a807988` で resign / auction draft 表示の 2 件を追加）。 |
| `basketball_sim/tests/test_fa_market_readonly_window.py` | FA 市場閲覧窓のテキスト生成。 |
| `basketball_sim/tests/test_future_draft_pool_readonly_window.py` | 来年ドラフト候補窓のテキスト生成。 |
| `basketball_sim/tests/test_offseason_flow_overview_window.py` | オフの流れ説明窓のテキスト生成。 |
| `basketball_sim/tests/test_contract_resign_history.py` | `apply_resign` の `team.history_transactions` 記録（commit `a807988` で新規 4 件）。 |
| `basketball_sim/tests/test_draft_auction_team_history.py` | `_record_team_auction_draft_history` の単体動作と recap 連携（commit `a807988` で新規 4 件）。 |

最新スナップショットでは全テスト **939 件 passed**、`smoke ok`。

---

## 8. データ正本一覧（Godot 移行用に固定）

| 機能 | 正本 |
|------|------|
| ロスター | `team.players` |
| FA 市場 | `Season.free_agents`（フォールバック: `team.free_agents`） |
| 来年ドラフト候補 | `team.league_future_draft_pool`（フォールバック: `Season` 経由 `_iter_league_teams`） |
| 当年ドラフト候補 | `Offseason.draft_pool` |
| 契約満了候補 | `contract_logic.get_expiring_players` |
| オフシーズン流れ | `OFFSEASON_PHASES` + `build_offseason_focus_summary` |
| 直近オフ振り返り | `team.history_transactions` / `team.finance_history` / `team.history_milestones` / `player.acquisition_type` / `player.career_history` |
| 財務 | `team.finance_history` / `team.cashflow_last_season` / `team.revenue_last_season` / `team.expense_last_season` / `team.money` |
| 昇降格 | `Season._process_promotion_relegation` + `team.history_milestones` |
| 戦術 | `team_tactics` / `team.tactics` |
| 強化 | training 関連フィールド（`Player` 側の `training_*` / `_apply_training_effect` 等） |

詳細は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` §10 を参照。

---

## 9. Godot 実装中のゲーム性改善ルール

### 基本方針

```txt
Godot 実装に入った後でもゲーム性向上は並行してよい。
ただし、Godot 側は表示・操作層として扱い、ゲームの正本ロジックは既存 Python 側に残す。
Python 側と Godot 側で同じ処理を二重実装しない。
```

### 安全に並行できるもの

- 選手データ追加
- 能力値バランス調整
- 新人 / ドラフト候補データ調整
- 経営メニューの収支 / 施設 / スポンサー / 広報 / グッズ改善
- 強化メニューの育成効果 / 練習内容 / 表示改善
- FA / ドラフト / 契約 / 戦術のゲーム性改善
- 試合バランス調整

### 注意が必要なもの

- save 構造変更
- `Player` / `Team` / `Season` の根本変更
- `Offseason.run()` の大改造
- Godot 画面都合でロジックを直接書き換えること
- Python 側と Godot 側で同じ処理を二重実装すること

### 運用ルール

- A（Godot ライン）と B（ゲーム性改善ライン）を分ける。
- 片方が大きく動くとき、もう片方は同週内で**小変更に留める**。
- **1 コミット 1 目的**。
- **save 構造変更は別 PR・別週**で扱う（`format_version` と移行フックの方針を遵守）。
- 表示用データは「モデル → DTO/表示 dict → UI」の順に正本化（将来の JSON 化に備える）。
- バランス係数変更は `.github/workflows/balance-guard.yml`（heavy）成功を必須判定とする（PRODUCT Phase 1）。

---

## 10. Steam / Phase 0 / Phase 4 の現状

### 仮 GUI スコープと PRODUCT の整合（2026-05-11 同期）

- 仮 GUI 上のリアリティ強化・補助導線・Godot 情報設計は **一区切り完了**。
- **Phase 0 必須項目は 2026-05-11 までに完了**（`docs/PRODUCT_ROADMAP_AND_VISION.md` Phase 0 節「◎ 必須項目は 2026-05-11 までに完了」、`docs/IMPLEMENTATION_PLAN_MASTER.md` §5.1 §11 ステップ 1〜2、`docs/PHASE0_COMPLETION_TEMPLATE.md` §2 冒頭 2026-05-11 追記）。
- 次工程は **Phase 4 / Godot 本番 GUI 実装準備**（実コード着手前の docs 整合・情報設計メモのレビュー）。**Godot プロジェクトの実コード着手はまだしない**（`docs/IMPLEMENTATION_PLAN_MASTER.md` §3「Godot 全面移行は本計画の主戦場にしない」方針を維持）。

### Phase 0 必須項目の完了内訳（2026-05-11）

- ① **ライセンス強制実機テスト** — 完了（commit `a650444`、`docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md` §7 判定表に Case A／B／C を記録）
- ② **セーブ README** — 完了（commit `48ecbaa`、ルート `README.md` §「Steam 版を遊ぶ前に（ユーザー向け）」§A〜§E 追加）
- ③ **ストア説明文への「セーブはローカル」明記** — 完了（commit `8dec1f1`、Steam パートナー画面へ反映済み）
- ④ **クラッシュログ判断 ＋ Tk callback 例外フック追加** — 完了（commit `b0a8f75`、`install_tk_callback_excepthook(root)` 追加・`MainMenuView` / `SpectateView` で適用）
- ⑤ **GHA 継続判断** — 完了（commit `44910f1`、判定 A：継続）

### Phase 0 で **済**（Phase 0 必須項目完了に至るまでの蓄積）

- PyInstaller / SteamPipe / `steam_appid.txt` 運用 / 実績 `ACH_PHASE0_TEST` 解除確認
- `--steam-diag` 初期化成功（環境依存）
- クラウドセーブ／Rich Presence は v1 対象外（2026-04-05 決定）
- セーブ・ビルド・Steam 主要 docs 相互同期（2026-04-06）／Steam 関連正本 docs の同期確定
- 上記 ①〜⑤ の 5 項目（2026-05-08〜2026-05-11）

### 継続管理項目（v1 出荷判断の必須項目ではない／Phase 0 必須残件ではない）

- **ストア説明文（日本語）への「実績の有無」明記** — 未反映（`[ ]`）。`basketball_sim/config/steam_achievements.py` の登録状況とパートナー画面の実績ダッシュボードを照合する別タスクとして、Phase 4 検討と並行して別途進める。
- **パートナー画面側の人間作業**: ストア一般公開、最終「発売」審査、税務・本人確認の現在表示確認。`docs/PHASE0_COMPLETION_TEMPLATE.md` §4.3 で別管理。

### Steam 販売品質として不足／未確認（Phase 4 領域）

- 本番 GUI（Godot）
- 見た目 / 演出
- BGM / SE
- チュートリアル
- 長期飽き対策

---

## 11. 既知の後工程・未着手課題

### A. Godot 前に小 PR で価値あり

- ~~再契約結果を `team.history_transactions` に 1 行追加（`apply_resign` 経由）~~ → **commit `a807988` で対応済み**
- ~~オークションドラフト結果を `team.history_transactions` に 1 行追加（`draft_auction.py` 経由、`draft.py` 側 `_record_team_draft_history` の対称化）~~ → **commit `a807988` で対応済み**
- ~~直近オフ振り返り窓で上記履歴を拾う~~ → **commit `a807988` で対応済み**（`_format_offseason_result_recap_text` の `wanted_types` / `type_label` 更新）
- 残候補（必要があれば次の小 PR 候補）：
  - 直近オフ振り返り窓の disclaimer 文の見直し（`a807988` 反映で「再契約・オークションドラフトは履歴に出ない」前提が崩れたため、文言の最終調整は別 PR でも可）
  - 当年ドラフト候補ビュー（Offseason 中限定の閲覧窓）の追加

### B. Godot 実装中でもよい

- 正式メニュー配置の現状確認（Tk を整えすぎず、Godot で正式化する選択肢）
- クラブ史との完全統合

### C. Godot 後 / 後工程

- FA / ドラフト / 直近オフの検索・絞り込み
- 選手検索 / スカウトセンター
- オフシーズン処理中のプログレス表示（`Offseason.run()` の分割が必要）
- オフシーズン中断 / 再開（save 拡張必要）

### D. 設計相談が必要

- 施設プロジェクト制（経営本実装の設計論点整理 / IMPLEMENTATION_PLAN §5.2）
- 代表イベントの理想設計との接続
- ハイライトの尺・演出の最終仕様

### E. Phase 0 残（doc・運用） — **2026-05-11 までに必須項目すべて完了**

- ~~ライセンス強制実機テスト~~ → 完了（commit `a650444`）
- ~~セーブ README~~ → 完了（commit `48ecbaa`）
- ~~ストア「セーブはローカル」明記~~ → 完了（commit `8dec1f1`、Steam パートナー画面反映済み）
- ~~クラッシュログ判断~~ → 完了（commit `b0a8f75`、Tk callback 例外フックも追加）
- ~~GHA 継続判断~~ → 完了（commit `44910f1`、判定 A：継続）
- ストア一般公開・最終「発売」審査 → **パートナー画面側人間作業として `docs/PHASE0_COMPLETION_TEMPLATE.md` §4.3 で別管理**（Phase 0 必須残件ではない）
- 継続管理項目: ストア説明文（日本語）への「実績の有無」明記 → **v1 出荷判断の必須項目ではないため Phase 0 必須残件ではない**

---

## 12. 次にやるべきタスク

### 次にやるべき具体的タスク（1 つだけ）

```txt
Phase 4 / Godot 本番 GUI 実装準備（実コード着手前の docs 整合・情報設計メモのレビュー）の 1 件目を選ぶ。
（推奨: docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md §10「データ正本一覧」と §9「Godot 実装中のゲーム性改善ルール」の再レビュー）
```

### 直前タスクの確認結果（2026-05-11 Phase 0 完了確認 PR 反映後）

- **Phase 0 必須項目はすべて完了**（旧 Phase 0 残 5 項目を 2026-05-08〜2026-05-11 の連続 PR で消化、最終 commit `a650444`）。
- `docs/IMPLEMENTATION_PLAN_MASTER.md` §5.1 を **Phase 4 / Godot 本番 GUI 実装準備**（docs 同期・情報設計メモのレビュー・データ正本化の境界整理・Tk 並走ルール再確認）へ更新。§11 を 6 ステップ構成（ステップ 0〜2 完了済み、ステップ 3「Phase 4 / Godot 本番 GUI 実装準備」が現在地）へ更新。§12 も Phase 4 準備タスクへ更新。
- `docs/PRODUCT_ROADMAP_AND_VISION.md` Phase 0 節を **◎ 必須項目は 2026-05-11 までに完了** へ更新。最終ロードマップ照合日を **2026-05-11** に更新。Phase 0 ★ の現在地表示は外れた。
- `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §1（現在の開発段階）・§2（ロードマップ上の位置）・§6（直近修正履歴表に 9 件追加）・§8.1 を **Phase 0 必須完了／Phase 4 準備** へ更新。
- `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` §0「本実装着手の前提」を **2026-05-11 時点で前提を満たした** へ更新。
- `docs/PHASE0_COMPLETION_TEMPLATE.md` は commit `a650444` で §3 ランタイム「ライセンス」`[x]` 化・§4.2 #1 完了化・§2 冒頭 2026-05-11 追記・改訂履歴 2026-05-11 追加まで完了済み。

### Phase 0 必須項目（完了内訳）

| # | 項目 | 完了 commit | 種別 |
|---|------|--------------|------|
| 1 | ライセンス強制実機テスト | `a650444`（2026-05-11） | 実機作業＋ docs |
| 2 | セーブ README | `48ecbaa`（2026-05-08） | docs のみ |
| 3 | ストア説明文への「セーブはローカル」明記 | `8dec1f1`（2026-05-09、Steam パートナー画面反映済み） | 人間作業＋ docs |
| 4 | クラッシュログ判断 ＋ Tk callback 例外フック追加 | `b0a8f75`（2026-05-08、coverage 3 件追加） | コード＋ docs |
| 5 | GHA 継続判断（判定 A：継続） | `44910f1`（2026-05-08） | CI 棚卸し＋ docs |

### 継続管理項目（v1 出荷判断の必須項目ではない／Phase 0 必須残件ではない）

- ストア説明文（日本語）への「実績の有無」明記（`docs/PHASE0_COMPLETION_TEMPLATE.md` §5 `[ ]`）

### その際の注意

- **1 タスク 1 PR**。複数項目を 1 コミットに混ぜない。
- **`docs/PHASE0_COMPLETION_TEMPLATE.md` §5「実績の有無」`[ ]` は継続管理項目として保持**（`[x]` 化しない）。
- **Godot プロジェクトの実コード着手はまだしない**。Phase 4 準備フェーズは docs 整合・情報設計メモのレビューが主目的。実装着手判定はユーザー側の意思決定が別途必要。
- `reports/*.txt` をコミットしない。`git add .` を使わない。
- **不変条件**: save 構造変更なし、コア Player/Team/Season ロジック変更なし、`Offseason.run()` 順序変更なし。

### 完了条件（次タスク）

- 選んだ Phase 4 準備項目（情報設計メモのレビュー結果・データ正本表の差分など）が `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` または隣接 docs に反映され、Godot 着手判定の前提条件がさらに明確化される。
- 既存テスト維持・smoke ok（Phase 0 必須完了時点の `939+ 件 all passed` を維持）。

### 旧版（履歴メモ）

- 旧 §12 は「Phase 0 残の 1 件化（PRODUCT/Steam 系 docs との整合確認を兼ねる）現状確認」指示書を作る、という現状確認段階の指示だった。**2026-05-08 の docs 同期 PR で確認結果を 4 docs に反映済み**のため、本 §12 は実作業フェーズへ進んだ。

---

## 付録 A. 主要コマンド早見

### git 状態確認

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
git status --short
git log -1 --oneline
git diff --name-only
git log --oneline -10
```

### 健全性確認

```powershell
python -m basketball_sim --smoke
```

ログを残す場合：

```powershell
python -m basketball_sim --smoke *> reports/<タスク名>_smoke.txt
Select-String -Path reports/<タスク名>_*.txt -Pattern "FAILED","ERROR","Traceback","AssertionError","TclError","readline"
```

### 4 閲覧窓テスト

```powershell
python -m pytest basketball_sim/tests/test_offseason_result_recap_readonly_window.py basketball_sim/tests/test_fa_market_readonly_window.py basketball_sim/tests/test_future_draft_pool_readonly_window.py basketball_sim/tests/test_offseason_flow_overview_window.py -q --tb=short
```

### コード探索（次工程の現状確認に使う）

```powershell
rg -n "apply_resign|apply_contract_extension|conduct_auction_draft|_set_drafted_player_contract|_record_team_draft_history|_record_team_fa_history|_record_team_resign_history|_record_team_auction_draft_history|add_history_transaction" basketball_sim
```

### docs 整合確認（次工程の現状確認に使う）

```powershell
rg -n "Phase 0|Steamworks|Steam 配布|セーブ README|ライセンス強制|GHA" docs/PRODUCT_ROADMAP_AND_VISION.md docs/IMPLEMENTATION_PLAN_MASTER.md docs/CURRENT_STATE_ANALYSIS_MASTER.md docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md docs/PHASE0_COMPLETION_TEMPLATE.md
```

---

## 付録 B. 関連ドキュメント

- `docs/PRODUCT_ROADMAP_AND_VISION.md`（Phase 正本）
- `docs/IMPLEMENTATION_PLAN_MASTER.md`（実装順正本）
- `docs/CURRENT_STATE_ANALYSIS_MASTER.md`（現状分析正本）
- `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`（Steam 再開状況）
- `docs/PHASE0_COMPLETION_TEMPLATE.md`（Phase 0 完了チェックリスト）
- `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md`（Godot 情報設計メモ）
- `docs/CURSOR_CHAT_HANDOFF_LATEST_2026-04.md`（旧引き継ぎ正本・FA payroll budget 関連の記録）
- `docs/PROJECT_HANDOFF_MASTER_2026-04-08.md`（旧プロジェクト引き継ぎ正本）
- `docs/TACTICS_MENU_FULL_HANDOFF_2026-04.md`（戦術メニュー引き継ぎ）
- `docs/HIGHLIGHT_MODE_SPEC.md`（Phase 4 ハイライト正本）
- `docs/MATCH_STARTING_LINEUP_RULES.md`（試合先発正本）
- `docs/DRAFT_AUCTION_SYSTEM.md`（ドラフト制度正本）
- `docs/OFFSEASON_WEEK_MODEL.md`（オフ週モデル正本）
- `docs/SEASON_SCHEDULE_MODEL.md`（シーズン日程正本）

---

**最終確認**: **2026-05-11**（commit `a650444 ライセンス強制実機テスト結果を記録` 反映後、**Phase 0 必須項目すべて完了**の最終棚卸し PR 反映後）。本文書は新 Chat 移行用のスナップショットであり、コード・ロジック・save 構造を変更していない。次のアクションは **§12 の「Phase 4 / Godot 本番 GUI 実装準備の 1 件目」を選ぶこと**（実コード着手前の docs 整合・情報設計メモのレビュー段階）。Godot プロジェクトの実コード着手はまだしない（実装着手判定はユーザー側の意思決定が別途必要）。

### 改訂履歴（本文書）

- 2026-05-08: 新規作成（commit `a807988 再契約とオークションドラフトの履歴記録を追加` 反映、次工程を Phase 0 残の 1 件化へ切替）。
- 2026-05-08: commit `5aeaf81 新Chat引き継ぎ書を最新状態へ更新` で本文書を git 追跡へ。
- 2026-05-11: **Phase 0 必須項目完了スナップショットへ更新**。ヘッダ「最終本文同期」を 2026-05-11（commit `a650444`）へ、§1 冒頭サマリーを「Phase 0 必須項目は 2026-05-11 までに完了／次工程は Phase 4 / Godot 本番 GUI 実装準備」へ更新。§4 進捗ツリーに **Phase 0 実作業（5 項目すべて ◎）** を追加、次工程の ★ を Phase 4 / Godot 本番 GUI 実装準備へ移動、継続管理項目（実績の有無表記）を ☆ 別管理として明記。§10 を「Phase 0 必須完了の内訳」「継続管理項目」「Phase 4 領域」に再構成。§11 E を完了取り消し線へ。§12 を Phase 4 準備タスクへ更新（直前タスクの確認結果に 2026-05-11 反映、Phase 0 必須項目の完了表、継続管理項目を明記）。本文書「最終確認」を 2026-05-11／`a650444` へ更新。**コード差分・README 差分・workflow 差分ゼロ、docs 差分のみ**。
