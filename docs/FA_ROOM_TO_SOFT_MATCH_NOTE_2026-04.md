# `room_to_soft` と Cell B 実 save 観測の照合（soft cap 直前停止の読み固定）

**作成日**: 2026-04-08  
**性質**: **照合メモ（コード変更なし）**。コードパス: `docs/FA_HARD_CAP_OVER_CODE_PATH_NOTE_2026-04.md`。候補整理: `docs/FA_HARD_CAP_OVER_STOP_REASON_NOTE_2026-04.md`。ゲート未到達: `docs/FA_SOFT_CAP_GATE_UNREACHED_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`** / **`_calculate_offer`**）。

---

## 1. 目的

- **`room_to_soft = max(0, soft_cap - payroll_before)`** を使う **bridge / over 段の上限制御**と、**Cell B 実 save** の **`soft_cap=1.2B`**・**`payroll_after_pre_soft_pushback`** の観測を **突き合わせ**、**「soft cap 直前で止まる」読み**が **どこまで自然か**を **固定**する。
- **修正案・単一原因の断定はしない**。

---

## 2. 確定事実

**観測（D2 / D1・`pre_le_pop` 母集団に整合する範囲）**

- **`soft_cap_pushback_applied`**: **`true=0` `false=1920`**（**全件偽**）。
- **`payroll_after_pre_vs_soft_cap`**: **`gt=0` が 0%**、**`le_eq` が 100%**（**`payroll_after_pre_soft_pushback > soft_cap` は実質 0 件**）。
- **`soft_cap`**: **観測上 1.2B 固定**（**`value=1200000000`**）。
- **D2**: **`payroll_after_pre_soft_pushback` の最大が 1.2B ちょうど**。**D1**: **最大はそれ未満**（**観測ログより**）。

**コード（bridge / over）**

- **bridge**: **`offer = min(offer, room_to_soft)`**（**`room_to_soft = max(0, soft_cap - payroll_before)`**）。
- **over**: **`offer = min(offer, room_to_soft, low_cost_limit)`**（**同じ `room_to_soft`**）。
- **よって** **hard cap 前段**に **`payroll_before + offer <= soft_cap` に寄せる**経路が **明示的に存在する**（**`FA_HARD_CAP_OVER_CODE_PATH_NOTE` どおり**）。

---

## 3. 今回の照合

- **`room_to_soft`** は **offer の上限**として **`min(...)` に入る**。**理論上** **`offer <= room_to_soft`** のとき **`payroll_before + offer <= payroll_before + (soft_cap - payroll_before) = soft_cap`**（**`room_to_soft` が 0 でない通常ケース**）となり、**soft cap を超えない側**に **止まりうる**。
- **実観測**では **`> soft_cap` が 0 件**で **pushback も全偽**。**D2 では合成 payroll の最大が `soft_cap` と一致**する。
- **この組み合わせ**は、**「bridge / over で `room_to_soft` により上限がかかり、ゲート手前の `payroll_before + offer` が soft cap を超えないまま寄っている」**という **読み**と **整合的**である（**最有力の説明候補の一つ**としてよい）。

**限界（正直に置く）**

- **pair 単位**で **`room_to_soft` の値と diagnostic 各行を直接突合**したわけでは **ない**。
- **D1 が max 未満**なのは **`room_to_soft` 以外**（**`low_cost_limit`**・**bridge 未進入**等）も **ありうる**。
- **よって** **「コードが観測を完全に説明した」とは言わず**、**整合・第1候補読み**の **固定**に **とどめる**。

---

## 4. 今回の判断（1 案）

**soft cap pushback 不発の第1説明として、bridge / over 段で `room_to_soft` を使った上限制御が働き、`payroll_before + offer_after_hard_cap_over` が soft cap を超えないように止まっている読みを第1候補として固定する。**

- **本命の説明軸**は **pushback 本体ではなく hard cap bridge / over 前段**。
- **D2 の max と `soft_cap` の一致**は **その読みを強める**が **単独証明ではない**。
- **次段**は **この読みを崩しうる要素**（**未進入分岐**・**`low_cost_limit`**・**丸め**等）を **必要なら観測で見る**。

---

## 5. 非目的

- **コード変更**。
- **修正案の決定**。
- **pushback 側へ議論の主軸を戻すこと**。
- **`final_offer` 飽和まで同時に片付けること**。
- **読みの最終断定**。

---

## 6. 次に続く実務（1つだけ）

**`room_to_soft` 相当の値を observer に最小追加する必要があるか、または既存情報で十分かを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md -Pattern "目的|確定事実|今回の照合|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`room_to_soft` と実観測の照合・第1候補読みの固定）。
