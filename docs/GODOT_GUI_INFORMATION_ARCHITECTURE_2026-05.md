# Godot 本番 GUI 向け 情報設計メモ（2026-05）

**位置づけ**: これは **Godot 実装そのものではない**。Tk 仮 GUI で固まってきた情報設計を、Godot 本番 GUI へ移すための **再整理メモ**。CLI / Tk で確認できている**正本データ・正本ロジックを壊さず**、画面構成だけを本番向けに描き直すための叩き台。

- 関連: `docs/PRODUCT_ROADMAP_AND_VISION.md`（Phase 0〜6）／`docs/IMPLEMENTATION_PLAN_MASTER.md`（§5.1 §11 §12）／`docs/PHASE0_COMPLETION_TEMPLATE.md`（§4 Phase 0 残 集約）／`docs/IDEAL_GAME_DESIGN_MASTER.md`／`docs/INFORMATION_MENU_SPEC_V1.md`／`docs/SCHEDULE_MENU_SPEC_V1.md`／`docs/SYSTEM_MENU_SPEC_V1.md`／`docs/PERSONNEL_GUI_MINOPS.md`／`docs/TACTICS_MENU_FULL_HANDOFF_2026-04.md`
- 直近コミット（2026-05-11 同期）: `daef1e2 FA市場の閲覧専用窓を追加` → `154c114 直近オフ振り返り窓と補助ボタン配置を整理` → `f8898a7 Godot本番GUI向け情報設計メモを追加`（本ファイル）→ `a807988 再契約とオークションドラフトの履歴記録を追加` → `5aeaf81 新Chat引き継ぎ書を最新状態へ更新` → `2fe7651 Phase 0残現状をdocsに同期` → `48ecbaa セーブREADME反映` → `4b2401b クラッシュログ判断` → `b0a8f75 Tk callback例外フック追加` → `44910f1 GHA継続判断` → `7c0d7d6 ストア説明文ドラフト` → `1bce4c9 ライセンス手順書` → `8dec1f1 ストア説明文ローカルセーブ反映` → **`a650444 ライセンス強制実機テスト結果を記録`（Phase 0 必須項目すべて完了の最終 commit）**
- **本実装着手の前提**（2026-05-11 同期）: 本メモは情報設計メモであり、Godot 本実装の決定書ではない。**Phase 0 必須項目（旧 5 項目：ライセンス強制実機テスト・セーブ README・ストア説明文ローカルセーブ表記・クラッシュログ判断・GHA 継続判断）は 2026-05-11 までに完了**（`docs/PHASE0_COMPLETION_TEMPLATE.md` §2 冒頭 2026-05-11 追記・§4.2 残作業表・改訂履歴 2026-05-11）。**したがって本メモ §0「Godot 本番 GUI 実装準備へ進む位置づけ」は 2026-05-11 時点で前提を満たした**。次は `docs/IMPLEMENTATION_PLAN_MASTER.md` §5.1（Phase 4 / Godot 本番 GUI 実装準備）・§11 ステップ 3 に沿って、本メモの章立て（特に §10「データ正本一覧」・§13「Godot 移行時に壊してはいけないもの」）を再レビューする段階に移行する。§9「経営・強化・戦術・情報・歴史の整理」は画面割当・メニュー構造の整理メモとして参照する。**ただし、Godot プロジェクトの実コード着手はまだしない**：実装着手判定はユーザー側の意思決定が別途必要で、本書 §1「Godot 実装そのものではない」「確定版ではない」の位置づけは維持する。**継続管理項目**（v1 出荷判断の必須項目ではない）として `docs/PHASE0_COMPLETION_TEMPLATE.md` §5「ストア説明文への実績の有無明記」`[ ]` が残るが、Godot 着手判定の前提条件ではない。

---

## 1. このメモの位置づけ

- **Godot 実装の決定書ではない**。Tk 仮 GUI で確認できた「画面構造・情報粒度・操作と閲覧の分離」を **Godot 移行前に明文化** する。
- **既存ロジック（FA / ドラフト / 契約 / 年俸 / 財務 / 昇降格 / save 構造）は変更しない前提**で、画面側の整理だけを扱う。
- 候補案には「正式配置の候補」「後工程に回すもの」「Godot 移行時に壊してはいけないもの」を含める。**確定版ではない**。実装着手前にもう一度レビューする。

---

## 2. 現在の大ロードマップ上の位置

```txt
◎ 基盤完成
★ リアリティ強化
  ◎ 経営メニュー改善
  ◎ 強化メニュー改善
  ◎ 人事・ロスター改善
  ◎ オフシーズン導線改善
  ◎ O-4：FA市場／ドラフト候補の閲覧専用整理
  ◎ オフシーズン結果ハイライト

★ Godot 本番 GUI 向け情報設計（このメモ）
□ Godot 本番 GUI 実装
□ グラフィック・音楽などの演出実装
□ 完成・ブラッシュアップ・公開準備
□ リリース・販売展開
```

`PRODUCT_ROADMAP_AND_VISION.md` の Phase 4「UI・演出」の手前で、本番 GUI 移行前の地ならしフェーズに位置づける。

---

## 3. 現在の Tk 仮 GUI の画面棚卸し

`basketball_sim/systems/main_menu_view.py` の `MENU_ITEMS` は **9 項目**（2026-05 時点）：

```txt
日程 / 人事 / クラブ案内 / 経営 / 強化 / 戦術 / 情報 / 歴史 / システム
```

加えて、左パネル下に補助枠があり、`aux_buttons_frame` で **2 列グリッド**：

```txt
[オフの流れ] [来年候補]
[FA市場]    [直近オフ]
[デバッグ: オフシーズンまで飛ばす]   ※ debug_skip_cb があるときだけ・2列幅
```

ホーム中央〜右にはダッシュボード（次戦・クラブ状況・やること・ニュース）、右端は **進行ブロック専用**（`advance_button` ／「次へ進む」「オフシーズンを実行」「次のシーズンへ」）。

| 画面 | 現状の入口 | 主な表示 | 主な操作 | 現在の課題 | Godot での扱い候補 |
|------|------------|----------|----------|------------|--------------------|
| ホーム | アプリ起動直後 | 次戦／クラブ状況サマリー／やること（最大 3）／ニュース／進行ボタン | 進行（`_on_advance` → `on_advance`） | 補助閲覧ボタンがホーム左下に同居している | ダッシュボード化。進行と要約の集約点 |
| 日程 | `MENU_ITEMS["日程"]` → `open_schedule_window` | 試合日程・カップ・国際大会・PO 等 | 表示中心 | 仕様正本: `docs/SCHEDULE_MENU_SPEC_V1.md` | 専用画面 / カレンダー UI |
| 人事 | `open_roster_window` | ロスター・契約満了候補・編成ルール／トレード／FA／＋1 年延長／契約解除 | 操作多め（GM 系） | 仕様正本: `docs/PERSONNEL_GUI_MINOPS.md` | 大画面化、検索／絞り込みは後工程 |
| クラブ案内（GM） | `_open_gm_dashboard_window` | クラブ全体ダッシュボード | 表示中心 | ホームと内容が一部重複 | クラブ概要画面 or 廃止しホームに集約 |
| 経営 | `open_finance_window` | 財務 / 施設 / スポンサー / 広報 / グッズ / レポート | 操作（投資・更新・契約等） | サブ窓（`facility/sponsor/pr/merch/report`）が複数（`_on_menu` の `key==` 分岐参照） | 経営センター（タブ構成） |
| 強化 | `open_development_window` | 育成サマリー / 個別練習 / 育成方針 / 直近変更 | 操作（個別練習等） | 仕様の参照元: 強化メニュー設計（複数 PR コミット由来） | 育成センター |
| 戦術 | `open_strategy_window` | プレイスタイル統合（0〜7）／ローテ統合（0〜2）／補助設定（HC/Team） | 操作多め | `TACTICS_MENU_FULL_HANDOFF_2026-04.md` 参照 | 戦術センター（プレイスタイル + ローテ + 補助の3タブ） |
| 情報 | `open_information_window` | リーグ情報・ランキング・成績 | 表示中心 | `INFORMATION_MENU_SPEC_V1.md` | 情報センター |
| 歴史 | `open_history_window` | クラブ史・マイルストーン・歴代 | 表示中心 | `Team.get_club_history_report_text` を再利用 | 歴史画面 |
| システム | `open` 不在時は `on_system_menu` 経由 | セーブ／ロード／設定／キーバインド | 操作 | `SYSTEM_MENU_SPEC_V1.md` | 設定／システム画面 |
| 補助枠 | 左パネル下の `aux_buttons_frame` | オフの流れ／来年候補／FA市場／直近オフ／デバッグ | 表示専用＋デバッグ | **仮 GUI の発展用置き場**。本番では正式画面へ卒業 | 各機能の正式画面に分散 |

---

## 4. ホーム画面の情報設計（Godot）

### 方針

- ホームは「**いま、次に何をするか**」を即決させる場。詳細閲覧の置き場ではない。
- 右端進行ブロックは引き続き **進行専用**。確認操作（次へ進む／オフシーズンを実行／次のシーズンへ）以外を増やさない。
- 補助閲覧ボタン（FA市場・来年候補・オフの流れ・直近オフ）は**ホーム下から正式画面へ卒業**させる。

### ホームに残す（候補）

- **次戦／次イベント**: 当該ラウンドの主要試合・イベント（`Season` 経由）
- **クラブ状況サマリー（短い）**: 順位・直近成績・所属ディビジョン・財務 1 行
- **次にやること**: 「やること」最大 3 行（既存 `_get_task_lines`）
- **重要ニュース**: 直近の昇降格・受賞・トレード・FA 結果 など重要度フィルタを通したヘッドライン
- **進行ボタン**: 「次へ進む」「オフシーズンを実行」「次のシーズンへ」

### ホームから分ける（候補）

- **FA市場**: 人事 / FA市場タブへ
- **来年ドラフト候補**: ドラフトセンター / 情報メニュー → ドラフトタブへ
- **オフシーズンの流れ**: オフシーズンセンター（実行前ヘルプ）／進行確認ダイアログ内へ
- **直近オフ振り返り**: 情報メニュー → 直近オフタブ／歴史→クラブ史下のサブ
- **デバッグボタン**: 開発ビルド限定のデバッグパネルへ（製品ビルドでは非表示）

### 注意

- ホームのダッシュボード化を進めるとしても、現在の `home_center_right_paned`・`SectionTitle.TLabel` 等の役割（中央＝次戦/クラブ状況、右＝やること/ニュース/進行）を**根拠なく崩さない**。

---

## 5. 補助枠の正式移設候補

| 補助ボタン | 現在の入口 | Godot 候補 1 | Godot 候補 2 | 備考 |
|------------|------------|--------------|--------------|------|
| オフの流れ | `_open_offseason_flow_overview_window` | **オフシーズンセンター内ヘルプ** | 進行確認ダイアログ | 本文は `OFFSEASON_PHASES` + `build_offseason_focus_summary` 由来 |
| 来年候補 | `_open_future_draft_pool_overview_window` | **ドラフトセンター → 来年候補タブ** | 情報メニュー → ドラフト | `team.league_future_draft_pool` 経由 |
| FA市場 | `_open_fa_market_overview_window` | **人事 → FA市場タブ（閲覧）** | 情報メニュー → FA タブ | 獲得操作は人事の別タブ |
| 直近オフ | `_open_offseason_result_recap_window` | **情報メニュー → 直近オフ振り返り** | 歴史メニュー内サブ | 既存 `history_transactions` などの読み取り集約 |
| デバッグ | `menu_callbacks["DEBUG_SKIP_TO_OFFSEASON"]` | **開発ビルド限定のデバッグパネル** | 起動オプション／ホットキー | 製品ビルドでは非表示 |

正式配置は **未確定**。Godot 着手前にもう一度確認する。

---

## 6. 人事・ロスターの Godot 情報設計

### 大方針：FA「閲覧」と「獲得操作」は混ぜない

- **FA市場（閲覧専用）** と **インシーズン FA 獲得 UI** を別タブ／別パネルに保つ。
- これは Tk 仮 GUI でも **`_open_fa_market_overview_window` は閲覧のみ**、`sign_free_agent` を呼ばない、という設計が定着しているため。

### サブ機能の分け方（候補）

| サブ機能 | 想定タブ／場所 | 操作／閲覧 | 主データ・正本 |
|----------|----------------|------------|----------------|
| ロスター一覧 | ロスタータブ | 閲覧＋並び替え | `team.players` |
| ロスター状況 | ロスタータブ／概要 | 閲覧 | 編成ルール（`roster_rules`）の検証結果 |
| 編成ルール | ロスタータブ → ヘルプ／注意 | 閲覧 | `roster_rules.is_contract_roster_valid` 等 |
| 契約満了候補 | 契約タブ | 閲覧（事前警告） | `contract_logic.get_expiring_players(teams)` |
| FA市場 | FA タブ（閲覧） | 閲覧 | `season.free_agents` |
| インシーズン FA 獲得 | FA タブ（獲得） | 操作（`sign_free_agent` 経由） | `docs/GUI_INSEASON_FA_ENTRY_POLICY.md` を遵守 |
| トレード | トレードタブ | 操作 | `systems/trade.py` / `trade_logic` |
| 契約解除 | ロスタータブ → 行アクション | 操作 | `team.remove_player` + FA 処理 |
| ＋1 年延長 | 契約タブ → 行アクション | 操作 | `apply_contract_extension` |
| 選手検索／スカウト機能 | **後工程** | 後工程 | 検索／絞り込み専用パネル |

### 重要

- **シーズン中の人事はラウンド 22 終了でロック**（`PRODUCT_ROADMAP_AND_VISION.md` Phase 3）。ガードは現行コード（`season_transaction_rules.py`）を経由させる。Godot 側で独自にガードを書かない。

---

## 7. ドラフト・スカウトの Godot 情報設計

### 配置候補

- **ドラフトセンター（新設）** を作るか、**情報メニュー → ドラフトタブ**＋**オフシーズンセンター → ドラフトセクション** に分けるかの 2 系統。

### 取り扱う情報・操作

| 機能 | 配置候補 | 正本データ・処理 |
|------|----------|------------------|
| 来年ドラフト候補（閲覧） | ドラフトセンター → 来年タブ／情報 → ドラフト | `team.league_future_draft_pool`（team_id 最小チーム保持） |
| 当年ドラフト候補（閲覧） | ドラフトセンター → 当年タブ／オフシーズンセンター | `Offseason.draft_pool` |
| スカウト派遣方針 | スカウトセクション | `team.scout_dispatch` 等（CLI に既定値あり） |
| コンバイン方針 | スカウトセクション | `team.scout_focus` 等 |
| ドラフト本番（指名／入札） | オフシーズンセンター → ドラフト実行 | `conduct_auction_draft`（正本: `docs/DRAFT_AUCTION_SYSTEM.md`） |
| ドラフト結果 | オフシーズンセンター → 結果／クラブ史 | 現状: 選手側 `acquisition_type / acquisition_note / is_draft_rookie_contract / draft_rookie_locked_salary`。**`Team.add_history_transaction("draft", ...)` は `draft.py` 側でしか呼ばれず、`draft_auction.py` では未記録**（後工程で対称化候補） |

### 注意

- **オークションドラフトの履歴は現状弱い**。Godot 側で結果画面を作るときは、選手側のフラグから組み立てるか、後工程で `draft_auction` 側にも履歴 1 行を足してから本格対応する。

---

## 8. オフシーズン画面の Godot 情報設計

### オフシーズンセンター（新設想定）に集約する候補

- **オフの流れ**: `OFFSEASON_PHASES` + `build_offseason_focus_summary` の閲覧（ヘルプ）
- **実行前の確認**: 契約満了候補・FA市場・ドラフト候補の事前閲覧
- **契約満了候補**: `contract_logic.get_expiring_players` ベース
- **FA市場**: 同タブ内の閲覧 or 人事の FA タブへリンク
- **ドラフト候補**: ドラフトセンターへリンク
- **直近オフ振り返り**: 情報メニューと相互リンク
- **オフ実行ボタン**: 既存 `Offseason(teams, free_agents).run()` を呼び出すだけ。**順序や戻り値は変えない**

### 後工程（明示延期）

- **実行中のプログレス表示**: `Offseason.run()` を分割するか進捗コールバックを足す必要があり大きい。**いまはやらない**。
- **オフシーズン中断 / 再開**: save スキーマ拡張が必要。**いまはやらない**。

---

## 9. 経営・強化・戦術・情報・歴史の整理

### 経営

- **対象**: 財務、施設、スポンサー、広報、グッズ、レポート
- **正本**: `team.finance_history` / `Team.record_financial_result` / `cashflow_last_season` / `revenue_last_season` / `expense_last_season` / `money` / `team.facility_*` / 経営アクション系 systems。
- **Godot**: 財務概要 + サブタブ（施設／スポンサー／広報／グッズ／レポート）。Tk 側の `_on_menu("経営")` → `open_finance_window` が `key in {facility, sponsor, pr, merch, report}` で分岐している構成と合わせる。
- **将来**: 「施設プロジェクト制」（`IDEAL_GAME_DESIGN_MASTER.md` 系）は**後工程**。

### 強化

- **対象**: 育成サマリー、個別練習、育成方針、直近変更ログ、スペシャル練習
- **正本**: 選手側の練習関連フィールド／`DevelopmentSystem` 系。
- **Godot**: 育成センター（チーム概観 + 個別練習編集）。

### 戦術

- **対象**: プレイスタイル（0〜7）、ローテーション統合（0〜2）、補助設定（Team 基本方針／HC スタイル）、起用プリセット、起用序列、目標出場時間
- **正本**: `team_tactics` 系・`team.tactics` 関連、`docs/TACTICS_MENU_FULL_HANDOFF_2026-04.md`。
- **Godot**: 戦術センター（プレイスタイル / ローテ / 補助 の 3 タブ）。**統合画面の補助動線（プレイスタイル → 補助設定）と整合**。

### 情報

- **対象**: リーグ情報、成績、ニュース、FA／ドラフトの情報タブ候補、直近オフ振り返り
- **正本**: `Season` 公開メソッド（順位・ランキング・進行）、`team.history_*`、`team.finance_history`。
- **Godot**: 情報センター。仕様正本は `INFORMATION_MENU_SPEC_V1.md`。**直近オフ振り返り** は情報メニュー配下に置くのが自然な候補。

### 歴史

- **対象**: クラブ史、シーズン履歴、マイルストーン、歴代インパクト、直近オフとの関係
- **正本**: `team.history_seasons` / `team.history_milestones` / `team.history_transactions` / `team.all_time_player_archive` 等、`Team.get_club_history_report_text`。
- **Godot**: 歴史画面（クラブ史 + 歴代記録）。**直近オフ振り返り** とは入口を分けつつ相互リンク。

---

## 10. データ正本一覧（重要）

