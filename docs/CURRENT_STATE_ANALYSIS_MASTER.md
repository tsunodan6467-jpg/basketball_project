# 国内バスケGM開発 現状分析書（正本）

**第1版作成日**: 2026-04-06（ワークスペース上の日付基準）  
**文書の性質**: 理想設計・実装計画ではなく、**リポジトリと参照 docs から読み取れる現状の整理**。推測で埋めない。  
**更新**: コード・運用・正本 docs が変わったら本書を更新する。

---

## 0. この文書の使い方

- **目的**: 開発トップ（ユーザー）・ChatGPT（第二の開発統括）・Cursor（実装役）の **認識合わせ用の現状スナップショット**。
- **理想像・願望・実装順**は本書の主題ではない。別文書（例: `docs/PRODUCT_ROADMAP_AND_VISION.md`）を正とする。
- 各論点は可能な限り次のラベルで分ける: **実装済み** / **暫定** / **未実装** / **未確認**。
- **未確認**は「リポジトリ内のファイル・ログだけでは断定できない」ことを意味する。

---

## 1. プロジェクト概要

| 項目 | 事実（出典） |
|------|----------------|
| ゲーム概要 | 日本のプロバスケを**参考**にした**独自リーグ**の GM シミュレーション。架空のリーグ名・チーム名・選手名（`docs/PRODUCT_ROADMAP_AND_VISION.md`）。 |
| 対象プラットフォーム | 開発・配布は **Windows** を主に想定（Steam / PyInstaller / `steam_api64.dll` 言及はコード・docs に基づく）。他 OS の動作保証は **未確認**。 |
| 主言語 | **Python**。GUI は **tkinter**（`docs/PRODUCT_ROADMAP_AND_VISION.md`・`basketball_sim/systems/main_menu_view.py`）。 |
| コード規模（目安） | `basketball_sim/` 配下に **`.py` が 120 本前後**（2026-04-06 時点のワークスペースでのファイル一覧）。`PRODUCT_ROADMAP_AND_VISION.md` にある「約34ファイル」表記は **旧い可能性**あり（本書では上記実数を優先）。 |
| 現在の開発段階 | `docs/PRODUCT_ROADMAP_AND_VISION.md` 上 **Phase 0（★現在地・最優先）** と明記。並行して Phase 1 相当のシミュ・リーグは厚い（同 doc の「レビュー反映」節）。 |
| 現在の最優先テーマ（doc 上） | **安定性**、セーブ・ビルド・Steam 販売の技術・商業前提（Phase 0）。 |

---

## 2. 現在地（ロードマップ上の位置）

| 項目 | 事実 |
|------|------|
| ロードマップ上の位置 | **Phase 0 が★現在地**（`docs/PRODUCT_ROADMAP_AND_VISION.md`）。 |
| だいたい固まっているもの（doc 記載ベース） | 48チーム3部リーグ・Season/Offseason ループ・試合シミュ・CLI 長期周回・pytest スモーク等（同 doc「Phase 1 相当: △〜◎」）。日本独自ルール・カップ/国際・クラブ史・GM/経済の一部・tkinter 主画面は **△** 表現（同 doc）。 |
| 今の主戦場（傾向） | `docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` に、主画面 tkinter・日程表示・大会表示名・各メニュー情報設計が「直近の主戦場（傾向）」として列挙されている（要約文書の記述）。 |
| 次の大きな節目（doc 記載） | ストア・デポ・発売に関する手続き、Phase 0 でのクラウドセーブ/Rich Presence の要否（`docs/PRODUCT_ROADMAP_AND_VISION.md` Phase 0 節・**2026-04-05 決定で v1 にクラウド/Rich Presence は含めない**と明記）。 |

---

## 3. 開発運用ルール

以下は **`.cursorrules`** および **`docs/AI_WORKFLOW_RULES.md`** に基づく事実の要約。

