from typing import List, Optional, Tuple
import random

from basketball_sim.models.team import Team
from basketball_sim.models.player import Player

try:
    from basketball_sim.systems.scout_logic import get_team_scout_report, get_team_visible_draft_score
except Exception:  # フォールバック安全策
    get_team_scout_report = None
    get_team_visible_draft_score = None


USER_DRAFT_VISIBLE_CANDIDATES = 12


def _get_player_label(player: Player) -> str:
    profile_label = getattr(player, "draft_profile_label", None)
    if profile_label:
        return profile_label

    reborn_type = getattr(player, "reborn_type", "none")

    if reborn_type == "special":
        hint = getattr(player, "reborn_archetype_hint", None)
        return f"目玉新人 / {hint}" if hint else "目玉新人"

    if reborn_type in ("japanese_reborn", "jp"):
        from_name = getattr(player, "reborn_from_name", None) or getattr(player, "reborn_from", None)
        return f"転生新人 / 元:{from_name}" if from_name else "転生新人"

    if getattr(player, "is_reborn", False):
        from_name = getattr(player, "reborn_from", None)
        return f"転生新人 / 元:{from_name}" if from_name else "転生新人"

    return "通常新人"



def _get_draft_priority_bonus(player: Player) -> int:
    bonus = getattr(player, "draft_priority_bonus", None)
    if bonus is not None:
        return int(bonus)

    reborn_type = getattr(player, "reborn_type", "none")

    if reborn_type == "special":
        return 8

    if reborn_type in ("japanese_reborn", "jp"):
        return 2

    if getattr(player, "is_featured_prospect", False):
        return 8

    if getattr(player, "is_reborn", False):
        return 2

    return 0



def _get_draft_score(player: Player) -> float:
    ovr = getattr(player, "ovr", 0)
    bonus = _get_draft_priority_bonus(player)

    potential_bonus_map = {
        "S": 2.0,
        "A": 1.0,
        "B": 0.3,
        "C": 0.0,
        "D": -0.2,
    }

    potential = str(getattr(player, "potential", "C")).upper()
    potential_bonus = potential_bonus_map.get(potential, 0.0)

    return ovr + bonus + potential_bonus



def _get_team_base_visible_score(team: Team, player: Player) -> float:
    if get_team_visible_draft_score is not None:
        try:
            return float(get_team_visible_draft_score(team, player))
        except Exception:
            pass
    return _get_draft_score(player)



def _get_team_draft_score(team: Team, player: Player) -> float:
    """チームごとのドラフト評価（Scout Report対応版）"""
    base_score = _get_team_base_visible_score(team, player)

    same_pos = sum(1 for p in team.players if p.position == player.position)

    need_bonus = 0.0
    if same_pos <= 1:
        need_bonus += 2.0
    elif same_pos <= 2:
        need_bonus += 1.0

    coach_style = getattr(team, "coach_style", "balanced")
    style_bonus = 0.0

    try:
        if coach_style == "offense":
            shoot = player.get_adjusted_attribute("shoot")
            if shoot >= 70:
                style_bonus += 1.5
        elif coach_style == "defense":
            defense = player.get_adjusted_attribute("defense")
            if defense >= 70:
                style_bonus += 1.5
        elif coach_style == "development":
            potential = getattr(player, "potential", "C")
            if potential in ("S", "A"):
                style_bonus += 1.2
    except Exception:
        pass

    random_bonus = random.uniform(-0.5, 0.5)
    return base_score + need_bonus + style_bonus + random_bonus



def _print_draft_buzz(draft_pool: List[Player], top_n: int = 5):
    if not draft_pool:
        return

    print("\n[Draft Buzz]")

    # Combineで is_top_prospect が付いていればそれを優先。なければ従来ロジックで表示。
    top_players = [p for p in draft_pool if getattr(p, "is_top_prospect", False)]
    if top_players:
        top_players = sorted(
            top_players,
            key=lambda p: (getattr(p, "top_prospect_score", _get_draft_score(p)), getattr(p, "ovr", 0)),
            reverse=True,
        )[:top_n]
    else:
        top_players = sorted(
            draft_pool,
            key=lambda p: (_get_draft_score(p), getattr(p, "ovr", 0)),
            reverse=True,
        )[:top_n]

    for i, p in enumerate(top_players, 1):
        label = _get_player_label(p)
        print(
            f"{i}. {p.name} | {p.position} | OVR:{p.ovr} | "
            f"Potential:{p.potential} | {label}"
        )



