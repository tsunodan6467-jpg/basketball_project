# 戦術メニュー開発 — 完全引き継ぎ書（設計・実装・履歴・次タスク）

**位置づけ**: 国内バスケ GM シミュにおける **戦術メニュー（GUI）** の、**2026年4月時点**の実装状況・データ正本・改修履歴・制約・次の安全な手を **新チャット／新担当者が迷わず再開できる** ようまとめた文書である。  
**正本の優先順位**: ① リポジトリ上の **現行コード** ② 本書の **日付入り事実** ③ 他 `docs`（内容が古い箇所は本書の「ドキュメント鮮度」節を参照）。  
**最初に実行すること（再現性）**:

```text
cd <repo>
git status
git log -5 --oneline
```

未コミット差分や直近コミットは、**作業再開時点の git** を正とする（本書のコミット列は「主要マイルストーン」であり、**最新が常にここに追記されているとは限らない**）。

---

## 目次

1. [プロダクト上の位置づけ](#1-プロダクト上の位置づけ)  
2. [クイック再開チェックリスト](#2-クイック再開チェックリスト)  
3. [リポジトリで「理解が深まる」ドキュメント案内](#3-リポジトリで理解が深まるドキュメント案内)  
4. [ソースコード上の正本（ファイル・エントリポイント）](#4-ソースコード上の正本ファイルエントリポイント)  
5. [データモデル：Team と team_tactics の分離（最重要）](#5-データモデルteam-と-team_tactics-の分離最重要)  
6. [戦術メニュー UI 構造（現行）](#6-戦術メニュー-ui-構造現行)  
7. [起用方針（usage_policy）7キーと GUI 方針](#7-起用方針usage_policy7キーと-gui-方針)  
8. [補助導線・子窓一覧（現状）](#8-補助導線子窓一覧現状)  
9. [試合ロジックとの接続（要約）](#9-試合ロジックとの接続要約)  
10. [主要 Git 履歴（戦術メニュー整理の積み重ね）](#10-主要-git-履歴戦術メニュー整理の積み重ね)  
11. [セッション上の作業内容（会話・実装の時系列要約）](#11-セッション上の作業内容会話実装の時系列要約)  
12. [意図的に触っていない／触ってはいけない範囲](#12-意図的に触っていない触ってはいけない範囲)  
13. [推奨テスト・スモーク](#13-推奨テストスモーク)  
14. [既知のギャップと今後候補（ロードマップ）](#14-既知のギャップと今後候補ロードマップ)  
15. [用語・関数名クイック索引](#15-用語関数名クイック索引)  
16. [他 docs との矛盾が出たときの扱い](#16-他-docs-との矛盾が出たときの扱い)  
17. [手動反映とリポジトリ運用上の注意](#17-手動反映とリポジトリ運用上の注意)  

---

## 1. プロダクト上の位置づけ

- **メイン操作は GUI**（`basketball_sim` の tkinter ダッシュ）が主目的。CLI は smoke・開発補助。  
- **戦術**は左メニュー「戦術」→ **`open_strategy_window`** が**戦術メニュー親（ハブ）**。  
- 同じ用語でも **保存先が複数**（例：`Team` の起用方針と `team_tactics["usage_policy"]` の7項目）は、**意図的に二層**。**キー名をいじらず**説明と導線で分ける方針。

---

## 2. クイック再開チェックリスト

- [ ] `python -m basketball_sim --smoke` が通る。  
- [ ] `git status` で意図しない差分がない（または、意図をメモに残す）。  
- [ ] 戦術ハブで **「プレイスタイル」「ローテーション」** の2導線から統合窓が開く。  
- [ ] プレイスタイル統合で **0〜7**、ローテーション統合で **0〜2** が直接編集できる。  
- [ ] 仕様上触らない: **Team 正本**の先発/6th/ベンチをローテプリセットが勝手に変えない。  
- [ ] 本書 §3 の「深く読む順」を把握した。

---

## 3. リポジトリで理解が深まるドキュメント案内

| おすすめ度 | パス | 何が分かるか |
|------------|------|--------------|
| 必須 | `docs/TACTICS_PRESET_CUSTOM_STATE_POLICY.md` | プリセットが**触る/触らない**対象、カスタム表示、`preset_meta` |
| 必須 | `docs/TACTICS_MENU_MIGRATION_PLAN.md` | 旧7ボタン→2枠の**経緯**（注: 以降さらに「統合画面」が入ったため [§16](#16-他-docs-との矛盾が出たときの扱い) 参照） |
| 必須 | `docs/ROTATION_CONTENT_MIGRATION.md` | ローテ枠のブロックと保存先、プリセット3種、roles の一部反映 |
| 必須 | `docs/PLAYSTYLE_CONTENT_MIGRATION.md` | プレイスタイル枠と `PLAYSTYLE_PRESET_DEFS` |
| 高 | `docs/MATCH_STARTING_LINEUP_RULES.md` | **ベース先発**と **戦術先発**（`rotation.starters`）の**差し替え**模型 |
| 高 | `docs/GM_ROSTER_DISPLAY_RULES.md` | 人事「タグ:」＝**自動**、`main_role`＝**手動参考**（混同厳禁） |
| 高 | `docs/AUTO_ROLE_TAG_PARAMS.md` | 自動役割タグの正本 |
| 中 | `docs/GUI_MAIN_FLOW_AUDIT.md` | GUI 全体の流れの監査メモ |
| 中 | `docs/PRODUCT_ROADMAP_AND_VISION.md` | 製品方向性 |
| 中 | `docs/GM_MANAGEMENT_MENU_SPEC_V1.md` | GM 周辺（戦術は別だが用語揃い） |
| 参照 | `docs/CHATGPT_NEW_CHAT_HANDOFF_FOR_CURSOR_SYNC.md` | 汎用・同期系の手引（戦術専用ではない） |
| 実装正本 | `basketball_sim/systems/team_tactics.py` | 正規化、プリセット定数、`apply_*_preset` |
| 実装正本 | `basketball_sim/systems/main_menu_view.py` | 全戦術窓の UI |

**読む順（短時間）**: `TACTICS_PRESET_CUSTOM_STATE_POLICY` → `MATCH_STARTING_LINEUP_RULES` → `team_tactics.py`（`PLAYSTYLE_PRESET_DEFS` / `ROTATION_PRESET_DEFS` 周辺）→ `main_menu_view.py`（`open_strategy_window` から辿る）。

---

## 4. ソースコード上の正本（ファイル・エントリポイント）

| 役割 | 主ファイル |
|------|------------|
| 戦術ハブ・全 `Toplevel` 戦術 UI | `basketball_sim/systems/main_menu_view.py` |
| 戦術データ正規化・プリセット適用 | `basketball_sim/systems/team_tactics.py` |
| 試合中ローテーション（交代・目標分等） | `basketball_sim/systems/rotation.py`（**`systems` 下に同名無し。試合本丸は** `basketball_sim/models/match.py`） |
| ダッシュ用テキスト（先発/ベンチ編集系の apply/get） | `basketball_sim/systems/gm_dashboard_text.py` |
| Team 側 GM 3項目の適用ヘルパ | `basketball_sim/systems/gm_ui_constants.py`（`apply_team_gm_settings` 等。戦術専用ではないが**HC/基本起用**の保存に接続） |

**grep の勘違い防止**: 試合シミュのクラス `Match` は **`models/match.py`**。`systems/match.py` は**別物の可能性**（リポジトリ版を確認すること）。

---

## 5. データモデル：Team と team_tactics の分離（最重要）

### 5.1 粗い整理

| 概念 | 主な保持場所 | 説明（ユーザー向けイメージ） |
|------|----------------|------------------------------|
| **Team 起用**（`Team.usage_policy`） | `Team` | 粗い3択系（`balanced` / `win_now` / `development` 等）。**ローテ `Rotation` の大きなバイアス**にも使われる。 |
| **起用方針テンプレ 7 項目** | `team_tactics["usage_policy"]` | 優先度、評価基準、調子、年齢/ケガ/連戦、外国籍起用**微調整**等。**試合中の補正オーバーレイ**に**一部**接続。 |
| **ローテ詳細** | `team_tactics["rotation"]` | 戦術先発 `starters`、`target_minutes`、疲労/ファウル/終盤方針等。**Team 正本先発と別**（`docs/MATCH_STARTING_LINEUP_RULES.md`）。 |
| **Team 正本序列** | `Team` | `starting_lineup`、Sixth、ベンチ序列。**試合登録上の主たる起用**の正に近い。 |
| **プレイスタイル** | `team_tactics["team_strategy"]` / `playbook` 等 + `Team.strategy` | 攻守・セット。プリセット v1 では `coach_style` / **粗い** `Team.usage_policy` は**触れない**方針（`TACTICS_PRESET_CUSTOM_STATE_POLICY`）。 |
| **個別役割** | `team_tactics["roles"]` | 手動。人事の**自動タグ**の正本では**ない**（`GM_ROSTER_DISPLAY_RULES`）。 |

### 5.2 プリセット適用（ローテーション v1）で変わる／変わらない

- **変わる**: `Team.usage_policy`、 `team_tactics["usage_policy"]`、 `team_tactics["rotation"]`（定義上 `starters` は `{}` 等）。  
- **変わらない**: `Team` の**先発/6th/ベンチ**、`team_tactics["roles"]`（`apply_rotation_preset` の docstring および `TACTICS_PRESET_CUSTOM_STATE_POLICY` と整合）。  

→ 統合画面で **「プリセットを変えても先発が変わらない」** のは**仕様**。見た目で変化が小さいと感じる要因の一つ（**`target_minutes` が統合に直置きされていない**、Team 正本を触らない、等）。

---

## 6. 戦術メニュー UI 構造（現行）

### 6.1 ハブ `open_strategy_window`

- ナビ: **「プレイスタイル」「ローテーション」** の2ボタンのみ。  
- 下段: **参照専用**のチーム概要・スタメン表示・注記（**編集の正本は上の2ボタン**）。  
- 文言は「暫定ボタン」等の**旧表現を整理済み**（`2618e49` 前後。詳細は git）。  

### 6.2 プレイスタイル統合 `_open_tactics_playstyle_overview_window`

- **0〜7** を**同一 Toplevel 内**で直接編集（Canvas + スクロール）。  
- **補助**: `補助設定を開く（Team基本方針・HC）` → `_open_tactics_core_policy_window`（`Team.strategy` / `coach_style` / `Team.usage_policy`）。  
- 重複していた **「別窓で攻守の傾向」「別窓でセット傾向」** ボタンは**非表示化済み**（`2618e49`）。**関数** `_open_tactics_team_strategy_window` / `_open_tactics_playbook_window` は**削除しておらず**、将来のデバッグ用に**コード上残存**可。

### 6.3 ローテーション統合 `_open_tactics_rotation_overview_window`

- **0. 起用プリセット** / **1. チーム起用方針** / **2. 起用序列** を同一 Toplevel 内に配置。  
- **2. 起用序列**: `_build_team_lineup_editor_ui`（先発/6th/ベンチ。**折り畳み**）。`gm_dashboard_text` の `apply_*` / `get_*` を**そのまま**利用。  
- **補助**: ローテ詳細（`_open_tactics_rotation_window`）は**2ボタン**（同じ窓。文言のみ分割）。`target_minutes` / 戦術先発は**未統合のため導線必須**。  
- 重複 **「起用テンプレ別窓」「先発/6th/ベンチ別窓」** は**非表示化済み**（`2618e49`）。**`_open_tactics_usage_policy_window` / `_open_tactics_team_lineup_window` は未削除。**

#### ローテーション統合の利用フロー（2026-04 時点・一区切り）

1. **起用プリセット**を選び、必要なら **「プリセット適用」**する。  
2. **起用方針の反映サマリー**（読み取り）で、プリセットと `usage_policy` / `rotation` 補助の要約を確認する。  
3. **目標出場時間のおすすめ**（読み取り）を確認する。必要なら **「このおすすめを目標出場時間に反映」** で `team_tactics["rotation"]["target_minutes"]` だけ手動上書き（**確認ダイアログ必須**。**自動反映はしない**）。  
4. **おすすめ起用序列**（読み取り）を確認する。必要なら **「このおすすめを起用序列に反映」** で **Team 正本**（先発 / 6th / `bench_order`）だけ手動上書き（**確認ダイアログ必須**。**自動反映はしない**）。`target_minutes` はここでは変えない。  
5. **現在のベンチ順**（7番手〜）を**一覧**で確認する。  
6. 従来どおり **枠A/B＋「選択2人の順序を入れ替え」**でベンチ順を手動調整する。  
7. 先発・6thの詳細編集、**ローテ詳細**（`target_minutes`・戦術先発など）は既存導線どおり。  

`Team` 正本と `team_tactics`（`rotation` 等）の**分離**は従来どおり。**起用プリセット適用**だけで Team 正本が勝手に書き換わることはない（方針どおり）。

### 6.4 個別役割

- 統合ローテ画面から**手動導線は非表示**（`6042b29` 系の整理）。  
- `_open_tactics_roles_window` は**削除していない**が、**当時の調査では UI から到達不能**（grep で呼び出し箇所なし）。`team_tactics["roles"]` のデータ路は**温存**。

---

## 7. 起用方針（usage_policy）7キーと GUI 方針

`main_menu_view` の定数 `_USAGE_POLICY_EDITOR_KEYS` には7キー（`priority`, `evaluation_focus`, `form_weight`, `age_balance`, `injury_care`, `schedule_care`, `foreign_player_usage`）が列挙される。

**直近セッション方針（第1段・製品向けに簡素化）** — 実装は **`main_menu_view.py` のみ**、**`team_tactics.py` 非変更**で:

1. **評価基準**のコンボ候補から **「将来性重視」**（内部 `evaluation_focus: "potential"`）を**選べない**ようにする。  
2. 既存セーブ等で `potential` が入っていても、**表示は `overall` に寄せ、保存で `overall` へ**（**見えない potential を温存し続けない**）。`ALLOWED_*` から `potential` を**削らない**（要請どおり）。  
3. **外国籍起用補助**（`foreign_player_usage`）の**行を出さない**。**保存**は `usage_policy` 既存 dict に **非表示キーをマージ**し **`foreign_player_usage` を上書きで消さない**。

**次チャットでは**: 上記の**未コミット／コミット済**は **`git log` / `git diff` で必ず確認**（本書に特定ハッシュを固定しない）。

---

## 8. 補助導線・子窓一覧（現状）

| 導線（ボタン文言の系統） | 相当関数 | 備考 |
|--------------------------|----------|------|
| 補助設定（Team基本方針・HC） | `_open_tactics_core_policy_window` | 必須。試合他モジュールが `coach_style` 等を参照。 |
| ローテ詳細（交代・目標出場 等） | `_open_tactics_rotation_window` | 未統合。完全削除は**アクセス喪失**。 |
| 起用方針テンプレ専用 | `_open_tactics_usage_policy_window` | ハブから**重複導線は外した**が関数は**残存**（内部で同じ usage エディタ）。 |
| 先発/6th/ベンチ専用 | `_open_tactics_team_lineup_window` | 同上。 |
| プレイ/セット別窓 | `_open_tactics_team_strategy_window`, `_open_tactics_playbook_window` | ボタン非表示。関数**残存**。 |
| 個別役割 | `_open_tactics_roles_window` | 到達困難の可能性。 |

---

## 9. 試合ロジックとの接続（要約）

- **先発（実際にコートに並ぶ5人）**: ベースは `Match._get_starting_five_from_players`。**戦術** `get_normalized_rotation_starters_map` による**条件付き**差し替え（`MATCH_STARTING_LINEUP_RULES.md`）。`Team` の**正本**と `rotation.starters` は**二層**。  
- **HC `coach_style`**: `basketball_sim/models/match.py` 等で**参照**。**戦術メニューから完全非表示**は**非推奨**（過去の調査結論）。補助窓に**集約**している。  
- **交代候補スコア**: `rotation.py` 内で `get_evaluation_focus_substitute_overlay` / `get_foreign_player_usage_substitute_overlay` 等（`team_tactics.py`）。**7項目をUIから隠しても、内部キーと正規化は残る**限り、ロジックは**破綻しない**設計。

---

## 10. 主要 Git 履歴（戦術メニュー整理の積み重ね）

### 10.1 直近のローテーション UI 整理（`main_menu_view` 中心・**新しい順**）

| コミット | メッセージ要約 |
|----------|----------------|
| `66c3459` | ベンチ順を一覧で見やすく表示 |
| `db49056` | おすすめ起用序列の手動反映を追加 |
| `c0fa2e7` | おすすめ起用序列プレビューを追加 |
| `420621d` | おすすめ目標出場時間の手動反映を追加 |
| `e0fa6a5` | ローテーション読み取り表示の文字色を改善 |
| `dafd402` | 目標出場時間のおすすめ表示を追加 |
| `8abf02e` | 起用プリセットにコンディション重視型を追加 |
| `b09442a` | チーム起用方針の不要項目を整理 |

### 10.2 それ以前の主要整理（ハブ・統合土台・**新しい順**）

| コミット | メッセージ要約 |
|----------|----------------|
| `2618e49` | 戦術メニューの補助導線を整理（重複別窓非表示、文言整理） |
| `6042b29` | ローテーション画面で0〜2を直接編集できるように整理（Team 起用序列の共通ヘルパー、折り畳み 等） |
| `152cf56` | プレイスタイル画面で0〜7を直接編集できるように整理 |
| `1df2f65` | 戦術メニューを2ボタン構成に整理 |

**追補**: `git log --oneline basketball_sim/systems/main_menu_view.py`。

---

## 11. セッション上の作業内容（会話・実装の時系列要約）

以下は **Cursor 上の会話系タスク**から抽出した**高レベル履歴**（**コードは `git diff` を正**）。

1. **ローテーション統合（0〜2）**  
   - Team 正本（先発/6th/ベンチ）を `_build_team_lineup_editor_ui` に共通化。  
   - 折り畳み、Canvas の `scrollregion` 更新。  
   - 個別役割の**主導線は非表示**（3 を復活させていない）。  

2. **補助導線の整理**（`2618e49`）  
   - プレイスタイル: 別窓重複2つ削除、Team 方針ボタン名整理。  
   - ローテ: 起用テンプレ/先発別窓の重複削除。ローテ詳細**維持**。  
   - 戦術ハブ・GM 案内文の**旧用語**を更新。  

3. **調査**  
   - HC/二重起用/プリセット可視性/次のロードマップ。  

4. **起用方針 GUI 第1段（usage_policy 簡素化）**（`b09442a` 等で反映済み想定）  
   - 将来性・外国籍行の**非表示**と**保存マージ**（`main_menu_view` のみ）。次作業前に `git status` で確認。  

5. **ローテーション読み取り系・手動反映・ベンチ一覧**（`dafd402` 〜 `66c3459`）  
   - 目標出場・起用序列の**おすすめ表示**と**確認付き手動反映**、ベンチ順**一覧**など。  

---

## 12. 意図的に触っていない／触ってはいけない範囲

- **`team_tactics.py`**: `ALLOWED_*`、`ROTATION_PRESET_DEFS` 内 `evaluation_focus: "potential"` 等を**会話上は変更禁止**（GUI からの**緩和**を別タスク化）。  
- **`rotation.py` / `models/match.py` / `auto_role_tag.py` / `gm_dashboard_text.py`**: 会話上の**戦術UIタスク**では**原則変更なし**（不具合以外）。  
- **一括 `git add .`**: ユーザー方針で**禁止**されがち。明示パスのみ `git add` を使う。  

---

## 13. 推奨テスト・スモーク

```powershell
python -m basketball_sim --smoke
python -m pytest basketball_sim/tests/test_management_menu_snapshot.py -q --tb=short
python -m pytest basketball_sim/tests/test_team_tactics_normalize.py -q --tb=short
python -m pytest basketball_sim/tests -q --tb=short -k "not test_regular_season_balance_guard_multi_season"
```

---

## 14. 既知のギャップと今後候補（ロードマップ）

### 14.1 実装済（2026-04 本書更新時点）

| 内容 | 備考 |
|------|------|
| 起用プリセットに **コンディション重視型** | `8abf02e` |
| **目標出場時間のおすすめ**（読み取り） | `dafd402` ほか |
| **おすすめ目標出場時間の手動反映**（確認後・`target_minutes` のみ） | `420621d` |
| **おすすめ起用序列**プレビュー（読み取り） | `c0fa2e7` |
| **おすすめ起用序列の手動反映**（確認後・Team 正本のみ） | `db49056` |
| **ベンチ7〜12番手の一覧**＋従来 **A/B ＋入替**（`apply_bench_order_swap`） | `66c3459` |
| プリセット適用後の **起用/ローテ反映サマリー**（読み取り） | 0. 起用プリセット近傍 |
| 起用方針 **不要行の非表示**・保存マージ | `b09442a` ほか |

**自動で書き換わるのではないもの**: `target_minutes` のおすすめ値 → **確認ボタン**後のみ保存。起用序列のおすすめ → **確認ボタン**後のみ Team 正本更新。プリセット適用は **`team_tactics` / `Team.usage_policy` 側**が主で、**Team 先発/6th/ベンチ正本を勝手に上書きしない**方針は維持。

### 14.2 今後候補

| 段階 | 内容 | 注意 |
|------|------|------|
| 1 | 起用方針の**更なる簡素化**・文言 | 正規化・`ALLOWED` と**整合** |
| 2 | 起用の**階層説明**（Team 正本 vs `rotation`）を画面に短く | 誤解防止 |
| 3 | 「別窓」表記の**さらに**整理 | ローテ詳細**は残す** |
| 4 | ベンチ順の **上へ/下へ** 等（**未実装**。現状は A/B 入替のみ） | ロジック既存の範囲で |

`ROTATION_CONTENT_MIGRATION.md` §6 の**今後候補**と**重複**しうる点あり（本書を**戦術のメイン巻子**にできる）。

---

## 15. 用語・関数名クイック索引

- `open_strategy_window` — 戦術ハブ。  
- `_open_tactics_playstyle_overview_window` — プレイスタイル統合。  
- `_open_tactics_rotation_overview_window` — ローテーション統合。  
- `_build_team_lineup_editor_ui` — Team 正本エディタ（`flat` / `collapsed`）。  
- `_build_playstyle_preset_editor_ui` / `_build_rotation_preset_editor_ui` — 各プリセット行。  
- `apply_playstyle_preset_with_preset_meta` / `apply_rotation_preset_with_preset_meta` — `team_tactics.py`。  
- `_usage_policy_editor_save` / `_usage_policy_editor_collect` — 起用7項目の保存。  
- `get_normalized_rotation_starters_map` — 戦術先発スロット。  
- `get_rotation_target_minutes_by_player_id` — 目標分。  

---

## 16. 他 `docs` との矛盾が出たときの扱い

- `TACTICS_PRESET_CUSTOM_STATE_POLICY.md` の **「ナビ7本・複数 `LabelFrame`」** 等の**古い**戦術メニュー記述は、**152cf56 / 6042b29 / 2618e49** 以降の**統合画面**・**2ボタン+補助整理**の実装に**必ずしも追従していない**。  
- 矛盾時: **(1) `main_menu_view.py` (2) `git` の該当コミット (3) 本書**の順。  
- `ROTATION_CONTENT_MIGRATION` の**窓一覧**は**役割導線の有無**が現状と**ずれる**可能性（統合非表示**済み**）。

---

## 17. 手動反映とリポジトリ運用上の注意

- **`target_minutes`**: おすすめは**常に読み取り**。`team_tactics` への上書きは、**「このおすすめを目標出場時間に反映」**の**確認後のみ**（自動保存なし）。  
- **起用序列（Team 正本）**: おすすめは**読み取り**。`starting_lineup` / `sixth_man_id` / `bench_order` への反映は、**「このおすすめを起用序列に反映」**の**確認後のみ**（自動保存なし）。`target_minutes` は同操作では**変えない**。  
- **Team 正本**と **`team_tactics`（`rotation`・`usage_policy` 等）**の**分離方針**は従来どおり。  
- **`reports/*.txt`**: 多くは **pytest / smoke のリダイレクト作業ログ**。**リポジトリのコミット必須ではない**。**一括 `git add .` は使わない**方針のとき、作業ログを誤って載せないよう、**明示パス**で `git add` する。

---

## 付記：このファイルの更新ルール

- 戦術メニューに**大きな仕様追加**が入ったら、**コミットハッシュ**と**日付**を追記する。  
- セーブ形式や `team_tactics` スキーマを**変えた**場合は、**専用の設計文書**または**CHANGELOG**をリンクする。  
- 本書は**戦術専用**。FA・給与等は `docs/FA_*.md` 群を正とし、**ここに複製しない**（**索引のみ**可）。

---

**文書端**: 以降の作業者へ — 迷ったら **`git show <hash>:basketball_sim/systems/main_menu_view.py` の差分**と、本書 §3 の **3 点セット**（プリセット方針・先発ルール・ローテ migration）に戻る。
