# `player.salary` — observer 最小追加の要否（判断メモ）

**作成日**: 2026-04-08  
**性質**: **観測追加要否の判断（コード変更なし）**。次焦点の決裁: `docs/FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md`。過去の base 優先判断: `docs/FA_SALARY_VS_BASE_OUTPUT_DECISION_2026-04.md`。生成式: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。observer: `tools/fa_offer_real_distribution_observer.py`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **salary 主体読みを一段進める**ために、**`player.salary` を observer に最小追加する必要があるか**を **1 案として切る**。
- **実装はしない**。**追加する場合も 1 項目に限定**する。

---

## 2. 既存情報で分かること

- **`base`** は **既に observer の `pre_le_pop` 等で要約**され、**stdout で読める**（**診断辞書の `base`**）。  
- **`bonus`**・**`offer_after_base_bonus`** も **同じ母集団・近傍で要約済み**。  
- **観測上** **`base` は D1/D2 とも約 85M〜115M 級**、**`bonus` は約 21M〜29M 級**、**合計は 100M 台**— **100M 台 offer の骨格が base 側**という **読みはかなり強い**。  
- **コード上** **`base` は通常 `player.salary`**、**例外は `salary <= 0` のときだけ `max(ovr×10k, 300k)`**（**`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE` どおり**）。

---

## 3. 既存情報でまだ弱いこと

- **実観測（stdout）では `player.salary` そのものはまだ出ていない**。**診断に載るのは確定後の `base`**。  
- そのため次を **直接**は確認できない。  
  - **母集団全体で `base ≒ salary` が成り立つか**  
  - **`salary <= 0` 由来の例外が実際に混ざっているか**（**件数・分布への影響**）

---

## 4. 追加候補（1 項目のみ）

### 候補A: `player.salary` の要約

- **形式**: **固定なら単一 value**、**ばらつきがあれば min / max / p25 / p50 / p75**（**既存の `base`・`bonus` 行と同型でよい**）。  
- **目的**: **`base` と並べて**、**通常ケースでほぼ一致するか**、**例外経路の有無**を **確認する**。

---

## 5. 今回の判断（1 案）

**salary 主体読みを確かめるには、`player.salary` を 1 行だけ observer に追加する価値がある。理由は、`base` と並べて見ることで、通常ケースで `base ≒ salary` が成り立つか、例外経路が実際に混ざるかを直接確認できるから。**

- **既存の `base`・`bonus`・`offer_after_base_bonus` だけでも**、**骨格が base 側**という **読み自体はかなり立つ**。  
- よって **`player.salary` は「必須」ではなく**、**確認価値が高い最小追加**として位置づける。  
- **`FA_SALARY_VS_BASE_OUTPUT_DECISION` で先に `base` を載せた**ことと **矛盾しない**（**土台が見えたうえでの raw 突き合わせ**）。

---

## 6. 非目的

- **今回のメモ段階でのコード変更**。  
- **salary を唯一の主因と断定すること**。  
- **`bonus` の恒久的否定**。  
- **hard cap 系へ主軸を戻すこと**。  
- **2 項目以上の同時追加を今回決めること**。  
- **実装指示・修正案の具体化**。  
- **budget 側へ議論を戻すこと**。

---

## 7. 次に続く実務（1つだけ）

**`player.salary` だけを observer に最小追加する実装指示書を作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PLAYER_SALARY_OUTPUT_DECISION_2026-04.md -Pattern "目的|既存情報で分かること|既存情報でまだ弱いこと|追加候補|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`player.salary` 1 行追加は確認価値が高い最小追加と判断）。
