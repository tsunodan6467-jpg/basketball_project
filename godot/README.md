# Godot — Phase 4 読み取り専用プロトタイプ（ホーム／ロスター／クラブ史／順位表／日程／施設サマリー／財務サマリー／オーナーミッション／戦術サマリー／契約・人事サマリー）

このフォルダは **Phase 4 / Godot 本番 GUI 実装準備** 用の **最小 Godot プロジェクト** です。**本番 GUI の完成ではなく**、読み取り専用の **仮 GUI 足場** を置いています。

## 位置づけ

- **ホーム・ロスター閲覧・クラブ史閲覧・順位表（リーグ状況）閲覧・日程（スケジュール）閲覧・施設サマリー（アリーナ等）閲覧・財務サマリー（経営）閲覧・オーナーミッション / クラブ評価閲覧・戦術 / ローテーションサマリー閲覧・契約 / 人事サマリー閲覧**の **10 画面**はいずれも **JSON を読んで表示するだけ**です。ゲームの正本ロジックは **Python 側の `basketball_sim/`** にあり、このプロジェクトでは **再実装しません**。
- **Godot から Python を自動起動する処理はありません**（子プロセス呼び出し、HTTP/RPC 等は未実装）。**手動で配置した JSON ファイルだけ**を読みます。
- **`save` 構造・`format_version` / `PAYLOAD_SCHEMA_VERSION` には触れません**。

## Phase 4 初期の到達点（10画面の足場）

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
- **契約 / 人事サマリー閲覧**（`scenes/contract_personnel_summary_view.tscn`）: 契約概要・人事リスク（簡易目安）・主要契約選手・ロスター構成・注意文などを JSON で閲覧（**第10画面の第1弾**。**契約交渉画面ではない**。**契約更新・交渉・獲得・解雇・FA 操作などの UI は未接続**）。財務サマリー（クラブ全体の資金・収支）とは役割が異なり、**選手単位の年俸・契約残・満了目安・国籍枠・構成バランス**に寄せた閲覧。ロスター（編成表）とは役割が異なり、**年俸・契約・人事リスクの読み取り**に寄せた閲覧。
- **仮ナビ**: ホーム → ロスター → ホーム、ホーム → クラブ史 → ホーム、**ホーム → 順位表 → ホーム**、**ホーム → 日程 → ホーム**、**ホーム → 施設サマリー → ホーム**、**ホーム → 財務サマリー → ホーム**、**ホーム → オーナーミッション → ホーム**、**ホーム → 戦術サマリー → ホーム**、**ホーム → 契約・人事サマリー → ホーム**（各サブ画面の **閲覧／戻る** はシーン切替のみ）。
- **ホーム内「画面メニュー（読み取り）」カード**: **チーム**（**ロスター**・**戦術サマリー**）／**リーグ**（順位表・日程）／**クラブ**（クラブ史・**施設**）／**経営**（**財務サマリー**・**オーナーミッション**・**契約・人事サマリー**）からも上記閲覧画面へ遷移可能（**HeaderNavRow と併用の二重導線**。本格ナビではない）。**戦術サマリー**・**財務サマリー**・**オーナーミッション**・**契約・人事サマリー**は **HeaderNavRow には載せず**、カードの **チーム** / **経営** 列から遷移します。**経営**列は **3 ボタン**（財務／オーナーミッション／契約・人事）。**経営**列にだけあった補足説明ラベルは削除し、他カテゴリとボタン位置を揃えています（`56bcd9e Godotホーム経営カテゴリの説明文を削除`）。
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
  - `data/contract_personnel_summary_from_python.json`
- **mock 表示**はユーザー環境の **Godot 4.6.2** で確認済み。**Python 生成 JSON の優先表示**も各画面で確認済み。個別画面用 CLI はリポジトリルートから `python -m basketball_sim.export.*_readonly` で `godot/data/` に出力する運用に加え、**10 画面分をまとめて書き出す一括コマンド** `python -m basketball_sim.export.godot_readonly_bundle` も利用できる（**Godot からの自動起動ではなく**、**PowerShell 等で手動実行**。詳細は後述の **「10画面分の `*_from_python.json` を一括生成（Python のみ・手動）」** 節）。

## 本番ホームワイヤー sandbox（`scenes/home_production_wire_preview.tscn`）

**位置づけ**: 本番 GUI のレイアウト・情報密度・左レール＋上部クラブ帯の**研究用**シーン。`scenes/home_dashboard.tscn`（**10 画面導線・`from_python` / mock の正本**）とは別ファイルで、**本線を壊さず**に目視確認する。

**最新状態（2026-05 sandbox 到達点）**:

- **左レール**はカテゴリナビ風に調整済み。**現在地「ホーム」**を強調表示。
- 左の大分類は **ホーム / チーム / リーグ / 経営 / クラブ**（見た目のみ。クリック・遷移なし）。
- **ClubBand** に **SG / LOGO** の仮クラブロゴ枠を追加済み（実画像・外部ロゴ素材なし）。
- **左レール現在地**（`StyleBoxFlat_nav_active`）のアクセント枠色を、ClubBand の仮ロゴ枠（琥珀系）に**馴染む暖色**へ**最小調整**済み（Theme 非変更・シーン内 SubResource のみ）。
- **CardShortcuts** は **2 行から 1 行**へ圧縮済み。`詳細画面: チーム / リーグ / 経営 / クラブ` の**補助案内**はそのまま残し、左レール大分類との**役割重複感を軽減**。
- **ClubBand**（`EAST DIVISION`・`12勝12敗 / 地区4位` など）と**中央カード**の地区／勝敗／順位の**情報重複**は調査済み（レポート `reports/godot_phase4_home_wire_clubband_card_overlap_survey_2026-05.txt`。**本コミットでは reports は変更しない**）。
- **CardStandings** のタイトル「順位・成績」は維持し、本文ラベル（`CardStandingsBody`）のみ **立ち位置判断文**へ変更済み: **`PO圏まで 2.0差 / 直近5試合 3勝2敗`**（ClubBand の現在値の**単純な繰り返し**から脱却）。
- **CardTasks / CardNews / CardClubState** の役割は調査済み（レポート `reports/godot_phase4_home_wire_task_news_state_survey_2026-05.txt`、および CardClubState 重点の `reports/godot_phase4_home_wire_club_state_survey_2026-05.txt`。**本コミットでは reports は変更しない**）。
- **CardNewsBody** は 2 行ニュースから **`ホーム快勝、次戦へ弾み`** の **1 行ヘッドライン**へ短縮済み（`CardNews` カードとタイトル「ニュース」は維持）。右列の**情報密度を下げ**、**CardTasks**（`Phase4WarningCard`）が**主役**として見えやすい整理。
- **CardClubBody** は 2 行から **`サラリー余力あり / 士気良好`** の **1 行要約**へ短縮済み（`CardClubState` カードとタイトル「クラブ状態」は維持）。ClubBand の**資金・オーナー信頼**と「クラブの健康」情報が**重く被りすぎない**よう、**詳細ではなく状態要約**に整理。**中央左列**の密度も一段軽くし、**CardTasks** の主役感を維持しやすくした。
- 右列の読み: **タスク＝次にやること（ToDo）**、**ニュース＝雰囲気・世界の動き**、**ショートカット＝補助案内**。
- **中央 2 カラムの低〜中密度カード**と **BottomStrip** は従来どおり維持。
- **ユーザー環境 Godot 4.6.2** で sandbox を **F6 表示確認**済み（ナビ・ClubBand・中央・**アクセント調整後**）。**UID 参照エラーなし**、**実行後の不要な追跡差分なし**（手元運用の目安）。
- 色・質感の追加試験前に、候補整理は **`reports/godot_phase4_home_wire_color_texture_survey_2026-05.txt`**（調査レポート）で実施済み。**Theme 全面改色は未着手**。

### 右サマリー列あり版の比較scene（`scenes/home_production_wire_preview_right_summary.tscn`）

