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

1. **第一候補**: `L` のうち `T.position` と同一ポジションの選手がいれば、その中で **1 人**を選ぶ（複数いる場合は **OVR が最も `T` に近い**、同率は `L` 内の先頭など、実装で固定）。
2. **同一ポジがいない場合のフォールバック**: `L` のうち、まだ「戦術指定による差し替えで入れた選手」でない席から **OVR 最低の 1 人**を victim とする、など **1 行ルール**をコードコメントと本書に明記して固定する（未決定なら実装 PR で決め、本書を更新）。

**許可条件（すべて満たすこと）**

1. **出場可能**: `T` が `active` に存在する。
2. **OVR 差**: `abs(T.get_effective_ovr() - victim.get_effective_ovr()) <= 3`（**初期版の定数**。調整時は `game_constants` 等への集約を検討）。
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

## 4. 現行実装との関係（追記時点のメモ）

| 項目 | 内容 |
|------|------|
| **本書の差し替えモデル** | **目標仕様**。`Match._resolve_match_starters` を本アルゴリズムに合わせるのが正しい最終形。 |
| **Phase B（過渡）** | 実装が「5 スロット完備かつ `collect_tactics_starter_players` が成功し `_validate_lineup` を通る場合、戦術 5 人をそのまま採用」になっている期間がある。**本書と異なる場合は本書に合わせて置き換える**。 |
| **ヘルパ** | `basketball_sim/systems/team_tactics.py` の `collect_tactics_starter_players` 等。差し替えモデルでは **スロット単位の読み取り**や正規化再利用が中心になる。 |
| **GM 画面の `Team.starting_lineup` / `get_starting_five()`** | **試合エンジンの先発正本には使わない**（現方針）。戦術メニューと GM ロスターは別経路。将来統合する場合は本書と GM 仕様を同時に改訂する。 |

---

## 5. 実装前に固定しておくとよい項目

1. **ベース 5 人の並び**（リスト順のままか、表示用に PG〜C へ並べ替えるか）。
2. **victim が取れない・同ポジ複数時**のタイブレーク。
3. **戦術適性**をポジ一致のみで開始するか、`roles` を同時に入れるか。
4. **複数スロット連続適用**で全員戦術寄りになることの許容（必要なら「1 試合あたり最大 N 人まで差し替え」など上限を本書に追加）。

---

## 6. 関連ファイル（目安）

- `basketball_sim/models/match.py` — `_resolve_match_starters`, `_get_starting_five_from_players`, `_validate_lineup`
- `basketball_sim/systems/team_tactics.py` — `rotation.starters` の正規化・取得
- `basketball_sim/tests/test_team_tactics_phase_b.py` — 先発・規定まわりの回帰（仕様変更時に更新）

---

## 7. 変更履歴（手動メモ）

| 日付 | 内容 |
|------|------|
| 2026-03-28 | 初版: ユーザー案（ベース先発＋条件付き戦術差し替え・OVR 差 3・適性）を正本化。 |
