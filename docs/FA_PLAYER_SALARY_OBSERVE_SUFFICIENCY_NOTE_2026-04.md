# `player.salary` 分布 — observer 出力で足りるか（判断メモ）

**作成日**: 2026-04-08  
**性質**: **観測十分性の判断（コード変更なし）**。次焦点の決裁: `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`。`player.salary` 観測判断: `docs/FA_PLAYER_SALARY_OUTPUT_DECISION_2026-04.md`。base 主因: `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`。observer: `tools/fa_offer_real_distribution_observer.py`。

---

## 1. 目的

- **`player.salary` 分布を本命として読む**にあたり、**既存の observer 出力だけで第1段の観測に足りるか**、**追加観測が要るか**を **1 案として切る**。  
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`player_salary`** は **`pre_le_pop` で min / max / p25 / p50 / p75** が **既に出ている**。  
- **`base`** も **同型で並んでおり**、**Cell B 実 save 母集団では `player_salary` と一致**した（**`FA_PLAYER_SALARY_DISTRIBUTION_DECISION` どおり**）。  
- **`bonus`**・**`offer_after_base_bonus`**・**`offer_after_hard_cap_over`**、**`payroll_before`**、**`soft_cap`**、**`room_to_soft`**（**gate 行**）も **同じ実行で読める**。  
- **したがって** **「土台が raw salary で、上乗せと hard cap 前後がどう重なるか」**という **salary 主体読み**は **かなり強い段階**にある。

---

## 3. 既存出力でまだ弱いこと

- **分位要約だけ**では、**分布の裾の形**、**特定高額帯に何件溜まっているか**、**D1 / D2 / D3 ごとの内訳**まで **一度に細かくは読めない**（**ヒストグラムや層別件数が無い**）。  
- **ただし** **次段でまず必要なのは** **「salary 分布が全体として高いかどうか」**の **荒い判断**であり、**そこに到達するために追加観測が今すぐ必須とは限らない**。

---

## 4. 追加候補（1 項目のみ）

### 候補A

- **salary 高額帯の件数**や **リーグ別（`league_level`）内訳**などの **追加観測**（**stdout に行を足すイメージ**）。  
- **今回は候補として触れるだけ**。**実装・仕様固定はしない**。

---

## 5. 今回の判断（1 案）

**現時点では、既存の `player_salary` 要約だけで「salary 分布が高いかどうか」を見る第1段の観測には概ね足りる。追加観測は、salary 高額帯件数やリーグ別差を読みたくなった段階で後続タスクとして検討する。**

- **今すぐの追加実装は不要**と **置く**（**恒久禁止ではない**）。  
- **まずは** **既存の `player_salary` 行**（**および隣接する `base` / `bonus` / `abb`**）を **材料にして読む**。  
- **足りなくなったら** **候補A** を **次タスクで検討**する。

---

## 6. 非目的

- **今回のメモ段階でのコード変更**。  
- **salary を唯一の主因と断定すること**。  
- **追加観測を今すぐ実装すること**。  
- **`final_offer` 側まで主軸を広げること**。  
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**既存の `player_salary` 要約をもとに、salary 分布が高いと言えるかを短く読む観測メモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PLAYER_SALARY_OBSERVE_SUFFICIENCY_NOTE_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（既存 `player_salary` 要約で第1段は概ね十分と判断）。
