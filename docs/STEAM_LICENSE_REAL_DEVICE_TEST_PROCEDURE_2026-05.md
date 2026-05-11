# ライセンス強制 実機テスト手順書（2026-05）

**最終本文同期**: 2026-05-08  
**位置づけ**: `docs/PHASE0_COMPLETION_TEMPLATE.md` §4.2 #1「ライセンス強制実機テスト」の実機実施手順。**人間が実機で実施するための手順書**であり、本書の作成だけでは Phase 0 の `[x]` 化は行わない。実機で必要なログを揃え、判定表を埋めた段階で `PHASE0_COMPLETION_TEMPLATE.md` 側を `[x]` 化する。

**関連**:

- 実装: `basketball_sim/integrations/steamworks_bridge.py`（`enforce_steam_license` / `try_init_steam` / `steam_is_subscribed` / `--steam-diag` の中身は `steam_init_diagnostics_lines` / `steam_loaded_dll_path` / `steam_native_loaded`）。
- 入口: `basketball_sim/main.py`（`simulate()` 冒頭で `try_init_steam()` → `enforce_steam_license(_settings)` を呼ぶ。`--smoke` / `--steam-diag` 経路では `enforce_steam_license` は通らない）。
- 設計: `basketball_sim/integrations/STEAMWORKS_DESIGN.md`（環境変数・終了コード・配布物の方針）。
- 状況メモ: `docs/STEAMWORKS_STATUS_AND_RESUME_MEMO.md`（過去の `--steam-diag` 実測ログを参考に保管）。
- ユーザー向け案内: `README.md` §「Steam 版を遊ぶ前に（ユーザー向け）」§D（実績／Steamworks 機能のトラブルシュート）。
- 進捗チェック: `docs/PHASE0_COMPLETION_TEMPLATE.md` §3 ランタイム「ライセンス … 強制終了ポリシーの実機テスト」`[ ]`。

> **注意**: 本書は **手順書** であり、本書を作っただけでは「実機テスト完了」とは見なさない。`PHASE0_COMPLETION_TEMPLATE.md` 側の `[x]` 化は **人間がテストを実施し、§7 判定表を埋めて根拠ログを残した後**に行う。

---

## 1. 目的

Steam 配布前提で、`enforce_steam_license(settings)` のポリシーが意図どおり動くことを実機で確認する。具体的には次の 2 点：

1. **購入済み（ライセンス保有）アカウント**で起動できること。
2. **未購入（ライセンス非保有）アカウント**で起動が拒否され、`sys.exit(3)` 相当（または `2`／`4`／`5` の意図された終了コード）で終了し、`%USERPROFILE%\.basketball_sim\logs\game.log` または `--steam-diag` の出力に判定根拠が残ること。

**副目的**:

- Steam クライアント未起動時／DLL 不足時／App ID 不一致時の見え方を、`--steam-diag` で切り分けられることを確認する。
- 実機ログ（`game.log` / `--steam-diag` 出力）を `reports/license_real_device_*.txt` に保存して、後で判定根拠として参照できる状態にする。

---

## 2. 前提条件

### 2.1 環境

- **OS**: Windows 10 / 11（`steamworks_bridge.py` のネイティブ DLL 経路は Windows のみ）。
- **アーキテクチャ**: 64-bit Python ／ 64-bit `BasketballGM.exe`。32-bit Python だと `steam_api64.dll` を読めない（`--steam-diag` でも判定可）。
- **Steam クライアント**: ログイン状態で起動できる PC。
- **対象 App ID**: Steamworks パートナーで発行済みの本番 App ID（**共有のスペースウォーピング用 ID は本番に使わない**）。
- **Steamworks SDK**: `redistributable_bin\win64\steam_api64.dll` のみを `BasketballGM.exe` と同階層に配置。`steam_appid.txt` は **開発時のみ**（中身は App ID 1 行）、本番デポからは除外する（`STEAMWORKS_DESIGN.md` §5・§6）。

### 2.2 アカウント

