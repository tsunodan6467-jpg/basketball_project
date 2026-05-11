# Godot — Phase 4 ホーム／ダッシュボード（読み取り専用プロトタイプ）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。

## 位置づけ

- **第1弾は仮データ（JSON）表示のみ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Godot から Python を自動起動する処理はありません**（子プロセス呼び出し、HTTP/RPC 等は未実装）。**手動で配置した JSON ファイルだけ**を読みます。
- **`save` 構造・`format_version` / `PAYLOAD_SCHEMA_VERSION` には触れません**。

## 第1弾の到達点（現在）

Phase 4 の Godot ホーム第1弾は、**読み取り専用のプロトタイプ**として次まで完了しています。

- **ホーム → ロスター閲覧**へは、ホーム画面上部の **「ロスター閲覧へ（別画面・読取のみ）」** で片方向遷移（`roster_view.tscn`）。**戻る導線は未実装**のため、ホームへ戻るには **F5 でプロジェクトを再実行**してください。
- **mock JSON**（`res://data/home_dashboard_mock.json`）による表示は、ユーザー環境の **Godot 4.6.2** で確認済み（例: クラブ名「イーストペンギンズ」）。
- **Python が生成した読み取り専用 JSON** を手動で置いたうえでの **優先読込**も、ユーザー環境で確認済み（例: セーブ由来のクラブ名・順位・資金などが表示されること）。
- 読み込みの **優先順**（`scripts/home_dashboard.gd` の `_home_json_candidate_paths`）:
  1. **`res://data/home_dashboard_from_python.json`**（あれば最優先）
  2. **`res://data/home_dashboard_mock.json`**（上記が無い／読めないときのフォールバック）
- 両方とも読めない場合は、画面上に **「データ読込に失敗しました」** と表示する。
- **`home_dashboard_from_python.json` は開発用の生成物**であり、**Git にコミットしない**（`godot/.gitignore` で除外）。

## 含まれないもの（第1弾）

次の操作・機能は **接続していません**（ボタンや本番導線もありません）。

- 実進行（次ラウンド／オフシーズン実行／次シーズンへ等）
- セーブ / ロード
- 人事・経営・強化・戦術の各操作
- `Offseason.run()` やその他 Python API の呼び出し

### まだ未実装であること（明示）

次は **第1弾の範囲外**であり、現時点では実装していません。

- Godot から Python を **自動起動して JSON を生成する**こと
- Godot から **ゲーム進行**すること
- Godot から **セーブ / ロード**すること
- Godot から **人事・経営・強化・戦術**などの操作をすること
- **`Offseason.run()` を Godot から呼ぶ**こと

## ファイル構成

| パス | 役割 |
|------|------|
| `project.godot` | Godot 4.x プロジェクト設定。メインシーンは `scenes/home_dashboard.tscn` |
| `scenes/home_dashboard.tscn` | ホーム用レイアウト（ラベルのみ） |
| `scripts/home_dashboard.gd` | JSON を読みラベルに流し込むのみ（ロジック判断なし） |
| `data/home_dashboard_mock.json` | 表示用の **架空データ**（正本データではない） |
| `data/home_dashboard_from_python.json` | **任意**。Python CLI で生成する開発用 JSON（無ければ mock を読む） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする（本リポジトリでは **Godot 4.6.2** での動作確認実績あり）。
2. Godot エディタで **「プロジェクトをインポート」** ではなく **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーンが開き、下記の優先順で JSON が読み込まれれば成功です。

## ホーム用 JSON の読み込み（手動接続）

`scripts/home_dashboard.gd` は、次の **優先順** で JSON を探します（先に読み取れたものを採用。存在しない場合は次候補へ）。

1. **`res://data/home_dashboard_from_python.json`**（Python CLI で生成した **開発用** ファイル）
2. **`res://data/home_dashboard_mock.json`**（同梱のモック）

どちらも無い／開けない／JSON が壊れている場合は、画面上に **「データ読込に失敗しました」** と表示します。

### Python で生成 JSON を置く（読み取り専用）

リポジトリルート（`basketball_project/`）で実行し、**任意の既存 `.sav` のパス**に `--save` を置き換えてください。

汎用例（パスは環境に合わせて変更）:

```bash
python -m basketball_sim.export.home_dashboard_readonly --save path\to\your.sav --output godot\data\home_dashboard_from_python.json
```

PowerShell の一例（**ファイル名は一例**です。実際はお使いの `.sav` に読み替えてください）:

```powershell
python -m basketball_sim.export.home_dashboard_readonly --save "$env:USERPROFILE\.basketball_sim\saves\debug_user_boost_d1_user_cellb.sav" --output "godot\data\home_dashboard_from_python.json"
```

- 生成物は **開発用** です。**Git にコミットしない**でください（`godot/.gitignore` で `data/home_dashboard_from_python.json` を除外）。
- **まだ Godot から Python を自動起動する段階ではありません**。上記のように CLI を手動実行してから Godot を起動・実行してください。

### 通常の動き

- **`home_dashboard_from_python.json` を置いていない**場合は、従来どおり **`home_dashboard_mock.json`** だけが読まれます。

## 将来（第2弾以降の想定）

- 読み込み候補パスは `home_dashboard.gd` の **`_home_json_candidate_paths`** にまとめてあります。追加・差し替えは主にこの変数を触ります。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
