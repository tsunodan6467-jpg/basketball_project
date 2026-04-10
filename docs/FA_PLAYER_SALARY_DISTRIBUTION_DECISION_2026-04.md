# 次焦点 — **`player.salary` 分布**（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **読み優先度の決裁（コード変更なし）**。前段の次焦点: `docs/FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md`。base 主因の固定: `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`。`player.salary` 観測判断: `docs/FA_PLAYER_SALARY_OUTPUT_DECISION_2026-04.md`。observer: `tools/fa_offer_real_distribution_observer.py`。生成式: `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`。

---

## 1. 目的

- **Cell B 実 save** で **`player_salary` と `base` が一致した結果**を踏まえ、**100M 台 offer の本命を `player.salary` 分布**へ **一段はっきり移す**決裁メモである。  
- **コード変更・修正案・単一原因の最終断定はしない**。

---

## 2. 確定事実

**観測（Cell B 実 save・`pre_le_pop` 母集団・分布要約レベル）**

| リーグ | `base`（目安） | `bonus`（目安） | `offer_after_base_bonus`（目安） |
|--------|----------------|-----------------|----------------------------------|
| **D2** | 約 **85M〜115M 級** | 約 **21M〜29M 級** | 約 **107M〜138M 級** |
| **D1** | 約 **89M〜115M 級** | 約 **22M〜29M 級** | 約 **111M〜144M 級** |

**今回の新しい確認**

- **D2**・**D1** とも **`player_salary` と `base` の min / max / p25 / p50 / p75 がすべて一致**（**observer 出力で確認**）。  
- **よってこの母集団では** **`salary <= 0` の例外経路は実質効いておらず**、**`base` は raw `player.salary` と一致**する **読みが自然**（**他母集団・全期間への外挿まではしない**）。

**ここから言えること（読み）**

- **100M 台 offer の土台**は、**少なくともこの Cell B 実 save では** **そのまま `player.salary`** と **整理するのが自然**。  
- **骨格が bonus 側ではない**という **既決の読み**とも **矛盾しない**。

---

## 3. 今回の判断（1 案）

**次段の第1焦点は、offer ロジック後段ではなく `player.salary` 分布そのものに置く。まずは salary 水準・分布が高いのかを読み、その後必要なら salary 生成や契約設計へ降りる。**

- **`bonus` 主因読み**・**hard cap 後段の主因読み**は **後順位**（**恒久否定ではない**）。  
- **本命**は **`player.salary` の水準と分布**（**FA プール・シーズン経路との関係はこのメモでは断定しない**）。  
- **原因の一本化**（**「salary が唯一の主因」**など）は **まだしない**が、**調査の優先順位は salary 側へ明確に移す**。

---

## 4. 理由

- **観測上** **`base` が offer の大半を作っており**、**`bonus` は上乗せに留まる**（**既存決裁どおり**）。  
- **同一母集団で** **`player_salary` と `base` が一致**したため、**土台は raw salary** と **見るのが最短**。  
- **なら次に見るべきは** **salary がなぜその水準にあるか**（**分布・生成・契約**）であって、**同じことを offer 式の後段だけで繰り返しても効率が落ちる**。

---

## 5. 非目的

- **コード変更**。  
- **`bonus` の恒久的否定**。  
- **hard cap 系の恒久的否定**。  
- **`final_offer` 側まで主軸を同時に広げること**。  
- **修正案の決定**。  
- **「salary が唯一の主因」の過剰断定**。  
- **budget 側へ議論を戻すこと**。

---

## 6. 次に続く実務（1つだけ）

**`player.salary` 分布を observer で読むために、追加観測が必要か、既存出力で足りるかを判断する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（次焦点を `player.salary` 分布へ固定）。