- **位置づけ**: 現行 2 カラム sandbox（`home_production_wire_preview.tscn`）を壊さず、**右に第 3 列（状態サマリー）**を足したレイアウトを **比較する**ための **別シーン**（script なし・固定文言・**F6 単体**）。**本線 `home_dashboard.tscn` には未接続**。
- **UID**: `cf8012c`（`Godot右サマリー比較sceneのUIDを安定化`）で先頭行を Godot 側の正式 UID 表記へ合わせ済み。調査: `a8b4a1d`（`Godot右サマリー比較sceneのUID問題を調査`）。scene 追加: `a7858c3`。
- **ユーザー環境 Godot 4.6.2**: **F6 表示確認 OK**。**UID エラーなし**。**実行後の不要な追跡差分なし**（手元運用の目安）。
- **右サマリー列「状態サマリー」**: **キャップ余力**・**士気**・**ロスター**・**契約警告**・**疲労リスク**の短い行（固定文言）。**ClubBand の資金・オーナー信頼**、**中央「順位・成績」カードの立ち位置文**、**タスク ToDo の箇条書き**を**右列で繰り返さない**比較用の情報分担サンプル。
- **目視評価（2026-05）**: 1280×720 では中央カードの**横幅がやや詰まり**、**現行 2 カラム版より見やすいとは言いにくい**。**右サマリー列あり版は比較候補・参考案として残す**。**現時点の本命候補は、余白と可読性に優れる現行 2 カラム版**（`home_production_wire_preview.tscn`）寄り。
- **本線への移植**: **未実施**。**別タスク・別コミット**で、可読性・余白・情報密度・本線 DTO との整合を見て判断する。

**本線との役割分担**:

- **本線 `home_dashboard.tscn`** は **10 画面導線**・**from_python 優先 + mock フォールバック**・pytest の**正本**として維持。
- **sandbox** は **script なし**・**固定文言のみ**・**F6 単体**での確認用。
- **`project.godot` の `run/main_scene` は変更しない**（既定のまま本線ホーム）。
- **実データ接続**、**Python 自動起動**、**本線への `change_scene_to_file`** は**未実装**。

### 本線ホーム Header の ClubBand 風寄せ（`scenes/home_dashboard.tscn`）

- **段階移植の第一歩**（`83d7fc0`「Godot本線ホームHeaderにクラブ帯要素を追加」）: **HeaderCard 内だけ**を sandbox **ClubBand** 風へ**最小寄せ**。**大レイアウト移植ではない**。
- **追加**: `HeaderClubBandRow`（HBox）・`HomeLogoSlot`（`custom_minimum_size = Vector2(72, 58)`・`StyleBoxFlat_home_logo_slot`・暗地背景・**琥珀系枠**・**角丸 9**）・`LogoSlotCenter` / `LogoSlotCol` / **`LogoMark`（`SG`）** / **`LogoHint`（`LOGO`）**・`HeaderBandTextCol`。**`load_steps` は 5→6**。
- **既存ラベル**: **`ClubNameLabel` / `SeasonLabel` / `DataSourceLabel`** は **ノード名と `unique_name_in_owner = true`** を維持したまま **`HeaderBandTextCol` 配下へ親移動**（`home_dashboard.gd` の `%` 参照は変更不要）。
- **`DataSourceLabel`**: **`autowrap_mode = 2`** を追加し、**長い読込元パス**にやや強くした。**from_python / mock の読込元表示として維持**（削除なし）。
- **`HeaderTopRow`**（Badge / Placeholder）、**`HeaderNavRow` と 5 ボタン**は**維持**。**文言・tooltip・`[connection]`・遷移先は変更なし**。
- **`home_dashboard.gd` は未変更**（**`83d7fc0` / `ed106c8` / `8676095` / `762f5bc` / `d18bf1f` / `2471b67` いずれでも変更なし**）。**from_python / mock の候補パス・読込経路は未変更**。**`83d7fc0` は HeaderCard のみ**で **`Scroll` 以下は未着手だった**が、その後 **`ed106c8` で `CardNews`、`8676095` で `CardNext`、`762f5bc` で `CardWarnings`、`d18bf1f` で `CardTasks`、`2471b67` で MetricsRow の `CardRank` / `CardMoney`** Theme 限定適用（下記「Scroll 以下 `CardNews`」〜「MetricsRow」節）。
- **左レール**は **`a5e548f` 以前は本線未実装**（**表示用の最小追加は下記「表示用 LeftRail」節**）。**右サマリー比較scene**（`home_production_wire_preview_right_summary.tscn`）は**本線未接続**（上記「右サマリー列あり版」節）。
- **ユーザー環境 Godot 4.6.2**: 通常起動 / F6 で **仮ロゴ枠・ClubName / Season / DataSourceLabel・HeaderNavRow** が問題なく表示。**UID エラーなし**。**実行後の不要差分なし**（手元運用の目安）。
- **今後（Header 節・`83d7fc0` 時点の補足）**: Scroll 以下 Theme・**`club_summary` 状況メモ化**（`91cfaed`）・**`CardTeamExtras` / `CardSummary` / `CardNavMenu` Theme**（`dc0182a`・`1d070ba`・`d9bd713`）は**別節**。**News 1 行化**・**Header 資金・成績本格移植**は **別タスク**（**左レールの表示追加は `a5e548f` で実施済み・クリック化は別タスク**）。

### 本線ホーム Scroll 以下 `CardNews` の Theme 限定適用（`ed106c8`）

