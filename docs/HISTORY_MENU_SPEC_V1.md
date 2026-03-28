# 歴史メニュー仕様 第1稿（たたき台）

**関連（現状の正本に近い場所）**

| 領域 | 主な参照先 |
|------|------------|
| チームの永続履歴 | `basketball_sim/models/team.py`（`history_seasons` / `history_milestones` / `history_awards` / `history_transactions` / `club_legends` / `all_time_player_archive` / `club_history` / `finance_history` / `owner_mission_history`） |
| シーズン終了時の記録 | `basketball_sim/models/season.py`（`_record_division_season_history`、`_record_competition_team_result` → `add_history_milestone`） |
| オフシーズン・国際・昇降格のマイルストーン | `basketball_sim/models/offseason.py`（`club_history` テキスト列・`history_milestones`） |
| トレード／ドラフト／FA | `basketball_sim/systems/trade.py` / `draft.py` / `fa_logic.py` → `add_history_transaction` |
| 既存 GUI | `basketball_sim/systems/main_menu_view.py`（`open_history_window`・`_build_history_report_lines`） |
| CLI | `basketball_sim/main.py`（`print_user_team_history`）・`Team.print_history` / `get_club_history_report_text` |

**位置づけ**: 確定仕様ではない。**読み取り専用**の表示拡張を前提とし、履歴の**追記・集計の正本は Team / Season / 各システム側**に残す。

---

## 0. 全体所見・保全上の前提

### 0.1 全体所見（Cursor 所見）

- 提案の **5分類（年表・歩み・レジェンド・ドラマ・経営文化）** はプレイヤー体験として自然だが、**コード上はすでに `Team` 为中心に多くの履歴コンテナとレポート用メソッドが存在**する。歴史メニューは **新しい「史実」を発明するのではなく、既存 API の投影とタブ分割**に寄せるのが最も壊れにくい。
- 現状の歴史ウィンドウは **単一 `Text` に長文レポート**を詰め込んでおり、情報メニューで行ったような **「`history_display.py`（Tk 非依存）＋ Notebook」**へ段階移行すると、仕様の5分類と整合しやすい。
- **「ドラマ」「創設期／黄金期」などの物語ラベル**は、現状 **専用の永続ログはほぼ無く**、`history_milestones`・`history_seasons`・`_build_recent_trend_line` 等からの **その場要約／ルールベースタグ**が現実的。保存型にするとスキーマ負債と本番ロジックとの二重定義リスクが上がる。

### 0.2 現状構造に対して危険そうな点

1. **`history_seasons` の記録経路が複数あった問題（対策済み）**  
   - `Season._record_division_season_history` が **順位・D 所属付き**の行を追加する。  
   - `Team.record_season_history`（`reset_season_stats` から）は、**直前行に `top_players` が無いときは追記せず `top_players` のみ最終行へマージ**する（二重行化を抑止）。  
   - **旧セーブ**に既に二重行が残っている場合は、年表表示の **`dedupe_timeline_rows`** で **同一シーズンは情報の多い行を優先**する。表彰行にシーズンが無い古いデータは **UI 注記**で許容。

2. **`history_milestones` のスキーマゆれ**  
   - コメントどおり `title` / `detail` / `type` / `milestone_type` / `note` が混在。`get_club_history_summary` はキーワード判定でタイトル・昇降格を数えており、**表示専用の新ロジックを増やすと二重カウントや取りこぼし**が起きやすい。**集計は既存メソッドに寄せ、GUI は行の表示に徹する**のが安全。

3. **`get_club_history_legend_rows` と `club_legends` ペイロード**  
   - 格納は `player_name` 等だが、表示ヘルパは `name` もフォールバック。**列定義は既存 dict キーを正**とし、勝手にキー名を変えない。

4. **「クラブ年表」のプレーオフ・カップ・国際**  
   - リーグ最終順位は `history_seasons`（division 記録）に載りやすい。  
   - **プレーオフ結果・カップ・国際**は多くが **`history_milestones` と `add_history_milestone` 系**に依存。年表の1行に全部載せると **JOIN ルール**が要る。欠損は正常系。

5. **経営・文化の時系列**  
   - `finance_history` はスナップショット列だが、**全シーズン分が揃っている保証はない**（旧セーブ互換）。観客・人気は `Team` / `Season` のどこに年次ログがあるか **項目ごとに要確認**。無いものは **「現在値のみ」または非表示**。

