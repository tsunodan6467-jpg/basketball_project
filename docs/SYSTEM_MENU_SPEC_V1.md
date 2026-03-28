# システムメニュー仕様 第1稿（たたき台）

**関連（現状の正本）**

| 領域 | 主な参照先 |
|------|------------|
| セーブ・ロード | `basketball_sim/persistence/save_load.py`（`save_world` / `load_world` / `normalize_payload` / `migrate_blob_to_current` / `validate_payload` / `find_user_team`） |
| ペイロード組み立て・再束縛 | `basketball_sim/persistence/save_payload.py`（`build_save_payload` / `rebind_resume_season_to_world`） |
| セーブパス | `default_save_dir` / `default_save_path(slot)` → `~/.basketball_sim/saves/{slot}.sav`（`utils/paths.py`） |
| ペイロード形・バージョン | `config/game_constants.py`（`PAYLOAD_SCHEMA_VERSION` / `GAME_ID`） |
| ユーザー設定（セーブとは別） | `basketball_sim/utils/user_settings.py`（JSON・`settings_path()`・`_normalize`・`save_user_settings` 原子的保存） |
| CLI セーブ | `main.py`：`build_save_payload` 経由（年度メニュー `6`・シーズンメニュー `10`） |
| 主画面 | `main_menu_view.py`：`MENU_ITEMS` に「システム」あり。**`on_system_menu` 注入時**は `main._open_main_menu_system_window` が Toplevel を開く（未注入時は従来どおり未実装メッセージ可） |
| UI モード | `main.run_main_menu_ui_mode`：`game_state` 辞書＋`on_system_menu`＋`on_main_window_close`（未保存の弱い確認）。**タイトル「続きから」**でセーブ読込後は `choose_resume_launch_mode` により **CLI 再開 / 主画面 UI 再開**を選択可（UI 未ロード時は従来どおり CLI にフォールバック）。**オフ完了後**はダイアログで **主画面のまま次シーズン**（`_apply_next_season_from_annual_gate`＝CLI 年度「次のシーズンへ進む」と同義）か **閉じて CLI 年度メニュー**を選択可。`ui_flow["offseason_completed"]` の間は主ボタンで **再オフに入らず** 同じ次年度確認（`_gui_prompt_next_season_after_offseason_gate`）へ。 |
| Steam・ライセンス | `integrations/steamworks_bridge.py` / `user_settings.steam_require_license` |

**位置づけ**: 確定仕様ではない。**セーブ互換と設定ファイルの保全**を最優先し、GUI は **既存 API の薄い皮**に留める。

---

## 0. 全体所見・保全上の前提

### 0.1 全体所見（Cursor 所見）

- 提示の **6分類（セーブ／ロード／コンフィグ／プレイガイド／タイトルへ戻る／終了）** は一般的で自然。**システム（セーブ／ロード）の第1段**は UI モードで **`on_system_menu` → Toplevel** として接続済み（設定・ガイド・タイトル戻り・終了ボタンは未または別経路）。**`season_count`** は `game_state["season_count"]` で保持し、ロードで上書き可能。
- **セーブ**は **`save_world` + blob バージョン + `normalize_payload`** を維持し、ペイロード組み立ては **`build_save_payload` に集約**。途中ラウンドは **`resume_season`（`Season` インスタンスを pickle 同一グラフで保存）** と **`at_annual_menu=False`** で表現。年度進行メニュー相当（オフ済み後の UI セーブ等）は **`at_annual_menu=True` で `resume_season` を載せない**（古い Season の不整合回避）。
- **設定**は **`settings.json`（`user_settings`）が正本**。音量・演出速度など **未実装キー**をいきなり仕様に大量追加すると、`_normalize` と既存ドキュメントの整合が必要になる。**第1段は既存キーの可視化・編集・保存**に限定するのが安全。
- **ロード**は `load_world` 後に **`Season` / `MainMenuView` の再構築**が必要で、**1 関数で完結しない**。保全的には **`main.py`（または専用オーケストレータ）に `on_load_world(payload)` を置き**、GUI は「ファイル選択＋検証＋コールバック」に徹するのがよい。
- **タイトルへ戻る**は、現状の UI モードは「ウィンドウ閉鎖 → CLI 年度メニュー」であり、**真のタイトル（`simulate()` 先頭）へ戻す**にはプロセス／メインループの再設計に近い。**第1段は「未実装」「CLI 案内」または `root.quit()` + 外側ループ任せ**など、**既存フローと衝突しない範囲**で定義する。

