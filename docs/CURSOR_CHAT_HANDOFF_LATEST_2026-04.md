# Cursor チャット引き継ぎ正本（最新）

**更新日**: 2026-04-08  
**用途**: 新しい Cursor チャットへ**文脈をズレなく渡す**ための単一正本。実装の細部は **docs 既存メモ**と **git 履歴**に委ね、ここでは**判断・現在地・次の1手**を固定する。

---

## 1. この文書の目的

- 新チャットが **すぐ同じ前提**で動けるようにする。  
- **長文コードは不要**（チャットでは **変更ファイル名 / 要点 / 実行コマンド / 抽出コマンド / 差分要約** を優先する運用と整合）。  
- **1コミット1目的**を維持する。

---

## 2. 現在の開発テーマの要約

- **主題**: オフシーズン FA における **`payroll_budget`（`room_to_budget`）クリップ**と、提示年俸（`_calculate_offer` 系）の整合。  
- **経緯の認識**: **buffer（`_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER`）を 3M→10M→30M と上げる S6 試行**で現象は動いたが、**本命は「クリップ構造・式」側**であると整理済み（張り付き／全面化の説明は buffer 単体では足りない）。  
- **`room_to_budget` クリップ**は **`_clip_offer_to_payroll_budget(...)` に単一ヘルパ化**済み（`_calculate_offer` と diagnostic で共有）。

---

## 3. 現在の最重要決裁済み事項

| 論点 | 決裁の要旨 | 参照 doc（例） |
|------|------------|----------------|
| クリップ式 | 線形緩和（内分）案を土台化し、λ で調整 | `docs/FA_PAYROLL_BUDGET_CLIP_FORMULA_OPTIONS_NOTE_2026-04.md` |
| λ 第一試行 | **0.1** | `docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_FIRST_TRIAL_DECISION_2026-04.md` |
| λ 第二試行 | **0.05** | `docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_SECOND_DECISION_2026-04.md` |
| 第三試行 vs 行列 | **主路線は λ=0.025 ではなく、観測行列の差し替え／拡張方針を先に設計** | `docs/FA_PAYROLL_BUDGET_CLIP_THIRD_TRIAL_OR_MATRIX_DECISION_2026-04.md` |

---

## 4. 直近の実装済み内容

- **`basketball_sim/systems/free_agency.py`**: `_clip_offer_to_payroll_budget` 抽出後、**`_PAYROLL_BUDGET_CLIP_LAMBDA` は現状 `0.05`**（第二試行まで反映済み）。  
- **クリップ専用テスト**: `basketball_sim/tests/test_free_agency_payroll_budget_clip.py`（既定 λ、代表数式、λ=0 monkeypatch 回帰）。  
- **観測ツール**（改修は別タスク）: `tools/fa_offer_real_distribution_observer.py`、`tools/fa_offer_diagnostic_observer.py`。  
- **buffer 30M** 等の過去試行は `offseason` 側定数・決裁メモに記録（詳細は git と S6 系 docs）。

---

## 5. 直近の観測で分かったこと

- **λ=0.1 / 0.05** いずれも、**現行の real distribution observer 行列**（上位 FA × 全チーム、1920 ペア）では **`final_offer > buffer`（表示 30M）が全面化**し続けた（quick / quicksave / `--seasons 1` で同型の記録あり）。  
- **合成 diagnostic** では λ の効きが見える（例: 高額 S6b で **37.86M → 33.93M**、λ=0.05 時）。  
- **gap 観測**（`docs/FA_PAYROLL_BUDGET_CLIP_GAP_PLAYCHECK_2026-04.md`）: 現行行列では **`offer_after_soft_cap_pushback > room_to_budget` が 1920/1920**、**`room_to_budget` は 30M 固定**、**offer はおおよそ 約72M〜102M（中央 約85M 前後）**、**offer/room 約 2.34〜3.41**。→ **行列が `offer ≫ room` で飽和**しており、**λ を細かく動かしても「全面 > buffer」が解けにくい**のは構造と整合。  
- したがって **次の主路線は λ 第三試行ではなく、観測行列の差し替え／拡張の設計**（決裁済み）。

---

## 6. 今はまだ触らないこと

