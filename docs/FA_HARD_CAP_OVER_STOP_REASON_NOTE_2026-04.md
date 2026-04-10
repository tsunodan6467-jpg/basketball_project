# `offer_after_hard_cap_over` — soft cap 直前停止の読み（原因候補メモ）

**作成日**: 2026-04-08  
**性質**: **読みの整理（コード変更なし）**。ゲート未到達の固定: `docs/FA_SOFT_CAP_GATE_UNREACHED_DECISION_2026-04.md`。pre-gate 関係: `docs/FA_SOFT_CAP_PRE_GATE_RELATION_NOTE_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`**）。

---

## 1. 目的

- **Cell B 実 save** で **soft cap pushback がゲート未到達**と **固定された次段**として、**`offer_after_hard_cap_over` が soft cap 到達直前で止まっている**という **読み**を **原因候補レベルで整理**する。
- **断定・修正案は書かない**。

---

## 2. 確定事実

**母集団・観測**（**D2 / D1 とも**、**`pre_le_pop` 相当**）:

- **`soft_cap_pushback_applied`**: **`true=0` `false=1920`**（**全件偽**）。
- **`payroll_after_pre_vs_soft_cap`**: **`gt=0 (0.0%)` `le_eq=1920 (100.0%)`**（**`payroll_after_pre_soft_pushback > soft_cap` は 0 件**）。
- **`soft_cap`**: **観測上 `value=1200000000` で固定**（**1.2B**）。
- **`hard_over_minus_soft_pushback`**: **前後 offer 一致**（**eq0 が母集団全体**）— **pushback は発火していない**。

**レンジ（観測ログより・参考）**

| リーグ | `payroll_before` | `offer_after_hard_cap_over` | `payroll_after_pre_soft_pushback` |
|--------|------------------|----------------------------|-----------------------------------|
| **D2** | 約 588M〜1,091M | 約 106M〜138M | 約 694M〜**1,200M（max が soft cap と一致）** |
| **D1** | 約 697M〜1,048M | 約 111M〜144M | 約 808M〜1,192M |

**ここから言えること（読み）**

- **soft cap を超えた行は観測上ない**一方、**D2 では合成 payroll の最大が soft cap と一致**する。
- **よって**「未到達はたまたま」より、**上限直前で止まる構造**がある **読みがかなり有力**（**原因の単一断定はしない**）。
- **次段の焦点**は **`offer_after_hard_cap_over` がその直前でどう作られるか**。

---

## 3. 原因候補（3 のみ）

### 候補A: hard cap over 段の min / clamp

- **`offer_after_hard_cap_over` を確定する段**で、**結果的に soft cap 超過を避ける**ような **上限制御**（**`min(...)` や clamp**）が **入っている可能性**。
- **読むべき次対象**: **hard cap over 段の `min(...)`**、**`soft_cap - payroll_before` 相当**との **関係**。

### 候補B: その前段の bridge / over で既に制限

- **`offer_after_hard_cap_over` の式だけ**でなく、**直前の hard cap bridge / hard cap over の分岐**で、**すでに**「soft cap を超えない側」に **寄っている可能性**。
- **読むべき次対象**: **hard cap bridge**、**hard cap over**、**代入・分岐の順序**。

### 候補C: 等号扱いによる未発火

- **pushback ゲート**は **`payroll_after > soft_cap`**。**ちょうど一致**（**`==`**）は **偽枝**のまま **止まりうる**。
- **前段**が **`soft_cap - payroll_before` にぴったり揃える**なら、**`>` に届かず** **pushback 不発**が **続く構造**の **可能性**（**丸め・int 化**も **併せて見る**）。
- **読むべき次対象**: **`>` 条件**、**前段の丸め / int 化**、**ぴったり一致の作られ方**。

---

## 4. 今回の判断（1 案）

**次の読解・観測は、まず `offer_after_hard_cap_over` 段の上限制御を疑い、`soft_cap - payroll_before` 近辺で止まる構造があるかを優先して確認する。bridge / over 前段は第2順、等号未発火は第3順とする。**

- **第1**: **hard cap over 段**の **clamp / min**。
- **第2**: **その直前**の **bridge / over 分岐**。
- **第3**: **`>` と `==` の扱い**（**等号で止まる線**）。
- **修正案はまだ出さない**。

---

## 5. 観測順の優先順位

1. **`offer_after_hard_cap_over` の生成式 / min / clamp**（**`free_agency._calculate_offer_diagnostic` 内**）。
2. **hard cap bridge / hard cap over の前段分岐**（**代入順**）。
3. **`payroll_after > soft_cap` の `>`** と **`==` で止まる可能性**（**丸め・int**）。

---

## 6. 非目的

- **コード変更**。
- **pushback 修正式の決定**。
- **budget 側へ戻ること**。
- **`final_offer` 飽和まで同時に片付けること**。
- **原因の断定**。

---

## 7. 次に続く実務（1つだけ）

**`basketball_sim/systems/free_agency.py` で `offer_after_hard_cap_over` を作る式と、その直前の bridge / over 分岐を拾う短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_HARD_CAP_OVER_STOP_REASON_NOTE_2026-04.md -Pattern "目的|確定事実|原因候補|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（hard cap over 直前停止の読み・候補3つ・観測順）。