### 0.2 現状構造に対して危険そうな点

1. **セーブ許可タイミング（方針更新）**  
   - **プロダクト方針**: シーズン途中もセーブ可。実装は **`resume_season` + `rebind_resume_season_to_world`** で整合を取る。  
   - **オフシーズン完了後の UI セーブ**は **`at_annual_menu=True`・`resume_season=None`** に固定（Season オブジェクトを載せない）。旧コメントと矛盾する場合は **本ドキュメントと `save_load.py` モジュール doc** を正とする。

2. **`payload` 組み立ての所在**  
   - **対応済**: `save_payload.build_save_payload` が単一ソース。CLI（年度 `6`・シーズン `10`）と UI システム窓の両方から利用。

3. **未保存（dirty）判定**  
   - **UI モード（第1段・弱い版）**: `ui_flow["dirty"]`。`次へ進む` で 1 ラウンド進行後・オフシーズン完了後・デバッグ一括進行後に `True`。システムからの **セーブ成功・ロード成功**で `False`。メインウィンドウ **×閉じる** で `dirty` 時のみ確認。**ロスター編集のみ**などは未検知（厳密 dirty は後段）。

4. **ロードの副作用**  
   - **UI モード対応**: 検証成功後に **`MainMenuView.close_all_subwindows()`** で子ウィンドウを閉じ、`game_state` と `view.team` / `view.season` を差し替え、`init_simulation_random`（種あり時）、`refresh()`。失敗時は **状態を書き換えない**。

5. **コンフィグの音量・キー再割り当て**  
   - `user_settings` 既定に **BGM/SE は無い**。追加は **スキーマ拡張＋再生層の参照**が必要。**第1段では「未対応」表示か、settings にキーを足すなら `_DEFAULTS` と `_normalize` を同時更新**。

6. **pickle とメタデータ一覧**  
   - スロット一覧で **各セーブの `saved_at_unix` を出す**には、**ファイル全体を unpickle**するか、**別メタファイル**が必要。前者は **悪意ある pickle のリスク**（信頼できる自ディレクトリ前提で許容するか方針化）。**第1段はファイル名＋`Path.stat().st_mtime` のみ**でもよい。

### 0.3 より安全にするための前提（仕様に明記）

- **セーブ形式・`normalize_payload`・`validate_payload` を GUI から迂回しない**。
- **設定は `save_user_settings(_normalize(...))` 経由**（手編集 JSON の想定挙動は docstring 既存どおり）。
- **システムメニュー = 表示＋確認ダイアログ＋既存関数呼び出し**。ビジネスロジックを `main_menu_view` に増やさない。
- **タイトル／終了**は **二段階確認**（未保存の定義を文言で明示）。
- **プレイガイド**は **静的テキストまたはリポジトリ内 `docs/` 参照**でよい。実行時に外部 URL へ依存しない（オフライン配布考慮）。

---

## 1. システムメニュー仕様 第1稿（たたき台）

### 1.1 大分類（6案＋整理提案）

| ID | 名称（UI） | 役割 | 既存との関係 |
|----|------------|------|----------------|
| S1 | **セーブ** | 現在世界の永続化 | `save_world`・`validate_payload`・payload 組み立て |
| S2 | **ロード** | 世界の復元 | `load_world`・`validate_payload`・**再入オーケストレーション** |
| S3 | **設定** | 環境・表示 | `user_settings`（ウィンドウ・ログ・キーバインド・Steam フラグ） |
| S4 | **プレイガイド** | ヘルプ | 静的（`Text` / `ScrolledText`）または `docs` 抜粋 |
| S5 | **タイトルへ戻る** | セッション離脱 | **現状フローと整合する範囲**で定義（後述） |
| S6 | **終了** | アプリ終了 | `root.quit` / `destroy`＋確認 |

