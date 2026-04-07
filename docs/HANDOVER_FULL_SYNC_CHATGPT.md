# 国内バスケGM開発プロジェクト 完全引き継ぎ書（新Chat同期用）

**文書の性質**: 新しい ChatGPT（または別セッション）が **この1本を読めば、2026-04-06 時点のリポジトリ認識と開発続行の前提を再現できる**ことを目的とする **正本級ハンドオフ**。  
**基準日**: 2026-04-06（ユーザーサイドの「Today's date」および `docs/` の主要更新日に整合）  
**コードの正本**: 本書は **説明**であり、数値・挙動の最終断定は **コード**と **個別の専用 doc** に従う。  
**既存ブリッジ**: `docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` は Cursor/ChatGPT 三者同期の短い要約。**本書は 2026-04 前後の GUI・FA・経済の積み上げを補完・上書きする詳細版**として使う。

---

## 0. 最初に絶対守る固定ルール

### 0.1 ユーザーの固定ルール（チャット・実装の前提）

- **日本語**: チャット・ゲーム内表示は日本語（コード・識別子・コミットは英語可）。
- **安定性最優先**: クラッシュ・セーブ破損・再現不能を最も恐れる。
- **最小変更・ついで修正禁止**: 依頼と無関係な広げ変更をしない。
- **中規模以上はいきなり実装しない**: 調査・計画・完了条件を先に（例外はタイポ・import・1ファイル内の安全な小修正）。
- **実装後の自己レビュー**: 依頼箇所・近接・None・イベント順・テスト等。
- **実環境で調査**: 可能ならコマンド実行・ツールで確認し、「実行してください」だけに逃げない（ユーザー方針）。
- **Cursor 返答の締め**: 「手動でやってほしいこと」「次の一手（**1つだけ**）」を分ける（`.cursorrules`）。
- **Git**: 作業単位ごとに commit / push、**1コミット1目的**。
- **コード引用**: 会話でコードを示すときは ```startLine:endLine:path``` 形式（Cursor ルール）。
- **日付**: ユーザーコンテキストの「Today's date」を権威とする（推測で過去年を埋めない）。

### 0.2 回答スタイル

- 技術ブログ品質の日本語（完整文、過剰な装飾やテンプレート的締めを避ける）。
- 不確かなことは **未確認** と明記し、断定しない。

### 0.3 コード提示方針

- 長文の全文貼り付けより **ワークスペース上のファイル参照**（`AI_WORKFLOW_RULES.md` と同旨）。

### 0.4 次タスクは原則1つだけ

- 実装計画書・本書とも **「次の一手」は1本に絞る**運用（複数候補は並記しても **推奨は1つ**）。

### 0.5 安定性最優先

- セーブ形式・`PAYLOAD_SCHEMA_VERSION`・Steam 起動経路を変える変更は **影響範囲と移行**を先に書く（`PRODUCT_ROADMAP_AND_VISION.md` と整合）。

### 0.6 Steam 販売目標（プロダクト文脈）

- **Steam** での商品化が前提。**v1 ではクラウドセーブ・Rich Presence は含めない**（2026-04-05 決定、`ea4da85` ほか `PRODUCT_ROADMAP_AND_VISION.md` 記載）。
- 価格・本数のミッション文脈は `CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` §2（例: 単価1500円・10000本）に要約あり。**最終価格はリリース時判断**。

---

## 1. 現在のプロジェクト全体像

### 1.1 作品概要

- 日本のプロバスケを**参考**にした**独自リーグ**の GM シミュレーション（架空の名称）。**Python**、GUI は **tkinter**。
- エントリ: `python -m basketball_sim`（`__main__.py` → `main.simulate()`）。**`--smoke`** は対話なし最小経路。**`--steam-diag`** は Steam 橋の診断。
- **製品としての主操作は GUI** が目標。CLI は開発・CI・検証用に併存（`PRODUCT_ROADMAP_AND_VISION.md`）。

### 1.2 コア制度の現在地（要約）

| 領域 | 事実ベースの位置づけ（詳細は `CURRENT_STATE_ANALYSIS_MASTER.md`） |
|------|------------------------------------------------------------------|
| リーグ・シーズン | 48チーム3部、進行・PO・昇降格など **実装は厚い** |
| 試合 | `Match` シミュ、ローテ・規約関連モジュールあり |
| セーブ | pickle・`format_version`・pytest で保護 |
| 経済 | **仮調整**（初期資金・ラウンド加算・オフ締め係数 `TEMP_*`）で回している。**本実装は設計整理が先**（`ECONOMY_DESIGN_NOTES.md`） |
| Steam | 橋渡し・実績 API・diag あり。**パートナー画面の「いま」の状態はリポジトリ外**（人間確認が必要なら doc に日付と事実を残す） |

