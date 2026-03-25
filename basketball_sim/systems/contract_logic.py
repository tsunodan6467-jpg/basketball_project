from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


# =========================================================
# Contract System (Safe Foundation)
# ---------------------------------------------------------
# 目的:
# - 既存システムを壊さずに契約処理の責務を分離する
# - 再契約 / 契約満了 / FA移行の土台を作る
# - 将来の財政・交渉UI・サラリーキャップ拡張に耐える
#
# 設計方針:
# - Team / Player の既存属性を最大限そのまま使う
# - 新規属性が未定義でも落ちないように defensive に書く
# - offseason.py から少しずつ呼び出せる関数単位で構成する
# =========================================================


# -----------------------------
# constants
# -----------------------------
SALARY_CAP_DEFAULT = 9_000_000  # 開発用仮スケール: 現在の年俸水準に合わせたキャップ
SALARY_SOFT_LIMIT_MULTIPLIER = 1.20
MIN_SALARY_DEFAULT = 300_000
MAX_CONTRACT_YEARS_DEFAULT = 5

POTENTIAL_BONUS = {
    "S": 18_000_000,
    "A": 10_000_000,
    "B": 4_000_000,
    "C": 0,
    "D": -3_000_000,
}

AGE_SALARY_BONUS = {
    18: 12_000_000,
    19: 10_000_000,
    20: 8_000_000,
    21: 6_000_000,
    22: 4_000_000,
    23: 2_000_000,
}

ROLE_EXPECTATION_ORDER = ("star", "starter", "rotation", "bench")


# -----------------------------
# data classes
# -----------------------------
@dataclass
class ContractDemand:
    desired_salary: int
    desired_years: int
    role_expectation: str


@dataclass
class ReSignDecision:
    accepted: bool
    score: float
    threshold: float
    offered_salary: int
    offered_years: int
    reason: str


@dataclass
class ExpiringContractInfo:
    player: object
    team: object
    years_left_before_advance: int


# -----------------------------
# utility helpers
# -----------------------------
def clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, int(value)))



def safe_getattr_int(obj: object, attr_name: str, default: int = 0) -> int:
    try:
        return int(getattr(obj, attr_name, default))
    except Exception:
        return int(default)



def normalize_potential(raw: object) -> str:
    val = str(raw or "C").upper().strip()
    return val if val in POTENTIAL_BONUS else "C"



def get_all_team_players(teams: Iterable[object]) -> List[object]:
    players: List[object] = []
    for team in teams:
        for player in getattr(team, "players", []):
            players.append(player)
    return players



def get_team_payroll(team: object) -> int:
    return sum(safe_getattr_int(p, "salary", 0) for p in getattr(team, "players", []))



def get_team_player_rank(team: object, player: object) -> int:
    roster = sorted(
        getattr(team, "players", []),
        key=lambda p: safe_getattr_int(p, "ovr", 0),
        reverse=True,
    )
    for idx, p in enumerate(roster, 1):
        if getattr(p, "player_id", None) == getattr(player, "player_id", None):
            return idx
    return 99



def infer_role_expectation(team: object, player: object) -> str:
    rank = get_team_player_rank(team, player)
    if rank <= 2:
        return "star"
    if rank <= 5:
        return "starter"
    if rank <= 9:
        return "rotation"
    return "bench"



def set_contract_foundation_fields(player: object, team: Optional[object] = None) -> None:
    """
    既存 Player に契約系の不足属性を安全に補完する。
    models/player.py に今すぐ追加しなくても落ちないようにするための土台。
    """
    if not hasattr(player, "contract_total_years"):
        setattr(player, "contract_total_years", safe_getattr_int(player, "contract_years_left", 0))

    if not hasattr(player, "desired_salary"):
        setattr(player, "desired_salary", safe_getattr_int(player, "salary", 0))

    if not hasattr(player, "desired_years"):
        current_years = safe_getattr_int(player, "contract_years_left", 0)
        setattr(player, "desired_years", max(1, current_years))

    if not hasattr(player, "contract_role_expectation"):
        inferred = infer_role_expectation(team, player) if team is not None else "rotation"
        setattr(player, "contract_role_expectation", inferred)

    if not hasattr(player, "last_contract_team_id"):
        team_id = getattr(team, "team_id", None) if team is not None else getattr(player, "team_id", None)
        setattr(player, "last_contract_team_id", team_id)


