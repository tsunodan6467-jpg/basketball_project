# FAプール `player.salary` と `estimate_fa_market_value` の整合・CPU本格FA接続 設計書

**作成日**: 2026-04-07  
**文書の性質**: **実装設計（案）**。本書はコード変更を伴わない。実装時は `docs/SALARY_SCALE_MASTER_TABLE_2026-04.md`・`docs/FA_SALARY_SCALE_CONNECTION_PLAN_2026-04.md` と整合させる。  
**前提監査**: `docs/SALARY_SCALE_AUDIT_2026-04.md`  
**前提正本**: `docs/SALARY_SCALE_MASTER_TABLE_2026-04.md`  
**直前実装**: `estimate_fa_market_value` 第1弾（開幕ロスター単価オーダーへ）

---

## 1. 文書の目的

`estimate_fa_market_value` を開幕年俸スケールへ寄せたことで、**インシーズンFA**の表示と既定契約は一本化された。一方、**CPU 本格FA**は `free_agency._calculate_offer` が **`player.salary` を起点**としており、FA プール上の `salary` が旧スケールや別単価のままだと、**同じプール選手でも経路によって金額の物差しが分岐**し続ける。

本書は、**FA プール選手の `player.salary` を何とみなすか**、**`estimate_fa_market_value` とどう揃えるか**、**CPU 本格FA・オフ手動FA へどう波及させるか**を段階的に実装するための**合意形成用の正本**とする。

---

## 2. 現在のFAプール salary / estimate / 本格FA の関係

### 2.1 `player.salary` の由来（FA プール文脈）

- **元所属からの流出**: 満了・解雇等で FA に出た選手は、**直近の契約年俸**が `salary` に残っていることが多い。開幕後のリバランスや個別取引の結果、**`estimate_fa_market_value`（GENERATOR 単価＋補正）と数値が一致しない**ことが普通にある。
- **属性欠損時の補完**: `ensure_fa_market_fields`（`free_agent_market.py`）は、`salary` が未設定のとき **`ovr * PLAYER_SALARY_BASE_PER_OVR`（100万/OVR）** で埋める。これは **開幕 `calculate_initial_salary`（122万/OVR 素）** や **現行 estimate** とも**完全一致しない**。
- **`_calculate_offer` 内のフォールバック**: `salary <= 0` のとき **`ovr * 10_000`**（さらに別物差し）に落ちる（`free_agency.py`）。

### 2.2 経路別の使う値

| 経路 | 主に参照する年俸系 |
|------|---------------------|
| **インシーズンFA**（`main_menu_view`） | **`estimate_fa_market_value`**（表示・`sign_free_agent` 未指定時の契約額） |
| **オフ手動FA** | 主に **`_calculate_offer(team, player)`（`player.salary` 起点）**＋余地が無いとき **`estimate` フォールバック**、さらに **`estimate * 1.35` 下限**（暫定） |
| **CPU 本格FA** | **`_calculate_offer`** → **`player.salary` 起点**（`estimate` は直接は使わない） |

### 2.3 二重化の帰結

FA プール上では、**「画面上・インシーズン契約の目安」＝ estimate** と **「本格オファー計算の芯」＝ salary** が**別立て**になっている。estimate だけ新スケールへ上げると、**インシーズンは新世界、CPU 本格FA は旧 `salary` のまま**という**経路間の断裂**が残る。

---

## 3. 何がズレの震源地になっているか

- **`estimate_fa_market_value` を正しくしても**、FA プール選手の **`player.salary` が更新されなければ**、**CPU 本格FA のオファー芯**は**従来のまま**である。
- **オフ手動FA**は `_calculate_offer` が正なら **salary 側**、フォールバック・下限では **estimate 側**を見るため、**両方の基準が食い違う**と「コアは低い・下限は estimate で持ち上げ」など**半端な二重基準**が残りやすい。
- したがって、**FA プール上の「基準年俸」をどこに置くか**（＝`salary` をどう同期するか）が、**震源地の次のレバー**である。

---

## 4. `player.salary` の役割整理

### 4.1 比較する三案