- **Scroll 以下の第一歩**（`ed106c8`「Godot本線ホームのニュースカードにThemeを限定適用」）: **`CardNews` 1 枚だけ**を `phase4_readonly_core.tres` の **`Phase4SummaryCard`** に寄せた。**中央カード全体の大移植ではなく、1 カード限定の見た目寄せ**。
- **`CardNews`**: `theme = ExtResource("2_theme")`、`theme_type_variation = &"Phase4SummaryCard"`。**`theme_override_styles/panel = SubResource("StyleBoxFlat_card")` を削除**（パネル見た目は Theme 側に委譲）。**共有 `StyleBoxFlat_card` SubResource は他カード用に削除せず残存**。
- **`HNews` / `NewsLabel`**: 白カード向け濃色（**`Color(0.08, 0.11, 0.18, 1)`** / **`Color(0.16, 0.2, 0.3, 1)`**）。**`NewsLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。
- **`news` の行数制限は未実装**。**`_join_lines` は従来どおり**。**`home_dashboard.gd` は未変更**。**JSON / Python / DTO は未変更**。**Theme `.tres` は未変更**。**CardNews 以外の Scroll 下カードは未変更**。**HeaderNavRow は未変更**。
- **ユーザー環境 Godot 4.6.2**: **白カード表示・タイトル/本文の可読性・news 本文・行数は従来どおり**を確認。**UID エラーなし**。**実行後不要差分なし**（手元運用の目安）。
- **今後**: sandbox の **`CardNewsBody = ホーム快勝、次戦へ弾み`** のような **1 行ヘッドライン**を本線へ本格導入する場合は、**`.gd` 側の表示行数制御**、または **export / DTO の `news_headline` 等**を**別タスク**で設計する。

### 本線ホーム Scroll 以下 `CardNext` の Theme 限定適用（`8676095`）

- **Scroll 以下の 2 枚目**（`8676095`「Godot本線ホームの次戦カードにThemeを限定適用」）: **`CardNews` に続き** **`CardNext` 1 枚だけ**を `phase4_readonly_core.tres` の **`Phase4SummaryCard`** に寄せた。**大レイアウト移植ではなく、1 カード限定の見た目寄せ**。
- **`CardNext`**: `theme = ExtResource("2_theme")`、`theme_type_variation = &"Phase4SummaryCard"`。**`theme_override_styles/panel = SubResource("StyleBoxFlat_card")` を削除**（パネルは Theme 側）。**共有 `StyleBoxFlat_card` SubResource は他カード用に残存**。
- **`HNext` / `NextGameLabel`**: 白カード向け濃色（**`Color(0.08, 0.11, 0.18, 1)`** / **`Color(0.16, 0.2, 0.3, 1)`**）。**`NextGameLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text` は維持**。
- **`next_game` の本文・`_apply_snapshot` の割当・表示ロジックは不変**。**`home_dashboard.gd` は未変更**。**JSON / Python / DTO は未変更**。**Theme `.tres` は未変更**。**`CardNews` は既存の白カード状態を維持**。**`CardNext` 以外の Scroll 下カードは未変更**。**HeaderNavRow は未変更**。
- **ユーザー環境 Godot 4.6.2**: **白カード表示・見出し「次戦 / 次イベント」/ 本文の可読性・`next_game` 表示は従来どおり**を確認。**UID エラーなし**。**実行後不要差分なし**（手元運用の目安）。

### 本線ホーム Scroll 以下 `CardWarnings` の Theme 限定適用（`762f5bc`）

- **Scroll 以下の警告カード**（`762f5bc`「Godot本線ホームの警告カードにThemeを限定適用」）: **`CardNews` / `CardNext` に続き** **`CardWarnings` 1 枚だけ**を `phase4_readonly_core.tres` の **`Phase4WarningCard`** に寄せた。**大レイアウト移植ではなく、1 カード限定の見た目寄せ**。
- **`CardWarnings`**: `theme = ExtResource("2_theme")`、`theme_type_variation = &"Phase4WarningCard"`。**`theme_override_styles/panel = SubResource("StyleBoxFlat_warn")` を削除**（パネルは Theme 側）。**`StyleBoxFlat_warn` SubResource は削除せず残存**。**`StyleBoxFlat_card` も削除していない**。
- **`HWarn` / `WarningsLabel`**: ライト警告カード向け濃色（**`Color(0.32, 0.2, 0.08, 1)`** / **`Color(0.3, 0.22, 0.12, 1)`**）。**`WarningsRow` の tscn 上 `visible = false` は維持**。**`unique_name_in_owner` / `autowrap_mode` / `font_size` / `text` / `layout_mode` 等は原則維持**。
- **`warnings` の表示/非表示**は **`_set_optional_row` / `_warnings_card.visible` / `_warnings_row.visible` の従来ロジックのまま**。**`home_dashboard.gd` は未変更**。**JSON / Python / DTO は未変更**。**Theme `.tres` は未変更**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**`762f5bc` 時点では `CardTasks` は未変更**（**その後 `d18bf1f` で SummaryCard 化 — 下記「`CardTasks`」節**）。**`CardWarnings` 以外の Scroll 下カードは未変更**。**HeaderNavRow は未変更**。
- **ユーザー環境 Godot 4.6.2**: **WarningCard 表示・`HWarn` / `WarningsLabel` 可読性・`warnings` 挙動**を確認。**UID エラーなし**。**実行後不要差分なし**（手元運用の目安）。

### 本線ホーム Scroll 以下 `CardTasks` の Theme 限定適用（`d18bf1f`）

- **Scroll 以下のタスクカード**（`d18bf1f`「Godot本線ホームのタスクカードにThemeを限定適用」）: **`CardNews` / `CardNext` / `CardWarnings` に続き** **`CardTasks` 1 枚だけ**を `phase4_readonly_core.tres` の **`Phase4SummaryCard`** に寄せた。**中央カード全体の大移植ではなく、1 カード限定の見た目寄せ**。
- **`CardTasks`**: `theme = ExtResource("2_theme")`、`theme_type_variation = &"Phase4SummaryCard"`。**`theme_override_styles/panel = SubResource("StyleBoxFlat_card")` を削除**（パネルは Theme 側）。**共有 `StyleBoxFlat_card` SubResource は他カード用に削除せず残存**。**`StyleBoxFlat_warn` SubResource も削除していない**。
- **`HTasks` / `TasksLabel`**: 白カード向け濃色（**`Color(0.08, 0.11, 0.18, 1)`** / **`Color(0.16, 0.2, 0.3, 1)`**）。**`TasksLabel` の `unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text = "（タスク）"` は維持**。
- **`tasks` の本文・最大 3 行表示は未変更**。**`_join_lines(d, "tasks", 3)` は従来どおり**。**`home_dashboard.gd` は未変更**。**JSON / Python / DTO は未変更**。**Theme `.tres` は未変更**。**from_python / mock の読込経路は未変更**。**HeaderNavRow は未変更**。**`CardWarnings` は既存の WarningCard 状態を維持**。**`CardNews` / `CardNext` は既存の白カード状態を維持**。**`CardTasks` 以外の Scroll 下カードは未変更**。**HeaderCard のクラブ帯要素は維持**。**左レール**は **`a5e548f` で表示用のみ本線追加**（下記節）。**右サマリー比較scene**は**本線未接続の参考案**。
- **役割分界**: **`CardWarnings`＝警告・リスク**、**`CardTasks`＝行動・ToDo**（**WarningCard に寄せず SummaryCard** で意味の被りを避ける）。
- **ユーザー環境 Godot 4.6.2**: **CardTasks 白カード表示・`HTasks` / `TasksLabel` 可読性・tasks 本文・最大 3 行表示維持**を確認。**UID エラーなし**。**実行後不要差分なし**（手元運用の目安）。
- **現時点の本線ホーム**（`d18bf1f` 時点）: **HeaderCard クラブ帯要素**＋**`CardNews` / `CardNext` / `CardTasks` の SummaryCard**＋**`CardWarnings` の WarningCard**まで進んだ状態（**MetricsRow は `2471b67` で更新 — 下記**）。

### 本線ホーム MetricsRow `CardRank` / `CardMoney` の Theme 限定適用（`2471b67`）

- **MetricsRow 内の見た目統一**（`2471b67`「Godot本線ホームMetricsRowの指標カードにThemeを限定適用」）: 既に **`Phase4SummaryCard` 済み**だった **`CardDivision` に続き**、**`CardRank` / `CardMoney` の 2 枚だけ**を**同一コミット**で `phase4_readonly_core.tres` の **`Phase4SummaryCard`** に寄せた。**中央カード密度の大移植ではなく、MetricsRow 内の見た目統一**。
- **`CardRank` / `CardMoney`**: 各 `theme = ExtResource("2_theme")`、`theme_type_variation = &"Phase4SummaryCard"`。**各 `theme_override_styles/panel = SubResource("StyleBoxFlat_card")` を削除**（パネルは Theme 側）。**共有 `StyleBoxFlat_card` SubResource は他カード用に削除せず残存**。**`StyleBoxFlat_warn` SubResource も削除していない**。
- **文字色**（`CardDivision` / `CardNews` / `CardNext` / `CardTasks` と同系）: **`HRank` / `HMoney`** → **`Color(0.08, 0.11, 0.18, 1)`**。**`RankRecordLabel` / `MoneyLabel`** → **`Color(0.16, 0.2, 0.3, 1)`**。
- **`RankRecordLabel` / `MoneyLabel`**: **`unique_name_in_owner` / `autowrap_mode` / `font_size` / プレースホルダ `text`（`（順位）` / `（資金）`）は維持**。
- **`rank_record` / `money` の表示内容は未変更**。**`_rank_record.text = _txt(d, "rank_record")` / `_money.text = _txt(d, "money")` は従来どおり**。**`home_dashboard.gd` は未変更**。**JSON / Python / DTO は未変更**。**Theme `.tres` は未変更**。**from_python / mock の読込経路は未変更**。**HeaderNavRow は未変更**。
- **`CardDivision` は未変更**（既存 SummaryCard 済み）。**`SecMetricsTitle` は未変更**。**MetricsRow の構造・幅・`separation` は未変更**。**`CardRank` / `CardMoney` 以外の Scroll 下カードは未変更**。**`CardNews` / `CardNext` / `CardTasks` は既存の SummaryCard 状態を維持**。**`CardWarnings` は既存の WarningCard 状態を維持**。**HeaderCard のクラブ帯要素は維持**。**左レール**は **`a5e548f` で表示用のみ本線追加**（下記節）。**右サマリー比較scene**は**本線未接続の参考案**。
- **ユーザー環境 Godot 4.6.2**: **MetricsRow 3 枚の白カード統一・`CardRank` / `CardMoney` 見出し・本文の可読性・`rank_record` / `money` 内容維持**を確認。**UID エラーなし**。**実行後不要差分なし**（手元運用の目安）。
- **現時点の本線ホーム**（`2471b67` 時点）: **HeaderCard クラブ帯要素**＋**MetricsRow 3 枚**＋**Scroll 以下の Summary / Warning 系**まで（**`CardTeamExtras` / `CardSummary` の Theme・`club_summary` 状況メモ化は下記 3 コミット**）。

### 本線ホーム `club_summary` 状況メモ化（`91cfaed`）

- **DTO / export のみ**（`home_dashboard_readonly.py`・`test_home_dashboard_readonly_export.py`・`home_dashboard_mock.json`）。**`.tscn` / `.gd` / Theme は未変更**。
- **`club_summary` の役割**: **順位・資金・salary_cap の再掲サマリー**から **シーズン状態などの短い状況メモ**（原則 1〜2 行、最大 3 行）へ変更。
- **削った再掲**: `rank_record` / `division` / `money` / `salary_cap` 全文（**MetricsRow**・**CardTeamExtras**・トップレベルキーで表示）。
- **トップレベル** `division` / `rank_record` / `money` / `salary_cap` / `owner_trust` / `recent_form` は**維持**。

### 本線ホーム `CardTeamExtras` の Theme 限定適用（`dc0182a`）

- **`home_dashboard.tscn` のみ**。`theme` + **`Phase4SummaryCard`**、**`StyleBoxFlat_card` の panel override のみ除去**（SubResource は **CardNavMenu** 用に残存）。
- **表示**: `owner_trust` / `salary_cap` / `recent_form`（**`_extras_card.visible` 等の .gd ロジックは不変**）。

### 本線ホーム `CardSummary` の Theme 限定適用（`1d070ba`）

- **`home_dashboard.tscn` のみ**（**`91cfaed` の状況メモ化の後**）。`CardTeamExtras` と同型の **SummaryCard** 化。

### 本線ホーム 表示用 LeftRail（`a5e548f`）

- **変更ファイル**: **`home_dashboard.tscn` のみ**（`a5e548f`「Godot本線ホームに表示用左レールを追加」）。**大レイアウト全面移植ではなく、`MainRow` 挿入による第 1 段**。
- **構造**: `HeaderCard`・`StatusLabel`・`FooterNote` は**全幅維持**。**`StatusLabel` 直下**に **`MainRow`（HBox・separation 14）** → **左** `LeftRail`（**200px**）・**右** 既存 **`Scroll` / `Inner`**（`CardNavMenu` → MetricsRow → 各カードの順序は不変）。
- **LeftRail**: sandbox 本命（`home_production_wire_preview.tscn`）を参考。**大分類 5**（**ホーム**＝現在地強調、**チーム**・**リーグ**・**経営**・**クラブ**）。**Panel + Label**、**`mouse_filter = 2`**。**Button 化・`[connection]` 追加・`home_dashboard.gd` 変更なし**。タイトル **MAIN**、注記 **「表示のみ / 詳細は中央メニュー」**。
- **維持**: **`HeaderNavRow`（5 ボタン）**、**`CardNavMenu`（8 ボタン・#7〜#10 の主入口含む）** — **削除・縮小なし**（**`d9bd713` で CardNavMenu のみ Theme 化 — 下記節**）。CardNavMenu 側の connection は **`Margin/RootCol/MainRow/Scroll/...`** へパス更新のみ（**既存 9 handler 名は不変**）。
- **未変更**: **`home_dashboard.gd`**、**Theme `.tres`**、**export / mock JSON**、**`project.godot`**。
- **ユーザー環境 Godot（ローカル目視・スクショ約 1216×684）**: **大きなレイアウト崩れなし**。**HeaderCard 全幅**・**LeftRail 左表示**・**CardNavMenu 4 列**・**MetricsRow 以降のカード**・**FooterNote** 表示 OK。**HeaderNavRow** のメニュー遷移 OK。**CardNavMenu**（画面メニュー）のメニュー遷移 OK。**左の MAIN / LeftRail はクリック遷移しないのが正しい**（**表示のみ**）。
- **今後**: LeftRail を**クリック可能**にするかは**別タスク・別設計判断**（大分類と複数画面の対応・handler 流用・CardNavMenu 縮小可否）。

### 本線ホーム `CardNavMenu` の Theme 限定適用（`d9bd713`）

- **変更ファイル**: **`home_dashboard.tscn` のみ**（`d9bd713`「Godot本線ホームCardNavMenuにThemeを限定適用」）。**導線・ナビ構造の再設計ではない**。
- **`CardNavMenu`**: `theme` + **`Phase4SummaryCard`**。**`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は削除せず残置**）。
- **ラベル**: `NavTitle` / カテゴリラベル（`CatTeam` 等）を白カード向け濃色（`CardTeamExtras` / `CardSummary` と同系）。**8 ボタン**のノード名・text・tooltip・**14 connection**・**9 handler 名は不変**。
- **維持**: **`HeaderNavRow`**、**表示のみ `LeftRail`**（Button / connection / script 追加なし）。**`CardNavMenu` は削除・縮小していない**。
- **未変更**: **`home_dashboard.gd`**、**Theme `.tres`**、**export / mock JSON**。
- **ユーザー環境 Godot（ローカル目視・1280×720）**: **大きなレイアウト崩れなし**。**CardNavMenu 白系カード化**（Scroll 内の**唯一暗色カード状態は解消**）。**4 列表示成立**。**8 ボタン視認 OK**。**#7〜#10 入口表示 OK**（財務サマリー・オーナーミッション・戦術サマリー・契約・人事サマリー）。**CardNavMenu 遷移 OK**。**LeftRail は表示のみ**（**遷移しないのが正しい**）。**実行後 git 差分なし**（手元確認）。
- **現在のホーム到達点（ナビ）**: **HeaderNavRow**＝上部主要5導線、**LeftRail**＝大分類・現在地の表示、**CardNavMenu**＝**実操作用**の中央画面メニュー（9詳細・#7〜10含む）。
- **今後**: **LeftRail クリック化**は**別タスク**。**次の自然な進め方**は **他詳細画面への Theme 方針展開**（次画面選定調査 → 1画面ずつ）または **ホーム DTO/表示の別整理**（`CardNews` 1行化等）。**CardNavMenu の削除・縮小は当面しない**。

