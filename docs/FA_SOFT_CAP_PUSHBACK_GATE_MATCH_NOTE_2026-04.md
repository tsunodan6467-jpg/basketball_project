# `payroll_after_pre_soft_pushback` と `soft_cap` — Cell B 観測とゲート条件の照合

**作成日**: 2026-04-08  
**性質**: **観測とコードの照合（コード変更なし）**。コードパス: `docs/FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE_2026-04.md`。読み順: `docs/FA_SOFT_CAP_PUSHBACK_GATE_NOTE_2026-04.md`。観測: `docs/FA_SOFT_CAP_PUSHBACK_OBSERVE_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`**）。

---

## 1. 目的

- **Cell B 実 save の observer 結果**と **`if payroll_after > soft_cap:`** ゲートを **突き合わせ**、**`soft_cap_pushback_applied` が偽ばかりになる読み**が **どこまで妥当か**を **短く整理**する。
- **修正案・仮説の断定はしない**。

---

## 2. 確定事実

- **Cell B 実 save 観測**（**`pre_le_pop` 母集団**）: **`soft_cap_pushback_applied true=0 false=1920`**。
- **`hard_over_minus_soft_pushback eq0=1920 gt0=0`** — **pushback 前後 offer は一致**。
- **コード上**（**`FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE` どおり**）: **`payroll_after > soft_cap`** のときだけ **`offer` を `max(0, soft_cap - payroll_before)` に置き換え**、**`soft_cap_pushback_applied` は真**。**それ以外は偽**で **offer はそのまま**。
- **よって**、**少なくとも当該母集団では** **「pushback 側の真枝に入っていない」**読みが **コードと整合**する（**最有力**）。

---

## 3. 今回の照合

| 観測 | コード |
|------|--------|
| **`soft_cap_pushback_applied` が偽一色** | **`if payroll_after > soft_cap:`** が **常に偽** |
| **前後 offer 差分ゼロ** | **偽枝では `offer` を変えない**ため **自然** |

**照合の帰結（最有力読み・断定しない）**: **Cell B 実 save の母集団では**、**`payroll_after_pre_soft_pushback`（= ゲート直前の `payroll_after`）が `soft_cap` 以下に収まっている行が支配的**である **可能性が高い**（**ゲート未到達**）。

**留保**:

- **標準出力では** **`payroll_after_pre_soft_pushback` の分布**や **`soft_cap` との差**を **まだ直接は出していない**（**`diag` キーは存在**）。
- **よって** 上記は **観測フラグとコード構造からの整合推論**に留まり、**数値分布までの実証は次段**。

---

## 4. 今回の判断（1 案）

**次の観測では、`payroll_after_pre_soft_pushback` と `soft_cap` の関係そのものを確認する。つまり、soft cap pushback 不発の理由は、まず「ゲート未到達」を第1仮説として扱う。**

- **いちばん自然な仮説**は **`payroll_after_pre_soft_pushback <= soft_cap`** が **続いている**こと。
- **先に** それを **観測で確かめる**。
- **pushback 式が「弱い」**といった **次の段階の議論には、まだ進めない**。

---

## 5. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **budget 側へ議論を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。
- **仮説の断定**。

---

## 6. 次に続く実務（1つだけ）

**`payroll_after_pre_soft_pushback` と `soft_cap` の min/max/代表分位、または `> soft_cap` 件数を最小限 observer に出す必要があるかを決める短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE_2026-04.md -Pattern "目的|確定事実|今回の照合|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（Cell B 観測とゲートの照合）。
