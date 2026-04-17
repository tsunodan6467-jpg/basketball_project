from __future__ import annotations

import random
from typing import Dict, List, Optional

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.free_agent_market import assign_fa_pool_market_salary_on_release_to_fa
from basketball_sim.systems.generator import generate_single_player
from basketball_sim.systems.salary_cap_budget import league_level_for_team
from basketball_sim.systems.opening_roster_salary_v11 import _MIN_SALARY_D1, _MIN_SALARY_D2_D3
from basketball_sim.systems.resign_salary_anchor import (
    resign_anchor_lo_hi_effective,
    resign_nat_band_key,
)


YOUTH_GLOBAL_POLICIES = ("technical", "physical", "balanced")
YOUTH_FOCUS_POLICIES = ("pg", "shooter", "big", "defender", "balanced")


def ensure_team_youth_profile(team: Team) -> None:
    if not hasattr(team, "youth_players") or getattr(team, "youth_players", None) is None:
        team.youth_players = []
    if not hasattr(team, "youth_callups") or getattr(team, "youth_callups", None) is None:
        team.youth_callups = []

    team.youth_capacity = int(max(0, getattr(team, "youth_capacity", 10)))
    team.youth_callups_limit_per_year = int(max(0, getattr(team, "youth_callups_limit_per_year", 2)))
    team.youth_callups_used_this_year = int(max(0, getattr(team, "youth_callups_used_this_year", 0)))
    team.youth_graduate_rights_limit_per_year = int(max(0, getattr(team, "youth_graduate_rights_limit_per_year", 2)))
    team.youth_graduate_rights_used_this_year = int(max(0, getattr(team, "youth_graduate_rights_used_this_year", 0)))

    if getattr(team, "youth_policy_global", "balanced") not in YOUTH_GLOBAL_POLICIES:
        team.youth_policy_global = "balanced"
    if getattr(team, "youth_policy_focus", "balanced") not in YOUTH_FOCUS_POLICIES:
        team.youth_policy_focus = "balanced"

    inv = getattr(team, "youth_investment", None)
    if not isinstance(inv, dict):
        inv = {"facility": 50, "coaching": 50, "scout": 50, "community": 50}
    for k in ("facility", "coaching", "scout", "community"):
        inv[k] = int(max(0, min(100, inv.get(k, 50))))
    team.youth_investment = inv

    if not hasattr(team, "youth_prospect_ids") or getattr(team, "youth_prospect_ids", None) is None:
        team.youth_prospect_ids = []
    if not hasattr(team, "youth_rights_players") or getattr(team, "youth_rights_players", None) is None:
        team.youth_rights_players = []
    if not hasattr(team, "icon_youth_return_reservations") or getattr(team, "icon_youth_return_reservations", None) is None:
        team.icon_youth_return_reservations = []


def _investment_bonus(inv: Dict[str, int]) -> float:
    return (
        (inv.get("facility", 50) - 50) * 0.04
        + (inv.get("coaching", 50) - 50) * 0.05
        + (inv.get("scout", 50) - 50) * 0.03
        + (inv.get("community", 50) - 50) * 0.02
    )


def _youth_base_ovr_range(team: Team) -> tuple[int, int]:
    inv = getattr(team, "youth_investment", {"facility": 50, "coaching": 50, "scout": 50, "community": 50})
    bump = _investment_bonus(inv)
    low = int(48 + bump)
    high = int(62 + bump)
    low = max(42, min(60, low))
    high = max(low + 3, min(70, high))
    return low, high


def _choose_youth_position(team: Team) -> str:
    focus = getattr(team, "youth_policy_focus", "balanced")
    if focus == "pg":
        weights = {"PG": 44, "SG": 22, "SF": 14, "PF": 10, "C": 10}
    elif focus == "shooter":
        weights = {"PG": 20, "SG": 40, "SF": 22, "PF": 10, "C": 8}
    elif focus == "big":
        weights = {"PG": 10, "SG": 12, "SF": 18, "PF": 26, "C": 34}
    elif focus == "defender":
        weights = {"PG": 18, "SG": 22, "SF": 26, "PF": 20, "C": 14}
    else:
        weights = {"PG": 20, "SG": 22, "SF": 22, "PF": 18, "C": 18}
    return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def _choose_youth_potential(team: Team, base_ovr: int) -> str:
    inv = getattr(team, "youth_investment", {})
    scout = int(inv.get("scout", 50))
    coaching = int(inv.get("coaching", 50))
    roll = random.random()
    # v1: 確定化しない。投資で少しだけ上振れやすくする。
    s_chance = 0.02 + max(0.0, (scout - 50) * 0.0004) + (1.0 if base_ovr >= 60 else 0.0) * 0.01
    a_chance = 0.18 + max(0.0, (coaching - 50) * 0.0010)
    if roll < s_chance:
        return "S"
    if roll < s_chance + a_chance:
        return "A"
    if roll < s_chance + a_chance + 0.45:
        return "B"
    return "C"


