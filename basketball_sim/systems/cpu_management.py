"""
CPU クラブの軽量な裏経営（ラウンド終了時）。

ユーザーチームは対象外。施設・スポンサー・広報・グッズ・人気などを低確率で調整。
`management.cpu_mgmt_log` に裏処理の要約を残す（デバッグ・セーブ確認用）。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §4
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, List, Sequence

from basketball_sim.systems.facility_investment import (
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    commit_facility_upgrade,
)
from basketball_sim.systems.merchandise_management import try_cpu_merchandise_advance
from basketball_sim.systems.pr_campaign_management import try_cpu_pr_campaign

MAX_CPU_TEAMS_PER_ROUND = 22
MAX_CPU_MGMT_LOG = 48


def append_cpu_management_log(team: Any, season: Any, action: str, detail: str) -> None:
    if not hasattr(team, "management") or team.management is None or not isinstance(team.management, dict):
        team.management = {}
    log = team.management.get("cpu_mgmt_log")
    if not isinstance(log, list):
        log = []
        team.management["cpu_mgmt_log"] = log
    rnd = int(getattr(season, "current_round", 0) or 0)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "round": rnd,
        "action": str(action)[:64],
        "detail": str(detail)[:220],
    }
    log.append(entry)
    while len(log) > MAX_CPU_MGMT_LOG:
        log.pop(0)


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


def _maybe_cpu_facility_upgrade(team: Any, season: Any, rng: random.Random) -> None:
    if rng.random() >= _cpu_facility_roll_probability(team, rng):
        return
    candidates: List[str] = [
        k for k in FACILITY_ORDER if can_commit_facility_upgrade(team, k)[0]
    ]
    if not candidates:
        return
    fk = rng.choice(candidates)
    ok, _ = commit_facility_upgrade(team, fk)
    if ok:
        append_cpu_management_log(team, season, "facility_upgrade", fk)


def _maybe_cpu_sponsor_drift(team: Any, season: Any, rng: random.Random) -> None:
    if rng.random() >= 0.052:
        return
    delta = int(rng.choice((-1, -1, 0, 0, 1, 1)))
    sp = int(getattr(team, "sponsor_power", 50))
    new_sp = max(1, min(100, sp + delta))
    if new_sp != sp:
        setattr(team, "sponsor_power", new_sp)
        append_cpu_management_log(team, season, "sponsor_power", f"{sp}→{new_sp}")


def _maybe_cpu_popularity_fan_drift(team: Any, season: Any, rng: random.Random) -> None:
    changed = False
    if rng.random() < 0.062:
        d = int(rng.choice((-1, 0, 0, 0, 1)))
        pop = int(getattr(team, "popularity", 50))
        new_pop = max(0, min(100, pop + d))
        if new_pop != pop:
            setattr(team, "popularity", new_pop)
            changed = True
    if rng.random() < 0.038:
        fb = int(getattr(team, "fan_base", 0))
        add = int(rng.randint(0, 3))
        if add:
            setattr(team, "fan_base", max(0, fb + add))
            changed = True
    if changed:
        append_cpu_management_log(team, season, "fan_pop_drift", "popularity/fan_base")


def apply_cpu_management_to_team(team: Any, rng: random.Random, season: Any) -> None:
    """1 チーム・1 ラウンド分の裏経営（複数アクションあり得る）。"""
    if bool(getattr(team, "is_user_team", False)):
        return
    if hasattr(team, "_ensure_history_fields"):
        try:
            team._ensure_history_fields()
        except Exception:
            pass
    _maybe_cpu_facility_upgrade(team, season, rng)
    _maybe_cpu_sponsor_drift(team, season, rng)
    _maybe_cpu_popularity_fan_drift(team, season, rng)
    if try_cpu_pr_campaign(team, season, rng):
        append_cpu_management_log(team, season, "pr_campaign", "広報施策")
    if try_cpu_merchandise_advance(team, season, rng):
        append_cpu_management_log(team, season, "merchandise", "グッズ開発")


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
            apply_cpu_management_to_team(t, rng, season)
        except Exception:
            continue
