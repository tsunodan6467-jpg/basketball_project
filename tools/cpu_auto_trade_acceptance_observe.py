"""
オフ CPU 自動トレード（`trade.conduct_trades`）の成立観測。

本体は変更せず、実行中のみ builtins.print をラップして `[TRADE]` 行を捕捉する。
成立条件の数式は `basketball_sim/systems/trade.py` conduct_trades 内（gain / min_gain / OVR gap 等）に準拠。

例:
  python tools/cpu_auto_trade_acceptance_observe.py --years 3 --seed 424242 \\
    --out reports/cpu_auto_trade_acceptance_y3_s424242.txt
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import io
import re
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

_TRADE_LINE = re.compile(
    r"^\[TRADE\] (?P<a>.+?) traded (?P<pa>.+?) \(OVR:(?P<ovra>\d+)\) to (?P<b>.+?) for (?P<pb>.+?) \(OVR:(?P<ovrb>\d+)\) \| "
    r"gain_a=(?P<ga>[\d.]+) gain_b=(?P<gb>[\d.]+)"
)


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


def _find_player(teams: List[Any], name: str, ovr: int) -> Optional[Any]:
    name = str(name).strip()
    for t in teams:
        for p in getattr(t, "players", []) or []:
            if str(getattr(p, "name", "")).strip() == name and int(getattr(p, "ovr", -1) or -1) == int(ovr):
                return p
    return None


def _find_team(teams: List[Any], name: str) -> Optional[Any]:
    n = str(name).strip()
    for t in teams:
        if str(getattr(t, "name", "")).strip() == n:
            return t
    return None


def observe_auto_trades(*, years: int, seed: int, lines: List[str]) -> List[Dict[str, Any]]:
    years = max(1, min(8, int(years)))
    seed = int(seed)
    captured: List[str] = []
    real_print = builtins.print

    def _capture_print(*args: Any, **kwargs: Any) -> None:
        if args and isinstance(args[0], str) and args[0].startswith("[TRADE]"):
            captured.append(args[0])
        return real_print(*args, **kwargs)

    sim_rng_mod.init_simulation_random(seed)
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    rows: List[Dict[str, Any]] = []
    builtins.print = _capture_print
    try:
        for y in range(1, years + 1):
            captured.clear()
            season = _run_season_quiet(teams, free_agents)
            free_agents = list(getattr(season, "free_agents", []) or [])
            _offseason_quiet(teams, free_agents)
            for raw in captured:
                m = _TRADE_LINE.match(raw.strip())
                if not m:
                    continue
                ga = float(m.group("ga"))
                gb = float(m.group("gb"))
                oa = int(m.group("ovra"))
                ob = int(m.group("ovrb"))
                pa_n, pb_n = m.group("pa").strip(), m.group("pb").strip()
                ta_n, tb_n = m.group("a").strip(), m.group("b").strip()
                p_a = _find_player(teams, pa_n, oa)
                p_b = _find_player(teams, pb_n, ob)
                team_a = _find_team(teams, ta_n)
                team_b = _find_team(teams, tb_n)
                row: Dict[str, Any] = {
                    "year": y,
                    "line": raw.strip(),
                    "gain_a": ga,
                    "gain_b": gb,
                    "balance_abs": abs(ga - gb),
                }
                for side, p, team_recv, g in (
                    ("a_gets_pb", p_b, team_a, ga),
                    ("b_gets_pa", p_a, team_b, gb),
                ):
                    if p is None or team_recv is None:
                        row[f"{side}_age"] = None
                        row[f"{side}_tag"] = None
                        continue
                    row[f"{side}_age"] = int(getattr(p, "age", 0) or 0)
                    row[f"{side}_ovr"] = int(getattr(p, "ovr", 0) or 0)
                    row[f"{side}_pot"] = str(getattr(p, "potential", "") or "")
                    row[f"{side}_tag"] = (
                        get_cpu_club_strategy(team_recv).strategy_tag
                        if not bool(getattr(team_recv, "is_user_team", False))
                        else "user"
                    )
                    row[f"{side}_gain"] = g
                rows.append(row)
    finally:
        builtins.print = real_print

    lines.append(f"cpu_auto_trade_acceptance_observe | seed={seed} years={years}")
    lines.append("Source: trade.conduct_trades — captured lines starting with [TRADE]")
    lines.append("")
    lines.append("conduct_trades 成立条件（trade.py 要約）:")
    lines.append("  1) 参加チームは勝敗に応じた確率で選ばれる")
    lines.append("  2) tradeable: ルーキー契約でない / コアでない / OVR>=MIN_TRADE_OVR(58)")
    lines.append("  3) rebuilding なら若手高ポテ(OVR>=68,<=22,S/A)を候補から除外")
    lines.append("  4) 候補は評価値で昇順ソートし先頭12、シャッフル後ペア探索")
    lines.append("  5) |OVR差|<=MAX_TRADE_OVR_GAP(8), 給与吸収, 日本籍ルール")
    lines.append("  6) gain_* = gets - gives（_evaluate_trade_value）; min_gain = _get_min_gain_threshold(再建1.0/win_now1.2/他1.0)")
    lines.append("  7) gain_a>=min_a かつ gain_b>=min_b かつ |gain_a-gain_b|<=14 で成立")
    lines.append("")
    lines.append(f"Total [TRADE] events captured: {len(rows)}")
    if not rows:
        lines.append("(none — try longer years or different seed)")
        return rows

    for r in rows:
        lines.append("")
        lines.append(r["line"])
        lines.append(
            f"  year={r['year']}  gain_a={r['gain_a']:.2f} gain_b={r['gain_b']:.2f} |gain_a-gain_b|={r['balance_abs']:.2f}"
        )
        for lab in ("a_gets_pb", "b_gets_pa"):
            if r.get(f"{lab}_age") is not None:
                lines.append(
                    f"  {lab}: age={r[f'{lab}_age']} ovr={r.get(f'{lab}_ovr')} pot={r.get(f'{lab}_pot')} "
                    f"strategy_tag={r.get(f'{lab}_tag')}"
                )

    ages_pb = [float(r["a_gets_pb_age"]) for r in rows if r.get("a_gets_pb_age") is not None]
    ages_pa = [float(r["b_gets_pa_age"]) for r in rows if r.get("b_gets_pa_age") is not None]
    all_age = ages_pb + ages_pa
    lines.append("")
    lines.append("Aggregate (acquired players both sides):")
    if all_age:
        lines.append(f"  n_acquisitions={len(all_age)}  mean_age={sum(all_age)/len(all_age):.2f}")
    lines.append(f"  mean_gain_a={sum(r['gain_a'] for r in rows)/len(rows):.3f}  mean_gain_b={sum(r['gain_b'] for r in rows)/len(rows):.3f}")
    lines.append(f"  mean|gain_a-gain_b|={sum(r['balance_abs'] for r in rows)/len(rows):.3f}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--out", type=Path, default=Path("reports") / "cpu_auto_trade_acceptance.txt")
    args = ap.parse_args()
    lines: List[str] = []
    observe_auto_trades(years=int(args.years), seed=int(args.seed), lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
