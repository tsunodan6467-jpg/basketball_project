"""
契約解除（FA送り）の共通判定・適用。GUI / CLI で同一の状態遷移に使う。
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from basketball_sim.config.game_constants import CONTRACT_ROSTER_MIN_SEASON, PLAYER_SALARY_BASE_PER_OVR
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.season_transaction_rules import INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA, inseason_roster_moves_unlocked


def inseason_roster_release_unlocked(season: Optional[Any]) -> bool:
    """`MainMenuView.inseason_roster_moves_allowed` と同一。"""
    if season is None:
        return True
    if bool(getattr(season, "season_finished", False)):
        return True
    try:
        return inseason_roster_moves_unlocked(season)
    except Exception:
        return True


def precheck_release_player_to_fa(
    team: Team,
    player: Player,
    season: Optional[Any],
) -> Optional[Tuple[str, str]]:
    """
    確認ダイアログの直前までのガード。
    不可なら (messagebox_title, message_body)。可なら None。
    """
    if not inseason_roster_release_unlocked(season):
        return (
            "トレード・インシーズンFAは不可",
            "期限ルールにより、現在は実行できません。\n"
            "（オフシーズンは別処理で進行します）\n\n"
            + INSEASON_ROSTER_MOVE_LOCK_MESSAGE_JA,
        )
    if bool(getattr(player, "icon_locked", False)) or bool(getattr(player, "is_icon", False)):
        return ("人事", "この選手は契約解除できません（アイコン／保護選手）。")
    players = list(getattr(team, "players", []) or [])
    if len(players) <= CONTRACT_ROSTER_MIN_SEASON:
        return (
            "人事",
            f"契約選手は最低 {CONTRACT_ROSTER_MIN_SEASON} 人必要です（現状 {len(players)} 人）。解除できません。",
        )
    return None


def postcheck_release_player_to_fa_season(season: Optional[Any]) -> Optional[Tuple[str, str]]:
    """ユーザー確認後、FA プール接続の可否。"""
    if season is None:
        return ("人事", "シーズン未接続のため FA プールへ追加できません。")
    fa_list = getattr(season, "free_agents", None)
    if fa_list is None:
        return ("人事", "FA プールが未初期化です。")
    return None


def apply_release_player_to_fa(
    team: Team,
    player: Player,
    free_agents: List[Any],
    *,
    history_event: str = "gui_release",
    history_note: str = "GUI人事：契約解除",
) -> None:
    """前提チェック済みの契約解除を適用する。"""
    team.remove_player(player)
    setattr(player, "contract_years_left", 0)
    if int(getattr(player, "salary", 0) or 0) <= 0:
        setattr(
            player,
            "salary",
            max(int(getattr(player, "ovr", 0) or 0) * PLAYER_SALARY_BASE_PER_OVR, 300_000),
        )
    if player not in free_agents:
        free_agents.append(player)
    add_hist = getattr(team, "add_history_transaction", None)
    if callable(add_hist):
        try:
            add_hist(history_event, player, history_note)
        except Exception:
            pass
