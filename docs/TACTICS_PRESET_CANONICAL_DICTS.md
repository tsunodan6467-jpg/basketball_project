# 戦術プリセット正典 dict — 実装照合メモ

**位置づけ**: `basketball_sim/systems/team_tactics.py` の **`PLAYSTYLE_PRESET_DEFS`** / **`ROTATION_PRESET_DEFS`** を正本とする。本書は **実装と矛盾しない範囲**で、設計上の補足・将来候補を分けて記す。値の唯一の根拠は **Python 定数**（本書の表は要約）。

---

## 1. 実装済み — プレイスタイル正典（`PLAYSTYLE_PRESET_DEFS`）

**v1 範囲（実装）**: `Team.strategy` + `team_tactics["team_strategy"]` + `team_tactics["playbook"]`。  
**含めない（意図どおり）**: `coach_style`、`Team.usage_policy`、`roles`（`apply_playstyle_preset` 系の docstring 参照）。

| 論理プリセット ID | 日本語表示名（`label_ja`） | `Team.strategy` 内部キー | `team_strategy` / `playbook` |
|---------------------|----------------------------|--------------------------|-------------------------------|
| `balanced_v1` | バランス型 | `balanced` | いずれも `TEAM_STRATEGY_DEFAULTS` / `PLAYBOOK_DEFAULTS` 相当 |
| `run_and_gun_3p_v1` | ラン＆ガン3P型 | `run_and_gun` | 例: テンポ `fast`、攻撃スタイル `three_point`、`transition_style: push`、playbook は handoff/off_ball/transition を `high` 寄り 等（**詳細はコード定数**） |
| `defense_first_v1` | 堅守型 | `defense` | 例: テンポ `slow`、`defense_style: protect_paint`、playbook の transition `low` 等（**詳細はコード定数**） |

**UI**: `main_menu_view` が `PLAYSTYLE_PRESET_DEFS` のキーから候補を生成し、選択 ID を `apply_playstyle_preset_with_preset_meta(team, preset_id)` に渡す（`get_current_playstyle_preset_state` で表示・カスタム判定）。

---

## 2. 実装済み — ローテーション正典（`ROTATION_PRESET_DEFS`）

**v1 範囲（実装）**: `Team.usage_policy` + `team_tactics["usage_policy"]` + `team_tactics["rotation"]`（`starters` は定義上 `{}`）。  
**含めない（意図どおり）**: 先発 / 6th / ベンチ（`Team` 側）、`roles` 個別（`apply_rotation_preset` 系の docstring 参照）。

| 論理プリセット ID | 日本語表示名（`label_ja`） | `Team.usage_policy` | 概要（詳細はコード定数） |
|---------------------|----------------------------|---------------------|---------------------------|
| `balanced_v1` | バランス型 | `balanced` | `USAGE_POLICY_DEFAULTS` + `ROTATION_DEFAULTS` 系（`starters: {}`） |
| `win_now_v1` | 勝利優先型 | `win_now` | 例: `priority: win`、`sub_policy: starters_long`、`clutch_policy: stars` 等 |
| `development_v1` | 育成優先型 | `development` | 例: `priority: development`、`sub_policy: youth_dev`、`clutch_policy: hot_hand` 等 |

**注意（語彙）**: `Team.usage_policy` の内部キーは `win_now` 等。`usage_policy.priority` の `win` は **別フィールド**（`ROTATION_CONTENT_MIGRATION.md` 等と同じ二層の整理）。

**UI**: `main_menu_view` が `ROTATION_PRESET_DEFS` から候補を生成し、`apply_rotation_preset_with_preset_meta(team, preset_id)` を呼ぶ（`get_current_rotation_preset_state` で表示・カスタム判定）。

---

## 3. 正典 dict の構造（実装と一致）

```text
PLAYSTYLE_PRESET_DEFS: preset_id -> {
  "label_ja": str,
  "team": { "strategy": str },
  "team_strategy": { 6 keys },
  "playbook": { 6 keys },
}

ROTATION_PRESET_DEFS: preset_id -> {
  "label_ja": str,
  "team": { "usage_policy": str },
  "usage_policy": { 7 keys },
  "rotation": { ... "starters": {} 推奨 ... },
}
```

マージ・正規化は `team_tactics.py` の `apply_*` / `normalize_team_tactics` に従う。

---

## 4. 将来候補（未実装）— 本リポジトリの正典 dict には**未登録**

以下は **過去の設計表や名称案**として残しうるが、**現行コードの `PLAYSTYLE_PRESET_DEFS` / `ROTATION_PRESET_DEFS` には含めない**（追加時は `ALLOWED_*`・正規化・UI・セーブ互換を別途レビューすること）。

| 区分 | 例（ID 案） | メモ |
|------|-------------|------|
| プレイスタイル | `inside_control_v1`, `switch_and_space_v1` 等 | 旧メモの「案」行。`Team.strategy` のホワイトリストや正典の整合が取れてから。 |
| ローテーション | `core_heavy_v1`, `bench_mob_v1`, `condition_first_v1` 等 | 同上。既存 `ROTATION_DEFAULTS` / サブポリシー列挙への落とし込みが必要。 |

---

## 5. 初期 v1 設計で「正典に入れない」もの（実装方針の再掲）

- **プレイスタイル正典**: `Team.coach_style`、`Team.usage_policy`（ローテ側で扱う）  
- **ローテーション正典**: `Team` 先発 / `sixth_man_id` / `bench_order`、**`rotation.starters` を手動先発で埋めるプリセット**（v1 では空 dict 固定）  
- **`roles` / `main_role`**: プリセット正典の比較対象外（カスタム表示ポリシーは `TACTICS_PRESET_CUSTOM_STATE_POLICY.md` 参照）

---

## 6. リスク・メモ（短く）

- **Team と team_tactics 両方**へ書くため、片系統だけ更新するバグに注意（適用 API は分離済み）。  
- **`playbook`**: 試合ロジックへの**参照範囲**は全モジュール grep での網羅は別タスク。保存・カスタム表示とは切り分けて説明する。  
- **docs と Python**: 本書は概要。**数値の微差**は常に `team_tactics.py` の dict を正とする。

---

## 7. 設計履歴（旧メモからの改訂）

- 本ファイルは、旧「設計専用ドラフト」「実装前正本」の位置づけをやめ、**`team_tactics.py` の v1 実装**（コミット `1957346` 系）に**追従**する。  
- 日付固有情報（例: 特定日の 7 ボタン直列前提）は **`TACTICS_MENU_MIGRATION_PLAN.md` の「設計履歴」**へ移譲。