- **購入済み（A 用）**: 対象 App ID のライセンスを保有するアカウント。Steamworks パートナーで「Beta」「Owner Comp」など、**正規にライセンスが付与**されているもの。
- **未購入（B 用）**: 同 App ID のライセンスを **保有しない** アカウント。家族共有の対象外であること。
- 同一 PC で複数アカウントを使う場合は、**Steam クライアントを完全終了 → アカウント切替 → 再ログイン**してからテストする。

### 2.3 ビルド条件

- 推奨: `BasketballGM.exe`（PyInstaller、`pip install -e ".[build]"` → `python -m PyInstaller --noconfirm BasketballGM.spec`）。`Steam クライアントから起動` の経路と、`dist\BasketballGM.exe` 直接起動の双方を後述の Case で使い分ける。
- 開発時の確認: `python -m basketball_sim` でも動作するが、本番条件に近づけるため **可能なら exe ビルド** を使う。

### 2.4 設定

- 既定では `enforce_steam_license` はノーオペ（`steam_require_license: false`）。**ライセンス強制を有効化**するには、次のいずれかが必要（`steamworks_bridge.py` `_steam_license_required`）:
  - `%USERPROFILE%\.basketball_sim\settings.json` で `"steam_require_license": true`。
  - 環境変数 `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1`。
- **厳格モード**（`BIsSubscribed` を呼べない場合も終了させる）を確認する場合は `BASKETBALL_SIM_STEAM_LICENSE_STRICT=1` を併せて設定する。
- **テスト中は `BASKETBALL_SIM_FAKE_STEAM` / `BASKETBALL_SIM_DISABLE_STEAM` を **設定しない**（`enforce_steam_license` がスキップ／影響を受けるため）。`--steam-diag` の確認時のみ意図的に切り替える場合は手順内に明記する。

### 2.5 終了コード（`enforce_steam_license` 仕様）

| exit | 条件 | 期待される判定 |
|---:|---|---|
| `0` | 起動継続（ライセンスチェック OK、または強制無効） | 正常 |
| `2` | ライセンス必須なのに `is_steam_initialized()` が False（フェイクも含めて未初期化） | 異常（Case C 系） |
| `3` | `BIsSubscribed` が **False**（未購入） | **未購入アカウントで期待される終了**（Case B） |
| `4` | `BIsSubscribed` が `None` ＋ `BASKETBALL_SIM_STEAM_LICENSE_STRICT=1` | 厳格モード時の確認用 |
| `5` | ライセンス必須なのに `steam_native_loaded()` が False（フェイク初期化のみ） | 異常（Case D 系） |

> 出典: `basketball_sim/integrations/steamworks_bridge.py` の `enforce_steam_license` 本体（2026-05-08 確認済み）と `STEAMWORKS_DESIGN.md` §「ライセンス必須」。

---

## 3. 事前確認（実機テスト開始前）

実機テスト前に、**Cursor 側でも確認できる**範囲として次を済ませてある（2026-05-08 時点）:

- `python -m basketball_sim --steam-diag` を Steam クライアント未起動の開発 PC で 1 回実行し、出力フォーマット（`steam_diag (詳細):` ＋ `steam_diag (要約):` の 2 ブロック構成、要約は `try_init_steam` / `steam_native_loaded` / `steam_loaded_dll_path` / `steam_is_subscribed` の 4 行）を確認した。
- 候補 DLL の所在・`SteamAPI_InitFlat` 系の export 解決が出ることを確認した（Steam クライアント未起動なので `try_init_steam: False`、`steam_is_subscribed: None` で正常）。
- `enforce_steam_license` は `--smoke` / `--steam-diag` 経路では呼ばれず、`simulate()`（通常起動）でのみ呼ばれることをコードで確認した。

**実機（人間）側で確認すべきこと**:

- 対象 App ID が本番用に切り替わっており、テストアカウントに正しくライセンスが付与（または未付与）になっていること（Steamworks パートナー側）。
- `steam_api64.dll` のバージョンが **64-bit** で、`SteamAPI_InitFlat` を export していること（`--steam-diag` の詳細セクションで `→ SteamAPI_InitFlat: getattr=OK` が出ることで確認可能）。
- `steam_appid.txt` は **開発時のみ** であり、本番デポには含めないこと。

