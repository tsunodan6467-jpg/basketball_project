# `player.salary` 要約から読む — 分布は高いか（観測メモ）

**作成日**: 2026-04-08  
**性質**: **観測の読み取り（コード変更なし）**。十分性判断: `docs/FA_PLAYER_SALARY_OBSERVE_SUFFICIENCY_NOTE_2026-04.md`。次焦点の決裁: `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`。骨格・レンジの整理: `docs/FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md`。observer: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **既存の `player_salary` 要約（min / max / p25 / p50 / p75）だけ**を材料に、**salary 分布が「高い」と言えるか**、**どの程度まで言えるか**を **短く固定**する。  
- **コード変更・修正案・最終断定はしない**。

---

## 2. 確定事実

**Cell B 実 save・`pre_le_pop` 母集団・observer 出力ベース**

- **`player_salary` と `base` は一致**（**min / max / p25 / p50 / p75 いずれも**。**`FA_PLAYER_SALARY_DISTRIBUTION_DECISION` どおり**）。  
- **D2** の **`player_salary`** は 約 **85.0M〜110.2M**。  
- **D1** の **`player_salary`** は 約 **88.7M〜115.1M**。  
- **`bonus`** は **D1/D2 とも約 21M〜29M 級**。  
- **`offer_after_base_bonus`** は **約 107M〜144M 級**（**D2 下限寄り〜D1 上限寄りの帯として読む**）。

---

## 3. 今回の読解

- **`player_salary` 自体**が、**この観測では** すでに **約8.5千万〜1.15億円級**（**上記 min/max のオーダー**）に **乗っている**。  
- **その上に `bonus` が 2 千数百万円規模で乗る**ため、**合計が 1 億円台前半〜中盤（100M 台）に乗る**のは **足し算として自然**。  
- **第1段の観測**としては、**salary 分布そのものがかなり高い**と **読むのが自然**（**「高い」の基準は「FA offer の土台として 1 億近いオーダーが典型レンジに入っている」という実務目線**）。

**ただし**

- **分布の裾**や **特定高額帯の件数**は **この要約だけでは見ていない**。  
- **D1 / D2 / D3 を同粒度で横並び**にした **全体比較**も **まだ細かくはしていない**（**今回の数値は主に Cell B・D1/D2 観測**）。  
- よって **「かなり高い」「第1段としては十分読める」**で **止める**。**単一原因の確定や恒久結論にはしない**。

---

## 4. 今回の判断（1 案）

**既存の `player_salary` 要約だけでも、少なくとも Cell B 実 save については salary 分布が高いと読むには十分である。したがって次段は、salary 分布が高いという前提で、必要なら高額帯件数やリーグ別差へ進む。**

- **`bonus` / hard cap の恒久否定**ではない（**あくまで読みの順序と材料**の話）。  
- **次に何を足すか**は **別メモで切る**。

---

## 5. 非目的

- **コード変更**。  
- **salary を唯一の主因と断定すること**。  
- **`bonus` / hard cap の恒久的否定**。  
- **高額帯件数などの追加実装に、今すぐ着手すること**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**salary の高額帯件数やリーグ別差が本当に必要かを切る短い判断メモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PLAYER_SALARY_READ_NOTE_2026-04.md -Pattern "目的|確定事実|今回の読解|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`player_salary` 要約から第1段の「高さ」を読む）。
