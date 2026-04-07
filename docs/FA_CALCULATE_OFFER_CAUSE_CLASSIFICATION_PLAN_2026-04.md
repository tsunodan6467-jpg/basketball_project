# `_calculate_offer` の 0 / 極小オファー: 原因分類の観測・ログ設計メモ

**作成日**: 2026-04-06  
**文書の性質**: **設計のみ（コード変更なし）**。対象実装: `basketball_sim/systems/free_agency.py` の `_calculate_offer`。  
**直前観測**: `docs/OFFSEASON_FA_PAYROLL_BUDGET_BUFFER_PLAYCHECK_2026-04.md`（budget buffer は room=0 型に効くが soft cap 型には効かない等）

---

## 1. 文書の目的

`payroll_budget` 同期＋`MIN_SALARY_DEFAULT` buffer 後も、**`_calculate_offer == 0` や極小オファー**は複数経路で起きうる。**buffer 増・本体改修の前に**、**原因カテゴリを切り分けて見える化**し、次の実装判断（どの層に手を入れるか）の根拠にする。本メモは **本体にログを埋め込まず**に済む **最小・安全な観測方針**を整理する。

---

## 2. 0 / 極小オファーの原因候補

`basketball_sim/systems/free_agency.py` の `_calculate_offer` の**実行順**に沿った候補（ラベルは実装時の列挙子の例）。

| カテゴリ（例） | 条件・内容 |
|----------------|------------|
| **S1_soft_cap_early** | **`payroll_before >= soft_cap`** のとき **即 `return 0`**。以降の分岐は通らない。 |
| **S2_base_low** | `player.salary <= 0` のとき **`base = max(ovr * 10_000, 300_000)`**。FA の芯が意図的に低いと、その後のクリップまで **極小の出発点**になる（単独では 0 とは限らない）。 |
| **S3_hard_cap_bridge** | **`payroll_before <= cap_base < payroll_after`**（契約でハードをまたぐ）→ **`offer = min(offer, room_to_soft)`**、`room_to_soft = soft_cap - payroll_before`。 |
| **S4_hard_cap_over** | **`payroll_before > cap_base`**（既にハード超え）→ **`min(offer, room_to_soft, low_cost_limit)`**、`low_cost_limit` は **`min(max(base,0), 900_000)`** 等で **極小化しやすい**。 |
| **S5_soft_cap_pushback** | **`payroll_after > soft_cap`** → **`offer = max(0, soft_cap - payroll_before)`**。 |
| **S6_budget_room** | **`room_to_budget = max(0, payroll_budget - payroll_before)`**、`room_to_budget == 0` なら **`offer = 0`**。buffer で緩和しうるのは主にここ。 |
| **S7_luxury_tax** | **`tax_delta >= tax_warn`** → **`offer = int(offer * 0.85)`**。直前まで正でも **一段下げ**。 |
| **S8_floor_zero** | 最終 **`return max(0, int(offer))`** の丸め。 |

**「極小オファー」**は **S6（room が MIN_SALARY 程度）**、**S4/S5 と S6 の複合**、**S7 後**など、**最終額 << base＋ボーナス理論値**の状態として扱う。

---

## 3. 原因ごとの見分け方

**単一の「最終ラベル」**は、パイプラインが**直列クリップ**のため、**各段の前後で `offer` のスナップショット**がないと誤判定しやすい。観測では最低限、次を取る。

### 3.1 入口（分類の土台）

- **`payroll_before`** … `_team_salary(team)`（= `get_team_payroll`）  
- **`soft_cap`**, **`cap_base`（ハード）** … `_soft_cap` / `_hard_cap` と同型の単一入口（`salary_cap_budget`）  
- **`payroll_budget`** … `getattr(team, "payroll_budget", soft_cap) or soft_cap` と**本体と同じ式**  
- **`base`** … `player.salary` または `ovr * 10_000` 下限 300,000  
- **ボーナス前後** … `surplus`, `bonus`, **`offer_pre_clip = base + bonus`**（観測用の名前）

### 3.2 判定のヒント（静的・単点では不十分な場合あり）

- **S1**: `payroll_before >= soft_cap` なら **確定**（他を見なくてよい）。  
- **S6**: `payroll_before < soft_cap` かつ **`room_to_budget == 0`** なら **予算クリップが 0 に寄与**。**最終 0** のとき特に有効。  
- **S5**: クリップ直前 `payroll_before + offer > soft_cap` かつ **直後 `offer == soft_cap - payroll_before`** に近い関係。  
- **S4**: `payroll_before > cap_base` かつ **最終 offer が `low_cost_limit` オーダー**に張り付きがち。  
- **S7**: `tax_delta >= tax_warn` が真なら **最後に 15% 減**。  
- **極小**: **`offer_pre_clip` に対し最終が極端に小さい** → **どの `min` が効いたか**を段別スナップショットで特定。

