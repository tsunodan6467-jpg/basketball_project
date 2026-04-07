# 国内バスケGM開発 GUI multi トレード導線方針メモ

**作成日**: 2026-04-06  
**文書の性質**: **小設計メモ**。**multi トレード（複数人数＋現金＋RB）**を GUI に載せる場合の**入口・第1実装の範囲**だけを固定する。完成 UI 仕様・`trade_logic` / `evaluate_*` 改修の正本ではない。

| 参照 | 文書 |
|------|------|
| GUI 1対1（人事・選手のみ） | `docs/GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md` |
| GUI 主導線のギャップ | `docs/GUI_MAIN_FLOW_AUDIT.md` |
| CLI トレードメニュー（1対1 / multi） | `docs/TRADE_MENU_ONE_FOR_ONE_ENTRY_POLICY.md` |
| 1対1 と multi の現金・住み分け | `docs/ONE_FOR_ONE_TRADE_CASH_POLICY.md` |
| トレード現金の会計・履歴 | `docs/TRADE_CASH_ACCOUNTING_POLICY.md` |
| 現状ラベル | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §5.5・§5.7 |
| 実装順・フェーズ | `docs/IMPLEMENTATION_PLAN_MASTER.md` |

**コード上の事実（リポジトリ静的確認・2026-04-06）**: `main.propose_multi_trade` は `inseason_roster_moves_unlocked` 後、**6 STEP**（…）→ `TradeSystem` multi 経路。相手候補は `get_trade_candidate_teams`。**GUI**: 人事 **「multi（複数人）」** の **同一ウィザード**で **選手選択＋現金・RB（自分→相手）**まで（`_run_multi_trade_players_only_wizard`）。人数は `validate_multi_trade_player_counts`、現金・RB は `parse_multi_trade_side_payment`（**CLI STEP 5/6 と共用**）。

---

## 0. この文書の使い方

- **何のためか**: multi を人事 GUI に載せる際の**入口・段階的スコープ**を整理する（**第1弾→現金・RB まで**の経緯メモ）。
- **コード変更ではない**: 本書の作成・更新のみ。ウィンドウ実装・`trade_logic` 変更は別タスク。
- **役割分担**: **1対1 の入口・スコープ**は `GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md`。**CLI の番号・文言**は `TRADE_MENU_*`。**現金の会計表示**は `TRADE_CASH_ACCOUNTING_POLICY.md`。本書は **multi の GUI 化の入口と最小スコープ**に限定する。

---

## 1. 現在の multi トレードの位置づけ

| 論点 | 内容 |
|------|------|
| **CLI でできること** | `run_trade_menu` の **3** → `propose_multi_trade`。複数選手の入替（人数制約あり）、**現金**、**RB**、評価表示、`should_ai_accept_multi_trade`、成立時 `execute_multi_trade`（`free_agents` 必須・ロスター違反時の FA 送り等は `trade_logic` 側）。 |
| **GUI で未実装なこと** | **特になし**（multi は人事で CLI 同等の `MultiTradeOffer` まで組める。**未確認**: エッジケースの手動網羅）。 |
| **1対1 GUI との住み分け** | **1対1**＝**選手1対1のみ**（現金・RB なし、`one_for_one_trade_*` / `execute_one_for_one_trade`）。**multi**＝**別 API**（`MultiTradeOffer`、`evaluate_multi_trade`、`execute_multi_trade`）。**混同しない**（ウィンドウタイトル・先頭文で「複数人・現金・RB あり」を明示）。 |
| **CLI multi の位置づけ** | **GUI と並存**（メニュー **3**）。入力順のみ CLI 固有（カンマ入力等）。評価・実行は同一 `TradeSystem`。 |

---

## 2. GUI 入口の候補

