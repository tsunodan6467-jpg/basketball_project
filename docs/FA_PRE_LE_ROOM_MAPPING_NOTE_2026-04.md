# `pre_le_room` と observer `summary` 行の対応（実装紐づけ）

**作成日**: 2026-04-08  
**性質**: **対応関係の固定（コード変更なし）**。文脈: `docs/FA_OFFER_SIDE_OBSERVATION_NOTE_2026-04.md`。

---

## 1. 目的

- observer が **`summary:` 行で出す `pre_le_room`** が、**どの集計・どの診断キー**に対応するかを **`fa_offer_real_distribution_observer.py` の実装に即して**固定する。
- **良し悪しや改修方針は決めない**（**意味の固定のみ**）。

---

## 2. 対応箇所

| 項目 | 内容 |
|------|------|
| **ファイル** | `tools/fa_offer_real_distribution_observer.py` |
| **関数** | **`_matrix_summary_line`**（`summary:` 1 行を組み立てる） |
| **入力** | **`_run_matrix`** が返す `rows`。各要素は **`_calculate_offer_diagnostic`（`free_agency`）** の戻りを **`diag`** キーに保持。 |
| **出力に出る行** | `print(_matrix_summary_line(rows))` により、**ヒストグラム直前**の **`summary: ... room_unique=... pre_le_room=...`** |

**集計変数**: 関数内ローカル **`pre_le`**（ループで増分）→ 文字列では **`pre_le_room=`** として出力。

---

## 3. 何を比較しているか

**対象行**: **`soft_cap_early` が偽**の (team, FA) のみ（**`soft_cap_early` 真の行はスキップ**）。

**比較する値**（いずれも **`diag` = `_calculate_offer_diagnostic` の辞書**から取得）:

| 変数（コード上） | 診断キー | 意味（段階の目安） |
|------------------|----------|-------------------|
| **`o`** | **`offer_after_soft_cap_pushback`** | **soft cap 押し戻し適用後**の offer。**`_clip_offer_to_payroll_budget`（payroll_budget clip）より前**のスナップショット。 |
| **`rtb`** | **`room_to_budget`** | **`_clip_offer_to_payroll_budget` 呼び出しの戻り値**として diagnostic に格納される **room**（**`free_agency._calculate_offer_diagnostic` 内で clip ステップと同時にセット**）。 |

**条件**: **`o` と `rtb` の両方が非 `None`** のときだけ件数に入る。  
**カウント**: **`int(o) <= int(rtb)`** なら **`pre_le` を 1 増やす**。

**`final_offer` との関係**: **`pre_le_room` は `diag["final_offer"]` とは比較していない**。**`final_offer` は budget clip・贅沢税処理などの後段**（同一 diagnostic 内の別キー）。observer の **`final_offer > buffer` 等は `_aggregate`** 側で **`final_offer` を数えている**。

---

## 4. 今回の整理

- **`pre_le_room=0`** は、**上記の定義で数えた「`offer_after_soft_cap_pushback <= room_to_budget` かつ `soft_cap_early` でない pair」の件数が 0**という意味に **固定**する。
- **clip 後の最終 offer そのもの**との比較 **ではない**（**後段の飽和**は **`pre_le_room` だけでは読めない**）。

---

## 5. 非目的

- **コード変更**。
- **原因の断定**や **解決策の決定**。
- **`final_offer` / `final_offer > buffer`** の同時整理（**別ステップ**）。

---

## 6. 次に続く実務（1つだけ）

**`pre_le_room=0` となりうる **原因候補**を、**diagnostic のどの段階値**（例: `offer_after_soft_cap_pushback` の分布、`room_to_budget` の分布、欠損スキップの有無）から **読むべきか**を整理する **短いメモ**を **`docs/` に 1 本**作成する。

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_PRE_LE_ROOM_MAPPING_NOTE_2026-04.md -Pattern "目的|対応箇所|何を比較しているか|今回の整理|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（`_matrix_summary_line`・診断キー対応）。
