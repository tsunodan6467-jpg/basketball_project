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

## Steamworks（開発者向け）

Steam 実装の優先度（ライセンス・実績・クラウド要否）、`steam_api64.dll` と `steam_appid.txt` の配置、tkinter とのコールバック統合の考え方は **`basketball_sim/integrations/STEAMWORKS_DESIGN.md`** にまとめています。`steamworks_bridge.py` は **Windows で DLL が見つかり `SteamAPI_Init` が成功したとき** ctypes 実接続し、主画面では約 100ms ごとに `RunCallbacks` を回します。DLL が無い・Init 失敗・`BASKETBALL_SIM_DISABLE_STEAM` では従来どおり影響しません。Steam 販売ビルドでは `%USERPROFILE%\.basketball_sim\settings.json` の `steam_require_license` または `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1` で、未購入時に起動終了するポリシーを有効にできます（詳細は `STEAMWORKS_DESIGN.md` と `steamworks_bridge.py` 先頭コメント）。実績は `unlock_achievement` のみを経由し、API 名は `basketball_sim/config/steam_achievements.py` でダッシュボードと揃えます。**セーブは初回リリースまでローカル（`%USERPROFILE%\.basketball_sim\saves`）のみ**とし、Steam クラウドは `STEAMWORKS_DESIGN.md` の方針どおり将来オプションとして検討します。**Rich Presence（フレンド表示用のプレイ状態）は v1 では未対応**です。**Steam オーバーレイ**はクライアント既定（通常オン）のまま利用可能ですが、tkinter とショートカットが競合する場合は Steam のゲームプロパティでオーバーレイをオフにできる旨は `STEAMWORKS_DESIGN.md` §5 と FAQ たたき台を参照してください。

**EULA・プライバシー**はストア／Steamworks を主に整備する方針で、チェックリストは `STEAMWORKS_DESIGN.md` §6 を参照してください（ゲーム内の同意 UI は現状未実装）。

Steam パートナー画面の**起動に使う実行ファイル名**は、PyInstaller の出力（既定 **`BasketballGM.exe`**）と揃えてください。リネームする場合は `BasketballGM.spec` と `installer/BasketballGM.iss` を同じ名前に更新する旨は **`STEAMWORKS_DESIGN.md`**（「Steam クライアントの起動と実行ファイル名」）にあります。

---

## ライセンス

リポジトリにライセンスファイルが無い場合は、利用条件はリポジトリ所有者の方針に従ってください。
