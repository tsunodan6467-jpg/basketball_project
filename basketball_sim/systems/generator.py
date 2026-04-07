import random

from basketball_sim.config.game_constants import GENERATOR_INITIAL_SALARY_BASE_PER_OVR
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.contract_logic import MIN_SALARY_DEFAULT

# 選手IDが重複しないように管理するカウンタ
_player_id_counter = 1


def sync_player_id_counter_from_world(teams, free_agents) -> int:
    """
    セーブロード後に呼ぶ。既存ロスター・FA の player_id の最大値の次から採番する。

    モジュール内カウンタは pickle で保存されないため、再開後に ID が衝突しないようにする。
    """
    global _player_id_counter
    m = 0
    for t in teams or []:
        for p in getattr(t, "players", None) or []:
            pid = getattr(p, "player_id", None)
            if isinstance(pid, int):
                m = max(m, pid)
    for p in free_agents or []:
        pid = getattr(p, "player_id", None)
        if isinstance(pid, int):
            m = max(m, pid)
    _player_id_counter = max(_player_id_counter, m + 1)
    return _player_id_counter


def calculate_initial_salary(ovr: int) -> int:
    """OVR をもとに generator が付与する初期年俸（開幕ペイロール用。契約希望額は PLAYER_SALARY_BASE_PER_OVR）。"""
    return int(ovr) * GENERATOR_INITIAL_SALARY_BASE_PER_OVR


def _initial_roster_target_team_payroll(league_level: int) -> int:
    """
    開幕ロスター専用: ディビジョンごとの目標総年俸（円/年）。
    `generate_teams` のみで使用。D1 > D2 > D3 となる非重複レンジで段差を付ける。
    """
    lv = max(1, min(3, int(league_level)))
    if lv == 1:
        return random.randint(1_020_000_000, 1_140_000_000)
    if lv == 2:
        return random.randint(680_000_000, 780_000_000)
    return random.randint(480_000_000, 580_000_000)


def _rebalance_team_initial_salaries_to_target(players: list[Player], target_total: int) -> None:
    """
    素年俸（calculate_initial_salary）の相対比を保ちつつ、チーム合計が target_total になるよう整数配分する。
    最大剰余法で総額一致 → 下限適用後に総額を再調整。generate_teams 専用。
    """
    n = len(players)
    if n == 0 or target_total <= 0:
        return

    floor = int(MIN_SALARY_DEFAULT)
    min_sum = floor * n
    if target_total < min_sum:
        target_total = min_sum

    raw = [max(1, int(getattr(p, "salary", 0) or 0)) for p in players]
    weight_sum = sum(raw)
    if weight_sum <= 0:
        base = target_total // n
        rem = target_total % n
        for i, p in enumerate(players):
            p.salary = base + (1 if i < rem else 0)
        return

    exact = [raw[i] / weight_sum * target_total for i in range(n)]
    alloc = [int(x) for x in exact]
    remainder = target_total - sum(alloc)
    order = sorted(range(n), key=lambda i: exact[i] - alloc[i], reverse=True)
    for k in range(remainder):
        alloc[order[k]] += 1

    alloc = [max(floor, a) for a in alloc]
    diff = target_total - sum(alloc)
    if diff == 0:
        for i, p in enumerate(players):
            p.salary = int(alloc[i])
        return

    if diff > 0:
        by_high = sorted(range(n), key=lambda i: alloc[i], reverse=True)
        i = 0
        while diff > 0:
            alloc[by_high[i % n]] += 1
            diff -= 1
            i += 1
    else:
        need = -diff
        by_high = sorted(range(n), key=lambda i: alloc[i], reverse=True)
        i = 0
        guard = 0
        while need > 0 and guard < n * (target_total + 1):
            j = by_high[i % n]
            if alloc[j] > floor:
                alloc[j] -= 1
                need -= 1
            i += 1
            guard += 1

    for i, p in enumerate(players):
        p.salary = int(alloc[i])


