# salary が高いときの次の本命 — 設計論点の優先（決裁メモ）

**作成日**: 2026-04-08  
**性質**: **調査順序の決裁（コード変更なし）**。細分観測の後送り: `docs/FA_PLAYER_SALARY_NEXT_OBSERVE_DECISION_2026-04.md`。第1段の読み: `docs/FA_PLAYER_SALARY_READ_NOTE_2026-04.md`。次焦点: `docs/FA_PLAYER_SALARY_DISTRIBUTION_DECISION_2026-04.md`。参照実装: `basketball_sim/systems/free_agent_market.py`、`basketball_sim/systems/generator.py`。

---

## 1. 目的

- **salary 土台が高い**ことを **前提**に、**次にどの設計論点から先に読むべきか**の **優先順位を 1 案で固定**する。  
- **コード変更・修正案・原因の最終断定はしない**。

---

## 2. 確定事実

- **Cell B 実 save・`pre_le_pop`** では **`player_salary ≒ base`**（**observer 確認済み**）。  
- **100M 台 offer の骨格**は **raw `player.salary` 側**（**`bonus` は主因ではない**という **既決の読み**）。  
- **`bonus`** は **約 2 千万円台規模の上乗せ**。  
- **高額帯件数・リーグ別差の細分観測**は **今すぐ必須ではない**（**`FA_PLAYER_SALARY_NEXT_OBSERVE_DECISION` どおり**）。

---

## 3. 比較候補（3 のみ）

### 候補A — 契約初期値・開幕ロスター構成

- **開幕時の目標ペイロール**や **層別への年俸再配分**など、**ロスター所属選手の年俸をまとめて決める経路**（**`generator.generate_teams` 周辺**。**`_rebalance_team_initial_salaries_to_target` 等**）。

### 候補B — 年俸生成ロジック（式・係数）

- **OVR・年齢・潜在・FA 待機年**などから **年俸を組み立てる式**と **`GENERATOR_INITIAL_SALARY_BASE_PER_OVR` 系の係数**（**`calculate_initial_salary`**、**`estimate_fa_market_value`**。**`free_agent_market.py` / `generator.py`**）。

### 候補C — 選手分布（能力・年齢・市場全体）

- **そもそも高 OVR が多い**など、**母集団の分布**が **式に入った結果として** 年俸を押し上げている可能性。

---

## 4. 今回の判断（1 案）

**次段の第1焦点は、salary を FA プール上で直接数値化している経路＝年俸生成ロジック（候補B）に置く。第2に契約初期値・開幕ロスター（候補A）。第3に選手分布（候補C）。**

- **コード上**、**FA プールの `player.salary` は `normalize_free_agents` 等で `estimate_fa_market_value` に揃えられる経路が単一ソースに近い**（**`sync_fa_pool_player_salary_to_estimate`**）。**observer が読む FA の土台はここに直結**しやすい。  
- **開幕ロスター**は **`calculate_initial_salary`＋目標総額への再配分**が **別経路**で、**所属選手の年俸**には効くが、**FA 行の `salary` 確定の第一経路としては B の方が手前**（**断定ではなく読み順**）。  
- **候補C**は **B の入力**でもあり、**式と係数を見たあと**でも **遅くない**。

---

## 5. 理由

- **観測で salary 側が本命**になった以上、**`player.salary` に数字を書き込む関数・係数**から **辿るのが最短**（**offer 式の後段より先**）。  
- **分布論（候補C）**は **重要だが**、**高さの主因が「式か母集団か」**を **混ぜずに見る**なら **B→A→C** の **方が切り分けしやすい**（**まだどちらが本丸かは断定しない**）。

---

## 6. 非目的

- **コード変更**。  
- **高額帯件数・リーグ別要約の実装に、今すぐ着手すること**。  
- **修正案の決定**。  
- **budget 側へ議論を戻すこと**。  
- **候補を 4 つ目以降に広げること**。

---

## 7. 次に続く実務（1つだけ）

**今回の第1候補（年俸生成ロジック）について、実際のコード読解先を拾う短いメモを docs に1本作る。**

---

## 抽出コマンド（参照用）

```powershell
Set-Location c:\Users\tsuno\Desktop\basketball_project
Select-String -Path docs\FA_SALARY_DESIGN_FOCUS_DECISION_2026-04.md -Pattern "目的|確定事実|比較候補|今回の判断|理由|非目的|次に続く実務"
```

---

## 改訂履歴

- 2026-04-08: 初版（第1候補を年俸生成ロジックに固定。`estimate_fa_market_value` / 開幕再配分の経路差を根拠に記載）。
