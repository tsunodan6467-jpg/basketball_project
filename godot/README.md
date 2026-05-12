# Godot — Phase 4 読み取り専用プロトタイプ（ホーム／ロスター／クラブ史／順位表／日程／施設サマリー／財務サマリー／オーナーミッション／戦術サマリー）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。**本番 GUI の完成ではなく**、読み取り専用の **仮 GUI 足場** を置いています。

## 位置づけ

- **ホーム・ロスター閲覧・クラブ史閲覧・順位表（リーグ状況）閲覧・日程（スケジュール）閲覧・施設サマリー（アリーナ等）閲覧・財務サマリー（経営）閲覧・オーナーミッション / クラブ評価閲覧・戦術 / ローテーションサマリー閲覧**の **9 画面**はいずれも **JSON を読んで表示するだけ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Godot から Python を自動起動する処理はありません**（子プロセス呼び出し、HTTP/RPC 等は未実装）。**手動で配置した JSON ファイルだけ**を読みます。
- **`save` 構造・`format_version` / `PAYLOAD_SCHEMA_VERSION` には触れません**。

## Phase 4 初期の到達点（9画面の足場）

**仮 GUI 導線**として、次まであります（いずれも **画面切替のみ**。進行・保存・契約・トレード・経営・育成・戦術保存・**施設投資・施設レベルアップ**・**予算変更・投資・契約更新（財務）**・**ミッション生成・評価更新・報酬付与（オーナーミッション）**・**戦術変更・ローテーション保存・先発変更・出場時間変更**などの操作は **未接続**）。

- **ホーム**（`scenes/home_dashboard.tscn`）: クラブ状況サマリー。**現在の仮ハブ**（メインシーンは `project.godot` でホームのまま）。
- **ロスター閲覧**（`scenes/roster_view.tscn`）: 現在の編成の表形式閲覧。
- **クラブ史閲覧**（`scenes/club_history_view.tscn`）: 長期プレイの蓄積（履歴）閲覧。
- **順位表（リーグ状況）閲覧**（`scenes/standings_view.tscn`）: D1/D2/D3 の順位表を JSON で閲覧。
- **日程（スケジュール）閲覧**（`scenes/schedule_view.tscn`）: 次戦・今後の予定・進行ヒントなどを JSON で閲覧（**第1弾の読み取り専用表示**。大会別フル・過去結果・本格スケジュール管理は未接続）。
- **施設サマリー閲覧**（`scenes/facility_summary_view.tscn`）: アリーナ・練習施設・メディカル・フロントオフィス・施設強化ポイントなどを JSON で閲覧（**第6画面の第1弾**。現状レベルの表示のみ。**施設投資・レベルアップ・施設プロジェクト制は未接続**）。
- **財務サマリー閲覧**（`scenes/finance_summary_view.tscn`）: 現在資金・前季収支・サラリー状況・財務履歴などを JSON で閲覧（**第7画面の第1弾**。**予算変更・投資・契約更新などの操作は未接続**）。
- **オーナーミッション / クラブ評価閲覧**（`scenes/owner_mission_view.tscn`）: オーナー信頼・今季ミッション・ミッション状態・進捗・報酬/ペナルティ・クラブ評価・注意文などを JSON で閲覧（**第8画面の第1弾**。**ミッション生成・評価更新・報酬付与・オーナー評価の操作は未接続**）。
- **戦術 / ローテーションサマリー閲覧**（`scenes/tactics_summary_view.tscn`）: 戦術プリセット・プレイスタイル・オフェンス/ディフェンス/リバウンド/速攻方針・ローテーション方針・先発数・目標出場時間設定数・選手ロール・注意文などを JSON で閲覧（**第9画面の第1弾**。**戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択 UI は未接続**）。
- **仮ナビ**: ホーム → ロスター → ホーム、ホーム → クラブ史 → ホーム、**ホーム → 順位表 → ホーム**、**ホーム → 日程 → ホーム**、**ホーム → 施設サマリー → ホーム**、**ホーム → 財務サマリー → ホーム**、**ホーム → オーナーミッション → ホーム**、**ホーム → 戦術サマリー → ホーム**（各サブ画面の **閲覧／戻る** はシーン切替のみ）。
- **ホーム内「画面メニュー（読み取り）」カード**: **チーム**（**ロスター**・**戦術サマリー**）／**リーグ**（順位表・日程）／**クラブ**（クラブ史・**施設**）／**経営**（**財務サマリー**・**オーナーミッション**）からも上記閲覧画面へ遷移可能（**HeaderNavRow と併用の二重導線**。本格ナビではない）。**戦術サマリー**・**財務サマリー**・**オーナーミッション**は **HeaderNavRow には載せず**、カードの **チーム** / **経営** 列から遷移します。**経営**列にだけあった補足説明ラベルは削除し、他カテゴリとボタン位置を揃えています（`56bcd9e Godotホーム経営カテゴリの説明文を削除`）。
- **JSON 運用（共通）**: 各画面とも **`*_from_python.json` を優先**し、無い／読めないとき **同梱の `*_mock.json` にフォールバック**（各 `scripts/*.gd` の候補パス配列を参照）。
- **手動生成した次のファイルは Git にコミットしない**（`godot/.gitignore` で除外）:
  - `data/home_dashboard_from_python.json`
  - `data/roster_from_python.json`
  - `data/club_history_from_python.json`
  - `data/standings_from_python.json`
  - `data/schedule_from_python.json`
  - `data/facility_summary_from_python.json`
  - `data/finance_summary_from_python.json`
  - `data/owner_mission_from_python.json`
  - `data/tactics_summary_from_python.json`
