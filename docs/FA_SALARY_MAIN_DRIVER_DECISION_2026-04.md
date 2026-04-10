# 次焦点 — **`player.salary` / salary 分布**（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **読み優先度の決裁（コード変更なし）**。base 主因の固定: `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`。observer での `base` 追加判断: `docs/FA_SALARY_VS_BASE_OUTPUT_DECISION_2026-04.md`。生成式: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **Cell B 実 save** で **`base`・`bonus`・`offer_after_base_bonus` が並んだ結果**を踏まえ、**100M 台 offer の骨格が base 側**という **読みを維持したうえで**、**次段の第1焦点を `player.salary` および salary 分布**に **置く**。
- **`player.salary` が診断上の `base` と実質一致しているか**を **確認対象として明示**し、**salary 水準そのものが高すぎないか**を **次に見る**。**コード変更・修正案・最終断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・分布要約レベル）**

| リーグ | `base`（目安） | `bonus`（目安） | `offer_after_base_bonus`（目安） |
|--------|----------------|-----------------|----------------------------------|
| **D2** | 約 **85.0M〜110.2M** | 約 **21.2M〜27.6M** | 約 **106.2M〜137.8M** |
| **D1** | 約 **88.7M〜115.1M** | 約 **22.2M〜28.8M** | 約 **110.8M〜143.9M** |

**コード上（`FA_BASE_BONUS_BUILD_CODE_PATH_NOTE` どおり）**

- **`base`** は **通常 `int(player.salary)`**。**`salary <= 0` のときのみ** **`max(ovr×10k, 300k)`** に置換。  
- **`bonus`** は **上乗せ**。**`offer_after_base_bonus = base + bonus`**。

**ここから言えること（読み・断定まではしない）**

- **100M 台の芯**は **`bonus` 単体では説明しきれず**、**`base` 側の寄与が大きい**読みが **観測と整合**する。  
- **コード上** **通常経路では `base` と `player.salary` は同一ソース**— **次に検証すべきは salary 側**。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は、`bonus` ではなく `player.salary` / salary 分布に置く。まず `player.salary` が診断の `base` と実質一致しているかを確認し、そのうえで salary 水準・分布そのものが高すぎないかを見る。**

- **base 主因読み**（**骨格は base 側**）は **維持**。  
- **焦点の移動**は **「次に何を数字で突き合わせるか」** の話であり、**bonus や hard cap を恒久的に否定するものではない**。  
- **`base` を observer に載せた**ことは **矛盾しない**（**土台の要約が見える段階になったうえで**、**raw salary との一致・母集団の水準**へ進む）。

---

## 4. 理由

- **観測上** **`base` が 85M〜115M 級**で **`offer_after_base_bonus` の大半を占め**、**`bonus` は 21M〜29M 級の上乗せに留まる**。  
- **`offer_after_base_bonus` 時点で 100M 台はほぼ完成**という **既決の読み**と **整合**する。  
- **コード上** **`base` は通常 `player.salary`**— **骨格が base 側なら**、**次は salary の実値・分布を見るのが最短**。

---

## 5. 非目的

- **コード変更**。  
- **`bonus` の恒久的否定**。  
- **hard cap 系の恒久的否定**。  
- **`final_offer` 側まで主軸を広げること**。  
- **修正案の決定**。  
- **「salary が唯一の主因」などの過剰断定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`player.salary` を observer に最小追加する必要があるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（次焦点を `player.salary` / salary 分布へ移す決裁）。
