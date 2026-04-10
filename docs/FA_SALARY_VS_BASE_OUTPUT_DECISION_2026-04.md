# `player.salary` か `base` か — observer 最小追加の優先（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否・優先の判断（コード変更なし）**。主因の決裁: `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`。生成式: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。bonus 優先判断（経過）: `docs/FA_BASE_OR_BONUS_OUTPUT_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **100M 台 offer の主因が base / salary 側**という **現在の読み**を **一段進める**ために、**observer に `player.salary` と `base` のどちらを（先に）足すか**、**両方要るか**を **1 案として切る**。
- **実装はしない**。**2 項目同時追加は今回決めない**。

---

## 2. 既存情報で分かること

- **`offer_after_base_bonus`**・**`bonus`** は **既に observer で要約**され、**合計と上乗せ**が **並べて読める**。  
- **観測**では **`bonus` は 2 千数百万規模**で **`offer_after_base_bonus` に対して小さく**、**bonus 主因読みは後退**（**`FA_BASE_MAIN_DRIVER_DECISION` どおり**）。  
- **コード上** **`base` は基本 `player.salary`**、**`salary <= 0` のときだけ ovr 下限**（**`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE` どおり**）。  
- **一方** **診断辞書の `base` と raw `player.salary` が stdout で突き合わせ**は **まだしにくい**。

---

## 3. 比較候補（2 のみ）

### 候補A: `base` を追加

- **理由**: **offer 土台そのもの**（**ボーナス前の確定値**）を **直接**見られる。**`offer_after_base_bonus` と並べれば** **`bonus` の相対寄与**（**差・比率の目安**）も **読みやすい**。  
- **弱み**: **コード上 `base` ≈ salary** が **既に明確**で、**salary との一致検証**は **単独では弱い**。

### 候補B: `player.salary` を追加

- **理由**: **`base` が本当に salary とほぼ同値か**を **行ごとに直接検証**できる。**`salary <= 0` 例外**が **母集団に混ざるか**も **見える**。  
- **弱み**: **通常 FA では `base` と重複**しやすく、**まず土台の「確定後の base」**より **一段メタ**になる。

---

## 4. 今回の判断（1 案）

**次段の最小追加は `base` を第1候補にする。理由は、offer 土台そのものを直接見られ、`offer_after_base_bonus` と並べて bonus の相対寄与も読めるから。`player.salary` は、base と乖離が疑われる段階で第2候補とする。**

- **先に 1 行だけ足すなら `base` 要約**（**母集団・位置は実装指示で確定**。**`pre_le`・`bonus` と揃える**のが **自然**）。  
- **`player.salary`** は **第2候補**（**例外経路・データ不整合疑い**で **価値が上がる**）。  
- **2 項目同時追加は今回決めない**。

---

## 5. 非目的

- **今回のメモ段階でのコード変更**。  
- **base 主因の過剰断定**。  
- **hard cap 系へ主軸を戻すこと**。  
- **`final_offer` 側まで同時に広げること**。  
- **2 項目同時追加の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**選んだ方（本判断では `base`）だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SALARY_VS_BASE_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存情報で分かること|比較候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（最小追加は `base` 第1候補、`player.salary` は第2候補）。
