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

**2026-05-11 追記**: §4.2 の **Phase 0 残（実作業候補 5 項目）はすべて完了**（`#1 ライセンス強制実機テスト` 完了をもって全項目 `[x]` 化済み）。§3 ランタイム「ライセンス」`[x]` も同日に更新。**Phase 0 必須項目（出荷可否判断系・ユーザー向け doc 系）はこれで完了**。§5 Steam パートナーの **「ストア説明文（日本語）に実績の有無を明記する」**（v1 出荷判断の必須項目ではない継続管理項目）と、§4.3 の人間作業（ストア一般公開・最終発売審査・税務／本人確認の現在表示の都度確認）は本書の Phase 0 残対象外として別途管理する。詳細は改訂履歴 2026-05-11 を参照。

### 配布・ビルド

- [x] Windows 向け **`BasketballGM.exe`**（PyInstaller）が **Steam 用コンテンツルート**に配置できる
- [x] **`steam_api64.dll`**（SDK が許可する再配布物のみ）を exe と同階層に置ける運用が確定している
- [x] **SteamPipe** でビルドをアップロードし、**デフォルトブランチ**に載せられることを確認した（**default に Build をライブ設定**すること）
- [x] 起動オプション・作業ディレクトリが **`BasketballGM.exe`** と一致している（`STEAMWORKS_DESIGN.md` の整合表）。Steam クライアントの**起動オプションは空**で確認済み

### Steamworks ランタイム

