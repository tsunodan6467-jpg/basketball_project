# ローテーション枠 — 構成とプリセット（実装照合メモ）

**位置づけ**: 戦術メニュー **ローテーション** 枠の、**画面ブロック**と**データ正本**の対応。`main_menu_view.py` / `team_tactics.py` を正とする。  
**参考役割 / 人事の自動タグ**: `docs/AUTO_ROLE_TAG_PARAMS.md` / `docs/GM_ROSTER_DISPLAY_RULES.md`（`main_role`＝**手動参考**、人事行末 `タグ:`＝**自動**。**正本逆向き**にしない）。

---

## 1. 戦術ハブ上の「ローテーション」枠（実装済み）

ローテーション枠に、**少なくとも**次の**系統**の窓が**整理されている**（旧 4+ 窓相当を**一枠**に集約した表現）。

| ブロック | 主な窓 | 主な保存先 | 主な中身（キー）の要約 |
|----------|--------|------------|------------------------|
| **ローテ詳細** | `_open_tactics_rotation_window` 等 | `team_tactics["rotation"]` | 戦術先発枠 `starters`（`Team` 先発**と別**）、`target_minutes`、`sub_policy` / `fatigue` / `foul` / `clutch` 等 |
| **起用方針テンプレ** | `_open_tactics_usage_policy_window` | `team_tactics["usage_policy"]` | `priority` 等 7 キー。**`Team.usage_policy`（基本方針）とは別レーン**（窓内注記の通り） |
| **先発・6th・ベンチ** | `_open_tactics_team_lineup_window` | **`Team`** | `starting_lineup`, `sixth_man_id`, `bench_order`（**正本**） |
| **参考役割・個別起用** | `_open_tactics_roles_window` | `team_tactics["roles"]` 各 `pid` | `offense_involvement`, `shot_priority`, `clutch_priority`, `playmaking_role`, `defense_assignment`, **`main_role`（参考）** |

**人事表示の `タグ:`**は **`compute_auto_role_tags_for_team` 由来**（`auto_role_tag.py`）— **`main_role` の代替表示ではない**（上記コミット済み docs 参照）。

---

## 2. ローテーションプリセット（`ROTATION_PRESET_DEFS`）— 実装済み 3 候補

**正本**: `basketball_sim/systems/team_tactics.py`。UI はキー列挙し `apply_rotation_preset_with_preset_meta` に渡す。  
**触れない**: 先発 / 6th / ベンチ、**`roles` / `main_role`**（適用 API の docstring 参照）。

| 論理 ID | 表示名（`label_ja`） |
|---------|----------------------|
| `balanced_v1` | バランス型 |
| `win_now_v1` | 勝利優先型 |
| `development_v1` | 育成優先型 |

`get_current_rotation_preset_state` で**カスタム**（正典と手動差分）を**表示**。

---

## 3. 関連実装 — `roles` の試合ロジックへの**一部**反映

次は **`rotation.py`** 経路で、**`team_tactics["roles"]` の**一部が**代替・判断補正**に**用いられている**想定（**挙動の**網羅的な保証**は**テストとコード参照**に委ねる）。

- **`clutch_priority`**: 終盤の**代わり要員**の選択に**オーバーレイ**（`get_roles_clutch_priority_substitute_overlay`）  
- **`defense_assignment`**: **交代判断** / **最短交代**に**小さな**補正（`get_roles_defense_assignment_sub_out_modifier`、**他条件と合成・クランプ**）  

**参照テスト**（本リポジトリ）:  
`basketball_sim/tests/test_roles_clutch_priority_substitute_overlay.py`  
`basketball_sim/tests/test_roles_defense_assignment_sub_out.py`  

**コミット**（本トピック）: `3d9ba32 役割設定をローテ交代判断に反映`。

---

## 4. 旧「最終 0〜4 見出し」表との関係

- 章立て案（**起用プリセット(0) … 参考役割(4)** 等）は、**導線整理**の**メモ**として**有効**だが、**現行の**窓タイトルと**1:1**でない箇所あり（**コード**を正とする）。  
- `rotation` の **`foul_policy`** 等、**試合**への**接続**が**限定的**であっても、**UI** や**プリセット比較**上は**値**が**保存**される（`TACTICS_PRESET_CUSTOM_STATE_POLICY.md` と**整合**）。

---

## 5. 主に参照する実装

- `basketball_sim/systems/main_menu_view.py`  
- `basketball_sim/systems/team_tactics.py` — `ROTATION_PRESET_DEFS`, `get_current_rotation_preset_state`  
- `basketball_sim/systems/rotation.py` — `roles` 参照**箇所**（上記）  
- `basketball_sim/systems/auto_role_tag.py` / `gm_dashboard_text.py`  
- テスト: 上記 **rotation roles** テスト、`test_team_tactics_normalize.py` 他

---

## 6. 今後候補（要製品判断・未完了可）

- **`Team.usage_policy`** と **`usage_policy.priority` の**見出し**・**1画面化**案（**内部**は**未一本化**の**まま**扱いうる）  
- プリセット**追加**（`TACTICS_PRESET_CANONICAL_DICTS.md` §4 の**将来候補**行）

---

## 7. 未確認事項（本紙で断定しない）

- `evaluation_focus` 等を**更に**分割**表示**するだけで**足りる**か、**将来のキー**再設計が**要る**か  
- **シム全体**で `roles` が**参照される**完全一覧

---

## 8. 設計履歴

- 本ファイルの旧版は、**起用プリセット(0) が**まだ**設計確定前**の書き方を**含みうる**。**現行**は **`ROTATION_PRESET_DEFS` 3 本＋`preset_meta`＋`get_current_rotation_preset_state`** が**実装**されている。  
- 一部「**当該作業 完了**」等の**フェーズ表**は、**以降**の**文言**・**導線**整備**が**重なる**部分は、**要更新**（**本節**で**現状**へ**接続**した）。
