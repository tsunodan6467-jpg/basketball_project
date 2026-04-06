# 国内バスケGM開発 経営 money フロー監査メモ

**調査日**: 2026-04-06（リポジトリ現状の静的調査）  
**文書の性質**: **調査報告**。コード変更・仕様決定・理想像の正本ではない。

| 参照 | 文書 |
|------|------|
| 経営本実装の論点・置換順 | `docs/ECONOMY_DESIGN_NOTES.md` |
| 会計の第1正本・内訳の思想 | `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` §0.3 |
| 現状の事実ラベル | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §5.8 |
| フェーズ上の位置づけ | `docs/IMPLEMENTATION_PLAN_MASTER.md` |

**更新**: `basketball_sim` 側の money 更新経路が変わったら、本書を**事実ベースで**更新する。推測で穴埋めしない。

---

## 0. この文書の使い方

- **目的**: `Team.money` および `record_financial_result` / `finance_history` が **どのコード経路で変わるか**を、実装者・設計者が同じ地図を見られるようにする（`ECONOMY_DESIGN_NOTES` §7 候補 B）。
- **今回の範囲**: リポジトリ内の **`.py` を grep・読解した結果**。実行パス網羅や全分岐の証明は**未実施**（未確認として残す）。
- **断定の扱い**: 「必ず二重計上」とまでは書かず、**リスク候補**として整理する。
- **役割分担**: 設計の「べき論」は `ECONOMY_DESIGN_NOTES`、メニュー UI の詳細は `GM_MANAGEMENT_MENU_SPEC_V1.md`、本書は **いまのコードの事実**に限定する。

---

## 1. 調査対象と方法

### 参照した文書

- 上表の4文書（§0.3 の第1正本・内訳スナップショットの記述を確認）。

### 読んだ主要ファイル（代表）

- `basketball_sim/models/team.py` — `record_financial_result`
- `basketball_sim/models/offseason.py` — 締め・大会報酬・外部チーム生成
- `basketball_sim/models/season.py` — ラウンド仮収入・`_process_finances`（金額は触らない旨）
- `basketball_sim/main.py` — 初期所持金
- `basketball_sim/systems/trade_logic.py` — `execute_multi_trade`
- `basketball_sim/systems/free_agent_market.py` — `sign_free_agent` / `ensure_team_fa_market_fields`
- `basketball_sim/systems/free_agency.py` — `conduct_free_agency` 内の署名時
- `basketball_sim/systems/facility_investment.py` — `commit_facility_upgrade`
- `basketball_sim/systems/pr_campaign_management.py` — `_commit_pr_campaign_core`
- `basketball_sim/systems/merchandise_management.py` — `_advance_merchandise_phase_core`
- `basketball_sim/systems/cpu_management.py` — 間接経路（`commit_*` 経由）
- `basketball_sim/systems/finance_report_display.py` — コメント上の正本参照
- `basketball_sim/persistence/` — `money` 専用処理の有無（**ヒットなし**）

### 使った検索

- `\.money\s*[=+\-]|\.money\s*\+=|record_financial_result|finance_history`
- `money` を含む行の広めの grep（テスト・`__main__` ダミー含む）

### 「money 更新」とみなしたもの

- `team.money` / `Team` 相当に対する **代入・加算・減算**（`max(0, …)` を含む）。
- `Team.record_financial_result` 内の `self.money += cashflow`（実質的な正本経路）。
- **除外**: テストコード内の期待値、`main_menu_view.py` の `if __name__ == "__main__"` 内 `_DummyTeam`（本番ゲームの `Team` ではない）。

---

## 2. 現在の money 更新経路の一覧

※ **未確認**: 別名のヘルパ経由や動的 `setattr` による更新は、今回の grep で**拾えていない可能性**あり。

