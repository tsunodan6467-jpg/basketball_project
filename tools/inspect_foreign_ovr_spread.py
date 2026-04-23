#!/usr/bin/env python3
"""
generate_teams() 直後の全48クラブについて、同一チーム内の外国籍（nationality==Foreign）選手の
OVR 分布・max-min 差を一覧し、落差が大きいチームを抽出する調査用ツール。ゲームロジックは変更しない。
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path
from typing import Any, List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.systems.generator import generate_teams  # noqa: E402


def run(seed: int, out_path: Path) -> None:
    random.seed(seed)
    teams = list(generate_teams())

    rows: List[Tuple[Any, ...]] = []
    gaps_by_div: dict[int, List[int]] = {1: [], 2: [], 3: []}
    gap_at_least = {15: 0, 18: 0, 20: 0, 25: 0}
    issue_rows: List[Tuple[int, str, int, int, List[int]]] = []

    for t in teams:
        tid = getattr(t, "team_id", "")
        tname = getattr(t, "name", "")
        div = int(getattr(t, "league_level", 0) or 0)
        ovrs = sorted(
            (
                int(getattr(p, "ovr", 0) or 0)
                for p in getattr(t, "players", []) or []
                if str(getattr(p, "nationality", "") or "") == "Foreign"
            ),
            reverse=True,
        )
        n = len(ovrs)
        if n == 0:
            gap = 0
            mx = mn = 0
        else:
            mx, mn = max(ovrs), min(ovrs)
            gap = mx - mn
        rows.append((tid, tname, div, n, ovrs, mx, mn, gap))
        if div in gaps_by_div and n > 0:
            gaps_by_div[div].append(gap)
        for thr in gap_at_least:
            if gap >= thr:
                gap_at_least[thr] += 1
        if gap >= 18:
            issue_rows.append((int(tid), str(tname), div, gap, ovrs))

    lines: List[str] = []
    w = lines.append

    w(f"foreign_ovr_spread_inspection seed={seed} teams={len(teams)}")
    w("")
    w(
        "team_id\tteam_name\tdiv\tforeign_count\tforeign_ovrs_desc\tmax\tmin\tgap"
    )
    for tid, tname, div, n, ovrs, mx, mn, gap in rows:
        desc = ",".join(str(x) for x in ovrs) if ovrs else "-"
        w(
            f"{tid}\t{tname}\tD{div}\t{n}\t[{desc}]\t{mx}\t{mn}\t{gap}"
        )
    w("")
    w("=== Foreign OVR spread summary ===")
    w(f"teams with Foreign players: {sum(1 for r in rows if r[3] > 0)}")
    for thr in sorted(gap_at_least.keys()):
        w(f"gap >= {thr}: {gap_at_least[thr]} teams")
    w("")
    w("=== By division (gap = max OVR - min OVR among Foreign on team) ===")
    for d in (1, 2, 3):
        gs = gaps_by_div[d]
        if not gs:
            w(f"D{d} (no foreign or n=0): n=0")
            continue
        w(
            f"D{d} n_teams_with_foreign={len(gs)} "
            f"avg_gap={statistics.mean(gs):.2f} "
            f"min_gap={min(gs)} max_gap={max(gs)} "
            f"p50_gap={statistics.median(gs):.1f}"
        )
    w("")
    w("=== Potential spread issues (gap >= 18) ===")
    issue_rows.sort(key=lambda x: (-x[3], x[0]))
    if not issue_rows:
        w("(none)")
    else:
        for tid, tname, div, gap, ovrs in issue_rows:
            w(f"- team_id={tid} {tname} D{div} gap={gap} ovrs={ovrs}")
    w("")
    w("Notes: nationality==Foreign only (本契約枠の外国籍3人想定). generate_teams 直後。")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(lines)} lines)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument(
        "--out",
        type=str,
        default="reports/foreign_ovr_spread_seed424242.txt",
    )
    args = ap.parse_args()
    run(int(args.seed), Path(args.out))


if __name__ == "__main__":
    main()
