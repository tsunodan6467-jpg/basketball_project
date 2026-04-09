# user team の `payroll_budget`：ゲーム進行順の設定・維持・再設定（原因整理）

**作成日**: 2026-04-08  
**文書の性質**: **原因分析メモ（コード変更なし）**。前提: `docs/PAYROLL_BUDGET_PERSISTENCE_CAUSE_NOTE_2026-04.md`（保存経路）、`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`（before gap）、round-trip 実証 `basketball_sim/tests/test_payroll_budget_roundtrip.py`（load は不変）。

---

## 1. 文書の目的

**load が壊している説を弱めたうえで**、**save 前のゲーム進行のどの段階で user team の `payroll_budget` がその値になるか**を、**実行順ベース**に整理する。**「低い／既定の budget がどこで固定化しうるか」**の主線仮説を、次の観測・実装担当がそのまま使える形で固定する。

---

## 2. `payroll_budget` の時系列整理

### 2.1 どこで代入（新規・再設定）されるか（コードから読める）

| 順序目安 | 処理・モジュール | 内容 |
|----------|------------------|------|
| ① | **`Team` dataclass**（`basketball_sim/models/team.py`） | フィールド既定 **`payroll_budget = 120_000_000`**。 |
| ② | **`generate_teams()`**（`generator.py`） | `Team(...)` 生成時 **`payroll_budget` を渡さない** → **①の既定のまま**。ロスター年俸は `_rebalance_team_initial_salaries_to_target` で調整。 |
| ③ | **`apply_user_team_to_league()`**（`main.py`） | 名前・`money`・`is_user_team` 等を設定。**`payroll_budget` は触らない**（置き換え元 D3 チームの値＝多くの場合 ② と同じ既定）。 |
| ④ | **ドラフト**（`auto_draft_players` / `draft_players` 等） | 選手・年俸は変わる。**`team.payroll_budget` への代入はこの経路に無い**（静的 grep 上）。 |
| ⑤ | **`normalize_initial_payrolls_for_teams()`**（`main.py` の `build_initial_game_world` 末尾、`contract_logic`） | **所属選手の年俸をキャップ下に正規化**。**`Team.payroll_budget` 自体は更新しない**。 |
| ⑥ | **`Offseason.run` 内・FA 直前**（`offseason.py`） | **`_sync_payroll_budget_with_roster_payroll`**（2回）: **`payroll_budget = max(既存, roster_payroll + buffer)`**。下げはしない。 |
| ⑦ | **`Offseason.run` 内・FA の後**（`offseason.py`） | **`_process_team_finances()`** 内で **`team.payroll_budget = max(base_budget, 市場・人気・スポンサー等の式)`** として **「来季人件費目安」を再計算・上書き**。 |
| ⑧ | **load 直後**（`save_load.normalize_payload`） | **`payroll_budget` の再計算なし**（round-trip テストで不変を確認済み）。 |

### 2.2 どこでは基本的に維持（代入されない）か

| 範囲 | 内容 |
|------|------|
| **レギュラーシーズン進行**（`Season`） | **`payroll_budget` への代入は見当たらない**（静的確認）。シーズン中キャッシュは `money` 側。年次収支の正本はオフ `_process_team_finances` 寄り（`season.py` コメント系と整合）。 |
| **`record_financial_result`（`Team`）** | **`money` と昨季収支フィールドのみ更新**。**`payroll_budget` は更新しない**。 |
| **save→load** | pickle で **属性ごと復元**。 |

### 2.3 観測済みとの対応（整理）

- **user_team_snapshot で「money 大・payroll_budget 小」**: **③で `money` だけ上がり、③〜⑤で `payroll_budget` は触られない**ため、**②の既定（1.2 億）のまま**になりやすい、と読める。
- **before gap=0**: **`payroll_budget << roster_payroll`** のとき **`max(0, budget − roster)=0`**（別メモ）。

