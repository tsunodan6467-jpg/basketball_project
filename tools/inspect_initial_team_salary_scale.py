#!/usr/bin/env python3
"""
新規 `generate_teams()` 直後（＋任意で normalize_initial_payrolls 後）の全48クラブ年俸スケール調査。

用法:
  python tools/inspect_initial_team_salary_scale.py --out reports/initial_team_salary_scale.txt
  python tools/inspect_initial_team_salary_scale.py --seed 424242 --also-normalize
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# リポジトリルートを import パスに追加
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _player_salaries(team: Any) -> List[int]:
    out: List[int] = []
    for p in list(getattr(team, "players", []) or []):
        try:
            out.append(int(getattr(p, "salary", 0) or 0))
        except (TypeError, ValueError):
            out.append(0)
    return out


def _team_row(team: Any) -> Dict[str, Any]:
    sals = _player_salaries(team)
    n = len(sals)
    tot = sum(sals)
    tier = str(getattr(team, "initial_payroll_tier", "") or "")
    lv = int(getattr(team, "league_level", 0) or 0)
    return {
        "team_id": int(getattr(team, "team_id", -1) or -1),
        "name": str(getattr(team, "name", "") or "")[:28],
        "div": f"D{lv}",
        "tier": tier,
        "players": n,
        "total": tot,
        "avg": (tot // n) if n else 0,
        "max": max(sals) if sals else 0,
        "min": min(sals) if sals else 0,
    }


def _division_avg_totals(rows: List[Dict[str, Any]], div: str) -> Tuple[int, int]:
    sub = [r for r in rows if r["div"] == div]
    if not sub:
        return 0, 0
    return sum(r["total"] for r in sub), len(sub)


def _emit_report(rows: List[Dict[str, Any]], fh, *, title: str, normalize_note: str) -> None:
    fh.write(f"\n{'=' * 72}\n")
    fh.write(f"{title}\n")
    fh.write(f"{normalize_note}\n")
    fh.write(f"{'=' * 72}\n")
    fh.write(
        f"{'team_id':>7}  {'team_name':<28}  {'div':>4}  {'tier':>6}  "
        f"{'pl':>3}  {'total_salary':>14}  {'avg':>10}  {'max':>10}  {'min':>10}\n"
    )
    for r in sorted(rows, key=lambda x: x["team_id"]):
        fh.write(
            f"{r['team_id']:>7}  {r['name']:<28}  {r['div']:>4}  {r['tier']:>6}  "
            f"{r['players']:>3}  {r['total']:>14,}  {r['avg']:>10,}  "
            f"{r['max']:>10,}  {r['min']:>10,}\n"
        )
    fh.write("\nDivision summary (avg total_salary per team)\n")
    for div in ("D1", "D2", "D3"):
        s_tot, cnt = _division_avg_totals(rows, div)
        if cnt:
            fh.write(f"  {div}: 平均総年俸 {s_tot // cnt:,} 円/チーム（{cnt}チーム・合計 {s_tot:,} 円）\n")
    d3_bot = [r for r in rows if r["div"] == "D3" and r["tier"] == "bottom"]
    if d3_bot:
        bt = sum(r["total"] for r in d3_bot) // len(d3_bot)
        fh.write(
            f"\nD3 bottom tier only: {len(d3_bot)} teams, avg total_salary = {bt:,} 円/チーム\n"
        )
        for r in sorted(d3_bot, key=lambda x: x["team_id"]):
            fh.write(
                f"    id={r['team_id']} {r['name']!r} total={r['total']:,} avg={r['avg']:,} "
                f"max={r['max']:,} min={r['min']:,}\n"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect opening roster salary scale (48 teams).")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/initial_team_salary_scale.txt"),
        help="Output text path",
    )
    ap.add_argument("--seed", type=int, default=None, help="Simulation seed (default: env or time)")
    ap.add_argument(
        "--also-normalize",
        action="store_true",
        help="After generate_teams, run normalize_initial_payrolls_for_teams (same as build_initial_game_world)",
    )
    args = ap.parse_args()

    from basketball_sim.systems.contract_logic import (
        get_team_payroll,
        normalize_initial_payrolls_for_teams,
    )
    from basketball_sim.systems.generator import generate_teams
    from basketball_sim.utils.sim_rng import init_simulation_random

    seed_used = init_simulation_random(args.seed)
    teams = generate_teams()

    def rows_from_teams(ts) -> List[Dict[str, Any]]:
        rows_local: List[Dict[str, Any]] = []
        for t in ts:
            r = _team_row(t)
            r["total"] = int(get_team_payroll(t))
            rows_local.append(r)
        return rows_local

    rows_a = rows_from_teams(teams)
    normalize_count = 0
    if args.also_normalize:
        normalize_count = int(normalize_initial_payrolls_for_teams(teams))
        rows_b = rows_from_teams(teams)
    else:
        rows_b = []

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write("inspect_initial_team_salary_scale.py\n")
        fh.write(f"seed_used={seed_used}  also_normalize={args.also_normalize}\n")
        fh.write("\n正本メモ:\n")
        fh.write(
            "  - 48チーム生成: systems/generator.py generate_teams\n"
            "  - 開幕年俸帯・総額: systems/opening_roster_salary_v11.py "
            "(roll_target_team_payroll, apply_opening_team_payroll_v11)\n"
            "  - 新規世界末尾: main.build_initial_game_world → normalize_initial_payrolls_for_teams\n"
            "    （上限超のみ縮小: contract_logic.normalize_team_payroll_under_league_cap）\n"
        )
        _emit_report(
            rows_a,
            fh,
            title="Phase A: generate_teams() 直後（CPU 開幕ロスター・全48）",
            normalize_note="normalize 未適用",
        )
        if args.also_normalize:
            _emit_report(
                rows_b,
                fh,
                title="Phase B: normalize_initial_payrolls_for_teams 直後",
                normalize_note=f"調整したチーム数 = {normalize_count}",
            )
        fh.write("\n" + "=" * 72 + "\n")
        fh.write("Code-path notes (調査用・このスクリプトはゲームロジックを変更しない)\n")
        fh.write("=" * 72 + "\n")
        fh.write(
            "1) Phase A の CPU48は generator.generate_teams → opening_roster_salary_v11 "
            "(roll_target_team_payroll + apply_opening_team_payroll_v11) で総額が帯に収まる。\n"
            "   D3 bottom の target 総額は opening_roster_salary_v11.roll_target_team_payroll で "
            "約 3.8〜4.2 億円レンジ。\n"
            "2) ユーザー自動編成 main.auto_draft_players は user_team.players を空にし、"
            "create_fictional_player_pool → generate_fictional_player 由来の選手で再構成する。\n"
            "   年俸は generator.calculate_initial_salary(ovr, league_market_division)（OVR×"
            "GENERATOR_INITIAL_SALARY_BASE_PER_OVR）で、開幕 v11 のチーム総額再配分はかからない。\n"
            "3) build_initial_game_world 末尾の normalize_initial_payrolls_for_teams は "
            "リーグ上限×margin を超えるときのみ縮小。D3 でも上限 12 億なので ~8〜9 億台は縮小されないことがある。\n"
            "4) よって「D3 ボトム CPU は ~4 億だがユーザーだけ平均数千万〜億近い」は、"
            "設計上ユーザー枠だけ別経路になっている可能性が高い（要: 実プレイ後の user_team 集計で確認）。\n"
        )
    print(f"Wrote {args.out.resolve()} (seed={seed_used})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
