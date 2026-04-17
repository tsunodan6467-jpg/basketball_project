"""
開幕ロスター年俸 — 経済スケール正本 v1.1 寄せ（generate_teams 専用）。

FA / 再契約 / ドラフトとは独立。テンプレ＋微調整＋±5% 以内の誤差吸収のみ。
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Literal, Sequence, Tuple

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team

NatSlot = Literal["Foreign", "Japan", "X"]  # X = Asia または Naturalized の1枠
Rank = Literal["top", "middle", "bottom"]

# D1: 100 万円未満禁止
_MIN_SALARY_D1 = 1_000_000
_MIN_SALARY_D2_D3 = 500_000

# 若手の異常高額抑制（年齢 <= 20）
_YOUNG_MAX_SALARY_BY_DIV = {1: 55_000_000, 2: 28_000_000, 3: 18_000_000}

# (division, nat_for_band, rank) -> (low, high) 円。nat_for_band は Asia / Naturalized 別表。
_BANDS: Dict[Tuple[int, str, Rank], Tuple[int, int]] = {
    # D1 外国籍
    (1, "foreign", "top"): (175_000_000, 225_000_000),
    (1, "foreign", "middle"): (105_000_000, 135_000_000),
    (1, "foreign", "bottom"): (70_000_000, 92_000_000),
    # D1 帰化
    (1, "naturalized", "top"): (220_000_000, 275_000_000),
    (1, "naturalized", "middle"): (155_000_000, 185_000_000),
    (1, "naturalized", "bottom"): (110_000_000, 132_000_000),
    # D1 アジア
    (1, "asia", "top"): (88_000_000, 112_000_000),
    (1, "asia", "middle"): (70_000_000, 92_000_000),
    (1, "asia", "bottom"): (42_000_000, 58_000_000),
    # D1 日本人
    (1, "japan", "top"): (130_000_000, 165_000_000),
    (1, "japan", "middle"): (70_000_000, 92_000_000),
    (1, "japan", "bottom"): (34_000_000, 48_000_000),
    # D2
    (2, "foreign", "top"): (88_000_000, 112_000_000),
    (2, "foreign", "middle"): (52_000_000, 68_000_000),
    (2, "foreign", "bottom"): (34_000_000, 46_000_000),
    (2, "naturalized", "top"): (110_000_000, 138_000_000),
    (2, "naturalized", "middle"): (75_000_000, 95_000_000),
    (2, "naturalized", "bottom"): (52_000_000, 68_000_000),
    (2, "asia", "top"): (44_000_000, 56_000_000),
    (2, "asia", "middle"): (34_000_000, 46_000_000),
    (2, "asia", "bottom"): (20_000_000, 30_000_000),
    (2, "japan", "top"): (65_000_000, 85_000_000),
    (2, "japan", "middle"): (34_000_000, 46_000_000),
    (2, "japan", "bottom"): (16_000_000, 24_000_000),
    # D3 — 5〜6 億 tier の target 到達のため上限を抑えめに拡張（下限は据え置き）
    (3, "foreign", "top"): (44_000_000, 72_000_000),
    (3, "foreign", "middle"): (26_000_000, 46_000_000),
    (3, "foreign", "bottom"): (17_000_000, 32_000_000),
    (3, "naturalized", "top"): (55_000_000, 82_000_000),
    (3, "naturalized", "middle"): (38_000_000, 58_000_000),
    (3, "naturalized", "bottom"): (27_000_000, 44_000_000),
    (3, "asia", "top"): (22_000_000, 34_000_000),
    (3, "asia", "middle"): (17_000_000, 30_000_000),
    (3, "asia", "bottom"): (10_000_000, 22_000_000),
    (3, "japan", "top"): (32_000_000, 56_000_000),
    (3, "japan", "middle"): (17_000_000, 38_000_000),
    (3, "japan", "bottom"): (8_000_000, 32_000_000),
}

_RANK_ORDER = {"top": 0, "middle": 1, "bottom": 2}


def _rebalance_priority_add(band_key: str, rank: Rank) -> int:
    """円を足す順: 外国籍 top→帰化 top→アジア top→日本人 top→各 middle→各 bottom。"""
    ro = _RANK_ORDER[rank]
    bk = (band_key or "japan").lower()
    if bk == "foreign":
        off = 0
    elif bk == "naturalized":
        off = 1
    elif bk == "asia":
        off = 2
    else:
        off = 3
    return ro * 4 + off


# (division, team_payroll_tier) -> 13 スロット (NatSlot, rank)。X はアジア/帰化の1人に割当。
_TEMPLATES: Dict[Tuple[int, str], List[Tuple[NatSlot, Rank]]] = {
    (1, "top"): [
        ("Foreign", "top"),
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("X", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (1, "middle"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "middle"),
        ("X", "middle"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (1, "bottom"): [
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("Foreign", "bottom"),
        ("X", "middle"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (2, "top"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("X", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (2, "middle"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "middle"),
        ("X", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (2, "bottom"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("X", "bottom"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (3, "top"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("X", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (3, "middle"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("X", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
    (3, "bottom"): [
        ("Foreign", "top"),
        ("Foreign", "middle"),
        ("Foreign", "bottom"),
        ("X", "middle"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "top"),
        ("Japan", "middle"),
        ("Japan", "middle"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
        ("Japan", "bottom"),
    ],
}


def payroll_tier_labels_for_division(*, first_team_must_be_bottom: bool) -> List[str]:
    """16 チーム分: top 4 / middle 8 / bottom 4。D3 の先頭チームは必ず bottom。"""
    labels = ["top"] * 4 + ["middle"] * 8 + ["bottom"] * 4
    if first_team_must_be_bottom:
        labels.remove("bottom")
        random.shuffle(labels)
        return ["bottom"] + labels
    random.shuffle(labels)
    return labels


def roll_target_team_payroll(league_level: int, payroll_tier: str) -> int:
    lv = max(1, min(3, int(league_level)))
    t = str(payroll_tier).lower()
    if t not in ("top", "middle", "bottom"):
        t = "middle"
    key = (lv, t)
    ranges: Dict[Tuple[int, str], Tuple[int, int]] = {
        (1, "top"): (1_140_000_000, 1_260_000_000),
        (1, "middle"): (950_000_000, 1_050_000_000),
        (1, "bottom"): (760_000_000, 840_000_000),
        (2, "top"): (760_000_000, 840_000_000),
        (2, "middle"): (665_000_000, 735_000_000),
        (2, "bottom"): (570_000_000, 630_000_000),
        (3, "top"): (570_000_000, 630_000_000),
        (3, "middle"): (475_000_000, 525_000_000),
        (3, "bottom"): (380_000_000, 420_000_000),
    }
    lo, hi = ranges[key]
    return random.randint(lo, hi)


def _player_nat_band(player: Player) -> str:
    nat = str(getattr(player, "nationality", "Japan") or "Japan")
    if nat == "Foreign":
        return "foreign"
    if nat == "Naturalized":
        return "naturalized"
    if nat == "Asia":
        return "asia"
    return "japan"


# D2/D3 開幕 13 人の年齢バケット人数 (18-20, 21-23, 24-29, 30-34, 35+)。合計 13。
# top は若手上限厳しめ、bottom も総額が死なないよう中堅厚め。
_OPENING_AGE_BUCKETS_D23: Dict[Tuple[int, str], Tuple[int, int, int, int, int]] = {
    (2, "top"): (2, 3, 5, 2, 1),
    (2, "middle"): (2, 3, 5, 2, 1),
    (2, "bottom"): (2, 3, 4, 3, 1),
    (3, "top"): (1, 3, 5, 3, 1),
    (3, "middle"): (2, 3, 5, 2, 1),
    (3, "bottom"): (2, 3, 5, 2, 1),
}


def _build_opening_roster_ages_d23(div: int, tier: str) -> List[int]:
    key = (div, tier)
    n18, n21, n24, n30, n35 = _OPENING_AGE_BUCKETS_D23[key]
    ages: List[int] = []
    for _ in range(n18):
        ages.append(random.randint(18, 20))
    for _ in range(n21):
        ages.append(random.randint(21, 23))
    for _ in range(n24):
        ages.append(random.randint(24, 29))
    for _ in range(n30):
        ages.append(random.randint(30, 34))
    for _ in range(n35):
        ages.append(random.randint(35, 37))
    return ages


def _opening_age_assign_priority(p: Player) -> Tuple[int, int, int]:
    """高年齢を外国籍→帰化→アジア→日本人の順で寄せ、高額枠と整合しやすくする。"""
    nat = str(getattr(p, "nationality", "") or "")
    if nat == "Foreign":
        g = 0
    elif nat == "Naturalized":
        g = 1
    elif nat == "Asia":
        g = 2
    else:
        g = 3
    return (g, -int(getattr(p, "ovr", 0)), int(getattr(p, "player_id", 0)))


def apply_opening_roster_age_profile_v11(team: Team) -> None:
    """D2/D3 の開幕 13 人だけ年齢を正本寄せのプロファイルに差し替える（D1 は無変更）。"""
    players = list(getattr(team, "players", []) or [])
    if len(players) != 13:
        return
    div = max(1, min(3, int(getattr(team, "league_level", 3))))
    if div not in (2, 3):
        return
    tier = str(getattr(team, "initial_payroll_tier", "middle") or "middle").lower()
    if tier not in ("top", "middle", "bottom"):
        tier = "middle"
    key = (div, tier)
    if key not in _OPENING_AGE_BUCKETS_D23:
        return
    ages = _build_opening_roster_ages_d23(div, tier)
    ages.sort(reverse=True)
    ordered = sorted(players, key=_opening_age_assign_priority)
    for p, a in zip(ordered, ages):
        aa = int(a)
        setattr(p, "age", aa)
        yp = max(0, aa - 18)
        setattr(p, "years_pro", yp)
        if hasattr(p, "league_years"):
            setattr(p, "league_years", yp)


def _band_bounds(division: int, band_key: str, rank: Rank) -> Tuple[int, int]:
    div = max(1, min(3, division))
    bk = band_key.lower()
    if bk == "foreign":
        k = "foreign"
    elif bk == "naturalized":
        k = "naturalized"
    elif bk == "asia":
        k = "asia"
    else:
        k = "japan"
    return _BANDS[(div, k, rank)]


def _ovr_factor(ovr: int) -> float:
    o = max(45, min(95, int(ovr)))
    # 中心 72 → 1.0、±15% まで
    x = (o - 72) / 23.0
    return max(0.85, min(1.15, 1.0 + x * 0.15))


def _age_factor(age: int, division: int) -> float:
    a = int(age)
    if a <= 20:
        return max(0.90, min(1.10, 0.94 + (a - 18) * 0.03))
    if a <= 24:
        return max(0.90, min(1.10, 0.98 + (a - 21) * 0.008))
    if a <= 30:
        return max(0.90, min(1.10, 1.02))
    return max(0.90, min(1.10, 1.04 - (a - 30) * 0.01))


def _pot_factor(potential: str) -> float:
    p = str(potential or "C").upper()
    m = {"S": 1.08, "A": 1.05, "B": 1.02, "C": 1.0, "D": 0.92}
    return max(0.92, min(1.08, m.get(p, 1.0)))


def _assign_ranks_to_players(
    players: Sequence[Player],
    template: Sequence[Tuple[NatSlot, Rank]],
) -> Dict[int, Tuple[str, Rank]]:
    """テンプレの国籍枠と実ロスターを対応づけ、各選手に (band_key, rank) を割当。"""
    foreign = [p for p in players if _player_nat_band(p) == "foreign"]
    japan = [p for p in players if _player_nat_band(p) == "japan"]
    x_players = [p for p in players if _player_nat_band(p) in ("asia", "naturalized")]

    need_f = sum(1 for s, _ in template if s == "Foreign")
    need_j = sum(1 for s, _ in template if s == "Japan")
    need_x = sum(1 for s, _ in template if s == "X")

    if len(foreign) != need_f or len(japan) != need_j or len(x_players) != need_x:
        raise RuntimeError(
            f"opening_roster_salary_v11: roster/template nationality count mismatch "
            f"foreign {len(foreign)}/{need_f} japan {len(japan)}/{need_j} x {len(x_players)}/{need_x}"
        )

    ranks_by_nat: Dict[str, List[Rank]] = defaultdict(list)
    for slot, rk in template:
        if slot == "Foreign":
            ranks_by_nat["foreign"].append(rk)
        elif slot == "Japan":
            ranks_by_nat["japan"].append(rk)
        else:
            ranks_by_nat["x"].append(rk)

    for key in ranks_by_nat:
        ranks_by_nat[key].sort(key=lambda r: _RANK_ORDER[r])

    out: Dict[int, Tuple[str, Rank]] = {}

    def _ovr_pid(p: Player) -> Tuple[int, int]:
        return (-int(getattr(p, "ovr", 0)), int(getattr(p, "player_id", 0)))

    def _consume(target_list: List[Player], nat_key: str, ranks: List[Rank]) -> None:
        rs = sorted(ranks, key=lambda r: _RANK_ORDER[r])
        adults = [p for p in target_list if int(getattr(p, "age", 99)) > 20]
        youths = [p for p in target_list if int(getattr(p, "age", 99)) <= 20]
        adults.sort(key=_ovr_pid)
        youths.sort(key=_ovr_pid)
        if len(adults) + len(youths) != len(rs):
            raise RuntimeError(
                "opening_roster_salary_v11: internal rank count mismatch "
                f"{nat_key} adults {len(adults)} youths {len(youths)} ranks {len(rs)}"
            )
        adult_ranks = rs[: len(adults)]
        youth_ranks = sorted(rs[len(adults) :], key=lambda r: -_RANK_ORDER[r])
        for p, rk in zip(adults, adult_ranks):
            if nat_key == "x":
                bk = _player_nat_band(p)
            elif nat_key == "foreign":
                bk = "foreign"
            else:
                bk = "japan"
            out[int(getattr(p, "player_id", 0))] = (bk, rk)
        for p, rk in zip(youths, youth_ranks):
            if nat_key == "x":
                bk = _player_nat_band(p)
            elif nat_key == "foreign":
                bk = "foreign"
            else:
                bk = "japan"
            out[int(getattr(p, "player_id", 0))] = (bk, rk)

    _consume(foreign, "foreign", ranks_by_nat["foreign"])
    _consume(japan, "japan", ranks_by_nat["japan"])
    _consume(x_players, "x", ranks_by_nat["x"])
    return out


def _salary_from_share(
    division: int,
    band_key: str,
    rank: Rank,
    player: Player,
    share_yen: float,
) -> Tuple[int, int, int]:
    """target 按分額 share に OVR/年齢/POT を乗せ、帯内に収める。戻り: (salary, lo, hi)。

    若手（<=20）では rank 帯下限より若手 cap を優先: cap 未満に収まらない帯下限は捨て、
    実効 (lo, hi) は _gentle_rebalance の再配分上限としてそのまま使う。
    """
    lo, hi = _band_bounds(division, band_key, rank)
    div = max(1, min(3, division))
    floor_m = _MIN_SALARY_D1 if div == 1 else _MIN_SALARY_D2_D3
    lo = max(lo, floor_m)
    if int(getattr(player, "age", 99)) <= 20:
        cap_y = _YOUNG_MAX_SALARY_BY_DIV.get(div, hi)
        hi = min(hi, cap_y)
        if lo > hi:
            lo = floor_m
    ovr_f = _ovr_factor(int(getattr(player, "ovr", 70)))
    age_f = _age_factor(int(getattr(player, "age", 25)), division)
    pot_f = _pot_factor(str(getattr(player, "potential", "C")))
    raw = int(round(float(share_yen) * ovr_f * age_f * pot_f))
    sal = max(lo, min(hi, raw))
    return sal, lo, hi


def _gentle_rebalance(
    players: List[Player],
    bounds: Dict[int, Tuple[int, int]],
    target_total: int,
    *,
    division: int,
    assign_by_pid: Dict[int, Tuple[str, Rank]] | None = None,
) -> None:
    """±5% 窓と rank 帯の交差内でスケールし、残差は帯内で数円単位で吸収。

    assign_by_pid があるとき、残差の + は外国籍・帰化の上位枠を優先、- は日本人下位枠から削る。
    """
    div = max(1, min(3, division))
    floor_m = _MIN_SALARY_D1 if div == 1 else _MIN_SALARY_D2_D3

    def _pid(p: Player) -> int:
        return int(getattr(p, "player_id", 0))

    base = { _pid(p): max(floor_m, int(getattr(p, "salary", 0))) for p in players }

    def _window(pid: int, s: int, *, tight: bool) -> Tuple[int, int]:
        lo_b, hi_b = bounds[pid]
        if tight:
            lo = max(lo_b, floor_m, int(s * 0.95))
            hi = min(hi_b, int(s * 1.05))
            if lo > hi:
                mid = (lo_b + hi_b) // 2
                lo = max(lo_b, floor_m, int(mid * 0.97))
                hi = min(hi_b, int(mid * 1.03))
        else:
            lo = max(lo_b, floor_m)
            hi = hi_b
        return lo, hi

    def _sum_at_scale(factor: float, *, tight: bool) -> Tuple[Dict[int, int], int]:
        cur: Dict[int, int] = {}
        for pid, s in base.items():
            raw = int(round(s * factor))
            lo, hi = _window(pid, s, tight=tight)
            cur[pid] = max(lo, min(hi, raw))
        return cur, sum(cur.values())

    def _fit(*, tight: bool) -> Dict[int, int]:
        lo_f, hi_f = 0.85, 1.15
        cur0, t0 = _sum_at_scale(1.0, tight=tight)
        best_cur, best_diff = cur0.copy(), abs(t0 - target_total)
        for _ in range(28):
            mid = (lo_f + hi_f) / 2.0
            cur, tot = _sum_at_scale(mid, tight=tight)
            diff = tot - target_total
            if abs(diff) < best_diff:
                best_diff = abs(diff)
                best_cur = cur.copy()
            if diff == 0:
                return cur
            if diff < 0:
                lo_f = mid
            else:
                hi_f = mid
        return best_cur

    cur = _fit(tight=True)
    if sum(cur.values()) != target_total:
        cur = _fit(tight=False)

    diff = target_total - sum(cur.values())
    guard = 0
    pids = list(cur.keys())

    def _add_key(pid: int) -> Tuple[int, int, int]:
        if assign_by_pid and pid in assign_by_pid:
            bk, rk = assign_by_pid[pid]
            return (_rebalance_priority_add(bk, rk), -cur[pid], pid)
        return (999, -cur[pid], pid)

    def _sub_key(pid: int) -> Tuple[int, int]:
        if assign_by_pid and pid in assign_by_pid:
            bk, rk = assign_by_pid[pid]
            return (-_rebalance_priority_add(bk, rk), cur[pid])
        return (0, cur[pid])

    while diff != 0 and guard < 10_000:
        guard += 1
        progressed = False
        if diff > 0:
            for pid in sorted(pids, key=_add_key):
                lo, hi = bounds[pid]
                lo = max(lo, floor_m)
                if cur[pid] < hi:
                    cur[pid] += 1
                    diff -= 1
                    progressed = True
                    break
        else:
            for pid in sorted(pids, key=_sub_key):
                lo, hi = bounds[pid]
                lo = max(lo, floor_m)
                if cur[pid] > lo:
                    cur[pid] -= 1
                    diff += 1
                    progressed = True
                    break
        if not progressed:
            break

    for p in players:
        p.salary = int(cur[_pid(p)])


def apply_opening_team_payroll_v11(team: Team, *, target_total: int) -> None:
    """
    開幕 13 人の salary を正本 v1.1 テンプレ＋微調整＋ gentle rebalance で確定。
    team.league_level / team.initial_payroll_tier / team.players を使用。
    """
    players = list(getattr(team, "players", []) or [])
    if len(players) != 13:
        return

    div = max(1, min(3, int(getattr(team, "league_level", 3))))
    tier = str(getattr(team, "initial_payroll_tier", "middle") or "middle").lower()
    if tier not in ("top", "middle", "bottom"):
        tier = "middle"

    template = _TEMPLATES.get((div, tier)) or _TEMPLATES[(div, "middle")]
    assign = _assign_ranks_to_players(players, template)

    weights: List[float] = []
    plist: List[Player] = []
    for p in players:
        pid = int(getattr(p, "player_id", 0))
        bk, rk = assign[pid]
        lo, hi = _band_bounds(div, bk, rk)
        mid = float((lo + hi) / 2)
        if div in (2, 3):
            if bk == "foreign":
                mid *= 1.1
            elif bk == "naturalized":
                mid *= 1.06
            elif bk == "asia":
                mid *= 1.04
        weights.append(mid)
        plist.append(p)
    wsum = sum(weights) or 1.0
    tgt = max(1, int(target_total))

    bounds: Dict[int, Tuple[int, int]] = {}
    for p, w in zip(plist, weights):
        pid = int(getattr(p, "player_id", 0))
        bk, rk = assign[pid]
        share = tgt * (w / wsum)
        sal, lo, hi = _salary_from_share(div, bk, rk, p, share)
        p.salary = sal
        bounds[pid] = (lo, hi)

    sum_lo_b = sum(lo for lo, _ in bounds.values())
    sum_hi_b = sum(hi for _, hi in bounds.values())
    eff_target = max(sum_lo_b, min(int(target_total), sum_hi_b))

    _gentle_rebalance(players, bounds, eff_target, division=div, assign_by_pid=assign)


def _user_stair_player_key(player: Player) -> Tuple[int, int, int]:
    """外国籍→アジア/帰化→日本人、同一帯内は OVR 高い順。"""
    nat = str(getattr(player, "nationality", "") or "")
    if nat == "Foreign":
        g = 2
    elif nat in ("Asia", "Naturalized"):
        g = 1
    else:
        g = 0
    return (g, int(getattr(player, "ovr", 0) or 0), -int(getattr(player, "player_id", 0) or 0))


# D3 ボトム想定の階段（円）。13 人フル。アイコン 0 固定時は非アイコン n 人に上位 n 枠を割当ててスケールする。
_D3_BOTTOM_STAIR_FULL_YEN: Tuple[int, ...] = (
    60_000_000,
    60_000_000,
    40_000_000,
    40_000_000,
    35_000_000,
    35_000_000,
    30_000_000,
    25_000_000,
    20_000_000,
    20_000_000,
    15_000_000,
    10_000_000,
    10_000_000,
)


def _d3_bottom_template_for_n(n: int) -> List[int]:
    """高い順に n 本（13 本から下位を落とすイメージ）。"""
    full = list(_D3_BOTTOM_STAIR_FULL_YEN)
    full.sort(reverse=True)
    if n >= len(full):
        return full[:]
    return full[:n]


def _int_scale_to_target(values: List[int], target: int, floor_m: int) -> List[int]:
    """整数配分で合計が target になるよう調整。"""
    n = len(values)
    if n == 0:
        return []
    s = sum(values) or 1
    tgt = max(floor_m * n, int(target))
    raw = [max(floor_m, int(round(v * tgt / float(s)))) for v in values]
    diff = tgt - sum(raw)
    guard = 0
    while diff != 0 and guard < n * 2000:
        guard += 1
        if diff > 0:
            i = max(range(n), key=lambda k: raw[k])
            raw[i] += 1
            diff -= 1
        else:
            i = max(range(n), key=lambda k: raw[k])
            if raw[i] > floor_m:
                raw[i] -= 1
                diff += 1
            else:
                break
    return raw


def _assign_d3_bottom_staircase_non_icons(players: Sequence[Player], target_total: int) -> None:
    n = len(players)
    if n == 0:
        return
    floor_m = int(_MIN_SALARY_D2_D3)
    base = _d3_bottom_template_for_n(n)
    alloc = _int_scale_to_target(list(base), int(target_total), floor_m)
    ordered_p = sorted(list(players), key=_user_stair_player_key, reverse=True)
    alloc_s = sorted(alloc, reverse=True)
    for p, sal in zip(ordered_p, alloc_s):
        p.salary = int(sal)


def _scale_player_list_to_target(players: Sequence[Player], target_total: int, *, division: int) -> None:
    """非アイコン群のみ、target へ比例配分（最低床付き）。"""
    plist = list(players)
    n = len(plist)
    if n == 0:
        return
    div = max(1, min(3, int(division)))
    fl = int(_MIN_SALARY_D1 if div == 1 else _MIN_SALARY_D2_D3)
    tgt = max(fl * n, int(target_total))
    cur = [max(fl, int(getattr(p, "salary", 0) or 0)) for p in plist]
    tot_cur = sum(cur)
    if tot_cur <= 0:
        base, rem = divmod(tgt, n)
        for i, p in enumerate(plist):
            setattr(p, "salary", max(fl, base + (1 if i < rem else 0)))
        return
    factor = tgt / float(tot_cur)
    newv = [max(fl, int(round(c * factor))) for c in cur]
    diff = tgt - sum(newv)
    guard = 0
    while diff != 0 and guard < n * 2000:
        guard += 1
        if diff > 0:
            idx = max(range(n), key=lambda i: newv[i])
            newv[idx] += 1
            diff -= 1
        else:
            idx = max(range(n), key=lambda i: newv[i])
            if newv[idx] > fl:
                newv[idx] -= 1
                diff += 1
            else:
                break
    for p, s in zip(plist, newv):
        setattr(p, "salary", int(s))


def _finalize_user_opening_balances(team: object, target_total: int, div: int, tier: str) -> None:
    """
    アイコン年俸を必ず 0 にし、非アイコンだけで target_total を満たす。
    D3 bottom は階段テンプレ、それ以外は比例スケール。
    """
    players = list(getattr(team, "players", []) or [])
    for p in players:
        if bool(getattr(p, "is_icon", False)):
            setattr(p, "salary", 0)
    others = [p for p in players if not bool(getattr(p, "is_icon", False))]
    if not others:
        return
    fl = int(_MIN_SALARY_D1 if div == 1 else _MIN_SALARY_D2_D3)
    tgt = max(fl * len(others), int(target_total))
    if div == 3 and tier == "bottom":
        _assign_d3_bottom_staircase_non_icons(others, tgt)
    else:
        _scale_player_list_to_target(others, tgt, division=div)
    for p in players:
        if bool(getattr(p, "is_icon", False)):
            setattr(p, "salary", 0)


def apply_user_team_opening_payroll_v11_if_roster_complete(team: object) -> bool:
    """
    ユーザー編成済みの13人ロスターに開幕総年俸を適用する。

    1) 正本 apply_opening_team_payroll_v11 を試す（国籍一致時のみ有効な配分）。
    2) 続けてアイコン 0 円固定のうえ、非アイコンで target を満たす最終配分を行う
       （D3 bottom は階段テンプレ、他は比例）。
    """
    players = list(getattr(team, "players", []) or [])
    if len(players) != 13:
        return False
    div = max(1, min(3, int(getattr(team, "league_level", 3))))
    tier = str(getattr(team, "initial_payroll_tier", "middle") or "middle").lower()
    if tier not in ("top", "middle", "bottom"):
        tier = "middle"
    tgt = roll_target_team_payroll(div, tier)
    try:
        apply_opening_team_payroll_v11(team, target_total=tgt)  # type: ignore[arg-type]
    except Exception:
        pass
    try:
        _finalize_user_opening_balances(team, tgt, div, tier)
        return True
    except Exception:
        return False
