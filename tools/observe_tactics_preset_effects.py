"""
プレイスタイル/ローテーションフリセット差の**軽量観測**（CLI・非対戦・本編ロジック非改変）。

同一シードの world 生成から2チームを得、ホームの team_tactics のみ差し替え、
同一相手（アウェイ：デフォルトで両プリセット `balanced_v1` 固定）で複数試合を
`Match.simulate()` し、集計を `reports/` へ出す。

例:
  python tools/observe_tactics_preset_effects.py --seed 42 --games 20 \\
    --out reports/tactics_preset_effects_light_report.txt
"""

from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basketball_sim.models.match import Match  # noqa: E402
from basketball_sim.models.team import Team  # noqa: E402
from basketball_sim.models.player import Player  # noqa: E402
from basketball_sim.systems.generator import (  # noqa: E402
    generate_teams,
    sync_player_id_counter_from_world,
)
from basketball_sim.systems.team_tactics import (  # noqa: E402
    ROTATION_PRESET_DEFS,
    PLAYSTYLE_PRESET_DEFS,
    apply_playstyle_preset_with_preset_meta,
    apply_rotation_preset_with_preset_meta,
    ensure_team_tactics_on_team,
)
from basketball_sim.utils.sim_rng import init_simulation_random  # noqa: E402

# --- 比較対象（正本は team_tactics.PLAYSTYLE/ROTATION_PRESET_DEFS）---
PLAYSTYLES = [
    "balanced_v1",
    "run_and_gun_3p_v1",
    "defense_first_v1",
]
ROTATIONS = [
    "balanced_v1",
    "win_now_v1",
    "development_v1",
]


@dataclass
class GameRow:
    home_score: int
    away_score: int
    pace_proxy: int  # match.total_possessions
    fga2: int
    fga3: int
    fgm2: int
    fgm3: int
    fta_ignored: int
    tov: int
    oreb: int
    dreb: int
    subs: int
    q4_subs: int
    lineups_used: int  # players with >0.5 min
    min_top5_mean: float
    min_bench_mean: float
    min_youth_mean: float
    n_youth: int


YOUTH_MAX_AGE = 23  # 観測上の若手帯（固定閾値・ラフ）


def _youth_age_cutoff(_players: List[Player]) -> int:
    return YOUTH_MAX_AGE


def _apply_default_presets(t: Team) -> None:
    apply_playstyle_preset_with_preset_meta(t, "balanced_v1")
    apply_rotation_preset_with_preset_meta(t, "balanced_v1")


def _focal_pbp_aggregates(match: Any, focal_key: str) -> Dict[str, int]:
    fga2 = fga3 = fgm2 = fgm3 = 0
    fta = 0
    tov = oreb = dreb = 0
    subs = 0
    q4_subs = 0
    for e in match.play_by_play_log:
        et = e.get("event_type")
        oi = e.get("offense_team_id")
        di = e.get("defense_team_id")
        if et in ("made_2", "miss_2") and oi == focal_key:
            fga2 += 1
            if et == "made_2":
                fgm2 += 1
        if et in ("made_3", "miss_3") and oi == focal_key:
            fga3 += 1
            if et == "made_3":
                fgm3 += 1
        if et in ("made_ft", "miss_ft") and oi == focal_key:
            fta += 1
        if et == "turnover" and oi == focal_key:
            tov += 1
        if et == "off_rebound" and oi == focal_key:
            oreb += 1
        if et == "def_rebound" and di == focal_key:
            dreb += 1
        if et == "substitution" and oi == focal_key:
            subs += 1
            q = e.get("quarter")
            if q == 4:
                q4_subs += 1
    return {
        "fga2": fga2,
        "fga3": fga3,
        "fgm2": fgm2,
        "fgm3": fgm3,
        "fta": fta,
        "tov": tov,
        "oreb": oreb,
        "dreb": dreb,
        "subs": subs,
        "q4_subs": q4_subs,
    }


