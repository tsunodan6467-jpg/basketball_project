# サラリーキャップ一本化（12 億）

## 現状（実装済み）

- **制度上の基準額**: 12 億円（全ディビジョン同一）。
- **定数**: `LEAGUE_SALARY_CAP_BY_DIVISION` = `1_200_000_000`、`SALARY_SOFT_LIMIT_MULTIPLIER` = `1.0`。
- **API**: `get_hard_cap` / `get_soft_cap` は後方互換のため両方残し、**同一額**を返す。
- **`cap_status`**: `under_cap` と `over_soft_cap` のみ（旧 10〜12 億の `over_cap` 帯は廃止）。
- **贅沢税**: `compute_luxury_tax` は従来どおり **上限超過分**（＝現状は 12 億超）に課す。
- **開幕 normalize**: `normalize_team_payroll_under_league_cap` を正とし、`normalize_team_payroll_under_hard_cap` はエイリアス。

## PR2（初期ロスター×給与分布）

- 上限一本化後の開幕ペイロール調整は **`docs/INITIAL_ROSTER_PAYROLL_PR2.md`** と `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` を参照。

## セーブ

- キャップ数値はセーブ形式のフィールドではなく実行時定数。既存セーブの年俸データはそのまま読めるが、**続きからプレイ時の上限解釈は 12 億基準に変わる**。
