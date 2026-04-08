import random
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from basketball_sim.config.game_constants import CONTRACT_ROSTER_MAX
from basketball_sim.models.team import Team
from basketball_sim.models.player import Player
from basketball_sim.systems.contract_logic import (
    calculate_fa_retention_bonus,
    fa_roll_accept_offer,
    get_team_payroll,
)
from basketball_sim.systems.salary_cap_budget import (
    cap_status as shared_cap_status,
    compute_luxury_tax,
    get_hard_cap,
    get_soft_cap as shared_get_soft_cap,
    league_level_for_team,
)


MAX_FA_SIGNINGS = 3
MAX_FA_OFFERS_PER_TEAM = 6
MAX_DECLINES_PER_PLAYER = 2

# 線形緩和（内分）係数。第一試行: docs/FA_PAYROLL_BUDGET_CLIP_LAMBDA_FIRST_TRIAL_DECISION_2026-04.md
_PAYROLL_BUDGET_CLIP_LAMBDA = 0.1


def _team_salary(team: Team) -> int:
    return int(get_team_payroll(team))


def _team_wins(team: Team) -> int:
    return getattr(team, "last_season_wins", getattr(team, "regular_wins", 15))


def _hard_cap(team: Team) -> int:
    return int(get_hard_cap(league_level=league_level_for_team(team)))


def _soft_cap(team: Team) -> int:
    # サラリー判定は salary_cap_budget の単一入口に寄せる（判定ズレ防止）
    return int(shared_get_soft_cap(league_level=league_level_for_team(team)))


def _cap_status(payroll: int, team: Team) -> str:
    return str(shared_cap_status(int(payroll), league_level=league_level_for_team(team)))


def _get_fa_profile(player: Player) -> dict:
    if hasattr(player, "get_free_agency_profile"):
        try:
            profile = player.get_free_agency_profile()
            if isinstance(profile, dict):
                return _merge_fa_profile_defaults(player, profile)
        except Exception:
            pass

    return _merge_fa_profile_defaults(
        player,
        {
            "money": 50,
            "role": 50,
            "winning": 50,
            "fit": 50,
            "security": 50,
            "loyalty": int(getattr(player, "loyalty", 50)),
            "preferred_team_style": "",
            "preferred_coach_style": "",
            "fa_personality": "balanced",
        },
    )


def _merge_fa_profile_defaults(player: Player, profile: dict) -> dict:
    """get_free_agency_profile の結果に、Player 側の志向（表示・重みは _negotiation_weights で合成）。"""
    out = dict(profile)
    pts = str(getattr(player, "preferred_team_style", "") or "").strip()
    pcs = str(getattr(player, "preferred_coach_style", "") or "").strip()
    if pts and not str(out.get("preferred_team_style", "") or "").strip():
        out["preferred_team_style"] = pts
    if pcs and not str(out.get("preferred_coach_style", "") or "").strip():
        out["preferred_coach_style"] = pcs
    pers = str(getattr(player, "fa_personality", "") or "").strip()
    if pers and pers != "balanced":
        out["fa_personality"] = pers
    return out


