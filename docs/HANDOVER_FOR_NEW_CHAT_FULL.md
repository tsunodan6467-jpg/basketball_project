# 新チャット用 リポジトリ引き継ぎ書（フル）

この引き継ぎ書は、**現在のリポジトリ状態を基準に**、コードベースと既存ドキュメントを読んだ範囲で事実を整理したものです。推測で断定しないため、未読・未追跡の箇所は **未確認** と明記しています。

---

## 1. プロジェクト概要

### 何のゲームか

- **国内プロバスケクラブ運営シミュレーション（GM 視点）**。
- 実装の中心は Python パッケージ `basketball_sim/`。**Tkinter メイン画面**（`MainMenuView`）と **CLI**（`python -m basketball_sim`）の両系統が共存する。
- **Steam 連携**の土台あり（`steamworks_bridge.py`、`basketball_sim/integrations/STEAMWORKS_DESIGN.md`）。README に exe ビルド・診断コマンドの説明あり。

### 何を目指しているか / 作品の核

- リーグ運営（日程・試合・昇降格）、ロスター／契約／年俸キャップ、FA・ドラフト・トレード、施設・経営・オーナー期待、育成・戦術指定などを **一つの世界観**で繋ぐシミュレーション。
- README の表現: 「国内バスケ GM シミュレーション（開発中）」。

### Steam 販売目標

- リポジトリ内に **数値化された販売 KPI の単一ソースは未確認**（README / `STEAMWORKS_DESIGN.md` は技術・ポリシー寄り）。
- Steam は **初回リリースまでローカルセーブ主**、クラウドは将来オプション、などの方針が `STEAMWORKS_DESIGN.md` に記載。

### 現在の開発フェーズ

- **Phase 4 系の GUI ダッシュボード**（`main_menu_view.py` 先頭コメント）と、**経済・FA・ペイロール・トレード**の細かい正本調整が並行している段階（`docs/` に意思決定メモが大量に存在）。
- **「製品完成」ではなく「コア＋運営ループ＋GUI の拡張途中」**と捉えるのが安全。

---

## 2. 固定運用ルール（リポジトリ／会話から読み取れる範囲）

以下は **README・コードコメント・会話指示のパターン**から抽出した「運用方針」であり、リポジトリに `CONTRIBUTING.md` として一本化されているわけではない（**未確認**: 別途チーム規約がある場合は上書き）。

- **ChatGPT / Cursor 連携**: タスク単位で指示書を渡し、エージェントがコードを読んで実装するスタイルが想定される。
- **コード出力ルール**: ユーザー側ルールとして「最小差分」「全文貼り換え禁止気味」「長文コード全文不要」が繰り返し指定されている。
- **最小差分優先**: 既存構造を壊さない・永続フィールドを増やさない変更が好まれる。
- **実行コマンド**: `python -m basketball_sim --smoke` と `pytest basketball_sim/tests` が **README および CI 相当の標準**。
- **「次にやるタスクは1つだけ」**: 会話指示で明示されることが多い（本書末尾も同様）。
- **安定性最優先・速度より精度**: テストとスモークを通すことを重視する文化。
- **Antigravity / Cursor の使い分け**: リポジトリ内に明文化された正本は **未確認**（Cursor 前提の記述は会話側）。

---

## 3. 現在のロードマップと現在地（解釈）

ユーザー提示の **4 段階**（コア成立 → 長期運営の面白さ → 見せ方強化 → 製品仕上げ）をコードから機械的に証明するフラグはないため、**現状の読み取り**として以下に整理する。

| 段階 | 内容 | 現状の目安 |
|------|------|------------|
| コア成立 | 試合・シーズンループ・チーム／選手 | `Season` / `Match` / `Team` / `Player` が厚く、テスト群あり → **かなり前進** |
| 長期運営 | FA・契約・年俸・オフシーズン・CPU 行動 | `offseason.py`・`free_agent_market`・`contract_logic`・各種 docs が厚い → **進行中** |
| 見せ方強化 | GUI・文言・ハイライト | `main_menu_view.py` が大規模。ハイライト仕様は `docs/HIGHLIGHT_MODE_SPEC.md` 等 → **進行中** |
| 製品仕上げ | Steam・インストーラ・署名 | README / installer / Steam 設計あり → **一部着手** |

**現在地の一言**: 「シミュレーションコア＋経済 FA 周りの正本調整＋ GM GUI の機能追加」が同時に進んでいるフェーズ。

---

## 4. コード構造の重要ファイル

各項目: **担当** / **ここまでの変化の目安** / **触る時の注意**

