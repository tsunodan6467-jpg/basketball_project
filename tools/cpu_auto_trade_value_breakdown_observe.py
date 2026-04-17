"""
`trade._evaluate_trade_value` の内訳を、本体の bonus 関数を再利用して観測する。

方式: 本体の `_age_bonus` 等を import して内訳を再構成し、`_evaluate_trade_value` を一時ラップして
`conduct_trades` 成立直前の4連呼（gives/gets ×2チーム）を `[TRADE]` 行と突き合わせる。
本体ロジック・ファイルは変更しない。finally で必ず復元。

例:
  python tools/cpu_auto_trade_value_breakdown_observe.py --years 3 --seed 424242 \\
    --out reports/cpu_auto_trade_value_breakdown_y3_s424242.txt
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import io
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import basketball_sim.systems.trade as trade_mod  # noqa: E402
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

_PART_KEYS = (
    "ovr",
    "age_bonus",
    "potential_bonus",
    "contract_bonus",
    "position_need_bonus",
    "strategy_fit_bonus",
    "direction_ovr_bonus",
)


def _breakdown_parts(player: Any, team: Any, is_incoming: bool) -> Dict[str, float]:
    """`trade._evaluate_trade_value` と同じ項を、trade_mod の関数で算出（式の重複なし）。"""
    direction = trade_mod._get_team_direction(team)
    ovr = float(getattr(player, "ovr", 60))
    return {
        "ovr": ovr,
        "age_bonus": float(trade_mod._age_bonus(player, direction)),
        "potential_bonus": float(trade_mod._potential_bonus(player)),
        "contract_bonus": float(trade_mod._contract_bonus(player)),
        "position_need_bonus": float(trade_mod._position_need_bonus(player, team, is_incoming)),
        "strategy_fit_bonus": float(trade_mod._strategy_fit_bonus(player, team)),
        "direction_ovr_bonus": float(trade_mod._direction_ovr_bonus(player, direction)),
    }


def _player_sig(p: Any) -> Tuple[str, int]:
    return (str(getattr(p, "name", "")).strip(), int(getattr(p, "ovr", -1) or -1))


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


def _quad_chunk_matches(
    chunk: List[Dict[str, Any]],
    pa_sig: Tuple[str, int],
    pb_sig: Tuple[str, int],
    team_a_name: str,
    team_b_name: str,
) -> bool:
    want = (
        (pa_sig, team_a_name, False),
        (pb_sig, team_a_name, True),
        (pb_sig, team_b_name, False),
        (pa_sig, team_b_name, True),
    )
    if len(chunk) != 4:
        return False
    for i, (sig, tname, inc) in enumerate(want):
        r = chunk[i]
        if _player_sig(r["player"]) != sig:
            return False
        if str(r["team_name"]).strip() != str(tname).strip():
            return False
        if bool(r["is_incoming"]) != inc:
            return False
    return True


def _match_quad(
    ring: Deque[Dict[str, Any]],
    pa_sig: Tuple[str, int],
    pb_sig: Tuple[str, int],
    team_a_name: str,
    team_b_name: str,
) -> Optional[List[Dict[str, Any]]]:
    """成立直前の4連呼。通常はリング末尾4件（gain計算と print の間に他呼び出しなし）。"""
    seq = list(ring)
    n = len(seq)
    if n >= 4:
        tail = seq[-4:]
        if _quad_chunk_matches(tail, pa_sig, pb_sig, team_a_name, team_b_name):
            return tail
    if n < 4:
        return None
    lo = max(0, n - 400)
    for start in range(n - 4, lo - 1, -1):
        chunk = seq[start : start + 4]
        if _quad_chunk_matches(chunk, pa_sig, pb_sig, team_a_name, team_b_name):
            return chunk
    return None


def _append_trade_record_from_line(
    raw: str,
    year: int,
    teams: List[Any],
    ring: Deque[Dict[str, Any]],
    trades: List[Dict[str, Any]],
) -> None:
    m = _TRADE_LINE.match(raw.strip())
    if not m:
        trades.append({"year": year, "line": raw.strip(), "quad_found": False, "note": "parse_failed"})
        return
    ga = float(m.group("ga"))
    gb = float(m.group("gb"))
    oa = int(m.group("ovra"))
    ob = int(m.group("ovrb"))
    pa_n, pb_n = m.group("pa").strip(), m.group("pb").strip()
    ta_n, tb_n = m.group("a").strip(), m.group("b").strip()
    pa_sig = (pa_n, oa)
    pb_sig = (pb_n, ob)
    quad = _match_quad(ring, pa_sig, pb_sig, ta_n, tb_n)
    rec: Dict[str, Any] = {
        "year": year,
        "line": raw.strip(),
        "gain_a": ga,
        "gain_b": gb,
        "gain_a_line": ga,
        "gain_b_line": gb,
        "quad_found": quad is not None,
    }
    if quad is None:
        rec["note"] = "no_matching_eval_quad_in_ring"
        trades.append(rec)
        return
    ev_aa_out, ev_ab_in, ev_bb_out, ev_ba_in = quad
    parts_aa = ev_aa_out["parts"]
    parts_ab = ev_ab_in["parts"]
    parts_bb = ev_bb_out["parts"]
    parts_ba = ev_ba_in["parts"]
    tot_aa = ev_aa_out["official"]
    tot_ab = ev_ab_in["official"]
    tot_bb = ev_bb_out["official"]
    tot_ba = ev_ba_in["official"]
    gain_a_calc = tot_ab - tot_aa
    gain_b_calc = tot_ba - tot_bb
    rec["gain_a_calc"] = gain_a_calc
    rec["gain_b_calc"] = gain_b_calc
    rec["gain_a_delta_vs_line"] = abs(gain_a_calc - ga)
    rec["gain_b_delta_vs_line"] = abs(gain_b_calc - gb)
    d_a: Dict[str, float] = {}
    d_b: Dict[str, float] = {}
    for k in _PART_KEYS:
        d_a[k] = float(parts_ab[k]) - float(parts_aa[k])
        d_b[k] = float(parts_ba[k]) - float(parts_bb[k])
    rec["diff_parts_team_a_gain"] = d_a
    rec["diff_parts_team_b_gain"] = d_b
    rec["sum_diff_a"] = sum(d_a.values())
    rec["sum_diff_b"] = sum(d_b.values())
    p_a = ev_aa_out["player"]
    p_b = ev_ab_in["player"]
    rec["team_a"] = ta_n
    rec["team_b"] = tb_n
    rec["p_a"] = pa_n
    rec["p_b"] = pb_n
    rec["p_a_age"] = int(getattr(p_a, "age", 0) or 0)
    rec["p_b_age"] = int(getattr(p_b, "age", 0) or 0)
    rec["p_a_pot"] = str(getattr(p_a, "potential", "") or "")
    rec["p_b_pot"] = str(getattr(p_b, "potential", "") or "")
    ta = _find_team(teams, ta_n)
    tb = _find_team(teams, tb_n)
    rec["tag_a_gets_pb"] = (
        get_cpu_club_strategy(ta).strategy_tag if ta and not getattr(ta, "is_user_team", False) else None
    )
    rec["tag_b_gets_pa"] = (
        get_cpu_club_strategy(tb).strategy_tag if tb and not getattr(tb, "is_user_team", False) else None
    )
    trades.append(rec)


def observe_trade_value_breakdown(
    *, years: int, seed: int, lines: List[str]
) -> Tuple[List[Dict[str, Any]], int]:
    years = max(1, min(8, int(years)))
    seed = int(seed)
    real_print = builtins.print
    ring: Deque[Dict[str, Any]] = deque(maxlen=50_000)
    mismatch_evals = 0

    orig_eval = trade_mod._evaluate_trade_value

    def _wrapped_eval(player: Any, team: Any, is_incoming: bool) -> float:
        nonlocal mismatch_evals
        parts = _breakdown_parts(player, team, is_incoming)
        official = orig_eval(player, team, is_incoming)
        dbg = sum(parts.values())
        if abs(dbg - official) > 0.02:
            mismatch_evals += 1
        ring.append(
            {
                "player": player,
                "team": team,
                "team_name": getattr(team, "name", ""),
                "is_incoming": bool(is_incoming),
                "parts": parts,
                "official": float(official),
            }
        )
        return official

    sim_rng_mod.init_simulation_random(seed)
    with contextlib.redirect_stdout(io.StringIO()):
        teams = generate_teams()
    for t in teams:
        if hasattr(t, "is_user_team"):
            t.is_user_team = False
    free_agents: List[Any] = []
    sync_player_id_counter_from_world(teams, free_agents)

    trades: List[Dict[str, Any]] = []
    year_ref = [0]

    def _capture_print(*args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], str) and args[0].startswith("[TRADE]"):
            _append_trade_record_from_line(args[0], year_ref[0], teams, ring, trades)
        return real_print(*args, **kwargs)

    builtins.print = _capture_print
    trade_mod._evaluate_trade_value = _wrapped_eval
    try:
        for y in range(1, years + 1):
            year_ref[0] = y
            season = _run_season_quiet(teams, free_agents)
            free_agents = list(getattr(season, "free_agents", []) or [])
            _offseason_quiet(teams, free_agents)
    finally:
        trade_mod._evaluate_trade_value = orig_eval
        builtins.print = real_print

    lines.append(f"cpu_auto_trade_value_breakdown_observe | seed={seed} years={years}")
    lines.append(
        "Method: breakdown via trade_mod._age_bonus etc.; wrap _evaluate_trade_value; "
        "on each [TRADE] print, match ring tail (gain計算の4連呼の直後に print のみ)"
    )
    lines.append(f"Eval breakdown vs official mismatch count (|sum(parts)-official|>0.02): {mismatch_evals}")
    lines.append("")

    ok_trades = [t for t in trades if t.get("quad_found")]
    lines.append(f"Trades parsed from [TRADE]: {len(trades)}  |  quad matched to eval log: {len(ok_trades)}")
    if mismatch_evals:
        lines.append("(warning: some eval rows had part-sum drift vs official; see mismatch count above)")

    if not ok_trades:
        lines.append("No matched trades — ring correlation failed or zero trades.")
        return trades, mismatch_evals

    def _mean(keys: List[str], side: str) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for k in keys:
            vals = [float(t["diff_parts_team_a_gain" if side == "a" else "diff_parts_team_b_gain"][k]) for t in ok_trades]
            out[k] = sum(vals) / len(vals)
        return out

    mean_a = _mean(list(_PART_KEYS), "a")
    mean_b = _mean(list(_PART_KEYS), "b")
    lines.append("")
    lines.append("Aggregate: mean component diff (incoming - outgoing) toward each team’s gain")
    lines.append("  Team A gain = value(p_b at team_a, in) - value(p_a at team_a, out)")
    lines.append("  Team B gain = value(p_a at team_b, in) - value(p_b at team_b, out)")
    lines.append("")
    lines.append(f"  mean gain_a (line)={sum(t['gain_a'] for t in ok_trades)/len(ok_trades):.4f}  mean gain_b={sum(t['gain_b'] for t in ok_trades)/len(ok_trades):.4f}")
    lines.append("  mean diff parts — side A (gain_a):")
    for k in _PART_KEYS:
        lines.append(f"    {k}: {mean_a[k]:+.4f}")
    lines.append("  mean diff parts — side B (gain_b):")
    for k in _PART_KEYS:
        lines.append(f"    {k}: {mean_b[k]:+.4f}")

    abs_a = {k: abs(mean_a[k]) for k in _PART_KEYS}
    abs_b = {k: abs(mean_b[k]) for k in _PART_KEYS}
    top_a = max(_PART_KEYS, key=lambda k: abs_a[k])
    top_b = max(_PART_KEYS, key=lambda k: abs_b[k])
    lines.append("")
    lines.append(f"Largest |mean| component for gain_a: {top_a} ({mean_a[top_a]:+.4f})")
    lines.append(f"Largest |mean| component for gain_b: {top_b} ({mean_b[top_b]:+.4f})")

    lines.append("")
    lines.append("Per-trade (abbrev):")
    for t in ok_trades:
        lines.append("")
        lines.append(t["line"])
        lines.append(
            f"  y={t['year']} gain_a={t['gain_a']:.2f} gain_b={t['gain_b']:.2f} "
            f"|calcΔa={t.get('gain_a_delta_vs_line',0):.4f} calcΔb={t.get('gain_b_delta_vs_line',0):.4f} "
            f"| tags a_gets:{t.get('tag_a_gets_pb')} b_gets:{t.get('tag_b_gets_pa')}"
        )
        lines.append(
            f"  players: {t['p_a']} age={t['p_a_age']} pot={t['p_a_pot']} <-> {t['p_b']} age={t['p_b_age']} pot={t['p_b_pot']}"
        )
        da = t["diff_parts_team_a_gain"]
        db = t["diff_parts_team_b_gain"]
        lines.append(
            "  gain_a parts: "
            + " ".join(f"{k}={da[k]:+.2f}" for k in _PART_KEYS)
        )
        lines.append(
            "  gain_b parts: "
            + " ".join(f"{k}={db[k]:+.2f}" for k in _PART_KEYS)
        )

    return trades, mismatch_evals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--out", type=Path, default=Path("reports") / "cpu_auto_trade_value_breakdown.txt")
    args = ap.parse_args()
    lines: List[str] = []
    observe_trade_value_breakdown(years=int(args.years), seed=int(args.seed), lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