def _assign_extended_attributes(player: Player, pos: str, ovr: int) -> None:
    """
    拡張能力（handling/iq/speed/power）の初期値を安全に付与。
    Phase 1 では試合計算へ強く反映しないため、既存8能力を基準に小さく配る。
    """
    base = int(max(40, min(99, ovr)))
    pos = str(pos or "SF")
    if pos == "PG":
        player.handling = min(99, int(base + random.randint(4, 9)))
        player.iq = min(99, int(base + random.randint(2, 7)))
        player.speed = min(99, int(base + random.randint(1, 6)))
        player.power = max(1, int(base + random.randint(-8, -2)))
    elif pos == "SG":
        player.handling = min(99, int(base + random.randint(2, 7)))
        player.iq = min(99, int(base + random.randint(1, 5)))
        player.speed = min(99, int(base + random.randint(1, 6)))
        player.power = max(1, int(base + random.randint(-5, 1)))
    elif pos == "SF":
        player.handling = min(99, int(base + random.randint(-1, 4)))
        player.iq = min(99, int(base + random.randint(1, 5)))
        player.speed = min(99, int(base + random.randint(-1, 4)))
        player.power = min(99, int(base + random.randint(-1, 5)))
    elif pos == "PF":
        player.handling = max(1, int(base + random.randint(-6, 1)))
        player.iq = min(99, int(base + random.randint(0, 4)))
        player.speed = max(1, int(base + random.randint(-4, 2)))
        player.power = min(99, int(base + random.randint(3, 9)))
    else:  # C
        player.handling = max(1, int(base + random.randint(-8, -1)))
        player.iq = min(99, int(base + random.randint(0, 4)))
        player.speed = max(1, int(base + random.randint(-6, 1)))
        player.power = min(99, int(base + random.randint(5, 12)))


def _get_team_strategy() -> str:
    """
    初期チームに割り当てる戦術を抽選する。
    現在のリーグ全体バランスに合わせて、極端に偏らない重みで設定。
    """
    strategies = [
        "balanced",
        "run_and_gun",
        "three_point",
        "defense",
        "inside",
    ]
    weights = [0.35, 0.20, 0.20, 0.15, 0.10]
    return random.choices(strategies, weights=weights, k=1)[0]


def _get_coach_style() -> str:
    """
    初期チームに割り当てるコーチスタイルを抽選する。
    まずは極端に偏らないようにしつつ、balanced をやや多めにする。
    """
    coach_styles = [
        "balanced",
        "offense",
        "defense",
        "development",
    ]
    weights = [0.40, 0.20, 0.20, 0.20]
    return random.choices(coach_styles, weights=weights, k=1)[0]


def _get_weighted_base_ovr() -> int:
    """重み付けされた分布から基準OVRを抽選する"""
    ranges = [
        (84, 89),
        (78, 83),
        (72, 77),
        (66, 71),
        (60, 65),
        (50, 59)
    ]
    weights = [4, 12, 22, 28, 22, 12]

    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    return random.randint(selected_range[0], selected_range[1])


def _get_weighted_fictional_base_ovr() -> int:
    """
    架空D3選手向けの弱めOVR分布。
    目安: 50〜68
    """
    ranges = [
        (66, 68),
        (62, 65),
        (58, 61),
        (54, 57),
        (50, 53),
    ]
    weights = [10, 20, 28, 24, 18]

    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    return random.randint(selected_range[0], selected_range[1])


def _get_weighted_draft_ovr() -> int:
    """
    ドラフト候補専用のOVR分布。
    50が大量発生しないようにしつつ、
    上位数人はしっかり有望株が出る形に寄せる。
    """
    ranges = [
        (73, 76),
        (69, 72),
        (65, 68),
        (61, 64),
        (57, 60),
        (54, 56),
        (51, 53),
    ]
    weights = [4, 10, 18, 24, 22, 14, 8]

    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    return random.randint(selected_range[0], selected_range[1])


