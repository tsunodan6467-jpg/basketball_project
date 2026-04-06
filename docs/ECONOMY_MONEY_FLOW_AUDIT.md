# 国内バスケGM開発 経営 money フロー監査メモ

**調査日**: 2026-04-06（リポジトリ現状の静的調査）  
**R1 検証追記**: 2026-04-06（§7）  
**R1 実装対応**: 2026-04-06（締めのみ方式・§2 / §4 / §7 更新）  
**大会賞金の正本合流**: 2026-04-06（リーグ所属クラブ・§2 / §3 / R4）  
**シーズン中ラウンド加算の名称整理**: 2026-04-06（§2 行・§3 脚注。`Season._apply_inseason_league_distribution_round`）  
**文書の性質**: **調査報告**。コード変更・仕様決定・理想像の正本ではない。

| 参照 | 文書 |
|------|------|
| 経営本実装の論点・置換順 | `docs/ECONOMY_DESIGN_NOTES.md` |
| **正本外 `money` の扱い方針（整理）** | `docs/ECONOMY_NON_LEDGER_MONEY_POLICY.md` |
| **トレード現金の会計・表示方針** | `docs/TRADE_CASH_ACCOUNTING_POLICY.md` |
| 会計の第1正本・内訳の思想 | `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` §0.3 |
| 現状の事実ラベル | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §5.8 |
| フェーズ上の位置づけ | `docs/IMPLEMENTATION_PLAN_MASTER.md` |

**更新**: `basketball_sim` 側の money 更新経路が変わったら、本書を**事実ベースで**更新する。推測で穴埋めしない。

---

## 0. この文書の使い方

- **目的**: `Team.money` および `record_financial_result` / `finance_history` が **どのコード経路で変わるか**を、実装者・設計者が同じ地図を見られるようにする（`ECONOMY_DESIGN_NOTES` §7 候補 B）。
- **今回の範囲**: リポジトリ内の **`.py` を grep・読解した結果**。実行パス網羅や全分岐の証明は**未実施**（未確認として残す）。
- **断定の扱い**: 「必ず二重計上」とまでは書かず、**リスク候補**として整理する（**R1 は §7 で検証済み**）。
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
| シーズン中（非正本） | `season.py` | `Season._apply_inseason_league_distribution_round` | 全 `all_teams` の `money` | ラウンドごと加算（`INSEASON_LEAGUE_DISTRIBUTION_ROUND_YEN_BY_LEVEL`、`league_level` 別。旧名 `TEMP_ROUND_OPERATING_INCOME_BY_LEVEL` は同一 dict の別名） | **リーグ分配・放映等のラウンド分**（CLI で「シーズン中収益」と表示） | **`finance_history` には載らない** | `simulate_next_round` の試合処理・CPU 裏経営の**前**に実行 |
| シーズン進行順序 | `season.py` | `simulate_next_round` | （上記＋間接） | — | 1 ラウンドのオーケストレーション | 仮収入 → `current_round` 加算 → `run_cpu_management_after_round` | CPU は施設/PR/グッズで間接的に money が動きうる |
| 新規・CLI 初期化 | `main.py` | ユーザーチーム/ライバル設定（該当箇所） | `target_team.money`, `rival_team.money` | 代入 `TEMP_INITIAL_TEAM_MONEY` | セッション開始時の資金 | 正本履歴とは別 | 定数は `main.TEMP_INITIAL_TEAM_MONEY` |
| FA 補完 | `free_agent_market.py` | `ensure_team_fa_market_fields` | `team.money` | 欠損時に `2_000_000_000` 代入 | セーブ互換・欠損ガード | 履歴なし | 本番 `Team` デフォルトも 20 億（`team.py`）と同額 |
| FA 署名（市場） | `free_agent_market.py` | `sign_free_agent` | （年俸の `money` 即時減算**なし**） | — | 年俸はオフ締め payroll → `record`（R1 / 締めのみ） | 正本は `_process_team_finances` 経由 | 2026-04-06 以前は `max(0, money - salary)` あり |
| FA（オフ交渉ループ） | `free_agency.py` | `conduct_free_agency` 内 | （同上） | — | 同上 | 同上 | 2026-04-06 以前は `-= offer` あり |
| トレード現金 | `trade_logic.py` | `TradeSystem.execute_multi_trade` / `execute_one_for_one_trade`（`cash_a_to_b`） | `team_a.money`, `team_b.money` | 現金ネットの移転（`-cash` / `+cash`） | トレード条件の現金 | **`record_financial_result` 未使用** | 現金あり時、`history_transactions` に `trade_cash_delta` / `trade_counterparty_*`。rookie_budget は multi のみ |
| 広報施策 | `pr_campaign_management.py` | `_commit_pr_campaign_core` | `team.money` | 減算（コスト） | 施策コスト | **履歴に載らない**（`management` にログ） | コメントに「局所的な money」と明記 |
| グッズ開発進行 | `merchandise_management.py` | `_advance_merchandise_phase_core` | `team.money` | 減算（開発費） | フェーズ進行コスト | **履歴に載らない**（コメントで money のみ減算と明記） | オフの merchandise 内訳加算は別（コメント参照・本監査では深掘り未） |
| オフ大会報酬（国内クラブ） | `offseason.py` | `_apply_offseason_asia_cup_rewards` → `Team.offseason_competition_revenue_pending` → `_process_team_finances` | リーグ所属 `Team` の賞金 | 締めまで仮積み→`revenue` / `breakdown_revenue` に合流→`record_financial_result` | オフシーズン杯の賞金 | **締め時に正本へ**（内訳キー `offseason_asia_cup_prize`） | **外部招待チーム**は `self.teams` 外のため従来どおり `money` 直接加算 |
| オフ大会報酬（洲际等） | `offseason.py` | `_apply_intercontinental_cup_rewards` → 同上 | 同上 | 同上 | 同上 | **締め時に正本へ**（`intercontinental_cup_prize`） | 同上 |
| FINAL BOSS 報酬 | `offseason.py` | `_apply_final_boss_rewards` → 同上 | 挑戦クラブ（ユーザークラブ想定） | 同上 | イベント報酬 | **締め時に正本へ**（`final_boss_prize`） | 同上 |
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