### 1.3 現在の重点領域

1. **Phase 0**（安定・配布・Steam 商品成立）— ロードマップ上 ★現在地  
2. **GUI 主導線**（人事・オフ・進行の迷子削減）— 2026-04 前後で **編成まわりが大幅に前進**  
3. **FA 年俸の二系統**（estimate vs `_calculate_offer`）— **オフ手動のみ本格FA同型に寄せ済**＋ **payroll_budget 起因の回帰をフォールバックで修正済**（後述）

---

## 2. 開発環境・実行前提

### 2.1 よく使うコマンド（Windows・プロジェクトルート）

```powershell
cd c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim
python -m basketball_sim --smoke
python -m basketball_sim --steam-diag
python -m pytest basketball_sim/tests/ -q
```

### 2.2 ログ

- 長時間 CLI: `python -m basketball_sim *>&1 | Tee-Object -FilePath cli_log.txt`（慣例）

### 2.3 GUI / CLI の前提

- **GUI 主画面**: `basketball_sim/systems/main_menu_view.py`（左メニュー、中央「次へ進む」ほか）。
- **CLI オフ**: `Offseason` に `resign_ui_prompt` / `pre_conduct_free_agency_ui_prompt` **未注入**のため、再契約は標準入力、オフ手動1人FAウィンドウは **出ない**（`GUI_FA_CONTRACT_ENTRY_POLICY.md` / `GUI_FULL_FA_MARKET_ENTRY_POLICY.md` と整合）。

---

## 3. 直近の重要方針

### 3.1 GUI 主導線強化

- **目的**: 製品でプレイヤーが **ターミナルなしで** 主要編成判断を完結できるようにする。
- **監査の正本**: `docs/GUI_MAIN_FLOW_AUDIT.md`（メニュー役割・穴・優先度）。
- **2026-04-07 前後の緩和**: 主画面進行パネル先頭の**一文案内**、日程・情報・歴史ウィンドウ先頭の**一文案内**（迷子対策）。

### 3.2 人事 GUI 本格化（達成済みの範囲）

- **1対1トレード（選手のみ）**: 人事から。`main` 共用ヘルパ＋`TradeSystem`。**相手候補は全ディビジョン**（`get_trade_candidate_teams`）。
- **multi トレード（複数人・現金・RB）**: **人事 GUI でも CLI と同等スコープで実装済**（`GUI_MULTI_TRADE_ENTRY_POLICY.md`）。CLI `run_trade_menu` も継続。
- **契約解除（FA 送り）**: ロスター選択＋**トレード行または下部**の同一ハンドラ（`_on_roster_release_selected`）。
- **インシーズンFA（1人）**: 人事から `sign_free_agent`。**`run_gm_menu` に FA 契約メニューはない**（事実）。

### 3.3 オフ FA の最小 GUI

- **再契約 y/n**: `Offseason` の `resign_ui_prompt` 注入 → `offseason_resign_tk.prompt_user_resign_offer`（GUI オフ時）。
- **本格 `conduct_free_agency` 直前の手動1人**: `pre_conduct_free_agency_ui_prompt` → `offseason_full_fa_tk.run_user_offseason_fa_one_pick`。**`conduct_free_agency` 本体は無改変**。

### 3.4 FA 年俸問題の現在地

| 経路 | 年俸・年数の決め方（**2026-04-06 以降の事実**） |
|------|--------------------------------------------------|
| **オフ・手動1人 GUI** | 単一ソース `offseason_manual_fa_offer_and_years` → 原則 `_calculate_offer` / `_determine_contract_years`。**例外**: オフFA直前は `_process_team_finances` より前で `payroll_budget` が実ペイロールに対して小さいと `_calculate_offer` が 0 になりうる → **`get_team_fa_signing_limit` に余地があるときだけ** `min(estimate_fa_market_value, room)` にフォールバック（**オフ手動専用**、`8fb5906`）。 |
| **オフ・CPU 本格FA** | `conduct_free_agency` 内で `_calculate_offer` / `_determine_contract_years`（従来どおり）。 |
| **インシーズン・手動 GUI** | `estimate_fa_market_value` / `estimate_fa_contract_years`（**オフ手動とは別モデル**・方針どおり）。 |
| **インシーズン・CPU 補強** | `sign_free_agent`（estimate）。 |

