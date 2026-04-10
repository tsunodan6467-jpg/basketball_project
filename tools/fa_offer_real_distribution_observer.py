#!/usr/bin/env python3
"""
Observe S6 tiny offers over real save or simulated league state (not wired to production).

Uses `_calculate_offer_diagnostic` only. Run from repo root:

  python tools/fa_offer_real_distribution_observer.py
  python tools/fa_offer_real_distribution_observer.py --save path/to/file.sav
  python tools/fa_offer_real_distribution_observer.py --save path/to/file.sav --apply-temp-postoff-floor
  python tools/fa_offer_real_distribution_observer.py --seasons 1 --seed 42
  python tools/fa_offer_real_distribution_observer.py --population-mode mixed_mid_fa_roomy
  python tools/fa_offer_real_distribution_observer.py --save-list a.sav b.sav

Optional population modes (default unchanged): see docs/FA_OBSERVER_MATRIX_REDESIGN_PLAN_2026-04.md

Each run prints one ASCII summary line before the main histogram (soft_cap_early rate, room_to_budget
uniques, pre-clip offer<=room count on non-soft_cap_early rows), then a short pre_le_pop block: same
population as pre_le_room (soft_cap_early False, offer_after_soft_cap_pushback & room_to_budget non-None)
with min/max/p25–p75 for room_to_budget, offer_after_hard_cap_over (pushback前), offer_after_soft_cap_pushback
(pushback後), offer_minus_room le0/gt0/gt_temp counts, plus soft_cap_pushback_applied true/false counts
and hard_over_minus_soft_pushback eq0/gt0 pair counts (same pre_le_pop population).
Plus gate subset (pre_le rows with payroll_after_pre_soft_pushback & soft_cap non-None): payroll_after_pre_soft
min/max/p25–p75 and gt/le_eq soft_cap counts; soft_cap value or min/max/unique (n_gate). payroll_before min/max/p25–p75
for pre_le rows with payroll_before non-None.

After loading teams, prints sync_observation (before / sync1 / sync2): payroll_budget and roster payroll
uniques plus gap = max(0, payroll_budget - roster_payroll) for these stats (same sign convention as roomy helper).
payroll_budget is the team's stored field (post-offseason formula when ⑦ has run); roster_payroll is sum of
player salaries (contract reality). Do not equate low budget with "bug" — see docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md.
See docs/FA_ROOM_UNIQUE_ONE_CAUSE_NOTE_2026-04.md
Immediately after the before: line, prints one user_team_snapshot line (pre-sync league_level / market_size /
popularity / sponsor_power / fan_base — inputs to offseason payroll_budget formula — plus money / payroll_budget /
roster_payroll / gap). payroll_budget vs roster_payroll meanings same as sync_observation. See
docs/FA_BEFORE_GAP_ZERO_CAUSE_NOTE_2026-04.md and docs/PAYROLL_BUDGET_FORMULA_CAUSE_NOTE_2026-04.md
Then reading_guide plus reading_note_ja: primary=before for compare; sync1/sync2 and matrix/summary are secondary
(prod-aligned). See docs/FA_OBSERVER_SYNC_HANDLING_DECISION_2026-04.md

See docs/FA_S6_TINY_OFFER_DECISION_MEMO_2026-04.md
"""

from __future__ import annotations

import argparse
import contextlib
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.models.offseason import (  # noqa: E402
    _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER,
    _sync_payroll_budget_with_roster_payroll,
    reapply_temp_postoff_payroll_budget_floor_to_teams,
)
from basketball_sim.models.player import Player  # noqa: E402
from basketball_sim.models.team import Team  # noqa: E402
from basketball_sim.persistence.save_load import load_world, validate_payload  # noqa: E402
from basketball_sim.systems import free_agency as fa_mod  # noqa: E402
from basketball_sim.utils.sim_rng import init_simulation_random  # noqa: E402

TINY_MAX = 300_000
BAND_3M = 3_000_000
BAND_10M = 10_000_000
HIGH_SALARY = 50_000_000