| 案 | 内容 | 利点 | 欠点 |
|----|------|------|------|
| **A. 直近契約の残像** | ロスター時代の実額をそのまま尊重 | リアリティ（「この人は去年これだけもらっていた」） | FA 市場の**現在価値**と乖離し、**本格FA オファーが旧額に引っ張られる** |
| **B. FA プール上は市場ベース＝`salary` に寄せる** | プール在籍中は **`salary` を市場ベース年俸**とみなし、estimate と整合 | **`_calculate_offer` がそのまま新世界に乗る**。新フィールド不要 | ロスター流出直後は「表示上の契約額」と**一時的に**ズレうる（同期タイミングで説明） |
| **C. 別フィールド** | `market_base_salary` 等を追加し `salary` は実績のまま | 概念分離がきれい | **全経路の参照切替**が広く、**セーブ互換・改修コスト**が大きい |

### 4.2 推奨（このプロジェクト段階）

**案 B を推奨する**（**新フィールドはまず増やさない**）。

**理由**: CPU 本格FA・オフの主経路は既に **`player.salary` 参照に固定**されている。`estimate` と**数値を揃える方向で `salary` を更新**すれば、**`_calculate_offer` を触らずにオファー芯が新世界へ寄る**。案 C は正しいが、**第1弾の投資対効果が低く、回帰面が広い**。

補足: ロスター所属中は従来どおり **`salary`＝契約額**。**FA プールにいる間**（またはプール正規化のタイミング）に限り、**市場ベースへ寄せる**と責務を分けやすい。

---

## 5. `estimate_fa_market_value` との整合方針

### 5.1 estimate の位置づけ（本書での固定）

- **単一の「FA 市場ベース年俸」の計算関数**として既に実装済み（開幕単価オーダー＋補正）。
- **本書作成時点では estimate の式は変更しない**（ユーザー合意）。整合は **`salary` 側を estimate に寄せる**方向が主戦場。

### 5.2 `player.salary` と一致させるか

- **理想**: FA プール正規化後は **`player.salary == estimate_fa_market_value(player)`**（または意図的にのみ差を付ける将来拡張）。
- **同期タイミングの候補**: **`normalize_free_agents` 完了時**、または **FA プールへ入った直後の単一フック**（実装タスクで確定）。**毎フレーム全選手**は避け、**プール用の正規化経路に限定**する。

### 5.3 二重基準の解消イメージ

1. **estimate**＝計算上の正（表示・説明の言語化に使う）。  
2. **FA プール上の `salary`**＝**本格FA・オフ主経路が読む実体**として **estimate と同値に同期**。  
3. これにより **インシーズン・オフ・CPU が同じ円オーダー**を共有しやすくなる（オフの下限 1.35× も **同じベース上**で解釈できる）。

---

## 6. CPU本格FA / オフ手動FA への接続方針

### 6.1 CPU 本格FA

- **`_calculate_offer` は `player.salary` 起点**のため、**FA プール `salary` を市場ベースへ揃えれば、オファー額が自動的に新世界に寄る**（式自体は後続で調整可能）。
- **第1弾で `conduct_free_agency` 本体を開けない**方が安全。

### 6.2 オフ手動FA

- **主軸は `_calculate_offer`**。プール `salary` が揃えば **コアオファーが estimate と乖離しにくくなる**。
- **estimate フォールバック**と **1.35×下限**は、**プール salary 整理のあと**に「まだ必要か」「係数だけか」を見直すのがよい（**第2弾以降**）。

### 6.3 実装順序の推奨

**先に FA プール `salary` の整理（estimate との同期）**、**後からオフ手動の estimate 依存・下限の整理**。  
**理由**: 下限・フォールバックは **estimate と salary の両方**に依存する。**片方だけ先に変えると調整が二度手間**になりやすい。基準を **`salary` 側で一本化**してから、オフ専用ロジックを**観測ベースで簡略化**しやすい。

---

## 7. 安全な段階実装案

### 第1弾

- **FA プール正規化経路**（例: `normalize_free_agents` またはそれに準ずる単一入口）で、**`player.salary` を `estimate_fa_market_value(player)` に同期**する処理を追加する（**呼び出し箇所を最小化**）。
- **`ensure_fa_market_fields` の「欠損時だけ 100万×OVR」**は、同期後は**補助的**に残すか、**同期前のみ**とするかを実装タスクで決める（**全コンテキストで salary を上書きしない**）。

