# Steamworks ステータス・再開メモ（Phase 0）

最終更新: 2026-03-27

## 現在ステータス

- ステータス: **身分確認の返答待ち**
- ブロッカー: Steamworks パートナー側の本人確認完了待ち
- 返答待ちの間に継続する方針:
  - ゲーム本体の品質改善（クラッシュ回避、UI、観戦、シーズン進行）
  - Phase 0 のうち Steamworks 非依存の項目を前進

## ここまでの Phase 0（Steam まわり）実装状況

- `steamworks_bridge.py` で Windows の `steam_api64.dll` を使った初期化経路あり
- `try_init_steam()` / `pump_steam_callbacks()` / `shutdown_steam()` の導線あり
- `enforce_steam_license(settings)` の導線あり（設定・環境変数で必須化可能）
- 実績 API 入口 `unlock_achievement(api_name)` あり
- `--steam-diag` でローカル診断可能
- v1 方針: **ローカルセーブのみ**、**Rich Presence 未実装**

参照:
- `basketball_sim/integrations/STEAMWORKS_DESIGN.md`
- `installer/README.md`

## 返答が来たら最初にやること（再開手順）

1. Steamworks パートナー側のステータス確認（本人確認完了を確認）
2. App ID / Depot ID / 必要ロール権限を確認
3. ローカルで `--steam-diag` 実行し、現在の接続状態を記録
4. `dist/BasketballGM.exe` と `steam_api64.dll` の同階層配置で再テスト
5. ライセンス必須モードで起動確認（想定どおりの終了コード/挙動）
6. SteamPipe 初回デポ投入（最小ビルド）を実施
7. Steam クライアントから起動確認（実行ファイル名一致、起動可否）

## 返答が来た日にユーザーへ出す即時指示テンプレ（3手順）

1. `https://partner.steamgames.com/apps/` を開き、対象アプリのステータスが「本人確認完了」になっているか確認  
2. 同じアプリで `App Admin`（または同等の設定画面）を開き、`App ID` と `Depot ID` をメモ  
3. その2つをチャットに貼る（私はそれを受けて、次に行うコマンドと画面操作を1本化して案内）

## 返答待ち中に先行して進めるべき実装

- GUI内の年度進行完結（CLI依存の段階的縮小）
- 契約/サラリー/FAの土台強化（Phase 3 の実操作接続を見据える）
- 回帰テスト拡充（セーブ互換、ロスター制約、シーズン終了遷移）

## 運用ルール（このメモの更新）

- Steamworks ステータスに変化があったら、このファイルを当日中に更新
- `.cursorrules` の Steamworks 進捗ルールと内容を常に一致させる
- 更新時は「ステータス」「更新日」「次アクション（誰が実施）」を必ず記載
