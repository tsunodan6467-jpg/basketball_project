# Steamworks 実装・DLL 接続 設計メモ（Phase 0〜リリース）

本書は `steamworks_bridge.py` を実 API へ接続するときの**方針と優先順位**を固定する。コードの詳細は実装時に Steamworks ドキュメントと突き合わせる。

## 現状

- **Windows** で `steam_api64.dll` / `steam_api.dll` が実行ファイルまたはカレント付近にあり、`SteamAPI_Init` が成功した場合は **ctypes 実接続**（`SteamAPI_RunCallbacks` / `Shutdown` 含む）。失敗・DLL なし・非 Windows は **False で継続**（クラッシュしない）。ネイティブ接続時は `ISteamUserStats` が取れれば **`unlock_achievement` から SetAchievement/StoreStats**。
- 環境変数: `BASKETBALL_SIM_DISABLE_STEAM` / `BASKETBALL_SIM_FAKE_STEAM` / `BASKETBALL_SIM_STEAM_APPID` / `BASKETBALL_SIM_STEAM_DLL` / `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE` / `BASKETBALL_SIM_STEAM_LICENSE_STRICT`（モジュール先頭コメント参照）。
- `main.simulate()` 冒頭で `try_init_steam()` の直後に `enforce_steam_license(settings)`。`--smoke` 経路では呼ばない。
- **ライセンス必須**（`settings.json` の `steam_require_license: true` または `BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1`）: ネイティブ接続で `ISteamApps::BIsSubscribed` が **false** なら終了（exit 3）。API が呼べないときは既定では警告のみ続行; `BASKETBALL_SIM_STEAM_LICENSE_STRICT=1` で exit 4。Steam 未接続で必須なら exit 2、フェイク初期化のみ（ネイティブなし）で必須なら exit 5。`BASKETBALL_SIM_FAKE_STEAM` 中はチェックしない。
- tkinter 主画面は `MainMenuView.run()` 内で **ネイティブ接続時のみ** 約 100ms ごとに `pump_steam_callbacks()` を呼ぶ。
- **セーブ**: 初回 Steam リリースは **ローカルのみ**（下記 §3 選択肢 B）。Steam Remote Storage は未実装。
- **Rich Presence**: 初回リリースでは **未実装**（下記 §4）。
- **Steam オーバーレイ**: コードからは無効化しない（Steam 既定＝有効を前提）。問題時はユーザーがクライアント側でオフにできる（下記 §5）。
- **EULA・プライバシー**: ゲーム内フローは未実装。ストア・公式文書を主とする（下記 §6）。
- **SteamPipe デポ／ビルド**: パートナー画面で設定（下記「Steam デポ」内のチェックリスト）。

## 配布物・ファイル配置

| もの | 配置の目安 |
|------|------------|
| `steam_api64.dll`（および SDK が要求する同梱物） | **実行ファイルと同じディレクトリ**（PyInstaller `dist` 出力側）。SDK の再配布条件に従い、**許可されたバイナリのみ**同梱する。 |
| `steam_appid.txt` | **開発時のみ**（Steam ドキュメントの推奨）。中身は **App ID 1行**。本番 Steam ビルドでは通常不要だが、ローカルテストでは exe 横またはカレントに置く。 |
| App ID | Steamworks パートナーで発行した**自アプリの数値 ID**。スペースウォーピング用の共有 ID（例: 480）は**本番リリースに使わない**。 |

**注意**: Steamworks SDK のライセンス上、SDK zip 全体を公開リポジトリにコミットしない。CI ではシークレット／プライベート成果物で供給する運用を想定する。

## Steam デポ（SteamPipe）のコンテンツルート

Steamworks の **Depot** にアップロードするファイルは、クライアント PC 上の**インストール先ディレクトリと同じ相対配置**になる（単一 exe 配布の典型）。