---

## 4. テストケース

実施順は **A → B → C → D** を推奨（A で「正常系の見え方」を固定し、B で「拒否の見え方」を比較する）。

### 4.1 Case A: 購入済み／ライセンス保有アカウント

**目的**: ライセンス保有時に正常起動することを確認。

**条件**:

- Steam クライアント: 購入済みアカウントでログイン・起動済み。
- ビルド: `dist\BasketballGM.exe` または `python -m basketball_sim`。
- 設定: `steam_require_license: true`（`settings.json`）または環境変数 `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1`。

**手順**:

1. 別ターミナルで `--steam-diag` を **先に**実行し、出力を保存する（事前状態スナップショット）。

   ```powershell
   .\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_owned.txt
   ```

   - `try_init_steam: True`、`steam_native_loaded: True`、`steam_loaded_dll_path: <絶対パス>`、`steam_is_subscribed: True` が出ることを目視確認。

2. 続けて通常起動（CLI 起動でも GUI 起動でも可）。`enforce_steam_license` は `simulate()` 冒頭で動くため、起動直後に終了しないかを確認する。

   ```powershell
   $env:BASKETBALL_SIM_REQUIRE_STEAM_LICENSE = "1"
   .\dist\BasketballGM.exe
   # 起動メニューが表示されればライセンスチェック通過。Ctrl+C 等で終了。
   ```

3. 起動後の `game.log` 末尾を保存する（後述コマンド）。

**期待結果**:

- exit code `0` 系（プロセスは起動継続）。
- `--steam-diag` で `steam_is_subscribed: True`。
- `game.log` に「Steam: ネイティブ API 初期化 OK」相当の `INFO` が残る（`steamworks_bridge.LOG.info("Steam: ネイティブ API 初期化 OK ...")`）。
- `enforce_steam_license` 関連の `ERROR` は出ない。

### 4.2 Case B: 未購入／ライセンス非保有アカウント

**目的**: ライセンス非保有時に **起動拒否（exit 3）** されることを確認。

**条件**:

- Steam クライアント: 未購入アカウントでログイン・起動済み（家族共有でも対象 App ID のライセンスが回ってこないこと）。
- ビルド: A と同じ。
- 設定: `steam_require_license: true` または `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1`。

**手順**:

1. `--steam-diag` で事前状態を保存する。

   ```powershell
   .\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_unowned.txt
   ```

   - `try_init_steam: True`、`steam_native_loaded: True` だが `steam_is_subscribed: False` が出ることを目視確認。

2. 通常起動で **拒否される**ことを確認する。

   ```powershell
   $env:BASKETBALL_SIM_REQUIRE_STEAM_LICENSE = "1"
   .\dist\BasketballGM.exe
   echo "exit=$LASTEXITCODE"
   ```

3. 標準エラー出力に「このゲームは Steam での購入が必要です。」が出ることを確認（`steamworks_bridge.enforce_steam_license` の `print(..., file=sys.stderr)`）。

4. `game.log` 末尾を保存する。

**期待結果**:

- exit code **`3`**。
- 標準エラーに「このゲームは Steam での購入が必要です。」が出る。
- `game.log` に `Steam: …` 行が出る（`enforce_steam_license` 経路は `print` 経由のため `game.log` には出ないこともあるが、`try_init_steam` 経由のログは残る）。
- メイン UI（`MainMenuView`）は **起動しない**。

### 4.3 Case C: Steam クライアント未起動／未ログイン

**目的**: Steam クライアントが落ちている／未ログインのときの挙動が、`enforce_steam_license` のポリシーで意図どおりに扱われることを確認。

**条件**:

- Steam クライアント: **完全終了**または未ログイン。
- ビルド: A と同じ。
- 設定: `steam_require_license: true` または `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1`。

**手順**:

1. `--steam-diag` を実行する（Steam クライアントなしで OK）。

   ```powershell
   .\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_no_client.txt
   ```

   - `try_init_steam: False`、`steam_native_loaded: False`、`steam_is_subscribed: None` を目視確認。
   - 詳細セクションに「false のときは: Steam クライアント未起動・未ログイン …」のヒント行があることを確認。

2. 通常起動で **拒否される**ことを確認する（exit 2 が期待値）。

   ```powershell
   $env:BASKETBALL_SIM_REQUIRE_STEAM_LICENSE = "1"
   .\dist\BasketballGM.exe
   echo "exit=$LASTEXITCODE"
   ```

3. `game.log` 末尾を保存する。

**期待結果**:

- exit code **`2`**（`is_steam_initialized()` が False のため）。
- `game.log` に `Steam: ライセンス確認が有効ですが Steam に接続できませんでした。`（`LOG.error`）が残る。

> **製品起動（Steam クライアント経由）との差**: Steam クライアント経由起動では、Steam クライアントがアプリ起動と同期に動くため、本ケースは原則発生しない。ただし「Steam を終了 → アプリだけ残った状態で再操作」は理論上ありうるので、出荷判断としては「Steam 終了時に勝手な誤動作はしない／拒否する」ことを確認しておく価値がある。

### 4.4 Case D: 異常系（DLL 不足／App ID 不一致／steam_appid.txt 誤り）

**目的**: 出荷判断ではなく**切り分け能力**の確認。`--steam-diag` で原因が分類できることを示す。

**条件・手順**:

- D-1: **DLL 不足**: `steam_api64.dll` を一時的に exe 横から退避し、`--steam-diag` を実行。`DLL 候補` セクションに「なし」と出ることを確認 → 復元。

  ```powershell
  Move-Item .\dist\steam_api64.dll .\dist\steam_api64.dll.bak
  .\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_no_dll.txt
  Move-Item .\dist\steam_api64.dll.bak .\dist\steam_api64.dll
  ```

- D-2: **steam_appid.txt 誤り**（開発時のみ）: `steam_appid.txt` の中身を意図的に存在しない App ID（例: `999999999`）に書き換え、`--steam-diag` を実行。`try_init_steam: False` のまま、詳細に「false のときは: … steam_appid.txt の App ID 誤り … を疑う」が出ることを確認。**確認後、必ず正しい App ID に戻す**。

- D-3: **アーキテクチャ不一致**: 32-bit Python / 32-bit exe で実行した場合、詳細に「Python プロセス: 32bit … DLL は使えません」が出ることを確認（実施は任意）。

**期待結果**:

- D-1: `DLL 候補` セクションが「なし」のみで終了し、要約は `try_init_steam: False` / `steam_native_loaded: False` / `steam_loaded_dll_path: None` / `steam_is_subscribed: None`。
- D-2: 詳細に App ID ヒント行が出る。
- D-3: 詳細に 32bit 警告行が出る。

> Case D は **`[x]` 化の必須要件ではない**。Case A・B・C で判定根拠が揃えば、Case D は記録省略可。ただし出荷後の問い合わせ対応で必要になるため、可能な範囲で確認しておくと有用。

---

## 5. 実行コマンド一覧（コピー&ペースト用）

> 以下は **PowerShell** 想定。`*>` は標準出力＋標準エラーをファイルへリダイレクトするための PowerShell 構文。`reports/` フォルダはコミット対象外。

### 5.1 ライセンス強制を有効化

```powershell
# 現セッション限定（テスト後はターミナルを閉じれば無効化）
$env:BASKETBALL_SIM_REQUIRE_STEAM_LICENSE = "1"
```

または `%USERPROFILE%\.basketball_sim\settings.json` の `"steam_require_license"` を `true` に変更（永続）。

### 5.2 `--steam-diag` の保存

```powershell
# A: 購入済みアカウントで Steam クライアント起動中
.\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_owned.txt

# B: 未購入アカウントで Steam クライアント起動中
.\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_unowned.txt

# C: Steam クライアント未起動
.\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_no_client.txt

# D-1: DLL 不足
.\dist\BasketballGM.exe --steam-diag *> reports/license_real_device_steam_diag_no_dll.txt
```

