# `payroll_budget` が「低い」まま save／観測に出る理由（設定・更新・保存経路）

**作成日**: 2026-04-08  
**文書の性質**: **原因分析メモ（コード変更なし）**。関連: `docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`、`docs/FA_BEFORE_AXIS_SAVE_PLAYCHECK_2026-04.md`、`docs/FA_ROOM_UNIQUE_ONE_CAUSE_NOTE_2026-04.md`。観測例: `tools/fa_offer_real_distribution_observer.py` の `user_team_snapshot`（既定シミュで `money` 大・`payroll_budget=120,000,000`・`roster_payroll` 大・`gap=0`）。

---

## 1. 文書の目的

**所持金 `money` は多いのに `payroll_budget` が低い**という断面を、`money` ではなく **`payroll_budget` の設定・更新・保存経路**で説明できるようにする。**「資金難対策で所持金を増やした」**ことが **なぜ `payroll_budget` を押し上げないのか**に答え、**7 人ルールより先に見るべき論点**を固定する。

---

## 2. `payroll_budget` の設定・更新・保存経路

### 2.1 初期設定（コードから読める）

| 経路 | 内容 |
|------|------|
| **`Team`  dataclass 既定** | `basketball_sim/models/team.py` で **`payroll_budget: int = 120000000`**（1 億 2 千万円）。生成時に上書きされなければこの値のまま。 |
| **`generate_teams()`** | `basketball_sim/systems/generator.py` で `Team(...)` 生成時 **`payroll_budget` を渡していない**ため、**上記既定のまま**。ロスター年俸は `_rebalance_team_initial_salaries_to_target` で調整されるが、**チームの `payroll_budget` フィールドは自動ではロスターに追従しない**（別フィールド）。 |
| **`apply_user_team_to_league()`** | `basketball_sim/main.py` でユーザーチーム化の際 **`money = TEMP_INITIAL_TEAM_MONEY` 等は設定するが `payroll_budget` は触らない**。置き換え先 D3 チームも **`generate_teams` 由来なら既定 120M のまま**になりやすい。 |
| **欠損時の補完** | `Team` 側の `_ensure_history_fields` 等で **`payroll_budget` が無い場合は 120M 代入**（既存値がある場合は維持）。 |

### 2.2 シーズン中／オフでの更新（コードから読める）

| 経路 | 内容 |
|------|------|
| **`record_financial_result`（`Team`）** | **`money` に収支を反映**するが、**`payroll_budget` は更新しない**（`basketball_sim/models/team.py`）。 |
| **オフ・シーズン締め処理** | `basketball_sim/models/offseason.py` のシーズン締め経済処理で、**`team.payroll_budget = max(base_budget, 市場・人気・スポンサー等の式)`** により **「来季人件費目安」として再計算**されうる（リーグレベル別 `base_budget` ＋係数）。**ここを通らない局面では `payroll_budget` は古い／既定のまま**。 |
| **`_sync_payroll_budget_with_roster_payroll`** | **FA 直前など**で **`payroll_budget = max(既存, roster_payroll + buffer)`**。**既存が低くても同期後は床まで引き上げ**（observer の `sync1` 以降で見える挙動）。**ただし observer の `before` は同期前**なので、**この関数未実行時点では低い `payroll_budget` がそのまま見える**。 |

**観測済み（静的・実行）**: `Season` 本体に **`payroll_budget` を直接いじるgrepは主線に無い**（シーズン進行は主に試合・日程）。**更新の主戦場はオフ締め系と同期**。

### 2.3 save／load（コードから読める）

| 経路 | 内容 |
|------|------|
| **保存** | `save_world` は **pickle で `payload` ごと丸ごと**保存。`teams` は **`Team` インスタンスのグラフ**として **`payroll_budget` 属性ごと保持**。 |
| **読込** | `load_world` → `normalize_payload` は **チームごとに `ensure_*` をかけるが `payroll_budget` を再計算する処理は入っていない**（`basketball_sim/persistence/save_load.py`）。 |
| **主線仮説** | **「セーブに低い／既定の `payroll_budget` が書かれていれば、ロード直後もそのまま」**。**ロードが勝手に上げるわけではない**。 |

### 2.4 観測との接続（既定 observer シミュ）

