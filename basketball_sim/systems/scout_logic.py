from __future__ import annotations

import random
from typing import Dict, List, Tuple

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


SCOUT_FOCUS_OPTIONS = {
    "balanced": "Balanced",
    "shooting": "Shooting",
    "defense": "Defense",
    "playmaking": "Playmaking",
    "inside": "Inside",
    "athletic": "Athletic",
    "potential": "Potential",
}

SCOUT_DISPATCH_OPTIONS = {
    "highschool": "High School",
    "college": "College",
    "overseas": "Overseas",
}


def ensure_team_scout_profile(team: Team) -> None:
    """チームにスカウト関連の初期値を安全に補完する。"""
    if not hasattr(team, "scout_level") or getattr(team, "scout_level", None) is None:
        team.scout_level = 50
    team.scout_level = int(max(1, min(100, getattr(team, "scout_level", 50))))

    if not hasattr(team, "scout_focus") or getattr(team, "scout_focus", None) is None:
        team.scout_focus = "balanced"
    if getattr(team, "scout_focus", "balanced") not in SCOUT_FOCUS_OPTIONS:
        team.scout_focus = "balanced"

    if not hasattr(team, "scout_dispatch") or getattr(team, "scout_dispatch", None) is None:
        team.scout_dispatch = "college"
    if getattr(team, "scout_dispatch", "college") not in SCOUT_DISPATCH_OPTIONS:
        team.scout_dispatch = "college"


def get_scout_focus_label(team: Team) -> str:
    ensure_team_scout_profile(team)
    return SCOUT_FOCUS_OPTIONS.get(getattr(team, "scout_focus", "balanced"), "Balanced")


def set_team_scout_focus(team: Team, focus_key: str) -> None:
    ensure_team_scout_profile(team)
    if focus_key not in SCOUT_FOCUS_OPTIONS:
        focus_key = "balanced"
    team.scout_focus = focus_key


def get_scout_dispatch_label(team: Team) -> str:
    ensure_team_scout_profile(team)
    return SCOUT_DISPATCH_OPTIONS.get(getattr(team, "scout_dispatch", "college"), "College")


def set_team_scout_dispatch(team: Team, dispatch_key: str) -> None:
    ensure_team_scout_profile(team)
    if dispatch_key not in SCOUT_DISPATCH_OPTIONS:
        dispatch_key = "college"
    team.scout_dispatch = dispatch_key


def choose_ai_scout_dispatch(team: Team) -> str:
    ensure_team_scout_profile(team)

    coach_style = getattr(team, "coach_style", "balanced")
    strategy = getattr(team, "strategy", "balanced")

    if coach_style == "development":
        return "highschool"
    if strategy == "run_and_gun":
        return "overseas"
    if strategy == "inside":
        return "college"
    if coach_style == "offense":
        return random.choices(["college", "overseas", "highschool"], weights=[45, 40, 15], k=1)[0]
    if coach_style == "defense":
        return random.choices(["college", "highschool", "overseas"], weights=[50, 30, 20], k=1)[0]
    return random.choices(["college", "highschool", "overseas"], weights=[50, 30, 20], k=1)[0]


def assign_ai_scout_dispatches(teams: List[Team]) -> None:
    for team in teams:
        if getattr(team, "is_user_team", False):
            ensure_team_scout_profile(team)
            continue
        set_team_scout_dispatch(team, choose_ai_scout_dispatch(team))


def prompt_user_scout_dispatch(user_team: Team) -> None:
    ensure_team_scout_profile(user_team)

    print("\n=== Scout Dispatch ===")
    print("来年のドラフト候補調査先を選んでください。")
    print("1. 高校")
    print("2. 大学")
    print("3. 海外")

    mapping = {
        "1": "highschool",
        "2": "college",
        "3": "overseas",
    }

    while True:
        raw = input("番号: ").strip()
        if raw in mapping:
            set_team_scout_dispatch(user_team, mapping[raw])
            print(f"[SCOUT-DISPATCH] {user_team.name} -> {get_scout_dispatch_label(user_team)}")
            return
        print("正しい番号を入力してください。")


def choose_ai_scout_focus(team: Team) -> str:
    """AIチームの簡易スカウト方針。既存の戦術/HCスタイルを優先反映。"""
    ensure_team_scout_profile(team)

    coach_style = getattr(team, "coach_style", "balanced")
    strategy = getattr(team, "strategy", "balanced")

    if coach_style == "development":
        return "potential"
    if coach_style == "defense":
        return "defense"
    if coach_style == "offense":
        if strategy == "inside":
            return "inside"
        return "shooting"

    if strategy == "three_point":
        return "shooting"
    if strategy == "inside":
        return "inside"
    if strategy == "defense":
        return "defense"
    if strategy == "run_and_gun":
        return "athletic"

    return random.choices(
        ["balanced", "shooting", "defense", "playmaking", "inside", "athletic", "potential"],
        weights=[30, 12, 12, 10, 10, 10, 16],
        k=1,
    )[0]