| 区分 | ファイル | 関数 / 箇所 | 更新対象 | 更新方法 | 目的 / 文脈 | 正本履歴との関係 | 備考 |
|------|----------|-------------|----------|----------|-------------|------------------|------|
| 正本（集約） | `team.py` | `Team.record_financial_result` | `money`, `revenue_last_season`, `expense_last_season`, `cashflow_last_season`, `finance_history` | `money` に `revenue - expense` を加算、`finance_history` に payload | シーズン収支の**公式記録**（内訳は合計一致時のみ payload に載る） | **第1正本に最も近い**単一入口 | `GM_MANAGEMENT` §0.3 の「第1正本」思想と一致 |
| オフ締め | `offseason.py` | `Offseason._process_team_finances` | 同上（通常は `record_financial_result` 経由） | 主に `record_financial_result(...)` 呼び出し | 年次の収支・ペイロール・維持費等を計算し締める | **正本更新の主呼び出し元**（`season._process_finances` コメントと整合） | `TEMP_OFFSEASON_CENTRAL_PAYROLL_SHARE` で収入側を補正したうえで記録 |
| オフ締め・フォールバック | `offseason.py` | 同上（`try/except` 内） | `money`, `revenue_last_season` 等, `finance_history` | `record_financial_result` 失敗時は **手動で** `finance_history.append` + `money += cashflow` + スカラー更新 | 例外時の継続 | 正本と**同じ数値意図**だが、`record_financial_result` の内訳検証を**バイパス**しうる | リスク候補（§4） |
| 施設投資 | `facility_investment.py` | `commit_facility_upgrade` | `money`（他に Lv・人気等） | `record_financial_result(revenue=0, expense=cost, …)` | 投資コストを支出として記録 | **正本経由** | CPU 経由でも同関数 |
| 仮調整（シーズン中） | `season.py` | `Season._apply_temporary_round_operating_income` | 全 `all_teams` の `money` | ラウンドごと加算（`TEMP_ROUND_OPERATING_INCOME_BY_LEVEL`） | 営業キャッシュの**仮注入** | **`finance_history` には載らない** | `simulate_next_round` の試合処理・CPU 裏経営の**前**に実行（2775 行付近） |
| シーズン進行順序 | `season.py` | `simulate_next_round` | （上記＋間接） | — | 1 ラウンドのオーケストレーション | 仮収入 → `current_round` 加算 → `run_cpu_management_after_round` | CPU は施設/PR/グッズで間接的に money が動きうる |
| 新規・CLI 初期化 | `main.py` | ユーザーチーム/ライバル設定（該当箇所） | `target_team.money`, `rival_team.money` | 代入 `TEMP_INITIAL_TEAM_MONEY` | セッション開始時の資金 | 正本履歴とは別 | 定数は `main.TEMP_INITIAL_TEAM_MONEY` |
| FA 補完 | `free_agent_market.py` | `ensure_team_fa_market_fields` | `team.money` | 欠損時に `2_000_000_000` 代入 | セーブ互換・欠損ガード | 履歴なし | 本番 `Team` デフォルトも 20 億（`team.py`）と同額 |
| FA 署名（市場） | `free_agent_market.py` | `sign_free_agent` | `team.money` | `max(0, money - salary)` | 推定年俸を**即時に現金から減算** | **`record_financial_result` 未使用** | 年俸の会計上の扱い（前払/按分）は別論点 |
| FA（オフ交渉ループ） | `free_agency.py` | `conduct_free_agency` 内 | `team.money` | `-= offer` | CPU/一括 FA 交渉での契約成立時 | **`record_financial_result` 未使用** | `sign_free_agent` と**別経路** |
| トレード現金 | `trade_logic.py` | `TradeEngine.execute_multi_trade` | `team_a.money`, `team_b.money` | 現金ネットの移転（`-cash` / `+cash`） | トレード条件の現金 | **`record_financial_result` 未使用** | rookie_budget は別フィールド |
| 広報施策 | `pr_campaign_management.py` | `_commit_pr_campaign_core` | `team.money` | 減算（コスト） | 施策コスト | **履歴に載らない**（`management` にログ） | コメントに「局所的な money」と明記 |
| グッズ開発進行 | `merchandise_management.py` | `_advance_merchandise_phase_core` | `team.money` | 減算（開発費） | フェーズ進行コスト | **履歴に載らない**（コメントで money のみ減算と明記） | オフの merchandise 内訳加算は別（コメント参照・本監査では深掘り未） |
| オフ大会報酬（国内クラブ） | `offseason.py` | `_apply_offseason_asia_cup_rewards` | 優勝・準優勝の `money` | 加算（固定額） | オフシーズン杯の賞金 | **`record_financial_result` 未使用** | `finance_history` 非連動 |
| オフ大会報酬（洲际等） | `offseason.py` | `_apply_intercontinental_cup_rewards` | 同上 | 加算 | 同上 | 同上 | 同上 |
| FINAL BOSS 報酬 | `offseason.py` | `_apply_final_boss_rewards` | `challenger.money` | 加算（クリア/失敗で額不同） | イベント報酬 | 同上 | 同上 |
| 外部仮想チーム | `offseason.py` | `_create_external_asia_cup_team`, `_create_final_boss_team` | 生成 `Team.money` | 代入（800万 / 999999999 等） | プレイ用チームの初期値 | リーグ正本の財務とは別枠 | 国内リーグ `Team` のキャッシュフローとは別目的 |
| 欠損ガード | `offseason.py` | `_process_team_finances` ループ先頭 | `team.money` | `hasattr` なし時 `10_000_000` 代入 | 極端な欠損データの保険 | その後 `record_financial_result` で締め | |

