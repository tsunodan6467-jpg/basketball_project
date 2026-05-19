# Godot本格ナビゲーション方針メモ（Phase 4 / 2026-05）

## 1. この文書の位置づけ

- この文書は **Phase 4 / Godot 本番 GUI 準備**の段階で、**ナビゲーション（画面の切り替え方・整理の考え方）**をメモしたものです。**実装の仕様書ではありません。** あとから段階的に本格ナビへ移すときの **方針のたたき台** として使います。
- いまの Godot 側は **読み取り専用のプロトタイプ**（**仮 GUI 導線**）です。**Phase 4 初期の足場** であり、本番 GUI が「完成した」とはみなしません。
- **未実装**（別タスク・後工程）なものの例: Godot から Python を **自動起動** すること、本番の **セーブ／ロード** 接続、**状態を変える操作 UI**（進行・契約・編成など）、**本格ビジュアル**（ロゴ・イラスト・装飾の本制作）。
- **Steam 向けの本番 GUI** は見据えつつ、**いま優先するのは安全にデータを表示する足場**です。ナビの「最終形の細部」は **未確認** のまま残す余地があります（あとで設計を詰める）。

## 2. 現在の到達点

次の **10 画面**まで、**Python の DTO → JSON → Godot で表示** の形でつながっています。

| 画面 | ざっくりした役割 |
|------|------------------|
| ホーム | クラブ状況のサマリー。**いまの仮ハブ**（ここから他画面へ） |
| ロスター | いまのチーム編成の **閲覧** |
| クラブ史 | 長く遊んだ結果の蓄積の **閲覧** |
| 順位表 / リーグ状況 | リーグ内の順位などの **閲覧** |
| 日程 / スケジュール | 次の試合や予定の **閲覧**（第1弾の範囲。細部は情報設計ドキュメント側を正とする） |
| 施設サマリー | アリーナ・練習・メディカル・フロントオフィス・施設強化ポイントなどの **閲覧**（読み取り専用第1弾。**施設投資・レベルアップ・施設プロジェクト制は未接続**） |
| 財務 / 経営サマリー | 資金・前季収支・サラリー枠・財務履歴などの **閲覧**（読み取り専用第1弾。**予算変更・投資・契約更新などの操作は未接続**） |
| オーナーミッション / クラブ評価 | オーナー信頼・今季ミッション・進捗・報酬/ペナルティ・クラブ評価などの **閲覧**（読み取り専用第1弾。**ミッション生成・評価更新・報酬付与などの操作は未接続**） |
| 戦術 / ローテーションサマリー | 戦術プリセット・プレイスタイル・攻守方針・ローテーション方針・先発/目標分数・選手ロールなどの **閲覧**（読み取り専用第1弾。**戦術変更・ローテーション保存・先発変更・出場時間変更などの操作は未接続**） |
| 契約 / 人事サマリー | 契約状況・人事リスク・年俸バランスの **閲覧**（読み取り専用第1弾。**契約交渉画面ではない**。**契約更新・交渉・獲得・解雇・FA 操作などの UI は未接続**。財務サマリー（クラブ資金・収支）やロスター表とは役割が異なる） |

- 各画面とも **`…_from_python.json` を優先**し、無い・壊れているときは **同梱の mock JSON にフォールバック** する運用です。
- **10 画面分の `*_from_python.json` をまとめて更新**するときは、Python モジュール **`basketball_sim.export.godot_readonly_bundle`** を **リポジトリルートから手動実行**します（**Godot が Python を起動する処理ではありません**）。PowerShell の具体例・出力ファイル名・`git status --ignored` の確認例は **`godot/README.md`** の **「10画面分の `*_from_python.json` を一括生成（Python のみ・手動）」** 節を正とします。
- **ホーム → 各サブ画面**、**各サブ画面 → ホーム** の往復ができます。
- 画面の切り替えは **`change_scene_to_file` のみ** です（共通のナビ部品や自動起動はありません）。
- **進行・保存・編集などのゲーム操作は接続していません**（表示だけ）。

### 2.1 共通 Theme（白ベース検証・限定適用）

- **共通 Theme**（`godot/themes/phase4_readonly_core.tres`）と **preview**（`godot/scenes/theme_preview.tscn`）で **見た目を検証中**。**10 画面への一括適用**や **ホームの Scroll 以下の全面 Theme 化**は **していない**（**限定適用の段階**）。
- **契約 / 人事サマリー**: **Theme 残り第1段**（`5d1afa2`）＋**RiskRows / PlayerRows 動的行文字色最小補正**（`1df4820`）＋**第2段（最小）PlayerRows 行区切り**（`6b26fa3`）＋**第2段（最小）RiskRows 行区切り**（`97b26a8`）— §2.12 / §2.12a / §2.12b。
- **ロスター閲覧**: **Theme 第1段**（`f866f5b`・**`roster_view.tscn` のみ**）＋**表 Theme 通常 Table 化**（`407f014`・**`roster_view.gd` のみ**）＋**第2段（最小）RowList 選手行間 HSeparator**（`8a95fcf`・**`_apply_snapshot` players ループのみ**）。**`Scroll/TableCard`** の Phase4 化 ＋ **`Phase4TableHead` / `Phase4TableCell`**（§2.13 / §2.13a）。
- **施設サマリー閲覧**: **Theme 第1段**（`5987821`・**`facility_summary_view.tscn` のみ**）。**Header + Summary** の Phase4 化。**Scroll 動的本文は未変更**（§2.5）。
- **クラブ史閲覧**: **Theme 第1段**（`682a941`・**`club_history_view.tscn` のみ**）。**Header + Summary** の Phase4 化。**Scroll 内段落・シーズン表は未変更**（§2.6）。
- **順位表閲覧**: **Theme 第1段**（`927e918`・**`standings_view.tscn` のみ**）。**Header + Summary** の Phase4 化。**Scroll 内 8 列表・動的行は未変更**（§2.7）。
- **日程閲覧**: **Theme 第1段**（`440c3f6`）＋**第2段・前半**（`986c4ab`）＋**第2段・後半（最小）**（`7fecb99`）＋**追加最小 advance_hint**（`a62b3a7`・**なし/あり表示確認済み**）＋**追加最小 empty_message**（`463e74b`）＋**追加最小「今後の予定」見出し**（`a24cf6f`）＋**追加最小 upcoming 試合間 HSeparator 整理**（`a9fa054`）。**導線は HeaderNavRow + CardNavMenu から到達**（§2.8〜2.8g）。**LeftRail からは遷移しない**。
- **財務サマリー閲覧**: **Theme 第1段**（`4b43da5`）＋**履歴行文字色最小補正**（`6c3dc43`）＋**第2段（最小）HistoryBody 行区切り**（`d57b021`）＋**Body本格・最小 HistoryBody 内側余白**（`307e719`・**`_fill_history_rows` のみ** — §2.9a / §2.9b）。**`%HistoryBody` 構造全面整理は別タスク**。
- **オーナーミッション / クラブ評価閲覧**: **Theme 第1段**（`e6acce0`）＋**今季ミッション動的行文字色最小補正**（`2f808e5`）＋**第2段（最小）MissionsBody 行区切り**（`5a3ae2c`）＋**Body本格・最小 MissionsBody 内側余白**（`d4c0372`・**`_fill_mission_rows` のみ** — §2.10a / §2.10b）。**`%MissionsBody` 構造全面整理は別タスク**。
- **戦術 / ローテーションサマリー閲覧**: **Theme 第1段**（`44b0584`）＋**選手ロール動的行文字色最小補正**（`7bbbb4e`）＋**第2段（最小）PlayerRolesBody 行区切り**（`c9216d0`）＋**Body本格・最小 PlayerRolesBody 内側余白**（`2c637f2`・**`_fill_player_roles` 選手ロール行追加ループのみ** — §2.11a / §2.11b）。**`%PlayerRolesBody` 構造全面整理は別タスク**。
- **契約 / 人事サマリー閲覧**: **Theme 残り第1段**（`5d1afa2`）＋**RiskRows / PlayerRows 動的行文字色最小補正**（`1df4820`）＋**第2段（最小）PlayerRows 行区切り**（`6b26fa3`）＋**Body本格・最小 PlayerRows 内側余白**（`f19ed9b`・**`_fill_player_rows` 主要契約選手行追加ループのみ** — §2.12a / §2.12c）＋**第2段（最小）RiskRows 行区切り**（`97b26a8`・**`_fill_risk_rows` のみ** — §2.12b）。**RiskCard / PlayersCard** の Phase4 化。**契約・人事の PlayerRows / RiskRows 最小行区切りは両方完了**（§2.12 / §2.12a / §2.12b）。
- **ロスター閲覧**: **Theme 第1段**（`f866f5b`・**`roster_view.tscn` のみ**）＋**表 Theme 通常 Table 化**（`407f014`・**`roster_view.gd` のみ**）＋**第2段（最小）RowList 選手行間 HSeparator**（`8a95fcf`）。**`TableCard` + 9列表** の Phase4 化（**Header は既に Phase4 済み**）。**表行 Panel 化・行レイアウト本格調整は未変更**（§2.13 / §2.13a）。
- **ホーム**: **`HeaderCard` のみ**に Theme（**ルート `HomeDashboard` には付けない**）。**MetricsRow** 3 枚 + **`Scroll` 以下**（**`CardNavMenu` 含む**）**`Phase4SummaryCard` / `Phase4WarningCard`**（**`d9bd713` で `CardNavMenu` も Summary 化済み** — §2.3）。**`club_summary` は `91cfaed` で状況メモ化済み**（export/mock）。**Scroll 内の暗色カード問題は解消済み**。**HeaderNavRow** は **ボタン数・接続・遷移先不変**。
- **本線 LeftRail**: **`a5e548f` で表示用のみ追加済み**（§2.4）。**クリック・遷移は未実装**。**実操作導線**は引き続き **HeaderNavRow + CardNavMenu**。
- **本格ナビの全面実装**（LeftRail クリック化・CardNavMenu 整理等）は **未着手**（§10）。**第 11 画面を急いで増やすより**、いまは **本番 GUI 化の足場**（Theme 限定適用・読み取り導線の安定）を優先する段階、という整理でよい（優先度の最終判断はチーム）。
- 詳細・ロードマップ・運用は **`godot/README.md` の「共通 Theme / 白ベース検証」** と **`docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md` §15.1 / §15.2** を参照。

