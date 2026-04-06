# 製品ロードマップ・ビジョン・ドメイン固定方針（正本）

**位置づけ**: `.cursorrules` から参照。**Phase・リーグ・日程・ドラフト・製品ビジョン**の長文は本書を正とする。  
**更新**: 実装度や Steamworks 審査ステータスが変わったら、本書と `.cursorrules` の要約を整合させる。

---

## 開発の優先順位（固定）

現在地は **Phase 0**（土台の固定: セーブ・ビルド・依存関係・Steam 販売の技術・商業前提等）を最優先とする。スケジュールが長引いても品質・安定性を優先する。Phase 2 以降の大きな機能追加は Phase 0 の足場が整ってから（例外はバグ修正・クラッシュ防止・安定化に限る）。

**記号**: ◎ 完成　△ 土台は完成　□ ほぼ未着手　★ 現在地（Phase 0）

**全体の流れ**  
基盤完成 → 試合リアリティ強化 → GM モード・経営 → UI・演出 → 公開準備 → Steam 販売

**コードベース**: `basketball_sim/` 配下（Python 約 34 ファイル規模）。**最終ロードマップ照合日: 2026-04-05**（以前の「2025-03-26」表記は本書で置換）。

---

## レビュー反映: 実装度の目安（コードベース照合）

- **Phase 1 相当**: △〜◎ — 48 チーム 3 部リーグ・試合シミュ・Season/Offseason ループ・CLI で長期周回可能。pytest 最小スモーク等あり。継続強化。
- **日本独自ルール**: △ — 登録枠は Team 側で外国籍 3・Asia/帰化 1 想定。試合中ローテは RotationSystem で「外国籍オンコート最大 2・Asia/帰化最大 1」（B リーグ風）。数値は `config/game_constants.py`（`LEAGUE_*_CAP`）と Match / main / Rotation。カップ個別は `Match` / `competition_rules` 側。
- **カップ・国際**: △ — シーズン内「全日本カップ」、**東アジアトップリーグ**（内部キー `easl`）、**オールアジアトーナメント**（内部キー `asia_cl`）等。オフシーズン「アジアカップ / 世界一決定戦 / FINAL BOSS」等は `season.py` / `offseason.py`。表示名の正本は `systems/competition_display.py`。
- **クラブ史**: △ — メニュー・レポート・マイルストーン整合まで実装済。
- **転生**: △ — `offseason` の `_retire_and_reincarnate` 等。
- **GM・経済**: △ — contract_logic、オーナーミッション・財務の一部、トレード/ドラフト/FA/スカウトは実装。UI は読み取り専用が多く、プレイヤー操作の経営は未接続が多い。
- **UI**: △ — tkinter 主画面・観戦は試験実装。**製品目標はメイン操作の全面 GUI**（CLI 併用は移行途中）。`settings.json` の window / fullscreen、`key_bindings.close_subwindow`（既定 `<Escape>`）。**最終形は GUI 内で年度・シーズン完結**。
- **Steam 向け**: △ — セーブ/ロード（pickle・format_version・移行フック等）、初回**ローカルセーブのみ**、Rich Presence v1 未、オーバーレイはコードから無効化せずトラブル時は Steam プロパティでオフ案内（`STEAMWORKS_DESIGN` §5）、EULA/プライバシーはストア主・ゲーム内同意 UI は未（§6）、PyInstaller・Inno・`--smoke`・GHA・`steamworks_bridge` 等。**2026-04-05 時点**: SteamPipe ビルドを **default にライブ設定**しクライアントからインストール・起動確認、デポから **`steam_appid.txt` 除外**の運用、実績 **`ACH_PHASE0_TEST`** を実機解除（`RequestCurrentStats`＋`SetAchievement`）。アップロード用 VDF は `steam_pipe_upload/`。詳細は `basketball_sim/integrations/STEAMWORKS_DESIGN.md`。

---

## Phase 0〜6 の項目（一覧）

### Phase 0: Steam 販売の技術・商業前提（□〜△）（★ 現在地・最優先）

- パッケージング（PyInstaller・Inno `installer/BasketballGM.iss`・署名スクリプト・CI）と依存関係の固定（requirements / pyproject）
- セーブ・設定の永続化と検証
- Steamworks SDK 統合（実績・クラウドセーブは要否決定）
- クラッシュレポート・ログ（△ `logs/game.log` ローテーション・`last_crash.txt`・未処理例外フック）
- キーバインド・ウィンドウ・解像度の最低限仕様

### Phase 1: 基盤構築（△〜◎）