### 施設サマリー閲覧 `Phase4` Theme 限定適用・第1段（`5987821`）

- **9詳細画面 Theme 横展開の第1号**（選定調査 `23a8fcf` → 実装 `5987821`）。**変更ファイル**: **`facility_summary_view.tscn` のみ**。
- **ルート** `FacilitySummaryView` に `phase4_readonly_core.tres` を割当。**`HeaderCard`** → **`Phase4HeaderCard`**。**`SummaryCard`** → **`Phase4SummaryCard`**（**panel override のみ除去**。**`StyleBoxFlat_header` / `StyleBoxFlat_summary` の SubResource 定義は残置**）。**`ReadonlyBadge` / `ModeStrip`** の `StyleBoxFlat_chip` は維持。
- **ラベル**: ヘッダー・サマリーを白カード向け濃色（`roster_view` / 本線 `CardSummary` と同系）。**Scroll 内**の動的 `Label.new()`（施設一覧・sections）は**第2段** — **暗背景＋明文字のまま**（今回未変更）。
- **維持**: **`HomeNavButton`**（text / tooltip / connection / `_on_home_nav_button_pressed`）、**`%DataSourceLabel`** 等 **unique 名**、**from_python / mock** 読込（**`facility_summary_view.gd` 不変**）。
- **未変更**: **`facility_summary_view.gd`**、**Theme `.tres`**、**export / mock JSON**、**`project.godot`**、**`home_dashboard.tscn`**。
- **pytest**（実装時）: `test_home_dashboard_readonly_export` 10 / `test_roster_readonly_export` 10 / phase0 smoke 1 / **`test_facility_summary_readonly_export` 9** — いずれも passed。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 施設サマリー遷移 OK**（**HeaderNavRow** または **CardNavMenu・クラブ列**）。**施設サマリー表示 OK**。**HeaderCard Phase4 系・SummaryCard 白系 OK**。**ラベル可読性・DataSourceLabel OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **到達点**: **Header + Summary の白カード化第1段完了**（**画面全体の完全仕上げではない**）。
- **今後**: **Scroll 動的部分の第2段**（`.gd` または OnDark 系）か、**同型のクラブ史・順位表**への横展開を判断。

**sandbox（`home_production_wire_preview.tscn`）の確認運用:**

- **確認方法**: Godot エディタで当該シーンを開き、**「現在のシーンを実行」（F6）** で単体起動する。
- **試す場の例**（上記に加え）: 色味（シーン内 `StyleBoxFlat` と既存 `phase4_readonly_core.tres` の variation の組み合わせ）。
- **UID / `load_steps`（再シリアライズ運用）**: エディタで保存したあと **`git diff -- scenes/home_production_wire_preview.tscn`** を確認する。意図しない**先頭行付近だけ**（`uid://` / `load_steps` のみ等）の差分なら、必要に応じて `git checkout HEAD -- scenes/home_production_wire_preview.tscn` で戻し、**意図するレイアウト差分だけ**を再適用する（詳細方針は `reports/godot_phase4_home_wire_sandbox_policy_2026-05.txt`）。**実行後も `git diff` で意図外の差分が混ざっていないか**確認する。
- **本線へ反映**: 1280×720 での破綻なし・目視合意・左の大分類確定・ホーム表示情報の整理・必要 DTO の整理・UID 運用の安定・**小さなコミット単位**で切れる、を満たしてから **別タスク・別コミット**で `home_dashboard` 側へ移植する（**Header の ClubBand 風寄せ第 1 段**は `83d7fc0` で実施済み。**Scroll 以下**は **`ed106c8` で `CardNews`、`8676095` で `CardNext`、`d18bf1f` で `CardTasks`（いずれも `Phase4SummaryCard`）、`762f5bc` で `CardWarnings`（`Phase4WarningCard`）、`2471b67` で MetricsRow の `CardRank` / `CardMoney`（`Phase4SummaryCard`）**の Theme 限定適用を段階実施。**大レイアウト移植・DTO 本格整理は未着手**）。

