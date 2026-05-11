# Godot — Phase 4 ホーム／ダッシュボード（読み取り専用プロトタイプ）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。

## 位置づけ

- **第1弾は仮データ（JSON）表示のみ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Python との接続はありません**（子プロセス呼び出し、セーブ読み込み、HTTP/RPC 等は未実装）。
- **`save` 構造・`format_version` / `PAYLOAD_SCHEMA_VERSION` には触れません**。

## 含まれないもの（第1弾）

次の操作・機能は **接続していません**（ボタンや本番導線もありません）。

- 実進行（次ラウンド／オフシーズン実行／次シーズンへ等）
- セーブ / ロード
- 人事・経営・強化・戦術の各操作
- `Offseason.run()` やその他 Python API の呼び出し

## ファイル構成

| パス | 役割 |
|------|------|
| `project.godot` | Godot 4.x プロジェクト設定。メインシーンは `scenes/home_dashboard.tscn` |
| `scenes/home_dashboard.tscn` | ホーム用レイアウト（ラベルのみ） |
| `scripts/home_dashboard.gd` | JSON を読みラベルに流し込むのみ（ロジック判断なし） |
| `data/home_dashboard_mock.json` | 表示用の **架空データ**（正本データではない） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする。
2. Godot エディタで **「プロジェクトをインポート」** ではなく **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーンが開き、`data/home_dashboard_mock.json` が読み込まれれば成功です。

## 将来（第2弾以降の想定）

- Python が **読み取り専用のホーム用 JSON** を生成し、本プロジェクトの `home_dashboard.gd` がその URI を読むように **`_DATA_URIS` / `_active_source_key` だけ** を拡張する想定です。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
