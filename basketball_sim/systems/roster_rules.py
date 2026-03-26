"""
契約ロスター（本契約13枠）の検証。

Step 1 完成定義: どの画面/処理でも「違反ロスター」が生成されないこと。
ユース（youth_players）・特別指定（special_designation_players）は team.players に含めない。
"""

from __future__ import annotations

from typing import List, Tuple

from basketball_sim.config.game_constants import (
    CONTRACT_ROSTER_MAX,
    LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    LEAGUE_ROSTER_FOREIGN_CAP,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


class RosterViolationError(ValueError):
    """本契約枠または登録時国籍ルール違反。"""


def contract_roster_count(team: Team) -> int:
    return len(getattr(team, "players", []) or [])


def can_add_contract_player(team: Team, player: Player) -> Tuple[bool, str]:
    """
    追加可能か。既に所属していれば (True, "already_on_team")。
    """
    roster = list(getattr(team, "players", []) or [])
    if player in roster:
        return True, "already_on_team"

    if len(roster) >= CONTRACT_ROSTER_MAX:
        return False, "contract_roster_full"

    if not team.can_add_player_by_japan_rule(
        player,
        foreign_limit=LEAGUE_ROSTER_FOREIGN_CAP,
        asia_nat_limit=LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    ):
        return False, "nationality_slot"

    return True, "ok"


def validate_contract_roster(team: Team) -> List[str]:
    """
    違反があれば人間向けメッセージのリストを返す（空なら OK）。
    """
    errors: List[str] = []
    roster = list(getattr(team, "players", []) or [])
    n = len(roster)
    if n > CONTRACT_ROSTER_MAX:
        errors.append(
            f"本契約が{CONTRACT_ROSTER_MAX}人を超えています（{n}人）。"
        )

    summary = team.get_nationality_slot_summary(roster)
    if summary["foreign"] > LEAGUE_ROSTER_FOREIGN_CAP:
        errors.append(
            f"外国籍枠超過: {summary['foreign']}/{LEAGUE_ROSTER_FOREIGN_CAP}"
        )
    if summary["asia_or_naturalized"] > LEAGUE_ROSTER_ASIA_NATURALIZED_CAP:
        errors.append(
            f"アジア/帰化枠超過: {summary['asia_or_naturalized']}/{LEAGUE_ROSTER_ASIA_NATURALIZED_CAP}"
        )

    return errors


def is_contract_roster_valid(team: Team) -> bool:
    roster = list(getattr(team, "players", []) or [])
    if len(roster) > CONTRACT_ROSTER_MAX:
        return False
    summary = team.get_nationality_slot_summary(roster)
    if summary["foreign"] > LEAGUE_ROSTER_FOREIGN_CAP:
        return False
    if summary["asia_or_naturalized"] > LEAGUE_ROSTER_ASIA_NATURALIZED_CAP:
        return False
    return True
