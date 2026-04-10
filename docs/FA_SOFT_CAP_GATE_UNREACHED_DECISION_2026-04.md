# soft cap pushback ゲート未到達 — Cell B 実 save 観測の固定（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **観測結果の固定と次段焦点の決裁（コード変更なし）**。照合: `docs/FA_SOFT_CAP_PUSHBACK_GATE_MATCH_NOTE_2026-04.md`。読み順: `docs/FA_SOFT_CAP_PRE_GATE_RELATION_NOTE_2026-04.md`。出力判断: `docs/FA_PRE_GATE_MIN_OUTPUT_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**ゲート条件**）。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。

---

## 1. 目的

- **Cell B 実 save** の observer 結果から **soft cap pushback が「発火条件に届いていない」**読みを **決裁として固定**する。
- **次段の観測焦点**を **`soft_cap` 水準**と **`payroll_before + offer_after_hard_cap_over`（= `payroll_after_pre_soft_pushback`）が soft cap に届かない理由**に **置く**。
- **pushback 修正式の決定はしない**。

---

## 2. 確定事実

**母集団**: **`pre_le_pop`（1920 pair）**。**D2 / D1 ともに**以下が **観測上整合**する。

| 指標 | 内容 |
|------|------|
| **`soft_cap_pushback_applied`** | **`true=0` `false=1920`**（**全件偽**）。 |
| **`hard_over_minus_soft_pushback`** | **`eq0=1920` `gt0=0`**（**pushback 前後 offer は数値上一致**）。 |
| **`payroll_after_pre_vs_soft_cap`** | **`gt=0 (0.0%)` `le_eq=1920 (100.0%)`**（**`payroll_after_pre_soft_pushback > soft_cap` は 0 件**）。 |

**数値レンジ（参考・観測ログより）**

| リーグ | `payroll_before` | `offer_after_hard_cap_over` | `payroll_after_pre_soft_pushback` |
|--------|------------------|----------------------------|-----------------------------------|
| **D2** | 約 588M〜1,091M | 約 106M〜138M | 約 694M〜1,200M |
| **D1** | 約 697M〜1,048M | 約 111M〜144M | 約 808M〜1,192M |

**コード上のゲート**（**`if payroll_after > soft_cap:`**）と **併せると**、**少なくとも当該母集団では** **pushback 真枝に入っていない**ことが **観測・実装の両方で説明できる**（**根本原因の単一断定はしない**）。

---

## 3. 今回の判断（1 案）

**soft cap pushback 不発の第1仮説は、`payroll_after_pre_soft_pushback <= soft_cap` が母集団で支配的な「ゲート未到達」である。したがって次段は、pushback 式そのものではなく、`soft_cap` 水準と `payroll_before + offer_after_hard_cap_over` の関係を読む。**

- **pushback が「弱い」**議論には **まだ進めない**。
- **先に** **ゲート未到達**を **第1仮説として固定**する。
- **次**は **`soft_cap` と pre-gate 合成値の相対**（**未到達の理由**）を **観測で読む**。

---

## 4. この判断の理由

- **観測**（**`applied` 偽一色**、**`> soft_cap` 0 件**）と **コード**（**`payroll_after > soft_cap` のときだけ発火**）が **一致**している。
- **最も単純な説明**は **「発火条件に届いていない」**こと。**より複雑な説明**（**式の減衰不足**等）は **この段階では優先しない**。
- **前後 offer 差分ゼロ**は **未到達**と **矛盾しない**（**偽枝では offer を変えない**）。

---

## 5. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **budget 側（Cell B 式の再議論）へ戻ること**。
- **`final_offer` 飽和まで同時に片付けること**。
- **仮説の最終断定**（**あくまで第1仮説の固定**）。

---

## 6. 次に続く実務（1つだけ）

**`soft_cap` 水準と `payroll_before + offer_after_hard_cap_over` の相対を読むために、`soft_cap` 自体の観測追加が必要かを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SOFT_CAP_GATE_UNREACHED_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（Cell B 観測の固定・次段焦点）。
