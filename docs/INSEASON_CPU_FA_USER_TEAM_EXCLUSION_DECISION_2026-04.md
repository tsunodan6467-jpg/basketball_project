# インシーズン CPU FA：ユーザーチームを自動補強対象から除外するか（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。関連実装: `Season._process_inseason_free_agency`（`basketball_sim/models/season.py`）、`run_cpu_fa_market_cycle`（`basketball_sim/systems/free_agent_market.py`）、締切判定（`basketball_sim/systems/season_transaction_rules.py`）。観測用 save 要件の文脈: `docs/FA_CLIP_COMPARE_SAVE_REQUIREMENTS_2026-04.md`、`docs/FA_OBSERVER_SAVE_SCREENING_2026-04.md`。

---

## 1. 文書の目的

`simulate_next_round()` 経由の **インシーズン CPU FA** が **ユーザーチームにも `sign_free_agent` を適用しうる現仕様**について、**ユーザー意思外の自動補強を許すか**を整理し、**次実装の第一方針**を1本に固定する。

---

## 2. 現仕様の整理

- **呼び出し連鎖**: `Season.simulate_next_round()` → `_process_inseason_free_agency(round_number)` → `run_cpu_fa_market_cycle(teams=self.all_teams, free_agents=self.free_agents, max_signings_per_team=1, simulated_round=round_number)`。
- **`run_cpu_fa_market_cycle`**: 渡された `teams` を順に処理し、条件を満たせば **`sign_free_agent(team, target)`** を実行する（ロスター14人未満・FA在庫・締切内など）。
- **ユーザーチーム除外**: **`_process_inseason_free_agency` 側にも `run_cpu_fa_market_cycle` 側にも、`is_user_team` によるスキップは見えない**。よって **ユーザーチームも `self.all_teams` 経由で CPU FA の対象になりうる**。
- **締切**: `simulated_round` が `cpu_inseason_fa_allowed_for_simulated_round` を満たす間のみ動作（ラウンド22超過後は空振り）。これは **全チーム共通**のガードであり、ユーザー限定の例外ではない。
- **長所**
  - **全チーム同一ルール**（実装が単純、説明しやすい）。
  - **CPU 自動補強の一本化**（「人数が減ったら市場から拾う」が全チームに均等にかかる）。
- **短所**
  - **ユーザーが意図せずロスターが変わる**（ラウンド進行だけで補充されうる）。
  - **観測用 save が汚れやすい**（意図的に薄くしたロスターが維持できない）。
  - **検証・再現性**（FA clip / payroll 観測で「薄いロスター」を固定したい場合に不利）。
  - **プレイ感**（トレードで人数を減らしたのに、シミュが勝手に埋める違和感）。

---

## 3. ユーザーチーム除外案

- **実装イメージ（例）**
  - **`_process_inseason_free_agency`**: `run_cpu_fa_market_cycle` に渡す `teams` を **`[t for t in self.all_teams if not getattr(t, "is_user_team", False)]`** のようにする。
  - **または `run_cpu_fa_market_cycle` 内**: `is_user_team` のチームはループをスキップする（全呼び出し元に効く）。
- **長所**
  - **ユーザー意思外の自動補強を防げる**（シミュ進行がロスターを勝手に埋めない）。
  - **観測用 save を維持しやすい**（意図的な薄さを保持できる）。
  - **補強はプレイヤー操作（人事 GUI のインシーズンFA 等）に委ねられる**。
- **短所**
  - **CPU とユーザーのシミュ上の対称性は崩れる**（「同じルールで全チームが市場を漁る」ではなくなる）。
  - **人数不足のまま試合が進む**場合の扱い（最低人数・試合成立・forfeit 等）は **別途の設計・決裁が残る**。
  - **公平性の語り方**が変わる（CPU は自動補強しうるが、ユーザーはシミュ経由では自動で埋められない）。

---

## 4. 推奨判断

**第一候補: インシーズン CPU FA の自動補強対象からユーザーチームを除外する。**

- **理由（本プロジェクト段階）**
  - **観測用 save の作成・維持**が FA / payroll 調査の前提になっており、**現仕様はその前提を壊しやすい**。
  - **プレイヤー意思外のロスター変更**は体験上のコストが大きく、**「CPU が補う」ことのメリットより優先すべき**。
  - **人手でのインシーズンFA**（別経路）が既にあり、**「自動は CPU のみ・ユーザーは自発的に獲得」**は説明可能。
- **現仕様を主路線に残さない理由**
  - **対称性の簡潔さ**より、**再現可能な観測・ユーザー主権**を先に満たす方が、現在の開発焦点に合う。
  - 対称性が必要なモードは、将来 **オプション**（例: 「ユーザー自動補強 ON」）として切り替え可能にする方が安全（本メモでは実装しない）。

---

## 5. 決裁用の1行結論

**インシーズン CPU FA 自動補強（`simulate_next_round` 経由の `run_cpu_fa_market_cycle`）の対象からユーザーチームを除外し、ユーザーチームの補強はプレイヤー操作のみとする。**

---

## 6. 今回はまだやらないこと

- **本決裁に基づく具体コード修正**
- **最低人数ルールの改造**
- **forfeit / 試合成立人数の改造**
- **payroll_budget clip 系の修正**
- **`sign_free_agent` / `run_cpu_fa_market_cycle` のアルゴリズム変更**（除外以外の挙動変更）

---

## 7. 次に実装で触るべき対象（1つだけ）

**`Season._process_inseason_free_agency` で、`run_cpu_fa_market_cycle` に渡す `teams` から `is_user_team` を除いたリストを渡す最小差分**（＋該当経路のテスト更新・スモーク）。

- **なぜその1手が今もっとも妥当か**
  - **シーズンシミュ経路だけ**に効き、**「毎ラウンドの CPU FA」**という問題の発生源に直結する。
  - **`run_cpu_fa_market_cycle` を汎用関数のまま**残し、**pytest 等で明示的に全チームを渡すテスト**との切り分けがしやすい。
- **何はまだ残るか**
  - **人数不足時の試合・forfeit・最低ロスター**の別決裁。
  - **オプション化**（対称性重視モード）の要否。
  - **GUI / CLI からの `run_cpu_fa_market_cycle` 直呼び**がある場合の整合確認（現状の呼び分けに応じた追従）。

---

## 改訂履歴

- 2026-04-08: 初版（決裁メモ）。