## 共通 Theme / 白ベース検証（Phase 4・限定適用）

**位置づけ**: **本番 GUI の完成や Theme の全面適用ではない**。`themes/phase4_readonly_core.tres`（UID `uid://c9phase4rocore01`）による **白ベース検証版** と、`scenes/theme_preview.tscn` による **第 0 段 preview** で、見た目と variation の確認を進めている段階である。**既存 10 画面すべてに一括で当てる予定ではない**。

- **preview**: `theme_preview.tscn` は **既存 10 画面には未適用**。暗背景上のラベルには `Phase4OnDarkTitle` 等の variation を preview 側で使用し、可読性を確認している。
- **契約 / 人事サマリー**（`contract_personnel_summary_view.tscn`）: ルートに上記 Theme を割当。**ヘッダー**は `Phase4HeaderCard` とヘッダー内 Label の濃色 override。**契約概要**・**ロスター構成**は `Phase4SummaryCard`。**注意**は `Phase4WarningCard`。**人事リスク**・**主要契約選手**は従来の暗色 `StyleBoxFlat_summary` パネルのまま。動的に `Label.new()` している行は **暗地前提のまま**で、**白カード化・Theme 統一は未着手**（別タスクで `.gd` 調整が必要）。
- **ロスター閲覧**（`roster_view.tscn`）: ルート Theme。**ヘッダー**は `Phase4HeaderCard` + ヘッダー Label 濃色。**表**（`Scroll` / `RowList` 内の動的 `Label`）は **暗背景のまま**、`roster_view.gd` で `Phase4OnDarkTableHead` / `Phase4OnDarkTableCell` の **`theme_type_variation` に寄せた最小対応**（白カード化はしていない）。
- **施設サマリー閲覧**（`facility_summary_view.tscn`）: **第1段**（`5987821`）— ルート Theme。**`HeaderCard`**＝`Phase4HeaderCard`、**`SummaryCard`**＝`Phase4SummaryCard`。**Scroll 内動的 Label**は**未着手**（第2段）。詳細は上記「施設サマリー閲覧 `Phase4` Theme」節。
- **ホーム**（`home_dashboard.tscn`）: **ルートには Theme を付けていない**。**`HeaderCard` のみ** `Phase4HeaderCard`（**`83d7fc0` ClubBand 風寄せ**）。**`a5e548f` で表示用 `LeftRail`（200px・クリック不可）**。**MetricsRow** 3 枚 + **Scroll 以下**（**`CardNavMenu` 含む**）**`Phase4SummaryCard` / `Phase4WarningCard`**（**`d9bd713` で `CardNavMenu` も Summary 化済み**）。**Scroll 内の暗色カード問題は解消済み**。**`home_dashboard.gd`・Theme `.tres` は不変**。**HeaderNavRow**・**CardNavMenu**＝実操作導線（**LeftRail は表示のみ** — 下記2節）。
- **読込**: `from_python` 優先・mock フォールバック、**Godot から Python を自動起動しない**方針は **変更なし**。
- **UID / 実行後の git**: シーン編集後は **UID 参照エラーが出ないか** Godot で確認する。**実行やエディタ保存のあと** `git status --short` で、意図しない `.tscn` 差分や生成 JSON が混ざっていないか確認する（`*_from_python.json` は引き続き **コミットしない**）。**`home_production_wire_preview.tscn`（sandbox）**を触ったあとも同様に `git diff` を確認し、意図しない先頭行（`uid://` / `load_steps`）だけの差分なら `git checkout HEAD -- scenes/home_production_wire_preview.tscn` で戻す運用可（詳細は「本番ホームワイヤー sandbox」節）。

**Theme 検証ロードマップ（手元メモ・2026-05 時点）**

```txt
◎ Theme preview（theme_preview.tscn）
◎ 契約・人事サマリー・ヘッダー（Phase4HeaderCard + 文字色）
◎ 契約・人事サマリー・契約概要カード（Phase4SummaryCard）
◎ 契約・人事サマリー・ロスター構成カード（Phase4SummaryCard）
◎ 契約・人事サマリー・注意カード（Phase4WarningCard）
◎ ロスター閲覧・ヘッダー（Phase4HeaderCard + 文字色）
◎ ロスター表・OnDark（動的 Label → Phase4OnDarkTableHead / Phase4OnDarkTableCell・暗背景のまま）
◎ ホーム・Header のみ（HeaderCard に Theme 限定）
◎ ホーム・MetricsRow `CardDivision` / `CardRank` / `CardMoney` のみ `Phase4SummaryCard` 限定適用（`f66bcd2`・`2471b67`）
◎ ホーム・Scroll 以下 `CardNews` / `CardNext` / `CardTasks` のみ `Phase4SummaryCard` 限定適用（`ed106c8`・`8676095`・`d18bf1f`）
◎ ホーム・Scroll 以下 `CardWarnings` のみ `Phase4WarningCard` 限定適用（`762f5bc`）
◎ 本線ホーム `club_summary` 状況メモ化（`91cfaed`・export/tests/mock のみ）
◎ 本線ホーム `CardTeamExtras` のみ `Phase4SummaryCard` 限定適用（`dc0182a`）
◎ 本線ホーム `CardSummary` のみ `Phase4SummaryCard` 限定適用（`1d070ba`）
◎ 本番ホームワイヤー sandbox（`home_production_wire_preview.tscn`・F6 単体・script なし）
◎ sandbox 方針整理（`reports/godot_phase4_home_wire_sandbox_policy_2026-05.txt`）
◎ README/docs へ sandbox 位置づけ記録
◎ sandbox 左レールをカテゴリナビ風に調整（現在地ホーム強調）
◎ sandbox ClubBand に仮クラブロゴ枠（SG/LOGO）を追加
◎ sandbox 左レール現在地アクセント調整（ロゴ枠琥珀系に馴染む最小変更・SubResource のみ）
◎ sandbox CardShortcuts を 2 行から 1 行へ圧縮（補助案内ラベルは維持）
◎ ClubBand と中央カードの情報重複を調査（重複調査レポート）
◎ sandbox 順位カード本文（`CardStandingsBody`）を立ち位置判断文へ変更（`PO圏まで 2.0差 / 直近5試合 3勝2敗`）
◎ sandbox 中央カード（タスク／ニュース／クラブ状態）の役割調査
◎ sandbox CardNews 本文（`CardNewsBody`）を1行ヘッドラインへ短縮（`ホーム快勝、次戦へ弾み`）
◎ sandbox CardClubBody（`CardClubState`）を1行要約へ短縮（`サラリー余力あり / 士気良好`）
◎ sandbox 色・質感候補調査（`reports/godot_phase4_home_wire_color_texture_survey_2026-05.txt`）
◎ README/docs へ sandbox のクラブ状態短縮到達点を記録
◎ 右サマリー列あり版の調査
◎ 右サマリー比較scene追加（`home_production_wire_preview_right_summary.tscn`）
◎ 右サマリー比較sceneのUID問題を調査（`a8b4a1d`）
◎ 右サマリー比較sceneのUIDを安定化（`cf8012c`）
◎ 右サマリー比較sceneのF6表示確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に右サマリー比較の確認結果を記録（本命は現行2カラム版寄り）
◎ 本線 `home_dashboard` への段階移植方針を調査（`a2feb4e`）
◎ 本線 `home_dashboard` 中央カード密度の移植方針を調査（`c9e4474`）
◎ 本線 `home_dashboard` HeaderCard にクラブ帯要素を最小追加（`83d7fc0`）
◎ README/docs に本線 Header クラブ帯要素の到達点を記録（`a7be5d7`）
◎ Header 仮ロゴ枠 / ClubName / Season / DataSourceLabel / HeaderNavRow 表示確認 OK（ユーザー環境 Godot 4.6.2）
◎ 本線 `home_dashboard` の `CardNews` に Theme を限定適用（`ed106c8`）
◎ CardNews 白カード表示・可読性・news 行数維持を確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に本線 CardNews 限定 Theme 適用の到達点を記録（`44b4957`）
◎ 本線 `home_dashboard` 次カード Theme 候補を調査（`b83a9d7`）
◎ 本線 `home_dashboard` の `CardNext` に Theme を限定適用（`8676095`）
◎ CardNext 白カード表示・可読性・`next_game` 表示維持を確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に本線 CardNext 限定 Theme 適用の到達点を記録（`75fc9cc`）
◎ 本線 `home_dashboard` 警告とタスクカードの Theme 候補を調査（`57a8ce6`）
◎ 本線 `home_dashboard` タスクカードの Theme 候補を調査（`00a235a`）
◎ 本線 `home_dashboard` の `CardWarnings` に Theme を限定適用（`762f5bc`）
◎ CardWarnings WarningCard 表示・可読性・`warnings` 表示挙動を確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に本線 CardWarnings 限定 Theme 適用の到達点を記録（`44bb145`）
◎ 本線 `home_dashboard` の `CardTasks` に Theme を限定適用（`d18bf1f`）
◎ CardTasks 白カード表示・可読性・tasks 最大 3 行表示維持を確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に本線 CardTasks 限定 Theme 適用の到達点を記録（`07bbf12`）
◎ 本線 `home_dashboard` MetricsRow の Theme 統一方針を調査（`ffb14f8`）
◎ 本線 `home_dashboard` の `CardRank` / `CardMoney` に Theme を限定適用（`2471b67`）
◎ MetricsRow 3 枚白カード統一・`rank_record` / `money` 表示維持を確認（ユーザー環境 Godot 4.6.2）
◎ README/docs に本線 MetricsRow 限定 Theme 適用の到達点を記録（`43136f9`）
◎ 残る暗色カード・`club_summary` 整理方針を調査（`307a7cc`・`e45321c`）
◎ 本線ホーム `club_summary` 状況メモ化（`91cfaed`）
◎ 本線ホーム `CardTeamExtras` Theme 限定適用（`dc0182a`）
◎ 本線ホーム `CardSummary` Theme 限定適用（`1d070ba`）
★ README/docs に状況メモ化とカード Theme 到達点を記録（`1afaacc`）
◎ 本線 `home_dashboard` に表示用 LeftRail を追加（`a5e548f`）
◎ 表示用 LeftRail・HeaderNavRow・CardNavMenu のローカル目視確認 OK（ユーザー環境 Godot・約 1216×684）
◎ 本線 `home_dashboard` の `CardNavMenu` に Theme を限定適用（`d9bd713`）
◎ CardNavMenu 白系化・4列・8ボタン・#7〜#10・遷移確認 OK（ユーザー環境 Godot・1280×720）
◎ 9詳細画面UI現状調査（`23a8fcf`・reports）
◎ 施設サマリー・Header+Summary Phase4 Theme 第1段（`5987821`）
◎ 施設サマリー・遷移・表示・戻り・可読性確認 OK（ユーザー環境 Godot）
□ 施設サマリー Scroll 動的Labelの第2段、または同型画面（クラブ史・順位表）への横展開判断
□ CardNews 1 行化の表示制御 / DTO 整理判断
□ Header 資金・成績行の本格移植判断
□ home DTO / JSON の追加整理
□ sandbox 中央カード密度の追加調整
□ sandbox 色・質感バリエーション追加試験
□ 本線 `home_dashboard` 中央カード密度の大移植判断
□ LeftRail クリック化・CardNavMenu 縮小の設計判断（表示用追加は `a5e548f` 済み）
□ 契約・人事サマリー・人事リスク / 主要契約選手（動的行・.gd）
□ ホーム全体への Theme 拡大（ルート一括など）
□ LeftRail クリック接続（別タスク。sandbox は引き続き研究可）
□ ホーム「データ更新」表示 / ボタン判断
□ Theme 全面適用（10 画面一括など）
```

