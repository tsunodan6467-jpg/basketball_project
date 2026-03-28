# 試合先発決定ルール（team_tactics 連携）

**正本**: 本書。`.cursorrules` の該当節は要約＋参照のみ。実装とズレた場合は **本書優先**でコードを合わせる。

---

## 1. 目的

- **通常評価（アルゴリズム）を正本**にし、試合の実力感とオンコート規定を優先する。
- **戦術先発**（`team_tactics.rotation.starters`）は、**条件を満たした差し替え**に限定し、低評価の無理な先発を防ぐ。
- **細かいチーム戦術**（`team_strategy` 等）は Phase A 方針どおり、試合シミュの正本は引き続き `Team.strategy` 等の既存経路とする（本書の対象外）。

---

## 2. 用語

| 用語 | 意味 |
|------|------|
| **ベース先発** | 試合登録 `active` から `Match._get_starting_five_from_players` で得る 5 人。評価は `Player.get_roster_sort_weight()` ベースの並び＋オンコート規定による構築。 |
| **戦術スロット** | `team_tactics.rotation.starters` の `PG` / `SG` / `SF` / `PF` / `C`。値は `player_id` または未指定。 |
| **出場可能** | 当該試合の `active` に含まれる（非アクティブ・負傷・引退はロスター選定時点で除外済みであること）。 |
| **ルール上合法** | オンコート規定（外国籍上限、Asia/帰化枠など）。`Match._validate_lineup` と同種の基準で **最終 5 人** を検証。 |
| **戦術適性（初期版）** | 少なくとも **戦術で指定したポジション `pos` と `Player.position` が一致**すること。拡張時は `team_tactics.roles[].main_role` のホワイトリスト等を足してよい。 |

---

## 3. 目標アルゴリズム（差し替えモデル）

### 3.1 全体の流れ

1. **ベース先発** `B` を計算する（現行の `_get_starting_five_from_players`）。
2. 作業用ラインナップ `L ← copy(B)`。**5 人の並び順**は実装で固定する（推奨: ベースと同じリスト順。将来ポジ順に揃える場合は本書と `Match` コメントを同時更新）。
3. **戦術で `player_id` が入っているスロットだけ**、ポジション順（`PG` → `SG` → … → `C`）で次の **差し替え判定** を行う。
4. 各差し替え後、**5 人全体**が重複なし・全員 active・**ルール上合法**であること。不成立なら **その差し替えを拒否**（直前の `L` のまま）。
5. 最終的に不正が残る場合は **`B` にフォールバック**（または段階的拒否後の `L` を再検証してから確定）。

### 3.2 差し替え判定（スロット `pos` に戦術で選手 `T` が指定されているとき）

**置き換え対象（victim）の推奨定義**

1. **第一候補**: `L` のうち `T.position` と同一ポジションの選手がいれば、その中で **1 人**を選ぶ（**§5.1-2**: OVR が最も `T` に近い、同率は `L.index` 最小）。
2. **同一ポジがいない場合のフォールバック**: **§5.1-3** どおり、`tactics_introduced` に含まれないメンバーのうち **OVR 最低**（同率は `L` 先頭寄り）。

**許可条件（すべて満たすこと）**

1. **出場可能**: `T` が `active` に存在する。
2. **OVR 差**: `abs(T.get_effective_ovr() - victim.get_effective_ovr()) <= TACTICS_STARTER_OVR_MAX_DIFF`（`game_constants.py`、既定 3。§5.1-5）。
3. **戦術適性**: 少なくとも `T.position == pos`（初期版）。
4. **適用後の合法チェック**: `T` で victim を置き換えた `L'` がルール上合法。

条件を満たすときだけ `L ← L'`。満たさないときはスキップ。

### 3.3 戦術未指定・一部指定

- 5 スロットすべて未指定 → `B` のまま。
- 一部のみ指定 → 指定スロット分だけ上記を実行。残りはベースの選手のまま。

### 3.4 擬似コード（実装メモ）

```text
B ← _get_starting_five_from_players(active)
L ← copy(B)

for pos in (PG, SG, SF, PF, C):
    tid ← normalized tactics.starters[pos]
    if tid is None: continue
    T ← resolve_player(active, tid)
    if T is None: continue

    victim ← pick_victim(L, pos, T)   // 上記 3.2
    if victim is None: continue
    if abs(ovr(T) - ovr(victim)) > 3: continue
    if T.position != pos: continue      // 初期版の戦術適性

    L' ← replace(L, victim, T)
    if not legal_on_court(L'): continue
    L ← L'

return validate_final(L, fallback=B)    // 最終的に必ず合法な 5 人
```

