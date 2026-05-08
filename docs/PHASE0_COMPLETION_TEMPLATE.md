# Phase 0 完了メモ（自分用・テンプレート）

`basketball_sim/integrations/STEAMWORKS_DESIGN.md` の **「Phase 0 末期の決定チェックリスト」** のうち、特に **3（必須機能の定義）** と **5（ユーザー向け表記の更新リスト）** を具体化するためのメモである。  
**いつ書くか**: Steamworks の本人確認が済み、**本番 App ID** が扱え、**デポにビルドを載せる**段階が見えてきたときに、下を埋めて「Phase 0 の Steam 技術項はここまで」と区切る。

---

## いまの前提（未記入でも可）

| 項目 | メモ |
|------|------|
| 記入日 | 2026-04-05（SteamPipe・実績テストまで反映） |
| App ID（本番） | 4593200 |
| チェックリスト 1（クラウド v1） | **いいえ**（v1 はローカルセーブのみ。Remote Storage は採用しない）→ **決定日: 2026-04-05** |
| チェックリスト 2（Rich Presence v1） | **いいえ**（v1 では未実装のまま。v2 以降で再検討）→ **決定日: 2026-04-05** |

---

## 3. 初回 Steam リリースで「必須」とする機能一覧（Phase 0 完了の定義）

次をすべて満たしたとき、**このプロジェクトでは「Phase 0 の Steam 技術・配布の足場は完了」**とする（`.cursorrules` の Phase 0 と整合させる）。

**2026-04-05 追記**: `[x]` は**確認済み**、`[ ]` は**未了**。**クラウドセーブ／Rich Presence の v1 要否は上表で決定済み（いずれも v1 では含めない）**。Phase 0 全体の「完了宣言」には、セーブの README／ストア明記・ライセンス強制の実機確認など **未了項目**が残る。

### 配布・ビルド

- [x] Windows 向け **`BasketballGM.exe`**（PyInstaller）が **Steam 用コンテンツルート**に配置できる
- [x] **`steam_api64.dll`**（SDK が許可する再配布物のみ）を exe と同階層に置ける運用が確定している
- [x] **SteamPipe** でビルドをアップロードし、**デフォルトブランチ**に載せられることを確認した（**default に Build をライブ設定**すること）
- [x] 起動オプション・作業ディレクトリが **`BasketballGM.exe`** と一致している（`STEAMWORKS_DESIGN.md` の整合表）。Steam クライアントの**起動オプションは空**で確認済み

### Steamworks ランタイム

- [x] **`SteamAPI_Init` / `Shutdown` / `SteamAPI_RunCallbacks`** が安定（tkinter では `pump_steam_callbacks` が動いている）。**新 SDK では `SteamAPI_InitFlat` フォールバック**（`steamworks_bridge`）
- [ ] **ライセンス**: `BIsSubscribed` 相当で未購入時の挙動が仕様どおり（`settings.json` の `steam_require_license` と環境変数の整理済み）※診断・通常接続は確認済み、**強制終了ポリシーの実機テストは別途**
- [x] **実績**: 少なくとも 1 つ、`unlock_achievement` から StoreStats まで通ることを実機で確認（`ACH_PHASE0_TEST`。**`RequestCurrentStats` 後に SetAchievement**）
- [x] **`--steam-diag`** が期待どおり（DLL あり・Steam 起動時の値が説明と一致）

### セーブ・設定（v1 方針に合わせてチェック）

**クラウドセーブを v1 に含めない場合（現行ドキュメントの前提）**

- [x] セーブは **ローカルのみ**で破損しにくい（バージョン・正規化・バックアップ方針が README / ストアで説明できる）  
  ※ 2026-05-08 README 更新で「Steam 版を遊ぶ前に（ユーザー向け）§B / §C」にバックアップ手順・既定パス・atomic write（`*.sav.tmp`）の説明を反映。実装は `basketball_sim/utils/paths.py` / `basketball_sim/persistence/save_load.py`。
- [x] ストアまたは README に **「セーブデータは PC ローカル」** と明記した  
  ※ 2026-05-08 README §「Steam 版を遊ぶ前に（ユーザー向け）§B」で「v1 ではセーブデータは Steam クラウドに同期されません。すべてお使いの PC のローカルに保存されます」を明記。**ストア側（パートナー画面の説明文）は別途・人間作業**（4.2 #3 の対象、未完了）。

**クラウドを v1 に含める場合（チェックリスト 1 で「はい」になったとき）**