def _get_special_draft_ovr() -> int:
    """
    目玉新人専用OVR。
    通常新人より明確に上振れしやすくする。
    目安: 72〜79
    """
    ranges = [
        (76, 79),
        (74, 75),
        (72, 73),
    ]
    weights = [28, 42, 30]
    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    return random.randint(selected_range[0], selected_range[1])


def _get_international_market_ovr(nationality: str) -> int:
    """
    国際市場向けOVR。
    Foreign は高め、Asia はやや控えめ。
    """
    if nationality == "Foreign":
        ranges = [
            (78, 83),
            (74, 77),
            (70, 73),
            (66, 69),
        ]
        weights = [12, 28, 35, 25]
    else:
        ranges = [
            (74, 79),
            (70, 73),
            (66, 69),
            (62, 65),
        ]
        weights = [10, 25, 35, 30]

    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    return random.randint(selected_range[0], selected_range[1])


def _get_age_ovr_modifier(age: int) -> int:
    """年齢層に応じたOVR補正値を返す"""
    if 18 <= age <= 20:
        return random.randint(-4, 0)
    elif 21 <= age <= 23:
        return random.randint(-2, 1)
    elif 24 <= age <= 28:
        return random.randint(0, 3)
    elif 29 <= age <= 32:
        return random.randint(-1, 2)
    elif 33 <= age <= 35:
        return random.randint(-4, 0)
    return 0


def _get_fictional_age_ovr_modifier(age: int) -> int:
    """
    架空D3選手向けの年齢補正。
    若手寄りだが、全体として弱めに収める。
    """
    if 18 <= age <= 20:
        return random.randint(-2, 1)
    elif 21 <= age <= 23:
        return random.randint(-1, 1)
    elif 24 <= age <= 27:
        return random.randint(0, 1)
    elif 28 <= age <= 31:
        return random.randint(-1, 0)
    elif 32 <= age <= 35:
        return random.randint(-3, -1)
    return 0


def _get_potential(ovr: int, age: int) -> str:
    """年齢とOVRに基づいてPotential (A/B/C/D) を決定する"""
    if age <= 23:
        if ovr >= 78:
            return random.choices(['A', 'B', 'C'], weights=[70, 25, 5])[0]
        elif ovr >= 65:
            return random.choices(['A', 'B', 'C', 'D'], weights=[30, 50, 15, 5])[0]
        else:
            return random.choices(['B', 'C', 'D'], weights=[20, 50, 30])[0]

    elif age <= 28:
        if ovr >= 80:
            return random.choices(['B', 'C', 'D'], weights=[30, 50, 20])[0]
        else:
            return random.choices(['C', 'D'], weights=[40, 60])[0]

    else:
        if ovr >= 80:
            return random.choices(['C', 'D'], weights=[30, 70])[0]
        else:
            return random.choices(['D', 'C'], weights=[90, 10])[0]


def _get_fictional_potential(ovr: int, age: int) -> str:
    """架空D3選手向けのPotential決定"""
    if age <= 22:
        if ovr >= 64:
            return random.choices(['A', 'B', 'C', 'D'], weights=[18, 42, 30, 10])[0]
        else:
            return random.choices(['B', 'C', 'D'], weights=[30, 45, 25])[0]

    if age <= 27:
        return random.choices(['B', 'C', 'D'], weights=[20, 50, 30])[0]

    return random.choices(['C', 'D'], weights=[35, 65])[0]


def _get_special_potential() -> str:
    """目玉新人専用Potential"""
    return random.choices(
        ['S', 'A', 'B'],
        weights=[30, 50, 20],
        k=1
    )[0]


def _get_nationality() -> str:
    """国籍を定めた比率で抽選する"""
    nats = ["Japan", "Foreign", "Naturalized", "Asia"]
    weights = [70, 20, 5, 5]
    return random.choices(nats, weights=weights, k=1)[0]


