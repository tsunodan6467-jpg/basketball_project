"""
再契約希望年俸用 anchor band（正本 v1.1 寄せ）およびオフ CPU 本格 FA 用の芯計算。

開幕ロスター `opening_roster_salary_v11` の帯・若手上限を単一ソースとして参照する。
- 再契約: `calculate_desired_salary` の生値を帯内へ収める。
- 本格 FA: `fa_offer_base_salary` で帯＋FA プレミアムを芯とし save salary を補助ブレンド。
"""

from __future__ import annotations

from typing import Dict, Literal, Tuple

from basketball_sim.systems.contract_logic import (
    contract_min_salary_floor_for_division,
    contract_min_salary_floor_for_team,
)
from basketball_sim.systems.opening_roster_salary_v11 import (
    _BANDS,
    _YOUNG_MAX_SALARY_BY_DIV,
    _player_nat_band,
)


def clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, int(value)))


def safe_getattr_int(obj: object, attr_name: str, default: int = 0) -> int:
    try:
        return int(getattr(obj, attr_name, default))
    except Exception:
        return int(default)

Rank = Literal["top", "middle", "bottom"]


def infer_resign_role_band(team: object, player: object) -> Rank:
    """チーム内 OVR 順で top(上位5) / middle(次4) / bottom(残り)。最小ルール。"""
    roster = sorted(
        (p for p in getattr(team, "players", []) or [] if p is not None),
        key=lambda p: safe_getattr_int(p, "ovr", 0),
        reverse=True,
    )
    pid = getattr(player, "player_id", None)
    for i, p in enumerate(roster):
        if getattr(p, "player_id", None) == pid:
            if i < 5:
                return "top"
            if i < 9:
                return "middle"
            return "bottom"
    return "middle"


def resign_nat_band_key(player: object) -> str:
    """opening v11 と同一の国籍キー: foreign / naturalized / asia / japan。"""
    return str(_player_nat_band(player))


def effective_resign_anchor_hi(division: int, nat_key: str, rank: Rank, age: int) -> int:
    """若手抑制: 18–20 は top 上限に届かず、21–23 は middle 寄りの上端。"""
    _, hi = _BANDS[(division, nat_key, rank)]
    _, mid_hi = _BANDS[(division, nat_key, "middle")]
    _, top_hi = _BANDS[(division, nat_key, "top")]
    if age <= 20:
        young_cap = int(_YOUNG_MAX_SALARY_BY_DIV.get(division, hi))
        return min(hi, young_cap, mid_hi)
    if age <= 23:
        span = max(0, min(hi, top_hi) - mid_hi)
        cap = int(mid_hi + span * 0.45)
        return min(hi, cap)
    return hi


def resign_anchor_lo_hi_effective(
    division: int, nat_key: str, rank: Rank, age: int
) -> Tuple[int, int]:
    """
    帯 (lo, hi) と若手上限を突き合わせ、(eff_lo, eff_hi) で eff_lo <= eff_hi となるよう調整。
    若手で hi が帯下限より小さくなる場合は下限を引き下げる。
    """
    lo, hi = _BANDS[(division, nat_key, rank)]
    floor = int(contract_min_salary_floor_for_division(int(division)))
    eff_hi = effective_resign_anchor_hi(division, nat_key, rank, age)
    eff_lo = max(int(floor), int(lo))
    if eff_lo <= eff_hi:
        return eff_lo, eff_hi
    mid_lo, _mid_hi = _BANDS[(division, nat_key, "middle")]
    bot_lo, _bot_hi = _BANDS[(division, nat_key, "bottom")]
    eff_lo = max(int(floor), min(int(mid_lo), eff_hi))
    if eff_lo > eff_hi:
        eff_lo = max(int(floor), min(int(bot_lo), eff_hi))
    if eff_lo > eff_hi:
        eff_lo = max(int(floor), eff_hi)
    return eff_lo, eff_hi


def get_resign_anchor_band(player: object, team: object) -> Tuple[int, int, int]:
    """
    (anchor_min_effective, anchor_mid, anchor_max_effective) を円で返す。
    若手で帯下限が上限を超える場合は anchor_min を引き下げる。
    """
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_resign_role_band(team, player)
    age = safe_getattr_int(player, "age", 22)
    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    mid = (eff_lo + eff_hi) // 2
    return eff_lo, mid, eff_hi


def resign_anchor_debug(player: object, team: object, raw_desired: int) -> Dict[str, object]:
    """テスト・実測表示用。raw_desired は `calculate_desired_salary(player)` を渡す。"""
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_resign_role_band(team, player)
    lo, mid, eff_hi = get_resign_anchor_band(player, team)
    blended = blend_desired_salary_for_resign(player, team, int(raw_desired))
    return {
        "division": div,
        "nationality_band": nat,
        "role_band": rank,
        "age": safe_getattr_int(player, "age", 22),
        "ovr": safe_getattr_int(player, "ovr", 60),
        "prev_salary": safe_getattr_int(player, "salary", 0),
        "raw_desired": int(raw_desired),
        "blended_desired": blended,
        "anchor_lo": lo,
        "anchor_mid": mid,
        "anchor_hi_effective": eff_hi,
    }


