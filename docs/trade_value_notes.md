# Trade value 項の意味（設計メモ）

実装参照: `basketball_sim/systems/trade_logic.py` の `TradeSystem.calculate_player_trade_value` および `_cpu_future_value_trade_multiplier`、`_get_age_curve_bonus`、`_get_contract_score`。  
観測参照: `tools/cpu_strategy_trade_value_breakdown_observe.py`（分解式は上記と同一に揃えている）。

---

## A. `calculate_player_trade_value` 主要項の意味

| 項（観測名） | 式上の意味 |
|--------------|------------|
| **ovr_term** | `ovr * 1.35` — 現在能力の一次の中心項。総値の大半を占めやすい。 |
| **contract** | `_get_contract_score` — 年俸帯 vs OVR 期待帯、契約残年数による微加減。 |
| **youth_peak_raw** | `max(0, 28 - abs(age - 27)) * 0.4` — **下記 B 参照**。`m_fut` が掛かる前の素量。 |
| **youth_peak_term** | `youth_peak_raw * m_fut` — 将来価値倍率が掛かった後の寄与。 |
| **potential 系** | `potential_bonus`（S/A/B/C/D）を `pot_raw` とし、`pot_term = pot_raw * m_fut`。 |
| **_get_age_curve_bonus（正/負）** | `team.usage_policy` と年齢・OVR の組で決まる補正。正の部分だけ `age_pos_term = max(0,ac)*m_fut`、負は `age_neg_term = ac - max(0,ac)`（**m_fut 非掛け**）。 |
| **pop_term** | `max(0, popularity - 50) * 0.05`。 |
| **icon / injured** | アイコン等 +12、負傷 -4 等（観測集計では件数少なめ）。 |
| **future_value_weight / m_fut** | CPU のみ `get_cpu_club_strategy(...).future_value_weight` から `m_fut = 1 + 0.4*(w-1)` をクランプ（約 0.965〜1.035）。ユーザーチームは常に 1.0。 |
| **fut_delta（観測用定義）** | `(youth_peak_raw + pot_raw + age_pos_raw) * (m_fut - 1)` — **m_fut が 1 以外のとき**、上記三つの「m_fut 掛け項」に対する増分の近似。 |

---

## B. `youth_peak_raw` について（名称と直感の齟齬）

**`youth_peak_raw` は「若手ボーナス」ではない。**

- 数式は `max(0, 28 - |age - 27|) * 0.4` で、**27 歳前後にピーク**がある「キャリアピーク近接」項として読むのが正確。
- 極端に若い選手（例: 20 前後）は `|age-27|` が大きくなり、項はピークより**小さくなりうる**。
- 観測で「push 獲得の平均年齢が若い」と出ても、この項だけが「若さインセンティブ」だと解釈すると**誤読**する。

観測スクリプトでは歴史的に `youth_peak_raw` という名前を使っているが、**意味は「peak proximity」** と置き換えて読むこと。

---

## C. 現時点の観測ベース結論（multi-seed 分解より）

- **`future_value_weight` は主因ではない** — `m_fut` のレンジが狭く、`fut_delta` の絶対値は通常小数台程度。しかも **push（rebuild 志向の逆側）では `m_fut < 1` になりやすく**、将来掛け項を**わずかに抑圧**する方向。
- **「push で獲得が若手寄り」**は、式内部の将来補正の暴走より、**成立したトレードの候補分布（誰が板に乗るか）と、OVR 主項の差**で説明できる可能性が高い（`mean_ovr_term` が push で hold より低い seed が多い等）。
- **次の本線**は `calculate_player_trade_value` の先にある **`evaluate_trade_for_team`** — 差分スコア、OVR 追加補正、**CPU 時の `cutoff`（`trade_loss_tolerance`）**、reasons 群が「なぜ通ったか」を決める。

---

## D. 次に見るべきもの（`evaluate_trade_for_team` 観測）

1. **成立した案件**について、獲得側の `strategy_tag` と送受の age/OVR/potential。
2. **send_value / receive_value**、**score** の内訳（少なくとも `receive - send`、position need、OVR 差分補正まで）。
3. **cutoff**（CPU の `trade_loss_tolerance` 由来）と **`accepts`**。
4. **reasons**（`clear_upgrade` / `acceptable_value` / `younger_return` / `higher_ovr_return` 等）の分布。
5. **「今を買った」vs「将来を買った」proxy**（例: receive の `pot_raw` と send の比、age 差、または `fut_delta` 合計の符号）は補助指標として併記。

未確定で観測で埋めること:

- **候補分布**（誰が交渉に出るか）と **閾値側**（どこまで損しても許すか）のどちらがタグ差の主因か。
- マルチチーム・マルチレッグの経路が `evaluate_trade_for_team` 以外に分岐する場合は、観測スコープを明示する。

---

## 次段観測候補（チェックリスト）

- 獲得側チームの **strategy_tag**（成立時点）
- 成立時の **age / OVR / potential（proxy）**（送受両方）
- **`calculate_player_trade_value`** の送受 **最終値**
- **`evaluate_trade_for_team`**: `score`、`cutoff`、`accepts`、**reasons**
- **今 vs 将来 proxy**（上記 D.5）

実装方針（次タスク用メモ）:

- 本体は変更せず、`TradeSystem.evaluate_trade_for_team` を **一時ラップ**するか、呼び出し元が単一ならその経路のみフック（`finally` で必ず復元）。
- 既存の `cpu_strategy_trade_quality_observe` と同様、**CPU / 成立のみ**に絞るとノイズが減る。

関連雛形: `tools/cpu_trade_acceptance_observe.py`（現状は準備用スタブ）。
