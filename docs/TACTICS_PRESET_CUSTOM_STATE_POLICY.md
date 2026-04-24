# 戦術メニュー — プリセット・手動変更・「カスタム」表示（実装照合メモ）

**位置づけ**: `basketball_sim/systems/team_tactics.py` / `main_menu_view.py` の**現行挙動**に沿って整理。断定できない挙動（試合エンジン全経路の参照など）は **未確認** として分離する。

---

## 1. 現状の UI 概要（プレイスタイル / ローテーションの各ブロック）

戦術ハブ（`open_strategy_window`）は **「プレイスタイル」「ローテーション」** の2枠構成。各枠内に、従来どおり**複数のサブ窓**（`_open_tactics_*`）がぶら下がる。

| 枠 | 主な導線（窓） | 保存先の要約 |
|----|----------------|--------------|
| **プレイスタイル** | 基本方針（`Team`）、攻守の傾向（`team_strategy`）、セット傾向（`playbook`） | プリセットは **3 定義**（`PLAYSTYLE_PRESET_DEFS`）から選択し、`apply_playstyle_preset_with_preset_meta` で一括反映 |
| **ローテーション** | ローテ詳細、起用方針テンプレ、先発・6th・ベンチ、参考役割 等 | プリセットは **3 定義**（`ROTATION_PRESET_DEFS`）から選択し、`apply_rotation_preset_with_preset_meta` で一括反映（先発/6th/ベンチ・`roles` は**触れない**） |

**従来メモの「一括プリセット未実装」**は **廃止**（プレイスタイル・ローテーション**それぞれ**のプリセット選択 UI が **実装済み**）。

**実装済みの論理 ID / 表示名**（`team_tactics.py` 正本）:  
プレイスタイル — `balanced_v1`（バランス型）、`run_and_gun_3p_v1`（ラン＆ガン3P型）、`defense_first_v1`（堅守型）。  
ローテーション — `balanced_v1`（バランス型）、`win_now_v1`（勝利優先型）、`development_v1`（育成優先型）。

---

## 2. プリセットが「論理的に」触る対象（v1 実装）

### 2.1 プレイスタイル

- `Team.strategy`（`PLAYSTYLE_PRESET_DEFS["team"]`）  
- `team_tactics["team_strategy"]`（6 キー）  
- `team_tactics["playbook"]`（6 キー）  

**触れない（v1）**: `preset_meta` の**他キー**（`apply_playstyle_preset_with_preset_meta` 内で `rotation_preset_id` 等を維持）、`coach_style`、`Team.usage_policy`、**`roles`**。

### 2.2 ローテーション

- `Team.usage_policy`（`set_usage_policy` 等の経路）  
- `team_tactics["usage_policy"]`  
- `team_tactics["rotation"]`（定義上 `starters` は `{}`）  

**触れない（v1）**: `preset_meta` の**他キー**、**先発 / 6th / ベンチ（`Team`）**、**`roles` / `main_role`**

---

## 3. 「カスタム」表示 — 実装（`get_current_*_preset_state`）

**関数**: `get_current_playstyle_preset_state(team)` / `get_current_rotation_preset_state(team)`（`team_tactics.py`）。

| 状況 | 返却イメージ |
|------|----------------|
| 対象側の `preset_meta.*_preset_id` が**未設定** | `未設定`（`is_custom: false` 想定。詳細は実装） |
| ID が**正典に存在しない**、または**正典と正規化後の現値が一致しない** | **「カスタム」**（`label_ja` が `カスタム`） |
| 正典と一致 | プリセットの `label_ja` |

**再適用で正典と一致**すれば、表示は **プリセット名に戻る**（**手動微調整後**も、値を定義通りに戻せば整合）。

`main_role` 等 **roles のメモ**は、**上述のカスタム判定の対象外**（`GM_ROSTER_DISPLAY_RULES.md` / `AUTO_ROLE_TAG_PARAMS.md` の整理と整合）。

---

## 4. `team_tactics["preset_meta"]`（v1・実装済み）

| キー | 意味 |
|------|------|
| `version` | プリセットメタ用（`TACTICS_SCHEMA_VERSION` とは**別**） |
| `playstyle_preset_id` | 最後に適用したプレイスタイル論理 ID または `null` |
| `rotation_preset_id` | 最後に適用したローテーション論理 ID または `null` |

**片側の適用**: `apply_playstyle_preset_with_preset_meta` は **`playstyle_preset_id` のみ**更新し **`rotation_preset_id` は維持**。`apply_rotation_preset_with_preset_meta` はその逆（実装 docstring 参照）。

**手動保存経路（`main_menu_view._tactics_commit_payload`）**: ペイロードに `preset_meta` が無い場合、**直前の `team_tactics["preset_meta"]` をマージ**して**落とさない**（コメント・実装参照）。

**旧メモの「normalize が `preset_meta` を消すため永続化されない」**は、**正規化＋UI 保存経路の改修後は当てはまらない**。現行は `normalize_team_tactics` 返却に `preset_meta` を含め、上記 commit で**維持**する。

---

## 5. 比較するキー列（実装の方針）

- **プレイスタイル同一性**: 実装は **`Team.strategy`**、正規化後の **`team_strategy` / `playbook`**（`get_current_playstyle_preset_state` 内）  
- **ローテーション同一性**: **`Team.usage_policy`**、正規化後の **`usage_policy` / `rotation`**（`get_current_rotation_preset_state` 内）  

`playbook` や `foul_policy` が試合内で**未参照でも**、**保存はされている値**に対して**カスタム表示**を揃えている点は、**説明責任**として注記可能（試合本体内の参照度は**未検証**なら未確認でよい）。

---

## 6. 未反映項目の扱い（表示・体験）

| 項目 | 表示・設計上の扱い |
|------|---------------------|
| `foul_policy` 等、試合反映が**限定的**であっても | **比較対象**（ローテ正典比較に含まれる）。UI の「未反映」注記は、**各窓**の都合に合わせる |
| `main_role` | **起用プリセット名のカスタム判定に含めない**（手動参考役割） |
| 人事 `タグ:` | **人事表示用の自動タグ**（`auto_role_tag`）— `main_role` とは**別** |

---

## 7. 今後の改善候補（未実装・要検討）

- トラックの**更細分離**（例: team_strategy だけ外してもプレイスタイル名をどう扱うか）  
- CLI やテスト専用経路での `preset_meta` **同期**  
- 上記**将来候補プリセット**（`TACTICS_PRESET_CANONICAL_DICTS.md` §4）の追加

---

## 8. 設計履歴

- 本書の旧版は **「実装方針ドラフト」「一括未実装」「`preset_meta` 永続化未着手」** 前提を含む。**現行実装**（`1957346` 系＋ `preset_meta` 正規化・永続化・`*_state` 関数）に**追従して差し替え**た。