def blend_desired_salary_for_resign(player: object, team: object, raw_desired: int) -> int:
    """
    現行 `calculate_desired_salary` の結果 raw_desired を、正本 v1.1 帯へ clamp したうえで
    anchor_mid・前年 salary と軽くブレンドする（最小差分）。
    """
    raw = int(raw_desired)
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_resign_role_band(team, player)
    age = safe_getattr_int(player, "age", 22)

    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    floor = int(contract_min_salary_floor_for_team(team))

    anchor_mid = (eff_lo + eff_hi) // 2
    clamped = clamp_int(raw, eff_lo, eff_hi)

    prev = safe_getattr_int(player, "salary", 0)
    if prev > 0 and eff_lo * 0.85 <= prev <= eff_hi * 1.12:
        blended = int(0.42 * anchor_mid + 0.28 * prev + 0.30 * clamped)
    elif prev > eff_hi * 1.35 or (prev > 0 and prev < eff_lo * 0.65):
        blended = clamped
    else:
        blended = int(0.58 * clamped + 0.42 * anchor_mid)

    blended = clamp_int(blended, eff_lo, eff_hi)

    if prev > 0:
        max_up = max(8_000_000, int(prev * 0.18))
        max_dn = max(10_000_000, int(prev * 0.22))
        blended = clamp_int(blended, prev - max_dn, prev + max_up)
        blended = clamp_int(blended, eff_lo, eff_hi)

    return max(int(floor), int(blended))


# -----------------------------
# オフ CPU 本格 FA / FA プール（国際補充）用 — 再契約と同一 _BANDS・若手 eff_hi
# -----------------------------


def infer_fa_role_band_ovr_only(ovr: int) -> Rank:
    """FA 候補がロスター外のときの最小 role 代理（OVR のみ）。"""
    o = int(ovr)
    if o >= 82:
        return "top"
    if o >= 73:
        return "middle"
    return "bottom"


def infer_fa_candidate_role_band(team: object, player: object) -> Rank:
    """
    本格 FA: 候補をチームに加えたときの OVR 順位で role を推定。
    ロスターが薄いテスト・初年度では OVR 代理に落とす（誤って常に top にならないように）。
    """
    cur = [p for p in getattr(team, "players", []) or [] if p is not None]
    if len(cur) >= 11:
        merged = cur + [player]
        roster = sorted(merged, key=lambda p: safe_getattr_int(p, "ovr", 0), reverse=True)
        pid = getattr(player, "player_id", None)
        for i, p in enumerate(roster):
            if getattr(p, "player_id", None) == pid:
                if i < 5:
                    return "top"
                if i < 9:
                    return "middle"
                return "bottom"
    return infer_fa_role_band_ovr_only(safe_getattr_int(player, "ovr", 60))


def fa_market_premium_multiplier(player: object) -> float:
    """再契約 anchor 上に乗せる FA 市場プレミアム（若手・高年齢は抑えめ、外国籍系はわずかに厚め）。"""
    age = safe_getattr_int(player, "age", 25)
    nat = resign_nat_band_key(player)
    m = 1.18
    if age <= 20:
        m = 1.07
    elif age <= 23:
        m = 1.11
    elif age >= 37:
        m = 1.07
    elif age >= 34:
        m = 1.10
    if nat == "foreign":
        m *= 1.028
    elif nat == "naturalized":
        m *= 1.035
    elif nat == "asia":
        m *= 1.012
    return min(1.24, max(1.05, m))


def get_fa_offer_anchor_band(player: object, team: object) -> Tuple[int, int, int]:
    """本格 FA 用の (eff_lo, mid, eff_hi)。role は `infer_fa_candidate_role_band`。"""
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_fa_candidate_role_band(team, player)
    age = safe_getattr_int(player, "age", 25)
    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    mid = (eff_lo + eff_hi) // 2
    return eff_lo, mid, eff_hi


def fa_anchor_core_for_cpu_offer(player: object, team: object) -> int:
    """正本帯の mid × FA プレミアム。若手 eff_hi は resign と同一。"""
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_fa_candidate_role_band(team, player)
    age = safe_getattr_int(player, "age", 25)
    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    mid = (eff_lo + eff_hi) // 2
    boosted = int(mid * fa_market_premium_multiplier(player))
    cap = int(eff_hi * 1.12)
    return clamp_int(boosted, eff_lo, cap)


def fa_offer_base_salary(team: object, player: object) -> int:
    """
    `_calculate_offer` の芯: FA anchor を主に、save の player.salary を補助ブレンド。
    save が帯の大きく外れているときは anchor 寄りに戻す。
    """
    anchor_core = fa_anchor_core_for_cpu_offer(player, team)
    save = int(getattr(player, "salary", 0) or 0)
    div = max(1, min(3, safe_getattr_int(team, "league_level", 3)))
    nat = resign_nat_band_key(player)
    rank = infer_fa_candidate_role_band(team, player)
    age = safe_getattr_int(player, "age", 25)
    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    floor = int(contract_min_salary_floor_for_team(team))

    if save <= 0:
        return max(int(floor), int(anchor_core))

    save_c = clamp_int(save, int(eff_lo * 0.72), int(eff_hi * 1.32))
    if save > int(eff_hi * 2.1):
        blended = int(0.74 * anchor_core + 0.26 * min(save_c, int(eff_hi * 1.08)))
    else:
        blended = int(0.58 * anchor_core + 0.42 * save_c)
    return max(int(floor), int(blended))


