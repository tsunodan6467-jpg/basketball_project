from collections import Counter
import random
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from basketball_sim.config.game_constants import (
    LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    LEAGUE_ROSTER_FOREIGN_CAP,
    PAYLOAD_SCHEMA_VERSION,
)
from basketball_sim.models.season import Season
from basketball_sim.models.offseason import Offseason
from basketball_sim.systems.generator import (
    generate_teams,
    generate_fictional_player_pool,
    generate_single_player,
    sync_player_id_counter_from_world,
)
from basketball_sim.systems.helpers import print_separator
from basketball_sim.systems.trade_logic import TradeSystem
from basketball_sim.systems.contract_logic import (
    SALARY_CAP_DEFAULT,
    SALARY_SOFT_LIMIT_MULTIPLIER,
    get_team_payroll,
)

try:
    from basketball_sim.systems.main_menu_view import launch_main_menu
except Exception as exc:
    import logging

    logging.getLogger("basketball_sim.bootstrap").warning(
        "main_menu_view を読み込めませんでした（主画面UIは使えずCLIにフォールバック）: %s",
        exc,
    )
    launch_main_menu = None

from basketball_sim.persistence.save_load import (
    default_save_path,
    find_user_team,
    load_world,
    save_world,
    validate_payload,
)
from basketball_sim.integrations.steamworks_bridge import enforce_steam_license, try_init_steam
from basketball_sim.utils.game_logging import setup_application_logging
from basketball_sim.utils.sim_rng import get_last_simulation_seed, init_simulation_random
from basketball_sim.utils.user_settings import apply_settings_to_environment, ensure_settings_file_exists


CITY_MARKET_SIZE = {
    "札幌": 1.10, "仙台": 1.05, "秋田": 0.95, "宇都宮": 1.00, "前橋": 0.95,
    "東京": 1.20, "川崎": 1.15, "横浜": 1.15, "千葉": 1.10, "さいたま": 1.10,
    "新潟": 1.00, "富山": 0.95, "金沢": 0.95, "福井": 0.95, "長野": 0.95,
    "静岡": 1.00, "浜松": 1.00, "名古屋": 1.15, "豊田": 1.00, "岐阜": 0.95,
    "京都": 1.10, "大阪": 1.20, "神戸": 1.10, "奈良": 0.95, "和歌山": 0.95,
    "岡山": 1.00, "広島": 1.05, "山口": 0.95, "高松": 0.95, "松山": 0.95,
    "福岡": 1.10, "北九州": 1.00, "熊本": 0.95, "長崎": 0.95, "鹿児島": 0.95, "沖縄": 0.95,
}

ICON_PLAYER_CANDIDATES = [
    {"name": "戸叶優斗", "position": "PG", "ovr": 90, "nationality": "Japan"},
    {"name": "比川島誠", "position": "SG", "ovr": 88, "nationality": "Japan"},
    {"name": "河原勇星", "position": "PG", "ovr": 87, "nationality": "Japan"},
    {"name": "渡瀬雄真", "position": "SF", "ovr": 92, "nationality": "Japan"},
    {"name": "西崎大河", "position": "PF", "ovr": 86, "nationality": "Japan"},
    {"name": "佐倉ジェイ", "position": "C", "ovr": 89, "nationality": "Naturalized"},
    {"name": "真鍋亮", "position": "SG", "ovr": 85, "nationality": "Japan"},
    {"name": "黒田悠生", "position": "SF", "ovr": 84, "nationality": "Japan"},
]

ROSTER_TEMPLATE = {
    "PG": 2,
    "SG": 3,
    "SF": 3,
    "PF": 3,
    "C": 2,
}

STRATEGY_OPTIONS = [
    ("balanced", "バランス"),
    ("run_and_gun", "ラン＆ガン"),
    ("three_point", "スリーポイント偏重"),
    ("defense", "守備重視"),
    ("inside", "インサイド"),
]

COACH_STYLE_OPTIONS = [
    ("balanced", "バランス"),
    ("offense", "攻撃重視"),
    ("defense", "守備重視"),
    ("development", "育成"),
]


USAGE_POLICY_OPTIONS = [
    ("balanced", "バランス"),
    ("win_now", "勝利優先（今を勝つ）"),
    ("development", "育成・若手優先"),
]


def create_user_team_info():
    print_separator("クラブ作成")

    team_name = input("チーム名を入力してください: ").strip()

    print("\n拠点地を選んでください\n")
    cities = list(CITY_MARKET_SIZE.keys())

    for i, city in enumerate(cities, 1):
        print(f"{i}. {city}")

    while True:
        try:
            choice = int(input("\n番号を入力してください: "))
            if 1 <= choice <= len(cities):
                home_city = cities[choice - 1]
                break
        except ValueError:
            pass
        print("正しい番号を入力してください。")

    market_size = CITY_MARKET_SIZE[home_city]

    print_separator("クラブ情報")
    print(f"チーム名: {team_name}")
    print(f"拠点地: {home_city}")
    print(f"市場規模: {market_size}")

    return team_name, home_city, market_size


def apply_user_team_to_league(teams, team_name, home_city, market_size):
    target_team = None

    for team in teams:
        if getattr(team, "league_level", 0) == 3:
            target_team = team
            break

    if target_team is None:
        raise ValueError("D3チームが見つかりませんでした。")

    old_name = target_team.name

    target_team.name = team_name
    target_team.home_city = home_city
    target_team.market_size = market_size
    target_team.is_user_team = True
    target_team.popularity = 45
    target_team.money = 5000000

    print_separator("プレイヤーチーム登録")
    print(f"{old_name} → {target_team.name} に置き換えました")

    return target_team


def choose_icon_player():
    return choose_icon_player_from_league(None)


def _build_icon_candidate_rows(teams):
    rows = []
    if not teams:
        for row in ICON_PLAYER_CANDIDATES:
            rows.append(
                {
                    "player": None,
                    "team": None,
                    "name": row["name"],
                    "position": row["position"],
                    "ovr": int(row["ovr"]),
                    "nationality": row["nationality"],
                    "team_name": "固定候補",
                    "seed_data": row,
                }
            )
        return rows

    for team in teams:
        for player in getattr(team, "players", []):
            rows.append(
                {
                    "player": player,
                    "team": team,
                    "name": getattr(player, "name", "Unknown"),
                    "position": getattr(player, "position", "SF"),
                    "ovr": int(getattr(player, "ovr", 0)),
                    "nationality": getattr(player, "nationality", "Japan"),
                    "team_name": getattr(team, "name", "Unknown Team"),
                    "seed_data": None,
                }
            )
    return rows


def choose_icon_player_from_league(teams):
    print_separator("アイコンプレイヤー選択")

    all_rows = _build_icon_candidate_rows(teams)
    if not all_rows:
        raise ValueError("アイコン候補が見つかりません。")

    while True:
        keyword = input("\n選手名/チーム名で検索（空欄で上位表示）: ").strip().lower()
        filtered = []
        for row in all_rows:
            token = f"{row['name']} {row['team_name']} {row['position']} {row['nationality']}".lower()
            if not keyword or keyword in token:
                filtered.append(row)

        if not filtered:
            print("候補が見つかりません。検索語を変えてください。")
            continue

        filtered.sort(
            key=lambda r: (r["ovr"], r["position"], r["name"]),
            reverse=True,
        )
        display = filtered[:40]
        print("\n候補一覧（最大40件）")
        for i, row in enumerate(display, 1):
            print(
                f"{i}. {row['name']} {row['position']} OVR:{row['ovr']} "
                f"{row['nationality']} | {row['team_name']}"
            )
        print("r: 検索し直す")

        raw = input("番号: ").strip().lower()
        if raw == "r":
            continue
        try:
            idx = int(raw) - 1
        except ValueError:
            print("正しい番号を入力してください。")
            continue
        if not (0 <= idx < len(display)):
            print("正しい番号を入力してください。")
            continue
        icon = display[idx]
        break

    print_separator("選択されたアイコン")
    print(icon["name"], icon["position"], icon["ovr"], icon["nationality"], "|", icon["team_name"])

    return icon