def _get_popularity(ovr: int) -> int:
    """OVRに基づいて人気度を決定する"""
    if ovr >= 84:
        return random.randint(65, 80)
    elif ovr >= 78:
        return random.randint(55, 70)
    elif ovr >= 70:
        return random.randint(45, 60)
    elif ovr >= 60:
        return random.randint(40, 55)
    else:
        return random.randint(35, 50)


def _build_archetype_by_position(pos: str) -> str:
    archetypes = {
        "PG": ["Floor General", "Playmaker", "Shot Creator"],
        "SG": ["Shooter", "Scorer", "Two-Way Guard"],
        "SF": ["Wing", "Two-Way Wing", "Slasher"],
        "PF": ["Stretch Big", "Inside Finisher", "Rebounder"],
        "C": ["Rim Protector", "Post Big", "Rebounder"],
    }
    return random.choice(archetypes.get(pos, ["Balanced"]))


def _initialize_player_meta(player: Player):
    """
    ゲーム全体で使う補助属性を安全に初期化する。
    """
    if not hasattr(player, "league_years"):
        player.league_years = max(0, getattr(player, "years_pro", 0))

    if not hasattr(player, "was_naturalized"):
        player.was_naturalized = getattr(player, "nationality", "Japan") == "Naturalized"

    if not hasattr(player, "draft_profile_label"):
        player.draft_profile_label = "通常新人"

    if not hasattr(player, "draft_priority_bonus"):
        player.draft_priority_bonus = 0

    if not hasattr(player, "draft_origin_type"):
        player.draft_origin_type = "normal"

    if not hasattr(player, "acquisition_type"):
        player.acquisition_type = "normal"

    if not hasattr(player, "acquisition_note"):
        player.acquisition_note = ""

    if not hasattr(player, "reborn_from"):
        player.reborn_from = None

    if not hasattr(player, "is_reborn"):
        player.is_reborn = False

    if not hasattr(player, "is_international_reborn"):
        player.is_international_reborn = False


def _set_acquisition(player: Player, acquisition_type: str, acquisition_note: str = ""):
    """
    選手の獲得経路を安全に記録する。
    """
    player.acquisition_type = acquisition_type
    player.acquisition_note = acquisition_note


