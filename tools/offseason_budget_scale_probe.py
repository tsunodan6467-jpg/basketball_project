"""
⑦式の `current_formula_budget` を仮倍率で持ち上げたときの formula / floor 勝敗試算（本体非改変）。

試算定義（観測用）:
  scaled_cfb = max(base_budget, int(inner_sum * fac * scale))
  adopted_scaled = max(scaled_cfb, floor_expr)
  source = formula | floor | tie

同期先: basketball_sim/models/offseason.py `compute_postoff_payroll_budget_with_temp_floor`
（cfb / floor の素片は `offseason_budget_path_probe.py` と同じミラー）
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


def _roster_payroll(team: Any) -> int:
    return int(
        sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in getattr(team, "players", None) or [])
    )


def _decompose_base(team: Any, roster_payroll: int) -> Dict[str, Any]:
    league_level = int(getattr(team, "league_level", 3))
    base_budget = {1: 7_900_000, 2: 5_450_000, 3: 3_650_000}.get(league_level, 3_650_000)
    inner_sum = float(
        base_budget
        + float(getattr(team, "market_size", 1.0)) * 12_500
        + getattr(team, "popularity", 50) * 6_200
        + getattr(team, "sponsor_power", 50) * 5_000
        + getattr(team, "fan_base", 50) * 3_600
    )
    fac = 1.0
    try:
        if bool(getattr(team, "is_user_team", False)):
            fac = 1.0
        else:
            prof = get_club_base_profile(team)
            fac = (
                1.0
                + 0.022 * (float(prof.financial_power) - 1.0)
                + 0.018 * (float(prof.market_size) - 1.0)
                + 0.015 * (float(prof.arena_grade) - 1.0)
            )
            wn = float(prof.win_now_pressure)
            if wn >= 1.04:
                fac += 0.005
            elif wn <= 0.98:
                fac -= 0.005
            fac = max(0.97, min(1.03, float(fac)))
    except Exception:
        fac = 1.0

    raw_inner = float(inner_sum) * float(fac)
    current_formula_budget = max(base_budget, int(raw_inner))
    raw_floor = int(
        int(roster_payroll) * float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO)
        + float(TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER)
    )
    soft_cap = int(current_formula_budget)
    floor_expr = min(raw_floor, soft_cap)
    adopted = int(max(current_formula_budget, floor_expr))
    chk = compute_postoff_payroll_budget_with_temp_floor(team, roster_payroll)
    if adopted != chk:
        raise RuntimeError(f"cfb/floor mismatch team_id={getattr(team, 'team_id', '?')}: {adopted} vs {chk}")

    return {
        "base_budget": base_budget,
        "inner_sum": inner_sum,
        "fac": fac,
        "raw_inner": raw_inner,
        "current_formula_budget": current_formula_budget,
        "floor_expr": floor_expr,
        "adopted": adopted,
    }


def _scaled_cfb(base_budget: int, inner_sum: float, fac: float, scale: float) -> int:
    return max(int(base_budget), int(float(inner_sum) * float(fac) * float(scale)))


def _source(cfb: int, fl: int) -> str:
    if cfb > fl:
        return "formula"
    if fl > cfb:
        return "floor"
    return "tie"


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


def _offseason_quiet(teams: List[Any], free_agents: List[Any]) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        Offseason(teams, free_agents).run()


def run_scale_probe(
    *,
    years: int,
    seed: int,
    team_ids: Tuple[int, ...],
    scales: Tuple[float, ...],
) -> List[str]:
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
        f"offseason_budget_scale_probe | seed={seed} years={years} scales={list(scales)} "
        f"FLOOR_RATIO={TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_RATIO} BUFFER={TEMP_POSTOFF_PAYROLL_BUDGET_FLOOR_BUFFER}"
    )
    lines.append(f"team_ids={list(team_ids)}")
    lines.append(
        "scaled_cfb = max(base_budget, int(inner_sum * fac * scale)); winner = argmax(scaled_cfb, floor)"
    )
    lines.append("")

    scale_headers = " ".join(f"x{s:.2f}" for s in scales)
    hdr = f"phase year tid name cfb floor gap {scale_headers}"
    lines.append(hdr)
    lines.append("-" * min(160, len(hdr) + 40))

    for y in range(1, years + 1):
        season = _run_season_quiet(teams, free_agents)
        free_agents = list(getattr(season, "free_agents", []) or [])

        for tid in team_ids:
            team = _team_by_id(teams, tid)
            rp = _roster_payroll(team)
            d = _decompose_base(team, rp)
            gap = int(d["current_formula_budget"]) - int(d["floor_expr"])
            parts = [
                "post_season",
                f"y{y}",
                str(tid),
                repr(str(getattr(team, "name", ""))),
                str(d["current_formula_budget"]),
                str(d["floor_expr"]),
                str(gap),
            ]
            for sc in scales:
                scfb = _scaled_cfb(int(d["base_budget"]), float(d["inner_sum"]), float(d["fac"]), sc)
                parts.append(_source(scfb, int(d["floor_expr"])))
            lines.append(" ".join(parts))

        _offseason_quiet(teams, free_agents)

        for tid in team_ids:
            team = _team_by_id(teams, tid)
            rp = _roster_payroll(team)
            d = _decompose_base(team, rp)
            gap = int(d["current_formula_budget"]) - int(d["floor_expr"])
            parts = [
                "post_offseason",
                f"y{y}",
                str(tid),
                repr(str(getattr(team, "name", ""))),
                str(d["current_formula_budget"]),
                str(d["floor_expr"]),
                str(gap),
            ]
            for sc in scales:
                scfb = _scaled_cfb(int(d["base_budget"]), float(d["inner_sum"]), float(d["fac"]), sc)
                parts.append(_source(scfb, int(d["floor_expr"])))
            lines.append(" ".join(parts))

    lines.append("")
    lines.append(
        "Notes: x1.00 column should match live adopted_source (formula|floor|tie) for scaled_cfb vs floor."
    )
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Scale-sweep ⑦ formula side vs floor (observation only)")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=424_242)
    ap.add_argument("--teams", type=str, default="38,46,1,4,8,9,16,22,25,27")
    ap.add_argument("--scales", type=str, default="1.00,1.10,1.20,1.30")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    tids = tuple(int(x.strip()) for x in str(args.teams).split(",") if x.strip())
    scales = tuple(float(x.strip()) for x in str(args.scales).split(",") if x.strip())
    lines = run_scale_probe(years=max(1, int(args.years)), seed=int(args.seed), team_ids=tids, scales=scales)
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
