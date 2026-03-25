import random
from typing import List

from basketball_sim.models.team import Team
from basketball_sim.models.player import Player
from basketball_sim.systems.contract_logic import (
    SALARY_CAP_DEFAULT,
    SALARY_SOFT_LIMIT_MULTIPLIER,
    get_team_payroll,
)


MIN_TRADE_OVR = 58
MAX_TRADE_OVR_GAP = 8
DEBUG_TRADE = True


def _debug(message: str):
    if DEBUG_TRADE:
        print(f"[TRADE-DEBUG] {message}")


def _get_team_wins(team: Team) -> int:
    """安全にチームの前年勝利数を取得する"""
    return getattr(team, "last_season_wins", getattr(team, "regular_wins", 15))


def _get_team_direction(team: Team) -> str:
    """
    チーム方針をざっくり返す。
    rebuilding: 弱いので若手・将来性を重視
    balanced: 中間
    win_now: 強いので即戦力を重視
    """
    wins = _get_team_wins(team)
    if wins <= 10:
        return "rebuilding"
    if wins >= 18:
        return "win_now"
    return "balanced"


def _potential_bonus(player: Player) -> float:
    pot = str(getattr(player, "potential", "C")).upper()

    if pot == "S":
        return 8.0
    if pot == "A":
        return 5.0
    if pot == "B":
        return 2.5
    if pot == "C":
        return 0.0
    if pot == "D":
        return -2.0
    return 0.0


def _age_bonus(player: Player, direction: str) -> float:
    age = getattr(player, "age", 25)

    if direction == "rebuilding":
        if age <= 21:
            return 6.0
        if age <= 24:
            return 4.0
        if age <= 28:
            return 1.5
        if age <= 31:
            return -1.0
        return -4.0

    if direction == "win_now":
        if age <= 21:
            return 0.5
        if age <= 24:
            return 1.5
        if age <= 29:
            return 4.0
        if age <= 32:
            return 1.0
        return -3.0

    if age <= 22:
        return 4.0
    if age <= 27:
        return 3.0
    if age <= 31:
        return 0.0
    return -3.0


def _contract_bonus(player: Player) -> float:
    """
    契約のお得感 + 契約残年数の評価
    """
    salary = getattr(player, "salary", 500_000)
    ovr = getattr(player, "ovr", 60)
    years_left = getattr(player, "contract_years_left", 1)

    expected_salary = max(1, ovr * 10_000)
    salary_ratio = salary / expected_salary

    value_bonus = 0.0
    if salary_ratio <= 0.85:
        value_bonus += 4.0
    elif salary_ratio <= 1.00:
        value_bonus += 1.5
    elif salary_ratio >= 1.20:
        value_bonus -= 4.0
    elif salary_ratio >= 1.10:
        value_bonus -= 2.0

    term_bonus = 0.0
    if years_left >= 3:
        term_bonus += 2.0
    elif years_left == 2:
        term_bonus += 0.8
    elif years_left <= 1:
        term_bonus -= 2.0

    return value_bonus + term_bonus


def _position_need_bonus(player: Player, team: Team, is_incoming: bool) -> float:
    """
    ポジション人数に応じた補正。
    incoming=True のときは加入候補として評価。
    incoming=False のときは現所属選手として評価。
    """
    position = getattr(player, "position", "")
    same_pos_players = [p for p in team.players if getattr(p, "position", "") == position]

    if not is_incoming:
        same_pos_players = [
            p for p in same_pos_players
            if getattr(p, "player_id", None) != getattr(player, "player_id", None)
        ]

    same_pos_count = len(same_pos_players)

    if same_pos_count <= 1:
        return 5.0
    if same_pos_count == 2:
        return 2.5
    if same_pos_count >= 4:
        return -2.0
    return 0.0


def _strategy_fit_bonus(player: Player, team: Team) -> float:
    """
    戦術適性の補正。
    FAと同じ思想で、あくまで補助評価として小さめに加点減点する。
    目安: -3.0 ～ +5.0
    """
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