def create_icon_player(icon_data):
    source_player = icon_data.get("player") if isinstance(icon_data, dict) else None
    if source_player is not None:
        player = source_player
    else:
        seed = icon_data.get("seed_data", icon_data) if isinstance(icon_data, dict) else icon_data
        player = generate_single_player(
            age_override=27,
            base_ovr_override=seed["ovr"],
            position_override=seed["position"],
            nationality_override=seed["nationality"],
        )
        player.name = seed["name"]
        player.age = 27
        player.nationality = seed["nationality"]
        player.position = seed["position"]
        player.ovr = seed["ovr"]

    player.salary = 0
    player.contract_years_left = 99
    player.years_pro = max(5, int(getattr(player, "years_pro", 0)))
    player.is_icon = True
    player.icon_locked = True
    player.is_retired = False

    return player


def choose_roster_build_mode():
    print_separator("ロスター作成モード")
    print("1. 手動で選ぶ")
    print("2. 自動で編成する（テスト向け）")

    while True:
        choice = input("番号: ").strip()
        if choice == "1":
            return "manual"
        if choice == "2":
            return "auto"
        print("正しい番号を入力してください。")


def choose_icon_player_auto():
    return choose_icon_player_auto_from_league(None)


def choose_icon_player_auto_from_league(teams):
    candidate_pool = _build_icon_candidate_rows(teams)
    if not candidate_pool:
        raise ValueError("アイコン候補が存在しません。")
    icon = max(candidate_pool, key=lambda p: (p["ovr"], p["position"], p["name"]))

    print_separator("アイコンプレイヤー自動選択")
    print(
        f"{icon['name']} {icon['position']} OVR:{icon['ovr']} "
        f"{icon['nationality']} | {icon.get('team_name', '固定候補')}"
    )

    return icon


def get_nationality_bucket(player):
    nat = getattr(player, "nationality", "Japan")
    if nat == "Foreign":
        return "Foreign"
    if nat in ("Asia", "Naturalized"):
        return "AsiaNat"
    return "Japan"


def get_auto_roster_sort_key(player, counts, required_position=None):
    nat_bucket = get_nationality_bucket(player)
    nationality_penalty = 0

    if nat_bucket == "Foreign":
        nationality_penalty = 6 + counts["Foreign"] * 4
    elif nat_bucket == "AsiaNat":
        nationality_penalty = 5 + counts["AsiaNat"] * 8

    position_bonus = 0
    if required_position and getattr(player, "position", "") == required_position:
        position_bonus = 3

    age_bonus = max(0, 32 - getattr(player, "age", 25)) * 0.05

    return (
        getattr(player, "ovr", 0) + position_bonus + age_bonus - nationality_penalty,
        getattr(player, "ovr", 0),
        -getattr(player, "age", 25),
        getattr(player, "name", ""),
    )


def choose_best_auto_candidate(candidates, counts, required_position=None):
    legal_players = [p for p in candidates if nationality_check(p, counts)]
    if not legal_players:
        return None
    return max(
        legal_players,
        key=lambda p: get_auto_roster_sort_key(p, counts, required_position=required_position),
    )


def print_roster_rule_summary(players):
    counts = {"Foreign": 0, "AsiaNat": 0}
    pos_counter = Counter(getattr(p, "position", "Unknown") for p in players)

    for p in players:
        update_counts(p, counts)

    print("\n[ロスター内訳]")
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        print(f"{pos}: {pos_counter.get(pos, 0)}")
    print(f"Foreign: {counts['Foreign']}/{LEAGUE_ROSTER_FOREIGN_CAP}")
    print(f"Asia/Naturalized: {counts['AsiaNat']}/{LEAGUE_ROSTER_ASIA_NATURALIZED_CAP}")


def auto_draft_players(pool, user_team, icon_player):
    print_separator("ロスター自動編成")

    user_team.players = []
    user_team.add_player(icon_player)

    counts = {"Foreign": 0, "AsiaNat": 0}
    update_counts(icon_player, counts)

    working_pool = list(pool)
    selected = []

    remaining_needs = dict(ROSTER_TEMPLATE)
    icon_position = getattr(icon_player, "position", "")
    if remaining_needs.get(icon_position, 0) > 0:
        remaining_needs[icon_position] -= 1

    for pos in ["PG", "SG", "SF", "PF", "C"]:
        while remaining_needs.get(pos, 0) > 0:
            position_candidates = [p for p in working_pool if getattr(p, "position", "") == pos]
            chosen = choose_best_auto_candidate(position_candidates, counts, required_position=pos)

            if chosen is None:
                fallback_pool = [
                    p for p in working_pool
                    if nationality_check(p, counts)
                ]
                chosen = choose_best_auto_candidate(fallback_pool, counts)

            if chosen is None:
                raise ValueError(f"自動編成に失敗しました。{pos} の候補が不足しています。")

            selected.append(chosen)
            user_team.add_player(chosen)
            update_counts(chosen, counts)
            working_pool.remove(chosen)
            remaining_needs[pos] -= 1

    while len(selected) < 12:
        chosen = choose_best_auto_candidate(working_pool, counts)
        if chosen is None:
            raise ValueError("自動編成に失敗しました。国籍ルールを満たす候補が不足しています。")

        selected.append(chosen)
        user_team.add_player(chosen)
        update_counts(chosen, counts)
        working_pool.remove(chosen)

    for p in selected:
        if p in pool:
            pool.remove(p)

    print("自動編成が完了しました。")
    print_roster_rule_summary(user_team.players)

    return selected


def nationality_check(player, counts):
    nat = getattr(player, "nationality", "Japan")

    if nat == "Foreign" and counts["Foreign"] >= 3:
        return False

    if nat in ("Asia", "Naturalized") and counts["AsiaNat"] >= LEAGUE_ROSTER_ASIA_NATURALIZED_CAP:
        return False

    return True


def update_counts(player, counts):
    nat = getattr(player, "nationality", "Japan")

    if nat == "Foreign":
        counts["Foreign"] += 1

    if nat in ("Asia", "Naturalized"):
        counts["AsiaNat"] += 1


def draft_players(pool, user_team, icon_player):
    print_separator("ロスター選択")

    user_team.players = []
    user_team.add_player(icon_player)

    counts = {"Foreign": 0, "AsiaNat": 0}
    update_counts(icon_player, counts)

    pos_groups = {}
    for p in pool:
        pos_groups.setdefault(p.position, []).append(p)

    selected = []

    while len(selected) < 12:
        print(f"\n現在 {len(selected)}/12人")
        print(
            f"国籍枠: Foreign {counts['Foreign']}/{LEAGUE_ROSTER_FOREIGN_CAP} | "
            f"Asia/Naturalized {counts['AsiaNat']}/{LEAGUE_ROSTER_ASIA_NATURALIZED_CAP}"
        )

        print("\nポジション選択")
        print("1. PG")
        print("2. SG")
        print("3. SF")
        print("4. PF")
        print("5. C")

        while True:
            try:
                pos_choice = int(input("番号: "))
                if pos_choice in [1, 2, 3, 4, 5]:
                    break
            except ValueError:
                pass
            print("正しい番号を入力してください。")

        pos_map = {1: "PG", 2: "SG", 3: "SF", 4: "PF", 5: "C"}
        pos = pos_map[pos_choice]

        players = sorted(pos_groups[pos], key=lambda p: p.ovr, reverse=True)[:15]

        print(f"\n[{pos} 候補]")
        for i, p in enumerate(players, 1):
            print(
                f"{i}. {p.name:<15} "
                f"OVR:{p.ovr} "
                f"Age:{p.age} "
                f"{p.nationality}"
            )

        while True:
            try:
                pick = int(input("選択: "))
                if 1 <= pick <= len(players):
                    break
            except ValueError:
                pass
            print("正しい番号を入力してください。")

        player = players[pick - 1]

        if not nationality_check(player, counts):
            print("外国籍ルール違反のため獲得できません。")
            continue

        selected.append(player)
        update_counts(player, counts)
        user_team.add_player(player)

        pool.remove(player)
        pos_groups[pos].remove(player)

        print(f"獲得: {player.name}")

    return selected