### 2.2 本番ホームワイヤー sandbox（左サイドナビ研究）

- **本線の左サイドナビ**: **`a5e548f` で表示用 `LeftRail` を追加済み**（§2.4）。**クリック・遷移・script はなし**。**実操作導線**は **`HeaderNavRow`（5 ボタン）＋`CardNavMenu`（画面メニュー）**（§3）。**`HeaderNavRow` は本線で当面維持**。
- **`godot/scenes/home_production_wire_preview.tscn`**: **左サイドナビ（大分類）と上部クラブ帯・中央カード密度・情報の役割分担**を研究する **sandbox**（script なし・固定文言・**F6 で単体実行**）。**`project.godot` の `run/main_scene` は変更しない**（`godot/README.md`「本番ホームワイヤー sandbox」節）。
- **大分類の試験**: sandbox 上では **ホーム / チーム / リーグ / 経営 / クラブ**。**最新（2026-05）**では左レールが**カテゴリナビ風**になり、**現在地「ホーム」**が強調されている（見た目のみ。クリック・遷移なし）。
- **10 画面を左に全部並べない**方針のもと、**大分類＋中央カードで選ぶ**方向を sandbox で検証中（**HeaderNavRow は本線で維持**。全面左ナビ化は未着手）。
- **ClubBand** に **SG / LOGO** の**仮クラブロゴ枠**（実画像なし）を置き、**上部クラブ帯**の方向性も並行して検証中。
- **左レール現在地アクセント**は、ロゴ枠の琥珀系に**馴染む**よう **SubResource のみ**で**最小調整**済み（本線の `HeaderNavRow` とは独立）。
- **CardShortcuts** は **2 行から 1 行**へ圧縮済み。左レール大分類との**役割重複を軽減**（補助案内ラベルは維持）。
- **中央の「順位・成績」カード**は、ClubBand と同じ地区／勝敗／順位を**繰り返さない**よう、本文を**立ち位置判断文**（例: **`PO圏まで 2.0差 / 直近5試合 3勝2敗`**）へ変更済み。**タスクカード**（実行する行動の列挙）とは役割を分離。
- **CardNews** の本文（`CardNewsBody`）は **`ホーム快勝、次戦へ弾み`** の **1 行ヘッドライン**へ短縮済み。右列の**情報密度を下げ**、**CardTasks** が**主役**として見えやすい整理（ニュースは**雰囲気**として軽く残す）。
- **CardClubState** の本文（`CardClubBody`）は **`サラリー余力あり / 士気良好`** の **1 行要約**へ短縮済み。ClubBand の**資金・オーナー信頼**と**重く被らない**よう整理済み。
- **ユーザー環境 Godot 4.6.2** で sandbox 表示確認済み、**UID 参照エラーなし**、**実行後の不要な追跡差分なし**（手元運用の目安。README「本番ホームワイヤー sandbox」節と整合）。
- **本線 `home_dashboard.tscn` の HeaderCard 内**に、sandbox **ClubBand** 風のクラブ帯要素を**最小追加済み**（`83d7fc0`）。**`HeaderClubBandRow`・`HomeLogoSlot`（`SG` / `LOGO`）・`HeaderBandTextCol`**。既存 **`ClubNameLabel` / `SeasonLabel` / `DataSourceLabel`** は **ノード名と `unique_name_in_owner` を維持**。**`DataSourceLabel` に `autowrap_mode = 2`**。**`HeaderNavRow` 5 ボタン・connection・遷移先は変更なし**。**`home_dashboard.gd` 未変更**。**今回の変更は Header 内の見た目寄せであり、ナビ構造の移行ではない**。**中央 2 カラム・右サマリー列の本線移植**は**別タスク**。**右サマリー比較scene**も**本線未接続の参考案**。
- **本線 `home_dashboard.tscn` の Scroll 以下**では、**HeaderCard の ClubBand 風寄せ**（`83d7fc0`）に続き、**`CardNews`（`ed106c8`）・`CardNext`（`8676095`）・`CardWarnings`（`762f5bc`）・`CardTasks`（`d18bf1f`）**の限定 Theme 適用に加え、**MetricsRow の `CardRank` / `CardMoney`（`2471b67`）**にも **`Phase4SummaryCard`** を限定適用済み。**`CardDivision` / `CardRank` / `CardMoney` の MetricsRow 3 枚が白カード系で統一**された。**ナビ構造の変更ではない**。**`rank_record` / `money` の表示ロジック**・**`tasks` の本文・最大 3 行表示**（**`_join_lines(d, "tasks", 3)`**）・**`news` / `next_game` / `warnings` の表示ロジック**・**from_python / mock 経路は不変**（**`home_dashboard.gd` 不変**）。**HeaderNavRow は本線で維持**。**`a5e548f` で表示用 LeftRail を追加**（§2.4・**クリック化は未着手**）。**右サマリー比較scene は本線未接続の参考案**。**`CardWarnings`＝警告・リスク、`CardTasks`＝行動・ToDo** の分界を維持。**sandbox の `CardNewsBody` 級の 1 行ヘッドライン本格導入**は **`.gd` または `news_headline` 等の DTO** を**別タスク**で検討。**本線移行は今後も小さなコミット単位**で行う。
- **`godot/scenes/home_production_wire_preview_right_summary.tscn`**: **右サマリー列あり版**の**比較scene**として追加済み。**Godot 4.6.2** で UID 問題解消後の **F6 表示確認済み**。ただし 1280×720 では**中央が詰まりやすく**、**現時点では本命ではない**。**本命候補は左レール＋ClubBand＋中央 2 カラムの現行 sandbox**（`home_production_wire_preview.tscn`）。右サマリー列あり版は**将来の情報密度比較・参考画像寄せ**のための**参考案**として残す。**本線移行は別タスク・別コミット**。
- **本線への取り込み**は **別タスク・別コミット**（本書 §10「左サイドメニューの全面実装」はいま着手しない方針と整合）。

### 2.3 本線 `CardNavMenu`（Theme 化済み・導線維持）