# Temporary: "large" positive offer-room gap for pre_le_pop gt_temp bucket (tune later).
TEMP_PRE_LE_DIFF_LARGE_THRESHOLD = 5_000_000


class _SilentWriter:
    def write(self, _data: str) -> int:
        return len(_data)

    def flush(self) -> None:
        return None


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FA offer diagnostic distribution observer")
    p.add_argument(
        "--save",
        type=str,
        default="",
        help="Path to .sav file (pickle). If set, skip world generation. "
        "Mutually exclusive with --save-list.",
    )
    p.add_argument(
        "--save-list",
        nargs="+",
        default=None,
        metavar="PATH",
        help="Run observer once per .sav path, in order (same population-mode / fa-cap as single run). "
        "Mutually exclusive with --save.",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed for simulated world")
    p.add_argument(
        "--fa-cap",
        type=int,
        default=40,
        help="Top N free agents by salary to pair with each team",
    )
    p.add_argument(
        "--seasons",
        type=int,
        default=0,
        help="If >0, run Season.simulate_to_end() this many times after world build (slow)",
    )
    p.add_argument(
        "--population-mode",
        choices=("default", "mixed_mid_fa_roomy"),
        default="default",
        help="default: top fa-cap FAs by salary x all teams (legacy). "
        "mixed_mid_fa_roomy: FA salary rank band + optional top-N roomiest teams.",
    )
    p.add_argument(
        "--fa-rank-start",
        type=int,
        default=11,
        help="1-based inclusive start rank by FA salary (desc). Used only when --population-mode mixed_mid_fa_roomy.",
    )
    p.add_argument(
        "--fa-rank-end",
        type=int,
        default=50,
        help="1-based inclusive end rank by FA salary (desc). Used only when --population-mode mixed_mid_fa_roomy.",
    )
    p.add_argument(
        "--roomy-team-count",
        type=int,
        default=0,
        help="If >0, keep only this many teams with largest (payroll_budget - roster payroll). "
        "0 means all teams. Used only when --population-mode mixed_mid_fa_roomy.",
    )
    p.add_argument(
        "--apply-temp-postoff-floor",
        action="store_true",
        help="After loading --save/--save-list: overwrite each team.payroll_budget using TEMP_POSTOFF_* "
        "(same as ⑦ floor formula). Static .sav keeps stale payroll_budget; use this for BUFFER tuning compares.",
    )
    return p.parse_args()


def _check_save_args_exclusive(save: str, save_list: Optional[List[str]]) -> Optional[str]:
    if save and save_list is not None:
        return "use either --save or --save-list, not both"
    return None


def _load_teams_fas_from_save(path: Path) -> Tuple[List[Team], List[Player]]:
    payload = load_world(path)
    validate_payload(payload)
    teams = list(payload.get("teams") or [])
    fas = list(payload.get("free_agents") or [])
    return teams, fas


def _build_simulated_world(args: argparse.Namespace) -> Tuple[List[Team], List[Player]]:
    from basketball_sim.main import (
        CITY_MARKET_SIZE,
        apply_user_team_to_league,
        assign_fictional_teams_and_rival,
        auto_draft_players,
        choose_icon_player_auto,
        create_fictional_player_pool,
        create_icon_player,
    )
    from basketball_sim.models.season import Season
    from basketball_sim.systems.generator import generate_teams

    init_simulation_random(args.seed)
    silent = _SilentWriter()
    with contextlib.redirect_stdout(silent):
        home = "東京" if "東京" in CITY_MARKET_SIZE else next(iter(CITY_MARKET_SIZE.keys()))
        market = float(CITY_MARKET_SIZE.get(home, 1.0))
        teams = generate_teams()
        user_team = apply_user_team_to_league(teams, "ObserverClub", home, market)
        icon_player = create_icon_player(choose_icon_player_auto())
        pool = create_fictional_player_pool()
        auto_draft_players(pool, user_team, icon_player)
        free_agents: List[Player] = []
        assign_fictional_teams_and_rival(teams, user_team, pool, free_agents)

        if args.seasons > 0:
            season = Season(teams, free_agents)
            for _ in range(args.seasons):
                season.simulate_to_end()

    return teams, free_agents


def _fa_salary(p: Player) -> int:
    try:
        return max(0, int(getattr(p, "salary", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _fa_pool_by_salary_desc(free_agents: List[Player]) -> List[Player]:
    pool = [p for p in free_agents if getattr(p, "team_id", None) is None]
    if not pool:
        pool = list(free_agents)
    pool.sort(key=_fa_salary, reverse=True)
    return pool


def _select_fa_sample(free_agents: List[Player], cap: int) -> List[Player]:
    pool = _fa_pool_by_salary_desc(free_agents)
    return pool[: max(1, cap)]


def _select_fa_sample_by_salary_rank(
    free_agents: List[Player],
    rank_start: int,
    rank_end: int,
) -> List[Player]:
    """1-based inclusive ranks on salary-descending FA pool (same pool as legacy top-N)."""
    pool = _fa_pool_by_salary_desc(free_agents)
    if not pool:
        return []
    rs = max(1, int(rank_start))
    re = max(rs, int(rank_end))
    rs_c = min(rs, len(pool))
    re_c = min(re, len(pool))
    if rs_c > re_c:
        return []
    # inclusive ranks [rs_c, re_c] -> slice [rs_c - 1 : re_c]
    return pool[rs_c - 1 : re_c]


def _team_roster_payroll(team: Team) -> int:
    return int(
        sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in getattr(team, "players", []) or [])
    )


def _team_payroll_room(team: Team) -> int:
    budget = int(getattr(team, "payroll_budget", 0) or 0)
    return max(0, budget - _team_roster_payroll(team))


def _team_payroll_budget_int(team: Team) -> int:
    return int(getattr(team, "payroll_budget", 0) or 0)


def _teams_payroll_gap_stats(teams: List[Team]) -> Dict[str, Any]:
    """Per-team payroll_budget, roster payroll, gap (room-like); distribution summary for sync probe."""
    if not teams:
        return {
            "n": 0,
            "budget_u": 0,
            "roster_u": 0,
            "gap_u": 0,
            "gap_min": None,
            "gap_max": None,
        }
    budgets = [_team_payroll_budget_int(t) for t in teams]
    rosters = [_team_roster_payroll(t) for t in teams]
    gaps = [_team_payroll_room(t) for t in teams]
    return {
        "n": len(teams),
        "budget_u": len(set(budgets)),
        "roster_u": len(set(rosters)),
        "gap_u": len(set(gaps)),
        "gap_min": min(gaps),
        "gap_max": max(gaps),
    }


READING_GUIDE_LINE = (
    "reading_guide: primary=before (compare axis); secondary=sync1/sync2 and matrix/summary below "
    "(prod-aligned auxiliary). "
    "payroll_budget=current post-off formula field (not roster sum); roster_payroll=contract sum; "
    "gap=max(0, payroll_budget-roster_payroll) here."
)
READING_GUIDE_NOTE_JA = (
    "reading_note_ja: payroll_budget=現行オフ後式のチームフィールド; roster_payroll=契約実態(salary合計); "
    "gap=観測用max(0,差). before=比較主軸 / sync後・下の行列・summary=補助. 式変更は別決裁 "
    "(docs/PAYROLL_BUDGET_POSTOFF_DECISION_2026-04.md)."
)


def _pick_snapshot_team(teams: List[Team]) -> Tuple[Team, bool]:
    """First is_user_team if any, else teams[0]. Second is True when user team was found."""
    for t in teams:
        if bool(getattr(t, "is_user_team", False)):
            return t, True
    return teams[0], False


def _format_pre_sync_user_team_snapshot_line(teams: List[Team]) -> str:
    """
    Single-line diagnostic aligned with pre-sync (before) state: same gap as _team_payroll_room.
    payroll_budget = stored formula field; roster_payroll = sum of player salaries (not the same axis).
    Includes league_level / market_size / popularity / sponsor_power / fan_base for manual cross-check
    against Offseason._process_team_finances payroll_budget formula (see PAYROLL_BUDGET_FORMULA_CAUSE_NOTE).
    """
    if not teams:
        return "user_team_snapshot: (no teams)"
    team, is_user = _pick_snapshot_team(teams)
    tag = "user_team_snapshot" if is_user else "user_team_snapshot[fallback]"
    name = str(getattr(team, "name", "?"))
    lv = int(getattr(team, "league_level", 3) or 3)
    ms_raw = getattr(team, "market_size", 1.0)
    ms = float(1.0 if ms_raw is None else ms_raw)
    pop = int(getattr(team, "popularity", 50))
    sp = int(getattr(team, "sponsor_power", 50))
    fb = int(getattr(team, "fan_base", 50))
    money = int(getattr(team, "money", 0) or 0)
    pb = _team_payroll_budget_int(team)
    rp = _team_roster_payroll(team)
    gap = _team_payroll_room(team)
    ms_s = f"{ms:g}"
    return (
        f"{tag}: team={name} league_level={lv} market_size={ms_s} popularity={pop} "
        f"sponsor_power={sp} fan_base={fb} money={money:,} payroll_budget={pb:,} "
        f"roster_payroll={rp:,} gap={gap:,}"
    )


def _print_one_sync_stat_line(label: str, st: Dict[str, Any]) -> None:
    gmin = st["gap_min"]
    gmax = st["gap_max"]
    if gmin is None:
        gmin_s = gmax_s = "n/a"
    else:
        gmin_s, gmax_s = str(gmin), str(gmax)
    print(
        f"  {label}: n={st['n']} budget_unique={st['budget_u']} roster_unique={st['roster_u']} "
        f"gap_unique={st['gap_u']} gap_min={gmin_s} gap_max={gmax_s}"
    )


def _print_sync_observation_block(
    before: Dict[str, Any],
    sync1: Dict[str, Any],
    sync2: Dict[str, Any],
    *,
    pre_sync_user_snapshot: Optional[str] = None,
) -> None:
    buf = int(_OFFSEASON_FA_PAYROLL_BUDGET_BUFFER)
    print(f"sync_observation: buffer_const={buf} (roster+buffer floor in _sync_payroll_budget_with_roster_payroll)")
    _print_one_sync_stat_line("before", before)
    if pre_sync_user_snapshot:
        print(f"  {pre_sync_user_snapshot}")
    _print_one_sync_stat_line("sync1", sync1)
    _print_one_sync_stat_line("sync2", sync2)
    print(READING_GUIDE_LINE)
    print(READING_GUIDE_NOTE_JA)


def _select_teams_by_room(teams: List[Team], top_n: int) -> List[Team]:
    if top_n <= 0:
        return list(teams)
    n = min(int(top_n), len(teams))
    if n <= 0:
        return []
    sorted_teams = sorted(
        teams,
        key=lambda t: (-_team_payroll_room(t), -int(getattr(t, "team_id", 0))),
    )
    return sorted_teams[:n]


def _run_matrix(
    teams: List[Team],
    fa_sample: List[Player],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team in teams:
        for fa in fa_sample:
            d = fa_mod._calculate_offer_diagnostic(team, fa)
            lv = int(d.get("league_level") or getattr(team, "league_level", 1) or 1)
            lv = max(1, min(3, lv))
            fo = int(d["final_offer"])
            se = bool(d["soft_cap_early"])
            rtb = d.get("room_to_budget")
            rtb_i: Optional[int] = int(rtb) if rtb is not None else None
            sal = _fa_salary(fa)
            rows.append(
                {
                    "team_name": getattr(team, "name", "?"),
                    "team_id": int(getattr(team, "team_id", -1)),
                    "league_level": lv,
                    "soft_cap_early": se,
                    "final_offer": fo,
                    "room_to_budget": rtb_i,
                    "payroll_before": int(d["payroll_before"]),
                    "payroll_budget": _payroll_budget_display(team, d),
                    "fa_salary": sal,
                    "fa_id": int(getattr(fa, "player_id", 0)),
                    "diag": d,
                }
            )
    return rows


def _payroll_budget_display(team: Team, d: Dict[str, Any]) -> int:
    v = d.get("payroll_budget")
    if v is not None:
        return int(v)
    return int(getattr(team, "payroll_budget", 0) or 0)


def _matrix_summary_line(rows: List[Dict[str, Any]]) -> str:
    """One-line matrix probe: soft_cap_early share, distinct room_to_budget, pre-clip offer<=room (post-sync inputs)."""
    n = len(rows)
    n_s1 = sum(1 for r in rows if r["soft_cap_early"])
    pct = (100.0 * n_s1 / n) if n else 0.0
    rooms = [r["room_to_budget"] for r in rows if r["room_to_budget"] is not None]
    room_unique = len(set(rooms))
    pre_le = 0
    for r in rows:
        if r["soft_cap_early"]:
            continue
        d = r["diag"]
        o = d.get("offer_after_soft_cap_pushback")
        rtb = d.get("room_to_budget")
        if o is None or rtb is None:
            continue
        if int(o) <= int(rtb):
            pre_le += 1
    return (
        f"summary: soft_cap_early={n_s1}/{n} ({pct:.1f}%), "
        f"room_unique={room_unique}, pre_le_room={pre_le} "
        f"(matrix=post-sync payroll_budget; compare axis=sync_observation before)"
    )


def _quartiles_int(vals: List[int]) -> Tuple[int, int, int]:
    """Return (p25, p50, p75) as ints; vals non-empty."""
    if len(vals) == 1:
        v = vals[0]
        return v, v, v
    q1, q2, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    return int(round(q1)), int(round(q2)), int(round(q3))


def _pre_le_population_summary_lines(rows: List[Dict[str, Any]]) -> List[str]:
    """Same population as pre_le_room count in _matrix_summary_line (both keys non-None, not soft_cap_early)."""
    rtbs: List[int] = []
    offers: List[int] = []
    hard_vals: List[int] = []
    n_applied_true = 0
    n_applied_false = 0
    n_hm_eq0 = 0
    n_hm_gt0 = 0
    n_hm_cmp = 0
    gate_payrolls: List[int] = []
    n_pap_gt_sc = 0
    n_pap_le_sc = 0
    sc_gate_vals: List[int] = []
    pb_vals: List[int] = []
    for r in rows:
        if r["soft_cap_early"]:
            continue
        d = r["diag"]
        o = d.get("offer_after_soft_cap_pushback")
        rtb = d.get("room_to_budget")
        if o is None or rtb is None:
            continue
        oi = int(o)
        offers.append(oi)
        rtbs.append(int(rtb))
        pbx = d.get("payroll_before")
        if pbx is not None:
            pb_vals.append(int(pbx))
        if bool(d.get("soft_cap_pushback_applied")):
            n_applied_true += 1
        else:
            n_applied_false += 1
        ho = d.get("offer_after_hard_cap_over")
        if ho is not None:
            hi = int(ho)
            hard_vals.append(hi)
            n_hm_cmp += 1
            delta_hs = hi - oi
            if delta_hs == 0:
                n_hm_eq0 += 1
            elif delta_hs > 0:
                n_hm_gt0 += 1
        pap = d.get("payroll_after_pre_soft_pushback")
        sc = d.get("soft_cap")
        if pap is not None and sc is not None:
            pi, si = int(pap), int(sc)
            gate_payrolls.append(pi)
            sc_gate_vals.append(si)
            if pi > si:
                n_pap_gt_sc += 1
            else:
                n_pap_le_sc += 1
    n = len(rtbs)
    if n == 0:
        return [
            "pre_le_pop: n=0 (soft_cap_early=False, offer_after_soft_cap_pushback & room_to_budget both non-None)"
        ]
    p25_r, p50_r, p75_r = _quartiles_int(rtbs)
    p25_o, p50_o, p75_o = _quartiles_int(offers)
    diffs = [offers[i] - rtbs[i] for i in range(n)]
    n_le0 = sum(1 for x in diffs if x <= 0)
    n_gt0 = sum(1 for x in diffs if x > 0)
    thr = TEMP_PRE_LE_DIFF_LARGE_THRESHOLD
    n_gt_temp = sum(1 for x in diffs if x > thr)
    nh = len(hard_vals)
    if nh == 0:
        hard_line = "  offer_after_hard_cap_over n_hard=0"
    else:
        p25_h, p50_h, p75_h = _quartiles_int(hard_vals)
        hard_line = (
            "  offer_after_hard_cap_over "
            f"min={min(hard_vals)} max={max(hard_vals)} "
            f"p25={p25_h} p50={p50_h} p75={p75_h}"
        )
        if nh != n:
            hard_line += f" n_hard={nh}"
    ng = len(gate_payrolls)
    if ng == 0:
        gate_pap_line = "  payroll_after_pre_soft_pushback n_gate=0"
        gate_cmp_line = "  payroll_after_pre_vs_soft_cap gt=0 (0.0%) le_eq=0 (0.0%) (n_gate=0)"
        soft_cap_gate_line = "  soft_cap n_gate=0"
    else:
        p25_pap, p50_pap, p75_pap = _quartiles_int(gate_payrolls)
        gate_pap_line = (
            "  payroll_after_pre_soft_pushback "
            f"min={min(gate_payrolls)} max={max(gate_payrolls)} "
            f"p25={p25_pap} p50={p50_pap} p75={p75_pap} (n_gate={ng})"
        )
        pct_gt = (100.0 * n_pap_gt_sc / ng) if ng else 0.0
        pct_le = (100.0 * n_pap_le_sc / ng) if ng else 0.0
        gate_cmp_line = (
            "  payroll_after_pre_vs_soft_cap "
            f"gt={n_pap_gt_sc} ({pct_gt:.1f}%) "
            f"le_eq={n_pap_le_sc} ({pct_le:.1f}%) (n_gate={ng})"
        )
        sc_u = set(sc_gate_vals)
        if len(sc_u) == 1:
            soft_cap_gate_line = f"  soft_cap value={sc_gate_vals[0]} (n_gate={ng})"
        else:
            soft_cap_gate_line = (
                "  soft_cap "
                f"min={min(sc_gate_vals)} max={max(sc_gate_vals)} "
                f"unique={len(sc_u)} (n_gate={ng})"
            )
    npb = len(pb_vals)
    if npb == 0:
        pb_line = "  payroll_before n_pb=0"
    else:
        p25_pb, p50_pb, p75_pb = _quartiles_int(pb_vals)
        pb_line = (
            "  payroll_before "
            f"min={min(pb_vals)} max={max(pb_vals)} "
            f"p25={p25_pb} p50={p50_pb} p75={p75_pb}"
        )
        if npb != n:
            pb_line += f" (n_pb={npb})"
    return [
        "pre_le_pop: "
        f"n={n} "
        f"room_to_budget min={min(rtbs)} max={max(rtbs)} "
        f"p25={p25_r} p50={p50_r} p75={p75_r}",
        pb_line,
        hard_line,
        "  offer_after_soft_cap_pushback "
        f"min={min(offers)} max={max(offers)} "
        f"p25={p25_o} p50={p50_o} p75={p75_o}",
        "  offer_minus_room "
        f"le0={n_le0} gt0={n_gt0} gt_temp={n_gt_temp} "
        f"(TEMP_PRE_LE_DIFF_LARGE_THRESHOLD={thr})",
        "  soft_cap_pushback_applied "
        f"true={n_applied_true} false={n_applied_false} (n={n})",
        "  hard_over_minus_soft_pushback "
        f"eq0={n_hm_eq0} gt0={n_hm_gt0} (n_cmp={n_hm_cmp})",
        gate_pap_line,
        gate_cmp_line,
        soft_cap_gate_line,
    ]


def _print_pre_le_population_summary(rows: List[Dict[str, Any]]) -> None:
    for line in _pre_le_population_summary_lines(rows):
        print(line)


def _aggregate(rows: List[Dict[str, Any]], population_banner: str = "") -> None:
    buf = _OFFSEASON_FA_PAYROLL_BUDGET_BUFFER
    n = len(rows)
    n_s1 = sum(1 for r in rows if r["soft_cap_early"])
    n_zero = sum(1 for r in rows if r["final_offer"] == 0)
    n_tiny = sum(1 for r in rows if 0 < r["final_offer"] <= TINY_MAX)
    n_le_3m = sum(1 for r in rows if 0 < r["final_offer"] <= BAND_3M)
    n_le_10m = sum(1 for r in rows if 0 < r["final_offer"] <= BAND_10M)
    n_le_buffer = sum(1 for r in rows if 0 < r["final_offer"] <= buf)
    n_final_eq_buffer = sum(1 for r in rows if r["final_offer"] == buf)
    n_final_open_lt_buffer = sum(1 for r in rows if 0 < r["final_offer"] < buf)
    n_final_gt_buffer = sum(1 for r in rows if r["final_offer"] > buf)
    n_s6_tiny = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    )
    n_s6_le_3m = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= BAND_3M
    )
    n_s6_le_10m = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= BAND_10M
    )
    n_s6_le_buffer = sum(
        1 for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= buf
    )
    n_room_le = sum(
        1
        for r in rows
        if r["room_to_budget"] is not None and r["room_to_budget"] <= TINY_MAX
    )
    n_high_tiny = sum(
        1
        for r in rows
        if (not r["soft_cap_early"])
        and 0 < r["final_offer"] <= TINY_MAX
        and r["fa_salary"] >= HIGH_SALARY
    )

    by_lv = Counter(r["league_level"] for r in rows)
    by_lv_s6_tiny = Counter(
        r["league_level"] for r in rows if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    )

    def pct(x: int) -> str:
        if n <= 0:
            return "0.00%"
        return f"{100.0 * x / n:.2f}%"

    print("FA offer real/sim distribution observer (_calculate_offer_diagnostic)")
    if population_banner:
        print(population_banner)
    print("---")
    print(f"total_samples (team x fa): {n}")
    print(f"soft_cap_early True:       {n_s1} ({pct(n_s1)})")
    print(f"final_offer == 0:          {n_zero} ({pct(n_zero)})")
    print(f"0 < final <= {TINY_MAX}:        {n_tiny} ({pct(n_tiny)})")
    print(f"0 < final <= {BAND_3M}:        {n_le_3m} ({pct(n_le_3m)})")
    print(f"0 < final <= {BAND_10M}:       {n_le_10m} ({pct(n_le_10m)})")
    print(f"0 < final <= buffer ({buf:,}): {n_le_buffer} ({pct(n_le_buffer)})")
    print(f"final_offer == buffer ({buf:,}): {n_final_eq_buffer} ({pct(n_final_eq_buffer)})")
    print(f"0 < final_offer < buffer:        {n_final_open_lt_buffer} ({pct(n_final_open_lt_buffer)})")
    print(f"final_offer > buffer:            {n_final_gt_buffer} ({pct(n_final_gt_buffer)})")
    print(
        "soft_cap_early False & "
        f"0 < final <= {TINY_MAX}: {n_s6_tiny} ({pct(n_s6_tiny)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= {BAND_3M}: {n_s6_le_3m} ({pct(n_s6_le_3m)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= {BAND_10M}: {n_s6_le_10m} ({pct(n_s6_le_10m)})"
    )
    print(
        "soft_cap_early False & "
        f"0 < final <= buffer: {n_s6_le_buffer} ({pct(n_s6_le_buffer)})"
    )
    print(
        "room_to_budget not None & "
        f"<= {TINY_MAX}:          {n_room_le} ({pct(n_room_le)})"
    )
    print(
        f"high FA (sal>={HIGH_SALARY}) & S6-tiny: {n_high_tiny} ({pct(n_high_tiny)})"
    )
    print("---")
    print("samples by team league_level (all pairs):")
    for lv in (1, 2, 3):
        c = by_lv.get(lv, 0)
        print(f"  D{lv}: {c} ({pct(c)})")
    print("S6-tiny pairs by team league_level:")
    for lv in (1, 2, 3):
        c = by_lv_s6_tiny.get(lv, 0)
        print(f"  D{lv}: {c}")
    print("---")
    tiny_rows = [
        r
        for r in rows
        if (not r["soft_cap_early"]) and 0 < r["final_offer"] <= TINY_MAX
    ]
    tiny_rows.sort(key=lambda r: (-r["fa_salary"], -r["final_offer"]))
    print("sample S6-tiny cases (up to 5):")
    for i, r in enumerate(tiny_rows[:5]):
        print(f"  [{i + 1}] team={r['team_name']} id={r['team_id']} league=D{r['league_level']}")
        print(f"      payroll_before={r['payroll_before']:,}")
        print(f"      payroll_budget={r['payroll_budget']:,}")
        print(f"      room_to_budget={r['room_to_budget']}")
        print(f"      fa_salary={r['fa_salary']:,} fa_id={r['fa_id']}")
        print(f"      final_offer={r['final_offer']:,} soft_cap_early={r['soft_cap_early']}")


def _run_one_observation(args: argparse.Namespace, *, save_path: Optional[str]) -> bool:
    """Load or build world, run matrix, print aggregate. Returns False on abort."""
    if save_path:
        sp = Path(save_path)
        if not sp.is_file():
            print(f"save file not found: {sp}")
            return False
        teams, fas = _load_teams_fas_from_save(sp)
    else:
        teams, fas = _build_simulated_world(args)

    if not teams:
        print("no teams; abort")
        return False

    if getattr(args, "apply_temp_postoff_floor", False):
        if not save_path:
            print("--apply-temp-postoff-floor requires --save or --save-list; abort")
            return False
        reapply_temp_postoff_payroll_budget_floor_to_teams(teams)

    pre_sync_snapshot = _format_pre_sync_user_team_snapshot_line(teams)
    stats_before = _teams_payroll_gap_stats(teams)
    _sync_payroll_budget_with_roster_payroll(teams)
    stats_sync1 = _teams_payroll_gap_stats(teams)
    _sync_payroll_budget_with_roster_payroll(teams)
    stats_sync2 = _teams_payroll_gap_stats(teams)
    _print_sync_observation_block(
        stats_before, stats_sync1, stats_sync2, pre_sync_user_snapshot=pre_sync_snapshot
    )

    population_banner = ""
    if args.population_mode == "default":
        fa_sample = _select_fa_sample(fas, args.fa_cap)
        team_subset = teams
    else:
        if args.fa_rank_end < args.fa_rank_start:
            print("fa-rank-end must be >= fa-rank-start; abort")
            return False
        fa_sample = _select_fa_sample_by_salary_rank(fas, args.fa_rank_start, args.fa_rank_end)
        if not fa_sample:
            print("no FAs in selected salary-rank band; abort")
            return False
        team_subset = _select_teams_by_room(teams, args.roomy_team_count)
        if not team_subset:
            print("no teams after room filter; abort")
            return False
        rtc = args.roomy_team_count
        rtc_note = "all teams" if rtc <= 0 else f"top {min(rtc, len(teams))} by payroll room"
        population_banner = (
            f"population_mode={args.population_mode} "
            f"fa_salary_ranks={args.fa_rank_start}-{args.fa_rank_end} ({len(fa_sample)} FAs) "
            f"teams={len(team_subset)} ({rtc_note})"
        )

    rows = _run_matrix(team_subset, fa_sample)
    print(_matrix_summary_line(rows))
    _print_pre_le_population_summary(rows)
    _aggregate(rows, population_banner=population_banner)
    return True


def main() -> None:
    args = _parse_args()
    err = _check_save_args_exclusive(args.save, args.save_list)
    if err:
        print(err, file=sys.stderr)
        sys.exit(2)

    if args.save_list is not None:
        total = len(args.save_list)
        for i, path in enumerate(args.save_list, start=1):
            print()
            print("=" * 72)
            print(f"# save [{i}/{total}]: {path}")
            print("=" * 72)
            if not _run_one_observation(args, save_path=path):
                sys.exit(1)
        return

    save_path = args.save if args.save else None
    if not _run_one_observation(args, save_path=save_path):
        sys.exit(1)


if __name__ == "__main__":
    main()
