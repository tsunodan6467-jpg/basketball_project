# `offer_after_soft_cap_pushback` 高止まり — 原因候補（観測メモ）

**作成日**: 2026-04-08  
**性質**: **原因候補と観測順の固定（コード変更なし）**。`pre_le_room` 定義: `docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`。読み順の前段: `docs/FA_PRE_LE_ROOM_CAUSE_READ_ORDER_NOTE_2026-04.md`。観測: `docs/FA_ROOM_TO_BUDGET_AND_PUSHBACK_OBSERVE_NOTE_2026-04.md`、出力: `docs/FA_OBSERVER_OUTPUT_SUFFICIENCY_NOTE_2026-04.md`（**`pre_le_pop`**）。

---

## 1. 目的

- **`offer_after_soft_cap_pushback` が高止まりする**（**`room_to_budget` を系統的に上回る**）状況について、**原因候補を 3 つに絞って整理**する。
- **本メモは解決策メモではない**。**読み筋の固定**であり、**式変更・断定はしない**。

---

## 2. 確定事実

- **`pre_le_room=0` の直接条件**（mapping メモどおり）: **`soft_cap_early` 偽**かつ **両キー non-None** の pair で、**`int(offer_after_soft_cap_pushback) <= int(room_to_budget)`** が **0 件**であること。
- **Cell B 実 save 観測（D2 / D1）**では、**`room_to_budget` はおおむね約 40M〜65M**、**`offer_after_soft_cap_pushback` はおおむね約 106M〜144M**。**`pre_le_pop` の `offer_minus_room`** は **`le0=0`・`gt0=1920`・`gt_temp=1920`**（**全件で room を上回る**）。
- **`room_to_budget` はゼロ付近に張り付いているわけではなく**、**一定の幅**がある。
- **よって**、「**room が完全に死んでいる**」単独説より、**「pushback 後の offer がなお高く、比較段階で常に room を超える」**という読みが **`pre_le_room=0` の直接理由として有力**（**観測事実に基づく整理**。**根本原因の単一断定はしない**）。

---

## 3. 原因候補（3 のみ）

### 候補A: pushback の減衰が弱い

- **イメージ**: **soft cap pushback を通しても**、**offer が十分には下がっていない**。
- **読むべき次対象**: **pushback 前後の値の関係**、**pushback 後の残り幅**（**diagnostic 上の前後キー**）。

### 候補B: pushback 前の元 offer が高すぎる

- **イメージ**: **pushback 式そのものより**、**入力側の offer がすでに大きく**、**減衰後も room を超えやすい**。
- **読むべき次対象**: **pushback 前 offer の規模・分布**、**どの段階から大きくなっているか**（**診断パイプラインの手前から追う**）。

### 候補C: `room_to_budget` と比較する段階が強すぎる

- **イメージ**: **比較に `offer_after_soft_cap_pushback` を使うこと自体**が、**room 側より常に大きく出やすい**（**段階のミスマッチ**）。
- **読むべき次対象**: **pre-pushback / post-pushback / `final_offer` 等**の **どの段階を並べているか**（**`pre_le_room` が意図する段階**との **整合**）。

---

## 4. 今回の判断（1 案）

**次の観測は、まず `offer_after_soft_cap_pushback` の形成側を読む。具体的には、pushback の減衰が弱いのか、pushback 前の元 offer が高すぎるのかを優先して切り分ける。比較段階の妥当性はその次に確認する。**

- **まず pushback 後 offer 側**（**候補A・B**）を疑う。
- **「減衰不足」か「入力過大」か**を **先に**見る。
- **比較段階の問題**（**候補C**）は **第 2 順**。

---

## 5. 観測順の優先順位

1. **pushback 前 offer と pushback 後 offer の関係**（**候補A vs B**）。
2. **pushback 後 offer と `room_to_budget` の関係**（**既存 `pre_le_pop`・差分**の **補強**）。
3. **比較している段階そのものの妥当性**（**候補C**）。

---

## 6. 非目的

- **コード変更**。
- **pushback 式の修正方針決定**。
- **`clip` / `λ` / FA `buffer` の変更**。
- **Cell B の再比較**。
- **`final_offer` 飽和まで同時に片付けること**。

---

## 7. 次に続く実務（1つだけ）

**pushback 前 offer と pushback 後 offer の対応関係を、diagnostic のどのキーから読むか整理する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PUSHBACK_OFFER_CAUSE_NOTE_2026-04.md -Pattern "目的|確定事実|原因候補|今回の判断|観測順の優先順位|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（高止まり 3 候補・観測順）。