def _set_draft_acquisition(player: Player, team: Team, pick_num: int):
    player.acquisition_type = "draft"
    player.acquisition_note = f"pick_{pick_num}_to_{team.name}"



def _record_team_draft_history(team: Team, player: Player, pick_num: int):
    if hasattr(team, "add_history_transaction"):
        label = _get_player_label(player)
        note = (
            f"draft_pick={pick_num} | "
            f"player={player.name} | "
            f"ovr={player.ovr} | "
            f"potential={player.potential} | "
            f"label={label}"
        )
        team.add_history_transaction(
            transaction_type="draft",
            player=player,
            note=note,
        )



def _record_player_draft_career(player: Player, team: Team, pick_num: int):
    if hasattr(player, "add_career_entry"):
        label = _get_player_label(player)
        player.add_career_entry(
            season=max(1, getattr(player, "years_pro", 0) + 1),
            team_name=team.name,
            event="Draft",
            note=f"Pick {pick_num} / {label}",
        )



def _get_rookie_roster_value(player: Player, pick_num: int) -> float:
    score = float(getattr(player, "ovr", 0))

    potential = str(getattr(player, "potential", "C")).upper()
    potential_bonus_map = {
        "S": 6.0,
        "A": 4.0,
        "B": 2.0,
        "C": 0.5,
        "D": -1.0,
    }
    score += potential_bonus_map.get(potential, 0.0)

    age = int(getattr(player, "age", 22))
    if age <= 18:
        score += 3.0
    elif age <= 19:
        score += 2.0
    elif age <= 20:
        score += 1.0
    elif age >= 22:
        score -= 1.0

    score += min(6.0, max(0.0, _get_draft_priority_bonus(player) * 0.8))

    if pick_num <= 8:
        score += 4.0
    elif pick_num <= 16:
        score += 2.5
    elif pick_num <= 24:
        score += 1.2
    elif pick_num <= 32:
        score += 0.5
    else:
        score -= 0.8

    return round(score, 1)



def _get_existing_player_keep_value(player: Player) -> float:
    score = float(getattr(player, "ovr", 0))

    age = int(getattr(player, "age", 24))
    if age <= 22:
        score += 2.0
    elif age >= 31:
        score -= 1.0
    elif age >= 34:
        score -= 2.5

    potential = str(getattr(player, "potential", "C")).upper()
    potential_bonus_map = {
        "S": 3.0,
        "A": 2.0,
        "B": 1.0,
        "C": 0.0,
        "D": -1.0,
    }
    score += potential_bonus_map.get(potential, 0.0)

    years_pro = int(getattr(player, "years_pro", 0))
    if years_pro >= 6:
        score -= 0.8
    if years_pro >= 9:
        score -= 1.0

    contract_years_left = int(getattr(player, "contract_years_left", 0))
    if contract_years_left >= 2:
        score += 0.8
    elif contract_years_left == 0:
        score -= 0.8

    if getattr(player, "icon_locked", False):
        score += 99.0

    return round(score, 1)



def _find_release_candidate(team: Team) -> Optional[Player]:
    candidates = []
    for player in getattr(team, "players", []):
        if getattr(player, "icon_locked", False):
            continue
        candidates.append(player)

    if not candidates:
        return None

    return min(candidates, key=lambda p: (_get_existing_player_keep_value(p), getattr(p, "ovr", 0), getattr(p, "age", 99)))



def _required_release_margin(pick_num: int, rookie: Player, release_player: Player) -> float:
    margin = 3.0

    if pick_num <= 8:
        margin += 0.0
    elif pick_num <= 16:
        margin += 1.0
    elif pick_num <= 24:
        margin += 2.0
    elif pick_num <= 32:
        margin += 3.0
    else:
        margin += 6.0

    rookie_ovr = int(getattr(rookie, "ovr", 0))
    release_ovr = int(getattr(release_player, "ovr", 0))
    ovr_gap = rookie_ovr - release_ovr

    if ovr_gap < 0:
        margin += abs(ovr_gap) * 2.0
    elif ovr_gap == 0:
        margin += 1.0

    potential = str(getattr(rookie, "potential", "C")).upper()
    if potential == "S":
        margin -= 1.5
    elif potential == "A":
        margin -= 0.8
    elif potential == "D":
        margin += 1.0

    age = int(getattr(rookie, "age", 22))
    if age <= 18:
        margin -= 0.8
    elif age >= 22:
        margin += 0.8

    if pick_num >= 33 and rookie_ovr < release_ovr:
        margin += 4.0
    if pick_num >= 33 and rookie_ovr <= release_ovr - 2:
        margin += 3.0

    if pick_num >= 33 and rookie_ovr <= 55:
        margin += 2.5
    if pick_num >= 33 and rookie_ovr <= 53:
        margin += 2.0

    return round(max(2.0, margin), 1)



