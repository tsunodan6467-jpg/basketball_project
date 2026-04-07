# 国内バスケGM開発 FA年俸目安監査メモ

**作成日**: 2026-04-06  
**文書の性質**: **調査メモ**。オフFA GUI 等で見える **年俸目安**と、実契約・CPU オファーが **どの関数から来るか**をコード追跡で整理する。**数値の正しさの断定や修正案の確定はしない**（修正は別タスク）。

| 参照 | 文書 |
|------|------|
| オフ・手動1人FA GUI | `docs/GUI_FULL_FA_MARKET_ENTRY_POLICY.md` |
| インシーズンFA GUI | `docs/GUI_INSEASON_FA_ENTRY_POLICY.md` |
| 現状ラベル | `docs/CURRENT_STATE_ANALYSIS_MASTER.md` |
| 経済・締めと FA | `docs/ECONOMY_DESIGN_NOTES.md`（`money` と payroll の扱い） |
| 金流の事実 | `docs/ECONOMY_MONEY_FLOW_AUDIT.md` |
| 年俸モデルをどこまで揃えるか（方針） | `docs/FA_SALARY_MODEL_ALIGNMENT_POLICY.md` |

**静的確認の基準**: `basketball_sim/systems/free_agent_market.py`、`free_agency.py`、`offseason_full_fa_tk.py`、`main_menu_view.py`（インシーズンFAウィザード部）を 2026-04-06 時点で照合。

---

## 0. この文書の使い方

- **何のためか**: 「年俸目安が低く見える」体感の前に、**表示・実契約・CPU が同じ式か**を事実で固定し、**誤った場所を直す**のを防ぐ。
- **調査メモであること**: プレイ感の良し悪しの評価や、バランス調整の最終方針は **本書の範囲外**。
- **修正は別タスク**: `estimate_fa_market_value` の係数変更、GUI 文言、CPU `_calculate_offer` の統合などは **別コミット・別設計**で扱う。

---

## 1. 現在見えている問題（事実と未確認）

| 項目 | 内容 |
|------|------|
| **報告されている体感** | **オフFA GUI**（`offseason_full_fa_tk`）の一覧・確認ダイアログで示す **年俸目安**が、プレイヤー期待より **かなり低く見える**ことがある（**主観**。**未検証**: 全OVR帯での統計は未実施）。 |
| **どの画面か** | **オフシーズン実行中・本格FA直前**の「オフFA（手動で1人まで）」ウィンドウ。インシーズン人事の「インシーズンFA（1人）」も **同系の数値**を表示する。 |
| **まだ未確認な点（例）** | ① 実プレイで **同一選手**について GUI 表示額と契約後ロスター上の `salary` が一致するかの **スクリーンショット級の確認**（コード上は一致する設計）。② プレイヤーの「低い」基準が **他ゲーム・現実NBA**なのか **同一セーブ内の既存契約年俸**なのか（**未確認**）。 |

---

## 2. 表示値の出所

### 2.1 オフFA GUI（`offseason_full_fa_tk.py`）

| 表示箇所 | 呼び出し | 備考 |
|----------|----------|------|
| Treeview の年俸・年数 | `offseason_manual_fa_offer_and_years(user_team, player)` → 内部で **`free_agency._calculate_offer`** / **`_determine_contract_years`**（**`conduct_free_agency` と同型**、2026-04-06 実装反映）。 |
| 制限確認 | `precheck_user_fa_sign(..., contract_salary=offer)` | 上記 **offer** で所持金・サラリー余地を判定。 |
| 最終確認・契約 | `sign_free_agent(..., contract_salary=..., contract_years=...)` | 表示と **同一の offer / years** を適用。 |

**結論（事実）**: オフ手動FA GUI の年俸・年数は **estimate ではなく本格FA同型**。表示専用と実契約の **別ソースはない**（**表示＝契約**）。

### 2.2 インシーズンFA GUI（`main_menu_view._run_inseason_fa_one_wizard`）

| 表示箇所 | 呼び出し |
|----------|----------|
| Treeview「年俸目安」 | `estimate_fa_market_value(p)` |
| 制限確認・最終確認 | 同上 + `estimate_fa_contract_years` |

**結論（事実）**: インシーズンFA GUI は **estimate 系**。オフ手動FA GUI は **本格FA同型（§2.1）**。**オフ手動とインシーズン手動ではモデルが異なる**（意図的・`FA_SALARY_MODEL_ALIGNMENT_POLICY.md`）。

---

## 3. 実契約値の出所（`sign_free_agent`）

`free_agent_market.sign_free_agent(team, player, *, contract_salary=None, contract_years=None)`（抜粋）:

| 項目 | 出所 |
|------|------|
| **既定（インシーズン等）** | `contract_salary` 未指定時は `estimate_fa_market_value`、年数は `estimate_fa_contract_years`。 |
| **オフ手動FA** | `contract_salary` / `contract_years` 指定時は **その値**を適用（**本格FA同型の offer** と揃える）。 |
| **ガード** | `can_team_sign_player_by_japan_rule`、`salary <= 0` で return、`salary > get_team_fa_signing_limit` で **早期 return**。 |

**結論（事実）**: **オフ手動GUI**では表示に使った額と **`sign_free_agent` の `contract_salary` が同一**。**インシーズンGUI**では表示＝**estimate**＝未指定時の `sign_free_agent`。

**契約年数**: オフ手動は **`_determine_contract_years`**（§4 と同型）。インシーズン手動は **`estimate_fa_contract_years`**。

---

## 4. CPU FA のオファー額の出所

### 4.1 オフ・本格FA `conduct_free_agency`（`free_agency.py`）

