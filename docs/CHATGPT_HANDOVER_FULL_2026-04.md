# ChatGPT 新チャット向け・完全引き継ぎ書

**作成日**: 2026-04-08  
**リポジトリ**: `basketball_project`（ルート: 開発者の `Desktop\basketball_project` を想定）  
**性質**: Cursor 側の調査・決裁のフル同期用。**曖昧語で流さない**。**未確認は未確認と書く**。

---

## 1. この引き継ぎ書の目的

新しい ChatGPT チャットに **このファイルを貼る（または要約ブロック＋本ファイルパスを渡す）だけで**、次を再現できるようにする。

- いま何の問題を調査しているか  
- どこまで切り分けが進んだか  
- 何が犯人候補から外れたか  
- 現在の第1候補は何か  
- どの `docs/` が決裁として固定されているか  
- どのコード・定数・関数が論点か  
- 次に何をすべきか  
- どのコマンドで再観測できるか  
- 現在のコード差分の要約  
- revert / 継続判断に必要な材料  

---

## 2. プロジェクト全体の現在地

- **ゲーム**: バスケシミュレーション（`basketball_sim/`）。オフシーズン FA・給与上限・オファー診断が論点。  
- **今回の主戦場**: **FA オファーが 100M 円台に高止まりする理由**の切り分け。  
- **方針の移動**: 当初は budget / soft cap pushback / bridge 等も疑ったが、**観測とコードで「土台は salary（`player.salary` ≒ offer の `base`）」に寄った**。  
- **ツール**: `tools/fa_offer_real_distribution_observer.py` が **`_calculate_offer_diagnostic` ベース**で行列観測を出す。Cell B 実 save で比較軸を固定。

---

## 3. 現在の最重要論点

- **FA オファー額が高すぎる問題**を、**予算側だけでなく offer 内訳（base / bonus / hard cap 前後）**まで分解済み。  
- **本命は salary 生成側**: **`player.salary` をどう決めているか**（特に **`estimate_fa_market_value`** と **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**）。  
- **現在の第1調整候補**: 定数 **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（いま **`1_150_000` に変更済み**）。**第2候補**: **`legacy_floor`**（`estimate_fa_market_value` 内の `max(raw_linear, floor)`）。  
- **OVR 帯の仮線引き（決裁）**: 注意帯 **OVR 80 前後**、危険帯 **OVR 90 前後**。係数を下げるとそこに素直に効く（机上表あり）。

---

## 4. ここまでの切り分けの流れ（時系列・要約）

1. **post-off budget 側**の観測・**Cell B**（例: α=1.05, β=10M など）を第1候補として整理。  
2. **budget 論点**と **offer 論点**を分離。  
3. **pre_le_room=0**、**final_offer > buffer 飽和** 等を観測で固定。  
4. **soft cap pushback** を疑う → **不発**寄り。  
5. **bridge / over** 主因読みは相対的に弱まる。  
6. **hard cap 後段**は主因ではなく微修正寄り。  
7. **`offer_after_base_bonus` 時点で 100M 台がほぼ完成** → 本命を **base 側**へ。  
8. **base vs bonus** → **bonus は 2 千万円台規模の上乗せ**、骨格は **base**。  
9. **base ≒ `player.salary`**: Cell B 実 save・`pre_le_pop` で **`player_salary` と `base` の min/max/p25/p50/p75 が完全一致**（D1/D2）。**`salary <= 0` 例外経路は実質効いていない**読み。  
10. **salary 分布が高い**と第1段で読める → 細分観測（高額帯件数・リーグ別）は後送り可（決裁済み）。  
11. **設計論点の順**: 年俸生成（**`estimate_fa_market_value`**）→ 開幕・契約 → 分布。  
12. **係数 `GENERATOR_INITIAL_SALARY_BASE_PER_OVR`** が第1疑い。**仮候補 `1_180_000` / `1_150_000`**、**主候補 `1_150_000`** で試行方針を docs 化。  
13. **実装**: `1_220_000` → **`1_150_000`** に変更するコミットを実施（`game_constants.py` の1行）。  
14. **重要**: **同じ Cell B 実 save で observer を回しても数値が変わらなかった**。理由は **セーブに埋め込まれた `player.salary` をそのまま読んでおり**、**`normalize_free_agents` → `estimate_fa_market_value` による再同期がその CLI 経路では走らない**ため。**係数変更の効きを見るには観測経路の修正が必要**（次チャットの最優先）。

---

## 5. 現在の確定事実（既決）