def _should_keep_rookie_over_existing(rookie: Player, release_player: Player, pick_num: int) -> Tuple[bool, float, float, float]:
    rookie_score = _get_rookie_roster_value(rookie, pick_num)
    release_score = _get_existing_player_keep_value(release_player)
    margin = _required_release_margin(pick_num, rookie, release_player)

    rookie_ovr = int(getattr(rookie, "ovr", 0))
    release_ovr = int(getattr(release_player, "ovr", 0))

    if pick_num >= 33 and rookie_ovr < release_ovr:
        potential = str(getattr(rookie, "potential", "C")).upper()
        rookie_age = int(getattr(rookie, "age", 22))
        exceptional_case = potential == "S" and rookie_age <= 19 and (release_ovr - rookie_ovr) <= 1
        if not exceptional_case:
            return False, rookie_score, release_score, margin

    decision = rookie_score >= (release_score + margin)
    return decision, rookie_score, release_score, margin



def _get_report_value(team: Team, player: Player, key: str, fallback: str) -> str:
    if get_team_scout_report is None:
        return fallback
    try:
        report = get_team_scout_report(team, player)
        return str(report.get(key, fallback))
    except Exception:
        return fallback



def _get_user_visible_candidates(team: Team, draft_pool: List[Player]) -> List[Player]:
    scored_candidates = []
    for player in draft_pool:
        visible_score = _get_team_base_visible_score(team, player)
        scored_candidates.append((player, visible_score, getattr(player, "ovr", 0)))

    scored_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [p for p, _, _ in scored_candidates[:USER_DRAFT_VISIBLE_CANDIDATES]]


def _parse_report_range_mid(value: str, fallback: int = 50) -> int:
    raw = str(value).strip()
    if not raw or raw == "?":
        return int(fallback)
    if "〜" in raw:
        left, right = raw.split("〜", 1)
        try:
            return int((int(left) + int(right)) / 2)
        except Exception:
            return int(fallback)
    try:
        return int(raw)
    except Exception:
        return int(fallback)