### 第2弾

- **オフ手動FA**: `offseason_manual_fa_offer_and_years` の **estimate フォールバック・1.35×** が、新しい `salary` / estimate 関係で**過大・過小になっていないか**を検証し、**係数分離や分岐整理**。
- **`_calculate_offer` の `salary<=0` 時 `ovr*10000`** の**レガシー補正**を、**estimate または PLAYER/GENERATOR 単価**のどちらに寄せるか検討（**本体変更は慎重に**）。

### 将来タスク

- **再契約希望額**・**経済表示**・**正本 §5 層別**との完全整合。
- 必要なら **案 C（別フィールド）** への移行検討（大規模リファクタ）。

---

## 8. 今回の第1弾実装で「やること / やらないこと」

### やること（第1弾・コード実装時）

- **FA プール用の正規化フロー**で **`player.salary` を `estimate_fa_market_value` に同期**（専用ヘルパ1つ＋呼び出し1箇所に集約するのが望ましい）。
- **同期のスコープ**を「FA プールにいる選手」「`normalize_free_agents` 経由」等に**明文化**し、ロスター所属中の選手を**誤って上書きしない**ガードを設計する。

### やらないこと（第1弾）

- **`estimate_fa_market_value` の式変更**（本設計書作成時点の合意）。
- **`conduct_free_agency` / `_calculate_offer` / `_determine_contract_years` の変更**。
- **`sign_free_agent` のシグネチャ・本体の変更**。
- **d995b48 系暫定補正の削除**（第2弾で検証後に判断）。
- **generator 開幕ロスター・GUI・経営本体**の変更。

---

## 9. テストと確認観点

- **プール上**: 正規化後 **`salary` と `estimate_fa_market_value(player)` が一致**（または意図した差のみ）であること。
- **CPU 本格FA**: 同一選手に対する **`_calculate_offer` のベース**が旧「数十万円台の salary」に引っ張られていないこと（**シード付きの数値テスト**が有効）。
- **オフ手動FA**: `test_offseason_manual_fa_offer_alignment` 等で **フォールバック・下限経路**の期待値が意図どおりか（**第1弾で同期だけ入れた直後**も**第2弾で係数整理後**も）。
- **インシーズンFA**: **表示＝契約**の経路が壊れていないこと（回帰）。
- **スモーク / 既存 FA 系 pytest** を毎回フルで回す。

---

## 10. 次に実装で触るべき対象（1つだけ）

**`basketball_sim/systems/free_agent_market.py` に新設する **`sync_fa_pool_player_salary_to_estimate(player)`（仮称）** を **`normalize_free_agents` からだけ呼ぶ**形にまとめること**（**「新規同期ヘルパ＋`normalize_free_agents` の1カ所改修」を1コミット単位の芯**とする）。

### なぜ最初の1手として最も安全か

- **`ensure_fa_market_fields` は多くの処理から呼ばれる**ため、ここに「常に estimate で上書き」を入れると**ロスター・その他文脈で誤爆**しうる。一方 **`normalize_free_agents` は FA プール列挙の正規化に特化**しており、**スコープを限定**しやすい。
- **`sign_free_agent` や `_calculate_offer` を最初から触らない**で済み、**データ側（`salary`）を揃えるだけ**で CPU 本格FA に効く。

### そこだけ触ると何が改善するか

- **FA プール上の `salary` と estimate が一致**し、**CPU 本格FA のオファー芯**が**開幕スケール**に乗りやすくなる。オフ手動の **主経路 `_calculate_offer`** も同じ芯を見る。

### 何はまだ残るか

- **オフ手動の estimate フォールバック・1.35×下限**の整理（第2弾）。
- **`_calculate_offer` 内 `ovr*10000` フォールバック**の整理。
- **再契約・経済・正本 §5 の精密化**。

---

## 変更履歴

- 2026-04-07: 初版（FA プール salary 整合と CPU 本格FA 接続の設計書）。