- **100M 台 offer の土台**は **raw `player.salary`**（Cell B 母集団で **`player_salary` ≒ `base`**）。  
- **`bonus`** は上乗せで **主因ではない**（約 21M〜29M 級）。  
- **hard cap 後段**は **微修正寄り**（`hard_over_minus_soft_pushback` 等で差が小さい / 実質一致に近い読み）。  
- **主水準（FA 見積）**: **`raw_linear = ovr × GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**＋**`legacy_floor` との max**＋**potential / age / fa_years_waiting**（`free_agent_market.estimate_fa_market_value`）。  
- **第1調整候補**: **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**。  
- **第2調整候補**: **`legacy_floor`**。  
- **注意帯**: **OVR 80 前後**。**危険帯**: **OVR 90 前後**（仮線引き）。  
- **係数の試行値**: コミット済みで **`1_150_000`**（旧 **`1_220_000`**）。**保険候補 `1_180_000`** は docs 上残置。  
- **観測の落とし穴（確定）**: **既存 Cell B save + 現行 observer だけでは、係数変更が `player_salary` 行に反映されない**（**再見積経路が未実行**）。

---

## 6. 現在の未決事項

- **`1_150_000` をブランチに残すか、一旦 `1_220_000` に戻すか**（プロダクト方針次第）。  
- **係数変更の効きを検証する公式手順**: **FA プールを `normalize_free_agents` 相当で見積に揃えた後に observer を回す**のか、**新規生成 save** にするのか、**observer にオプションで再同期を挟む**のか——**未決**（次チャットで決裁推奨）。  
- **`legacy_floor` を触るタイミング**（係数試行の結果を見てから）。  
- **`potential` 加算の見直し**は **第3候補**として後続可。

---

## 7. 現在のコード構造上の重要読解先

| 優先度 | パス | シンボル |
|--------|------|----------|
| 定数 | `basketball_sim/config/game_constants.py` | **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR`**（**現値 `1_150_000`**）、`PLAYER_SALARY_BASE_PER_OVR` |
| FA 見積 | `basketball_sim/systems/free_agent_market.py` | **`estimate_fa_market_value`**, **`normalize_free_agents`**, **`sync_fa_pool_player_salary_to_estimate`**, **`ensure_fa_market_fields`**, **`_scale_fa_estimate_bonus`** |
| オファー芯 | `basketball_sim/systems/free_agency.py` | **`_calculate_offer`**, **`_calculate_offer_diagnostic`**（`base = int(player.salary)` 等） |
| 観測 | `tools/fa_offer_real_distribution_observer.py` | **`_run_matrix`**, **`_pre_le_population_summary_lines`**（`player_salary` 行は行 dict の `int(getattr(fa,"salary",0))`） |

---

## 8. 今回増やした observer 出力（`pre_le_pop` 周辺）

**`pre_le_pop` ブロック内（母集団は soft_cap_early 除外かつ `offer_after_soft_cap_pushback` と `room_to_budget` が両方 non-None）**で、少なくとも以下を要約出力。

- `room_to_budget`  
- `payroll_before`  
- `cap_base`（gate 行）  
- **`player_salary`**（追加済み）  
- **`base`**  
- **`bonus`**  
- **`offer_after_base_bonus`**  
- **`offer_after_hard_cap_over`**  
- **`offer_after_soft_cap_pushback`**  
- `offer_minus_room`（le0/gt0/gt_temp）  
- `soft_cap_pushback_applied`（true/false 件数）  
- `hard_over_minus_soft_pushback`（eq0/gt0）  
- `payroll_after_pre_soft_pushback`、soft cap 比較、`soft_cap`、`room_to_soft`（gate 系）  

**テスト**: `basketball_sim/tests/test_fa_offer_real_distribution_observer_population.py`

---

## 9. 観測で得た代表値（Cell B 実 save・係数変更前 baseline）

**※ 以下は `GENERATOR_INITIAL_SALARY_BASE_PER_OVR = 1_220_000` 時代の Cell B 出力に基づく。係数 `1_150_000` への変更後、同じ save では pre_le_pop の salary 行は変化なし（§4 末尾参照）。**

| 項目 | D2（目安） | D1（目安） |
|------|------------|------------|
| `player_salary` / `base` | 約 85.0M〜110.2M（**両者一致**） | 約 88.7M〜115.1M（**両者一致**） |
| `bonus` | 約 21.2M〜27.6M | 約 22.2M〜28.8M |
| `offer_after_base_bonus` | 約 106.2M〜137.8M | 約 110.8M〜143.9M |

- **pushback**: 実観測では **不発**寄り。  
- **hard cap 後段**: **abb と近い / 微修正**寄り。

---

## 10. docs 決裁ログ（主要どおり辿る用）

**必須に近いもの（このスレッドで固定した決裁の核）**

- `docs/PAYROLL_BUDGET_POSTOFF_CELL_B_LOCK_DECISION_2026-04.md`  
- `docs/FA_PRE_HARD_CAP_FORMATION_DECISION_2026-04.md`  
- `docs/FA_BASE_MAIN_DRIVER_DECISION_2026-04.md`  
- `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`  
- `docs/FA_SALARY_DESIGN_FOCUS_DECISION_2026-04.md`  
- `docs/FA_OVR_THRESHOLD_DECISION_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_VS_FLOOR_DECISION_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_CANDIDATES_DECISION_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_1150_IMPL_PLAN_2026-04.md`  
- `docs/FA_PLAYER_SALARY_OUTPUT_IMPL_NOTE_2026-04.md`  
- `docs/FA_MARKET_VALUE_CODE_PATH_NOTE_2026-04.md`  
- `docs/FA_MARKET_VALUE_DRIVER_READ_NOTE_2026-04.md`  