def generate_single_player(
    age_override: int = None,
    base_ovr_override: int = None,
    position_override: str = None,
    nationality_override: str = None,
    height_override: float = None,
    weight_override: float = None
) -> Player:
    """
    ランダムで実情に即した能力や特徴を持つ選手を1人生成します。
    オーバーライド引数が指定されている場合はそれを使います。
    """
    global _player_id_counter
    pid = _player_id_counter
    _player_id_counter += 1

    age = age_override if age_override is not None else random.randint(18, 35)

    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    pos = position_override if position_override is not None else random.choice(positions)

    nationality = nationality_override if nationality_override is not None else _get_nationality()

    if base_ovr_override is not None:
        final_ovr = min(99, max(40, base_ovr_override))
    else:
        base_ovr = _get_weighted_base_ovr()
        age_mod = _get_age_ovr_modifier(age)
        final_ovr = min(99, max(53, base_ovr + age_mod))

    potential = _get_potential(final_ovr, age)
    pop = _get_popularity(final_ovr)

    height_cm = 0.0
    weight_kg = 0.0

    shoot = final_ovr
    three = final_ovr
    drive = final_ovr
    passing = final_ovr
    rebound = final_ovr
    defense = final_ovr
    ft = final_ovr + random.randint(-5, 5)

    if pos == 'PG':
        height_cm = random.uniform(170, 185)
        weight_kg = random.uniform(65, 80)
        passing += random.randint(3, 8)
        shoot += random.randint(0, 5)
        three += random.randint(0, 5)
        rebound -= random.randint(5, 12)

    elif pos == 'SG':
        height_cm = random.uniform(175, 192)
        weight_kg = random.uniform(70, 88)
        shoot += random.randint(3, 8)
        three += random.randint(3, 8)

    elif pos == 'SF':
        height_cm = random.uniform(185, 200)
        weight_kg = random.uniform(80, 100)
        shoot += random.randint(-2, 3)
        defense += random.randint(-2, 3)

    elif pos == 'PF':
        height_cm = random.uniform(195, 208)
        weight_kg = random.uniform(90, 110)
        rebound += random.randint(4, 9)
        defense += random.randint(2, 7)
        three -= random.randint(4, 10)
        passing -= random.randint(2, 7)

    elif pos == 'C':
        height_cm = random.uniform(200, 215)
        weight_kg = random.uniform(100, 125)
        rebound += random.randint(6, 12)
        defense += random.randint(5, 10)
        three -= random.randint(8, 15)
        passing -= random.randint(5, 12)

    if height_override is not None:
        height_cm = height_override
    if weight_override is not None:
        weight_kg = weight_override

    shoot = max(1, min(99, shoot + random.randint(-3, 3)))
    three = max(1, min(99, three + random.randint(-3, 3)))
    drive = max(1, min(99, drive + random.randint(-3, 3)))
    passing = max(1, min(99, passing + random.randint(-3, 3)))
    rebound = max(1, min(99, rebound + random.randint(-3, 3)))
    defense = max(1, min(99, defense + random.randint(-3, 3)))
    ft = max(1, min(99, ft))

    stamina = random.randint(60, 99)

    player = Player(
        player_id=pid,
        name=f"Player_{pid}",
        age=age,
        nationality=nationality,
        position=pos,
        height_cm=height_cm,
        weight_kg=weight_kg,

        shoot=shoot,
        three=three,
        drive=drive,
        passing=passing,
        rebound=rebound,
        defense=defense,
        ft=ft,
        stamina=stamina,

        ovr=final_ovr,
        potential=potential,
        archetype=_build_archetype_by_position(pos),
        usage_base=random.randint(10, 30),
        popularity=pop
    )

    player.salary = calculate_initial_salary(player.ovr)
    _assign_extended_attributes(player, pos, final_ovr)
    player.years_pro = max(0, player.age - 18)
    player.contract_years_left = random.randint(2, 4)

    _initialize_player_meta(player)
    _set_acquisition(player, "normal", "standard_generation")
    return player