| データ名 | 正本 | 表示先候補 | 読み取り専用 / 操作あり | 注意点 |
|----------|------|------------|--------------------------|--------|
| ロスター | `team.players` | 人事 → ロスタータブ／ホーム要約 | 操作あり（`add/remove_player` 等） | Godot から直接 `players` を書き換えない。`team_lineup` 等の操作 API 経由 |
| FA市場 | `season.free_agents`（フォールバック: `self.free_agents`） | 人事 → FA タブ（閲覧）／情報 → FA | 閲覧＋獲得操作は別タブ | `_collect_fa_market_candidates` 同様、表示用には**コピーを使い破壊しない** |
| 来年ドラフト候補 | `team.league_future_draft_pool`（team_id 最小に保持。`Season` 経由フォールバック） | ドラフトセンター → 来年タブ／情報 | 閲覧 | プールの所有チーム側で更新される設計を尊重 |
| 当年ドラフト候補 | `Offseason.draft_pool` | オフシーズンセンター → ドラフト | 閲覧（実行は `conduct_auction_draft`） | `Offseason.run()` 中だけに有効。表示は瞬間値 |
| 契約満了候補 | `contract_logic.get_expiring_players(teams)` | 人事 → 契約タブ／オフシーズンセンター事前 | 閲覧 | 表示時にプレイヤー集合の同期を意識 |
| オフシーズン流れ | `systems/offseason_phases.py: OFFSEASON_PHASES` + `build_offseason_focus_summary` | オフシーズンセンター → ヘルプ／補助窓 | 閲覧 | 文言は CLI / Tk と一致させる |
| 直近オフ振り返り | `team.history_transactions` / `team.finance_history` / `team.history_milestones` / `team.players[].acquisition_*` ／`is_draft_rookie_contract` ／`draft_rookie_locked_salary` ／`career_history`（`Re-sign` / `Contract Extension`） | 情報 → 直近オフタブ／補助 | 閲覧 | **新規 save フィールドを足さず**、既存データのみを読む（現行 Tk 仮実装と同じ規律） |
| 財務 | `team.finance_history`（最新行）／`cashflow_last_season` / `revenue_last_season` / `expense_last_season` / `money` | 経営 → 財務／ホーム要約 | 閲覧 / 経営アクションは別経路 | `Team.record_financial_result` を画面側から二重呼び出ししない |
| 昇降格 | `Season._process_promotion_relegation` 結果＋ `team.history_milestones`（`promoted` / `relegated`） | 歴史／情報／直近オフ | 閲覧 | 表示は `team.league_level` と整合させる |
| 戦術 | `team.tactics` / `team_tactics` 系 | 戦術センター | 操作 | 既存 API（`apply_*` 系）越しに変更する |
| 強化 | 選手側練習関連フィールド／`DevelopmentSystem` | 強化センター | 操作 | チーム外（FA など）への波及は既存 `_player_progression` のまま |

---

## 11. Godot で最初に作るべき画面候補（優先順）

| 順 | 画面 | 理由 |
|----|------|------|
| 1 | **ホーム／ダッシュボード** | アプリ起点。進行と要約の集約点。先に骨組みを固めると他画面の依存関係が確定する |
| 2 | **人事・ロスター** | 操作密度が高く、既存 API（FA / トレード / 解除 / 延長）の入口が多い。`PERSONNEL_GUI_MINOPS.md` を準拠点にできる |
| 3 | **オフシーズンセンター** | 「オフの流れ」「FA市場（閲覧）」「ドラフト候補」「直近オフ」の補助枠を最初に卒業させる先 |
| 4 | **日程／試合結果** | 進行と密接。シミュレーション結果の表示は副作用が小さい |
| 5 | **経営** | サブ窓が多い（施設／スポンサー／広報／グッズ／レポート）が、表示中心〜操作までグラデーションで作れる |
| 6 | **強化** | 育成編集 UI は既存の Tk 設計が比較的安定。`Player` 直編集を避け、`DevelopmentSystem` 経由に統一 |
| 7 | **戦術** | プレイスタイル / ローテ / 補助の 3 タブ。Tk 側でも統合画面が完成しているので移植しやすい |
| 8 | **情報／歴史** | 表示中心。クラブ史テキストと直近オフ振り返りを相互リンク |

---

## 12. 後工程に回すもの（明示）

- 正式な **選手検索／スカウトセンター**（フィルタ、年齢／ポジション、契約状況、OVR レンジ等の絞り込み）
- **FA／ドラフト候補の検索／絞り込み**
- **再契約結果の履歴表示強化**（`apply_resign` から `Team.add_history_transaction("re_sign", ...)` を呼ぶ等の小ロジック追加）
- **オークションドラフト結果の履歴 1 行追加**（`draft_auction.py` を `draft.py` の `_record_team_draft_history` 同等に対称化）
- **施設プロジェクト制**
- **オフシーズン中のプログレス表示**（`Offseason.run()` 分割や進捗コールバック）
- **オフシーズン中断 / 再開**
- **クラブ史との完全統合**（直近オフ振り返り ↔ クラブ史を 1 画面に統合する案）
- **演出 / グラフィック / 音楽**（`PRODUCT_ROADMAP_AND_VISION.md` Phase 4 後段）

---

## 13. Godot 移行時に壊してはいけないもの

- **CLI / Tk で安定しているロジックを、本番 GUI 都合で直接書き換えない**。GUI は表示／操作呼び出しの薄い層に保つ。
- **`Player` / `Team` / `Season` / save 構造を安易に変えない**。`format_version` と移行フックの方針（`PRODUCT_ROADMAP_AND_VISION.md`）を尊重する。
- **FA 獲得 / ドラフト / 契約 / 年俸 / 昇降格 / 財務ロジックを画面都合で変えない**。例: `sign_free_agent` の入口は `docs/GUI_INSEASON_FA_ENTRY_POLICY.md` / `docs/GUI_FA_CONTRACT_ENTRY_POLICY.md` を遵守。
- **読み取り表示と操作呼び出しを分離する**。FA市場・来年候補・直近オフ・オフの流れ等の閲覧窓パターン（`_format_*_text` を Tk 非依存にする）を Godot でも維持する。
- **`Offseason.run()` の戻り値・順序に依存しない**。現状は副作用ベース。プログレスや結果集約が必要になっても、まずは既存の永続データ（`history_transactions` / `finance_history` / `history_milestones` 等）を経由する案から検討する。
- **シーズン中のトランザクション・カットオフ**（ラウンド 22）を画面側で勝手に外さない。
- **テスト容易性**（Tk root 不要・`SimpleNamespace` で本文関数を単体テストできる構造）を継承する。

---

## 14. Godot / Python ランタイム連携方針（Phase 4 初期）

本節は **2026-05** 時点の方針メモである。運用手順の詳細は `godot/README.md`、読み取り専用 export の実装は `basketball_sim/export/` の `home_dashboard_readonly.py` / `roster_readonly.py` / `club_history_readonly.py` / `standings_readonly.py` / **`schedule_readonly.py`** / **`facility_summary_readonly.py`** / **`finance_summary_readonly.py`** / **`owner_mission_readonly.py`** / **`tactics_summary_readonly.py`** / **`contract_personnel_summary_readonly.py`** に加え、**10 画面分を一括で `godot/data/` に書き出す** **`godot_readonly_bundle.py`**（モジュール `basketball_sim.export.godot_readonly_bundle`）を正とする（§15）。

### 14.1 現在の接続方式（手動 JSON）

- Python CLI（`python -m basketball_sim.export.home_dashboard_readonly --save <.sav> --output <.json>`）で **読み取り専用のホーム用 JSON** を手動生成する。処理は `load_world` による **セーブの読み取りのみ**であり、**セーブファイルを書き換えない**。
- Godot は **`res://data/home_dashboard_from_python.json`** を優先して読み、無ければ **`res://data/home_dashboard_mock.json`** にフォールバックする（`godot/scripts/home_dashboard.gd` の `_home_json_candidate_paths`）。
- ロスター・クラブ史・順位表・日程・施設・財務・**オーナーミッション**・**戦術サマリー**・**契約 / 人事サマリー**など **他画面も同型**（`_*_from_python.json` 優先・`*_mock.json` フォールバック）。CLI とファイル名は `godot/README.md` を正とする。
- **共通 Theme**（`phase4_readonly_core.tres`）は **一部の閲覧画面にのみ**割当てており、**JSON 読込パスや Python 連携方針とは独立**（§15.1）。
- **10 画面分を一度に更新**するには、`py -m basketball_sim.export.godot_readonly_bundle --save <.sav> --output-dir godot\data` のように **Python のみの CLI を手動実行**する（**Godot が Python を自動起動する実装ではない**。PowerShell 等からの運用。任意の `--max-history` / `--max-missions` / `--max-players` などは `godot/README.md` と CLI ヘルプを参照）。
- **Godot から Python プロセスを起動する処理は、本節の時点では入れない**。
- 生成物 `*_from_python.json`（ホーム用に限らず **10 種**）は開発用であり、`godot/.gitignore` で **コミット対象外**。

### 14.2 今すぐ実装しないこと

次は **Phase 4 初期の範囲外**とし、ランタイム連携の実装は行わない。

- Godot から Python を **自動起動して JSON を生成する**こと
- Godot から **ゲーム進行**すること
- Godot から **セーブ / ロード**を本番同様に接続すること
- Godot から **人事・経営・強化・戦術**などの正本操作を行うこと
- **`Offseason.run()` を Godot から呼ぶ**こと
- Python の正本ロジックを **Godot 側へ二重実装**すること
- **`format_version` / `PAYLOAD_SCHEMA_VERSION` を変更すること**（不要な変更は行わない）
- **MainMenuView / Tk の実行中状態を横取り**すること

### 14.3 自動起動を実装する場合に想定されるリスク（調査メモ）

以下は実装前調査で洗い出した留意点であり、**本節では解決策を確定しない**。

- Windows で `python` が PATH に通っているとは限らない
- venv 利用時は **`venv\Scripts\python.exe` をどう指定するか**が課題になり得る
- 作業ディレクトリ（cwd）が異なると **`basketball_sim` の import に失敗**し得る
- Godot の **`res://` と OS 実パス**の対応、および **書き込み可否**（エクスポート配布時は別検証が必要）
- PowerShell の `$env:USERPROFILE` と Godot の環境変数取得は **別系統**の扱いになる
- **日本語パス・スペース入りパス**の子プロセス引数は要検証
- **stdout / stderr** の取得・閲覧方法は未決（ログファイル化等は後工程）
- 自動生成に失敗した場合、**古い JSON が残り誤表示**につながる可能性
- **Steam 配布**で Python をユーザーに要求するか、**同梱 exe 化**するかは **未決**

### 14.4 将来候補（実装判断は後工程）

- **開発限定**: Godot から OS 経由で Python CLI を呼び、成功後に JSON を再読込する案
- **本番寄り**: Python ロジック（または export 専用）を **exe 化**し、Godot から呼ぶ案
- **通信**: ローカル HTTP / RPC で Godot がデータを取得する案
- **当面継続**: 手動 JSON のまま、**ホーム見た目**・**DTO 品質**・**次の読み取り専用画面**で足場を広げる案

### 14.5 現時点の推奨方針

- Phase 4 初期では **Godot から Python 自動起動は実装しない**
- 開発中は **手動 JSON 生成**（画面単体の export に加え、必要なら **`godot_readonly_bundle` による一括 export**）**+ Godot 優先読込**で十分とする
- 先に **ホームの見た目改善**、**DTO 品質改善**、**次の読み取り専用 Godot 画面**でパターンを積む
- **自動起動**は、Python 実行環境の前提・対象 save の決め方・JSON 出力先（`res://` vs `user://` 等）・**配布方針**を固めてから **実装するかを判断**する

---

## 15. Phase 4 初期プロトタイプ到達点（Godot / 読み取り専用）

**位置づけ**: 本節は **`godot/` 上の仮 GUI 足場** の記録であり、本番 GUI 完成・確定仕様の宣言ではない。詳細な運用手順は `godot/README.md` を正とする。ナビの整理方針は `docs/GODOT_NAVIGATION_PHASE4_2026-05.md` と併読。

- **2026-05 時点の到達点**: `godot/` に **ホーム・ロスター閲覧・クラブ史閲覧・順位表（リーグ状況）閲覧・日程（スケジュール）閲覧・施設サマリー閲覧・財務サマリー（経営）閲覧・オーナーミッション / クラブ評価閲覧・戦術 / ローテーションサマリー閲覧・契約 / 人事サマリー閲覧** の **10 画面**があり、いずれも **読み取り専用プロトタイプ**（進行・保存・契約・トレード・経営・育成・戦術保存・**施設投資・施設レベルアップ**・**財務の予算変更・投資・契約更新**・**ミッション生成・評価更新・報酬付与・オーナー評価の操作**・**戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択**などの **状態変更系 UI は未接続**）。
- **画面の役割（仮）**:
  - **ホーム**: **仮ハブ**およびクラブ状況サマリー（`home_dashboard_readonly` DTO に相当する JSON）。
  - **ロスター閲覧**: **現在のチーム編成**の表形式閲覧（`roster_readonly` DTO）。
  - **クラブ史閲覧**: **長期プレイの蓄積**閲覧（`club_history_readonly` DTO）。
  - **順位表 / リーグ状況閲覧**: **D1/D2/D3 の順位・リーグ状況**の閲覧（`standings_readonly` DTO）。
  - **日程 / スケジュール閲覧**: **次戦・今後の予定・進行ヒント**などの閲覧（`schedule_readonly` DTO。**第1弾の読み取り専用表示**であり、大会別フル・過去結果・本格スケジュール管理は未接続）。
  - **施設サマリー閲覧**: **アリーナ・練習施設・メディカル・フロントオフィス・施設強化ポイント**などの閲覧（`facility_summary_readonly` DTO。**第6画面の第1弾**。**施設投資・レベルアップ・施設プロジェクト制は未接続**）。
  - **財務サマリー閲覧**: **現在資金・前季収入・前季支出・前季収支・サラリー上限・選手年俸合計・サラリー余力・財務履歴**などの閲覧（`finance_summary_readonly` DTO。**第7画面の第1弾**。**予算変更・投資・契約更新などの操作は未接続**）。
  - **オーナーミッション / クラブ評価閲覧**: **オーナー信頼・今季ミッション・ミッション状態・進捗・報酬/ペナルティ・クラブ評価・注意文**などの閲覧（`owner_mission_readonly` DTO。**第8画面の第1弾**。ミッション生成・評価更新・報酬付与などの **操作は未接続**）。
  - **戦術 / ローテーションサマリー閲覧**: **戦術プリセット・プレイスタイル・オフェンステンポ/傾向/組み立て・ディフェンス方針・リバウンド方針・速攻方針・ローテーション方針・先発設定数・目標出場時間設定数・選手ロール・注意文**などの閲覧（`tactics_summary_readonly` DTO。**第9画面の第1弾**。戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択などの **操作は未接続**）。
  - **契約 / 人事サマリー閲覧**: GM が **ロスターの契約状況・人事リスク・年俸バランス**を読むための画面（`contract_personnel_summary_readonly` DTO。**第10画面の第1弾**）。**契約交渉画面ではない**。**契約更新・交渉・獲得・解雇・FA 操作などの UI は未接続**（閲覧のみ）。**財務サマリー**（クラブ全体の資金・収支）とは役割が異なり、**選手単位の契約情報・人事リスク**に寄せた閲覧。**ロスター**（編成表）とは異なり、**年俸・契約残・満了目安・国籍枠・構成バランス**に寄せた閲覧。表示の目安: **契約概要**、**人事リスク**、**主要契約選手**、**ロスター構成**、**注意**、ロスター人数・年俸合計・サラリーキャップ・サラリー余力・平均年俸・最高年俸・契約満了予定・FA 予備軍、選手別の年俸・契約残・国籍枠・FA 目安、ポジション人数・U23・30 歳以上・外国籍/アジア/帰化/国内 など。
- **ファイル構成（財務サマリー）**:
  - Python: `basketball_sim/export/finance_summary_readonly.py`、テスト: `basketball_sim/tests/test_finance_summary_readonly_export.py`
  - Godot: `godot/scenes/finance_summary_view.tscn`、`godot/scripts/finance_summary_view.gd`、`godot/scripts/finance_summary_view.gd.uid`（エディタ UID）、`godot/data/finance_summary_mock.json`
  - 手動生成: `godot/data/finance_summary_from_python.json`（**`godot/.gitignore` 対象・コミットしない**）
- **ファイル構成（オーナーミッション）**:
  - Python: `basketball_sim/export/owner_mission_readonly.py`、テスト: `basketball_sim/tests/test_owner_mission_readonly_export.py`
  - Godot: `godot/scenes/owner_mission_view.tscn`、`godot/scripts/owner_mission_view.gd`、`godot/scripts/owner_mission_view.gd.uid`（エディタ UID）、`godot/data/owner_mission_mock.json`
  - 手動生成: `godot/data/owner_mission_from_python.json`（**`godot/.gitignore` 対象・コミットしない**）
- **ファイル構成（戦術 / ローテーションサマリー）**:
  - Python: `basketball_sim/export/tactics_summary_readonly.py`、テスト: `basketball_sim/tests/test_tactics_summary_readonly_export.py`
  - Godot: `godot/scenes/tactics_summary_view.tscn`、`godot/scripts/tactics_summary_view.gd`、`godot/scripts/tactics_summary_view.gd.uid`（エディタ UID）、`godot/data/tactics_summary_mock.json`
  - 手動生成: `godot/data/tactics_summary_from_python.json`（**`godot/.gitignore` 対象・コミットしない**）
- **ファイル構成（契約 / 人事サマリー）**:
  - Python: `basketball_sim/export/contract_personnel_summary_readonly.py`、テスト: `basketball_sim/tests/test_contract_personnel_summary_readonly_export.py`
  - Godot: `godot/scenes/contract_personnel_summary_view.tscn`、`godot/scripts/contract_personnel_summary_view.gd`、`godot/scripts/contract_personnel_summary_view.gd.uid`（エディタ UID）、`godot/data/contract_personnel_summary_mock.json`
  - 手動生成: `godot/data/contract_personnel_summary_from_python.json`（**`godot/.gitignore` 対象・コミットしない**）
  - 一括 export: `basketball_sim/export/godot_readonly_bundle.py`、テスト: `basketball_sim/tests/test_godot_readonly_bundle_export.py`（**10 件目**として `contract_personnel_summary_from_python.json` を含む。`61cc09a`）
- **読込仕様（財務サマリー）**: **`finance_summary_from_python.json` を優先**し、無い／読めないとき **`finance_summary_mock.json` にフォールバック**（`finance_summary_view.gd` の候補パス配列）。**Godot から Python 自動起動は未実装**。
- **読込仕様（オーナーミッション）**: **`owner_mission_from_python.json` を優先**し、無い／読めないとき **`owner_mission_mock.json` にフォールバック**。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。
- **読込仕様（戦術サマリー）**: **`tactics_summary_from_python.json` を優先**し、無い／読めないとき **`tactics_summary_mock.json` にフォールバック**。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。
- **読込仕様（契約 / 人事サマリー）**: **`contract_personnel_summary_from_python.json` を優先**し、無い／読めないとき **`contract_personnel_summary_mock.json` にフォールバック**。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。
- **データ経路**: いずれも **Python export（`load_world` による読み取りのみ）→ JSON → Godot 表示** の型。各画面は **`_*_from_python.json` 優先・同梱 `*_mock.json` フォールバック**（§14.1 の手動 JSON 方針と同じ運用）。
- **一括 export（Python CLI・手動）**: `godot_readonly_bundle` で **10 件**の `*_from_python.json` を **`godot/data/` にまとめて書き出し**できる（`8822b87` 一括追加、`61cc09a` で 10 本目）。例: `py -m basketball_sim.export.godot_readonly_bundle --save "$env:USERPROFILE\.basketball_sim\saves\debug_user_boost_d1_user_cellb.sav" --output-dir "godot\data" --max-history 8 --max-missions 8 --max-players 8`。**ユーザー環境では** 10 行 `Wrote` のあと **`Bundle complete: 10 succeeded, 0 failed`**、10 ファイルが **`git status --short --ignored` で `!!`**（ignored）になることを確認済み。**Godot からの自動起動・自動更新パイプラインの完成ではない**（詳細は `godot/README.md`）。
- **導線**: **ホーム上部 `HeaderNavRow` は 5 ボタンのまま**（財務・オーナーミッション・**戦術サマリー**・**契約 / 人事サマリー**は **HeaderNavRow に追加していない**）。**ホーム内カード型メニュー**の **「チーム」** カテゴリから **「ロスター」**・**「戦術サマリー」**（第9画面）、**「経営」** カテゴリから **「財務サマリー」**（第7画面）・**「オーナーミッション」**（第8画面）・**「契約・人事サマリー」**（第10画面）へ遷移（**経営列は 3 ボタン**）。各閲覧画面から **ホームへ戻る**（`change_scene_to_file` のみ）。**経営カテゴリにだけあった補足説明ラベルは削除**し、他カテゴリとボタン位置を揃えた（`56bcd9e Godotホーム経営カテゴリの説明文を削除`）。関連実装の足場（戦術）: `f6f5434`（DTO）→ `b2d5e5c`（mock）→ `1be9e1d`（UID）→ `33a26ac`（from_python 優先）→ `f91757d`（ホーム導線）。財務・オーナーミッション側: `ca79138`（DTO）→ `d876227`（mock）→ `de912f2`（UID）→ `bdcb163`（from_python 優先）→ `14cc572`（ホーム導線）。契約・人事サマリー: `d88c8bb`（DTO）→ `689462a`（mock）→ `53f7707`（from_python 優先）→ `2f32a14`（ホーム導線）→ `61cc09a`（一括 10 本目）。
- **確認済み（ユーザー環境 Godot 4.6.2 の目安）**: ホーム → 財務サマリー → ホーム、**ホーム → オーナーミッション → ホーム**、**ホーム → 戦術サマリー → ホーム**、**ホーム → 契約・人事サマリー → ホーム**、**経営カテゴリ 3 ボタン表示**、**既存 9 画面往復**、`from_python` 優先・mock フォールバック、**HeaderNavRow 未変更**、**UID 参照エラー解消**、実行後の追跡差分なし、**一括 export 10 件** など（詳細は `godot/README.md`）。
- **仮ナビ**: ホームを起点に **ホーム → 各閲覧画面 → ホーム**（画面切替のみ。本格ナビゲーションではない）。**ホーム内のカード型メニュー（読み取り）**からも各閲覧画面へ遷移可能（**HeaderNavRow と併用の二重導線**）。
- **未着手**（§14.2 と整合）: Godot からの **Python 自動起動**、**ホームの「データ更新」ボタン**、**画面遷移直前の個別 export**、**配布用 export 専用 exe 化と Godot からの起動**、**`generated_at` の全 DTO 一斉追加**、**Godot で JSON 更新時刻（mtime）のみ常時表示**、本番 **セーブ／ロード** 接続、**進行処理**、状態変更系 UI（**ミッション生成 UI・評価更新 UI・報酬付与 UI・オーナー評価の操作 UI**、**戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択 UI**、**契約更新・契約交渉・獲得・解雇・FA 操作などの契約 / 人事系操作 UI** を含む）、**施設投資・施設レベルアップ・施設プロジェクト制**の UI 接続、**本格ナビゲーション**、**Godot 本番 GUI の一本化**、**Steam 向け本番レイアウト**の確定、**財務・オーナーミッション・戦術サマリー・契約 / 人事サマリー画面の本格ビジュアル調整**、**10 画面すべてへの共通 Theme 一括適用**（現状は **限定適用の検証段階**。詳細は §15.1）。

