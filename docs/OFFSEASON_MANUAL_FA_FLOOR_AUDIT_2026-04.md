# オフ手動FA `1.35 × estimate` 下限の強度監査メモ

**作成日**: 2026-04-07  
**文書の性質**: **監査メモ（読み取り・数値観測）**。コード変更・倍率確定・実装コミットは本書の範囲外。  
**前提設計**: `docs/OFFSEASON_MANUAL_FA_ALIGNMENT_PLAN_2026-04.md`、`docs/FA_POOL_SALARY_ALIGNMENT_PLAN_2026-04.md`、`docs/FA_SALARY_SCALE_CONNECTION_PLAN_2026-04.md`

---

## 1. 文書の目的

`estimate_fa_market_value` と FA プール `salary` が**高額オーダー**に揃った後も、オフ手動FA では **`MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER`（既定 1.35）× estimate** が**下限**として常に作用する。

旧スケールでは「極端に安いオファー防止」の **safety net** として妥当だった可能性が高い一方、**今は 1.35 倍の絶対額が大きく**、**意図せずオファーを押し上げ・`signing_room` 張り付きを誘発**していないかを、**式と代表ケース**で整理する。

---

## 2. 現在の 1.35× 下限の入り方

実装は `basketball_sim/systems/free_agent_market.py` の `offseason_manual_fa_offer_and_years` に集約されている（整理後の変数名で記す）。

- **`manual_floor_offer = int(estimate_for_floor * MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER)`**（既定 **1.35**）。
- **`final_salary = min(max(core_offer, manual_floor_offer), signing_room)`**。

重要な含意:

- 下限は **`core_offer <= estimate` のときだけ**ではなく、**`core_offer < manual_floor_offer` の全ケース**で **`core` を `floor` まで引き上げうる**。
- したがって **`estimate < core < 1.35×estimate`** の帯でも、**floor が効いて `core` を上回る**。
- 最後に **`signing_room`** でクリップされるため、**`floor > signing_room`** のときは **`final_salary == signing_room`**（張り付き）。

---

## 3. どのケースで効いているか

| 状況 | ざっくりした挙動 |
|------|------------------|
| **`core_offer >= manual_floor_offer`** | **`max(core, floor) = core`** → 下限は**実質ノーオペ**に近い。 |
| **`estimate <= core_offer < manual_floor_offer`** | **floor が `core` を上回る**ため、**下限が能動的に効く**（旧「safety net」より**強い引き上げ**）。 |
| **`core_offer < estimate`** | 通常 **`max(core, floor) = floor`**（`core` が極小のとき）。 |
| **`core_offer <= 0` かつ `signing_room > 0`** | 先に **estimate フォールバック**で `core` を **`min(estimate, signing_room)`** まで持ち上げたうえで、**さらに floor** が **`max` に効く**。フォールバック後の `core` が **`estimate` 全体**なら、**次段の floor はほぼ必ず `core` を上げる**（`1.35×estimate > estimate` のため）。 |
| **`signing_room` が小さい** | **`min(..., signing_room)`** により **最終額は room 上限張り付き**。floor が理論上は高くても**実効は room**。 |

---

## 4. どのケースで強すぎる可能性があるか

- **estimate の絶対額が大きい**（OVR 60〜70 台で**数千万〜1億円超**オーダー）ため、**同じ 1.35 倍でも円ベースの押し上げ量が旧時代比で桁違い**になる。
- その結果、**`manual_floor_offer` が `signing_room` に早期に到達**しやすく、**「市場ベースより高いオファーが cap 余地で打ち切られる」**パターンが増えうる。ゲームデザイン上それが望ましいかは別論だが、**旧来の「底上げ safety net」から「高額帯への強制寄せ」**に近づいている可能性がある。
- **フォールバック直後**: `core ≈ estimate` となってから **必ず 1.35 倍へ引き上げ**るため、**「フォールバックで救った直後にさらに 35% 上げる」**二段構えになり、**意図の説明が難しくなっている**余地がある。
- **本当に「問題」かどうか**は、`signing_room` の典型的な大きさ・`core` の分布に依存するため、**全シーズン横断の実測**があると確度が上がる（本メモでは**代表ケース＋合成例**で代替）。

---

## 5. 実測または想定ケースの整理

### 5.1 `estimate` と `floor = 1.35×estimate`（代表・2026-04 時点の実装）

条件: potential **C**、age **25**、`estimate_fa_market_value` 利用（`ensure_fa_market_fields` 済み）。

| OVR | estimate（円/年） | floor 1.35×（円/年） |
|-----|-------------------|----------------------|
| 55 | 67,100,000 | 90,585,000 |
| 60 | 73,200,000 | 98,820,000 |
| 65 | 79,300,000 | 107,055,000 |
| 72 | 87,840,000 | 118,584,000 |
| 78 | 95,160,000 | 128,466,000 |

### 5.2 実測 A: 空ロスター・`money=5億`・FA OVR 72（`salary` はプール同期イメージで約 8800 万円台）

- **`signing_room`**: **1,200,000,000**（D1 ハードキャップオーダーに整合）
- **`core_offer`**（`_calculate_offer`）: **108,600,000**
- **`estimate`**: **87,840,000**
- **`manual_floor_offer`**: **118,584,000**
- **`final_salary`**: **118,584,000**

解釈: **`core` は既に `estimate` を上回っている**が、**まだ `1.35×estimate` 未満**のため、**下限が能動的に約 1,000 万円規模で `core` を押し上げている**。いわゆる「safety net」ではなく**上乗せ**に近い挙動。