**断定でない部分**: 実プレイ save が **⑥⑦ を何回通したか**は save 依存。**GUI 経路で `build_initial_game_world` を飛ばす場合**も、**⑤の有無**でロスター年俸だけ差が出うる。

---

## 3. 既定 observer ワールドと実プレイ save の差が出そうな地点

| 観点 | 既定 `fa_offer_real_distribution_observer`（`--seasons 0`） | 実プレイ CLI 新規（`build_initial_game_world`） |
|------|--------------------------------------------------------------|--------------------------------------------------|
| **`generate_teams` / `apply_user` / ドラフト / `assign_fictional...`** | **通る**（`main` から同系関数を import） | **通る** |
| **`normalize_initial_payrolls_for_teams`** | **呼ばない** | **呼ぶ**（⑤） |
| **`Season.simulate_to_end`** | 既定では **0 周** | プレイに応じ **1 年以上** |
| **`Offseason.run`（⑥⑦）** | **通さない**（observer 単体ではオフ未実行） | **シーズン終了後に通りうる** |

**主線仮説（コード＋経路差）**

- **`payroll_budget=120M` が残りやすい**: **②③④ までで止まり、⑤も「budget フィールドは変えない」、⑥⑦ に未到達**（**observer 既定**、**レギュラー途中 save**、**初年度オフ前 save** 等）。
- **オフ締めを通すと**: **⑦で式による再設定**が入り、**⑥で床同期**も FA 直前にかかる（順序: ⑥ → FA → **⑦** は `Offseason.run` の並びとして **⑦が FA の後**）。

**逆に「再設定されうる」**: **少なくとも 1 回 `Offseason.run` が `_process_team_finances` まで到達**した save。

---

## 4. 今回の原因整理から分かること

- **主因候補（強い）**: **「既定 120M のまま残る経路」**と **「オフ `_process_team_finances` で⑦が走る経路」**の差。**money は timeline 上の別レーン**。
- **疑うべき断面**: **「最後に ⑦ が走ったか」**、走っていなければ **②〜⑤の時点の値がそのまま save に載る**（load は壊さない）。
- **7 人ルール**: **先に上記 timeline のどこで固定されているか**を切らないと、人数だけいじっても **budget フィールドは動かない**可能性が高い（優先度は低め）。
- **いちばん切り分けが進む段階差**: **「新規ロスター確定直後（⑤直後）の `payroll_budget`」** vs **「1 オフ完了後（⑦直後）の `payroll_budget`」**。

---

## 5. 今回はまだやらないこと

- **`payroll_budget` 式・同期・clip の改修**  
- **observer の出力変更**  
- **7 人ルールの変更**

---

## 6. 次に実装で触るべき対象（1つだけ）

**対話なしで再現できる順序として、`generate_teams` → `apply_user_team_to_league`（テスト用に既存 D3 を user 化）→ 最小ドラフト相当でロスターに給与付き選手を載せる → `normalize_initial_payrolls_for_teams(teams)` まで実行した直後の user `payroll_budget` が **依然 `120_000_000`（既定）のままであることを assert する pytest を 1 本追加する**（`build_initial_game_world` と同じ「⑤まで」の帰結をコードで固定）。**

- **なぜその1手が今もっとも妥当か**  
  **「新規開始直後は budget フィールドは触られず既定のまま」**を自動で証明でき、**実プレイ mid-season save の低 budget** と **「⑦未経過」** の読みを接続できる。  
- **何はまだ残るか**  
  **`Offseason.run` 完了前後（⑥直前・⑦直後）のスナップショット**、**実 save の「オフ通過有無」メタデータの記録**、**本番対話フローとの完全一致検証**。

---

## 実行コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python -m basketball_sim --smoke
```

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md -Pattern "120|_process_team_finances|normalize_initial|Offseason"
```

---

## 改訂履歴

- 2026-04-08: 初版（実行順ベースの `payroll_budget` 整理）。