### 15.1 白ベース Theme 検証（`phase4_readonly_core.tres`・限定適用）

**位置づけ**: **本番 GUI の確定デザインではない**。`godot/themes/phase4_readonly_core.tres`（UID `uid://c9phase4rocore01`）による **白ベース検証版** と、`godot/scenes/theme_preview.tscn` による **第 0 段 preview** で、variation とコントラストを確認している。**既存 10 画面へ一括適用したわけではない**。

- **preview**: `theme_preview.tscn` は **本番10画面に未適用**。暗背景用に `Phase4OnDarkTitle` / `Phase4OnDarkTableHead` 等を使い分け、可読性を確認している。
- **限定適用の方針**: まず **`.tscn` のみ**で済む **静的ヘッダー**・**静的 Panel カード**から当てる。**`Label.new()` + 暗地前提の明色 override** は、白い `Phase4SummaryCard` 内へ載せ替えるには **`.gd` で色を直す**最小補正が必要（財務 `6c3dc43` / OM `2f808e5` / 戦術 `7bbbb4e` / 契約人事 `1df4820` で実績あり）。**ロスター表**は **`TableCard` + `Phase4TableHead` / `Phase4TableCell`**（`f866f5b` / `407f014`）— 詳細は §15.1 ロスター節。
- **契約 / 人事サマリー**（`contract_personnel_summary_view.tscn` / `contract_personnel_summary_view.gd`）: **詳細画面 Theme 横展開第8号相当・残り第1段**（`5d1afa2`）＋**RiskRows / PlayerRows 動的行文字色の最小補正**（`1df4820`）＋**第2段（最小）PlayerRows / RiskRows 行区切り**（`6b26fa3` / `97b26a8`）＋**Body本格・最小 PlayerRows / RiskRows 内側余白**（`f19ed9b` / `420f240`）。ルート Theme。**`Phase4HeaderCard`**。**`Phase4SummaryCard`**: 契約概要・ロスター構成・**RiskCard**・**PlayersCard**。**`Phase4WarningCard`**: 注意。**`1df4820`**: 動的行色。**`6b26fa3` / `97b26a8`**: PlayerRows / RiskRows 行間 **`HSeparator`**（**契約・人事の最小行区切りは両方完了**）。**`f19ed9b` / `420f240`**: PlayerRows / RiskRows の **`MarginContainer` 内側余白**（**Body余白横展開レーン 5 Body 完了** — **各 Body 全体の第2段完了ではない**）。選定: PlayerRows **`8034a1d`**、RiskRows **`9411623`**。詳細は §15.1 契約・人事節。
- **ロスター閲覧**（`roster_view.tscn` / `roster_view.gd`）: **詳細画面 Theme 横展開の締め（第9号相当）・第1段**（`f866f5b` + `407f014`）＋**第2段（最小）RowList 選手行間 HSeparator**（`8a95fcf`・`_apply_snapshot` players ループ）＋**ロスター本格整備・第1手 平坦行背景**（`9445d0e`・`_add_player_row` のみ）＋**ロスター本格整備・第2手 主要列強調**（`6c1e25f`・`_add_player_row` のみ）＋**ロスター本格整備・第3手 状態列視認補助**（`746e861`・`_add_player_row` のみ）。ルート Theme。**`Phase4HeaderCard`**。**`Scroll/TableCard`**＝`Phase4SummaryCard`、**`%RowList`** 内9列表は **`Phase4TableHead` / `Phase4TableCell`**（**選手行カード化・9列本格・列幅本格は未対応**）。詳細は §15.1 ロスター節。
- **施設サマリー閲覧**（`facility_summary_view.tscn`）: **詳細画面 Theme 横展開第1号・第1段**（`5987821`）。ルート Theme。**`HeaderCard`**＝**`Phase4HeaderCard`**、**`SummaryCard`**＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。**Scroll 内**の `facility_summary_view.gd` による **`Label.new()`** は**暗背景＋明文字のまま**（**第2段**）。**`.gd`・Theme `.tres`・DTO/export/mock 不変**。選定は **`23a8fcf`** 調査（Header+Summary 型・`.tscn` のみ・HeaderNavRow 到達・DTO 安定・クラブ史/順位表へ横展開しやすい）。
- **クラブ史閲覧**（`club_history_view.tscn`）: **詳細画面 Theme 横展開第2号・第1段**（`682a941`）。ルート Theme。**`HeaderCard`**＝**`Phase4HeaderCard`**、**`SummaryCard`**＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。**Scroll 内**の段落・シーズン表（`club_history_view.gd` の **`Label.new()` / シーズン表 `HBoxContainer`**）は**暗背景＋明文字のまま**（**第2段**）。**`.gd`・Theme `.tres`・DTO/export/mock 不変**。選定は **`64abb9c`**（施設第2段より先に横展開推奨・同型・順位表より Scroll ギャップ小）。
- **順位表閲覧**（`standings_view.tscn`）: **詳細画面 Theme 横展開第3号・第1段**（`927e918`）。ルート Theme。**`HeaderCard`**＝**`Phase4HeaderCard`**、**`SummaryCard`**＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。**Scroll 内**の **8 列表・動的行**（`standings_view.gd` の **`Label.new()`** 等）は**暗背景＋明文字のまま**（**第2段**）。**`.gd`・Theme `.tres`・DTO/export/mock 不変**。
- **日程閲覧**（`schedule_view.tscn` / `schedule_view.gd`）: **詳細画面 Theme 横展開第4号・第1段**（`440c3f6`）＋**第2段・前半**（`986c4ab`）＋**第2段・後半（最小）**（`7fecb99`）＋**追加最小 advance_hint**（`a62b3a7`・**なし/あり表示確認済み**）＋**追加最小 empty_message**（`463e74b`）＋**追加最小「今後の予定」見出し**（`a24cf6f`）＋**追加最小 upcoming 試合間 HSeparator 整理**（`a9fa054`）＋**中規模改善第1手 upcoming 試合カード内情報階層**（`fa36271`）＋**日程本格整備・第2手 advance_hint 情報階層**（`5a98e31`）＋**日程本格整備・第3手 empty_message 本文情報階層**（`065197b`）。ルート Theme。**`HeaderCard`**＝**`Phase4HeaderCard`**。**`SummaryCard`**・**`NextGameCard`**・**upcoming 試合ブロック**（`_add_upcoming_block` — **`fa36271` で line1 HBox 分解・line2 主役化・line3 副情報**）・**advance_hint ブロック**（`_add_advance_hint_block` — **`5a98e31` で block 主役・one_line 副情報**）・**empty_message（お知らせ）ブロック**（`_add_empty_message_block` — **`065197b` で本文主役化・separation 6**）・**「今後の予定」セクション見出し**（`_add_upcoming_section_heading`）＝**`Phase4SummaryCard`**（**`notes` は `_footer_note` — 対象外**）。**試合間区切りは親 VBox `separation=8`**。**ScrollContent 全体整理**は**別タスク**。選定: 第1段 **`a5eec31`**、中規模第1手 **`ff2b5e1`**。詳細は §15.1 日程節。
- **財務サマリー閲覧**（`finance_summary_view.tscn` / `finance_summary_view.gd`）: **詳細画面 Theme 横展開第5号・第1段**（`4b43da5`）＋**履歴行文字色の最小補正**（`6c3dc43`）＋**第2段（最小）HistoryBody 行区切り**（`d57b021`）＋**Body本格・最小 HistoryBody 内側余白**（`307e719`）＋**Body本格整備・中規模第1手 平坦 Panel 行ラップ**（`c762d88`・`_fill_history_rows` 履歴行ループのみ）。選定: 第1段 **`99c279d`**、Body系第2段最小 **`d2c08d1`**、Body本格最小入口 **`a5d9d0e`**。詳細は §15.1 財務節。
  - **`4b43da5` 実装範囲**（**`finance_summary_view.tscn` のみ**）: ルート **`phase4_readonly_core.tres`**。**`HeaderCard`**＝**`Phase4HeaderCard`**。**Scroll/ScrollContent 内** **Finance / Prior / Salary / History / Caution** の5枚＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。Header・各カード・**`NotesFooterLabel`** のラベル濃色化。**`HomeNavButton` / `%DataSourceLabel` / from_python・mock 読込は維持**。
  - **`4b43da5` 実装境界**: **`.gd`・Theme `.tres`・DTO/export/mock 未変更**。**`%HistoryBody` 内動的履歴行は未変更**（第2段扱い）。
  - **目視で発見された課題**: **財務履歴カード内**の動的履歴行テキストが**白カード上で薄く読みにくい**（暗背景向け明色のまま）。
  - **`6c3dc43` 補正範囲**（**`finance_summary_view.gd` のみ・第2段本格整備ではない**）: **`_fill_history_rows`** の履歴行 `Label` と履歴なし **`empty_lab`** の **`font_color`** を **`Color(0.16, 0.2, 0.3)`**（白カード本文と同系）へ。**HistoryBody 構造・履歴行の文言・件数・生成順・JSON key・scene・Theme・DTO は未変更**。
  - **第2段（第1段・色補正時点）**: **HistoryBody 行区切り**（**`d57b021` で対応**）・**内側余白**（**`307e719` で対応 — Body本格最小入口**）・構造整理（**Panel 化等は未着手**）。
  - **ユーザー環境 Godot**: **CardNavMenu → 財務サマリー OK**・**表示・Header/5静的カード・DataSourceLabel OK**・**`6c3dc43` 後は財務履歴の可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
  - **横展開テンプレ**: 日程の **Scroll 内カード型**に続き、**Scroll 内複数静的 Panel 型**でも第1段が成功 — **財務で手順を固め、OM 等への判断材料**となる。
- **オーナーミッション / クラブ評価閲覧**（`owner_mission_view.tscn` / `owner_mission_view.gd`）: **詳細画面 Theme 横展開第6号・第1段**（`e6acce0`）＋**今季ミッション動的行文字色の最小補正**（`2f808e5`）＋**第2段（最小）MissionsBody 行区切り**（`5a3ae2c`）＋**Body本格・最小 MissionsBody 内側余白**（`d4c0372`）。選定: 第1段 **`130137a`**、Body系第2段最小第2号 **`bb6866d`**、Body本格余白横展開第1号 **`b7f5bc4`**。詳細は §15.1 OM 節。
  - **`e6acce0` 実装範囲**（**`owner_mission_view.tscn` のみ**）: ルート **`phase4_readonly_core.tres`**。**`HeaderCard`**＝**`Phase4HeaderCard`**。**Scroll/ScrollContent 内** **Trust / Missions / Eval / Caution** の4枚＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。Header・各カード・**`NotesFooterLabel`** のラベル濃色化。**`HomeNavButton` / `%DataSourceLabel` / from_python・mock 読込は維持**。
  - **`e6acce0` 実装境界**: **`.gd`・Theme `.tres`・DTO/export/mock 未変更**。**`%MissionsBody` 内動的ミッション行は未変更**（第2段扱い）。
  - **目視で発見された課題**: **今季ミッションカード内**の MissionsBody 動的行テキストが**白カード上で薄く読みにくい**（暗背景向け明色のまま）。
  - **`2f808e5` 補正範囲**（**`owner_mission_view.gd` のみ・第2段本格整備ではない**）: **`_fill_mission_rows`** のミッション行 `Label` とミッションなし **`lab`** の **`font_color`** を **`Color(0.16, 0.2, 0.3, 1)`**（白カード本文と同系）へ。**MissionsBody 構造・ミッション行の文言・件数・生成順・JSON key・scene・Theme・DTO は未変更**。
  - **第2段（第1段・色補正時点）**: **MissionsBody 行区切り**（**`5a3ae2c` で対応**）・**内側余白**（**`d4c0372` で対応 — Body本格余白横展開第1号**）・構造整理（**Panel 化等は未着手**）。
  - **ユーザー環境 Godot**: **CardNavMenu #8 → オーナーミッション OK**・**表示・Header/4静的カード・DataSourceLabel OK**・**`2f808e5` 後は今季ミッションの可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
  - **横展開テンプレ**: 財務に続き **OM でも Scroll 内複数静的 Panel 型**へ第1段が成功 — **動的行可読性の最小補正も財務 `6c3dc43` と同手順** — **戦術 / 契約人事 / ロスターへ進む判断材料**。