---

## 4. 現行実装との関係

| 項目 | 内容 |
|------|------|
| **試合先発** | `Match._resolve_match_starters` が **本書 §3 の差し替えモデル**を実装。`TACTICS_STARTER_OVR_MAX_DIFF`（OVR 差）と `TACTICS_STARTER_MAX_SUBSTITUTIONS`（成功 swap 回数上限）は `config/game_constants.py`。 |
| **正規化済みスロット** | `get_normalized_rotation_starters_map`（`team_tactics.py`）で PG〜C を取得。 |
| **`collect_tactics_starter_players`** | 5 スロット完備時の一覧取得用（テスト等）。試合先発の必須ヘルパではない。 |
| **GM 画面の `Team.starting_lineup` / `get_starting_five()`** | **試合エンジンの先発正本には使わない**（現方針）。 |

---

## 5. 設計上の決定事項（v1 実装）

### 5.1 確定済み（プレイ感・コードと一致）

1. **ベース 5 人の並び**  
   `_get_starting_five_from_players` が返す **リスト順**を `L` の初期状態とする（PG〜C への並べ替えはしない）。

2. **victim（同ポジが L にいるとき）**  
   `T.position` と同一の選手のうち、`get_effective_ovr()` が **T に最も近い** 1 人。  
   **同率**は `L.index(p)` が **小さい**方（先頭寄り）。

3. **victim フォールバック（ベース先発に T と同ポジがいないとき）**  
   `tactics_introduced`（戦術差し替えで先発に入れた選手の `player_id`）に **含まれない** メンバーのみを候補とし、そのうち **OVR 最低**の 1 人。  
   **同率**は `L.index(p)` が **小さい**方。候補が空ならそのスロットはスキップ。

4. **戦術適性（初期版）**  
   **`T.position == スロット名`（PG〜C）** のみ。`team_tactics.roles` は未使用。

5. **OVR 差上限**  
   `basketball_sim/config/game_constants.py` の **`TACTICS_STARTER_OVR_MAX_DIFF`**（既定 **3**）。  
   バランス調整は **原則この定数のみ**変更し、試合全体の他係数と混ぜない。

6. **複数スロットと差し替え回数の上限**  
   スロットは PG→…→C の順。成功した差し替え（swap）の累計が **`TACTICS_STARTER_MAX_SUBSTITUTIONS`** に達したら、残りスロットは**見ない**（既定 **5**＝従来どおり最大 5 回まで試行可能）。  
   違法・重複・条件不一致のスロットは従来どおりスキップし、swap カウントは増えない。

### 5.2 将来の調整候補（未実装）

- **`roles`** や別指標による戦術適性の拡張。

---

## 6. 関連ファイル（目安）

- `basketball_sim/config/game_constants.py` — `TACTICS_STARTER_OVR_MAX_DIFF`, `TACTICS_STARTER_MAX_SUBSTITUTIONS`
- `basketball_sim/models/match.py` — `_resolve_match_starters`, `_pick_tactics_substitution_victim`, `_get_starting_five_from_players`, `_validate_lineup`
- `basketball_sim/systems/team_tactics.py` — `rotation.starters` の正規化・取得
- `basketball_sim/tests/test_team_tactics_phase_b.py` — 先発・規定まわりの回帰（仕様変更時に更新）

---

## 7. 変更履歴（手動メモ）

| 日付 | 内容 |
|------|------|
| 2026-03-28 | 初版: ユーザー案（ベース先発＋条件付き戦術差し替え・OVR 差 3・適性）を正本化。 |
| 2026-03-28 | `Match._resolve_match_starters` に差し替えモデルを実装。§4 を実装済み表記に更新。 |
| 2026-03-28 | §5 を v1 決定事項＋将来候補に整理。`TACTICS_STARTER_OVR_MAX_DIFF` を `game_constants` に集約。 |
| 2026-03-28 | `TACTICS_STARTER_MAX_SUBSTITUTIONS`（既定 5）で戦術先発の成功 swap 回数上限を実装。§5.2 の「最大人数」を §5.1-6 に移管。 |