- **日本語**: チャット・ゲーム内表示は日本語（コード・識別子・コミット英語可）。
- **安定性最優先**（クラッシュ・セーブ破損・再現不能を最も恐れる）。
- **最小変更・ついで修正禁止**（無関係箇所に広げない）。
- **中規模以上はいきなり実装しない**: 調査・計画・完了条件を先に（例外はタイポ・import・1ファイル内の安全な小修正）。
- **実装後の自己レビュー**必須（依頼箇所・近接・None・イベント順・テスト等）。
- **ログ・コマンド**: ログ依頼時は抽出コマンドをセットで示す（`docs/AI_WORKFLOW_RULES.md`）。
- **Cursor 返答の締め**: 「手動でやってほしいこと」「次の一手（1つ）」を分ける（`.cursorrules`）。
- **Git**: 作業単位ごとに commit / push、**1コミット1目的**（`.cursorrules`）。

---

## 4. 現在の全体構造

| 項目 | 事実 |
|------|------|
| エントリポイント（モジュール実行） | `python -m basketball_sim` → `basketball_sim/__main__.py` → `basketball_sim.main.simulate()`（`--smoke` / `--steam-diag` 分岐あり）。 |
| PyInstaller エントリ | `BasketballGM.spec` の `Analysis` で **`basketball_sim/main.py`** を指定。 |
| CLI と GUI | **CLI**: `main.py` のメニュー群・`--smoke` 等。**GUI**: tkinter 主画面（`systems/main_menu_view.py`）。`docs/PRODUCT_ROADMAP_AND_VISION.md` は **製品ではメイン操作は GUI**、CLI は開発・CI・smoke 補助と記載。 |
| ディレクトリ要点 | `basketball_sim/models/`（Season, Team, Match, Offseason 等）、`basketball_sim/systems/`（UI・ルール・市場等）、`basketball_sim/persistence/`（pickle セーブ）、`basketball_sim/integrations/`（Steam 橋渡し）、`basketball_sim/tests/`（pytest）。 |
| `docs/` の位置づけ | Phase・日程・メニュー仕様・Steam 設計等の**正本**が分散配置。`.cursorrules` は要約し詳細は docs を正とする。 |
| `tests/` の位置づけ | pytest による回帰。`--smoke` は対話なしの最小起動経路（`main.py` の `run_smoke`）。 |

---

## 5. 現在の実装状況（分野別）

※ **主要ファイル**は代表例。網羅ではない。

### 5.1 リーグ / シーズン進行

| 区分 | 内容 |
|------|------|
| 実装済み | 48チーム・3ディビジョン、ラウンド進行、昇降格・PO 等（`models/season.py`、git 履歴・PRODUCT 記載と整合）。 |
| 暫定 | **未確認**（「暫定」とラベルできる明確な一文はコード上は個別確認していない）。 |
| 未実装 | doc 上の「製品としての GUI 内での年度・シーズン完結」は**目標**として残る（`PRODUCT_ROADMAP_AND_VISION.md`）。 |
| 未確認 | 全ブランチ・全メニュー経路での進行の網羅テスト。 |
| 主要ファイル | `basketball_sim/models/season.py`, `basketball_sim/main.py`, `basketball_sim/models/offseason.py` |

### 5.2 日程生成

| 区分 | 内容 |
|------|------|
| 実装済み | ラウンド設定・大会週・代表ウィンドウ等（`season.py` の `ROUND_CONFIG` 等）。仕様正本 `docs/SEASON_SCHEDULE_MODEL.md`。 |
| 暫定 | **未確認**。 |
| 未実装 | **未確認**（doc と実装の差分は個別 diff が必要）。 |
| 未確認 | 全ラウンド・全大会の組み合わせの手動網羅。 |
| 主要ファイル | `basketball_sim/models/season.py`, `docs/SEASON_SCHEDULE_MODEL.md` |

### 5.3 試合シミュレーション

| 区分 | 内容 |
|------|------|
| 実装済み | `Match` によるシミュ（`models/match.py`）、ローテ・規約関連（`systems/rotation.py`, `systems/japan_regulation.py` 等）。 |
| 暫定 | **未確認**。 |
| 未実装 | doc 上 Phase 2 の「実況・情緒テキスト」本格は後続（`PRODUCT_ROADMAP_AND_VISION.md`）。 |
| 未確認 | バランスの主観的妥当性（数値目標は別 CI）。 |
| 主要ファイル | `basketball_sim/models/match.py`, `basketball_sim/systems/rotation.py` |

### 5.4 試合の見せ方

