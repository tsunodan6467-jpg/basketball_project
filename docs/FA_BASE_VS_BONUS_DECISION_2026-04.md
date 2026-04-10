# `base` vs `bonus` — `offer_after_base_bonus` の内訳を次の本命に置く（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **次段焦点の決裁（コード変更なし）**。observer 判断: `docs/FA_BASE_BONUS_OUTPUT_DECISION_2026-04.md`。コードパス: `docs/FA_BASE_BONUS_CODE_PATH_NOTE_2026-04.md`。前段形成の決裁: `docs/FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **Cell B 実 save** で **`offer_after_base_bonus` と `offer_after_hard_cap_over` がほぼ一致**したうえで、**100M 台 offer** の **主因が `base` か `bonus` か**を **次段の第1焦点**として **固定**する。
- **コード変更・修正案・寄与の単一断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・分布要約レベル）**

| リーグ | `offer_after_base_bonus` | `offer_after_hard_cap_over` |
|--------|--------------------------|------------------------------|
| **D2** | 約 106M〜138M | 約 106M〜138M（**差はごく小さい**） |
| **D1** | **実質** | **`offer_after_hard_cap_over` と一致** |

**読み**

- **100M 台 offer** は **hard cap 前段（`base + bonus` 直後）でほぼ完成**している。  
- **hard cap bridge / over** は **主因というより微修正レベル**に **見える**（**hard cap 系を否定はしない**）。  
- **よって** **次に見るべき本丸**は **`offer_after_base_bonus = base + bonus` のうち、どちらがその水準を主に作っているか**（**内訳**）。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は、`offer_after_base_bonus` を構成する `base` と `bonus` の寄与比較に置く。hard cap 系の後段より先に、前段形成の内訳を読む。**

- **今の本命読み**は **base vs bonus**（**どちらが主因かはまだ断定しない**）。  
- **hard cap 後段**は **後順位**（**観測上は差が小さい**）。  
- **まず** **内訳を観測・突合できる形**（**`snap["base"]` / `snap["bonus"]` 等**）を **読む**。

---

## 4. 理由

- **`offer_after_base_bonus` と `offer_after_hard_cap_over` の差が小さい** → **前段でほぼ確定**の **読みが強い**。  
- **ならば** **形成値そのものの分解**（**base・bonus**）が **最短の次ステップ**。  
- **コード上**も **`bonus` は `surplus` と `base` に依存**（**`FA_BASE_BONUS_CODE_PATH_NOTE` どおり**）— **寄与の切り分け**に **向く**。

---

## 5. 非目的

- **コード変更**。  
- **hard cap 系の恒久的否定**。  
- **`final_offer` 側まで同時に主軸を広げること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。  
- **`base` / `bonus` どちらか一方の最終断定**。

---

## 6. 次に続く実務（1つだけ）

**`basketball_sim/systems/free_agency.py` で `base` と `bonus` の生成・加算順を拾う短いコード読解メモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_BASE_VS_BONUS_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（base vs bonus を次の本命焦点に固定）。