def _focal_lineup_aggregates(
    match: Any, focal: Team, active: List[Player]
) -> Tuple[float, float, float, int, int, Tuple[str, ...]]:
    rows: List[Tuple[float, str, int]] = []
    y_cut = _youth_age_cutoff(list(active))
    y_minutes: List[float] = []
    n_youth = 0
    for p in active:
        m = float(match._get_player_minutes(p))
        pid = str(getattr(p, "player_id", p.name) or p.name)
        ag = int(getattr(p, "age", 99) or 99)
        rows.append((m, pid, ag))
        if ag <= y_cut:
            y_minutes.append(m)
            n_youth += 1
    rows.sort(key=lambda x: -x[0])
    if not rows:
        return 0.0, 0.0, 0.0, 0, 0, tuple()
    top5 = rows[:5]
    rest = rows[5:]
    lineups = sum(1 for m, _, _ in rows if m > 0.4)
    top_mean = sum(m for m, _, _ in top5) / min(5, len(top5))
    bench_mean = (sum(m for m, _, _ in rest) / len(rest)) if rest else 0.0
    youth_mean = (sum(y_minutes) / len(y_minutes)) if y_minutes else 0.0
    top5_ids = tuple(s for _, s, _ in top5)
    return top_mean, bench_mean, youth_mean, lineups, n_youth, top5_ids