def _build_scout_comment(team: Team, player: Player) -> str:
    comments = []

    age = int(getattr(player, "age", 20))
    archetype = str(getattr(player, "archetype", "") or "")
    work_ethic = int(getattr(player, "work_ethic", 50))
    basketball_iq = int(getattr(player, "basketball_iq", 50))
    competitiveness = int(getattr(player, "competitiveness", 50))

    scout_ovr = _get_report_value(team, player, "scout_ovr_range", str(getattr(player, "ovr", 0)))
    scout_potential = _get_report_value(team, player, "scout_potential", str(getattr(player, "potential", "C")))
    shoot_range = _get_report_value(team, player, "shoot_range", "?")
    defense_range = _get_report_value(team, player, "defense_range", "?")
    athletic_range = _get_report_value(team, player, "athletic_range", "?")
    inside_range = _get_report_value(team, player, "rebound_range", "?")
    playmaking_range = _get_report_value(team, player, "passing_range", "?")

    ovr_mid = _parse_report_range_mid(scout_ovr, getattr(player, "ovr", 50))
    shoot_mid = _parse_report_range_mid(shoot_range, 50)
    defense_mid = _parse_report_range_mid(defense_range, 50)
    athletic_mid = _parse_report_range_mid(athletic_range, 50)
    inside_mid = _parse_report_range_mid(inside_range, 50)
    playmaking_mid = _parse_report_range_mid(playmaking_range, 50)

    potential = str(scout_potential).upper()

    profile_comments = []
    trait_comments = []
    context_comments = []

    # どんな候補か
    if potential == "S":
        profile_comments.append("大化け候補" if age <= 20 else "上位指名級の素材")
    elif potential == "A":
        profile_comments.append("素材型" if age <= 20 else "伸びしろ大")
    elif potential == "B":
        if age <= 20:
            profile_comments.append("伸びしろ大")
        elif ovr_mid >= 68:
            profile_comments.append("即戦力寄り")
    elif ovr_mid >= 72:
        profile_comments.append("即戦力寄り")
    elif age <= 19:
        profile_comments.append("育成前提")

    # 強み。身体能力は本当に高い時だけ「武器」
    if athletic_mid >= 90:
        trait_comments.append("身体能力が武器")
    elif athletic_mid >= 82:
        trait_comments.append("運動能力に魅力")

    if defense_mid >= 72:
        trait_comments.append("守備評価が高い")
    elif defense_mid >= 66:
        trait_comments.append("守備は合格点")

    if shoot_mid >= 72:
        trait_comments.append("外角に魅力")
    elif shoot_mid >= 67:
        trait_comments.append("得点感覚あり")

    if playmaking_mid >= 72:
        trait_comments.append("ゲームメイク期待")
    elif playmaking_mid >= 67 and archetype in ("playmaker", "floor_general", "scoring_guard"):
        trait_comments.append("展開力がある")

    if inside_mid >= 72:
        trait_comments.append("インサイド戦力")
    elif inside_mid >= 67 and getattr(player, "position", "") in ("PF", "C"):
        trait_comments.append("中で戦える")

    if basketball_iq >= 74:
        context_comments.append("判断力が高い")
    elif basketball_iq <= 42:
        context_comments.append("判断力に粗さ")

    if work_ethic >= 72:
        context_comments.append("練習熱心")
    elif work_ethic <= 40:
        context_comments.append("成長に不安")

    if competitiveness >= 72:
        context_comments.append("勝負強さあり")
    elif competitiveness <= 40:
        context_comments.append("メンタルに波")

    coach_style = getattr(team, "coach_style", "balanced")
    if coach_style == "development" and potential in ("S", "A", "B") and age <= 21:
        context_comments.append("育成方針と好相性")
    elif coach_style == "defense" and defense_mid >= 68:
        context_comments.append("守備型HCと合う")
    elif coach_style == "offense" and shoot_mid >= 68:
        context_comments.append("攻撃型HCと合う")

    if archetype in ("playmaker", "floor_general"):
        context_comments.append("司令塔候補")
    elif archetype in ("two_way_wing",):
        context_comments.append("両面型ウイング")
    elif archetype in ("stretch_big",):
        context_comments.append("ストレッチ要素あり")
    elif archetype in ("rim_protector",):
        context_comments.append("リム守備が持ち味")

    for comment in profile_comments + trait_comments + context_comments:
        if comment not in comments:
            comments.append(comment)
        if len(comments) >= 3:
            break

    if not comments:
        if athletic_mid >= 82:
            comments.append("運動能力に魅力")
        elif ovr_mid >= 66:
            comments.append("完成度はまずまず")
        elif age <= 20:
            comments.append("素材の見極めが必要")
        else:
            comments.append("役割を絞れば使える候補")

    return " / ".join(comments[:3])



def _print_user_draft_candidates(team: Team, pick_num: int, candidates: List[Player]):
    print(f"\n=== USER DRAFT PICK {pick_num} | {team.name} ===")
    print("指名候補を選んでください。")
    print("今は安全版として『上位候補から手動指名』のみ実装しています。")
    print("Combine Buzzは上位注目株、ここは自チームのScout Reportです。\n")

    for i, p in enumerate(candidates, 1):
        label = _get_player_label(p)
        scout_ovr = _get_report_value(team, p, "scout_ovr_range", str(getattr(p, "ovr", 0)))
        scout_potential = _get_report_value(team, p, "scout_potential", str(getattr(p, "potential", "C")))
        shoot_range = _get_report_value(team, p, "shoot_range", "?")
        defense_range = _get_report_value(team, p, "defense_range", "?")
        athletic_range = _get_report_value(team, p, "athletic_range", "?")
        scout_grade = _get_report_value(team, p, "scout_grade", "C")

        print(
            f"{i:>2}. {p.name:<15} {p.position:<2} Age:{getattr(p, 'age', 0):<2} {label}"
        )
        print(
            f"    Scout OVR : {scout_ovr} | Grade:{scout_grade} | Potential:{scout_potential}"
        )
        print(
            f"    Shoot     : {shoot_range} | Defense:{defense_range} | Athletic:{athletic_range}"
        )
        print(f"    Comment   : {_build_scout_comment(team, p)}")