| 案 | メリット | デメリット | プレイヤー分かりやすさ | 今の構造への乗せやすさ | 将来拡張 |
|----|----------|------------|------------------------|------------------------|----------|
| **A. 人事画面から入る** | **1対1 と同じ「編成の場」**。`trade_fa_wrap` に **「multi」ボタンを並べる**だけで発見性が揃う。`MainMenuView._all_teams_for_trade_gui`・ロック・`get_trade_candidate_teams` を **1対1 と共有**しやすい。 | 人事を開かないと気づかない（**クラブ案内からの一文誘導**は別タスク可）。 | **高**（トレード＝人事、と既に 1対1 で学習済み）。 | **高**（`main_menu_view` の子 `Toplevel` ウィザード追加が自然）。 | 同ブロックに **入口だけ増やし**、中身はウィザードで段階拡張可能。 |
| **B. 独立トレードウィンドウ / タブ** | **発見性**が高い。製品イメージに直結。 | **左メニューまたは新規ハブ**が要り、人事・1対1 との**説明責任**が増える。第1コミットが重くなりがち。 | **高** | **中**（`MENU_ITEMS` やタブ構成の決定が必要）。 | 長期的にはあり得るが、**最小導線の初手には重い**。 |
| **C. 1対1 GUI の拡張（同一ウィザード内で分岐）** | ウィンドウ数が増えない。 | **「選手のみ」と「複数・現金・RB」**が1画面だと**誤操作・誤解**が増えやすい。ステップ数が大きく変わるため **UI 分岐が複雑**。 | **低〜中** | **低**（1対1 の単純さを損ないやすい）。 | 保守時に **1対1 回帰**のリスクが高い。**非推奨**（入口は分ける）。 |

---

## 3. 最小実装候補の比較

| 候補 | 小さく切れるか | プレイヤー価値 | 既存ロジック流用しやすさ | 今の段階に合うか |
|------|----------------|----------------|--------------------------|------------------|
| **複数人数のみ（現金・RB は 0 固定）** | **高**（STEP 1〜4 相当の UI のみ）。 | **中**（「お金を付けたい multi」は CLI へ戻す必要あり）。 | **高**（`MultiTradeOffer(cash_a_to_b=0, rookie_budget_a_to_b=0)` で **evaluate / accept / execute はそのまま**）。 | **第1マージに最適**（欲張りすぎない切り口）。 |
| **複数人数＋現金まで（RB は 0）** | **中**（金額入力・上限チェックの UI）。 | **高**（CLI の主要パターンに近い）。 | **高**（既存 6 STEP の一部省略）。 | **第2コミット**向き（会計は `TRADE_CASH_ACCOUNTING_POLICY` の既存経路のまま）。 |
| **複数人数＋現金＋RB（CLI と同範囲）** | **低〜中**（ウィザードは長いが **ロジック分岐は増やさない**）。 | **最高**（CLI 不要で multi 完結）。 | **最高**（`propose_multi_trade` の置き換えに近い）。 | **1 タスクで「multi GUI 完了」と言える**が、**初手の画面工数は最大**。 |
| **GUI は入口のみ（詳細は CLI）** | **最高** | **低**（誤解の元。**非推奨**）。 | — | 価値が薄い。 |

**補足（自然な最小案）**: **「第1弾＝複数人数のみ」→「第2弾で現金・RB」**の **2 段コミット**は、`propose_multi_trade` の STEP 順と**一致**し、後戻りが少ない。

---

## 4. 推奨する最小導線

**結論（1 本）**

| 項目 | 内容 |
|------|------|
| **入口** | **案 A — 人事ウィンドウ**のトレード行に、**1対1 の隣**で **「multi（複数人＋現金＋RB）」**（ラベルは実装で短縮可）。**1対1 ウィザードとは別 `Toplevel`**（案 C は取らない）。 |
| **実装済みスコープ（2026-04-06）** | **複数人数＋現金・RB（自分→相手）**まで同一ウィザード。人数・現金・RB の検証は `main` 共用ヘルパ。評価〜実行は **`TradeSystem` 既存のみ**。 |
| **今後やらない（本メモのスコープ外）** | トレード下書き、ドラッグ UI、**1対1 の変更**、`evaluate_*` / `execute_multi_trade` の仕様変更、**structured cash log の新設**。 |

---

## 5. 最小 UI フロー案（ワイヤーなし）

前提: `inseason_roster_moves_unlocked` が偽なら **1対1 と同じロック**で終了。`all_teams` は `_all_teams_for_trade_gui`、相手は `get_trade_candidate_teams`。`free_agents` は `season.free_agents`（GUI モードで `MainMenuView` が保持する `season` から渡す。**未確認**: 全起動経路で `season` が非 `None` かは実装時に要確認）。