### `record_financial_result` の呼び出し元（調査範囲）

| ファイル | 箇所 | 備考 |
|----------|------|------|
| `offseason.py` | `_process_team_finances` | 内訳 `breakdown_revenue` / `breakdown_expense` を渡す（`provisional_central_distribution` 含む） |
| `facility_investment.py` | `commit_facility_upgrade` | 支出のみ（`revenue=0`） |
| `tests/test_finance_report_display.py` | テスト | 本番経路ではない |

### `finance_history` の append

- **主経路**: `Team.record_financial_result` 内。
- **副経路**: `offseason._process_team_finances` の `record_financial_result` **失敗時**の `except` 節、および `record_financial_result` **非存在**時の `elif hasattr(team, "finance_history")` 分岐（手動 append + `money` 加算）。

### persistence

- `basketball_sim/persistence/` 内に **`money` / `finance_history` を特別扱いする記述は見つからず**（チーム丸ごとシリアライズ想定）。**未確認**: ペイロード移行フック全体の網羅。

---

## 3. 正本に近い経路 / 横入り経路の整理

### 正本に近い経路

- **`Team.record_financial_result`**: `money`・前季スカラー・`finance_history` を**一括で**更新し、内訳は合計一致時のみ永続化（`team.py` 実装）。
- **`Offseason._process_team_finances` → record_financial_result`**: シーズン年次締めの**意図された正本**（`season._process_finances` ドキュメントと一致）。

### サイドエフェクト的（履歴に乗らない or 正本外）

- **`Season._apply_temporary_round_operating_income`**: 仮調整。`finance_history` なし。
- **`pr_campaign_management` / `merchandise_management`**: `money` のみ減算、コメントで明記。`management` 系ログは別。
- **トレード現金 / FA 署名時の即時減算・加算**: `record_financial_result` 外。
- **オフ杯・洲际・FINAL BOSS の賞金加算**: `record_financial_result` 外。

### 仮調整

- ラウンド営業収入（`season`）、オフ締めの `TEMP_OFFSEASON_CENTRAL_PAYROLL_SHARE`（`offseason` の収入計算側。**`money` への反映自体は record 経由**）。

### 将来の置換候補（設計メモと対応）

- ラウンド仮収入 → `ECONOMY_DESIGN_NOTES` §5 段階 2。
- オフ締め集中配分 → 同 §5 段階 3。
- 正本外の `money` 変動 → **すべて `record` または内訳付きサブレジャーに寄せるか**を別タスクで判断。

---

## 4. リスク候補

| ID | 内容 | 根拠（事実） | 断定 |
|----|------|----------------|------|
| R1 | **同じシーズンで「給与・契約」と「オフ締めのペイロール支出」が別ルールで数えられる** | FA 署名で `money` を即減算しつつ、オフで `_calculate_team_expenses` がペイロールを含む可能性 | **リスク候補**（会計モデルの整合要検証） |
| R2 | **`finance_history` に載らない支出・収入が累積**し、レポートと `money` の説明がプレイヤーに伝わりにくい | PR・グッズ・杯賞金・トレード現金・仮ラウンド収入 | 表示設計の課題 |
| R3 | **`record_financial_result` 失敗時フォールバック**が、内訳検証をすり抜けうる | `offseason` の `except` 分岐 | 例外経路のテスト要 |
| R4 | **オフ杯賞金が `record_financial_result` を通らない** | `_apply_*_rewards` は `money` のみ加算 | 年次レポートの「収入」に含まれるかプレイヤー認識とズレうる |
| R5 | **責任主体の分散**: シーズン中は `Season`、オフは `Offseason`、人事は `trade_logic` / FA、施策は各 `systems` | ファイル横断 | 変更時の回帰範囲が広い |
| R6 | **JSON 出口・外部可視化**時、正本外変動が列挙漏れしうる | 散在する直接更新 | 将来タスクのリスク候補 |

---

## 5. 第1正本検証の暫定結論

### 現状の第1正本候補

- **`Team.record_financial_result`** を、コード上の **単一の「公式な収支記録＋`money` 更新」入口**とみなすのが最も一貫している。  
- **年次の主たる呼び出し**は **`Offseason._process_team_finances`**（`season._process_finances` が `money` を触らない旨のコメントと整合）。

### まだ正本と呼びきれない理由

- **`money` が同メソッドを経由せず動く経路**が複数ある（仮収入、トレード、FA、施策、杯賞金等）。
- **`finance_history` と `money` の差分**が、プレイヤー説明として常に説けるわけではない（R2）。

### 本実装で優先して整えるべき境界（提案・断定ではなく次設計の入力）

1. **`money` を変える全経路の列挙**（本書を正としてメンテ）と、**`record_financial_result` への統合可否**の判断。  
2. **シーズン中の「現金」と「オフ締めのペイロール会計」**の二重性の有無の検証（R1）。  
3. **正本外支出**を、§0.3 の内訳スナップショットに載せるか、週次レジャーに載せるか。

---

## 6. 次に切り出しやすいタスク候補（3 件以内）

### T1: R1 の検証（シミュレーション or 単体シナリオ）

- **目的**: FA 署名・インシーズン減算と、オフ締めペイロールの **`money` 整合**を1シーズン分で数値追跡し、二重計上の有無を**事実で**記録する。  
- **触る範囲**: 新規テスト or 手順付きメモ（**コード変更は別コミット**）。  
- **触らない範囲**: 定数変更、ロジック修正（検証結果が出るまで）。  
- **完了条件**: 「二重である/ない/部分的重複」の**観察結果**が1ページに書ける。

### T2: `record_financial_result` 失敗フォールバックのテスト

- **目的**: `offseason` の `except` 経路で、`finance_history` と `money` が**意図どおり**かを回帰で固定。  
- **触る範囲**: `tests/` のみ（**別タスク**）。  
- **触らない範囲**: 本番ロジックのリファクタ。  
- **完了条件**: フォールバックが発火する条件をモックし、**1本以上**の pytest が緑。

### T3: 正本外 money 更新の「表示ラベル」表（doc のみ）

- **目的**: 経営画面・CLI で「この変動は履歴のどこに出るか」を **プレイヤー向けに**整理（実装は後）。  
- **触る範囲**: `docs/` のみ。  
- **触らない範囲**: GUI コード。  
- **完了条件**: 本書 §2 の各行について **表示方針が TBD/表示あり/非表示**の3値が振れる。

---

## 7. 更新ルール

- `money` / `record_financial_result` / `finance_history` の更新経路が増減したら、**§2 を更新**する。  
- **推測で埋めない**。実行確認が必要なら「未確認」と書く。  
- **実装・リファクタ**は本書では行わず、別タスクとコミットに分ける。

---

**改訂履歴**

- 2026-04-06: 初版（静的 grep・読解に基づく監査）。
