"""
12 クラブパイロットを team_id 固定で年次追跡（観測専用・本体非改変）。

`generate_teams` → Season / Offseason を静かに完走し、各スナップショットで
`strategy_tag`、累積 trade_in / trade_out / FA 署名、直前スナップショットからの
増分、ロスター平均年齢・OVR を 12 チーム分だけ記録する。

例:
  python tools/club_profile_pilot_team_trace.py --years 3 --seed 424242 \\
    --out reports/club_profile_pilot_team_trace_y3_s424242.txt
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import Offseason  # noqa: E402
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.systems.cpu_club_strategy import get_cpu_club_strategy  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402

PILOT_IDS: Tuple[int, ...] = (1, 4, 8, 12, 13, 18, 21, 25, 29, 33, 38, 46)


def _cum_trade_in(team: Any) -> int:
    n = 0
    for r in getattr(team, "history_transactions", None) or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("transaction_type", "")).lower() != "trade":
            continue
        note = str(r.get("note", "") or "").lower()
        if "trade_in" in note or "acquired from" in note:
            n += 1
    return n


def _cum_trade_out(team: Any) -> int:
    n = 0
    for r in getattr(team, "history_transactions", None) or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("transaction_type", "")).lower() != "trade":
            continue
        note = str(r.get("note", "") or "").lower()
        if "trade_out" in note:
            n += 1
    return n


def _cum_fa_sign(team: Any) -> int:
    n = 0
    for r in getattr(team, "history_transactions", None) or []:
        if not isinstance(r, dict):
            continue
        tt = str(r.get("transaction_type", "")).lower()
        if tt in ("free_agent", "free_agent_sign"):
            n += 1
    return n


def _roster_mean_age_ovr(team: Any) -> Tuple[Optional[float], Optional[float]]:
    ps = list(getattr(team, "players", None) or [])
    if not ps:
        return None, None
    ages = [float(getattr(p, "age", 0) or 0) for p in ps]
    ovrs = [float(getattr(p, "ovr", 0) or 0) for p in ps]
    return sum(ages) / len(ages), sum(ovrs) / len(ovrs)


def _team_by_id(teams: List[Any], tid: int) -> Any:
    return next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)


def _run_season_quiet(teams: List[Any], free_agents: List[Any]) -> Season:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        season = Season(teams, free_agents)
        safety = 0
        cap = max(500, int(getattr(season, "total_rounds", 0) or 0) + 400)
        while not bool(getattr(season, "season_finished", False)):
            season.simulate_next_round()
            safety += 1
            if safety > cap:
                raise RuntimeError(f"season loop exceeded cap={cap}")
    return season


def _offseason_quiet(teams: List[Any], free_agents: List[Any]) -> Offseason:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        off = Offseason(teams, free_agents)
        off.run()
    return off


def _metrics(team: Any) -> Dict[str, Any]:
    ma, mo = _roster_mean_age_ovr(team)
    tin, tout = _cum_trade_in(team), _cum_trade_out(team)
    return {
        "tag": get_cpu_club_strategy(team).strategy_tag,
        "trade_in": tin,
        "trade_out": tout,
        "trade_any": tin + tout,
        "fa": _cum_fa_sign(team),
        "age_mean": ma,
        "ovr_mean": mo,
    }


def collect_trace_snapshots(*, years: int, seed: int) -> List[Dict[str, Any]]:
    """
    1 seed 分のスナップショット列を構造化データで返す（multi-seed 集計用）。

    各要素: {"label": str, "rows": {team_id: {name, tag, d_tin, d_tout, d_any, d_fa,
    cum_tin, cum_tout, cum_fa, age_mean, ovr_mean}}}
    d_* は opening 以外で整数。opening では d_* は None。
    """
    sim_rng_mod.init_simulation_random(int(seed))
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    snapshots: List[Dict[str, Any]] = []
    prev: Dict[int, Dict[str, Any]] = {}

    def snap(label: str) -> None:
        nonlocal prev
        rows: Dict[int, Dict[str, Any]] = {}
        for tid in PILOT_IDS:
            team = _team_by_id(teams, tid)
            m = _metrics(team)
            name = str(getattr(team, "name", "") or "")
            p = prev.get(tid)
            if p is None:
                d_tin = d_tout = d_any = d_fa = None
            else:
                d_tin = int(m["trade_in"]) - int(p["trade_in"])
                d_tout = int(m["trade_out"]) - int(p["trade_out"])
                d_any = int(m["trade_any"]) - int(p["trade_any"])
                d_fa = int(m["fa"]) - int(p["fa"])
            rows[tid] = {
                "name": name,
                "tag": m["tag"],
                "d_tin": d_tin,
                "d_tout": d_tout,
                "d_any": d_any,
                "d_fa": d_fa,
                "cum_tin": int(m["trade_in"]),
                "cum_tout": int(m["trade_out"]),
                "cum_fa": int(m["fa"]),
                "age_mean": m["age_mean"],
                "ovr_mean": m["ovr_mean"],
            }
            prev[tid] = {
                "trade_in": m["trade_in"],
                "trade_out": m["trade_out"],
                "trade_any": m["trade_any"],
                "fa": m["fa"],
            }
        snapshots.append({"label": label, "rows": rows})

    snap("opening")

    for y in range(1, years + 1):
        season = _run_season_quiet(teams, free_agents)
        free_agents = list(getattr(season, "free_agents", []) or [])
        snap(f"after_season_y{y}")

        _offseason_quiet(teams, free_agents)
        snap(f"after_offseason_y{y}")

    return snapshots


def run_trace(*, years: int, seed: int, lines: List[str]) -> None:
    lines.append(f"club_profile_pilot_team_trace | seed={seed} years={years}")
    lines.append(f"pilot_team_ids={list(PILOT_IDS)}")
    lines.append("")

    for block in collect_trace_snapshots(years=years, seed=seed):
        label = str(block["label"])
        rows: Dict[int, Dict[str, Any]] = block["rows"]
        lines.append(f"=== {label} ===")
        hdr = (
            "team_id name tag d_tin d_tout d_any d_fa "
            "cum_tin cum_tout cum_fa age_mean ovr_mean"
        )
        lines.append(hdr)
        for tid in PILOT_IDS:
            r = rows[tid]
            ag, ov = r["age_mean"], r["ovr_mean"]
            ag_s = f"{float(ag):.2f}" if ag is not None else "-"
            ov_s = f"{float(ov):.2f}" if ov is not None else "-"
            if r["d_tin"] is None:
                dcols = "- - - -"
            else:
                dcols = f"{r['d_tin']} {r['d_tout']} {r['d_any']} {r['d_fa']}"
            lines.append(
                f"{tid} {r['name']!r} {r['tag']} {dcols} "
                f"{r['cum_tin']} {r['cum_tout']} {r['cum_fa']} {ag_s} {ov_s}"
            )
        lines.append("")

    lines.append(
        "Notes: d_tin/d_tout/d_any/d_fa = delta vs previous row. "
        "trade_any = cum trade_in + cum trade_out (1 completed trade → 1 row for this team)."
    )
    lines.append(
        "Interpret push/hold/rebuild vs profile types using club_profile.py pilot comments; "
        "this file does not repeat per-club type labels."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-team pilot trace (12 clubs, by team_id)")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42_424_242)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "club_profile_pilot_team_trace.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    lines: List[str] = []
    run_trace(years=years, seed=int(args.seed), lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