**同チェーン上・補助（必要に応じて）**

- `docs/FA_SALARY_MAIN_DRIVER_DECISION_2026-04.md`  
- `docs/FA_BASE_BONUS_BUILD_CODE_PATH_NOTE_2026-04.md`  
- `docs/FA_MARKET_VALUE_MATCH_NOTE_2026-04.md`  
- `docs/FA_OVR_BAND_MATCH_NOTE_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_CODE_PATH_NOTE_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_READ_NOTE_2026-04.md`  
- `docs/FA_OVR_COEFFICIENT_EFFECT_NOTE_2026-04.md`  
- `docs/FA_PLAYER_SALARY_OBSERVE_SUFFICIENCY_NOTE_2026-04.md`  
- `docs/FA_PLAYER_SALARY_READ_NOTE_2026-04.md`  
- `docs/FA_PLAYER_SALARY_NEXT_OBSERVE_DECISION_2026-04.md`  
- `docs/FA_OVR_BAND_DRIVER_DECISION_2026-04.md`  

**指示書オリジナルパス（ローカル）**: `Desktop\chatGPTのファイル一旦置くところ\cursor_to_new_chat_handover_instruction.md`（**本リポジトリ外**）

---

## 11. 現在のワーキングツリー / コミット上の注意点

- **係数変更コミット**: `2ca4506` — `tune: temporarily lower FA salary ovr coefficient to 1_150_000 for observation`  
- **変更ファイル**: `basketball_sim/config/game_constants.py` の **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR = 1_150_000`** のみ（**floor / potential / observer 本体は未変更**）。  
- **観測**: Cell B save で **数値は baseline と同一** → **セーブ内 `player.salary` がそのまま使われ、係数は `estimate` 再実行まで効かない**ことが確認済み。  
- **次チャットで必ず決めること**: このコミットを **残す / revert する**、および **効き検証用の公式経路**。

---

## 12. 次チャットで最初にやるべきこと（1 つだけ）

**「係数変更の効きを正しく観測するための経路決裁」**  
- 例: **load 後に FA サンプルへ `normalize_free_agents` を挟んでから行列を回す**、**新規シーズン生成 save で測る**、**observer に `--resync-fa-salary` 的な最小フラグを追加する** 等。**いずれも未実装・未決裁**。

---

## 13. 次チャット開始直後にそのまま貼れる要約（コピペ用）

```
【引き継ぎ】basketball_project / FA 高額オファー調査（2026-04-08時点）
・論点: 100M台offerの土台は raw player.salary。bonusは上乗せ。hard cap後段は微修正寄り。
・Cell B実save: player_salary≒base（D1/D2で分位まで一致）。estimateの主水準は ovr×GENERATOR_INITIAL_SALARY_BASE_PER_OVR。
・第1調整候補は同定数。いま game_constants で 1_150_000 に変更済み（コミット 2ca4506）。第2候補 legacy_floor。OVR注意帯~80前後、危険帯~90前後（仮）。
・問題: 既存save+現行observerではセーブ上のsalaryをそのまま読むため、係数変更がpre_le_popに反映されなかった。効きを見るには FA再見積経路を観測に含める決裁が必要。
・詳細: リポジトリの docs/CHATGPT_HANDOVER_FULL_2026-04.md を開くこと。
```

---

## 返答用メタ（Cursor → ユーザー）

### 変更ファイル

- 追加: `docs/CHATGPT_HANDOVER_FULL_2026-04.md`

### 要点

- 指示書の **全必須章（1〜13）** を日本語で満たし、**係数試行後に判明した「save では効かない」**を **確定事実・未決・次タスク**に明記した。  
- **コミットハッシュ・現行定数値・代表観測・主要 docs 一覧・コード読解先**を **1 ファイルに集約**した。  
- **次チャット用コピペ要約**を §13 に置いた。

### 実行コマンド

```powershell
Set-Location C:\Users\tsuno\Desktop\basketball_project
git show --stat HEAD
```

### 抽出コマンド

```powershell
Select-String -Path docs\CHATGPT_HANDOVER_FULL_2026-04.md -Pattern "^#|^##|現在の最重要論点|現在の確定事実|現在の未決事項|次チャットで最初にやるべきこと"
Select-String -Path basketball_sim\config\game_constants.py -Pattern "GENERATOR_INITIAL_SALARY_BASE_PER_OVR"
```

### 差分要約

- **新規 1 本**: 上記 13 章構成の引き継ぎ全文。

### 次にやるタスク

- **1 つだけ**: **§12 どおり「係数変更の効きを正しく観測する経路」を決裁し、必要なら最小実装する。**

---

## 改訂履歴

- 2026-04-08: 初版（`cursor_to_new_chat_handover_instruction.md` の必須章に準拠）。
