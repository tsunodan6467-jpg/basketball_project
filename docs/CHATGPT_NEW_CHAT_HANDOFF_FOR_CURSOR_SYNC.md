# ChatGPT 新チャット ↔ Cursor 現状同期用（正本）

**最終更新**: 2026-04-01（本ファイルの作成日。以降の変更があれば日付と要約を追記すること）  
**用途**: 新しい ChatGPT チャットを開いたとき **このファイルを最初に貼る**（またはリポジトリ上で共有し「このパスを読め」と指示する）。Cursor 側の認識とズレないよう、**事実ベース**で統合した。  
**注意**: 本書は「引き継ぎ用の要約正本」である。**詳細仕様の正本**は各専用 `docs/`（例: `PRODUCT_ROADMAP_AND_VISION.md`、`SCHEDULE_MENU_SPEC_V1.md`）に残る。食い違いがあれば **コードと専用 doc を優先**し、本書を更新する。

---

## 1. このファイルの目的

- **何のためか**: 新チャットの AI が、**いまどこまで進んでいるか・何が直っているか・何が残るか・次に何をすべきか・どんなルールで動くか**を、**1 本で概ね正確に**掴むため。
- **どう使うか**: 新チャットの冒頭で本ファイルを渡し、必要なら「直近の issue / 違和感」だけ追加で書く。Cursor では `.cursorrules` と `docs/AI_WORKFLOW_RULES.md` が自動参照されやすいが、**ChatGPT 側には本ファイルがブリッジ**になる。
- **同期の意味**: 「ChatGPT で話した内容」と「Cursor で実装した内容」の **単一の参照点**。推測で埋めない。不明は **未確認**と書く。

---

## 2. プロジェクトの大目的

| 項目 | 内容（合意ベース・正本は `docs/PRODUCT_ROADMAP_AND_VISION.md`） |
|------|------------------------------------------------------------------|
| ゲーム種別 | 日本のプロバスケを**参考**にした**独自リーグ**の **GM シミュレーション**（架空のリーグ名・チーム名・選手名）。2D・90 年代コンソール風を現代風に。 |
| 販売目標 | **Steam** で販売。数値目標として **単価 1500 円・10000 本以上**がミッション文脈で使われる（最終価格・割引はリリース時に手動判断）。 |
| 品質目標 | **安定性最優先**（クラッシュ・セーブ破損・再現不能バグを最も恐れる）。その上で商業品質を目指す。 |
| 言語・市場 | **日本語話者向け**。チャットもゲーム内表示も**日本語仕上げ**（コード・識別子・コミットメッセージの英語は可）。 |
| 核となる体験 | 長期シーズン運営、戦術・人事・経営の意思決定、試合シミュと結果の追体験（将来はハイライト／結果だけモード等。正本 `docs/HIGHLIGHT_MODE_SPEC.md`）。**製品ではメイン操作は GUI 一本化**が目標（CLI は開発・CI・smoke 補助）。 |

---

## 3. 現在の開発方針

| 論点 | 内容 |
|------|------|
| 最優先 Phase | **Phase 0**（セーブ・ビルド・依存関係・Steam 技術・商業前提）。詳細は `docs/PRODUCT_ROADMAP_AND_VISION.md`。 |
| CLI と GUI | **製品プレイの前提は GUI**。CLI（`main.py` のメニュー群・`--smoke` 等）は開発・検証・CI 向け。シーズン終了後に CLI 年度メニューへ出る**暫定**経路がコード上に残る場合がある。**最終形は GUI 内で年度・シーズン完結**（ロードマップ記載）。 |
| 安定性 | 新機能より **検証・ログ・再現手順・セーブ互換**。破壊的変更は移行パスまたはバージョン分岐（Phase 1 方針）。 |
| 既存構造 | **既存の呼び出し契約・セーブ・UI 導線を無闇に変えない**。**ついで修正禁止**（`docs/AI_WORKFLOW_RULES.md`）。 |
| 進め方 | **小さく・最小差分・高保全**。中規模以上は**先に調査・計画・完了条件**（同 doc §1）。 |

---

## 4. このプロジェクトの固定ルール（ChatGPT が押さえる要点）

### 4.1 言語・コミュニケーション

- チャットは**日本語**。**情報の後出し・小出しは避け**、一度の返答で読みやすくまとめる（`.cursorrules`）。

### 4.2 Cursor / 実装の依頼方針

- **長いコードはチャットに全文ベタ貼りしない**。ワークスペース上のファイル編集を前提にする（`docs/AI_WORKFLOW_RULES.md`）。
- 「コードは全文書き換え前提」の意味合い: **チャット上でファイル丸ごと貼って置き換える運用はしない**という実務ルールとして理解する（**既存を無闇に全消しする**意味ではない）。

