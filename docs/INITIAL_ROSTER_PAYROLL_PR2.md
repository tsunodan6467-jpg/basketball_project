# PR2: 開幕ロスター年俸分布（12 億一本化後）

## 計測メモ（実装前）

- `generate_teams` の 48 チーム・各 13 人、`salary = OVR × 1,000,000` 時:
  - チーム総年俸の目安: 中央値・平均 **約 8.9〜9.0 億**、最大 **約 9.6〜9.8 億**（複数シード）。
  - **12 億超**: 観測されず（`normalize_initial_payrolls_for_teams` も主に未発火）。
- 主因: **OVR×単価 が低く、合計がキャップに対して余裕が大きい**（人数 13 は固定）。

## 実装方針（最小変更）

- 契約希望額・オフシーズン等の **`PLAYER_SALARY_BASE_PER_OVR`（100 万/OVR）は変更しない**。
- **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`（1,220,000 円/OVR）** を `game_constants` に追加し、`generator.calculate_initial_salary` のみで使用。
- ごく一部のロールで `sum(OVR)×単価 > 12 億` となり得るが、既存の **`normalize_initial_payrolls_for_teams`（main.py 経路）** で 0.98×上限に収まる。

## セーブ互換

- 新規世界生成時の初期 `Player.salary` のみ変化。セーブ形式の変更なし。

## 関連テスト

- `basketball_sim/tests/test_initial_payroll_cap.py`