関連コミット（Theme 周辺・必要最小限の列）: `26fa722`（preview）→ `b572a7e` / `88f5f52`（白ベース検証調整）→ `8bf6788` / `4c1cb08`（文字色調整）→ `b319af3` → `2995a22` → `77c5d04` → `310ebed` → `2bb594c`（ロスターヘッダー）→ `d33edb6`（ロスター表 OnDark）→ `afb482d`（ホーム Header のみ）。調査: `827e6f8`、`c0e018e`、`03494b8`、`2cb49ed`（`reports/` は追跡されない場合あり）。到達点の文書化: `c41a6f5` など。

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

### 契約 / 人事サマリー（第10画面）のファイル構成（参照）

| 種別 | パス |
|------|------|
| Python export | `basketball_sim/export/contract_personnel_summary_readonly.py` |
| pytest | `basketball_sim/tests/test_contract_personnel_summary_readonly_export.py` |
| Godot シーン / スクリプト | `scenes/contract_personnel_summary_view.tscn` / `scripts/contract_personnel_summary_view.gd` |
| スクリプト UID（エディタ） | `scripts/contract_personnel_summary_view.gd.uid` |
| 同梱 mock | `data/contract_personnel_summary_mock.json` |
| 手動生成 JSON（コミットしない） | `data/contract_personnel_summary_from_python.json` |
| 一括 export（10 件目） | `basketball_sim/export/godot_readonly_bundle.py`（`test_godot_readonly_bundle_export.py`） |

### 契約 / 人事サマリーの表示内容（JSON / DTO の目安）

- **セクション**: 契約概要、人事リスク（表示用の簡易目安）、主要契約選手、ロスター構成、注意
- **概要・項目**: ロスター人数、年俸合計、サラリーキャップ、サラリー余力、平均年俸、最高年俸、契約満了予定、FA 予備軍（`fa_shortlist` 件数など）、高年俸選手数、契約データ接続状況
- **選手行**: 選手名、POS、年齢、OVR / POT、年俸ラベル、契約残ラベル、契約状態、国籍枠ラベル、FA 目安、リスクラベル、メモ
- **ロスター構成**: PG〜C 人数、U23、30 歳以上、外国籍 / アジア枠概算 / 帰化 / 国内 など（データ不足時は「未接続」表記に倒す場合あり）

### 読込仕様（契約 / 人事サマリー）

- **`contract_personnel_summary_from_python.json` を優先**し、無い／読めないとき **`contract_personnel_summary_mock.json` にフォールバック**（`contract_personnel_summary_view.gd` の候補パス配列）。**Godot から Python 自動起動は未実装**。生成 JSON は **コミットしない**。

### 確認済み（ユーザー環境 Godot 4.6.2 の目安）