def generate_fictional_player(
    age_override: int = None,
    base_ovr_override: int = None,
    position_override: str = None,
    nationality_override: str = None,
    height_override: float = None,
    weight_override: float = None
) -> Player:
    """
    D3の架空チーム向け、弱め設定の選手を1人生成する。
    OVR目安は 50〜68。
    """
    global _player_id_counter
    pid = _player_id_counter
    _player_id_counter += 1

    age = age_override if age_override is not None else random.randint(18, 32)

    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    pos = position_override if position_override is not None else random.choice(positions)

    nationality = nationality_override if nationality_override is not None else _get_nationality()

    if base_ovr_override is not None:
        final_ovr = min(68, max(50, base_ovr_override))
    else:
        base_ovr = _get_weighted_fictional_base_ovr()
        age_mod = _get_fictional_age_ovr_modifier(age)
        final_ovr = min(68, max(50, base_ovr + age_mod))

    potential = _get_fictional_potential(final_ovr, age)
    pop = _get_popularity(final_ovr)

    height_cm = 0.0
    weight_kg = 0.0

    shoot = final_ovr
    three = final_ovr
    drive = final_ovr
    passing = final_ovr
    rebound = final_ovr
    defense = final_ovr
    ft = final_ovr + random.randint(-5, 5)

    if pos == 'PG':
        height_cm = random.uniform(170, 185)
        weight_kg = random.uniform(65, 80)
        passing += random.randint(2, 6)
        shoot += random.randint(0, 4)
        three += random.randint(0, 4)
        rebound -= random.randint(5, 10)

    elif pos == 'SG':
        height_cm = random.uniform(175, 192)
        weight_kg = random.uniform(70, 88)
        shoot += random.randint(2, 6)
        three += random.randint(2, 6)

    elif pos == 'SF':
        height_cm = random.uniform(185, 200)
        weight_kg = random.uniform(80, 100)
        shoot += random.randint(-2, 2)
        defense += random.randint(-2, 2)

    elif pos == 'PF':
        height_cm = random.uniform(195, 208)
        weight_kg = random.uniform(90, 110)
        rebound += random.randint(3, 7)
        defense += random.randint(2, 5)
        three -= random.randint(4, 8)
        passing -= random.randint(2, 5)

    elif pos == 'C':
        height_cm = random.uniform(200, 215)
        weight_kg = random.uniform(100, 125)
        rebound += random.randint(5, 10)
        defense += random.randint(4, 8)
        three -= random.randint(8, 12)
        passing -= random.randint(4, 8)

    if height_override is not None:
        height_cm = height_override
    if weight_override is not None:
        weight_kg = weight_override

    shoot = max(1, min(99, shoot + random.randint(-3, 3)))
    three = max(1, min(99, three + random.randint(-3, 3)))
    drive = max(1, min(99, drive + random.randint(-3, 3)))
    passing = max(1, min(99, passing + random.randint(-3, 3)))
    rebound = max(1, min(99, rebound + random.randint(-3, 3)))
    defense = max(1, min(99, defense + random.randint(-3, 3)))
    ft = max(1, min(99, ft))

    stamina = random.randint(58, 90)

    player = Player(
        player_id=pid,
        name=f"Fictional_{pid}",
        age=age,
        nationality=nationality,
        position=pos,
        height_cm=height_cm,
        weight_kg=weight_kg,

        shoot=shoot,
        three=three,
        drive=drive,
        passing=passing,
        rebound=rebound,
        defense=defense,
        ft=ft,
        stamina=stamina,

        ovr=final_ovr,
        potential=potential,
        archetype=_build_archetype_by_position(pos),
        usage_base=random.randint(8, 24),
        popularity=pop
    )

    player.salary = calculate_initial_salary(player.ovr)
    _assign_extended_attributes(player, pos, final_ovr)
    player.years_pro = max(0, player.age - 18)
    player.contract_years_left = random.randint(1, 3)

    _initialize_player_meta(player)
    _set_acquisition(player, "normal", "fictional_pool_generation")
    return player


def generate_fictional_player_pool(count: int = 104) -> list[Player]:
    """
    ゲーム開始時の架空選手プールを生成する。
    初期状態ではFAプールとして扱う想定。
    """
    pool = []

    target_positions = (
        ['PG'] * 20 +
        ['SG'] * 20 +
        ['SF'] * 22 +
        ['PF'] * 22 +
        ['C'] * 20
    )

    if count != 104:
        positions = ['PG', 'SG', 'SF', 'PF', 'C']
        while len(target_positions) < count:
            target_positions.append(random.choice(positions))
        target_positions = target_positions[:count]

    random.shuffle(target_positions)

    for pos in target_positions:
        player = generate_fictional_player(position_override=pos)
        pool.append(player)

    return pool


def generate_draft_prospect(
    age_override: int = None,
    base_ovr_override: int = None
) -> Player:
    """
    ドラフト候補専用生成。
    通常選手生成より若手寄り・OVR分布をドラフト向けに調整する。
    """
    age = age_override if age_override is not None else random.randint(18, 22)
    base_ovr = base_ovr_override if base_ovr_override is not None else _get_weighted_draft_ovr()

    player = generate_single_player(
        age_override=age,
        base_ovr_override=base_ovr,
        nationality_override="Japan"
    )

    if player.age <= 20:
        if player.ovr >= 70:
            player.potential = random.choices(['A', 'B', 'C'], weights=[45, 45, 10])[0]
        elif player.ovr >= 62:
            player.potential = random.choices(['A', 'B', 'C', 'D'], weights=[20, 45, 25, 10])[0]
        else:
            player.potential = random.choices(['B', 'C', 'D'], weights=[35, 45, 20])[0]
    else:
        if player.ovr >= 68:
            player.potential = random.choices(['A', 'B', 'C'], weights=[20, 50, 30])[0]
        elif player.ovr >= 60:
            player.potential = random.choices(['B', 'C', 'D'], weights=[30, 50, 20])[0]
        else:
            player.potential = random.choices(['B', 'C', 'D'], weights=[15, 50, 35])[0]

    player.draft_profile_label = "通常新人"
    player.draft_priority_bonus = 0
    player.draft_origin_type = "normal"
    _set_acquisition(player, "draft", "draft_prospect")
    return player