def create_fictional_player_pool():
    pool = generate_fictional_player_pool(180)

    print_separator("架空選手プール生成")
    print("人数:", len(pool))

    position_counts = Counter(p.position for p in pool)

    print("\n[ポジション内訳]")
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        print(f"{pos}: {position_counts.get(pos, 0)}")

    return pool


def get_fictional_cpu_teams(teams, user_team):
    d3_teams = [t for t in teams if getattr(t, "league_level", 0) == 3 and t != user_team]
    return d3_teams[:7]


def clear_team_rosters(target_teams):
    for team in target_teams:
        team.players = []


def build_position_buckets(players):
    buckets = {"PG": [], "SG": [], "SF": [], "PF": [], "C": []}
    for p in players:
        buckets[p.position].append(p)

    for pos in buckets:
        buckets[pos] = sorted(buckets[pos], key=lambda x: x.ovr, reverse=True)

    return buckets


def build_japan_rule_counts(players):
    counts = {"Foreign": 0, "AsiaNat": 0}
    for player in players:
        update_counts(player, counts)
    return counts


def get_cpu_roster_sort_key(player, counts, stronger=False, required_position=None):
    nat_bucket = get_nationality_bucket(player)
    nationality_penalty = 0

    if nat_bucket == "Foreign":
        nationality_penalty = 5 + counts["Foreign"] * 4
    elif nat_bucket == "AsiaNat":
        nationality_penalty = 7 + counts["AsiaNat"] * 8

    position_bonus = 0
    if required_position and getattr(player, "position", "") == required_position:
        position_bonus = 3

    age = getattr(player, "age", 25)
    age_bonus = max(0, 31 - age) * 0.04 if stronger else max(0, 29 - age) * 0.03

    return (
        getattr(player, "ovr", 0) + position_bonus + age_bonus - nationality_penalty,
        getattr(player, "ovr", 0),
        -age,
        getattr(player, "name", ""),
    )


