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

本節は **2026-05** 時点の方針メモである。運用手順の詳細は `godot/README.md`、読み取り専用 export の実装は `basketball_sim/export/` の `home_dashboard_readonly.py` / `roster_readonly.py` / `club_history_readonly.py` を正とする（§15）。

### 14.1 現在の接続方式（手動 JSON）

- Python CLI（`python -m basketball_sim.export.home_dashboard_readonly --save <.sav> --output <.json>`）で **読み取り専用のホーム用 JSON** を手動生成する。処理は `load_world` による **セーブの読み取りのみ**であり、**セーブファイルを書き換えない**。
- Godot は **`res://data/home_dashboard_from_python.json`** を優先して読み、無ければ **`res://data/home_dashboard_mock.json`** にフォールバックする（`godot/scripts/home_dashboard.gd` の `_home_json_candidate_paths`）。
- **Godot から Python プロセスを起動する処理は、本節の時点では入れない**。
- 生成物 `home_dashboard_from_python.json` は開発用であり、`godot/.gitignore` で **コミット対象外**。

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
- 開発中は **手動 JSON 生成 + Godot 優先読込**で十分とする
- 先に **ホームの見た目改善**、**DTO 品質改善**、**次の読み取り専用 Godot 画面**でパターンを積む
- **自動起動**は、Python 実行環境の前提・対象 save の決め方・JSON 出力先（`res://` vs `user://` 等）・**配布方針**を固めてから **実装するかを判断**する

---

## 15. Phase 4 初期プロトタイプ到達点（Godot / 読み取り専用）

**位置づけ**: 本節は **`godot/` 上の仮 GUI 足場** の記録であり、本番 GUI 完成・確定仕様の宣言ではない。詳細な運用手順は `godot/README.md` を正とする。

- **2026-05 時点の到達点**: `godot/` に **ホーム・ロスター閲覧・クラブ史閲覧** の 3 画面があり、いずれも **読み取り専用プロトタイプ**（進行・保存・契約・トレード・経営・育成・戦術保存などの **状態変更系 UI は未接続**）。
- **画面の役割（仮）**:
  - **ホーム**: **仮ハブ**およびクラブ状況サマリー（`home_dashboard_readonly` DTO に相当する JSON）。
  - **ロスター閲覧**: **現在のチーム編成**の表形式閲覧（`roster_readonly` DTO）。
  - **クラブ史閲覧**: **長期プレイの蓄積**閲覧（`club_history_readonly` DTO）。
- **データ経路**: いずれも **Python export（`load_world` による読み取りのみ）→ JSON → Godot 表示** の型。各画面は **`_*_from_python.json` 優先・同梱 `*_mock.json` フォールバック**（§14.1 の手動 JSON 方針と同じ運用）。
- **仮ナビ**: ホームを起点に **ホーム → ロスター → ホーム**、**ホーム → クラブ史 → ホーム**（画面切替のみ。本格ナビゲーションではない）。
- **未着手**（§14.2 と整合）: Godot からの **Python 自動起動**、本番 **セーブ／ロード** 接続、**進行処理**、状態変更系 UI、**本格ナビゲーション**、**Steam 向け本番レイアウト**の確定。

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

- `godot/README.md`（Phase 4 最小 Godot プロジェクトの運用・手動 JSON 手順）
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
