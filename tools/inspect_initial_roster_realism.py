#!/usr/bin/env python3
"""
新規開始直後（generate_teams のみ）の全48クラブ初期ロスターを点検し、
年齢・国籍・OVR・ディビジョンの整合性の観測と違和感候補をテキストに出力する調査用ツール。
ゲームロジック・データモデルは変更しない。
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.systems.generator import generate_teams  # noqa: E402
from basketball_sim.systems.japan_regulation_display import (  # noqa: E402
    get_player_nationality_bucket_label,
)


def _q(vals: Sequence[int], p: float) -> float:
    if not vals:
        return float("nan")
    xs = sorted(vals)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return float(xs[f])
    return float(xs[f] + (xs[c] - xs[f]) * (k - f))


def _fmt_stats(xs: List[int]) -> str:
    if not xs:
        return "n=0"
    return (
        f"n={len(xs)} mean={statistics.mean(xs):.2f} "
        f"min={min(xs)} p25={_q(xs, 0.25):.1f} p50={_q(xs, 0.5):.1f} "
        f"p75={_q(xs, 0.75):.1f} max={max(xs)}"
    )


def _safe_cell(s: Any) -> str:
    t = str(s).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return t


def run(seed: int, out_path: Path) -> None:
    random.seed(seed)
    teams = list(generate_teams())

    rows: List[Tuple[Any, ...]] = []
    ovrs_by_div: Dict[int, List[int]] = {1: [], 2: [], 3: []}
    ages_all: List[int] = []
    ages_by_nat: Dict[str, List[int]] = defaultdict(list)
    bucket_counts: Dict[str, int] = defaultdict(int)
    nat_raw_counts: Dict[str, int] = defaultdict(int)
    ages_special_bucket: List[int] = []  # アジア/帰化 枠の年齢

    for t in teams:
        tid = getattr(t, "team_id", "")
        tname = getattr(t, "name", "")
        div = int(getattr(t, "league_level", 0) or 0)
        for p in getattr(t, "players", None) or []:
            age = int(getattr(p, "age", 0) or 0)
            nat = str(getattr(p, "nationality", "") or "")
            ovr = int(getattr(p, "ovr", 0) or 0)
            pot = getattr(p, "potential", "")
            sal = int(getattr(p, "salary", 0) or 0)
            icon = bool(getattr(p, "is_icon", False))
            bucket = get_player_nationality_bucket_label(p)
            pname = getattr(p, "name", "")

            rows.append((tid, tname, div, pname, age, nat, bucket, ovr, pot, sal, icon))
            if div in ovrs_by_div:
                ovrs_by_div[div].append(ovr)
            ages_all.append(age)
            nat_raw_counts[nat or "(empty)"] += 1
            bucket_counts[bucket] += 1
            if bucket == "アジア/帰化":
                ages_special_bucket.append(age)
            ages_by_nat[nat or "(empty)"].append(age)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    w = lines.append

    w(f"initial_roster_realism_inspection seed={seed}")
    w(f"teams={len(teams)} players={len(rows)}")
    w("")

    w("=== PLAYER TABLE (tab-separated) ===")
    w(
        "team_id\tteam_name\tdiv\tplayer\tage\tnat\tbucket\tOVR\tPOT\tsalary\ticon"
    )
    for r in rows:
        w(
            "\t".join(
                _safe_cell(x)
                for x in (
                    r[0],
                    r[1],
                    f"D{r[2]}",
                    r[3],
                    r[4],
                    r[5],
                    r[6],
                    r[7],
                    r[8],
                    r[9],
                    r[10],
                )
            )
        )
    w("")

    w("=== Division summary (OVR) ===")
    for d in (1, 2, 3):
        w(f"D{d} {_fmt_stats(ovrs_by_div[d])}")
    w("")

    w("=== Nationality summary (raw nationality string) ===")
    for k in sorted(nat_raw_counts.keys(), key=lambda x: (-nat_raw_counts[x], x)):
        w(f"  {k}: {nat_raw_counts[k]}")
    w("")

    w("=== Contract-roster bucket summary (GUIと同じ判定) ===")
    for k in sorted(bucket_counts.keys(), key=lambda x: (-bucket_counts[x], x)):
        w(f"  {k}: {bucket_counts[k]}")
    w("")

    w("=== Age (all players) ===")
    w(_fmt_stats(ages_all))
    buckets = [("<=20", lambda a: a <= 20), ("21-24", lambda a: 21 <= a <= 24), ("25-29", lambda a: 25 <= a <= 29), ("30-34", lambda a: 30 <= a <= 34), (">=35", lambda a: a >= 35)]
    for label, pred in buckets:
        c = sum(1 for a in ages_all if pred(a))
        w(f"  {label}: {c}")
    w("")

    w("=== アジア/帰化枠の年齢（bucket label == アジア/帰化） ===")
    w(_fmt_stats(ages_special_bucket))
    w("")

    # --- Heuristic issue candidates ---
    issues: List[str] = []

    d1_ovrs = ovrs_by_div[1]
    d3_ovrs = ovrs_by_div[3]
    d1_p10 = int(round(_q(d1_ovrs, 0.10))) if len(d1_ovrs) >= 5 else None
    d3_p90 = int(round(_q(d3_ovrs, 0.90))) if len(d3_ovrs) >= 5 else None

    # 若い帰化・若い外国籍高OVR
    d1_low_list: List[str] = []
    for r in rows:
        _tid, _tname, div, pname, age, nat, bucket, ovr, _pot, _sal, _icon = r
        div_i = int(div)
        if nat == "Naturalized" and age <= 22:
            issues.append(
                f"若い帰化: team_id={_tid} D{div_i} {pname} age={age} OVR={ovr} nat={nat}"
            )
        if bucket == "外国籍" and age <= 21 and ovr >= 62:
            issues.append(
                f"若手外国籍高OVR: team_id={_tid} D{div_i} {pname} age={age} OVR={ovr}"
            )

    # D3 で高OVR（全体のD3 p90 を超える選手を列挙し、さらに OVR>=68 を強調）
    if d3_ovrs:
        thr = max(68, int(round(_q(d3_ovrs, 0.92))))
        hi_d3 = [r for r in rows if int(r[2]) == 3 and int(r[7]) >= thr]
        if len(hi_d3) > 8:
            issues.append(
                f"D3でOVR>={thr}の選手が{len(hi_d3)}人（多すぎる可能性）。例: "
                + ", ".join(f"{r[3]}({r[7]})" for r in hi_d3[:6])
                + ("…" if len(hi_d3) > 6 else "")
            )
        else:
            for r in hi_d3:
                if int(r[7]) >= 70:
                    issues.append(
                        f"D3高OVR: team_id={r[0]} {r[3]} OVR={r[7]} age={r[4]} bucket={r[6]}"
                    )

    # D1 で低OVR（p10 未満かつ非アイコン）
    if d1_ovrs and d1_p10 is not None:
        low_thr = min(52, d1_p10 - 2)
        for r in rows:
            if int(r[2]) != 1:
                continue
            if r[10]:
                continue
            if int(r[7]) <= low_thr:
                d1_low_list.append(
                    f"D1低OVR: team_id={r[0]} {r[3]} OVR={r[7]} age={r[4]} bucket={r[6]} (threshold<={low_thr})"
                )
    issues.extend(d1_low_list[:25])
    if len(d1_low_list) > 25:
        issues.append(f"... D1低OVR 省略: 他 {len(d1_low_list) - 25} 件")

    # D1 高OVRがD3平均を大きく上回るのは想定内なので、D1下位 tier チームの主力が極端に弱い場合
    tier_by_team = {getattr(t, "team_id", None): str(getattr(t, "initial_payroll_tier", "") or "") for t in teams}
    for r in rows:
        if int(r[2]) != 1:
            continue
        tier = tier_by_team.get(r[0], "")
        if tier == "bottom" and int(r[7]) <= 46 and int(r[4]) <= 28:
            # 控えまで拾うと多すぎるので、重複を避けつつ代表的に
            pass
    # bottom tier: count players OVR<=45 per team
    bottom_d1_low = defaultdict(int)
    for r in rows:
        if int(r[2]) != 1:
            continue
        if tier_by_team.get(r[0]) != "bottom":
            continue
        if int(r[7]) <= 45:
            bottom_d1_low[r[0]] += 1
    for tid, cnt in bottom_d1_low.items():
        if cnt >= 5:
            tnm = next((str(getattr(t, "name", "")) for t in teams if getattr(t, "team_id", None) == tid), "")
            issues.append(
                f"D1 bottom tier チーム team_id={tid} {tnm} に OVR<=45 が{cnt}人"
            )

    # 外国籍3人の強さのばらつき（同一チームで外国籍のOVR极差>25）
    by_team_foreign: Dict[Any, List[int]] = defaultdict(list)
    for r in rows:
        if r[6] == "外国籍":
            by_team_foreign[r[0]].append(int(r[7]))
    for tid, ovs in by_team_foreign.items():
        if len(ovs) >= 2 and max(ovs) - min(ovs) >= 28:
            tnm = next((str(getattr(t, "name", "")) for t in teams if getattr(t, "team_id", None) == tid), "")
            issues.append(
                f"同一チーム外国籍OVR差大: team_id={tid} {tnm} foreign_ovrs={sorted(ovs)}"
            )

    w("=== Potential realism issues (heuristic) ===")
    if not issues:
        w("(none flagged with current thresholds)")
    else:
        for msg in issues[:80]:
            w(f"- {msg}")
        if len(issues) > 80:
            w(f"... and {len(issues) - 80} more")
    w("")

    w("=== Notes ===")
    w("div=Team.league_level (1=D1, 2=D2, 3=D3). bucket=get_player_nationality_bucket_label (本契約枠).")
    w("Heuristics are rough signals only; tune thresholds after generator changes.")
    w(f"D1 OVR p10≈{d1_p10}  D3 OVR p90≈{d3_p90}")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(lines)} lines)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument(
        "--out",
        type=str,
        default="reports/initial_roster_realism_seed424242.txt",
    )
    args = ap.parse_args()
    run(int(args.seed), Path(args.out))


if __name__ == "__main__":
    main()