**名称・順序の提案**

- **「コンフィグ」→「設定」**の方が日本語 UI と `settings.json` と一致しやすい。  
- **セーブ／ロードを隣接**（上から S1→S2）。  
- **終了は最下**（誤タップ対策）。  
- **タイトルへ戻る**は **S6 の直上**、または **「セッション」サブセクション**にまとめる。

**統合案（第1段の軽量化）**

- **S1+S2 を1タブ「セーブ／ロード」**にし、左にスロット一覧・右に操作ボタン → 実装コスト削減。6タブ維持でもよい。

---

### 1.2 各分類の中項目・入力形式

#### S1 セーブ

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| スロット選択 | リスト／ラジオ | `default_save_path(slot)` と整合する **英数字スロット名**（`quicksave` 等） |
| 上書き確認 | OK/Cancel | 既存ファイルあり時 |
| 実行 | ボタン | **`build_save_payload` + `validate_payload` + `save_world`** |
| 成功／失敗 | ダイアログ／ラベル | 例外はユーザー向け短文＋ログ |
| セーブ不可 | グレーアウト＋ツールチップ | **レギュラー中など禁止条件**を `save_load` コメントと揃える |
| 日時・簡易メタ表示 | 表示 | **第1段**: ファイル `mtime` のみ可 |
| 自由なセーブ名 | テキスト入力 | **後段**（パスサニタイズは `default_save_path` と同型に） |

#### S2 ロード

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| スロット／ファイル選択 | リスト or ファイルダイアログ | `.sav` のみ |
| 読み込み確認 | OK/Cancel | **現在の未保存方針**に連動 |
| 実行 | ボタン | `load_world` → `validate_payload` → **`on_apply_loaded_world`（要新設・main 側）** |
| エラー表示 | ダイアログ | `ValueError` / `FileNotFoundError` メッセージをそのまま短く |
| 破損・バージョン不一致 | 表示 | `migrate_blob_to_current` 失敗時は **ロード中止**（既存挙動尊重） |

#### S3 設定

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| ウィンドウ幅・高さ | スピンまたはプリセット | `resolve_window_geometry` と矛盾しない範囲 |
| フルスクリーン | チェック | `apply_tk_window_settings` 既存 |
| ログレベル | ドロップダウン | `DEBUG`〜`CRITICAL`（`apply_settings_to_environment` との兼ね合い） |
| サブウィンドウ閉じるキー | 表示＋将来: 入力 | `tk_binding_for(..., KEY_ACTION_CLOSE_SUBWINDOW)` |
| Steam ライセンス必須 | チェック | `steam_require_license`（起動時挙動は既存） |
| 既定に戻す | ボタン | `_DEFAULTS` に戻し `save_user_settings` |
| BGM / SE 音量 | スライダー | **後段**（再生エンジンと `_DEFAULTS` 拡張が必要） |

#### S4 プレイガイド

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| カテゴリ | リスト or Notebook | 基本操作／GM／ルール／用語 等 |
| 本文 | スクロールテキスト | **静的文字列**または `docs/*.md` から読み込み（ビルドに同梱） |
| 外部 Wiki リンク | 任意 | **第2段** |

#### S5 タイトルへ戻る

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| 確認 | OK/Cancel | 未保存警告 |
| 実行 | ボタン | **第1段案A**: 「タイトル画面は現在 CLI 起動時のみです。終了してターミナルから再起動してください」と案内のみ。**案B**: `root.quit()` で `main` の `mainloop` 後にタイトルループへ戻すよう **`simulate()` を構造化**（**変更範囲大・要設計**） |

#### S6 終了