def _direction_ovr_bonus(player: Player, direction: str) -> float:
    ovr = float(getattr(player, "ovr", 60))
    pot = str(getattr(player, "potential", "C")).upper()
    age = getattr(player, "age", 25)

    if direction == "win_now":
        return max(0.0, (ovr - 65.0) * 0.45)

    if direction == "rebuilding":
        bonus = 0.0
        if age <= 23:
            bonus += 1.2
        if pot in ("S", "A"):
            bonus += 1.5
        return bonus

    return max(0.0, (ovr - 68.0) * 0.15)


def _evaluate_trade_value(player: Player, team: Team, is_incoming: bool) -> float:
    """
    チーム目線での選手価値を評価する。
    """
    direction = _get_team_direction(team)
    ovr = float(getattr(player, "ovr", 60))

    score = 0.0
    score += ovr
    score += _age_bonus(player, direction)
    score += _potential_bonus(player)
    score += _contract_bonus(player)
    score += _position_need_bonus(player, team, is_incoming)
    score += _strategy_fit_bonus(player, team)
    score += _direction_ovr_bonus(player, direction)

    return score


def _is_core_player(player: Player, team: Team) -> bool:
    """
    コア選手は基本的に出さない。
    - チーム内上位2OVR
    - もしくは超若手高ポテンシャル
    """
    sorted_players = sorted(team.players, key=lambda p: getattr(p, "ovr", 0), reverse=True)
    top_ids = {getattr(p, "player_id", id(p)) for p in sorted_players[:2]}
    player_id = getattr(player, "player_id", id(player))

    if player_id in top_ids:
        return True

    if (
        getattr(player, "age", 30) <= 22
        and str(getattr(player, "potential", "C")).upper() in ("S", "A")
        and getattr(player, "ovr", 0) >= 70
    ):
        return True

    return False


def _is_tradeable_player(player: Player, team: Team) -> bool:
    """
    実際にトレード候補に入れてよい選手か。
    """
    if _is_core_player(player, team):
        return False

    if getattr(player, "ovr", 0) < MIN_TRADE_OVR:
        return False

    return True


def _get_trade_payroll_after(team: Team, outgoing: Player, incoming: Player) -> int:
    return (
        get_team_payroll(team)
        - getattr(outgoing, "salary", 0)
        + getattr(incoming, "salary", 0)
    )


def _get_cap_status(payroll_after: int) -> str:
    soft_cap = int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER)
    if payroll_after > soft_cap:
        return "over_soft_cap"
    if payroll_after > SALARY_CAP_DEFAULT:
        return "over_cap"
    return "under_cap"


def _can_absorb_salary(team: Team, outgoing: Player, incoming: Player) -> bool:
    """
    トレード後のサラリーキャップと資金状態を簡易チェック。
    contract_logic.py の cap と統一する。
    """
    team_salary_after = _get_trade_payroll_after(team, outgoing, incoming)

    if team_salary_after > SALARY_CAP_DEFAULT:
        return False

    salary_diff = getattr(incoming, "salary", 0) - getattr(outgoing, "salary", 0)
    if salary_diff > 0 and getattr(team, "money", 0) < salary_diff * 2:
        return False

    return True


def _get_min_gain_threshold(team: Team) -> float:
    direction = _get_team_direction(team)
    if direction == "rebuilding":
        return 1.0
    if direction == "win_now":
        return 1.2
    return 1.0


def _set_trade_acquisition(player: Player, from_team: Team, to_team: Team):
    """
    トレード加入の履歴を安全に記録する。
    """
    player.acquisition_type = "trade"
    player.acquisition_note = f"traded_from_{from_team.name}_to_{to_team.name}"


def _record_team_trade_history(team_from: Team, team_to: Team, outgoing: Player, incoming: Player):
    """
    クラブ史にトレード履歴を保存する。
    team_to 視点で「incoming」を記録し、
    team_from 視点でも「outgoing」を記録する。
    """
    if hasattr(team_to, "add_history_transaction"):
        note_to = (
            f"trade_in | "
            f"from={team_from.name} | "
            f"received={incoming.name} | "
            f"received_ovr={incoming.ovr} | "
            f"sent={outgoing.name} | "
            f"sent_ovr={outgoing.ovr}"
        )
        team_to.add_history_transaction(
            transaction_type="trade",
            player=incoming,
            note=note_to
        )

    if hasattr(team_from, "add_history_transaction"):
        note_from = (
            f"trade_out | "
            f"to={team_to.name} | "
            f"sent={outgoing.name} | "
            f"sent_ovr={outgoing.ovr} | "
            f"received={incoming.name} | "
            f"received_ovr={incoming.ovr}"
        )
        team_from.add_history_transaction(
            transaction_type="trade",
            player=outgoing,
            note=note_from
        )


