# `_calculate_offer` 0 / 極小オファー: 原因内訳の短い観測メモ

**作成日**: 2026-04-06  
**文書の性質**: **観測メモ（コード変更なし）**。ツール: `basketball_sim/systems/free_agency.py` の **`_calculate_offer_diagnostic`**。分類枠: `docs/FA_CALCULATE_OFFER_CAUSE_CLASSIFICATION_PLAN_2026-04.md`。  
**関連**: `docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAYCHECK_2026-04.md`（buffer は room 型に効くが soft cap 早期には効かない）

---

## 1. 文書の目的

診断関数が入った段階で、**合成代表ケース**に対し **0 / 極小オファーがどのクリップに偏るか**を1回集計し、**次に buffer を触るか・本体を触るか・別観測に進むか**の判断材料にする。

---

## 2. 観測方法

- **方法**: リポジトリルートで **`python -c`** により、合成 `Team` / `Player` を組み立て **`_calculate_offer_diagnostic(team, fa)`** を実行。出力は **`final_offer`** と診断 dict の **`soft_cap_early` / `room_to_budget` / `hard_cap_*` / `soft_cap_pushback_applied` / `luxury_tax_clip_applied` / `offer_after_base_bonus` / `offer_after_budget_clip`** を目視集計。  
- **再現**: `from basketball_sim.systems import free_agency as fa` → `fa._calculate_offer_diagnostic(...)`。D1 の **`get_soft_cap` / `get_hard_cap` はいずれも 1,200,000,000**（本観測時点の `salary_cap_budget`）。  
- **見た代表ケース（ラベルは観測用）**  
  - **S1**: ロスター年俸合計 **`== soft_cap`**（D1）・FA 中程度  
  - **S6a**: `payroll_budget == payroll_before`（例: 7.6M）・FA 中程度  
  - **S6b**: `payroll_budget = payroll_before + 300_000`（buffer 相当）・FA 中程度 / **高額 `salary`（例: 88M）**  
  - **Healthy**: **空ロスター**・`payroll_budget` 十分大・高額 FA  
  - **Bridge**: `payroll_before` を soft 直前付近に置き、**ハード跨ぎクリップ**が効くか  
  - **Hard-over 試行**: `payroll_before > hard_cap` を意図したが、**hard == soft** のため **早期 return と同義**になることを確認  

**限界**: **実セーブ全ロスター・CPU FA 全分岐の頻度分布ではない**。あくまで **診断キーが意味を持つかのスモーク内訳**。

---

## 3. 0オファーの原因内訳（本観測サンプル）

| ケース | `final_offer` | 主に効いた要因（診断上） |
|--------|---------------|---------------------------|
| **S1**（`payroll >= soft_cap`） | **0** | **`soft_cap_early == True`**。以降のキーは未設定（早期 return）。 |
| **S6a**（`room_to_budget == 0`） | **0** | **`soft_cap_early` False**。`offer_after_base_bonus` は正だが **`offer_after_budget_clip == 0`**。**budget room 0 が主因**。 |
| **Hard-over 試行**（`payroll > hard_cap` を狙った合成） | **0** | 現設定では **hard_cap == soft_cap** のため、**ペイロールが hard を超えると同時に `soft_cap_early` が真**になり、**S4「ハード超え」専用分岐より前に 0**。 |

**分類して分かったこと（サンプル範囲）**

- **即 0 は大きく二系統**: **(A) soft cap 早期**、**(B) budget room 0**。  
- **(A) と (B) は診断上すぐ区別できる**（`soft_cap_early` の有無）。  
- **本コードベース（D1〜3 で hard==soft）では、「hard 超えのみで soft 未満」は成立しにくく**、**hard 超え試行は観測上 S1 に吸い込まれた**。

---

## 4. 極小オファーの原因内訳（本観測サンプル）

**極小**を本メモでは **`0 < final_offer < 5,000,000`** とおいた（任意の目安）。