| 区分 | 内容 |
|------|------|
| 実装済み | ハイライト・カメラ・プレゼン層のコードとテストが存在（`systems/highlight_*.py`, `presentation_layer.py`, 対応 tests）。 |
| 暫定 | **未確認**（製品仕様との距離は `HIGHLIGHT_MODE_SPEC.md` 照合が必要）。 |
| 未実装 | `PRODUCT_ROADMAP_AND_VISION.md` は Phase 4 でハイライト/結果だけを **□** 表現。 |
| 未確認 | 実プレイでの尺・操作性の合意度。 |
| 主要ファイル | `docs/HIGHLIGHT_MODE_SPEC.md`, `basketball_sim/systems/spectate_view.py` 等 |

### 5.5 メニュー構造

| 区分 | 内容 |
|------|------|
| 実装済み | tkinter 主画面に複数メニュー（`main_menu_view.py`）。システム・情報・履歴等の仕様 doc が複数。 |
| 暫定 | CLI と GUI の**併存**（`PRODUCT`・引き継ぎ doc に記載）。 |
| 未実装 | doc 記載の「GUI 一本化」は**目標**。 |
| 未確認 | 全ボタン・全サブウィンドウの欠陥の有無。 |
| 主要ファイル | `basketball_sim/systems/main_menu_view.py`, `docs/SYSTEM_MENU_SPEC_V1.md` 等 |

### 5.6 戦術

| 区分 | 内容 |
|------|------|
| 実装済み | チーム戦術・先発ルール等（`team_tactics.py`, `MATCH_STARTING_LINEUP_RULES.md` 正本）。 |
| 暫定 | **未確認**。 |
| 未実装 | **未確認**（細部は doc 照合）。 |
| 未確認 | Phase B 以降の試合反映範囲（doc に記載あり）。 |
| 主要ファイル | `basketball_sim/systems/team_tactics.py`, `docs/MATCH_STARTING_LINEUP_RULES.md` |

### 5.7 人事

| 区分 | 内容 |
|------|------|
| 実装済み | トレード（`trade_logic.py`, `main.py` CLI）、FA（`free_agent_market.py` 等）、ドラフト（`draft.py`, `draft_auction.py`）。シーズン中取引締切（`season_transaction_rules.py`）。 |
| 暫定 | **未確認**。 |
| 未実装 | `PRODUCT` は GUI からの同一ガード通過を **残** と記載。 |
| 未確認 | 全 GUI 経路でのロック整合。 |
| 主要ファイル | `basketball_sim/main.py`, `basketball_sim/systems/trade_logic.py`, `basketball_sim/systems/season_transaction_rules.py` |

### 5.8 経営

| 区分 | 内容 |
|------|------|
| 実装済み | スポンサー・広報・グッズ・施設・CPU 裏経営等のモジュールとテストが存在（git 履歴・ファイル存在）。**国内リーグ所属クラブ**のオフ国際大会賞金（杯・洲际・FINAL BOSS）は、オフ締め `record_financial_result` の `revenue` 内訳に合流（2026-04-06）。**シーズン中**のリーグ分配等ラウンド記録（`Team.inseason_cash_round_log`）は**経営 GUI・財務サマリー**で一覧表示可能（2026-04-06、正本 `finance_history` 非経由）。**実装済み（最小）**: 第 2 キー `inseason_matchday_estimate_round`（主場概算・`money`＋`inseason_cash_round_log`＋財務サマリー表示、仮単価。2026-04-06）。ホーム数は `Season.get_regular_season_home_game_count_for_round`。数え方は `docs/INSEASON_MATCHDAY_ESTIMATE_POLICY.md`。 |
| 暫定 | **初期資金 20 億・ラウンド仮収入**（`team.py` デフォルト、`season.py` のラウンド加算）。**オフシーズン締めでの `TEMP_OFFSEASON_CENTRAL_PAYROLL_SHARE = 0.98`**（`offseason.py`）。いずれもコメント上 **仮調整・後で本実装想定**。 |
| 未実装 | doc 上「操作は GUI でクリック完結」等の完全達成は **未** の記述が残る（`PRODUCT` Phase 3）。 |
| 未確認 | 経済バランスの長期納得感。 |
| 主要ファイル | `basketball_sim/models/offseason.py`, `basketball_sim/models/season.py`, `basketball_sim/models/team.py`, `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` |
| 補足 | PR・グッズの `money` は `management` 履歴が説明の正（財務画面との分担は `docs/PR_MERCH_MONEY_VISIBILITY_POLICY.md`、2026-04-06）。 |

