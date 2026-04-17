"""
第1優先9 + 第2優先6 = 15クラブ個別 club_profile の薄い観測（本体非改変）。

get_club_base_profile / payroll fac / CPU 戦略（tendency + opening hint + tag）/ get_cpu_club_strategy。
比較用に型テンプレのみの team_id を併記。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.offseason import compute_postoff_payroll_budget_with_temp_floor  # noqa: E402
from basketball_sim.systems.club_profile import get_club_base_profile  # noqa: E402
from basketball_sim.systems.cpu_club_strategy import (  # noqa: E402
    _VALID_EXPECTATIONS,
    _opening_profile_strategy_hint,
    _resolve_strategy_tag,
    _tendency_scores,
    get_cpu_club_strategy,
)
from basketball_sim.systems.generator import generate_teams, sync_player_id_counter_from_world  # noqa: E402

# 第1優先9 + 第2優先6（個別値 override 対象）
USER15_IDS: Tuple[int, ...] = (1, 2, 3, 4, 5, 7, 12, 13, 18, 21, 25, 29, 33, 38, 46)
COMPARE_IDS: Tuple[int, ...] = (6, 9, 14, 19, 48)


def _payroll_fac(team: Any) -> float:
    try:
        if bool(getattr(team, "is_user_team", False)):
            return 1.0
        prof = get_club_base_profile(team)
        fac = (
            1.0
            + 0.022 * (float(prof.financial_power) - 1.0)
            + 0.018 * (float(prof.market_size) - 1.0)
            + 0.015 * (float(prof.arena_grade) - 1.0)
        )
        return max(0.97, min(1.03, float(fac)))
    except Exception:
        return 1.0


def _strategy_inputs(team: Any) -> Tuple[str, int, int, int]:
    exp = str(getattr(team, "owner_expectation", "playoff_race") or "playoff_race").strip().lower()
    if exp not in _VALID_EXPECTATIONS:
        exp = "playoff_race"
    ll = max(1, min(3, int(getattr(team, "league_level", 2) or 2)))
    wins = max(0, min(40, int(getattr(team, "regular_wins", 0) or 0)))
    money = max(0, int(getattr(team, "money", 0) or 0))
    return exp, ll, wins, money


def _nudge_preview(team: Any) -> Tuple[int, int, bool, str, str]:
    exp, ll, wins, money = _strategy_inputs(team)
    ps, rs = _tendency_scores(team, exp, ll, wins, money)
    amb = -1 <= ps - rs <= 1
    prof = get_club_base_profile(team)
    net = float(prof.win_now_pressure) - float(prof.financial_power)
    if not amb:
        return ps, rs, False, f"net={net:.4f}", "n/a (not ambiguous)"
    if net > 0.035:
        return ps, rs, True, f"net={net:.4f}", "would +1 push_s"
    if net < -0.035:
        return ps, rs, True, f"net={net:.4f}", "would +1 reb_s"
    return ps, rs, True, f"net={net:.4f}", "no nudge (|net|<=0.035)"


def _roster_payroll(team: Any) -> int:
    return int(
        sum(max(0, int(getattr(p, "salary", 0) or 0)) for p in getattr(team, "players", []) or [])
    )


def run_probe() -> List[str]:
    lines: List[str] = []
    teams = generate_teams()
    sync_player_id_counter_from_world(teams, [])

    lines.append("club_profile_user15_probe (USER15 individual overrides + compare)")
    lines.append("")

    lines.append("=== 1) get_club_base_profile (USER15) ===")
    for tid in USER15_IDS:
        t = next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)
        p = get_club_base_profile(t)
        lines.append(
            f"  team_id={tid} name={getattr(t, 'name', '')!r} -> "
            f"fin={p.financial_power} mkt={p.market_size} arena={p.arena_grade} "
            f"youth={p.youth_development_bias} win_now={p.win_now_pressure}"
        )

    lines.append("")
    lines.append("=== 1b) compare: type-template clubs (not in USER15) ===")
    for tid in COMPARE_IDS:
        t = next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)
        p = get_club_base_profile(t)
        lines.append(
            f"  team_id={tid} name={getattr(t, 'name', '')!r} -> "
            f"fin={p.financial_power} mkt={p.market_size} arena={p.arena_grade} "
            f"youth={p.youth_development_bias} win_now={p.win_now_pressure}"
        )

    lines.append("")
    lines.append("=== 2) payroll fac (CPU) + budget(roster_payroll=0 and actual) ===")
    user_like = SimpleNamespace(
        team_id=99,
        league_level=3,
        is_user_team=True,
        market_size=1.0,
        popularity=50,
        sponsor_power=50,
        fan_base=5000,
        money=50_000_000,
    )
    lines.append(f"  user_like is_user_team=True fac={_payroll_fac(user_like):.6f} (expect 1.0)")
    for tid in USER15_IDS:
        t = next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)
        rp = _roster_payroll(t)
        fac = _payroll_fac(t)
        b0 = compute_postoff_payroll_budget_with_temp_floor(t, 0)
        br = compute_postoff_payroll_budget_with_temp_floor(t, rp)
        lines.append(
            f"  id={tid} fac={fac:.6f} budget_rp0={b0:,} budget_actual_rp={rp:,}->{br:,}"
        )

    lines.append("")
    lines.append(
        "=== 3) strategy: tendency + opening_profile_hint + ambiguous preview + tag + scalars ==="
    )
    for tid in USER15_IDS + (6, 9, 14):
        t = next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)
        exp, ll, wins, money = _strategy_inputs(t)
        ps, rs = _tendency_scores(t, exp, ll, wins, money)
        hp, hr = _opening_profile_strategy_hint(t)
        tag = _resolve_strategy_tag(t, exp, ll, wins, money)
        _, _, amb, net_s, nudge = _nudge_preview(t)
        s = get_cpu_club_strategy(t)
        ps2, rs2 = ps + hp, rs + hr
        lines.append(
            f"  id={tid} push_s={ps} reb_s={rs} hint=({hp},{hr}) eff={ps2},{rs2} diff_eff={ps2 - rs2} "
            f"ambiguous={amb} {net_s} -> {nudge} | "
            f"tag={tag} fa={s.fa_aggressiveness} trade_tol={s.trade_loss_tolerance} fut={s.future_value_weight}"
        )

    lines.append("")
    lines.append("=== 4) fac spread (USER15 only, sorted by fac desc) ===")
    rows = []
    for tid in USER15_IDS:
        t = next(x for x in teams if int(getattr(x, "team_id", 0) or 0) == tid)
        rows.append((tid, getattr(t, "name", ""), _payroll_fac(t)))
    rows.sort(key=lambda x: -x[2])
    for tid, nm, fac in rows:
        lines.append(f"  fac_rank tid={tid} fac={fac:.6f} name={nm!r}")

    lines.append("")
    lines.append("Done.")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("reports") / "club_profile_user15_probe.txt")
    args = ap.parse_args()
    lines = run_probe()
    text = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