| ケース | `final_offer` | 所見 |
|--------|---------------|------|
| **S6b・中程度 FA** | **300,000** | `room_to_budget == 300_000`。芯は数百万だが **budget で 300,000 に張り付き**。**buffer（+MIN_SALARY）と整合**。 |
| **S6b・高額 FA（base 88M）** | **300,000** | `offer_after_base_bonus` は **約 1.08 億**だが、**同じく `room_to_budget == 300_000` でクリップ**。**高額候補でも極小のまま**。 |
| **Bridge 付近** | **50,000,000** 等 | **`hard_cap_bridge_applied == True`** で芯が削られたうえ、**budget 側の `room_to_budget` も効く**。極小ではないが **多段クリップの例**。 |
| **Luxury tax** | （本サンプルでは未発火） | `tax_delta` が `tax_warn` 未満のケースのみ確認。**贅沢税クリップは別途、ペイロール帯を上げた再観測が必要**。 |

**buffer 300,000 の見え方**

- **room=0 型の 0** は **buffer 同期後の `room = 300_000` に変えうる**（既知）。  
- その結果、**高額 FA でも `final_offer` が 300,000 で頭打ち**になりうる——**「0 は減るが、プレイ感は依然として破綻しうる」**層が残る。

---

## 5. 今回の観測から分かること

- **buffer / payroll_budget 同期が効く層**: **`soft_cap_early` が偽**かつ **`room_to_budget` がボトルネック**のとき（S6 系）。  
- **効かない層**: **`payroll_before >= soft_cap` の S1**。ここは **budget をいじっても `_calculate_offer` に到達しない**。  
- **本命の次論点（サンプル内訳）**: **S1（soft cap 早期）と S6（budget room）のどちらが実プレイで多いか**は、本メモの範囲では未計測だが、**設計上は S1 が「buffer とは独立の最上流」**である。  
- **極小オファー**: **S6＋小さい `room_to_budget`** が典型。**buffer を大きくしない限り、高額 FA の芯は復活しない**。

---

## 6. 今回はまだやらないこと

- **`_calculate_offer` 本体の挙動変更**  
- **`payroll_budget` buffer のさらなる増額**  
- **`offseason_manual_fa_offer_and_years` の floor 条件・倍率変更**  
- **オフ手動FA全面再設計**  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`payroll_before >= soft_cap` 時の即 `0`（soft cap 早期 return）について、プロダクト上の意図を一文で確定し、その前提で「緩和する／しない／別表現にする」の設計メモを1本にまとめる（本体変更はその合意後の別コミット）。**

- **なぜ今もっとも妥当か**  
  - 本観測では **0 オファーの即死経路として S1 が最上流**であり、**buffer・同期では到達不能**。ここを曖昧にしたまま buffer や下流クリップだけ弄ると、**対症療法の順序が逆**になりやすい。  

- **何がまだ残るか**  
  - **S6 の `room` サイズ**（300,000 張り付きの是非）、**luxury tax / bridge 等の多段クリップ**の実データでの頻度、**hard==soft 下での分岐到達性**の整理。

---

## 参考: 観測セッション要約（2026-04-06・`python -c`）

- **S1**: `final_offer=0`, `soft_cap_early=True`  
- **S6a**: `final_offer=0`, `room_to_budget=0`, `offer_after_budget_clip=0`  
- **S6b（中/高 FA）**: `final_offer=300_000`, `room_to_budget=300_000`  
- **Healthy（空ロスター）**: `final_offer=108_600_000` 前後（例では budget に十分余地）  
- **Bridge 例**: `hard_cap_bridge_applied=True`, `final_offer=50_000_000`（多段要約）  
- **Hard-over 試行**: 診断上 **S1 に帰着**（hard==soft のため）

---

## 改訂履歴

- 2026-04-06: 初版（診断ベースの短い内訳観測）。