### 5.3 実測 B: `test_offseason_manual_fa_fallback_when_payroll_budget_zeroes_calculate_offer` 相当（`core=0`・フォールバック）

- **`signing_room`**: **1,192,400,000**
- **`core`**（フォールバック後）: **`min(estimate, room) = 87,840,000`**
- **`manual_floor_offer`**: **118,584,000**
- **`final_salary`**: **118,584,000**（**room 未張り付き**だが **floor による上乗せは明確**）

### 5.4 合成例（`final = min(max(core, floor), room)` のみ抜粋）

`estimate=80,000,000` → `floor=108,000,000` と仮定:

| ラベル | core | room | final | コメント |
|--------|------|------|-------|----------|
| core 十分高い | 120,000,000 | 120,000,000 | 120,000,000 | floor ノーオペ |
| core は中程度 | 50,000,000 | 120,000,000 | 108,000,000 | floor が支配 |
| core 0（合成） | 0 | 120,000,000 | 108,000,000 | 実コードではフォールバック後に再度 floor |
| room タイト | 50,000,000 | 90,000,000 | 90,000,000 | **room 張り付き** |
| room が floor 未満 | 30,000,000 | 100,000,000 | 100,000,000 | 理論 floor より **room が効く** |

---

## 6. 倍率見直し候補の比較

| 候補 | 想定される効果 | リスク・トレードオフ |
|------|----------------|----------------------|
| **1.35 維持** | 現状維持・回帰なし | 高額 estimate 下で**上乗せが強いまま** |
| **1.20 付近** | floor の絶対額を約 **11% 削減**（1.35→1.20 の比） | 「旧プレイ感」からの変化。テスト期待値の更新 |
| **1.10 付近** | さらに穏やか。**estimate 直上**に近づく | オフ手動の「最低品位」が弱まる懸念 |
| **1.00** | **floor = estimate**。`core` と estimate の **max** 相当まで単純化しうる | フォールバック＋下限の**二重押し上げ解消**に近いが、**意図したプレミアム消失** |
| **倍率維持＋条件付き** | 例: **`core >= estimate` のときは floor スキップ** | ロジック複雑化。要テストと説明の更新 |

※数値は**候補の目安**であり、正本の最終決定ではない。

---

## 7. 今の段階での推奨判断

- **即時に倍率を変える必然性までは監査だけでは断定しない**。ただし、**代表実測（§5.2）**により、**空き枠の大きいチームでも `core > estimate` なのに floor がさらに上乗せする**ことは**事実として確認できた**。したがって **「1.35 は safety net というより、高額帯での追加プレミアム」**として振る舞っている可能性が高い。
- **次の一手の優先度**: **倍率そのもの**より先に、**プロダクト上「オフ手動は estimate より必ず何%高く契約させたいのか」**を一文で決めると、`1.35` の妥当性が判断しやすい。
- **フォールバック条件の整理**（`core <= 0` のみ等）は**別軸**だが、**floor が強い**現状では **フォールバック後の二段上げ**が目立つため、**倍率または条件のどちらか一方を先に触る**のが現実的。
- **結論（現時点）**: **倍率見直しの実装タスクは「価値あり」**。根拠は **(1) 絶対額インパクトの増大**、(2) **`core > estimate` でも上乗せしうる仕様**の自覚。ただし **本番データでの分布ログ**があれば、**1.20 vs 1.10** の選択はより安全。

---

## 8. 今回はまだやらないこと

- **`MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER` の値変更**
- **`offseason_manual_fa_offer_and_years` のロジック変更**
- **`_calculate_offer` / `estimate_fa_market_value` / `sign_free_agent` / `conduct_free_agency` の変更**
- **オフ手動FA の全面再設計・GUI・経済・generator**

---

## 9. テストと確認観点

- **`test_offseason_manual_fa_offer_alignment`**: フォールバック経路で **`final == min(floor, room)`** が維持されているか（倍率変更時は**期待値の意図的更新**が必要）。
- **`test_precheck_user_fa_sign`**: 事前チェックと契約の一貫性。
- **表示＝契約**: オフ手動ウィザード経路で **`offseason_manual_fa_offer_and_years` の戻り値**がそのまま使われているか（回帰）。
- **room 張り付きの監視**: 実装変更後は、**`final_salary == signing_room` の頻度**をログまたはサンプルシーズンで確認できるとよい。

---

## 10. 次に実装で触るべき対象（1つだけ）

**`basketball_sim/config/game_constants.py` ではなく、`free_agent_market.py` の `MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER`（モジュール定数）の数値**

（現状どおり **オフ手動専用倍率はこのファイルに存在**するため、**単一箇所の変更＋pytest 更新**で閉じやすい。）

### なぜ最初の1手として最も安全か

- **floor 適用条件の分岐追加**は**挙動の説明責任とテストケースが増える**。一方 **倍率は 1 定数**で、**本監査メモの数値表**と直結して**効果を予測しやすい**。
- **`_calculate_offer` 本体を触らず**に済む。

### そこだけ触ると何が改善するか

- **`manual_floor_offer` の絶対額**が下がり、**`core` との max 関係**が緩み、**不要な上乗せ・room 張り付き**が減る**可能性**。

### 何はまだ残るか

- **`core < estimate` 未満帯**の扱い、**フォールバック後の二段上げ**の是非（**条件付き floor** は別コミット）。
- **長期的には** `game_constants` への移管や **正本テーブル連動**は未着手。

---

## 変更履歴

- 2026-04-07: 初版（1.35× estimate 下限の強度監査メモ）。