### `basketball_sim/main.py`

- **担当**: CLI のメインループ、新規世界構築、進行、トレード提案（1対1・multi）、各種メニュー呼び出しのハブ。
- **変化の目安**: `club_profile.get_initial_team_money_cpu` / `get_initial_user_team_money`、`opening_roster_salary_v11`、`trade_input_helpers`（現金億+万・RB 入力）、`parse_multi_trade_side_payment` 連携、`TradeSystem` 呼び出し。
- **注意**: 新規ゲームのみ `DEBUG_BOOST_USER_TEAM_ENV` 等のデバッグ経路あり。セーブ読込経路と混同しないこと。

### `basketball_sim/models/season.py`

- **担当**: シーズン進行、`ROUND_CONFIG`（月・リーグ試合数・杯・代表ウィンドウ等のカレンダー構造）、試合生成・結果反映の中心。
- **変化の目安**: ファイルサイズ大。**未確認**: 末尾のオフシーズン分岐の詳細は読み切っていない。
- **注意**: `ROUND_CONFIG` は他モジュール（取引期限など）の参照正本になりやすい。

### `basketball_sim/models/offseason.py`

- **担当**: オフシーズンフェーズの処理塊（FA・契約更新・ドラフト等の入口がここに集約されがち）。`Offseason` クラス、ペイロールバジェット同期ヘルパ等。
- **変化の目安**: ペイロール・FA 周りの同期関数が先頭付近に存在（`_sync_payroll_budget_with_roster_payroll` 等）。
- **注意**: 単一ファイルが極大。**変更は最小差分＋該当テスト必須**。

### `basketball_sim/models/team.py`

- **担当**: クラブ状態のデータモデル（`players`、`money`、`strategy` / `coach_style` / `usage_policy`、`team_training_focus`、`team_tactics`、`management` ネスト、ユース、オーナー、財務ログ等）。
- **変化の目安**: `team_tactics` は **Phase A 永続化**コメントあり（`MainMenuView` の戦術ウィンドウ注記とセットで理解）。
- **注意**: `INITIAL_TEAM_MONEY_NEW_GAME` は game_constants 由来のデフォルト。**新規開始の実所持金**は `club_profile` 側の関数が上書きし得る。

### `basketball_sim/systems/generator.py`

- **担当**: `generate_teams`、開幕 48 チーム `OPENING_LEAGUE_TEAMS`、選手生成、**開幕年俸・年齢プロファイル**へのフック（`opening_roster_salary_v11` インポート）。
- **変化の目安**: `_young_foreign_opening_ovr_penalty` 等、**若年外国籍 OVR** の調整がここに存在。
- **注意**: `GENERATOR_INITIAL_SALARY_BASE_PER_OVR`（game_constants）と開幕専用ロジックの二系統がある。

### `basketball_sim/systems/club_profile.py`

- **担当**: クラブの **実行時プロファイル**（倍率）、**新規開始時の所持金**。
- **変化の目安**: CPU は `get_financial_power_band_1_to_5` → `_INITIAL_OPENING_CASH_BY_BAND`（2億〜8億）。ユーザーは `INITIAL_USER_TEAM_MONEY_NEW_GAME = 5億` 固定（`get_initial_user_team_money`）。
- **注意**: `team_id` 別の上書きテーブルが多段でマージされている。変更時は帯計算との整合を壊しやすい。

### `basketball_sim/systems/opening_roster_salary_v11.py`

- **担当**: **開幕本契約 13 人の年俸バンド**（ディビジョン × 国籍カテゴリ × top/middle/bottom）。`OPENING_NATURALIZED_MIN_AGE = 27`。D3 bottom 帯のコメントで「5〜6億 tier」言及。
- **変化の目安**: `apply_opening_team_payroll_v11` 等が `generator` から呼ばれる。
- **注意**: FA / 再契約の年俸ロジックとは独立（ファイル先頭コメント通り）。

### `basketball_sim/systems/trade_logic.py`

- **担当**: `TradeSystem`（1対1 / multi の評価・AI 承諾・実行の土台）、**現金・RB の評価補正**、RB 刻み検証。
- **定数（正本）**:
  - `TRADE_VALUE_BONUS_PER_MILLION_CASH = 0.10`（100 万円あたり評価 +0.10）
  - `TRADE_VALUE_BONUS_PER_MILLION_RB = 0.18`
  - `TRADE_RB_TRANSFER_STEP_YEN = 5_000_000`（500 万刻み）
  - `TRADE_RB_TRANSFER_MAX_LEG_YEN = 40_000_000`（片道 4000 万上限）