| 段 | 内容 | 第1弾に含める |
|----|------|----------------|
| 1 | 相手チーム選択（一覧・1対1 と同型で可） | はい |
| 2 | 出す人数 / 受け取る人数（1〜3、差最大1） | はい |
| 3 | 相手から獲得する選手を **複数選択**（`Listbox` マルチ選択 or チェックリスト等） | はい |
| 4 | 自チームから放出する選手を **複数選択** | はい |
| 5 | 現金（自分→相手）、上限は `user_team.money` | **実装済み**（`parse_multi_trade_side_payment`） |
| 6 | RB（自分→相手）、上限は `rookie_budget_remaining` | **実装済み** |
| — | 評価サマリー表示（`print_trade_evaluation_summary` 相当のテキスト化） | はい |
| — | AI 拒否時は理由表示して終了 | はい |
| — | 最終確認 yes/no → `execute_multi_trade` | はい |
| — | 成功時: ロスター・`refresh` / `_refresh_roster_window` | はい |

**今回やらない（フロー外）**: 相手からの現金・RB 受け取り（**現状 CLI も自分→相手のみ**の前提。変更は本メモのスコープ外）。

---

## 6. 実装時の注意点

| 注意 | 内容 |
|------|------|
| **既存 CLI ロジック流用** | 人数 **`validate_multi_trade_player_counts`**、現金・RB **`parse_multi_trade_side_payment`**（`propose_multi_trade` STEP 5/6 と共用）。評価〜実行は **`TradeSystem` + `MultiTradeOffer`**。 |
| **1対1 との誤解防止** | ウィンドウタイトルに **「multi」**、先頭に **「1対1 ではありません」**は不要だが、**「複数選手。現金・RB は…」**の一文は第1弾で有用。 |
| **現金・RB を先に入れるか** | 本メモ **§4** は **第1弾は省略推奨**。一気に載せるなら **§4 代替案**に従い **6 STEP 完コピ**。 |
| **structured cash log** | `execute_multi_trade` 既存の `history_transactions` をそのまま利用（`TRADE_CASH_ACCOUNTING_POLICY.md`）。**GUI 専用の二重会計は作らない**。 |
| **全ディビジョン候補** | `get_trade_candidate_teams` を **1対1 と共有**し、**母集団のずれ**を作らない。 |
| **将来拡張** | 独立「トレードセンター」（案 B）に移すときも **`execute_multi_trade` への集約は1系**に保ちやすいよう、**オファー組み立て＋1回実行**に寄せる。 |

---

## 7. 次に切り出せる実装タスク候補（2 件以内）

### タスク 1: 人事から multi ウィザード（第1弾・複数人数のみ）— **実装済み（2026-04-06）**

| 項目 | 内容 |
|------|------|
| **目的** | GUI のみで **現金・RB なしの multi** が1回成立する（CLI と同一評価・実行経路）。 |
| **触った範囲** | `main_menu_view.py`（`_run_multi_trade_players_only_wizard`）、`main.validate_multi_trade_player_counts`・`propose_multi_trade` の人数チェック共用。 |
| **次段** | タスク 2（現金・RB）。 |

### タスク 2: multi ウィザードに現金・RB 入力を追加（CLI 同等）— **実装済み（2026-04-06）**

| 項目 | 内容 |
|------|------|
| **目的** | **STEP 5〜6** を GUI に載せ、`propose_multi_trade` と**同能力**にする。 |
| **触った範囲** | 既存ウィザードに **現金・RB ステップ**、`main.parse_multi_trade_side_payment`、CLI の該当ループの共用化。 |

---

## 8. 更新ルール

- **導線方針・第1スコープ**が変わったら本書を更新する。  
- **実装は別タスク・別コミット**。  
- **推測を断定にしない**（例: 全セーブで `season.free_agents` が非 `None` かはコードで確認した範囲のみ書く）。

---

## 変更履歴

- 2026-04-06: 初版。GUI multi の入口（人事推奨）、第1弾スコープ（複数人数のみ→現金RBは第2弾）、フロー・注意・タスク2件。
- 2026-04-06: 第1弾を実装（人事「multi（複数人）」、`validate_multi_trade_player_counts` 追加）。§1・§6・§7 タスク1 を事実に同期。
- 2026-04-06: 第2弾として現金・RB 入力を同一ウィザードに追加（`parse_multi_trade_side_payment`、§4・§5・§7 を同期）。