| 中項目 | 入力形式 | 備考 |
|--------|----------|------|
| 未保存警告 | チェック付き確認 | S5 と共通ロジック化 |
| 実行 | ボタン | `root.destroy` or `quit`（**Steam 終了フック**があれば既存に合わせる） |

---

### 1.3 初期実装での役割（まとめ）

- **システム（現状の第1段）**: 左「システム」から **`main._open_main_menu_system_window` が開く Toplevel**（クイックセーブ／名前付き保存／ロード／閉じる）。**Notebook 6 タブは未着手**（情報／歴史と同型の大型化は後段）。
- **セーブ**: 常時 `save_world` 可（途中は `resume_season` 付き）。**`build_save_payload` 単一ソース**。クイックセーブは **既存ファイルがある場合のみ上書き確認**。
- **ロード**: **main 閉包**で `game_state` 更新＋`close_all_subwindows`＋`view` 差し替え＋`refresh`。
- **設定**: 既存キーのみ編集・即時プレビュー（geometry は次回起動も含め注意書き）。
- **ガイド**: 静的。
- **タイトル／終了**: 確認ダイアログ必須。**タイトルは第1段は案Aでも可**。

---

### 1.4 どこまでを初期実装対象にするか

| 区分 | 内容 |
|------|------|
| **初期（第1段・最優先）** | **payload 単一化**（`build_save_payload`）✓。**システム Toplevel（セーブ／ロード）**✓。**メイン閉じる時の弱い未保存確認**✓。 |
| **初期（第1段・残り）** | ~~**設定タブ**~~ ✓。~~システム内終了~~ ✓。**セーブ禁止条件**は現状「なし」（途中セーブ可方針）。 |
| **第2段** | 全 `*.sav` 列挙、`saved_at` 表示。Notebook 化。**厳密 dirty**（GM 操作含む）。 |
| **後回し** | 音量・演出速度、キー再割り当て UI、自動セーブ、Steam クラウド、タイトルへの完全リセット（案B）。 |

---

### 1.5 切り分け（表示のみ / 接続のみ / 後回し）

| 項目 | 区分 |
|------|------|
| セーブパス・制約の説明文 | **表示のみ**でよい（初回） |
| `save_world` / `load_world` | **既存接続のみ** |
| `user_settings` 編集 | **接続＋検証** |
| プレイガイド本文 | **静的表示** |
| メタリッチなスロット一覧 | **後回し**（mtime のみ先でも可） |
| 未保存の厳密トラッキング | **後回し**（第1段は確認ダイアログ固定でも可） |

---

### 1.6 初期反映イメージ（実装済みとの対応）

- **`persistence/save_payload.py`** … `build_save_payload` / `rebind_resume_season_to_world`。  
- **`main._open_main_menu_system_window`** … Tk のみ。ロジックは閉包内。  
- **`main.run_main_menu_ui_mode`** … `game_state`・`ui_flow`・`on_system_menu`・`on_main_window_close`。ロード時は `resume_season` があればそれを、なければ `Season(teams, free_agents)` を代入。`at_annual_menu` を `ui_flow["offseason_completed"]` に反映。

---

### 1.7 実装優先順位（保全優先・更新）

1. ~~payload 抽出~~ ✓  
2. ~~システム窓・セーブ／ロード・CLI 途中セーブ~~ ✓  
3. ~~**設定タブ**~~ ✓。  
4. ~~システムからの終了~~ ✓（**アプリを終了**、`dirty` 時は注意文）。メイン × 閉じるも **弱い確認**あり。  
5. **プレイガイド**（静的）。  
6. **タイトルへ戻る**（案A 文案）。  
7. スロット一覧・メタ表示・厳密 dirty。

---

## 2. Cursor 視点：質問への回答

### 2.1 この構成は現状に対して自然か

**はい。** 6分類は既存の **セーブ／設定／終了**の責務と対応する。ただし **タイトルへ戻る**だけは **現行 UI↔CLI 境界**と噛み合わせる定義が必要。

### 2.2 どれを先に作ると最も安全か

