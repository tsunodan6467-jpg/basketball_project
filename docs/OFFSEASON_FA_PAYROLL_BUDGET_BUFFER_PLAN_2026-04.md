# オフFA直前: `payroll_budget` 同期に「最低余地（buffer）」を足す最小差分案

**作成日**: 2026-04-06  
**文書の性質**: **短い設計メモ（実装なし）**。前提の第1弾同期は `docs/OFFSEASON_FA_PAYROLL_BUDGET_SYNC_PLAN_2026-04.md` および `basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll`。  
**背景プレイ観測**: `docs/OFFSEASON_MANUAL_FA_PLAYCHECK_2026-04.md`

---

## 1. 文書の目的

第1弾で **`payroll_budget = max(existing, roster_payroll)`** をオフFA直前に2回入れたが、実測どおり **`payroll_budget == payroll_before`（= 実ペイロール）のとき `room_to_budget = 0`** のまま **`_calculate_offer` が 0** になりうる。本メモは、**`_calculate_offer` 本体をまだ触らず**、**同期ヘルパに足す最小の「実ペイロール＋余地」**をどう定義するかを整理し、**次の1コミットのスコープ**を決める。

---

## 2. 現在の同期案で足りない理由

`free_agency._calculate_offer` では **`payroll_before = get_team_payroll(team)`** とし、クラブ予算クリップで

`room_to_budget = max(0, payroll_budget - payroll_before)`、  
`offer = min(offer, room_to_budget if room_to_budget > 0 else 0)`

となる（`basketball_sim/systems/free_agency.py`）。

第1弾同期後 **`payroll_budget = roster_payroll = payroll_before`** なら

`room_to_budget = max(0, roster_payroll - roster_payroll) = 0`

であり、**予算ライン上の「追加枠」がゼロ**のまま。したがって **「実ペイロール未満をなくす」同期だけでは、`room_to_budget` 起因の 0 オファーを解消しきれない**。

今後の打ち手は、**ズレ補正**に加えて、**オフFA直前のガイドライン上、最低限オファーが立ちうる正の余地を `payroll_budget` 側に持たせる**方向が必要になる（キャップ・ソフトキャップ・贅沢税など**別理由の 0**は別課題）。

---

## 3. 最低余地の候補比較

| 候補 | 概要 | 実装の簡単さ | 既存構造との整合 | 暴れにくさ | テストしやすさ |
|------|------|--------------|------------------|------------|----------------|
| **固定小額 `+ B`（モジュール定数）** | `roster_payroll + B` を下限に `max(existing, …)` | ◎ 1定数＋1行 | ◎ offseason 局所 | △ B の大きさ次第で過大になりうる | ◎ 単体で数値固定 |
| **最低年俸1人分 `+ MIN_SALARY_DEFAULT`** | `contract_logic.MIN_SALARY_DEFAULT`（300,000 円）を再利用 | ◎ 既存定数 | ◎ 契約体系と語彙が一致 | ◎ 暴れ幅は小さい | ◎ | 
| **estimate 一定割合** | FA候補の `estimate_fa_market_value` に依存 | △ 同期が選手非依存であるべき場面で循環・責務が濁る | △ offseason が estimate に寄りすぎ | △ 高額帯で振れうる | △ |
| **`get_team_fa_signing_limit` の一部** | キャップ余地と予算を混同しやすい | △ 依存増・説明が難しい | △ 二系統クリップの関係が複雑 | ○ 上限はキャップ側 | △ モックが重い |
| **soft_cap 比の極小割合** | リーグでスケールする B | ○ | ○ `salary_cap_budget` 既存 | △ 式選びが要議論 | ○ |

**整理**

- **estimate 連動**は「チーム全体の同期」から外し、**オフFA直前の全チーム2回同期**の責務としては**避けた方が安全**。  
- **`get_team_fa_signing_limit`** は **キャップ系の単一入口**であり、**クラブ `payroll_budget` の意味**と**混ぜると二重計上の誤解**を生みやすい。同期はあくまで **「guideline を roster ＋小さな buffer に引き上げる」**に留めるのが筋。  
- **固定小額**と**最低年俸**はどちらも **実装が最小**。高額 FA で **`base + bonus` が buffer をはるかに超える**場合、**buffer を上げる段階設計**か、**将来 `_calculate_offer` 側の見直し**が別途必要になる（本メモでは前者を第2弾の調整ノブとする）。

---

## 4. 最も安全な最小差分案（次の実装で1つ採用）

