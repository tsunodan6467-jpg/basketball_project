# `offer_after_hard_cap_over` — `free_agency.py` 上のコードパス（読み先固定）

**作成日**: 2026-04-08  
**性質**: **コード読解メモ（コード変更なし）**。直前停止の候補整理: `docs/FA_HARD_CAP_OVER_STOP_REASON_NOTE_2026-04.md`。ゲート未到達: `docs/FA_SOFT_CAP_GATE_UNREACHED_DECISION_2026-04.md`。soft cap pushback パス対照: `docs/FA_SOFT_CAP_PUSHBACK_CODE_PATH_NOTE_2026-04.md`。前後キー: `docs/FA_PUSHBACK_BEFORE_AFTER_KEY_MAPPING_NOTE_2026-04.md`。実装: `basketball_sim/systems/free_agency.py`。

---

## 1. 目的

- **`offer_after_hard_cap_over` がどの式・分岐で決まるか**を **`free_agency.py` 上で読み先として固定**し、**soft cap 直前停止**（`docs/FA_HARD_CAP_OVER_STOP_REASON_NOTE_2026-04.md` の候補 A/B）を **コードで追う入口**にする。
- **修正案・原因断定はしない**。

---

## 2. 対象関数

| 優先度 | 関数 | 役割 |
|--------|------|------|
| **主** | **`_calculate_offer_diagnostic`** | **`snap["offer_after_hard_cap_bridge"]`** / **`snap["offer_after_hard_cap_over"]`** および **`room_to_soft_*`** 等が **ここで取れる**。行番号は **本メモ記載時点のファイル**を指す。 |
| **対照** | **`_calculate_offer`** | **本番 offer**。**bridge / over の `if` と `min(...)` は diagnostic と同一**（docstring どおり）。**`offer_after_*` キーは無い**ため **段の対応は diagnostic で見る**。 |

**前提**: **`payroll_before >= soft_cap`** のときは **早期 return**（diagnostic は **`soft_cap_early`** で終了）。**hard cap bridge / over は通らない**。

---

## 3. コードパスの読み先（3 のみ）

### 読み先A: `offer_after_hard_cap_over` の代入

- **ファイル**: `basketball_sim/systems/free_agency.py`
- **`_calculate_offer_diagnostic`**: **`snap["offer_after_hard_cap_over"] = offer`**（**約 L331**）。
- **右辺の式**: **`offer` 変数の参照のみ**。**この行自体に `min` / clamp は無い**。**上限制御**は **すべて直前までの `offer` 更新**に **内包**される。
- **変数の流れ**: 局所 **`offer`** が **`offer_after_base_bonus`（`base + bonus`）** → **bridge 通過後** → **over 通過後** と **順に上書き**され、**最後の値**が **`offer_after_hard_cap_over`** になる。

### 読み先B: 直前の hard cap bridge / over 分岐

- **bridge（hard cap 未超〜跨ぎ）**  
  - **条件**: **`if payroll_before <= cap_base < payroll_after:`**（**約 L310**）。**`payroll_after`** は **この時点では `payroll_before + offer`（初期合成）**。  
  - **真枝**: **`room_to_soft = max(0, soft_cap - payroll_before)`** → **`offer = min(offer, room_to_soft)`**。**`snap["offer_after_hard_cap_bridge"]`** は **この直後（約 L318）**。  
  - **偽枝**: bridge はスキップ。**`offer` は base+bonus のまま**。
- **over（すでに hard cap 超え）**  
  - **条件**: **`if payroll_before > cap_base:`**（**約 L320**）。**bridge とは別の `if`**（**両方評価されうる**が、**通常は排他的**になりやすい）。  
  - **真枝**: **`room_to_soft = max(0, soft_cap - payroll_before)`**、**`low_cost_limit = min(max(base, 0), 900_000)`** → **`offer = min(offer, room_to_soft, low_cost_limit)`**。**snap** に **`hard_cap_over_applied`**・**`room_to_soft_over`**・**`low_cost_limit`**（**約 L324–L326**）。  
  - **偽枝**: over 未適用。**`offer` は bridge 後の値のまま**。
- **補助**: **`offer_after_hard_cap_bridge`**（**約 L318**）で **bridge 直後**の **`offer`** を **切り出し確認**できる。

### 読み先C: `soft_cap - payroll_before` 相当との結びつき

- **直接ある**。**bridge 真枝・over 真枝の両方**で **`room_to_soft = max(0, soft_cap - payroll_before)`**（**約 L311・L321**）。  
- **`offer_after_hard_cap_over` に至る `offer`** は、**該当枝に入った場合** **`min(..., room_to_soft, ...)` により** **`payroll_before + offer <= soft_cap`** になるよう **抑えられる**（**整数・`max(0, …)` のため「ぴったり soft cap」も起こりうる**）。  
- **pushback ゲート**（**約 L335 `if payroll_after > soft_cap:`**）は **この後**。**`>` のみ**（**`==` は偽**）。

---

## 4. 今回の整理

**「soft cap 直前で止まる」構造を追うときは、(A) L331 の代入はスナップのみなので、(B) 直前の L310–L326 の bridge / over で `offer` がどこまで `room_to_soft` で切られているかを読み、(C) `room_to_soft` が `soft_cap - payroll_before` 由来であることを踏まえて `payroll_before + offer` と soft cap の関係までつなげる。順序は A→B→C で足りる。いまの段階では観測・コードの一致まででよく、単一原因は断定しない。**

---

## 5. 非目的

- **コード変更**。
- **修正案の決定**。
- **pushback 本体の再説明に主眼を戻すこと**（**参照は突合のために触れる程度**）。
- **`final_offer`・贅沢税・budget clip まで同時に片付けること**。

---

## 6. 次に続く実務（1つだけ）

**拾った生成式 / 分岐と、Cell B 実 save の `soft_cap=1.2B`・`payroll_after_pre_soft_pushback max=1.2B` を照合する短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_HARD_CAP_OVER_CODE_PATH_NOTE_2026-04.md -Pattern "目的|対象関数|コードパスの読み先|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`offer_after_hard_cap_over` 代入・bridge/over・`room_to_soft` の固定）。