1. **payload 単一化**（セーブ互換の要）。  
2. **設定タブ**（`user_settings` は既に整備済み）。  
3. **終了確認**。  
4. セーブ・ロード。

### 2.3 接続だけ先／詳細 UI は後回し

- **先**: `save_world`／`load_world`／`save_user_settings`。  
- **後**: スロットメタのリッチ化、音量、キー UI、自動セーブ。

### 2.4 初期から入れても壊れにくい項目

- 設定の **ウィンドウサイズ・フルスクリーン・ログレベル**（既定 `_DEFAULTS` 範囲）。  
- プレイガイド **固定文**。  
- **終了確認**。

### 2.5 仕様として曖昧・危険・衝突しそうな箇所

- ~~セーブ許可タイミング~~ → **途中セーブ可**（`resume_season`）。オフ直後 UI は `at_annual_menu=True` で Season 非保存。  
- **未保存の定義** → UI は **進行ベースの弱い dirty** のみ。GM のみ変更は未検知。  
- ~~ロード後の View 同期~~ → **close_all_subwindows + game_state + refresh** で対応済。  
- **タイトルへ戻る**の意味（CLI 再起動 vs アプリ内ループ）… 未着手。

### 2.6 責務分離（推奨）

| 層 | 責務 |
|----|------|
| `save_load.py` | I/O・バージョン・normalize |
| `user_settings.py` | 設定スキーマ・検証・保存 |
| `main.py`（または薄い orchestrator） | payload 生成・ロード後の世界再構築・`season_count` 管理 |
| GUI | 入力・確認・コールバック起動のみ |

### 2.7 セーブスロット情報の安全な参照

- **第1段**: `saves_dir().glob("*.sav")` の **ファイル名＋mtime**。  
- **第2段**: 信頼ディレクトリ前提で **pickle 先頭のみ読み `saved_at_unix` 表示**（実装時は **信頼境界を doc に明記**）。

### 2.8 未保存状態・確認ダイアログの層

- **現状**: `run_main_menu_ui_mode` の **`ui_flow["dirty"]`** と **`on_main_window_close`**（メイン × 閉じる）。  
- **後段**: `last_save_unix`、システムからの **`can_save_state_message()`** コールバック、GM 操作フックによる厳密化。

### 2.9 より安全な画面分けの代替案

- **タブ3つ**: **「データ（セーブ／ロード）」／「設定」／「ヘルプと終了」** — 終了・タイトルを1タブにまとめ誤操作を減らす。

---

## 3. 改善提案・注意（実装時）

- **このまま進めてよい点**: 6分類の枠、`user_settings` 起点の設定、既存 `save_load` 尊重、**`build_save_payload` 単一ソース**。  
- **先に確認したい論点**: **厳密 dirty** の範囲。**タイトルへ戻る**のプロダクト定義。  
- **破壊回避**: pickle 形式変更は `SAVE_FORMAT_VERSION` と `migrate_blob_to_current` で。**GUI から `normalize_payload` をスキップしない**。**`settings.json` のキーを勝手にリネームしない**。

---

## 4. 手動スモークチェックリスト（システム／第1段想定）

1. 設定変更 → **ファイルが `settings.json` に反映**され、再起動後も維持される。  
2. 不正な JSON を手で壊しても **起動時フォールバック**（既存挙動）で落ちない。  
3. セーブ実行で **`.tmp` → replace** が行われ、途中クラッシュで壊ファイルが残りにくい（既存）。  
4. ロード失敗時 **世界が半端に書き換わらない**（トランザクション的に）。  
5. メインウィンドウ × 閉じる／終了確認で **誤タップでも1回はキャンセル可能**。  
6. UI で人事など **サブウィンドウを開いた状態でロード** → 子ウィンドウが閉じ、ダッシュが新しい世界に一致する。  
7. **クイックセーブ**で既存 `quicksave.sav` があるとき **上書き確認**が出る。  

---

## 5. 実装反映メモ（2026-03-28 追記）

以下は **リポジトリ現状**に合わせた要約（確定仕様ではない）。

### 5.1 ペイロードと `resume_season`

