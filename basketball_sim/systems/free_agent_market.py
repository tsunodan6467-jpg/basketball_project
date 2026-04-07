from typing import List, Optional, Tuple
import random

from basketball_sim.config.game_constants import PLAYER_SALARY_BASE_PER_OVR
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.season_transaction_rules import cpu_inseason_fa_allowed_for_simulated_round
from basketball_sim.systems.contract_logic import get_team_payroll
from basketball_sim.systems.salary_cap_budget import get_hard_cap, get_soft_cap, league_level_for_team


FA_SOFT_CAP_SIGNING_BUFFER_RATIO = 0.08
FA_SOFT_CAP_MIN_ROOM = 8_000_000


def ensure_fa_market_fields(player: Player) -> None:
    """
    FA市場用の安全補完。
    既存セーブでも落ちにくいように最低限の属性を埋める。
    """
    if not hasattr(player, "fa_years_waiting") or player.fa_years_waiting is None:
        player.fa_years_waiting = 0

    if not hasattr(player, "is_retired"):
        player.is_retired = False

    if not hasattr(player, "salary") or player.salary is None:
        player.salary = max(getattr(player, "ovr", 0) * PLAYER_SALARY_BASE_PER_OVR, 300000)

    if not hasattr(player, "contract_years_left") or player.contract_years_left is None:
        player.contract_years_left = 0

    if not hasattr(player, "team_id"):
        player.team_id = None



def ensure_team_fa_market_fields(team: Team) -> None:
    """
    Team側の最低限の安全補完。
    """
    if not hasattr(team, "money") or team.money is None:
        team.money = 2_000_000_000

    if not hasattr(team, "players") or team.players is None:
        team.players = []



def normalize_free_agents(free_agents: List[Player]) -> List[Player]:
    """
    retired選手を除外しつつ、必要属性を補完して返す。
    """
    normalized: List[Player] = []

    for player in free_agents:
        ensure_fa_market_fields(player)
        if getattr(player, "is_retired", False):
            continue
        normalized.append(player)

    return normalized



def estimate_fa_market_value(player: Player) -> int:
    """
    FA市場でのざっくり年俸目安。
    将来は契約ロジックと統合できるように単独関数化。
    """
    ensure_fa_market_fields(player)

    ovr = int(getattr(player, "ovr", 0))
    age = int(getattr(player, "age", 25))
    potential = str(getattr(player, "potential", "C")).upper()
    fa_wait = int(getattr(player, "fa_years_waiting", 0))

    base = max(ovr * 12000, 400000)

    potential_bonus_map = {
        "S": 250000,
        "A": 180000,
        "B": 100000,
        "C": 0,
        "D": -80000,
    }
    base += potential_bonus_map.get(potential, 0)

    if age <= 23:
        base += 120000
    elif age >= 35:
        base -= 220000
    elif age >= 32:
        base -= 120000

    if fa_wait >= 1:
        base -= 80000
    if fa_wait >= 2:
        base -= 120000
    if fa_wait >= 3:
        base -= 150000

    return max(300000, int(base))



def estimate_fa_contract_years(player: Player) -> int:
    """
    FA契約の安全版年数。
    """
    age = int(getattr(player, "age", 25))
    potential = str(getattr(player, "potential", "C")).upper()

    if age <= 22 and potential in ("S", "A"):
        return 3
    if age <= 28:
        return 2
    if age <= 33:
        return 1
    return 1



def evaluate_team_need_for_player(team: Team, player: Player) -> float:
    """
    チーム需要を簡易評価。
    ポジション不足と若干の戦術適性だけ見る安全版。
    """
    ensure_team_fa_market_fields(team)
    ensure_fa_market_fields(player)

    base_score = float(getattr(player, "ovr", 0))

    player_position = getattr(player, "position", "SF")
    same_pos = sum(1 for p in getattr(team, "players", []) if getattr(p, "position", "SF") == player_position)

    need_bonus = 0.0
    if same_pos <= 1:
        need_bonus += 6.0
    elif same_pos <= 2:
        need_bonus += 3.0

    coach_style = getattr(team, "coach_style", "balanced")
    style_bonus = 0.0

    try:
        if coach_style == "offense":
            if player.get_adjusted_attribute("shoot") >= 70:
                style_bonus += 2.0
        elif coach_style == "defense":
            if player.get_adjusted_attribute("defense") >= 70:
                style_bonus += 2.0
        elif coach_style == "development":
            if str(getattr(player, "potential", "C")).upper() in ("S", "A"):
                style_bonus += 2.0
    except Exception:
        pass

    age = int(getattr(player, "age", 25))
    age_bonus = 0.0
    if age <= 24:
        age_bonus += 1.5
    elif age >= 34:
        age_bonus -= 1.5

    return round(base_score + need_bonus + style_bonus + age_bonus, 2)



