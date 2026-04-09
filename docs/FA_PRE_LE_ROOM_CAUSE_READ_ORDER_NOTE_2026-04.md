# `pre_le_room=0` の原因候補 — diagnostic の読み順（観測メモ）

**作成日**: 2026-04-08  
**性質**: **原因候補と観測順の固定（コード変更なし）**。定義の正本: `docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`。文脈: `docs/FA_OFFER_SIDE_OBSERVATION_NOTE_2026-04.md`。

---

## 1. 目的

- **`pre_le_room=0`** が **どのような状況で起きうるか**を、**`offer_after_soft_cap_pushback` と `room_to_budget` のどちら側から先に読むか**含め **観測順つき**で整理する。
- **原因の断定**や **改修方針の確定はしない**。

---

## 2. 前提整理

- **`pre_le_room`** は **`final_offer` ベースの集計ではない**（`docs/FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md`）。
- **条件**: **`soft_cap_early` が偽**かつ **`offer_after_soft_cap_pushback` と `room_to_budget` が両方 non-None** の pair について、**`int(offer_after_soft_cap_pushback) <= int(room_to_budget)`** なら **1 件加算**。
- **`pre_le_room=0`** は **上記を満たす pair が 0 件** — すなわち **対象 pair では概ね `offer_after_soft_cap_pushback > room_to_budget`**、または **比較に入らない欠損が支配的**、のいずれかを **まず疑う**。
- **`final_offer` や clip 後飽和**は **別集計** — **同時に片付けない**。

---

## 3. 原因候補の読み分け（3 のみ）

### 候補A: `room_to_budget` が小さすぎる

- **イメージ**: **予算由来の room が全体的に小さく**、**soft cap pushback 後の offer でも **`offer > room`** が並ぶ。
- **読むべき diagnostic 値**: **`room_to_budget`**（**分布・最小／最大・代表 pair**）。**`room_unique`**（observer `summary`）は **ユニーク数**の目安。

### 候補B: `offer_after_soft_cap_pushback` が大きすぎる

- **イメージ**: **room は一定あるが**、**base+bonus〜soft cap までの結果として offer 側が大きく**、**常に room を超える**。
- **読むべき diagnostic 値**: **`offer_after_soft_cap_pushback`**（**分布**）。**`room_to_budget` との大小**を **ペアで**見る。

### 候補C: 両者の相対関係の問題

- **イメージ**: **単独の「小さい／大きい」だけでは説明せず**、**ペアごとに `offer - room` が正に偏る**。**全体傾向か、極端な tail か**を分けたい。
- **読むべき値**: **差分 `offer_after_soft_cap_pushback - room_to_budget`**、**上回り幅の分布**、**外れ値の有無**。

---

## 4. 今回の判断（1 案）

**次の観測では、まず `room_to_budget` の分布を読み、そのうえで `offer_after_soft_cap_pushback` と **大小関係・差分**を読む。  
`pre_le_room=0` を **「片方だけが悪い」**と **先に断定しない**。**

- **手順の心構え**: **候補A→B→C の順で「読む優先度」を持つ**が、**実データでは C（相対）が最初に効く**場合もあるため、**分布とペア比較はセット**で見る。

---

## 5. 観測順（固定）

1. **`room_to_budget` の分布確認**（**最小・最大・ユニーク数・典型行**）。
2. **`offer_after_soft_cap_pushback` の分布確認**（**同様**）。
3. **両者の大小関係・差分**（**`offer <= room` になる pair が本当に 0 か**、**欠損スキップの割合**も **併記**）。

---

## 6. 非目的

- **コード変更**。
- **`clip` / `λ` / FA `buffer` の方針決定**。
- **`final_offer` / `final_offer > buffer` まで同時解決**。
- **原因の断定**。
- **budget 側（Cell B）の再議論**。

---

## 7. 次に続く実務（1つだけ）

**observer / diagnostic 上で、** **`room_to_budget`** と **`offer_after_soft_cap_pushback`** の **分布・大小関係**を **読むための最小手順**（**既存出力で足りるか／1 行追加が要るかは次メモで切る**）を **`docs/` に 1 本**まとめる。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PRE_LE_ROOM_CAUSE_READ_ORDER_NOTE_2026-04.md -Pattern "目的|前提整理|原因候補の読み分け|今回の判断|観測順|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（候補A〜C・観測順・断定しない判断）。