- **`_PAYROLL_BUDGET_CLIP_LAMBDA` の無決裁変更**（第三試行 0.025 は**主路線にしない**決裁済み。必要なら**別決裁**）。  
- **`_clip_offer_to_payroll_budget` の式タイプ変更**（線形以外への切替は決裁後）。  
- **`_calculate_offer` / `_calculate_offer_diagnostic` の全面改造**（構造一致テストがある）。  
- **floor / オフ手動 FA 全面再設計 / 低額例外ルールの本体 / generator・GUI・経営収支のついで改修**。  
- **観測スクリプトの無設計改修**（行列差し替えは**設計メモ承認後**に段階的に）。

---

## 7. 固定運用ルール

- **1コミット1目的**。**ついで修正禁止**（依頼範囲外のリファクタや別テーマを混ぜない）。  
- チャット返答は **長文コード直書きを避け**、**変更ファイル名 / 要点 / 実行コマンド / 抽出コマンド / 差分要約**を優先。  
- 着手前に **本ファイル**と、該当する **FA 系 docs** を読む。  
- ユーザー・プロジェクトの **user rules**（実環境でコマンド実行、日付の前提など）に従う。

---

## 8. 直近コミット一覧（新しい順・主要のみ）

| ハッシュ | メッセージ（要約） |
|----------|-------------------|
| `396abb2` | docs: FA payroll budget clip third trial vs matrix decision |
| `2757711` | docs: FA payroll budget clip offer-room gap playcheck |
| `2608ca4` | feat(fa): second trial payroll budget clip lambda 0.05 |
| `63d7ba2` | docs: FA payroll budget clip lambda second trial decision (0.05) |
| `e89de6a` | docs: FA payroll budget clip lambda 0.1 playcheck memo |
| `c9e6f29` | feat: set payroll budget clip lambda to 0.1 (first trial) |
| `b01e7b8` | docs: FA payroll budget clip lambda first trial 0.1 decision |
| `edd69c2` | feat: add payroll budget clip linear lambda scaffold (default 0) |
| `3d6f84f` | docs: FA payroll budget clip formula options and first trial |
| `4f848b3` | refactor: extract payroll budget clip to `_clip_offer_to_payroll_budget` |
| `ae4cc85` | docs: FA room_to_budget clip redesign note |
| `156e954` | Raise offseason FA payroll budget buffer to 30M (S6 third trial) |
| （以下） | S6 buffer 試行・observer 出力拡張など（`git log` 参照） |

---

## 9. 現在地の要約

- **クリップ構造＋λ** まで実装し、**λ は 0.05 で固定**。  
- **現行観測行列**では **`final > buffer` 一色**と **`offer ≫ room` 飽和**が両方確認でき、**λ だけをさらに刻む優先度は低い**。  
- **決裁どおり**、次は **観測行列の差し替え／拡張を docs で設計**してから、必要なら observer や λ を動かす。

---

## 10. 次にやるタスク（1つだけ）

**`docs/` に、観測行列の差し替え（または拡張）の「母集団・再現手順・成功指標」を1〜2ページで固める短い設計メモを1本追加する**（中額 FA、`room` 分布、別 save／シーズン後、top N の取り方など。**コード変更はこのメモの Go 後**。根拠: `docs/FA_PAYROLL_BUDGET_CLIP_THIRD_TRIAL_OR_MATRIX_DECISION_2026-04.md` §7）。

---

## 11. 新チャットの最初の指示文（そのまま貼れる形）

```text
まず docs/CURSOR_CHAT_HANDOFF_LATEST_2026-04.md を全文読み、現状・決裁・次の1手を把握してください。

ルール:
- いきなりコードを書かないこと。
- 最初の返答は次の3点のみにすること:
  1) 現状理解の要約
  2) 絶対に守るルール（本ファイル §7 と user rules）
  3) 次にやるタスク1つ（本ファイル §10）
- 長文コードは不要。必要なら本ファイルと関連 docs を再確認してから答えること。
- 1コミット1目的。ついで修正禁止。

理解後、§10 のタスクに着手する場合は、その設計メモのファイル名案と章立て案から始めてください。
```

---

## 参考コマンド（検証・抽出）

**スモーク**

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

**本ファイルの要点抽出**

```powershell
Select-String -Path docs\CURSOR_CHAT_HANDOFF_LATEST_2026-04.md -Pattern "次にやる|主路線|0\.05|触らない|決裁"
```

---

## 改訂履歴

- 2026-04-08: 初版（新チャット移行用正本）。