def generate_youth_intake_for_team(team: Team) -> List[Player]:
    ensure_team_youth_profile(team)

    # reset yearly counters (v1)
    team.youth_callups_used_this_year = 0
    team.youth_graduate_rights_used_this_year = 0

    low, high = _youth_base_ovr_range(team)
    created: List[Player] = []

    while len(team.youth_players) + len(created) < int(getattr(team, "youth_capacity", 10)):
        age = random.choice([16, 17, 18])
        base_ovr = random.randint(low, high)
        pos = _choose_youth_position(team)
        _youth_div = int(league_level_for_team(team))
        p = generate_single_player(
            age_override=age,
            base_ovr_override=base_ovr,
            position_override=pos,
            nationality_override="Japan",
            league_market_division=_youth_div,
        )
        p.acquisition_type = "youth"
        p.acquisition_note = "youth_intake"
        p.youth_team_id = getattr(team, "team_id", None)
        p.team_id = None
        p.salary = 0
        p.contract_years_left = 0
        p.contract_total_years = 0
        p.potential = _choose_youth_potential(team, base_ovr)
        p.youth_reputation = ""
        p.youth_hidden_score = 0.0
        created.append(p)

    team.youth_players.extend(created)
    return created


def process_icon_youth_returns_for_team(team: Team) -> List[Player]:
    """
    アイコンのユース復帰予約を進め、0になったらユースへ再登場させる。
    v1: まずは「生成して youth_players に積む」まで。
    """
    ensure_team_youth_profile(team)
    reservations = list(getattr(team, "icon_youth_return_reservations", []) or [])
    if not reservations:
        return []

    produced: List[Player] = []
    kept: List[dict] = []

    for r in reservations:
        try:
            years_left = int(r.get("years_left", 0))
        except Exception:
            years_left = 0
        years_left -= 1
        if years_left > 0:
            r["years_left"] = years_left
            kept.append(r)
            continue

        peak = int(r.get("peak_ovr", 70) or 70)
        base_ovr = int(max(55, min(70, peak * random.uniform(0.68, 0.75) + random.randint(-2, 2))))
        age = random.choice([16, 17, 18])
        pos = str(r.get("position", "SF") or "SF")
        _youth_div = int(league_level_for_team(team))
        p = generate_single_player(
            age_override=age,
            base_ovr_override=base_ovr,
            position_override=pos,
            nationality_override="Japan",
            league_market_division=_youth_div,
        )
        p.name = str(r.get("from_name", p.name) or p.name)
        p.is_icon = True
        p.icon_locked = True
        p.acquisition_type = "youth"
        p.acquisition_note = "icon_youth_return"
        # UI/ログで目立たせるための内部バッジ（v1土台）
        p.nickname_title = "ICON LEGACY"
        p.title_level = max(int(getattr(p, "title_level", 0) or 0), 3)
        p.youth_team_id = getattr(team, "team_id", None)
        p.team_id = None
        p.salary = 0
        p.contract_years_left = 0
        p.contract_total_years = 0
        p.potential = random.choices(["S", "A", "B"], weights=[45, 45, 10], k=1)[0]
        p.youth_reputation = "A"
        p.youth_hidden_score = 80.0 + random.uniform(-2.0, 2.0)
        produced.append(p)

    team.icon_youth_return_reservations = kept
    if produced:
        # If youth is full, drop lowest non-icon youth first.
        cap = int(getattr(team, "youth_capacity", 10))
        for p in produced:
            if len(team.youth_players) >= cap:
                non_icon = [x for x in team.youth_players if not bool(getattr(x, "is_icon", False))]
                if non_icon:
                    drop = min(non_icon, key=lambda x: int(getattr(x, "ovr", 0) or 0))
                    team.youth_players.remove(drop)
            team.youth_players.append(p)
    return produced


