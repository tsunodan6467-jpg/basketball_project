#!/usr/bin/env python3
"""開幕ロスター v1.1 実測集計（generate_teams のみ）。FA/再契約/ドラフトは対象外。"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from basketball_sim.systems.generator import generate_teams  # noqa: E402


def _nat_bucket(p) -> str:
    n = str(getattr(p, "nationality", "") or "")
    if n == "Foreign":
        return "Foreign"
    if n == "Naturalized":
        return "Naturalized"
    if n == "Asia":
        return "Asia"
    return "Japan"


def _summarize(vals: List[int]) -> str:
    if not vals:
        return "n=0"
    xs = sorted(vals)
    if len(xs) == 1:
        return f"n=1 min={xs[0]:,} p25/p50/p75=max={xs[0]:,}"
    qs = statistics.quantiles(xs, n=4, method="inclusive")
    q1, q2, q3 = int(qs[0]), float(qs[1]), int(qs[2])
    return (
        f"n={len(xs)} min={xs[0]:,} p25={q1:,} p50={q2:,.0f} "
        f"p75={q3:,} max={xs[-1]:,}"
    )


def run_report(seed: int) -> None:
    random.seed(seed)
    teams = generate_teams()

    all_salaries: List[int] = []
    d1_under_1m = 0
    d23_under_500k = 0
    young_flagged: List[Tuple[str, str, int, int, int]] = []  # team, name, age, salary, div
    jp_higher_than_foreign_team: List[str] = []
    jp_higher_than_imports_team: List[str] = []

    # division, tier -> list of team totals
    by_div_tier_totals: Dict[Tuple[int, str], List[int]] = defaultdict(list)
    by_div_tier_salaries: Dict[Tuple[int, str], List[int]] = defaultdict(list)

    young_cap = {1: 55_000_000, 2: 28_000_000, 3: 18_000_000}
    sample_d3_bottom: Any = None

    print(f"=== seed={seed} ===\n")
    print("--- 1. チーム単位（全48） ---\n")

    for t in teams:
        div = int(getattr(t, "league_level", 0))
        tier = str(getattr(t, "initial_payroll_tier", "") or "")
        players = list(getattr(t, "players", []) or [])
        salaries = sorted([int(getattr(p, "salary", 0)) for p in players], reverse=True)
        total = sum(salaries)
        all_salaries.extend(salaries)

        cnt: Dict[str, int] = defaultdict(int)
        for p in players:
            cnt[_nat_bucket(p)] += 1
            sal = int(getattr(p, "salary", 0))
            age = int(getattr(p, "age", 99))
            if div == 1 and sal < 1_000_000:
                d1_under_1m += 1
            if div in (2, 3) and sal < 500_000:
                d23_under_500k += 1
            if age <= 20 and sal > young_cap.get(div, 0):
                young_flagged.append(
                    (t.name, str(getattr(p, "name", "")), age, sal, div)
                )

        foreign_sals = [int(getattr(p, "salary", 0)) for p in players if _nat_bucket(p) == "Foreign"]
        japan_sals = [int(getattr(p, "salary", 0)) for p in players if _nat_bucket(p) == "Japan"]
        import_sals = [int(getattr(p, "salary", 0)) for p in players if _nat_bucket(p) != "Japan"]
        if foreign_sals and japan_sals and max(japan_sals) > max(foreign_sals):
            jp_higher_than_foreign_team.append(t.name)
        if japan_sals and import_sals and max(japan_sals) > max(import_sals):
            jp_higher_than_imports_team.append(t.name)

        by_div_tier_totals[(div, tier)].append(total)
        by_div_tier_salaries[(div, tier)].extend(salaries)

        if div == 3 and tier == "bottom" and sample_d3_bottom is None:
            sample_d3_bottom = t

        top5 = salaries[:5]
        nat_str = " ".join(f"{k}={cnt[k]}" for k in ("Foreign", "Naturalized", "Asia", "Japan") if cnt[k])

        print(
            f"{t.name} | D{div} | tier={tier} | total={total:,} | {nat_str} | top5={[f'{x:,}' for x in top5]}"
        )

    print("\n--- 2. 集約: division × tier ---\n")
    for div in (1, 2, 3):
        for tier in ("bottom", "middle", "top"):
            key = (div, tier)
            totals = sorted(by_div_tier_totals.get(key, []))
            sals = by_div_tier_salaries.get(key, [])
            if not totals:
                continue
            print(f"D{div} tier={tier} チーム総額: {_summarize(totals)}")
            print(f"D{div} tier={tier} 選手salary: {_summarize(sals)}")

    def _age_hist_for(div: int, tier: str) -> str:
        ages: List[int] = []
        for t in teams:
            if int(getattr(t, "league_level", 0)) != div:
                continue
            if str(getattr(t, "initial_payroll_tier", "") or "") != tier:
                continue
            for p in getattr(t, "players", []) or []:
                ages.append(int(getattr(p, "age", 0)))
        if not ages:
            return "n=0"
        b1 = sum(1 for a in ages if 18 <= a <= 20)
        b2 = sum(1 for a in ages if 21 <= a <= 23)
        b3 = sum(1 for a in ages if 24 <= a <= 29)
        b4 = sum(1 for a in ages if 30 <= a <= 34)
        b5 = sum(1 for a in ages if a >= 35)
        return (
            f"n={len(ages)} 18-20={b1} 21-23={b2} 24-29={b3} "
            f"30-34={b4} 35+={b5}"
        )

    print("\n--- 2b. 年齢分布（D2 top / D3 top / D3 middle / D3 bottom、全チーム選手合算） ---\n")
    for div, tier in ((2, "top"), (3, "top"), (3, "middle"), (3, "bottom")):
        print(f"D{div} tier={tier}: {_age_hist_for(div, tier)}")

    print("\n--- 閾値カウント ---\n")
    print(f"D1 で salary < 1,000,000 円の選手数: {d1_under_1m}")
    print(f"D2/D3 で salary < 500,000 円の選手数: {d23_under_500k}")
    print(f"20歳以下かつ若手上限超え（D1>55M / D2>28M / D3>18M）: {len(young_flagged)} 件")
    for row in young_flagged[:15]:
        print(f"  {row}")
    if len(young_flagged) > 15:
        print(f"  ... 他 {len(young_flagged) - 15} 件")

    print(
        f"\n同一チームで max(Japan salary) > max(Foreign salary) のチーム数: "
        f"{len(jp_higher_than_foreign_team)} / {len(teams)}"
    )
    if jp_higher_than_foreign_team:
        print(f"  例: {', '.join(jp_higher_than_foreign_team[:8])}{' ...' if len(jp_higher_than_foreign_team) > 8 else ''}")
    print(
        f"同一チームで max(Japan) > max(非日本人=Foreign+Naturalized+Asia) のチーム数: "
        f"{len(jp_higher_than_imports_team)} / {len(teams)}"
    )
    if jp_higher_than_imports_team:
        print(
            f"  例: {', '.join(jp_higher_than_imports_team[:8])}"
            f"{' ...' if len(jp_higher_than_imports_team) > 8 else ''}"
        )

    print("\n--- 3. D3 bottom 重点 ---\n")
    d3b_totals = sorted(by_div_tier_totals.get((3, "bottom"), []))
    if d3b_totals:
        in_band = sum(1 for x in d3b_totals if 380_000_000 <= x <= 420_000_000)
        print(f"D3 bottom チーム数: {len(d3b_totals)}")
        print(f"総額 3.8〜4.2億に入るチーム数: {in_band} / {len(d3b_totals)}")
        print(f"総額一覧（百万円）: {[round(x / 1_000_000) for x in d3b_totals]}")
    d3b_sals = by_div_tier_salaries.get((3, "bottom"), [])
    if d3b_sals:
        print(f"D3 bottom 選手 salary: {_summarize(d3b_sals)}")
    if sample_d3_bottom is not None:
        s5 = sorted(
            [int(getattr(p, "salary", 0)) for p in getattr(sample_d3_bottom, "players", [])],
            reverse=True,
        )[:5]
        print(
            f"D3 bottom 代表1チーム top5 salary: {getattr(sample_d3_bottom, 'name', '')} "
            f"-> {[f'{x:,}' for x in s5]}"
        )

    print("\n--- 代表チーム抜粋（D1 top / D2 middle / D3 bottom 各1） ---\n")
    pick: Dict[str, Any] = {}
    for t in teams:
        div = int(getattr(t, "league_level", 0))
        tier = str(getattr(t, "initial_payroll_tier", ""))
        if div == 1 and tier == "top" and "d1_top" not in pick:
            pick["d1_top"] = t
        if div == 2 and tier == "middle" and "d2_mid" not in pick:
            pick["d2_mid"] = t
        if div == 3 and tier == "bottom" and "d3_bot" not in pick:
            pick["d3_bot"] = t

    for label, team in pick.items():
        t = team
        pl = sorted(getattr(t, "players", []), key=lambda p: -int(getattr(p, "salary", 0)))
        print(f"[{label}] {t.name} D{getattr(t, 'league_level')} tier={getattr(t, 'initial_payroll_tier')} total={sum(int(getattr(p, 'salary', 0)) for p in pl):,}")
        for p in pl[:8]:
            print(
                f"  {getattr(p, 'name')} age={getattr(p, 'age')} {_nat_bucket(p)} "
                f"sal={int(getattr(p, 'salary', 0)):,} ovr={getattr(p, 'ovr')}"
            )
        print()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42, help="RNG seed (repeat with other seeds to compare)")
    args = p.parse_args()
    run_report(args.seed)


if __name__ == "__main__":
    main()
