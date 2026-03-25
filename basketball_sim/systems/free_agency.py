import random
from typing import List
from collections import defaultdict

from basketball_sim.models.team import Team
from basketball_sim.models.player import Player
from basketball_sim.systems.contract_logic import (
    SALARY_CAP_DEFAULT,
    SALARY_SOFT_LIMIT_MULTIPLIER,
    get_team_payroll,
)


MAX_FA_SIGNINGS = 3
MAX_FA_OFFERS_PER_TEAM = 6
MAX_DECLINES_PER_PLAYER = 2


def _team_salary(team: Team) -> int:
    return int(get_team_payroll(team))


def _team_wins(team: Team) -> int:
    return getattr(team, "last_season_wins", getattr(team, "regular_wins", 15))


def _soft_cap() -> int:
    return int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER)


def _cap_status(payroll: int) -> str:
    if payroll > _soft_cap():
        return "over_soft_cap"
    if payroll > SALARY_CAP_DEFAULT:
        return "over_cap"
    return "under_cap"


def _get_fa_profile(player: Player) -> dict:
    if hasattr(player, "get_free_agency_profile"):
        try:
            profile = player.get_free_agency_profile()
            if isinstance(profile, dict):
                return profile
        except Exception:
            pass

    return {
        "money": 50,
        "role": 50,
        "winning": 50,
        "fit": 50,
        "security": 50,
        "loyalty": int(getattr(player, "loyalty", 50)),
        "preferred_team_style": "",
        "preferred_coach_style": "",
        "fa_personality": "balanced",
    }


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
    return max(15.0, min(100.0, 52.0 * ratio))


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
    if payroll_before > SALARY_CAP_DEFAULT and years >= 3:
        years -= 1

    return max(1, min(4, years))


def _calculate_offer(team: Team, player: Player) -> int:
    payroll_before = _team_salary(team)
    soft_cap = _soft_cap()

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

    if payroll_before <= SALARY_CAP_DEFAULT < payroll_after:
        # cap超えは許容。ただし超えた瞬間の契約は少し控えめにする
        room_to_soft = max(0, soft_cap - payroll_before)
        offer = min(offer, room_to_soft)

    if payroll_before > SALARY_CAP_DEFAULT:
        # すでにcap超えなら、soft capまでの低額契約のみ許可
        room_to_soft = max(0, soft_cap - payroll_before)
        low_cost_limit = min(max(base, 0), 900_000)
        offer = min(offer, room_to_soft, low_cost_limit)

    payroll_after = payroll_before + offer
    if payroll_after > soft_cap:
        offer = max(0, soft_cap - payroll_before)

    return max(0, int(offer))


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
        security_score += max(-18.0, min(20.0, (years - desired_years) * 7.0))
    else:
        security_score += (years - 2) * 8.0
    if years >= 3:
        security_score += 6.0
    security_score = max(20.0, min(100.0, security_score))

    loyalty_bonus = 0.0
    if getattr(player, "last_contract_team_id", None) == getattr(team, "team_id", None):
        loyalty_bonus += int(profile.get("loyalty", 50)) * 0.12

    popularity = getattr(team, "popularity", 50)
    market_score = max(20.0, min(100.0, popularity * 0.9 + float(getattr(team, "market_size", 1.0)) * 8.0))

    weights = {
        "money": int(profile.get("money", 50)),
        "role": int(profile.get("role", 50)),
        "winning": int(profile.get("winning", 50)),
        "fit": int(profile.get("fit", 50)),
        "security": int(profile.get("security", 50)),
    }
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
    if hasattr(team, "can_add_player_by_japan_rule"):
        try:
            return bool(team.can_add_player_by_japan_rule(player))
        except Exception:
            pass

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
            status_before = _cap_status(payroll_before)

            offer = _calculate_offer(team, candidate)

            if offer <= 0:
                break

            payroll_after = payroll_before + offer
            status_after = _cap_status(payroll_after)

            fit_value = _get_strategy_fit(team, candidate)
            coach_fit_value = _get_coach_fit(team, candidate)
            contract_years = _determine_contract_years(candidate, team, offer)
            score = _offer_score(candidate, team, offer, contract_years)
            profile = _get_fa_profile(candidate)
            role_value = _estimate_role_opportunity(team, candidate)
            winning_value = _estimate_winning_score(team)

            team_offers[team.team_id] += 1

            print(
                f"[FA-OFFER] {team.name} offered ${offer:,} / {contract_years}y to {candidate.name} "
                f"| ovr={candidate.ovr} | personality={profile.get('fa_personality', 'balanced')} "
                f"| role={role_value:.1f} | win={winning_value:.1f} "
                f"| fit={fit_value:.1f} | coach_fit={coach_fit_value:.1f} "
                f"| score={score:.1f} | payroll={payroll_before:,}->{payroll_after:,} "
                f"| cap={SALARY_CAP_DEFAULT:,} | soft_cap={_soft_cap():,} "
                f"| status_before={status_before} | status_after={status_after}"
            )

            accept = False

            if score >= 68:
                accept = random.random() < 0.92
            elif score >= 63:
                accept = random.random() < 0.78
            elif score >= 58:
                accept = random.random() < 0.58
            elif score >= 54:
                accept = random.random() < 0.38
            elif score >= 50:
                accept = random.random() < 0.22

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

                team.money -= offer

                team_signings[team.team_id] += 1
                signed_players.add(candidate.player_id)

                print(
                    f"[FA] {team.name} signed {candidate.name} for ${offer:,} / {contract_years}y "
                    f"| Payroll:{payroll_after:,} / SoftCap:{_soft_cap():,} "
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