def _score_youth_prospect(team: Team, player: Player) -> float:
    inv = getattr(team, "youth_investment", {})
    base = float(getattr(player, "ovr", 0))
    pot = str(getattr(player, "potential", "C")).upper()
    pot_bonus = {"S": 6.0, "A": 4.0, "B": 2.0, "C": 0.0, "D": -1.0}.get(pot, 0.0)

    global_policy = getattr(team, "youth_policy_global", "balanced")
    if global_policy == "technical":
        policy_bonus = (inv.get("coaching", 50) - 50) * 0.03
    elif global_policy == "physical":
        policy_bonus = (inv.get("facility", 50) - 50) * 0.03
    else:
        policy_bonus = (sum(inv.get(k, 50) for k in ("facility", "coaching", "scout", "community")) / 4 - 50) * 0.02

    age_bonus = {16: 1.6, 17: 0.8, 18: 0.0}.get(int(getattr(player, "age", 17)), 0.0)

    score = base + pot_bonus + policy_bonus + age_bonus + random.uniform(-0.8, 0.8)
    return round(score, 2)


def refresh_youth_prospects_for_team(team: Team) -> List[Player]:
    ensure_team_youth_profile(team)
    if not team.youth_players:
        team.youth_prospect_ids = []
        return []

    scored = [(p, _score_youth_prospect(team, p)) for p in team.youth_players]
    scored.sort(key=lambda x: x[1], reverse=True)

    top = [p for p, _s in scored[:3]]
    for p, s in scored:
        p.youth_hidden_score = float(s)
        p.youth_reputation = ""

    # v1: A〜D は相対評価（上位3だけ付与）
    # A: 1位かつスコアが十分、B: 2位、C: 3位、Dはv1では有力候補に付けない
    if top:
        top[0].youth_reputation = "A" if getattr(top[0], "youth_hidden_score", 0.0) >= 66.0 else "B"
    if len(top) >= 2:
        top[1].youth_reputation = "B"
    if len(top) >= 3:
        top[2].youth_reputation = "C"

    team.youth_prospect_ids = [int(getattr(p, "player_id", 0)) for p in top if getattr(p, "player_id", None) is not None]
    return top


def advance_youth_year_for_team(team: Team) -> None:
    """
    オフシーズンの年次更新（v1）。
    - ユース選手は全員 age+1（16〜18→17〜19）
    - OVRは微小に伸びる（投資でわずかに期待値が上がるが確定化はしない）
    """
    ensure_team_youth_profile(team)
    inv = getattr(team, "youth_investment", {})
    coaching = int(inv.get("coaching", 50))
    facility = int(inv.get("facility", 50))
    bump = (coaching - 50) * 0.015 + (facility - 50) * 0.010

    for p in list(getattr(team, "youth_players", []) or []):
        p.age = int(getattr(p, "age", 16)) + 1
        grow = random.random()
        delta = 0
        # 期待値は小さく、年齢が若いほど伸びやすい
        if grow < 0.55:
            delta = 1
        if grow < 0.18:
            delta = 2
        if grow < 0.04:
            delta = 3
        delta += int(round(bump))
        if random.random() < 0.20:
            delta -= 1
        p.ovr = int(max(40, min(78, int(getattr(p, "ovr", 50)) + delta)))


def graduate_youth_players_for_team(team: Team) -> List[Player]:
    """
    卒業（v1最小）。
    - オフシーズン時点で age>=19 を「卒業」とみなす（18歳シーズン終了後）
    - 自クラブは一部を優先確保（youth_rights_players へ）
    - 残りはドラフトへ流す（呼び出し側で draft_pool へ追加）
    """
    ensure_team_youth_profile(team)
    grads = [p for p in (getattr(team, "youth_players", []) or []) if int(getattr(p, "age", 0)) >= 19]
    if not grads:
        return []

    # 有力順（scoreが未設定ならrefreshしてから）
    for p in grads:
        if not getattr(p, "youth_hidden_score", 0.0):
            p.youth_hidden_score = _score_youth_prospect(team, p)
    grads.sort(key=lambda p: float(getattr(p, "youth_hidden_score", 0.0)), reverse=True)

    limit = int(getattr(team, "youth_graduate_rights_limit_per_year", 2))
    used = int(getattr(team, "youth_graduate_rights_used_this_year", 0))
    remaining = max(0, limit - used)

    keep = grads[:remaining]
    send_to_draft = grads[remaining:]

    for p in keep:
        # v1: 卒業と同時に「ユース枠」でトップに追加（既存ロスターを削らず受け入れる）
        p.team_id = getattr(team, "team_id", None)
        p.acquisition_type = "youth_graduate"
        p.acquisition_note = "youth_graduate_rights"
        getattr(team, "youth_rights_players", []).append(p)
        team.youth_graduate_rights_used_this_year = int(getattr(team, "youth_graduate_rights_used_this_year", 0)) + 1

    for p in send_to_draft:
        p.team_id = None
        p.acquisition_type = "youth"
        p.acquisition_note = f"youth_graduate_draft_from:{getattr(team, 'team_id', None)}"
        p.draft_origin_type = "youth"
        p.draft_profile_label = f"ユース卒({getattr(team, 'name', 'Unknown')})"
        p.is_draft_prospect = False
        p.draft_market_grade = ""

    team.youth_players = [p for p in team.youth_players if p not in grads]
    team.youth_prospect_ids = []
    return send_to_draft


