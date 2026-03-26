from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


@dataclass(frozen=True)
class DraftTierConfig:
    tier: str  # "T1" | "T2" | "T3"
    name: str
    min_price_low: int
    min_price_high: int


TIER_CONFIGS: Dict[str, DraftTierConfig] = {
    "T1": DraftTierConfig(tier="T1", name="プロスペクト級", min_price_low=20_000_000, min_price_high=26_000_000),
    "T2": DraftTierConfig(tier="T2", name="有望株級", min_price_low=9_000_000, min_price_high=14_000_000),
    "T3": DraftTierConfig(tier="T3", name="素材級", min_price_low=3_000_000, min_price_high=7_000_000),
}


@dataclass
class DraftCandidateMeta:
    player: Player
    tier: str
    min_price: int
    draft_value: float


CAP_DEFAULT = 40_000_000


def _potential_bonus(potential: str) -> float:
    p = str(potential or "C").upper()
    return {"S": 2.0, "A": 1.0, "B": 0.3, "C": 0.0, "D": -0.2}.get(p, 0.0)


def _priority_bonus(player: Player) -> int:
    return int(getattr(player, "draft_priority_bonus", 0) or 0)


def _base_draft_value(player: Player) -> float:
    ovr = float(getattr(player, "ovr", 0) or 0)
    return ovr + float(_priority_bonus(player)) + _potential_bonus(getattr(player, "potential", "C"))


def _assign_tiers_and_min_prices(draft_pool: List[Player]) -> Dict[int, DraftCandidateMeta]:
    """
    draft_pool から tier (T1/T2/T3) と最低落札額を割り当てる。

    - 価値上位 6 人: T1
    - 次の 10 人: T2
    - 残り: T3
    """
    metas: List[DraftCandidateMeta] = []
    for p in draft_pool:
        value = _base_draft_value(p)
        metas.append(DraftCandidateMeta(player=p, tier="T3", min_price=0, draft_value=value))

    metas.sort(key=lambda m: (m.draft_value, getattr(m.player, "ovr", 0)), reverse=True)

    for idx, m in enumerate(metas):
        if idx < 6:
            tier = "T1"
        elif idx < 16:
            tier = "T2"
        else:
            tier = "T3"
        cfg = TIER_CONFIGS[tier]
        m.tier = tier
        m.min_price = random.randint(cfg.min_price_low, cfg.min_price_high)

    return {id(m.player): m for m in metas}


def _tax_extra_for_total_spend(total_spend: int, cap: int) -> int:
    """
    段階式ぜいたく税（追加負担分）を返す。

    cap 超過分に対して:
    - 0〜5,000,000: x1
    - 5,000,000〜15,000,000: x2
    - 15,000,000〜: x3

    ここで xN は「超過分に追加で払う額」の倍率（追加負担）を意味する。
    """
    total_spend = int(total_spend)
    cap = int(cap)
    over = max(0, total_spend - cap)
    if over <= 0:
        return 0

    tier1 = min(over, 5_000_000)
    tier2 = min(max(over - 5_000_000, 0), 10_000_000)
    tier3 = max(over - 15_000_000, 0)
    return int(tier1 * 1 + tier2 * 2 + tier3 * 3)


def _compute_charge_increment(team: Team, bid: int, cap: int) -> Tuple[int, int]:
    """
    bid を足したときの請求額（RBから引く増分）を返す。
    戻り値: (charge, new_total_spend)
    """
    bid = int(max(0, bid))
    cap = int(cap)
    base = int(getattr(team, "rookie_budget", cap) or cap)
    remaining = int(getattr(team, "rookie_budget_remaining", base) or base)
    spent = base - remaining

    new_spent = spent + bid
    extra_before = _tax_extra_for_total_spend(spent, cap)
    extra_after = _tax_extra_for_total_spend(new_spent, cap)
    tax_delta = extra_after - extra_before
    charge = bid + tax_delta
    return int(charge), int(new_spent)


