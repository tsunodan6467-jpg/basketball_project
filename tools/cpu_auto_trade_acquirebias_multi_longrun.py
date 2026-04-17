"""
CPU 獲得資産優先（incoming acquire バイアス等）の長期観測。

`[TRADE]` をオフシーズン後に捕捉し、取得側チームの strategy_tag と
移籍後ロスター上の「受け取った」選手（名前+ログ OVR）の属性を集計する。

本体は変更しない。import 前に POSITION_NEED_BONUS_SCALE 既定 0.90。

例:
  $env:BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE='0.90'
  python tools/cpu_auto_trade_acquirebias_multi_longrun.py --years 5 \\
    --seeds 424242,424243,424244,424245,424246 \\
    --out reports/cpu_auto_trade_acquirebias_y5_multi_seed_summary.txt
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import io
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE", "0.90")

from basketball_sim.models.offseason import Offseason  # noqa: E402
from basketball_sim.models.season import Season  # noqa: E402
from basketball_sim.systems.cpu_club_strategy import get_cpu_club_strategy  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.systems.trade import PUSH_TRADE_PROTECT_MIN_OVR  # noqa: E402
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


def _pot_u(p: Any) -> str:
    return str(getattr(p, "potential", "C") or "C").upper()


def _tag(team: Optional[Any]) -> str:
    if team is None:
        return "unknown"
    try:
        return str(get_cpu_club_strategy(team, season=None).strategy_tag)
    except Exception:
        return "unknown"


def _rebuild_sab24(p: Any) -> bool:
    age = int(getattr(p, "age", 99) or 99)
    return age <= 24 and _pot_u(p) in ("S", "A", "B")


def _rebuild_sa22(p: Any) -> bool:
    age = int(getattr(p, "age", 99) or 99)
    return age <= 22 and _pot_u(p) in ("S", "A")


def _hold_mid_band(p: Any) -> bool:
    """hold 参考: 極端な若手高ポテ／超高 OVR 以外の中間帯（観測用の粗い定義）。"""
    age = int(getattr(p, "age", 99) or 99)
    ovr = int(getattr(p, "ovr", 0) or 0)
    return 24 <= age <= 29 and 64 <= ovr <= 72


def _record_incoming(stats: Dict[str, Any], team: Optional[Any], player: Optional[Any]) -> None:
    if player is None:
        stats["in_missing_player"] = stats.get("in_missing_player", 0) + 1
        return
    tag = _tag(team)
    ovr = int(getattr(player, "ovr", 0) or 0)
    age = int(getattr(player, "age", 0) or 0)
    stats["in_total"] = stats.get("in_total", 0) + 1
    stats["by_acquirer_tag"][tag] = stats["by_acquirer_tag"].get(tag, 0) + 1

    if tag == "rebuild":
        stats["rebuild_in_total"] = stats.get("rebuild_in_total", 0) + 1
        stats["rebuild_sum_ovr"] = stats.get("rebuild_sum_ovr", 0) + ovr
        stats["rebuild_sum_age"] = stats.get("rebuild_sum_age", 0) + age
        if _rebuild_sab24(player):
            stats["rebuild_in_sab24"] = stats.get("rebuild_in_sab24", 0) + 1
        if _rebuild_sa22(player):
            stats["rebuild_in_sa22"] = stats.get("rebuild_in_sa22", 0) + 1
    elif tag == "push":
        stats["push_in_total"] = stats.get("push_in_total", 0) + 1
        stats["push_sum_ovr"] = stats.get("push_sum_ovr", 0) + ovr
        stats["push_sum_age"] = stats.get("push_sum_age", 0) + age
        if ovr >= PUSH_TRADE_PROTECT_MIN_OVR:
            stats["push_in_ge73"] = stats.get("push_in_ge73", 0) + 1
        if ovr >= 70:
            stats["push_in_ge70"] = stats.get("push_in_ge70", 0) + 1
    elif tag == "hold":
        stats["hold_in_total"] = stats.get("hold_in_total", 0) + 1
        stats["hold_sum_ovr"] = stats.get("hold_sum_ovr", 0) + ovr
        stats["hold_sum_age"] = stats.get("hold_sum_age", 0) + age
        if _hold_mid_band(player):
            stats["hold_in_mid_band"] = stats.get("hold_in_mid_band", 0) + 1
    else:
        stats["other_tag_in"] = stats.get("other_tag_in", 0) + 1


def observe_acquirebias_one_seed(*, years: int, seed: int) -> Dict[str, Any]:
    years = max(1, min(8, int(years)))
    seed = int(seed)
    real_print = builtins.print
    captured: List[Tuple[int, str]] = []
    year_ref = [0]

    def _capture_print(*args: Any, **kwargs: Any) -> None:
        if args and isinstance(args[0], str) and args[0].startswith("[TRADE]"):
            captured.append((year_ref[0], args[0]))
        return real_print(*args, **kwargs)

    sim_rng_mod.init_simulation_random(seed)
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    stats: Dict[str, Any] = {
        "seed": seed,
        "years": years,
        "n_trades": 0,
        "by_year": Counter(),
        "by_acquirer_tag": {},
        "in_total": 0,
        "rebuild_in_total": 0,
        "rebuild_in_sab24": 0,
        "rebuild_in_sa22": 0,
        "rebuild_sum_ovr": 0,
        "rebuild_sum_age": 0,
        "push_in_total": 0,
        "push_in_ge73": 0,
        "push_in_ge70": 0,
        "push_sum_ovr": 0,
        "push_sum_age": 0,
        "hold_in_total": 0,
        "hold_in_mid_band": 0,
        "hold_sum_ovr": 0,
        "hold_sum_age": 0,
        "other_tag_in": 0,
        "in_missing_player": 0,
    }

    builtins.print = _capture_print
    try:
        for y in range(1, years + 1):
            year_ref[0] = y
            cap_before = len(captured)
            season = _run_season_quiet(teams, free_agents)
            free_agents = list(getattr(season, "free_agents", []) or [])
            _offseason_quiet(teams, free_agents)
            for _yr, raw in captured[cap_before:]:
                m = _TRADE_LINE.match(raw.strip())
                if not m:
                    continue
                stats["n_trades"] += 1
                stats["by_year"][y] += 1
                pa_n = m.group("pa").strip()
                pb_n = m.group("pb").strip()
                oa = int(m.group("ovra"))
                ob = int(m.group("ovrb"))
                ta_n = m.group("a").strip()
                tb_n = m.group("b").strip()
                team_a = _find_team(teams, ta_n)
                team_b = _find_team(teams, tb_n)
                p_a = _find_player(teams, pa_n, oa)
                p_b = _find_player(teams, pb_n, ob)
                # A sends p_a, receives p_b; B sends p_b, receives p_a
                _record_incoming(stats, team_a, p_b)
                _record_incoming(stats, team_b, p_a)
    finally:
        builtins.print = real_print

    def ratio(num: int, den: int) -> float:
        return round(100.0 * num / den, 2) if den else 0.0

    rt = stats.get("rebuild_in_total", 0)
    pt = stats.get("push_in_total", 0)
    ht = stats.get("hold_in_total", 0)
    stats["pct_rebuild_sab24"] = ratio(stats.get("rebuild_in_sab24", 0), rt)
    stats["pct_rebuild_sa22"] = ratio(stats.get("rebuild_in_sa22", 0), rt)
    stats["pct_push_ge73"] = ratio(stats.get("push_in_ge73", 0), pt)
    stats["pct_push_ge70"] = ratio(stats.get("push_in_ge70", 0), pt)
    stats["pct_hold_mid"] = ratio(stats.get("hold_in_mid_band", 0), ht)
    stats["rebuild_mean_ovr"] = round(stats["rebuild_sum_ovr"] / rt, 2) if rt else 0.0
    stats["rebuild_mean_age"] = round(stats["rebuild_sum_age"] / rt, 2) if rt else 0.0
    stats["push_mean_ovr"] = round(stats["push_sum_ovr"] / pt, 2) if pt else 0.0
    stats["push_mean_age"] = round(stats["push_sum_age"] / pt, 2) if pt else 0.0
    stats["hold_mean_ovr"] = round(stats["hold_sum_ovr"] / ht, 2) if ht else 0.0
    stats["hold_mean_age"] = round(stats["hold_sum_age"] / ht, 2) if ht else 0.0

    return stats


def _fmt_seed_block(st: Dict[str, Any]) -> List[str]:
    return [
        f"--- seed {st['seed']} ---",
        f"  n_trades={st['n_trades']}  by_year={dict(st.get('by_year', {}))}",
        f"  incoming events (2 per trade): total={st.get('in_total', 0)}",
        f"  by_acquirer_tag: {st.get('by_acquirer_tag', {})}",
        f"  rebuild acquire: n={st.get('rebuild_in_total', 0)}  "
        f"sab24={st.get('rebuild_in_sab24', 0)} ({st.get('pct_rebuild_sab24', 0)}%)  "
        f"sa22={st.get('rebuild_in_sa22', 0)} ({st.get('pct_rebuild_sa22', 0)}%)  "
        f"mean_ovr={st.get('rebuild_mean_ovr', 0)} mean_age={st.get('rebuild_mean_age', 0)}",
        f"  push acquire: n={st.get('push_in_total', 0)}  "
        f"ge73={st.get('push_in_ge73', 0)} ({st.get('pct_push_ge73', 0)}%)  "
        f"ge70={st.get('push_in_ge70', 0)} ({st.get('pct_push_ge70', 0)}%)  "
        f"mean_ovr={st.get('push_mean_ovr', 0)} mean_age={st.get('push_mean_age', 0)}",
        f"  hold acquire: n={st.get('hold_in_total', 0)}  "
        f"mid_band(age24-29&ovr64-72)={st.get('hold_in_mid_band', 0)} ({st.get('pct_hold_mid', 0)}%)  "
        f"mean_ovr={st.get('hold_mean_ovr', 0)} mean_age={st.get('hold_mean_age', 0)}",
        f"  other_tag_in={st.get('other_tag_in', 0)}  missing_player_lookups={st.get('in_missing_player', 0)}",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seeds", type=str, default="424242,424243,424244,424245,424246")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "cpu_auto_trade_acquirebias_y5_multi_seed_summary.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]

    all_rows: List[Dict[str, Any]] = []
    out_lines: List[str] = []
    out_lines.append("cpu_auto_trade_acquirebias_multi_longrun")
    out_lines.append(
        f"os.environ BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE={os.environ.get('BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE', '')!r}"
    )
    out_lines.append(f"years={years}  seeds={seeds}")
    out_lines.append("")
    out_lines.append(
        "Incoming: acquirer's strategy_tag; player received after trade (name+OVR on roster). "
        "hold mid_band = age 24-29 and ovr 64-72 (observation shorthand)."
    )
    out_lines.append("")

    for sd in seeds:
        st = observe_acquirebias_one_seed(years=years, seed=sd)
        all_rows.append(st)
        out_lines.extend(_fmt_seed_block(st))
        out_lines.append("")

    def meanf(key: str) -> float:
        xs = [float(r.get(key, 0) or 0) for r in all_rows]
        return sum(xs) / len(xs) if xs else 0.0

    out_lines.append("=== Across seeds (mean of per-seed metrics) ===")
    for key in (
        "n_trades",
        "rebuild_in_total",
        "rebuild_in_sab24",
        "pct_rebuild_sab24",
        "rebuild_in_sa22",
        "pct_rebuild_sa22",
        "push_in_total",
        "push_in_ge73",
        "pct_push_ge73",
        "push_in_ge70",
        "pct_push_ge70",
        "hold_in_total",
        "hold_in_mid_band",
        "pct_hold_mid",
        "rebuild_mean_ovr",
        "rebuild_mean_age",
        "push_mean_ovr",
        "push_mean_age",
    ):
        out_lines.append(f"  mean {key}: {meanf(key):.4f}")

    out_lines.append("")
    out_lines.append(
        "Note: Strict before/after (pre-acquire-bias) not automated. "
        "Prior assetrule outgoing 5y5s ~mean n_trades 27.6/seed same seeds (reference)."
    )
    text = "\n".join(out_lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