- チーム・リーグ構造（◎）
- 試合シミュエンジン（△）
- 長期自動進行テスト（△）

### Phase 2: 試合リアリティ強化

- スタッツ・バランス（△）
- 独自ルール（外国籍枠等）（△）
- シーズン中カップ（△ 全日本カップ等）
- オフシーズンカップ（△ アジアカップ等）
- クラブ史（△）
- 実況・情緒テキスト（△、Phase 0 後に本格強化の主戦場の一つ）

### Phase 3: GM モード・経営（△）

- 予算・財務（△）
- オーナーミッション（△）
- ドラフト・スカウト・FA（△）
- アリーナ・施設（□）

**シーズン中人事（トレード／インシーズン FA）**  
**3 月第 2 週終了（ラウンド 22 消化後）まで**可、以降はシーズン終了までロック。実装: `REGULAR_SEASON_TRANSACTION_CUTOFF_ROUND`、`season_transaction_rules.py`、CLI GM／トレード、`run_cpu_fa_market_cycle`。**残**: 主画面 GUI からも同じガードを通す。

### Phase 4: UI・演出（△〜□）

- UI デザイン（△ 試作 → 製品は現代風 GM GUI）
- **メイン操作の GUI 一本化**（CLI は開発・CI・smoke 補助）
- ハイライト / 結果だけモード（□）— 正本 `docs/HIGHLIGHT_MODE_SPEC.md`
- 2D 選手（□）— `docs/PLAYER_GRAPHICS_DESIGN.md`
- BGM・SE（□）

### Phase 5: ブラッシュアップ・公開準備（□）

- バグ取り・整合性（Antigravity 等の活用）
- MOD・外部データ（□）
- AI 実況ボイス テスト（□）
- ベータ・フィードバック（□）

### Phase 6: リリース・販売（□）

- Steam 正式リリース（目標単価 1500 円）
- 継続アップデート

**GOAL**: 販売目標（本数・売上）の達成 — **目標: 単価 1500 円・10000 本以上**（ビジョンの数値目標）。

---

## 各 Phase 方針（判断の固定）

実装タスクの細目ではなく、**手戻りが大きい論点**のみ。製品ビジョンの詳細は本章末【製品ビジョン】と `docs/PLAYER_GRAPHICS_DESIGN.md` を正とする。

### Phase 0（★）

- **最優先は安定性**（クラッシュ・セーブ破損・再現不能バグを最も恐れる）。
- **配布**: 単一 exe＋Inno＋署名（可能なら）。`--smoke`・SHA256・README。
- **Steamworks**: 初回は **ライセンス・実績・ローカルセーブ** を核。**クラウドセーブ・Rich Presence** の要否は Phase 0 末期に決定（`STEAMWORKS_DESIGN.md` と整合）。
- **Steamworks 審査・身分確認（運用）**  
  **現状（2026-04-05 更新）**: パートナーで **App 4593200・デポ・SteamPipe ビルド・実績**まで運用確認済み（ユーザー作業）。**税務・本人確認は通過済み**（ユーザー報告）。**ストアページの一般公開・最終の「発売」審査**など、商品として外に出す段階の残タスクは別途フォローする。変化があれば本節を更新する。
- **設定**: 解像度・ウィンドウ・キーはゲーム内変更を目標。Steam オーバーレイ等との衝突に配慮。
- **CLI**: `--smoke`・テスト・開発用。**製品プレイの前提ではない**。

### Phase 1

- セーブ・`PAYLOAD_SCHEMA_VERSION`・シード・ID 契約変更は **移行パスまたはバージョン分岐**必須。
- 試合結果は **単一シミュの真実**（ハイライト等は別シミュにしない）。
- pytest・スモークを資産とみなす。
- バランス係数変更は `.github/workflows/balance-guard.yml`（heavy）成功を必須判定とする。

### Phase 2

- 先発: `docs/MATCH_STARTING_LINEUP_RULES.md`／`Match._resolve_match_starters`。
- 数値は `game_constants` 等に集約。
- イベントログ契約をハイライト抽出に使えるよう先に固める。
- カップ・国際は国内リーグのプレイ感を優先。初版に全部入れない選択も可。

### Phase 3

- 経営メニューたたき台: `docs/GM_MANAGEMENT_MENU_SPEC_V1.md`。
- 操作は **GUI でクリック完結**。数値の増減理由が追える表示を目標。
- アリーナ・施設は効果の体感とインフレ抑制の両立。

### Phase 4