def _apply_rookie_budget_charge(team: Team, charge: int) -> None:
    if hasattr(team, "spend_rookie_budget"):
        team.spend_rookie_budget(int(charge))
        return
    team.rookie_budget_remaining = int(getattr(team, "rookie_budget_remaining", 0) or 0) - int(charge)


def _team_rank_key_for_tiebreak(team: Team) -> Tuple[int, float]:
    """同額タイブレーク用: (RB残高の降順, 成績の悪さ)"""
    base = int(getattr(team, "rookie_budget", CAP_DEFAULT) or CAP_DEFAULT)
    remaining = int(getattr(team, "rookie_budget_remaining", base) or base)
    wins = int(getattr(team, "last_season_wins", getattr(team, "regular_wins", 15)) or 0)
    return (remaining, -wins)


def _pick_winner_by_tiebreak(teams: List[Team]) -> Team:
    # 1) RB残高が多い 2) 成績が悪い（勝ち数が少ない） 3) 乱数
    best_remaining = max(_team_rank_key_for_tiebreak(t)[0] for t in teams)
    stage1 = [t for t in teams if _team_rank_key_for_tiebreak(t)[0] == best_remaining]
    if len(stage1) == 1:
        return stage1[0]

    min_wins = min(int(getattr(t, "last_season_wins", getattr(t, "regular_wins", 15)) or 0) for t in stage1)
    stage2 = [t for t in stage1 if int(getattr(t, "last_season_wins", getattr(t, "regular_wins", 15)) or 0) == min_wins]
    if len(stage2) == 1:
        return stage2[0]
    return random.choice(stage2)


def _downrank_discount_for_one_pick(team: Team, player_meta: DraftCandidateMeta) -> int:
    """
    下位救済C案: 一本釣り（単独指名）の最低落札額を少し下げる。
    ここでは「所属ディビジョンが下がるほど」割引率を上げる（D1 < D2 < D3）。
    追加で、前年勝利数が少ないほど割引率を上げる（同一ディビジョン内の差）。
    （順位テーブルをSeason側で持つようになったら差し替える）
    """
    wins = int(getattr(team, "last_season_wins", getattr(team, "regular_wins", 15)) or 0)
    # 0〜30勝想定のざっくりスケール。下位ほど割引。
    if wins <= 6:
        rate = 0.22
    elif wins <= 10:
        rate = 0.16
    elif wins <= 14:
        rate = 0.10
    elif wins <= 18:
        rate = 0.06
    else:
        rate = 0.03

    league_level = int(getattr(team, "league_level", 1) or 1)
    # D1: +0, D2: +4%, D3: +8%
    div_bonus = {1: 0.00, 2: 0.04, 3: 0.08}.get(league_level, 0.00)
    rate = min(0.40, float(rate) + float(div_bonus))
    discount = int(round(player_meta.min_price * rate))
    return max(0, player_meta.min_price - discount)


def _set_drafted_player_contract(player: Player, slot: str, bid: int) -> None:
    """
    オークションドラフトでは「指名順固定給」ではなく、slot と bid を記録する。
    ただしゲーム内の salary フィールドが必要なので、当面は tier/slot で安全な固定値を使う。
    """
    player.acquisition_type = "draft"
    player.acquisition_note = f"auction_draft slot={slot} bid={int(bid)}"

    if slot == "A":
        player.contract_years_left = 3
        player.salary = 700_000
    else:
        player.contract_years_left = 2
        player.salary = 450_000

    player.years_pro = 0
    player.league_years = 0


def _add_player_to_team_and_trim(team: Team, player: Player, free_agents: List[Player]) -> None:
    team.add_player(player)

    # 13人超なら、最低OVRの非アイコンをFAへ。
    roster = list(getattr(team, "players", []) or [])
    if len(roster) <= 13:
        return

    candidates = [p for p in roster if not bool(getattr(p, "icon_locked", False))]
    if not candidates:
        return

    release = min(candidates, key=lambda p: (int(getattr(p, "ovr", 0) or 0), int(getattr(p, "age", 99) or 99)))
    if release is player:
        # どうしても枠が作れない場合は新人をFAへ（安全策）
        team.remove_player(player)
        player.contract_years_left = 0
        free_agents.append(player)
        return

    team.remove_player(release)
    release.contract_years_left = 0
    if int(getattr(release, "salary", 0) or 0) <= 0:
        release.salary = max(int(getattr(release, "ovr", 0) or 0) * 10_000, 300_000)
    free_agents.append(release)