def assign_ai_scout_focuses(teams: List[Team]) -> None:
    for team in teams:
        if getattr(team, "is_user_team", False):
            ensure_team_scout_profile(team)
            continue
        set_team_scout_focus(team, choose_ai_scout_focus(team))


def prompt_user_scout_focus(user_team: Team) -> None:
    ensure_team_scout_profile(user_team)

    print("\n=== Draft Combine / Scout Focus ===")
    print("今オフのスカウト重点項目を選んでください。")
    print("1. Balanced")
    print("2. Shooting")
    print("3. Defense")
    print("4. Playmaking")
    print("5. Inside")
    print("6. Athletic")
    print("7. Potential")

    mapping = {
        "1": "balanced",
        "2": "shooting",
        "3": "defense",
        "4": "playmaking",
        "5": "inside",
        "6": "athletic",
        "7": "potential",
    }

    while True:
        raw = input("番号: ").strip()
        if raw in mapping:
            set_team_scout_focus(user_team, mapping[raw])
            print(f"[SCOUT-FOCUS] {user_team.name} -> {get_scout_focus_label(user_team)}")
            return
        print("正しい番号を入力してください。")


def _potential_bonus(potential: str) -> float:
    p = str(potential).upper().strip()
    return {
        "S": 6.0,
        "A": 4.0,
        "B": 2.0,
        "C": 0.0,
        "D": -1.0,
    }.get(p, 0.0)


def _age_bonus(age: int) -> float:
    if age <= 18:
        return 2.0
    if age == 19:
        return 1.0
    if age == 20:
        return 0.0
    if age == 21:
        return -0.5
    return -1.0


def _featured_bonus(player: Player) -> float:
    reborn_type = getattr(player, "reborn_type", "none")
    if reborn_type == "special":
        return 5.0
    if getattr(player, "is_featured_prospect", False):
        return 5.0
    return 0.0


def _reborn_bonus(player: Player) -> float:
    reborn_type = getattr(player, "reborn_type", "none")
    if reborn_type in ("japanese_reborn", "jp", "international_reborn", "special"):
        return 3.0
    if getattr(player, "is_reborn", False):
        return 3.0
    return 0.0


def calculate_top_prospect_score(player: Player) -> float:
    base = float(getattr(player, "ovr", 0))
    base += _potential_bonus(getattr(player, "potential", "C"))
    base += _age_bonus(int(getattr(player, "age", 22)))
    base += _featured_bonus(player)
    base += _reborn_bonus(player)
    base += random.uniform(-0.5, 0.5)
    return round(base, 1)


def _scout_tier_from_score(scout_level: int) -> int:
    scout_level = int(max(1, min(100, scout_level)))
    if scout_level >= 90:
        return 5
    if scout_level >= 75:
        return 4
    if scout_level >= 60:
        return 3
    if scout_level >= 45:
        return 2
    return 1


def _base_ovr_error_by_level(level: int) -> int:
    return {
        1: 10,
        2: 7,
        3: 5,
        4: 3,
        5: 1,
    }.get(level, 5)


def _focused_keys_for_focus(focus: str) -> List[str]:
    mapping = {
        "balanced": [],
        "shooting": ["shoot", "three", "ft"],
        "defense": ["defense", "rebound"],
        "playmaking": ["passing", "drive"],
        "inside": ["rebound", "defense", "drive"],
        "athletic": ["stamina", "drive", "defense"],
        "potential": ["potential"],
    }
    return mapping.get(focus, [])


def _attribute_error(level: int, is_focused: bool) -> int:
    base = _base_ovr_error_by_level(level)
    if is_focused:
        return max(1, int(round(base * 0.5)))
    return base


def _make_range_text(actual: int, err: int) -> str:
    low = max(1, actual - err)
    high = min(99, actual + err)
    if low == high:
        return f"{low}"
    return f"{low}〜{high}"


def _grade_from_score(score: float) -> str:
    if score >= 82:
        return "S"
    if score >= 78:
        return "A+"
    if score >= 74:
        return "A"
    if score >= 70:
        return "A-"
    if score >= 66:
        return "B+"
    if score >= 62:
        return "B"
    if score >= 58:
        return "B-"
    if score >= 54:
        return "C+"
    if score >= 50:
        return "C"
    return "C-"


def _dispatch_ovr_bonus(dispatch: str) -> int:
    if dispatch == "college":
        return 1
    return 0