- ホーム → 戦術サマリー → ホーム、ホーム → オーナーミッション → ホーム、**ホーム → 契約・人事サマリー → ホーム**、**既存9画面往復**、**経営カテゴリ3ボタン表示**、**HeaderNavRow 未変更**（契約・人事は **経営** カード列のみ）、`from_python` 優先・mock フォールバック、**UID 参照エラー解消**、実行後の不要な追跡差分なし、など。
- **Python 一括 export**（`godot_readonly_bundle`）を **PowerShell から手動実行**し、**10 件すべて `Wrote` → `Bundle complete: 10 succeeded, 0 failed`**、生成 10 JSON が **`git status --ignored` で `!!`（ignored）**、通常の `git status --short` は **handoff 未追跡のみ**、まで確認済み（一括 10 本目: `61cc09a`）。

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
  ◎ 契約 / 人事サマリー 第10画面
  ◎ 10画面のPython readonly DTO / JSON足場
  ◎ 10画面のGodot mock表示
  ◎ Python生成JSON優先読込
  ◎ ホームカード型メニュー経由の遷移
  ◎ Python自動JSON生成設計調査
  ◎ Python一括exportコマンド追加（10件）
  ◎ ユーザー環境で一括export確認（10 succeeded）
  ◎ README/docsに一括export運用を記録
  ◎ 共通Theme preview・白ベース検証版（`phase4_readonly_core.tres` / `theme_preview.tscn`）
  ◎ 契約・人事サマリーへのTheme限定適用（ヘッダー・契約概要・ロスター構成・注意）
  ◎ ロスター閲覧ヘッダーへのTheme限定適用
  ◎ ロスター表OnDark（動的Label・.gd）
  ◎ ホームHeaderのみTheme限定適用（.tscn・MetricsRow/Scroll以下のTheme適用以外は従来）
  ◎ ホームMetricsRow CardDivision/CardRank/CardMoneyのみPhase4SummaryCard限定適用（`f66bcd2`・`2471b67`）
  ◎ ホームScroll以下CardNews/CardNext/CardTasksのみPhase4SummaryCard限定適用（`ed106c8`・`8676095`・`d18bf1f`）
  ◎ ホームScroll以下CardWarningsのみPhase4WarningCard限定適用（`762f5bc`）
  ◎ README/docs Theme展開の到達点記録（過去コミット）
  ◎ 本番ホームワイヤーsandbox（`home_production_wire_preview.tscn`・F6単体）
  ◎ sandbox方針整理（レポート）
  ◎ README/docsへsandbox位置づけ記録
  ◎ sandbox左レールをカテゴリナビ風に調整（現在地ホーム強調）
  ◎ sandbox ClubBandに仮クラブロゴ枠（SG/LOGO）を追加
  ◎ sandbox左レール現在地アクセント調整（ロゴ枠琥珀系に馴染む最小変更）
  ◎ sandbox CardShortcuts を1行へ圧縮
  ◎ ClubBandと中央カードの情報重複を調査
  ◎ sandbox順位カード本文を立ち位置判断文へ変更
  ◎ sandbox中央カード（タスク／ニュース／クラブ状態）の役割調査
  ◎ sandbox CardNewsを1行ヘッドラインへ短縮
  ◎ sandbox CardClubStateを1行要約へ短縮
  ◎ sandbox色・質感候補調査（レポート）
  ◎ README/docs へ sandbox のクラブ状態短縮到達点を記録
  ◎ 右サマリー列あり版の調査
  ◎ 右サマリー比較scene追加（`home_production_wire_preview_right_summary.tscn`）
  ◎ 右サマリー比較sceneのUID問題を調査（`a8b4a1d`）
  ◎ 右サマリー比較sceneのUIDを安定化（`cf8012c`）
  ◎ 右サマリー比較sceneのF6表示確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docs に右サマリー比較の確認結果を記録（本命は現行2カラム版寄り）
  ◎ 本線home_dashboardへの段階移植方針を調査（`a2feb4e`）
  ◎ 本線home_dashboard中央カード密度の移植方針を調査（`c9e4474`）
  ◎ 本線home_dashboard HeaderCardにクラブ帯要素を最小追加（`83d7fc0`）
  ◎ README/docsに本線Headerクラブ帯要素の到達点を記録（`a7be5d7`）
  ◎ Header仮ロゴ枠 / ClubName / Season / DataSourceLabel / HeaderNavRow 表示確認OK（ユーザー環境 Godot 4.6.2）
  ◎ 本線home_dashboardのCardNewsにThemeを限定適用（`ed106c8`）
  ◎ CardNews白カード表示・可読性・news行数維持を確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docsに本線CardNews限定Theme適用の到達点を記録（`44b4957`）
  ◎ 本線home_dashboard次カードTheme候補を調査（`b83a9d7`）
  ◎ 本線home_dashboardのCardNextにThemeを限定適用（`8676095`）
  ◎ CardNext白カード表示・可読性・next_game表示維持を確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docsに本線CardNext限定Theme適用の到達点を記録（`75fc9cc`）
  ◎ 本線home_dashboard警告とタスクカードのTheme候補を調査（`57a8ce6`）
  ◎ 本線home_dashboardタスクカードのTheme候補を調査（`00a235a`）
  ◎ 本線home_dashboardのCardWarningsにThemeを限定適用（`762f5bc`）
  ◎ CardWarnings WarningCard表示・可読性・warnings表示挙動を確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docsに本線CardWarnings限定Theme適用の到達点を記録（`44bb145`）
  ◎ 本線home_dashboardのCardTasksにThemeを限定適用（`d18bf1f`）
  ◎ CardTasks白カード表示・可読性・tasks最大3行表示維持を確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docsに本線CardTasks限定Theme適用の到達点を記録（`07bbf12`）
  ◎ 本線home_dashboard MetricsRowのTheme統一方針を調査（`ffb14f8`）
  ◎ 本線home_dashboard CardRank/CardMoneyにThemeを限定適用（`2471b67`）
  ◎ MetricsRow 3枚白カード統一・rank_record/money表示維持を確認（ユーザー環境 Godot 4.6.2）
  ◎ README/docsに本線MetricsRow限定Theme適用の到達点を記録（`43136f9`）
  ◎ 残る暗色カード・club_summary整理方針を調査（`307a7cc`・`e45321c`）
  ◎ 本線ホームclub_summary状況メモ化（`91cfaed`）
  ◎ 本線ホームCardTeamExtras Theme限定適用（`dc0182a`）
  ◎ 本線ホームCardSummary Theme限定適用（`1d070ba`）
  ★ README/docsに状況メモ化とカードTheme到達点を記録（本コミット）
◎ CardNavMenu Theme化済み・導線維持（`d9bd713`）
□ CardNews1行化の表示制御 / DTO整理判断
□ Header資金・成績行の本格移植判断
□ home DTO / JSON の追加整理
□ sandbox中央カード密度の追加調整
□ sandbox色・質感バリエーション追加試験
□ 本線home_dashboard中央カード密度の大移植判断
□ home DTO / JSON の追加整理
□ LeftRail クリック化・CardNavMenu 縮小の設計判断（表示用追加は `a5e548f` 済み）
□ 契約・人事サマリー・動的行（人事リスク・主要契約選手）のTheme／色整理（.gd 前提）
□ ホーム・Scroll以下カードのTheme／本番ビジュアル調整
□ Theme全面適用（10画面一括・ルート一括など）
□ ホーム「データ更新」表示/ボタン判断
□ 本格ナビ次段階 / 左サイドメニュー設計（本線・sandboxは別。本線はHeaderNavRow維持）
□ 第11画面を増やすかの判断（慎重）
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

- Godot から Python を **自動起動して JSON を生成する**こと（**一括 export は PowerShell 等から手動実行する Python CLI のみ**。**ホームの「データ更新」ボタンや画面遷移トリガによる自動起動は未実装**）
- Godot から **ゲーム進行**すること
- Godot から **セーブ / ロード**すること
- Godot から **人事・経営・強化・戦術**や **施設投資・施設レベルアップ**などの操作をすること
- **`Offseason.run()` を Godot から呼ぶ**こと
- **本格ナビゲーション**（左メニュー統合・画面管理の一本化など）
- **財務画面・オーナーミッション画面・戦術サマリー画面の本格ビジュアル調整**（現状は読み取りプロトタイプ優先）
- **ミッション生成・評価更新・報酬付与・オーナー評価の操作 UI**
- **戦術変更・ローテーション保存・先発変更・出場時間変更・戦術プリセット選択 UI**
- **契約更新・契約交渉・獲得・解雇・FA 操作などの契約 / 人事系操作 UI**（契約・人事サマリー画面は **閲覧のみ**）
- **ホームに「データ更新」ボタンを置き、Godot から Python export を起動する**こと（**未実装**。現状は **ターミナルで `godot_readonly_bundle` を手動実行**する運用）
- **画面遷移の直前に個別 export を自動実行する**こと（未実装）
- **配布用に export 専用 exe を同梱し Godot から起動する**こと（未実装）
- **`generated_at` を全 DTO に一斉追加する**こと、**Godot 側で JSON の更新時刻だけを常時表示する**こと（未実装・要別判断）
- **契約 / 人事サマリー画面の本格ビジュアル調整**（現状は読み取りプロトタイプ優先）
- **10 画面すべてへの共通 Theme の一括適用**、**ホームの Scroll 以下まで含む全体 Theme 化**（**限定適用の検証段階**。ホーム Scroll 以下は **Summary / Warning 系で白カード化済み**（**`CardNavMenu` 含む・`d9bd713`**）。**詳細9画面の Theme 展開は未着手**）
- **本番ホームワイヤー sandbox**（`scenes/home_production_wire_preview.tscn`）および **右サマリー比較scene**（`scenes/home_production_wire_preview_right_summary.tscn`）を **本線ホームに自動接続**すること（**script なし・JSON なし・本線遷移なし**。研究・比較用。詳細は「本番ホームワイヤー sandbox」「右サマリー列あり版」節）
- **Godot 本番 GUI の一本化**

## ファイル構成（抜粋）