- [x] **`SteamAPI_Init` / `Shutdown` / `SteamAPI_RunCallbacks`** が安定（tkinter では `pump_steam_callbacks` が動いている）。**新 SDK では `SteamAPI_InitFlat` フォールバック**（`steamworks_bridge`）
- [x] **ライセンス**: `BIsSubscribed` 相当で未購入時の挙動が仕様どおり（`settings.json` の `steam_require_license` と環境変数の整理済み）／**強制終了ポリシーの実機テスト（Case A 購入済み・B 未購入・C Steam 未起動）を 2026-05-11 に完了**（`docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md` §7 判定表・改訂履歴参照。Case B は実機で `BIsSubscribed: False` ＋ exit 3 ではなく Steam API 初期化失敗 ＋ exit 2 で起動拒否されたが、ゲームメニュー未到達のため合格扱い／同 §8 注 1）
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
- [x] **GitHub Actions** で pytest ＋（該当するなら）Windows ビルドが継続できる  
  ※ 2026-05-08 完了。`.github/workflows/ci.yml`（`push`/`pull_request`/`workflow_dispatch`、ubuntu-latest × windows-latest × Python 3.11/3.12 で `pip install -e ".[dev]"` → `pytest`（heavy 除外）→ `--smoke`、加えて windows-latest で `PyInstaller --noconfirm BasketballGM.spec` → `BasketballGM.exe --smoke` → SHA256 生成 → `actions/upload-artifact@v4`（保管 14 日））と `.github/workflows/balance-guard.yml`（`workflow_dispatch` ＋日次 cron `0 18 * * *`、`test_simulation_balance_guard.py` のみ実行）の 2 本構成は、現行 `pyproject.toml` `[dev]` / `[build]`、`BasketballGM.spec`、`basketball_sim/main.py --smoke` と整合。**継続方針**で出荷判断可。判定詳細は §4.6 を参照。

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
| 1 | **ライセンス強制実機テスト** | **完了**（2026-05-11、実機実施済み・人間作業） | 実機作業＋ docs 完了化 | §3 ランタイム `[x]`「ライセンス／強制終了ポリシーの実機テスト」 | `docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md` §7 判定表に Case A（購入済み・`steam_is_subscribed: True` ＋ Steam クライアントから起動可）／Case B（未購入・**Steam API 初期化失敗 ＋ `LASTEXITCODE=2` で起動拒否**・ゲームメニュー未到達・§8 注 1 で合格扱い）／Case C（Steam 未起動・`LASTEXITCODE=2` で起動拒否）を記録済み。根拠ログは `reports/license_real_device_steam_diag_owned.txt` ほか同 §7 メモ欄に列挙（`reports/*.txt` 自体はコミット対象外）。Case D は省略（A・B・C で `[x]` 化必要十分条件を充足）。 |
| 2 | **セーブ README** | **完了**（2026-05-08） | docs（コード変更なし） | §3 セーブ `[x]` / §5「ルート `README.md` `[x]`」 | ルート `README.md` に Steam 版起動・セーブ所在（PC ローカル）・バックアップ・トラブルシュートを追記済み（§「Steam 版を遊ぶ前に（ユーザー向け）」§A〜§E）。**残候補**: `installer/README.md` のリリース・インストーラ手順への補足は別 PR で（必要に応じ）。 |
| 3 | **ストア説明文への「セーブはローカル」明記** | **完了**（2026-05-09、Steam パートナー画面のストア説明文へ反映済み・人間作業） | 人間作業（パートナー画面）＋ docs ドラフト | §3 セーブ（README 側は `[x]` 済）／ §5「ストア説明文（日本語）」`[x]` 化 | §4.7 のドラフトを基に **2026-05-09 に Steam パートナー画面のストア説明文へ反映済み**。採用文言は §4.7 末尾「採用文言（2026-05-09 反映）」を参照。今後ストア文面を編集する際は、§4.7 と README §「Steam 版を遊ぶ前に（ユーザー向け）」§B〜§E の差分を同期すること。 |
| 4 | **クラッシュログ判断** | **完了**（2026-05-08、§4.5 で完了化） | コード（小 PR）＋ docs 完了化 | §3 品質・運用 `[x]`「クラッシュログ … 出荷してよい水準か判断」 | 詳細は §4.5 参照。`install_tk_callback_excepthook(root)` を `basketball_sim/utils/game_logging.py` に追加し、`MainMenuView` / `SpectateView` の `tk.Tk()` 直後で `root.report_callback_exception` を差し替え。Tk callback 例外も `game.log` と `last_crash.txt` に記録される。pytest 3 件追加・smoke ok。 |
| 5 | **GHA 継続判断** | **完了**（2026-05-08、§4.6 で判定 A：**継続**） | CI 棚卸し＋ docs 判定 | §3 品質・運用 `[x]`「GitHub Actions で pytest ＋ Win ビルドが継続」 | `.github/workflows/ci.yml`（matrix pytest ＋ smoke ＋ PyInstaller artifact）／`.github/workflows/balance-guard.yml`（heavy／日次）の 2 本構成は現行コード／`pyproject.toml`／`BasketballGM.spec` と整合。**設定変更なしで継続**。GitHub 上の最新実行結果（成功／失敗履歴）の目視確認は人間作業（運用監視）として残るが、Phase 0「継続できる」判断としては完了扱い。 |

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

### 4.6 GHA 継続判断 詳細記録（2026-05-08 現状確認）

**確認したもの**: `.github/workflows/ci.yml`（CI 本体）、`.github/workflows/balance-guard.yml`（heavy／日次）、`pyproject.toml`（`[dev]` / `[build]` extras・`testpaths`・`requires-python`）、`requirements.txt` / `requirements-dev.txt`、`BasketballGM.spec`（PyInstaller 入口）、`basketball_sim/main.py`（`--smoke` ハンドラと `print("smoke ok")`）、`basketball_sim/__main__.py`（`python -m basketball_sim` 経路）、`basketball_sim/tests/test_simulation_balance_guard.py`（heavy 監視テスト）、`docs/SIMULATION_BALANCE_GUARD.md`、`README.md`「GitHub Actions の Artifact から exe を確認」節、`docs/PRODUCT_ROADMAP_AND_VISION.md` §138（バランス係数変更時の heavy 成功必須）。

**workflow 一覧と整合性（◎）**:

