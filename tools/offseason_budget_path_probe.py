"""
⑦ `compute_postoff_payroll_budget_with_temp_floor` の formula / floor 採用経路を観測（本体非改変）。

`offseason.py` の式と乖離しないよう、採用額は必ず `compute_postoff_payroll_budget_with_temp_floor` を呼んで一致確認する。
分解値（cfb, floor, fac, profile）は観測用に同ファイルの式をミラーする（コメントで同期先を明示）。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import (  # noqa: E402
    Offseason,
    TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER,
    TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO,
    compute_postoff_payroll_budget_with_temp_floor,
)
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.systems.club_profile import get_club_base_profile  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402

# 同期先: basketball_sim/models/offseason.py `compute_postoff_payroll_budget_with_temp_floor`


def _roster_payroll(team: Any) -> int:
    return int(
        sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in getattr(team, "players", None) or [])
    )


def _decompose_postoff_budget(team: Any, roster_payroll: int) -> Dict[str, Any]:
    league_level = int(getattr(team, "league_level", 3))
    base_budget = {1: 7_900_000, 2: 5_450_000, 3: 3_650_000}.get(league_level, 3_650_000)
    inner_sum = float(
        base_budget
        + float(getattr(team, "market_size", 1.0)) * 12_500
        + getattr(team, "popularity", 50) * 6_200
        + getattr(team, "sponsor_power", 50) * 5_000
        + getattr(team, "fan_base", 50) * 3_600
    )
    fin = mkt = ar = wn = None
    fac = 1.0
    try:
        if bool(getattr(team, "is_user_team", False)):
            fac = 1.0
        else:
            prof = get_club_base_profile(team)
            fin = float(prof.financial_power)
            mkt = float(prof.market_size)
            ar = float(prof.arena_grade)
            wn = float(prof.win_now_pressure)
            fac = (
                1.0
                + 0.022 * (fin - 1.0)
                + 0.018 * (mkt - 1.0)
                + 0.015 * (ar - 1.0)
            )
            if wn >= 1.04:
                fac += 0.005
            elif wn <= 0.98:
                fac -= 0.005
            fac = max(0.97, min(1.03, float(fac)))
    except Exception:
        fac = 1.0

    current_formula_budget = max(base_budget, int(inner_sum * fac))
    raw_floor = int(
        int(roster_payroll) * float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO)
        + float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER)
    )
    soft_cap = int(current_formula_budget)
    floor_expr = min(raw_floor, soft_cap)
    adopted = int(max(current_formula_budget, floor_expr))
    if current_formula_budget > floor_expr:
        source = "formula"
    elif floor_expr > current_formula_budget:
        source = "floor"
    else:
        source = "tie"

    adopted_fn = compute_postoff_payroll_budget_with_temp_floor(team, roster_payroll)
    if adopted != adopted_fn:
        raise RuntimeError(
            f"probe decompose mismatch team_id={getattr(team, 'team_id', '?')}: "
            f"decompose={adopted} fn={adopted_fn}"
        )

    room_under_guideline = max(0, adopted - int(roster_payroll))
    return {
        "league_level": league_level,
        "base_budget": base_budget,
        "inner_sum": inner_sum,
        "fac": round(fac, 6),
        "financial_power": fin,
        "market_size_prof": mkt,
        "arena_grade": ar,
        "win_now_pressure": wn,
        "current_formula_budget": current_formula_budget,
        "floor_expr": floor_expr,
        "adopted_budget": adopted,
        "adopted_source": source,
        "roster_payroll": int(roster_payroll),
        "room_under_guideline": room_under_guideline,
    }


def _team_by_id(teams: List[Any], tid: int) -> Any:
    return next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)


def _run_season_quiet(teams: List[Any], free_agents: List[Any]) -> Season:
    season = Season(teams, free_agents)
    safety = 0
    cap = max(500, int(getattr(season, "total_rounds", 0) or 0) + 400)
    while not bool(getattr(season, "season_finished", False)):
        season.simulate_next_round()
        safety += 1
        if safety > cap:
            raise RuntimeError("season loop exceeded cap")
    return season


def _offseason_quiet(teams: List[Any], free_agents: List[Any]) -> Offseason:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        off = Offseason(teams, free_agents)
        off.run()
    return off


def run_probe(*, years: int, seed: int, team_ids: Tuple[int, ...]) -> List[str]:
    sim_rng_mod.init_simulation_random(int(seed))
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    lines: List[str] = []
    lines.append(
        f"offseason_budget_path_probe | seed={seed} years={years} "
        f"TEMP_FLOOR_RATIO={TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO} "
        f"BUFFER={TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER}"
    )
    lines.append(f"team_ids={list(team_ids)}")
    lines.append("")
    hdr = (
        "phase year team_id name roster_payroll fac fin mkt arena win_now "
        "cfb floor adopted source room_under_guideline"
    )
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for y in range(1, years + 1):
        season = _run_season_quiet(teams, free_agents)
        free_agents = list(getattr(season, "free_agents", []) or [])

        for tid in team_ids:
            team = _team_by_id(teams, tid)
            rp_end = _roster_payroll(team)
            d0 = _decompose_postoff_budget(team, rp_end)
            lines.append(
                f"post_season y{y} {tid} {getattr(team, 'name', '')!r} "
                f"{d0['roster_payroll']} {d0['fac']} "
                f"{_fmt_opt(d0['financial_power'])} {_fmt_opt(d0['market_size_prof'])} "
                f"{_fmt_opt(d0['arena_grade'])} {_fmt_opt(d0['win_now_pressure'])} "
                f"{d0['current_formula_budget']} {d0['floor_expr']} {d0['adopted_budget']} "
                f"{d0['adopted_source']} {d0['room_under_guideline']}"
            )

        _offseason_quiet(teams, free_agents)

        for tid in team_ids:
            team = _team_by_id(teams, tid)
            rp_after = _roster_payroll(team)
            d1 = _decompose_postoff_budget(team, rp_after)
            pb = int(getattr(team, "payroll_budget", 0) or 0)
            if pb != d1["adopted_budget"]:
                lines.append(
                    f"WARN post_off y{y} tid={tid} payroll_budget_field={pb} "
                    f"decompose_adopted={d1['adopted_budget']}"
                )
            lines.append(
                f"post_offseason y{y} {tid} {getattr(team, 'name', '')!r} "
                f"{d1['roster_payroll']} {d1['fac']} "
                f"{_fmt_opt(d1['financial_power'])} {_fmt_opt(d1['market_size_prof'])} "
                f"{_fmt_opt(d1['arena_grade'])} {_fmt_opt(d1['win_now_pressure'])} "
                f"{d1['current_formula_budget']} {d1['floor_expr']} {d1['adopted_budget']} "
                f"{d1['adopted_source']} {d1['room_under_guideline']} "
                f"payroll_budget_field={pb}"
            )

    lines.append("")
    lines.append(
        "Notes: post_season = end of regular season roster; post_offseason = after Offseason.run "
        "(⑦ uses payroll at _process_team_finances = post-FA roster). "
        "room_under_guideline = max(0, adopted_budget - roster_payroll) for same rp as ⑦."
    )
    return lines


def _fmt_opt(x: Any) -> str:
    if x is None:
        return "-"
    return f"{float(x):.4f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe ⑦ payroll budget formula vs floor adoption path")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=424_242)
    ap.add_argument(
        "--teams",
        type=str,
        default="38,46,1,4,8,9,16,22",
        help="Comma-separated team_id list",
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    tids = tuple(int(x.strip()) for x in str(args.teams).split(",") if x.strip())
    lines = run_probe(years=max(1, int(args.years)), seed=int(args.seed), team_ids=tids)
    text = "\n".join(lines) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out.resolve()} ({len(text)} chars)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