- [ ] `STEAMWORKS_DESIGN.md` の §3 で選んだ方式（A/B/C）どおりに実装・テスト済み
- [ ] 衝突・オフライン・クォータの**手動確認**をした（範囲を下にメモ）

### 品質・運用

- [x] **クラッシュログ**（`game.log` ローテーション・未処理例外フック等）が「出荷してよい」水準か判断した  
  ※ 2026-05-08 完了。`game.log` ローテーション（1 MB × 3 世代・UTF-8）、`last_crash.txt`、`sys.excepthook`、`threading.excepthook` に加え、**`install_tk_callback_excepthook(root)`** を `basketball_sim/utils/game_logging.py` に追加し、`MainMenuView` / `SpectateView` の `tk.Tk()` 直後で適用。これにより Tk callback 内例外も `game.log` と `last_crash.txt` に記録される。判定詳細は §4.5 を参照。
- [ ] **GitHub Actions** で pytest ＋（該当するなら）Windows ビルドが継続できる

### Phase 0 完了の宣言（1 行）

> Phase 0（Steam 技術・配布）は、上記チェックがすべて埋まった **____年__月__日** をもって完了とする。

---

## 4. 2026-05 時点の Phase 0 残 集約

**位置づけ**: §3 のチェック表（記入日 2026-04-05 起点）を **2026-05 時点の現実に合わせて再要約**したもの。`§3 の `[ ]` を勝手に `[x]` に変えない` を原則に、**残としてどの項目が今も生きているか**を一覧化する。**実機作業や人間作業が必要な項目は本表でも未完了扱い**。詳細な実装方針・運用は `docs/IMPLEMENTATION_PLAN_MASTER.md` §5.1 §11 §12、`docs/PRODUCT_ROADMAP_AND_VISION.md` Phase 0 節と整合。

### 4.1 完了済み・決定済み（再確認・上記 §3 で `[x]` または上表で「いいえ」と確定済み）

| カテゴリ | 項目 | 根拠 |
|---|---|---|
| 配布・ビルド | `BasketballGM.exe`（PyInstaller）配置 | §3 配布・ビルド `[x]` |
| 配布・ビルド | `steam_api64.dll` 同階層配置 | §3 配布・ビルド `[x]` |
| 配布・ビルド | SteamPipe アップロード／default ライブ設定 | §3 配布・ビルド `[x]` |
| 配布・ビルド | 起動オプション・作業ディレクトリ整合 | §3 配布・ビルド `[x]` |
| Steamworks ランタイム | `SteamAPI_Init/Shutdown/RunCallbacks`（`pump_steam_callbacks`）／`SteamAPI_InitFlat` フォールバック | §3 ランタイム `[x]` |
| Steamworks ランタイム | 実績テスト（`ACH_PHASE0_TEST` を `RequestCurrentStats` 後に解除） | §3 ランタイム `[x]` |
| Steamworks ランタイム | `--steam-diag`（DLL あり・Steam 起動時の値が説明と一致） | §3 ランタイム `[x]` |
| v1 方針 | **クラウドセーブを v1 に含めない**（決定日 2026-04-05） | 上表「チェックリスト 1: いいえ」 |
| v1 方針 | **Rich Presence v1 未実装**（決定日 2026-04-05） | 上表「チェックリスト 2: いいえ」 |
| docs 同期 | Steam 主要 docs（PRODUCT / STEAMWORKS_STATUS / STEAMWORKS_DESIGN）の相互同期 | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §5.12 §8.1（2026-04-06 完了） |

### 4.2 Phase 0 残（実作業候補 5 項目・1 件ずつチケット化する）

