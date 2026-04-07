# オフFA直前: `payroll_budget` 同期＋`MIN_SALARY_DEFAULT` buffer の 0オファー観測メモ

**作成日**: 2026-04-06  
**文書の性質**: **短い観測メモ（コード変更なし）**。実装正本: `basketball_sim/models/offseason.py` の `_sync_payroll_budget_with_roster_payroll`（`max(existing, roster_payroll + MIN_SALARY_DEFAULT)`）、`Offseason.run` 内の同関数2回呼び出し。  
**前提設計**: `docs/OFFSEASON_FA_PAYROLL_BUDGET_SYNC_PLAN_2026-04.md`、`docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAN_2026-04.md`、`docs/OFFSEASON_MANUAL_FA_PLAYCHECK_2026-04.md`

---

## 1. 文書の目的

第2弾で **`roster_payroll + MIN_SALARY_DEFAULT`（300,000 円）** を `payroll_budget` の下限に足し込んだ。**`room_to_budget = payroll_budget - payroll_before` が 0 固定だったタイプ**の **`_calculate_offer == 0` がどれだけ減るか**、**まだ何が残るか**を短く整理し、**buffer をすぐ大きくするか／一旦止めるか／別原因を見るか**の判断材料を残す。

---

## 2. 観測方法

- **方法**: **GUI 実プレイではなく**、リポジトリ上の現行コードに対する **再現用 `python -c`** および **`free_agency._calculate_offer` の読み取り**（`basketball_sim/systems/free_agency.py`）。既存テスト `test_offseason_payroll_budget_sync.py` の考え方と整合する **合成 `Team` / `Player`**。  
- **代表ケース**  
  - **A**: D1、`money=5億`、ロスター1人 **年俸 7,600,000**、**`payroll_budget` も 7,600,000**（**budget == roster**）。FA は **OVR 72・`salary` 4,000,000**（本格FA同型の芯）。  
  - **B**: **A と同一チーム**（同期後 `room = 300,000`）に対し、FA を **`salary` 88,000,000**（高額候補）に差し替え。  
  - **C**: **`payroll_before >= soft_cap`** の早期 return が効くかの確認（D1 `soft_cap` は **1,200,000,000** 円オーダー。`payroll_before == soft_cap` の合成チームで `_calculate_offer` を1回）。  

**再現の目安**: 同期は **`_sync_payroll_budget_with_roster_payroll([team])`** を1回呼ぶ（`Offseason.run` 全体は不要）。`MIN_SALARY_DEFAULT` は **300,000**（`contract_logic`）。

**スモーク**: `python -m basketball_sim --smoke` でリポジトリ健全性のみ確認可能（本観測の数値根拠は `python -c` 側）。

---

## 3. 0オファー改善の観測結果

| ラベル | 状況（要約） | 同期前 | 同期後（第2弾） |
|--------|----------------|--------|------------------|
| **A** | budget == roster・中額ベース FA | `room_to_budget = 0`、**`_calculate_offer = 0`** | `room_to_budget = 300,000`、**`_calculate_offer = 300,000`** |

- **減ったタイプ**: **`payroll_budget <= payroll_before` かつ `payroll_before < soft_cap`** で、**それ以外の段階（ベース＋ボーナス等）が正のオファー芯を立てている**とき、**最終段のクラブ予算クリップだけが `room_to_budget == 0` で 0 に落としていた**パターン。  
- **改善額**: **最大でも `MIN_SALARY_DEFAULT` 分（300,000 円）**が予算ライン上の追加枠として入るため、**`_calculate_offer` も同上限でクリップされうる**（ケース A）。  
- **オフ手動FA / CPU 本格FA**: いずれも **`conduct_free_agency` より前の同期**で同じ `Team.payroll_budget` を共有するため、**同型の `_calculate_offer` に対する効き方は理論上一致**（手動専用の `offseason_manual_fa_offer_and_years` の estimate フォールバックは別経路）。  
- **「ゼロ余地解消」という目的**: **数式上の `room_to_budget = 0` は解消**（少なくとも **正の余地**が立つ）。ただし **高額候補にとって「意味のあるオファー額」にはならない**（§4）。

