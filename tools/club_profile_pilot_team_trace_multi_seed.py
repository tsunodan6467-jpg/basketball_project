"""
12 クラブパイロットの multi-seed 再現性観測（本体非改変）。

`club_profile_pilot_team_trace.collect_trace_snapshots` を複数 seed で実行し、
クラブごとにタグ分布・trade/FA 累積・増分合計・最終 age/ovr の平均を集計する。

例:
  python tools/club_profile_pilot_team_trace_multi_seed.py --years 3 \\
    --seeds 424242,424243,424244,424245,424246 \\
    --out reports/club_profile_pilot_team_trace_y3_multi_seed.txt
"""

from __future__ import annotations

import argparse
import importlib.util
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TRACE_PATH = ROOT / "tools" / "club_profile_pilot_team_trace.py"
_spec = importlib.util.spec_from_file_location("_pilot_team_trace", _TRACE_PATH)
assert _spec and _spec.loader
_pt = importlib.util.module_from_spec(_spec)
sys.modules["_pilot_team_trace"] = _pt
_spec.loader.exec_module(_pt)
collect_trace_snapshots = _pt.collect_trace_snapshots
PILOT_IDS: Tuple[int, ...] = _pt.PILOT_IDS


def _sum_delta(rows_by_label: List[Dict[str, Any]], tid: int, key: str) -> int:
    s = 0
    for block in rows_by_label[1:]:
        v = block["rows"][tid].get(key)
        if v is not None:
            s += int(v)
    return s


def _final_block(rows_by_label: List[Dict[str, Any]]) -> Dict[str, Any]:
    return rows_by_label[-1]


def _fmt_tag_dist(c: Counter) -> str:
    p, h, r = int(c.get("push", 0)), int(c.get("hold", 0)), int(c.get("rebuild", 0))
    return f"push={p} hold={h} reb={r}"


def _one_line_comment(tid: int, c_all: Counter, mean_d_any: float, mean_cum_fa: float) -> str:
    dom = c_all.most_common(1)[0][0] if c_all else "?"
    return f"dominant_tag={dom} mean_d_any/run={mean_d_any:.2f} mean_cum_fa@end={mean_cum_fa:.2f}"


def run_multi(*, years: int, seeds: List[int], lines: List[str]) -> None:
    runs: Dict[int, List[Dict[str, Any]]] = {s: collect_trace_snapshots(years=years, seed=s) for s in seeds}
    labels = [b["label"] for b in runs[seeds[0]]]
    n_seeds = len(seeds)
    n_snap = len(labels)

    lines.append(
        f"club_profile_pilot_team_trace_multi_seed | years={years} seeds={seeds} "
        f"snapshots={n_snap}×{n_seeds}={n_snap * n_seeds} rows per team"
    )
    lines.append("")

    lines.append("=== Per-seed: final cum trade + FA (after last snapshot) ===")
    lines.append("seed " + " ".join(f"id{tid}:tin+tout=fa" for tid in PILOT_IDS))
    last_label = labels[-1]
    for s in seeds:
        fin = _final_block(runs[s])
        assert str(fin["label"]) == last_label
        parts = [str(s)]
        for tid in PILOT_IDS:
            r = fin["rows"][tid]
            parts.append(f"{tid}:{r['cum_tin'] + r['cum_tout']}={r['cum_fa']}")
        lines.append("  " + " ".join(parts))
    lines.append("")

    lines.append("=== Per team_id: tag distribution per snapshot label (counts over seeds) ===")
    for tid in PILOT_IDS:
        name0 = runs[seeds[0]][0]["rows"][tid]["name"]
        lines.append(f"team_id={tid} name={name0!r}")
        for lab in labels:
            ctr: Counter = Counter()
            for s in seeds:
                block = next(b for b in runs[s] if str(b["label"]) == lab)
                tag = block["rows"][tid]["tag"]
                ctr[str(tag)] += 1
            lines.append(f"  {lab:22s} {_fmt_tag_dist(ctr)} / {n_seeds}")
        lines.append("")

    lines.append("=== Per team_id: totals across seeds (mean ± stdev where n>1) ===")
    lines.append(
        "team_id name | mean_final_cum_tin mean_final_cum_tout mean_final_cum_any "
        "| mean_sum_d_any/run mean_sum_d_fa/run | mean_final_age mean_final_ovr "
        "| tag_hits_35(push/hold/reb) | note"
    )
    total_obs = n_snap * n_seeds
    for tid in PILOT_IDS:
        name0 = runs[seeds[0]][0]["rows"][tid]["name"]
        finals_tin = []
        finals_tout = []
        finals_fa = []
        sum_d_any_list = []
        sum_d_fa_list = []
        ages = []
        ovrs = []
        c_all: Counter = Counter()
        for s in seeds:
            seq = runs[s]
            fb = _final_block(seq)["rows"][tid]
            finals_tin.append(int(fb["cum_tin"]))
            finals_tout.append(int(fb["cum_tout"]))
            finals_fa.append(int(fb["cum_fa"]))
            sum_d_any_list.append(_sum_delta(seq, tid, "d_any"))
            sum_d_fa_list.append(_sum_delta(seq, tid, "d_fa"))
            ag, ov = fb["age_mean"], fb["ovr_mean"]
            if ag is not None:
                ages.append(float(ag))
            if ov is not None:
                ovrs.append(float(ov))
            for block in seq:
                c_all[str(block["rows"][tid]["tag"])] += 1

        def m_std(xs: List[float]) -> Tuple[float, float]:
            if not xs:
                return float("nan"), float("nan")
            m = statistics.mean(xs)
            st = statistics.pstdev(xs) if len(xs) > 1 else 0.0
            return m, st

        mtin, _ = m_std([float(x) for x in finals_tin])
        mtout, _ = m_std([float(x) for x in finals_tout])
        mfa, sfa = m_std([float(x) for x in finals_fa])
        md_any, sd_any = m_std([float(x) for x in sum_d_any_list])
        md_fa, sd_fa = m_std([float(x) for x in sum_d_fa_list])
        mage, sage = m_std(ages)
        movr, sovr = m_std(ovrs)
        p, h, rb = int(c_all.get("push", 0)), int(c_all.get("hold", 0)), int(c_all.get("rebuild", 0))
        note = _one_line_comment(tid, c_all, md_any, mfa)
        lines.append(
            f"{tid} {name0!r} | {mtin:.2f} {mtout:.2f} {mtin + mtout:.2f} | "
            f"{md_any:.2f}±{sd_any:.2f} {md_fa:.2f}±{sd_fa:.2f} | "
            f"{mage:.2f}±{sage:.2f} {movr:.2f}±{sovr:.2f} | "
            f"{p}/{h}/{rb} of {total_obs} | {note}"
        )

    lines.append("")
    lines.append("=== Interpretation ===")
    lines.append(
        "Per-label rows: e.g. push=4 / 5 means 4 of 5 seeds had strategy_tag=push at that snapshot."
    )
    lines.append(
        "mean_sum_d_any/run: sum of d_any over all post-opening snapshots in one run, averaged over seeds."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-seed pilot team trace aggregate")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument(
        "--seeds",
        type=str,
        default="424242,424243,424244,424245,424246",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "club_profile_pilot_team_trace_y3_multi_seed.txt",
    )
    args = ap.parse_args()
    years = max(1, min(8, int(args.years)))
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    if len(seeds) < 1:
        raise SystemExit("need at least one seed")
    lines: List[str] = []
    run_multi(years=years, seeds=seeds, lines=lines)
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.resolve()} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