| 項目 | 出所 |
|------|------|
| **オファー額** | **`_calculate_offer(team, player)`**（`estimate_fa_market_value` は **使わない**）。 |
| **年数** | **`_determine_contract_years(player, team, offer)`**（`estimate_fa_contract_years` は **使わない**）。 |
| **成立時の年俸** | 抽受後 `candidate.salary = offer`（**オファー額＝契約年俸**）。 |

`_calculate_offer` の要点（**要約・事実**）:

- ベースは **`player.salary`（>0 のとき）**。≤0 のときは `max(ovr * 10_000, 300_000)`。
- チーム `money` との差の 5% など **ボーナス項**、**ソフトキャップ／ハードキャップ／payroll_budget／贅沢税**に応じた **上限クリップ**。

**結論（事実）**: **オフ CPU 本格FA**の金額は **`estimate_fa_market_value` とは別ロジック**。同一選手でも **手動 `sign_free_agent` の年俸と CPU オファーは一致しないことがある**。

### 4.2 インシーズン CPU 補強 `run_cpu_fa_market_cycle`（`free_agent_market.py`）

| 項目 | 出所 |
|------|------|
| **誰を取るか** | `pick_best_free_agent_for_team` → 候補は `can_team_afford_free_agent` 等で絞る（内部で **`estimate_fa_market_value` を使用**）。 |
| **契約の適用** | **`sign_free_agent(team, target)`**。 |
| **ログの Salary 表示** | `estimate_fa_market_value(target)`（**実契約と同じ estimate**）。 |

**結論（事実）**: インシーズン CPU 補強の **実契約**は **常に `sign_free_agent` → `estimate_fa_market_value`**。オフ CPU 本格FA（`conduct_free_agency`）とは **額の決め方が異なる**。

---

## 5. 一致している点 / ずれている点

| 比較 | 関係（事実） |
|------|----------------|
| **オフFA GUI 表示 ↔ 手動 `sign_free_agent` 契約年俸** | **同一**（`estimate_fa_market_value`）。 |
| **インシーズンFA GUI 表示 ↔ 手動 `sign_free_agent`** | **同一**（同上）。 |
| **オフFA GUI ↔ オフ `conduct_free_agency` のオファー** | **別ロジック**（GUI/手動は estimate、CPU 本格FA は `_calculate_offer`）。 |
| **手動 `sign_free_agent` ↔ インシーズン CPU `run_cpu_fa_market_cycle`** | **契約年俸の式は同一**（どちらも `sign_free_agent`）。 |
| **手動 `sign_free_agent` ↔ オフ `conduct_free_agency`** | **一般に非一致**（後者は `_calculate_offer` ベース）。 |
| **契約年数：手動FA ↔ オフCPU FA** | **別**（`estimate_fa_contract_years` vs `_determine_contract_years`）。 |

---

## 6. 原因候補と次タスク候補（断定しない）

### 6.1 原因候補（コードに基づく **候補**）

| 候補 | 説明 |
|------|------|
| **estimate 式そのもの** | `estimate_fa_market_value` は `base = max(ovr * 12_000, 400_000)` を核に potential/年齢/FA待機で加減算。**高OVRでも数百万円台に留まりやすい**構造（例: OVR70 → 840,000 スタート前後）。 |
| **他システムの年俸スケールとの比較** | `game_constants` には `PLAYER_SALARY_BASE_PER_OVR = 1_000_000` 等があり、**ロスター上の既存年俸**は別ルールで付いている可能性。**同一選手の「昔の salary」が高い**と、CPU 本格FAの `_calculate_offer` は **その salary をベース**にしうるため、**ログ上は高く見え、GUI estimate は低く見える**、という **見かけのギャップ**が起きうる（**状況依存**）。 |
| **単位・フォーマット** | GUI は `:,` 区切りの **円**。**万円表示ではない**（混同時の誤読候補）。 |
| **「表示だけ低い」** | **該当なし**（表示も契約も同じ `estimate_fa_market_value`）。 |

### 6.2 次タスク候補（1〜3件）

1. **仕様判断**: 手動FAとオフCPU本格FAで **年俸決定を揃えるか**は **`FA_SALARY_MODEL_ALIGNMENT_POLICY.md`** で第1弾スコープを固定。**本監査メモでは決めない**。
2. **検証**: 実セーブで **具体選手1〜2名**について、GUI 表示・契約後 `salary`・同一オフの `[FA-OFFER]` ログを並べ、**期待との差**を記録する（**再現手順付きメモ**）。
3. **ドキュメント**: プレイヤー向けに「手動FAの年俸は市場目安アルゴリズム」「CPU本格FAは別計算」と **一文で区別**するか（**別タスク**）。

---

## 7. 更新ルール

- **`estimate_fa_market_value` / `_calculate_offer` / `sign_free_agent` のいずれかを変えたら**、本書の §2〜§5 を **コードに合わせて更新**する。
- **バランス調整の正本**は本書にしない（実装コメント・設計書へ）。

---

## 変更履歴

- 2026-04-06: 初版。表示＝`estimate_fa_market_value`、手動契約＝同一、オフCPU本格FA＝`_calculate_offer`、インシーズンCPU＝`sign_free_agent` を整理。
- 2026-04-06: 参照に `FA_SALARY_MODEL_ALIGNMENT_POLICY.md` を追加。§6.2 の「仕様判断」を方針メモへ誘導。
- 2026-04-06: **オフ手動FA**を本格FA同型に変更（§2.1・§2 結論・§3）。`sign_free_agent` / `precheck_user_fa_sign` のオプション追記。