- **注意**: CPU 将来価値倍率など細部あり。入力 UI は別モジュール。

### `basketball_sim/systems/main_menu_view.py`

- **担当**: **メイン GUI**（左メニュー、人事・経営・強化・戦術・情報・歴史・システム各ウィンドウ）。ロスター Treeview、トレードウィザード、**個別練習エディタ**（`MainMenuView._open_player_training_editor_window`）、戦術ハブ `open_strategy_window` 等。
- **変化の目安（会話・コードから確実）**:
  - トレード: multi GUI で現金＝億+万 Combobox、RB Combobox、`trade_input_helpers` + `parse_multi_trade_side_payment`。
  - 個別練習: 全員 Treeview、詳細欄で能力グリッド、国籍は `jp_reg_display.get_player_nationality_bucket_label`、ポジション型は `build_draft_candidate_role_shape_label`、列名は **「タイプ」**（戦術の「役割設定」と混同しないよう改名済み）。
  - 戦術ウィンドウ: 上部ナビボタン（チーム戦術・ローテ・起用方針・**役割設定**・セットプレー）＋ **Canvas 内スクロール**したメインコンテンツに、**同じ戦術・HC・起用の Combobox** が並ぶ二重系（後述の課題）。
- **注意**: 単一ファイルが極大。grep で当たりを付けてから部分読みすること。

### `basketball_sim/config/game_constants.py`

- **担当**: **数値・識別子の単一ソース**（ペイロードスキーマ版、クォーター秒、ロスター人数、**外国籍枠**、年俸キャップ・フロア、ぜいたく税ブレット、インシーズン取引カットオフラウンド、ハイライトプリセット等）。
- **変化の目安**: `LEAGUE_ROSTER_FOREIGN_CAP = 3`、`LEAGUE_ROSTER_ASIA_NATURALIZED_CAP = 1`、`LEAGUE_ONCOURT_FOREIGN_CAP = 2` 等。
- **注意**: 「表示丸め」はここではなく `money_display.py`。

### `basketball_sim/systems/trade_input_helpers.py`

- **担当**: トレード入力用の **億+万 → 円**、**RB 万表記 → 円**、候補列生成のみ。評価式は変更しない。
- **注意**: CLI / GUI で共有。`main.py` と `main_menu_view.py` の両方から利用。

### `basketball_sim/systems/money_display.py`

- **担当**: `format_money_yen_ja_readable` — 円整数を **100 万円未満切り捨て**、**万円の整数倍**で「〇〇万円」「x 億 y 万円」表記。
- **注意**: 内部整数は変えない。旧表記が一部 UI に残る可能性は **grep で要確認**（未全検）。

### テスト群 `basketball_sim/tests/`

- **担当**: 契約・FA・年俸・トレード・GUI 定数・スモーク等、**100 本超**の `test_*.py`。
- **変化の目安**: `test_trade_input_helpers.py`、`test_parse_multi_trade_side_payment.py`、`test_trade_asset_bonus.py`、`test_club_profile.py`、`test_initial_payroll_cap.py` など経済・トレード系が厚い。
- **注意**: フル `pytest basketball_sim/tests` は **数分規模**（環境依存）。

### その他、参照頻度が高いファイル（追加）

| パス | 担当の要約 |
|------|------------|
| `basketball_sim/systems/contract_logic.py` | 契約・年俸・キャップ正規化、`get_team_payroll`、ドラフトルーキー判定等 |
| `basketball_sim/systems/free_agent_market.py` / `free_agency.py` | FA 市場・交渉 |
| `basketball_sim/systems/japan_regulation.py` / `japan_regulation_display.py` | 外国籍枠・表示ラベル |
| `basketball_sim/systems/team_tactics.py` | `team_tactics` の正規化・先発マップ等（`Match` から import あり） |
| `basketball_sim/models/match.py` | 試合本体。`team_tactics` の **先発マップ系**を利用 |
| `basketball_sim/systems/cpu_club_strategy.py` | CPU クラブの方針・トレード倍率など |
| `docs/CURRENT_STATE_ANALYSIS_MASTER.md` | 別系統のマスタ分析（**本書と内容重複時はコード優先で矛盾解消**すること） |

---

## 5. ここまでの主要修正履歴（系統別・事実ベース）

### 初期ロスター / 初期資金 / 初期世界の是正

- **開幕年俸**: `opening_roster_salary_v11.py` のバンド表＋`generator.generate_teams` からの適用。
- **初期所持金**: `club_profile.get_initial_team_money_cpu`（帯 1〜5: 2億〜8億）、ユーザー固定 **5 億**（`INITIAL_USER_TEAM_MONEY_NEW_GAME`）。
- **game_constants**: 合成チーム用フォールバック `INITIAL_TEAM_MONEY_NEW_GAME = 2億`（コメントで本番は club_profile と明記）。

