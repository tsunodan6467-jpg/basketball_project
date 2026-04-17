#!/usr/bin/env python3
"""generate_teams 直後の全48クラブ: 資金力帯・開始所持金・ユーザー補正後の想定を一覧する。"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--out", type=Path, default=Path("reports/initial_money_by_financial_band.txt"))
    args = ap.parse_args()

    from basketball_sim.systems.club_profile import (
        get_financial_power_band_1_to_5,
        get_initial_team_money_cpu,
        get_initial_user_team_money,
    )
    from basketball_sim.systems.generator import generate_teams
    from basketball_sim.utils.sim_rng import init_simulation_random

    init_simulation_random(args.seed)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        teams = generate_teams()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write(f"seed={args.seed}  (after generate_teams only; no user swap)\n\n")
        fh.write(
            f"{'team_id':>6}  {'team_name':<26}  {'div':>4}  {'band':>4}  "
            f"{'cpu_start_money':>14}  {'+if_user':>14}\n"
        )
        for t in sorted(teams, key=lambda x: int(getattr(x, "team_id", 0))):
            tid = int(getattr(t, "team_id", 0))
            lv = int(getattr(t, "league_level", 0) or 0)
            band = get_financial_power_band_1_to_5(t)
            cpu_m = int(get_initial_team_money_cpu(t))
            user_m = int(get_initial_user_team_money(t))
            fh.write(
                f"{tid:>6}  {str(getattr(t, 'name', ''))[:26]:<26}  D{lv}  {band:>4}  "
                f"{cpu_m:>14,}  {user_m:>14,}\n"
            )

        fh.write("\nBand → CPU opening cash (yen)\n")
        fh.write("  1 → 200,000,000  2 → 280,000,000  3 → 380,000,000  4 → 550,000,000  5 → 800,000,000\n")
        fh.write("  User team: CPU amount + 70,000,000\n")

    print(f"Wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