| ファイル | 名前 | トリガー | runs-on / matrix | 主要コマンド | 整合性 |
|---|---|---|---|---|---|
| `.github/workflows/ci.yml` | `CI` | `push: [main, master]` / `pull_request` / `workflow_dispatch` | `[ubuntu-latest, windows-latest] × [3.11, 3.12]`（fail-fast: false） | `pip install -e ".[dev]"` → `python -m pytest basketball_sim/tests -q --ignore=...test_simulation_balance_guard.py` → `python -m basketball_sim.main --smoke` | `pyproject.toml` `[project.optional-dependencies] dev = ["pytest>=8.3.0,<9"]`、`requires-python = ">=3.10"`、`testpaths = ["basketball_sim/tests"]` と整合。`basketball_sim/main.py` に `if "--smoke" in sys.argv:` が存在し `print("smoke ok")` する（2026-05-08 ローカル確認）。`test_simulation_balance_guard.py` は実在し heavy 除外できる。 |
| 同（続き） | `build_exe_windows` | 同上（`workflow_dispatch` などを通じて起動） | `windows-latest`（timeout-minutes: 30） | `pip install -e ".[build]"` → `PyInstaller --noconfirm BasketballGM.spec` → `.\dist\BasketballGM.exe --smoke` → SHA256 生成 → `actions/upload-artifact@v4`（`BasketballGM-windows-exe`、保管 14 日、`if-no-files-found: error`） | `pyproject.toml` `[project.optional-dependencies] build = ["pyinstaller>=6.0,<8"]`、`BasketballGM.spec`（`name="BasketballGM"`、`Analysis(["basketball_sim/main.py"])`）、`README.md` §「GitHub Actions の Artifact から exe を確認」と整合。 |
| `.github/workflows/balance-guard.yml` | `Balance Guard (heavy)` | `workflow_dispatch` / `schedule: cron "0 18 * * *"`（03:00 JST） | `ubuntu-latest`（timeout-minutes: 20） | `pip install -e ".[dev]"` → `python -m pytest basketball_sim/tests/test_simulation_balance_guard.py -q` | `test_simulation_balance_guard.py` 実在。`docs/SIMULATION_BALANCE_GUARD.md` に監視指標（総得点／3P／TO／勝率偏り等）が記載、`docs/PRODUCT_ROADMAP_AND_VISION.md` §138「バランス係数変更は `.github/workflows/balance-guard.yml`（heavy）成功を必須判定」と整合。CI 本体から除外され、heavy だけ別 workflow に分離する設計は妥当。 |

**ローカル確認**:

- `python -m basketball_sim --smoke` → `smoke ok`（2026-05-08）。
- `python -m pytest basketball_sim/tests -q --ignore=basketball_sim/tests/test_simulation_balance_guard.py --collect-only` → エラーなく収集できる（`pyproject.toml` の `addopts = "-q"` と `testpaths` を使用）。
- `actions/checkout@v4` / `actions/setup-python@v5` / `actions/upload-artifact@v4` はいずれも 2026-05 時点で広くメンテされている安定版。

**判定**: **A**（継続）

**理由**:
- workflow 構成（`ci.yml` の 2 ジョブ ＋ `balance-guard.yml` の 1 ジョブ）が、現行コード／`pyproject.toml`／`BasketballGM.spec`／`basketball_sim/main.py --smoke` と矛盾していない。
- Phase 0 として必要な最小限（**pytest（heavy 除外）／CLI smoke／Windows PyInstaller artifact ／ heavy 監視の独立 schedule**）はすべて揃っている。
- `requires-python>=3.10` に対し matrix が 3.11／3.12 を使うのは安全側。
- 設定変更を加えなくても、現状のまま GitHub 上で push／PR ごとに走らせられる。
- 重い `test_simulation_balance_guard.py` は CI 本体から除外され、`balance-guard.yml` 経由でのみ走る設計（バランス係数変更時の必須判定として機能）。

