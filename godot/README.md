# Godot — Phase 4 読み取り専用プロトタイプ（ホーム／ロスター／クラブ史）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。**本番 GUI の完成ではなく**、読み取り専用の **仮 GUI 足場** を置いています。

## 位置づけ

- **ホーム・ロスター閲覧・クラブ史閲覧**の 3 画面はいずれも **JSON を読んで表示するだけ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Godot から Python を自動起動する処理はありません**（子プロセス呼び出し、HTTP/RPC 等は未実装）。**手動で配置した JSON ファイルだけ**を読みます。
- **`save` 構造・`format_version` / `PAYLOAD_SCHEMA_VERSION` には触れません**。

## Phase 4 初期の到達点（3画面の足場）

**仮 GUI 導線**として、次まであります（いずれも **画面切替のみ**。進行・保存・契約・トレード・経営・育成・戦術保存などの操作は **未接続**）。

- **ホーム**（`scenes/home_dashboard.tscn`）: クラブ状況サマリー。**現在の仮ハブ**（メインシーンは `project.godot` でホームのまま）。
- **ロスター閲覧**（`scenes/roster_view.tscn`）: 現在の編成の表形式閲覧。
- **クラブ史閲覧**（`scenes/club_history_view.tscn`）: 長期プレイの蓄積（履歴）閲覧。
- **仮ナビ**: ホーム → ロスター → ホーム、ホーム → クラブ史 → ホーム（各画面の **閲覧／戻る** ボタンはシーン切替のみ）。
- **JSON 運用（共通）**: 各画面とも **`*_from_python.json` を優先**し、無い／読めないとき **同梱の `*_mock.json` にフォールバック**（各 `scripts/*.gd` の候補パス配列を参照）。
- **手動生成した次のファイルは Git にコミットしない**（`godot/.gitignore` で除外）:
  - `data/home_dashboard_from_python.json`
  - `data/roster_from_python.json`
  - `data/club_history_from_python.json`
- **mock 表示**はユーザー環境の **Godot 4.6.2** で確認済み。**Python 生成 JSON の優先表示**も各画面で確認済み（CLI はリポジトリルートから `python -m basketball_sim.export.*_readonly` を実行し、`godot/data/` へ出力する運用）。

## 含まれないもの（Phase 4 初期の範囲外）

次の操作・機能は **接続していません**。

- 実進行（次ラウンド／オフシーズン実行／次シーズンへ等）
- セーブ / ロード
- 人事・経営・強化・戦術の各操作
- `Offseason.run()` やその他 Python API の呼び出し

### まだ未実装であること（明示）

- Godot から Python を **自動起動して JSON を生成する**こと
- Godot から **ゲーム進行**すること
- Godot から **セーブ / ロード**すること
- Godot から **人事・経営・強化・戦術**などの操作をすること
- **`Offseason.run()` を Godot から呼ぶ**こと
- **本格ナビゲーション**（左メニュー統合・画面管理の一本化など）

## ファイル構成（抜粋）

| パス | 役割 |
|------|------|
| `project.godot` | Godot 4.x プロジェクト設定。メインシーンは `scenes/home_dashboard.tscn` |
| `scenes/home_dashboard.tscn` / `scripts/home_dashboard.gd` | ホームレイアウト・JSON 表示 |
| `scenes/roster_view.tscn` / `scripts/roster_view.gd` | ロスター閲覧・JSON 表示 |
| `scenes/club_history_view.tscn` / `scripts/club_history_view.gd` | クラブ史閲覧・JSON 表示 |
| `data/home_dashboard_mock.json` 等 | 各画面の **同梱モック**（正本データではない） |
| `data/*_from_python.json` | **任意**。CLI で生成する開発用 JSON（無ければ mock） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする（本リポジトリでは **Godot 4.6.2** での動作確認実績あり）。
2. Godot エディタで **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーン（ホーム）が開き、各画面の **優先順** で JSON が読み込まれれば成功です。

## ホーム用 JSON の読み込み（手動接続）

`scripts/home_dashboard.gd` は、次の **優先順** で JSON を探します。

1. **`res://data/home_dashboard_from_python.json`**
2. **`res://data/home_dashboard_mock.json`**

どちらも無い／開けない／JSON が壊れている場合は、画面上に **「データ読込に失敗しました」** と表示します。

### Python で生成 JSON を置く（読み取り専用）

リポジトリルート（`basketball_project/`）で実行し、**任意の既存 `.sav` のパス**に `--save` を置き換えてください。

```bash
python -m basketball_sim.export.home_dashboard_readonly --save path\to\your.sav --output godot\data\home_dashboard_from_python.json
```

PowerShell の一例（パスは環境に合わせて読み替え）:

```powershell
python -m basketball_sim.export.home_dashboard_readonly --save "$env:USERPROFILE\.basketball_sim\saves\debug_user_boost_d1_user_cellb.sav" --output "godot\data\home_dashboard_from_python.json"
```

**ロスター**・**クラブ史**も同様に、`basketball_sim.export.roster_readonly` / `basketball_sim.export.club_history_readonly` で `godot/data/roster_from_python.json` / `godot/data/club_history_from_python.json` を生成して配置します（**まだ Godot から自動実行しません**）。

- 生成物は **開発用** です。**Git にコミットしない**でください（上記 3 ファイルは `godot/.gitignore` で除外）。

### 通常の動き

- **`*_from_python.json` を置いていない**場合は、従来どおり **同梱の `*_mock.json`** が読まれます。

## 将来（第2弾以降の想定）

- 読み込み候補パスは各 `scripts/*.gd` の **候補パス配列**にまとめてあります。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 / **§15（Phase 4 初期プロトタイプ到達点）** を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