def get_team_fa_signing_limit(
    team: Team,
    salary_cap: Optional[int] = None,
) -> int:
    """
    FA契約に使える簡易上限。

    - キャップ未満: 上限まで契約余地あり
    - キャップちょうど〜超過: ルール上は FA 追加不可（市場側の簡易モデル）

    上限額は salary_cap_budget.get_soft_cap（＝リーグ年俸上限 12 億・get_hard_cap と同一）と同一。
    salary_cap を省略時はチーム所属ディビジョンのリーグ年俸上限を使用。
    """
    ensure_team_fa_market_fields(team)

    payroll = get_team_payroll(team)
    if salary_cap is None:
        salary_cap = int(get_hard_cap(league_level=league_level_for_team(team)))
    soft_cap_limit = int(get_soft_cap(salary_cap))

    if payroll >= soft_cap_limit:
        return 0

    if payroll < salary_cap:
        return max(0, soft_cap_limit - payroll)

    buffer_limit = max(FA_SOFT_CAP_MIN_ROOM, int(salary_cap * FA_SOFT_CAP_SIGNING_BUFFER_RATIO))
    return max(0, min(buffer_limit, soft_cap_limit - payroll))



def precheck_user_fa_sign(
    team: Team,
    player: Player,
    *,
    contract_salary: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    GUI 向け: `sign_free_agent` 実行前の可否と簡潔な理由。

    `sign_free_agent` は所持金を見ないため、ここで `can_team_afford_free_agent` も含める。

    `contract_salary` を渡した場合（オフ手動FA・本格FA同型オファー）、その額で所持金・
    サラリー余地を判定する。未指定時は従来どおり `estimate_fa_market_value`。
    """
    from basketball_sim.config.game_constants import CONTRACT_ROSTER_MAX
    from basketball_sim.systems.roster_rules import can_add_contract_player

    ensure_team_fa_market_fields(team)
    ensure_fa_market_fields(player)

    ok_roster, roster_msg = can_add_contract_player(team, player)
    if not ok_roster:
        code = roster_msg or ""
        if code == "contract_roster_full":
            return False, f"本契約ロスターが上限（{CONTRACT_ROSTER_MAX}人）に達しています。"
        if code == "nationality_slot":
            return False, "国籍枠の都合により追加できません。"
        return False, code or "ロスターに追加できません。"

    if not can_team_sign_player_by_japan_rule(team, player):
        return False, "国籍枠・チームルールにより契約できません。"

    if contract_salary is not None:
        sal = int(contract_salary)
        if sal <= 0:
            return False, "本格FAと同型のオファー額が算出できません（0円以下）。"
        afford = can_team_afford_fa_salary(team, sal)
        label = "契約年俸（本格FA同型）"
    else:
        sal = int(estimate_fa_market_value(player))
        afford = can_team_afford_free_agent(team, player)
        label = "年俸目安"

    if not afford:
        room = int(get_team_fa_signing_limit(team))
        money = int(getattr(team, "money", 0) or 0)
        if money < sal:
            return False, f"所持金が不足しています（{label} {sal:,} 円、所持 {money:,} 円）。"
        return False, (
            f"サラリー上限の契約余地が不足しています（{label} {sal:,} 円、余地 {room:,} 円）。"
        )

    return True, ""


def can_team_afford_free_agent(
    team: Team,
    player: Player,
    salary_cap: Optional[int] = None,
) -> bool:
    """
    所持金 + サラリーキャップの両方で判定する。
    """
    ensure_team_fa_market_fields(team)
    ask = estimate_fa_market_value(player)
    return can_team_afford_fa_salary(team, ask, salary_cap=salary_cap)


def can_team_afford_fa_salary(
    team: Team,
    ask: int,
    salary_cap: Optional[int] = None,
) -> bool:
    """明示年俸 `ask` で所持金・サラリー契約余地を判定（オフ手動FAの本格FA同型オファー用）。"""
    ensure_team_fa_market_fields(team)
    ask = int(ask)
    if int(getattr(team, "money", 0)) < ask:
        return False
    signing_limit = get_team_fa_signing_limit(team, salary_cap=salary_cap)
    return ask <= signing_limit



def can_team_sign_player_by_japan_rule(team: Team, player: Player) -> bool:
    """
    日本独自ルール用の安全チェック。

    優先順位:
    1. roster_rules.can_add_contract_player（本契約13＋国籍）
    2. Team の can_add_player_by_japan_rule
    3. nationality フォールバック

    目的は CPU FA が明確な枠超過契約をしないようにすること。
    """
    ensure_team_fa_market_fields(team)
    ensure_fa_market_fields(player)

    try:
        from basketball_sim.systems.roster_rules import can_add_contract_player

        ok, _ = can_add_contract_player(team, player)
        return bool(ok)
    except Exception:
        pass

    can_add = getattr(team, "can_add_player_by_japan_rule", None)
    if callable(can_add):
        try:
            return bool(can_add(player))
        except Exception:
            pass

    players = list(getattr(team, "players", []) or [])
    nationality = str(getattr(player, "nationality", "Japan") or "Japan")

    foreign_count = 0
    asia_nat_count = 0
    for existing in players:
        existing_nat = str(getattr(existing, "nationality", "Japan") or "Japan")
        if existing_nat == "Foreign":
            foreign_count += 1
        elif existing_nat in ("Asia", "Naturalized"):
            asia_nat_count += 1

    if nationality == "Foreign":
        return foreign_count < 3
    if nationality in ("Asia", "Naturalized"):
        return asia_nat_count < 1
    return True



def pick_best_free_agent_for_team(team: Team, free_agents: List[Player]) -> Optional[Player]:
    """
    チーム視点で最も欲しいFAを1人返す。
    """
    candidates = []

    for player in free_agents:
        ensure_fa_market_fields(player)
        if getattr(player, "is_retired", False):
            continue
        if not can_team_afford_free_agent(team, player):
            continue
        if not can_team_sign_player_by_japan_rule(team, player):
            continue

        score = evaluate_team_need_for_player(team, player)
        score += random.uniform(-0.5, 0.5)
        candidates.append((score, player))

    if not candidates:
        return None

    candidates.sort(key=lambda row: row[0], reverse=True)
    return candidates[0][1]



def sign_free_agent(
    team: Team,
    player: Player,
    *,
    contract_salary: Optional[int] = None,
    contract_years: Optional[int] = None,
) -> None:
    """
    FA契約を反映。
    日本独自ルールの最終ガードもここで行う。

    年俸相当の `money` 即時減算は行わない（R1 / 締めのみ方式）。
    年俸コストはオフ `_process_team_finances` の payroll → `record_financial_result` に一元化する。

    `contract_salary` / `contract_years` を指定した場合（オフ手動FA・CPU本格FA同型のオファー）、
    それをそのまま適用する。未指定時は `estimate_fa_market_value` / `estimate_fa_contract_years`。
    """
    ensure_team_fa_market_fields(team)
    ensure_fa_market_fields(player)

    if not can_team_sign_player_by_japan_rule(team, player):
        return

    if contract_salary is not None:
        salary = int(contract_salary)
        years = (
            int(contract_years)
            if contract_years is not None
            else int(estimate_fa_contract_years(player))
        )
    else:
        salary = int(estimate_fa_market_value(player))
        years = int(estimate_fa_contract_years(player))

    if salary <= 0:
        return

    signing_room = int(get_team_fa_signing_limit(team))
    if salary > signing_room:
        return

    player.salary = salary
    player.contract_years_left = years
    player.fa_years_waiting = 0

    if hasattr(player, "contract_total_years"):
        player.contract_total_years = years
    if hasattr(player, "last_contract_team_id"):
        player.last_contract_team_id = getattr(team, "team_id", None)
    if hasattr(player, "acquisition_type"):
        player.acquisition_type = "free_agent"
    if hasattr(player, "acquisition_note"):
        player.acquisition_note = f"signed_by_{getattr(team, 'name', 'unknown_team')}"

    if hasattr(team, "add_player"):
        team.add_player(player)
    else:
        team.players.append(player)
        player.team_id = getattr(team, "team_id", None)

    if hasattr(team, "add_history_transaction"):
        team.add_history_transaction(
            transaction_type="free_agent_sign",
            player=player,
            note=f"salary={salary} | years={years}",
        )


def offseason_manual_fa_offer_and_years(team: Team, player: Player) -> Tuple[int, int]:
    """
    オフ手動FA（`conduct_free_agency` 直前）専用: CPU 本格FA と同じ
    `free_agency._calculate_offer` / `_determine_contract_years` による年俸・契約年数。
    `conduct_free_agency` 本体は変更しない（同関数を読むだけ）。
    """
    from basketball_sim.systems.free_agency import _calculate_offer, _determine_contract_years

    offer = int(_calculate_offer(team, player))
    if offer <= 0:
        return 0, 1
    years = int(_determine_contract_years(player, team, offer))
    return offer, max(1, years)


def age_free_agents_one_year(free_agents: List[Player]) -> None:
    """
    オフシーズンごとにFA待機年数を進める。
    """
    for player in free_agents:
        ensure_fa_market_fields(player)
        if getattr(player, "is_retired", False):
            continue
        player.fa_years_waiting += 1



def calculate_fa_retirement_probability(player: Player) -> float:
    """
    FA選手用の引退確率。
    - 高齢
    - 低OVR
    - 長期FA
    で上がる
    - peak_ovr が高い元スターはやや粘る
    """
    ensure_fa_market_fields(player)

    age = int(getattr(player, "age", 25))
    ovr = int(getattr(player, "ovr", 0))
    peak_ovr = int(getattr(player, "peak_ovr", ovr))
    fa_wait = int(getattr(player, "fa_years_waiting", 0))

    prob = 0.0

    if age >= 38:
        prob += 0.45
    elif age >= 35:
        prob += 0.22
    elif age >= 32:
        prob += 0.08

    if ovr <= 58:
        prob += 0.20
    elif ovr <= 64:
        prob += 0.10

    if fa_wait >= 1:
        prob += 0.08
    if fa_wait >= 2:
        prob += 0.16
    if fa_wait >= 3:
        prob += 0.24

    if peak_ovr >= 85:
        prob -= 0.12
    elif peak_ovr >= 80:
        prob -= 0.06

    return max(0.01, min(0.95, round(prob, 3)))



def retire_stale_free_agents(free_agents: List[Player]) -> Tuple[List[Player], List[Player]]:
    """
    FA市場から引退する選手を処理。
    戻り値:
    - remaining_free_agents
    - retired_players
    """
    remaining: List[Player] = []
    retired: List[Player] = []

    for player in free_agents:
        ensure_fa_market_fields(player)

        if getattr(player, "is_retired", False):
            retired.append(player)
            continue

        prob = calculate_fa_retirement_probability(player)
        if random.random() < prob:
            player.is_retired = True
            retired.append(player)
        else:
            remaining.append(player)

    return remaining, retired



def maintain_minimum_fa_pool(
    free_agents: List[Player],
    target_minimum: int,
    generator_func=None,
) -> List[Player]:
    """
    FA市場が枯れすぎないように最低人数を維持する。
    generator_func は Player を1人返す関数を想定。
    """
    normalized = normalize_free_agents(free_agents)

    if generator_func is None:
        return normalized

    while len(normalized) < max(0, int(target_minimum)):
        try:
            player = generator_func()
        except Exception:
            break

        ensure_fa_market_fields(player)
        player.contract_years_left = 0
        player.team_id = None
        normalized.append(player)

    return normalized



def run_cpu_fa_market_cycle(
    teams: List[Team],
    free_agents: List[Player],
    max_signings_per_team: int = 1,
    *,
    simulated_round: Optional[int] = None,
) -> List[str]:
    """
    CPUチームがFAを拾う簡易サイクル。
    シーズン中FA補強の土台として使える安全版。

    simulated_round: シーズンシミュレーション中のラウンド番号（1始まり）を渡すと、
    レギュラー中トレード/FA締切後は処理しない（空リストを返す）。オフ等で呼ぶ場合は None。
    """
    if simulated_round is not None and not cpu_inseason_fa_allowed_for_simulated_round(
        int(simulated_round)
    ):
        return []

    logs: List[str] = []
    market = normalize_free_agents(free_agents)

    for team in teams:
        ensure_team_fa_market_fields(team)

        sign_count = 0
        while sign_count < max_signings_per_team:
            target = pick_best_free_agent_for_team(team, market)
            if target is None:
                break

            if len(getattr(team, "players", [])) >= 14:
                break

            sign_free_agent(team, target)
            if target in market:
                market.remove(target)

            logs.append(
                f"[FA-SIGN] {team.name} signed {target.name} "
                f"(OVR:{getattr(target, 'ovr', 0)}) | "
                f"Salary:{estimate_fa_market_value(target)} | "
                f"Years:{estimate_fa_contract_years(target)} | "
                f"Payroll:{get_team_payroll(team)} / SoftCap:{int(get_soft_cap(league_level=league_level_for_team(team)))}"
            )
            sign_count += 1

    free_agents.clear()
    free_agents.extend(market)
    return logs