def generate_special_draft_prospect() -> Player:
    """
    目玉新人を生成する。
    通常新人より上振れしやすく、必ずラベルが付く。
    """
    age = random.choice([18, 19, 19, 20])
    pos = random.choice(["PG", "SG", "SF", "PF", "C"])
    base_ovr = _get_special_draft_ovr()

    player = generate_single_player(
        age_override=age,
        base_ovr_override=base_ovr,
        position_override=pos,
        nationality_override="Japan"
    )

    player.potential = _get_special_potential()
    player.popularity = min(90, max(player.popularity, random.randint(60, 76)))
    player.usage_base = max(player.usage_base, random.randint(18, 28))

    profiles = {
        "PG": [
            ("目玉新人 / 将来有望な司令塔", "Floor General"),
            ("目玉新人 / ゲームメイク型PG", "Playmaker"),
        ],
        "SG": [
            ("目玉新人 / 爆発力あるスコアラー", "Scorer"),
            ("目玉新人 / 純正シューター", "Shooter"),
        ],
        "SF": [
            ("目玉新人 / 万能ウイング", "Two-Way Wing"),
            ("目玉新人 / エース候補ウイング", "Wing"),
        ],
        "PF": [
            ("目玉新人 / フィジカルエース候補", "Inside Finisher"),
            ("目玉新人 / ストレッチビッグ", "Stretch Big"),
        ],
        "C": [
            ("目玉新人 / 規格外のビッグマン", "Post Big"),
            ("目玉新人 / 守備職人", "Rim Protector"),
        ],
    }

    label, archetype = random.choice(profiles[pos])
    player.draft_profile_label = label
    player.archetype = archetype
    player.draft_origin_type = "special"

    if player.potential == "S":
        player.ovr = max(player.ovr, 75)
        player.draft_priority_bonus = 12
    elif player.potential == "A":
        player.ovr = max(player.ovr, 74)
        player.draft_priority_bonus = 10
    else:
        player.ovr = max(player.ovr, 72)
        player.draft_priority_bonus = 8

    if pos in ("PG", "SG"):
        player.shoot = min(99, player.shoot + random.randint(1, 3))
        player.three = min(99, player.three + random.randint(1, 4))
        player.passing = min(99, player.passing + random.randint(1, 3))
    elif pos == "SF":
        player.shoot = min(99, player.shoot + random.randint(1, 3))
        player.defense = min(99, player.defense + random.randint(1, 3))
        player.drive = min(99, player.drive + random.randint(1, 3))
    elif pos == "PF":
        player.rebound = min(99, player.rebound + random.randint(1, 3))
        player.defense = min(99, player.defense + random.randint(1, 3))
        player.three = min(99, player.three + random.randint(0, 3))
    elif pos == "C":
        player.rebound = min(99, player.rebound + random.randint(2, 4))
        player.defense = min(99, player.defense + random.randint(2, 4))

    _set_acquisition(player, "draft", "special_draft_prospect")
    return player