def _ai_choose_target(team: Team, candidates: List[DraftCandidateMeta], used_ids: set[int]) -> Optional[DraftCandidateMeta]:
    if not candidates:
        return None

    coach_style = str(getattr(team, "coach_style", "balanced") or "balanced")
    scored: List[Tuple[float, DraftCandidateMeta]] = []
    for meta in candidates:
        if id(meta.player) in used_ids:
            continue
        p = meta.player
        v = float(meta.draft_value)

        # ポジション不足ボーナス（簡易）
        pos = str(getattr(p, "position", "") or "")
        same_pos = sum(1 for tp in getattr(team, "players", []) if str(getattr(tp, "position", "")) == pos)
        if same_pos <= 1:
            v += 1.8
        elif same_pos <= 2:
            v += 0.9

        # スタイル補正（安全に小さめ）
        try:
            if coach_style == "offense" and int(p.get_adjusted_attribute("shoot")) >= 70:
                v += 1.0
            elif coach_style == "defense" and int(p.get_adjusted_attribute("defense")) >= 70:
                v += 1.0
            elif coach_style == "development" and str(getattr(p, "potential", "C")).upper() in ("S", "A"):
                v += 0.8
        except Exception:
            pass

        v += random.uniform(-0.4, 0.4)
        scored.append((v, meta))

    if not scored:
        return None
    scored.sort(key=lambda row: row[0], reverse=True)
    return scored[0][1]


def _ai_bid_amount(team: Team, meta: DraftCandidateMeta, cap: int) -> int:
    """
    AIの一発入札。最小額をベースに、評価・RB残高・税段階で上限を決める。
    """
    base = int(meta.min_price)
    base_budget = int(getattr(team, "rookie_budget", cap) or cap)
    remaining = int(getattr(team, "rookie_budget_remaining", base_budget) or base_budget)
    spent = base_budget - remaining

    # 価値に応じた上乗せ。T1ほど強め。
    value = float(meta.draft_value)
    if meta.tier == "T1":
        bump = int(max(0, (value - 72.0) * 900_000))
    elif meta.tier == "T2":
        bump = int(max(0, (value - 66.0) * 450_000))
    else:
        bump = int(max(0, (value - 60.0) * 220_000))

    # 税が重くなるほど控える
    over = max(0, spent - cap)
    caution = 1.0
    if over >= 15_000_000:
        caution = 0.55
    elif over >= 5_000_000:
        caution = 0.75

    target = base + int(bump * caution)
    target = int(target + random.randint(-500_000, 1_200_000))
    target = max(base, target)

    # 使い切りすぎ防止（0人も戦略、をAI側にも少し反映）
    soft_max = int(base_budget * (0.92 if meta.tier == "T1" else 0.70))
    target = min(target, soft_max)
    return target


