# hard cap **bridge** 条件と Cell B 実観測の照合（ゲート整合メモ）

**作成日**: 2026-04-08  
**性質**: **照合メモ（コード変更なし）**。bridge vs over 決裁: `docs/FA_BRIDGE_VS_OVER_DECISION_2026-04.md`。`room_to_soft`: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。`low_cost_limit` パス: `docs/FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`（**`_calculate_offer_diagnostic`**）。

---

## 1. 目的

- **bridge 枝の条件**（**`payroll_before <= cap_base < payroll_after`**）と **Cell B 実 save の観測**（**`payroll_before`・`offer_after_hard_cap_over`・`payroll_after_pre_soft_pushback`**）を **突き合わせ**、**「bridge が主に効いている」読み**が **どこまで自然か**を **固定**する。
- **コード変更・修正案・単一原因の断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・D2 / D1・分布要約）**

- **`room_to_soft`**（**108M〜612M / 152M〜503M 目安**）と **`offer_after_hard_cap_over`**（**106M〜138M / 111M〜144M 目安**）は **`offer <= room_to_soft`** の **読みとかなり整合**（**`FA_ROOM_TO_SOFT_MATCH_NOTE` 系の整理**）。
- **`payroll_after_pre_vs_soft_cap`**: **`> soft_cap` は 0 件**、**`soft_cap` は 1.2B 固定**。**D2 max は 1.2B ちょうど**。**合成 payroll は常に soft cap 以下**。
- **over 枝の `low_cost_limit`（≤900k）**は **観測の 100M 台 offer と乖離が大きく**、**現時点では支配説明として弱い**（**`FA_BRIDGE_VS_OVER_DECISION` どおり**）。

**よって** **bridge 枝を第1候補とする決裁**は **観測と矛盾しにくい**（**本命の確定ではない**）。

---

## 3. 今回の照合

**コード上の bridge 条件**（**`payroll_after` は `base + bonus` 直後の `payroll_before + offer`**）

- **`payroll_before <= cap_base < payroll_after`**  
  → **現 payroll は hard cap 以下だが、この FA の芯＋ボーナス後の合成が hard cap をまたぐ**とき **bridge 真枝**。**`offer = min(offer, room_to_soft)`**。

**実観測との関係（読み）**

- **`payroll_after_pre_soft_pushback = payroll_before + offer_after_hard_cap_over`**（**mapping どおり**）。**全件 `<= soft_cap`** かつ **D2 で max が cap に一致**するのは **`room_to_soft` による上限**と **整合**する。
- **`offer_after_hard_cap_over <= room_to_soft`** が **強い**のは **`min(offer, room_to_soft)` が効いた後**の **典型的な姿**と **一致しやすい**。
- **したがって** **少なくとも Cell B 実 save では**、**bridge で `min(offer, room_to_soft)` が効いている読みは自然**（**最有力候補の一つ**として **よい**）。

**限界**

- **`cap_base`**（**`_hard_cap(team)`**）は **現行 observer 標準出力に無い**。**条件式の左端・中点を行ごとに検証したわけではない**。  
- **over が同一行で後から更に絞るケース**や **bridge 未進入**の **混在**は **このメモだけでは切り分けない**。  
- **よって** **「整合的」「第1候補」で止め**、**断定はしない**。

---

## 4. 今回の判断（1 案）

**bridge 条件は Cell B 実観測と整合する第1候補読みとして固定する。次段では `cap_base` を観測に足す必要があるかを判断する。**

- **`room_to_soft` 軸**・**bridge 本命候補**（**`FA_BRIDGE_VS_OVER_DECISION`**）を **維持**。  
- **`cap_base` 有無**は **次の判断メモ**で **最小追加要否**を **切る**。

---

## 5. 非目的

- **コード変更**。  
- **over 枝の恒久的否定**。  
- **pushback 側へ主軸を戻すこと**。  
- **`final_offer` 側まで同時に広げること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。  
- **bridge 読みの最終断定**。

---

## 6. 次に続く実務（1つだけ）

**`cap_base` 自体を observer に最小追加する必要があるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BRIDGE_GATE_MATCH_NOTE_2026-04.md -Pattern "目的|確定事実|今回の照合|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（bridge 条件と Cell B 観測の照合・第1候補の固定）。
