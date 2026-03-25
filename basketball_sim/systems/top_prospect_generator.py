import random
from typing import List, Dict, Any, Optional

from basketball_sim.models.player import Player


TOP_PROSPECT_MIN = 6
TOP_PROSPECT_MAX = 10


def generate_top_prospect_count() -> int:
    """
    その年のTop Prospect人数を決定する。
    6〜10人の可変。
    """
    return random.randint(TOP_PROSPECT_MIN, TOP_PROSPECT_MAX)


def generate_reincarnation_count() -> int:
    """
    転生スター人数。
    最大2人。
    """
    return random.randint(0, 2)


def generate_homage_count() -> int:
    """
    オマージュ目玉新人。
    最大2人。
    """
    return random.randint(0, 2)


def calculate_rookie_ovr_from_peak(peak_ovr: int, entry_type: str) -> int:
    """
    転生時OVR計算。
    peak_ovr を基準に入団経路で補正する。
    """
    base = peak_ovr * 0.82

    if entry_type == "highschool":
        base -= 3
    elif entry_type == "overseas":
        base += 2

    base += random.randint(-1, 1)
    return int(base)


def generate_entry_type() -> str:
    """
    転生入団タイプ。
    """
    r = random.random()

    if r < 0.45:
        return "highschool"
    if r < 0.85:
        return "college"
    return "overseas"


def generate_entry_age(entry_type: str) -> int:
    """
    入団年齢。
    """
    if entry_type == "highschool":
        return 18
    if entry_type == "college":
        return random.randint(21, 22)
    return random.randint(23, 24)


def _normalize_potential(value: str) -> str:
    value = str(value).upper()
    if value in {"S", "A", "B", "C", "D"}:
        return value
    return "C"


def _potential_bonus(value: str) -> float:
    value = _normalize_potential(value)
    bonus_map = {
        "S": 6.0,
        "A": 4.0,
        "B": 2.0,
        "C": 0.0,
        "D": -1.0,
    }
    return bonus_map.get(value, 0.0)


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
    if getattr(player, "draft_origin_type", "") == "special":
        return 5.0
    if getattr(player, "is_featured_prospect", False):
        return 5.0
    if getattr(player, "reborn_type", "") == "special":
        return 5.0
    return 0.0


def _reborn_bonus(player: Player) -> float:
    if getattr(player, "is_reborn", False):
        return 3.0
    if getattr(player, "reborn_type", "") in ("jp", "japanese_reborn"):
        return 3.0
    return 0.0


def calculate_top_prospect_score(player: Player) -> float:
    """
    Top Prospect内部スコア。
    OVR主軸 + potential + age + featured + reborn + 微小ランダム
    """
    ovr = float(getattr(player, "ovr", 0))
    potential = _normalize_potential(getattr(player, "potential", "C"))
    age = int(getattr(player, "age", 20))

    score = ovr
    score += _potential_bonus(potential)
    score += _age_bonus(age)
    score += _featured_bonus(player)
    score += _reborn_bonus(player)
    score += random.uniform(-0.5, 0.5)

    return round(score, 2)


def _determine_buzz_tier(rank: int) -> str:
    if rank <= 3:
        return "elite"
    if rank <= 6:
        return "notable"
    return "watchlist"


def _get_player_prospect_type(player: Player) -> str:
    if getattr(player, "is_reborn", False) or getattr(player, "reborn_type", "") in ("jp", "japanese_reborn"):
        return "reincarnation"

    if getattr(player, "draft_origin_type", "") == "special":
        return "homage"

    if getattr(player, "is_featured_prospect", False):
        return "homage"

    if getattr(player, "reborn_type", "") == "special":
        return "homage"

    return "generic"


def clear_top_prospect_flags(players: List[Player]) -> None:
    """
    前年データが残っていても事故らないように、関連属性を初期化する。
    """
    for player in players:
        player.is_top_prospect = False
        player.top_prospect_rank = None
        player.top_prospect_score = 0.0
        player.prospect_type = _get_player_prospect_type(player)
        player.draft_buzz_tier = None