- **表示＝契約**: オフ手動では一覧・`precheck_user_fa_sign(contract_salary=…)`・`sign_free_agent(contract_salary=…, contract_years=…)` が **同じ offer/years**（`FA_SALARY_ESTIMATE_AUDIT.md` §2.1・§3 と整合）。
- **注意（doc 鮮度）**: `FA_SALARY_ESTIMATE_AUDIT.md` の **§5 比較表**の一部は、§2.1 更新前の表現が残る可能性がある。**オフ手動と estimate の関係は §2.1・§3 を正**とする（必要なら表の追従が別タスク）。

---

## 4. GUI 編成導線の現在地

### 4.1 いま GUI でできること（人事・オフ関連）

- ロスター閲覧、**契約＋1年**、**FA 送り**、**1対1 トレード**、**multi トレード（現金・RB 込み）**、**インシーズンFA（1人）**。
- **オフ実行中（GUI）**: **再契約ダイアログ**、**本格FA直前の手動1人**。

### 4.2 まだ未完了・弱いこと（docs 整合）

- **本格 FA 市場の全面 GUI**（`conduct_free_agency` をユーザー参加型に作り替える類）は **未**。第1弾は **直前の手動1人のみ**（`GUI_FULL_FA_MARKET_ENTRY_POLICY.md`）。
- **手動1人の直後に CPU 本格FAが走り、ユーザーチームも再度補強されうる**（二重化）。**第2タスク候補として doc に明記**（同書 §4・§7 タスク2）。
- **シーズン中の「GUI と CLI の同一ガード」**の完全達成は `PRODUCT` 上まだ **残** の記述あり（現状分析 §8）。
- **1対1 方針メモ**（`GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md`）の本文に、昔の「multi は CLI のみ」に近い行が残る箇所がある。**最新の事実は `GUI_MAIN_FLOW_AUDIT.md` と `GUI_MULTI_TRADE_ENTRY_POLICY.md`**（人事 multi 実装済）。

### 4.3 人事 GUI の現在価値

- **編成の実操作の大半**（トレード・FA送り・インシーズン1人FA）が **人事1カ所に集約**されつつある。オフ固有は **オフ実行フロー内**（再契約・手動1人）。

---

## 5. このセッション期に完了した大きな実装群（時系列・要約）

**厳密な git log でなく、流れ理解用**（最新が上）。

| 時期 | 内容 |
|------|------|
| 2026-04-06 前後 | 人事 **1対1 トレード GUI**、**multi GUI**（段階的に現金・RB まで）、**インシーズンFA 1人**、**FA送りボタン配置**、**オフ再契約 GUI**、**オフ本格FA直前の手動1人 GUI**、**FA 年俸整合（オフ手動→`_calculate_offer` 系）**、**payroll_budget 起因の全件0オファー回帰修正**（フォールバック） |
| 同頃 | 主画面・日程・情報・歴史の**一文案内**、1対1トレード一覧に**年齢・国籍・年俸**、強化/戦術/デバッグの**レイアウト修正** |
| 同頃 | **docs** に GUI 方針・FA 監査・整合方針・実装計画・現状分析の**相互参照更新** |

### 5.1 代表的コミット（短縮ハッシュ・意味）

- `8fb5906` — オフ手動FA: `payroll_budget` で `_calculate_offer` が 0 になる場合の **estimate＋signing_room フォールバック**
- `f2fe902` — オフ手動FA を **本格FA同型オファー**に整合（`sign_free_agent` 拡張等）
- `a952895` / `846118a` — オフ本格FA直前の **手動1人**＋方針 doc
- `98abca8` / `283a13b` / `d28b07f` — **multi GUI** ＋方針 doc
- `d9ee6f7` / `9b7ae76` — **インシーズンFA 1人** ＋方針 doc
- `58deafb` / `ca8b193` — **オフ再契約 GUI** ＋ FA/契約方針 doc
- `cee354c` / `49e9825` — **1対1 トレード GUI** ＋方針 doc
- `1b276b5` / `fafef31` — 主画面・他ウィンドウの**案内一文**

### 5.2 更新された docs（代表）

- `GUI_MAIN_FLOW_AUDIT.md`、`GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md`、`GUI_MULTI_TRADE_ENTRY_POLICY.md`、`GUI_FA_CONTRACT_ENTRY_POLICY.md`、`GUI_INSEASON_FA_ENTRY_POLICY.md`、`GUI_FULL_FA_MARKET_ENTRY_POLICY.md`
- `FA_SALARY_ESTIMATE_AUDIT.md`、`FA_SALARY_MODEL_ALIGNMENT_POLICY.md`
- `CURRENT_STATE_ANALYSIS_MASTER.md`、`IMPLEMENTATION_PLAN_MASTER.md`
- 経済系: `ECONOMY_*`（ユーザー指定リストに含まれるものは **設計・監査の正本**として参照）