# -----------------------------
# demand calculation
# -----------------------------
def calculate_desired_salary(player: object) -> int:
    """
    安全版の希望年俸計算。
    OVR主軸 + potential / age / popularity / career の軽補正。
    今後の本実装ではここを財政・市場・エージェント込みに拡張する。
    """
    ovr = safe_getattr_int(player, "ovr", 60)
    age = safe_getattr_int(player, "age", 22)
    popularity = safe_getattr_int(player, "popularity", 50)
    career_games = safe_getattr_int(player, "career_games_played", 0)
    peak_ovr = safe_getattr_int(player, "peak_ovr", ovr)
    potential = normalize_potential(getattr(player, "potential", "C"))

    # OVR主軸
    base_salary = ovr * 1_800_000

    # potential補正
    potential_bonus = POTENTIAL_BONUS[potential]

    # 年齢補正
    age_bonus = AGE_SALARY_BONUS.get(age, 0)
    if 24 <= age <= 28:
        age_bonus += 6_000_000
    elif 29 <= age <= 31:
        age_bonus += 2_000_000
    elif 32 <= age <= 34:
        age_bonus -= 5_000_000
    elif age >= 35:
        age_bonus -= 10_000_000

    # 人気補正
    popularity_bonus = max(0, popularity - 50) * 150_000

    # 実績補正
    experience_bonus = min(12_000_000, (career_games // 30) * 1_000_000)
    peak_bonus = max(0, peak_ovr - 75) * 700_000

    desired_salary = (
        base_salary
        + potential_bonus
        + age_bonus
        + popularity_bonus
        + experience_bonus
        + peak_bonus
    )

    return clamp_int(desired_salary, MIN_SALARY_DEFAULT, 500_000_000)



def calculate_desired_years(player: object) -> int:
    age = safe_getattr_int(player, "age", 22)
    ovr = safe_getattr_int(player, "ovr", 60)
    potential = normalize_potential(getattr(player, "potential", "C"))

    if age <= 22:
        years = 4 if potential in ("S", "A") else 3
    elif age <= 25:
        years = 4 if ovr >= 72 else 3
    elif age <= 29:
        years = 3 if ovr >= 75 else 2
    elif age <= 33:
        years = 2
    else:
        years = 1

    return clamp_int(years, 1, MAX_CONTRACT_YEARS_DEFAULT)



def update_player_contract_demand(player: object, team: Optional[object] = None) -> ContractDemand:
    set_contract_foundation_fields(player, team)

    desired_salary = calculate_desired_salary(player)
    desired_years = calculate_desired_years(player)

    setattr(player, "desired_salary", desired_salary)
    setattr(player, "desired_years", desired_years)

    role_expectation = getattr(player, "contract_role_expectation", None)
    if not role_expectation or role_expectation not in ROLE_EXPECTATION_ORDER:
        role_expectation = infer_role_expectation(team, player) if team is not None else "rotation"
        setattr(player, "contract_role_expectation", role_expectation)

    return ContractDemand(
        desired_salary=desired_salary,
        desired_years=desired_years,
        role_expectation=role_expectation,
    )


# -----------------------------
# contract advancing / expiry
# -----------------------------
def get_expiring_players(teams: Iterable[object]) -> List[ExpiringContractInfo]:
    expiring: List[ExpiringContractInfo] = []
    for team in teams:
        for player in getattr(team, "players", []):
            years_left = safe_getattr_int(player, "contract_years_left", 0)
            if years_left == 1:
                expiring.append(
                    ExpiringContractInfo(
                        player=player,
                        team=team,
                        years_left_before_advance=years_left,
                    )
                )
    return expiring



def advance_contract_years(
    teams: Iterable[object],
    free_agents: List[object],
    skip_player_ids: Optional[set] = None,
) -> List[Tuple[object, object]]:
    """
    契約年数を1年進め、満了した選手を FA に送る。
    return: [(player, former_team), ...]
    """
    if skip_player_ids is None:
        skip_player_ids = set()

    moved_to_fa: List[Tuple[object, object]] = []

    for team in teams:
        leaving_players: List[object] = []

        for player in list(getattr(team, "players", [])):
            player_id = getattr(player, "player_id", None)
            if player_id in skip_player_ids:
                continue

            current_years = safe_getattr_int(player, "contract_years_left", 0)
            setattr(player, "contract_years_left", current_years - 1)

            if safe_getattr_int(player, "contract_years_left", 0) <= 0:
                leaving_players.append(player)

        for player in leaving_players:
            if hasattr(team, "remove_player"):
                team.remove_player(player)
            else:
                team.players.remove(player)

            setattr(player, "team_id", None)
            setattr(player, "last_contract_team_id", getattr(team, "team_id", getattr(player, "last_contract_team_id", None)))

            if player not in free_agents:
                free_agents.append(player)
            moved_to_fa.append((player, team))

    return moved_to_fa


# -----------------------------
# re-sign evaluation
# -----------------------------
def calculate_role_satisfaction_score(team: object, player: object) -> float:
    expected_role = getattr(player, "contract_role_expectation", None)
    if expected_role not in ROLE_EXPECTATION_ORDER:
        expected_role = infer_role_expectation(team, player)

    current_role = infer_role_expectation(team, player)

    expected_idx = ROLE_EXPECTATION_ORDER.index(expected_role)
    current_idx = ROLE_EXPECTATION_ORDER.index(current_role)
    diff = current_idx - expected_idx

    if diff <= -1:
        return 100.0
    if diff == 0:
        return 85.0
    if diff == 1:
        return 55.0
    return 20.0



def calculate_team_context_score(team: object) -> float:
    league_level = safe_getattr_int(team, "league_level", 3)
    wins = safe_getattr_int(team, "last_season_wins", safe_getattr_int(team, "regular_wins", 15))
    popularity = safe_getattr_int(team, "popularity", 50)

    league_score_map = {1: 100.0, 2: 72.0, 3: 48.0}
    league_score = league_score_map.get(league_level, 48.0)
    win_score = (wins / 30.0) * 100.0
    popularity_score = float(popularity)

    return (league_score * 0.45) + (win_score * 0.35) + (popularity_score * 0.20)



def calculate_resign_score(
    team: object,
    player: object,
    offer_salary: int,
    offer_years: int,
) -> float:
    demand = update_player_contract_demand(player, team)
    loyalty = safe_getattr_int(player, "loyalty", 50)

    salary_ratio = offer_salary / max(1, demand.desired_salary)
    if salary_ratio >= 1.10:
        salary_score = 100.0
    elif salary_ratio >= 1.00:
        salary_score = 88.0
    elif salary_ratio >= 0.95:
        salary_score = 72.0
    elif salary_ratio >= 0.90:
        salary_score = 56.0
    else:
        salary_score = 30.0

    year_diff = abs(offer_years - demand.desired_years)
    if year_diff == 0:
        years_score = 100.0
    elif year_diff == 1:
        years_score = 70.0
    else:
        years_score = 35.0

    role_score = calculate_role_satisfaction_score(team, player)
    context_score = calculate_team_context_score(team)
    loyalty_score = float(loyalty)

    final_score = (
        salary_score * 0.42
        + years_score * 0.10
        + role_score * 0.18
        + context_score * 0.18
        + loyalty_score * 0.12
    )
    return round(final_score, 2)



def get_resign_threshold(player: object) -> float:
    age = safe_getattr_int(player, "age", 22)
    ovr = safe_getattr_int(player, "ovr", 60)
    loyalty = safe_getattr_int(player, "loyalty", 50)

    threshold = 64.0

    if ovr >= 85:
        threshold += 8.0
    elif ovr >= 80:
        threshold += 5.0
    elif ovr >= 75:
        threshold += 2.0

    if age >= 33:
        threshold -= 5.0
    elif age <= 22:
        threshold += 2.0

    if loyalty >= 75:
        threshold -= 5.0
    elif loyalty <= 35:
        threshold += 4.0

    return max(52.0, min(78.0, threshold))



def build_default_offer(player: object) -> Tuple[int, int]:
    demand = update_player_contract_demand(player)

    # 初期安全版: 需要額ほぼベース、端数は丸める
    offered_salary = int(round(demand.desired_salary / 1_000_000) * 1_000_000)
    offered_years = clamp_int(demand.desired_years, 1, MAX_CONTRACT_YEARS_DEFAULT)
    return offered_salary, offered_years



def would_offer_break_soft_limit(
    team: object,
    player: object,
    offer_salary: int,
    salary_cap: int = SALARY_CAP_DEFAULT,
    soft_multiplier: float = SALARY_SOFT_LIMIT_MULTIPLIER,
) -> bool:
    team_payroll = get_team_payroll(team)
    current_salary = safe_getattr_int(player, "salary", 0)
    projected_payroll = team_payroll - current_salary + offer_salary
    return projected_payroll > int(salary_cap * soft_multiplier)



def evaluate_resign(
    team: object,
    player: object,
    offer_salary: Optional[int] = None,
    offer_years: Optional[int] = None,
    salary_cap: int = SALARY_CAP_DEFAULT,
) -> ReSignDecision:
    if offer_salary is None or offer_years is None:
        default_salary, default_years = build_default_offer(player)
        offer_salary = default_salary if offer_salary is None else offer_salary
        offer_years = default_years if offer_years is None else offer_years

    if would_offer_break_soft_limit(team, player, offer_salary, salary_cap=salary_cap):
        return ReSignDecision(
            accepted=False,
            score=0.0,
            threshold=get_resign_threshold(player),
            offered_salary=offer_salary,
            offered_years=offer_years,
            reason="soft_cap_block",
        )

    score = calculate_resign_score(team, player, offer_salary, offer_years)
    threshold = get_resign_threshold(player)
    accepted = score >= threshold

    reason = "accepted" if accepted else "score_too_low"
    return ReSignDecision(
        accepted=accepted,
        score=score,
        threshold=threshold,
        offered_salary=offer_salary,
        offered_years=offer_years,
        reason=reason,
    )



def apply_resign(
    team: object,
    player: object,
    offer_salary: int,
    offer_years: int,
    season_label: Optional[int] = None,
) -> None:
    set_contract_foundation_fields(player, team)

    setattr(player, "salary", int(offer_salary))
    setattr(player, "contract_years_left", int(offer_years))
    setattr(player, "contract_total_years", int(offer_years))
    setattr(player, "team_id", getattr(team, "team_id", getattr(player, "team_id", None)))
    setattr(player, "last_contract_team_id", getattr(team, "team_id", getattr(player, "last_contract_team_id", None)))
    setattr(player, "desired_salary", int(offer_salary))
    setattr(player, "desired_years", int(offer_years))
    setattr(player, "contract_role_expectation", infer_role_expectation(team, player))

    if hasattr(player, "add_career_entry"):
        season = season_label if season_label is not None else max(1, safe_getattr_int(player, "years_pro", 0))
        player.add_career_entry(
            season=season,
            team_name=getattr(team, "name", "Unknown Team"),
            event="Re-sign",
            note=f"{offer_years}Y / {offer_salary:,}"
        )



def release_expired_players_to_fa(
    teams: Iterable[object],
    free_agents: List[object],
    season_label: Optional[int] = None,
    skip_player_ids: Optional[set] = None,
) -> List[Tuple[object, object]]:
    moved = advance_contract_years(teams, free_agents, skip_player_ids=skip_player_ids)

    for player, former_team in moved:
        if hasattr(player, "add_career_entry"):
            season = season_label if season_label is not None else max(1, safe_getattr_int(player, "years_pro", 0))
            player.add_career_entry(
                season=season,
                team_name=getattr(former_team, "name", "Unknown Team"),
                event="Contract Expired",
                note="Moved to Free Agency",
            )

    return moved


# -----------------------------
# convenience bootstrap
# -----------------------------
def initialize_contract_foundations_for_league(teams: Iterable[object], free_agents: Optional[Iterable[object]] = None) -> None:
    for team in teams:
        for player in getattr(team, "players", []):
            set_contract_foundation_fields(player, team)
            update_player_contract_demand(player, team)

    if free_agents is not None:
        for player in free_agents:
            set_contract_foundation_fields(player, None)
            update_player_contract_demand(player, None)
