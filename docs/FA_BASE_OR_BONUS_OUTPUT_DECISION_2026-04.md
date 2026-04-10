# `base` か `bonus` か — observer 最小追加の優先（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加優先の判断（コード変更なし）**。次焦点: `docs/FA_BASE_VS_BONUS_DECISION_2026-04.md`。生成順: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。`offer_after_base_bonus` 判断: `docs/FA_BASE_BONUS_OUTPUT_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **100M 台 offer** の **主因が `base` か `bonus` か**を **観測で切る**うえで、**observer に最小 1 項目足すならどちらを先に出すか**を **1 案として切る**。
- **実装はしない**。**主因の断定はしない**。

---

## 2. 既存情報で分かること

- **`offer_after_base_bonus`** は **既に observer で要約**され、**D1/D2 で 100M 台**・**`offer_after_hard_cap_over` とほぼ一致**することが **読める**（**前段でほぼ完成**の **読み**）。  
- **`base` / `bonus` の生成式**（**salary / ovr 下限**、**surplus・5%・25% キャップ**）は **コード読解で固定済み**（**`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE`**）。  
- **一方**、**実観測の stdout** では **`base` と `bonus` の数値そのもの**は **まだ並ばない**。**内訳の直接比較**は **しにくい**。

---

## 3. 比較候補（2 のみ）

### 候補A: `base` を追加

- **理由**: **土台の絶対額**が **一目で分かる**。**FA の salary 主体**なら **主因判定に直結**しやすい。  
- **弱み**: **コード上すでに `base ≈ player.salary`（または ovr 下限）**と **かなり明示**されており、**「なぜ 100M なのか」の説明**は **多くが salary 側に寄る**可能性があり、**追加の新情報**が **相対的に薄い**場合がある。

### 候補B: `bonus` を追加

- **理由**: **`surplus` / `team.money` 由来の上乗せ**が **どの程度効いているか**を **直接見られる**。**`base` に対する比率**・**キャップ前後の体感**を **`offer_after_base_bonus` 行と並べて**読みやすい。  
- **弱み**: **`bonus` は `base` に依存**するため、**単独解釈**は **`base` なしだとやや弱い**（**ただし合計行は既にある**）。

---

## 4. 今回の判断（1 案）

**次段の最小追加は `bonus` を第1候補にする。理由は、`base` は salary 主体であることが既にコード上かなり明確で、100M 台形成の「上振れ要因」を切るには `bonus` を直接見る価値が高いから。**

- **先に 1 行だけ足すなら `bonus` 要約**（**母集団・出し方は実装指示で確定**。**`pre_le` と `offer_after_base_bonus` に揃える**のが **自然**）。  
- **`base` は第2候補**（**salary 分布を疑う段**や **`bonus` が小さいのに合計が大きい**等の **矛盾検知**で **価値が上がる**）。  
- **2 項目同時追加は今回決めない**（**`FA_BASE_VS_BONUS_DECISION` の「まず内訳」に対し、段階的に 1 項目**）。

---

## 5. 非目的

- **今回のメモ段階でのコード変更**。  
- **`base` / `bonus` 主因の最終断定**。  
- **hard cap 系へ議論の主軸を戻すこと**。  
- **`final_offer` 側まで同時に広げること**。  
- **2 項目同時追加の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**選んだ方（本判断では `bonus`）だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_OR_BONUS_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存情報で分かること|比較候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（最小追加は `bonus` 第1候補）。