- ハイライトと結果だけは **同一シミュのビュー違い**。`docs/HIGHLIGHT_MODE_SPEC.md` 正本。
- GM 画面は 1280×720 前後から破綻しないことを基準に。
- 2D・選手: `PLAYER_GRAPHICS_DESIGN.md` の Phase A→B→C。
- 音: 個別音量・ミュート。ライセンス管理は別メモまたは `docs/`。

### Phase 5

- クラッシュ・セーブ互換のチェックリスト化。
- MOD・外部データはスキーマ版管理。実在選手名の直書きは避け架空データ＋参考統計。
- AI 実況ボイスはオプション扱い。初版に入れない判断も可。
- ベータは Discord 等の窓口も検討（運用は手動）。

### Phase 6

- 価格 1500 円基準。割引・バンドルは Steam ガイドラインと相場（最終決定は手動）。
- アップデートはセーブ互換をパッチノート最優先。
- 法務: 架空リーグ・データソースの扱いをストア/EULA/クレジットに明記。

---

## 基本構成・リーグ構造

- 全 48 チーム、D1/D2/D3。**独自リーグ**（B リーグ**風**参考）。**ゲーム内のリーグ名・チーム名は実名と同一にしない**。

---

## レギュラーシーズン日程モデル（ユーザー確定案）

- **1 チーム 60 試合**を目標。
- **天皇杯週（R13・R14）**はリーグ試合数 0。
- **代表ウィーク（R7・R20）**および **東アジアトップリーグ ノックアウト週（R23・`easl_event`）**もリーグ試合数 0。
- **R1〜R30** の全文表は **`docs/SEASON_SCHEDULE_MODEL.md`** を正。実装は `season.py` と突き合わせ、ズレは本書優先で修正。
- 合計 60 試合（R8・R21 は 2 試合/週）— 詳細は上記 doc。

---

## 年間カレンダー・オフシーズン

- オフは **6 月第 1 週**開始、6〜7 月を **W1〜W8**（`docs/OFFSEASON_WEEK_MODEL.md` 正）。
- **8 月**完全休養（カレンダー飛ばし可）。
- **9 月**プレシーズン（詳細は今後）。
- **10 月**開幕（R1 と整合）。

---

## ドラフト制度（正本）

- **Rookie Budget ドラフト**（同時指名＋競合時オークション）。最大 **2 人**（0 可）。枠 A（T1/T2×1）＋枠 B（T3×1）。
- 基準上限 **4000 万円**（ソフトキャップ）＋段階式ぜいたく税。下位救済 **C 案**。
- 詳細: `docs/DRAFT_AUCTION_SYSTEM.md`（変更時は本書と `.cursorrules` 要約を同期）。
- スカウト可視化: `docs/SCOUT_VISIBILITY_MODEL.md`。

---

## 選手データ方針

実在風と架空の混合。スタッツは参考データとして収集。**固有名詞は現実と同一にしない**。肖像のそっくり再現は狙わない（`PLAYER_GRAPHICS_DESIGN.md` NG6）。

---

## ゲームエンジン・ロジック（要約）

- 日本独自ルール: 外国籍 3 枠・オンコート制限、アジア・帰化 1 枠の登録・出場を厳格に再現。
- **試合先発**: `docs/MATCH_STARTING_LINEUP_RULES.md` 正本。`TACTICS_STARTER_OVR_MAX_DIFF` / `TACTICS_STARTER_MAX_SUBSTITUTIONS` は `game_constants.py`。実装 `match.py` の `_resolve_match_starters`、`team_tactics.py`。`starting_lineup` / `get_starting_five()` は試合先発正本に**用いない**（統合する場合は doc 同時改訂）。
- 長期シミュ、**アイコンプレイヤー**、**転生**、**クラブ史**。

---

## コンセプト・方向性

90 年代コンソール風 2D を現代風に洗練した GM シミュ。**手ごわい**難易度・攻略しがい。

---

## 製品ビジョン・固定方針（ユーザー合意）

- **操作**: メインは **すべて GUI**（CLI は開発・CI・`--smoke` 補助）。
- **プレイ人数**: **シングル**主役（マルチは現時点で目標外）。
- **試合の見せ方**: ハイライト（可変尺・「結果へ」スキップ）／結果だけ（約 10 秒以下）。`docs/HIGHLIGHT_MODE_SPEC.md`。
- **GM UI**: 洗練された今風 UI、操作ストレス最小化。
- **試合グラフィック**: 2D、3 頭身前後（2.75〜3.25 目安）、シルエット優先。詳細は `docs/PLAYER_GRAPHICS_DESIGN.md`（H/B/F 区分、Phase A/B/C、最低パーツ一覧 v1）。
