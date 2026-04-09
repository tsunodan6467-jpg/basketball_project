# オフ後 `payroll_budget` 再設定式と観測 `24,018,800` の対応（原因整理）

**作成日**: 2026-04-08  
**文書の性質**: **原因分析メモ（コード変更なし）**。観測例: save `fa_gap_20260408_postoff_01.sav`（`payroll_budget=24,018,800`, `roster_payroll=832,032,108`, `gap=0`）。前提: `docs/PAYROLL_BUDGET_TIMELINE_CAUSE_NOTE_2026-04.md`、`docs/PAYROLL_BUDGET_PERSISTENCE_CAUSE_NOTE_2026-04.md`、`docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md`。実装: `basketball_sim/models/offseason.py` の `_process_team_finances`。

---

## 1. 文書の目的

**1 オフ後 save** で `payroll_budget=24,018,800` となった理由を、**⑦ `_process_team_finances` 内の再設定式**だけで読み解く。**ロスター年俸（約 8.3 億）とこの数値の関係**を、**仕様として自然か／観測上のボトルネックか**に分類して次の判断に渡す。

---

## 2. オフ後 `payroll_budget` 再設定式の読み下し

### 2.1 どこで・どう計算されるか（コードから読める）

- **場所**: `Offseason._process_team_finances` の各チームループ内。シーズン締めの収支・賞金合算の処理の**後**、チームごとに **1 回、代入**される。
- **形**: **`max(底上げ用の base_budget, 内側の式)`**。通常は **内側の式の方が大きく**、**その整数化結果が `team.payroll_budget`** になる。
- **リーグ別 `base_budget`（底）**  
  - **D1**: 7,900,000 円  
  - **D2**: 5,450,000 円  
  - **D3**: **3,650,000 円**  
  いずれも「これ未満にはしない」ための **下限**。
- **内側の式（人間向けの読み）**  
  **「`base_budget` に、市場規模・人気・スポンサー・ファン基盤のスコアを、それぞれ固定の円単価で足し合わせた見積り」**。  
  - **市場規模 `market_size`**: 倍率として **`× 12,500` 円**（浮動小数で掛けてから全体を `int`）。  
  - **人気 `popularity`**: **`× 6,200` 円**。  
  - **スポンサー力 `sponsor_power`**: **`× 5,000` 円**。  
  - **ファン基盤 `fan_base`**: **`× 3,600` 円**（ここが数が大きいと **一気に千万円オーダー**を作りやすい）。  
- **`money` は式に入らない**。`getattr` のデフォルトは **欠損時**用（例: `fan_base` 未設定時は 50 など）で、通常の `Team` では実フィールド値が使われる。

### 2.2 観測済みとの関係

- この式は **「実際の契約年俸総額（ロスター payroll）」を入力に含まない**。よって **再設定後の `payroll_budget` がロスターより桁違いに小さくても、コード上は矛盾ではない**。

---

## 3. user team の 24,018,800 との対応

### 3.1 式と整合するか

- **はい**。`league_level=3`（D3）とすれば `base_budget=3,650,000`。内側の和が **20,368,800** なら全体は **24,018,800**。
- **厳密に一致する整数例**（検算用・実 save と同一とは限らない）:  
  **`market_size=1.2`, `popularity=44`, `sponsor_power=49`, `fan_base=5510`** のとき、コードと同じ `int(max(...))` で **ちょうど 24,018,800** になる（静的検算で確認済み）。
- **実 save** の user team が上記と同じ属性かは **セーブ内の `Team` を読めば確定**する。いずれにせよ **「約 2400 万円台」は、D3 の base と上記4係数の組合せとして十分ありうるオーダー**。

### 3.2 なぜ `roster_payroll=832,032,108` と乖離するか

- **理由（仕様）**: **再設定式は「来季人件費目安」用の経営指標**で、**現ロスターの年俸合計に追従しない**。高額ロスターでも **式の出力は数千万〜億未満台に留まりうる**。
- **D3 だから特別に低いか**: **base の 365 万は D1/D2 より小さい**が、**内側の主役は `fan_base × 3,600` 等**であり、**「D3 だから 8 億ロスターに引きずられる」処理は無い**。
- **before `gap=0`**: observer 定義 **`gap = max(0, payroll_budget − roster_payroll)`** なので、**予算がロスターより小さいと必ず 0**。観測 **「24,018,800 vs 832,032,108」** は **クリップで 0** と整合。

### 3.3 自然か／ボトルネックか

- **仕様としては自然**（式に roster を入れていない）。  
- **FA clip 観測の「before で gap が開かない」**という目的では **強いボトルネック**（**予算フィールドがロスター規模と無関係に低く出る**ため、**同期前でも room が生まれにくい**）。

---

## 4. 今回の原因整理から分かること

- **本丸**は **`money` でも load でもなく**、**⑦の再設定式が作る `payroll_budget` の水準**側に寄った。  
- **この式のまま**では **`payroll_budget << roster_payroll`** が起きやすく、**before の `gap=0` 一色**は **自然な帰結**。  
- **7 人ルール**は **ロスター人数は変えても、この式は `payroll_budget` を直接動かさない**ため、**本質改善には直結しにくい**。  
- **式そのものを議論する前に**、**実 save の user team の 4 属性＋ `league_level` を観測し、24,018,800 を式で再検算できる状態**にすると、**「想定どおりの式か／属性が想定外か」**が切れる。

---

## 5. 今回はまだやらないこと

- **`_process_team_finances` 内の式の変更**  
- **`payroll_budget` と roster の連動化**  
- **observer / clip / buffer / λ の変更**

---

## 6. 次に実装で触るべき対象（1つだけ）

**`user_team_snapshot`（または load 直後の1行ログ）に、`league_level`・`market_size`・`popularity`・`sponsor_power`・`fan_base` を追加し、手元 save で `24,018,800` を本式で再検算できるようにする。**

- **なぜその1手が今もっとも妥当か**  
  観測値が **式の結果か**、**別経路の上書きか**を切り分ける最短。**数式の是非**に入る前に **入力属性の確定**が要る。  
- **何はまだ残るか**  
  **D1/D2/D3 で同式の分布を並べる pytest**、**式・同期・clip の設計決裁**、**「目安」と roster の関係をゲームデザインでどう扱うか**。

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
Select-String -Path docs\PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md -Pattern "24,018,800|base_budget|fan_base|gap"
```

---

## 改訂履歴

- 2026-04-08: 初版（オフ後式と観測 `24,018,800` の整理）。