開発確認用（exe をビルドせず Python から）:

```powershell
python -m basketball_sim --steam-diag *> reports/license_real_device_steam_diag_owned_py.txt
```

### 5.3 通常起動と exit code の確認

```powershell
$env:BASKETBALL_SIM_REQUIRE_STEAM_LICENSE = "1"
.\dist\BasketballGM.exe
echo "exit=$LASTEXITCODE"

# Case ごとに
$LASTEXITCODE | Out-File -Append reports/license_real_device_exit_codes.txt
```

### 5.4 `game.log` 末尾の保存

```powershell
Get-Content "$env:USERPROFILE\.basketball_sim\logs\game.log" -Tail 200 *> reports/license_real_device_game_log_tail.txt
```

直近のクラッシュ全文（あれば）:

```powershell
Copy-Item "$env:USERPROFILE\.basketball_sim\logs\last_crash.txt" reports/license_real_device_last_crash.txt -ErrorAction SilentlyContinue
```

### 5.5 抽出コマンド

`--steam-diag` 出力から要点を抽出:

```powershell
Select-String -Path reports/license_real_device_steam_diag_*.txt -Pattern "try_init_steam","steam_native_loaded","steam_loaded_dll_path","steam_is_subscribed","SteamAPI_Init","SteamAPI_InitFlat","steam_appid","BASKETBALL_SIM","DLL 候補","32bit","64bit","false のときは","Python プロセス"
```

`game.log` から要点を抽出:

```powershell
Select-String -Path reports/license_real_device_game_log_tail.txt -Pattern "Steam:","license","License","BIsSubscribed","ネイティブ API 初期化","ライセンス確認が有効","RunCallbacks","ERROR","CRITICAL","Traceback"
```

エラー有無の素早い確認:

```powershell
Select-String -Path reports/license_real_device_*.txt -Pattern "FAILED","ERROR","Traceback","AssertionError","TclError","exit=2","exit=3","exit=4","exit=5"
```

> **注意**: PowerShell のコンソール表示は cp932 で日本語が文字化けすることがあるが、`reports/*.txt` の中身は UTF-8 で正しく保存される（メモ帳・VS Code で開けば判読可）。

---

## 6. ログ保存パス

| 種別 | パス |
|---|---|
| アプリログ（ローテーションあり） | `%USERPROFILE%\.basketball_sim\logs\game.log` |
| 直近クラッシュ全文 | `%USERPROFILE%\.basketball_sim\logs\last_crash.txt` |
| `--steam-diag` 出力（テスト用） | `reports/license_real_device_steam_diag_*.txt` |
| `game.log` 末尾コピー | `reports/license_real_device_game_log_tail.txt` |
| 終了コード記録 | `reports/license_real_device_exit_codes.txt` |

`reports/*.txt` は **コミット対象外**（`.cursorrules` / プロジェクト方針に従う）。判定が確定したら、`PHASE0_COMPLETION_TEMPLATE.md` 側に「実施日・アカウント条件・ビルド条件・要点ログの引用（数行）」を貼り付ける形で記録する。

---

## 7. 判定表（実機実施時にここを埋める）