- **到達点（`d9bd713`）**: **`home_dashboard.tscn` のみ**。**`CardNavMenu`** に `theme` + **`Phase4SummaryCard`**。**`StyleBoxFlat_card` の panel override のみ除去**（**SubResource 定義は削除せず残置**）。**ラベル**（`NavTitle` / カテゴリラベル等）を白カード向け濃色。**8 ボタン・4 列・14 connection・9 handler 名は不変**。**削除・縮小なし**。
- **役割（現在形）**: **ホーム除く詳細画面**への**中央の実操作用画面メニュー**（§3）。**HeaderNavRow 5 ボタンと一部重複**するが、**#7〜#10**（財務サマリー・オーナーミッション・戦術サマリー・契約・人事サマリー）は**主にこちらから遷移**。**当面は中央画面メニューとして維持**。
- **未変更**: **`home_dashboard.gd`**、**Theme `.tres`**、**export / mock JSON**。
- **ユーザー環境 Godot（ローカル目視・1280×720）**: **大きなレイアウト崩れなし**。**CardNavMenu 白系カード化**（Scroll 内の**唯一暗色カード状態は解消**）。**4 列表示成立**。**8 ボタン視認 OK**。**#7〜#10 入口表示 OK**。**CardNavMenu 遷移 OK**。
- **今後の判断**（**LeftRail クリック化は別タスク**）:
  - **CardNavMenu** は当面 **#7〜#10 を含む画面選択導線**として維持（**削除・縮小はしない**）。
  - **HeaderNavRow へ統合・カード縮小**や**左レール本線化時の置換**は、**大分類と複数詳細画面の対応**を設計してから**別タスク**。
- **関連コミット**: **`dc0182a`**（`CardTeamExtras`）、**`1d070ba`**（`CardSummary`）、**`a5e548f`**（表示用 LeftRail・connection パス更新のみ）、**`d9bd713`**（`CardNavMenu` Theme）。

### 2.4 本線 表示用 LeftRail（`a5e548f`）

- **到達点**: **`home_dashboard.tscn` のみ**。**`StatusLabel` 直下**に **`MainRow`（HBox）** を挿入。**左** `LeftRail`（**200px**）・**右** 既存 **`Scroll`**。**`HeaderCard` / `StatusLabel` / `FooterNote` は全幅維持**。
- **LeftRail の役割**: **現在地・大分類の視覚ナビ**（**ホーム**＝現在地強調、**チーム / リーグ / 経営 / クラブ**）。**表示のみ** — **Panel + Label**、**`mouse_filter = 2`**、**Button / `[connection]` / `home_dashboard.gd` なし**。注記 **「表示のみ / 詳細は中央メニュー」**。
- **HeaderNavRow**: **主要 5 画面**（ロスター・クラブ史・順位表・日程・施設サマリー）への**上部導線**として**維持**。**ユーザー環境 Godot（ローカル目視・約 1216×684）で遷移 OK**。
- **CardNavMenu**: **ホーム除く詳細画面**への**中央の実操作用画面メニュー**として**維持**（**`d9bd713` で `Phase4SummaryCard` 化済み**。**#7〜#10 の主入口を含む**。**8 ボタン・4 列・connection / handler 不変**）。**ユーザー環境 Godot（ローカル目視・1280×720）で遷移 OK**。
- **LeftRail と遷移**: **意図的にクリック不可**。**LeftRail から画面遷移できないのが正しい**（**LeftRail 遷移 OK とは書かない**）。
- **役割分担（現在形）**: **HeaderNavRow**＝上部主要 5 導線。**CardNavMenu**＝**実操作用**の画面選択メニュー（二重 5 導線＋#7〜10 専用入口）。**LeftRail**＝大分類・現在地の**視覚ナビ**（**表示のみ**・操作ナビではない）。
- **未変更**: **`home_dashboard.gd`**、**Theme `.tres`**、**export / mock JSON**。
- **ユーザー環境 Godot（ローカル目視・スクショ約 1216×684）**: **大きなレイアウト崩れなし**。**HeaderCard 全幅**・**LeftRail 左表示**・**CardNavMenu 4 列**・**MetricsRow 以降**・**FooterNote** 表示 OK。
- **今後**: **LeftRail クリック化**は**別タスク**（**大分類と複数詳細画面の対応**を先に設計）。**次にナビを触る場合**も、**CardNavMenu 削除・縮小は当面しない**。**HeaderNavRow / CardNavMenu は現時点では維持**。

### 2.5 施設サマリー閲覧・Theme 第1段と導線確認（`5987821`）

- **到達点**: **`facility_summary_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`facility_summary_view.gd`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **施設サマリー**（第6画面）。
  - **`CardNavMenu`** — **クラブ**列の **施設** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。
- **施設サマリーからホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**text / tooltip / connection / handler 名は維持**。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 施設サマリー遷移 OK**。**施設画面表示 OK**。**HomeNavButton でホームへ戻る OK**。**HeaderNavRow / CardNavMenu の役割分担は維持**（Theme 適用は施設画面の静的カードのみ）。
- **Theme 適用範囲**: **`HeaderCard`**＝`Phase4HeaderCard`、**`SummaryCard`**＝`Phase4SummaryCard`。**Scroll 内動的リストは第2段**（今回未変更）。

### 2.6 クラブ史閲覧・Theme 第1段と導線確認（`682a941`）

- **到達点**: **`club_history_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`club_history_view.gd`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **クラブ史閲覧**（第3画面）。
  - **`CardNavMenu`** — **クラブ**列の **クラブ史** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、クラブ史画面へのショートカットではない**。
- **クラブ史からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**text / tooltip / connection / handler 名は維持**。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → クラブ史遷移 OK**。**クラブ史画面表示 OK**。**HomeNavButton でホームへ戻る OK**。**HeaderNavRow / CardNavMenu の役割分担は維持**（Theme 適用はクラブ史画面の Header/Summary のみ）。
- **Theme 適用範囲**: **`HeaderCard`**＝`Phase4HeaderCard`、**`SummaryCard`**＝`Phase4SummaryCard`。**Scroll 内の段落・シーズン表は第2段**（暗背景＋明文字のまま・今回未変更）。

### 2.7 順位表閲覧・Theme 第1段と導線確認（`927e918`）

- **到達点**: **`standings_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`standings_view.gd`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **順位表閲覧**（第4画面）。
  - **`CardNavMenu`** — **リーグ**列の **順位表** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、順位表画面へのショートカットではない**。
- **順位表からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**text / tooltip / connection / handler 名は維持**。
- **ユーザー環境 Godot（ローカル目視・1280×720）**: **ホーム → 順位表遷移 OK**。**順位表画面表示 OK**。**HomeNavButton でホームへ戻る OK**。**HeaderNavRow / CardNavMenu の役割分担は維持**（Theme 適用は順位表画面の Header/Summary のみ）。
- **Theme 適用範囲**: **`HeaderCard`**＝`Phase4HeaderCard`、**`SummaryCard`**＝`Phase4SummaryCard`。**Scroll 内 8 列表・動的行は第2段**（暗背景＋明文字のまま・今回未変更）。

### 2.8 日程閲覧・Theme 第1段と導線確認（`440c3f6`）

- **到達点**: **`schedule_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`schedule_view.gd`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **日程閲覧**（第5画面）。
  - **`CardNavMenu`** — **リーグ**列の **日程** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、日程画面へのショートカットではない**。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**text / tooltip / connection / handler 名は維持**。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**。**日程画面表示 OK**。**HomeNavButton でホームへ戻る OK**。**HeaderNavRow / CardNavMenu の役割分担は維持**（Theme 適用は Header と Scroll 内 SummaryCard のみ）。
- **Theme 適用範囲**: **`HeaderCard`**＝`Phase4HeaderCard`、**`Scroll/ScrollMain/SummaryCard`**＝`Phase4SummaryCard`。**`NextGameCard`**・**`ScrollContent` / 試合リストは第2段**（暗背景＋明文字のまま・第1段時点）。

### 2.8a 日程閲覧・Theme 第2段・前半と導線確認（`986c4ab`）

