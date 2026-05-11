# Godot — Phase 4 ホーム／ダッシュボード（読み取り専用プロトタイプ）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。

## 位置づけ

- **第1弾は仮データ（JSON）表示のみ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Godot から Python を自動起動する処理はありません**（子プロセス呼び出し、HTTP/RPC 等は未実装）。**手動で配置した JSON ファイルだけ**を読みます。
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
| `data/home_dashboard_from_python.json` | **任意**。Python CLI で生成する開発用 JSON（無ければ mock を読む） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする。
2. Godot エディタで **「プロジェクトをインポート」** ではなく **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーンが開き、下記の優先順で JSON が読み込まれれば成功です。

## ホーム用 JSON の読み込み（手動接続）

`scripts/home_dashboard.gd` は、次の **優先順** で JSON を探します（先に見つかったものを採用）。

1. **`data/home_dashboard_from_python.json`**（Python CLI で生成した **開発用** ファイル。存在すれば **最優先**）
2. **`data/home_dashboard_mock.json`**（同梱のモック。上記が無いときの既定）

どちらも無い／開けない／JSON が壊れている場合は、画面上に **「データ読込に失敗しました」** と表示します。

### Python で生成 JSON を置く例（読み取り専用）

リポジトリルート（`basketball_project/`）で、**既存の `.sav` のパス**を指定して出力します。

```bash
python -m basketball_sim.export.home_dashboard_readonly --save path\to\your.sav --output godot\data\home_dashboard_from_python.json
```

- 生成物は **開発用** です。**Git にコミットしない**でください（`godot/.gitignore` で `data/home_dashboard_from_python.json` を除外）。
- **まだ Godot から Python を自動起動する段階ではありません**。上記のように CLI を手動実行してから Godot を起動・実行してください。

### 通常の動き

- **`home_dashboard_from_python.json` を置いていない**場合は、従来どおり **`home_dashboard_mock.json`** だけが読まれます。

## 将来（第2弾以降の想定）

- 読み込み候補パスは `home_dashboard.gd` の **`_HOME_JSON_CANDIDATE_PATHS`** にまとめてあります。追加・差し替えは主にこの定数を触ります。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
