# 次段: RATIO を比較調整に含めるか（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **決裁メモ（コード変更なし）**。根拠観測: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_RESULTS_2026-04.md`。BUFFER 優先の前段: `docs/PAYROLL_BUDGET_POSTOFF_TEMP_TUNING_DECISION_2026-04.md`、計画: `docs/PAYROLL_BUDGET_POSTOFF_BUFFER_TUNING_PLAN_2026-04.md`。

---

## 1. 目的

- **BUFFER-only 3 段階観測**の結果を受け、**次段で `TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO`（α 相当）を調整対象に含めるべきか**を **1 本に判断**する。
- **本メモは実装着手の合図ではない**。**次の観測設計**に渡す **決裁**である。

---

## 2. 確定事実（BUFFER-only 結果の要約）

- **β を 3M / 10M / 30M** とした **3 段階**で、**before の `gap_min` / `gap_max`** および **user 断面の `gap`** は **β に応じて素直に増加**した（詳細は結果表参照）。
- **3 段階すべて**で **`gap_unique=1`**、**`summary.room_unique=1` / `pre_le_room=0`**、**`final_offer > buffer = 1920/1920`** は **不変**だった。
- **D2 / D1** の **2 save** では **形が同型**だった。
- **読み取り**: **BUFFER は主に gap の「水準」を動かした**が、**当該母集団・手順では「分布の潰れ」（補助軸の `room_unique` / `pre_le_room` 等）を崩すには至らなかった**。

---

## 3. 今回の判断（1 案）

**次段では、BUFFER 単独の段階比較はいったん打ち止めとし、`RATIO`（α 相当）も **比較調整対象に含める**。**

- **`clip` / `λ` / FA 経路の `buffer`** は **引き続き別トラック**（**本決裁では触らない**）。
- **次の観測**は **多変量同時最適化にしない**。**β を固定**したうえで **α を 2〜3 段階**だけ動かす **小さな比較**に進む。
- **断定しないこと**: **α の最終値**、**即日のコード変更**、**β の最終確定**。

---

## 4. この判断の理由

- **BUFFER だけで before gap は増えた**が、**`room_unique=1` / `pre_le_room=0` は崩れなかった**。
- よって **観測上の「潰れ」を崩すには**、**ロスター規模への係り方（α 側）**も **検証対象に入れる**のが **自然**である。
- **まず α を段階的に比較**し、**チーム間で `floor_expr` の差の付き方**が **どう変わるか**を見る方が、**次の切り分けとして素直**である（**β と α を同時に振らない**）。

---

## 5. 非目的

- **本メモによるコード変更**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **α または β の最終値の断定**。
- **α と β の同時チューニング**を **次の最初の一歩**とすること。

---

## 6. 次に続く実務（1つだけ）

**β を固定したまま α を **2〜3 段階**で比較する **RATIO 観測計画メモ**を `docs/` に 1 本作成する**（**save 手順・`--apply-temp-postoff-floor` の扱い**は **BUFFER 観測時と整合**させる）。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\PAYROLL_BUDGET_POSTOFF_RATIO_DECISION_2026-04.md -Pattern "目的|確定事実|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（BUFFER-only 打ち止め・次段に RATIO 比較を含める）。