- **到達点**: **`schedule_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第2段・前半**）。**`schedule_view.gd`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **日程閲覧**（第5画面）。
  - **`CardNavMenu`** — **リーグ**列の **日程** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、日程画面へのショートカットではない**。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`986c4ab` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**。**日程画面表示 OK**。**HeaderCard / SummaryCard は従来どおり OK**。**NextGameCard 白カード化・内ラベル可読性 OK**。**ScrollContent / 試合リスト残存 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・前半）**: **`NextGameCard`**＝`Phase4SummaryCard`（内ラベル濃色化）。**`ScrollContent` 内 upcoming 試合ブロックは第2段・後半（最小）**（`7fecb99` で対応 — §2.8b）。

### 2.8b 日程閲覧・Theme 第2段・後半（最小）と導線確認（`7fecb99`）

- **到達点**: **`schedule_view.gd` の `_add_upcoming_block` のみ**（**ナビ構造の変更ではない**・**見た目第2段・後半（最小）**）。**`schedule_view.tscn`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **日程閲覧**（第5画面）。
  - **`CardNavMenu`** — **リーグ**列の **日程** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、日程画面へのショートカットではない**。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`7fecb99` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**。**日程画面表示 OK**。**HeaderCard / SummaryCard / NextGameCard は従来どおり OK**。**upcoming 試合ブロック白カード化・3 Label 可読性 OK**。**HSeparator 維持 OK**。**試合リスト内容・件数・順序不変 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・後半・最小）**: **`_add_upcoming_block` の runtime `PanelContainer`**＝`Phase4SummaryCard`（内 Label 濃色化）。**見出し / advance_hint / `%ScrollContent` 全体整理は別タスク**（**advance_hint は `a62b3a7` で対応 — §2.8c**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4 — HeaderNavRow＝上部主要導線、CardNavMenu＝実操作用中央画面メニュー、LeftRail＝表示のみの大分類ナビ）。

### 2.8c 日程閲覧・Theme 第2段・追加最小と導線確認（`a62b3a7`）

- **到達点**: **`schedule_view.gd` の `_fill_scroll_body` advance_hint 分岐 + `_add_advance_hint_block` 新設**（**ナビ構造の変更ではない**・**見た目第2段・追加最小**）。**`schedule_view.tscn`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — 5 導線のうち **日程閲覧**（第5画面）。
  - **`CardNavMenu`** — **リーグ**列の **日程** ボタン（**HeaderNavRow と二重導線**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、日程画面へのショートカットではない**。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`a62b3a7` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視・advance_hint なし・`f16450f` 記録）**: **ホーム → 日程遷移 OK**（**日程画面表示 OK**）。**HeaderCard / SummaryCard / NextGameCard は従来どおり OK**。**upcoming 試合ブロックは従来状態を維持 OK**。**既存のお知らせ表示 OK**。**画面全体の崩れなし・文字可読性 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。**当時データは advance_hint なし** — **advance_hint 白カードそのものは未表示**。**advance_hint なし時に不要な空カードが出ていないことは確認済み**。
- **Theme 適用範囲（第2段・追加最小）**: **`_add_advance_hint_block` の runtime `PanelContainer`**＝`Phase4SummaryCard`（見出し / block / one_line を白カード向け濃色化）。**`_add_upcoming_block` / NextGameCard / SummaryCard / HeaderCard は今回未変更**。**見出し全体 / ScrollContent 全体整理は別タスク**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.8d 日程閲覧・advance_hint ありデータ実表示確認と導線確認（ユーザー確認・`e819da0` 推奨後）

- **到達点**: **ナビ構造の変更ではない** — **`a62b3a7` の advance_hint 白カードが、advance_hint ありデータでも正しく表示されることを確認**（**コード・scene・data JSON・Theme は不変**）。
- **ホームからの到達**（**変更なし**）: **`HeaderNavRow`** または **`CardNavMenu`（リーグ列・日程）** から日程へ。**LeftRail からは遷移しない**（§2.4）。
- **確認データ**: **`schedule_from_python.json` を一時退避**し、**同梱 `schedule_mock.json`**（**`advance_hint` あり**）を読込。**確認後 `schedule_from_python.json` は復元済み**。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`**。**node 名 / text / tooltip / connection / handler 名は維持**。
- **ユーザー環境 Godot（ローカル目視・advance_hint あり・mock）**: **DataSourceLabel**＝**同梱モックJSON**。**advance_hint 白カード表示 OK**。**見出し「進行ヒント（advance_hint）」 OK**。**block / one_line 可読性 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **`a62b3a7` / `f16450f` との関係**: **`f16450f`** は **なし時の空カードなし**を記録。**今回**で **あり時の白カード実表示**も確認済み — **`f16450f` 時点の未確認ギャップは解消**。

### 2.8e 日程閲覧・empty_message（お知らせ）ブロック白カード化と導線確認（`463e74b`）

- **到達点**: **`schedule_view.gd` の `_fill_scroll_body` empty_message 分岐 + `_add_empty_message_block` 新設**（**ナビ構造の変更ではない**・**見た目第2段・追加最小**）。**`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）: **`HeaderNavRow`** または **`CardNavMenu`（リーグ列・日程）** から日程へ。**LeftRail からは遷移しない**（§2.4）。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`**。**node 名 / text / tooltip / connection / handler 名は維持**（`463e74b` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**。**通常状態**で **empty_message 空カードなし OK**。**一時 JSON**で **お知らせ / empty_message 白カード表示 OK**。**見出し「お知らせ」・本文可読性 OK**。**upcoming・advance_hint 維持 OK**。**notes / Footer 従来どおり OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・追加最小）**: **`_add_empty_message_block` の runtime `PanelContainer`**＝`Phase4SummaryCard`。**`_add_upcoming_block` / `_add_advance_hint_block` / NextGameCard / SummaryCard / HeaderCard は今回未変更**。**notes / Footer は対象外**。**ScrollContent 全体整理は別タスク**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.8f 日程閲覧・「今後の予定」セクション見出し白カード化と導線確認（`a24cf6f`）

- **到達点**: **`schedule_view.gd` の `_fill_scroll_body` upcoming 非空時の見出し1箇所 + `_add_upcoming_section_heading` 新設**（**ナビ構造の変更ではない**・**見た目第2段・追加最小**）。**`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）: **`HeaderNavRow`** または **`CardNavMenu`（リーグ列・日程）** から日程へ。**LeftRail からは遷移しない**（§2.4）。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`**。**node 名 / text / tooltip / connection / handler 名は維持**（`a24cf6f` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視・同梱 mock）**: **`schedule_from_python.json` 一時退避 → 同梱 mock 読込 → 確認後復元済み**。**DataSourceLabel**＝**同梱モックJSON**。**ホーム → 日程遷移 OK**。**「今後の予定」見出し白カード表示 OK**。**見出し可読性 OK**。**upcoming 試合カード表示 OK**。**upcoming 内容・順序 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・追加最小）**: **`_add_upcoming_section_heading` の runtime `PanelContainer`**＝`Phase4SummaryCard`。**`_add_upcoming_block` / `_add_advance_hint_block` / `_add_empty_message_block` / NextGameCard / SummaryCard / HeaderCard / notes / Footer は今回未変更**。**ScrollContent 全体・試合リスト本格整理は別タスク**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.8g 日程閲覧・upcoming 試合間 HSeparator 整理と導線確認（`a9fa054`）

- **到達点**: **`schedule_view.gd` の `_fill_scroll_body` upcoming ループ内から試合間 HSeparator 追加処理を削除**（**ナビ構造の変更ではない**・**見た目第2段・追加最小**）。**`schedule_view.tscn`・data JSON・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）: **`HeaderNavRow`** または **`CardNavMenu`（リーグ列・日程）** から日程へ。**LeftRail からは遷移しない**（§2.4）。
- **日程からホームへ**: **`HomeNavButton`**（**`HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`**。**node 名 / text / tooltip / connection / handler 名は維持**（`a9fa054` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 日程遷移 OK**。**upcoming カード間の暗色 HSeparator 消失 OK**。**カード間余白 OK**。**upcoming 8件 / 内容 / 順序維持 OK**。**「今後の予定」見出し・advance_hint・empty_message・notes / Footer 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・追加最小）**: **区切り方針の変更のみ** — 暗色 Separator を廃止し **`ScrollContent` / 親 VBox の `separation=8`** に任せる。**`_add_upcoming_block` 他の白カードブロックは今回未変更**。**ScrollContent 全体・試合リスト本格整理は別タスク**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.9 財務サマリー閲覧・Theme 第1段・可読性補正と導線確認（`4b43da5` / `6c3dc43`）