def _dispatch_attribute_bonus(dispatch: str, attr_name: str) -> int:
    if dispatch == "college" and attr_name in {"shoot", "defense", "stamina", "drive", "passing"}:
        return 1
    return 0


def _dispatch_potential_view(player: Player, dispatch: str) -> str:
    actual = str(getattr(player, "potential", "C")).upper()

    if dispatch == "highschool":
        return actual

    mistake_roll = 0.10
    if dispatch == "college":
        mistake_roll = 0.18
    elif dispatch == "overseas":
        mistake_roll = 0.22

    if random.random() >= mistake_roll:
        return actual

    if actual == "S":
        return random.choice(["A", "B"])
    if actual == "A":
        return random.choice(["S", "B"])
    if actual == "B":
        return random.choice(["A", "C"])
    if actual == "C":
        return random.choice(["B", "D"])
    return random.choice(["C", "D"])


def _dispatch_buzz_bonus(player: Player, dispatch: str) -> float:
    age = int(getattr(player, "age", 20))
    potential = str(getattr(player, "potential", "C")).upper()
    bonus = 0.0

    if dispatch == "highschool":
        if age <= 19:
            bonus += 2.0
        if potential in ("S", "A"):
            bonus += 2.0
    elif dispatch == "college":
        if age >= 20:
            bonus += 1.0
        bonus += max(0.0, (getattr(player, "ovr", 60) - 68) * 0.08)
    elif dispatch == "overseas":
        if getattr(player, "is_reborn", False):
            bonus += 2.5
        if getattr(player, "draft_origin_type", "") == "special":
            bonus += 2.5
        if getattr(player, "is_featured_prospect", False):
            bonus += 1.5

    return bonus


def generate_player_scout_report_for_team(player: Player, team: Team) -> Dict[str, object]:
    ensure_team_scout_profile(team)
    scout_score_value = int(getattr(team, "scout_level", 50))
    level = _scout_tier_from_score(scout_score_value)
    focus = getattr(team, "scout_focus", "balanced")
    focused_keys = _focused_keys_for_focus(focus)
    dispatch = getattr(team, "scout_dispatch", "college")

    actual_ovr = int(getattr(player, "ovr", 0))
    ovr_err = max(1, _base_ovr_error_by_level(level) - _dispatch_ovr_bonus(dispatch))
    if "potential" in focused_keys:
        ovr_err = max(1, ovr_err - 1)

    shoot_err = max(1, _attribute_error(level, "shoot" in focused_keys or "three" in focused_keys or "ft" in focused_keys) - _dispatch_attribute_bonus(dispatch, "shoot"))
    defense_err = max(1, _attribute_error(level, "defense" in focused_keys or "rebound" in focused_keys) - _dispatch_attribute_bonus(dispatch, "defense"))
    playmaking_err = max(1, _attribute_error(level, "passing" in focused_keys or "drive" in focused_keys) - _dispatch_attribute_bonus(dispatch, "passing"))
    inside_err = max(1, _attribute_error(level, "rebound" in focused_keys or "defense" in focused_keys or "drive" in focused_keys) - _dispatch_attribute_bonus(dispatch, "drive"))
    athletic_err = max(1, _attribute_error(level, "stamina" in focused_keys or "drive" in focused_keys or "defense" in focused_keys) - _dispatch_attribute_bonus(dispatch, "stamina"))

    scout_top_score = calculate_top_prospect_score(player)
    if level <= 2:
        scout_top_score += random.uniform(-2.5, 2.5)
    elif level == 3:
        scout_top_score += random.uniform(-1.5, 1.5)
    elif level == 4:
        scout_top_score += random.uniform(-1.0, 1.0)
    else:
        scout_top_score += random.uniform(-0.5, 0.5)

    potential_true = str(getattr(player, "potential", "C")).upper()
    if "potential" in focused_keys:
        shown_potential = potential_true
    else:
        shown_potential = _dispatch_potential_view(player, dispatch)

    return {
        "player_id": getattr(player, "player_id", None),
        "player_name": getattr(player, "name", "Unknown"),
        "focus": focus,
        "dispatch": dispatch,
        "dispatch_label": SCOUT_DISPATCH_OPTIONS.get(dispatch, "College"),
        "scout_level": scout_score_value,
        "scout_tier": level,
        "scout_grade": _grade_from_score(scout_top_score),
        "scout_top_score": round(scout_top_score, 1),
        "scout_ovr_range": _make_range_text(actual_ovr, ovr_err),
        "scout_potential": shown_potential,
        "shoot_range": _make_range_text(int(getattr(player, "shoot", 50)), shoot_err),
        "defense_range": _make_range_text(int(getattr(player, "defense", 50)), defense_err),
        "playmaking_range": _make_range_text(int(getattr(player, "passing", 50)), playmaking_err),
        "inside_range": _make_range_text(int(getattr(player, "rebound", 50)), inside_err),
        "athletic_range": _make_range_text(int(getattr(player, "stamina", 50)), athletic_err),
    }


