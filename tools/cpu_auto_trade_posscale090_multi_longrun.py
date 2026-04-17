"""
`BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE=0.90` 固定で、複数 seed・複数年の
CPU 自動トレード観測を順に実行し、1 本のサマリーテキストにまとめる。

各 seed ごとに:
  - cpu_auto_trade_acceptance_observe（成立件数・取得側 OVR/年齢・tag・低OVR比率）
  - cpu_auto_trade_value_breakdown_observe（position_need 平均寄与・mean gain）

例:
  python tools/cpu_auto_trade_posscale090_multi_longrun.py --years 5 \\
    --seeds 424242,424243,424244,424245,424246 \\
    --out reports/cpu_auto_trade_posscale090_y5_multi_seed_summary.txt
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = ROOT / "tools" / "cpu_auto_trade_acceptance_observe.py"
BDOWN = ROOT / "tools" / "cpu_auto_trade_value_breakdown_observe.py"


def _parse_acceptance(path: Path) -> Dict[str, Any]:
    t = path.read_text(encoding="utf-8")
    n = int(re.search(r"Total \[TRADE\] events captured: (\d+)", t).group(1))
    years = [int(m.group(1)) for m in re.finditer(r"  year=(\d+) ", t)]
    yc = dict(Counter(years))
    ovrs = [int(x) for x in re.findall(r"(?:a_gets_pb|b_gets_pa):.*\bovr=(\d+)", t)]
    ages = [int(x) for x in re.findall(r"(?:a_gets_pb|b_gets_pa): age=(\d+)", t)]
    tags = re.findall(r"strategy_tag=(\w+)", t)
    tc = Counter(tags)
    def pct(th: int) -> float:
        if not ovrs:
            return 0.0
        return 100.0 * sum(1 for o in ovrs if o <= th) / len(ovrs)
    so = sorted(ovrs)
    sa = sorted(ages)
    med_o = so[len(so) // 2] if so else None
    med_a = sa[len(sa) // 2] if sa else None
    return {
        "n_trades": n,
        "year_counts": yc,
        "n_acquisitions": len(ovrs),
        "mean_ovr": round(sum(ovrs) / len(ovrs), 4) if ovrs else 0.0,
        "median_ovr": med_o,
        "mean_age": round(sum(ages) / len(ages), 4) if ages else 0.0,
        "median_age": med_a,
        "pct_ovr_le_58": round(pct(58), 2),
        "pct_ovr_le_60": round(pct(60), 2),
        "pct_ovr_le_62": round(pct(62), 2),
        "tag_push": int(tc.get("push", 0)),
        "tag_hold": int(tc.get("hold", 0)),
        "tag_rebuild": int(tc.get("rebuild", 0)),
    }


def _parse_breakdown(path: Path) -> Dict[str, float]:
    t = path.read_text(encoding="utf-8")
    m = re.search(r"mean gain_a \(line\)=([\d.]+)\s+mean gain_b=([\d.]+)", t)
    ga = float(m.group(1)) if m else 0.0
    gb = float(m.group(2)) if m else 0.0
    ma = re.search(r"mean diff parts — side A \(gain_a\):.*?position_need_bonus:\s*([+-]?[\d.]+)", t, re.S)
    mb = re.search(r"mean diff parts — side B \(gain_b\):.*?position_need_bonus:\s*([+-]?[\d.]+)", t, re.S)
    pos_a = float(ma.group(1)) if ma else 0.0
    pos_b = float(mb.group(1)) if mb else 0.0
    pos_avg = (pos_a + pos_b) / 2.0 if (ma or mb) else 0.0
    return {"pos_a": pos_a, "pos_b": pos_b, "pos_avg": pos_avg, "gain_a": ga, "gain_b": gb}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seeds", type=str, default="424242,424243,424244,424245,424246")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "cpu_auto_trade_posscale090_y5_multi_seed_summary.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    env = os.environ.copy()
    env["BASKETBALL_SIM_POSITION_NEED_BONUS_SCALE"] = "0.90"

    lines: List[str] = []
    lines.append("cpu_auto_trade_posscale090_multi_longrun summary")
    lines.append(f"POSITION_NEED_BONUS_SCALE=0.90 (env)  years={years}  seeds={seeds}")
    lines.append("")

    rows: List[Dict[str, Any]] = []

    for seed in seeds:
        acc_out = ROOT / "reports" / f"cpu_auto_trade_acceptance_y{years}_s{seed}_posscale090.txt"
        bd_out = ROOT / "reports" / f"cpu_auto_trade_value_breakdown_y{years}_s{seed}_posscale090.txt"

        subprocess.run(
            [
                sys.executable,
                str(ACCEPT),
                "--years",
                str(years),
                "--seed",
                str(seed),
                "--out",
                str(acc_out),
            ],
            env=env,
            cwd=str(ROOT),
            check=True,
        )
        pa = _parse_acceptance(acc_out)

        subprocess.run(
            [
                sys.executable,
                str(BDOWN),
                "--years",
                str(years),
                "--seed",
                str(seed),
                "--out",
                str(bd_out),
            ],
            env=env,
            cwd=str(ROOT),
            check=True,
        )
        bd = _parse_breakdown(bd_out)

        row = {
            "seed": seed,
            **pa,
            "position_need_mean_a": round(bd["pos_a"], 4),
            "position_need_mean_b": round(bd["pos_b"], 4),
            "position_need_mean_avg": round(bd["pos_avg"], 4),
            "mean_gain_a_bd": round(bd["gain_a"], 4),
            "mean_gain_b_bd": round(bd["gain_b"], 4),
        }
        rows.append(row)

        lines.append(f"--- seed {seed} ---")
        lines.append(f"  n_trades={pa['n_trades']}  year_counts={pa['year_counts']}")
        lines.append(
            f"  acquisitions={pa['n_acquisitions']}  mean_ovr={pa['mean_ovr']}  median_ovr={pa['median_ovr']}  "
            f"mean_age={pa['mean_age']}  median_age={pa['median_age']}"
        )
        lines.append(
            f"  low_OVR_pct: <=58 {pa['pct_ovr_le_58']}%  <=60 {pa['pct_ovr_le_60']}%  <=62 {pa['pct_ovr_le_62']}%"
        )
        lines.append(
            f"  strategy_tag: push={pa['tag_push']} hold={pa['tag_hold']} rebuild={pa['tag_rebuild']}"
        )
        lines.append(
            f"  breakdown: pos_need_A={row['position_need_mean_a']} pos_need_B={row['position_need_mean_b']} "
            f"pos_need_avg={row['position_need_mean_avg']}  mean_ga={row['mean_gain_a_bd']} mean_gb={row['mean_gain_b_bd']}"
        )
        lines.append("")

    def meanf(key: str) -> float:
        xs = [float(r[key]) for r in rows]
        return sum(xs) / len(xs) if xs else 0.0

    def stdevf(key: str) -> float:
        xs = [float(r[key]) for r in rows]
        if len(xs) < 2:
            return 0.0
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

    lines.append("=== Across seeds (arithmetic mean of per-seed scalars) ===")
    for key in (
        "n_trades",
        "mean_ovr",
        "mean_age",
        "pct_ovr_le_58",
        "pct_ovr_le_60",
        "pct_ovr_le_62",
        "position_need_mean_avg",
    ):
        lines.append(f"  mean {key}: {meanf(key):.4f}  stdev {key}: {stdevf(key):.4f}")

    lines.append("")
    lines.append("=== JSON (machine-readable) ===")
    lines.append(json.dumps(rows, indent=2, ensure_ascii=False))

    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