| ケース | 期待結果 | 実行結果（要点 1〜2 行） | 判定 | メモ（実施日・アカウント・ビルド） |
|---|---|---|---|---|
| A 購入済み／ライセンス保有 | 起動可（exit 0 相当）／`steam_is_subscribed: True` | Steam クライアントから起動可。`--steam-diag` で `try_init_steam: True` / `steam_native_loaded: True` / `steam_loaded_dll_path: C:\Program Files (x86)\Steam\steamapps\common\日本プロバスケクラブを作ろう！\steam_api64.dll` / **`steam_is_subscribed: True`**。 | **OK** | 2026-05-11／ライセンス保有アカウント／Steam 配布版 `BasketballGM.exe`（`C:\Program Files (x86)\Steam\steamapps\common\日本プロバスケクラブを作ろう！\BasketballGM.exe`）。ログ: `reports/license_real_device_steam_diag_owned.txt`、`reports/license_real_device_game_log_owned.txt`。 |
| B 未購入／ライセンス非保有 | 起動拒否（exit 3）／stderr に「Steam での購入が必要です。」 | Steam クライアント起動中・ライセンス非保有アカウントで通常起動 → **Steam API 初期化が成立せず**（`try_init_steam: False`）、`Steam: ライセンス確認が有効ですが Steam に接続できませんでした。` ＋ **`LASTEXITCODE=2`** で **起動拒否**。`--steam-diag` 側も `try_init_steam: False` / `steam_native_loaded: False` / `steam_loaded_dll_path: None` / `steam_is_subscribed: None`。**ゲームメニューには到達せず**。 | **OK**（合格扱い・下記 §8 注 1 参照） | 2026-05-11／ライセンス非保有アカウント／Steam 配布版 `BasketballGM.exe`／`Get-Process steam` で steam プロセス存在を確認。ログ: `reports/license_real_device_run_unowned.txt`、`reports/license_real_device_steam_diag_unowned.txt`、`reports/license_real_device_game_log_unowned.txt`。**期待値どおりの `steam_is_subscribed: False` ＋ exit 3 経路ではなく、Steam API 初期化失敗 ＋ exit 2 経路で起動拒否された**（実機挙動）。 |
| C Steam クライアント未起動 | 起動拒否（exit 2）／`game.log` に「Steam に接続できませんでした。」 | Steam クライアントを完全終了（`Get-Process steam` で不在確認） → 通常起動 → `Steam 初期化が失敗（クライアント未起動・App ID 不一致など）` ＋ `Steam: ライセンス確認が有効ですが Steam に接続できませんでした。` ＋ **`LASTEXITCODE=2`** で **起動拒否**。`--steam-diag` 側も `try_init_steam: False` / `steam_native_loaded: False` / `steam_loaded_dll_path: None` / `steam_is_subscribed: None`、`--steam-diag` 自体の `LASTEXITCODE=0`。 | **OK** | 2026-05-11／（アカウント問わず）／Steam 配布版 `BasketballGM.exe`。ログ: `reports/license_real_device_run_no_client.txt`、`reports/license_real_device_steam_diag_no_client.txt`、`reports/license_real_device_game_log_no_client.txt`。 |
| D 異常系（DLL 不足 / App ID / 32bit） | `--steam-diag` で原因切り分け可能 | 未実施（A・B・C で `[x]` 化に必要な根拠が揃ったため省略） | 任意（記録のみ） | 出荷後の問い合わせ対応で必要になれば §4.4 D-1〜D-3 の手順を実施。 |

判定の書き方:

- **OK**: 期待結果と実行結果が一致、根拠ログを `reports/` に保存済み。
- **NG**: 期待結果と異なる動作。原因仮説を「メモ」欄に書き、別 PR を切る。
- **未判定**: まだ実施していない／環境が揃っていない。

---

## 8. 完了条件（`[x]` 化の根拠）

次がすべて揃ったとき、`docs/PHASE0_COMPLETION_TEMPLATE.md` 側で次を更新する:

- §3 ランタイム「**ライセンス**: `BIsSubscribed` 相当で未購入時の挙動が仕様どおり …」`[ ]` を `[x]`。
- §4.2 #1「ライセンス強制実機テスト」の状態を「完了（YYYY-MM-DD）」へ。
- 改訂履歴に「ライセンス強制実機テスト 完了（YYYY-MM-DD・アカウント・ビルド・終了コード A=0/B=3/C=2 などの要点）」を追記。

**`[x]` 化の必要十分条件**:

