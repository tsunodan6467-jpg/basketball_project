from dataclasses import dataclass
from typing import List, Tuple, Dict

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


@dataclass
class TradeEvaluation:
    accepts: bool
    score: float
    reasons: List[str]


class TradeSystem:
    """
    GMモード向けの安全なトレード土台。

    初期方針:
    - まずは 1対1 トレード専用
    - 契約 / 外国籍枠 / 年齢 / OVR / ポジション事情 を軽く評価
    - 既存構造を壊さない
    - 実際の実行は main.py / offseason.py 側から呼ぶ前提

    将来拡張:
    - 2対1 / 2対2
    - 指名権
    - 再建型 / 優勝狙いAI
    - 選手の不満 / loyalty / popularity
    """

    POSITION_KEYS = ["PG", "SG", "SF", "PF", "C"]

    def _is_foreign(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") == "Foreign"

    def _is_asia_or_naturalized(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") in ("Asia", "Naturalized")

    def _count_foreign(self, players: List[Player]) -> int:
        return sum(1 for p in players if self._is_foreign(p))

    def _count_asia_nat(self, players: List[Player]) -> int:
        return sum(1 for p in players if self._is_asia_or_naturalized(p))

    def _get_active_roster_after_trade(
        self,
        team: Team,
        send_player: Player,
        receive_player: Player
    ) -> List[Player]:
        roster = [p for p in getattr(team, "players", []) if p != send_player]
        roster.append(receive_player)
        return roster

    def _passes_nationality_rule_after_trade(
        self,
        team: Team,
        send_player: Player,
        receive_player: Player
    ) -> bool:
        roster = self._get_active_roster_after_trade(team, send_player, receive_player)

        foreign = self._count_foreign(roster)
        asia_nat = self._count_asia_nat(roster)

        # ロスター全体は従来ルールに合わせる
        return foreign <= 3 and asia_nat <= 1

    def _position_depth(self, team: Team) -> Dict[str, int]:
        depth = {pos: 0 for pos in self.POSITION_KEYS}
        for p in getattr(team, "players", []):
            if p.is_retired:
                continue
            pos = getattr(p, "position", "SF")
            if pos in depth:
                depth[pos] += 1
        return depth

    def _get_position_need_score(
        self,
        team: Team,
        send_player: Player,
        receive_player: Player
    ) -> float:
        depth_before = self._position_depth(team)
        send_pos = getattr(send_player, "position", "SF")
        recv_pos = getattr(receive_player, "position", "SF")

        score = 0.0

        # 送る側ポジションが薄いとマイナス
        if depth_before.get(send_pos, 0) <= 1:
            score -= 8.0
        elif depth_before.get(send_pos, 0) == 2:
            score -= 3.0

        # 受け取る側ポジションが薄いとプラス
        if depth_before.get(recv_pos, 0) <= 1:
            score += 8.0
        elif depth_before.get(recv_pos, 0) == 2:
            score += 3.0

        return score

    def _get_age_curve_bonus(self, player: Player, team: Team) -> float:
        age = getattr(player, "age", 25)
        ovr = getattr(player, "ovr", 50)
        usage_policy = getattr(team, "usage_policy", "balanced")

        if usage_policy == "win_now":
            if age <= 24 and ovr < 70:
                return -1.5
            if 25 <= age <= 30 and ovr >= 70:
                return 2.0
            if age >= 31 and ovr >= 74:
                return 0.8

        if usage_policy == "development":
            if age <= 22:
                return 3.0
            if age <= 24:
                return 2.0
            if age >= 30:
                return -2.0

        # balanced
        if age <= 23:
            return 1.2
        if age >= 32:
            return -1.0
        return 0.0

    def _get_contract_score(self, player: Player) -> float:
        salary = getattr(player, "salary", 0)
        years_left = getattr(player, "contract_years_left", 0)
        ovr = getattr(player, "ovr", 50)

        score = 0.0

        # 高OVRで安い契約は高評価
        expected_salary_band = max(300000, (ovr - 40) * 25000)
        if salary < expected_salary_band:
            score += 2.0
        elif salary > expected_salary_band * 1.6:
            score -= 2.0

        if years_left >= 3:
            score += 1.0
        elif years_left == 0:
            score -= 1.0

        return score

    def calculate_player_trade_value(self, player: Player, team: Team) -> float:
        ovr = getattr(player, "ovr", 50)
        age = getattr(player, "age", 25)
        potential = str(getattr(player, "potential", "C")).upper()
        popularity = getattr(player, "popularity", 50)
        is_icon = getattr(player, "is_icon", False)
        injured = player.is_injured()

        value = 0.0
        value += ovr * 1.35
        value += max(0, 28 - abs(age - 27)) * 0.40
        value += self._get_contract_score(player)
        value += self._get_age_curve_bonus(player, team)
        value += max(0, popularity - 50) * 0.05

        potential_bonus = {
            "S": 5.0,
            "A": 3.5,
            "B": 2.0,
            "C": 0.8,
            "D": 0.0,
        }
        value += potential_bonus.get(potential, 0.0)

        if injured:
            value -= 4.0
        if is_icon or getattr(player, "icon_locked", False):
            value += 12.0

        return round(value, 2)

    def evaluate_trade_for_team(
        self,
        team: Team,
        send_player: Player,
        receive_player: Player
    ) -> TradeEvaluation:
        reasons: List[str] = []

        if send_player == receive_player:
            return TradeEvaluation(False, -999.0, ["same_player"])

        if send_player not in getattr(team, "players", []):
            return TradeEvaluation(False, -999.0, ["send_player_not_on_team"])

        if getattr(send_player, "icon_locked", False):
            return TradeEvaluation(False, -999.0, ["icon_locked"])

        if not self._passes_nationality_rule_after_trade(team, send_player, receive_player):
            return TradeEvaluation(False, -999.0, ["nationality_rule_violation"])

        send_value = self.calculate_player_trade_value(send_player, team)
        receive_value = self.calculate_player_trade_value(receive_player, team)

        score = receive_value - send_value
        score += self._get_position_need_score(team, send_player, receive_player)

        send_ovr = getattr(send_player, "ovr", 50)
        recv_ovr = getattr(receive_player, "ovr", 50)
        if recv_ovr > send_ovr:
            score += (recv_ovr - send_ovr) * 0.35
        elif recv_ovr < send_ovr:
            score -= (send_ovr - recv_ovr) * 0.25

        if score >= 3.0:
            reasons.append("clear_upgrade")
        elif score >= 0.5:
            reasons.append("acceptable_value")
        else:
            reasons.append("not_enough_value")

        if getattr(receive_player, "age", 25) < getattr(send_player, "age", 25):
            reasons.append("younger_return")
        if getattr(receive_player, "ovr", 50) > getattr(send_player, "ovr", 50):
            reasons.append("higher_ovr_return")

        accepts = score >= 0.5
        return TradeEvaluation(accepts, round(score, 2), reasons)

    def evaluate_one_for_one_trade(
        self,
        user_team: Team,
        ai_team: Team,
        user_send_player: Player,
        ai_send_player: Player
    ) -> Tuple[TradeEvaluation, TradeEvaluation]:
        user_eval = self.evaluate_trade_for_team(
            team=user_team,
            send_player=user_send_player,
            receive_player=ai_send_player
        )
        ai_eval = self.evaluate_trade_for_team(
            team=ai_team,
            send_player=ai_send_player,
            receive_player=user_send_player
        )
        return user_eval, ai_eval

    def should_ai_accept_trade(
        self,
        user_team: Team,
        ai_team: Team,
        user_send_player: Player,
        ai_send_player: Player
    ) -> Tuple[bool, str, TradeEvaluation]:
        _, ai_eval = self.evaluate_one_for_one_trade(
            user_team=user_team,
            ai_team=ai_team,
            user_send_player=user_send_player,
            ai_send_player=ai_send_player
        )

        if ai_eval.accepts:
            return True, "accepted", ai_eval

        if "icon_locked" in ai_eval.reasons:
            return False, "icon_locked", ai_eval
        if "nationality_rule_violation" in ai_eval.reasons:
            return False, "nationality_rule_violation", ai_eval
        return False, "rejected_value", ai_eval

    def execute_one_for_one_trade(
        self,
        team_a: Team,
        team_b: Team,
        player_a: Player,
        player_b: Player
    ) -> bool:
        if player_a not in getattr(team_a, "players", []):
            return False
        if player_b not in getattr(team_b, "players", []):
            return False

        if not self._passes_nationality_rule_after_trade(team_a, player_a, player_b):
            return False
        if not self._passes_nationality_rule_after_trade(team_b, player_b, player_a):
            return False

        team_a.remove_player(player_a)
        team_b.remove_player(player_b)

        team_a.add_player(player_b)
        team_b.add_player(player_a)

        if hasattr(team_a, "add_history_transaction"):
            team_a.add_history_transaction("trade", player_b, note=f"Acquired from {team_b.name}")
            team_a.add_history_transaction("trade", player_a, note=f"Traded to {team_b.name}")

        if hasattr(team_b, "add_history_transaction"):
            team_b.add_history_transaction("trade", player_a, note=f"Acquired from {team_a.name}")
            team_b.add_history_transaction("trade", player_b, note=f"Traded to {team_a.name}")

        return True