---

## 6. 現在の最重要未解決課題

### 6.1 いま何が一番大事か（プロダクト横断）

- **Phase 0 の完了度**（セーブ・ビルド・配布・Steam としての商品成立）が、ロードマップ上の **★現在地**（`PRODUCT_ROADMAP_AND_VISION.md`、`CURRENT_STATE_ANALYSIS_MASTER.md` §2）。
- **並行して**: **GUI 主操作の残ギャップ**（本格FA全面化は未、オフ手動後の **CPU 二重補強**はプレイ感・説明上の課題）。

### 6.2 なぜそれが「次」の議論になるか

- Steam・配布を止めると **販売に進めない**。
- 二重補強を放置すると、**オフ手動1人の意図がログ上すぐ上書きされうる**とプレイヤーが感じる（`GUI_FULL_FA_MARKET_ENTRY_POLICY.md` が明示）。

### 6.3 直近の推奨方針（doc 上）

- **実装計画の実行順**（`IMPLEMENTATION_PLAN_MASTER.md` §11）: 先に **Steam 正本の事実整合** → Phase 0 残の1件化 → 経営設計 → GUI 中核設計…  
- **現状分析**（`CURRENT_STATE_ANALYSIS_MASTER.md` §5.12・§8）: **主要 Steam docs の相互同期は 2026-04-06 完了**と記載。**残るのはパートナーポータル上の「いま」の事実の都度確認**（リポジトリ単体では断定不可）。

---

## 7. 次タスクの具体的な進め方

### 7.1 新Chatが最初に確認すること（15分チェック）

1. `docs/IMPLEMENTATION_PLAN_MASTER.md` の **§11・§12**（実行順と「次にやる1件」）。
2. `docs/CURRENT_STATE_ANALYSIS_MASTER.md` の **§5.7（人事）・§8（未解決）**。
3. `docs/GUI_FULL_FA_MARKET_ENTRY_POLICY.md` の **§7 タスク2**（二重補強）が、**いまのコードとまだ未解決か**を `free_agency.py` / `offseason.py` で確認。

### 7.2 いきなりやってはいけないこと（このプロジェクトの合意）

- **`conduct_free_agency` の市場アルゴリズムの大型書き換え**（第1弾方針は **触らない**）。
- **estimate の係数だけいじってごまかす**（FA 方針で明示的に避ける）。
- **セーブ形式の無計画破壊**、**ついで修正だらけの巨大コミット**。

### 7.3 次タスク **1つだけ**（本書の推奨）

**`docs/IMPLEMENTATION_PLAN_MASTER.md` §12 に従い、「Steam 関連正本 docs の同期確定」を完了条件ベースで棚卸しする。**  
具体的には:

1. `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md` と `docs/PRODUCT_ROADMAP_AND_VISION.md`（Phase 0・Steam 節）を並読する。  
2. **パートナー画面で人間が確認した事実**（公開状態・デポ・ビルド・未了タスク）が **未記載なら追記**し、**最終確認日**を残す。  
3. もし **既にすべて満たしている**と判断したら、**§12 を「完了」に更新**し、**次キューとして `IMPLEMENTATION_PLAN_MASTER.md` §11 のステップ2（Phase 0 残の1件化）** または **`GUI_FULL_FA_MARKET_ENTRY_POLICY.md` §7 タスク2（二重補強）** の **どちらか1件だけ** を新§12に立てる（**商業最優先なら前者、編成体験最優先なら後者** — 迷ったらユーザーに1行確認）。

※ **コード変更は必須ではない**（doc のみで完結しうる）。

---

## 8. 重要ドキュメント一覧（新Chatがまず見るべきもの）

