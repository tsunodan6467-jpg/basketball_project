# `estimate_fa_market_value` と観測 salary の照合（メモ）

**作成日**: 2026-04-08  
**性質**: **入出力と観測の突き合わせ（コード変更なし）**。コードパス: `docs/FA_MARKET_VALUE_CODE_PATH_NOTE_2026-04.md`。設計焦点: `docs/FA_SALARY_DESIGN_FOCUS_DECISION_2026-04.md`。次焦点: `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agent_market.py`。

---

## 1. 目的

- **Cell B 実 save** で見えている **`player_salary`（85M〜115M 級）**が、**`estimate_fa_market_value` の出力として** **読みとして整合するか**を **短く固定**する。  
- **ペア単位の再計算・原因の最終断定・修正案はしない**。

---

## 2. 確定事実

- **Cell B・`pre_le_pop`** では **`player_salary ≒ base`**（**observer 確認済み**）。  
- **D2** で 約 **85.0M〜110.2M**、**D1** で 約 **88.7M〜115.1M**。  
- **FA 土台**は **`normalize_free_agents` → `sync_fa_pool_player_salary_to_estimate` で `estimate_fa_market_value` に揃えられる**読みが **最有力**（**`FA_MARKET_VALUE_CODE_PATH_NOTE` どおり**）。  
- **正規化時**は **`int(estimate_fa_market_value(player))` をそのまま `player.salary` に入れ**、**追加の上限・丸めは無い**。

---

## 3. 今回の照合

**式の骨格（実装どおり）**

- **`base`** の芯は **`ovr * GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**現設定 `1_220_000` 円/OVR 点**）と **レガシー床のスケール値**の **max**。  
- その上に **`potential`**・**`age`**・**`fa_years_waiting`** 由来の **加減算**（**金額は `_scale_fa_estimate_bonus` で `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` 比にスケール**）。  
- **最後に `max(MIN_SALARY_DEFAULT, …)`**（**`MIN_SALARY_DEFAULT` は 30 万円オーダー**。**観測レンジでは事実上ただちには効かない**）。

**85M〜115M 級は自然か（オーダー感）**

- **線形項だけ**で見ると **`salary ≈ ovr × 122 万円`** なので、**概ね **約 **70 点台後半〜90 点台前半の `ovr`** が **そのレンジの芯**に **対応しうる**（**逆算は目安**。**他項で数千万〜数千万円単位の上下**あり）。  
- **`potential` が S/A 等**のときは **スケール後の加算が大きく**、**同じ `ovr` でも上振れしうる**。  
- **`age`**（**若年の加算・ベテランの減算**）や **`fa_years_waiting`**（**待機年による減算**）は **主項に比べると** **相対的に小さめの修正**になりやすい（**符号・段階は実装どおり**）。

**どの入力が主に効きそうか（読み・断定ではない）**

- **主導は `ovr`**（**係数が OVR 全点に掛かる線形項**）。  
- **次点は `potential`**（**加算幅がスケール後も大きい**）。  
- **`age`・`fa_years_waiting`** は **同じレンジ内の差分**や **個体ブレ**に **効きやすい**。

**限界**

- **今回**は **team×FA の各行について `estimate` を再実行して検算したわけではない**。  
- よって **「整合的」「主に `ovr`（＋`potential`）が効きそう」**で **止める**。

---

## 4. 今回の判断（1 案）

**現時点では、Cell B の 85M〜115M 級 salary は `estimate_fa_market_value` の出力として整合的とみなし、次段ではその式の中でどの入力・係数が金額を押し上げているかを読む。**

- **年俸生成がゲーム内で唯一の原因**とは **断定しない**（**§5 非目的どおり**）。  
- **開幕ロスター・選手分布**は **まだ主軸に戻さない**（**決裁どおり後続**）。

---

## 5. 非目的

- **コード変更**。  
- **年俸生成が唯一原因**の **断定**。  
- **開幕ロスター側**への **議論の戻し**（**第2候補は別タスク**）。  
- **選手分布**への **拡張**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`estimate_fa_market_value` の中で、どの入力・係数が 85M〜115M 級に最も効いているかを読む短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_MARKET_VALUE_MATCH_NOTE_2026-04.md -Pattern "目的|確定事実|今回の照合|今回の判断|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（観測レンジと `ovr×1,220,000` 骨格のオーダー整合を記載）。