**注意**: 「**primary cause**」を1つに決めるより、**「効いたクリップの列」**（例: `S4 → S6 → S7`）として記録する方が実装と整合しやすい。

---

## 4. 最小の観測・ログ設計案

| 案 | 内容 | 利点 | 欠点 |
|----|------|------|------|
| **A. `_calculate_offer` 本体に `print`/ログ** | 各分岐で出力 | 本物の順序が取れる | **ユーザー方針: 本体へのログ埋め込みは避ける**。本番ノイズ・パフォーマンス・差分肥大。 |
| **B. 呼び出し側だけ観測** | `conduct_free_agency` 前後で team/player をダンプ | 本体非変更 | **中間 `offer` が見えず**、S4/S5/S6 の**重なり**が分類しにくい。 |
| **C. テスト行列（pytest）** | 合成 `Team`/`Player` で **期待カテゴリ**をタグ付け | CI で回帰、本体ゼロ改変で可能 | **実セーブの分布は取れない**・ケース追加コスト。 |
| **D. 観測専用ヘルパ（別関数）** | `_calculate_offer` と**同じ式**をトレース付きで実行し **dict/dataclass 返却** | 本体行をいじらない・**段別スナップショット**が取れる | **ロジック二重化**（ドリフトリスク）→ **テストで本関数と一致**を必須にする。 |

**推奨（今の段階で一番安全）**: **案 D（`free_agency.py` に観測専用の別関数）＋ 案 C の一部（一致テスト）**。  
本体 **`_calculate_offer` は1行も変えず**、開発時のみ `explain_*` を呼ぶか、一時的に CLI/スクリプトから呼ぶ。**本番デフォルトでは無出力**。

---

## 5. 今の段階で最も安全な観測方法

- **なぜ本体変更より観測を先にやるか**  
  - buffer は **S6 系**に効き、**S1 系**には効かないことが既に観測済み。**同じ「0」でも対策が別**のため、**対症療法の順序を誤らない**には **分類が先**。  

- **最小の観測点をどこに置くか**  
  - **`free_agency.py` 内の観測専用関数**（例: `_calculate_offer_trace` / `diagnose_calculate_offer`）。**`conduct_free_agency`・`offseason_manual_fa_offer_and_years` には触れない**第1弾とする。  

- **どの程度で次の判断ができるか**  
  - **合成ケース**で S1/S4/S5/S6/S7 の **再現とラベル一致**が取れれば、**「buffer を上げるべきか / soft cap 側を見るべきか」**の門番は立つ。  
  - **実プレイ分布**は、必要なら **後段で**開発フラグ付きログやセーブフックを検討（本メモ範囲外）。

---

## 6. 今回はまだやらないこと

- **`_calculate_offer` の本体ロジック変更**（クリップ式の変更・早期 return の変更を含む）  
- **`_calculate_offer` 本体へのログ・print の恒久的埋め込み**  
- **`payroll_budget` buffer のさらなる増額**  
- **`offseason_manual_fa_offer_and_years` の floor 条件・倍率変更**  
- **オフ手動FA全面再設計**  
- **generator / GUI / 経営収支のついで改修**

---

## 7. 次に実装で触るべき対象（1つだけ）

**`basketball_sim/systems/free_agency.py` に、観測専用の別関数を1本追加する**（例: **`_calculate_offer_diagnostic(team, player) -> dict`** または **小さな `@dataclass` 戻り値**）。

- **なぜ最も安全か**  
  - **`_calculate_offer` のシグネチャ・戻り値・本番呼び出し経路を変えない**。  
  - **`conduct_free_agency` / オフ手動FA / GUI に波及しない**よう、**デフォルトでは未使用**にできる。  
  - ログを本体に散らさず、**必要なときだけ**診断関数を呼べる。  

- **そこだけ触ると何が分かり、何がまだ残るか**  
  - **分かる**: 合成ケースにおける **段別の `offer`・トリガとなった条件**（S1/S4〜S7 のどれが効いたかの列）。  
  - **残る**: **実セーブでの頻度**、**診断関数と本体のドリフト防止**（**同一入力で `_calculate_offer` と最終数値が一致するテスト**が別途必須）、**極小の主観閾値**（何円未満を「極小」と呼ぶかのプロダクト定義）。

---

## 参考: 観測用に取るとよいフィールド一覧（実装時チェックリスト）

- `payroll_before`, `soft_cap`, `cap_base`, `lv`  
- `base`, `bonus`, `offer_after_base_bonus`  
- `room_to_soft`（S3/S4 での値）  
- `low_cost_limit`（S4）  
- `payroll_after`（S5 判定前後）  
- `payroll_budget`, `room_to_budget`（S6）  
- `tax_before`, `tax_after`, `tax_delta`, `tax_warn`, `tax_clip_applied`（S7）  
- `final_offer`（`_calculate_offer` と必ず一致させる）  

---

## 改訂履歴

- 2026-04-06: 初版（原因分類と観測専用ヘルパ方針）。