- **`Season._apply_inseason_league_distribution_round`**: シーズン中のリーグ分配等（非正本）。`finance_history` なし。
- **`pr_campaign_management` / `merchandise_management`**: `money` のみ減算、コメントで明記。`management` 系ログは別。
- **トレード現金**: `record_financial_result` 外。**FA 年俸の即時減算**は廃止（締めのみ・正本側で payroll）。
- **オフ杯・洲际・FINAL BOSS の賞金**: **リーグ所属クラブ**は締めで `record_financial_result` に合流。**外部招待**のみ `money` 直接（正本対象外）。

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
| R1 | ~~同上~~ **2026-04-06 対応**: FA 成立時の年俸即時 `money` 減算を除去し、**締めのみ**（payroll → `record`）に統一 | 旧: `conduct_free_agency` の `money -= offer` と `_process_team_finances` の payroll 重複。現: 即時減算なし（`free_agency.py` / `free_agent_market.py`）。 | **解消済み**（§7 履歴・`ECONOMY_DESIGN_NOTES` §1） |
| R2 | **`finance_history` に載らない支出・収入が累積**し、レポートと `money` の説明がプレイヤーに伝わりにくい | PR・グッズ・トレード現金・仮ラウンド収入（**所属クラブの杯系賞金は 2026-04-06 正本合流**） | 表示設計の課題。**方針整理**: `docs/ECONOMY_NON_LEDGER_MONEY_POLICY.md` |
| R3 | **`record_financial_result` 失敗時フォールバック**が、内訳検証をすり抜けうる | `offseason` の `except` 分岐 | 例外経路のテスト要 |
| R4 | **オフ杯賞金と正本** | **2026-04-06**: リーグ所属は締め `record` 合流で**主に解消**。外部招待のみ `money` 直接のまま | 外部枠はレポート対象外でよいが、列挙時は区別が必要 |
| R5 | **責任主体の分散**: シーズン中は `Season`、オフは `Offseason`、人事は `trade_logic` / FA、施策は各 `systems` | ファイル横断 | 変更時の回帰範囲が広い |
| R6 | **JSON 出口・外部可視化**時、正本外変動が列挙漏れしうる | 散在する直接更新 | 将来タスクのリスク候補 |

---

## 5. 第1正本検証の暫定結論

### 現状の第1正本候補

- **`Team.record_financial_result`** を、コード上の **単一の「公式な収支記録＋`money` 更新」入口**とみなすのが最も一貫している。  
- **年次の主たる呼び出し**は **`Offseason._process_team_finances`**（`season._process_finances` が `money` を触らない旨のコメントと整合）。

### まだ正本と呼びきれない理由

- **`money` が同メソッドを経由せず動く経路**が複数ある（仮収入、トレード、施策、FA 補完、**外部杯招待**の賞金等）。
- **`finance_history` と `money` の差分**が、プレイヤー説明として常に説けるわけではない（R2）。

### 本実装で優先して整えるべき境界（提案・断定ではなく次設計の入力）

1. **`money` を変える全経路の列挙**（本書を正としてメンテ）と、**`record_financial_result` への統合可否**の判断。  
2. **シーズン中の「現金」と「オフ締めのペイロール会計」の二重性（R1）** — **§7 参照（旧挙動は検証済み・2026-04-06 に締めのみ方式で解消）**  
3. **正本外支出**を、§0.3 の内訳スナップショットに載せるか、週次レジャーに載せるか。

---