---

## 4. まだ残る 0オファーの可能性

- **buffer 300,000 が小さすぎるタイプ（B）**: 同期後も **`room_to_budget = 300,000` のまま**。FA の **`base` が数千万〜億オーダー**のとき、理論上の芯は巨大だが **`offer = min(芯, 300,000) = 300,000`**。**0 ではないが、プレイ感としては「本格FAとして不自然に低い」**まま。オフ手動では **`estimate`＋floor＋`signing_room`** が別途効くため **表示は救われうる**が、**CPU 本格FA のオファー分布は 300,000 張り付きになりうる**。  
- **soft cap 早期 return（C）**: **`payroll_before >= soft_cap` なら `_calculate_offer` は即 `0`**（`free_agency.py`）。**`payroll_budget`／buffer とは無関係**。  
- **hard cap 超過後の低額制限・soft cap 内への圧縮・贅沢税圧縮**: いずれも **`payroll_budget` 以前または以降**で **0 または極小**に落ちうる。**buffer だけでは解けない**。  
- **次に見るべき原因（観測の切り分け）**: **`_calculate_offer == 0` を「① soft cap 早期」「② 予算 room」「③ cap/tax クリップ」「④ その他」に分類**するログまたはテスト行列があれば、**buffer 増額が効く層**と **本体・別設計が必要な層**を混同せずに進められる。

---

## 5. 今の buffer に対する判断

- **寄せた結論**: **当面 `MIN_SALARY_DEFAULT` のまま維持でよい（すぐに buffer を百万〜千万単位で上げる判断は保留）**。根拠は、(1) **設計書どおり「最小の正の余地」を入れる第2弾は達成**、(2) **0 オファーの主因の一部（予算 room=0）は確実に潰せる**、(3) **buffer を大きくするとオファー芯まで乗せてしまい、経営ガイドライン・オーナーミッションとの整合を要検証**になる。  
- **追加観測が必要なら**: **実セーブ／長期シーズン**で「CPU 本格FA が 300,000 オファーを多発していないか」「オフ手動の表示と CPU の挙動のギャップが目立つか」。

---

## 6. 今回はまだやらないこと

- **`_calculate_offer` 本体の改造**  
- **`MIN_SALARY_DEFAULT` を超える buffer の増額実装**（およびそれに伴う定数・式の拡張）  
- **`offseason_manual_fa_offer_and_years` の floor 条件・倍率変更**  
- **オフ手動FAの全面再設計**  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`_calculate_offer == 0`（および極小オファー）の要因分類用の観測・ログまたはテストの整備**（本体ロジックの「挙動変更」ではなく、**分岐ごとのラベル付きデバグ出力／回帰用の行列テスト**に限定するのが安全）。

- **なぜその1手が今もっとも妥当か**  
  - 第2弾 buffer は **「予算 room=0」型**には効くが、**soft cap・cap・tax 型**とは **別物**。いま buffer を上げると **効かない 0 が混ざったまま**になり、**調整根拠が曖昧**になる。  
  - **分類が取れた後**なら、**buffer 増**と **`_calculate_offer` 改修**のどちらが効くかを**データで選べる**。  

- **何はまだ残るか**  
  - **buffer 増額の是非**、**オフ手動と CPU の表示整合**、**`_process_team_finances` 後の guideline との長期一貫性**。

---

## 参考: 観測セッションで得た数値（2026-04-06・`python -c`）

- **D1 `soft_cap`**: 1,200,000,000  
- **A（tight eq）**: 同期後 `payroll_budget = 7,900,000`、`room_to_budget = 300,000`、`_calculate_offer = 300,000`  
- **B（高額 FA・base 88M）**: 同期後も `room_to_budget = 300,000`、**`_calculate_offer = 300,000`**（0 ではないが芯に対して極小）  
- **C2（`payroll_before == soft_cap`）**: **`_calculate_offer = 0`**（buffer 無関係）

---

## 改訂履歴

- 2026-04-06: 初版（MIN_SALARY_DEFAULT buffer の 0オファー観測メモ）。