**推奨案**: **`payroll_budget = max(existing, roster_payroll + B)`** とし、**`B` は `basketball_sim/models/offseason.py` に名前付き定数**（例: `_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER`）として置く。**初期値は `MIN_SALARY_DEFAULT`（`contract_logic`、300,000 円）を第一候補**とし、**プレイ・回帰で「まだ 0 が多い」なら B を段階的に引き上げる**（例: 数百万〜数千万の固定）運用を想定する。

**なぜ安全か**

- **単調増分**（`roster + B`）のみで、**既存の `max(existing, …)` により「意図的に高い guideline」は壊さない**。  
- **キャップ・ソフトキャップ・贅沢税**は従来どおり `_calculate_offer` 内で効くため、**無限にオファーが膨らむわけではない**。  
- **B を小さく始めれば**、経営・オーナーミッションへのインパクトを**段階的に計測**できる。

**なぜ `_calculate_offer` 本体より先にやるべきか**

- 問題の起点は **「オフFAが `_process_team_finances` より前」**という**パイプライン順**と **`payroll_budget` スカラーの陳腐化**であり、**FA交渉核の式を広く変えるより、入力側の guideline を1箇所で揃える**方が**回帰面が読みやすい**。  
- 本体変更は **全インシーズン・CPU FA・将来の交渉拡張**に波及し、**第2弾の「buffer 調整」より重い**。

**なぜ今の段階に向いているか**

- 第1弾で **呼び出し箇所（2回）は確定**済み。**中身を `+ B` に差し替えるだけ**で第2弾を完結できる。

**注意（読み手向け）**: **`B = MIN_SALARY_DEFAULT` だけでは、高年俸候補に対する `room_to_budget` が依然不足し `_calculate_offer` が 0 のまま**になりうる。それは **「buffer の段階引き上げ」または別タスク（本体・フォールバック）**の対象として切り分ける。

---

## 5. 第1弾（＝次コミット）実装のスコープ

### 触るもの

- **`basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll` のみ**（＋**同一ファイル内の小さな buffer 定数**、必要なら **`MIN_SALARY_DEFAULT` の import**）。  
- **`Offseason.run` の呼び出し回数・位置は変更しない**（第1弾同期どおり2回）。

### 触らないもの

- **`_calculate_offer` / `_determine_contract_years` / `conduct_free_agency` 本体**  
- **`offseason_manual_fa_offer_and_years` / floor 倍率 / estimate**  
- **`_process_team_finances` の予算算定式**  
- **GUI / generator / 経営収支のついで改修**

---

## 6. テストと確認観点

- **代表ケース**: 第1弾で **`payroll_budget < roster`** だった set up で、同期後 **`payroll_budget >= roster + B`** となり、**`room_to_budget >= B`** になりうること。可能なら **`_calculate_offer` が 0 → 正**の例を1つ以上（B の大きさに依存するため、**テストでは B かオファー芯を読みやすい値に固定**）。  
- **オフ手動FA**: 表示＝契約の回帰 — `test_offseason_manual_fa_offer_alignment.py`、`test_precheck_user_fa_sign.py`。  
- **呼び出し順**: `test_economy_r1_fa_payroll_trace.py`（`conduct_free_agency` と `_process_team_finances` の前後関係）。  
- **同期ヘルパ単体**: `test_offseason_payroll_budget_sync.py` の更新（`roster + B` 期待値、オーナー guideline が既に高い場合は `max` で維持）。  
- **`python -m basketball_sim --smoke`**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`basketball_sim/models/offseason.py` 内の `_sync_payroll_budget_with_roster_payroll` の式と、同ファイルに追加する buffer 定数（必要な import のみ）**

- **なぜ最初の1手として最も安全か**  
  - 第1弾で **FA 直前のフック位置は固定済み**。**責務を広げず「下限式の1行」に留められる**。  
  - **`_calculate_offer` や `free_agency` を開かない**ため、**CPU／インシーズンとの差分が読みやすい**。  

- **そこだけ触ると何が改善し、何がまだ残るか**  
  - **改善**: **`payroll_budget == payroll_before` 固定による `room_to_budget = 0`** を、**意図した B 分だけ緩和**しうる。  
  - **残る**: **B では足りない高額オファー**、**ソフトキャップ早期 return**、**贅沢税・ハードキャップ**など**別経路の 0**、**オフ手動専用フォールバックの要否**。

---

## 改訂履歴

- 2026-04-06: 初版（`max(existing, roster)` 限界と `+ buffer` 最小案）。