6. **ドラマの「名勝負・ブザービーター」**  
   - 永続の試合ログがナラティブ用に整備されていなければ **未実装が正解**。既存の `game_results` 等からの抽出は **負荷・欠損・定義揺れ**が大きい。

### 0.3 より安全にするための前提（仕様に明記）

- **ユーザーによる履歴の手動編集は行わない**（表示のみ）。
- **集計ロジックの複製を避ける**：年表行は `get_club_history_season_rows`、マイルストーンは `get_club_history_milestone_rows`、サマリは `get_club_history_summary`、通算ランキングは `get_all_time_*` / `get_single_season_*` を優先。**新規は `systems/history_display.py` のような純関数で「読み取り・整形のみ」**。
- **欠損は正常系**：空リスト、`rank` なし行、マイルストーン未設定は **「—」「データなし」**。
- **旧セーブ**：属性欠落は `_ensure_history_fields` 系の精神に合わせ、**getattr + 空リスト**で落ちないこと。
- **物語・ドラマ**は **その場生成＝本番シミュ結果と独立した「読み物」**とラベルし、本番ロジックと同一視しない。

---

## 1. 歴史メニュー仕様 第1稿（たたき台）

### 1.1 大分類（ユーザー案との対応と名称）

ユーザー提示の **5分類を維持**しつつ、**実装・保守上の対応関係**を明示する。タブ順は **年表を先**（入口）にし、物語系は **マイルストーンと内容が被るため「エピソード」として束ねる**と安全。

| ID | 大分類（UI 名案） | 役割 | 現状データ・API の主な対応 |
|----|-------------------|------|-----------------------------|
| H1 | **クラブ年表** | シーズン単位の時系列の中心 | `history_seasons` → `get_club_history_season_rows`；行詳細にマイルストーンを **同シーズンでフィルタ**した抜粋を足せる（任意） |
| H2 | **チームの歩み** | 数年スパンの流れ・要約 | `get_club_history_summary`、`_build_recent_trend_line`、`get_club_history_report_text` 内の「クラブ格」系（**既存文面を分割表示**） |
| H3 | **レジェンド** | 象徴選手・記録の蓄積感 | `club_legends` → `get_club_history_legend_rows`；通算系 → `get_all_time_scorers` / `get_all_time_games` 等；単年記録 → `get_single_season_points_records` 等 |
| H4 | **ドラマ（エピソード）** | 数字以外の体験 | **第1段**: `history_milestones` を **優先度キーワード付きで一覧**（既存 `_build_milestone_headlines` と表裏一体）。**第2段**: ルールベースで「初優勝」「昇格」等の **ラベル付けしたサブリスト**（永続保存はしない） |
| H5 | **経営・文化** | 戦績以外の積み上げ | `finance_history`（`get_finance_report_detail_text` の元）；`owner_mission_history`；スポンサー・PR は **既存 `format_*_history_lines` があるなら読み出しのみ**；施設は **現レベル＋履歴が無ければ現在値のみ** |

**統合・分割の提案（非破壊）**

- **「ドラマ」を独立タブにしない**選択肢: H1 の年表行を選んだときに **右ペインでマイルストーン抜粋**（日程ウィンドウの二段パターンに近い）。**ただし**ユーザーが物語の居場所を明確にしたい場合は **H4 タブを残し、中身はマイルストーンの「物語ビュー」**に限定し、H1 では数値年表に集中する **役割分離**が衝突が少ない。
- **「チームの歩み」と「サマリ」**: 既存レポート先頭の要約と被る。**H2 は既存テキストを分割表示するだけ**にすると実装リスク最小。

### 1.2 各分類の中項目・入力形式

#### H1 クラブ年表

| 中項目 | 入力形式 | データ正本・備考 |
|--------|----------|------------------|
| シーズンラベル | 表示 | `Season N` 形式は `_format_history_season_label` |
| 所属リーグ（D1–D3） | 表示 | `league_level` |
| 最終順位 | 表示 | `rank`（行によって欠損あり得る → 「—」） |
| 勝敗・勝率 | 表示 | `wins` / `losses` / `win_pct` |
| 得点・失点・得失差 | 表示 | `points_for` / `points_against` / `point_diff` |
| プレーオフ・カップ・国際（1行要約） | 表示 | **主に `history_milestones` の該当シーズン抽出**（キーワード・`season_index` 合致）。欠損可 |
| 主な受賞（クラブ／選手） | 表示 | `history_awards` をシーズンで紐付けできるなら表示。紐付け弱い場合は **別タブ集約**でも可 |
| 昇格／降格 | 表示 | マイルストーンまたはサマリのカウント参照 |
| 年度詳細 | 表示 | 行選択で **マイルストーン詳細・`top_players`（`record_season_history` 行に含まれる場合）** を下に表示 |

