# オフFA直前: `payroll_budget` と実ペイロールの同期・前処理改善 設計書

**作成日**: 2026-04-06  
**文書の性質**: **設計のみ**。本書はコード変更を伴わない。実装時は `docs/OFFSEASON_MANUAL_FA_ALIGNMENT_PLAN_2026-04.md`、`docs/OFFSEASON_MANUAL_FA_PLAYCHECK_2026-04.md` と整合させる。  
**動機**: オフ手動FAで `_calculate_offer` が 0 になり estimate フォールバックが発火する主因の一つとして、**オフFA直前の `payroll_budget` と実ペイロール（ロスター年俸合計）のズレ**が疑われるため、**どこでズレ、どこで同期すべきか**を整理する。

---

## 1. 文書の目的

1. `payroll_budget` が**どこでセット・参照**され、**実ペイロール**と**いつ乖離**しうるかをコード根拠付きで押さえる。  
2. **オフFA直前**（手動1人 GUI → CPU 本格 `conduct_free_agency`）において、なぜ **`room_to_budget = payroll_budget - payroll_before` が 0** になりやすいかを説明可能にする。  
3. **同期・前処理**の候補を比較し、**第1弾で触るべき最小・安全な箇所**と、**`_calculate_offer` 本体をまだ触らずに済むか**を明示する。

---

## 2. `payroll_budget` と実ペイロールの現在の関係

### 2.1 どこに保持されるか

- **`payroll_budget`** は **`Team` のフィールド**（既定値は大きめの整数。`basketball_sim/models/team.py`）。セーブ・ロードや `__post_init__` で非負整数に正規化される。  
- **実ペイロール（ロスター年俸合計）** は **`get_team_payroll(team)`**（`basketball_sim/systems/contract_logic.py`）で、**所属 `players` の `salary` 合算**として都度計算される。永続フィールドではなく**導出値**。

### 2.2 どこで更新されるか（現状の「正本」）

コードベース上、**シーズン進行に沿った再計算で `payroll_budget` を上書きしている主経路**は、**オフシーズン末尾の `_process_team_finances`**（`basketball_sim/models/offseason.py`）内である。ここでは市場規模・人気・スポンサー等から **「来季人件費目安」**として `team.payroll_budget` が **`max(base_budget, 式…)`** で再設定され、ユーザー向けログにも **「来季人件費目安」**として出力される。

**grep 上、`payroll_budget =` の代入はテスト用・初期化以外ではこの財務処理が中心**である（他は `Team` 初期化・正規化のみ）。

### 2.3 `_calculate_offer` がどう使うか

`basketball_sim/systems/free_agency.py` の `_calculate_offer` は:

- **`payroll_before = _team_salary(team)`**（内部で `get_team_payroll`）として**実ペイロール**を取得する。  
- ソフトキャップ超え等の分岐の後、**クラブ予算**として **`payroll_budget = getattr(team, "payroll_budget", soft_cap) or soft_cap`** を読む。  
- **`room_to_budget = max(0, payroll_budget - payroll_before)`** とし、**`offer` を `room_to_budget` でクリップ**する（`room_to_budget == 0` ならオファーは 0 になりうる）。

つまり **「実際のロスター年俸」は常に最新の合算**だが、**「予算ライン」は `Team` に蓄積されたスカラー**であり、**オフ中にロスターが動いても自動では追従しない**。

### 2.4 責務のあるべき姿（設計上の整理）

- **実ペイロール**: ロスターの真実。契約・トレード・ドラフト・満了処理の結果として**いつでも再計算可能な正**。  
- **`payroll_budget`**: 経営・オーナー期待・来季目安としての**ガイドライン**（現実装では主に `_process_team_finances` で年1回更新）。  
- **FA オファー計算**: キャップ（ハード／ソフト）と**クラブ予算ライン**の両方で圧縮するのは妥当だが、**ガイドラインが実ペイロールより小さいまま固定**されていると、**「キャップ上はまだ枠があるのにオファーだけ 0」**という**表示・挙動の断裂**が起きうる（`get_team_fa_signing_limit` 系とは別入口のため）。

---