### 4.3 ログ・コマンド

- ログを依頼するときは **抽出コマンドをセット**で示す（Windows PowerShell 想定。コピペ 1 行優先）。詳細は **§11**。

### 4.4 返答の締め（Cursor 側ルール）

- Cursor の AI は会話の最後に必ず次の 2 つを分ける:  
  1. **私に手動でやってほしいこと**（該当なしなら「なし」と明記）  
  2. **次の一手**（**最も推奨する 1 つだけ**・具体タスク名レベル）  
- ChatGPT 側も、ユーザーが同じ運用を望むなら**倣ってよい**（本プロジェクトの合意）。

### 4.5 Git（Cursor 自律運用）

- 作業単位ごとに **`git commit` と `git push`**（リモート・認証・コンフリクト等で失敗したら報告）。**1 コミット 1 目的**。広範囲はブランチ推奨（`.cursorrules`）。

### 4.6 `.cursorrules` / `docs/AI_WORKFLOW_RULES.md` の運用要点（転載ではなく要約）

| # | 要点 |
|---|------|
| 1 | **いきなり実装しない**（中規模以上は原因候補・触るファイル・触らないファイル・副作用・確認方法・方針を先に）。タイポ・import・1 ファイル内の安全な小修正は即可。 |
| 2 | **最小変更・ついで修正禁止**・契約を壊さない。 |
| 3 | 実装前に **完了条件**を観察可能な形で明示。 |
| 4 | 実装後 **自己レビュー**（依頼箇所・近接・None・イベント順・テスト）。 |
| 5〜6 | UI / ロジック変更時は **隣接画面**や**同系列別ケース**も見る。 |
| 7〜8 | 調査・実装・レビューを分離。報告は「直した／触れない／リスク／確認観点（手動は **3 個以内**）」。 |
| 9〜10 | セルフレビュー前提。**共通処理・season/match・save** は波及を疑う。 |

**必読パス**: `.cursorrules`（短い要約）、`docs/AI_WORKFLOW_RULES.md`（手順の正本）、`docs/PRODUCT_ROADMAP_AND_VISION.md`（Phase・ドメインの正本）。

---

## 5. 現在地（ロードマップ）

| 項目 | 内容 |
|------|------|
| Phase | **Phase 0 が★現在地**（Steam・セーブ・ビルド・ログ等の土台）。並行して Phase 1 相当のシミュ・リーグは既に厚い（△〜◎）。 |
| 全体の位置 | 基盤完成 → 試合リアリティ → GM・経営 → UI・演出 → 公開準備 → Steam。いまは**土台と安定化**と**GUI 移行**が継続的に交差。 |
| 最重要テーマ | **安定性・セーブ・再現性**、**GUI 主操作への寄せ**、**Steamworks 手続き**（審査はユーザー確認では**未完了**）。 |
| 直近の主戦場（傾向） | **主画面 tkinter**（`main_menu_view.py`）、**日程表示**（`schedule_display.py` + `season.py`）、**大会表示名**（`competition_display.py`）、**クラブ案内／人事／戦術／経営の情報設計**（`DESIGN_BACKLOG_UX.md` §17 付近）。 |
| 次の大きな節目 | Steamworks 審査完了後のストア・デポ作業、Phase 0 のクラウドセーブ／Rich Presence の要否決定（設計は `integrations/STEAMWORKS_DESIGN.md`）。 |

**Steamworks（ユーザー確認済・2026-04）**: **審査はまだ終わっていない**。完了後にユーザーが報告 → `docs/PRODUCT_ROADMAP_AND_VISION.md` 等を更新する運用。

---

## 6. ここまでに実装・修正済みの重要項目（分野別）

※日付は主に `docs/DESIGN_BACKLOG_UX.md` と **git ログ**に基づく。**細部はコードとテストが正本**。

### 6.1 メニュー・情報設計

- **左メニュー「GM」→「クラブ案内」へ改名**（GUI）。中身は閲覧・案内・CLI ショートカット中心（`DESIGN_BACKLOG_UX.md` §17〜18）。
- **スタメン／6th・ベンチの編集** → **戦術**ウィンドウへ移設済み。クラブ案内側は**参照**。
- **strategy / coach / usage の編集** → **戦術**へ移設済み。クラブ案内は**参照**。
- **サラリーキャップ閲覧の正本** → **経営**の財務サマリー内へ。クラブ案内は案内のみ。
- **チーム属性の正本** → **情報→概要**。クラブ案内は案内のみ。
- **ロスター全文（`format_gm_roster_text`）の正本** → **人事**ウィンドウ。クラブ案内は案内のみ。
- **トレード／インシーズン FA の案内の正本** → **人事**。クラブ案内は誘導＋CLI ショートカット。
- **内部キー** `menu_callbacks` の `"GM"` 等は**後方互換**で残る場合あり。CLI の「8.GMメニュー」表記は**未整理のまま**の可能性（§18 backlog）。

