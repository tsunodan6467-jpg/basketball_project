# インストーラ・署名スクリプト

- **Inno Setup**: `BasketballGM.iss`（先に PyInstaller で `dist\BasketballGM.exe` を生成）
- **Authenticode**: `sign_windows_release.ps1`

ビルド手順・**リリース前の最短コマンド**（pytest・`--smoke`・exe スモーク）は、リポジトリ直下の **`README.md`**（「単一 exe」「リリース前チェック」節）を参照してください。

**バージョン番号**: リリース時は `BasketballGM.iss` 先頭の `#define MyAppVersion` とルート **`pyproject.toml` の `[project].version`** を同じ値に揃える（出力ファイル名 `BasketballGM_Setup_<version>.exe` と表示に反映される）。
