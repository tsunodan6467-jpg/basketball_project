"""Aggregate club_profile_user29_team_trace reports: per-team rank/OVR/age/cum stats."""

from __future__ import annotations

import argparse
import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Body stops at next `=== ...` header (avoid pulling after_offseason into season stats).
_BLOCK_AFTER_SEASON = re.compile(
    r"^=== (after_season_y(\d+)) ===\s*\n(.*?)(?=^=== |\Z)",
    re.MULTILINE | re.DOTALL,
)
_BLOCK_AFTER_OFFSEASON = re.compile(
    r"^=== (after_offseason_y(\d+)) ===\s*\n(.*?)(?=^=== |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _parse_trace_line(line: str) -> Optional[Tuple[int, str, Dict[str, Any]]]:
    """Return (team_id, name_token, fields) or None. fields: rank, age, ovr, cum_* or None if skip."""
    line = line.strip()
    if not line or line.startswith("team_id"):
        return None
    toks = line.split()
    if len(toks) < 12:
        return None
    try:
        tid = int(toks[0])
    except ValueError:
        return None
    name_tok = toks[1] if len(toks) > 1 else ""
    tag = toks[2]

    def _f(x: str) -> Optional[float]:
        if x == "-":
            return None
        try:
            return float(x)
        except ValueError:
            return None

    def _i(x: str) -> Optional[int]:
        if x == "-":
            return None
        try:
            return int(x)
        except ValueError:
            return None

    rk = _i(toks[-3])
    ovr = _f(toks[-4])
    age = _f(toks[-5])
    cum_fa = _i(toks[-6])
    cum_tout = _i(toks[-7])
    cum_tin = _i(toks[-8])
    return tid, name_tok, {
        "tag": tag,
        "rank_last": rk,
        "ovr_mean": ovr,
        "age_mean": age,
        "cum_tin": cum_tin,
        "cum_tout": cum_tout,
        "cum_fa": cum_fa,
    }


def _iter_block_bodies(text: str, rx: re.Pattern[str]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for m in rx.finditer(text):
        label = m.group(1)
        body = m.group(3)  # (.*?) block after header; y from m.group(2)
        out.append((label, body))
    return out


def _collect_from_file(path: Path) -> Tuple[Dict[int, Dict[str, List[Any]]], Dict[int, str]]:
    """
    Per team_id: ranks, ovr, age from after_season_y*; cum_* from after_offseason_y*.
    """
    text = path.read_text(encoding="utf-8")
    m = re.search(r"seed=(\d+)", text)
    seed = m.group(1) if m else path.stem

    acc: Dict[int, Dict[str, List[Any]]] = {}
    names: Dict[int, str] = {}

    def _ensure(tid: int) -> Dict[str, List[Any]]:
        if tid not in acc:
            acc[tid] = {
                "ranks": [],
                "ovr": [],
                "age": [],
                "cum_tin": [],
                "cum_tout": [],
                "cum_fa": [],
                "seed": seed,
            }
        return acc[tid]

    for _label, body in _iter_block_bodies(text, _BLOCK_AFTER_SEASON):
        for line in body.splitlines():
            parsed = _parse_trace_line(line)
            if not parsed:
                continue
            tid, name_tok, d = parsed
            names.setdefault(tid, name_tok)
            a = _ensure(tid)
            if d["rank_last"] is not None:
                a["ranks"].append(int(d["rank_last"]))
            if d["ovr_mean"] is not None:
                a["ovr"].append(float(d["ovr_mean"]))
            if d["age_mean"] is not None:
                a["age"].append(float(d["age_mean"]))

    for _label, body in _iter_block_bodies(text, _BLOCK_AFTER_OFFSEASON):
        for line in body.splitlines():
            parsed = _parse_trace_line(line)
            if not parsed:
                continue
            tid, name_tok, d = parsed
            names.setdefault(tid, name_tok)
            a = _ensure(tid)
            if d["cum_tin"] is not None:
                a["cum_tin"].append(int(d["cum_tin"]))
            if d["cum_tout"] is not None:
                a["cum_tout"].append(int(d["cum_tout"]))
            if d["cum_fa"] is not None:
                a["cum_fa"].append(int(d["cum_fa"]))

    return acc, names


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _rates(ranks: List[int]) -> Tuple[float, float, float]:
    if not ranks:
        return float("nan"), float("nan"), float("nan")
    n = len(ranks)
    top = sum(1 for r in ranks if r <= 4) / n
    upper = sum(1 for r in ranks if r <= 8) / n
    bottom = sum(1 for r in ranks if r >= 13) / n
    return top, upper, bottom


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate user29 team trace rank/OVR/age/cum stats.")
    ap.add_argument("reports", nargs="+", type=Path, help="Trace .txt files (same years).")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports") / "club_profile_user29_rank_aggregate.txt",
        help="Output summary path.",
    )
    args = ap.parse_args()

    merged: Dict[int, Dict[str, List[Any]]] = {}
    names: Dict[int, str] = {}

    for rp in args.reports:
        part, part_names = _collect_from_file(rp)
        for tid, d in part.items():
            names.setdefault(tid, part_names.get(tid, ""))
            if tid not in merged:
                merged[tid] = {
                    "ranks": [],
                    "ovr": [],
                    "age": [],
                    "cum_tin": [],
                    "cum_tout": [],
                    "cum_fa": [],
                }
            for k in ("ranks", "ovr", "age", "cum_tin", "cum_tout", "cum_fa"):
                merged[tid][k].extend(d[k])

    lines: List[str] = []
    lines.append("club_profile_user29_rank_aggregate")
    lines.append(f"inputs={len(args.reports)} " + " ".join(str(p) for p in args.reports))
    lines.append(
        "Scope: after_season_y* → rank_last, ovr_mean, age_mean; "
        "after_offseason_y* → cum_tin, cum_tout, cum_fa (pooled across all seeds×years)."
    )
    lines.append("Rates: top_rate=P(rank<=4), upper_rate=P(rank<=8), bottom_rate=P(rank>=13).")
    lines.append("")

    hdr = (
        "team_id name n mean_rank median_rank best worst "
        "top_rate upper_rate bottom_rate mean_ovr mean_age "
        "mean_cum_tin mean_cum_tout mean_cum_fa"
    )
    lines.append(hdr)
    lines.append("-" * len(hdr))

    rows_out: List[Tuple[int, str]] = []
    for tid in sorted(merged.keys()):
        d = merged[tid]
        ranks: List[int] = d["ranks"]
        n = len(ranks)
        if n == 0:
            continue
        mr = _mean([float(x) for x in ranks])
        med = float(statistics.median(ranks))
        best = min(ranks)
        worst = max(ranks)
        tr, ur, br = _rates(ranks)
        ovr = d["ovr"]
        age = d["age"]
        mean_ovr = _mean(ovr) if ovr else float("nan")
        mean_age = _mean(age) if age else float("nan")
        ctin = d["cum_tin"]
        ctout = d["cum_tout"]
        cfa = d["cum_fa"]
        mean_ctin = _mean([float(x) for x in ctin]) if ctin else float("nan")
        mean_ctout = _mean([float(x) for x in ctout]) if ctout else float("nan")
        mean_cfa = _mean([float(x) for x in cfa]) if cfa else float("nan")
        nm = names.get(tid, "")
        rows_out.append(
            (
                tid,
                f"{tid} {nm} {n} {mr:.3f} {med:.1f} {best} {worst} "
                f"{tr:.3f} {ur:.3f} {br:.3f} {mean_ovr:.3f} {mean_age:.3f} "
                f"{mean_ctin:.3f} {mean_ctout:.3f} {mean_cfa:.3f}",
            )
        )

    for _tid, row in sorted(rows_out, key=lambda x: x[0]):
        lines.append(row)

    lines.append("")
    lines.append("--- Focus: Nara 38, Tottori 46 ---")
    for tid in (38, 46):
        line = next((r[1] for r in rows_out if r[0] == tid), None)
        if line:
            lines.append(line)

    lines.append("")
    lines.append("--- Focus: strong (1,2,3,4,8,9) ---")
    for tid in (1, 2, 3, 4, 8, 9):
        line = next((r[1] for r in rows_out if r[0] == tid), None)
        if line:
            lines.append(line)

    lines.append("")
    lines.append("--- Focus: tier4-ish (6,8,9,10,16,17,22) ---")
    for tid in (6, 8, 9, 10, 16, 17, 22):
        line = next((r[1] for r in rows_out if r[0] == tid), None)
        if line:
            lines.append(line)

    lines.append("")
    lines.append("--- Compare: 14,15,19,33 ---")
    for tid in (14, 15, 19, 33):
        line = next((r[1] for r in rows_out if r[0] == tid), None)
        if line:
            lines.append(line)

    out_text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_text, encoding="utf-8")
    print(out_text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