## 3. ズレが発生しうる地点

以下のイベントは**実ペイロールを変える**が、**現状のままでは `payroll_budget` を必ずしも同じタイミングで更新しない**。

- **ロスター変更**: トレード、ドラフト指名後の契約、再契約、FA 署名、解雇・放出など。  
- **オフ内の契約年数進行**: `_decrease_contracts` 等で契約状況が変わると年俸総額が変わりうる。  
- **再署名・CPU 再契約**: オフ前半で年俸が動いても、`payroll_budget` は**前回 `_process_team_finances` 時点の値のまま**残りうる。

特に **「前オフの締めで設定された `payroll_budget`」が「今オフの途中までに膨らんだ実ペイロール」より小さい**とき、

`room_to_budget = max(0, payroll_budget - payroll_before) = 0`

となり、**ソフトキャップ内にいても `_calculate_offer` が 0** になりうる。既存テスト `test_offseason_manual_fa_fallback_when_payroll_budget_zeroes_calculate_offer` は、**意図的に `payroll_budget` を実ペイロールに張り付けてこの経路を再現**している。

---

## 4. オフFA直前で何が起きているか

### 4.1 呼び出し順（`Offseason.run`）

`basketball_sim/models/offseason.py` のオフ処理は概ね次の順である（抜粋）。

1. ドラフト、トレード、契約満了・再契約など**多数のフェーズ**でロスターと年俸が変化する。  
2. **`_maybe_run_pre_conduct_free_agency_ui()`** … 注入されていれば **`offseason_full_fa_tk.run_user_offseason_fa_one_pick`** が動き、一覧表示・確認・署名のたびに **`offseason_manual_fa_offer_and_years` → `_calculate_offer`** が呼ばれる。  
3. **`conduct_free_agency(self.teams, self.free_agents)`** … CPU 本格FA。全チームで同じ `_calculate_offer` が使われる。  
4. その後 **`_process_team_finances()`** … ここで **`payroll_budget` が来季目安として再計算**され、収支が締まる。

したがって **手動オフFAも CPU 本格FAも、いずれも `_process_team_finances` より前**である。コメントどおり **「オフFA直前は `_process_team_finances` より前で `payroll_budget` が実ペイロールに追いついていないことがある」** 状態は、**現行のパイプライン順序上、構造的に起きうる**。

### 4.2 いつ `payroll_budget` が「古い」か

- **直前の `_process_team_finances` 実行時**に設定された値が、その後のオフ処理で**実ペイロールが上振れした場合**に古くなる。  
- **初年度・テスト・異常系**では、既定の `payroll_budget` のまま実ペイロールだけが大きい、というパターンもありうる。

### 4.3 `_calculate_offer == 0` になりやすい条件（整理）

- **`payroll_before >= soft_cap`**: 早期 `return 0`（予算以前の理由）。  
- **`room_to_budget == 0`**（**本書の焦点**）: `payroll_budget <= payroll_before` のとき。  
- その他、ハードキャップ超過後の低額制限・贅沢税圧縮など、**複合的に 0 へ落ちる**場合もある。

### 4.4 既存フォールバックが救っているもの

`offseason_manual_fa_offer_and_years`（`free_agent_market.py`）は、**`core_offer <= 0` かつ `get_team_fa_signing_limit > 0`** のとき **`min(estimate, room)` で芯を立て**、続けて **1.20×estimate 下限**と **room クリップ**を適用する。これは **「キャップ上は枠があるのに本格式だけ 0」** を**オフ手動専用に救済**している。ただし **CPU 本格FA**はこのフォールバックを経由しないため、**同じ `payroll_budget` ズレは CPU 側のオファー分布にも影響しうる**。

---

## 5. 同期・前処理改善の候補

