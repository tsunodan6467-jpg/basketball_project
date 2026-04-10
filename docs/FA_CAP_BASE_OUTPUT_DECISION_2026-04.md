# `cap_base` — observer への観測追加要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。bridge 照合: `docs/FA_BRIDGE_GATE_MATCH_NOTE_2026-04.md`。bridge vs over: `docs/FA_BRIDGE_VS_OVER_DECISION_2026-04.md`。`room_to_soft`: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。実装参照: `tools/fa_offer_real_distribution_observer.py`、**`basketball_sim/systems/free_agency.py`**（**`_hard_cap(team)` → `cap_base`**）。

---

## 1. 目的

- **hard cap bridge 条件**（**`payroll_before <= cap_base < payroll_after`**）の読解を **一段進める**ために、**`cap_base` 自体を observer に足す必要があるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`payroll_before`**・**`offer_after_hard_cap_over`**・**`payroll_after_pre_soft_pushback`**・**`soft_cap`**・**`room_to_soft`** が **`pre_le_pop` 系**で **読める**（**実装済み想定**）。
- **`payroll_after_pre_soft_pushback = payroll_before + offer_after_hard_cap_over`**（**キー対応どおり**）まで **突合**できる。
- **`offer_after_hard_cap_over <= room_to_soft`**・**合成 payroll の soft cap 以下**など、**bridge＋`room_to_soft` 読み**は **かなり強く整合**（**`FA_BRIDGE_GATE_MATCH_NOTE` どおり**）。

---

## 3. 既存出力でまだ弱いこと

- **`cap_base`**（**hard cap 閾値**）が **stdout に無い**。  
- **よって** **`payroll_before <= cap_base < payroll_after`**（**`payroll_after` は bridge 判定時点の `payroll_before + offer`、base+bonus 直後**）の **真偽を行ごとに直接は追えない**。  
- **bridge 読みは有力だが**、**条件式の「中点」に相当する観測が 1 枚足りない**（**推論・外挿に寄せがち**）。

---

## 4. 追加候補（1 のみ）

### 候補A: `cap_base` の要約

- **意味**: **診断辞書の `cap_base`**（**`_hard_cap(team)`**）を **gate 母集団（`n_gate` と揃える）**で **1 行要約**。  
- **出し方**: **リーグ内で実質一定**なら **`value=`**。**複数値**なら **`min` / `max` / `unique`** 程度（**長い分布は不要**）。  
- **目的**: **bridge 条件の左・中・右**を **同じブロックで並べて読む**（**実装指示で位置・母集団を確定**）。

---

## 5. 今回の判断（1 案）

**bridge 読みは既存出力だけでもかなり強いが、`cap_base` を 1 行だけ追加すると `payroll_before <= cap_base < payroll_after` の整合を直接読みやすくなる。したがって、次段で `cap_base` 1 行を最小追加する価値がある。**

- **必須ではないが有益**（**「直接証拠」1 枚**）。  
- **追加するなら `cap_base` のみ**（**2 項目目以降は広げない**）。

---

## 6. 非目的

- **今回のメモ段階でのコード変更**。  
- **over 側へ主軸を戻すこと**。  
- **`final_offer` 側まで広げること**。  
- **2 項目以上を主軸にすること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`cap_base` だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_CAP_BASE_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`cap_base` 観測 1 行追加の価値あり）。
