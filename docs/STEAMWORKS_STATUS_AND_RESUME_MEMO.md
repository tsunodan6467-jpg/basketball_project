# Steamworks ステータス・再開メモ（Phase 0）

**最終本文同期**: 2026-04-06  
**文書の役割**: 再開状況・確認状況・次に確認すべきことの**実務メモ**。ロードマップ上の位置づけは `docs/PRODUCT_ROADMAP_AND_VISION.md`、実装・運用の型は `basketball_sim/integrations/STEAMWORKS_DESIGN.md` を正とする。

---

## 現在の整理（2026-04-06）

- **Phase 0 の Steam 周り**: 長期停滞していた要因は解消し、**作業は再開済み**（プロジェクト内の合意・ユーザー報告・開発環境での確認に基づく）。
- **コード経路**: `steamworks_bridge`・`--steam-diag`・ライセンス系は **かなり整備済み**（詳細は現状分析書 §5.12・本リポジトリの実装を正）。
- **Steam API 初期化**: 適切な DLL 配置・Steam クライアント起動下で **`--steam-diag` 等により初期化成功（例: `try_init_steam: True`）がログに出る状態**まで、開発側で確認済み（**環境により異なる**。CI や Steam なし環境では `False` 継続も正常）。

---

## いま読み取れる「確認済み」（高確度・プロジェクト内）

| 項目 | メモ |
|------|------|
| 作業再開 | Steamworks 手続きが進み、Phase 0 の Steam タスクを継続できる状態。 |
| 診断・初期化 | DLL 同梱・App ID・クライアント条件が揃った環境で、**API 初期化成功ログが取れる**ことを確認。 |
| 配管・実績（概要） | `PRODUCT_ROADMAP_AND_VISION.md` 記載どおり、**App・デポ・SteamPipe default・実績の実機確認**等まで進んでいる（**細目はロードマップ正本**）。 |
| v1 方針 | **ローカルセーブのみ**、**Rich Presence v1 未**（`STEAMWORKS_DESIGN.md`・`PHASE0_COMPLETION_TEMPLATE.md` と整合）。 |

---

## 未確認・パートナー画面で都度要確認

以下は **リポジトリ外の画面**に依存する。**断定せず**、作業のたびにパートナーで確認する。

- **ストアページの一般公開状態**、**最終の「発売」審査**、その他商品として外に出す段階の残タスク（`PRODUCT` Phase 0 節と同趣旨）。
- **税務・本人確認**の「いまこの瞬間」の表示（過去に通過報告あり。**再確認が必要ならパートナーで見る**）。

---

## Phase 0（Steam まわり）実装状況（コード観点の要約）

- `steamworks_bridge.py` で Windows の `steam_api64.dll` を使った初期化経路あり
- `try_init_steam()` / `pump_steam_callbacks()` / `shutdown_steam()` の導線あり
- `enforce_steam_license(settings)` の導線あり（設定・環境変数で必須化可能）
- 実績 API 入口 `unlock_achievement(api_name)` あり（`RequestCurrentStats` 順序等は実装・テストを正）
- `--steam-diag` でローカル診断可能

参照:

- `basketball_sim/integrations/STEAMWORKS_DESIGN.md`
- `installer/README.md`
- `docs/CURRENT_STATE_ANALYSIS_MASTER.md` §5.12

---

## 実測ログ（参考）

### A. 2026-03-27（再開前・DLL 未同梱または本人確認待ち時の例）

コマンド例: `dist\BasketballGM.exe --steam-diag`（PyInstaller ビルド直後）

```
steam_diag:
  try_init_steam: False
  steam_native_loaded: False
  steam_loaded_dll_path: None
  steam_is_subscribed: None
```

`STEAMWORKS_DESIGN.md` の「本人確認待ち・DLL 未同梱の期待値（正常）」と一致する例。**現在も同条件なら同様の出力は正常**。

### B. 再開後・条件が揃った環境（2026-04-06 時点の整理）

**DLL 同階層・有効な App ID・Steam クライアント起動**など条件が揃うと、`try_init_steam: True`、`steam_loaded_dll_path` が非 null 等になり得る。**実際の1行ログは環境依存**のため、都度 `--steam-diag` で記録する。

---

## 次に確認すること（優先度の高い順）

1. **Steamworks パートナー**で、対象アプリの**現在のステータス**（公開・審査・必須タスク）を目視する。
2. **`--steam-diag`** を**配布 exe** と **開発起動**の両方で必要に応じて実行し、ログを1回スナップショットする（長期比較用）。
3. `PRODUCT` に書いた **残タスク**（ストア・発売・法務表記等）のうち、次に着手する1件を `docs/IMPLEMENTATION_PLAN_MASTER.md` から切り出す。

細かいクリック手順は **`STEAMWORKS_DESIGN.md`** のチェックリストと Valve 公式ドキュメントを正とする。本メモには手順の全文を増やしすぎない。

---

## 先行して進めてよい実装（Steam 非依存・プロジェクト方針）

- GUI 内の年度進行完結（CLI 依存の縮小）
- 契約 / サラリー / FA の土台強化
- 回帰テスト拡充（セーブ互換、ロスター制約、シーズン終了遷移）

---

## 運用ルール（このメモの更新）

- Steamworks の**事実**（審査・公開・パートナー表示）に変化があったら、**当日中に**本ファイルを更新する。
- `docs/PRODUCT_ROADMAP_AND_VISION.md` の Phase 0 Steam 節と**矛盾しない**ようにする（詳細は本メモ、一行要約は PRODUCT）。
- 更新時は **「最終本文同期」**、**確認済み / 未確認**、**次アクション（誰が実施）** を必ず分かるように書く。
- `.cursorrules` の Steam 一行要約とずれる場合は、**docs 優先で直し**、必要なら `.cursorrules` を別コミットで追随する（本メモの役割外だが整合のため記載）。

---

## 履歴メモ

- **2026-03-27 版**: 身分確認返答待ちをブロッカーとして記載していた。**2026-04-06** に再開後の状態へ整理し、旧「返答待ち」前提の文言を更新した。