def median_league_level_for_teams(teams: object) -> int:
    """国際補充など FA プール全体の代表 division（中央値）。"""
    if not teams:
        return 3
    xs: list[int] = []
    for t in teams:
        xs.append(max(1, min(3, safe_getattr_int(t, "league_level", 3))))
    if not xs:
        return 3
    xs.sort()
    return xs[len(xs) // 2]


def fa_anchor_core_for_pool_player(player: object, division: int) -> int:
    """ロスター無し: OVR role + 代表 division で FA 芯（国際補充の salary 初期値）。"""
    div = max(1, min(3, int(division)))
    nat = resign_nat_band_key(player)
    rank = infer_fa_role_band_ovr_only(safe_getattr_int(player, "ovr", 60))
    age = safe_getattr_int(player, "age", 25)
    eff_lo, eff_hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    mid = (eff_lo + eff_hi) // 2
    boosted = int(mid * fa_market_premium_multiplier(player))
    cap = int(eff_hi * 1.12)
    return clamp_int(boosted, eff_lo, cap)


def blend_fa_pool_market_salary(player: object, league_division: int, estimate_yen: int) -> int:
    """
    FAプールに保存する `player.salary`（市場基準値）: anchor_core を主、estimate を補助にブレンド。
    正本帯 `resign_anchor_lo_hi_effective` と同じ floor/ceiling でクランプ（インシーズン契約帯と同世界観）。
    """
    div = max(1, min(3, int(league_division)))
    core = int(fa_anchor_core_for_pool_player(player, div))
    est = int(estimate_yen)
    ratio = est / max(1, core)
    if ratio < 0.42 or ratio > 2.3:
        wc, we = 0.94, 0.06
    else:
        wc, we = 0.88, 0.12
    _pool_floor = int(contract_min_salary_floor_for_division(div))
    est_c = clamp_int(est, max(_pool_floor, int(core * 0.38)), int(core * 1.42))
    out = int(wc * core + we * est_c)
    nat = resign_nat_band_key(player)
    rank = infer_fa_role_band_ovr_only(safe_getattr_int(player, "ovr", 60))
    age = safe_getattr_int(player, "age", 25)
    lo, hi = resign_anchor_lo_hi_effective(div, nat, rank, age)
    floor = int(contract_min_salary_floor_for_division(div))
    return max(int(floor), clamp_int(out, lo, int(hi * 1.08)))


def inseason_fa_market_multiplier(player: object) -> float:
    """オフ本格FA `fa_market_premium_multiplier` より弱く、再契約帯よりやや高い乗数。"""
    age = safe_getattr_int(player, "age", 25)
    nat = resign_nat_band_key(player)
    m = 1.10
    if age <= 20:
        m = 1.04
    elif age <= 23:
        m = 1.06
    elif age >= 37:
        m = 1.04
    elif age >= 34:
        m = 1.07
    if nat == "foreign":
        m *= 1.015
    elif nat == "naturalized":
        m *= 1.022
    elif nat == "asia":
        m *= 1.006
    return min(1.14, max(1.03, m))


def inseason_fa_anchor_core_for_sign(player: object, team: object) -> Tuple[int, int, int]:
    """(anchor_core, eff_lo, eff_hi)。帯は `get_fa_offer_anchor_band` と若手 eff と同一。"""
    eff_lo, mid, eff_hi = get_fa_offer_anchor_band(player, team)
    boosted = int(mid * inseason_fa_market_multiplier(player))
    core = clamp_int(boosted, eff_lo, int(eff_hi * 1.06))
    return core, eff_lo, eff_hi


def blend_inseason_fa_contract_salary(team: object, player: object, estimate_yen: int) -> int:
    """
    インシーズンFA 契約額: anchor_core を主、`estimate_yen` を補助にブレンド。
    estimate 単独からの乖離が大きいときは anchor 重みを上げる。
    """
    core, eff_lo, eff_hi = inseason_fa_anchor_core_for_sign(player, team)
    est = int(estimate_yen)
    ratio = est / max(1, core)
    if ratio < 0.4 or ratio > 2.4:
        wc, we = 0.74, 0.26
    else:
        wc, we = 0.62, 0.38
    _inseason_floor = int(contract_min_salary_floor_for_team(team))
    est_c = clamp_int(est, max(_inseason_floor, int(eff_lo * 0.5)), int(eff_hi * 1.3))
    out = int(wc * core + we * est_c)
    floor = int(contract_min_salary_floor_for_team(team))
    return max(int(floor), clamp_int(out, eff_lo, int(eff_hi * 1.07)))