- **mock 表示**はユーザー環境の **Godot 4.6.2** で確認済み。**Python 生成 JSON の優先表示**も各画面で確認済み（CLI はリポジトリルートから `python -m basketball_sim.export.*_readonly` を実行し、`godot/data/` へ出力する運用）。

### 財務サマリー（第7画面）のファイル構成（参照）

| 種別 | パス |
|------|------|
| Python export | `basketball_sim/export/finance_summary_readonly.py` |
| pytest | `basketball_sim/tests/test_finance_summary_readonly_export.py` |
| Godot シーン / スクリプト | `scenes/finance_summary_view.tscn` / `scripts/finance_summary_view.gd` |
| スクリプト UID（エディタ） | `scripts/finance_summary_view.gd.uid` |
| 同梱 mock | `data/finance_summary_mock.json` |
| 手動生成 JSON（コミットしない） | `data/finance_summary_from_python.json` |

### 財務サマリーの表示内容（JSON / DTO）

- 現在資金、前季収入・前季支出・前季収支、サラリー上限・選手年俸合計・サラリー余力、財務履歴、注意文（読み取り専用の注記）

### オーナーミッション（第8画面）のファイル構成（参照）

| 種別 | パス |
|------|------|
| Python export | `basketball_sim/export/owner_mission_readonly.py` |
| pytest | `basketball_sim/tests/test_owner_mission_readonly_export.py` |
| Godot シーン / スクリプト | `scenes/owner_mission_view.tscn` / `scripts/owner_mission_view.gd` |
| スクリプト UID（エディタ） | `scripts/owner_mission_view.gd.uid` |
| 同梱 mock | `data/owner_mission_mock.json` |
| 手動生成 JSON（コミットしない） | `data/owner_mission_from_python.json` |

### オーナーミッションの表示内容（JSON / DTO）

- オーナー信頼、今季ミッション、ミッション状態、進捗、報酬 / ペナルティ、クラブ評価、注意文（読み取り専用の注記）

### 読込仕様（オーナーミッション）

- **`owner_mission_from_python.json` を優先**し、無い／読めないとき **`owner_mission_mock.json` にフォールバック**（`owner_mission_view.gd` の候補パス配列）。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。