- **到達点**: **`4b43da5`** は **`finance_summary_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`6c3dc43`** は **`finance_summary_view.gd` のみ**（**HistoryBody 動的履歴行の `font_color` のみ** — **第2段本格整備ではない**）。**Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **財務サマリー** ボタン（**#7・主入口**）。
  - **`HeaderNavRow` には載せない**（5 導線はロスター・クラブ史・順位表・日程・施設サマリーのみ — §3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、財務サマリー画面へのショートカットではない**。
- **財務サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内** — **HeaderNavRow ではない**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**`4b43da5` / `6c3dc43` いずれも** text / tooltip / connection / handler 名は維持。
- **ユーザー環境 Godot（ローカル目視）**:
  - **`4b43da5` 後**: **CardNavMenu → 財務サマリー遷移 OK**。**財務画面表示 OK**。**HeaderCard Phase4 系・Scroll 内5静的カード白系 OK**。**DataSourceLabel OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし**。**財務履歴の動的履歴行は薄く読みにくい**ことが判明。
  - **`6c3dc43` 後**: **財務履歴の動的履歴行テキストの可読性改善 OK**。**その他の動作・HomeNavButton 戻り OK**。**エラーなし**。
- **Theme 適用範囲（`4b43da5`）**: **`HeaderCard`**＝`Phase4HeaderCard`、**Scroll/ScrollContent 内5枚静的カード**＝`Phase4SummaryCard`（Finance / Prior / Salary / History / Caution）。
- **可読性補正（`6c3dc43`）**: **`%HistoryBody`** に追加される動的履歴行 `Label` の色のみ **`Color(0.16, 0.2, 0.3)`** へ。**HistoryBody 構造・履歴行レイアウト本格整理は第2段**（**第2段・最小 `d57b021` で行区切り**、**Body本格・最小 `307e719` で内側余白** — §2.9a / §2.9b）。

### 2.9a 財務サマリー閲覧・Theme 第2段（最小）と導線確認（`d57b021`）

- **到達点**: **`finance_summary_view.gd` の `_fill_history_rows` のみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`finance_summary_view.tscn`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **財務サマリー** ボタン（**#7・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、財務サマリー画面へのショートカットではない**。
- **財務サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`d57b021` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 財務サマリー遷移 OK**。**財務サマリー画面表示 OK**。**HeaderCard / 5静的カードは従来どおり OK**。**履歴行区切り OK**。**最終行後の不要区切りなし OK**。**履歴行可読性 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%HistoryBody` 内動的履歴行**の**行間 `HSeparator`**（**Panel 化・カード化は別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.9b 財務サマリー閲覧・Theme 第2段（Body本格・最小）と導線確認（`307e719`）

- **到達点**: **`finance_summary_view.gd` の `_fill_history_rows` 履歴行追加部分のみ**（**ナビ構造の変更ではない**・**Body本格整備の最小入口**）。**`finance_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**HeaderCard / 静的5カード・DataSourceLabel 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **財務サマリー** ボタン（**#7・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、財務サマリー画面へのショートカットではない**。
- **財務サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`307e719` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 財務サマリー遷移 OK**。**財務サマリー画面表示 OK**。**HistoryBody 履歴行の内側余白 OK**。**HSeparator 維持 OK**。**最終履歴行後の不要 HSeparator なし OK**。**履歴文言 / 件数 / 順序維持 OK**。**HeaderCard / 5静的カードは従来どおり OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（Body本格・最小）**: **`%HistoryBody` 内動的履歴行**の **`MarginContainer` 内側余白**（**Panel 化・履歴行カード化・本格レイアウトは別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）:
  - **HeaderNavRow**＝上部主要 5 導線（財務は載せない）。
  - **CardNavMenu**＝実操作用中央画面メニュー（**経営 → 財務サマリー**が主入口）。
  - **LeftRail**＝表示のみの大分類ナビ（**財務サマリーへ直接遷移しない**）。

### 2.10 オーナーミッション / クラブ評価閲覧・Theme 第1段・可読性補正と導線確認（`e6acce0` / `2f808e5`）

- **到達点**: **`e6acce0`** は **`owner_mission_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`2f808e5`** は **`owner_mission_view.gd` のみ**（**MissionsBody 動的ミッション行の `font_color` のみ** — **第2段本格整備ではない**）。**Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **オーナーミッション** ボタン（**#8・主入口**）。
  - **`HeaderNavRow` には載せない**（5 導線はロスター・クラブ史・順位表・日程・施設サマリーのみ — §3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、オーナーミッション画面へのショートカットではない**。
- **オーナーミッションからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内** — **HeaderNavRow ではない**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**`e6acce0` / `2f808e5` いずれも** text / tooltip / connection / handler 名は維持。
- **ユーザー環境 Godot（ローカル目視）**:
  - **`e6acce0` 後**: **CardNavMenu #8 → オーナーミッション遷移 OK**。**オーナーミッション画面表示 OK**。**HeaderCard Phase4 系・Scroll 内4静的カード白系 OK**。**DataSourceLabel OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし**。**今季ミッションカード内の MissionsBody 動的行は薄く読みにくい**ことが判明。
  - **`2f808e5` 後**: **今季ミッションの動的行テキストの可読性改善 OK**。**その他の動作・HomeNavButton 戻り OK**。**エラーなし**。
- **Theme 適用範囲（`e6acce0`）**: **`HeaderCard`**＝`Phase4HeaderCard`、**Scroll/ScrollContent 内4枚静的カード**＝`Phase4SummaryCard`（Trust / Missions / Eval / Caution）。
- **可読性補正（`2f808e5`）**: **`%MissionsBody`** に追加される動的ミッション行 `Label` の色のみ **`Color(0.16, 0.2, 0.3, 1)`** へ。**MissionsBody 構造・ミッション行レイアウト本格整理は第2段**（**第2段・最小 `5a3ae2c` で行区切り**、**Body本格・最小 `d4c0372` で内側余白** — §2.10a / §2.10b）。

### 2.10a オーナーミッション / クラブ評価閲覧・Theme 第2段（最小）と導線確認（`5a3ae2c`）

- **到達点**: **`owner_mission_view.gd` の `_fill_mission_rows` のみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`owner_mission_view.tscn`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **オーナーミッション** ボタン（**#8・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、オーナーミッション画面へのショートカットではない**。
- **オーナーミッションからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`5a3ae2c` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → オーナーミッション遷移 OK**。**オーナーミッション画面表示 OK**。**HeaderCard / 4静的カードは従来どおり OK**。**MissionsBody 行区切り OK**。**最終行後の不要区切りなし OK**。**ミッション行可読性 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%MissionsBody` 内動的ミッション行**の**行間 `HSeparator`**（**Panel 化・カード化は別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.10b オーナーミッション / クラブ評価閲覧・Theme 第2段（Body本格・最小）と導線確認（`d4c0372`）

- **到達点**: **`owner_mission_view.gd` の `_fill_mission_rows` ミッション行追加部分のみ**（**ナビ構造の変更ではない**・**Body本格整備の余白横展開第1号**）。**`owner_mission_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**HeaderCard / 静的4カード・DataSourceLabel 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **オーナーミッション** ボタン（**#8・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、オーナーミッション画面へのショートカットではない**。
- **オーナーミッションからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`d4c0372` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → オーナーミッション遷移 OK**。**オーナーミッション画面表示 OK**。**MissionsBody ミッション行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**ミッション文言 / 件数 / 順序維持 OK**。**HeaderCard / 4静的カードは従来どおり OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（Body本格・最小）**: **`%MissionsBody` 内動的ミッション行**の **`MarginContainer` 内側余白**（財務 `307e719` と同値。**Panel 化・ミッション行カード化・本格レイアウトは別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）:
  - **HeaderNavRow**＝上部主要 5 導線（オーナーミッションは載せない）。
  - **CardNavMenu**＝実操作用中央画面メニュー（**経営 → オーナーミッション**が主入口）。
  - **LeftRail**＝表示のみの大分類ナビ（**オーナーミッションへ直接遷移しない**）。

### 2.11 戦術 / ローテーションサマリー閲覧・Theme 第1段・可読性補正と導線確認（`44b0584` / `7bbbb4e`）

- **到達点**: **`44b0584`** は **`tactics_summary_view.tscn` のみ**（**ナビ構造の変更ではない**・**見た目第1段**）。**`7bbbb4e`** は **`tactics_summary_view.gd` のみ**（**PlayerRolesBody 動的選手ロール行の `font_color` のみ** — **第2段本格整備ではない**）。**Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **チーム**列の **戦術サマリー** ボタン（**#9・主入口**）。
  - **`HeaderNavRow` には載せない**（5 導線はロスター・クラブ史・順位表・日程・施設サマリーのみ — §3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、戦術サマリー画面へのショートカットではない**。
- **戦術サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内** — **HeaderNavRow ではない**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**`44b0584` / `7bbbb4e` いずれも** text / tooltip / connection / handler 名は維持。
- **ユーザー環境 Godot（ローカル目視）**:
  - **`44b0584` 後**: **CardNavMenu #9 → 戦術サマリー遷移 OK**。**戦術サマリー画面表示 OK**。**HeaderCard Phase4 系・Scroll 内6静的カード白系 OK**。**DataSourceLabel OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし**。**選手ロールカード内の PlayerRolesBody 動的行は薄く読みにくい**ことが判明。
  - **`7bbbb4e` 後**: **選手ロールの動的行テキストの可読性改善 OK**。**その他の動作・HomeNavButton 戻り OK**。**エラーなし**。