### 5.9 情報表示 / UI

| 区分 | 内容 |
|------|------|
| 実装済み | 日程表示・大会名表示（`schedule_display.py`, `competition_display.py`）と対応 pytest。 |
| 暫定 | 経営 GUI の一部はダミー表示の記述が `main_menu_view.py` コメント等に存在（**未確認**: 全画面を網羅していない）。 |
| 未実装 | **未確認**（画面単位での照合が必要）。 |
| 未確認 | 全解像度・全ロケール。 |
| 主要ファイル | `basketball_sim/systems/schedule_display.py`, `basketball_sim/systems/competition_display.py` |

### 5.10 負傷対応

| 区分 | 内容 |
|------|------|
| 実装済み | `injury_lineup_autorepair.py` とテストが存在。 |
| 暫定 | **未確認**。 |
| 未実装 | **未確認**。 |
| 未確認 | 実プレイでの体感バランス。 |
| 主要ファイル | `basketball_sim/systems/injury_lineup_autorepair.py` |

### 5.11 セーブ / ロード

| 区分 | 内容 |
|------|------|
| 実装済み | pickle・`format_version`・`PAYLOAD_SCHEMA_VERSION`（`persistence/save_load.py`, `save_payload.py`, `config/game_constants.py`）。テスト `test_phase0_smoke.py` 等。 |
| 暫定 | **未確認**（移行フックの範囲はコード読みが必要）。 |
| 未実装 | Steam クラウドセーブは **v1 に含めない**（2026-04-05 決定、`PRODUCT`・`ea4da85` commit message）。 |
| 未確認 | 旧セーブ全バージョンの実機互換。 |
| 主要ファイル | `basketball_sim/persistence/save_load.py`, `basketball_sim/persistence/save_payload.py` |

### 5.12 Steam 対応

| 区分 | 内容 |
|------|------|
| 実装済み | `steamworks_bridge.py`（DLL ロード・`try_init_steam`・実績 API 経路・環境変数）、`main.py` の `try_init_steam` / `enforce_steam_license` / `--steam-diag`、`config/steam_achievements.py`、テスト `test_steamworks_bridge.py`。実績 `RequestCurrentStats` 順序修正等は git に記録（`85876c0` 等）。**doc（2026-04-06 同期）**: `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`・`docs/PRODUCT_ROADMAP_AND_VISION.md`・`basketball_sim/integrations/STEAMWORKS_DESIGN.md` の **Steam/Phase 0 記述は主要正本間で整合**（旧「2026-03-27 身分確認待ち」前提のズレは解消）。**プロジェクト上の記述**: Steamworks 作業は**再開済み**；条件が揃った環境では **`--steam-diag` 等で Steam API 初期化成功ログ**（例: `try_init_steam: True`）が取れるところまで確認（`PRODUCT`・`STEAMWORKS_STATUS` と整合）。 |
| 暫定 | **未確認**: 開発者マシン以外・ストアビルド以外での挙動の**網羅**。 |
| 未実装 | Rich Presence（設計上 v1 未）、クラウドセーブ（同上）。 |
| 未確認 | **パートナー画面**における**現在の**審査・**ストア一般公開**・**発売審査**・税務/本人確認の**表示**（リポジトリ外。**過去の通過報告と「いまの画面」は別**）。**全環境**での `--steam-diag` 結果の統一は **未確認**（DLL・クライアント・App ID 条件による）。 |
| 主要ファイル | `basketball_sim/integrations/steamworks_bridge.py`, `basketball_sim/integrations/STEAMWORKS_DESIGN.md`, `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`, `docs/PRODUCT_ROADMAP_AND_VISION.md`, `installer/README.md`（存在する場合） |

### 5.13 エンジン（Godot 等）