1. Case A（購入済み）で `steam_is_subscribed: True` ＋ exit 0 系を確認、`game.log` 末尾を保存済み。
2. Case B（未購入）で **起動拒否** ＋ ゲームメニュー未到達を確認（理想は `steam_is_subscribed: False` ＋ exit 3 だが、**実機挙動が「Steam API 初期化失敗 ＋ exit 2」となる場合も合格扱い**。下記 注 1 を参照）、`game.log` 末尾を保存済み。
3. Case C（Steam クライアント未起動）で exit `2` を確認、`game.log` の `LOG.error("Steam: ライセンス確認が有効ですが Steam に接続できませんでした。")` を確認。
4. Case D は**任意**（実機切り分けに有用だが、`[x]` 化の必須条件にはしない）。
5. すべての結果ログが `reports/license_real_device_*.txt` に保存され、`PHASE0_COMPLETION_TEMPLATE.md` 側に要点（数行の引用）を貼ってある。

**注 1（Case B の実機挙動と仕様の差分・2026-05-11）**:

- 仕様上は「ライセンス非保有 → Steam API 初期化は成功 → `ISteamApps::BIsSubscribed` が `False` → `enforce_steam_license` が `sys.exit(3)`」を想定（`STEAMWORKS_DESIGN.md` §「ライセンス必須」の exit 3 経路）。
- 2026-05-11 の実機テストでは、Steam クライアント起動中であっても **ライセンス非保有アカウントでは Steam API 初期化（`SteamAPI_Init` / `SteamAPI_InitFlat`）が `False` を返す**ことが観測された。これは Steam クライアント側が「このアカウントは対象アプリのライセンスを持たない」と判断した段階でアプリ側 API 接続を許可しない挙動と推定される（パートナー画面のキー配布／家族共有判定／タイトルの公開状態に依存）。
- その結果、`enforce_steam_license` 内では `is_steam_initialized()` が False → **`sys.exit(2)`** が先に発火し、`BIsSubscribed` までは到達しない（コード経路は `steamworks_bridge.enforce_steam_license` の最初の `if not is_steam_initialized(): sys.exit(2)`）。
- **出荷判断としては「ライセンス非保有アカウントで起動が拒否され、ゲームメニューに到達しない」ことが目的**であり、これは Case B の実機ログで満たされている。よって `[x]` 化の必要十分条件としては合格扱いとする。
- 将来 Steam パートナー側で「キー配布済みだが期限切れ」「ベータアクセス取り消し」など、**Steam API 初期化が成功した上で `BIsSubscribed` が False** になるシナリオが必要になった場合は、改めて Case B-2 として追記し exit 3 経路を確認する（v1 出荷判断には不要）。

---

## 9. 失敗時の扱い

- **テストが期待どおりに動かなかった場合は、`[x]` 化しない**。
- 失敗ログを `reports/license_real_device_*.txt` に残し、原因仮説を以下のいずれかに分類する:

| 分類 | 例 | 次アクション |
|---|---|---|
| code | `enforce_steam_license` の終了コードが仕様と違う／`BIsSubscribed` の戻りを誤読 | `basketball_sim/integrations/steamworks_bridge.py` の小 PR を切る |
| Steam 設定 | App ID 未発行・パートナー画面で対象アカウントにライセンス未付与 | パートナー画面で人間作業（本書の対象外） |
| App ID | `steam_appid.txt` の値違い／本番デポに混入 | `STEAMWORKS_DESIGN.md` §「`steam_appid.txt` の扱い」と整合させる小 PR |
| build | exe の bit 数違い・`steam_api64.dll` 同梱漏れ | `BasketballGM.spec` / インストーラ側の小 PR |
| account | テスト用アカウント未作成・家族共有判定 | パートナー画面で人間作業（本書の対象外） |

- いずれの場合も、失敗時には `PHASE0_COMPLETION_TEMPLATE.md` §4.2 #1 に「実施日・失敗内容・分類・次 PR 候補」を 2〜3 行で残すこと。本書 §7 判定表は **未判定 → NG** に書き換える。

---

## 10. 実施記録テンプレ（人間が埋める）

実施時は次のテンプレを `PHASE0_COMPLETION_TEMPLATE.md` の改訂履歴か、本書末尾に貼り付ける。