| 案 | 内容 | 利点 | 注意 |
|----|------|------|------|
| **A. `conduct_free_agency` 直前に全チームで `payroll_budget` を明示同期** | 例: `payroll_budget = max(payroll_budget, get_team_payroll(team))` や、`_process_team_finances` と同じ式の再利用 | **手動FA・CPU FA の両方**で一貫。呼び出し箇所が明確 | 式の重複を避けるなら**小ヘルパ化**。手動署名の**前後**で2回必要になる（後述） |
| **B. `_maybe_run_pre_conduct_free_agency_ui` 内でユーザーチームのみ同期** | コールバック直前に `user_team` だけ補正 | 変更範囲が狭い | **手動で1人獲得した後**、再度実ペイロールが伸びるため **`conduct_free_agency` 直前にもう一度必要**になりやすい。**CPU FA との一貫性単体では不足** |
| **C. `_calculate_offer` 内で都度 `effective_budget = max(payroll_budget, payroll_before)`** | ロジックを FA 核に集約 | 全呼び出し元で自動 | **本体変更**になり、意図・テスト・「ガイドライン」の意味の再定義が必要。**第1弾の「前処理のみ」方針とズレる** |
| **D. `offseason_manual_fa_offer_and_years` 先頭でだけ同期** | オフ手動だけ直す | 局所 | **CPU 本格FAは未解決**。責務が分散 |

**安全性の整理**

- **手動1人 → 即 `conduct_free_agency`** という順序では、**同期を1回だけ**にすると **「手動署名後にまたズレる」** ため、**理想的には「`_maybe_run` の直前」と「`conduct_free_agency` の直前」の2回**、**同一ヘルパ**で実行するのが一貫する。  
- **最小変更だけ**取るなら、まず **`conduct_free_agency` 直前の1回**でも **未署名の CPU のみ**は改善するが、**手動FA一覧表示はまだ古い `payroll_budget` のまま**になりうる。よって **実用上は 2 回呼び出しが望ましい**。

---

## 6. 最も安全な改善案（次の実装で採るべき1案）

**採用案**: **`basketball_sim/models/offseason.py` の `Offseason.run` において、`conduct_free_agency` を呼ぶブロックの直前に、全チーム向けの薄い前処理関数を用意し、それを**

1. **`_maybe_run_pre_conduct_free_agency_ui()` の直前**（手動FAの候補表示で `_calculate_offer` が意味を持つため）  
2. **`conduct_free_agency(...)` の直前**（手動で1人獲得した直後のロスターに合わせるため）

**の2回、同一ヘルパで呼ぶ。**

**ヘルパの中身（第1弾の典型）**は、例として **`team.payroll_budget = max(int(getattr(team, "payroll_budget", 0)), get_team_payroll(team))`** のように、**実ペイロールを下回らないようガイドラインを引き上げる**形が安全で、**`_calculate_offer` の `room_to_budget` が 0 固定になる典型パターン（実ペイロール = 予算ラインで張り付いているだけ）を解消**しやすい。

**ユーザー案（手動FA直前のみ）との関係**: 直感どおり **「手動FAのすぐそば」**は重要だが、**コード構造上は `Offseason.run` に置くことで `offseason_full_fa_tk` を膨らませず**、かつ **CPU FA 直前の第2回**で **手動署名後のズレ**も吸収できる。これを **全体として最も安全な一本化**とする。

**オーナーミッション等への影響**: `payroll_budget` はオーナー期待テンプレート（例: 給与規律）にも参照される。**「実態以下にしか下げない」同期**は、**来季目安を事後的に現実に合わせる**意味になり、**過大な引き下げより解釈が素直**である。逆に **無条件で大きく引き上げる**設計にするとミッションとの整合を要検証するため、**第1弾は `max(既存, 実ペイロール)` 型**に留めるのがよい。

---

## 7. 安全な段階実装案

### 第1弾

- **`Offseason.run`**: 上記 **2 箇所**から呼ぶ **`_sync_payroll_budget_with_roster_payroll(self.teams)`**（名前は実装時に決定）を追加。  
- 中身は **`payroll_budget = max(現在値, get_team_payroll(team))`** に限定し、**`_calculate_offer` / `conduct_free_agency` / `offseason_manual_fa_offer_and_years` の式は変更しない**。

### 第2弾

- **`_process_team_finances` の `payroll_budget` 算定式**との**重複解消**（単一関数に寄せる、または「オフFA直前は暫定同期、締めで本計算」とコメントで二段構えを明示）。  
- **`_calculate_offer` が 0 になる他理由**（ソフトキャップ早期 return 等）の**観測・ログ**と、**フォールバック条件の見直し**は別タスク。