### 戦術 / ローテーションサマリー（第9画面）のファイル構成（参照）

| 種別 | パス |
|------|------|
| Python export | `basketball_sim/export/tactics_summary_readonly.py` |
| pytest | `basketball_sim/tests/test_tactics_summary_readonly_export.py` |
| Godot シーン / スクリプト | `scenes/tactics_summary_view.tscn` / `scripts/tactics_summary_view.gd` |
| スクリプト UID（エディタ） | `scripts/tactics_summary_view.gd.uid` |
| 同梱 mock | `data/tactics_summary_mock.json` |
| 手動生成 JSON（コミットしない） | `data/tactics_summary_from_python.json` |

### 戦術サマリーの表示内容（JSON / DTO の目安）

- 戦術プリセット、プレイスタイル、オフェンステンポ、オフェンス傾向、オフェンス組み立て、ディフェンス方針、リバウンド方針、速攻方針、ローテーション方針、先発設定数、目標出場時間設定数、選手ロール（先発/控え・役割・目標出場時間など）、注意文（読み取り専用の注記）

### 読込仕様（戦術サマリー）

- **`tactics_summary_from_python.json` を優先**し、無い／読めないとき **`tactics_summary_mock.json` にフォールバック**（`tactics_summary_view.gd` の候補パス配列）。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。

### 確認済み（ユーザー環境 Godot 4.6.2 の目安）

- ホーム → 戦術サマリー → ホーム、ホーム → オーナーミッション → ホーム、**既存8画面往復**、**HeaderNavRow 未変更**（戦術サマリーは **チーム** カード列のみ）、`from_python` 優先・mock フォールバック、**UID 参照エラー解消**、実行後の不要な追跡差分なし、など。

### Phase 4 ロードマップ上の位置（手元メモ）

```txt
◎ 基盤完成
★ Phase 4 / Godot本番GUI準備
  ◎ ホーム第1画面
  ◎ ロスター第2画面
  ◎ クラブ史第3画面
  ◎ 順位表 / リーグ状況 第4画面
  ◎ 日程 / スケジュール 第5画面
  ◎ 施設 / アリーナ / 練習環境サマリー 第6画面
  ◎ 財務 / 経営サマリー 第7画面
  ◎ オーナーミッション / クラブ評価 第8画面
  ◎ 戦術 / ローテーションサマリー 第9画面
  ◎ 9画面のPython readonly DTO / JSON足場
  ◎ 9画面のGodot mock表示
  ◎ Python生成JSON優先読込
  ◎ ホームカード型メニュー経由の遷移
  ◎ README/docs 9画面到達点更新
□ Python自動起動設計
□ 本格ナビ次段階
□ Godot本番GUI一本化
□ グラフィック・音楽などの演出実装
□ 完成・ブラッシュアップ・公開準備
□ リリース・販売展開
```

## 含まれないもの（Phase 4 初期の範囲外）

次の操作・機能は **接続していません**。

- 実進行（次ラウンド／オフシーズン実行／次シーズンへ等）
- セーブ / ロード
- 人事・経営・強化・戦術の各操作（**財務の予算変更・投資・契約更新を含む**）
- `Offseason.run()` やその他 Python API の呼び出し

### まだ未実装であること（明示）

- Godot から Python を **自動起動して JSON を生成する**こと
- Godot から **ゲーム進行**すること
- Godot から **セーブ / ロード**すること
- Godot から **人事・経営・強化・戦術**や **施設投資・施設レベルアップ**などの操作をすること
- **`Offseason.run()` を Godot から呼ぶ**こと
- **本格ナビゲーション**（左メニュー統合・画面管理の一本化など）
- **財務画面・オーナーミッション画面・戦術サマリー画面の本格ビジュアル調整**（現状は読み取りプロトタイプ優先）
- **ミッション生成・評価更新・報酬付与・オーナー評価の操作 UI**
- **戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択 UI**
- **Godot 本番 GUI の一本化**