- **戦術 / ローテーションサマリー閲覧**（`tactics_summary_view.tscn` / `tactics_summary_view.gd`）: **詳細画面 Theme 横展開第7号・第1段**（`44b0584`）＋**選手ロール動的行文字色の最小補正**（`7bbbb4e`）＋**第2段（最小）PlayerRolesBody 行区切り**（`c9216d0`）＋**Body本格・最小 PlayerRolesBody 内側余白**（`2c637f2`）。選定: 第1段 **`6afb201`**、Body系第2段最小第3号 **`b73feb7`**、Body本格余白横展開第2号 **`1f11c2d`**。詳細は §15.1 戦術節。
  - **`44b0584` 実装範囲**（**`tactics_summary_view.tscn` のみ**）: ルート **`phase4_readonly_core.tres`**。**`HeaderCard`**＝**`Phase4HeaderCard`**。**Scroll/ScrollContent 内** **Overview / Attack / Defense / Rotation / PlayerRoles / Notes** の6枚＝**`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。Header・各カードのラベル濃色化。**`HomeNavButton` / `%DataSourceLabel` / from_python・mock 読込は維持**。
  - **`44b0584` 実装境界**: **`tactics_summary_view.gd`・Theme `.tres`・export / mock JSON 未変更**。**`%PlayerRolesBody` 動的選手ロール行は第2段扱いで未変更**。
  - **目視課題**: 第1段適用後、**選手ロールカード内**の動的選手ロール行が**白カード上で薄く読みにくい**。
  - **`7bbbb4e` 補正範囲**（**`tactics_summary_view.gd` のみ・第2段本格整備ではない**）: **`_fill_player_roles`** の選手ロール行 `Label` と空表示 **`lab`** の **`font_color`** を **`Color(0.16, 0.2, 0.3, 1)`** へ（白カード本文と同系）。**PlayerRolesBody 構造・選手ロール行の文言・件数・生成順・JSON key・scene・Theme・DTO は未変更**。
  - **第2段（第1段・色補正時点）**: **PlayerRolesBody 行区切り**（**`c9216d0` で対応**）・**内側余白**（**`2c637f2` で対応 — Body本格余白横展開第2号**）・構造整理（**Panel 化等は未着手**）。
  - **ユーザー環境 Godot**: **CardNavMenu #9 → 戦術サマリー OK**・**表示・Header/6静的カード・DataSourceLabel OK**・**`7bbbb4e` 後は選手ロールの可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
  - **横展開テンプレ**: 財務・OM に続き **戦術でも Scroll 内複数静的 Panel 型**（6枚）へ第1段が成功 — **動的行色補正は財務 `6c3dc43` / OM `2f808e5` と同手順** — **契約人事 / ロスターへ進む判断材料**。
- **ホーム**（`home_dashboard.tscn`）: **ルートに Theme なし**。**`HeaderCard` のみ**に `phase4_readonly_core.tres` を割当し **`Phase4HeaderCard`**。**`83d7fc0` で HeaderCard 内に ClubBand 風クラブ帯**。**`a5e548f` で `MainRow` 左に表示用 `LeftRail`（200px・大分類 5・クリック不可）** — 構造は §15.2 参照。**MetricsRow** 3 枚 + **`Scroll` 以下**（**`CardNavMenu` 含む**）**`Phase4SummaryCard` / `Phase4WarningCard`**（**`d9bd713` で `CardNavMenu` も最小 Theme 化済み**）。**Scroll 内の暗色カード問題は解消済み**。**`91cfaed` で `club_summary` 状況メモ化**（export / mock のみ）。**`home_dashboard.gd`・JSON / Python / DTO・Theme `.tres` は不変**。**HeaderNavRow・CardNavMenu・10 画面導線は維持**（実操作導線）。**LeftRail は表示のみ**。
- **読込・導線**: `from_python` / mock、**HeaderNavRow のボタン数・接続・遷移先のシーン定義は変更していない**（`afb482d` は HeaderCard とラベル色・SubResource 整理のみ）、**Godot から Python 自動起動なし**（§14.1 と同じ）。
- **運用**: シーン保存後は **UID 参照エラー**が出ないか Godot で確認。**エディタ実行後**は `git status` で意図しない差分が混ざっていないか確認（`*_from_python.json` は **コミットしない**）。**UID の再シリアライズ**で他画面参照が壊れないか、差分レビュー時に注意。

**関連コミット（Theme 周辺・本節で列挙する必要最小限）**: `26fa722` → `b572a7e` → `8bf6788` → `4c1cb08` → `2995a22` → `77c5d04` → `310ebed` → `2bb594c` → `d33edb6` → `afb482d`（契約人事ヘッダー適用は `b319af3`）。他の調査・文言コミットは `godot/README.md` や履歴を参照。

### 15.2 本番ホームワイヤー sandbox（`godot/scenes/home_production_wire_preview.tscn`）

- **役割**: **レイアウト・情報設計**の sandbox。本番ホームの**情報密度・左レール＋上部クラブ帯・色味**を、**JSON / Python / `change_scene_to_file` なし**で研究する固定文言 preview。**Theme と情報設計の研究用**であり、**本番 GUI が確定したわけではない**（**まだ正式 GUI 完成ではない**）。
- **最新到達点（2026-05）**:
  - 左レールは**ナビ風の見た目**へ前進（**現在地「ホーム」**の強調、大分類 **ホーム / チーム / リーグ / 経営 / クラブ**）。
  - **ClubBand** に**仮ロゴ枠**（**SG / LOGO**、実画像なし）を追加し、**クラブ運営感・スポーツ GM 画面感**の検証を強めた。
  - **左レール現在地**の枠線アクセントは、仮ロゴ枠の**琥珀系**に**馴染む暖色**へ**最小調整**済み（`StyleBoxFlat_nav_active` の `border_color` のみ・Theme 非変更）。
  - **CardShortcuts** は **2 行から 1 行**へ圧縮し、左レール大分類との**役割重複感を軽減**（`詳細画面: …` の補助案内は維持）。
  - **ClubBand と中央カード**の地区／勝敗／順位の**情報重複**は調査済み。中央の**「順位・成績」カード**は、ClubBand と同じ数字の**繰り返し**ではなく**立ち位置判断**へ寄せ、本文（`CardStandingsBody`）を **`PO圏まで 2.0差 / 直近5試合 3勝2敗`** に変更済み（タイトル「順位・成績」は維持）。
  - **CardTasks / CardNews / CardClubState** の役割は調査済み（`reports/godot_phase4_home_wire_task_news_state_survey_2026-05.txt` を参照。追跡されない場合あり）。
  - **CardNewsBody** は **`ホーム快勝、次戦へ弾み`** の **1 行ヘッドライン**へ短縮済み（ニュースは**雰囲気づくり**として軽く残し、右列では **CardTasks を主役**に見せる方向）。
  - **CardClubBody** は **`サラリー余力あり / 士気良好`** の **1 行要約**へ短縮済み。**ClubState** は詳細ではなく、**キャップ余力と士気の短い状態要約**として扱う方向（ClubBand の資金・信頼と**重く被らない**）。
  - **中央カード**は**低〜中密度のまま**維持。
  - **ユーザー環境 Godot 4.6.2** での sandbox 表示確認・**UID 問題なし**・**実行後の不要差分なし**は手元運用の目安として README に同期。
  - **右サマリー列あり版の比較scene**（`godot/scenes/home_production_wire_preview_right_summary.tscn`）: **別ファイル**で追加済み。UID 安定化（`cf8012c`）後、**Godot 4.6.2 で F6 表示確認 OK**。右列は**キャップ余力・士気・ロスター・契約警告・疲労リスク**の短い「状態サマリー」。**ClubBand や中央カードとの重複は避ける**向きで固定文言を配置。**ただし目視比較では 1280×720 上で中央カードの横幅が狭くなり、現行 2 カラム版より見やすさで劣る可能性**がある。**現時点の本命候補は現行 2 カラム版**（`home_production_wire_preview.tscn`）。右サマリー列あり版は**参考画像寄せ・将来再検討用の比較資産**として残す。**本線 `home_dashboard.tscn` への移植はまだ行わない**。**本線移植判断**では、**可読性・余白・情報密度・本線 DTO との整合**を改めて見る。
  - **本線ホーム Header の ClubBand 風寄せ（`83d7fc0`）**: sandbox 検証の成果を本線へ入れる**第一歩**として、**`home_dashboard.tscn` の HeaderCard 内だけ**を ClubBand 風へ**最小寄せ**した。**当時は左レール本線化は未着手**（**表示用 LeftRail は `a5e548f` で追加 — 次項**）。**中央 2 カラム・右サマリー列の本線化は未着手**。**`HeaderClubBandRow`・`HomeLogoSlot`（`SG` / `LOGO`）・`StyleBoxFlat_home_logo_slot`・`HeaderBandTextCol`** を追加し、**`ClubNameLabel` / `SeasonLabel` / `DataSourceLabel`** はノード名と `unique_name_in_owner` を維持したままクラブ帯内に配置。**`DataSourceLabel` は from_python / mock の読込元表示として維持**（`autowrap_mode = 2` 付与）。**`home_dashboard.gd`・JSON・Python・DTO は未変更**。**HeaderNavRow 5 ボタンと既存 10 画面導線は維持**。**当時の `83d7fc0` の範囲では Scroll 以下は未着手**（**その後 `ed106c8` で `CardNews`、`8676095` で `CardNext`、`762f5bc` で `CardWarnings`、`d18bf1f` で `CardTasks`、`2471b67` で MetricsRow の `CardRank` / `CardMoney` のみ Theme 限定適用** — 次項〜次々々々々項）。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。
  - **本線ホーム Scroll 以下 `CardNews` の Theme 限定適用（`ed106c8`）**: **Scroll 以下の最初の 1 カード見た目寄せ**として **`CardNews` のみ** **`Phase4SummaryCard`** を適用。**大レイアウト移植ではない**。**パネルは Theme 側に任せ**、`CardNews` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**）。**`HNews` / `NewsLabel` を白カード向け濃色に調整**。**`news` の内容・行数・JSON キーは不変**。**`_join_lines`・`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardNews 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**sandbox の `CardNewsBody` 級の 1 行ヘッドラインを本線へ本格導入する場合**は、**`.gd` の表示行数制御**または **export / DTO の `news_headline` 等**を**別工程**で設計する。**現時点では「見た目だけ 1 カード限定で移植した段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardNext` の Theme 限定適用（`8676095`）**: **`CardNews` に続く 2 枚目**として **`CardNext` のみ** **`Phase4SummaryCard`** を適用。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardNext` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**）。**`HNext` / `NextGameLabel` を白カード向け濃色に調整**。**`next_game` の内容・JSON キー・表示ロジックは不変**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardNext 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` は既存の白カード状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardWarnings` の Theme 限定適用（`762f5bc`）**: **`CardNews` / `CardNext` に続く警告カード**として **`CardWarnings` のみ** **`Phase4WarningCard`** を適用。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardWarnings` から **`StyleBoxFlat_warn` の panel override のみ除去**（**SubResource 定義は残存**）。**`HWarn` / `WarningsLabel` をライト警告カード向け濃色に調整**。**`WarningsRow` の初期 `visible = false` は維持**。**`warnings` の内容・JSON キー・表示/非表示ロジックは不変**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardWarnings 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**`762f5bc` 時点では `CardTasks` は未変更**（**`d18bf1f` で SummaryCard — 次項**）。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardTasks` の Theme 限定適用（`d18bf1f`）**: **`CardNews` / `CardNext` に続く SummaryCard 系**として **`CardTasks` のみ** **`Phase4SummaryCard`** を適用。**`CardWarnings` は `Phase4WarningCard` のまま**とし、**警告と ToDo の役割を分離**。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardTasks` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**。**`StyleBoxFlat_warn` も削除していない**）。**`HTasks` / `TasksLabel` を白カード向け濃色に調整**。**`tasks` の内容・JSON キー・最大 3 行表示**は不変（**`_join_lines(d, "tasks", 3)` 不変**）。**`TasksLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardTasks 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardWarnings` は既存の WarningCard 状態を維持**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム MetricsRow `CardRank` / `CardMoney` の Theme 限定適用（`2471b67`）**: 既に **`Phase4SummaryCard` 済み**だった **`CardDivision` に続き**、**`CardRank` / `CardMoney` の 2 枚だけ**を**同一コミット**で **`Phase4SummaryCard`** に適用。**MetricsRow の `CardDivision` / `CardRank` / `CardMoney` 3 枚が白カード系で統一**された。**Scroll 以下の大レイアウト移植ではなく、MetricsRow 内の見た目統一**。**パネルは Theme 側**に任せ、各カードから **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**。**`StyleBoxFlat_warn` も削除していない**）。**`HRank` / `RankRecordLabel` / `HMoney` / `MoneyLabel` を白カード向け濃色に調整**。**`rank_record` / `money` の内容・JSON キー・表示ロジックは不変**（**`_rank_record.text = _txt(d, "rank_record")` / `_money.text = _txt(d, "money")` 不変**）。**`RankRecordLabel` / `MoneyLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。**`CardDivision` / `SecMetricsTitle` / MetricsRow 構造は未変更**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardRank / CardMoney 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` / `CardNext` / `CardTasks` は既存の SummaryCard 状態を維持**。**`CardWarnings` は既存の WarningCard 状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ限定移植している段階」**と明記する。
  - **本線ホーム `club_summary` の状況メモ化（`91cfaed`）**: **`basketball_sim/export/home_dashboard_readonly.py`** の **`_club_summary_lines()`** のみ変更（**`home_dashboard.tscn` / `home_dashboard.gd` / Theme `.tres` は不変**）。**`godot/data/home_dashboard_mock.json`** と **pytest** を追随。**旧**: `club_summary` が **`rank_record` / `division` / `money` / `salary_cap` を段落再掲**。**新**: **シーズン状態**（終了 / 進行 / 未同梱）＋短い補足（**原則 1〜2 行、最大 3 行**）。**トップレベル** `division` / `rank_record` / `money` / `salary_cap` / `owner_trust` / `recent_form` **キーは維持**。**役割分担（現形）**: **MetricsRow**＝`division` / `rank_record` / `money`。**CardTeamExtras**＝`owner_trust` / `salary_cap` / `recent_form`（任意行・カード visible 制御は `.gd` 不変）。**CardSummary**＝`club_summary`（状況メモ）。**CardWarnings**＝`warnings`。**CardTasks**＝`tasks`。**CardNews**＝`news`。**CardNext**＝`next_game`。
  - **本線ホーム `CardTeamExtras` の Theme 限定適用（`dc0182a`）**: **`home_dashboard.tscn` のみ**。**`CardTeamExtras`** に `theme` + **`Phase4SummaryCard`**。**`StyleBoxFlat_card` の panel override のみ除去**（**SubResource は `CardNavMenu` 用に残存**）。**見出し・キー・値ラベルを白カード向け濃色**（`CardTasks` 等と同系）。**`OwnerTrustLabel` / `SalaryCapLabel` / `RecentFormLabel` の `unique_name_in_owner`・visible 制御は不変**。**`home_dashboard.gd`・export・Theme `.tres` は不変**。
  - **本線ホーム `CardSummary` の Theme 限定適用（`1d070ba`）**: **`home_dashboard.tscn` のみ**（**`91cfaed` の状況メモ化の後**）。**`CardSummary`** に **`Phase4SummaryCard`**（**`HSum` / `ClubSummaryLabel` 濃色化**）。**`_join_lines(d, "club_summary")`・JSON キーは不変**。
  - **本線ホーム `CardNavMenu` の Theme 限定適用（`d9bd713`）**: **`home_dashboard.tscn` のみ**。**`CardNavMenu`** に **`Phase4SummaryCard`**（**panel override のみ除去**。**SubResource は残置**）。**`NavTitle` / カテゴリラベルを白カード向け濃色**。**8 ボタン・4 列・14 connection・9 handler 名は不変**。**削除・縮小なし**。
  - **CardNavMenu の情報役割（現在形）**: **中央の画面メニュー** — **ホーム除く詳細画面**への**主入口**（**#7〜#10** 含む）。**HeaderNavRow** と一部重複するが、**経営・戦術系の詳細入口はこちらが主**。**最小 Theme 化済み**（導線は維持）。
  - **施設サマリー閲覧・Phase4 Theme 第1段（`5987821`）** — **9詳細画面 UI 整備のテンプレ候補第1号**:
    - **選定（`23a8fcf`）**: **Header + Summary カード型**・**`.tscn` のみで第1段を閉じやすい**・**HeaderNavRow から到達**（第6画面）・**`facility_summary_readonly` + pytest 安定**・**`club_history_view` / `standings_view` と同型で横展開しやすい**。
    - **実装範囲**: **`facility_summary_view.tscn` のみ**。ルートに **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**、**`SummaryCard`** → **`Phase4SummaryCard`**。**`StyleBoxFlat_header` / `StyleBoxFlat_summary` の panel override のみ除去**（SubResource 定義は残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`**（タイトル・チーム・リーグ段階・DataSource・HomeNav）→ **`SummaryCard`**（施設強化ポイント等の要約）→ **`Scroll/ScrollContent`**（施設一覧・sections — **`.gd` で動的生成**）。
    - **実装境界**: **`facility_summary_view.gd`・Theme `.tres`・export / mock JSON 未変更**。
    - **第2段（未着手）**: **Scroll 内動的 `Label.new()`** の白カード化・行レイアウト整理（**`.gd` 調整が必要**）。**今回の第1段では Scroll は暗地＋明文字のまま許容**。
    - **ユーザー環境 Godot**: **ホーム → 施設サマリー OK**・**表示・Header/Summary 見た目・可読性・DataSourceLabel OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **今後**: **施設の Scroll 第2段**か、**クラブ史・順位表**への同型横展開を判断（**LeftRail クリック化は別工程**）。
  - **クラブ史閲覧・Phase4 Theme 第1段（`682a941`）** — **9詳細画面 UI 整備のテンプレ候補第2号**:
    - **選定（`64abb9c`）**: 施設 `5987821` の横展開テンプレ検証のため **施設第2段（`.gd` 必須）より先**。**`64abb9c` 比較調査** — 同型 Header+Summary・`.tscn` のみ・施設テンプレの再現性確認・順位表より Scroll 表ギャップが小さい。
    - **実装範囲**: **`club_history_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**、**`SummaryCard`** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`** → **`SummaryCard`** → **`Scroll/ScrollContent`**（overview・achievements・honors・events・シーズン履歴表 — **`.gd` で動的生成**）。
    - **実装境界**: **`club_history_view.gd`・Theme `.tres`・export / mock JSON 未変更**。
    - **第2段（未着手）**: **Scroll 内段落・シーズン表**の白カード化・表/行レイアウト整理（**`.gd` 必須**）。**第1段では Scroll は暗地＋明文字のまま許容**。
    - **ユーザー環境 Godot**: **ホーム → クラブ史 OK**・**表示・Header/Summary 見た目・可読性・DataSourceLabel OK**・**Scroll 内段落・シーズン表の残存 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: 施設に続き **クラブ史でも Header + Summary 第1段が成功** — **次は順位表**への同型横展開の判断材料（**`927e918` で完了 — 次項**）。
  - **順位表閲覧・Phase4 Theme 第1段（`927e918`）** — **9詳細画面 UI 整備のテンプレ候補第3号**:
    - **選定**: 施設・クラブ史の第1段テンプレ検証の続き。**`64abb9c` 比較調査**で **順位表**が次候補（同型 Header+Summary・`.tscn` のみ・**HeaderNavRow** 到達・**`standings_readonly` + pytest 安定**）。
    - **実装範囲**: **`standings_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**、**`SummaryCard`** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`** → **`SummaryCard`** → **`Scroll/ScrollContent`**（D1/D2/D3 順位・**8 列表** — **`.gd` で動的生成**）。
    - **実装境界**: **`standings_view.gd`・Theme `.tres`・export / mock JSON 未変更**。
    - **第2段（未着手）**: **Scroll 内 8 列表・動的行**の白カード化・表/行レイアウト整理（**`.gd` 必須**）。**第1段では Scroll は暗地＋明文字のまま許容**。
    - **ユーザー環境 Godot（1280×720）**: **ホーム → 順位表 OK**・**表示・Header/Summary 見た目・可読性・DataSourceLabel OK**・**Scroll 内 8 列表の残存 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: **施設・クラブ史・順位表**の 3 画面で **Header + Summary 第1段**が成功 — **詳細画面の第1段 Theme 横展開パターンが 3 画面で確認**された。
    - **今後**: **残り詳細画面**への同型第1段か、施設/クラブ史/順位表の **Scroll 第2段**（**LeftRail クリック化は別工程**）。
  - **日程閲覧・Phase4 Theme 第1段（`440c3f6`）** — **9詳細画面 UI 整備のテンプレ候補第4号**:
    - **選定（`a5eec31`）**: 3画面完了後、**Scroll 第2段より先に残り詳細への横展開**。**日程**は **HeaderNavRow** 到達・**`schedule_readonly` + pytest 安定**。**`SummaryCard` が `Scroll/ScrollMain` 内**（RootCol 直下型との構造差あり）。
    - **実装範囲**: **`schedule_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**、**`Scroll/ScrollMain/SummaryCard`** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**Header + `SummaryBlockLabel` 濃色化**。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/ScrollMain`**（**`SummaryCard`** → **`NextGameCard`** → **`ScrollContent`** 試合リスト — **`.gd` で動的生成**）。
    - **実装境界**: **`schedule_view.gd`・Theme `.tres`・export / mock JSON 未変更**。
    - **第2段（第1段時点・未着手）**: **`NextGameCard`**（`StyleBoxFlat_nextgame` のまま）・**`ScrollContent` / 試合リスト**（**第2段・前半 `986c4ab` で NextGameCard のみ対応**）。
    - **ユーザー環境 Godot（第1段 `440c3f6`）**: **ホーム → 日程 OK**・**Header/Scroll内Summary 見た目 OK**・**NextGameCard 暗色残存 OK**・**試合リスト残存 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: RootCol 直下 Header+Summary 型に加え、**Scroll 内 SummaryCard 型**でも第1段が成功 — **構造バリエーションへの横展開が開始**された。
  - **日程閲覧・Phase4 Theme 第2段・前半 — NextGameCard 白カード化（`986c4ab`）** — **主要10画面 Theme 第1段完了後の第2段初手**:
    - **選定（`8fc2d91`）**: ロスター第1段記録（`19781ac`）後、**完了済み10画面の第2段候補を比較**。**日程 `NextGameCard`** を第2段初手に推奨 — **理由**: **`.tscn` のみで閉じられる**・**静的1カードでリスクが小さい**・**SummaryCard は白系済みで NextGameCard だけ暗色残り**・**`.gd` の動的行や表改修に入る前の安全な第2段入口**・**ScrollContent / 試合リストは後半へ分割できる**。
    - **実装範囲（`986c4ab`）**: **`schedule_view.tscn` のみ**。**`NextGameCard`** → **`Phase4SummaryCard`**（**`theme_override_styles/panel` 除去**・**`theme_type_variation` へ置換**・**`StyleBoxFlat_nextgame` SubResource 定義は残置**）。**NextGameCard 内ラベル**を白カード向け濃色化（**SectionTitle / NextGameLabel**＝`Color(0.08, 0.11, 0.18, 1)`、**Competition / Round / Opponent**＝`Color(0.16, 0.2, 0.3, 1)`、**HomeAway / Status**＝`Color(0.2, 0.25, 0.36, 1)`）。
    - **実装境界**: **`schedule_view.gd`・Theme `.tres`・export / mock JSON 未変更**。**`%ScrollContent` / 試合リスト未変更**。**HeaderCard / SummaryCard / HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`986c4ab`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**・**日程画面表示 OK**・**HeaderCard / SummaryCard は従来どおり OK**・**NextGameCard 白カード化 OK**・**NextGameCard 内ラベル可読性 OK**・**ScrollContent / 試合リスト残存 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **日程閲覧 Phase4 Theme 第2段・前半完了**（**第2段全体・日程画面の完全仕上げではない**）。
    - **第2段・後半（第1段・前半時点・未着手）**: **upcoming 試合ブロック**・見出し / advance_hint 等（**第2段・後半（最小）`7fecb99` で upcoming のみ対応**）。
  - **日程閲覧・Phase4 Theme 第2段・後半（最小）— upcoming試合ブロック白カード化（`7fecb99`）**:
    - **選定（`20efa29`）**: **`986c4ab` 成功後**、同一画面内の **白/暗ギャップ**を小さくするため **upcoming 試合ブロック**を推奨 — **理由**: **`986c4ab` の続き**・**フル Scroll 整理ではなく `_add_upcoming_block` のみで1関数で閉じられる**・**runtime `PanelContainer` + `Label×3` で白カード化しやすい**・**ロスター表 / 順位表よりリスク低**・**財務 Body 横展開前に日程内で動的ブロック最小成功例を積める**。
    - **実装範囲（`7fecb99`）**: **`schedule_view.gd` のみ**。**`_add_upcoming_block` のみ**。runtime **`PanelContainer`** に **`Phase4SummaryCard`**。**l1 / l2 / l3** を白カード向け濃色化（**l1**＝`Color(0.16, 0.2, 0.3, 1)`、**l2**＝`Color(0.08, 0.11, 0.18, 1)`、**l3**＝`Color(0.2, 0.25, 0.36, 1)`）。
    - **実装境界**: **`schedule_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・件数・並び順・JSON key 未変更**。**`_fill_scroll_body` / `_add_scroll_heading` / `_add_scroll_paragraph` 未変更**。**試合間 `HSeparator` 維持**。**HeaderCard / SummaryCard / NextGameCard / HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`7fecb99`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**・**upcoming 試合ブロック白カード化 OK**・**3 Label 可読性 OK**・**HSeparator 維持 OK**・**試合リスト内容・件数・順序不変 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **日程閲覧 Phase4 Theme 第2段・後半（最小）完了**（**日程 Scroll 全体の第2段完了ではない**）。
    - **別タスク（`7fecb99` 時点）**: 見出し整理、**advance_hint** 整理、**ScrollContent 全体**整理、試合リスト全体の行レイアウト・余白・区切り・カード化（**advance_hint は `a62b3a7` で対応 — 下記**）。
    - **横展開全体の意味**: **第2段初手 NextGameCard（`986c4ab`）に続き、日程内の動的ブロック最小対応にも成功** — **財務 HistoryBody / OM / 戦術 / 契約 Body やロスター表行など、より重い `.gd` 第2段へ進む前の安全な実績**（**日程第2段全体完了ではない**）。
    - **今後**: **日程 Scroll 見出し / advance_hint**、**契約 RiskRows / PlayerRows 行区切り** 等の他画面第2段を個別判断（**LeftRail クリック化は別工程**）。
  - **日程閲覧・Phase4 Theme 第2段・追加最小 — advance_hintブロック白カード化（`a62b3a7`）**:
    - **選定（`b396db9`）**: **Body系第2段（最小）5件完了**（財務 / OM / 戦術 / 契約 PlayerRows / RiskRows）後、日程 Scroll 残りへ安全に戻る。**Scroll 全体ではなく advance_hint 分岐のみ**を最小スライスに選定 — **理由**: **NextGameCard / upcoming は白カード化済み**・**残る見出し / advance_hint / paragraph は暗地＋明色**・**見出し全体や ScrollContent 全体へ進むと範囲が大きい**・**advance_hint 分岐のみなら1関数内の最小変更**・**`Phase4SummaryCard` 白 Panel ラップは `_add_upcoming_block`（`7fecb99`）で実績あり**。
    - **実装範囲（`a62b3a7`）**: **`schedule_view.gd` のみ**。**`_fill_scroll_body` の advance_hint 分岐のみ** — **`_add_advance_hint_block` 新設**。**runtime `PanelContainer`** に **`Phase4SummaryCard`**。**内側 `VBoxContainer`（separation 4）**に見出し / **block** / **one_line** を白カード向け濃色化（見出し＝`Color(0.08, 0.11, 0.18, 1)`、block＝`Color(0.16, 0.2, 0.3, 1)`、one_line＝`Color(0.2, 0.25, 0.36, 1)`）。**advance_hint なし時は `block_s` と `one_s` が両方空なら何も追加しない**（空カードなし）。
    - **実装境界**: **`schedule_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**`_add_upcoming_block` / `_add_scroll_heading` / `_add_scroll_paragraph` 未変更**。**NextGameCard / SummaryCard / HeaderCard 未変更**。**試合リスト内容・件数・順序・JSON key 未変更**。**HomeNavButton / DataSourceLabel / from_python・mock 維持**。
    - **pytest（`a62b3a7`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視・advance_hint なし・`f16450f` 記録）**: **日程画面表示 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**・**HeaderCard / SummaryCard / NextGameCard 従来どおり OK**・**upcoming 試合ブロック維持 OK**・**既存のお知らせ表示 OK**・**画面崩れなし・文字可読性 OK**・**当時データは advance_hint なし**（**白カード未表示**）・**advance_hint なし時の空カードなしは確認済み**。
    - **advance_hint ありデータでの白カード実表示確認**（**`e819da0` 推奨後・ユーザー環境**）:
      - **同梱 `schedule_mock.json` に `advance_hint`（block + one_line）あり**。ユーザー環境では **`schedule_from_python.json` が from_python 優先で hint なし**のため、**一時退避して mock 読込**で確認。**確認後 `schedule_from_python.json` は復元済み**（**削除ではない**）。**復元後 git 差分なし**。
      - **DataSourceLabel**＝**同梱モックJSON**。**advance_hint 白カード表示 OK**・**見出し「進行ヒント（advance_hint）」 OK**・**block / one_line 可読性 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
      - **`a62b3a7` の未確認ギャップ解消** — **実装・pytest・なし時・あり時の表示確認まで完了**。
    - **到達点**: **日程閲覧 — advance_hint ブロック白カード化**（**日程 Scroll 全体の第2段完了ではない**）。
    - **別タスク（`a62b3a7` 時点）**: 日程Scroll見出し全体整理、**ScrollContent 全体**整理、試合リスト全体の行レイアウト整理、試合リスト行の余白・区切り・カード化（**empty_message は `463e74b` で対応 — 下記**）。
    - **横展開全体の意味**: **Body系第2段（最小）完了後、日程 Scroll 残りへ安全に戻る初手として成立** — **advance_hint スライスは表示確認まで完了** — **ただし日程 Scroll 全体の第2段完了ではない**。
  - **日程閲覧・Phase4 Theme 第2段・追加最小 — empty_message（お知らせ）ブロック白カード化（`463e74b`）**:
    - **選定（`4cd3623`）**: **advance_hint 確認完了後**、日程 Scroll 残りの **次スライス**として **empty_message（お知らせ）**を選定 — **理由**: **NextGameCard / upcoming / advance_hint は白カード化・確認済み**・**`_fill_scroll_body` の empty_message 分岐は1箇所のみ**・**`Phase4SummaryCard` 実績（`_add_advance_hint_block` 等）を流用可能**・**`notes` は Scroll 外の `_footer_note` / Footer で本タスク対象外**・**ScrollContent 全体や試合リスト本格整理より安全**。
    - **実装範囲（`463e74b`）**: **`schedule_view.gd` のみ**。**`_fill_scroll_body` の empty_message 分岐のみ** — **`_add_empty_message_block` 新設**。**runtime `PanelContainer`** に **`Phase4SummaryCard`**。見出し「お知らせ」/ 本文 **`empty_msg`** を白カード向け濃色化。**表示条件**は **`upcoming.is_empty() and not empty_msg.is_empty()`** のみ（空カードなし）。
    - **実装境界**: **`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。**`_add_upcoming_block` / `_add_advance_hint_block` / `_add_scroll_heading` / `_add_scroll_paragraph` 未変更**。**notes / Footer 未変更**。NextGameCard / SummaryCard / HeaderCard 未変更。試合リスト・JSON key 未変更。DTO/export/tests/mock 未変更。HomeNavButton / DataSourceLabel 維持。
    - **pytest（`463e74b`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **通常状態**（upcoming あり・`empty_message` 空）で **empty_message 空カードなし OK**。**一時 JSON**（upcoming 空・`empty_message` 非空）で **お知らせ / empty_message 白カード表示 OK**・**見出し「お知らせ」可読性 OK**・**本文可読性 OK**・**upcoming 維持 OK**・**advance_hint 維持 OK**・**notes / Footer 従来どおり OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **日程 Scroll 残りの最小スライス — empty_message（お知らせ）ブロック白カード化**（**日程 Scroll 全体の第2段完了ではない**）。
    - **別タスク（`463e74b` 時点）**: 日程Scroll見出し全体整理、**ScrollContent 全体**整理、試合リスト全体の行レイアウト整理、試合リスト行の余白・区切り・カード化（**「今後の予定」見出しは `a24cf6f` で対応 — 下記**）。
    - **横展開全体の意味**: **日程 Scroll 内で NextGame / upcoming / advance_hint / empty_message の主要小ブロック白カード化が進んだ** — **ただし日程 Scroll 全体の第2段完了ではない**。
  - **日程閲覧・Phase4 Theme 第2段・追加最小 — 「今後の予定」セクション見出し白カード化（`a24cf6f`）**:
    - **選定（`46c934d`）**: **empty_message 確認完了後**、日程 Scroll 残りの **次スライス**として **「今後の予定（upcoming_games）」セクション見出しの表示整理**を選定 — **理由**: **NextGameCard / upcoming / advance_hint / empty_message は白カード化・確認済み**・**`_add_scroll_heading` 呼び出しは1箇所のみ**・**`_add_scroll_paragraph` は未使用**・**ScrollContent 全体や試合リスト本格整理より小さい**・**`Phase4SummaryCard` 実績を流用可能**。
    - **実装範囲（`a24cf6f`）**: **`schedule_view.gd` のみ**。**`_fill_scroll_body` の upcoming 非空時の見出し1箇所のみ** — **`_add_upcoming_section_heading` 新設**。**runtime `PanelContainer`** に **`Phase4SummaryCard`**。見出し Label **「今後の予定」**（ユーザー向け表示として統一）を白カード向け濃色化。
    - **実装境界**: **`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。**`_add_upcoming_block` / `_add_advance_hint_block` / `_add_empty_message_block` 未変更**。**`_add_scroll_heading` / `_add_scroll_paragraph` 定義未変更**（他呼び出しなし）。**notes / Footer 未変更**。NextGameCard / SummaryCard / HeaderCard 未変更。試合リスト内容・件数・順序・HSeparator・JSON key 未変更。DTO/export/tests/mock 未変更。HomeNavButton / DataSourceLabel 維持。
    - **pytest（`a24cf6f`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視・同梱 mock）**: **`schedule_from_python.json` 一時退避 → 同梱 mock 読込 → 確認後復元済み**。**DataSourceLabel**＝**同梱モックJSON**・**「今後の予定」白カード表示 OK**・**見出し可読性 OK**・**upcoming 試合カード表示 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **日程 Scroll 内の「今後の予定」セクション見出し白カード化**（**日程 Scroll 全体の第2段完了ではない**）。**小ブロック・見出し系**: NextGame / upcoming / advance_hint / empty_message / **今後の予定見出し** — **完了**。
    - **別タスク（`a24cf6f` 時点）**: **ScrollContent 全体**整理、試合リスト全体の行レイアウト整理、試合リスト行の余白・区切り・カード化、日程 Scroll 全体の本格整備（**upcoming 試合間 HSeparator は `a9fa054` で対応 — 下記**）。
    - **横展開全体の意味**: **日程 Scroll 内の主要小ブロック・見出しの白カード化が一区切り** — **ScrollContent 全体・試合リスト本格整理は別タスク**。
  - **日程閲覧・Phase4 Theme 第2段・追加最小 — upcoming 試合間 HSeparator 整理（`a9fa054`）**:
    - **選定（`e427d61`）**: **見出し系完了後**、日程 Scroll 残りの **最小スライス**として **upcoming 試合間 HSeparator 廃止**を選定 — **理由**: **NextGame / upcoming / advance_hint / empty_message / 今後の予定見出しは白カード化・確認済み**・**Scroll 内で残る目立つ暗色要素が試合間 HSeparator**・**`ScrollContent` / 親 VBox は既に `separation=8`**・**`_add_upcoming_block` を触らずに済む**・**試合リスト本格整理や ScrollContent 全体より小さい**。
    - **実装範囲（`a9fa054`）**: **`schedule_view.gd` のみ**。**`_fill_scroll_body` の upcoming ループ内のみ** — **`if i < n - 1:` + `_scroll_content.add_child(HSeparator.new())` の2行削除**。**`schedule_view.gd` 内の `HSeparator` 参照なし**。
    - **実装境界**: **`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。**`_add_upcoming_block` / `_add_upcoming_section_heading` / `_add_advance_hint_block` / `_add_empty_message_block` 未変更**。**notes / Footer 未変更**。NextGameCard / SummaryCard / HeaderCard 未変更。upcoming 件数・順序・表示内容・JSON key 未変更。DTO/export/tests/mock 未変更。HomeNavButton / DataSourceLabel 維持。
    - **pytest（`a9fa054`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **upcoming カード間の暗色 HSeparator 消失 OK**・**カード間余白 OK**・**upcoming 8件 / 内容 / 順序維持 OK**・**今後の予定見出し維持 OK**・**advance_hint / empty_message / notes / Footer 維持 OK**・**HomeNavButton 戻り OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **日程 upcoming 試合間 HSeparator 整理完了**（**日程 Scroll 全体の第2段完了ではない**）。**小ブロック・見出し・区切り**: NextGame / upcoming / advance_hint / empty_message / 今後の予定見出し / **試合間 HSeparator 整理** — **完了**。
    - **別タスク（未着手）**: **ScrollContent 全体**整理、試合リスト全体の行レイアウト整理、試合リスト行の余白・区切り・カード化、日程 Scroll 全体の本格整備、**ロスター表第2段（本格）**、**Body 本格整備**。
    - **横展開全体の意味**: **日程 Scroll 内の暗色区切りを除去し、白カード間は既存 separation に統一** — **ScrollContent 全体・試合リスト本格整理は別タスク**。
  - **日程閲覧 — upcoming 試合カード内情報階層整理（`fa36271`）** — **Body余白横展開後の中規模改善第1手**:
    - **選定（`ff2b5e1`）**: **Body余白横展開レーン 5 Body 完了**（`b71a183`）後、**細かい余白 / 区切り微調整を止め**、**中規模以上**へ。**日程 `_add_upcoming_block` 内情報階層**を選定 — **理由**: **1ファイル・1関数で閉じられる**・**試合 / 対戦の可読性がプレイ感に直結**・**ロスター本格（9列）より回帰リスクが低い**・**margin 4/2/4/2 追加ではない構造改善**。
    - **実装範囲（`fa36271`）**: **`schedule_view.gd` のみ**。**`_add_upcoming_block` のみ**。line1 を **HBox + round / competition / home_away**（区切り **` ／ `** を Label で再現）。line2 **`対戦: %s`** 文言維持・**font_size 16** で主役化。line3 **`detail` / `label` 組み立て維持**・副情報色を控えめに。**`PanelContainer` + `Phase4SummaryCard` + 内側 VBox** 維持（**separation 4→6**）。
    - **実装境界**: **`_fill_scroll_body`・他 `_add_*` 未変更**。**`schedule_view.tscn`・Theme `.tres`・project.godot 未変更**。**data JSON / JSON key / DTO/export/tests/mock JSON 未変更**。**upcoming 件数・順序・表示文言の中身未変更**。**Header / Summary / NextGame・advance_hint / empty_message / notes / Footer 未変更**。**HomeNavButton / DataSourceLabel 未変更**。
    - **pytest（`fa36271`）**: schedule 10 / home_dashboard 10 / phase0 smoke 1 / roster 10 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **`schedule_from_python.json` 一時退避 → 同梱 mock → 復元済み**。**DataSourceLabel 同梱モックJSON OK**。**上段メタ横並び OK**。**対戦行可読性 OK**。**detail 副情報 OK**。**件数 / 順序 / 文言維持 OK**。**HomeNavButton 戻り OK**。**エラーなし・復元後差分なし**。
    - **到達点**: **Body余白横展開後の中規模改善第1手 — 日程 upcoming 試合カード内情報階層整理完了**（**日程 ScrollContent 全体整理の完了ではない**。**試合リスト本格全体の完了でもない**）。
    - **進行方針**: **細かい UI 余白調整から、試合カード内の情報設計改善へ切り替えた第1手** — **margin レーンの継続ではない**。
    - **未対応（別タスク）**: **日程 ScrollContent 全体整理**、試合リスト行レイアウトのさらなる本格整理、**ロスター本格整備**、**Body本格中規模整理**、**ゲーム体験寄り機能 / 画面**（**advance_hint 情報階層は `5a98e31` で対応 — 下記**）。
  - **日程閲覧 — 日程本格整備・第2手 — advance_hint ブロック内情報階層整理（`5a98e31`）**:
    - **選定（`9aef110`）**: **ロスター平坦行背景（`9445d0e`）完了後**、次の中規模改善として **日程 advance_hint 情報階層整理**を選定 — **理由**: **`fa36271` の upcoming 情報階層整理が成功済み**・**ロスター第1手後に日程へ戻すことで画面バランスがよい**・**`_add_advance_hint_block` のみで1ファイル・1関数**・**block / one_line の読み分けで進行判断情報が分かりやすくなる**。
    - **実装範囲（`5a98e31`）**: **`schedule_view.gd` のみ**。**`_add_advance_hint_block` のみ** — **block 主役化**（font_size 15・`Color(0.08, 0.11, 0.18, 1)`）、**one_line 副情報化**（font_size 11・`Color(0.32, 0.36, 0.48, 1)`）、inner **separation 4→6**。
    - **実装境界**: **見出し文言維持**。**block / one_line 文言維持**。**JSON key（`advance_hint` / `block` / `one_line`）維持**。**空時非表示維持**。**`_fill_scroll_body` 未変更**。**upcoming / empty_message 未変更**。**Header/Summary/NextGame / notes/Footer 未変更**。**`schedule_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`5a98e31`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **advance_hint表示OK**・**block主役化OK**・**one_line副情報化OK**・**文言維持OK**・**空時非表示維持OK**・**upcoming / empty_message / notes / Footer / Header / Summary / NextGame 維持OK**・**HomeNavButton戻りOK**・**エラーなし・差分なし**。
    - **横展開全体の意味**: **upcomingカード内情報階層整理に続き、advance_hintカードにも情報階層整理を適用** — **細かい余白追加ではなく、日程画面の進行判断情報を読みやすくする構造改善** — **ただし日程ScrollContent全体整理や試合リスト本格全体は未完了**。
    - **到達点**: **日程本格整備・第2手 — advance_hint ブロック内情報階層整理完了**（**日程本格整備全体の完了ではない**）。
    - **未対応（別タスク）**: **日程 ScrollContent 全体整理**、試合リスト行レイアウトのさらなる本格整理、日程画面全体の統一整理、**ロスター本格整備の続き**、**Body本格中規模整理**、**ゲーム体験寄り機能/画面**（**empty_message 情報階層は `065197b` で対応 — 下記**）。
  - **日程閲覧 — 日程本格整備・第3手 — empty_message（お知らせ）本文の情報階層整理（`065197b`）**:
    - **選定（`930b395`）**: **ロスター主要列強調（`6c1e25f`）完了後**、次の中規模改善として **日程 empty_message（お知らせ）本文情報階層整理**を選定 — **理由**: **upcoming / advance_hint はすでに情報階層整理済み**・**empty_message は本文 font 13 のままで相対的に弱かった**・**`_add_empty_message_block` のみで1ファイル・1関数**・**日程2手 → ロスター2手の交互改善後、日程へ戻す流れとして自然**・**試合予定がない場合や補足メッセージの理解がしやすくなる**。
    - **実装範囲（`065197b`）**: **`schedule_view.gd` のみ**。**`_add_empty_message_block` のみ** — inner **separation 4→6**、本文 **font_size 13→15**、本文 **`font_color` `Color(0.08, 0.11, 0.18, 1)`**（advance_hint block 同系）。
    - **実装境界**: **見出し「お知らせ」文言 / font / 色 維持**。**本文文言（`empty_msg`）維持**。**JSON key 維持**。**空時 / 表示時の条件維持**。**`_fill_scroll_body` 未変更**。**upcoming / advance_hint 未変更**。**notes / Footer 未変更**。**Header / Summary / NextGame 未変更**。**`schedule_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`065197b`）**: schedule 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **empty_message表示OK**・**見出し維持OK**・**本文読みやすさOK**・**本文文言維持OK**・**表示/非表示条件維持OK**・**upcoming / advance_hint / notes / Footer / Header / Summary / NextGame 維持OK**・**DataSourceLabel維持OK**・**HomeNavButton戻りOK**・**エラーなし・差分なし**。
    - **横展開全体の意味**: **upcoming・advance_hint に続き empty_message もカード内情報階層を整理** — **細かい余白追加ではなく日程画面内の補足・案内情報を読みやすくする構造改善** — **ただし日程ScrollContent全体整理や試合リスト本格全体は未完了**。
    - **到達点**: **日程本格整備・第3手 — empty_message（お知らせ）本文の情報階層整理完了**（**日程本格整備全体の完了ではない**）。
    - **未対応（別タスク）**: **日程 ScrollContent 全体整理**、試合リスト行レイアウトのさらなる本格整理、日程画面全体の統一整理、**ロスター本格整備の続き**、**Body本格中規模整理**、**ゲーム体験寄り機能/画面**、**Python本体 / ゲームロジック側への復帰検討**。
  - **財務サマリー閲覧・Phase4 Theme 第2段（最小）— HistoryBody 履歴行区切り（`d57b021`）** — **Body系第2段テンプレ第1号**:
    - **選定（`d2c08d1`）**: **日程**は NextGameCard（`986c4ab`）＋ upcoming 最小（`7fecb99`）まで完了。**日程残り**は見出し / advance_hint / Scroll 全体が絡み**中〜大**。**財務 HistoryBody** は**白カード内**・**色補正済み（`6c3dc43`）**・**最大5件**・**HSeparator のみなら1関数・1コミット**・**OM / 戦術 / 契約へ横展開しやすい**。
    - **実装範囲（`d57b021`）**: **`finance_summary_view.gd` のみ**。**`_fill_history_rows` のみ**。履歴行 `Label` 追加後 **`i < lim - 1` のとき `HSeparator.new()`**。**履歴なし時は HSeparator なし**。
    - **実装境界**: **`finance_summary_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・件数・並び順・JSON key 未変更**。**`6c3dc43` の font_color 維持**。**HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`d57b021`）**: finance_summary 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 財務サマリー遷移 OK**・**履歴行区切り OK**・**最終行後の不要区切りなし OK**・**履歴行可読性 OK**・**Header/5静的カード OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）第1号 — 財務 HistoryBody 動的履歴行の行区切り追加完了**（**財務 HistoryBody 全体の第2段完了ではない**）。
    - **別タスク（`d57b021` 時点・未着手）**: **HistoryBody の Panel 化**、履歴行カード化、余白・行レイアウト本格調整、**OM / 戦術 / 契約人事**への段階的横展開（**内側余白最小は `307e719` で対応 — 下記**）。
    - **横展開全体の意味**: **日程第2段に続き、Body系第2段の最小テンプレ第1号として成功** — **一括横展開ではなく OM → 戦術 → 契約の順で安全に進める**。
  - **財務サマリー閲覧・Phase4 Theme 第2段（Body本格・最小）— HistoryBody 履歴行の内側余白（margin）追加（`307e719`）** — **Body本格整備の最小入口**:
    - **選定（`a5d9d0e`）**: **Body系第2段（最小）行区切り 5/5 完了**（財務 / OM / 戦術 / 契約 PlayerRows / RiskRows）。**日程小粒改善**は一区切り。**ロスター第2段（最小）**（`8a95fcf`）完了。**ロスター本格**（9列 / tooltip / 列幅）は**中〜大**。**財務 HistoryBody** は**1画面・1関数**（`_fill_history_rows`）で切れるため安全。**Panel 化・行カード化ではなく、まず内側余白のみ**が最小スライス。
    - **実装範囲（`307e719`）**: **`finance_summary_view.gd` のみ**。**`_fill_history_rows` の履歴行 `Label` 追加部分のみ**。各履歴 `Label` を **`MarginContainer` でラップ** — **左 4px / 上 2px / 右 4px / 下 2px**。**`margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL`**。**`_history_body.add_child(margin)`**（Label 直置きから変更）。
    - **実装境界**: **`finance_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`i < lim - 1` の HSeparator** 位置・条件未変更。**履歴文言・`lim = mini(rows.size(), 5)`・並び順・`font_color` / `font_size` 未変更**。**空表示** `（履歴がありません）` は **margin ラップなし**。**HeaderCard / 静的5カード・DataSourceLabel / HomeNavButton 未変更**。**JSON key / DTO / export / tests / mock JSON 未変更**。
    - **pytest（`307e719`）**: finance_summary 10 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **HistoryBody 履歴行の内側余白 OK**。**HSeparator 維持 OK**。**最終履歴行後の不要 HSeparator なし OK**。**履歴文言 / 件数 / 順序維持 OK**。**HeaderCard / 静的5カード維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホーム復帰 OK**。**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body本格整備の最小入口 — 財務 HistoryBody 履歴行の内側余白（margin）追加完了**（**財務 HistoryBody 全体の第2段完了ではない**。**Body本格整備全体の完了でもない**）。
    - **横展開全体の意味**: **Body系第2段（最小）行区切りパターン完了後、Body本格整備の入口として余白改善に入った** — **OM / 戦術 / 契約 margin は `d4c0372` / `2c637f2` / `f19ed9b` / `420f240` で対応**。
    - **未対応（`307e719` 時点・別タスク）**: **HistoryBody の Panel 化**、履歴行カード化、余白・行レイアウト本格調整、**OM / 戦術 / 契約への横展開**、**Body系本格整備の中規模整理**、**ロスター本格整備**、**日程 ScrollContent / 試合リスト本格整備**（**平坦 Panel 行ラップは `c762d88` で対応 — 下記**）。
  - **財務サマリー閲覧 — Body本格整備・中規模第1手 — HistoryBody 履歴行の平坦 Panel 行ラップ（`c762d88`）**:
    - **選定（`11fde1b`）**: **ロスター状態列視認補助（`746e861`）完了後**、次の中規模改善として **Body本格整備・中規模第1手**を選定 — **理由**: **日程3系統・ロスター3読み取りポイントの typography レーンは一区切り**・**5 Body 全体ではなく財務 HistoryBody のみで Panel 行ラップをパイロット**・**`9445d0e` の平坦行背景を低リスクに横展開**・**`_fill_history_rows` の履歴行ループのみで1コミット**。
    - **実装範囲（`c762d88`）**: **`finance_summary_view.gd` のみ**。**`_fill_history_rows` の履歴行追加ループのみ** — **PanelContainer → MarginContainer → Label**。**StyleBoxFlat** 背景 **`Color(0.965, 0.975, 0.99, 1)`**、**content margin 4**、**角丸 2**、**枠線なし**。**空表示分岐は未変更**。
    - **実装境界**: **履歴文言・件数 `lim=5`・順序・JSON key 維持**。**空表示「（履歴がありません）」維持**。**MarginContainer 内側余白・Label font/autowrap 維持**。**HSeparator ロジック維持**（**Panel 行の間・最終行後なし**）。**Summary / finance_items / notes 未変更**。**DataSourceLabel / HomeNavButton 維持**。**`finance_summary_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`c762d88`）**: finance_summary 10 / home_dashboard 10 / roster 10 / schedule 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **HistoryBody 履歴行 Panel 表示 OK**。**行背景が派手すぎない OK**。**履歴文言/件数/順序/空表示維持 OK**。**HSeparator 維持 OK**。**Summary / finance_items / notes 維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton 戻り OK**。**エラーなし・差分なし**。
    - **Composer 2.5 指定運用**: **`c762d88` は Composer 2.5 指定での実装** — **報告ベースでは指示外変更なし** — **モデル変更を理由に作業範囲を広げていない**。
    - **横展開全体の意味**: **5 Body 余白横展開後、初めて Body の「行単位の情報カード化」に踏み込む中規模パイロット** — **財務 HistoryBody のみに限定** — **OM / 戦術 / 契約 Body への横展開は別判断** — **Body本格整備全体や5 Body 横展開は未完了**。
    - **到達点**: **Body本格整備・中規模第1手 — 財務 HistoryBody 履歴行の平坦 Panel 行ラップ完了**（**Body本格整備全体の完了ではない**）。
    - **未対応（別タスク）**: **財務 HistoryBody のさらなる本格整理**、**OM / 戦術 / 契約 Body への Panel 行ラップ横展開検討**、**Body 共通方針の整理**、**日程 ScrollContent**、**ロスター本格続き**、**ゲーム体験寄り機能/画面**、**Python本体復帰検討**。
  - **オーナーミッション / クラブ評価閲覧・Phase4 Theme 第2段（最小）— MissionsBody ミッション行区切り（`5a3ae2c`）** — **Body系第2段テンプレ第2号**:
    - **選定（`bb6866d`）**: **財務 HistoryBody 行区切り（`d57b021`）**が成功。**OM MissionsBody** は**白カード内**・**色補正済み（`2f808e5`）**・**`_fill_mission_rows` の1関数**・**財務と同型の HSeparator**・**複数行ミッションブロックの区切り効果が大きい**・**戦術 / 契約より先の第2号として安全**。
    - **実装範囲（`5a3ae2c`）**: **`owner_mission_view.gd` のみ**。**`_fill_mission_rows` のみ**。有効ミッションを配列化 → **`for i in range(n)`** で Label 生成 → **`i < n - 1` のとき `HSeparator.new()`**。**ミッションなし時は HSeparator なし**。
    - **実装境界**: **`owner_mission_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・件数上限・並び順・JSON key 未変更**。**`_mission_block_text` 未変更**。**`2f808e5` の font_color 維持**。**HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`5a3ae2c`）**: owner_mission 13 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → オーナーミッション遷移 OK**・**MissionsBody 行区切り OK**・**最終行後の不要区切りなし OK**・**ミッション行可読性 OK**・**Header/4静的カード OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）第2号 — OM MissionsBody 動的ミッション行の行区切り追加完了**（**OM MissionsBody 全体の第2段完了ではない**）。
    - **別タスク（`5a3ae2c` 時点・未着手）**: **MissionsBody の Panel 化**、ミッション行カード化、余白・行レイアウト本格調整、**戦術 / 契約人事**への段階的横展開（**内側余白最小は `d4c0372` で対応 — 下記**）。
    - **横展開全体の意味**: **財務に続き Body 系第2段（最小）第2号として成功** — **次候補は戦術 PlayerRolesBody → 契約 RiskRows / PlayerRows**。
  - **オーナーミッション / クラブ評価閲覧・Phase4 Theme 第2段（Body本格・最小）— MissionsBody ミッション行の内側余白（margin）追加（`d4c0372`）** — **Body本格整備の余白横展開第1号**:
    - **選定（`b7f5bc4`）**: **財務 HistoryBody 内側余白（`307e719`）**が成功。**OM MissionsBody** は**白カード内**・**HSeparator 最小完了（`5a3ae2c`）**・**複数行ミッションブロックで余白効果が大きい**・**`_fill_mission_rows` の1関数**・**財務 margin パターンをそのまま横展開可能**・**Panel 化・行カード化より先に余白のみが安全**。
    - **実装範囲（`d4c0372`）**: **`owner_mission_view.gd` のみ**。**`_fill_mission_rows` のミッション行追加ループ部分のみ**。各ミッション `Label` を **`MarginContainer` でラップ** — **左 4px / 上 2px / 右 4px / 下 2px**（財務 `307e719` と同値）。**`margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL`**。**`margin.add_child(lab)` → `_missions_body.add_child(margin)`**。
    - **実装境界**: **`owner_mission_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`i < n - 1` の HSeparator** 位置・条件未変更。**ミッション文言・`_mission_block_text`・件数・並び順・`font_color` / `font_size` 未変更**。**空表示** `今季ミッションはありません。` は **margin ラップなし**。**HeaderCard / 静的4カード・DataSourceLabel / HomeNavButton 未変更**。**JSON key / DTO / export / tests / mock JSON 未変更**。
    - **pytest（`d4c0372`）**: owner_mission 13 / home_dashboard 10 / finance_summary 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **MissionsBody ミッション行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**ミッション文言 / 件数 / 順序維持 OK**。**HeaderCard / 静的4カード維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホーム復帰 OK**。**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body本格整備の余白横展開第1号 — OM MissionsBody ミッション行の内側余白（margin）追加完了**（**財務 `307e719` パターンの OM 横展開**。**OM MissionsBody 全体の第2段完了ではない**。**Body本格整備全体の完了でもない**）。
    - **横展開全体の意味**: **財務 HistoryBody 余白成功後、Body 本格整備の余白レーンへ OM を第1号として適用** — **戦術は `2c637f2` で対応**。**契約 margin は `f19ed9b` / `420f240` で対応**。
    - **未対応（別タスク）**: **MissionsBody Panel 化**、ミッション行カード化、余白・行レイアウト本格調整、**Body系本格整備の中規模整理**、**ロスター本格整備**、**日程本格**、**ゲーム体験寄りの機能 / 画面**。
  - **戦術 / ローテーションサマリー閲覧・Phase4 Theme 第2段（最小）— PlayerRolesBody 選手ロール行区切り（`c9216d0`）** — **Body系第2段テンプレ第3号**:
    - **選定（`b73feb7`）**: **財務 HistoryBody（`d57b021`）**・**OM MissionsBody（`5a3ae2c`）**の行区切りが成功。**戦術 PlayerRolesBody** は**白カード内**・**色補正済み（`7bbbb4e`）**・**`_fill_player_roles` の1関数**・**財務/OMと同型の HSeparator**・**最大8件の選手ロール行に区切り効果**・**契約 RiskRows / PlayerRows より先の第3号として安全**。
    - **実装範囲（`c9216d0`）**: **`tactics_summary_view.gd` のみ**。**`_fill_player_roles` のみ**。有効選手ロールを最大8件まで配列化 → **`for i in range(n)`** で Label 生成 → **`i < n - 1` のとき `HSeparator.new()`**。**選手ロールなし時は HSeparator なし**。
    - **実装境界**: **`tactics_summary_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・最大8件制限・並び順・JSON key 未変更**。**`_player_role_line` 未変更**。**`7bbbb4e` の font_color 維持**。**HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`c9216d0`）**: tactics_summary 15 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 戦術サマリー遷移 OK**・**PlayerRolesBody 行区切り OK**・**最終行後の不要区切りなし OK**・**選手ロール行可読性 OK**・**Header/6静的カード OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）第3号 — 戦術 PlayerRolesBody 動的選手ロール行の行区切り追加完了**（**戦術 PlayerRolesBody 全体の第2段完了ではない**）。
    - **別タスク（`c9216d0` 時点・未着手）**: **PlayerRolesBody の Panel 化**、選手ロール行カード化、余白・行レイアウト本格調整、**契約人事 RiskRows / PlayerRows** への段階的横展開（**内側余白最小は `2c637f2` で対応 — 下記**）。
    - **横展開全体の意味**: **財務・OMに続き Body 系第2段（最小）第3号として成功** — **次候補は契約 RiskRows / PlayerRows**（**2 VBox のため分割または慎重な1コミット**）。
  - **戦術 / ローテーションサマリー閲覧・Phase4 Theme 第2段（Body本格・最小）— PlayerRolesBody 選手ロール行の内側余白（margin）追加（`2c637f2`）** — **Body本格整備の余白横展開第2号**:
    - **選定（`1f11c2d`）**: **財務 HistoryBody 内側余白（`307e719`）**・**OM MissionsBody 内側余白（`d4c0372`）**が成功。**戦術 PlayerRolesBody** は**白カード内**・**HSeparator 最小完了（`c9216d0`）**・**1関数・1Body**・**最大8件・1行Labelで財務に近い**・**契約2箇所より軽い**・**Body最小横展開の歴史順（財務→OM→戦術）に一致**。
    - **実装範囲（`2c637f2`）**: **`tactics_summary_view.gd` のみ**。**`_fill_player_roles` の選手ロール行追加ループ部分のみ**。各 `Label` を **`MarginContainer` でラップ** — **左 4px / 上 2px / 右 4px / 下 2px**（財務・OM と同値）。**`margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL`**。**`margin.add_child(lab)` → `_player_roles_body.add_child(margin)`**。
    - **実装境界**: **`tactics_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`i < n - 1` の HSeparator** 位置・条件未変更。**選手ロール文言・`_player_role_line`・最大8件制限・並び順・`font_color` / `font_size` 未変更**。**空表示** `選手ロール情報はありません。` は **margin ラップなし**。**HeaderCard / 静的6カード・DataSourceLabel / HomeNavButton 未変更**。**JSON key / DTO / export / tests / mock JSON 未変更**。
    - **pytest（`2c637f2`）**: tactics_summary 15 / home_dashboard 10 / owner_mission 13 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **PlayerRolesBody 選手ロール行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**選手ロール文言 / 件数 / 順序維持 OK**。**最大8件制限維持 OK**。**HeaderCard / 静的6カード維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホーム復帰 OK**。**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body本格整備の余白横展開第2号 — 戦術 PlayerRolesBody 選手ロール行の内側余白（margin）追加完了**。**財務 → OM → 戦術 まで MarginContainer パターンの横展開が完了**（**戦術 PlayerRolesBody 全体の第2段完了ではない**。**Body本格整備全体の完了でもない**）。
    - **横展開全体の意味**: **財務・OM の余白成功後、Body 本格整備の余白レーン第2号として戦術に適用** — **契約 margin は `f19ed9b` / `420f240` で対応**。
    - **未対応（別タスク）**: **PlayerRolesBody Panel 化**、選手ロール行カード化、余白・行レイアウト本格調整、**Body系本格整備の中規模整理**、**ロスター本格整備**、**日程本格**、**ゲーム体験寄りの機能 / 画面**。
  - **契約 / 人事サマリー閲覧・Phase4 Theme 第2段（最小）— PlayerRows 主要契約選手行区切り（`6b26fa3`）** — **Body系第2段テンプレ第4号**:
    - **選定（`aac7281`）**: **財務 HistoryBody（`d57b021`）**・**OM MissionsBody（`5a3ae2c`）**・**戦術 PlayerRolesBody（`c9216d0`）**の行区切りが成功。**契約 PlayerRows** は**白カード内**・**色補正済み（`1df4820`）**・**`_fill_player_rows` の1関数**・**`for i in range(lim)`・最大8件で財務/戦術テンプレに近い**・**RiskRows より先に PlayerRows 単体で2関数同時変更を回避**・**1関数1コミットの安全性を優先**。
    - **実装範囲（`6b26fa3`）**: **`contract_personnel_summary_view.gd` のみ**。**`_fill_player_rows` のみ**。既存 **`lim` / `for i in range(lim)`** を維持 → 各 Label 追加直後 **`i < lim - 1` のとき `HSeparator.new()`**。**主要契約選手なし時は HSeparator なし**。
    - **実装境界**: **`contract_personnel_summary_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・最大8件制限・並び順・JSON key 未変更**。**`_fill_risk_rows` 未変更**。**`_fill_player_rows` 以外の関数未変更**。**`1df4820` の font_color 維持**。**HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`6b26fa3`）**: contract_personnel_summary 16 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 契約・人事サマリー遷移 OK**・**PlayerRows 主要契約選手行区切り OK**・**最終行後の不要区切りなし OK**・**主要契約選手行可読性 OK**・**RiskRows 従来どおり OK**・**Header/5静的カード OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）第4号 — 契約・人事 PlayerRows 動的主要契約選手行の行区切り追加完了**（**契約・人事 PlayerRows 全体の第2段完了ではない**。**契約・人事サマリー全体の Body 第2段も完了ではない**）。
    - **別タスク（未着手）**: **RiskRows の人事リスク行区切り**（**第5号 `97b26a8` で完了 — 下記節**）、**PlayerRows の Panel 化**、主要契約選手行カード化、余白・行レイアウト本格調整、**RiskRows / PlayerRows 全体の本格整備**。
    - **横展開全体の意味**: **財務・OM・戦術に続き Body 系第2段（最小）第4号として成功** — **次候補は契約 RiskRows**（**1関数1コミット**）。
  - **契約 / 人事サマリー閲覧・Phase4 Theme 第2段（最小）— RiskRows 人事リスク行区切り（`97b26a8`）** — **Body系第2段テンプレ第5号**:
    - **選定**: **PlayerRows 行区切り（`6b26fa3` / 記録 `d3ffb13`）成功後**。**財務 HistoryBody → OM MissionsBody → 戦術 PlayerRolesBody → 契約 PlayerRows** の行区切りが成功し、**契約人事の残り Body 最小候補が RiskRows** だった。**白カード内**・**色補正済み（`1df4820`）**・**`_fill_risk_rows` の1関数**・**OM と同型の配列化 + `i < n - 1` HSeparator**・**`_fill_player_rows` と同時ではなく1関数1コミット**。
    - **実装範囲（`97b26a8`）**: **`contract_personnel_summary_view.gd` のみ**。**`_fill_risk_rows` のみ**。有効リスク行を **`risks` 配列に順序維持で集約** → **`for i in range(n)`** で4行ブロック Label → **`i < n - 1` のとき `HSeparator.new()`**。**人事リスクなし時は HSeparator なし**。
    - **実装境界**: **`contract_personnel_summary_view.tscn`・Theme `.tres`・DTO/export/mock 未変更**。**表示文言・表示件数・並び順・JSON key 未変更**。**`_fill_player_rows` は未変更（`6b26fa3` 維持）**。**`_fill_risk_rows` 以外の関数未変更**。**`1df4820` の font_color 維持**。**HomeNavButton / DataSourceLabel 維持**。
    - **pytest（`97b26a8`）**: contract_personnel_summary 16 / home_dashboard 10 / roster 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **ホーム → 契約・人事サマリー遷移 OK**・**RiskRows 人事リスク行区切り OK**・**最終行後の不要区切りなし OK**・**人事リスク行可読性 OK**・**PlayerRows は `6b26fa3` の状態を維持 OK**・**Header/5静的カード OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）第5号 — 契約・人事 RiskRows 動的人事リスク行の行区切り追加完了**。**契約・人事は PlayerRows / RiskRows の最小行区切りが両方完了**（**契約・人事 RiskRows / PlayerRows 全体の第2段完了ではない**。**契約・人事サマリー全体の Body 第2段も完了ではない**）。
    - **別タスク（未着手）**: **RiskRows / PlayerRows の Panel 化**、人事リスク行・主要契約選手行カード化、余白・行レイアウト本格調整、**契約・人事 Body 全体の本格整備**。
    - **横展開全体の意味**: **財務・OM・戦術・契約 PlayerRows・契約 RiskRows まで Body 系第2段（最小）5画面成功** — **契約・人事の最小行区切り横展開は一区切り**。**以後は Body系最小の次候補比較**または**各画面 Body 本格第2段**を個別判断。
  - **契約 / 人事サマリー閲覧・Phase4 Theme 第2段（Body本格・最小）— PlayerRows 主要契約選手行の内側余白（margin）追加（`f19ed9b`）** — **Body本格整備の余白横展開第3号**:
    - **選定（`8034a1d`）**: **財務 HistoryBody 内側余白（`307e719`）**・**OM MissionsBody 内側余白（`d4c0372`）**・**戦術 PlayerRolesBody 内側余白（`2c637f2`）**が成功。**契約 PlayerRows** は**白カード内**・**HSeparator 最小完了（`6b26fa3`）**・**`_fill_player_rows` の1関数**・**戦術 / 財務に近い1行Label系**・**`lim` 最大8件**・**RiskRows とは別関数・別Body** — **2箇所同時変更を避け PlayerRows 単体が安全**。
    - **実装範囲（`f19ed9b`）**: **`contract_personnel_summary_view.gd` のみ**。**`_fill_player_rows` の主要契約選手行追加ループ部分のみ**。各 `Label` を **`MarginContainer` でラップ** — **左 4px / 上 2px / 右 4px / 下 2px**（財務・OM・戦術と同値）。**`margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL`**。**`margin.add_child(line)` → `_player_rows.add_child(margin)`**。
    - **実装境界**: **`_fill_risk_rows` / RiskRows 未変更**。**`contract_personnel_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`i < lim - 1` の HSeparator** 位置・条件未変更。**主要契約選手文言・`lim = mini(rows.size(), 8)`・並び順・`_style_body_label` / font_size 12 未変更**。**空表示** `（選手行がありません）` は **margin ラップなし**。**HeaderCard / 静的5カード・DataSourceLabel / HomeNavButton 未変更**。**JSON key / DTO / export / tests / mock JSON 未変更**。
    - **pytest（`f19ed9b`）**: contract_personnel_summary 16 / home_dashboard 10 / tactics_summary 15 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **PlayerRows 主要契約選手行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**主要契約選手文言 / 件数 / 順序維持 OK**。**RiskRows 従来どおり OK**。**HeaderCard / 静的5カード維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホーム復帰 OK**。**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body本格整備の余白横展開第3号 — 契約 PlayerRows 主要契約選手行の内側余白（margin）追加完了**。**財務 → OM → 戦術 → 契約 PlayerRows まで MarginContainer パターンの横展開が完了**（**契約 PlayerRows 全体の第2段完了ではない**。**Body本格整備全体の完了でもない**。**契約 RiskRows margin は `420f240` で対応 — 下記**）。
    - **横展開全体の意味**: **財務・OM・戦術の余白成功後、Body 本格整備の余白レーン第3号として契約 PlayerRows に適用** — **次候補は契約 RiskRows margin（`9411623` → `420f240`）**。
    - **未対応（`f19ed9b` 時点・別タスク）**: **契約 RiskRows への margin 横展開**（**`420f240` で対応 — 下記**）、**PlayerRows Panel 化**、主要契約選手行カード化、余白・行レイアウト本格調整、**Body系本格整備の中規模整理**。
  - **契約 / 人事サマリー閲覧・Phase4 Theme 第2段（Body本格・最小）— RiskRows 人事リスク行の内側余白（margin）追加（`420f240`）** — **Body本格整備の余白横展開第4号（レーン締め）**:
    - **選定（`9411623`）**: **契約 PlayerRows margin（`f19ed9b`）成功後**、**余白横展開レーンの締め**として **契約 RiskRows margin** を選定。**理由**: **財務 `307e719` / OM `d4c0372` / 戦術 `2c637f2` / 契約 PlayerRows `f19ed9b` で MarginContainer パターンが成功**。**契約 RiskRows は HSeparator 最小完了済み（`97b26a8`）**。**RiskRows は OM 型の複数行ブロックに近い**。**PlayerRows は `f19ed9b` で margin 済みのため今回は触らない**。**`_fill_risk_rows` 単体なら 1 関数・1 コミットで切れる**。
    - **実装範囲（`420f240`）**: **`contract_personnel_summary_view.gd` のみ**。**`_fill_risk_rows` の人事リスク行 Label 追加ループ部分のみ**。各 `Label`（`block`）を **`MarginContainer` でラップ** — **左 4px / 上 2px / 右 4px / 下 2px**（財務・OM・戦術・契約 PlayerRows と同値）。**`margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL`**。**`margin.add_child(block)` → `_risk_rows.add_child(margin)`**。
    - **実装境界**: **`_fill_player_rows` / PlayerRows 未変更（`f19ed9b` 維持）**。**`contract_personnel_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`i < n - 1` の HSeparator** 位置・条件未変更。**人事リスク文言・件数・並び順・`_style_body_label` / font_size 12 未変更**。**空表示** `（リスク項目がありません）` は **margin ラップなし**。**HeaderCard / 静的5カード・DataSourceLabel / HomeNavButton 未変更**。**JSON key / DTO / export / tests / mock JSON 未変更**。
    - **pytest（`420f240`）**: contract_personnel_summary 16 / home_dashboard 10 / tactics_summary 15 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **RiskRows 人事リスク行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**人事リスク文言 / 件数 / 順序維持 OK**。**PlayerRows 従来どおり OK**。**HeaderCard / 静的5カード維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホーム復帰 OK**。**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body本格整備の余白横展開レーン — 5 Body 完了**（**財務 HistoryBody** / **OM MissionsBody** / **戦術 PlayerRolesBody** / **契約 PlayerRows** / **契約 RiskRows**）。**財務 → OM → 戦術 → 契約 PlayerRows → 契約 RiskRows まで MarginContainer パターンの横展開が完了**（**契約 RiskRows 全体の第2段完了ではない**。**Body本格整備全体の完了でもない**）。
    - **進行方針（`420f240` 確認記録時点）**: **この粒度の行余白・区切り微調整（margin / HSeparator の最小追加）はここで一区切り**。**次は中規模以上** — **ロスター本格整備**、**日程 ScrollContent / 試合リスト本格整備**、**Body系本格整備の中規模整理**、**ゲーム体験に近い機能 / 画面**。
    - **未対応（別タスク）**: **RiskRows / PlayerRows の Panel 化**、人事リスク行・主要契約選手行カード化、余白・行レイアウト本格調整、**Body系本格整備の中規模整理**、**ロスター本格整備**、**日程本格**、**ゲーム体験寄りの機能 / 画面**。
  - **財務サマリー閲覧・Phase4 Theme 第1段（`4b43da5`）＋履歴行文字色最小補正（`6c3dc43`）** — **9詳細画面 UI 整備のテンプレ候補第5号**:
    - **選定（`99c279d`）**: 4画面第1段完了後、**完了済み4画面の Scroll 第2段（`.gd` 必須）より先に残り詳細へ**。**財務**は **CardNavMenu 経営列 #7**（**HeaderNavRow 非搭載**）・**`finance_summary_readonly` + pytest 安定**・**Scroll 内静的5カード**（Finance / Prior / Salary / History / Caution）・**`.tscn` のみで第1段を閉じやすい**。
    - **実装範囲（`4b43da5`）**: **`finance_summary_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**。**Scroll/ScrollContent 内5枚** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/ScrollContent`**（5枚静的カード ＋ **`%HistoryBody`** 動的履歴行 ＋ **`NotesFooterLabel`** — **履歴行は `.gd` で `Label.new()`**）。
    - **実装境界（`4b43da5`）**: **`finance_summary_view.gd`・Theme `.tres`・export / mock JSON 未変更**。**`%HistoryBody` 動的履歴行は第2段扱いで未変更**。
    - **目視課題**: 第1段適用後、**財務履歴カード内**の動的履歴行が**白カード上で薄く読みにくい**。
    - **補正（`6c3dc43`）**: **`finance_summary_view.gd` のみ** — **`_fill_history_rows`** の **`font_color`** を **`Color(0.16, 0.2, 0.3)`** へ（**第2段本格整備ではなく可読性の最小補正**）。**scene / Theme / DTO 不変**。
    - **第2段（第1段記録時点・未着手）**: **HistoryBody 行区切り**・構造整理（**第2段・最小 `d57b021` で行区切りのみ — 上記節参照**）。
    - **ユーザー環境 Godot**: **CardNavMenu → 財務サマリー OK**・**Header/5静的カード・DataSourceLabel OK**・**`6c3dc43` 後は財務履歴の可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: **Scroll 内複数静的 Panel 型**でも第1段が成功 — **OM（4枚・Missions 動的は第2段）等への手順が固まった**。
    - **今後**: **契約 RiskRows / PlayerRows 行区切り**、日程 Scroll 残り、**残り詳細画面**の第2段（**LeftRail クリック化は別工程**）。
  - **オーナーミッション / クラブ評価閲覧・Phase4 Theme 第1段（`e6acce0`）＋今季ミッション動的行文字色最小補正（`2f808e5`）** — **9詳細画面 UI 整備のテンプレ候補第6号**:
    - **選定（`130137a`）**: 5画面第1段完了後、**財務 `4b43da5` と同型の経営系横展開**。**オーナーミッション**は **CardNavMenu 経営列 #8**（**HeaderNavRow 非搭載**）・**`owner_mission_readonly` + pytest 安定**・**Scroll 内静的4カード**（Trust / Missions / Eval / Caution）・**`.tscn` のみで第1段を閉じやすい**。
    - **実装範囲（`e6acce0`）**: **`owner_mission_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**。**Scroll/ScrollContent 内4枚** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/ScrollContent`**（4枚静的カード ＋ **`%MissionsBody`** 動的ミッション行 ＋ **`NotesFooterLabel`** — **ミッション行は `.gd` で `Label.new()`**）。
    - **実装境界（`e6acce0`）**: **`owner_mission_view.gd`・Theme `.tres`・export / mock JSON 未変更**。**`%MissionsBody` 動的ミッション行は第2段扱いで未変更**。
    - **目視課題**: 第1段適用後、**今季ミッションカード内**の動的ミッション行が**白カード上で薄く読みにくい**。
    - **補正（`2f808e5`）**: **`owner_mission_view.gd` のみ** — **`_fill_mission_rows`** の **`font_color`** を **`Color(0.16, 0.2, 0.3, 1)`** へ（**第2段本格整備ではなく可読性の最小補正**）。**scene / Theme / DTO 不変**。
    - **第2段（第1段記録時点・未着手）**: **MissionsBody 行区切り**・構造整理（**第2段・最小 `5a3ae2c` で行区切りのみ — 上記節参照**）。
    - **ユーザー環境 Godot**: **CardNavMenu #8 → オーナーミッション OK**・**Header/4静的カード・DataSourceLabel OK**・**`2f808e5` 後は今季ミッションの可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: 財務に続き **経営系 OM でも Scroll 内複数静的 Panel 型**で第1段成功 — **動的行色補正は財務 `6c3dc43` と同型**。
    - **今後**: **契約 RiskRows / PlayerRows 行区切り**、**残り詳細画面**の第2段（**LeftRail クリック化は別工程**）。
  - **戦術 / ローテーションサマリー閲覧・Phase4 Theme 第1段（`44b0584`）＋選手ロール動的行文字色最小補正（`7bbbb4e`）** — **9詳細画面 UI 整備のテンプレ候補第7号**:
    - **選定（`6afb201`）**: 6画面第1段完了後、**未Themeの残り3画面のうちフル第1段が可能**。**戦術サマリー**は **CardNavMenu チーム列 #9**（**HeaderNavRow 非搭載**）・**`tactics_summary_readonly` + pytest 15 安定**・**Scroll 内静的6カード**（Overview / Attack / Defense / Rotation / PlayerRoles / Notes）・**`.tscn` のみで第1段を閉じやすい**（財務5枚・OM4枚と同型）。
    - **実装範囲（`44b0584`）**: **`tactics_summary_view.tscn` のみ**。ルート **`phase4_readonly_core.tres`**。**`HeaderCard`** → **`Phase4HeaderCard`**。**Scroll/ScrollContent 内6枚** → **`Phase4SummaryCard`**。**panel override のみ除去**（SubResource 残置）。**静的ラベル**を白カード向け濃色。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/ScrollContent`**（6枚静的カード ＋ **`%PlayerRolesBody`** 動的選手ロール行 — **選手ロール行は `.gd` で `Label.new()`**）。
    - **実装境界（`44b0584`）**: **`tactics_summary_view.gd`・Theme `.tres`・export / mock JSON 未変更**。**`%PlayerRolesBody` 動的選手ロール行は第2段扱いで未変更**。
    - **目視課題**: 第1段適用後、**選手ロールカード内**の動的選手ロール行が**白カード上で薄く読みにくい**。
    - **補正（`7bbbb4e`）**: **`tactics_summary_view.gd` のみ** — **`_fill_player_roles`** の **`font_color`** を **`Color(0.16, 0.2, 0.3, 1)`** へ（**第2段本格整備ではなく可読性の最小補正**）。**scene / Theme / DTO 不変**。
    - **第2段（第1段・色補正時点・未着手）**: **PlayerRolesBody 行区切り**・構造整理（**第2段・最小 `c9216d0` で行区切りのみ対応**）。
    - **ユーザー環境 Godot**: **CardNavMenu #9 → 戦術サマリー OK**・**Header/6静的カード・DataSourceLabel OK**・**`7bbbb4e` 後は選手ロールの可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: 財務・OM に続き **チーム系戦術でも Scroll 内複数静的 Panel 型**（6枚）で第1段成功 — **動的行色補正は財務 `6c3dc43` / OM `2f808e5` と同型**。
    - **今後**: **契約 RiskRows / PlayerRows 行区切り**、**残り詳細画面**の第2段（**LeftRail クリック化は別工程**）。
  - **契約 / 人事サマリー閲覧・Phase4 Theme 残り第1段（`5d1afa2`）＋RiskRows / PlayerRows 動的行文字色最小補正（`1df4820`）** — **9詳細画面 UI 整備のテンプレ候補第8号相当**:
    - **選定（`a01de09`）**: 7画面第1段完了後、**完了済み7画面の第2段は `.gd` 必須で後回し**。**契約・人事**は **CardNavMenu 経営列 #10**・**暗色残り Risk / Players の2 Panel のみ**・**`.tscn` のみで1コミット可能**。
    - **実装範囲（`5d1afa2`）**: **`contract_personnel_summary_view.tscn` のみ**。**`RiskCard` / `PlayersCard`** → **`Phase4SummaryCard`**（panel override 除去・SubResource 残置）。**RiskTitle / RiskHint / PlayersTitle** 濃色化。**`HomeNavButton` / `%DataSourceLabel` / from_python・mock 読込は維持**。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/ScrollContent`**（Contract / **Risk** / **Players** / Balance / Caution — **Risk/Players 内動的行は `.gd`**）。
    - **実装境界（`5d1afa2`）**: **`contract_personnel_summary_view.gd`・Theme `.tres`・DTO/export/mock 未変更**。**`%RiskRows` / `%PlayerRows` 動的行は第2段扱いで未変更**。
    - **目視課題**: 第1段適用後、**人事リスク / 主要契約選手**の RiskRows / PlayerRows 動的行が**白カード上で薄く読みにくい**。
    - **補正（`1df4820`）**: **`contract_personnel_summary_view.gd` のみ** — **`_fill_risk_rows` / `_fill_player_rows`** の **`font_color`** を **`Color(0.16, 0.2, 0.3, 1)`** へ（**`_style_body_label` 経由**・**第2段本格整備ではなく可読性の最小補正**）。**scene / Theme / DTO 不変**。
    - **第2段（`5d1afa2` / `1df4820` 時点・行区切り未着手）**: **RiskRows / PlayerRows 構造**・行レイアウト（**PlayerRows / RiskRows 行区切りは第2段・最小 `6b26fa3` / `97b26a8` で対応 — 上記節参照**。**Panel 化・カード化は未着手**）。
    - **ユーザー環境 Godot**: **CardNavMenu #10 → 契約・人事サマリー OK**・**表示・Scroll 内カード白系統一・DataSourceLabel OK**・**Risk/Players 白カード化 OK**・**`1df4820` 後は人事リスク・主要契約選手の可読性改善 OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開テンプレ**: **部分 Theme 済み画面**でも **暗色残り2枚**の `.tscn` 限定適用で Scroll 白系統一 — **動的行色は財務/OM/戦術と同手順の最小補正**。
    - **今後**: **RiskRows / PlayerRows Panel 化**等、完了済み画面の **Scroll / Body 第2段本格整備**（**LeftRail クリック化は別工程**）。
  - **ロスター閲覧・Phase4 Theme 第1段（`f866f5b`）＋表 Theme 通常 Table 化（`407f014`）** — **9詳細画面 UI 整備のテンプレ候補第9号相当（横展開の締め）**:
    - **選定（`cccbc6d`）**: 契約人事第1段記録後、**主要詳細画面の第1段で残っていた重要画面**。**ロスター**は **CardNavMenu チーム列 #1** ＋ **HeaderNavRow 先頭**・**ゲーム中心価値が高い**。**HeaderCard は既に Phase4**。**表 `%RowList` は `.gd` 動的9列**で **OnDark 系 Theme**。**`.tscn` の白カード化だけでは可読性破綻**のため **TableCard 追加（`f866f5b`）と表 Theme 切替（`407f014`）を2コミットで分割**。
    - **実装範囲（`f866f5b`）**: **`roster_view.tscn` のみ**。**`Scroll` 直下 `TableCard`** → **`Phase4SummaryCard`**。**`%RowList`** を **`Scroll/TableCard` の子へ移動**（**unique_name 維持**）。**Header / HomeNavButton / DataSourceLabel / connection 維持**。
    - **情報構造（不変）**: **`HeaderCard`** → **`Scroll/TableCard/RowList`**（**9列表は `.gd` で `HBoxContainer` + `Label.new()`**）。
    - **実装境界（`f866f5b`）**: **`roster_view.gd`・Theme `.tres`・DTO/export/mock 未変更**。
    - **補正（`407f014`）**: **`roster_view.gd` のみ** — **`Phase4OnDarkTableHead` → `Phase4TableHead`**、**`Phase4OnDarkTableCell` → `Phase4TableCell`**（**Theme variation 切替のみ・第2段本格整備ではない**）。**scene / Theme / DTO 不変**。**9列・列幅・行生成順・JSON key 不変**。
    - **第2段（本格・未着手）**: **表行の Panel 化**、**選手行カード化**、**余白・行レイアウト本格調整**、**9列レイアウト本格整理**、**ReadonlyBadge / ModeStrip 暗 chip 整理**。
    - **ユーザー環境 Godot**: **HeaderNavRow または CardNavMenu → ロスター OK**・**白 TableCard 内9列表 OK**・**表ヘッダー/セル可読性 OK**・**DataSourceLabel OK**・**HomeNavButton でホーム復帰 OK**・**エラーなし**。
    - **横展開全体**: **主要10画面の Theme 第1段が一通り完了**。**日程第2段**: **前半 NextGameCard（`986c4ab`）**＋**後半（最小）upcoming（`7fecb99`）**＋**日程 Scroll 小ブロック・見出し・区切り整理一区切り**＋**中規模改善第1手 upcoming 試合カード内情報階層（`fa36271`）**＋**日程本格整備・第2手 advance_hint 情報階層（`5a98e31`）**＋**日程本格整備・第3手 empty_message 本文情報階層（`065197b`）**。**Body系第2段（最小）**: **財務 HistoryBody（`d57b021`）**＋**財務 HistoryBody 内側余白（`307e719`）**＋**OM MissionsBody（`5a3ae2c`）**＋**OM MissionsBody 内側余白（`d4c0372`）**＋**戦術 PlayerRolesBody 行区切り（`c9216d0`）**＋**戦術 PlayerRolesBody 内側余白（`2c637f2`）**＋**契約・人事 PlayerRows 行区切り（`6b26fa3`）**＋**契約・人事 PlayerRows 内側余白（`f19ed9b`）**＋**契約・人事 RiskRows 行区切り（`97b26a8`）**＋**契約・人事 RiskRows 内側余白（`420f240`）** — **契約・人事の最小行区切りは両方完了**。**Body余白横展開レーン 5 Body 完了**。**Body本格整備・中規模第1手 財務 HistoryBody 平坦 Panel 行ラップ（`c762d88`）**。**ロスター本格整備・第1手 平坦行背景（`9445d0e`）**。**ロスター本格整備・第2手 主要列強調（氏名列・OVR列）（`6c1e25f`）**。**ロスター本格整備・第3手 状態列視認補助（`746e861`）**。**細かい行余白・区切り微調整は一区切り**。**次候補（中規模以上）**: **日程 Scroll 残り**、**ロスター本格の続き**、**Body 本格の続き**、**ゲーム体験寄りの機能 / 画面**。
  - **ロスター閲覧・Phase4 Theme 第2段（最小）— RowList 選手行間 HSeparator 追加（`8a95fcf`）**:
    - **選定（`2ec93f8`）**: **日程 Scroll 小ブロック・見出し・区切り整理が一区切り**したあと、**Body系第2段（最小）の行区切りパターン**（財務 / OM / 戦術 / 契約 PlayerRows / 契約 RiskRows）を **ゲーム中心画面であるロスター**へ横展開する候補として **RowList 選手行間 HSeparator 追加**を選定 — **理由**: **5箇所で実績あり**・**ロスターは CardNavMenu #1 / HeaderNavRow 先頭で UI 効果が高い**・**`_add_player_row` を触らず `_apply_snapshot` の players ループのみで1コミット**・**9列レイアウト本格調整は重いためまず行間 HSeparator のみが安全**。
    - **実装範囲（`8a95fcf`）**: **`roster_view.gd` のみ**。**`_apply_snapshot` 内 players ループのみ** — **`valid_players` に Dictionary 行のみ収集**（順序維持）→ **`for i in range(n)`** で **`_add_player_row`** → **`i < n - 1` のとき `_row_list.add_child(HSeparator.new())`**。**有効選手0件時は行間 HSeparator なし**。
    - **実装境界**: **`roster_view.tscn`・Theme `.tres`・project.godot 未変更**。**`_add_player_row` 本体未変更**。**9列幅・tooltip 未変更**。**ヘッダー下 Separator 未変更**。**HeaderCard / TableCard 未変更**。**ReadonlyBadge / ModeStrip 未変更**。**DataSourceLabel / HomeNavButton 未変更**。**JSON key / 表示文言 / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`8a95fcf`）**: roster 10 / home_dashboard 10 / schedule 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **RowList 選手行間区切り OK**・**最終行後の不要区切りなし OK**・**ヘッダー下区切り維持 OK**・**9列内容 / 順序 / 幅維持 OK**・**tooltip 維持 OK**・**DataSourceLabel 維持 OK**・**HomeNavButton 戻り OK**・**エラーなし・実行後 git 差分なし**。
    - **到達点**: **Body系第2段（最小）パターンのロスター横展開 — RowList 選手行間 HSeparator 追加完了**（**ロスター表第2段全体の完了ではない**。**TableCard + Phase4Table 第1段に続く最小スライス**）。
    - **別タスク（未着手）**: **選手行カード化**、**9列レイアウト本格整理**、**tooltip 再設計**、**列幅・表示優先度の本格調整**、**RowList 全体の余白・行レイアウト本格調整**、**Body 本格整備**、**日程 ScrollContent 全体整理**、**日程試合リスト行レイアウト本格整理**（**平坦行背景ラップは `9445d0e` で対応 — 下記**）。
  - **ロスター閲覧・ロスター本格整備・第1手 — RowList 選手行の平坦行背景追加（`9445d0e`）**:
    - **選定（`6d9c0a8`）**: **日程 upcoming 情報階層整理（`fa36271`）完了後**、次の中規模改善として **ロスター本格整備の第1手**を選定 — **理由**: **ロスターはゲーム判断の中心画面**・**HeaderNavRow 先頭の重要画面**・**9列 / tooltip / 列幅リスクがあるため一括本格ではなく `_add_player_row` のみの行背景ラップに限定**・**`fa36271` と同型の 1 ファイル・1 関数**。
    - **実装範囲（`9445d0e`）**: **`roster_view.gd` のみ**。**`_add_player_row` のみ** — 既存 **9列 HBox** を **`PanelContainer` でラップ**。**`StyleBoxFlat`** による薄い平坦な行背景（角丸 2px・content margin 4px・枠線なし）。**`Phase4SummaryCard` は使わない**（TableCard 内の行帯）。
    - **実装境界**: **`_apply_snapshot` 未変更**。**players / valid_players 未変更**。**RowList 行間 HSeparator ロジック未変更**。**9列・列順・列幅・文言・JSON key 未変更**。**tooltip / mouse_filter 未変更**。**ヘッダー行 / ヘッダー下 Separator 未変更**。**HeaderCard / TableCard 未変更**。**`roster_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`9445d0e`）**: roster 10 / home_dashboard 10 / schedule 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **行背景 OK**・**9列内容 / 順序 / 幅維持 OK**・**tooltip 維持 OK**・**HSeparator 維持 OK**・**最終行後不要 HSeparator なし OK**・**Header行 / Header下Separator / HeaderCard / TableCard 維持 OK**・**DataSourceLabel 維持 OK**・**HomeNavButton 戻り OK**・**エラーなし・差分なし**。
    - **横展開全体の意味**: **日程中規模改善第1手後、ゲーム中心画面であるロスターへ中規模改善を横展開** — **細かい余白調整ではなく行の視認性を上げる構造改善**（**`8a95fcf` の行間区切りとは別レイヤ**）。
    - **到達点**: **ロスター本格整備・第1手 — RowList 選手行の平坦 PanelContainer 行背景ラップ完了**（**ロスター本格整備全体の完了ではない**。**9列本格再設計は未完了**）。
    - **未対応（別タスク）**: **選手行カード化**、**9列レイアウト本格整理**、**tooltip 再設計**、**列幅・表示優先度の本格調整**、**RowList 全体の余白・行レイアウト本格調整**（**主要列強調は `6c1e25f` で対応 — 下記**）。
  - **ロスター閲覧・ロスター本格整備・第2手 — RowList 選手行の主要列強調（氏名列・OVR列）（`6c1e25f`）**:
    - **選定（`079f1cb`）**: **日程 advance_hint 情報階層整理（`5a98e31`）完了後**、次の中規模改善として **ロスター本格整備の第2手**を選定 — **理由**: **ロスターはゲーム判断の中心画面**・**氏名と OVR は「誰を・どれくらい評価するか」に直結する主要列**・**9列 / tooltip / 列幅リスクがあるため一括本格ではなく `_add_player_row` のみの最小強調に限定**・**`9445d0e` の行背景を壊さずに読み取りやすさを上げられる**。
    - **実装範囲（`6c1e25f`）**: **`roster_view.gd` のみ**。**`_add_player_row` のみ** — **氏名列（`i == 1`）** と **OVR列（`i == 4`）** に **`font_size` 13**（既存 12 から +1）と **`font_color` `Color(0.08, 0.11, 0.18, 1)`** を上書き。
    - **実装境界**: **`_apply_snapshot` 未変更**。**players / valid_players 未変更**。**RowList 行間 HSeparator ロジック未変更**。**9列・列順・列幅・文言・JSON key 未変更**。**tooltip / mouse_filter 未変更**。**PanelContainer 行背景 / StyleBoxFlat 未変更**。**ヘッダー行 / HeaderCard / TableCard 未変更**。**`roster_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`6c1e25f`）**: roster 10 / home_dashboard 10 / schedule 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **氏名列の読みやすさ OK**。**OVR列の読みやすさ OK**。**9列内容 / 順序 / 幅維持 OK**。**tooltip 維持 OK**。**行背景維持 OK**。**HSeparator 維持 OK**。**最終行後不要 HSeparator なし OK**。**Header行 / HeaderCard / TableCard 維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton 戻り OK**。**エラーなし・差分なし**。
    - **横展開全体の意味**: **行背景追加（`9445d0e`）後、9列再設計に踏み込まず主要列の視認性だけを上げた** — **細かい余白追加ではなくロスター上の判断情報の優先度を付けた構造改善**（**ロスター本格整備全体や9列本格再設計は未完了**）。
    - **到達点**: **ロスター本格整備・第2手 — RowList 選手行の主要列強調（氏名列・OVR列）完了**（**ロスター本格整備全体の完了ではない**。**9列本格整理・tooltip再設計・列幅本格調整は未対応**）。
    - **未対応（別タスク）**: **選手行カード化**、**9列レイアウト本格整理**、**tooltip 再設計**、**列幅・表示優先度の本格調整**、**RowList 全体の余白・行レイアウト本格調整**、**ソート / フィルタ / 選手詳細導線の前段整理**、**日程 ScrollContent / 試合リスト本格整備**、**Body 本格整備の中規模整理**、**ゲーム体験に近い機能 / 画面検討**、**Python本体 / ゲームロジック側への復帰検討**（**状態列視認補助は `746e861` で対応 — 下記**）。
  - **ロスター閲覧・ロスター本格整備・第3手 — RowList 選手行の状態列（i==8）視認補助（`746e861`）**:
    - **選定（`df10b8e`）**: **日程 empty_message 情報階層整理（`065197b`）完了後**、次の中規模改善として **ロスター本格整備の第3手**を選定 — **理由**: **日程は upcoming / advance_hint / empty_message の3系統ブロック内階層が一通り整理済み**・**ロスターはゲーム判断の中心画面**・**氏名列 / OVR列に続き状態列は「その選手が今どういう状態か」を拾う補助情報として重要**・**9列 / tooltip / 列幅リスクがあるため一括本格ではなく `_add_player_row` のみの最小 typography 視認補助に限定**・**`9445d0e` の行背景と `6c1e25f` の主要列強調を壊さずに読み取りやすさを上げられる**。
    - **実装範囲（`746e861`）**: **`roster_view.gd` のみ**。**`_add_player_row` のみ** — **`elif i == 8:` を 3 行追加**。**状態列（`i == 8`）** に **`font_size` 13**（既存 12 から +1）と **`font_color` `Color(0.08, 0.11, 0.18, 1)`**（氏名/OVR と同系）を上書き。**状態別色分け・状態文言変更は行わない**。
    - **実装境界**: **氏名列（`i == 1`）・OVR列（`i == 4`）の既存強調維持**。**`_apply_snapshot` 未変更**。**players / valid_players 未変更**。**RowList 行間 HSeparator ロジック未変更**。**9列・列順・列幅・文言・JSON key 未変更**。**状態列 tooltip（`st_s != "-"` 時）/ mouse_filter 未変更**。**PanelContainer 行背景 / StyleBoxFlat 未変更**。**ヘッダー行 / HeaderCard / TableCard 未変更**。**`roster_view.tscn`・Theme・project.godot・data JSON / DTO/export/tests/mock JSON 未変更**。
    - **pytest（`746e861`）**: roster 10 / home_dashboard 10 / schedule 10 / phase0 smoke 1 — いずれも passed。
    - **ユーザー環境 Godot（ローカル目視）**: **状態列の拾いやすさ OK**。**氏名列 / OVR列維持 OK**。**9列内容 / 順序 / 幅維持 OK**。**tooltip 維持 OK**。**mouse_filter 維持 OK**。**行背景維持 OK**。**HSeparator 維持 OK**。**最終行後不要 HSeparator なし OK**。**Header行 / HeaderCard / TableCard 維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton 戻り OK**。**エラーなし・差分なし**。
    - **横展開全体の意味**: **行背景（`9445d0e`）と主要列強調（`6c1e25f`）後、9列再設計に踏み込まず氏名・OVR・状態の読み取りポイントを最小強調した** — **細かい余白追加ではなくロスター上の判断情報の優先度を軽く付けた構造改善**（**ロスター本格整備全体や9列本格再設計は未完了**）。
    - **到達点**: **ロスター本格整備・第3手 — RowList 選手行の状態列（i==8）視認補助完了**（**ロスター本格整備全体の完了ではない**。**9列本格整理・tooltip再設計・列幅本格調整・選手行カード化は未対応**）。
    - **未対応（別タスク）**: **選手行カード化**、**9列レイアウト本格整理**、**tooltip 再設計**、**列幅・表示優先度の本格調整**、**RowList 全体の余白・行レイアウト本格調整**、**ソート / フィルタ / 選手詳細導線の前段整理**、**日程 ScrollContent / 試合リスト本格整備**、**Body 本格整備の中規模整理**、**ゲーム体験に近い機能 / 画面検討**、**Python本体 / ゲームロジック側への復帰検討**。
  - **本線ホーム 表示用 LeftRail（`a5e548f`）**: **`home_dashboard.tscn` のみ**。**レイアウト構造（情報設計）**:
    - **`HeaderCard`** — 全幅（クラブ帯・**`HeaderNavRow` 5 ボタン**）。
    - **`StatusLabel`** — 全幅。
    - **`MainRow`（HBox）** — **左** `LeftRail`（200px）・**右** `Scroll` / `Inner`。
    - **`Scroll/Inner` 順序** — **`CardNavMenu`** → **`SecMetricsTitle` / `MetricsRow`** → **`CardTeamExtras`** → **`CardWarnings`** → **`CardNext`** → **`CardSummary`** → **`CardTasks`** → **`CardNews`**（従来どおり）。
    - **`FooterNote`** — 全幅。
  - **LeftRail の情報役割**: **現在地（ホーム）**と**大分類**（チーム / リーグ / 経営 / クラブ）の**視覚ラベル**。**詳細画面の選択は中央の `CardNavMenu`**（8 ボタン・4 列）。**表示のみ** — **Button / connection / `home_dashboard.gd` なし**。
  - **既存カード群（現在形）**: **MetricsRow・`CardNavMenu`・`CardTeamExtras`・`CardSummary`・`CardNews`・`CardNext`・`CardTasks`・`CardWarnings`** は **Summary / Warning 系 Theme 済み**。**Scroll 内の暗色カード問題は解消済み**（**`d9bd713`**）。
  - **実装境界（`d9bd713` 含む）**: **`home_dashboard.gd`・Theme `.tres`・export / mock JSON は未変更**（**`d9bd713` は `.tscn` のみ**）。
  - **ユーザー環境 Godot（ローカル目視）**: **約 1216×684**（LeftRail 追加時）および **1280×720**（`d9bd713` 後）で **大きなレイアウト崩れなし**。**HeaderCard 全幅**・**LeftRail 左表示**・**CardNavMenu 白系カード・4 列・8 ボタン・#7〜#10 入口表示**・**MetricsRow 以降**・**FooterNote 表示**。**HeaderNavRow / CardNavMenu の遷移 OK**。**LeftRail は遷移しないのが正しい**（**表示のみ**）。
  - **今後**: **LeftRail クリック化**は**別工程**（大分類と複数詳細画面の IA を先に設計）。**次の自然な進め方**は **他詳細画面 UI 整備**または **次画面選定** — **LeftRail クリック化へ即進まない**。
  - **今後の注意（本線移植）**: sandbox 固定文言（**`PO圏まで 2.0差`** 等）を本線へ出すには **DTO / export / `.gd` の追加整理**が必要。**`news` の 1 行ヘッドライン本格化は未着手**。**`CardNavMenu` の削除・縮小**は **#7〜#10 入口の代替設計**ができるまで**当面しない**。**`CardNews` の 1 行化**や **`news_headline` 等**は **別工程**。**Header に資金・成績行を本格移植する場合**は **MetricsRow との重複を別途整理**（**`club_summary` は Metrics 再掲を含まない現形**）。本線判断では **from_python/mock**・**DataSourceLabel**・**HeaderNavRow**・**既存 10 画面導線を壊さないこと**を優先する。
- **本線 `home_dashboard.tscn` との違い（役割分担）**: **本線**＝**実導線**・**`from_python` / mock`**・**pytest の正本**（`home_dashboard.gd`、§15 冒頭の到達点と同じ）。**sandbox**＝**見た目・情報密度・左ナビ・クラブ帯・情報の役割分担**の研究。sandbox は **JSON / Python / scene 遷移を持たない**（script なし・固定文言のみ）。**本線への反映は別タスク・別コミット**。
- **`project.godot` の `run/main_scene` は変更しない**（エディタで当該シーンを開き **F6 / 現在のシーンを実行** で確認。運用は `godot/README.md`「本番ホームワイヤー sandbox」節）。
- **本線へ反映する目安条件**（満たしてから **別タスク・別コミット**で本線移植を検討。いずれも **未達＝sandbox 継続でよい**）:
  - 1280×720 でレイアウトが破綻しない
  - **目視合意**（情報の優先順位・帯の行数など）
  - **左サイドの大分類**が確定（10 画面を左に全部並べない方針と整合）
  - **ホーム表示情報**と **DTO 候補**の整理が済んでいる
  - **UID / `load_steps` の再シリアライズ**の確認・復旧手順が運用として安定している
  - 移植を **小さなコミット単位**に分割できる