| 優先 | パス | 役割 |
|------|------|------|
| ★ | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` | 現状の事実ラベル正本 |
| ★ | `docs/IMPLEMENTATION_PLAN_MASTER.md` | 実装順・「次の1件」 |
| ★ | `docs/PRODUCT_ROADMAP_AND_VISION.md` | Phase・ドメイン長文 |
| ★ | `docs/GUI_MAIN_FLOW_AUDIT.md` | GUI 導線の穴と優先度 |
| ★ | `docs/FA_SALARY_ESTIMATE_AUDIT.md` | FA 表示・契約・CPU の出所 |
| ★ | `docs/FA_SALARY_MODEL_ALIGNMENT_POLICY.md` | オフ手動 vs インシーズンの揃え方 |
| | `docs/GUI_FULL_FA_MARKET_ENTRY_POLICY.md` | オフ手動1人・本格FAとの関係 |
| | `docs/GUI_INSEASON_FA_ENTRY_POLICY.md` | インシーズン1人FA |
| | `docs/GUI_FA_CONTRACT_ENTRY_POLICY.md` | 再契約・契約導線全体 |
| | `docs/GUI_ONE_FOR_ONE_TRADE_ENTRY_POLICY.md` | 1対1（※本文の一部は multi 実装前の名残がありうる） |
| | `docs/GUI_MULTI_TRADE_ENTRY_POLICY.md` | multi GUI（実装済みの正） |
| | `docs/ECONOMY_DESIGN_NOTES.md` | 経営本実装の論点 |
| | `docs/ECONOMY_MONEY_FLOW_AUDIT.md` | money 更新経路の地図 |
| | `docs/ECONOMY_NON_LEDGER_MONEY_POLICY.md` | 正本外 money の分類 |
| | `docs/AI_WORKFLOW_RULES.md` | 実装手順の正本 |
| | `docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` | 短い三者同期ブリッジ |

---

## 9. 重要コード一覧（責務）

| ファイル | 責務 |
|----------|------|
| `basketball_sim/main.py` | CLI メニュー、スモーク、Steam、**トレード用共用ヘルパ**、GUI モードで `Offseason(..., resign_ui_prompt=..., pre_conduct_free_agency_ui_prompt=...)` 注入 |
| `basketball_sim/systems/main_menu_view.py` | tkinter 主画面、人事ウィンドウ（トレード・FA・解除）、インシーズンFAウィザード |
| `basketball_sim/models/offseason.py` | オフフェーズ全体、**再契約**、**本格FA直前 UI フック** `_maybe_run_pre_conduct_free_agency_ui` |
| `basketball_sim/systems/offseason_full_fa_tk.py` | オフ手動1人FAの UI、`offseason_manual_fa_offer_and_years` 利用 |
| `basketball_sim/systems/offseason_resign_tk.py` | オフ再契約 messagebox |
| `basketball_sim/systems/free_agent_market.py` | FA 市場、`sign_free_agent`、`precheck_user_fa_sign`、`offseason_manual_fa_offer_and_years`、`get_team_fa_signing_limit` |
| `basketball_sim/systems/free_agency.py` | `conduct_free_agency`、`_calculate_offer`、`_determine_contract_years` |
| `basketball_sim/systems/trade_logic.py` | トレード評価・実行（1対1 / multi） |

---

## 10. 直近コミット群の意味（理解用）

- **GUI 人事**: トレード（1対1→multi 完成）・FA送り・インシーズン1人FA。  
- **GUI オフ**: 再契約・本格FA直前の手動1人。  
- **FA 年俸**: オフ手動を `_calculate_offer` 系へ → **payroll_budget タイミング**で 0 オファーになる **回帰をフォールバックで修正**（`conduct_free_agency` 非変更）。  
- **docs**: 上記と整合する設計・監査・現状・計画の更新。

---

## 11. 新Chat向け初動テンプレ

1. 本書 **§0** と **§6–§7** を読む。  
2. `CURRENT_STATE_ANALYSIS_MASTER.md` の **§5.7** で人事の事実を確認。  
3. ユーザーからの依頼が **GUI** なら `GUI_MAIN_FLOW_AUDIT.md` を開く。  
4. 依頼が **FA 金額**なら `FA_SALARY_ESTIMATE_AUDIT.md` の **§2.1**（オフ手動）と **§2.2**（インシーズン）を混同しない。  
5. 実装する前に **`IMPLEMENTATION_PLAN_MASTER.md` §12** と矛盾しないか見る。  
6. 変更後は **`python -m basketball_sim --smoke`** と関連 pytest を意識する。

---

## 12. 次の一手（1つだけ）

**`IMPLEMENTATION_PLAN_MASTER.md` §12 のタスク（Steam 関連正本 docs の同期確定）を、現状の doc 記述と突き合わせて完了または更新し、次の「1件」を文書上で明確化する。**（コード変更は不要な場合がある。）

---

## 付記: 本書の限界

- **全ボタン・全分岐の動的検証済み**とは言わない（未確認は各所に残す）。  
- **Godot 本リポジトリに含まれず**（現状分析 §5.13）。  
- **ユーザー環境固有の Steam 成否**は環境依存。

---

**改訂履歴**

- 2026-04-06: 初版作成（新Chat完全同期用・必須 docs およびコード grep に基づく）。