def attach_scout_reports_for_all_teams(teams: List[Team], draft_pool: List[Player]) -> None:
    for team in teams:
        ensure_team_scout_profile(team)
        team.scout_reports = {}
        for player in draft_pool:
            report = generate_player_scout_report_for_team(player, team)
            team.scout_reports[getattr(player, "player_id", None)] = report


def get_team_scout_report(team: Team, player: Player) -> Dict[str, object]:
    ensure_team_scout_profile(team)
    if not hasattr(team, "scout_reports"):
        team.scout_reports = {}
    player_id = getattr(player, "player_id", None)
    report = team.scout_reports.get(player_id)
    if report is None:
        report = generate_player_scout_report_for_team(player, team)
        team.scout_reports[player_id] = report
    return report


def get_team_visible_draft_score(team: Team, player: Player) -> float:
    report = get_team_scout_report(team, player)
    return float(report.get("scout_top_score", calculate_top_prospect_score(player)))


def select_top_prospects(draft_pool: List[Player]) -> List[Player]:
    if not draft_pool:
        return []

    scored: List[Tuple[Player, float]] = []
    for player in draft_pool:
        score = calculate_top_prospect_score(player)
        setattr(player, "top_prospect_score", score)
        scored.append((player, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    high_band = [p for p, score in scored if score >= 78.0]
    if len(high_band) < 6:
        high_band = [p for p, _ in scored[:6]]
    elif len(high_band) > 10:
        high_band = high_band[:10]

    if len(high_band) < 6:
        while len(high_band) < 6 and len(high_band) < len(scored):
            candidate = scored[len(high_band)][0]
            if candidate not in high_band:
                high_band.append(candidate)

    if len(high_band) > 10:
        high_band = high_band[:10]

    top_ids = {getattr(p, "player_id", None) for p in high_band}
    for player in draft_pool:
        setattr(player, "is_top_prospect", getattr(player, "player_id", None) in top_ids)

    return high_band


def print_draft_combine_summary(teams: List[Team], draft_pool: List[Player]) -> List[Player]:
    print("\n=== Draft Combine ===")

    user_team = None
    for team in teams:
        if getattr(team, "is_user_team", False):
            user_team = team
            break

    if user_team is not None:
        ensure_team_scout_profile(user_team)
        print(
            f"[USER SCOUT] {user_team.name} | Level:{user_team.scout_level} | "
            f"Focus:{get_scout_focus_label(user_team)} | Dispatch:{get_scout_dispatch_label(user_team)}"
        )

    top_prospects = select_top_prospects(draft_pool)

    user_dispatch = "college"
    if user_team is not None:
        user_dispatch = getattr(user_team, "scout_dispatch", "college")
        top_prospects = sorted(
            top_prospects,
            key=lambda p: getattr(p, "top_prospect_score", 0.0) + _dispatch_buzz_bonus(p, user_dispatch),
            reverse=True,
        )

    print(f"Top Prospects: {len(top_prospects)}人")
    if user_team is not None:
        print("\n[Combine Report / User View]")
        for i, player in enumerate(top_prospects, 1):
            report = get_team_scout_report(user_team, player)
            print(
                f"{i}. {player.name} | {player.position} | "
                f"OVR:{report['scout_ovr_range']} | Pot:{report['scout_potential']} | "
                f"Grade:{report['scout_grade']} | Dispatch:{report.get('dispatch_label', 'College')} | "
                f"{_short_player_label(player)}"
            )
    else:
        print("\n[Combine Highlights]")
        for i, player in enumerate(top_prospects, 1):
            score = getattr(player, "top_prospect_score", calculate_top_prospect_score(player))
            print(
                f"{i}. {player.name} | {player.position} | "
                f"TopScore:{score:.1f} | Pot:{getattr(player, 'potential', 'C')} | {_short_player_label(player)}"
            )

    return top_prospects


def _short_player_label(player: Player) -> str:
    if getattr(player, "draft_profile_label", None):
        return str(getattr(player, "draft_profile_label"))
    if getattr(player, "is_reborn", False):
        from_name = getattr(player, "reborn_from_name", None) or getattr(player, "reborn_from", None)
        return f"転生 / 元:{from_name}" if from_name else "転生"
    if getattr(player, "reborn_type", "none") == "special":
        return "目玉新人"
    return "通常新人"
