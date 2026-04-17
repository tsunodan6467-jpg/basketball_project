"""
`POSITION_NEED_BONUS_SCALE` を環境変数で切り替え、複数 seed で CPU 自動トレード観測を比較する。

本体は import 時に `BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE` を読む（未設定時は `trade.py` の既定、現状 0.90）。
比較はサブプロセスごとにクリーンな import になるよう `--emit-metrics` を子で実行する。

例:
  python tools/cpu_auto_trade_position_need_scale_multi_compare.py \\
    --years 3 --seeds 424242,424243,424244,424245,424246 --scales 1.00,0.88 \\
    --out reports/cpu_auto_trade_position_need_scale_compare_y3.txt
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
THIS = Path(__file__).resolve()


def compute_metrics(years: int, seed: int) -> Dict[str, Any]:
    """同一プロセス内で trade のスケールは既に環境変数で確定している前提。"""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.cpu_auto_trade_acceptance_observe import observe_auto_trades
    from tools.cpu_auto_trade_value_breakdown_observe import observe_trade_value_breakdown

    years = int(years)
    seed = int(seed)

    lines_a: List[str] = []
    rows = observe_auto_trades(years=years, seed=seed, lines=lines_a)
    n_trades = len(rows)
    ovrs: List[int] = []
    ages: List[int] = []
    tags: List[str] = []
    for r in rows:
        for lab in ("a_gets_pb", "b_gets_pa"):
            o = r.get(f"{lab}_ovr")
            a = r.get(f"{lab}_age")
            tg = r.get(f"{lab}_tag")
            if o is not None:
                ovrs.append(int(o))
            if a is not None:
                ages.append(int(a))
            if tg is not None:
                tags.append(str(tg))

    mean_ovr = sum(ovrs) / len(ovrs) if ovrs else 0.0
    mean_age = sum(ages) / len(ages) if ages else 0.0
    mean_gain_a = sum(r["gain_a"] for r in rows) / n_trades if n_trades else 0.0
    mean_gain_b = sum(r["gain_b"] for r in rows) / n_trades if n_trades else 0.0

    lines_b: List[str] = []
    trades, mismatch = observe_trade_value_breakdown(years=years, seed=seed, lines=lines_b)
    ok = [t for t in trades if t.get("quad_found")]
    if ok:
        pos_a = sum(float(t["diff_parts_team_a_gain"]["position_need_bonus"]) for t in ok) / len(ok)
        pos_b = sum(float(t["diff_parts_team_b_gain"]["position_need_bonus"]) for t in ok) / len(ok)
    else:
        pos_a = 0.0
        pos_b = 0.0

    tc = Counter(tags)
    scale_env = os.environ.get("BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE", "")
    try:
        scale_eff = float(str(scale_env).strip()) if str(scale_env).strip() else float("nan")
    except ValueError:
        scale_eff = float("nan")

    return {
        "seed": seed,
        "years": years,
        "scale_env": scale_eff,
        "n_trades": n_trades,
        "mean_ovr_acquired": round(mean_ovr, 4),
        "mean_age_acquired": round(mean_age, 4),
        "mean_gain_a": round(mean_gain_a, 4),
        "mean_gain_b": round(mean_gain_b, 4),
        "position_need_mean_diff_a": round(pos_a, 4),
        "position_need_mean_diff_b": round(pos_b, 4),
        "position_need_mean_diff_avg": round((pos_a + pos_b) / 2.0, 4) if ok else 0.0,
        "breakdown_mismatch_evals": int(mismatch),
        "strategy_tag_push": int(tc.get("push", 0)),
        "strategy_tag_hold": int(tc.get("hold", 0)),
        "strategy_tag_rebuild": int(tc.get("rebuild", 0)),
    }


def _run_emit_subprocess(scale: float, years: int, seed: int) -> Dict[str, Any]:
    env = os.environ.copy()
    env["BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE"] = str(scale)
    cmd = [
        sys.executable,
        str(THIS),
        "--emit-metrics",
        "--years",
        str(years),
        "--seed",
        str(seed),
    ]
    proc = subprocess.run(
        cmd,
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"emit-metrics failed scale={scale} seed={seed} rc={proc.returncode}\n"
            f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
        )
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return dict(json.loads(line))


def run_matrix(
    *,
    years: int,
    seeds: List[int],
    scales: List[float],
) -> Tuple[List[Dict[str, Any]], str]:
    rows_out: List[Dict[str, Any]] = []
    for scale in scales:
        for seed in seeds:
            m = _run_emit_subprocess(scale, years, seed)
            m["scale"] = float(scale)
            rows_out.append(m)

    lines: List[str] = []
    lines.append("cpu_auto_trade_position_need_scale_multi_compare")
    lines.append(f"years={years}  scales={scales}  seeds={seeds}")
    lines.append("scale は subprocess 前に BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE を設定")
    lines.append("")
    lines.append(
        "seed\tscale\tn_trades\tmean_ovr\tmean_age\tpos_need_A\tpos_need_B\tpos_need_avg\tmean_ga\tmean_gb\tpush\thold\trebuild"
    )
    for r in sorted(rows_out, key=lambda x: (x["seed"], x["scale"])):
        lines.append(
            f"{r['seed']}\t{r['scale']:.2f}\t{r['n_trades']}\t{r['mean_ovr_acquired']:.4f}\t{r['mean_age_acquired']:.4f}\t"
            f"{r['position_need_mean_diff_a']:.4f}\t{r['position_need_mean_diff_b']:.4f}\t{r['position_need_mean_diff_avg']:.4f}\t"
            f"{r['mean_gain_a']:.4f}\t{r['mean_gain_b']:.4f}\t{r['strategy_tag_push']}\t{r['strategy_tag_hold']}\t{r['strategy_tag_rebuild']}"
        )

    def _avg(key: str, scale_filter: float) -> float:
        xs = [float(r[key]) for r in rows_out if abs(float(r["scale"]) - scale_filter) < 1e-6]
        return sum(xs) / len(xs) if xs else 0.0

    lines.append("")
    lines.append("Across seeds (simple mean of per-seed metrics):")
    for sc in scales:
        lines.append(
            f"  scale={sc:.2f}  avg n_trades={_avg('n_trades', sc):.2f}  avg mean_ovr={_avg('mean_ovr_acquired', sc):.3f}  "
            f"avg mean_age={_avg('mean_age_acquired', sc):.3f}  avg pos_need_avg={_avg('position_need_mean_diff_avg', sc):.4f}"
        )

    lines.append("")
    lines.append("Per-seed delta (0.88 - 1.00) for n_trades, mean_ovr, mean_age, pos_need_avg:")

    def _row(sd: int, sc: float) -> Dict[str, Any] | None:
        for r in rows_out:
            if int(r["seed"]) == sd and abs(float(r["scale"]) - sc) < 1e-6:
                return r
        return None

    for sd in seeds:
        a = _row(sd, 1.0)
        b = _row(sd, 0.88)
        if not a or not b:
            lines.append(f"  seed {sd}: missing row")
            continue
        lines.append(
            f"  seed {sd}: d_n={b['n_trades'] - a['n_trades']:+d}  d_ovr={b['mean_ovr_acquired'] - a['mean_ovr_acquired']:+.4f}  "
            f"d_age={b['mean_age_acquired'] - a['mean_age_acquired']:+.4f}  "
            f"d_pos={b['position_need_mean_diff_avg'] - a['position_need_mean_diff_avg']:+.4f}"
        )

    text = "\n".join(lines) + "\n"
    return rows_out, text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-metrics", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--seeds", type=str, default="424242,424243,424244,424245,424246")
    ap.add_argument("--scales", type=str, default="1.00,0.88")
    ap.add_argument("--out", type=Path, default=Path("reports") / "cpu_auto_trade_position_need_scale_compare.txt")
    args = ap.parse_args()

    if args.emit_metrics:
        m = compute_metrics(args.years, args.seed)
        print(json.dumps(m))
        return 0

    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    scales = [float(x.strip()) for x in str(args.scales).split(",") if x.strip()]
    _, text = run_matrix(years=int(args.years), seeds=seeds, scales=scales)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