def _record_player_trade_career(player: Player, to_team: Team, from_team: Team):
    """
    選手キャリア履歴にトレード移籍を保存する。
    """
    if hasattr(player, "add_career_entry"):
        season_value = max(1, getattr(player, "years_pro", 0) + 1)
        player.add_career_entry(
            season=season_value,
            team_name=to_team.name,
            event="Trade",
            note=f"From {from_team.name}"
        )


def _player_is_foreign(player: Player) -> bool:
    if hasattr(player, "is_foreign_player"):
        try:
            return bool(player.is_foreign_player())
        except Exception:
            pass
    return str(getattr(player, "nationality", "Japan")) == "Foreign"


def _player_is_asia_or_naturalized(player: Player) -> bool:
    if hasattr(player, "is_asia_or_naturalized_player"):
        try:
            return bool(player.is_asia_or_naturalized_player())
        except Exception:
            pass
    return str(getattr(player, "nationality", "Japan")) in ("Asia", "Naturalized")


def _count_japan_rule_slots(players: List[Player]) -> tuple[int, int]:
    foreign = 0
    asia_nat = 0
    for player in players:
        if _player_is_foreign(player):
            foreign += 1
        if _player_is_asia_or_naturalized(player):
            asia_nat += 1
    return foreign, asia_nat


def can_execute_trade_by_japan_rule(team: Team, outgoing: Player, incoming: Player) -> bool:
    """
    トレード後のチームロスターが日本独自ルールを満たすかを確認する。
    外国籍は最大3、Asia/Naturalizedは最大1。
    """
    simulated_players = []
    outgoing_id = getattr(outgoing, "player_id", id(outgoing))

    for player in getattr(team, "players", []):
        player_id = getattr(player, "player_id", id(player))
        if player_id == outgoing_id:
            continue
        simulated_players.append(player)

    simulated_players.append(incoming)

    foreign, asia_nat = _count_japan_rule_slots(simulated_players)
    return foreign <= 3 and asia_nat <= 1