def _choose_user_draft_player(team: Team, pick_num: int, draft_pool: List[Player]) -> Player:
    visible_candidates = _get_user_visible_candidates(team, draft_pool)

    _print_user_draft_candidates(team, pick_num, visible_candidates)

    while True:
        raw = input("指名する選手の番号: ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(visible_candidates):
                return visible_candidates[idx]
        except ValueError:
            pass
        print("正しい番号を入力してください。")



def _add_drafted_player_contract(player: Player, pick_num: int):
    if pick_num <= 16:
        player.contract_years_left = 3
    elif pick_num <= 32:
        player.contract_years_left = 2
    else:
        player.contract_years_left = 1

    if pick_num <= 8:
        player.salary = 700000
    elif pick_num <= 16:
        player.salary = 600000
    elif pick_num <= 32:
        player.salary = 500000
    else:
        player.salary = 400000

    player.years_pro = 0
    player.league_years = 0



def _finalize_team_addition(team: Team, player: Player, pick_num: int):
    _set_draft_acquisition(player, team, pick_num)
    _record_team_draft_history(team, player, pick_num)
    team.add_player(player)
    _record_player_draft_career(player, team, pick_num)



def _handle_roster_limit_after_draft(team: Team, drafted_player: Player, free_agents: List[Player], pick_num: int) -> bool:
    if len(getattr(team, "players", [])) <= 13:
        return True

    release_player = _find_release_candidate(team)
    if release_player is None or release_player == drafted_player:
        return True

    keep_rookie, rookie_score, release_score, margin = _should_keep_rookie_over_existing(
        rookie=drafted_player,
        release_player=release_player,
        pick_num=pick_num,
    )

    if keep_rookie:
        team.remove_player(release_player)
        release_player.contract_years_left = 0
        if getattr(release_player, "salary", 0) <= 0:
            release_player.salary = max(getattr(release_player, "ovr", 0) * 10000, 300000)
        free_agents.append(release_player)
        print(
            f"[DRAFT-RELEASE] {team.name} released {release_player.name} "
            f"(OVR:{getattr(release_player, 'ovr', 0)}) to make room for {drafted_player.name} | "
            f"rookie_score={rookie_score:.1f} >= release_score={release_score:.1f} + margin({margin:.1f})"
        )
        return True

    team.remove_player(drafted_player)
    drafted_player.contract_years_left = 0
    if getattr(drafted_player, "salary", 0) <= 0:
        drafted_player.salary = max(getattr(drafted_player, "ovr", 0) * 10000, 300000)
    free_agents.append(drafted_player)
    print(
        f"[DRAFT-KEEP] {team.name} kept current roster and sent {drafted_player.name} "
        f"(OVR:{getattr(drafted_player, 'ovr', 0)}) to FA | "
        f"rookie_score={rookie_score:.1f} < release_score={release_score:.1f} + margin({margin:.1f})"
    )
    return False



def conduct_draft(teams: List[Team], draft_pool: List[Player], free_agents: List[Player] = None):
    print("Conducting Draft...")

    if not draft_pool:
        print("Draft pool is empty.")
        return

    if free_agents is None:
        free_agents = []

    _print_draft_buzz(draft_pool)

    draft_order = sorted(
        teams,
        key=lambda t: getattr(t, "last_season_wins", getattr(t, "regular_wins", 15)),
    )

    for pick_num, team in enumerate(draft_order, 1):
        if not draft_pool:
            break

        if getattr(team, "is_user_team", False):
            selected_player = _choose_user_draft_player(team, pick_num, draft_pool)
        else:
            selected_player = max(
                draft_pool,
                key=lambda p: (_get_team_draft_score(team, p), getattr(p, "ovr", 0)),
            )

        draft_pool.remove(selected_player)
        _add_drafted_player_contract(selected_player, pick_num)
        _finalize_team_addition(team, selected_player, pick_num)

        kept_on_final_roster = _handle_roster_limit_after_draft(
            team=team,
            drafted_player=selected_player,
            free_agents=free_agents,
            pick_num=pick_num,
        )

        label = _get_player_label(selected_player)
        prefix = "[DRAFT-USER]" if getattr(team, "is_user_team", False) else "[DRAFT-CPU]"

        if kept_on_final_roster:
            print(
                f"{prefix} Pick {pick_num}: {team.name} selected {selected_player.name} "
                f"(OVR:{selected_player.ovr}) | {label} | "
                f"Salary: ${selected_player.salary:,} | Years: {selected_player.contract_years_left}"
            )
        else:
            print(
                f"[DRAFT-SKIP] Pick {pick_num}: {team.name} selected {selected_player.name} "
                f"but did not keep him on the final roster."
            )

    for p in draft_pool:
        p.contract_years_left = 0
        if getattr(p, "salary", 0) <= 0:
            p.salary = max(getattr(p, "ovr", 0) * 10000, 300000)
        free_agents.append(p)

    draft_pool.clear()