- **§14 との関係**: sandbox は **手動 JSON（§14.1）や自動起動（§14.2）の対象外**。実データを載せる変更は本線側で行う。

---

## 付録 A: 補助枠 → Godot 卒業先 早見

```txt
[オフの流れ]   → オフシーズンセンター（ヘルプ）
[来年候補]     → ドラフトセンター（来年タブ） or 情報 → ドラフト
[FA市場]       → 人事 → FA タブ（閲覧）
[直近オフ]     → 情報 → 直近オフ振り返り（クラブ史と相互リンク）
[デバッグ]     → 開発ビルド限定のデバッグパネル
```

## 付録 B: 関連ドキュメント

- `godot/README.md`（Phase 4 最小 Godot プロジェクトの運用・手動 JSON 手順・**`godot_readonly_bundle` 一括 export**・**共通 Theme / 白ベース検証（限定適用）**・**本番ホームワイヤー sandbox**）
- `docs/PRODUCT_ROADMAP_AND_VISION.md`（Phase 0〜6 ／製品ビジョン）
- `docs/IDEAL_GAME_DESIGN_MASTER.md`（理想形のドメイン設計）
- `docs/INFORMATION_MENU_SPEC_V1.md`／`docs/SCHEDULE_MENU_SPEC_V1.md`／`docs/SYSTEM_MENU_SPEC_V1.md`
- `docs/PERSONNEL_GUI_MINOPS.md`（人事メニューの最小操作）
- `docs/TACTICS_MENU_FULL_HANDOFF_2026-04.md`（戦術メニューの引き継ぎ）
- `docs/DRAFT_AUCTION_SYSTEM.md`（オークション正本）
- `docs/GUI_INSEASON_FA_ENTRY_POLICY.md`／`docs/GUI_FA_CONTRACT_ENTRY_POLICY.md`／`docs/GUI_FULL_FA_MARKET_ENTRY_POLICY.md`
- `docs/GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md`／`docs/TRADE_MENU_ONE_FOR_ONE_ENTRY_POLICY.md`
- `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`（Steam 配布の現状）
- `basketball_sim/integrations/STEAMWORKS_DESIGN.md`
