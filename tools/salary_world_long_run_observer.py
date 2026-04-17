"""
長期進行での金額世界の統合観測（CLI・非対話）。

例:
  python tools/salary_world_long_run_observer.py --years 5 --seed 424242 \\
    --out reports/salary_world_long_run.txt
"""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# プロジェクトルートをパスに追加
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import Offseason  # noqa: E402
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.utils import sim_rng as sim_rng_mod  # noqa: E402


def _pct(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


def _summarize(vals: List[int]) -> Tuple[float, float, float, float, float]:
    xs = sorted(float(x) for x in vals)
    return (_pct(xs, 0.0), _pct(xs, 0.25), _pct(xs, 0.5), _pct(xs, 0.75), _pct(xs, 1.0))


def _player_snap(p: object, team_id: Optional[int]) -> Dict[str, Any]:
    note = str(getattr(p, "acquisition_note", "") or "")
    draft_kind = "auction" if "auction_draft" in note else ("snake" if "snake_draft" in note else "")
    return {
        "player_id": int(getattr(p, "player_id", -1)),
        "name": str(getattr(p, "name", "")),
        "team_id": team_id,
        "salary": int(getattr(p, "salary", 0) or 0),
        "locked": int(getattr(p, "draft_rookie_locked_salary", 0) or 0),
        "is_rookie": bool(getattr(p, "is_draft_rookie_contract", False)),
        "cy": int(getattr(p, "contract_years_left", 0) or 0),
        "age": int(getattr(p, "age", 0) or 0),
        "nat": str(getattr(p, "nationality", "") or ""),
        "ovr": int(getattr(p, "ovr", 0) or 0),
        "note": note[:120],
        "draft_kind": draft_kind,
    }


def _snapshot_world(teams: List[Any], free_agents: List[Any]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for t in teams:
        tid = int(getattr(t, "team_id", 0) or 0)
        for p in getattr(t, "players", []) or []:
            out[int(getattr(p, "player_id", -1))] = _player_snap(p, tid)
    for p in free_agents:
        out[int(getattr(p, "player_id", -1))] = _player_snap(p, None)
    return out


def _iter_rostered_players(teams: List[Any]) -> Iterable[Tuple[Any, int, int]]:
    for t in teams:
        lvl = int(getattr(t, "league_level", 3) or 3)
        tid = int(getattr(t, "team_id", 0) or 0)
        for p in getattr(t, "players", []) or []:
            yield p, lvl, tid


@dataclass
class RookieTrack:
    player_id: int
    name: str
    draft_kind: str
    join_label: str
    salaries_by_year: Dict[str, int] = field(default_factory=dict)
    team_ids_by_year: Dict[str, Optional[int]] = field(default_factory=dict)
    traded_flags: Dict[str, bool] = field(default_factory=dict)
    salary_mismatch_flags: Dict[str, bool] = field(default_factory=dict)


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


def observe(
    *,
    years: int,
    seed: int,
    lines: List[str],
) -> None:
    sim_rng_mod.init_simulation_random(int(seed))
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    rookie_watch: Dict[int, RookieTrack] = {}
    prev_snap: Optional[Dict[int, Dict[str, Any]]] = None

    def label_opening() -> str:
        return "opening"

    def label_after_off(y: int) -> str:
        return f"after_offseason_y{y}"

    def record_metrics(tag: str) -> None:
        nonlocal prev_snap, rookie_watch
        snap = _snapshot_world(teams, free_agents)
        lines.append(f"\n=== {tag} ===")

        for lvl in (1, 2, 3):
            payrolls: List[int] = []
            sal_lv: List[int] = []
            for t in teams:
                if int(getattr(t, "league_level", 3) or 3) != lvl:
                    continue
                ps = list(getattr(t, "players", []) or [])
                payrolls.append(sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in ps))
                for p in ps:
                    sal_lv.append(max(0, int(getattr(p, "salary", 0) or 0)))
            if payrolls:
                a, b, c, d, e = _summarize(payrolls)
                lines.append(
                    f"D{lvl} team_payroll yen: min={a:,.0f} p25={b:,.0f} p50={c:,.0f} p75={d:,.0f} max={e:,.0f} (n={len(payrolls)})"
                )
            if sal_lv:
                a, b, c, d, e = _summarize(sal_lv)
                lines.append(
                    f"D{lvl} player_salary yen: min={a:,.0f} p25={b:,.0f} p50={c:,.0f} p75={d:,.0f} max={e:,.0f} (n={len(sal_lv)})"
                )

        d1_under_1m = 0
        d2_under_500k = 0
        d3_under_500k = 0
        rookie_salary_drift: List[str] = []
        rookie_trade: List[str] = []
        young_high: List[str] = []

        for p, lvl, tid in _iter_rostered_players(teams):
            sal = int(getattr(p, "salary", 0) or 0)
            if lvl == 1 and 0 < sal < 1_000_000:
                d1_under_1m += 1
            if lvl in (2, 3) and 0 < sal < 500_000:
                if lvl == 2:
                    d2_under_500k += 1
                else:
                    d3_under_500k += 1
            if bool(getattr(p, "is_draft_rookie_contract", False)):
                lock = int(getattr(p, "draft_rookie_locked_salary", 0) or 0)
                if lock > 0 and sal != lock:
                    rookie_salary_drift.append(
                        f"pid={p.player_id} name={p.name} sal={sal:,} lock={lock:,} cy={getattr(p,'contract_years_left',0)}"
                    )
                pid = int(p.player_id)
                if pid not in rookie_watch:
                    dk = "auction" if "auction_draft" in str(getattr(p, "acquisition_note", "")) else (
                        "snake" if "snake_draft" in str(getattr(p, "acquisition_note", "")) else "?"
                    )
                    rookie_watch[pid] = RookieTrack(
                        player_id=pid,
                        name=str(p.name),
                        draft_kind=dk,
                        join_label=tag,
                    )
                rt = rookie_watch[pid]
                rt.salaries_by_year[tag] = sal
                rt.team_ids_by_year[tag] = tid
                if prev_snap is not None and pid in prev_snap:
                    was = prev_snap[pid]
                    if was.get("is_rookie") and was.get("team_id") != tid:
                        rt.traded_flags[tag] = True
                        rookie_trade.append(f"pid={pid} {p.name} {was.get('team_id')} -> {tid} @ {tag}")
                rt.salary_mismatch_flags[tag] = bool(lock > 0 and sal != lock)

        roster_300k = 0
        fa_300k = 0
        for _p, _lvl, _tid in _iter_rostered_players(teams):
            if int(getattr(_p, "salary", 0) or 0) == 300_000:
                roster_300k += 1
        for _p in free_agents:
            if int(getattr(_p, "salary", 0) or 0) == 300_000:
                fa_300k += 1
        lines.append(
            f"Low bucket: salary==300_000 roster={roster_300k} FA_only={fa_300k} | "
            f"D1<1M={d1_under_1m} D2<500k={d2_under_500k} D3<500k={d3_under_500k}"
        )

        for lvl_y in (2, 3):
            xs_y: List[int] = []
            for p_y, lv_y, _ in _iter_rostered_players(teams):
                if int(lv_y) != int(lvl_y):
                    continue
                age_y = int(getattr(p_y, "age", 0) or 0)
                if 18 <= age_y <= 23:
                    xs_y.append(max(0, int(getattr(p_y, "salary", 0) or 0)))
            if len(xs_y) >= 3:
                lines.append(
                    f"D{lvl_y} age 18-23 salary median={statistics.median(xs_y):,.0f} (n={len(xs_y)})"
                )
            elif xs_y:
                lines.append(f"D{lvl_y} age 18-23 salary (sparse n={len(xs_y)})")
        if rookie_salary_drift:
            lines.append(f"ROOKIE salary != locked ({len(rookie_salary_drift)}):")
            for row in rookie_salary_drift[:12]:
                lines.append(f"  {row}")
        else:
            lines.append("ROOKIE salary vs locked: no mismatches on rosters.")
        if rookie_trade:
            lines.append(f"ROOKIE trades detected ({len(rookie_trade)}):")
            for row in rookie_trade[:12]:
                lines.append(f"  {row}")
        else:
            lines.append("ROOKIE mid-lock trades (team change while rookie): none.")

        for band_lo, band_hi, label in ((18, 20, "18-20"), (21, 23, "21-23")):
            by_nat: Dict[str, List[int]] = {}
            for p, lvl, _ in _iter_rostered_players(teams):
                if lvl != 1:
                    continue
                age = int(getattr(p, "age", 0) or 0)
                if not (band_lo <= age <= band_hi):
                    continue
                nat = str(getattr(p, "nationality", "") or "Other")
                by_nat.setdefault(nat, []).append(max(0, int(getattr(p, "salary", 0) or 0)))
            parts = []
            for nat, xs in sorted(by_nat.items(), key=lambda kv: -len(kv[1])):
                if len(xs) < 3:
                    continue
                parts.append(f"{nat}:n={len(xs)} med={statistics.median(xs):,.0f}")
            lines.append(f"D1 age {label} salary med summary: " + (" | ".join(parts) if parts else "(sparse)"))

        for p, lvl, tid in _iter_rostered_players(teams):
            age = int(getattr(p, "age", 0) or 0)
            sal = int(getattr(p, "salary", 0) or 0)
            if age <= 23 and sal >= 120_000_000 and not bool(getattr(p, "is_draft_rookie_contract", False)):
                young_high.append(
                    f"pid={p.player_id} age={age} nat={getattr(p,'nationality','')} "
                    f"ovr={getattr(p,'ovr',0)} sal={sal:,} D{lvl} tid={tid}"
                )
        lines.append(f"Youth high earners age<=23 sal>=120M non-rookie (sample up to 8): {len(young_high)}")
        for row in young_high[:8]:
            lines.append(f"  {row}")

        prev_snap = snap

    lines.append(f"\nCONFIG seed={seed} years={years}")

    record_metrics(label_opening())

    for y in range(1, years + 1):
        lines.append(f"\n--- Season sim year {y} ---")
        season = _run_season_quiet(teams, free_agents)
        free_agents = list(getattr(season, "free_agents", []) or [])

        lines.append(f"\n--- Offseason run year {y} ---")
        _offseason_quiet(teams, free_agents)

        record_metrics(label_after_off(y))

    lines.append("\n=== Rookie cohort (players ever flagged draft rookie in snap) ===")
    for rt in sorted(rookie_watch.values(), key=lambda r: r.player_id)[:24]:
        lines.append(
            f"pid={rt.player_id} {rt.name} kind={rt.draft_kind} join={rt.join_label} "
            f"salaries={rt.salaries_by_year} teams={rt.team_ids_by_year} traded={rt.traded_flags}"
        )
    if len(rookie_watch) > 24:
        lines.append(f"... ({len(rookie_watch) - 24} more tracked rookies omitted)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Salary world long-run observer")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42_424_242)
    ap.add_argument("--out", type=Path, default=Path("reports") / "salary_world_long_run.txt")
    args = ap.parse_args()

    lines: List[str] = []
    observe(years=max(1, min(8, int(args.years))), seed=int(args.seed), lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
