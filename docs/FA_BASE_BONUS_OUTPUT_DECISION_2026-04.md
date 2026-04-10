# `offer_after_base_bonus` — observer への観測追加要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **追加要否の判断（コード変更なし）**。コードパス: `docs/FA_BASE_BONUS_CODE_PATH_NOTE_2026-04.md`。次焦点の決裁: `docs/FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md`。bridge 照合: `docs/FA_BRIDGE_GATE_MATCH_NOTE_2026-04.md`。実装参照: `tools/fa_offer_real_distribution_observer.py`、**`basketball_sim/systems/free_agency.py`**。

---

## 1. 目的

- **hard cap 前の offer 形成**を **本命として読む**うえで、**`offer_after_base_bonus` を observer に足す必要があるか**を **1 案として切る**。
- **実装はしない**。

---

## 2. 既存出力で分かること

- **`offer_after_hard_cap_over`**・**`payroll_after_pre_soft_pushback`**・**`payroll_before`**・**`soft_cap`**・**`room_to_soft`**・**`cap_base`** 等が **`pre_le_pop` / gate 系**で **読める**（**実装済み想定**）。
- **hard cap 後〜pushback 手前**の **offer / payroll の関係**までは **かなり追える**。
- **一方**、**`base + bonus` 直後**の **額そのもの**（**診断キー `offer_after_base_bonus`**）は **標準出力に無い**。**hard cap 前の「形成値」はまだ見えていない**。

---

## 3. 既存出力でまだ弱いこと

- **100M 台 offer** が **形成段でほぼ完成している**のか、**hard cap bridge / over で大きく変わっている**のかを **同一ブロック内で直接は切れない**（**差分は推論に寄せがち**）。
- **`FA_PRE_HARD_CAP_FORMATION_DECISION` で第1焦点を前段に移した**以上、**その仮説の「直接確認」**には **`offer_after_base_bonus` が無いと不利**。

---

## 4. 追加候補（1 のみ）

### 候補A: `offer_after_base_bonus` の要約

- **意味**: **診断辞書の `offer_after_base_bonus`**（**`base + bonus` 直後・bridge より前**）を **`pre_le_pop` 母集団**（**既存の `n` と揃える**のが **解釈上一貫**）で **1 行要約**。  
- **出し方**: **実質一定**なら **`value=`**。**分布あり**なら **`min` / `max` / `p25` / `p50` / `p75`** 程度（**`offer_after_hard_cap_over` 行と同型でよい**）。**長い列挙は不要**。  
- **母集団の切り方**は **実装指示で確定**（**gate ではなく pre_le 全体**が **自然**）。

---

## 5. 今回の判断（1 案）

**hard cap 前の形成を本命として読むなら、`offer_after_base_bonus` を 1 行だけ observer に追加する価値が高い。これにより、100M 台 offer が形成段でほぼ出来上がっているのかを直接確認しやすくなる。**

- **必須ではないが有益**（**前段本命読みの検証コストが下がる**）。  
- **追加するなら `offer_after_base_bonus` のみ**（**2 項目目以降は広げない**）。

---

## 6. 非目的

- **今回のメモ段階でのコード変更**。  
- **hard cap 系の恒久的否定**。  
- **`final_offer` 側まで主軸を広げること**。  
- **2 項目以上を主軸にすること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`offer_after_base_bonus` だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_BONUS_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存出力で分かること|既存出力でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`offer_after_base_bonus` 観測 1 行追加の価値あり）。