def _negotiation_weights(player: Player, profile: dict) -> dict:
    """
    交渉スコアの重み。プロファイル値と fa_priority_* の平均（希望条件の差が出やすい）。
    """
    weights: dict = {}
    for key in ("money", "role", "winning", "fit", "security"):
        base = int(profile.get(key, 50) or 50)
        fp = int(getattr(player, f"fa_priority_{key}", 50) or 50)
        weights[key] = max(1, min(99, (base + fp) // 2))
    return weights


def _estimate_role_opportunity(team: Team, player: Player) -> float:
    same_pos = [p for p in getattr(team, "players", []) if getattr(p, "position", "") == getattr(player, "position", "")]
    if not same_pos:
        return 85.0

    same_pos_sorted = sorted(same_pos, key=lambda p: getattr(p, "ovr", 60), reverse=True)
    top_ovr = getattr(same_pos_sorted[0], "ovr", 60)
    player_ovr = getattr(player, "ovr", 60)
    gap = int(player_ovr) - int(top_ovr)

    if gap >= 4:
        return 92.0
    if gap >= 0:
        return 78.0
    if gap >= -4:
        return 60.0
    if gap >= -8:
        return 42.0
    return 25.0


def _estimate_winning_score(team: Team) -> float:
    league_component = {1: 82.0, 2: 58.0, 3: 38.0}.get(getattr(team, "league_level", 3), 38.0)
    win_component = (_team_wins(team) / 30) * 100.0
    return league_component * 0.55 + win_component * 0.45


def _estimate_salary_score(player: Player, salary: int) -> float:
    desired_salary = int(getattr(player, "desired_salary", 0) or 0)
    current_salary = int(getattr(player, "salary", 0) or 0)
    baseline = max(300_000, desired_salary, current_salary)
    ratio = salary / max(1, baseline)
    score = max(15.0, min(100.0, 52.0 * ratio))
    # 希望年俸を下回るオファーは交渉スコアを下げる（差が大きいほど不満）
    if desired_salary > 0 and salary < desired_salary:
        gap = (desired_salary - salary) / max(1, desired_salary)
        score -= min(38.0, gap * 58.0)
    return max(15.0, min(100.0, score))


def _determine_contract_years(player: Player, team: Team, offer: int) -> int:
    profile = _get_fa_profile(player)
    security = int(profile.get("security", 50))
    age = int(getattr(player, "age", 27))
    ovr = int(getattr(player, "ovr", 60))
    desired_years = int(getattr(player, "desired_years", 0) or 0)

    years = 2
    if security >= 72:
        years = 3
    if security >= 84 and age <= 30:
        years = 4

    if age >= 33:
        years = min(years, 2)
    if age >= 36:
        years = 1

    if ovr <= 64 and age >= 30:
        years = min(years, 1)

    if desired_years > 0:
        if security >= 60:
            years = max(years, min(4, desired_years))
        else:
            years = min(years, max(1, min(3, desired_years)))

    payroll_before = _team_salary(team)
    if payroll_before > _hard_cap(team) and years >= 3:
        years -= 1

    return max(1, min(4, years))


def _clip_offer_to_payroll_budget(
    offer: int,
    payroll_before: int,
    payroll_budget: int,
) -> Tuple[int, Optional[int]]:
    """
    `payroll_budget` による room_to_budget クリップ（`_calculate_offer` / diagnostic 共通）。

    `payroll_budget <= 0` のときはクリップせず、(offer, None) を返す。
    room = max(0, payroll_budget - payroll_before) とし、
    - room == 0 なら clipped = 0
    - offer <= room なら clipped = offer
    - それ以外（offer > room > 0）は
      clipped = room + round(_PAYROLL_BUDGET_CLIP_LAMBDA * (offer - room))。
    λ=0 なら上式は room となり、従来の min(offer, room) と同値（テストで monkeypatch 確認）。
    """
    pb = int(payroll_budget)
    if pb <= 0:
        return int(offer), None
    room_to_budget = max(0, pb - payroll_before)
    offer_i = int(offer)
    room = room_to_budget

    if room == 0:
        clipped = 0
    elif offer_i <= room:
        clipped = offer_i
    else:
        lam = float(_PAYROLL_BUDGET_CLIP_LAMBDA)
        clipped = room + int(round(lam * (offer_i - room)))

    return clipped, room_to_budget


def _calculate_offer(team: Team, player: Player) -> int:
    payroll_before = _team_salary(team)
    soft_cap = _soft_cap(team)
    cap_base = _hard_cap(team)
    lv = league_level_for_team(team)

    # 意図的ゲート（偶発ではない）: payroll >= soft cap なら FA 新規オファー芯は 0。CPU/手動で同一 `_calculate_offer`。
    # 緩和・変更時は docs/FA_SOFT_CAP_POLICY_DECISION_MEMO_2026-04.md の決裁を先に更新すること。
    if payroll_before >= soft_cap:
        return 0

    base = int(getattr(player, "salary", 0))
    if base <= 0:
        base = max(int(getattr(player, "ovr", 60)) * 10_000, 300_000)

    surplus = max(0, int(getattr(team, "money", 0)) - base)
    bonus = int(surplus * 0.05)
    max_bonus = int(base * 0.25)
    bonus = min(bonus, max_bonus)

    offer = base + bonus

    payroll_after = payroll_before + offer

    if payroll_before <= cap_base < payroll_after:
        # cap超えは許容。ただし超えた瞬間の契約は少し控えめにする
        room_to_soft = max(0, soft_cap - payroll_before)
        offer = min(offer, room_to_soft)

    if payroll_before > cap_base:
        # すでにcap超えなら、soft capまでの低額契約のみ許可
        room_to_soft = max(0, soft_cap - payroll_before)
        low_cost_limit = min(max(base, 0), 900_000)
        offer = min(offer, room_to_soft, low_cost_limit)

    payroll_after = payroll_before + offer
    if payroll_after > soft_cap:
        offer = max(0, soft_cap - payroll_before)

    # クラブ予算（ある場合）を超えるオファーは圧縮する。
    # payroll_budget が未設定なら従来どおり soft cap 基準で扱う。
    payroll_budget = int(getattr(team, "payroll_budget", soft_cap) or soft_cap)
    offer, _ = _clip_offer_to_payroll_budget(offer, payroll_before, payroll_budget)

    # 贅沢税の増分が大きすぎる契約は一段圧縮（過剰な赤字契約を抑制）。
    tax_before = int(compute_luxury_tax(payroll_before, league_level=lv))
    tax_after = int(compute_luxury_tax(payroll_before + offer, league_level=lv))
    tax_delta = max(0, tax_after - tax_before)
    tax_warn = max(8_000_000, soft_cap // 200)
    if tax_delta >= tax_warn:
        offer = int(offer * 0.85)

    return max(0, int(offer))


def _calculate_offer_diagnostic(team: Team, player: Player) -> Dict[str, Any]:
    """
    `_calculate_offer` と同じ計算を段別に記録する観測専用関数（本番経路からは呼ばない想定）。

    **ロジックは `_calculate_offer` と同一に保つこと。** 変更時は両方を直し、
    `test_free_agency_offer_diagnostic` で `final_offer` 一致を確認する。
    """
    payroll_before = _team_salary(team)
    soft_cap = _soft_cap(team)
    cap_base = _hard_cap(team)
    lv = league_level_for_team(team)

    snap: Dict[str, Any] = {
        "payroll_before": payroll_before,
        "soft_cap": soft_cap,
        "cap_base": cap_base,
        "league_level": lv,
        "soft_cap_early": payroll_before >= soft_cap,
    }

    if payroll_before >= soft_cap:
        snap["final_offer"] = 0
        snap["base"] = None
        snap["room_to_budget"] = None
        return snap

    base = int(getattr(player, "salary", 0))
    if base <= 0:
        base = max(int(getattr(player, "ovr", 60)) * 10_000, 300_000)
    snap["base"] = base

    surplus = max(0, int(getattr(team, "money", 0)) - base)
    bonus = int(surplus * 0.05)
    max_bonus = int(base * 0.25)
    bonus = min(bonus, max_bonus)
    snap["surplus"] = surplus
    snap["bonus"] = bonus

    offer = base + bonus
    snap["offer_after_base_bonus"] = offer

    payroll_after = payroll_before + offer
    snap["payroll_after_initial"] = payroll_after

    if payroll_before <= cap_base < payroll_after:
        room_to_soft = max(0, soft_cap - payroll_before)
        offer = min(offer, room_to_soft)
        snap["hard_cap_bridge_applied"] = True
        snap["room_to_soft_bridge"] = room_to_soft
    else:
        snap["hard_cap_bridge_applied"] = False
        snap["room_to_soft_bridge"] = None
    snap["offer_after_hard_cap_bridge"] = offer

    if payroll_before > cap_base:
        room_to_soft = max(0, soft_cap - payroll_before)
        low_cost_limit = min(max(base, 0), 900_000)
        offer = min(offer, room_to_soft, low_cost_limit)
        snap["hard_cap_over_applied"] = True
        snap["room_to_soft_over"] = room_to_soft
        snap["low_cost_limit"] = low_cost_limit
    else:
        snap["hard_cap_over_applied"] = False
        snap["room_to_soft_over"] = None
        snap["low_cost_limit"] = None
    snap["offer_after_hard_cap_over"] = offer

    payroll_after = payroll_before + offer
    snap["payroll_after_pre_soft_pushback"] = payroll_after
    if payroll_after > soft_cap:
        offer = max(0, soft_cap - payroll_before)
        snap["soft_cap_pushback_applied"] = True
    else:
        snap["soft_cap_pushback_applied"] = False
    snap["offer_after_soft_cap_pushback"] = offer

    payroll_budget = int(getattr(team, "payroll_budget", soft_cap) or soft_cap)
    snap["payroll_budget"] = payroll_budget
    offer, room_to_budget = _clip_offer_to_payroll_budget(offer, payroll_before, payroll_budget)
    snap["room_to_budget"] = room_to_budget
    snap["offer_after_budget_clip"] = offer

    tax_before = int(compute_luxury_tax(payroll_before, league_level=lv))
    tax_after = int(compute_luxury_tax(payroll_before + offer, league_level=lv))
    tax_delta = max(0, tax_after - tax_before)
    tax_warn = max(8_000_000, soft_cap // 200)
    snap["tax_before"] = tax_before
    snap["tax_after_probe"] = tax_after
    snap["tax_delta"] = tax_delta
    snap["tax_warn"] = tax_warn
    if tax_delta >= tax_warn:
        offer = int(offer * 0.85)
        snap["luxury_tax_clip_applied"] = True
    else:
        snap["luxury_tax_clip_applied"] = False
    snap["offer_after_luxury_tax"] = offer

    snap["final_offer"] = max(0, int(offer))
    return snap


# -------------------------------------------------
# Fit evaluation
# -------------------------------------------------

def _get_strategy_fit(team: Team, player: Player) -> float:
    strategy = getattr(team, "strategy", "balanced")

    three = getattr(player, "three", 50)
    shoot = getattr(player, "shoot", 50)
    drive = getattr(player, "drive", 50)
    passing = getattr(player, "passing", 50)
    rebound = getattr(player, "rebound", 50)
    defense = getattr(player, "defense", 50)
    stamina = getattr(player, "stamina", 50)
    position = getattr(player, "position", "SF")

    if strategy == "balanced":
        return 0.0

    if strategy == "run_and_gun":
        fit = (
            (stamina - 60) * 0.08 +
            (drive - 60) * 0.06 +
            (passing - 60) * 0.05 +
            (three - 60) * 0.03
        )
        return max(-3.0, min(5.0, fit))

    if strategy == "three_point":
        fit = (
            (three - 60) * 0.12 +
            (shoot - 60) * 0.04
        )

        if position in ["PG", "SG", "SF"]:
            fit += 0.6

        if position == "C":
            fit -= 1.0

        return max(-3.0, min(5.0, fit))

    if strategy == "defense":
        fit = (
            (defense - 60) * 0.12 +
            (rebound - 60) * 0.04 +
            (stamina - 60) * 0.03
        )
        return max(-3.0, min(5.0, fit))

    if strategy == "inside":
        fit = (
            (rebound - 60) * 0.10 +
            (drive - 60) * 0.05 +
            (shoot - 60) * 0.03
        )

        if position in ["PF", "C"]:
            fit += 1.0

        if position in ["PG", "SG"]:
            fit -= 0.8

        return max(-3.0, min(5.0, fit))

    return 0.0


def _get_coach_fit(team: Team, player: Player) -> float:
    coach_style = getattr(team, "coach_style", "balanced")

    three = getattr(player, "three", 50)
    shoot = getattr(player, "shoot", 50)
    drive = getattr(player, "drive", 50)
    passing = getattr(player, "passing", 50)
    rebound = getattr(player, "rebound", 50)
    defense = getattr(player, "defense", 50)
    stamina = getattr(player, "stamina", 50)
    age = getattr(player, "age", 27)
    potential = getattr(player, "potential", "C")
    position = getattr(player, "position", "SF")

    if coach_style == "balanced":
        return 0.0

    if coach_style == "offense":
        fit = (
            (shoot - 60) * 0.05 +
            (three - 60) * 0.07 +
            (drive - 60) * 0.04 +
            (passing - 60) * 0.03
        )

        if position in ["PG", "SG", "SF"]:
            fit += 0.5

        return max(-2.0, min(4.0, fit))

    if coach_style == "defense":
        fit = (
            (defense - 60) * 0.08 +
            (rebound - 60) * 0.04 +
            (stamina - 60) * 0.03
        )

        if position in ["PF", "C"]:
            fit += 0.4

        return max(-2.0, min(4.0, fit))

    if coach_style == "development":
        fit = 0.0

        if age <= 24:
            fit += 1.5
        elif age >= 31:
            fit -= 0.8

        if potential == "A":
            fit += 1.5
        elif potential == "B":
            fit += 0.8
        elif potential == "D":
            fit -= 0.5

        return max(-2.0, min(4.0, fit))

    return 0.0


# -------------------------------------------------
# Evaluation
# -------------------------------------------------

def _offer_score(player: Player, team: Team, salary: int, years: int) -> float:
    profile = _get_fa_profile(player)

    salary_score = _estimate_salary_score(player, salary)
    role_score = _estimate_role_opportunity(team, player)
    winning_score = _estimate_winning_score(team)

    strategy_fit = _get_strategy_fit(team, player)
    coach_fit = _get_coach_fit(team, player)
    preferred_team_style = str(profile.get("preferred_team_style", "") or "")
    preferred_coach_style = str(profile.get("preferred_coach_style", "") or "")

    fit_score = 55.0 + strategy_fit * 6.0 + coach_fit * 5.0
    if preferred_team_style and preferred_team_style == getattr(team, "strategy", "balanced"):
        fit_score += 8.0
    if preferred_coach_style and preferred_coach_style == getattr(team, "coach_style", "balanced"):
        fit_score += 6.0
    fit_score = max(15.0, min(100.0, fit_score))

    desired_years = int(getattr(player, "desired_years", 0) or 0)
    security_score = 55.0
    if desired_years > 0:
        # 提示年数が希望より短いほど「安定志向（security 重み）」で減点が効く
        security_score += max(-22.0, min(24.0, (years - desired_years) * 8.5))
    else:
        security_score += (years - 2) * 8.0
    if years >= 3:
        security_score += 6.0
    security_score = max(20.0, min(100.0, security_score))

    # 旧所属クラブからのオファー（引き留め・復帰）
    loyalty_bonus = float(calculate_fa_retention_bonus(player, team))

    popularity = getattr(team, "popularity", 50)
    market_score = max(20.0, min(100.0, popularity * 0.9 + float(getattr(team, "market_size", 1.0)) * 8.0))

    weights = _negotiation_weights(player, profile)
    total_weight = max(1, sum(weights.values()))

    weighted_score = (
        salary_score * weights["money"]
        + role_score * weights["role"]
        + winning_score * weights["winning"]
        + fit_score * weights["fit"]
        + security_score * weights["security"]
    ) / total_weight

    personality = str(profile.get("fa_personality", "balanced"))
    if personality == "money":
        weighted_score += (salary_score - 55.0) * 0.10
    elif personality == "winning":
        weighted_score += (winning_score - 55.0) * 0.10
    elif personality == "role":
        weighted_score += (role_score - 55.0) * 0.10
    elif personality == "fit":
        weighted_score += (fit_score - 55.0) * 0.10
    elif personality == "security":
        weighted_score += (security_score - 55.0) * 0.10
    elif personality == "loyal":
        loyalty_bonus += 5.0

    return weighted_score + loyalty_bonus + (market_score - 50.0) * 0.05




def can_team_sign_player_by_japan_rule(team: Team, player: Player) -> bool:
    try:
        from basketball_sim.systems.roster_rules import can_add_contract_player

        ok, _ = can_add_contract_player(team, player)
        return bool(ok)
    except Exception:
        pass

    if hasattr(team, "can_add_player_by_japan_rule"):
        try:
            if not bool(team.can_add_player_by_japan_rule(player)):
                return False
        except Exception:
            pass

    if len(getattr(team, "players", []) or []) >= CONTRACT_ROSTER_MAX:
        return False

    nationality = str(getattr(player, "nationality", "") or "")
    foreign_count = 0
    asia_nat_count = 0

    for existing in getattr(team, "players", []):
        existing_nat = str(getattr(existing, "nationality", "") or "")
        if existing_nat == "Foreign":
            foreign_count += 1
        if existing_nat in ("Asia", "Naturalized"):
            asia_nat_count += 1

    if nationality == "Foreign":
        return foreign_count < 3
    if nationality in ("Asia", "Naturalized"):
        return asia_nat_count < 1
    return True

def _get_candidate_priority(team: Team, player: Player) -> float:
    ovr = getattr(player, "ovr", 60)
    strategy_fit = _get_strategy_fit(team, player)
    coach_fit = _get_coach_fit(team, player)
    age = getattr(player, "age", 27)

    age_bonus = 0.0

    if age <= 24:
        age_bonus = 0.8
    elif age >= 33:
        age_bonus = -0.8

    return ovr + strategy_fit + coach_fit + age_bonus


# -------------------------------------------------
# History
# -------------------------------------------------

def _set_fa_acquisition(player: Player, team: Team):
    player.acquisition_type = "free_agent"
    player.acquisition_note = f"fa_signed_by_{team.name}"


def _record_team_fa_history(team: Team, player: Player, offer: int, years: int):
    if hasattr(team, "add_history_transaction"):
        note = (
            f"fa_signing | "
            f"player={player.name} | "
            f"ovr={player.ovr} | "
            f"salary={offer} | "
            f"years={years}"
        )

        team.add_history_transaction(
            transaction_type="free_agent",
            player=player,
            note=note
        )


def _record_player_fa_career(player: Player, team: Team, years: int):
    if hasattr(player, "add_career_entry"):
        season_value = max(1, getattr(player, "years_pro", 0) + 1)

        player.add_career_entry(
            season=season_value,
            team_name=team.name,
            event="FA",
            note=f"Free Agent Signing ({years}y)"
        )


# -------------------------------------------------
# Main Free Agency
# -------------------------------------------------

def conduct_free_agency(teams: List[Team], free_agents: List[Player]):
    print("Conducting Free Agency...")

    signed_players = set()
    team_signings = defaultdict(int)
    team_offers = defaultdict(int)
    fa_declines = defaultdict(int)

    random.shuffle(teams)
    teams.sort(key=lambda t: _team_wins(t))

    for team in teams:
        while len(team.players) < 13 and free_agents:
            if team_signings[team.team_id] >= MAX_FA_SIGNINGS:
                break

            if team_offers[team.team_id] >= MAX_FA_OFFERS_PER_TEAM:
                break

            candidate_pool = sorted(
                [
                    p for p in free_agents
                    if can_team_sign_player_by_japan_rule(team, p)
                ],
                key=lambda p: _get_candidate_priority(team, p),
                reverse=True
            )

            top_targets = candidate_pool[:5]

            if not top_targets:
                break

            candidate = random.choice(top_targets)

            if candidate.player_id in signed_players:
                break

            payroll_before = _team_salary(team)
            status_before = _cap_status(payroll_before, team)

            offer = _calculate_offer(team, candidate)

            if offer <= 0:
                break

            try:
                from basketball_sim.systems.free_agent_market import get_team_fa_signing_limit

                signing_room = int(get_team_fa_signing_limit(team))
            except Exception:
                signing_room = max(0, _soft_cap(team) - payroll_before)

            if offer > signing_room:
                print(
                    f"[FA-CAP] {team.name} skipped {candidate.name} "
                    f"(offer {offer:,}円 > room {signing_room:,}円)"
                )
                continue

            payroll_after = payroll_before + offer
            status_after = _cap_status(payroll_after, team)

            fit_value = _get_strategy_fit(team, candidate)
            coach_fit_value = _get_coach_fit(team, candidate)
            contract_years = _determine_contract_years(candidate, team, offer)
            score = _offer_score(candidate, team, offer, contract_years)
            profile = _get_fa_profile(candidate)
            role_value = _estimate_role_opportunity(team, candidate)
            winning_value = _estimate_winning_score(team)

            team_offers[team.team_id] += 1

            print(
                f"[FA-OFFER] {team.name} offered {offer:,}円 / {contract_years}y to {candidate.name} "
                f"| ovr={candidate.ovr} | personality={profile.get('fa_personality', 'balanced')} "
                f"| role={role_value:.1f} | win={winning_value:.1f} "
                f"| fit={fit_value:.1f} | coach_fit={coach_fit_value:.1f} "
                f"| score={score:.1f} | payroll={payroll_before:,}->{payroll_after:,} "
                f"| cap={_hard_cap(team):,} | soft_cap={_soft_cap(team):,} "
                f"| status_before={status_before} | status_after={status_after}"
            )

            accept = fa_roll_accept_offer(score)

            if accept:
                if not can_team_sign_player_by_japan_rule(team, candidate):
                    print(
                        f"[FA-BLOCK] {team.name} could not sign {candidate.name} "
                        f"because Japan-rule slots are full"
                    )
                    break

                free_agents.remove(candidate)

                candidate.salary = offer
                candidate.contract_years_left = contract_years
                candidate.contract_total_years = contract_years
                candidate.desired_salary = max(int(getattr(candidate, "desired_salary", 0) or 0), offer)
                candidate.desired_years = contract_years
                candidate.last_contract_team_id = getattr(team, "team_id", None)

                _set_fa_acquisition(candidate, team)
                _record_team_fa_history(team, candidate, offer, contract_years)

                team.add_player(candidate)

                _record_player_fa_career(candidate, team, contract_years)

                # 年俸の money 即時減算は行わない（R1 / 締めのみ方式）。payroll はオフ締めで集計。

                team_signings[team.team_id] += 1
                signed_players.add(candidate.player_id)

                print(
                    f"[FA] {team.name} signed {candidate.name} for {offer:,}円 / {contract_years}y "
                    f"| Payroll:{payroll_after:,} / SoftCap:{_soft_cap(team):,} "
                    f"| status_after={status_after}"
                )

            else:
                print(f"[FA-DECLINE] {candidate.name} declined offer from {team.name}")

                fa_declines[candidate.player_id] += 1

                if fa_declines[candidate.player_id] >= MAX_DECLINES_PER_PLAYER:
                    free_agents.remove(candidate)

                    print(
                        f"[FA-CLOSED] {candidate.name} is no longer considering offers this offseason"
                    )

                break

    return free_agents