### 6.2 ホーム画面・レイアウト

- **「やること」**ラベル・トップバー内訳・右上パネル・進行ヒントの整理（§21）。
- **ニュース欄**: `ScrolledText` 化・右カラム行比 2:3 など（§27）。
- **負傷者タスク**: 文言・戦術/人事への `①` サフィックス・詳細ガイド `Toplevel`（§25）。

### 6.3 戦術・経営ウィンドウ（表示・スクロール）

- **戦術**・**経営**ウィンドウに **Canvas + 縦スクロール**（§23〜24）。
- **経営ウィンドウ初期表示**: リフレッシュ前からプレースホルダ・未接続時の安全表示（§26）。

### 6.4 日程・リーグ生成

- **土日同一相手・同一 H/A・水曜は別相手・水曜 1 試合**のルールは `Season.collect_league_week_matchups` 等で実装（§12、テスト `tests/test_season_league_schedule_rules.py`）。
- **2026-04 前後の追加（git `a2d982d` 付近）**:  
  - **3 試合週**の内部リスト順を **水曜ブロック → 週末ブロック**にし、`simulate_next_round` / `game_results` の順とカレンダー解釈を整合。  
  - **`SeasonEvent.day_of_week`** に Wed/Sat/Sun を付与（division 境界 `_regular_round_division_spans` 利用）。  
  - **ラウンド 1** をコード上でも **水曜なし・2 試合/週**に固定。  
  - 表示補助として `schedule_display` の一部行に **水/土/日**接頭辞。  
  （詳細は `season.py` と `test_season_league_schedule_rules.py` を正本とする。`DESIGN_BACKLOG_UX.md` §12 の日付「2026-03」と**文言の更新時期がずれる**可能性あり。）
- **H/A 長期バランス**: ダブル RR の並べ方調整（§29）。
- **オールスター週**等の表示補完は `schedule_display` 側に実装済み（過去コミット `fix(schedule): ...` 参照）。

### 6.5 大会表示名（2026-04 前後）

- **内部キーは維持**（`easl` / `asia_cl`）。**表示名の正本**は `systems/competition_display.py`。  
  - `easl` → **東アジアトップリーグ**  
  - `asia_cl` → **オールアジアトーナメント**  
  - 代表ウィンドウのアジアカップは **アジアカップ（予選/本戦）**のまま（`season.py` のラベルマップ）。  
- CLI ログ・マイルストーン文言・`ROUND_CONFIG` の `notes` 表記も追随済み（同一コミット系）。

### 6.6 負傷・ローテ

- 試合終了フックで **`injury_lineup_autorepair`** によりローテ・`starting_lineup` 等を自動整合（§28）。通知はユーザーチームのみ `_injury_autorepair_notice_jp` 経由。

### 6.7 経営・財務（表示・土台）

- 経営メニューの説明文・プレースホルダ（§20）。**週次会計の本格実装や内訳スナップショットの永続化**は `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` が**たたき台**（未完了部分あり）。

### 6.8 GUI と CLI・システムメニュー

- **システムメニュー**（セーブ/ロード/設定タブ等）、**途中セーブ**、**シーズン後の次シーズン接続**・**二重オフ防止**等（git: `9558166`, `1fb0154` など。詳細は当該コミット差分が正本）。
- **`--smoke` / `--steam-diag`** は `main.py` の `__main__` 分岐。

### 6.9 テスト・品質

- **pytest** 多数（`basketball_sim/tests/`）。**バランス系**は `.github/workflows/balance-guard.yml`（heavy）がゲート（係数変更時は通過必須・ロードマップ記載）。
- **`test_simulation_balance_guard.py`**: 長時間シミュの集計レンジチェック（ローカル実行は数分かかる場合あり）。

### 6.10 コードベース規模（事実）

- `basketball_sim` 配下の `.py` は **2026-04-01 時点で合計 125 個**（PowerShell で再帰カウント）。  
  - そのうち **`tests` 配下 55**、**tests 以外 70**。  
- 旧ドキュメントの「Python 約 34 ファイル」は**古い目安**。**正確な本数は本カウントを正**とする。

---

## 7. 直近で触ったファイル・重要ファイル（役割つき）

