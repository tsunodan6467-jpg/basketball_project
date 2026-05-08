# 国内バスケ GM シミュレーション（開発中）

Python 製のプロバスケクラブ運営シミュレーションです。リポジトリのコードは主に `basketball_sim/` にあります。

## 必要環境

- Python **3.10 以上**
- 標準ライブラリ＋**tkinter**（Windows の公式インストーラ版 Python に同梱）

ランタイム用の追加 pip パッケージはありません（`pyproject.toml` の `dependencies` は空です）。

## Git（任意）

[Git for Windows](https://git-scm.com/download/win) を入れ、**まだリポジトリでない場合のみ**プロジェクトルートで `git init` を実行します（既に `.git` がある場合は不要）。ルートの **`.gitignore`** に `/dist/` と `/build/`（PyInstaller の出力）が含まれているため、これらはコミット対象になりません。

確認例（ビルド済みで `dist\` がある状態）:

```bash
git status
git check-ignore -v dist/BasketballGM.exe
```

`dist` や `build` が**未追跡ファイルとして一覧に出ない**こと、および `check-ignore` で `.gitignore` の行に紐づくことを確認できます。ターミナルで `git` が見つからない場合は、Git のインストール後にウィンドウを開き直すか、PATH に `Git\bin` を追加してください。

## ソースから起動

リポジトリのルートで:

```bash
pip install -e .
basketball-sim
```

または:

```bash
python -m basketball_sim
```

対話なしの土台検証（CI・`basketball_sim.main` 直実行と同じ経路）:

```bash
python -m basketball_sim --smoke
```

同等: `python -m basketball_sim.main --smoke`

Steam 連携の診断（DLL 検出・Init・BIsSubscribed の状態確認）:

```bash
python -m basketball_sim --steam-diag
```

開発用テスト:

```bash
pip install -e ".[dev]"
python -m pytest basketball_sim/tests -q
```

## 単一 exe（PyInstaller）

プロジェクトルートで:

```bash
pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm BasketballGM.spec
```

成果物は `dist/BasketballGM.exe` です。ビルド後のスモークは `dist\BasketballGM.exe --smoke` で確認できます（終了コード 0・標準出力に `smoke ok`）。

#### リリース前チェック（最短コマンド）

ソース環境で次を通す（GitHub Actions の `pytest` と CLI スモークに相当）:

```bash
pip install -e ".[dev]"
python -m pytest basketball_sim/tests -q
python -m basketball_sim --smoke
```

単一 exe をビルドしたあとは、同じく非対話で:

```bash
dist\BasketballGM.exe --smoke
```

#### GitHub Actions の Artifact から exe を確認（初心者向け）

GitHub 上で自動ビルドされた exe を手元で確認したい場合:

1. GitHub の Actions で最新の CI 実行を開く（例: リポジトリの「Actions」タブ）。
2. 画面下の **Artifacts** から `BasketballGM-windows-exe` をダウンロードして zip を展開。
3. 展開したフォルダの空白を **Shift+右クリック** → **「ターミナルをここで開く」**（または PowerShell）。
4. （任意・推奨）改ざん検知のため、同梱の `BasketballGM.exe.sha256.txt` と照合:

```powershell
Get-FileHash -Algorithm SHA256 .\BasketballGM.exe
Get-Content .\BasketballGM.exe.sha256.txt
```

出力された SHA256 は **大文字/小文字が違っても同じ値**です（内容が一致していればOK）。

5. 次を実行して `smoke ok` が出れば成功:

```powershell
.\BasketballGM.exe --smoke
```

6. （任意）Steam 連携の診断も同じ exe で実行できる（本人確認待ちでもOK）:

```powershell
.\BasketballGM.exe --steam-diag
```

**SmartScreen が出た場合**: 「詳細情報」→「実行」で続行できます（未署名 exe のため、開発中は出ることがあります）。

#### GitHub Release（配布 exe の添付）

`git tag`（例: `v0.1.0`）をプッシュしたあと、GitHub の **Releases** にビルドした `dist\BasketballGM.exe` や Inno のセットアップ exe を **Release 資産**として添付する手順は、**`installer/README.md`** の「GitHub Release」を参照してください（`dist/` は `.gitignore` 対象のため、バイナリはコミットせず Release へアップロードする想定です）。

### Windows インストーラ（Inno Setup・任意）

配布用のセットアップ exe を作る場合:

1. [Inno Setup 6](https://jrsoftware.org/isdl.php) をインストール（ウィザード言語に日本語を使う場合、同梱の `Japanese.isl` が使われます）。
2. 上記のとおり **`dist\BasketballGM.exe` を先にビルド**する。
3. 次のいずれかで `installer\BasketballGM.iss` をコンパイルする。
   - Inno Setup Compiler で `installer\BasketballGM.iss` を開き、メニューからコンパイル。
   - コマンド例:  
     `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\BasketballGM.iss`  
     （インストール先が異なる場合は `ISCC.exe` のパスを読み替えてください。）

出力は `dist\BasketballGM_Setup_0.1.0.exe` です（バージョンは `installer\BasketballGM.iss` 先頭の `#define MyAppVersion` と `pyproject.toml` を揃えると管理しやすいです）。

インストーラの内容（最小構成）:

- インストール先の既定: `%LOCALAPPDATA%\Programs\BasketballGM`（管理者権限不要）
- スタートメニュー: ゲーム本体＋「ユーザーデータフォルダを開く（`.basketball_sim`）」
- オプション: デスクトップショートカット
- 終了時: ゲーム起動（サイレントインストール時はスキップ）

`Japanese.isl` が見つからずコンパイルに失敗する場合は、`BasketballGM.iss` の `[Languages]` から `japanese` の行を外し、`english` のみにしてください。

### コード署名（Authenticode・任意・配布品質）

**目的**: 実行ファイルにデジタル署名を付け、Windows の SmartScreen や警告表示を**商用 CA の証明書**では緩和しやすくする（完全に消える保証はありません）。**自己署名だけ**では一般ユーザーの PC では警告が残りがちです。

**用意するもの**

- CA から発行された **コード署名用証明書**（PFX、またはハードウェアトークン＋別手順）
- **Windows SDK** に含まれる `signtool.exe`（典型的なパス: `Program Files (x86)\Windows Kits\10\bin\<バージョン>\x64\signtool.exe`）

**推奨フロー（リポジトリ同梱スクリプト）**

1. PyInstaller で `dist\BasketballGM.exe` をビルドする。  
2. 環境変数 `SIGNTOOL_PFX_PASSWORD` に PFX のパスワードを設定する（**コミット禁止**）。  
3. ゲーム本体に署名:  
   `powershell -ExecutionPolicy Bypass -File installer\sign_windows_release.ps1 -TargetPath dist\BasketballGM.exe -PfxPath <PFX のパス>`  
4. Inno Setup でインストーラをビルドする。  
5. 生成された `dist\BasketballGM_Setup_*.exe` に同じスクリプトで再度署名する。

タイムスタンプ URL はスクリプト既定で DigiCert（`/tr` RFC3161）を使用しています。CA の案内に従い、利用可能なタイムスタンプサーバーに差し替えてください。

**GitHub Actions でのメモ（自動ビルド時）**

- PFX を **リポジトリに含めない**。Base64 化したバイナリを **Encrypted secret**（例: `WINDOWS_PFX_BASE64`）に保存し、ジョブ内でファイルに復号して `signtool` を実行するのが一般的です。パスワードは別シークレット（例: `WINDOWS_PFX_PASSWORD`）に分ける。  
- `windows-latest` ランナーに Windows SDK が入っているため `signtool` のパスを `Get-ChildItem` 等で解決するか、本リポジトリの `installer\sign_windows_release.ps1` と同様の探索ロジックを流用できます。  
- 公開リポジトリではシークレットの利用権限（環境保護ルール）に注意してください。

公式リファレンス: [SignTool](https://learn.microsoft.com/windows/win32/seccrypto/signtool)（Microsoft Learn）

---

## ユーザーデータの保存場所

**ソース実行でも exe でも同じ**です。OS のユーザーフォルダ下にまとまります。

| 種類 | 場所（Windows の例） |
|------|----------------------|
| **設定** | `%USERPROFILE%\.basketball_sim\settings.json` |
| **セーブ** | `%USERPROFILE%\.basketball_sim\saves\`（`.sav` など） |
| **ログ** | `%USERPROFILE%\.basketball_sim\logs\game.log`（ローテーションあり） |
| **直近のクラッシュ全文** | `%USERPROFILE%\.basketball_sim\logs\last_crash.txt` |

エクスプローラーのアドレスバーに `%USERPROFILE%\.basketball_sim` と入力するとフォルダを開けます。

- ログの詳しさは `settings.json` の `log_level`、または環境変数 `BASKETBALL_SIM_LOG_LEVEL` で変更できます（後者が優先）。

### 不具合報告・問い合わせ用（添付すると助かるもの）

1. `logs\last_crash.txt`（クラッシュ直後に生成・更新されていれば）  
2. 可能なら `logs\game.log` の**直近数十行〜全体**（サイズが大きい場合は末尾のみでも可）  
3. 再現手順と、使用したのが **exe かソースか**、おおまかな OS バージョン  

セーブで再現する場合のみ、該当する `.sav` の共有を検討してください（個人情報は含みませんが、プレイ内容は含みます）。

---

## Steam 版を遊ぶ前に（ユーザー向け）

> **状況の前提**: 本ゲームは **開発中**のプロジェクトであり、現行 v1 方針では **Steam クラウドセーブと Rich Presence は対象外**です。Steam ストアでの一般公開・発売前後で挙動が変わる可能性があるため、本節は**現時点（v1）の運用**を案内するものです。

### A. Steam クライアントからの起動

- **想定**: Steam クライアントから本ゲームを起動する形を想定しています（販売ビルドの場合）。
- **Steamworks 機能（実績・ライセンスチェック・診断ログなど）は、Steam クライアントが起動中で、かつ DLL とアプリ ID の組み合わせが揃っている環境でのみ有効**になります。Steam クライアントを介さずに直接 exe を起動した場合は、これらの機能は無効として扱われます（ゲーム本体の起動・セーブ・ロードは可能）。
- **`steam_appid.txt` を exe と同階層に置く運用**は、開発・検証時のみのオプションです。Steam パートナー画面で正式に配信する場合の取り扱いは `basketball_sim/integrations/STEAMWORKS_DESIGN.md` を参照してください。
- **SmartScreen が出たとき**: 未署名 exe の場合、初回起動時に SmartScreen が表示されることがあります。「詳細情報」→「実行」で続行できます（コード署名済みのリリースでは出にくくなります）。

### B. セーブはローカル PC 保存（Steam クラウド非対応）

- **v1 ではセーブデータは Steam クラウドに同期されません**。すべて**お使いの PC のローカル**に保存されます。
- 既定の保存先（Windows）:

| 種類 | 場所 |
|------|------|
| 設定 | `%USERPROFILE%\.basketball_sim\settings.json` |
| セーブ | `%USERPROFILE%\.basketball_sim\saves\<スロット名>.sav` |
| ログ | `%USERPROFILE%\.basketball_sim\logs\game.log`（ローテーションあり） |
| クラッシュ全文 | `%USERPROFILE%\.basketball_sim\logs\last_crash.txt` |

- 既定スロット名は `quicksave` で、ファイル名は `quicksave.sav` になります（pickle 形式）。
- エクスプローラーのアドレスバーに `%USERPROFILE%\.basketball_sim` と入力するとフォルダを開けます。
- **Steam クラウドや OneDrive 等の自動同期に依存しない前提**で運用してください（クラウドセーブは将来オプションとして検討されていますが、v1 では未対応です）。

### C. バックアップ（PC 移行・再インストール前）

- **PC を買い替える／OS を再インストールする／ゲームをアンインストールする前**には、手動でバックアップを取ることを推奨します。
- バックアップ手順（推奨）:
  1. **ゲームを終了する**（プレイ中・セーブ書き込み中のバックアップは破損リスクがあるため）。
  2. エクスプローラーで `%USERPROFILE%\.basketball_sim` フォルダを開く。
  3. **`saves\` フォルダ全体**を別ドライブやクラウドストレージにコピーする（手動アップロード）。
  4. （任意）`settings.json` も合わせてコピーすると、設定もそのまま引き継げます。
- 復元したいときは、新しい PC の同じ場所（`%USERPROFILE%\.basketball_sim\saves\`）にコピーすれば認識されます。
- **バックアップ前にゲームを終了**すること、および **書き込み途中の `*.sav.tmp` ファイルはバックアップ対象から除外**してください（途中状態のため）。

### D. トラブルシュート（よくある状況）

| 症状 | まず確認すること |
|------|-----------------|
| **セーブが見つからない** | エクスプローラーで `%USERPROFILE%\.basketball_sim\saves\` を開き、`*.sav` ファイルがあるかを確認。誤って `.basketball_sim` フォルダを削除していないか、別ユーザーアカウントでプレイしていないかを確認。 |
| **起動できない** | `%USERPROFILE%\.basketball_sim\logs\game.log` の末尾と `last_crash.txt` を確認。`game.log` が無い場合は、フォルダ作成権限・アンチウイルスのブロックを疑う。 |
| **Steamworks 機能（実績など）が反応しない** | Steam クライアントがログイン状態で起動しているかを確認。`BasketballGM.exe --steam-diag` を実行し、`try_init_steam: True` が出るかを確認（`False` のままの場合は DLL 同梱・App ID・Steam クライアント条件が揃っていない）。 |
| **実績が反映されない** | `--steam-diag` で初期化成功を確認したうえで、実績解除条件を満たしたかをゲーム内で再確認。Steam パートナー画面の実績設定と API 名（`basketball_sim/config/steam_achievements.py`）が一致している必要があります（**開発者向け**）。 |
| **ログが必要** | 不具合報告時は `%USERPROFILE%\.basketball_sim\logs\last_crash.txt` と、可能なら `game.log` の末尾を添付してください（前述の「不具合報告・問い合わせ用」を参照）。 |

### E. v1 対象外機能（決定事項）

- **Steam クラウドセーブ**: v1 では対象外です（2026-04-05 決定）。セーブは PC ローカルのみ。将来アップデートで対応する可能性はありますが、現時点では予定を確約しません。
- **Rich Presence（フレンドへの「現在のプレイ状態」表示）**: v1 では未実装です（2026-04-05 決定）。
- これらの方針は `docs/PHASE0_COMPLETION_TEMPLATE.md` および `basketball_sim/integrations/STEAMWORKS_DESIGN.md` と整合します。

> **更新時の注意**: 本節の保存先・拡張子・既定スロット名は実装（`basketball_sim/utils/paths.py` / `basketball_sim/persistence/save_load.py`）に基づいています。実装が変わった場合は、本節と `docs/PHASE0_COMPLETION_TEMPLATE.md` の「セーブ・設定」節を同時に更新してください。

---

## Steamworks（開発者向け）

Steam 実装の優先度（ライセンス・実績・クラウド要否）、`steam_api64.dll` と `steam_appid.txt` の配置、tkinter とのコールバック統合の考え方は **`basketball_sim/integrations/STEAMWORKS_DESIGN.md`** にまとめています。`steamworks_bridge.py` は **Windows で DLL が見つかり `SteamAPI_Init` が成功したとき** ctypes 実接続し、主画面では約 100ms ごとに `RunCallbacks` を回します。DLL が無い・Init 失敗・`BASKETBALL_SIM_DISABLE_STEAM` では従来どおり影響しません。Steam 販売ビルドでは `%USERPROFILE%\.basketball_sim\settings.json` の `steam_require_license` または `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1` で、未購入時に起動終了するポリシーを有効にできます（詳細は `STEAMWORKS_DESIGN.md` と `steamworks_bridge.py` 先頭コメント）。実績は `unlock_achievement` のみを経由し、API 名は `basketball_sim/config/steam_achievements.py` でダッシュボードと揃えます。**セーブは初回リリースまでローカル（`%USERPROFILE%\.basketball_sim\saves`）のみ**とし、Steam クラウドは `STEAMWORKS_DESIGN.md` の方針どおり将来オプションとして検討します。**Rich Presence（フレンド表示用のプレイ状態）は v1 では未対応**です。**Steam オーバーレイ**はクライアント既定（通常オン）のまま利用可能ですが、tkinter とショートカットが競合する場合は Steam のゲームプロパティでオーバーレイをオフにできる旨は `STEAMWORKS_DESIGN.md` §5 と FAQ たたき台を参照してください。

**EULA・プライバシー**はストア／Steamworks を主に整備する方針で、チェックリストは `STEAMWORKS_DESIGN.md` §6 を参照してください（ゲーム内の同意 UI は現状未実装）。

Steam パートナー画面の**起動に使う実行ファイル名**は、PyInstaller の出力（既定 **`BasketballGM.exe`**）と揃えてください。リネームする場合は `BasketballGM.spec` と `installer/BasketballGM.iss` を同じ名前に更新する旨は **`STEAMWORKS_DESIGN.md`**（「Steam クライアントの起動と実行ファイル名」）にあります。

---

## ライセンス

リポジトリにライセンスファイルが無い場合は、利用条件はリポジトリ所有者の方針に従ってください。
