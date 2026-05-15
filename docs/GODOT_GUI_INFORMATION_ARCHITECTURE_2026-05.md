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
- **限定適用の方針**: まず **`.tscn` のみ**で済む **静的ヘッダー**・**静的 Panel カード**から当てる。**`Label.new()` + 暗地前提の明色 override** は、白い `Phase4SummaryCard` 内へ載せ替えるには **`.gd` で `theme_type_variation` または色を直す**必要がある。**ロスター表の動的行**は `Phase4OnDarkTableHead` / `Phase4OnDarkTableCell` で **暗背景のまま**対応済み（`d33edb6`）。**契約・人事の人事リスク／主要契約選手**は **未着手**。
- **契約 / 人事サマリー**（`contract_personnel_summary_view.tscn`）: ルート Theme 割当。**`Phase4HeaderCard`**（ヘッダー）＋ヘッダー内 Label 濃色。**`Phase4SummaryCard`**: 契約概要・ロスター構成。**`Phase4WarningCard`**: 注意。**人事リスク**・**主要契約選手**は従来の暗色 `StyleBoxFlat_summary` のまま（動的行は `.gd` 未変更）。
- **ロスター閲覧**（`roster_view.tscn`）: ルート Theme。**`Phase4HeaderCard`**（ヘッダー）。**表**は `roster_view.gd` で動的 `Label` に **`theme_type_variation`**（OnDark 系）を付与（**白カード化なし**）。
- **ホーム**（`home_dashboard.tscn`）: **ルートに Theme なし**。**`HeaderCard` のみ**に `phase4_readonly_core.tres` を割当し **`Phase4HeaderCard`**。従来の `StyleBoxFlat_header` は削除。**`83d7fc0` で HeaderCard 内に sandbox ClubBand 風の `HeaderClubBandRow`・`HomeLogoSlot`（`SG` / `LOGO`）・`HeaderBandTextCol` を追加**し、**`ClubNameLabel` / `SeasonLabel` / `DataSourceLabel`** をクラブ帯内に配置（**`unique_name_in_owner` 維持**）。**MetricsRow** は **`CardDivision`（`f66bcd2` 先行）・`CardRank` / `CardMoney`（`2471b67`）**に `theme` + **`Phase4SummaryCard`** を付与し、**各カードから `StyleBoxFlat_card` の panel override のみ除去**（**共有 `StyleBoxFlat_card` SubResource は他カード用に残存**）。**`HRank` / `RankRecordLabel` / `HMoney` / `MoneyLabel`** を白カード向け濃色に調整。**`rank_record` / `money` の内容・JSON キー・表示ロジックは不変**（**`_rank_record.text = _txt(d, "rank_record")` / `_money.text = _txt(d, "money")` 不変**）。**`CardDivision` / `SecMetricsTitle` / MetricsRow 構造は未変更**。**`Scroll` 以下**は **`ed106c8` で `CardNews`、`8676095` で `CardNext`、`d18bf1f` で `CardTasks`** に `theme` + **`Phase4SummaryCard`**、**`762f5bc` で `CardWarnings`** に `theme` + **`Phase4WarningCard`**（**`StyleBoxFlat_warn` の panel override のみ除去**。`StyleBoxFlat_warn` SubResource は残存）。**`HNews` / `NewsLabel`**、**`HNext` / `NextGameLabel`**、**`HTasks` / `TasksLabel`**、**`HWarn` / `WarningsLabel`** を各カード向け濃色に調整。**MetricsRow 3 枚と Scroll 縦カード群で Summary / Warning の役割分界を維持**。**`tasks` の最大 3 行表示**は不変（**`_join_lines(d, "tasks", 3)` も不変**）。**`news` / `next_game` / `warnings` の表示/非表示ロジック**は不変。**`home_dashboard.gd`・JSON / Python / DTO・Theme `.tres` は不変**。**CardRank / CardMoney 以外の Scroll 下カード・HeaderNavRow・10 画面導線は維持**。**from_python / mock 経路は不変**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ限定移植している段階」**（**大レイアウト移植ではない**）。
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
  - **本線ホーム Header の ClubBand 風寄せ（`83d7fc0`）**: sandbox 検証の成果を本線へ入れる**第一歩**として、**`home_dashboard.tscn` の HeaderCard 内だけ**を ClubBand 風へ**最小寄せ**した。**本線の大レイアウト移植・左レール・中央 2 カラム・右サマリー列の本線化は未着手**。**`HeaderClubBandRow`・`HomeLogoSlot`（`SG` / `LOGO`）・`StyleBoxFlat_home_logo_slot`・`HeaderBandTextCol`** を追加し、**`ClubNameLabel` / `SeasonLabel` / `DataSourceLabel`** はノード名と `unique_name_in_owner` を維持したままクラブ帯内に配置。**`DataSourceLabel` は from_python / mock の読込元表示として維持**（`autowrap_mode = 2` 付与）。**`home_dashboard.gd`・JSON・Python・DTO は未変更**。**HeaderNavRow 5 ボタンと既存 10 画面導線は維持**。**当時の `83d7fc0` の範囲では Scroll 以下は未着手**（**その後 `ed106c8` で `CardNews`、`8676095` で `CardNext`、`762f5bc` で `CardWarnings`、`d18bf1f` で `CardTasks`、`2471b67` で MetricsRow の `CardRank` / `CardMoney` のみ Theme 限定適用** — 次項〜次々々々々項）。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。
  - **本線ホーム Scroll 以下 `CardNews` の Theme 限定適用（`ed106c8`）**: **Scroll 以下の最初の 1 カード見た目寄せ**として **`CardNews` のみ** **`Phase4SummaryCard`** を適用。**大レイアウト移植ではない**。**パネルは Theme 側に任せ**、`CardNews` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**）。**`HNews` / `NewsLabel` を白カード向け濃色に調整**。**`news` の内容・行数・JSON キーは不変**。**`_join_lines`・`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardNews 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**sandbox の `CardNewsBody` 級の 1 行ヘッドラインを本線へ本格導入する場合**は、**`.gd` の表示行数制御**または **export / DTO の `news_headline` 等**を**別工程**で設計する。**現時点では「見た目だけ 1 カード限定で移植した段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardNext` の Theme 限定適用（`8676095`）**: **`CardNews` に続く 2 枚目**として **`CardNext` のみ** **`Phase4SummaryCard`** を適用。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardNext` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**）。**`HNext` / `NextGameLabel` を白カード向け濃色に調整**。**`next_game` の内容・JSON キー・表示ロジックは不変**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardNext 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` は既存の白カード状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardWarnings` の Theme 限定適用（`762f5bc`）**: **`CardNews` / `CardNext` に続く警告カード**として **`CardWarnings` のみ** **`Phase4WarningCard`** を適用。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardWarnings` から **`StyleBoxFlat_warn` の panel override のみ除去**（**SubResource 定義は残存**）。**`HWarn` / `WarningsLabel` をライト警告カード向け濃色に調整**。**`WarningsRow` の初期 `visible = false` は維持**。**`warnings` の内容・JSON キー・表示/非表示ロジックは不変**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardWarnings 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**`762f5bc` 時点では `CardTasks` は未変更**（**`d18bf1f` で SummaryCard — 次項**）。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム Scroll 以下 `CardTasks` の Theme 限定適用（`d18bf1f`）**: **`CardNews` / `CardNext` に続く SummaryCard 系**として **`CardTasks` のみ** **`Phase4SummaryCard`** を適用。**`CardWarnings` は `Phase4WarningCard` のまま**とし、**警告と ToDo の役割を分離**。**Scroll 以下の大レイアウト移植ではない**。**パネルは Theme 側**に任せ、`CardTasks` から **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**。**`StyleBoxFlat_warn` も削除していない**）。**`HTasks` / `TasksLabel` を白カード向け濃色に調整**。**`tasks` の内容・JSON キー・最大 3 行表示**は不変（**`_join_lines(d, "tasks", 3)` 不変**）。**`TasksLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardTasks 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardWarnings` は既存の WarningCard 状態を維持**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ 1 カードずつ限定移植している段階」**と明記する。
  - **本線ホーム MetricsRow `CardRank` / `CardMoney` の Theme 限定適用（`2471b67`）**: 既に **`Phase4SummaryCard` 済み**だった **`CardDivision` に続き**、**`CardRank` / `CardMoney` の 2 枚だけ**を**同一コミット**で **`Phase4SummaryCard`** に適用。**MetricsRow の `CardDivision` / `CardRank` / `CardMoney` 3 枚が白カード系で統一**された。**Scroll 以下の大レイアウト移植ではなく、MetricsRow 内の見た目統一**。**パネルは Theme 側**に任せ、各カードから **`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は他カード用に残存**。**`StyleBoxFlat_warn` も削除していない**）。**`HRank` / `RankRecordLabel` / `HMoney` / `MoneyLabel` を白カード向け濃色に調整**。**`rank_record` / `money` の内容・JSON キー・表示ロジックは不変**（**`_rank_record.text = _txt(d, "rank_record")` / `_money.text = _txt(d, "money")` 不変**）。**`RankRecordLabel` / `MoneyLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。**`CardDivision` / `SecMetricsTitle` / MetricsRow 構造は未変更**。**`home_dashboard.gd` は不変**。**from_python / mock 経路は不変**。**Theme `.tres` は不変**。**CardRank / CardMoney 以外のカード・HeaderNavRow・既存 10 画面導線は維持**。**`CardNews` / `CardNext` / `CardTasks` は既存の SummaryCard 状態を維持**。**`CardWarnings` は既存の WarningCard 状態を維持**。**Godot 4.6.2 で表示確認 OK・UID エラーなし・実行後差分なし**（手元運用の目安）。**現時点では「見た目だけ限定移植している段階」**と明記する。
  - **今後の注意（本線移植）**: sandbox 固定文言（**`PO圏まで 2.0差`**、**`ホーム快勝、次戦へ弾み`** 等）を本線へ出すには **DTO / export / `.gd` の追加整理**が必要。**現時点では本線 Header の見た目**、**MetricsRow 3 枚（`CardDivision` / `CardRank` / `CardMoney`）**、**Scroll 以下の `CardNews` / `CardNext` / `CardTasks` / `CardWarnings` の見た目**までを小さく移植した段階（**`news` の 1 行ヘッドライン本格化は未着手**）。**`CardSummary` / `club_summary` の整理**は **現 DTO の複数行説明との整合**が必要なため **別タスク**。**`CardNews` の 1 行化**や **`news_headline` 等**は **`.gd` / DTO / export の別工程**。**Header に資金・成績行を本格的に載せる場合**は **MetricsRow との情報重複を別途整理**する。本線移植判断では **from_python/mock**・**DataSourceLabel**・**HeaderNavRow**・**既存 10 画面導線を壊さないこと**を優先する。
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