| パス | 役割・注意 |
|------|------------|
| `basketball_sim/main.py` | CLI エントリ・各種メニュー・`--smoke`。**巨大**。変更は波及しやすい。 |
| `basketball_sim/models/season.py` | シーズン進行・`ROUND_CONFIG`・日程生成・EASL/ACL/杯のシミュ分岐・`SeasonEvent` 生成。**触ると全体日程・結果順に直結**。 |
| `basketball_sim/models/match.py` | 試合シミュ・負傷処理・先発解決（`MATCH_STARTING_LINEUP_RULES.md` と整合）。 |
| `basketball_sim/models/team.py` | チーム状態・履歴マイルストーン集計・財務スカラー。**セーブ互換の要**。 |
| `basketball_sim/systems/main_menu_view.py` | **tkinter 主画面の中心**。メニュー・各ウィンドウ・ホームレイアウト。**最も UI 変更が集中**。 |
| `basketball_sim/systems/schedule_display.py` | 日程タブ・次ラウンド表示・補完行。**表示と season の契約**に依存。 |
| `basketball_sim/systems/competition_display.py` | **大会名表示の正本**（内部キー→日本語）。 |
| `basketball_sim/systems/history_display.py` | クラブ史・マイルストーン行の分類表示。 |
| `basketball_sim/systems/injury_lineup_autorepair.py` | 負傷後のローテ自動修正。 |
| `basketball_sim/config/game_constants.py` | キャップ・外国人枠・日程カットオフ等の定数。**バランス変更は CI 意識**。 |
| `basketball_sim/persistence/save_load.py` / `save_payload.py` | セーブ形式・バージョン。**破壊的変更は最慎重**。 |
| `.cursorrules` | Cursor 向け短い憲法。 |
| `docs/AI_WORKFLOW_RULES.md` | 実装手順の正本。 |
| `docs/PRODUCT_ROADMAP_AND_VISION.md` | Phase・Steam・ドメイン固定の正本。 |
| `docs/DESIGN_BACKLOG_UX.md` | UX 変更の**時系列メモ・§番号**。メニュー再編・日程・負傷等の説明に強い。 |
| `docs/SCHEDULE_MENU_SPEC_V1.md` | 日程メニュー仕様・大会表示の内部キー対応表。 |
| `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` | 経営メニューたたき台。 |
| `docs/MATCH_STARTING_LINEUP_RULES.md` | 先発ルール正本。 |
| `docs/SEASON_SCHEDULE_MODEL.md` / `OFFSEASON_WEEK_MODEL.md` | 週次モデル正本。 |

**波及が大きい（触ると他が壊れやすい）**: `season.py`、`match.py`、`save_load.py` / `save_payload.py`、`main_menu_view.py`。

---

## 8. 未解決課題・注意点

優先度は**あくまで引き継ぎ用の目安**（ユーザーが再確認すべきものを上に）。

| 優先度 | 内容 |
|--------|------|
| **高（手動確認されやすい）** | **Steamworks 審査未完了**（完了後に doc 更新）。**日程**: 3 試合週・R1・杯週・代表週の**目視**（内部データと表示の一致）。**セーブ互換**: 古いセーブでの起動。 |
| **中** | **過去結果**（`past_league_result_rows`）は `game_results` ベースで**大会種別・ラウンドが「—」**になりやすい（仕様どおりの制限。別データソースが必要な論点は backlog）。 |
| **中** | **同一ラウンド内の試合間に戦術介入**は**未実装**（`simulate_next_round` が一括）。体験改善は `DESIGN_BACKLOG_UX.md` §11・§15・§16 の backlog。 |
| **中** | **クラブ案内（旧 GM）の最終処遇**（削除か縮小か）は **§18 で未確定**。CLI「8.GMメニュー」表記との同期も backlog。 |
| **中** | **`ROUND_CONFIG` の一部**（例: R2/R4 で `has_midweek_league: True` だが 2 試合週で水曜リーグ無し）— **意図的**（§12）。誤バグ報告されやすい。 |
| **低〜中** | **経営の本格シミュ**・**週次会計の永続化**は仕様ドラフト段階（`GM_MANAGEMENT_MENU_SPEC_V1.md`）。 |
| **低** | **ディビジョン PO の SeasonEvent 化**、杯のカード事前表示などは**将来イテレーション**（`SCHEDULE_MENU_SPEC` §0.4 等）。 |
| **再確認推奨** | **Balance Guard** を含む CI の通過、**`python -m basketball_sim --smoke`**、主要 pytest の一部（時間のかかるテストは個別実行）。 |

---

## 9. 再開時の推奨手順（ChatGPT 向け）

