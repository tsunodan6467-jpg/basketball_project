"""
複数 seed で trade value 内訳観測を連続実行し、1 本のサマリーを出力する。

例:
  python tools/cpu_strategy_trade_value_breakdown_multi_seed.py --years 5 \\
    --seeds 424242,424243,424244,424245,424246 --out-dir reports
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_mod():
    path = Path(__file__).resolve().parent / "cpu_strategy_trade_value_breakdown_observe.py"
    spec = importlib.util.spec_from_file_location("tv_breakdown", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("load failure")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get(d: Dict[str, Any], tag: str, key: str) -> float | None:
    a = d["by_tag"].get(tag) or {}
    if a.get("n", 0) == 0:
        return None
    return float(a.get(key)) if key in a else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seeds", type=str, default="424242,424243,424244,424245,424246")
    ap.add_argument("--out-dir", type=Path, default=Path("reports"))
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(s.strip()) for s in str(args.seeds).split(",") if s.strip()]
    mod = _load_mod()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for seed in seeds:
        data = mod.run_breakdown_observe(years, seed)
        results.append(data)
        p = out_dir / f"cpu_strategy_trade_value_breakdown_y{years}_s{seed}.txt"
        p.write_text("\n".join(mod.report_lines(data)) + "\n", encoding="utf-8")
        print(f"Wrote {p.resolve()}")

    ypk = "mean_youth_peak_raw"
    ovrk = "mean_ovr_term"
    fdk = "mean_fut_delta_on_scaled_parts"
    mfk = "mean_m_fut"

    c_youth = c_ovr = c_fut = 0
    for d in results:
        p, h = _get(d, "push", ypk), _get(d, "hold", ypk)
        if p is not None and h is not None and p > h:
            c_youth += 1
        po, ho = _get(d, "push", ovrk), _get(d, "hold", ovrk)
        if po is not None and ho is not None and po > ho:
            c_ovr += 1
        pf, hf = _get(d, "push", fdk), _get(d, "hold", fdk)
        if pf is not None and hf is not None and pf > hf:
            c_fut += 1

    lines = [
        "CPU strategy trade VALUE breakdown — multi-seed summary",
        f"years={years}  n_seeds={len(seeds)}",
        f"seeds: {', '.join(str(s) for s in seeds)}",
        "",
        f"Per-seed: see cpu_strategy_trade_value_breakdown_y{years}_s*.txt",
        "",
        "Rollups (count seeds where push mean > hold mean, both n>0):",
        f"  youth_peak_raw: {c_youth} / {len(seeds)}",
        f"  ovr_term:       {c_ovr} / {len(seeds)}",
        f"  fut_delta:      {c_fut} / {len(seeds)}  (push fut_delta > hold fut_delta)",
        "",
        "Per-seed one-line (push vs hold: youth_peak_raw, ovr_term, m_fut, n):",
    ]
    for d in results:
        s = d["seed"]
        bp, bh = d["by_tag"]["push"], d["by_tag"]["hold"]
        lines.append(
            f"  seed {s}: push n={bp.get('n',0)} hold n={bh.get('n',0)} | "
            f"youth_p_raw p/h={_get(d,'push',ypk)}/{_get(d,'hold',ypk)} "
            f"ovr p/h={_get(d,'push',ovrk)}/{_get(d,'hold',ovrk)} "
            f"m_fut p/h={_get(d,'push',mfk)}/{_get(d,'hold',mfk)}"
        )
    br = [d["by_tag"]["rebuild"].get("n", 0) for d in results]
    lines.append("")
    lines.append(f"rebuild n per seed: {br}  (seeds with rebuild n<5: {sum(1 for x in br if x < 5)}/{len(seeds)})")
    lines.extend(
        [
            "",
            "Interpretation (for report):",
            "- youth_peak_raw = max(0,28-|age-27|)*0.4 (peak near 27); NOT a monotonic 'younger is bigger' bonus.",
            "- m_fut from future_value_weight is small (e.g. push~0.976 vs hold 1.0); fut_delta is usually sub-1 point.",
            "- Compare mean_ovr_term vs mean_pot_raw: if OVR lower for push but pot similar/higher, roster mix dominates.",
        ]
    )

    summary = out_dir / f"cpu_strategy_trade_value_breakdown_y{years}_multi_seed_summary.txt"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
