# hard cap over 段 — `room_to_soft` 以外の上限制約を次焦点に置く（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **次段焦点の決裁（コード変更なし）**。`room_to_soft` 照合: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。コードパス: `docs/FA_HARD_CAP_OVER_CODE_PATH_NOTE_2026-04.md`。候補整理: `docs/FA_HARD_CAP_OVER_STOP_REASON_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`** / **`_calculate_offer`**）。

---

## 1. 目的

- **`room_to_soft` 上限制御**を **第1説明軸として維持**したうえで、**`offer_after_hard_cap_over` がそれよりさらに低い水準で止まっている**可能性に対し、**`low_cost_limit` 等の他制約**を **次の読み焦点**として **固定**する。
- **修正案・原因の単一断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・D2 / D1）**

- **`soft_cap`**・**`room_to_soft`**・**`offer_after_hard_cap_over`** が **同一 observer ブロックで読める**ようになった。
- **分布要約レベル**では **`offer_after_hard_cap_over <= room_to_soft`** の **読みがかなり強い**（**`room_to_soft` 説明と整合**）。

**残る論点**

- **`offer_after_hard_cap_over`** は **`room_to_soft` の典型値よりさらに低いレンジ**に **見える**ことがある（**pair ごとの厳密突合までは本メモの前提に含めない**）。
- **コード上**、hard cap **over** 枝では **`offer = min(offer, room_to_soft, low_cost_limit)`** があり、**`room_to_soft` 単独が上限ではない**。

**よって**、**`room_to_soft` だけで説明を閉じず**、**他の `min(...)` 要素・前段**を **見に行く価値が高い**（**撤回ではなく補完**）。

---

## 3. 今回の判断（1 案）

**hard cap bridge / over 段の第1説明軸は `room_to_soft` で維持する。そのうえで次段では、`offer_after_hard_cap_over` をさらに低く止める要素として、`low_cost_limit` を含む他制約を読む。**

- **`room_to_soft` 読みは維持**（**否定しない**）。
- **終着点にはしない**。**次は over 内の他上限**（**`low_cost_limit` 等**）**と必要なら前段の別 `min`**。
- **pushback 本体や `final_offer` 飽和**には **まだ主軸を移さない**。

---

## 4. 理由

- **D2 / D1** で **`offer_after_hard_cap_over` が `room_to_soft` より低そう**に見える **余地**がある。
- **over 分岐**に **`min(offer, room_to_soft, low_cost_limit)`** があるため、**実効上限**は **`min(room_to_soft, low_cost_limit, …)` 側**に **寄りうる**。
- **したがって** **`low_cost_limit` が支配的か**（**いつ効くか**）を **確認するのが自然な次ステップ**（**断定は観測・コード突合後**）。

---

## 5. 非目的

- **コード変更**。
- **`room_to_soft` 第1軸の撤回**。
- **pushback 側へ議論の主軸を戻すこと**。
- **`final_offer` 側まで同時に広げること**。
- **修正案の決定**。
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`basketball_sim/systems/free_agency.py` の over 分岐で、`low_cost_limit` を含む `min(...)` 要素と代入順を拾う短いコード読解メモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_HARD_CAP_OTHER_LIMITS_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`room_to_soft` 維持＋`low_cost_limit` 等を次焦点に固定）。