- **Theme 適用範囲（`44b0584`）**: **`HeaderCard`**＝`Phase4HeaderCard`、**Scroll/ScrollContent 内6枚静的カード**＝`Phase4SummaryCard`（Overview / Attack / Defense / Rotation / PlayerRoles / Notes）。
- **可読性補正（`7bbbb4e`）**: **`%PlayerRolesBody`** に追加される動的選手ロール行 `Label` の色のみ **`Color(0.16, 0.2, 0.3, 1)`** へ。**PlayerRolesBody 構造・選手ロール行レイアウト本格整理は第2段**（**第2段・最小 `c9216d0` で行区切り**、**Body本格・最小 `2c637f2` で内側余白** — §2.11a / §2.11b）。

### 2.11a 戦術 / ローテーションサマリー閲覧・Theme 第2段（最小）と導線確認（`c9216d0`）

- **到達点**: **`tactics_summary_view.gd` の `_fill_player_roles` のみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`tactics_summary_view.tscn`・Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **チーム**列の **戦術サマリー** ボタン（**#9・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、戦術サマリー画面へのショートカットではない**。
- **戦術サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`c9216d0` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 戦術サマリー遷移 OK**。**戦術サマリー画面表示 OK**。**HeaderCard / 6静的カードは従来どおり OK**。**PlayerRolesBody 行区切り OK**。**最終行後の不要区切りなし OK**。**選手ロール行可読性 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%PlayerRolesBody` 内動的選手ロール行**の**行間 `HSeparator`**（**Panel 化・カード化は別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.11b 戦術 / ローテーションサマリー閲覧・Theme 第2段（Body本格・最小）と導線確認（`2c637f2`）

- **到達点**: **`tactics_summary_view.gd` の `_fill_player_roles` 選手ロール行追加部分のみ**（**ナビ構造の変更ではない**・**Body本格整備の余白横展開第2号**）。**`tactics_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**HeaderCard / 静的6カード・DataSourceLabel 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **チーム**列の **戦術サマリー** ボタン（**#9・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、戦術サマリー画面へのショートカットではない**。
- **戦術サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`2c637f2` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 戦術サマリー遷移 OK**。**戦術サマリー画面表示 OK**。**PlayerRolesBody 選手ロール行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**選手ロール文言 / 件数 / 順序維持 OK**。**最大8件制限維持 OK**。**HeaderCard / 6静的カードは従来どおり OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（Body本格・最小）**: **`%PlayerRolesBody` 内動的選手ロール行**の **`MarginContainer` 内側余白**（財務 `307e719` / OM `d4c0372` と同値。**Panel 化・選手ロール行カード化・本格レイアウトは別タスク**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）:
  - **HeaderNavRow**＝上部主要 5 導線（戦術サマリーは載せない）。
  - **CardNavMenu**＝実操作用中央画面メニュー（**チーム → 戦術サマリー**が主入口）。
  - **LeftRail**＝表示のみの大分類ナビ（**戦術サマリーへ直接遷移しない**）。

### 2.12 契約 / 人事サマリー閲覧・Theme 残り第1段・可読性補正と導線確認（`5d1afa2` / `1df4820`）

- **到達点**: **`5d1afa2`** は **`contract_personnel_summary_view.tscn` のみ**（**ナビ構造の変更ではない**・**RiskCard / PlayersCard の見た目残り第1段**）。**`1df4820`** は **`contract_personnel_summary_view.gd` のみ**（**RiskRows / PlayerRows 動的行の `font_color` のみ** — **第2段本格整備ではない**）。**Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **契約・人事サマリー** ボタン（**#10・主入口**）。
  - **`HeaderNavRow` には載せない**（5 導線はロスター・クラブ史・順位表・日程・施設サマリーのみ — §3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、契約・人事サマリー画面へのショートカットではない**。
- **契約・人事サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内** — **HeaderNavRow ではない**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**`5d1afa2` / `1df4820` いずれも** text / tooltip / connection / handler 名は維持。
- **ユーザー環境 Godot（ローカル目視）**:
  - **`5d1afa2` 後**: **CardNavMenu #10 → 契約・人事サマリー遷移 OK**。**契約・人事サマリー画面表示 OK**。**RiskCard / PlayersCard 白カード化 OK**。**Scroll 内カード白系統一 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし**。**RiskRows / PlayerRows 動的行は薄く読みにくい**ことが判明。
  - **`1df4820` 後**: **人事リスクの動的行テキストの可読性改善 OK**。**主要契約選手の動的行テキストの可読性改善 OK**。**その他の動作・HomeNavButton 戻り OK**。**エラーなし**。
- **Theme 適用範囲（`5d1afa2`）**: **`RiskCard`**・**`PlayersCard`**＝`Phase4SummaryCard`（**Header / Contract / Balance / Caution は既に Phase4 済み**）。
- **可読性補正（`1df4820`）**: **`%RiskRows`**・**`%PlayerRows`** に追加される動的行 `Label` の色のみ **`Color(0.16, 0.2, 0.3, 1)`** へ。**RiskRows / PlayerRows 構造・行レイアウト本格整理は第2段**（**PlayerRows / RiskRows 行区切りは §2.12a / §2.12b**、**PlayerRows 内側余白は §2.12c**）。

### 2.12a 契約 / 人事サマリー閲覧・Theme 第2段（最小）PlayerRows と導線確認（`6b26fa3`）

- **到達点**: **`contract_personnel_summary_view.gd` の `_fill_player_rows` のみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`contract_personnel_summary_view.tscn`・Theme `.tres` 未変更**。**`_fill_risk_rows` は未変更**（**RiskRows は従来どおり**）。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **契約・人事サマリー** ボタン（**#10・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、契約・人事サマリー画面へのショートカットではない**。
- **契約・人事サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`6b26fa3` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 契約・人事サマリー遷移 OK**。**契約・人事サマリー画面表示 OK**。**HeaderCard / 5静的カードは従来どおり OK**。**PlayerRows 主要契約選手行区切り OK**。**最終行後の不要区切りなし OK**。**主要契約選手行可読性 OK**。**RiskRows 従来どおり OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%PlayerRows` 内動的主要契約選手行**の**行間 `HSeparator`**（**Panel 化・カード化は別タスク**。**`%RiskRows` は今回未変更**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.12b 契約 / 人事サマリー閲覧・Theme 第2段（最小）RiskRows と導線確認（`97b26a8`）

- **到達点**: **`contract_personnel_summary_view.gd` の `_fill_risk_rows` のみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`contract_personnel_summary_view.tscn`・Theme `.tres` 未変更**。**`_fill_player_rows` は未変更**（**PlayerRows は `6b26fa3` の状態を維持**）。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **契約・人事サマリー** ボタン（**#10・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、契約・人事サマリー画面へのショートカットではない**。
- **契約・人事サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`97b26a8` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 契約・人事サマリー遷移 OK**。**契約・人事サマリー画面表示 OK**。**HeaderCard / 5静的カードは従来どおり OK**。**RiskRows 人事リスク行区切り OK**。**最終行後の不要区切りなし OK**。**人事リスク行可読性 OK**。**PlayerRows は `6b26fa3` の状態を維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%RiskRows` 内動的人事リスク行**の**行間 `HSeparator`**（**Panel 化・カード化は別タスク**。**`%PlayerRows` は `6b26fa3` のまま**）。
- **契約・人事の最小行区切り**: **PlayerRows（`6b26fa3`）と RiskRows（`97b26a8`）の両方をユーザー確認済み**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

### 2.12c 契約 / 人事サマリー閲覧・Theme 第2段（Body本格・最小）PlayerRows 内側余白と導線確認（`f19ed9b`）

- **到達点**: **`contract_personnel_summary_view.gd` の `_fill_player_rows` 主要契約選手行追加部分のみ**（**ナビ構造の変更ではない**・**Body本格整備の余白横展開第3号**）。**`contract_personnel_summary_view.tscn`・Theme `.tres`・`project.godot` 未変更**。**`_fill_risk_rows` / RiskRows 未変更**。**HeaderCard / 静的5カード・DataSourceLabel 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`CardNavMenu`** — **経営**列の **契約・人事サマリー** ボタン（**#10・主入口**）。
  - **`HeaderNavRow` には載せない**（§3）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、契約・人事サマリー画面へのショートカットではない**。
