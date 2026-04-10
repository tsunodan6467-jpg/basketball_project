# hard cap **bridge** vs **over** — どちらを本命として読むか（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **読み優先度の決裁（コード変更なし）**。`low_cost_limit` パス: `docs/FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE_2026-04.md`。他制約の次焦点: `docs/FA_HARD_CAP_OTHER_LIMITS_DECISION_2026-04.md`。`room_to_soft` 照合: `docs/FA_ROOM_TO_SOFT_MATCH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **Cell B 実 save 観測**と **`free_agency.py` の bridge / over 式**を **突き合わせ**、**次段でどちらの枝を本命として読むか**を **1 案で固定**する。
- **コード変更・修正案・単一原因の断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・D2 / D1・分布要約レベル）**

| 指標 | D2（目安） | D1（目安） |
|------|------------|------------|
| **`room_to_soft`** | 約 108M〜612M | 約 152M〜503M |
| **`offer_after_hard_cap_over`** | 約 106M〜138M | 約 111M〜144M |
| **`payroll_after_pre_soft_pushback` max** | **1.2B（= `soft_cap`）** | **約 1.191B 台** |

**コード（over 枝・`FA_HARD_CAP_LOW_COST_LIMIT_CODE_PATH_NOTE` どおり）**

- **`low_cost_limit = min(max(base, 0), 900_000)`** → **上限は 900,000**。  
- over 真枝では **`offer = min(offer, room_to_soft, low_cost_limit)`**。

**整合の読み**

- **観測の `offer_after_hard_cap_over`（100M 台）**と **over 枝の `low_cost_limit`（最大 90 万）**が **同時に「支配」**していると見るのは **噛み合いにくい**（**`low_cost_limit` が効けば offer は 90 万以下に抑えられる**）。  
- **一方** **bridge 枝**は **`offer = min(offer, room_to_soft)` のみ**（**`low_cost_limit` なし**）— **100M 台の offer と `room_to_soft` 100M〜600M 級**は **整合しやすい**。  
- **よって** **今の母集団では** **over より bridge が主に効いている可能性が高い**（**`hard_cap_over_applied` 等の直接集計までは本メモの前提に含めない**）。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は over 枝そのものではなく、bridge 枝が主に効いて `room_to_soft` により soft cap 直前停止を作っている可能性に置く。over 枝の `low_cost_limit` は補助的・例外的な候補として後順位に下げる。**

- **`room_to_soft` を軸にした読みは維持**（**撤回しない**）。  
- **実装枝の本命候補**は **bridge を第1**、**over（と `low_cost_limit`）を第2**。  
- **over 枝を永久否定はしない**（**母集団・リーグ・行によっては over が効く余地**は **コード上残る**）。  
- **最終断定は** **`hard_cap_bridge_applied` / `hard_cap_over_applied` の観測追加や行別突合**の **後**に **委ねる**。

---

## 4. 理由

- **`low_cost_limit`（≤900k）**と **観測 offer（~100M）**の **ギャップ**が **大きい**。  
- **bridge** なら **`min(offer, room_to_soft)` だけ**で **観測レンジと矛盾しにくい**。  
- **D2 の `payroll_after_pre_soft_pushback max = soft_cap`** は **`room_to_soft` 説明**と **引き続き整合**する。

---

## 5. 非目的

- **コード変更**。  
- **`room_to_soft` 第1説明軸の撤回**。  
- **pushback 側へ主軸を戻すこと**。  
- **`final_offer` 側まで同時に広げること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。  
- **over 枝の恒久的否定**（**優先度の入れ替えにとどめる**）。

---

## 6. 次に続く実務（1つだけ）

**bridge 枝に入る条件（`payroll_before <= cap_base < payroll_after`）と Cell B 実観測の整合を読む短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BRIDGE_VS_OVER_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（bridge 本命候補・over/`low_cost_limit` 後順位の固定）。