| 配置の考え方 | メモ |
|--------------|------|
| ルートに `BasketballGM.exe` | PyInstaller の `dist\BasketballGM.exe` をそのまま置く。 |
| 同じフォルダに `steam_api64.dll` 等 | `steamworks_bridge` が検索するパスと一致させる。SDK が許可する**再配布バイナリのみ**を手元または CI で `dist\` にコピーしてからデポ用フォルダに集約する。 |
| `steam_appid.txt` | **開発・ローカルテスト用**。本番 Steam ビルドでは通常、クライアントに同梱しない（Steam ドキュメントの推奨に従う）。 |

**運用の目安**: リポジトリに DLL はコミットしない。リリース作業用に、**「PyInstaller 出力＋許可された Steam API DLL を同じディレクトリに揃えたフォルダ」**を 1 つ作り、それを Steam のデポ設定（または `steamcmd` の `build_app`）の **Content Root** に指定する。GitHub Release 用の zip と同じフォルダ構成にすると、差分が減る。

### Steamworks パートナーでのデポ・初回ビルド（チェックリスト）

パートナー画面のメニュー名は更新されることがあるため、**[Steamworks ドキュメント（Uploading to Steam）](https://partner.steamgames.com/doc/sdk/uploading)** を開きながら進める。

- [ ] **アプリ（App ID）** が発行済みである（本番用。共有のスペースウォーピング用 ID は本番に使わない）。
- [ ] **Depot** を追加する（Windows 向け。多くの単一 exe 構成では **1 デポ**で足りる）。Depot ID をメモする。
- [ ] **インストール先のイメージ**をデポのルート＝ゲームフォルダのルートに合わせる（上表どおり `BasketballGM.exe` と DLL が同階層）。
- [ ] ローカルに **コンテンツ用フォルダ**を 1 つ用意し、ビルド済みファイルをコピーしておく（中身は後から差し替え可能。**空に近いプレースホルダーでも**、UI の流れ確認には使える）。
- [ ] **SteamPipe** で「ビルド」を作成し、上記フォルダを **Content Root** としてアップロードする（GUI の Steamworks クライアント、または **`steamcmd` + VDF** のどちらか。自動化するなら後者を別途設計）。
- [ ] **デフォルトブランチ**（例: `default`）にどのビルドを載せるかを設定する（公開・テスト用）。
- [ ] 必要に応じて **設置スクリプト・起動オプション**（exe 名・作業ディレクトリ）をアプリ設定で確認する。

**メモ**: 上記はリポジトリ外（Valve のパートナーサイト）の作業であり、コード変更では代替できない。手順が固まったら、このチェックリストの文言を実際の画面に合わせて更新する。

## 実装方式の選択（推奨順）

1. **C API + `ctypes`（最小）**  
   - `SteamAPI_Init` / `SteamAPI_Shutdown` / `SteamAPI_RunCallbacks` などを DLL から直接呼ぶ。  
   - 依存パッケージを増やさない。シグネチャ・呼び出し規約の取り違えでクラッシュしやすいので、**まず Init/Shutdown/RunCallbacks だけ**で通す。

2. **サードパーティの Python ラッパー**  
   - 導入は速いが、メンテ状況・ライセンス・64bit 対応を確認する。長期は公式 C API 理解が必要になることが多い。

**推奨**: まず **ctypes で「初期化＋コールバックポンプ」** までを `steamworks_bridge` 内に閉じ込め、実績・クラウドは**薄いラッパー関数**を同モジュール（または `steamworks_api.py`）に追加する。

## コールバックとスレッド（重要）

- Steam API は **`SteamAPI_RunCallbacks` を定期的に呼ぶ**必要がある。  
- **tkinter メインループ**では `root.after(100, pump_steam_callbacks)` のような形で統合するのが現実的。  
- CLI 専用セッションでは、入力待ちの合間に呼ぶか、専用スレッド＋ドキュメント記載の注意（公式のスレッド要件に従う）を検討する。

## 機能別の優先度と判断

### 1. 必須に近い（リリース前に検討）

| 機能 | 目的 | メモ |
|------|------|------|
| 初期化 / 終了 | 接続の成否 | `SteamAPI_Init` 失敗時は **今と同様に False で継続**可能にするか、DRM 方針で強制終了するかを製品仕様で決める。 |
| ライセンス確認 | 未購入・家庭共有等 | `ISteamApps::BIsSubscribed` 相当。方針に応じて起動直後チェック。 |
| RunCallbacks | コールバック処理 | 上記スケジューリング必須。 |

### 2. 実績（Achievements）

**方針（固定）**: Steam 版では **実績を採用**する。ゲームロジック・UI からは **`steamworks_bridge.unlock_achievement(api_name)` のみ**呼ぶ（ctypes で `ISteamUserStats::SetAchievement`、続けて `StoreStats` を試行）。ネイティブ未接続・API 不足時は `False` を返しクラッシュしない。

- Steamworks ダッシュボードで ACH を定義し、**API Name** を `basketball_sim/config/steam_achievements.py` の `STEAM_ACHIEVEMENT_API_NAMES` に追加する（リリース前は空でないことを推奨。空のときは名前検証をスキップ）。  
- `BASKETBALL_SIM_FAKE_STEAM=1` のときは実際の DLL 呼び出しは行わず `True` を返す（テスト用）。

### 3. クラウドセーブ（方針）

**採用（固定）: 選択肢 B — ローカル `%USERPROFILE%\.basketball_sim\saves` のみ（初回 Steam リリース）**

- 既存の `save_load`・パス設計と一致し、**Phase 0 の安定性・工数**を優先する。  
- Steam ストアページや FAQ で「セーブは PC ローカル」と明記し、クラウド非対応の期待差を減らす。  
- **Remote Storage / ハイブリッド用の `steamworks_bridge` API は、方針を変えるマイルストーンが決まるまで追加しない**（未決実装を避ける）。

**将来（マイルストーンで再評価）**

- 第一候補は **選択肢 C（ハイブリッド）**: ローカルを正とし、起動・終了時に任意同期＋衝突 UI。ユーザー要望・サポート負荷を見て着手タイミングを決める。  
- **選択肢 A（Remote Storage のみ）** は、クラウドを唯一の正とするほど方針転換するときのみ検討（移行・オフライン・クォータのテストが重い）。

参考（比較用・上記採用の根拠）:

| 選択肢 | 概要 |
|--------|------|
| A | Remote Storage のみ — 端末横断に強いが衝突・クォータ・テストコスト大 |
| B | ローカルのみ — **現行採用** |
| C | ハイブリッド — 将来の拡張候補 |

### 4. Rich Presence

**方針（固定）: 初回 Steam リリースでは採用しない**

- フレンド一覧向けの状態表示は、**工数・テスト・Steam パートナー側の Rich Presence ローカライズ**との整合が必要なため **v1 はスコープ外**。実績・ライセンス・`RunCallbacks` 安定を優先する。
- **将来**入れる場合の推奨: ゲーム本体はモード名など**論理キー**だけ渡し、`steamworks_bridge` に **`set_rich_presence_state(...)` のような単一入口**を置き、`ISteamFriends::SetRichPresence` と**ダッシュボード側の文言**をここに閉じる（表示文字列のハードコード乱立を避ける）。

### 5. オーバーレイ

**方針（固定）: 既定は Steam クライアントの設定に従う（通常はオーバーレイ有効）**

- v1 では **`steamworks_bridge` からオーバーレイを無効化しない**（API での一括オフはスコープ外。挙動検証とサポート文章の負荷を抑える）。
- tkinter 主画面では **Shift+Tab 等のショートカット・フォーカス**が Steam オーバーレイと競合する可能性がある。**トラブル時の第一歩**として、プレイヤーに **Steam ライブラリ → 当ゲームを右クリック → プロパティ → 「ゲーム中に Steam オーバーレイを有効にする」をオフ**を案内する（日本語ストア／README のサポート節に転記可）。

**ストア・FAQ 用たたき台（要レビュー）**

- **Q.** ショートカットが効かない／画面の切り替わりがおかしい。  
  **A.** Steam の「ゲーム中に Steam オーバーレイを有効にする」を一時的にオフにしてお試しください。改善しない場合は `logs` 添付のうえお問い合わせください。
- **Q.** オーバーレイを使いたい。  
  **A.** 既定で利用できます。競合する場合は上記のとおりゲーム単位でオフにできるほか、Steam のキー設定でオーバーレイショートカットを変更できます。

### 6. EULA・プライバシー（未着手メモ）

**現状**: ゲーム内の同意画面・専用ビューは **未実装**。リリース前に法務・Steam 要件とあわせて確定する。

**方針のたたき台（推奨）**

- **主戦場は Steam ストア／パートナー設定**: 利用規約（EULA）・プライバシーポリシーは **公式サイトまたはドキュメントホストの URL** を用意し、**Steamworks の該当欄・ストアページ**に掲載する（Steam の標準フローに乗せる）。
- **ゲーム内表示**: v1 では **必須ではない**が、**設定やクレジットからブラウザで上記 URL を開くリンク**があると問い合わせが減る。初回起動の「同意チェック」は、未成年者向け配慮や地域法規の要否を確認してから検討する。
- **本タイトルの技術メモ**: 現行クライアントは **独自の遠隔トラッキングやアカウント連携を実装していない**想定（ログ・セーブはローカル、§3）。方針変更時（アナリティクス追加など）は **プライバシーポリシーとストア表示を先に更新**する。

**リリース前チェックリスト（作業用）**

- [ ] EULA 本文の確定（日本語／英語の要否は販売地域に合わせる）
- [ ] プライバシーポリシー URL の公開と、Steamworks・ストアへの登録
- [ ] 「収集するデータ」の有無を Steam のデータ収集アンケート等に**実装どおり**記載する
- [ ] サポート・問い合わせ先（メールまたはフォーム）をストア／README に記載
- [ ] （任意）ゲーム内から上記 URL を開く導線の有無を決め、実装する
- [ ] 必要に応じて**法務レビュー**（子ども向け、特定商取引、海外販売など）

## インターフェース（`steamworks_bridge`）

公開している**薄い API**（詳細は実装参照）。

- `try_init_steam() -> bool` / `shutdown_steam()` / `pump_steam_callbacks()`
- `steam_native_loaded()` / `is_steam_initialized()` / `steam_is_subscribed() -> Optional[bool]`
- `enforce_steam_license(settings)`（ライセンス必須ポリシー時）
- `unlock_achievement(api_name: str) -> bool`
- **クラウド採用時（将来）**: `steam_cloud_upload` 等は §3 の方針変更後に、セーブ契約とあわせて別途設計する。
- **Rich Presence（将来）**: §4 のとおり v1 では未実装。着手時は `set_rich_presence_state` 相当の単一入口を想定。

**原則**: ゲーム本体（`main.py` / シミュレーション）は **「Steam 利用可否」を分岐**するだけにし、DLL や ctypes の詳細は `integrations` に閉じる。

## テスト・CI

- `BASKETBALL_SIM_FAKE_STEAM=1`: UI や「Steam 接続済み」分岐のテスト継続。  
- `BASKETBALL_SIM_DISABLE_STEAM=1`: スタジオ／CI で Steam なし確定。  
- 実 DLL を使う結合テストは **手元または限定ランナー**（ライセンス・秘密保持のため自動公開 CI には載せない想定）。

## 参照

- [Steamworks Documentation](https://partner.steamgames.com/doc/home)（パートナーアカウント要）  
- モジュール実装: `basketball_sim/integrations/steamworks_bridge.py`
