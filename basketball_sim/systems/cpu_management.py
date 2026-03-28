"""
CPU クラブの軽量な裏経営（ラウンド終了時）。

ユーザーチームは対象外。施設・スポンサー力・人気などを低確率で微調整。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §4
"""

from __future__ import annotations

import random
from typing import Any, List, Sequence

from basketball_sim.systems.facility_investment import (
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
)

MAX_CPU_TEAMS_PER_ROUND = 22


def _round_rng(season: Any) -> random.Random:
    from basketball_sim.utils.sim_rng import get_last_simulation_seed

    base = get_last_simulation_seed()
    if base is None:
        base = 2_463_534_242
    r = int(getattr(season, "current_round", 0) or 0)
    tid = int(getattr(season, "game_count", 0) or 0)
    return random.Random((int(base) & 0xFFFFFFFF) ^ (r * 1_000_003) ^ (tid * 917_521))


def _cpu_facility_roll_probability(team: Any, rng: random.Random) -> float:
    ll = int(getattr(team, "league_level", 3))
    p = {1: 0.048, 2: 0.032, 3: 0.021}.get(min(3, max(1, ll)), 0.022)
    exp = str(getattr(team, "owner_expectation", "playoff_race"))
    if exp in {"title_challenge", "title_or_bust"}:
        p *= 1.38
    elif exp == "rebuild":
        p *= 0.8
    w = int(getattr(team, "regular_wins", 0))
    l = int(getattr(team, "regular_losses", 0))
    if w + l > 6:
        ratio = w / max(1, w + l)
        if ratio >= 0.58:
            p *= 1.12
        elif ratio <= 0.36:
            p *= 0.86
    # わずかなばらつき（同シードでもチーム間で差が付く）
    p *= 0.92 + 0.16 * rng.random()
    return min(0.085, max(0.006, p))


def _maybe_cpu_facility_upgrade(team: Any, rng: random.Random) -> None:
    if rng.random() >= _cpu_facility_roll_probability(team, rng):
        return
    candidates: List[str] = [
        k for k in FACILITY_ORDER if can_commit_facility_upgrade(team, k)[0]
    ]
    if not candidates:
        return
    commit_facility_upgrade(team, rng.choice(candidates))


def _maybe_cpu_sponsor_drift(team: Any, rng: random.Random) -> None:
    if rng.random() >= 0.052:
        return
    delta = int(rng.choice((-1, -1, 0, 0, 1, 1)))
    sp = int(getattr(team, "sponsor_power", 50))
    setattr(team, "sponsor_power", max(1, min(100, sp + delta)))


def _maybe_cpu_popularity_fan_drift(team: Any, rng: random.Random) -> None:
    if rng.random() < 0.062:
        d = int(rng.choice((-1, 0, 0, 0, 1)))
        pop = int(getattr(team, "popularity", 50))
        setattr(team, "popularity", max(0, min(100, pop + d)))
    if rng.random() < 0.038:
        fb = int(getattr(team, "fan_base", 0))
        setattr(team, "fan_base", max(0, fb + int(rng.randint(0, 3))))


def apply_cpu_management_to_team(team: Any, rng: random.Random) -> None:
    """1 チーム・1 ラウンド分の裏経営（複数アクションあり得る）。"""
    if bool(getattr(team, "is_user_team", False)):
        return
    if hasattr(team, "_ensure_history_fields"):
        try:
            team._ensure_history_fields()
        except Exception:
            pass
    _maybe_cpu_facility_upgrade(team, rng)
    _maybe_cpu_sponsor_drift(team, rng)
    _maybe_cpu_popularity_fan_drift(team, rng)


def run_cpu_management_after_round(season: Any) -> None:
    """
    `Season.simulate_next_round` のラウンド加算直後に呼ぶ。
    シーズン終了後は何もしない。
    """
    if bool(getattr(season, "season_finished", False)):
        return
    teams: Sequence[Any] = getattr(season, "all_teams", None) or []
    if not teams:
        return
    cpu = [t for t in teams if not bool(getattr(t, "is_user_team", False))]
    if not cpu:
        return
    rng = _round_rng(season)
    rng.shuffle(cpu)
    n = min(len(cpu), MAX_CPU_TEAMS_PER_ROUND)
    for t in cpu[:n]:
        try:
            apply_cpu_management_to_team(t, rng)
        except Exception:
            continue