**操作**: 表示専用。Treeview + 詳細ペイン推奨。

#### H2 チームの歩み

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| 通算シーズン数・タイトル・昇降格カウント | 表示 | `get_club_history_summary` |
| クラブ格・一言アイデンティティ | 表示 | `_build_club_identity_line` |
| 最近の流れ（短文） | 表示 | `_build_recent_trend_line(get_club_history_season_rows(...))` |
| 創設期／黄金期などの「時代」ラベル | 表示 | **後段**（ルールベースで `season_index` 区間にラベルを付けるなら **history_display でのみ**、正本データは増やさない） |
| 監督・主力交代の節目 | 表示 | **後段**（`history_seasons[].top_players` からの差分要約は可能だが仕様要定義） |

**操作**: 表示専用。初期は **既存レポートの「要約ブロック」をカード化**するイメージ。

#### H3 レジェンド

| 中項目 | 入力形式 | データ正本 |
|--------|----------|------------|
| クラブ認定レジェンド一覧 | 表示 | `club_legends` / `get_club_history_legend_rows` |
| 通算得点・出場数・他スタッツ上位 | 表示 | `get_all_time_scorers` / `get_all_time_games` 等 |
| 単シーズン得点／アシスト等トップ | 表示 | `get_single_season_*_records` |
| 殿堂・永久欠番 | 表示 | **後段**（`is_hall_of_famer` 等はアーカイブに載るが UI ラベルは要整理） |

**操作**: 表示専用。カテゴリタブまたはコンボで切替。

#### H4 ドラマ（エピソード）

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| マイルストーン時系列 | 表示 | `get_club_history_milestone_rows`（国際／FINAL BOSS／国内は既存レポートと同じ分類ロジックを **history_display に切り出し**） |
| 「初優勝」「大型連勝」等のストーリータグ | 表示 | **第1段はキーワード＋単純ルール**。**保存しない** |
| 名勝負・ブザービーター | 表示 | **後回し**（試合粒度ログの正本が無い限り） |

**操作**: 表示専用。

#### H5 経営・文化

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| 資金・収支履歴 | 表示 | `finance_history`、既存ファイナンスレポート整形を参照 |
| オーナーミッション達成履歴 | 表示 | `owner_mission_history` |
| スポンサー・PR・物販の履歴 | 表示 | 既存 `format_sponsor_history_lines` 等があれば **読み出しのみ** |
| 施設レベル | 表示 | **現状値**＋履歴が将来増えたら年表連動 |
| 観客・人気の推移 | 表示 | **データがある範囲のみ**。無ければ後段 |

**操作**: 表示専用。初期は **項目を絞る**（資金＋オーナーミッションのみ等）。

---

### 1.3 初期実装での役割（まとめ）

- **歴史メニュー全体**: 既存 `Team` データの **読み取り専用ダッシュボード**に近づける。CLI／長文レポートと **矛盾しない**ことを優先。
- **H1 年表**: 「入口」として **最優先で価値が高い**。
- **H2 歩み**: 既存要約の **配置換え**で十分なら開発コスト最小。
- **H3 レジェンド**: API が既に豊富で **表示だけ先**が容易。
- **H4 ドラマ**: **マイルストーン一覧＝ドラマの芯**。別生成エンジンは持たない。
- **H5 経営文化**: **データがある列だけ**出し、無いものは「今後蓄積」注記。

---

### 1.4 どこまでを初期実装対象にするか

