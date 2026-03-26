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


def generate_legend_rookie_count() -> int:
    """
    現実で引退している選手“風”のレジェンドルーキー。
    毎年必ず出すのではなく、たまに混ざる前提（基本は 0 か 1）。
    他の出自（転生/オマージュ）にも SS級が入り得るため、ここは「年に一人出るか出ないか」寄りに抑える。
    """
    r = random.random()
    return 1 if r < 0.42 else 0


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


def generate_legend_rookie_prospect() -> Dict[str, Any]:
    """
    現実引退選手“風”の新人（実名ではなく別名）。
    権利回避のため、再現ではなく「それっぽいアーキタイプ」を持つ。
    """
    # 第一次案（20人サンプルリスト）
    templates = [
        {"name": "森尾 玲司", "position": "SG", "archetype": "Sniper", "market_grade": "SS"},
        {"name": "佐戸 恒一", "position": "PG", "archetype": "Floor General", "market_grade": "SS"},
        {"name": "桜野 RJ", "position": "C", "archetype": "Rim Protector", "market_grade": "SS"},
        {"name": "ノック・マジークス", "position": "PF", "archetype": "Stretch Big", "market_grade": "SS"},
        {"name": "柏森 真司", "position": "PG", "archetype": "Floor General", "market_grade": "S"},
        {"name": "桜庭 恒一", "position": "SF", "archetype": "Two-Way Wing", "market_grade": "S"},
        {"name": "大川 敦司", "position": "C", "archetype": "Rim Protector", "market_grade": "S"},
        {"name": "木里 博人", "position": "SG", "archetype": "Scorer", "market_grade": "A"},
        {"name": "石原 司", "position": "PG", "archetype": "Defensive Guard", "market_grade": "A"},
        {"name": "岡寺 直人", "position": "SG", "archetype": "Sniper", "market_grade": "A"},
        {"name": "正上 隼人", "position": "PG", "archetype": "Playmaker", "market_grade": "A"},
        {"name": "青峰 文史", "position": "C", "archetype": "Post Big", "market_grade": "A"},
        {"name": "網代 友成", "position": "SF", "archetype": "Point Forward", "market_grade": "A"},
        {"name": "竹崎 賢吾", "position": "SF", "archetype": "3&D", "market_grade": "A"},
        {"name": "栗崎 貴洋", "position": "SF", "archetype": "Wing Scorer", "market_grade": "A"},
        {"name": "山路 大誠", "position": "PF", "archetype": "Post Big", "market_grade": "A"},
        {"name": "長谷寺 誠司", "position": "PG", "archetype": "Attacking PG", "market_grade": "S"},
        {"name": "北嶋 卓真", "position": "SG", "archetype": "Sniper", "market_grade": "A"},
        {"name": "節間 貴弘", "position": "PG", "archetype": "Floor General", "market_grade": "A"},
        {"name": "小野寺 秀三", "position": "PF", "archetype": "Glue Guy", "market_grade": "A"},
    ]

    # 同年に2人出る時は「役割がかぶり過ぎない」を優先するため、
    # 呼び出し側で used_names/used_archetypes を持てるが、ここは単体生成なので
    # まずは候補の偏りを避けるために軽いシャッフルのみ行う。
    # この時点の market_grade は「候補の格（ヒント）」として扱い、
    # 最終的な SS/S の確定は generate_top_prospects 側で「SS最大2」ルールにより決める。
    weights = []
    for row in templates:
        g = str(row.get("market_grade", "A") or "A").upper()
        if g == "SS":
            weights.append(0.8)
        elif g == "S":
            weights.append(1.0)
        else:
            weights.append(1.0)
    t = random.choices(templates, weights=weights, k=1)[0]
    return {
        "type": "legend_rookie",
        "name": t["name"],
        "archetype": t["archetype"],
        "position": t["position"],
        "market_grade_hint": str(t.get("market_grade", "A") or "A").upper(),
        "age": random.choice([20, 21, 22]),
        "ovr": random.randint(70, 76) if t.get("market_grade") in ("SS", "S") else random.randint(68, 74),
        "potential": random.choice(["S", "A"]) if t.get("market_grade") in ("SS", "S") else random.choice(["A", "B"]),
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
    legend_count = generate_legend_rookie_count()

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

    # 同年に2人出る場合、できるだけ役割（archetype/position）の被りを避ける
    used_keys = set()
    for _ in range(legend_count):
        for _retry in range(12):
            p = generate_legend_rookie_prospect()
            key = (p.get("archetype"), p.get("position"))
            if legend_count >= 2 and key in used_keys:
                continue
            used_keys.add(key)
            prospects.append(p)
            break

    while len(prospects) < total_count:
        prospects.append(generate_generic_prospect())

    # -------------------------
    # 市場評価（SS/S）を最終確定
    # 仕様: その年のプロスペクト（6〜10人）は SS/S のみ。SSは最大2。
    # 当たり年・外れ年の揺らぎとして、SS人数は 0〜2 で変動する。
    # -------------------------
    ss_target = random.choices([0, 1, 2], weights=[55, 35, 10], k=1)[0]

    # まず全員 S 扱いにする（A等はこの枠では使わない）
    for p in prospects:
        p["market_grade"] = "S"

    # SS候補の重み（出自で少し偏りを作る）
    def ss_weight(p: Dict[str, Any]) -> float:
        t = str(p.get("type", "generic") or "generic")
        hint = str(p.get("market_grade_hint", "A") or "A").upper()
        if t == "legend_rookie":
            return 2.2 if hint == "SS" else 1.4 if hint == "S" else 1.0
        if t == "reincarnation":
            return 1.8
        if t == "homage":
            return 1.6
        return 1.0

    ss_candidates = prospects[:]
    if ss_target > 0 and ss_candidates:
        chosen = []
        working = ss_candidates[:]
        for _ in range(min(2, ss_target)):
            weights = [ss_weight(p) for p in working]
            pick = random.choices(working, weights=weights, k=1)[0]
            chosen.append(pick)
            working.remove(pick)
            if not working:
                break
        for p in chosen:
            p["market_grade"] = "SS"

    random.shuffle(prospects)
    return prospects