- **契約・人事サマリーからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderTopRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`f19ed9b` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → 契約・人事サマリー遷移 OK**。**契約・人事サマリー画面表示 OK**。**PlayerRows 主要契約選手行の内側余白 OK**。**HSeparator 維持 OK**。**最終行後の不要 HSeparator なし OK**。**主要契約選手文言 / 件数 / 順序維持 OK**。**RiskRows 従来どおり OK**。**HeaderCard / 5静的カードは従来どおり OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（Body本格・最小）**: **`%PlayerRows` 内動的主要契約選手行**の **`MarginContainer` 内側余白**（財務 `307e719` / OM `d4c0372` / 戦術 `2c637f2` と同値。**Panel 化・行カード化・本格レイアウトは別タスク**。**`%RiskRows` は今回未変更**）。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）:
  - **HeaderNavRow**＝上部主要 5 導線（契約・人事サマリーは載せない）。
  - **CardNavMenu**＝実操作用中央画面メニュー（**経営 → 契約・人事サマリー**が主入口）。
  - **LeftRail**＝表示のみの大分類ナビ（**契約・人事サマリーへ直接遷移しない**）。

### 2.13 ロスター閲覧・Theme 第1段・表 Theme 切替と導線確認（`f866f5b` / `407f014`）

- **到達点**: **`f866f5b`** は **`roster_view.tscn` のみ**（**ナビ構造の変更ではない**・**Scroll 内 TableCard 白カード化**）。**`407f014`** は **`roster_view.gd` のみ**（**表ヘッダー/セルの `theme_type_variation` のみ** — **表ロジック・9列・行生成は不変**）。**Theme `.tres` 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — **5 導線の先頭**（**ロスター**）。
  - **`CardNavMenu`** — **チーム**列の **ロスター** ボタン（**#1・併用入口**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、ロスター画面へのショートカットではない**。
- **ロスターからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**`f866f5b` / `407f014` いずれも** text / tooltip / connection / handler 名は維持。
- **ユーザー環境 Godot（ローカル目視）**:
  - **HeaderNavRow または CardNavMenu → ロスター遷移 OK**。**ロスター画面表示 OK**。**HeaderCard Phase4 系 OK**。
  - **白 TableCard 内に9列表表示 OK**（**# / 選手名 / Pos / 年齢 / OVR / 年俸 / 残り契約 / 区分 / 状態**）。
  - **表ヘッダー・表セルの可読性 OK**。**DataSourceLabel OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし**。**実行後 git 差分なし**。
- **Theme 適用範囲（`f866f5b`）**: **`Scroll/TableCard`**＝`Phase4SummaryCard`（**`%RowList` は子のまま**）。
- **表 Theme 切替（`407f014`）**: 動的表 `Label` を **`Phase4TableHead` / `Phase4TableCell`** へ。**表行 Panel 化・行レイアウト本格調整は第2段・本格**（`8a95fcf` では未変更）。

### 2.13a ロスター閲覧・Theme 第2段（最小）と導線確認（`8a95fcf`）

- **到達点**: **`roster_view.gd` の `_apply_snapshot` 内 players ループのみ**（**ナビ構造の変更ではない**・**見た目第2段・最小**）。**`roster_view.tscn`・Theme `.tres`・project.godot 未変更**。
- **ホームからの到達**（**変更なし**）:
  - **`HeaderNavRow`** — **5 導線の先頭**（**ロスター**）。
  - **`CardNavMenu`** — **チーム**列の **ロスター** ボタン（**#1・併用入口**）。
  - **LeftRail からは遷移しない**（表示のみ — §2.4）。**LeftRail は大分類表示であり、ロスター画面へのショートカットではない**。
- **ロスターからホームへ**: **`HomeNavButton`**（**`HeaderCard/HeaderInner/HeaderNavRow` 内**）→ **`_on_home_nav_button_pressed`** → **`home_dashboard.tscn`**。**node 名 / text / tooltip / connection / handler 名は維持**（`8a95fcf` 後もユーザー確認済み）。
- **ユーザー環境 Godot（ローカル目視）**: **ホーム → ロスター遷移 OK**。**RowList 選手行間区切り OK**。**最終行後の不要区切りなし OK**。**ヘッダー下区切り維持 OK**。**9列内容 / 順序 / 幅維持 OK**。**tooltip 維持 OK**。**DataSourceLabel 維持 OK**。**HomeNavButton でホームへ戻る OK**。**エラーなし・実行後 git 差分なし**。
- **Theme 適用範囲（第2段・最小）**: **`%RowList` 内動的選手行**の**行間 `HSeparator`**（**`_add_player_row` 本体・9列幅・tooltip は未変更**。**ヘッダー下 Separator は維持**）。**HeaderCard / TableCard / ReadonlyBadge / ModeStrip / DataSourceLabel は今回未変更**。**Panel 化・選手行カード化・9列本格整理は別タスク**。
- **HeaderNavRow / CardNavMenu / LeftRail の役割分担は維持**（§2.4）。

## 3. 現行ナビ構造

- **ホーム**の上部に **`HeaderNavRow`** があり、横に **5 つのボタン** があります（**第7画面の財務サマリー・第8画面のオーナーミッション・第9画面の戦術サマリー・第10画面の契約 / 人事サマリーはここには載せていない**）。  
  **ロスター閲覧** / **クラブ史閲覧** / **順位表閲覧** / **日程閲覧** / **施設サマリー閲覧** へ飛びます。
- **ホーム左の表示用 `LeftRail`（`a5e548f`）**: **大分類 5**（ホーム・チーム・リーグ・経営・クラブ）の**表示のみ**。**画面遷移はしない**（§2.4）。**詳細画面の選択は `CardNavMenu`**（中央の画面メニュー）。
- **ホーム内のカード型メニュー（読み取り）**: **チーム**（**ロスター**・**戦術サマリー**）／**リーグ**（順位表・日程）／**クラブ**（クラブ史・**施設**）／**経営**（**財務サマリー**・**オーナーミッション**・**契約・人事サマリー**）の入り口。**経営列は 3 ボタン**。**施設サマリー**は **クラブ寄りの読み取り画面**として **クラブ列**に置いている。**財務サマリー**・**オーナーミッション**・**契約・人事サマリー**は **経営列**から遷移する。**戦術サマリー（第9画面）**は **チーム列**から遷移する（**HeaderNavRow には載せていない**）。経営列にだけあった補足説明ラベルは **削除**し、他カテゴリとボタン位置を揃えた（`56bcd9e Godotホーム経営カテゴリの説明文を削除`）。施設を経営列へ寄せる余地は **未確認**。
- **各サブ画面**の上部に **「ホームへ戻る（表示のみ）」** ボタンがあり、ホームへ戻ります。
- **`home_dashboard.gd`** に、各サブ画面への **シーンパス定数** と、ボタンから呼ぶ **handler**（`change_scene_to_file`）があります。
- **各サブ画面の `.gd`** に **`_HOME_DASHBOARD_SCENE_PATH`** と、同様の **handler** があります。
- **共通ナビ部品**、**autoload**、**シーン専用マネージャ** は **未実装** です。
- 全体として **安全さを優先した仮ナビ** です。

## 4. 現行方式のメリット

- **実装が単純**で、ファイルを開けば流れが追いやすい。
- **Python・セーブ・DTO 本体には手を入れず**に Godot 側だけで画面を足せる。
- **1 画面ずつ** 追加しやすく、問題が出たとき **元に戻しやすい**。
- **読み取り専用プロトタイプ** の段階には向いている。

## 5. 現行方式の限界

- ホーム上部に **横長のボタンを足し続ける** 方式は、**5 ボタン（第6画面までのヘッダー導線）の時点で限界に近い**（解像度 1280 幅などでは特に）。
- **第 7 画面以降** を **HeaderNavRow に同じやり方で足す**と、**横幅・文字の見やすさ**がさらに厳しくなる見込みが高い（**現状は第7・第8をヘッダーに載せず、カード「経営」から遷移**）。
- 画面同士の移動が **ホーム経由に偏りやすい**（サブ画面同士の直行はない）。
- **ボタン文言・ツールチップ・戻る処理** が画面ごとに似た内容で **重複** している。
- **本格的な GM ゲームの UI** としては、まだ **仮の雰囲気** が残る。
- **90 年代スポーツ GM 風**のように、情報を多くても整理して見せるには、のちほど **カテゴリで整理した導線** が必要になる。

## 6. 将来のナビ候補比較

### A. HeaderNavRow 継続・文言短縮

- **短期の安全策**。例:「ロスター」「クラブ史」「順位表」「日程」「施設」のように短くする。
- **第 7 画面前のつなぎ**としては有効。
- **根本解決**（画面が増え続ける問題そのもの）にはならない。

### B. ホームカード型メニュー