| 区分 | 内容 |
|------|------|
| **初期（第1段・最優先）** | **H1 年表**（Treeview + 欠損耐性 + 重複行があれば表示ルールを文書化）。**H3 レジェンド**のうち `club_legends` + 1〜2 種の `get_all_time_*`。既存 `_build_history_report_lines` は **残しつつ**、新タブにデータを流す（情報メニューと同様の増築）。 |
| **初期（第1段・短工数）** | **H2** をサマリ＋`_build_recent_trend_line` のみ。**H4** をマイルストーン一覧（分類は既存3ブロックと同等）。 |
| **表示だけ先（第2段）** | H1 行選択時の詳細ペイン。H3 の単年記録・カテゴリ増。H5 のスポンサー等の history lines 接続。 |
| **後回し** | 名勝負ログ、ブザービーター、永続ドラマDB、時代ラベル（黄金期等）の本格自動分類、観客推移（データ正本未定時）、手動編集・リライト機能。 |

---

### 1.5 表示だけ先 / 既存参照で足りる / 後回し（一覧）

| 項目 | 区分 |
|------|------|
| 年表（シーズン行） | 既存参照 + **重複・欠損の表示ルール**だけ要整理 |
| サマリ数値・昇降格カウント | 既存 `get_club_history_summary` |
| マイルストーン一覧 | 既存 `get_club_history_milestone_rows` + 分類 |
| クラブ表彰行 | 既存 `get_club_history_award_rows` |
| レジェンド・通算ランキング | 既存 `get_club_history_legend_rows` / `get_all_time_*` |
| 最近の流れテキスト | 既存 `_build_recent_trend_line` |
| 経営（財務・オーナー） | 既存 `finance_history` / `owner_mission_history`（表示整形は既存ヘルパ優先） |
| 物語タグ付きドラマ | **表示だけ先**（その場ルール） |
| 名勝負・詳細ナラティブ本文 | **後回し** |

---

### 1.6 初期反映イメージ（表示系）

- 新規 **`basketball_sim/systems/history_display.py`（仮）**  
  - `build_timeline_rows(team)` → `get_club_history_season_rows` の行を正規化（重複 `season_index` 対策をここに閉じる案）  
  - `build_milestone_sections(team)` → 既存 main_menu の国際／BOSS／国内フィルタを移植  
  - `build_legend_tabs_data(team)` → レジェンド + 指定 `get_all_time_*` の dict 列  
  - `build_finance_culture_snippet(team)` → 欠損時は短い説明文  
  **Tk 非依存**。
- **`main_menu_view`**  
  - `open_history_window` を **Notebook** 化（情報メニューと同型）。  
  - `_build_history_report_lines` は **「全統合レポート」タブ**として残すか、廃止は **後段**（互換・好み）。
- **単体テスト**  
  - ダミー `Team` に `history_seasons` / `history_milestones` を載せ、`history_display` の出力行数・キーを検証。

---

### 1.7 実装優先順位（保全優先）

1. **`history_display.py` + テスト**（モック Team）  
2. **H1 年表**タブ（Treeview、詳細は後でも可）  
3. **H3 レジェンド**タブ（レジェンド + 通算1種）  
4. **H2 歩み**（サマリ + トレンド1行）  
5. **H4 エピソード**（マイルストーン分類表示）  
6. **H5 経営・文化**（財務 + オーナーのみから）  
7. **`history_seasons` 二重記録の有無を検証**し、必要なら **表示層または Team 側の単一化**（**小さな修正**に留める）

---

## 2. Cursor 視点：改善提案・このまま進めてよい点・確認論点・注意

### 2.1 構成は現状に対して自然か

**はい。** 5分類は **既存の `Team` API と1対1で対応**しやすい。特に H1/H3 は **追加集計ほぼ不要**。

### 2.2 どれを先に作ると最も安全か

1. `history_display` + **H1 年表**  
2. **H3 レジェンド**（API 豊富）  
3. H2 / H4（既存テキスト・マイルストーンの切り出し）

### 2.3 表示だけ先／詳細・演出は後回し

- **先**: Treeview 行、マイルストーン一覧、通算ランキング、サマリ数値。  
- **後**: 詳細ペインのリッチ化、ドラマ専用生成、観客推移、時代ラベル。

### 2.4 初期から入れても壊れにくい表示項目

- `get_club_history_season_rows` の列（欠損は「—」）  
- `get_club_history_summary` の数値  
- `get_club_history_milestone_rows` + 既存3分類  
- `get_club_history_legend_rows`  
- `get_all_time_scorers` / `get_all_time_games`（引数は既存デフォルトに合わせる）

### 2.5 仕様として曖昧・危険・衝突しそうな箇所

