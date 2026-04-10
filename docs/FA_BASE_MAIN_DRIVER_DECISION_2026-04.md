# 100M 台 offer の主因 — **base** 側を本命に置く（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **読み優先度の決裁（コード変更なし）**。observer 優先判断: `docs/FA_BASE_OR_BONUS_OUTPUT_DECISION_2026-04.md`（**先に `bonus` を足して上振れを見る**段階は **経過**）。生成式: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。内訳の焦点: `docs/FA_BASE_VS_BONUS_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **Cell B 実 save** で **`bonus` と `offer_after_base_bonus` が並んだ結果**を踏まえ、**100M 台 offer の主因が `bonus` ではなく `base` 側**である **読みを固定**し、**次段の第1焦点を `player.salary` 主体の形成**に **置く**。
- **コード変更・修正案・数学的な最終断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・分布要約レベル）**

| リーグ | `bonus`（目安） | `offer_after_base_bonus`（目安） |
|--------|-----------------|----------------------------------|
| **D2** | 約 **21.2M〜27.6M** | 約 **106M〜137.8M** |
| **D1** | 約 **22.2M〜28.8M** | 約 **110.8M〜143.9M** |

**既に固定されている読み**

- **`offer_after_base_bonus`** と **`offer_after_hard_cap_over`** は **D1 で実質一致**、**D2 でも差がごく小さい**（**hard cap 前段でほぼ完成**）。  
- **コード上** **`offer_after_base_bonus = base + bonus`**、**`base` は通常 `player.salary`**（**`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE` どおり**）。

**ここから言えること（読み）**

- **`bonus` は 2 千数百万規模**で、**合計 100M 台に対して相対的に小さい**。  
- **よって** **100M 台の骨格**は **`bonus` より `base` 側**にある **可能性が高い**（**単一原因の確定まではしない**）。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は、`bonus` ではなく `base = player.salary` 側に置く。100M 台 offer の骨格は salary 主体で形成されている可能性が高いため、次は base の水準とその分布を読む。**

- **`bonus` 主因読み**は **後順位**（**否定ではなく相対的後退**）。  
- **本命**は **`base` / salary**（**分布・典型値・FA プールとの関係**）。  
- **`FA_BASE_OR_BONUS_OUTPUT_DECISION` で先に `bonus` を観測に載せた**ことは **矛盾しない**（**上振れ要因の切り分けに寄与した**）。

---

## 4. 理由

- **観測上** **`bonus` は 100M 台に対して小さく**、**主因を説明しきれない**。  
- **`offer_after_base_bonus` と hard cap 後の差も小さい**ため、**残る大きな項は `base`** と **見るのが自然**。  
- **コード上**も **`base` が通常は salary 直結**— **次はその水準**を **読む段階**。

---

## 5. 非目的

- **コード変更**。  
- **`bonus` の恒久的否定**。  
- **hard cap 系の恒久的否定**。  
- **`final_offer` 側まで同時に主軸を広げること**。  
- **修正案の決定**。  
- **base 主因の過剰断定**（**「可能性が高い」で止める**）。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`player.salary` と `base` の関係を observer に最小追加する必要があるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_MAIN_DRIVER_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（観測に基づき base/salary を第1焦点に固定）。