### 初期ロスター現実感パス

- `opening_roster_salary_v11` の **D3 bottom 帯**、若年の年俸上限 `_YOUNG_MAX_SALARY_BY_DIV`、帰化最低年齢 **27** 等がコード上の正本。
- 若年外国籍の **OVR ペナルティ**は `generator._young_foreign_opening_ovr_penalty`（年齢段階別）。

### GUI / CLI の判断性改善

- **トレード現金・RB 入力**: 円のフル手打ちから、**億+万（万は 1000 万刻み）**、**RB は 500 万刻みの選択**へ（`trade_input_helpers` + `main.py` の `_cli_read_trade_cash_yen` / `_cli_read_trade_rb_yen` + GUI multi ウィザード）。
- **個別練習**: プルダウン 1 人選択から **全員 Treeview + 詳細欄**へ。国籍区分・タイプ（ガード/ウイング/ビッグ）・能力グリッド・練習短縮列など。

### トレード改善

- `TradeSystem` に現金・RB の **評価加点**（上記定数）。
- 入力検証は `parse_multi_trade_side_payment`（`main.py`）が CLI/GUI で共用されるパターン。

---

## 6. 現在の GUI / CLI で何ができるか（実装済み範囲の目安）

**未確認**: すべてのメニューを実機で棚卸ししたわけではない。`main_menu_view.py` の `MENU_ITEMS` と各 `open_*` / `_on_*` から読み取った範囲。

| 領域 | CLI | GUI |
|------|-----|-----|
| 人事・ロスター | `main.py` に放出・延長・トレード/FA 導線の一部 | ロスターウィンドウ、契約延長、FA 1 人ウィザード、トレード multi 等 |
| 強化 | チーム/個別練習の CLI 経路あり | `open_development_window`、個別練習エディタ、チーム練習エディタ |
| 経営 | 施設・財務系 CLI 表示 | 経営ウィンドウ（ダッシュボード Text、オーナー・広報等） |
| 戦術 | `tactics_cli_display` 等 | `open_strategy_window`、先発/6th/ベンチ編集、別ウィンドウでチーム戦術・ローテ・起用・**役割設定**・セットプレー |
| トレード | 1対1 / multi、`TradeSystem` | 人事経由の multi ウィザード等 |
| FA | `free_agent_market` 連携 | インシーズン FA ウィザード等 |
| 再契約 | `contract_logic` / offseason 経路 | 人事オペレーションの一部（**未確認**: 画面の網羅性） |
| 試合前後 | `match_preview_cli_display` / `match_postgame_cli_display` | メイン画面の次試合・ニュース等 |
| オフシーズン | `offseason.py` が中心 | **未確認**: GUI でのオフ専用画面の有無は個別追跡が必要 |

---

## 7. 現在の数値正本 / 仕様正本（コードから読み取れるもの）

- **D3 ボトム年俸モデル**: `opening_roster_salary_v11._BANDS` の `(3, *, "bottom")` 各行。コメントに「5〜6 億 tier」への言及あり。
- **開始所持金**: CPU は `club_profile._INITIAL_OPENING_CASH_BY_BAND`（帯 1〜5: **2億 / 2.8億 / 3.8億 / 5.5億 / 8億**）。ユーザーは **`club_profile.INITIAL_USER_TEAM_MONEY_NEW_GAME = 5億` 固定**。
- **帰化最低年齢（開幕ロスター表現）**: `opening_roster_salary_v11.OPENING_NATURALIZED_MIN_AGE = 27`。
- **若年外国籍 OVR 補正（開幕生成）**: `generator._young_foreign_opening_ovr_penalty`（Foreign かつ年齢帯で 4/2/0）。
- **外国籍 3 人スロット・コート上 2 + アジア/帰化枠**: `game_constants` の `LEAGUE_ROSTER_FOREIGN_CAP` 等と `Match` ドキュメントコメントの組み合わせ。
- **金額表示丸め**: `money_display.format_money_yen_ja_readable` — **100 万円未満切り捨て**、表示は **万円整数倍**。
- **トレード現金 / RB**: 片道 RB 上限 **4000 万**、刻み **500 万**。評価補正は **現金 +0.10 / 百万円**、**RB +0.18 / 百万円**（`trade_logic.py`）。
- **リーグ年俸上限（全 D 同一 12 億）**: `game_constants.LEAGUE_SALARY_CAP_BY_DIVISION`。
- **ペイロールフロア**: D1 6 億、D2 4 億、D3 0（`PAYROLL_FLOOR_BY_DIVISION`）。
- **インシーズン取引締め**: `REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND = 22`（コメント: ラウンド 22 以降ロック）。

