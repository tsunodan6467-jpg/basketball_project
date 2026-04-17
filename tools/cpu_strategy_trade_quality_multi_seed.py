"""
複数 seed で `run_trade_quality_observe` を連続実行し、横比較サマリーを 1 ファイルにまとめる。

例:
  python tools/cpu_strategy_trade_quality_multi_seed.py --years 5 \\
    --seeds 424242,424243,424244,424245,424246 \\
    --out-dir reports
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_observe_module():
    path = Path(__file__).resolve().parent / "cpu_strategy_trade_quality_observe.py"
    spec = importlib.util.spec_from_file_location("cpu_strategy_trade_quality_observe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load cpu_strategy_trade_quality_observe")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cmp_push_younger_than_hold(d: Dict[str, Any]) -> bool:
    p, h = d["by_tag"]["push"], d["by_tag"]["hold"]
    if p["n"] == 0 or h["n"] == 0 or p["mean_age"] is None or h["mean_age"] is None:
        return False
    return float(p["mean_age"]) < float(h["mean_age"])


def _cmp_push_higher_ovr_than_hold(d: Dict[str, Any]) -> bool:
    p, h = d["by_tag"]["push"], d["by_tag"]["hold"]
    if p["n"] == 0 or h["n"] == 0 or p["mean_ovr"] is None or h["mean_ovr"] is None:
        return False
    return float(p["mean_ovr"]) > float(h["mean_ovr"])


def _cmp_rebuild_younger_than_push(d: Dict[str, Any]) -> bool:
    r, p = d["by_tag"]["rebuild"], d["by_tag"]["push"]
    if r["n"] == 0 or p["n"] == 0 or r["mean_age"] is None or p["mean_age"] is None:
        return False
    return float(r["mean_age"]) < float(p["mean_age"])


def _fmt_tag_row(tag: str, m: Dict[str, Any]) -> str:
    if m["n"] == 0:
        return f"  {tag:7s} n=0"
    return (
        f"  {tag:7s} n={m['n']:<3}  mean_age={m['mean_age']:.2f}  p50_age={m['p50_age']:.1f}  "
        f"mean_ovr={m['mean_ovr']:.2f}  p50_ovr={m['p50_ovr']:.1f}  "
        f"age<=24%={m['age_le24_rate']:.1f}%  young_SA%={m['young_sa_rate']:.1f}%  mean_pot={m['mean_pot']:.2f}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-seed CPU trade quality observer")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument(
        "--seeds",
        type=str,
        default="424242,424243,424244,424245,424246",
        help="comma-separated seeds",
    )
    ap.add_argument("--out-dir", type=Path, default=Path("reports"))
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(s.strip()) for s in str(args.seeds).split(",") if s.strip()]
    if not seeds:
        print("no seeds", file=sys.stderr)
        return 1

    mod = _load_observe_module()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for seed in seeds:
        data = mod.run_trade_quality_observe(years, seed)
        results.append(data)
        per_path = out_dir / f"cpu_strategy_trade_quality_y{years}_s{seed}.txt"
        text = "\n".join(mod.trade_quality_report_lines(data)) + "\n"
        per_path.write_text(text, encoding="utf-8")
        print(f"Wrote {per_path.resolve()}")

    n_seeds = len(results)
    push_more_count = sum(1 for d in results if d["by_tag"]["push"]["n"] > d["by_tag"]["hold"]["n"])
    younger = sum(1 for d in results if _cmp_push_younger_than_hold(d))
    higher_ovr = sum(1 for d in results if _cmp_push_higher_ovr_than_hold(d))
    reb_younger = sum(1 for d in results if _cmp_rebuild_younger_than_push(d))
    reb_low_n = sum(1 for d in results if d["by_tag"]["rebuild"]["n"] < 5)

    lines: List[str] = [
        "CPU strategy trade quality — multi-seed summary",
        f"years={years}  seeds={n_seeds}",
        f"seed list: {', '.join(str(s) for s in seeds)}",
        "",
        "Per-seed (CPU trade acquisitions, tag at acquire time):",
    ]
    for d in results:
        s = int(d["seed"])
        lines.append(f"\n--- seed {s}  total_incoming={d['total']} ---")
        for tag in ("push", "hold", "rebuild"):
            lines.append(_fmt_tag_row(tag, d["by_tag"][tag]))

    lines.extend(
        [
            "",
            "=== Cross-seed rollups ===",
            f"Seeds where push_n > hold_n: {push_more_count} / {n_seeds}",
            f"Seeds where (push mean_age < hold mean_age), both n>0: {younger} / {n_seeds}",
            f"Seeds where (push mean_ovr > hold mean_ovr), both n>0: {higher_ovr} / {n_seeds}",
            f"Seeds where (rebuild mean_age < push mean_age), both n>0: {reb_younger} / {n_seeds}",
            f"Seeds where rebuild n < 5: {reb_low_n} / {n_seeds}",
            "",
            "Interpretation hints:",
            "- If push_n > hold_n is stable but age/OVR ordering flips across seeds, 'youth skew' may be noise.",
            "- If rebuild n < 5 in most seeds, sample starvation is structural for this observe window.",
        ]
    )

    summary_path = out_dir / f"cpu_strategy_trade_quality_y{years}_multi_seed_summary.txt"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