def conduct_auction_draft(
    teams: List[Team],
    draft_pool: List[Player],
    free_agents: Optional[List[Player]] = None,
    cap: int = CAP_DEFAULT,
):
    """
    正本: docs/DRAFT_AUCTION_SYSTEM.md
    - 同時指名
    - 一本釣り（単独指名）は最低額（下位救済Cで割引）
    - 競合は sealed-bid（1発入札）
    - 最大2人（枠A: T1/T2, 枠B: T3）
    """
    if free_agents is None:
        free_agents = []

    if not draft_pool:
        print("[DRAFT] draft pool is empty.")
        return

    print("\n=== Auction Draft (Rookie Budget) ===")

    # capは原則 Team.rookie_budget と一致させる（未設定ならcapを使う）
    cap = int(cap)
    for t in teams:
        if not hasattr(t, "rookie_budget") or getattr(t, "rookie_budget", None) is None:
            t.rookie_budget = cap
        if not hasattr(t, "rookie_budget_remaining") or getattr(t, "rookie_budget_remaining", None) is None:
            t.rookie_budget_remaining = int(getattr(t, "rookie_budget", cap) or cap)

    metas_by_id = _assign_tiers_and_min_prices(draft_pool)
    metas_list = list(metas_by_id.values())

    def eligible_metas(slot: str) -> List[DraftCandidateMeta]:
        if slot == "A":
            return [m for m in metas_list if m.tier in ("T1", "T2")]
        return [m for m in metas_list if m.tier == "T3"]

    # 各チームの獲得状況
    won_ids: Dict[int, List[int]] = {id(t): [] for t in teams}  # team_id -> [player_id...]
    used_player_ids: set[int] = set()

    def print_budget_table(title: str):
        print(f"\n[{title}] Rookie Budget Remaining")
        rows = sorted(
            teams,
            key=lambda t: (
                -int(getattr(t, "rookie_budget_remaining", getattr(t, "rookie_budget", cap) or cap) or 0),
                str(getattr(t, "name", "")),
            ),
        )
        for t in rows[:12]:
            base_budget = int(getattr(t, "rookie_budget", cap) or cap)
            remaining = int(getattr(t, "rookie_budget_remaining", base_budget) or base_budget)
            print(f"- {t.name:<24} RB:{remaining:,}/{base_budget:,}")

    def choose_targets(slot: str) -> Dict[int, Optional[int]]:
        cand = eligible_metas(slot)
        targets: Dict[int, Optional[int]] = {}

        print_budget_table(f"Slot {slot} - Before Targets")

        for team in teams:
            if len(won_ids[id(team)]) >= 2:
                targets[id(team)] = None
                continue

            if getattr(team, "is_user_team", False):
                print(f"\n--- Slot {slot} Target Selection | {team.name} ---")
                print("狙う選手を選んでください。0 を入力すると「今回は取らない」。")
                display = [m for m in cand if id(m.player) not in used_player_ids][:12]
                for i, m in enumerate(display, 1):
                    p = m.player
                    pot = str(getattr(p, "potential", "C"))
                    label = str(getattr(p, "draft_profile_label", "") or "")
                    label_text = f" | {label}" if label else ""
                    print(
                        f"{i:>2}. {p.name:<16} {getattr(p,'position','-'):<2} "
                        f"OVR:{getattr(p,'ovr',0):<2} Pot:{pot} | "
                        f"{TIER_CONFIGS[m.tier].name} | min:{m.min_price:,}{label_text}"
                    )
                while True:
                    raw = input("番号: ").strip()
                    if raw == "0":
                        targets[id(team)] = None
                        break
                    try:
                        idx = int(raw) - 1
                        if 0 <= idx < len(display):
                            targets[id(team)] = id(display[idx].player)
                            break
                    except ValueError:
                        pass
                    print("正しい番号を入力してください。")
            else:
                pick = _ai_choose_target(team, cand, used_player_ids)
                targets[id(team)] = None if pick is None else id(pick.player)

        return targets

    def reveal_targets(slot: str, targets: Dict[int, Optional[int]]):
        print(f"\n[Slot {slot}] Targets (公開)")
        by_player: Dict[int, List[Team]] = {}
        skips: List[Team] = []
        for team in teams:
            pid = targets.get(id(team))
            if pid is None:
                skips.append(team)
                continue
            by_player.setdefault(pid, []).append(team)

        # 競合の見せ方
        for pid, tlist in sorted(by_player.items(), key=lambda row: (-len(row[1]), row[0])):
            meta = metas_by_id.get(pid)
            if meta is None:
                continue
            p = meta.player
            names = ", ".join(t.name for t in tlist[:8])
            extra = f" (+{len(tlist) - 8} more)" if len(tlist) > 8 else ""
            tag = "競合" if len(tlist) >= 2 else "一本釣り"
            print(f"- {p.name:<18} {tag:<4} x{len(tlist):<2} | {names}{extra}")

        if skips:
            print(f"- SKIP: {len(skips)} teams")

    def resolve_slot(slot: str, targets: Dict[int, Optional[int]]):
        by_player: Dict[int, List[Team]] = {}
        for team in teams:
            pid = targets.get(id(team))
            if pid is None:
                continue
            if pid in used_player_ids:
                continue
            by_player.setdefault(pid, []).append(team)

        # 一本釣り→確定
        for pid, tlist in list(by_player.items()):
            if len(tlist) != 1:
                continue
            team = tlist[0]
            meta = metas_by_id.get(pid)
            if meta is None:
                continue
            p = meta.player
            min_price = _downrank_discount_for_one_pick(team, meta)
            charge, _ = _compute_charge_increment(team, min_price, cap)
            _apply_rookie_budget_charge(team, charge)
            _set_drafted_player_contract(p, slot=slot, bid=min_price)
            _add_player_to_team_and_trim(team, p, free_agents)
            won_ids[id(team)].append(pid)
            used_player_ids.add(pid)
            print(f"[DRAFT-ONEPICK] {team.name} won {p.name} at {min_price:,} (charge {charge:,})")
            by_player.pop(pid, None)

        # 競合→一発入札
        for pid, tlist in by_player.items():
            meta = metas_by_id.get(pid)
            if meta is None:
                continue
            p = meta.player
            print(f"\n[AUCTION] Slot {slot} | {p.name} | min:{meta.min_price:,} | bidders:{len(tlist)}")

            bids: Dict[int, int] = {}
            for team in tlist:
                if getattr(team, "is_user_team", False):
                    base_budget = int(getattr(team, "rookie_budget", cap) or cap)
                    remaining = int(getattr(team, "rookie_budget_remaining", base_budget) or base_budget)
                    print(f"\n--- 入札 | {team.name} ---")
                    print(f"RB 残高: {remaining:,}/{base_budget:,}")
                    print("※ 一発入札（sealed-bid）。勝っても負けても入札内容は公開してOK。")
                    print(f"最低落札額（基準）: {meta.min_price:,}")
                    while True:
                        raw = input("入札額（円）: ").strip().replace(",", "")
                        try:
                            amount = int(raw)
                            if amount < meta.min_price:
                                print("最低落札額以上を入力してください。")
                                continue
                            bids[id(team)] = amount
                            break
                        except ValueError:
                            print("数字を入力してください。")
                else:
                    bids[id(team)] = _ai_bid_amount(team, meta, cap)

            # 勝者決定
            max_bid = max(bids.values()) if bids else meta.min_price
            top = [team for team in tlist if bids.get(id(team), 0) == max_bid]
            winner = top[0] if len(top) == 1 else _pick_winner_by_tiebreak(top)
            win_bid = int(bids.get(id(winner), meta.min_price))

            charge, _ = _compute_charge_increment(winner, win_bid, cap)
            _apply_rookie_budget_charge(winner, charge)
            _set_drafted_player_contract(p, slot=slot, bid=win_bid)
            _add_player_to_team_and_trim(winner, p, free_agents)
            won_ids[id(winner)].append(pid)
            used_player_ids.add(pid)

            print(f"[DRAFT-WIN] {winner.name} won {p.name} at {win_bid:,} (charge {charge:,})")

    # Slot A then Slot B
    for slot in ("A", "B"):
        targets = choose_targets(slot)
        reveal_targets(slot, targets)
        resolve_slot(slot, targets)

    # 未獲得の候補はFAへ
    leftover = [m.player for m in metas_list if id(m.player) not in used_player_ids]
    if leftover:
        print(f"\n[DRAFT] Undrafted players -> FA: {len(leftover)}")
    for p in leftover:
        p.contract_years_left = 0
        if int(getattr(p, "salary", 0) or 0) <= 0:
            p.salary = max(int(getattr(p, "ovr", 0) or 0) * 10_000, 300_000)
        free_agents.append(p)

    # draft_pool を空にする（既存 conduct_draft と同じ契約）
    draft_pool.clear()