---

## 8. 未解決 / 保留タスク

1. **戦術メニューの UI 二重化**  
   `open_strategy_window`: 上部に **「チーム戦術」「起用方針」等のナビボタン**があり、同時にスクロール内 `strategy_panel` に **`Team.strategy` / `coach_style` / `usage_policy` の Combobox** がある。**同じ設定への入口が二箇所**になり得る（ユーザ混乱・保守コスト）。  
   - **未確認**: 両者が常に同一状態に同期されているか、片方が古い UI 残骸かの精査は ` _sync_strategy_policy_combos` 周りの読み切りが必要。

2. **戦術メニューの「役割設定」が試合にどう効くか**  
   `_open_tactics_roles_window` が存在。`Team.team_tactics` の永続化はある一方、`MainMenuView._refresh_strategy_window` の文言では **「詳細戦術 (team_tactics): Phase A は試合未連携」** と説明されている。  
   - 一方で `match.py` は `team_tactics` から **先発マップ系**を import。**「未連携」の意味範囲（全パラメータ vs 一部キー）の正本整理は未完了**と見てよい。

3. **戦術メニュー改善が次の大きな軸**になりうる（ユーザー方針・本書の推奨アクション参照）。

4. **個別練習画面の軽い改善候補**  
   - 一覧の「現在練習」短縮と **億選択時の万 Combobox 動的絞り**は未実装（現状は候補フル＋検証で弾くパターンの記述が会話にあった）。  
   - 反映後の `messagebox` 連打の緩和など UX。

5. **金額表示の旧表記残り**  
   `format_money_yen_ja_readable` 以外の経路が残っている可能性 → **grep `format_money` / 万円以外** で要確認（未全検）。

6. **その他**  
   `offseason.py` の巨大さによるレビュー負荷、`docs/` と実装の drift（**未確認**: どのドキュメントが最新正本かはファイル単位で要照合）。

---

## 9. 次チャットの最初の推奨アクション（1 つだけ）

**戦術メニューの正本調査（UI 二重化の解消方針の確定）**

- **具体的タスク**: `MainMenuView.open_strategy_window` / `_refresh_strategy_window` / `_open_tactics_team_strategy_window` / `_sync_strategy_policy_combos` を読み、**(A) 上部ナビだけに集約するか (B) スクロール内だけに集約するか (C) 明示的に「クイック編集 vs 詳細画面」としてラベル分離するか** の方針を決め、**重複する Combobox または重複するボタン**の一方を削るまたは非表示にする設計メモ（＋必要なら最小パッチ）までを **1 PR 相当のスコープ**に収める。

※ コード上、`Match` は既に `team_tactics` の一部を参照するため、「すべて未連携」とは言い切れない。**調査結果で文言修正から入る**のもあり。

---

## 10. 実行コマンド / 確認コマンド

### 標準（README 整合）

```powershell
cd "c:\Users\tsuno\Desktop\basketball_project"
python -m basketball_sim --smoke
python -m pytest basketball_sim/tests -q --tb=short
```

### 単体・絞り込み pytest 例

```powershell
python -m pytest basketball_sim/tests/test_trade_logic.py -q --tb=short
python -m pytest basketball_sim/tests/test_club_profile.py -q --tb=short
python -m pytest basketball_sim/tests/test_team_tactics_phase_b.py -q --tb=short
```

### 主な調査（grep）例

```powershell
rg "team_tactics" basketball_sim --glob "*.py"
rg "役割設定" basketball_sim/systems/main_menu_view.py
rg "format_money_yen_ja_readable" basketball_sim --glob "*.py"
```

### ログ（README 記載のユーザーデータパス）

- セーブ: `%USERPROFILE%\.basketball_sim\saves\`
- ログ: `%USERPROFILE%\.basketball_sim\logs\game.log`、クラッシュ: `last_crash.txt`

---

## 末尾（必須）

- **この引き継ぎ書は、現在のリポジトリ状態を基準に作成した。**
- **次チャットの最初のタスクは 1 つだけ。**
- **その 1 つ**: 上記 **§9** のとおり — **戦術メニュー（`main_menu_view.py` の `open_strategy_window` 系）の正本調査と、設定 UI 二重化の解消方針確定（必要なら文言修正のみから着手）**。