| # | 項目 | 状態 | 種別 | §3 該当 | 次アクション例 |
|---|------|------|------|---------|----------------|
| 1 | **ライセンス強制実機テスト** | 未完了 | 実機作業＋（必要なら）docs | §3 ランタイム `[ ]`「強制終了ポリシーの実機テスト」 | `enforce_steam_license` を未購入アカウントで実機検証 → ログを `--steam-diag` と合わせて 1 度スナップショットし、判定を本書に追記 |
| 2 | **セーブ README** | **完了**（2026-05-08） | docs（コード変更なし） | §3 セーブ `[x]` / §5「ルート `README.md` `[x]`」 | ルート `README.md` に Steam 版起動・セーブ所在（PC ローカル）・バックアップ・トラブルシュートを追記済み（§「Steam 版を遊ぶ前に（ユーザー向け）」§A〜§E）。**残候補**: `installer/README.md` のリリース・インストーラ手順への補足は別 PR で（必要に応じ）。 |
| 3 | **ストア説明文への「セーブはローカル」明記** | 未完了 | 人間作業（パートナー画面）＋ docs ドラフト | §3 セーブ `[ ]` / §5「ストア説明文（日本語）」 | ゲーム内・README と同じ文言を docs にドラフト → パートナー画面で適用（人間） |
| 4 | **クラッシュログ判断** | **完了**（2026-05-08、§4.5 で完了化） | コード（小 PR）＋ docs 完了化 | §3 品質・運用 `[x]`「クラッシュログ … 出荷してよい水準か判断」 | 詳細は §4.5 参照。`install_tk_callback_excepthook(root)` を `basketball_sim/utils/game_logging.py` に追加し、`MainMenuView` / `SpectateView` の `tk.Tk()` 直後で `root.report_callback_exception` を差し替え。Tk callback 例外も `game.log` と `last_crash.txt` に記録される。pytest 3 件追加・smoke ok。 |
| 5 | **GHA 継続判断** | 未完了 | CI 棚卸し＋ docs 判定 | §3 品質・運用 `[ ]`「GitHub Actions で pytest ＋ Win ビルドが継続」 | `.github/workflows/` 系 CI の現状確認 → 維持／停止／再構成いずれにするかを本書に記録 |

**運用ルール（残 5 項目共通）**

- **1 タスク 1 PR**。複数の残項目を 1 コミットに混ぜない（`docs/IMPLEMENTATION_PLAN_MASTER.md` §6）。
- **実機確認なしに `[x]` 化しない**。各項目の `[ ]` は実作業 PR の中で同時に更新する。
- **コード変更を伴う場合**は `basketball_sim/` の触る範囲を事前に列挙する（`AI_WORKFLOW_RULES.md`）。

### 4.3 後工程・人間作業（パートナー画面で都度確認、本 Phase 0 残の対象外）

| 項目 | 状態 | 種別 | 備考 |
|------|------|------|------|
| ストア一般公開 | 保留 | 人間作業（パートナー画面） | `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`「未確認・パートナー画面で都度要確認」 |
| 最終発売審査 | 保留 | 人間作業（パートナー画面） | 同上 |
| 税務／本人確認の現在表示 | 判断保留 | 人間作業（パートナー画面） | 過去に通過報告あり、再確認が必要ならパートナー画面で目視 |

### 4.4 Phase 4 / Godot 本実装に進む前提条件

