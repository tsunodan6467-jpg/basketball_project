"""
ロスター保護（trade.py 候補フィルタ）の長期観測。

`[TRADE]` 行から放出側チームの `get_cpu_club_strategy(...).strategy_tag` と、
移籍後ロスター上の放出選手（名前+OVR一致）の age / potential を突き合わせ、
rebuild / push / hold ごとの放出プロファイルを集計する。

本体は変更しない。`BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE` は import 前に既定 0.90 をセット。

例:
  python tools/cpu_auto_trade_roster_protect_multi_longrun.py --years 5 \\
    --seeds 424242,424243,424244,424245,424246 \\
    --out reports/cpu_auto_trade_roster_protect_y5_multi_seed_summary.txt
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import io
import os
import re
import sys
from collections import Counter, defaultdict
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


def _young_sa(p: Any) -> bool:
    age = int(getattr(p, "age", 99) or 99)
    pot = _pot_u(p)
    return age <= 22 and pot in ("S", "A")


def _hold_thin(p: Any) -> bool:
    age = int(getattr(p, "age", 99) or 99)
    return age <= 21 and _pot_u(p) == "S"


def _tag(team: Optional[Any]) -> str:
    if team is None:
        return "unknown"
    try:
        return str(get_cpu_club_strategy(team, season=None).strategy_tag)
    except Exception:
        return "unknown"


def _record_outgoing(
    stats: Dict[str, Any],
    team: Optional[Any],
    player: Optional[Any],
) -> None:
    if player is None:
        stats["out_missing_player"] = stats.get("out_missing_player", 0) + 1
        return
    tag = _tag(team)
    ovr = int(getattr(player, "ovr", 0) or 0)
    stats["out_total"] = stats.get("out_total", 0) + 1
    stats["by_sender_tag"][tag] = stats["by_sender_tag"].get(tag, 0) + 1

    if tag == "rebuild":
        stats["rebuild_out_total"] = stats.get("rebuild_out_total", 0) + 1
        if _young_sa(player):
            stats["rebuild_out_young_sa"] = stats.get("rebuild_out_young_sa", 0) + 1
    elif tag == "push":
        stats["push_out_total"] = stats.get("push_out_total", 0) + 1
        if ovr >= PUSH_TRADE_PROTECT_MIN_OVR:
            stats["push_out_high_ovr"] = stats.get("push_out_high_ovr", 0) + 1
    elif tag == "hold":
        stats["hold_out_total"] = stats.get("hold_out_total", 0) + 1
        if _hold_thin(player):
            stats["hold_out_thin_s"] = stats.get("hold_out_thin_s", 0) + 1
    else:
        stats["other_tag_out"] = stats.get("other_tag_out", 0) + 1


def observe_roster_protect_one_seed(*, years: int, seed: int) -> Dict[str, Any]:
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
        "by_sender_tag": {},
        "out_total": 0,
        "rebuild_out_total": 0,
        "rebuild_out_young_sa": 0,
        "push_out_total": 0,
        "push_out_high_ovr": 0,
        "hold_out_total": 0,
        "hold_out_thin_s": 0,
        "other_tag_out": 0,
        "out_missing_player": 0,
    }

    builtins.print = _capture_print
    try:
        for y in range(1, years + 1):
            year_ref[0] = y
            cap_before = len(captured)
            season = _run_season_quiet(teams, free_agents)
            free_agents = list(getattr(season, "free_agents", []) or [])
            # [TRADE] は conduct_trades（オフシーズン）でのみ出力される。
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
                _record_outgoing(stats, team_a, p_a)
                _record_outgoing(stats, team_b, p_b)
    finally:
        builtins.print = real_print

    # ratios
    def ratio(num: int, den: int) -> float:
        return round(100.0 * num / den, 2) if den else 0.0

    rt = stats.get("rebuild_out_total", 0)
    pt = stats.get("push_out_total", 0)
    ht = stats.get("hold_out_total", 0)
    stats["pct_rebuild_out_young_sa_of_rebuild_out"] = ratio(stats.get("rebuild_out_young_sa", 0), rt)
    stats["pct_push_out_high_ovr_of_push_out"] = ratio(stats.get("push_out_high_ovr", 0), pt)
    stats["pct_hold_out_thin_of_hold_out"] = ratio(stats.get("hold_out_thin_s", 0), ht)

    return stats


def _fmt_seed_block(st: Dict[str, Any]) -> List[str]:
    lines = [
        f"--- seed {st['seed']} ---",
        f"  n_trades={st['n_trades']}  by_year={dict(st.get('by_year', {}))}",
        f"  outgoing events (2 per trade): total={st.get('out_total', 0)}",
        f"  by_sender_tag: {st.get('by_sender_tag', {})}",
        f"  rebuild: out_total={st.get('rebuild_out_total', 0)}  young_sa_out={st.get('rebuild_out_young_sa', 0)}  "
        f"pct_young_sa_of_rebuild_out={st.get('pct_rebuild_out_young_sa_of_rebuild_out', 0)}%",
        f"  push: out_total={st.get('push_out_total', 0)}  ovr>={PUSH_TRADE_PROTECT_MIN_OVR}_out={st.get('push_out_high_ovr', 0)}  "
        f"pct_high_ovr_of_push_out={st.get('pct_push_out_high_ovr_of_push_out', 0)}%",
        f"  hold: out_total={st.get('hold_out_total', 0)}  thin_s_out={st.get('hold_out_thin_s', 0)}  "
        f"pct_thin_of_hold_out={st.get('pct_hold_out_thin_of_hold_out', 0)}%",
        f"  other_tag_out={st.get('other_tag_out', 0)}  missing_player_lookups={st.get('out_missing_player', 0)}",
    ]
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seeds", type=str, default="424242,424243,424244,424245,424246")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "cpu_auto_trade_roster_protect_y5_multi_seed_summary.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]

    all_rows: List[Dict[str, Any]] = []
    out_lines: List[str] = []
    out_lines.append("cpu_auto_trade_roster_protect_multi_longrun")
    out_lines.append(
        f"os.environ BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE={os.environ.get('BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE', '')!r}"
    )
    out_lines.append(f"years={years}  seeds={seeds}")
    out_lines.append("")
    out_lines.append("Outgoing side: strategy_tag of sender team at trade print time; player age/pot/ovr after swap (name+ovr lookup).")
    out_lines.append("")

    for sd in seeds:
        st = observe_roster_protect_one_seed(years=years, seed=sd)
        all_rows.append(st)
        out_lines.extend(_fmt_seed_block(st))
        out_lines.append("")

    def meanf(key: str) -> float:
        xs = [float(r.get(key, 0) or 0) for r in all_rows]
        return sum(xs) / len(xs) if xs else 0.0

    out_lines.append("=== Across seeds (mean of per-seed metrics) ===")
    for key in (
        "n_trades",
        "rebuild_out_total",
        "rebuild_out_young_sa",
        "pct_rebuild_out_young_sa_of_rebuild_out",
        "push_out_total",
        "push_out_high_ovr",
        "pct_push_out_high_ovr_of_push_out",
        "hold_out_total",
        "hold_out_thin_s",
    ):
        out_lines.append(f"  mean {key}: {meanf(key):.4f}")

    out_lines.append("")
    out_lines.append("Note: Before/after guard comparison not automated; prior posscale090 multi_seed had ~mean 24.6 trades/seed (5y) for reference.")
    text = "\n".join(out_lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