### 将来タスク

- **`payroll_budget` の意味**を「年1回の目安」から「オフ中はロスター追随」へ寄せるかの**プロダクト決定**。  
- **CPU / インシーズン / オフ**で**財務フィールドの更新タイミングを一貫化**する広いリファクタ。

---

## 8. 今回の第1弾実装で「やること / やらないこと」

### やること（第1弾）

- **`Offseason.run` に限り**、**`_maybe_run_pre_conduct_free_agency_ui` 直前**と **`conduct_free_agency` 直前**の **2 回**、**全チーム**に対する **`payroll_budget` と `get_team_payroll` の整合（典型: `max` 同期）** を入れる。  
- **ヘルパは `offseason.py` 内または既存の contract / team 補助に隣接**し、**依存は `get_team_payroll` 程度に抑える**。

### やらないこと（第1弾）

- **`_calculate_offer` / `_determine_contract_years` / `conduct_free_agency` 本体の改造**  
- **`offseason_manual_fa_offer_and_years` の floor・フォールバック条件の変更**  
- **`MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER` の再変更**  
- **`estimate_fa_market_value` / `sign_free_agent` / generator / GUI 本実装のついで改修**  
- **`_process_team_finances` の式そのものの変更**（第1弾では触らない。同期はあくまで**暫定の下限合わせ**）

---

## 9. テストと確認観点

- **`_calculate_offer == 0` のうち、`payroll_budget <= payroll_before` が主因だったケースが減るか**（`test_offseason_manual_fa_offer_alignment` のフォールバックテストは、**同期後も意図的に低い `payroll_budget` を残す別ケース**が必要になる可能性あり。テストの意図を「ズレ再現」から「同期後の主経路」へ分離する検討）。  
- **`basketball_sim/tests/test_offseason_manual_fa_offer_alignment.py`**: 表示＝契約・フォールバックの回帰。  
- **`test_precheck_user_fa_sign.py` / `test_offseason_pre_fa_ui_prompt.py`**: UI 経路の破綻なし。  
- **`test_economy_r1_fa_payroll_trace.py`**: **`conduct_free_agency` が `_process_team_finances` より前**であることの前提は**維持**されること（呼び出し順インvariant）。  
- **`python -m basketball_sim --smoke`** および関連 pytest の一括実行。  
- **手動で1人獲得した直後の CPU FA**で、ユーザーチームのオファーが**極端に全件0**になりにくいか（目視・ログ）。

---

## 10. 次に実装で触るべき対象（1つだけ）

**`basketball_sim/models/offseason.py` の `Offseason.run`（および同ファイル内に追加する小さな同期ヘルパ）**

- **なぜ最初の1手として最も安全か**  
  - **ズレの原因が「オフFAが `_process_team_finances` より前にある」パイプライン順**に起因するため、**同じ `Offseason.run` 内で FA の手前にフックを置く**のが**説明責任と依存関係の両面で最も素直**である。  
  - **`offseason_full_fa_tk.py` に同期を埋め込む**と **GUI 専用**になり **CLI・テスト経路で漏れる**リスクがある。  
  - **`free_agent_market.py` だけ**では **CPU `conduct_free_agency`** をカバーしにくい。  
  - **`Team` にだけメソッドを足す**と **「いつ呼ぶか」**が散らばりやすい。  

- **そこだけ触ると何が改善し、何がまだ残るか**  
  - **改善**: **`payroll_budget < 実ペイロール` による `room_to_budget = 0` 型の `_calculate_offer` 0 を、オフ手動・CPU 本格の両方で減らせる**（第1弾の同期モデル次第）。  
  - **残る**: **ソフトキャップ超え・贅沢税・その他クリップによる 0**、**フォールバック・floor の設計論**、**`_process_team_finances` との長期的な二重定義の整理**。

---

## 改訂履歴

- 2026-04-06: 初版（`payroll_budget` / 実ペイロール / オフFA直前の整理と同期案）。