def choose_cpu_roster_candidate(candidates, counts, stronger=False, required_position=None):
    legal_players = [p for p in candidates if nationality_check(p, counts)]
    if not legal_players:
        return None

    if stronger:
        return max(
            legal_players,
            key=lambda p: get_cpu_roster_sort_key(
                p,
                counts,
                stronger=True,
                required_position=required_position,
            ),
        )

    sampled = list(legal_players)
    random.shuffle(sampled)
    sampled = sorted(
        sampled[:max(len(sampled) // 2, min(12, len(sampled)), 1)],
        key=lambda p: get_cpu_roster_sort_key(
            p,
            counts,
            stronger=False,
            required_position=required_position,
        ),
        reverse=True,
    )
    return sampled[0] if sampled else None


def summarize_roster_nationality_counts(players):
    counts = build_japan_rule_counts(players)
    return (
        f"Foreign:{counts['Foreign']}/{LEAGUE_ROSTER_FOREIGN_CAP} | "
        f"Asia/Naturalized:{counts['AsiaNat']}/{LEAGUE_ROSTER_ASIA_NATURALIZED_CAP}"
    )


def ensure_cpu_pool_viability(pool, team_count):
    target_total_by_position = {pos: need * team_count for pos, need in ROSTER_TEMPLATE.items()}
    current_position_counts = Counter(getattr(p, "position", "") for p in pool)

    added_players = []

    for pos in ["PG", "SG", "SF", "PF", "C"]:
        shortage = max(0, target_total_by_position.get(pos, 0) - current_position_counts.get(pos, 0))
        for _ in range(shortage):
            player = generate_single_player(position_override=pos, nationality_override="Japan")
            pool.append(player)
            added_players.append(player)
            current_position_counts[pos] = current_position_counts.get(pos, 0) + 1

    domestic_target = 9 * team_count
    domestic_count = sum(1 for p in pool if get_nationality_bucket(p) == "Japan")
    domestic_shortage = max(0, domestic_target - domestic_count)

    if domestic_shortage > 0:
        position_deficits = {
            pos: max(0, target_total_by_position.get(pos, 0) - sum(1 for p in pool if getattr(p, "position", "") == pos and get_nationality_bucket(p) == "Japan"))
            for pos in ["PG", "SG", "SF", "PF", "C"]
        }

        ordered_positions = sorted(
            ["PG", "SG", "SF", "PF", "C"],
            key=lambda pos: (position_deficits.get(pos, 0), target_total_by_position.get(pos, 0)),
            reverse=True,
        )

        for i in range(domestic_shortage):
            pos = ordered_positions[i % len(ordered_positions)]
            if position_deficits.get(pos, 0) <= 0:
                pos = min(
                    ["PG", "SG", "SF", "PF", "C"],
                    key=lambda p: current_position_counts.get(p, 0) / max(1, target_total_by_position.get(p, 1))
                )
            player = generate_single_player(position_override=pos, nationality_override="Japan")
            pool.append(player)
            added_players.append(player)
            current_position_counts[pos] = current_position_counts.get(pos, 0) + 1
            position_deficits[pos] = max(0, position_deficits.get(pos, 0) - 1)

    return added_players


def pick_balanced_roster_from_pool(pool, stronger=False):
    working_pool = list(pool)
    selected = []
    counts = {"Foreign": 0, "AsiaNat": 0}

    for pos, need in ROSTER_TEMPLATE.items():
        for _ in range(need):
            position_candidates = [
                p for p in working_pool
                if getattr(p, "position", "") == pos
            ]
            chosen = choose_cpu_roster_candidate(
                position_candidates,
                counts,
                stronger=stronger,
                required_position=pos,
            )

            if chosen is None:
                fallback_pool = [p for p in working_pool if nationality_check(p, counts)]
                chosen = choose_cpu_roster_candidate(
                    fallback_pool,
                    counts,
                    stronger=stronger,
                )

            if chosen is None:
                raise ValueError(
                    f"CPU架空チームの初期配分に失敗しました。{pos} を満たす合法候補が不足しています。"
                )

            selected.append(chosen)
            update_counts(chosen, counts)
            working_pool.remove(chosen)

    while len(selected) < 13:
        chosen = choose_cpu_roster_candidate(working_pool, counts, stronger=stronger)
        if chosen is None:
            raise ValueError("CPU架空チームの初期配分に失敗しました。国籍ルールを満たす候補が不足しています。")

        selected.append(chosen)
        update_counts(chosen, counts)
        working_pool.remove(chosen)

    return selected

def assign_fictional_teams_and_rival(teams, user_team, remaining_players, free_agents):
    cpu_fictional_teams = get_fictional_cpu_teams(teams, user_team)

    if len(cpu_fictional_teams) < 7:
        raise ValueError("架空CPUチームに使うD3チームが7つ確保できません。")

    rival_team = cpu_fictional_teams[0]
    rival_team.name = "埼京ライバルズ"
    rival_team.home_city = "さいたま"
    rival_team.market_size = 1.10
    rival_team.popularity = 52
    rival_team.money = 6500000
    rival_team.is_rival_team = True
    rival_team.coach_style = "development"

    clear_team_rosters(cpu_fictional_teams)

    pool = list(remaining_players)

    added_players = ensure_cpu_pool_viability(pool, len(cpu_fictional_teams))

    rival_roster = pick_balanced_roster_from_pool(pool, stronger=True)
    for p in rival_roster:
        rival_team.add_player(p)
        pool.remove(p)

    for team in cpu_fictional_teams[1:]:
        roster = pick_balanced_roster_from_pool(pool, stronger=False)
        for p in roster:
            team.add_player(p)
            pool.remove(p)

    for p in pool:
        free_agents.append(p)

    print_separator("架空チーム自動配分")
    print(f"ライバルチーム: {rival_team.name}")
    print(f"残りFA: {len(pool)}人")
    print(f"追加生成: {len(added_players)}人")

    print("\n[ライバルロスター上位5人]")
    rival_sorted = sorted(rival_team.players, key=lambda x: x.ovr, reverse=True)
    for i, p in enumerate(rival_sorted[:5], 1):
        print(f"{i}. {p.name:<15} {p.position} OVR:{p.ovr}")

    print("\n[架空CPUチーム国籍内訳]")
    for team in cpu_fictional_teams:
        summary = summarize_roster_nationality_counts(getattr(team, "players", []))
        print(f"{team.name:<18} {summary}")

    return rival_team


def print_user_roster(user_team):
    print_separator("ロスター完成")

    sorted_players = sorted(user_team.players, key=lambda p: (p.position, -p.ovr))

    for p in sorted_players:
        icon_mark = "★" if getattr(p, "is_icon", False) else " "
        print(
            f"{icon_mark} {p.name:<15} "
            f"{p.position} "
            f"OVR:{p.ovr} "
            f"{p.nationality}"
        )


def print_player_career_tracking(user_team, tracked_player_name=None):
    print_separator("キャリア追跡ログ")

    tracked_players = []

    if tracked_player_name:
        for p in user_team.players:
            if p.name == tracked_player_name:
                tracked_players.append(p)
                break

    if not tracked_players:
        tracked_players = sorted(
            user_team.players,
            key=lambda p: (
                getattr(p, "career_points", 0),
                getattr(p, "career_games_played", 0),
                getattr(p, "peak_ovr", getattr(p, "ovr", 0)),
            ),
            reverse=True
        )[:5]

    for p in tracked_players:
        hof_score = 0.0
        if hasattr(p, "calculate_hall_of_fame_score"):
            hof_score = p.calculate_hall_of_fame_score()
        else:
            hof_score = getattr(p, "hall_of_fame_score", 0.0)

        print(
            f"{p.name:<15} | Age:{p.age:<2} | OVR:{p.ovr:<2} | "
            f"Peak:{getattr(p, 'peak_ovr', p.ovr):<2} | "
            f"Career PTS:{getattr(p, 'career_points', 0):<5} | "
            f"Career GP:{getattr(p, 'career_games_played', 0):<4} | "
            f"HOF Score:{hof_score:.2f}"
        )


def print_user_team_history(user_team):
    if hasattr(user_team, "print_history"):
        print_separator("クラブ史確認")
        user_team.print_history()


def print_team_identity(user_team):
    print_separator("GMチーム情報")
    print(f"クラブ名      : {user_team.name}")
    print(f"拠点地        : {getattr(user_team, 'home_city', 'Unknown')}")
    print(f"市場規模      : {getattr(user_team, 'market_size', 1.0):.2f}")
    print(f"人気          : {getattr(user_team, 'popularity', 0)}")
    print(f"資金          : ${getattr(user_team, 'money', 0):,}")
    print(f"戦術          : {getattr(user_team, 'strategy', 'balanced')}")
    print(f"HCスタイル    : {getattr(user_team, 'coach_style', 'balanced')}")
    usage_label = getattr(user_team, "get_usage_policy_label", lambda: getattr(user_team, "usage_policy", "balanced"))()
    print(f"起用方針      : {usage_label}")


def print_salary_cap_status(user_team):
    print_separator("Salary Cap Status")

    payroll = int(get_team_payroll(user_team))
    hard_cap = int(SALARY_CAP_DEFAULT)
    soft_cap = int(SALARY_CAP_DEFAULT * SALARY_SOFT_LIMIT_MULTIPLIER)

    if payroll > soft_cap:
        status = "OVER SOFT CAP"
    elif payroll > hard_cap:
        status = "OVER CAP"
    else:
        status = "UNDER CAP"

    cap_space = hard_cap - payroll
    soft_room = soft_cap - payroll

    print(f"Team Payroll : ${payroll:,}")
    print(f"Hard Cap     : ${hard_cap:,}")
    print(f"Soft Cap     : ${soft_cap:,}")
    print()
    print(f"Status       : {status}")

    if cap_space >= 0:
        print(f"Cap Space    : ${cap_space:,}")
    else:
        print(f"Cap Over     : ${abs(cap_space):,}")

    if soft_room >= 0:
        print(f"Soft Room    : ${soft_room:,}")
    else:
        print(f"Soft Over    : ${abs(soft_room):,}")


def choose_option_from_list(title, items):
    print_separator(title)

    for i, (_, label) in enumerate(items, 1):
        print(f"{i}. {label}")

    while True:
        try:
            choice = int(input("番号: ").strip())
            if 1 <= choice <= len(items):
                return items[choice - 1][0]
        except ValueError:
            pass
        print("正しい番号を入力してください。")


def set_team_strategy(user_team):
    selected = choose_option_from_list("戦術変更", STRATEGY_OPTIONS)
    old_value = getattr(user_team, "strategy", "balanced")
    user_team.strategy = selected

    print_separator("戦術変更完了")
    print(f"{old_value} -> {user_team.strategy}")


def set_team_coach_style(user_team):
    selected = choose_option_from_list("HCスタイル変更", COACH_STYLE_OPTIONS)
    old_value = getattr(user_team, "coach_style", "balanced")
    user_team.coach_style = selected

    print_separator("HCスタイル変更完了")
    print(f"{old_value} -> {user_team.coach_style}")


def set_team_usage_policy(user_team):
    selected = choose_option_from_list("起用方針変更", USAGE_POLICY_OPTIONS)
    old_label = getattr(user_team, "get_usage_policy_label", lambda: getattr(user_team, "usage_policy", "balanced"))()
    if hasattr(user_team, "set_usage_policy"):
        user_team.set_usage_policy(selected)
    else:
        user_team.usage_policy = selected

    new_label = getattr(user_team, "get_usage_policy_label", lambda: getattr(user_team, "usage_policy", "balanced"))()

    print_separator("起用方針変更完了")
    print(f"{old_label} -> {new_label}")


def sort_roster_for_gm_view(players):
    position_order = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
    return sorted(
        players,
        key=lambda p: (
            position_order.get(getattr(p, "position", "SF"), 99),
            -getattr(p, "ovr", 0),
            getattr(p, "name", ""),
        )
    )


def get_current_starting_five(user_team):
    if hasattr(user_team, "get_starting_five"):
        return user_team.get_starting_five()
    roster = sort_roster_for_gm_view(getattr(user_team, "players", []))
    return roster[:5]


def get_starting_player_ids(user_team):
    return {
        getattr(p, "player_id", None)
        for p in get_current_starting_five(user_team)
    }


def get_current_sixth_man(user_team):
    if hasattr(user_team, "get_sixth_man"):
        return user_team.get_sixth_man()
    return None


def get_current_bench_order(user_team):
    if hasattr(user_team, "get_bench_order_players"):
        return user_team.get_bench_order_players()
    starter_ids = {
        getattr(p, "player_id", None)
        for p in get_current_starting_five(user_team)
    }
    roster = sort_roster_for_gm_view(getattr(user_team, "players", []))
    return [
        p for p in roster
        if not p.is_injured() and not p.is_retired and getattr(p, "player_id", None) not in starter_ids
    ]


def print_current_bench_order(user_team):
    print_separator("現在のベンチ序列")
    bench_players = get_current_bench_order(user_team)

    if not bench_players:
        print("ベンチ候補が存在しません。")
        return

    current_sixth = get_current_sixth_man(user_team)
    current_sixth_id = getattr(current_sixth, "player_id", None) if current_sixth is not None else None

    for i, p in enumerate(bench_players, 1):
        role_mark = "6" if getattr(p, "player_id", None) == current_sixth_id else " "
        print(
            f"{i}. {role_mark} {p.name:<15} "
            f"{p.position:<2} "
            f"OVR:{getattr(p, 'ovr', 0):<2} "
            f"Age:{getattr(p, 'age', 0):<2} "
            f"{getattr(p, 'nationality', 'Japan')}"
        )

    print("\n6 = current sixth man")


def print_gm_roster_view(user_team):
    print_separator("GMロスター確認")

    roster = sort_roster_for_gm_view(getattr(user_team, "players", []))
    if not roster:
        print("ロスターが存在しません。")
        return

    starter_ids = get_starting_player_ids(user_team)
    sixth_man = get_current_sixth_man(user_team)
    sixth_man_id = getattr(sixth_man, "player_id", None) if sixth_man is not None else None

    for i, p in enumerate(roster, 1):
        player_id = getattr(p, "player_id", None)

        if player_id in starter_ids:
            role_mark = "★"
        elif player_id == sixth_man_id:
            role_mark = "6"
        else:
            role_mark = " "

        print(
            f"{i:>2}. {role_mark} {p.name:<15} "
            f"{p.position:<2} "
            f"OVR:{getattr(p, 'ovr', 0):<2} "
            f"Age:{getattr(p, 'age', 0):<2} "
            f"{getattr(p, 'nationality', 'Japan'):<12} "
            f"Salary:${getattr(p, 'salary', 0):,}"
        )

    print("\n★ = current starter")
    print("6 = current sixth man")


def print_current_starting_five(user_team):
    print_separator("現在のスタメン")
    starters = get_current_starting_five(user_team)

    if not starters:
        print("スタメン候補が存在しません。")
        return

    for i, p in enumerate(starters, 1):
        print(
            f"{i}. {p.name:<15} "
            f"{p.position:<2} "
            f"OVR:{getattr(p, 'ovr', 0):<2} "
            f"Age:{getattr(p, 'age', 0):<2} "
            f"{getattr(p, 'nationality', 'Japan')}"
        )


def print_current_sixth_man(user_team):
    print_separator("現在の6thマン")
    sixth_man = get_current_sixth_man(user_team)

    if sixth_man is None:
        print("6thマン候補が存在しません。")
        return

    print(
        f"{getattr(sixth_man, 'name', 'Unknown'):<15} "
        f"{getattr(sixth_man, 'position', 'SF'):<2} "
        f"OVR:{getattr(sixth_man, 'ovr', 0):<2} "
        f"Age:{getattr(sixth_man, 'age', 0):<2} "
        f"{getattr(sixth_man, 'nationality', 'Japan')}"
    )


def get_available_starting_candidates(user_team, current_starters, slot_index):
    slot_player = current_starters[slot_index]
    slot_position = getattr(slot_player, "position", "SF")

    candidates = []
    for p in sort_roster_for_gm_view(getattr(user_team, "players", [])):
        if p.is_injured() or p.is_retired:
            continue

        same_position = getattr(p, "position", "SF") == slot_position
        current_ids_except_slot = {
            getattr(sp, "player_id", None)
            for i, sp in enumerate(current_starters)
            if i != slot_index
        }

        if getattr(p, "player_id", None) in current_ids_except_slot:
            continue

        if same_position or p == slot_player:
            candidates.append(p)

    if not candidates:
        for p in sort_roster_for_gm_view(getattr(user_team, "players", [])):
            if p.is_injured() or p.is_retired:
                continue

            current_ids_except_slot = {
                getattr(sp, "player_id", None)
                for i, sp in enumerate(current_starters)
                if i != slot_index
            }

            if getattr(p, "player_id", None) in current_ids_except_slot:
                continue

            candidates.append(p)

    return candidates


def change_starting_lineup(user_team):
    while True:
        current_starters = get_current_starting_five(user_team)
        if len(current_starters) < 5:
            print_separator("スタメン変更")
            print("スタメン候補が5人未満のため変更できません。")
            return

        print_current_starting_five(user_team)
        print("\n変更したい枠を選んでください")
        print("1. PG枠")
        print("2. SG枠")
        print("3. SF枠")
        print("4. PF枠")
        print("5. C枠")
        print("6. 自動スタメンに戻す")
        print("7. 戻る")

        choice = input("番号: ").strip()

        if choice == "7":
            return

        if choice == "6":
            if hasattr(user_team, "clear_starting_lineup"):
                user_team.clear_starting_lineup()
            print_separator("スタメン変更完了")
            print("自動スタメンに戻しました。")
            continue

        if choice not in {"1", "2", "3", "4", "5"}:
            print("正しい番号を入力してください。")
            continue

        slot_index = int(choice) - 1
        candidates = get_available_starting_candidates(user_team, current_starters, slot_index)

        if not candidates:
            print("変更可能な候補がいません。")
            continue

        print_separator("スタメン候補")
        for i, p in enumerate(candidates, 1):
            current_mark = "★" if p == current_starters[slot_index] else " "
            print(
                f"{i}. {current_mark}{p.name:<15} "
                f"{p.position:<2} "
                f"OVR:{getattr(p, 'ovr', 0):<2} "
                f"Age:{getattr(p, 'age', 0):<2} "
                f"{getattr(p, 'nationality', 'Japan')}"
            )

        while True:
            pick = input("選択番号: ").strip()
            try:
                pick_index = int(pick) - 1
                if 0 <= pick_index < len(candidates):
                    break
            except ValueError:
                pass
            print("正しい番号を入力してください。")

        new_player = candidates[pick_index]
        updated_starters = list(current_starters)
        updated_starters[slot_index] = new_player

        if hasattr(user_team, "set_starting_lineup_by_players"):
            user_team.set_starting_lineup_by_players(updated_starters)

        print_separator("スタメン変更完了")
        print(
            f"{getattr(current_starters[slot_index], 'name', 'Unknown')} -> "
            f"{getattr(new_player, 'name', 'Unknown')}"
        )


def get_sixth_man_candidates(user_team):
    starter_ids = get_starting_player_ids(user_team)
    candidates = []

    for p in sort_roster_for_gm_view(getattr(user_team, "players", [])):
        if p.is_injured() or p.is_retired:
            continue
        if getattr(p, "player_id", None) in starter_ids:
            continue
        candidates.append(p)

    return candidates


def change_sixth_man(user_team):
    while True:
        print_current_sixth_man(user_team)

        print("\n1. 6thマンを変更する")
        print("2. 自動6thマンに戻す")
        print("3. 戻る")

        choice = input("番号: ").strip()

        if choice == "3":
            return

        if choice == "2":
            if hasattr(user_team, "clear_sixth_man"):
                user_team.clear_sixth_man()
            print_separator("6thマン変更完了")
            print("自動6thマンに戻しました。")
            continue

        if choice != "1":
            print("正しい番号を入力してください。")
            continue

        candidates = get_sixth_man_candidates(user_team)
        if not candidates:
            print("6thマン候補がいません。")
            continue

        current_sixth_man = get_current_sixth_man(user_team)

        print_separator("6thマン候補")
        for i, p in enumerate(candidates, 1):
            current_mark = "6" if current_sixth_man is not None and getattr(p, "player_id", None) == getattr(current_sixth_man, "player_id", None) else " "
            print(
                f"{i}. {current_mark} {p.name:<15} "
                f"{p.position:<2} "
                f"OVR:{getattr(p, 'ovr', 0):<2} "
                f"Age:{getattr(p, 'age', 0):<2} "
                f"{getattr(p, 'nationality', 'Japan')}"
            )

        print("\n6 = current sixth man")

        while True:
            pick = input("選択番号: ").strip()
            try:
                pick_index = int(pick) - 1
                if 0 <= pick_index < len(candidates):
                    break
            except ValueError:
                pass
            print("正しい番号を入力してください。")

        new_player = candidates[pick_index]

        if hasattr(user_team, "set_sixth_man"):
            user_team.set_sixth_man(new_player)

        print_separator("6thマン変更完了")
        print(f"{getattr(new_player, 'name', 'Unknown')} を 6thマンに設定しました。")


def change_bench_order(user_team):
    while True:
        bench_players = get_current_bench_order(user_team)
        print_current_bench_order(user_team)

        print("\n1. 順位を入れ替える")
        print("2. 自動ベンチ序列に戻す")
        print("3. 戻る")

        choice = input("番号: ").strip()

        if choice == "3":
            return

        if choice == "2":
            if hasattr(user_team, "clear_bench_order"):
                user_team.clear_bench_order()
            print_separator("ベンチ序列変更完了")
            print("自動ベンチ序列に戻しました。")
            continue

        if choice != "1":
            print("正しい番号を入力してください。")
            continue

        if len(bench_players) < 2:
            print("入れ替え可能なベンチ候補が不足しています。")
            continue

        try:
            first = int(input("入れ替え元の番号: ").strip())
            second = int(input("入れ替え先の番号: ").strip())
        except ValueError:
            print("正しい番号を入力してください。")
            continue

        if not (1 <= first <= len(bench_players) and 1 <= second <= len(bench_players)):
            print("正しい番号を入力してください。")
            continue

        if first == second:
            print("同じ番号は入れ替えできません。")
            continue

        updated = bench_players[:]
        updated[first - 1], updated[second - 1] = updated[second - 1], updated[first - 1]

        if hasattr(user_team, "set_bench_order_by_players"):
            user_team.set_bench_order_by_players(updated)

        print_separator("ベンチ序列変更完了")
        print(
            f"{getattr(bench_players[first - 1], 'name', 'Unknown')} と "
            f"{getattr(bench_players[second - 1], 'name', 'Unknown')} を入れ替えました。"
        )



def get_trade_candidate_teams(all_teams, user_team):
    return [
        team for team in all_teams
        if team != user_team and getattr(team, "league_level", 0) == getattr(user_team, "league_level", 0)
    ]


def print_trade_team_list(all_teams, user_team):
    print_separator("トレード相手チーム一覧")
    teams = get_trade_candidate_teams(all_teams, user_team)

    if not teams:
        print("同リーグ内にトレード候補チームがありません。")
        return []

    for i, team in enumerate(teams, 1):
        print(
            f"{i}. {team.name:<20} "
            f"D{getattr(team, 'league_level', 0)} "
            f"W:{getattr(team, 'regular_wins', 0):<2} "
            f"L:{getattr(team, 'regular_losses', 0):<2}"
        )

    return teams


def get_tradeable_players(team):
    players = []
    for p in sort_roster_for_gm_view(getattr(team, "players", [])):
        if p.is_injured() or p.is_retired:
            continue
        if getattr(p, "icon_locked", False):
            continue
        players.append(p)
    return players


def print_tradeable_players(team, title):
    print_separator(title)
    players = get_tradeable_players(team)

    if not players:
        print("対象選手がいません。")
        return []

    for i, p in enumerate(players, 1):
        print(
            f"{i}. {p.name:<15} "
            f"{getattr(p, 'position', 'SF'):<2} "
            f"OVR:{getattr(p, 'ovr', 0):<2} "
            f"Age:{getattr(p, 'age', 0):<2} "
            f"{getattr(p, 'nationality', 'Japan'):<12} "
            f"Salary:${getattr(p, 'salary', 0):,}"
        )

    return players


def choose_trade_team(all_teams, user_team):
    teams = print_trade_team_list(all_teams, user_team)
    if not teams:
        return None

    while True:
        choice = input("番号: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(teams):
                return teams[idx]
        except ValueError:
            pass
        print("正しい番号を入力してください。")


def choose_player_from_list(players, prompt):
    if not players:
        return None

    while True:
        choice = input(prompt).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(players):
                return players[idx]
        except ValueError:
            pass
        print("正しい番号を入力してください。")


def print_trade_evaluation_summary(user_eval, ai_eval):
    print_separator("トレード評価")
    print(f"あなた側評価  : {'ACCEPT' if user_eval.accepts else 'REJECT'} | Score {user_eval.score}")
    print(f"AI側評価      : {'ACCEPT' if ai_eval.accepts else 'REJECT'} | Score {ai_eval.score}")
    print(f"あなた側理由   : {', '.join(user_eval.reasons)}")
    print(f"AI側理由       : {', '.join(ai_eval.reasons)}")


def propose_trade(all_teams, user_team):
    trade_system = TradeSystem()

    print_separator("トレード提案")
    ai_team = choose_trade_team(all_teams, user_team)
    if ai_team is None:
        return

    ai_players = print_tradeable_players(ai_team, f"{ai_team.name} のトレード候補")
    if not ai_players:
        return
    ai_player = choose_player_from_list(ai_players, "相手から欲しい選手の番号: ")
    if ai_player is None:
        return

    user_players = print_tradeable_players(user_team, "自チームの放出候補")
    if not user_players:
        return
    user_player = choose_player_from_list(user_players, "放出する選手の番号: ")
    if user_player is None:
        return

    user_eval, ai_eval = trade_system.evaluate_one_for_one_trade(
        user_team=user_team,
        ai_team=ai_team,
        user_send_player=user_player,
        ai_send_player=ai_player
    )
    print_trade_evaluation_summary(user_eval, ai_eval)

    accepted, reason, detail = trade_system.should_ai_accept_trade(
        user_team=user_team,
        ai_team=ai_team,
        user_send_player=user_player,
        ai_send_player=ai_player
    )

    if not accepted:
        print_separator("トレード結果")
        print(f"AIが拒否しました: {reason}")
        return

    confirm = input("このトレードを成立させますか？ (y/n): ").strip().lower()
    if confirm != "y":
        print("トレードを中止しました。")
        return

    success = trade_system.execute_one_for_one_trade(
        team_a=user_team,
        team_b=ai_team,
        player_a=user_player,
        player_b=ai_player
    )

    print_separator("トレード結果")
    if success:
        print(f"成立: {user_player.name} <-> {ai_player.name}")
    else:
        print("トレード実行に失敗しました。")


def run_trade_menu(all_teams, user_team):
    while True:
        print_separator("トレードメニュー")
        print("1. 相手チーム一覧を見る")
        print("2. トレード提案")
        print("3. 戻る")

        choice = input("番号: ").strip()

        if choice == "1":
            print_trade_team_list(all_teams, user_team)
        elif choice == "2":
            propose_trade(all_teams, user_team)
        elif choice == "3":
            return
        else:
            print("正しい番号を入力してください。")


FACILITY_LABELS = {
    "arena_level": "アリーナ",
    "training_facility_level": "トレーニング施設",
    "medical_facility_level": "メディカル施設",
    "front_office_level": "フロントオフィス",
}

FACILITY_BASE_COSTS = {
    "arena_level": 2_000_000,
    "training_facility_level": 1_200_000,
    "medical_facility_level": 1_000_000,
    "front_office_level": 900_000,
}


def get_facility_upgrade_cost(user_team, facility_key):
    current_level = int(getattr(user_team, facility_key, 1))
    base_cost = FACILITY_BASE_COSTS.get(facility_key, 1_000_000)
    return int(base_cost * max(1, current_level))


def print_facility_status(user_team):
    print_separator("施設投資状況")
    print(f"現在資金: ${int(getattr(user_team, 'money', 0)):,}")
    print()

    for facility_key in [
        "arena_level",
        "training_facility_level",
        "medical_facility_level",
        "front_office_level",
    ]:
        label = FACILITY_LABELS.get(facility_key, facility_key)
        level = int(getattr(user_team, facility_key, 1))
        upgrade_cost = get_facility_upgrade_cost(user_team, facility_key)
        print(f"{label:<18} Lv.{level:<2} -> 次回投資額 ${upgrade_cost:,}")

    print()
    print(f"人気          : {int(getattr(user_team, 'popularity', 0))}")
    print(f"ファン基盤      : {int(getattr(user_team, 'fan_base', 0))}")
    print(f"スカウト水準    : {int(getattr(user_team, 'scout_level', 0))}")


def apply_facility_upgrade(user_team, facility_key):
    label = FACILITY_LABELS.get(facility_key, facility_key)
    current_level = int(getattr(user_team, facility_key, 1))
    cost = get_facility_upgrade_cost(user_team, facility_key)
    money = int(getattr(user_team, "money", 0))

    print_separator(f"{label} 投資")
    print(f"現在レベル : Lv.{current_level}")
    print(f"必要資金   : ${cost:,}")
    print(f"現在資金   : ${money:,}")

    if money < cost:
        print("資金不足のため投資できません。")
        return

    confirm = input("投資を実行しますか？ (y/n): ").strip().lower()
    if confirm != "y":
        print("投資を中止しました。")
        return

    setattr(user_team, facility_key, current_level + 1)

    if facility_key == "arena_level":
        user_team.popularity = int(getattr(user_team, "popularity", 0)) + 1
        user_team.fan_base = int(getattr(user_team, "fan_base", 0)) + 2
    elif facility_key == "training_facility_level":
        user_team.popularity = int(getattr(user_team, "popularity", 0)) + 1
    elif facility_key == "medical_facility_level":
        user_team.popularity = int(getattr(user_team, "popularity", 0)) + 1
    elif facility_key == "front_office_level":
        user_team.scout_level = int(getattr(user_team, "scout_level", 0)) + 3

    if hasattr(user_team, "record_financial_result"):
        user_team.record_financial_result(
            revenue=0,
            expense=cost,
            note=f"facility_upgrade:{facility_key}:Lv{current_level + 1}"
        )

    print_separator("投資完了")
    print(f"{label} を Lv.{current_level} -> Lv.{current_level + 1} に強化しました。")
    print(f"残り資金: ${int(getattr(user_team, 'money', 0)):,}")


def run_facility_investment_menu(user_team):
    while True:
        print_facility_status(user_team)
        print("1. アリーナに投資")
        print("2. トレーニング施設に投資")
        print("3. メディカル施設に投資")
        print("4. フロントオフィスに投資")
        print("5. 財務レポートを見る")
        print("6. オーナーミッションを見る")
        print("7. 戻る")

        choice = input("番号: ").strip()

        if choice == "1":
            apply_facility_upgrade(user_team, "arena_level")
        elif choice == "2":
            apply_facility_upgrade(user_team, "training_facility_level")
        elif choice == "3":
            apply_facility_upgrade(user_team, "medical_facility_level")
        elif choice == "4":
            apply_facility_upgrade(user_team, "front_office_level")
        elif choice == "5":
            print_separator("財務レポート")
            if hasattr(user_team, "get_finance_report_text"):
                print(user_team.get_finance_report_text())
            else:
                print("財務レポートはまだ利用できません。")
        elif choice == "6":
            print_separator("オーナーミッション")
            if hasattr(user_team, "get_owner_mission_report_text"):
                print(user_team.get_owner_mission_report_text())
            else:
                print("オーナーミッションはまだ利用できません。")
        elif choice == "7":
            return
        else:
            print("正しい番号を入力してください。")


def run_gm_menu(all_teams, user_team):
    while True:
        print_separator("GMメニュー")
        print("1. チーム情報を見る")
        print("2. 戦術を変更する")
        print("3. HCスタイルを変更する")
        print("4. 起用方針を変更する")
        print("5. ロスターを見る")
        print("6. サラリーキャップ確認")
        print("7. スタメン変更")
        print("8. 6thマン変更")
        print("9. ベンチ序列変更")
        print("10. トレード")
        print("11. 施設投資")
        print("12. 戻る")

        choice = input("番号: ").strip()

        if choice == "1":
            print_team_identity(user_team)
        elif choice == "2":
            set_team_strategy(user_team)
        elif choice == "3":
            set_team_coach_style(user_team)
        elif choice == "4":
            set_team_usage_policy(user_team)
        elif choice == "5":
            print_gm_roster_view(user_team)
        elif choice == "6":
            print_salary_cap_status(user_team)
        elif choice == "7":
            change_starting_lineup(user_team)
        elif choice == "8":
            change_sixth_man(user_team)
        elif choice == "9":
            change_bench_order(user_team)
        elif choice == "10":
            run_trade_menu(all_teams, user_team)
        elif choice == "11":
            run_facility_investment_menu(user_team)
        elif choice == "12":
            break
        else:
            print("正しい番号を入力してください。")


def _prompt_save_path() -> Path:
    default_p = default_save_path("quicksave")
    print(f"保存先パス（Enter だけで {default_p}）:")
    raw = input().strip()
    return Path(raw) if raw else default_p


def _prompt_load_resume() -> Dict[str, Any]:
    default_p = default_save_path("quicksave")
    print(f"読み込むファイルパス（Enter だけで {default_p}）:")
    raw = input().strip()
    path = Path(raw) if raw else default_p
    payload = load_world(path)
    validate_payload(payload)
    return payload


def run_interactive_season(
    teams=None,
    free_agents=None,
    user_team=None,
    tracked_player_name=None,
    resume: Optional[Dict[str, Any]] = None,
    start_at_annual_menu: bool = False,
):
    """
    CLI シーズンループ。resume を渡すとセーブから続行（年度進行メニュー直後から再開可）。
    start_at_annual_menu: UI でオフシーズンまで済ませた直後など、年度進行メニューから開始する。
    """
    skip_to_annual_menu = False
    if resume is not None:
        validate_payload(resume)
        sync_player_id_counter_from_world(resume["teams"], resume["free_agents"])
        teams = resume["teams"]
        free_agents = resume["free_agents"]
        user_team = find_user_team(teams, resume["user_team_id"])
        tracked_player_name = resume.get("tracked_player_name")
        season_count = resume["season_count"]
        skip_to_annual_menu = bool(resume.get("at_annual_menu"))
    else:
        if teams is None or free_agents is None or user_team is None:
            raise ValueError("run_interactive_season: teams / free_agents / user_team が必要です（resume 未指定時）")
        season_count = 1
        if start_at_annual_menu:
            skip_to_annual_menu = True

    while True:
        if not skip_to_annual_menu:
            print_separator(f"シーズン {season_count} 開始")
            season = Season(teams, free_agents)

            while not season.season_finished:
                print_separator("シーズンメニュー")
                print(f"現在ラウンド: {season.current_round}/{season.total_rounds}")
                print(f"現在年数: {season_count}")
                print("1. 1ラウンド進める")
                print("2. 5ラウンド進める")
                print("3. 個人成績ランキングを見る")
                print("4. 順位表を見る")
                print("5. 進行状況を見る")
                print("6. クラブ史を見る")
                print("7. キャリア追跡ログを見る")
                print("8. GMメニュー")
                print("9. シーズンを最後まで進める")

                choice = input("番号: ").strip()

                if choice == "1":
                    season.simulate_next_round()
                elif choice == "2":
                    season.simulate_multiple_rounds(5)
                elif choice == "3":
                    season.print_midseason_leaderboards()
                elif choice == "4":
                    season.print_midseason_standings()
                elif choice == "5":
                    season.print_progress()
                elif choice == "6":
                    print_user_team_history(user_team)
                elif choice == "7":
                    print_player_career_tracking(user_team, tracked_player_name=tracked_player_name)
                elif choice == "8":
                    run_gm_menu(teams, user_team)
                elif choice == "9":
                    season.simulate_to_end()
                else:
                    print("正しい番号を入力してください。")

            print_separator("オフシーズン開始")
            offseason = Offseason(teams, free_agents)
            offseason.run()

            print_player_career_tracking(user_team, tracked_player_name=tracked_player_name)
            print_user_team_history(user_team)
        else:
            skip_to_annual_menu = False

        print_separator("年度進行メニュー")
        print("1. 次のシーズンへ進む")
        print("2. クラブ史を見る")
        print("3. キャリア追跡ログを見る")
        print("4. GMメニュー")
        print("5. 終了する")
        print("6. セーブする（この時点の続きから再開できます）")

        next_choice = input("番号: ").strip()

        if next_choice == "1":
            season_count += 1
            continue
        elif next_choice == "2":
            print_user_team_history(user_team)
            continue
        elif next_choice == "3":
            print_player_career_tracking(user_team, tracked_player_name=tracked_player_name)
            continue
        elif next_choice == "4":
            run_gm_menu(teams, user_team)
            continue
        elif next_choice == "6":
            save_path = _prompt_save_path()
            payload = {
                "teams": teams,
                "free_agents": free_agents,
                "user_team_id": user_team.team_id,
                "tracked_player_name": tracked_player_name,
                "season_count": season_count,
                "at_annual_menu": True,
                "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
                "simulation_seed": get_last_simulation_seed(),
            }
            try:
                save_world(save_path, payload)
                print(f"セーブしました: {save_path}")
            except Exception as exc:
                print(f"セーブに失敗しました: {exc}")
            continue
        elif next_choice == "5":
            print_separator("Simulation Completed")
            break
        else:
            print("正しい番号を入力してください。")


def build_initial_game_world():
    print_separator("クラブ作成・世界生成")

    team_name, home_city, market_size = create_user_team_info()
    roster_build_mode = choose_roster_build_mode()

    teams = generate_teams()
    user_team = apply_user_team_to_league(teams, team_name, home_city, market_size)

    if roster_build_mode == "auto":
        icon_data = choose_icon_player_auto_from_league(teams)
    else:
        icon_data = choose_icon_player_from_league(teams)

    source_team = icon_data.get("team") if isinstance(icon_data, dict) else None
    source_player = icon_data.get("player") if isinstance(icon_data, dict) else None
    if source_team is not None and source_player is not None and source_player in getattr(source_team, "players", []):
        source_team.remove_player(source_player)

    icon_player = create_icon_player(icon_data)

    fictional_pool = create_fictional_player_pool()

    if roster_build_mode == "auto":
        auto_draft_players(fictional_pool, user_team, icon_player)
    else:
        draft_players(fictional_pool, user_team, icon_player)
    print_user_roster(user_team)

    free_agents = []
    assign_fictional_teams_and_rival(teams, user_team, fictional_pool, free_agents)

    return teams, free_agents, user_team, icon_player


def choose_game_launch_mode():
    print_separator("起動モード選択")
    print("1. 従来CLIモード")
    print("2. 主画面UIモード（試験実装）")

    while True:
        choice = input("番号: ").strip()
        if choice in {"1", "2"}:
            return choice
        print("1 か 2 を入力してください。")


def run_main_menu_ui_mode(
    teams,
    free_agents,
    user_team,
    tracked_player_name=None,
    user_settings: Optional[Dict[str, Any]] = None,
):
    if launch_main_menu is None:
        print("main_menu_view.py の読み込みに失敗しました。CLIモードで続行します。")
        run_interactive_season(
            teams=teams,
            free_agents=free_agents,
            user_team=user_team,
            tracked_player_name=tracked_player_name,
        )
        return

    season = Season(teams, free_agents)
    ui_flow = {"offseason_completed": False}

    def advance_one_round():
        if season.season_finished:
            import tkinter as tk
            from tkinter import messagebox

            root = tk._default_root
            if root is not None:
                ok = messagebox.askokcancel(
                    "オフシーズン",
                    "オフシーズン処理（再契約・FA・ドラフト等）を開始します。\n"
                    "数分かかる場合があり、その間ウィンドウが応答しなくなることがあります。\n\n"
                    "続けますか？",
                    parent=root,
                )
                if not ok:
                    return
            print_separator("オフシーズン開始（UIモード）")
            try:
                offseason = Offseason(teams, free_agents)
                offseason.run()
            except Exception as exc:
                print(f"オフシーズン処理中にエラー: {exc}")
                if root is not None:
                    messagebox.showerror(
                        "エラー",
                        f"オフシーズン処理でエラーが発生しました:\n{exc}",
                        parent=root,
                    )
                return
            print_separator("オフシーズン完了")
            print_player_career_tracking(user_team, tracked_player_name=tracked_player_name)
            print_user_team_history(user_team)
            ui_flow["offseason_completed"] = True
            if root is not None:
                messagebox.showinfo(
                    "完了",
                    "オフシーズンが終わりました。\n"
                    "メインウィンドウを閉じると、ターミナルに年度進行メニューが続きます。\n"
                    "次シーズン・セーブはそこから操作できます。",
                    parent=root,
                )
            return
        season.simulate_next_round()
        print(f"[MAIN_MENU] round={season.current_round}/{season.total_rounds}")

    menu_callbacks = {
        "日程": advance_one_round,
    }

    print_separator("主画面UIモード開始")
    print("『日程』または『次へ進む』で1ラウンド進行します。")
    print("シーズン終了後は『オフシーズンを実行』→ 完了後、ウィンドウを閉じるとターミナルで年度進行メニューが続きます。")
    print("他メニューは段階的に接続します。")

    launch_main_menu(
        team=user_team,
        season=season,
        on_advance=advance_one_round,
        menu_callbacks=menu_callbacks,
        user_settings=user_settings,
    )

    if ui_flow["offseason_completed"]:
        print_separator("UIでのオフシーズン完了 → CLI 年度進行メニュー")
        run_interactive_season(
            teams=teams,
            free_agents=free_agents,
            user_team=user_team,
            tracked_player_name=tracked_player_name,
            start_at_annual_menu=True,
        )


def simulate():
    _settings = ensure_settings_file_exists()
    apply_settings_to_environment(_settings)
    setup_application_logging(_settings)
    try_init_steam()
    enforce_steam_license(_settings)
    print_separator("Basketball GM Simulation")
    print("1. 新しいゲームを始める")
    print("2. セーブデータを読み込んで続きから")
    resume_payload: Optional[Dict[str, Any]] = None
    while True:
        start_choice = input("番号: ").strip()
        if start_choice == "1":
            break
        if start_choice == "2":
            try:
                resume_payload = _prompt_load_resume()
            except FileNotFoundError:
                print("ファイルが見つかりません。もう一度選んでください。")
                continue
            except ValueError as exc:
                print(f"読み込みエラー: {exc}")
                continue
            break
        print("1 か 2 を入力してください。")

    if resume_payload is not None:
        print_separator("セーブを読み込みました")
        print("続きは従来の CLI モードで進行します（シーズン途中の途中ラウンドは未対応。年度進行メニュー付近から再開）。")
        init_simulation_random(resume_payload.get("simulation_seed"))
        run_interactive_season(resume=resume_payload)
        return

    init_simulation_random()
    teams, free_agents, user_team, icon_player = build_initial_game_world()

    print_separator("シーズン開始")
    print("シーズン途中でランキングや順位表を確認できます。")
    print("クラブ史とキャリア追跡ログもいつでも見られます。")
    print("GMメニューから戦術・HCスタイル・起用方針・ロスター・サラリーキャップ・スタメン・6thマン・ベンチ序列・トレードを変更できます。")
    print("オフシーズン後は同じ世界線のまま次の年へ進めます。")

    launch_mode = choose_game_launch_mode()

    if launch_mode == "2":
        run_main_menu_ui_mode(
            teams=teams,
            free_agents=free_agents,
            user_team=user_team,
            tracked_player_name=icon_player.name,
            user_settings=_settings,
        )
        return

    run_interactive_season(
        teams=teams,
        free_agents=free_agents,
        user_team=user_team,
        tracked_player_name=icon_player.name,
    )


def run_smoke() -> int:
    """
    対話なしで土台を検証する（配布 exe・CI・手動確認用）。成功時は 0 を返す。
    ログ初期化や Steam は行わず、セーブ・乱数の最小経路のみ。
    """
    import tempfile

    from basketball_sim.models.team import Team
    from basketball_sim.persistence.save_load import load_world, save_world, validate_payload
    from basketball_sim.utils.sim_rng import init_simulation_random

    try:
        init_simulation_random(42_424_242)
        team = Team(team_id=1, name="Smoke FC", league_level=1)
        payload_in = {
            "teams": [team],
            "free_agents": [],
            "user_team_id": 1,
            "season_count": 1,
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "smoke.sav"
            save_world(path, payload_in)
            out = load_world(path)
            validate_payload(out)
            if len(out["teams"]) != 1:
                raise ValueError("teams length mismatch after load")
    except Exception as exc:
        print(f"smoke failed: {exc}", file=sys.stderr)
        return 1
    print("smoke ok")
    return 0


def run_steam_diag() -> int:
    """
    Steam 連携の診断（手元確認用）。

    Steamworks パートナー側の App 作成前でも実行できる（未接続ならその旨が出るだけ）。
    """
    from basketball_sim.integrations.steamworks_bridge import (
        steam_is_subscribed,
        steam_loaded_dll_path,
        steam_native_loaded,
        try_init_steam,
    )

    ok = try_init_steam()
    print("steam_diag:")
    print(f"  try_init_steam: {ok}")
    print(f"  steam_native_loaded: {steam_native_loaded()}")
    print(f"  steam_loaded_dll_path: {steam_loaded_dll_path()}")
    print(f"  steam_is_subscribed: {steam_is_subscribed()}")
    return 0


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        raise SystemExit(run_smoke())
    if "--steam-diag" in sys.argv:
        raise SystemExit(run_steam_diag())
    simulate()