**残りの軽微な留意点（GHA 継続判断の `[x]` 化を妨げない）**:
- 直近 GitHub Actions の **実行履歴（成功／失敗の系列）** はリポジトリ Web UI でしか確認できない。**人間が GitHub 上で Actions タブを目視確認**する作業は別途必要だが、これは「workflow を継続するか」という判断（本タスクのスコープ）とは別レイヤー（運用監視）。
- リリース時に `BasketballGM.exe` の SHA256 を Steam デポと突き合わせる運用（`README.md` §165「GitHub Actions でのメモ（自動ビルド時）」）は人間が都度実施する。
- heavy `balance-guard.yml` の cron 実行は、リポジトリが Public または Pro/Team プランで動くこと前提。仮に **60 日無活動でリポジトリの schedule が停止**された場合は、push をきっかけに自動再開できる Actions 仕様を運用で許容する。

**次アクション**:
- **設定変更なし**で継続。
- 人間タスク: GitHub の Actions タブで直近の `CI` / `Balance Guard (heavy)` 実行が成功しているかを目視確認（運用監視・本 PR 範囲外）。
- 万一実行が壊れていた場合は別 PR で「修正範囲を限定して」対応する（CI 全体の再構成は不要）。

**完了条件の充足**:
- workflow 構成と現状コード／パッケージ構成の整合確認。
- ローカル `smoke ok`。
- §3 品質・運用「GitHub Actions」`[ ]` → `[x]` に更新。
- §4.2 #5「GHA 継続判断」を「完了（2026-05-08）」に更新。

### 4.7 ストア説明文ドラフト（セーブはローカル、2026-05-08）

**位置づけ**: §4.2 #3「ストア説明文への『セーブはローカル』明記」の **docs ドラフト**。Steam パートナー画面のストア説明文（日本語）に貼り付けるための文言を、**ゲーム内・README と整合する形**で本書に固定する。

**根拠**:
- ルート `README.md` §「Steam 版を遊ぶ前に（ユーザー向け）」§B「セーブはローカル PC 保存（Steam クラウド非対応）」、§C「バックアップ（PC 移行・再インストール前）」、§E「v1 対象外機能（決定事項）」（commit `48ecbaa`）。
- `basketball_sim/integrations/STEAMWORKS_DESIGN.md` §1（チェックリスト 1: クラウドセーブ v1 = いいえ、ストア／README で「セーブは PC ローカル」と明記する方針）。
- 本書 上表「チェックリスト 1（クラウド v1）= いいえ（決定日 2026-04-05）」。

**確認事項（パートナー画面反映前のチェック）**:

- [ ] 文言に「Steam クラウドセーブ対応」「クラウド自動同期あり」「どの PC でも自動で続きから遊べる」など、誤解を招く表現が **入っていない**こと。
- [ ] `%USERPROFILE%\.basketball_sim\` の表記が README §B と一致していること。
- [ ] 「v1 では未対応」「将来のアップデートで検討する可能性はあるが約束はしない」というトーンが維持されていること。
- [ ] 「発売済み／公開済み」と読める断定表現が入っていないこと。
- [ ] パートナー画面に貼り付けたあと、本書 §5「ストア説明文（日本語）」`[ ]` を `[x]` へ変えること（**人間作業**）。

#### A. 短い注意書き版（ストア「このゲームについて」末尾用・約 80 字）

```text
※セーブデータはお使いの PC にローカル保存されます。本作は Steam クラウドセーブには対応していません（v1）。PC 移行・再インストール前は手動バックアップを推奨します（手順は同梱の README を参照）。
```

#### B. 1 行版（システム要件欄や注意事項欄の補足用・約 50 字）

```text
※セーブデータはローカル保存です（Steam クラウドセーブ非対応・v1）。PC 移行前は手動バックアップを推奨します。
```

#### C. 丁寧な説明版（FAQ・補足セクション用）

```text
■ セーブデータについて（重要）

本作のセーブデータは、お使いの PC のローカル（%USERPROFILE%\.basketball_sim\saves\）に保存されます。本作は Steam クラウドセーブ（Steam Cloud）には対応していません（現行 v1）。