| 区分 | 内容 |
|------|------|
| 実装済み | **本リポジトリに Godot プロジェクトは含まれていない**（`docs/` を `Godot` で grep しても該当なし、2026-04-06 時点）。 |
| 暫定 | — |
| 未実装 | — |
| 未確認 | ユーザー頭出しの「別エンジン候補」は **本リポジトリの事実としては記載なし**。 |

---

## 6. ここまでに直した重要修正履歴

**出典**: `git log`（2026-04-06 時点で直近に見えたコミット）。日付は commit 順。

| コミット（短） | 内容（要約） |
|----------------|--------------|
| `707b84c` | CLI: トレード・再契約で **プロンプトを入力前に見せる**（flush・段階見出し）。 |
| `9317b4f` | オーナー信頼: **軽微赤字の減点緩和**・**単年減点の下限ガード**。 |
| `ea4da85` | Phase 0 方針: **クラウドセーブなし・Rich Presence なし**（v1）。 |
| `e4750d4` ほか | SteamPipe・実績・depot 関連の docs/実装更新（ログ上）。 |
| `6a85064` | 経営仮調整: オフ締めの **中央配分係数 0.98**。 |
| `d2b8ee9` | 経営仮調整: **初期資金 20 億・ラウンド仮収入**。 |
| `557ff37` | CLI: オフ **cp932 対策**、ドラフト Slot B **空候補**、トレード現金 **b/上限**、**全日本カップ** 表示名。 |

**安定化した重要箇所（事実ベース）**

- セーブ形式・`format_version` / `PAYLOAD_SCHEMA_VERSION` はテストで保護（`test_phase0_smoke.py` 等）。
- 大会表示名の正本は `competition_display.py`（テスト `test_competition_display.py`）。

**巻き戻し注意（一般論）**

- **セーブ互換**・**Steam クライアント起動パス**・**仮経済定数**を無通知で戻すと、プレイ体験・検証ログと齟齬が出やすい。巻き戻す場合は **意図的な差分**として記録することが望ましい（運用ルール・本書の趣旨）。

---

## 7. 重要ファイル一覧

### 7.1 中核

- `basketball_sim/main.py` — CLI メニュー・スモーク・Steam 診断・シーズン操作の集約。
- `basketball_sim/models/season.py` — シーズン進行・日程・大会。
- `basketball_sim/models/offseason.py` — オフ処理・再契約 UI・財務締め（仮配分含む）。
- `basketball_sim/models/team.py` — チーム・オーナーミッション評価。
- `basketball_sim/models/match.py` — 試合シミュ。
- `basketball_sim/persistence/save_load.py` — セーブ/ロード。

### 7.2 波及しやすい / 触りやすい

- `basketball_sim/systems/main_menu_view.py` — 大規模 GUI。
- `basketball_sim/systems/contract_logic.py`, `salary_cap_budget.py` — 契約・キャップの単一入口に近い。
- `basketball_sim/integrations/steamworks_bridge.py` — ネイティブ DLL・起動成否。

### 7.3 直近参照頻度が高い（会話・修正の実績ベース）

- `basketball_sim/systems/schedule_display.py`, `competition_display.py`, `draft_auction.py`, `trade_logic.py` / `main.py` トレード部。

### 7.4 重要 docs

- `docs/PRODUCT_ROADMAP_AND_VISION.md` — Phase・ドメイン正本。
- `docs/AI_WORKFLOW_RULES.md` — 実装手順正本。
- `docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` — 三者同期用ブリッジ。
- `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md` — Steam 手続き・再開メモ（**2026-04-06 本文同期**。詳細は本メモ、`PRODUCT` はロードマップ要約）。
- 仕様分散: `SCHEDULE_MENU_SPEC_V1.md`, `OFFSEASON_WEEK_MODEL.md`, `DRAFT_AUCTION_SYSTEM.md`, `STEAMWORKS_DESIGN.md` 等。

---

## 8. 未解決課題

※ **優先度**は doc・会話の明示に基づくラベル。数値優先順位は付けない。

### 8.1 高優先（doc またはコード上の「残」「最優先」）