## ファイル構成（抜粋）

| パス | 役割 |
|------|------|
| `project.godot` | Godot 4.x プロジェクト設定。メインシーンは `scenes/home_dashboard.tscn` |
| `scenes/home_dashboard.tscn` / `scripts/home_dashboard.gd` | ホームレイアウト・JSON 表示 |
| `scenes/roster_view.tscn` / `scripts/roster_view.gd` | ロスター閲覧・JSON 表示 |
| `scenes/club_history_view.tscn` / `scripts/club_history_view.gd` | クラブ史閲覧・JSON 表示 |
| `scenes/standings_view.tscn` / `scripts/standings_view.gd` | 順位表（リーグ状況）閲覧・JSON 表示 |
| `scenes/schedule_view.tscn` / `scripts/schedule_view.gd` | 日程（スケジュール）閲覧・JSON 表示 |
| `scenes/facility_summary_view.tscn` / `scripts/facility_summary_view.gd` | 施設サマリー閲覧・JSON 表示 |
| `scenes/finance_summary_view.tscn` / `scripts/finance_summary_view.gd` | 財務サマリー閲覧・JSON 表示 |
| `scenes/owner_mission_view.tscn` / `scripts/owner_mission_view.gd` | オーナーミッション閲覧・JSON 表示 |
| `scenes/tactics_summary_view.tscn` / `scripts/tactics_summary_view.gd` | 戦術 / ローテーションサマリー閲覧・JSON 表示 |
| `data/home_dashboard_mock.json` 等 | 各画面の **同梱モック**（正本データではない） |
| `data/*_from_python.json` | **任意**。CLI で生成する開発用 JSON（無ければ mock） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする（本リポジトリでは **Godot 4.6.2** での動作確認実績あり）。
2. Godot エディタで **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーン（ホーム）が開き、各画面の **優先順** で JSON が読み込まれれば成功です。
4. ロスター／クラブ史／**順位表**／**日程**／**施設サマリー**／**財務サマリー**／**オーナーミッション**／**戦術サマリー**からホームへ戻るときは、各画面上部の **「ホームへ戻る（表示のみ）」** を使います（ホームへ戻る目的でプロジェクト全体を再実行する必要はありません）。

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

**ロスター**・**クラブ史**・**順位表**・**日程**・**施設サマリー**・**財務サマリー**・**オーナーミッション**・**戦術サマリー**も同様に、`basketball_sim.export.roster_readonly` / `club_history_readonly` / **`standings_readonly`** / **`schedule_readonly`** / **`facility_summary_readonly`** / **`finance_summary_readonly`** / **`owner_mission_readonly`** / **`tactics_summary_readonly`** で `godot/data/roster_from_python.json` / `club_history_from_python.json` / **`standings_from_python.json`** / **`schedule_from_python.json`** / **`facility_summary_from_python.json`** / **`finance_summary_from_python.json`** / **`owner_mission_from_python.json`** / **`tactics_summary_from_python.json`** を生成して配置します（**まだ Godot から自動実行しません**）。

財務サマリーは履歴件数を変える場合: `--max-history 8` など（既定 5）。戦術サマリーは選手ロール表示件数など: `--max-players 8` など（エクスポート CLI のヘルプを参照）。

- 生成物は **開発用** です。**Git にコミットしない**でください（上記 **9** 種の `*_from_python.json` は `godot/.gitignore` で除外）。

### 通常の動き

- **`*_from_python.json` を置いていない**場合は、従来どおり **同梱の `*_mock.json`** が読まれます。

## 将来（第2弾以降の想定）

- 読み込み候補パスは各 `scripts/*.gd` の **候補パス配列**にまとめてあります。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 / **§15（Phase 4 初期プロトタイプ到達点）** を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