def _trim_team_roster_to_13(team: Team, free_agents: Optional[List[Player]] = None) -> None:
    """
    v1安全策:
    - 19歳でプロ契約（通常ロスター枠）に入った結果 13人を超えたら整理する
    - ユース枠（acquisition_type == "youth"）は将来のため保護
    """
    roster = list(getattr(team, "players", []) or [])
    if len(roster) <= 13:
        return

    candidates = [
        p for p in roster
        if not bool(getattr(p, "icon_locked", False))
        and str(getattr(p, "acquisition_type", "") or "") != "youth"
    ]
    if not candidates:
        return

    release = min(
        candidates,
        key=lambda p: (int(getattr(p, "ovr", 0) or 0), int(getattr(p, "age", 99) or 99)),
    )
    team.remove_player(release)
    release.contract_years_left = 0
    assign_fa_pool_market_salary_on_release_to_fa(release, team=team)
    if free_agents is not None:
        free_agents.append(release)


def _youth_graduate_roster_contract_salary(team: Team, player: Player) -> int:
    """
    ユース卒業の「プロ契約（通常ロスター）」年俸。
    固定 MIN は使わず、正本 v1.1（opening 帯 + resign_anchor の bottom・若手上限）に接続する。
    """
    div = int(max(1, min(3, int(getattr(team, "league_level", 3) or 3))))
    age = int(getattr(player, "age", 19) or 19)
    nat_key = resign_nat_band_key(player)
    lo, hi = resign_anchor_lo_hi_effective(div, nat_key, "bottom", age)
    ovr = int(max(40, min(99, int(getattr(player, "ovr", 52) or 52))))
    t = max(0.0, min(1.0, (ovr - 40) / 59.0))
    base = int(lo + (hi - lo) * (0.22 + 0.58 * float(t)))
    base += int(random.randint(-200_000, 200_000))
    sal = int(max(lo, min(hi, base)))
    floor = _MIN_SALARY_D1 if div == 1 else _MIN_SALARY_D2_D3
    return int(max(floor, sal))


def run_youth_offseason_update_for_teams(teams: List[Team], free_agents: Optional[List[Player]] = None) -> List[Player]:
    """
    オフシーズンで一括実行する v1 更新。
    返り値: ドラフトへ流すユース卒業生
    """
    draft_entrants: List[Player] = []
    for t in teams:
        ensure_team_youth_profile(t)
        advance_youth_year_for_team(t)
        process_icon_youth_returns_for_team(t)
        # 卒業→(一部は自クラブがプロ契約＝通常ロスター枠) / それ以外はドラフトへ
        before_rights = len(getattr(t, "youth_rights_players", []) or [])
        draft_entrants.extend(graduate_youth_players_for_team(t))

        # youth_rights_players に積まれた分をプロ契約扱いで roster へ追加（v1は自動）
        new_rights = list(getattr(t, "youth_rights_players", []) or [])[before_rights:]
        for p in new_rights:
            p.acquisition_type = "youth_graduate"
            p.acquisition_note = "youth_sign"
            p.salary = _youth_graduate_roster_contract_salary(t, p)
            p.contract_years_left = 2
            p.contract_total_years = 2
            t.add_player(p, force=True)
            _trim_team_roster_to_13(t, free_agents=free_agents)

        generate_youth_intake_for_team(t)
        refresh_youth_prospects_for_team(t)
    return draft_entrants


def callup_u18_youth_player(team: Team, player: Player) -> bool:
    """
    16〜18歳のユース選手を、ユース枠としてトップ側に保持する（通常ロスター枠とは別）。
    v1では試合起用へ自動反映はしない（13人前提の既存システムを壊さないため）。
    """
    ensure_team_youth_profile(team)
    if player not in getattr(team, "youth_players", []):
        return False
    if int(getattr(player, "age", 0)) >= 19:
        return False

    limit = int(getattr(team, "youth_callups_limit_per_year", 2))
    used = int(getattr(team, "youth_callups_used_this_year", 0))
    if used >= limit:
        return False

    team.youth_players.remove(player)
    team.youth_callups.append(player)
    team.youth_callups_used_this_year = used + 1

    player.team_id = getattr(team, "team_id", None)
    player.acquisition_type = "youth"
    player.acquisition_note = "u18_callup"
    return True