| キー | 役割 |
|------|------|
| `resume_season` | シーズン進行中の `Season` インスタンス（**`at_annual_menu=False` のときのみ**ペイロードに含める）。旧セーブに無い場合 `normalize_payload` で `None`。 |
| `at_annual_menu` | CLI / ロード再開で **年度進行メニューへスキップ**するフラグ。オフ済み後の UI クイックセーブでは `True` とし **`resume_season` は載せない**。 |
| `rebind_resume_season_to_world` | `load_world` 直後に呼び、`resume_season.all_teams` / `free_agents` をペイロード先頭と一致。失敗時は `resume_season` を `None` に落とす。 |

### 5.2 CLI

- シーズンメニュー **10**: 途中セーブ（`resume_season=season`, `at_annual_menu=False`）。  
- 年度メニュー **6**: `at_annual_menu=True`, `resume_season=None`。  
- タイトル「続きから」: `_prompt_load_resume` 内で `rebind` 済み → `run_interactive_season(resume=...)`。

### 5.3 主画面 UI（`run_main_menu_ui_mode`）

- **`game_state`**: `teams`, `free_agents`, `user_team`, `season`, `season_count`, `tracked_player_name`。  
  - UI オフ完了後の CLI 接続では `run_interactive_season(..., start_at_annual_menu=True, initial_season_count=game_state["season_count"])` とし、高年次の `season_count` が 1 に戻らないようにする。  
- **`ui_flow`**: `offseason_completed`, `dirty`。  
- **`MainMenuView`**: `on_system_menu`（システム）, `on_main_window_close`（未保存の弱い確認）。  
- **`close_all_subwindows`**: ロード適用直前に実行（人事・GM・情報・歴史・日程・システム窓など）。  
- **システム Toplevel**: Notebook（**データ**／**設定**）。データ: セーブ・ロード・アプリ終了。設定: `settings.json` 編集・即時反映（幾何・Esc バインド・ログレベルは実行中反映可、Steam 主に次回起動）。

### 5.4 テスト

- `basketball_sim/tests/test_phase0_smoke.py`: `test_save_load_midseason_season_roundtrip`（途中セーブの `current_round` と `all_teams is teams`）。  
- `main.run_smoke`: `build_save_payload` 経由で保存（本番と同形）。

### 5.5 次に詰めるとよい項目（未実装）

- ~~システム内 **設定タブ**~~ ✓（Notebook「設定」: 幅・高さ・フルスクリーン・ログ・閉じるキー・Steam／保存・画面上のみ既定に戻す）。  
- ~~システム内 **終了**~~ → **アプリを終了**ボタン（`dirty` 時は注意文付き確認のうえ `root.destroy`）。  
- **プレイガイド**・**タイトルへ戻る**文案。  
- **スロット一覧**（`*.sav` + mtime）。  
- **厳密 dirty**（GM 操作・トレード等をフック）。

---

## 6. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-28 | 第1稿: 6分類と既存 save_load / user_settings / main の対応、セーブタイミング・payload 単一化・ロード再入・未保存・タイトル戻りの論点、優先順位、スモーク項目。 |
| 2026-03-28 | 追記: `save_payload`・途中セーブ・UI システム窓・`game_state`／`dirty`／メイン閉じる確認・`close_all_subwindows`・クイックセーブ上書き確認・**アプリを終了**・`run_smoke` を `build_save_payload` 経由に統一・pytest を文書化。§5 実装反映メモ・§6 変更履歴に再編。 |
| 2026-03-28 | システム窓に **設定タブ**（`user_settings` 保存・`apply_runtime_user_settings`・ログ即時反映・フルスクリーン解除修正）。`fresh_default_settings` / `normalize_user_settings` / `is_valid_tk_binding_sequence` 公開。 |
| 2026-03-28 | `run_interactive_season(initial_season_count=…)` と `_starting_season_count_for_interactive_loop`：GUI→CLI 年度メニューで `season_count` を維持。増分は「次のシーズンへ」のみ。 |
