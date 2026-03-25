
from dataclasses import dataclass
from typing import List, Tuple
import random


@dataclass
class FAOfferResult:
    success: bool
    score: float
    reasons: List[str]


class FASystem:
    """
    Free Agency 安全版ロジック

    目的
    - GMゲーム用のシンプルFA取得
    - まずは「ユーザー単独オファー」
    - AI競合なし
    - 将来拡張しやすい構造

    将来拡張予定
    - AI競合
    - 再契約
    - 忠誠心 / 出場機会 / 優勝志向
    - エージェント交渉
    """

    # -------------------------------------------------
    # 基本パラメータ
    # -------------------------------------------------

    def get_player_market_value(self, player) -> int:
        """
        選手の市場年俸の簡易計算
        """
        ovr = getattr(player, "ovr", 50)
        age = getattr(player, "age", 25)

        base = (ovr - 40) * 25000

        # 年齢補正
        if age <= 23:
            base *= 1.10
        elif age >= 32:
            base *= 0.85

        return int(max(200000, base))

    def get_default_contract_years(self, player) -> int:
        age = getattr(player, "age", 25)

        if age <= 23:
            return 3
        if age <= 28:
            return 3
        if age <= 31:
            return 2
        return 1

    # -------------------------------------------------
    # オファー評価
    # -------------------------------------------------

    def evaluate_offer(self, team, player, salary_offer, years_offer):

        reasons = []

        market_value = self.get_player_market_value(player)
        default_years = self.get_default_contract_years(player)

        score = 0.0

        # 年俸評価
        if salary_offer >= market_value:
            score += 5.0
            reasons.append("good_salary")
        else:
            diff = market_value - salary_offer
            score -= diff / 100000
            reasons.append("low_salary")

        # 年数評価
        if years_offer >= default_years:
            score += 2.0
            reasons.append("good_years")
        else:
            score -= 1.5
            reasons.append("short_contract")

        # 市場規模
        market = getattr(team, "market_size", 1.0)
        score += (market - 1.0) * 3

        # チーム人気
        popularity = getattr(team, "popularity", 50)
        score += (popularity - 50) * 0.05

        # 出場機会
        roster_size = len(getattr(team, "players", []))
        if roster_size < 13:
            score += 2.0
            reasons.append("playing_time")

        # usage policy
        policy = getattr(team, "usage_policy", "balanced")

        age = getattr(player, "age", 25)

        if policy == "development" and age <= 23:
            score += 2.5
            reasons.append("development_fit")

        if policy == "win_now" and getattr(player, "ovr", 50) >= 75:
            score += 2.0
            reasons.append("contender_fit")

        success = score >= 3.0

        return FAOfferResult(success, round(score, 2), reasons)

    # -------------------------------------------------
    # 契約処理
    # -------------------------------------------------

    def sign_player(self, team, player, salary, years):

        if hasattr(team, "add_player"):
            team.add_player(player)

        player.salary = salary
        player.contract_years_left = years

        if hasattr(team, "add_history_transaction"):
            team.add_history_transaction(
                "free_agent",
                player,
                note=f"Signed FA {player.name}"
            )

        return True

    # -------------------------------------------------
    # 外国籍チェック
    # -------------------------------------------------

    def nationality_check(self, team, player):

        foreign_count = 0
        asia_nat_count = 0

        for p in getattr(team, "players", []):
            nat = getattr(p, "nationality", "Japan")

            if nat == "Foreign":
                foreign_count += 1

            if nat in ("Asia", "Naturalized"):
                asia_nat_count += 1

        nat = getattr(player, "nationality", "Japan")

        if nat == "Foreign" and foreign_count >= 3:
            return False

        if nat in ("Asia", "Naturalized") and asia_nat_count >= 1:
            return False

        return True