def generate_international_free_agent(nationality: str, reborn_profile: dict | None = None) -> Player:
    """
    国際市場向けFA生成。
    nationality は Foreign or Asia を想定。
    reborn_profile があれば転生国際選手として作る。
    """
    age = random.randint(22, 29)

    if reborn_profile is not None:
        pos = reborn_profile.get("position", random.choice(["PG", "SG", "SF", "PF", "C"]))
        base_ovr = reborn_profile.get("target_ovr", _get_international_market_ovr(nationality))
        player = generate_single_player(
            age_override=age,
            base_ovr_override=base_ovr,
            position_override=pos,
            nationality_override=nationality,
            height_override=reborn_profile.get("height_cm"),
            weight_override=reborn_profile.get("weight_kg"),
        )
        player.archetype = reborn_profile.get("archetype", player.archetype)
        player.naturalize_bonus_chance = reborn_profile.get("naturalize_bonus_chance", 0.0)
        player.reborn_type = "international_reborn"
        player.is_reborn = True
        player.is_international_reborn = True
        player.draft_origin_type = "international"
        player.draft_profile_label = "国際転生FA"
        _set_acquisition(player, "international", "international_reborn_market")
    else:
        base_ovr = _get_international_market_ovr(nationality)
        player = generate_single_player(
            age_override=age,
            base_ovr_override=base_ovr,
            nationality_override=nationality
        )
        player.naturalize_bonus_chance = 0.0
        player.draft_profile_label = "国際FA"
        player.draft_priority_bonus = 0
        player.draft_origin_type = "international"
        _set_acquisition(player, "international", "international_market")

    player.contract_years_left = random.randint(1, 2)
    player.salary = calculate_initial_salary(player.ovr)
    player.league_years = 0

    if nationality == "Asia":
        player.was_naturalized = False
    else:
        player.was_naturalized = getattr(player, "was_naturalized", False)

    return player


def generate_teams() -> list[Team]:
    """
    48チームを生成し、それぞれに13人の選手（ロスター）を配置して返します。
    48チームは、16チーム×3リーグ (league_level: 1, 2, 3) に分割して生成されます。
    """
    teams = []

    base_cities = ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo", "Sendai", "Kyoto", "Yokohama"]
    city_pool = []
    for city in base_cities:
        for _ in range(6):
            city_pool.append(city)
    random.shuffle(city_pool)

    mascots = ["Wolves", "Kings", "Mariners", "Eagles", "Lions", "Dragons", "Bulls", "Bears"]

    market_size_map = {
        "Tokyo": 1.15,
        "Osaka": 1.15,
        "Yokohama": 1.15,
        "Nagoya": 1.00,
        "Fukuoka": 1.00,
        "Sapporo": 1.00,
        "Kyoto": 1.00,
        "Sendai": 0.90
    }

    print("Generating 48 teams (3 Leagues x 16 Teams)...")

    team_id_counter = 1
    for level in range(1, 4):
        for _ in range(16):
            city = city_pool.pop()
            mascot = random.choice(mascots)
            name = f"{city} {mascot}_{team_id_counter}"

            market_size = market_size_map.get(city, 1.0)

            team = Team(
                team_id=team_id_counter,
                name=name,
                league_level=level,
                strategy=_get_team_strategy(),
                coach_style=_get_coach_style(),
                popularity=random.randint(40, 60),
                market_size=market_size
            )

            # 本契約13枠の国籍スロットを先に決めてから生成する。
            # 日本ルール: Foreign 3 / Asia-or-Naturalized 1 / Domestic 9
            nationality_slots = ["Foreign", "Foreign", "Foreign"]
            nationality_slots.append(random.choice(["Asia", "Naturalized"]))
            nationality_slots.extend(["Japan"] * 9)
            random.shuffle(nationality_slots)

            for nat in nationality_slots:
                p = generate_single_player(nationality_override=nat)
                p.years_pro = max(0, p.age - 18)
                p.contract_years_left = random.randint(2, 4)
                p.league_years = p.years_pro
                p.was_naturalized = p.nationality == "Naturalized"
                _set_acquisition(p, "normal", "initial_team_roster")
                team.add_player(p)

            target_pay = _initial_roster_target_team_payroll(team.league_level)
            _rebalance_team_initial_salaries_to_target(team.players, target_pay)

            teams.append(team)
            team_id_counter += 1

    return teams