- 上記 4.2 の 5 項目のうち、**少なくとも出荷判断系（クラッシュログ・GHA・ライセンス強制）と doc 系（セーブ README・ストア文面）の方針確定**が済んだ段階で、Phase 4 の検討に入る（`docs/IMPLEMENTATION_PLAN_MASTER.md` §11）。
- **Godot 全面移行は計画の主戦場にしない**方針は維持（同 §3）。Godot は情報設計メモ `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の段階で、本実装はまだ。

### 4.5 クラッシュログ判断 詳細記録（2026-05-08 現状確認）

**確認したもの**: `basketball_sim/utils/game_logging.py`（実装本体）、`basketball_sim/utils/paths.py`、`basketball_sim/main.py`（`setup_application_logging` 呼び出し位置）、`basketball_sim/tests/test_game_logging.py`（保護テスト 3 件）、ルート `README.md`（ユーザー向け案内）、実機 `%USERPROFILE%\.basketball_sim\logs\` フォルダ。

**実装済み（◎）**:

| 観点 | 実装 | 根拠 |
|------|------|------|
| ログ保存先 | `%USERPROFILE%\.basketball_sim\logs\game.log` | `game_logging.get_log_file_path()` → `paths.logs_dir() / "game.log"` |
| クラッシュ全文保存先 | `%USERPROFILE%\.basketball_sim\logs\last_crash.txt` | `game_logging.get_last_crash_path()` |
| ローテーション | `RotatingFileHandler(maxBytes=1_000_000, backupCount=3, encoding="utf-8", delay=True)` | `setup_application_logging` 内、1 MB × 3 世代 |
| ログレベル | 環境変数 `BASKETBALL_SIM_LOG_LEVEL` 優先、`settings.json` の `log_level`、既定 `INFO` | `_resolve_log_level` |
| メインスレッド未処理例外 | `sys.excepthook = _excepthook` で `log.critical` ＋ `last_crash.txt` 書き込み ＋ `sys.__excepthook__` 委譲 | `_excepthook` |
| バックグラウンドスレッド未処理例外 | `threading.excepthook = _thread_excepthook` で `log.error` ＋ `last_crash.txt` 書き込み | Python 3.8+ `threading.excepthook` |
| 起動タイミング | `simulate()` 先頭の `setup_application_logging(_settings)`（`try_init_steam` より前） | `basketball_sim/main.py` |
| README 整合 | ユーザー向け案内で `%USERPROFILE%\.basketball_sim\logs\game.log` / `last_crash.txt` を明記、トラブルシュート §D で「`last_crash.txt` を不具合報告に添付」と案内 | ルート `README.md` §「Steam 版を遊ぶ前に（ユーザー向け）§D」 |
| pytest 保護 | パス解決・ローテーション + ログレベル・`last_crash.txt` 書き込みの 3 件 | `basketball_sim/tests/test_game_logging.py` |
| 実機検証（2026-05-08 smoke） | `%USERPROFILE%\.basketball_sim\logs\game.log`（116 KB、smoke 直後に最終更新）、`last_crash.txt`（504 bytes、2026-04-30 生成）が実在 | `python -m basketball_sim --smoke` → `smoke ok` ＋ Get-ChildItem で確認 |

**不足している点（△）**:

- **`Tk.report_callback_exception` のオーバーライドが未実装**（`basketball_sim/` 全体で `report_callback_exception` の grep ヒットなし）。Tk のイベントループ内 callback で発生した未処理例外は、Tk のデフォルトでは標準エラーへ traceback を出力するだけで、`sys.excepthook` を経由しない。**結果として、GUI でユーザー操作中にクラッシュした際の traceback が `last_crash.txt` に残らない可能性が高い**（メインスレッドで `mainloop` 内 callback 経由のため）。
- 製品が **GUI 主操作（`tk.Tk()` を使う `main_menu_view.py` / `spectate_view.py`）** であることを踏まえると、出荷判断に **軽微な穴**として残る。

**判定**: **完了**（2026-05-08、Tk callback 例外フック追加 PR で穴を塞ぎ、§3 品質・運用「クラッシュログ」`[x]` 化）

**経緯（2026-05-08 追記）**:
- 上記「不足している点（△）」として確定した **`Tk.report_callback_exception` 未オーバーライド**を、本日同日の小 PR で解消。
- `basketball_sim/utils/game_logging.py` に **`install_tk_callback_excepthook(root)`** を追加。`root.report_callback_exception` を差し替え、Tk callback 内の未処理例外を以下の経路で記録するようにした。
  - `logging.getLogger("basketball_sim").error(..., exc_info=...)` で `game.log` に traceback 付きで記録（既存 `RotatingFileHandler` 経由）。
  - `_write_last_crash(exc_type, exc_value, exc_tb)` で `last_crash.txt` を上書き保存（既存メインスレッド／別スレッド例外フックと同一経路）。
  - 元の `report_callback_exception` も最後に呼ぶ実装にしたため、**Tk 標準の標準エラー出力挙動は維持**される。
- 適用箇所:
  - `basketball_sim/systems/main_menu_view.py`: `MainMenuView.__init__` の `self.root = root or tk.Tk()` 直後で `install_tk_callback_excepthook(self.root)` を呼び出し（外部から渡された root にも一様適用）。
  - `basketball_sim/systems/spectate_view.py`: `SpectateView.__init__` の `self.root = tk.Tk()` 直後で同様に呼び出し。
  - `basketball_sim/` 全体で `tk.Tk()` の生成箇所はこの 2 箇所のみ（`rg "tk\.Tk\(\)|= Tk\(\)"` で確認）。
- **不変条件の確認**:
  - `sys.excepthook` / `threading.excepthook` の設定経路は変更していない（`setup_application_logging` の本体は無変更）。
  - `game.log` ローテーション設定（1 MB × 3 世代・UTF-8）は変更していない。
  - `last_crash.txt` の保存先（`logs_dir() / "last_crash.txt"`）は変更していない。
  - 多重インストール対策として `root` 上に `_basketball_sim_tk_excepthook_installed` フラグを立て、2 回目以降は no-op。
  - `root` が `None` または `report_callback_exception` を持たない場合は何もしない（CLI 経路 / `--smoke` / `--steam-diag` には影響なし）。
  - フック内のロギング・`last_crash.txt` 書き込みはすべて `try/except` で囲み、Tk のイベントループ全体を巻き込む例外連鎖を起こさない。
- **テスト追加**（`basketball_sim/tests/test_game_logging.py`、tk 不要 / headless）:
  - `test_install_tk_callback_excepthook_writes_last_crash_and_logs`: ダミー root に対しフックをインストールし、`ValueError("boom-tk-callback")` を渡したとき `last_crash.txt` に `ValueError` / `boom-tk-callback` / `Traceback` が含まれること、`basketball_sim` ロガーに「Tk callback」を含むメッセージが流れること、元の `report_callback_exception` が呼ばれていることを検証。
  - `test_install_tk_callback_excepthook_is_idempotent`: 2 回呼んでも `report_callback_exception` が同一オブジェクトのままで、フラグ属性が立つことを検証。
  - `test_install_tk_callback_excepthook_handles_none_safely`: `None` および `report_callback_exception` 属性を持たないオブジェクトに対して安全に no-op で返ることを検証。
- **検証結果**:
  - `python -m pytest basketball_sim/tests/test_game_logging.py -q --tb=short` → 6 件全て pass。
  - `python -m pytest basketball_sim/tests/test_game_logging.py basketball_sim/tests/test_offseason_result_recap_readonly_window.py -q --tb=short` → 19 件全て pass。
  - `python -m basketball_sim --smoke` → `smoke ok`。

**完了条件の充足**:
- pytest 3 件追加 + 既存テスト維持。
- smoke ok。
- 本書 §3 品質・運用「クラッシュログ」`[ ]` → `[x]` に更新。
- §4.2 #4「クラッシュログ判断」を「完了（2026-05-08）」に更新。

---

## 5. 方針確定後に更新する「ユーザー向け」リスト

Steam の設定・ストア文面を変えたら、**同じタイミング**で次も確認する（不要な行は削除してよい）。

### Steam パートナー（ブラウザ）

- [ ] ストア説明文（日本語）… セーブの所在（ローカル／クラウド）、実績の有無
- [ ] ストアグラフィック・トレーラーに関する表記（該当する場合）
- [ ] システム要件・インストール先の説明

### リポジトリ・配布物

- [x] ルート **`README.md`** … Steam 版の起動・セーブ・トラブルシュート  
  ※ 2026-05-08 更新。§「Steam 版を遊ぶ前に（ユーザー向け）」§A 起動 / §B セーブ所在 / §C バックアップ / §D トラブルシュート / §E v1 対象外機能 を追加。
- [ ] **`installer/README.md`** … インストーラ・Release 手順（該当する場合）
- [ ] **`STEAMWORKS_DESIGN.md`** … 実装とズレたら本文を更新

### 法務・信用（該当する場合）

- [ ] プライバシーポリシー（公式サイトまたは Steam に載せる文面がある場合）
- [ ] ゲーム内クレジット（Steam 表記・SDK クレジット要件に合わせる）

### メモ欄

```
（パートナー画面の URL や、差分の要点を自由にメモ）
```

---

## 改訂履歴

- **2026-05-08**: §3 セーブ・設定の `[ ]` 2 件（ローカル＋バックアップ方針／README に「セーブはローカル」明記）と §5 ルート `README.md` を `[x]` に更新。根拠はルート `README.md` の§「Steam 版を遊ぶ前に（ユーザー向け）」§A〜§E。§4.2 #2「セーブ README」も完了状態へ更新。**他の `[ ]`（ライセンス強制実機テスト・クラッシュログ判断・GHA 継続・ストア説明文・`installer/README.md` 等）は実機作業／人間作業／別 PR が必要なため据え置き**。
- **2026-05-08**: §4.2 #4「クラッシュログ判断」と §4.5（新節）に **現状確認結果（判定 B）** を記録。基盤は揃っているが `Tk.report_callback_exception` のオーバーライド未実装が軽微な穴のため、§3 品質・運用「クラッシュログ」`[ ]` は **据え置き**。次 PR 案を §4.5 末尾に明記。実機 smoke で `game.log` / `last_crash.txt` の実在を確認済み。
- **2026-05-08**: 上記「次 PR 案」を実装完了。`basketball_sim/utils/game_logging.py` に `install_tk_callback_excepthook(root)` を追加し、`MainMenuView` / `SpectateView` の `tk.Tk()` 直後で適用。**§3 品質・運用「クラッシュログ」`[ ]` を `[x]` に更新**。§4.2 #4 を **「完了（2026-05-08）」**へ、§4.5 の判定を **「完了」** へ更新（経緯・検証・不変条件は §4.5 に記録）。pytest は headless ダミー root による 3 件追加（書き込み確認・冪等性・None 安全）が pass、`python -m basketball_sim --smoke` も `smoke ok`。Phase 0 残は #1（ライセンス強制実機テスト）／#3（ストア説明文）／#5（GHA 継続判断）の 3 項目。

---

## 参照

- `basketball_sim/integrations/STEAMWORKS_DESIGN.md`（ロードマップとの対応・チェックリスト 1〜5）
- リポジトリ直下 `.cursorrules`（Phase 0 方針）