def _one_game(
    home: Team, away: Team, *, is_playoff: bool = False
) -> Tuple[GameRow, int, int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        m = Match(
            home,
            away,
            is_playoff=is_playoff,
            competition_type="regular_season",
        )
        _, hsc, asc = m.simulate()
    fk = m._team_key(home)
    pb = _focal_pbp_aggregates(m, fk)
    top, bench, youth, lineups, n_y, _ = _focal_lineup_aggregates(m, home, m.home_active_players)
    row = GameRow(
        home_score=int(hsc),
        away_score=int(asc),
        pace_proxy=int(getattr(m, "total_possessions", 0) or 0),
        fga2=pb["fga2"],
        fga3=pb["fga3"],
        fgm2=pb["fgm2"],
        fgm3=pb["fgm3"],
        fta_ignored=pb["fta"],
        tov=pb["tov"],
        oreb=pb["oreb"],
        dreb=pb["dreb"],
        subs=pb["subs"],
        q4_subs=pb["q4_subs"],
        lineups_used=lineups,
        min_top5_mean=top,
        min_bench_mean=bench,
        min_youth_mean=youth,
        n_youth=n_y,
    )
    return row, hsc, asc, fk


def _mean_stdev(xs: List[float]) -> str:
    if not xs:
        return "n/a"
    if len(xs) == 1:
        return f"{xs[0]:.2f} (n=1)"
    return f"{statistics.mean(xs):.2f} (sd {statistics.pstdev(xs):.2f}, n={len(xs)})"


def _run_block(
    label: str,
    home_template: Team,
    away_template: Team,
    n_games: int,
    seed0: int,
    configure_home,  # (Team) -> None
) -> Tuple[List[GameRow], int]:
    rows: List[GameRow] = []
    gidx = 0
    for _ in range(n_games):
        init_simulation_random(int(seed0) + gidx)
        gidx += 1
        h = deepcopy(home_template)
        a = deepcopy(away_template)
        configure_home(h)
        _apply_default_presets(a)
        ensure_team_tactics_on_team(a)
        ensure_team_tactics_on_team(h)
        r, _, _, _ = _one_game(h, a)
        rows.append(r)
    return rows, gidx


def _print_report(
    out_path: Path,
    seed: int,
    games: int,
    h_name: str,
    a_name: str,
    ps_block: List[Dict[str, Any]],
    rot_block: List[Dict[str, Any]],
) -> None:
    lines: List[str] = []
    lines.append("=== tactics preset effects (light) ===")
    lines.append(f"seed={seed}  games_per_condition={games}")
    lines.append(f"home(focal)={h_name}  away(fixed)={a_name}")
    lines.append("away: apply_playstyle balanced_v1 + apply_rotation balanced_v1 (毎試合 deepcopy+再適用)")
    lines.append("")

    def dump_block(title: str, block: List[Dict[str, Any]]):
        lines.append(f"--- {title} ---")
        for row in block:
            lines.append(f"  {row['preset_id']:22s} {row.get('label_ja',''):8s}  " f"PPG {row['ppg']:<18s} Opp {row['oppg']:<18s} margin {row['margin']}")
            lines.append(
                f"     pace(avg pos) {row['pace']:<28s} 3PA {row.get('a3', 'n/a')}"
            )
            if "fg_pct" in row and row.get("fga_total", "0") != "0.00+":
                lines.append(
                    f"     2+3P FG% 約 {row['fg_pct']:<8s}  (2FGA+3FGA={row.get('fga_total', '')})  3P% 約 {row.get('p3', '')}  (3PA>0 時)"
                )
            if "tov" in row:
                lines.append(
                    f"     TO/試合(ホーム) {row['tov']}, OREB/試合 {row.get('oreb', '')} DREB/試合 {row.get('dreb', '')}, SUB 計 {row.get('subs', '')} (Q4: {row.get('q4_subs', '')})"
                )
            if "m_top5" in row and title.startswith("rotation"):
                lines.append(
                    f"     主力(上位5)平均 {row.get('m_top5', '')} 分, 6人目以降 {row.get('m_bench', '')} 分, 若手(年齢<={YOUTH_MAX_AGE}) 平均 {row.get('m_y', '')} 分, 起用 {row.get('lineups', '')} 人"
                )
        lines.append("")

    dump_block("playstyle sweep (rotation=balanced_v1 固定 on home)", ps_block)
    dump_block("rotation sweep (playstyle=balanced_v1 固定 on home)", rot_block)
    lines.append("--- 簡易所感（自動要約; 厳密な指標最適化ではない）---")
    lines.append(_brief_notes(ps_block, rot_block))
    lines.append("")
    lines.append("注: ペース＝1試合あたり合計 possession 数(試合同士比較用).")
    lines.append("※ FT は FGA 集計から除く(スクリム相当の 2+3P のみ). 試合エンジン改造なし、PBP 集計。")
    lines.append(
        f"※ 若手: 年齢<={YOUTH_MAX_AGE} の選手の平均出場(アクティブ枠内、各試合の n_youth 平均をレポート内集計)。"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_stats(rows: List[GameRow], label_ja: str) -> Dict[str, Any]:
    ppg = [float(r.home_score) for r in rows]
    opp = [float(r.away_score) for r in rows]
    mar = [float(r.home_score - r.away_score) for r in rows]
    pace = [float(r.pace_proxy) for r in rows]
    a3l = [float(r.fga3) for r in rows]
    fga2 = [float(r.fga2) for r in rows]
    fga3 = [float(r.fga3) for r in rows]
    fgm2 = [float(r.fgm2) for r in rows]
    fgm3 = [float(r.fgm3) for r in rows]
    tvl = [float(r.tov) for r in rows]
    orel = [float(r.oreb) for r in rows]
    drel = [float(r.dreb) for r in rows]
    sbl = [float(r.subs) for r in rows]
    q4l = [float(r.q4_subs) for r in rows]
    t_fga = sum(fga2) + sum(fga3)
    t_fgm = sum(fgm2) + sum(fgm3)
    t_3a = sum(fga3)
    t_3m = sum(fgm3)
    fg_pct = f"{(100.0 * t_fgm / t_fga):.1f}%" if t_fga else "n/a"
    p3_pct = f"{(100.0 * t_3m / t_3a):.1f}%" if t_3a else "n/a"
    m_top5 = [r.min_top5_mean for r in rows]
    m_bench = [r.min_bench_mean for r in rows]
    m_y = [r.min_youth_mean for r in rows]
    n_yo = int(statistics.mean([r.n_youth for r in rows]) + 0.5) if rows else 0
    return {
        "label_ja": label_ja,
        "ppg": _mean_stdev(ppg),
        "oppg": _mean_stdev(opp),
        "margin": _mean_stdev(mar),
        "pace": _mean_stdev(pace),
        "a3": _mean_stdev(a3l),
        "fg_pct": fg_pct,
        "fga_total": f"{int(t_fga)} (game-sum)",
        "p3": p3_pct,
        "tov": _mean_stdev(tvl),
        "oreb": _mean_stdev(orel),
        "dreb": _mean_stdev(drel),
        "subs": _mean_stdev(sbl),
        "q4_subs": _mean_stdev(q4l),
        "m_top5": _mean_stdev(m_top5),
        "m_bench": _mean_stdev(m_bench),
        "m_y": _mean_stdev(m_y),
        "y_n": n_yo,
        "lineups": _mean_stdev([float(r.lineups_used) for r in rows]),
    }


def _brief_notes(ps: List[Dict], rot: List[Dict]) -> str:
    try:
        best3 = max(ps, key=lambda d: float(d.get("a3", "0").split()[0]) if d.get("a3", "n/a") != "n/a" else 0)
    except Exception:
        best3 = ps[0] if ps else {}
    try:
        def _m(d, k):
            s = d.get(k, "0")
            return float(s.split()[0].replace("(", ""))

        low_opp = min(ps, key=lambda d: _m(d, "oppg"))
    except Exception:
        low_opp = ps[0] if ps else {}
    r_win = next((d for d in rot if d.get("preset_id") == "win_now_v1"), None)
    r_dev = next((d for d in rot if d.get("preset_id") == "development_v1"), None)
    notes: List[str] = []
    if best3 and best3.get("preset_id") == "run_and_gun_3p_v1":
        notes.append("- 3PA(ホーム)は run_and_gun_3p_v1 で最大傾向（PBP 集計）。")
    if low_opp and low_opp.get("preset_id") == "defense_first_v1":
        notes.append("- 対アウェー失点は defense_first_v1 で最も低い傾向（要：サンプル誤差あり）。")
    else:
        notes.append("- プレイスタイル間の得失点/3P の差は**小さい/不安定**な場合がある（N と seed に依存）。")
    if r_win and r_dev and r_win.get("m_top5", "0") != "n/a":
        try:
            if _m(r_win, "m_top5") > _m(r_dev, "m_top5") + 0.3:
                notes.append(
                    "- ローテ: 勝利優先が主力(上5)分数平均が育成寄りより高めの**傾向**（大差でない可能性）。"
                )
        except Exception:
            notes.append("- ローテ分数差の自動比較に失敗（要手元確認）。")
    if not any("ローテ" in n for n in notes) and len(rot) > 1:
        notes.append("- ローテ3種の分数差は**小さい**場合が多い（同じ相手＋同じプレースタイル固定のため）。")
    return "\n".join(f"  {n}" for n in notes)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--games", type=int, default=20, help="各条件あたりの試合数")
    p.add_argument(
        "--home-idx", type=int, default=0, help="focal(ホーム)に使う team index (generate_teams)"
    )
    p.add_argument(
        "--away-idx", type=int, default=1, help="相手(アウェイ)に使う team index"
    )
    p.add_argument(
        "--out", type=Path, default=ROOT / "reports" / "tactics_preset_effects_light_report.txt"
    )
    args = p.parse_args()

    init_simulation_random(args.seed)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        all_teams = generate_teams()
    sync_player_id_counter_from_world(all_teams, [])
    home0 = all_teams[args.home_idx]
    away0 = all_teams[args.away_idx]

    h_base = deepcopy(home0)
    a_base = deepcopy(away0)

    ps_out: List[Dict[str, Any]] = []
    for pid in PLAYSTYLES:

        def _ph(t: Team, p=pid) -> None:
            _apply_default_presets(t)
            apply_playstyle_preset_with_preset_meta(t, p)
            # rotation stays balanced (already set)

        rows, _ = _run_block(
            "ps",
            h_base,
            a_base,
            args.games,
            args.seed + 1000,
            _ph,
        )
        lj = str(PLAYSTYLE_PRESET_DEFS[pid].get("label_ja", pid))
        st = _row_stats(rows, lj)
        st["preset_id"] = pid
        ps_out.append(st)

    rot_out: List[Dict[str, Any]] = []
    for rid in ROTATIONS:

        def _rh(t: Team, p=rid) -> None:
            _apply_default_presets(t)
            # playstyle balanced first, then rotation
            apply_playstyle_preset_with_preset_meta(t, "balanced_v1")
            apply_rotation_preset_with_preset_meta(t, p)

        rows, _ = _run_block(
            "rot",
            h_base,
            a_base,
            args.games,
            args.seed + 2000,
            _rh,
        )
        lj = str(ROTATION_PRESET_DEFS[rid].get("label_ja", rid))
        st = _row_stats(rows, lj)
        st["preset_id"] = rid
        rot_out.append(st)

    _print_report(
        args.out,
        args.seed,
        args.games,
        str(home0.name),
        str(away0.name),
        ps_out,
        rot_out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