| パス | 役割 |
|------|------|
| `project.godot` | Godot 4.x プロジェクト設定。メインシーンは `scenes/home_dashboard.tscn` |
| `scenes/home_dashboard.tscn` / `scripts/home_dashboard.gd` | ホームレイアウト・JSON 表示 |
| `scenes/home_production_wire_preview.tscn` | **本番ホームワイヤー sandbox**（script なし・固定文言・F6 単体。本線とは別） |
| `scenes/home_production_wire_preview_right_summary.tscn` | **右サマリー列あり版の比較scene**（script なし・固定文言・F6 単体・本線未接続。レイアウト判断は README「右サマリー列あり版」節） |
| `scenes/roster_view.tscn` / `scripts/roster_view.gd` | ロスター閲覧・JSON 表示 |
| `scenes/club_history_view.tscn` / `scripts/club_history_view.gd` | クラブ史閲覧・JSON 表示 |
| `scenes/standings_view.tscn` / `scripts/standings_view.gd` | 順位表（リーグ状況）閲覧・JSON 表示 |
| `scenes/schedule_view.tscn` / `scripts/schedule_view.gd` | 日程（スケジュール）閲覧・JSON 表示 |
| `scenes/facility_summary_view.tscn` / `scripts/facility_summary_view.gd` | 施設サマリー閲覧・JSON 表示 |
| `scenes/finance_summary_view.tscn` / `scripts/finance_summary_view.gd` | 財務サマリー閲覧・JSON 表示 |
| `scenes/owner_mission_view.tscn` / `scripts/owner_mission_view.gd` | オーナーミッション閲覧・JSON 表示 |
| `scenes/tactics_summary_view.tscn` / `scripts/tactics_summary_view.gd` | 戦術 / ローテーションサマリー閲覧・JSON 表示 |
| `scenes/contract_personnel_summary_view.tscn` / `scripts/contract_personnel_summary_view.gd` | 契約 / 人事サマリー閲覧・JSON 表示 |
| `themes/phase4_readonly_core.tres` | 共通 Theme（白ベース検証版）。**限定適用中の画面のみ**が参照 |
| `scenes/theme_preview.tscn` | Theme 確認用プレビュー（**本番 10 画面には未適用**） |
| `data/home_dashboard_mock.json` 等 | 各画面の **同梱モック**（正本データではない） |
| `data/*_from_python.json` | **任意**。CLI で生成する開発用 JSON（無ければ mock） |

## 開き方

1. [Godot 4.2 以降](https://godotengine.org/) をインストールする（本リポジトリでは **Godot 4.6.2** での動作確認実績あり）。
2. Godot エディタで **「プロジェクトを編集」** から、この `godot/` フォルダを選ぶ（`project.godot` が入っているディレクトリ）。
3. 実行（F5）でメインシーン（ホーム）が開き、各画面の **優先順** で JSON が読み込まれれば成功です。
4. ロスター／クラブ史／**順位表**／**日程**／**施設サマリー**／**財務サマリー**／**オーナーミッション**／**戦術サマリー**／**契約・人事サマリー**からホームへ戻るときは、各画面上部の **「ホームへ戻る（表示のみ）」** を使います（ホームへ戻る目的でプロジェクト全体を再実行する必要はありません）。

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

**ロスター**・**クラブ史**・**順位表**・**日程**・**施設サマリー**・**財務サマリー**・**オーナーミッション**・**戦術サマリー**・**契約・人事サマリー**も同様に、`basketball_sim.export.roster_readonly` / `club_history_readonly` / **`standings_readonly`** / **`schedule_readonly`** / **`facility_summary_readonly`** / **`finance_summary_readonly`** / **`owner_mission_readonly`** / **`tactics_summary_readonly`** / **`contract_personnel_summary_readonly`** で `godot/data/roster_from_python.json` / `club_history_from_python.json` / **`standings_from_python.json`** / **`schedule_from_python.json`** / **`facility_summary_from_python.json`** / **`finance_summary_from_python.json`** / **`owner_mission_from_python.json`** / **`tactics_summary_from_python.json`** / **`contract_personnel_summary_from_python.json`** を生成して配置します（**まだ Godot から自動実行しません**）。

財務サマリーは履歴件数を変える場合: `--max-history 8` など（既定 5）。**戦術サマリー**と**契約・人事サマリー**は選手行の上限など: `--max-players 8` など（エクスポート CLI のヘルプを参照。一括 `godot_readonly_bundle` でも同じ `--max-players` が両方に渡る）。

- 生成物は **開発用** です。**Git にコミットしない**でください（上記 **10** 種の `*_from_python.json` は `godot/.gitignore` で除外）。

### 10画面分の `*_from_python.json` を一括生成（Python のみ・手動）

**位置づけ**: `basketball_sim.export.godot_readonly_bundle` は **Python 側だけ**の CLI です。**Godot が Python を自動起動する処理ではありません**。Phase 4 時点では **PowerShell（またはターミナル）から手動で実行**し、`godot/data/` に **10 ファイルまとめて**書き出してから Godot エディタで各画面を開く運用です（**自動更新パイプラインの完成ではない**）。

**標準形**（リポジトリルートで、`--save` と `--output-dir` を環境に合わせて置き換え）:

```powershell
py -m basketball_sim.export.godot_readonly_bundle --save <path\to\your.sav> --output-dir godot\data
```

**ユーザー環境で確認済みの例**（財務・オーナーミッション・戦術の件数上限を揃えたい場合の任意引数付き）:

```powershell
py -m basketball_sim.export.godot_readonly_bundle --save "$env:USERPROFILE\.basketball_sim\saves\debug_user_boost_d1_user_cellb.sav" --output-dir "godot\data" --max-history 8 --max-missions 8 --max-players 8
```

**`--output-dir` に書き出す固定ファイル名（10 件）**:

- `home_dashboard_from_python.json`
- `roster_from_python.json`
- `club_history_from_python.json`
- `standings_from_python.json`
- `schedule_from_python.json`
- `facility_summary_from_python.json`
- `finance_summary_from_python.json`
- `owner_mission_from_python.json`
- `tactics_summary_from_python.json`
- `contract_personnel_summary_from_python.json`

**Godot 側の読込**: 各画面は引き続き **`res://data/<上記ファイル名>` を優先**し、無ければ同梱の `*_mock.json` にフォールバックします。

**成功時のコンソール例**: 10 行の `Wrote ...` のあと `Bundle complete: 10 succeeded, 0 failed`。

**git 運用（生成物はコミットしない）**: `godot/.gitignore` により `*_from_python.json` は **ignored**。生成後に次のように **10 パスすべて `!!`** になることを確認できる（`facility_summary` は **1 回だけ**列挙）:

```powershell
git status --short --ignored -- godot/data/home_dashboard_from_python.json godot/data/roster_from_python.json godot/data/club_history_from_python.json godot/data/standings_from_python.json godot/data/schedule_from_python.json godot/data/facility_summary_from_python.json godot/data/finance_summary_from_python.json godot/data/owner_mission_from_python.json godot/data/tactics_summary_from_python.json godot/data/contract_personnel_summary_from_python.json
```

通常の `git status --short` では、生成 JSON は **表示されない**想定です（未追跡の handoff ドキュメントのみ出ることがある）。

**実装参照**: `8822b87`（一括 export 追加）、`61cc09a`（10 本目・契約・人事サマリー追加）。設計調査メモ: `reports/godot_phase4_python_auto_export_design_2026-05.txt`（**参照用**。当該 `reports/*.txt` はルート `.gitignore` により追跡されない場合がある）。

**まだ未実装**（本節の範囲外・誤解防止）: **Godot から Python を自動起動する処理**、**ホームの「データ更新」ボタン**、**画面遷移直前の個別 export**、**配布用 exe 化**、**`generated_at` の全 DTO 一斉追加**、**Godot で JSON 更新時刻のみ常時表示**。

**次工程候補（メモ）**: ホーム「データ更新」ボタンは **検討段階**（未実装）。本格ナビ・Godot 本番 GUI 一本化・**第11画面の要否判断**は **後工程**。

### 通常の動き

- **`*_from_python.json` を置いていない**場合は、従来どおり **同梱の `*_mock.json`** が読まれます。

## 将来（第2弾以降の想定）

- 読み込み候補パスは各 `scripts/*.gd` の **候補パス配列**にまとめてあります。
- 表示内容の正本・項目定義は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` の §4 / §10 / **§15（Phase 4 初期プロトタイプ到達点）** / **§15.1（Theme 検証・限定適用）** を参照してください。

## エディタ生成ファイル

`.godot/` はローカルキャッシュのため **Git 対象外**（`godot/.gitignore`）です。
