# オフシーズン週次・年間カレンダー（確定案）

本書は **ユーザー確定**の「いつオフが始まり、何週で何をするか」と **月単位の年間の流れ**を記録する。実装は `basketball_sim/models/offseason.py` の `Offseason.run()` 順と突き合わせる。UI では **週単位で区切って表示**し、中身は現状どおり一括実行でも、**週ごとにコミット**する設計にしてもよい。

---

## 年間の流れ（月イメージ）

| 期間 | 内容 |
|------|------|
| **5月** | レギュラーシーズン終盤〜**閉幕**（`docs/SEASON_SCHEDULE_MODEL.md` の R29〜R30 相当）。その後 **国内 PO・昇降格・シーズン内の国際処理**など、シーズン締め。 |
| **6月〜7月** | **オフシーズン**（下記 **W1〜W8**）。**6月第1週目**をオフ開始とする。 |
| **8月** | **完全休養**。選手・チームの時間が進むだけ、または **カレンダー上で省略（ワンクリックで9月へ）**してよい。 |
| **9月** | **プレシーズン**（練習試合・調整・陣容確定などは別途設計。未実装ならプレースホルダー）。 |
| **10月** | **開幕**（レギュラーシーズン **R1** 相当。`SEASON_SCHEDULE_MODEL.md` の 10月と整合）。 |

---

## オフシーズン W1〜W8 と処理ブロック（表示用）

`Offseason.run()` の論理順に対応。**6月第1週＝W1** とする。

| 週 | 目安（例） | 見出し | 処理の束（参照: `offseason.py`） |
|----|------------|--------|-------------------------------------|
| **W1** | 6月・第1週 | 国際①：アジアカップ | `_run_offseason_asia_cup` |
| **W2** | 6月・第2週以降 | 国際②：世界一決定戦 ＋ FINAL BOSS（条件付き） | `_run_intercontinental_cup` → `_run_final_boss_match` |
| **W3** | 6月下旬〜 | 夏のナショナル | `_run_summer_national_team_event` |
| **W4** | 7月・前半 | 人員整理 | `_age_players` → `_player_progression` → `_process_naturalization` → `_retire_and_reincarnate` → `_resign_players` |
| **W5** | 7月・中盤 | スカウト体制 | `_assign_scout_dispatches` → `_reset_team_stats` → `_reset_player_stats` → `_decrease_contracts` → `_refresh_international_market` |
| **W6** | 7月・後半 | ドラフト | `_generate_draft_pool` → `_run_draft_combine` → `conduct_draft` |
| **W7** | 7月末〜 | 補強 | `conduct_trades` → `conduct_free_agency` → `_maintain_free_agent_market` |
| **W8** | 7月・最終週 | 締め・次シーズンへ | `_process_team_finances` → `_process_owner_missions` → `_heal_players` → `_review_team_coaches` → `assign_team_strategies` / `print_team_strategies` |

- **W1〜W4**を主に **6月**、**W5〜W8**を主に **7月** に置くと、**「6月・7月がオフ」**のイメージと一致しやすい。厳密な週番号は UI 実装時に微調整してよい。
- 冒頭の各チームルーキー予算リセット（`reset_rookie_budget`）は **W1 直前**または **W1 に含める**表示でよい。

---

## 8月・9月・10月

| 月 | ゲーム上の扱い |
|----|----------------|
| **8月** | **完全休養**。イベントなしで **日付だけ進める**／**「8月をスキップ」ボタンで 9月1週へ**のどちらでもよい。 |
| **9月** | **プレシーズン**（練習試合・体力・調子・最終登録などは今後 `Phase` または専用モジュールで定義）。 |
| **10月** | **開幕** → シーズン **R1**（`docs/SEASON_SCHEDULE_MODEL.md`）。 |

---

## 関連ドキュメント

- **`docs/SEASON_SCHEDULE_MODEL.md`** … シーズン中 R1〜R30（10月開幕）
- **`.cursorrules`** … 本モデルの要約を参照
- **`basketball_sim/models/offseason.py`** … `Offseason.run()` の実行順
