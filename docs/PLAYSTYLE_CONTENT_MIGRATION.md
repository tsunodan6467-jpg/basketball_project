# プレイスタイル枠 — 構成とプリセット（実装照合メモ）

**位置づけ**: 戦術メニュー **プレイスタイル** 枠の、**画面ブロック**と**データ正本**の対応。実装の正本は `main_menu_view.py` / `team_tactics.py`。

---

## 1. 戦術ハブ上の「プレイスタイル」枠（実装済み）

プレイスタイル枠に、**少なくとも**次の**3 系統**の窓（誘導）が**整理されている**（旧「3 画面」相当を**一枠**に集約した表現）。

| ブロック | 主な窓 | 主な保存先 | 主な中身（キー） |
|----------|--------|------------|------------------|
| **基本方針** | `_open_tactics_core_policy_window` 等 | **`Team`**: `strategy`, `coach_style`, `usage_policy` | 手動で 3 コンボを保存可能。一方、**プレイスタイルプリセット**（`apply_playstyle_preset_with_preset_meta` / v1 正典）が**上書き**するのは **`Team.strategy`** および `team_tactics` の **`team_strategy` / `playbook` のみ**（**`coach_style` と `Team.usage_policy` はプリセットで変えない**） |
| **攻守の傾向** | `_open_tactics_team_strategy_window` | `team_tactics["team_strategy"]` | `offense_tempo`, `offense_style`, `offense_creation`, `defense_style`, `rebound_style`, `transition_style` |
| **セット傾向** | `_open_tactics_playbook_window` | `team_tactics["playbook"]` | P&R 系、オフボール、ポスト、トランジション等（`low` / `standard` / `high`） |

**補足**: 基本方針窓は **Team 3 項目**を**引き続き**編集する一方、**ラベル**「プレイスタイル枠」下に**置かれ**、基本起用 `Team.usage_policy` は**ローテ枠**の説明（窓**別**）と**分離**して理解する（二重正本の注意は `TACTICS_PRESET_CUSTOM_STATE_POLICY.md` 等と整合）。

---

## 2. プレイスタイルプリセット（`PLAYSTYLE_PRESET_DEFS`）— 実装済み 3 候補

**正本**: `basketball_sim/systems/team_tactics.py` の定数。UI はキー列挙し `apply_playstyle_preset_with_preset_meta` に渡す。

| 論理 ID | 表示名（`label_ja`） |
|---------|----------------------|
| `balanced_v1` | バランス型 |
| `run_and_gun_3p_v1` | ラン＆ガン3P型 |
| `defense_first_v1` | 堅守型 |

**正典の中身**（`Team.strategy` + `team_strategy` + `playbook`）の**数値**は、**同一定数**を参照。表示ラベル「**カスタム**」は `get_current_playstyle_preset_state` による**正典比較**（手動で一部ずらした場合 等）。

---

## 3. 試合内・バランスの「体感」

- **正典の数値**（各キーの**具体的な** `fast` / `high` 等の寄せ方）は、**今後のチューニング**の対象になりうる（**実装**はあるが、**最終バランス**の宣言は**していない**）。  
- `playbook` 各キーが試合シムで**参照される範囲**は、**全モジュール**を横断する**精査**が別途あると**安全**（**未検証**のままの可能性がある旨を、必要に応じ**UI 注記**で補足しうる）。

---

## 4. 古い「最終 0〜7 見出し」表との関係

- 旧メモの **0. 戦術プリセット 〜 7. セット傾向** という**章立て案**は、**表示ラベル**の**整理**メモとして**残る**が、**現行の**「基本方針 / 攻守 / セット」**3+窓**と**1:1 対応**するとは**限らない**（`main_menu_view` 上の**実ラベル**を正とする）。  
- **独立 Toplevel の**折りたたみ**統合**等は、**未完了**の**今後候補**（キー不変のまま**導線**だけ変える案がありうる）。

---

## 5. 主に参照する実装

- `basketball_sim/systems/main_menu_view.py` — プレイスタイル枠、プリセット行  
- `basketball_sim/systems/team_tactics.py` — `PLAYSTYLE_PRESET_DEFS`, `apply_*`, `get_current_playstyle_preset_state`  
- `basketball_sim/tests/test_team_tactics_normalize.py` — 正規化・プリセット**周辺**の**回帰**

---

## 6. 設計履歴

- 本ファイルの旧版は、ハブ上が「**まだ3つ**」等の**導入前**言い回しを含みうる。**2026-04 以降**、**2 枠ナビ＋3 系統窓＋3 プリセット**が**実装に接続**された旨へ**更新**した。
