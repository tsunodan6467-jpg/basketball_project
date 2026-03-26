from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Set

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import (
    SALARY_CAP_DEFAULT,
    SALARY_SOFT_LIMIT_MULTIPLIER,
    get_team_payroll,
)


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

    def _player_key(self, player: Player) -> int:
        # player_id が無いケースでも落ちないように保険
        return int(getattr(player, "player_id", id(player)))

    def _players_to_keys(self, players: List[Player]) -> Set[int]:
        return {self._player_key(p) for p in players}

    def _team_direction(self, team: Team) -> str:
        wins = int(getattr(team, "last_season_wins", getattr(team, "regular_wins", 15)) or 0)
        if wins <= 10:
            return "rebuilding"
        if wins >= 18:
            return "win_now"
        return "balanced"

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

    def _effective_ovr(self, player: Player) -> float:
        try:
            return float(player.get_effective_ovr())
        except Exception:
            return float(getattr(player, "ovr", 0) or 0)

    def _position_depth_from_players(self, players: List[Player]) -> Dict[str, int]:
        depth = {pos: 0 for pos in self.POSITION_KEYS}
        for p in players:
            if getattr(p, "is_retired", False) or getattr(p, "is_injured", lambda: False)():
                # Injured/retired は trade 候補から弾かれている想定だが保険
                continue
            pos = getattr(p, "position", "SF")
            if pos in depth:
                depth[pos] += 1
        return depth

    def _get_untouchable_player_keys(self, team: Team) -> Set[int]:
        explicit = getattr(team, "trade_block_untouchable_player_ids", None)
        if isinstance(explicit, (list, set, tuple)) and explicit:
            return {int(x) for x in explicit}

        # v1: 自動で“コア”を絶対放出不可に寄せる（win_now）
        direction = self._team_direction(team)
        if direction != "win_now":
            return {self._player_key(p) for p in getattr(team, "players", []) if bool(getattr(p, "icon_locked", False))}

        candidates = [p for p in getattr(team, "players", []) if not bool(getattr(p, "icon_locked", False))]
        top = sorted(candidates, key=lambda p: self._effective_ovr(p), reverse=True)[:2]
        keys = {self._player_key(p) for p in top}
        keys |= {self._player_key(p) for p in getattr(team, "players", []) if bool(getattr(p, "icon_locked", False))}
        return keys

    def _infer_negotiation_stance(self, team: Team, outgoing_players: List[Player]) -> str:
        untouchables = self._get_untouchable_player_keys(team)
        outgoing_keys = self._players_to_keys(outgoing_players)
        if outgoing_keys & untouchables:
            return "absolute_no_sell"

        direction = self._team_direction(team)
        if direction == "win_now":
            return "strong"
        if direction == "rebuilding":
            return "rebuild"
        return "normal"

    def _simulate_roster_after_multi_trade(
        self,
        team: Team,
        gives_players: List[Player],
        receives_players: List[Player],
        trim_to_13: bool,
    ) -> Optional[tuple[List[Player], List[Player]]]:
        """
        戻り値: (roster_after, dropped_incoming)
        - dropped_incoming は receives_players の一部で、13人を超えた分を埋めるために自動放出した想定の選手。
        """
        team_players = list(getattr(team, "players", []) or [])
        gives_keys = self._players_to_keys(gives_players)

        # gives_players がチーム所属になければシミュレーション不能
        if any(self._player_key(p) not in {self._player_key(tp) for tp in team_players} for p in gives_players):
            return None

        roster = [p for p in team_players if self._player_key(p) not in gives_keys]
        roster.extend(receives_players)

        if not trim_to_13 or len(roster) <= 13:
            return roster, []

        extra = len(roster) - 13

        # 放出は incoming(=receives_players) 優先。icon_locked / youth は保護。
        incoming_candidates = [
            p for p in receives_players
            if not bool(getattr(p, "icon_locked", False))
            and str(getattr(p, "acquisition_type", "") or "") != "youth"
        ]
        if len(incoming_candidates) < extra:
            return None

        # 低 effective OVR から順に放出
        incoming_candidates_sorted = sorted(
            incoming_candidates,
            key=lambda p: (self._effective_ovr(p), int(getattr(p, "age", 99) or 99)),
        )
        dropped = incoming_candidates_sorted[:extra]
        dropped_keys = self._players_to_keys(dropped)
        roster = [p for p in roster if self._player_key(p) not in dropped_keys]
        return roster, dropped

    def _passes_nationality_rule_after_multi_trade(
        self,
        roster_after: List[Player],
    ) -> bool:
        foreign = self._count_foreign(roster_after)
        asia_nat = self._count_asia_nat(roster_after)
        return foreign <= 3 and asia_nat <= 1

    def _calc_cash_rb_score(self, cash_change: int, rb_change: int) -> float:
        # スコアスケール: 目標は “選手価値との差が極端にならない” こと
        cash_score = cash_change / 2_500_000.0  # 2.5M = +1.0
        rb_score = rb_change / 10_000_000.0  # 10M = +1.0
        return cash_score + rb_score

    def evaluate_multi_trade_for_team(
        self,
        team: Team,
        gives_players: List[Player],
        receives_players: List[Player],
        cash_change: int,
        rb_change: int,
        trim_to_13: bool = True,
    ) -> TradeEvaluation:
        reasons: List[str] = []

        # icon / コア保護
        if any(bool(getattr(p, "icon_locked", False)) for p in (gives_players + receives_players)):
            return TradeEvaluation(False, -999.0, ["icon_locked"])

        # 所属・資産チェック
        if any(self._player_key(p) not in {self._player_key(tp) for tp in getattr(team, "players", [])} for p in gives_players):
            return TradeEvaluation(False, -999.0, ["gives_players_not_on_team"])

        if cash_change < 0 and int(getattr(team, "money", 0) or 0) < abs(cash_change):
            return TradeEvaluation(False, -999.0, ["cash_insufficient"])

        if rb_change < 0 and int(getattr(team, "rookie_budget_remaining", 0) or 0) < abs(rb_change):
            return TradeEvaluation(False, -999.0, ["rookie_budget_insufficient"])

        stance = self._infer_negotiation_stance(team, gives_players)
        reasons.append(f"stance:{stance}")

        sim = self._simulate_roster_after_multi_trade(
            team=team,
            gives_players=gives_players,
            receives_players=receives_players,
            trim_to_13=trim_to_13,
        )
        if sim is None:
            return TradeEvaluation(False, -999.0, ["roster_trim_failed"])

        roster_after, dropped_incoming = sim
        kept_incoming = [p for p in receives_players if p not in dropped_incoming]

        if not self._passes_nationality_rule_after_multi_trade(roster_after):
            reasons.append("nationality_rule_violation")
            return TradeEvaluation(False, -999.0, reasons)

        # salary soft-cap チェック（投影）
        payroll_current = get_team_payroll(team)
        outgoing_salary = sum(int(getattr(p, "salary", 0) or 0) for p in gives_players)
        incoming_salary = sum(int(getattr(p, "salary", 0) or 0) for p in kept_incoming)
        payroll_after = payroll_current - outgoing_salary + incoming_salary
        if payroll_after > int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER):
            reasons.append("soft_cap_block")
            return TradeEvaluation(False, -999.0, reasons)

        # pos 過多（最低限の拒否）
        depth_after = self._position_depth_from_players(roster_after)
        if any(cnt >= 5 for cnt in depth_after.values()):
            reasons.append("position_excess")
            return TradeEvaluation(False, -999.0, reasons)

        if stance == "absolute_no_sell":
            return TradeEvaluation(False, -999.0, reasons + ["untouchable_player"])

        send_value = sum(self.calculate_player_trade_value(p, team) for p in gives_players)
        receive_value = sum(self.calculate_player_trade_value(p, team) for p in kept_incoming)

        # ポジション事情（出入りの影響を、現在ロスター深さに対して概算）
        score = receive_value - send_value

        depth = self._position_depth(team)
        for out in gives_players:
            pos = getattr(out, "position", "SF")
            before = depth.get(pos, 0)
            if before <= 1:
                score -= 8.0
            elif before == 2:
                score -= 3.0
            depth[pos] = max(0, before - 1)

        for inc in kept_incoming:
            pos = getattr(inc, "position", "SF")
            before = depth.get(pos, 0)
            if before <= 1:
                score += 8.0
            elif before == 2:
                score += 3.0
            depth[pos] = before + 1

        score += self._calc_cash_rb_score(cash_change=cash_change, rb_change=rb_change)

        # age 差で“再建型”を補正
        def _avg_age(ps: List[Player]) -> float:
            if not ps:
                return 25.0
            return sum(float(getattr(p, "age", 25) or 25) for p in ps) / len(ps)

        if stance == "rebuild":
            avg_out = _avg_age(gives_players)
            avg_in = _avg_age(kept_incoming)
            if avg_in >= avg_out + 2 and rb_change <= 0:
                reasons.append("future_assets_missing")
                return TradeEvaluation(False, -999.0, reasons)

        # 受け側のスコア期待値
        n_assets = len(gives_players) + len(kept_incoming)
        base_threshold = {"strong": 1.2, "normal": 0.6, "rebuild": -0.2}.get(stance, 0.6)
        threshold = base_threshold + 0.05 * max(0, n_assets - 2)

        # 参考理由
        if score >= base_threshold + 1.0:
            reasons.append("clear_upgrade")
        elif score >= threshold:
            reasons.append("acceptable_value")
        else:
            reasons.append("not_enough_value")

        accepts = score >= threshold
        return TradeEvaluation(accepts, round(score, 2), reasons)

    def evaluate_multi_trade(
        self,
        team_a: Team,
        team_b: Team,
        offer: MultiTradeOffer,
        trim_to_13: bool = True,
    ) -> Tuple[TradeEvaluation, TradeEvaluation]:
        user_eval = self.evaluate_multi_trade_for_team(
            team=team_a,
            gives_players=offer.team_a_gives_players,
            receives_players=offer.team_a_receives_players,
            cash_change=-int(offer.cash_a_to_b or 0),
            rb_change=-int(offer.rookie_budget_a_to_b or 0),
            trim_to_13=trim_to_13,
        )
        ai_eval = self.evaluate_multi_trade_for_team(
            team=team_b,
            gives_players=offer.team_a_receives_players,
            receives_players=offer.team_a_gives_players,
            cash_change=+int(offer.cash_a_to_b or 0),
            rb_change=+int(offer.rookie_budget_a_to_b or 0),
            trim_to_13=trim_to_13,
        )
        return user_eval, ai_eval

    def should_ai_accept_multi_trade(
        self,
        team_a: Team,
        team_b: Team,
        offer: MultiTradeOffer,
    ) -> Tuple[bool, str, TradeEvaluation]:
        _, ai_eval = self.evaluate_multi_trade(
            team_a=team_a,
            team_b=team_b,
            offer=offer,
        )

        if ai_eval.accepts:
            return True, "accepted", ai_eval

        hard_reason = ai_eval.reasons[:]
        if "icon_locked" in hard_reason:
            return False, "icon_locked", ai_eval
        if "nationality_rule_violation" in hard_reason:
            return False, "nationality_rule_violation", ai_eval
        if "untouchable_player" in hard_reason:
            return False, "untouchable_player", ai_eval
        if "soft_cap_block" in hard_reason:
            return False, "soft_cap_block", ai_eval
        if "cash_insufficient" in hard_reason:
            return False, "cash_insufficient", ai_eval
        if "rookie_budget_insufficient" in hard_reason:
            return False, "rookie_budget_insufficient", ai_eval
        return False, "rejected_value", ai_eval

    def execute_multi_trade(
        self,
        team_a: Team,
        team_b: Team,
        offer: MultiTradeOffer,
        free_agents: Optional[List[Player]] = None,
    ) -> bool:
        """
        team_a: GMユーザー側（放出=team_a_gives、獲得=team_a_receives）
        team_b: AI側（放出=team_a_receives、獲得=team_a_gives）
        """
        gives_a = list(offer.team_a_gives_players)
        receives_a = list(offer.team_a_receives_players)
        gives_b = receives_a
        receives_b = gives_a

        cash = int(offer.cash_a_to_b or 0)
        rb = int(offer.rookie_budget_a_to_b or 0)

        # 基本検証
        if not gives_a or not receives_a:
            return False
        if any(bool(getattr(p, "icon_locked", False)) for p in (gives_a + receives_a)):
            return False
        if cash < 0 or rb < 0:
            return False

        if cash > int(getattr(team_a, "money", 0) or 0):
            return False
        if rb > int(getattr(team_a, "rookie_budget_remaining", 0) or 0):
            return False

        team_a_players = list(getattr(team_a, "players", []) or [])
        team_b_players = list(getattr(team_b, "players", []) or [])
        if any(p not in team_a_players for p in gives_a):
            return False
        if any(p not in team_b_players for p in gives_b):
            return False

        # 交換前に nationality / salary / roster overflow を安全確認（トリムシミュレーション）
        sim_a = self._simulate_roster_after_multi_trade(
            team=team_a,
            gives_players=gives_a,
            receives_players=receives_a,
            trim_to_13=True,
        )
        sim_b = self._simulate_roster_after_multi_trade(
            team=team_b,
            gives_players=gives_b,
            receives_players=receives_b,
            trim_to_13=True,
        )
        if sim_a is None or sim_b is None:
            return False

        roster_a_after, dropped_a = sim_a
        roster_b_after, dropped_b = sim_b

        if free_agents is None and (dropped_a or dropped_b):
            # 13人上限超過を“FA放出”で吸収する v1 のため
            return False

        if not self._passes_nationality_rule_after_multi_trade(roster_a_after):
            return False
        if not self._passes_nationality_rule_after_multi_trade(roster_b_after):
            return False

        payroll_current_a = get_team_payroll(team_a)
        payroll_current_b = get_team_payroll(team_b)
        outgoing_salary_a = sum(int(getattr(p, "salary", 0) or 0) for p in gives_a)
        outgoing_salary_b = sum(int(getattr(p, "salary", 0) or 0) for p in gives_b)

        kept_incoming_a = [p for p in receives_a if p not in dropped_a]
        kept_incoming_b = [p for p in receives_b if p not in dropped_b]

        payroll_after_a = payroll_current_a - outgoing_salary_a + sum(int(getattr(p, "salary", 0) or 0) for p in kept_incoming_a)
        payroll_after_b = payroll_current_b - outgoing_salary_b + sum(int(getattr(p, "salary", 0) or 0) for p in kept_incoming_b)
        if payroll_after_a > int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER):
            return False
        if payroll_after_b > int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER):
            return False

        # 実行（まず選手入替）
        for p in gives_a:
            team_a.remove_player(p)
        for p in gives_b:
            team_b.remove_player(p)

        for p in receives_a:
            team_a.add_player(p, force=True)
        for p in receives_b:
            team_b.add_player(p, force=True)

        # 現金 / rookie budget 移転
        team_a.money = int(getattr(team_a, "money", 0) or 0) - cash
        team_b.money = int(getattr(team_b, "money", 0) or 0) + cash
        team_a.rookie_budget_remaining = int(getattr(team_a, "rookie_budget_remaining", 0) or 0) - rb
        team_b.rookie_budget_remaining = int(getattr(team_b, "rookie_budget_remaining", 0) or 0) + rb

        # 13人超過分の自動FA放出（incoming から最小 effective OVR）
        for p in dropped_a:
            if p in getattr(team_a, "players", []):
                team_a.remove_player(p)
                p.contract_years_left = 0
                if int(getattr(p, "salary", 0) or 0) <= 0:
                    p.salary = max(int(getattr(p, "ovr", 0) or 0) * 10_000, 300_000)
                if free_agents is not None:
                    free_agents.append(p)
        for p in dropped_b:
            if p in getattr(team_b, "players", []):
                team_b.remove_player(p)
                p.contract_years_left = 0
                if int(getattr(p, "salary", 0) or 0) <= 0:
                    p.salary = max(int(getattr(p, "ovr", 0) or 0) * 10_000, 300_000)
                if free_agents is not None:
                    free_agents.append(p)

        # 履歴
        if hasattr(team_a, "add_history_transaction"):
            for p in receives_a:
                team_a.add_history_transaction("trade", p, note=f"Acquired from {team_b.name}")
            for p in gives_a:
                team_a.add_history_transaction("trade", p, note=f"Traded to {team_b.name}")
            if cash > 0:
                team_a.add_history_transaction("trade", None, note=f"Cash+${cash:,} to {team_b.name}")
            if rb > 0:
                team_a.add_history_transaction("trade", None, note=f"RB+${rb:,} to {team_b.name}")

        if hasattr(team_b, "add_history_transaction"):
            for p in receives_b:
                team_b.add_history_transaction("trade", p, note=f"Acquired from {team_a.name}")
            for p in gives_b:
                team_b.add_history_transaction("trade", p, note=f"Traded to {team_a.name}")
            if cash > 0:
                team_b.add_history_transaction("trade", None, note=f"Cash-${cash:,} received from {team_a.name}")
            if rb > 0:
                team_b.add_history_transaction("trade", None, note=f"RB-${rb:,} received from {team_a.name}")

        return True


@dataclass
class MultiTradeOffer:
    """
    team_a 視点の多人数トレード定義。

    - team_a_gives_players: team_a が放出する選手リスト
    - team_a_receives_players: team_a が獲得する選手リスト
    - cash_a_to_b: team_a から team_b へ渡す現金（0以上）
    - rookie_budget_a_to_b: team_a の rookie_budget_remaining を team_b へ移す額（0以上）
    """

    team_a_gives_players: List[Player]
    team_a_receives_players: List[Player]
    cash_a_to_b: int = 0
    rookie_budget_a_to_b: int = 0

