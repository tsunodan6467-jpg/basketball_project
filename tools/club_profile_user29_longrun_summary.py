"""Summarize club_profile_user29_team_trace report(s): per-team rank strings per seed."""

from __future__ import annotations

import argparse
import re
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
_TRACE = ROOT / "tools" / "club_profile_user29_team_trace.py"
_spec = importlib.util.spec_from_file_location("club_profile_user29_team_trace", _TRACE)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
TRACE_IDS: Tuple[int, ...] = tuple(_mod.TRACE_IDS)


def _parse_trace_report(text: str) -> Dict[str, Dict[int, Tuple[str, str, str]]]:
    """label -> team_id -> (tag, rank_last, wl)."""
    parts = re.split(r"=== (after_season_y\d+) ===\n", text)
    out: Dict[str, Dict[int, Tuple[str, str, str]]] = {}
    it = iter(parts[1:])
    for label, body in zip(it, it):
        rows: Dict[int, Tuple[str, str, str]] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("team_id"):
                continue
            toks = line.split()
            if len(toks) < 12:
                continue
            try:
                tid = int(toks[0])
            except ValueError:
                continue
            tag = toks[2]
            rk, rw, rl = toks[-3], toks[-2], toks[-1]
            rows[tid] = (tag, rk, f"{rw}-{rl}")
        out[label] = rows
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "reports",
        nargs="+",
        type=Path,
        help="e.g. reports/club_profile_user29_team_trace_y5_s424242.txt",
    )
    ap.add_argument("--years", type=int, default=5)
    args = ap.parse_args()

    years = max(1, int(args.years))
    for rp in args.reports:
        text = rp.read_text(encoding="utf-8")
        m = re.search(r"seed=(\d+)", text)
        seed = m.group(1) if m else rp.stem
        d = _parse_trace_report(text)
        print(f"## {rp.name} seed={seed}")
        hdr = "team_id | " + " | ".join(f"y{y}" for y in range(1, years + 1))
        print(hdr)
        print("-" * len(hdr))
        for tid in TRACE_IDS:
            cells: List[str] = []
            for y in range(1, years + 1):
                lab = f"after_season_y{y}"
                row = d.get(lab, {}).get(tid)
                cells.append(row[1] if row else "-")
            print(f"{tid:2d}      | " + " | ".join(f"{c:>3s}" for c in cells))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
