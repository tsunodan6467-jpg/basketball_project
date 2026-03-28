"""
セーブ用ペイロードの単一組み立てと、ロード直後の整合用ヘルパー。

GUI / CLI 双方から同じ dict 形を使い、キー欠落や Season 参照のズレを防ぐ。
"""

from __future__ import annotations

from typing import Any, Dict

from basketball_sim.config.game_constants import PAYLOAD_SCHEMA_VERSION


def build_save_payload(
    *,
    teams: Any,
    free_agents: Any,
    user_team_id: int,
    season_count: int,
    tracked_player_name: Any,
    at_annual_menu: bool,
    simulation_seed: Any,
    resume_season: Any = None,
) -> Dict[str, Any]:
    """
    CLI / GUI 共通のセーブ用ペイロード。

    season_count（進行用・payload 正本）:
      run_interactive_season のループ変数と同じ意味。レギュラー中・年度メニュー直後（オフ済み）
      もそのシーズン番号。増えるのは年度メニュー「次のシーズンへ進む」相当の処理のみ。
      呼び出し側が一貫した値を渡すこと。

    at_annual_menu が True のときは resume_season を保存しない（年度進行メニュー相当で
    Season インスタンスが世界と不整合になり得るため。チーム／FA のみで再開する）。
    """
    rs = None if at_annual_menu else resume_season
    return {
        "teams": teams,
        "free_agents": free_agents,
        "user_team_id": int(user_team_id),
        "tracked_player_name": tracked_player_name,
        "season_count": int(season_count),
        "at_annual_menu": bool(at_annual_menu),
        "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
        "simulation_seed": simulation_seed,
        "resume_season": rs,
    }


def rebind_resume_season_to_world(payload: Dict[str, Any]) -> None:
    """
    load_world 直後に呼ぶ。pickle 復元後も resume_season が必ず payload 先頭の
    teams / free_agents と同一リストを参照するようにする。
    失敗時は resume_season を外し、新規 Season での再開にフォールバックする。
    """
    teams = payload.get("teams")
    fa = payload.get("free_agents") or []
    rs = payload.get("resume_season")
    if rs is None:
        return
    if not isinstance(teams, list):
        payload["resume_season"] = None
        return
    try:
        rs.all_teams = teams
        rs.free_agents = fa
    except Exception:
        payload["resume_season"] = None