- **ホームを仮ハブとして強化**する案。カテゴリごとの入り口をカードなどで置くイメージ。
- **サブ画面のレイアウトへの影響は比較的小さく**しやすい。
- あとから **カテゴリ別メニュー** へつなげる **橋** になりうる。
- **2026-05 時点**: **小さなプロトタイプ**として **ホームにカード型メニューが入っている**（本格ハブではない）。
- **ヘッダーの 5 ボタン** と **カード** が並ぶと **二重導線** になるので、どちらを正とするか整理が必要。

### C. 左サイドメニュー

- **長期の本命候補**の一つ。画面が増えても **縦に項目を足しやすい**。
- **90 年代スポーツ GM 風**の、情報が多い画面とも相性がよい（※いまは **ビジュアルを作る話ではなく、構造の話**）。
- **全画面のレイアウト**に影響しやすいので、**いきなり全部を左メニュー化するのは重い**。

### D. 上部タブ方式

- **どの画面にいるか**は分かりやすい。
- ただし **タブが横に並ぶ**ので、画面が増えると **また横幅の問題** が出やすい。
- 今回の「横に並べる限界」への **根本解決としては弱い**。

### E. カテゴリ別 2 階層ナビ

- 例: **チーム / リーグ / クラブ / 経営** などでまとめ、その下に各画面。
- **Steam 向けの本番 GUI** に近い整理へ進みやすい。
- **いますべてを実装するのは重い**。
- **左サイドメニュー**と組み合わせると **有力** になりやすい（構造の話）。

### F. 共通ナビ部品 / 共通スクリプト化

- **重複を減らす**のに向く。
- その分 **どこまで共通化するか** の設計が必要で、**急ぎすぎるとあとで作り直す**リスクもある。

### G. 第 7・第 8・第 9・第 10 画面を HeaderNavRow に先に足す

- **画面を足す速度**は保てる。
- 一方で **ナビの負債**（詰まったヘッダー、重複）が増えやすい。**ヘッダーへの乱立は非推奨寄り**（方針を固めてからの方が安全）。**財務サマリー（第7）・オーナーミッション（第8）・戦術サマリー（第9）・契約 / 人事サマリー（第10）はヘッダーではなくカード経由で追加済み**。

## 7. 推奨方針

**短期**

- **すぐに** 左サイドメニューへ **全面移行** はしない。
- **第 6 画面（施設サマリー）** は **読み取り専用プロトタイプ**として追加済み。**第 7 画面（財務サマリー）**・**第 8 画面（オーナーミッション / クラブ評価）**・**第 9 画面（戦術 / ローテーションサマリー）**・**第 10 画面（契約 / 人事サマリー）** も **読み取り専用プロトタイプ**として追加済み（**HeaderNavRow は据え置き**で、**ホームカード「経営」→ 財務サマリー / オーナーミッション / 契約・人事サマリー**、**「チーム」→ 戦術サマリー**）。**第 11 画面以降** を足すかは **慎重に判断**する。少なくとも **ホーム上部ナビの整理**（文言短さ・行の分け方など）や **カードとヘッダーの二重導線の整理**を検討する余地がある。
- **ホームのカード型メニュー**は **小プロトタイプまで実施済み**。**本格左ナビ・共通ナビ・カテゴリ 2 階層の全面実装**は **未着手**。
- **次に手を入れる実装候補**の第一線は、**「HeaderNavRow の文言短縮・仮整理」**（カードは既にあるため、文言・行の整理が中心になりうる）。
- **その判断の前に**、まず **この文書で方針を固定**する（今回の作業）。

**中期**

- ホームを **ボタンだけ置き場** にせず、**カテゴリの入り口を持つハブ**へ育てていく。
- 画面を次のような **カテゴリ** で頭の中（および UI）に整理する（§9 の案。細部は **未確認** で変えてよい）。
- **既存 10 画面を一度に壊さない** ように、**少しずつ** 導線を整理する。

**長期**

- **左サイドメニュー + カテゴリ 2 階層** を **本命候補** とする。
- **90 年代スポーツ GM 風**の、**情報が多くても整理された画面**へ寄せる（ナビの **構造** から近づける。**見た目の本制作**は別工程）。
- 本番 GUI では、**いつでも触れるナビ**と、**画面上部の情報**の役割をはっきり分ける。
- **Python 自動起動**や **本番セーブ接続**は、**ナビの形とぶつからないように** 後工程で足す（詳細は **未確認** でよい）。

## 8. 次に実装するなら

1. **まず** この文書で方針を固定する（今回）。
2. **次に小さく実装するなら**、**「ホーム上部ボタンの文言短縮 / HeaderNavRow の仮整理」** が第一候補（1 コミットで収めやすい・戻しやすい）。
3. **その次** は **「第 11 画面以降に何を置くかの調査・判断」**（チームで優先度を決める。第10まで到達済み）。カード型メニューは **チーム列（ロスター・戦術サマリー）・経営列（財務・オーナーミッション・契約・人事サマリー）まで含め小プロトタイプが進行中**。
4. **左サイドメニュー**は、**いま全面実装しない**。試すなら **1 画面だけ** や、**別ブランチ** など、**本線の 10 画面確認を壊しにくい**やり方にする（タイミングは **未確認**）。

## 9. 画面カテゴリ案

あとからメニューや左ナビに落とすときの **整理用の案** です。**確定ラベルではありません**（変更してよい）。

- **ホーム**  
  - ホーム（ダッシュボード）
- **チーム**  
  - ロスター（いまある）  
  - 戦術 / ローテーションサマリー（いまある。読み取り専用第1弾。**戦術変更・ローテ保存・先発/目標分数の編集は将来**）  
  - 選手詳細（将来）
- **リーグ**  
  - 順位表（いまある）  
  - 日程（いまある）  
  - ニュース / 情報（将来）
- **クラブ**  
  - クラブ史（いまある）  
  - 施設サマリー（いまある。読み取り専用。**現時点ではクラブ列**。将来 **経営** 側へ寄せる余地は **未確認**）  
  - 施設投資・レベルアップ・施設プロジェクト制（将来）
- **経営**（ホームカード列として **いまある**。HeaderNavRow には載せない）  
  - 財務 / 経営サマリー（いまある。読み取り専用第1弾。**予算変更・投資・契約更新などは将来**）
  - オーナーミッション / クラブ評価（いまある。読み取り専用第1弾。**ミッション生成・評価更新・報酬付与などは将来**）
  - 契約 / 人事サマリー（いまある。読み取り専用第1弾。**契約交渉画面ではない**。**契約更新・交渉・獲得・解雇・FA 操作 UI は将来**）
- **進行 / シーズン**（操作は後工程）  
  - 「次へ進む」など  
  - セーブ / ロード  
  - 年度まわりのメニュー  

## 10. 今はやらないこと

次は **この文書の範囲では着手しない** ものとして明記する。

- 左サイドメニューの **全面実装**
- **共通ナビ**のコンポーネント化（急ぎの全面抽象化）
- **本格ビジュアル**の制作
- **ロゴ / イラスト / 装飾**の本制作
- **Python 自動起動**
- **本番セーブ / ロード**の接続
- **進行・保存・契約・編成・戦術**など、**状態を変える操作 UI**
- **第 11 画面以降を HeaderNavRow に乱立追加**すること（方針・ナビを固めないままの横並び増殖）
- **既存 10 画面**の **大規模なレイアウト変更**

## 11. 次タスク候補（短く）

| 優先度の目安 | 内容 |
|--------------|------|
| 第一候補 | ホーム上部ボタンの **文言短縮** / **HeaderNavRow の仮整理** |
| 第二候補 | **第 11 画面以降**に何を置くかの **調査・判断**（第10契約・人事サマリーまで追加済み） |
| 第三候補 | カードとヘッダーの **二重導線**の整理（どちらを正とするか。細部は **未確認**） |
| 第四候補 | **Godot から Python を自動起動**する設計・実装（一括 export は Python CLI `godot_readonly_bundle` が **10 ファイル**まで対応。`8822b87`・`61cc09a`。現状は手動実行のみ。運用は `godot/README.md`） |
| 第五候補 | **左サイドメニュー 1 画面**の試作（慎重に） |

---

**関連**: 画面ごとのデータの考え方・仮ナビの記述は `docs/GODOT_GUI_INFORMATION_ARCHITECTURE_2026-05.md`（§14 / §15 / **§15.1 Theme 検証**）と **あわせて読む** とよいです。本書は **ナビの段階移行** に特化したメモです。**Theme の進捗**は **§2.1** を参照。