def mark_top_prospects(draft_pool: List[Player]) -> List[Player]:
    """
    draft_pool から Top Prospect を正式抽出し、
    Player 側へ属性を付与する。

    付与属性:
    - is_top_prospect
    - top_prospect_rank
    - top_prospect_score
    - prospect_type
    - draft_buzz_tier
    """
    if not draft_pool:
        return []

    clear_top_prospect_flags(draft_pool)

    scored_rows = []
    for player in draft_pool:
        score = calculate_top_prospect_score(player)
        scored_rows.append((player, score))

    scored_rows.sort(
        key=lambda row: (
            row[1],
            getattr(row[0], "ovr", 0),
            getattr(row[0], "potential", "C"),
        ),
        reverse=True,
    )

    top_count = min(generate_top_prospect_count(), len(scored_rows))
    selected = []

    for rank, (player, score) in enumerate(scored_rows[:top_count], 1):
        player.is_top_prospect = True
        player.top_prospect_rank = rank
        player.top_prospect_score = score
        player.prospect_type = _get_player_prospect_type(player)
        player.draft_buzz_tier = _determine_buzz_tier(rank)
        selected.append(player)

    return selected


def build_top_prospect_snapshot(players: List[Player]) -> List[Dict[str, Any]]:
    """
    UIやオフシーズン側で保持しやすいようにスナップショットを作る。
    """
    snapshot = []

    ranked = sorted(
        [p for p in players if getattr(p, "is_top_prospect", False)],
        key=lambda p: (
            getattr(p, "top_prospect_rank", 999),
            -getattr(p, "top_prospect_score", 0.0),
        ),
    )

    for player in ranked:
        snapshot.append({
            "player_id": getattr(player, "player_id", None),
            "name": getattr(player, "name", "Unknown"),
            "position": getattr(player, "position", "SF"),
            "age": getattr(player, "age", 0),
            "ovr": getattr(player, "ovr", 0),
            "potential": getattr(player, "potential", "C"),
            "rank": getattr(player, "top_prospect_rank", None),
            "score": getattr(player, "top_prospect_score", 0.0),
            "prospect_type": getattr(player, "prospect_type", "generic"),
            "buzz_tier": getattr(player, "draft_buzz_tier", None),
            "label": getattr(player, "draft_profile_label", ""),
            "reborn_from": getattr(player, "reborn_from", None),
        })

    return snapshot


def build_prospect_profile(player: Player, peak_ovr: int) -> Dict[str, Any]:
    """
    旧土台互換用。
    転生スター生成のベース情報だけ返す。
    """
    entry_type = generate_entry_type()
    age = generate_entry_age(entry_type)

    rookie_ovr = calculate_rookie_ovr_from_peak(
        peak_ovr=peak_ovr,
        entry_type=entry_type,
    )

    return {
        "type": "reincarnation",
        "origin_player_id": getattr(player, "player_id", None),
        "entry_type": entry_type,
        "age": age,
        "ovr": rookie_ovr,
        "potential": random.choice(["A", "S"]),
    }


def generate_homage_prospect() -> Dict[str, Any]:
    """
    旧土台互換用。
    """
    archetypes = [
        "Sniper",
        "Floor General",
        "Defensive Monster",
        "Athletic Freak",
        "Point Forward",
        "Stretch Big",
    ]

    return {
        "type": "homage",
        "archetype": random.choice(archetypes),
        "age": random.randint(19, 22),
        "ovr": random.randint(70, 75),
        "potential": random.choice(["A", "S"]),
    }


def generate_generic_prospect() -> Dict[str, Any]:
    """
    旧土台互換用。
    """
    return {
        "type": "generic",
        "age": random.randint(19, 22),
        "ovr": random.randint(65, 72),
        "potential": random.choice(["A", "B"]),
    }


def generate_top_prospects(retired_players: List[Player]) -> List[Dict[str, Any]]:
    """
    旧土台互換用。
    将来の再利用のため残しておく。
    """
    prospects: List[Dict[str, Any]] = []

    total_count = generate_top_prospect_count()
    reinc_count = min(generate_reincarnation_count(), len(retired_players))
    homage_count = generate_homage_count()

    reinc_candidates = [
        p for p in retired_players
        if getattr(p, "peak_ovr", 0) >= 82
    ]
    random.shuffle(reinc_candidates)

    for player in reinc_candidates[:reinc_count]:
        prospects.append(
            build_prospect_profile(
                player=player,
                peak_ovr=getattr(player, "peak_ovr", 80),
            )
        )

    for _ in range(homage_count):
        prospects.append(generate_homage_prospect())

    while len(prospects) < total_count:
        prospects.append(generate_generic_prospect())

    random.shuffle(prospects)
    return prospects
