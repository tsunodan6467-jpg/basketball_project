# FA：`before` 主軸 — 代表 save と gap／room 一覧（観測値）

**作成日**: 2026-04-08  
**性質**: **一覧メモ（コード変更なし）**。数値は **`tools/fa_offer_real_distribution_observer.py` の当該バージョン出力**から取得（リポジトリルートで実行）。読み方の正本: `docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md`、`docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`。枠組み: `docs/FA_BEFORE_GAP_SCOPE_OVERVIEW_2026-04.md`。

---

## 1. 目的

- **before 主軸**で、**save ごとに `gap` がどの程度潰れているか**（`gap_min`／`gap_max`／`gap_unique`）と、**補助軸**として行列の **`room_unique`／`pre_le_room`** を**並べ、ざっくり比較する**ための表である。
- **オフ後式の変更決裁ではない**。判断前段の**代表サンプル**に過ぎない。

---

## 2. 読み方

- **`sync_observation` の `before`**: **比較観測の主軸**（同期前の全対象チーム集計）。
- **`summary:` の `room_unique`／`pre_le_room`**: **同期後の `payroll_budget` を入力にした行列**由来（**補助**）。
- **`payroll_budget`**: **現行式のフィールド**。**`roster_payroll`**: **契約実態**。同一視しない（`docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md`）。
- 本表の **`before`／`summary` はリーグ全体（48 チーム＝D1／D2／D3 各 16）の一括値**。**D 別に observer が行を分けては出力しない**。列「リーグ／母集団」はその説明と、**`user_team_snapshot` に出る user の `league_level`**（本データではいずれも **user=D3**）を併記する。

---

## 3. 代表表

取得コマンド（リポジトリルート）:

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
python tools\fa_offer_real_distribution_observer.py
python tools\fa_offer_real_distribution_observer.py --save-list fa_clip_20260408_01.sav fa_clip_20260408_02.sav fa_clip_20260408_04.sav fa_clip_20260408_05.sav
```

| save 名 | リーグ／母集団 | save 種別（推定） | before gap_min | before gap_max | before gap_unique | room_unique | pre_le_room | 補足 |
|--------|----------------|-------------------|----------------|----------------|-------------------|-------------|-------------|------|
| （引数なし・生成ワールド） | 48 チーム集計／user=D3 | sim / initial | 0 | 0 | 1 | 1 | 0 | `budget_unique=1`（120M 寄りの初期系） |
| `fa_clip_20260408_01.sav` | 〃 | initial / pre-off | 0 | 0 | 1 | 1 | 0 | `budget_unique=1`・user `payroll_budget=120,000,000` |
| `fa_clip_20260408_02.sav` | 〃 | post-off | 0 | 0 | 1 | 1 | 0 | `budget_unique=48`・user `payroll_budget=22,242,975`（⑦後型） |
| `fa_clip_20260408_04.sav` | 〃 | post-off | 0 | 0 | 1 | 1 | 0 | user `roster_payroll` が 02 より大（進行差） |
| `fa_clip_20260408_05.sav` | 〃 | post-off | 0 | 0 | 1 | 1 | 0 | 04 と user 断面同型（`docs` 用途の別採取） |

**本表に含めないもの**: **D1 または D2 の user のみ**に絞った save、`fa_gap_20260408_postoff_01.sav` のような **リポ外の post-off** は**今回 observer 未実行**のため行としては載せず、数値例は `docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md` 等を参照。**10 人ロスター特化 save** は本リポ同梱の 4 本ではラベル付けしていない；現象の整理は `docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`。

---

## 4. 暫定読解

- **本表に載った範囲**では、**いずれも `before` で `gap_min=gap_max=0` かつ `gap_unique=1`**（全チーム同型の潰れ）。**post-off 系（02／04／05）**でも **before 側の潰れ方は数値上は initial 系（01）と同じ見え方**になる。**差は `budget_unique` と user の `payroll_budget`／`roster_payroll` の断面**で読む必要がある。
- **行列の `room_unique=1`／`pre_le_room=0`** は **同期後入力で均されやすい**補助指標として一貫しており、**clip 前の多様性は before で見る**という既決読みと整合する。
- **D1／D2／D3 を save 行として分けた比較**は**できていない**（集計がリーグ横断のため）。**普遍性の判断はまだ粗い**。
- **断定**: 「式変更必須」まではこの表だけでは言えない。

---

## 5. 非目的

- **オフ後 `payroll_budget` 式の変更**、**clip／λ／buffer の変更**、**コード／observer の変更**は行わない。

---

## 6. 次に続く実務（1つだけ）

**この代表表を踏まえ、式変更要否の議論に入る前に、「D1 または D2 の user を含む save をあと 1〜2 本だけ追加し、同じ observer コマンドで `before`／`summary` を足すか否か」を短く決める**（採取は最小限）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BEFORE_GAP_REPRESENTATIVE_SAVE_TABLE_2026-04.md -Pattern "目的|読み方|代表表|暫定読解|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（リポ同梱 `fa_clip_*.sav` 4 本＋引数なし 1 行・observer 出力ベース）。