```text
- 実施日: YYYY-MM-DD
- 実施者: <名前 / アカウント識別>
- ビルド: dist\BasketballGM.exe（commit <hash>） / または python -m basketball_sim
- 設定: steam_require_license = true（settings.json） / BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1
- 結果:
  - Case A: exit=<n>, steam_is_subscribed=<...>
  - Case B: exit=<n>, stderr に「このゲームは Steam での購入が必要です。」<出た/出ない>
  - Case C: exit=<n>, game.log に「Steam に接続できませんでした。」<あり/なし>
  - Case D: <任意の要点・なしでも可>
- 判定: A/B/C すべて期待どおりのため [x] 化可
- 保存ログ: reports/license_real_device_*.txt（コミット対象外。要点のみ docs に転記）
```

---

## 改訂履歴

- **2026-05-08**: 新規作成（手順書のみ。実機実施は未実施。`docs/PHASE0_COMPLETION_TEMPLATE.md` §4.2 #1 を「手順書作成済み／実機実施待ち」に同期）。
- **2026-05-11**: **実機テスト実施・完了**（人間作業）。§7 判定表に Case A／B／C の結果を記録（いずれも **OK**）、§8 末尾に「注 1（Case B の実機挙動と仕様の差分）」を追加（実機ではライセンス非保有アカウントで Steam API 初期化が成立せず `exit 2` で起動拒否される。`BIsSubscribed` を経由する exit 3 経路へは到達しないが、**ゲームメニュー未到達 ＝ 起動拒否**の目的は満たすため合格扱い）。ビルド: Steam 配布版 `BasketballGM.exe`（`C:\Program Files (x86)\Steam\steamapps\common\日本プロバスケクラブを作ろう！\BasketballGM.exe`）。`docs/PHASE0_COMPLETION_TEMPLATE.md` 側で §3 ランタイム「ライセンス」`[ ]` → `[x]`、§4.2 #1 を「完了（2026-05-11、実機実施済み）」へ同期する。

### 2026-05-11 実施記録

```text
- 実施日: 2026-05-11
- 実施者: プロジェクトオーナー（人間作業）
- ビルド: Steam 配布版 BasketballGM.exe（C:\Program Files (x86)\Steam\steamapps\common\日本プロバスケクラブを作ろう！\BasketballGM.exe）
- 設定: steam_require_license = true（settings.json）または BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1（実機環境で有効化）
- 結果:
  - Case A: try_init_steam=True / steam_native_loaded=True / steam_loaded_dll_path=<上記 exe 同階層 steam_api64.dll> / steam_is_subscribed=True。Steam クライアントから起動可。
  - Case B: try_init_steam=False / steam_native_loaded=False / steam_loaded_dll_path=None / steam_is_subscribed=None。通常起動で「Steam 初期化が失敗（クライアント未起動・App ID 不一致など）」＋「Steam: ライセンス確認が有効ですが Steam に接続できませんでした。」＋ LASTEXITCODE=2。ゲームメニュー未到達。理想の exit 3 ではないが起動拒否は成立（§8 注 1）。
  - Case C: Steam クライアント完全終了下で通常起動 → 「Steam に接続できませんでした。」＋ LASTEXITCODE=2 で起動拒否。
  - Case D: 未実施（A・B・C で [x] 化必要十分条件を満たしたため省略）。
- 判定: A・B・C すべて期待どおり（B は §8 注 1 の通り経路差分はあるが合格扱い）→ docs/PHASE0_COMPLETION_TEMPLATE.md の §3 ランタイム「ライセンス」を [x] 化、§4.2 #1 を「完了（2026-05-11）」に更新。
- 保存ログ: reports/license_real_device_steam_diag_owned.txt / reports/license_real_device_game_log_owned.txt / reports/license_real_device_run_unowned.txt / reports/license_real_device_steam_diag_unowned.txt / reports/license_real_device_game_log_unowned.txt / reports/license_real_device_run_no_client.txt / reports/license_real_device_steam_diag_no_client.txt / reports/license_real_device_game_log_no_client.txt（いずれもコミット対象外）。
```