def conduct_trades(teams: List[Team]):
    """
    オフシーズン中の1対1トレード処理。
    両チームにとって一定以上プラスになる場合のみ成立。
    日本独自ルール上、交換後ロスターが合法な場合のみ成立する。
    """
    print("Conducting Trades...")

    traded_teams = set()

    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)

    participating_teams = []
    for team in shuffled_teams:
        wins = _get_team_wins(team)

        if wins <= 8:
            prob = 0.75
        elif wins <= 12:
            prob = 0.60
        elif wins <= 16:
            prob = 0.45
        else:
            prob = 0.25

        if random.random() < prob:
            participating_teams.append(team)

    _debug(f"participating={len(participating_teams)}")

    for team_a in participating_teams:
        if team_a.team_id in traded_teams:
            continue

        tradeable_a = [p for p in team_a.players if _is_tradeable_player(p, team_a)]
        if not tradeable_a:
            _debug(f"{team_a.name} | skip=no_tradeable_players")
            continue

        direction_a = _get_team_direction(team_a)
        if direction_a == "rebuilding":
            tradeable_a = [
                p for p in tradeable_a
                if not (
                    getattr(p, "age", 30) <= 22
                    and str(getattr(p, "potential", "C")).upper() in ("S", "A")
                    and getattr(p, "ovr", 0) >= 68
                )
            ]

        if not tradeable_a:
            _debug(f"{team_a.name} | skip=tradeable_empty_after_direction_filter")
            continue

        tradeable_a = sorted(
            tradeable_a,
            key=lambda p: _evaluate_trade_value(p, team_a, is_incoming=False)
        )

        potential_partners = [
            t for t in participating_teams
            if t.team_id != team_a.team_id and t.team_id not in traded_teams
        ]
        random.shuffle(potential_partners)

        trade_executed = False

        for team_b in potential_partners:
            tradeable_b = [p for p in team_b.players if _is_tradeable_player(p, team_b)]
            if not tradeable_b:
                continue

            direction_b = _get_team_direction(team_b)
            if direction_b == "rebuilding":
                tradeable_b = [
                    p for p in tradeable_b
                    if not (
                        getattr(p, "age", 30) <= 22
                        and str(getattr(p, "potential", "C")).upper() in ("S", "A")
                        and getattr(p, "ovr", 0) >= 68
                    )
                ]

            if not tradeable_b:
                continue

            tradeable_b = sorted(
                tradeable_b,
                key=lambda p: _evaluate_trade_value(p, team_b, is_incoming=False)
            )

            candidates_a = tradeable_a[:12]
            candidates_b = tradeable_b[:12]

            random.shuffle(candidates_a)
            random.shuffle(candidates_b)

            checked_pairs = 0

            for p_a in candidates_a:
                for p_b in candidates_b:
                    checked_pairs += 1

                    if getattr(p_a, "player_id", id(p_a)) == getattr(p_b, "player_id", id(p_b)):
                        continue

                    if abs(getattr(p_a, "ovr", 60) - getattr(p_b, "ovr", 60)) > MAX_TRADE_OVR_GAP:
                        continue

                    if not _can_absorb_salary(team_a, p_a, p_b):
                        continue

                    if not _can_absorb_salary(team_b, p_b, p_a):
                        continue

                    if not can_execute_trade_by_japan_rule(team_a, p_a, p_b):
                        continue

                    if not can_execute_trade_by_japan_rule(team_b, p_b, p_a):
                        continue

                    score_a_gives = _evaluate_trade_value(p_a, team_a, is_incoming=False)
                    score_a_gets = _evaluate_trade_value(p_b, team_a, is_incoming=True)
                    gain_a = score_a_gets - score_a_gives

                    score_b_gives = _evaluate_trade_value(p_b, team_b, is_incoming=False)
                    score_b_gets = _evaluate_trade_value(p_a, team_b, is_incoming=True)
                    gain_b = score_b_gets - score_b_gives

                    min_gain_a = _get_min_gain_threshold(team_a)
                    min_gain_b = _get_min_gain_threshold(team_b)

                    if gain_a < min_gain_a or gain_b < min_gain_b:
                        continue

                    if abs(gain_a - gain_b) > 14.0:
                        continue

                    payroll_a_after = _get_trade_payroll_after(team_a, p_a, p_b)
                    payroll_b_after = _get_trade_payroll_after(team_b, p_b, p_a)

                    # 最終直前でもう一度安全確認
                    if not can_execute_trade_by_japan_rule(team_a, p_a, p_b):
                        continue
                    if not can_execute_trade_by_japan_rule(team_b, p_b, p_a):
                        continue

                    team_a.remove_player(p_a)
                    team_b.remove_player(p_b)

                    _set_trade_acquisition(p_b, team_b, team_a)
                    _set_trade_acquisition(p_a, team_a, team_b)

                    _record_team_trade_history(team_a, team_b, p_a, p_b)
                    _record_team_trade_history(team_b, team_a, p_b, p_a)

                    team_a.add_player(p_b)
                    team_b.add_player(p_a)

                    _record_player_trade_career(p_b, team_a, team_b)
                    _record_player_trade_career(p_a, team_b, team_a)

                    traded_teams.add(team_a.team_id)
                    traded_teams.add(team_b.team_id)

                    print(
                        f"[TRADE] {team_a.name} traded {p_a.name} (OVR:{p_a.ovr}) "
                        f"to {team_b.name} for {p_b.name} (OVR:{p_b.ovr}) | "
                        f"gain_a={gain_a:.1f} gain_b={gain_b:.1f} | "
                        f"{team_a.name}:{payroll_a_after:,}({_get_cap_status(payroll_a_after)}) | "
                        f"{team_b.name}:{payroll_b_after:,}({_get_cap_status(payroll_b_after)})"
                    )

                    trade_executed = True
                    break

                if trade_executed:
                    break

            if not trade_executed:
                _debug(
                    f"{team_a.name} vs {team_b.name} | checked_pairs={checked_pairs} | no_deal"
                )

            if trade_executed:
                break

        if not trade_executed:
            _debug(f"{team_a.name} | no_trade_executed")
