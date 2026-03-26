# インストーラ・署名スクリプト

- **Inno Setup**: `BasketballGM.iss`（先に PyInstaller で `dist\BasketballGM.exe` を生成）
- **Authenticode**: `sign_windows_release.ps1`

ビルド手順・**リリース前の最短コマンド**（pytest・`--smoke`・exe スモーク）は、リポジトリ直下の **`README.md`**（「単一 exe」「リリース前チェック」節）を参照してください。

**バージョン番号**: リリース時は `BasketballGM.iss` 先頭の `#define MyAppVersion` とルート **`pyproject.toml` の `[project].version`** を同じ値に揃える（出力ファイル名 `BasketballGM_Setup_<version>.exe` と表示に反映される）。

**Steam へのアップロード（SteamPipe）**: デポの作成・初回ビルド・コンテンツルートの考え方は **`basketball_sim/integrations/STEAMWORKS_DESIGN.md`** の「Steam デポ」と「Steamworks パートナーでのデポ・初回ビルド（チェックリスト）」を参照する（パートナー画面での作業）。

## GitHub Release（配布物の添付）

1. ローカルで PyInstaller（および必要なら Inno・署名）を実行し、`dist\BasketballGM.exe` などを用意する。`--smoke` で動作確認してからアップロードすると安全です。
2. GitHub リポジトリの **Releases** → **Draft a new release** を開く。
3. **Choose a tag** で `v0.1.0` など、既に `git push` 済みのタグを選ぶ（タグが無い場合は画面の指示で作成してもよい）。
4. リリースタイトル・説明文（変更点・既知の問題）を記入する。
5. **Release 資産（Assets）** に、次をドラッグ＆ドロップで添付する。
   - **`BasketballGM.exe`** … `dist\` にある単体 exe（ポータブル配布向け）
   - （任意）**`BasketballGM_Setup_<version>.exe`** … Inno で生成したインストーラ
6. **Publish release** で公開する。

**注意**: `.gitignore` で `dist/` を除外しているため、**exe はリポジトリにコミットせず**、上記のように Release へ手動添付する運用が基本です。リリースのたびにローカルまたは信頼できるビルド環境で生成したバイナリを使ってください。CI から Release へ自動アップロードする場合は、別途 workflow とシークレット（署名鍵など）の設計が必要です。