別の PC で続きから遊びたい場合、PC 買い替え・OS 再インストール・ゲームのアンインストールを行う場合は、ゲームを終了した上で、上記フォルダ（特に saves\ 以下）をご自身でバックアップしてください。書き込み途中の *.sav.tmp ファイルはバックアップ対象から除きます。詳しい手順は同梱の README「Steam 版を遊ぶ前に（ユーザー向け）」§B〜§C をご確認ください。

将来のアップデートでクラウドセーブ対応を検討する可能性はありますが、現時点ではスケジュールをお約束するものではありません。
```

**運用メモ**:

- 上記 A／B／C はいずれも README §「Steam 版を遊ぶ前に（ユーザー向け）」§B〜§E の要約であり、新たな仕様を追加していない。**ストア・README・ゲーム内案内の三者を矛盾させないこと**を最優先とする。
- パートナー画面反映後は、**本書 §5「ストア説明文（日本語）」`[ ]` を `[x]` に変更**し、§改訂履歴に「ストア説明文へ反映（YYYY-MM-DD・人間作業）」を追記する。本 PR は **docs ドラフト作成まで**であり、`[x]` 化は行わない。
- 文言を編集した場合は、**README §「Steam 版を遊ぶ前に（ユーザー向け）」と本節の差分を必ず同期する**（実装の保存先・拡張子・既定スロット名が変わったときも同様）。

**パートナー画面反映後の次アクション**:
- 本書 §5「ストア説明文（日本語）」を `[x]` に変更し、反映日を改訂履歴に追記。
- §4.2 #3 の状態を「完了（YYYY-MM-DD）」へ更新（人間作業）。
- 必要なら `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md` の関連表へ反映済み旨を 1 行追記（任意）。

#### 採用文言（2026-05-09 反映）

**反映先**: Steam パートナー画面のストア説明文（日本語）。  
**反映日**: 2026-05-09（人間作業）。  
**位置づけ**: 上記 A／B／C（短い注意書き版／1 行版／丁寧な説明版）を踏まえ、**実際にパートナー画面へ貼り付けた本文**を不可分の事実として記録する。今後ストア文面を編集する場合は、本ブロックと README §「Steam 版を遊ぶ前に（ユーザー向け）」§B〜§E を同時に更新すること。

```text
【セーブデータについて】
本作のセーブデータは、お使いのPC内にローカル保存されます。現行バージョンではSteamクラウドセーブには対応していないため、PC移行・再インストール前には、同梱READMEの案内に沿って手動バックアップをお願いします。
```

**整合確認**:

- 「お使いの PC 内にローカル保存」: README §B「セーブはローカル PC 保存（Steam クラウド非対応）」と整合。
- 「現行バージョンでは Steam クラウドセーブには対応していない」: README §E「v1 対象外機能（決定事項）」および本書 上表「チェックリスト 1（クラウド v1）= いいえ」と整合。
- 「PC 移行・再インストール前には、同梱 README の案内に沿って手動バックアップ」: README §C「バックアップ（PC 移行・再インストール前）」と整合（具体手順は README 側に集約）。
- 「Steam クラウドセーブ対応」「クラウド自動同期あり」「どの PC でも自動で続きから遊べる」「発売済み／公開済み」「パートナー画面に反映済み」など、§4.7 冒頭の **誤解を招く避けるべき表現は含まれていない**ことを確認済み。

---

## 5. 方針確定後に更新する「ユーザー向け」リスト

Steam の設定・ストア文面を変えたら、**同じタイミング**で次も確認する（不要な行は削除してよい）。

### Steam パートナー（ブラウザ）

- [x] ストア説明文（日本語）に、**セーブの所在（PC ローカル保存／Steam Cloud v1 非対応）** を明記する  
  ※ 2026-05-09 反映。Steam パートナー画面のストア説明文（日本語）に「セーブデータはお使いの PC 内にローカル保存／現行バージョンでは Steam クラウドセーブ非対応／PC 移行・再インストール前は同梱 README に沿って手動バックアップ」の趣旨を §4.7「採用文言（2026-05-09 反映）」のとおり貼り付け済み（人間作業）。
- [ ] ストア説明文（日本語）に、**実績の有無**を明記する  
  ※ 2026-05-09 時点で未反映。`basketball_sim/config/steam_achievements.py` の登録状況（`STEAM_ACHIEVEMENT_API_NAMES`）と Steamworks パートナーの実績ダッシュボードを照合し、ストア説明文に実績有無の文面を載せるかを判断する別タスク（未完了）。本項目を `[x]` 化するときは §4.2 へ新規行を立てるか、§4.2 #3 の継続作業として記録する。
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
- **2026-05-08**: §4.6（新節）に **GHA 継続判断**の現状確認結果（判定 **A：継続**）を記録。`.github/workflows/ci.yml`（matrix pytest ＋ smoke ＋ Windows PyInstaller artifact）／`.github/workflows/balance-guard.yml`（heavy／日次 cron）の 2 本構成は、現行 `pyproject.toml`（`[dev]` / `[build]`／`requires-python>=3.10`／`testpaths`）、`BasketballGM.spec`、`basketball_sim/main.py --smoke` と整合。ローカル smoke ok。**§3 品質・運用「GitHub Actions」`[ ]` を `[x]` に更新**、§4.2 #5 を **「完了（2026-05-08）」**へ。設定変更は不要。**コード差分・workflow 差分ゼロ、docs 差分のみ**。Phase 0 残は #1（ライセンス強制実機テスト）／#3（ストア説明文）の 2 項目。
- **2026-05-08**: §4.7（新節）に **ストア説明文ドラフト**（A 短い注意書き版／B 1 行版／C 丁寧な説明版）を追加。文言は README §「Steam 版を遊ぶ前に（ユーザー向け）」§B〜§E と整合し、**Steam クラウドセーブ非対応（v1）／ローカル保存／手動バックアップ推奨**を明記。§4.2 #3 の状態を「**docs ドラフト作成済み／パートナー画面反映待ち（人間作業）**」へ更新。**`[x]` 化は行わない**（パートナー画面反映＝人間作業の完了が条件）。§3 セーブ・§5「ストア説明文（日本語）」`[ ]`／§3 ランタイム「ライセンス」`[ ]` は据え置き。**コード差分・workflow 差分・README 差分ゼロ、docs 差分のみ**。Phase 0 残は #1（ライセンス強制実機テスト）／#3（ストア説明文反映：人間作業）の 2 項目（うち #3 は文言ドラフト完成のため、残るは人間によるパートナー画面反映のみ）。
- **2026-05-08**: §4.2 #1「ライセンス強制実機テスト」用の **手順書 `docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md` を新規作成**（目的・前提条件・終了コード仕様（exit 0/2/3/4/5）・Case A〜D・PowerShell 実行コマンド・ログ保存／抽出コマンド・判定表・完了条件・失敗時の分類・実施記録テンプレ）。`enforce_steam_license` / `try_init_steam` / `--steam-diag`（`steam_init_diagnostics_lines` ＋要約 4 項目）の実装と整合。Cursor 側で `python -m basketball_sim --steam-diag` を 1 回ローカル実行し出力フォーマット（`steam_diag (詳細):` ＋ `steam_diag (要約):` の 2 ブロック）を確認済み。§4.2 #1 の状態を「**手順書作成済み／実機実施待ち（人間作業）**」へ更新。**`[x]` 化はしない**（実機での Case A・B・C の判定根拠が揃った時点で人間が `[x]` 化）。§3 ランタイム「ライセンス」`[ ]` は据え置き。**コード差分・workflow 差分・README 差分ゼロ、docs 差分のみ**。Phase 0 残は #1（ライセンス強制実機テスト：実機実施）／#3（ストア説明文反映：人間作業）の 2 項目（いずれも手順／文言は揃い、人間サイドのアクション待ち）。
- **2026-05-09**: **Steam パートナー画面のストア説明文（日本語）へローカルセーブ表記を反映**（人間作業）。採用文言は §4.7 末尾「採用文言（2026-05-09 反映）」に固定（README §B〜§E と整合・誤解表現なしを確認済み）。**§4.2 #3「ストア説明文への『セーブはローカル』明記」を「完了（2026-05-09）」へ更新**。§5 Steam パートナー「ストア説明文（日本語）」のチェック項目を **「セーブの所在（PC ローカル保存／Steam Cloud v1 非対応）」** と **「実績の有無」** の 2 行に分離し、前者のみ `[x]` 化。**実績の有無は未完了**（未反映）として `[ ]` のまま別途管理する（`basketball_sim/config/steam_achievements.py` の登録状況とパートナー画面の実績ダッシュボードを照合する別タスク）。**§3 ランタイム「ライセンス」`[ ]`／§4.2 #1「ライセンス強制実機テスト」は据え置き**（手順書作成済み・実機未実施のため）。**コード差分・workflow 差分・README 差分ゼロ、docs 差分のみ**。Phase 0 残は **#1 ライセンス強制実機テスト（実機実施・人間作業）** の 1 項目のみ（§5 の「実績の有無」は v1 出荷判断の必須項目ではない継続管理項目として別扱い）。
- **2026-05-11**: **ライセンス強制実機テスト（Phase 0 残最終項目）を実機で完了**（人間作業）。`docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md` §7 判定表に Case A（購入済み・`steam_is_subscribed: True` ＋ Steam クライアントから起動可）／Case B（未購入・**Steam API 初期化失敗 ＋ `LASTEXITCODE=2` で起動拒否**・ゲームメニュー未到達）／Case C（Steam クライアント未起動・`LASTEXITCODE=2` で起動拒否）を記録（いずれも **OK**）。Case D は省略（A・B・C で `[x]` 化必要十分条件を満たしたため）。**Case B は理想形（`BIsSubscribed: False` ＋ exit 3）ではなく実機では Steam API 初期化が成立しない経路（exit 2）で起動拒否されたが、ゲームメニュー未到達 ＝ 起動拒否の目的を満たすため合格扱い**（差分は手順書 §8 注 1 に明記。今後 `BIsSubscribed: False` ＋ exit 3 の実機再現が必要になった場合は Case B-2 として追記する想定）。**§3 ランタイム「ライセンス」`[ ]` を `[x]` に更新**、**§4.2 #1「ライセンス強制実機テスト」を「完了（2026-05-11、実機実施済み）」へ更新**、§2 冒頭に 2026-05-11 追記を追加。**これにより §4.2 の Phase 0 残（実作業候補 5 項目）はすべて完了**（#1 ライセンス強制実機テスト・#2 セーブ README・#3 ストア説明文ローカルセーブ表記・#4 クラッシュログ判断・#5 GHA 継続判断）。**Phase 0 必須項目は完了**。継続管理項目として §5 「ストア説明文（日本語）に実績の有無を明記する」`[ ]`（v1 出荷判断の必須項目ではない）と、§4.3 のパートナー画面側人間作業（ストア一般公開・最終発売審査・税務／本人確認）は別途進める。**コード差分ゼロ／README.md 差分ゼロ／`.github/` 差分ゼロ／`reports/*.txt` はコミット対象外・docs 差分のみ**（更新ファイル: `docs/STEAM_LICENSE_REAL_DEVICE_TEST_PROCEDURE_2026-05.md`／`docs/PHASE0_COMPLETION_TEMPLATE.md`）。ストア説明文の「実績の有無」`[ ]` はそのまま維持。

---

## 参照

- `basketball_sim/integrations/STEAMWORKS_DESIGN.md`（ロードマップとの対応・チェックリスト 1〜5）
- リポジトリ直下 `.cursorrules`（Phase 0 方針）