1. **本ファイルを読み**、ユーザーの「違和感」が **表示かロジックかセーブか**のどれかに仮分類する。  
2. **正本 doc を当たる**: 日程なら `SEASON_SCHEDULE_MODEL.md` + `SCHEDULE_MENU_SPEC_V1.md` + `test_season_league_schedule_rules.py`。先発なら `MATCH_STARTING_LINEUP_RULES.md`。Phase/Steam なら `PRODUCT_ROADMAP_AND_VISION.md`。  
3. **いきなり大規模パッチを提案しない**。中規模以上は `AI_WORKFLOW_RULES.md` の調査・計画・完了条件の順。  
4. **巻き戻してはいけないもの**: セーブ形式の無計画変更、**単一シミュの真実**を崩す二重シミュ、既存のトレードカットオフ（`REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND`）の黙殺。  
5. **安全な順序**: 再現手順の固定 → 最小再現テスト or ログ → 1 ファイルに閉じる修正 → pytest 該当 → 手動 3 点確認。

---

## 10. 次に着手すべき候補（優先順・最後に 1 件）

**候補（3〜5 件・順不同の意味合いで並べた）**

1. **Steamworks 審査完了後**のストアページ・デポ・ビルドアップロード（**手動中心**。完了報告後に doc 更新）。  
2. **主画面 GUI からトレード/FA/経営操作**を `season_transaction_rules` 等の**既存ガード**に接続（PRODUCT ロードマップ「残」記載）。  
3. **クラブ案内の最終縮小または削除**（§18 の決定後、段階 PR）。  
4. **過去結果の大会種別表示**（データモデル拡張の要否検討）。  
5. **Phase 0**: クラッシュログ・`last_crash.txt` の運用確認、配布物の `--smoke` 文書化の継続。

**最優先で次にやる 1 件（具体）**  
**「Steamworks 審査が完了したら、`docs/PRODUCT_ROADMAP_AND_VISION.md` の Steamworks 節を最新ステータスに更新し、次に必要なストア/デポ作業をチェックリスト化する」**  
※審査**未完了**の今は、並行してコード側では **「GUI からインシーズン取引ガードを通す」**または **「pytest / smoke を回して回帰確認」**のどちらかをユーザーと合意して進めるのが無難（**未完了の間の最優先はユーザー判断**）。

---

## 11. 実行コマンド・確認コマンド（コピペ用・PowerShell）

リポジトリルート（`basketball_project`）で実行する想定。

```powershell
cd c:\Users\tsuno\Desktop\basketball_project
```

| 目的 | コマンド（1 行） |
|------|------------------|
| ゲーム起動（CLI メニュー） | `python -m basketball_sim` |
| スモーク（終了コード 0 で成功） | `python -m basketball_sim --smoke` |
| Steam 診断 | `python -m basketball_sim --steam-diag` |
| pytest（表示・大会名まわりの早いセット例） | `python -m pytest basketball_sim/tests/test_competition_display.py basketball_sim/tests/test_schedule_display.py basketball_sim/tests/test_season_league_schedule_rules.py -q` |
| pytest（バランスガード・**数分〜**かかる） | `python -m pytest basketball_sim/tests/test_simulation_balance_guard.py -q` |
| 直近コミット確認 | `git log -10 --oneline` |
| 変更差分確認 | `git status` / `git diff` |

**長いログをファイルに保存**（例）:

```powershell
python -m pytest basketball_sim/tests/ -q 2>&1 | Tee-Object -FilePath pytest_out.txt
```

**ログ検索のヒント**: `game.log` や `last_crash.txt` を使う場合はパスをユーザー環境で確認（`utils/game_logging.py` 等が正本。**未確認の場合はリポジトリ内 `grep` で検索**）。

---

## 12. ChatGPT 新チャットに貼るときの推奨冒頭文（そのままコピペ可）

```
以下のファイルは、Cursor で開発中のバスケットボール GM シミュ（Steam 目標・日本語 UI）の「現状同期用正本」です。
リポジトリパス: docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md
この内容を前提に回答してください。詳細仕様は文中の docs リンクが正本です。
いまの目的は: （ここにユーザーがやりたいことを1行で書く）
```

---

## 付記: 直近 git ログ（参照用・コピー時点で変化する）

```
a2d982d feat: リーグ日程コア（3試合週・曜日・R1）と大会表示名統一、関連docs更新
7008c39 docs: .cursorrules を整理し AI 運用とロードマップを docs に分離
```

（より古い履歴は `git log` で確認。）

---

## 変更履歴（本ファイルのみ）

| 日付 | 内容 |
|------|------|
| 2026-04-01 | 初版作成。コード変更なし。 |