## 6. 次に切り出しやすいタスク候補（3 件以内）

### T1: R1 の検証（シミュレーション or 単体シナリオ）

- **状態**: **完了**（§7、検証＋**締めのみ実装**、`basketball_sim/tests/test_economy_r1_fa_payroll_trace.py`）。

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

## 7. 検証結果（R1）

**検証日**: 2026-04-06  
**実装対応日**: 2026-04-06 — FA 年俸の `money` 即時減算を廃止（`ECONOMY_DESIGN_NOTES` §1、§2 本表、`basketball_sim/tests/test_economy_r1_fa_payroll_trace.py`）。

### 検証（旧挙動・2026-04-06 以前）

以下は **対応前のコード** に対する検証記録である。

### 検証方法

1. **呼び出し順序の静的確認**: `Offseason.run` 内で `conduct_free_agency` が `_process_team_finances` **より前**（`offseason.py` 550 行付近 → 554 行付近）。  
2. **ペイロール定義の確認**: `_calculate_team_expenses` で `payroll = sum(salary for players)`（3193 行付近）。FA 成立後は新選手が `team.players` に含まれるため、**その年俸がペイロール合計に入る**。  
3. **即時減算の確認（旧）**: `conduct_free_agency` 成立時 `team.money -= offer`（当時 `free_agency.py`）。`offer` は契約の年俸として `candidate.salary` に設定される。  
4. **正本側**: `record_financial_result` は `money += revenue - expense`（`team.py`）。`expense` に上記 `payroll` が含まれる。  
5. **代数テスト**: `tests/test_economy_r1_fa_payroll_trace.py` — 「先に S を引いてから同じ `expense_total` で `record`」と「`record` のみ」の差が **ちょうど S** であることを assert。

### 検証シナリオ（要点）

- **オフ FA 経路**: 同一オフ内で (1) `money -= S` (2) 締めで `expense` にペイロール（S 含む）→ `record`。  
- **シーズン中 FA**（`sign_free_agent`、旧）: `money -= salary` があった。現状は即時減算なし。シーズン終了後の `_process_team_finances` で **ロスター全員の年俸合算**がペイロールに載る。**未確認**: 加入ラウンドによる按分は未実装（通年 sum のみ）。

### 観察した金額の流れ（オフ FA・1 選手・年俸 S のみに注目）

| 段階 | money（イメージ） | 根拠 |
|------|-------------------|------|
| 締め直前（FA後・旧） | M − S | 当時の `conduct_free_agency` の `money -= offer` |
| `record` 後 | M − S + (R − E) | E の内訳に payroll が含み、その payroll に S が含まれる |


**単一路径との比較**: `record` のみ（事前の `money -= S` なし）なら M + (R − E)。差は **−S**。よって **年俸 S が「現金からの即時減算」と「expense 内ペイロール」の両方に現れ、現金残高の意味では S を二回効かせたのと同型**。

### 判定（R1・旧挙動）

- **二重計上あり**（対応前）: 同一 S が即時減算と `record` の expense の両方に効いていた。

### 対応後の状態（2026-04-06）

- **締めのみ方式**: FA 成立時に年俸ぶんの `money` を減算せず、**オフ締めの payroll 合算のみ**が `record_financial_result` の支出に載る。現金残高の意味での **R1 二重効きは解消**。
- **プレイヤー視点**: 年俸の現金反映は「締めの収支」に寄せられる（按分・契約金は未導入）。

### 次に切り出せるタスク候補（経済因果の残論点）

- 按分・契約金・正本外の `money` 更新の整理（`ECONOMY_DESIGN_NOTES`・本書 §4 の他 ID）。  

---

## 8. 更新ルール

- `money` / `record_financial_result` / `finance_history` の更新経路が増減したら、**§2 を更新**する。  
- **推測で埋めない**。実行確認が必要なら「未確認」と書く。  
- **実装・リファクタ**は本書では行わず、別タスクとコミットに分ける。

---

**改訂履歴**

- 2026-04-06: 初版（静的 grep・読解に基づく監査）。
- 2026-04-06: §7 追加 — R1 検証（T1 完了）、§4 R1 更新、§6 T1 完了記載。
- 2026-04-06: R1 **実装** — FA 即時減算廃止、§2 表・§3・§4 R1・§7 に対応後状態を追記。
- 2026-04-06: **大会賞金の正本合流**（リーグ所属）— §2 表3行、§3、R2・R4、§5 本文。
- 2026-04-06: `TRADE_CASH_ACCOUNTING_POLICY.md` 参照を §0 表に追加（トレード現金は別紙で方針整理）。
- 2026-04-06: トレード現金の構造化ログ（`history_transactions` キー）— §2 トレード行・改訂履歴。
- 2026-04-06: 1対1 `execute_one_for_one_trade` の現金も同ログに統一 — §2 トレード行。