- **`history_seasons` の1シーズン1行か複数行か**（上記 0.2-1）  
- 年表1行に **PO・カップをどこまで埋めるか**（マイルストーンとの **二重表示**）  
- 「ドラマ」を **本番の勝敗ロジックと同一視**する誤解  
- レジェンドの **通算スタッツが「当クラブのみ」かキャリア全体か**（`career_*` の意味を UI で明示）

### 2.6 保全しやすい履歴参照の切り方

- **参照は `Team` の public メソッド経由**を原則とし、`history_seasons` を GUI から直接いじらない。  
- 新規整形は **`history_display` の純関数**に閉じ、Season 側の記録処理は **別タスクで慎重に**。

### 2.7 責務分離（GUI・履歴取得・年表・レジェンド・ドラマ）

| 層 | 責務 |
|----|------|
| **Team / Season / offseason / trade…** | 追記・正本 |
| **history_display.py** | 読み取り・正規化・結合・欠損メッセージ |
| **main_menu_view** | Notebook・Treeview・バインド |
| **ドラマ「タグ」** | `history_display` 内の純関数（入力は milestone 行の list のみ） |

### 2.8 ドラマ・文化：保存型 vs その場集計

- **推奨: その場集計／要約（非保存）**が安全。保存型はセーブ互換と検証コストが増える。  
- **文化・経営**で既に列として残っている `finance_history` 等は **保存済みの読み出し**でよい（新規スキーマを増やさない）。

### 2.9 より安全な画面分けの代替案

- **タブ4つに圧縮**: **年表 | 選手・記録（レジェンド+通算） | エピソード（マイルストーン） | 経営** にし、「チームの歩み」を年表上部のサマリカードに含める。  
- 5分類を維持する場合でも **H2 は短く**し、情報量は H1/H4 に寄せると重複が減る。

### 2.10 このまま進めてよい点

- 5分類のコンセプト。  
- 表示専用・段階実装。  
- `history_display` による分離。  
- 情報メニューで実証済みの **Notebook 増築パターン**の再利用。

### 2.11 先に確認した方がよい論点

- **`history_seasons` の実際の並び・重複**（1 シーズン playthrough での行数）。  
- 年表に載せる **「シーズン」の定義**（レギュラー終了時点 vs オフシーズン後）。  
- `history_awards` の **シーズンキー**が表示に十分か。

### 2.12 破壊的変更を避ける実装上の注意

- 既存 `get_club_history_report_text` / CLI を **いきなり削除しない**。  
- `Team` のフィールド名をリネームしない（旧セーブ対策）。  
- マイルストーンのキーワード判定を **GUI にコピペしない**（`history_display` に1箇所集約）。  
- 二重記録がある場合、**いきなり `record_season_history` を消さず**、まず表示で吸収し、次段で記録一本化を検討。

---

## 3. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-28 | 第1稿: 5分類と既存 Team/Season API の対応、`history_seasons` 複数経路リスク、責務分離、優先順位、ドラマ・経営の扱い。 |
| 2026-03-28 | **安全実装（第1段）**: `systems/history_display.py`、歴史ウィンドウ Notebook 化（年表+詳細／歩み／レジェンド／エピソード／経営・文化／全文）、`tests/test_history_display.py`。 |
| 2026-03-28 | **締め**: `record_season_history` の top_players マージ、レジェンドにシーズン記録表示、経営タブにスポンサー／PR／物販要約、表彰・通算の注記、閉じるボタン、スモークチェックリスト、`tests/test_team_history_record.py`。 |

---

## 4. 手動スモークチェックリスト（歴史ウィンドウ）

1. **開閉**: 歴史を開く／閉じる／再オープンで落ちない。下部「閉じる」で閉じられる。  
2. **年表**: 行が表示され、選択で詳細ペインが更新される。未選択時の注記が読める。  
3. **歩み・エピソード・経営・全文**: チーム未接続でも骨格表示。接続時は文字が極端に欠けない。  
4. **レジェンド**: コンボを切替えて列見出しと行が変わる（通算／シーズン記録）。  
5. **経営・文化**: 財務に続きスポンサー／PR／物販の見出しが出る（データゼロは「履歴なし」可）。  
6. **全文レポート**: 以前と同様の長文が得られる（CLI／`get_club_history_report_text` との大矛盾がないこと）。  
7. **リフレッシュ**: メイン画面からシーズン進行後、開いたままの歴史を更新できる（クラッシュなし）。
