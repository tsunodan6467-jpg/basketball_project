"""
オフシーズン・ユーザーチーム再契約の GUI 確認（Tk）。
GUI モードで Offseason を走らせる際、標準入力の y/n の代わりに messagebox を使う。
"""

from __future__ import annotations

from typing import Any

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.salary_cap_budget import get_soft_cap


def prompt_user_resign_offer(
    parent: Any,
    *,
    team: Team,
    player: Player,
    new_salary: int,
    desired_years: int,
    resign_score: float,
    threshold: float,
    current_team_salary: int,
    salary_cap: int,
) -> bool:
    """再契約オファーを出すか。Yes=True / No=False。"""
    from tkinter import messagebox

    soft_limit = int(get_soft_cap(salary_cap))
    cur = int(getattr(player, "salary", 0) or 0)
    body = (
        f"選手: {getattr(player, 'name', '-')}\n"
        f"ポジション: {getattr(player, 'position', '-')}\n"
        f"年齢: {getattr(player, 'age', '-')}\n"
        f"OVR: {getattr(player, 'ovr', '-')}\n"
        f"現年俸: {cur:,} 円\n"
        f"提示年俸: {int(new_salary):,} 円\n"
        f"契約年数: {int(desired_years)} 年\n\n"
        f"再契約スコア: {float(resign_score):.1f}（基準 {float(threshold):.1f}）\n"
        f"契約後ペイロール見込: {int(current_team_salary):,} 円\n"
        f"ソフトキャップ: {soft_limit:,} 円\n\n"
        f"この条件で再契約オファーを出しますか？"
    )
    title = f"再契約 | {getattr(team, 'name', '')}"
    return bool(messagebox.askyesno(title, body, parent=parent))