**観測済み**: 既定 `fa_offer_real_distribution_observer.py`（`--seasons 0`）は **`generate_teams` → `apply_user_team_to_league` → ドラフト**までを通し、**`main.py` のインタラクティブ開始で走る `normalize_initial_payrolls_for_teams` は呼ばない**。また **`Offseason.run` による締めの `payroll_budget` 再計算も通さない**。  
→ **ユーザーチームの `payroll_budget` が `Team` 既定の 1.2 億円のまま**、一方でドラフト後 **ロスター給与だけが大きい**、という組合せは **コード上自然**。**`money` は `apply_user_team_to_league` で 20 億に上がる**ため、**`user_team_snapshot` で乖離が出る**。

**断定でない部分**: 実プレイ save が **いつオフ締めを通過したか**は save ごと。**「低い」のが「未締めの既定のまま」か「締め式の結果として低い」か**は **その save の進行履歴と式の出力次第**。

---

## 3. `money` と `payroll_budget` が乖離しうる理由

- **別フィールド**: **`money` はクラブの現金残高**。**`payroll_budget` は「給与の目安・ガイドライン」**（経営レポートや FA の room 計算の入力）。**同じ財布ではない**。
- **所持金を増やしても**: **`record_financial_result` 経路では `payroll_budget` は増えない**。チートや外部で `money` だけ上げた場合も、**`payroll_budget` が自動連動するコードは主線に無い**。
- **間接経路（ありうる）**: **オフ締め・経営メニュー等で触る処理**が `payroll_budget` を更新する場合は **間接的に変わりうる**が、**「money が増えたから」という単純な因果ではない**。
- **強さ**: **「資金難対策で所持金をかなり増やした」→「`payroll_budget` が上がる」は期待しにくい**。**観測上の乖離は仕様上も自然**。

---

## 4. 今回の原因整理から分かること

- **ボトルネック**は **ロスター人数より `payroll_budget` 側**の可能性が高い（before gap／snapshot と整合）。
- **7 人ルールより先に**、**どの経路で `payroll_budget` が最後に書き換わったか**を切り分けるのが安全。
- **主因候補の強さ（短い判断）**  
  1. **`money` 非連動**（強い）— コード上、収支は `money` に効き、`payroll_budget` は別更新。  
  2. **保存値の持ち越し**（強い）— pickle は `payroll_budget` をそのまま保持；**低ければロードも低い**。  
  3. **オフ締め等での再設定**（ケース依存）— **通っていれば**式の結果で上書き；**通っていなければ**既定／古い値のまま。

**ユーザーの感覚（money 非連動＋保存 or 別経路で低い）**は **コード構造と整合**。**より強い補足**は、**既定観測ワールドでは「オフ締め・normalize 経路を通さないため既定 120M が残る」**が **再現しやすい**こと。

---

## 5. 今回はまだやらないこと

- **`payroll_budget` の式・同期・clip の改修**  
- **save 形式の変更**、**ロード時の自動引き上げ**  
- **observer のロジック変更**（本メモは読み取りのみ）

---

## 6. 次に実装で触るべき対象（1つだけ）

**`save_world` → `load_world` の round-trip で、同一 `Team`（少なくともユーザーチーム）の `payroll_budget` が不変であることを確認する最小 pytest を 1 本追加する**（テスト用にメモリ上で `build_save_payload` 相当の dict を組み、保存→読込→同一性 assert）。

- **なぜその1手が今もっとも妥当か**  
  **「低いのはロードが壊している」**仮説を先に潰せる。**残る論点は「セーブ前のゲーム進行で `payroll_budget` がいつ最後に更新されたか」**に集中できる。  
- **何はまだ残るか**  
  **本番フローで `normalize_initial_payrolls_for_teams` 前後・オフ締め前後の `payroll_budget` を段階ログする観測**、**実 save と進行履歴の突合**、**要件メモ（`FA_CLIP_COMPARE_SAVE_REQUIREMENTS`）の更新**。

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
Select-String -Path docs\PAYROLL_BUDGET_PERSISTENCE_CAUSE_NOTE_2026-04.md -Pattern "payroll_budget|money|pickle|round-trip"
```

---

## 改訂履歴

- 2026-04-08: 初版（`payroll_budget` の持たれ方と `money` 乖離の整理）。