- Phase 0 の残（クラッシュログ・設定・配布パイプラインの継続、`PRODUCT` Phase 0 一覧）。
- **GUI 主操作への寄せ**と **CLI 依存の縮小**（`PRODUCT`・引き継ぎ doc）。
- **Steamworks の対外状態の実務確認**（パートナー画面で**都度**確認: ストア一般公開・発売審査・表示上の必須タスク等。**断定はリポジトリ単体では不可**）。Steam **主要 docs の相互同期**は **2026-04-06 完了**（`STEAMWORKS_STATUS`・`PRODUCT`・`STEAMWORKS_DESIGN`）。

### 8.2 中優先

- シーズン中トレード/FA の **GUI からの同一ガード**（`PRODUCT` Phase 3「残」）。
- 経済・オーナー評価の **仮調整から本モデルへの置換**（コードコメント上の意図。時期は **未記載**）。

### 8.3 低優先 / 後回し（doc 上 □ に近いもの）

- BGM/SE、MOD、ベータ運用（`PRODUCT` Phase 5〜6）。

---

## 9. 手動確認で違和感が出やすい箇所

| 現象 | 確認観点 | 関連 |
|------|-----------|------|
| 長いオフシーズン・大量ログ | 対話入力が挟まる経路では **入力順**が重要 | `offseason.py`, ドラフト |
| リダイレクト・パイプ実行 | stdout バッファで **表示が遅れる**可能性 | `sys.stdout.flush` を入れた箇所・それ以外 |
| 経済の「ぬるさ/厳しさ」 | 仮定数（初期資金・ラウンド収入・0.98）の体感 | `team.py`, `season.py`, `offseason.py` |
| オーナー信頼の変化 | 複合ミッションの累積 | `team.py` `evaluate_owner_missions` |

---

## 10. 今すぐ着手しない大型課題

| 課題 | なぜ「今すぐ」と書かないか | doc 上の位置 |
|------|----------------------------|----------------|
| 給与テーブル全面見直し | 会話上「仮経済で様子見」とされてきた事実がある。時期は **未確定**。 | Phase 3 系 |
| ハイライト/2D/音の本格 | Phase 4〜5 の **□/△** 記載。 | `PRODUCT` |
| クラウドセーブ・Rich Presence | **v1 に含めない**が決定済み（`PRODUCT` 2026-04-05、`ea4da85`）。「今やる」対象ではない。 | Phase 0 決定事項 |

---

## 11. よく使う実行コマンド・確認コマンド

（Windows PowerShell 想定。プロジェクトルートで実行。）

```powershell
cd c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim
python -m basketball_sim --smoke
python -m basketball_sim --steam-diag
python -m pytest basketball_sim/tests/test_competition_display.py basketball_sim/tests/test_schedule_display.py basketball_sim/tests/test_season_league_schedule_rules.py -q
```

長いログの保存例（ユーザー環境向け・doc 慣例）:

```powershell
python -m basketball_sim *>&1 | Tee-Object -FilePath cli_log.txt
```

Steam 診断: 上記 `--steam-diag`。**成功/失敗は環境依存**（DLL・Steam クライアント・App ID）。

---

## 12. 現時点の総評

- **土台**: シーズン/オフ/試合/セーブ/最小テストは **リポジトリ上で一貫して厚い**（`PRODUCT` の △〜◎ 記述と整合）。
- **ボトルネック**: **製品としての GUI 一本化**・**経済の本実装**・**Steam のパートナー上の対外状態の確認と Phase 0 残の実務**が、doc と会話の両方で繰り返し現れる。
- **次に取り組むべきテーマ**（複数候補の事実整理）: Phase 0 残の潰し込み、**パートナー画面に基づく Steam 対外状態の更新**（必要なら `STEAMWORKS_STATUS` / `PRODUCT` を追記）、GUI 経路の欠け埋め。**1つに絞る必要は本書ではない**（`.cursorrules` の「次の一手」は会話単位の運用）。

---

## 13. 更新ルール

- コード・運用・正本 docs が変わったら **本書を更新**する。
- **推測・願望・実装順の詳細**は本書に書かない（別 doc）。
- 数値・ファイル数・コミットは **更新時に再取得**する。

---

**改訂履歴**

- 第1版: 2026-04-06 初版作成。
- 2026-04-06: §5.12・§8（Steam）ほか、Steam docs 同期後の整合（§7.4・§12 の関連1行）。
