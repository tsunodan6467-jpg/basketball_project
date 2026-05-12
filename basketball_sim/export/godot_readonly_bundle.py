"""
9 画面分の Godot 向け *_from_python.json を一括生成する CLI。

各画面の既存 export_*_from_world を呼ぶだけ。セーブは読み取りのみ（各 export 内の load_world）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from basketball_sim.export.club_history_readonly import export_club_history_json_from_world
from basketball_sim.export.facility_summary_readonly import export_facility_summary_json_from_world
from basketball_sim.export.finance_summary_readonly import export_finance_summary_json_from_world
from basketball_sim.export.home_dashboard_readonly import export_home_dashboard_json_from_world
from basketball_sim.export.owner_mission_readonly import export_owner_mission_json_from_world
from basketball_sim.export.roster_readonly import export_roster_json_from_world
from basketball_sim.export.schedule_readonly import export_schedule_json_from_world
from basketball_sim.export.standings_readonly import export_standings_json_from_world
from basketball_sim.export.tactics_summary_readonly import export_tactics_summary_json_from_world


def export_godot_readonly_bundle(
    save_path: Path | str,
    output_dir: Path | str,
    *,
    max_upcoming: int = 8,
    max_history: int = 5,
    max_missions: int = 8,
    max_players: int = 8,
    continue_on_error: bool = False,
) -> Dict[str, Any]:
    """
    ``output_dir`` に 9 つの ``*_from_python.json`` を書き出す。

    Args:
        save_path: 読み取り専用の .sav パス。
        output_dir: 出力先ディレクトリ（存在しなければ作成）。
        max_upcoming: ``export_schedule_json_from_world`` に渡す既定（各 CLI と同じ 8）。
        max_history: ``export_finance_summary_json_from_world`` に渡す既定（finance CLI 既定 5）。
        max_missions: ``export_owner_mission_json_from_world`` の既定 8。
        max_players: ``export_tactics_summary_json_from_world`` の既定 8。
        continue_on_error: True のとき例外を記録して次へ進む。False のとき最初の失敗で打ち切り。
    """
    save = Path(save_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks: List[Tuple[str, str, Callable[[Path], Any]]] = [
        ("home_dashboard", "home_dashboard_from_python.json", lambda op: export_home_dashboard_json_from_world(save, op)),
        ("roster", "roster_from_python.json", lambda op: export_roster_json_from_world(save, op)),
        ("club_history", "club_history_from_python.json", lambda op: export_club_history_json_from_world(save, op)),
        ("standings", "standings_from_python.json", lambda op: export_standings_json_from_world(save, op)),
        (
            "schedule",
            "schedule_from_python.json",
            lambda op: export_schedule_json_from_world(save, op, max_upcoming=max_upcoming),
        ),
        ("facility_summary", "facility_summary_from_python.json", lambda op: export_facility_summary_json_from_world(save, op)),
        (
            "finance_summary",
            "finance_summary_from_python.json",
            lambda op: export_finance_summary_json_from_world(save, op, max_history=max_history),
        ),
        (
            "owner_mission",
            "owner_mission_from_python.json",
            lambda op: export_owner_mission_json_from_world(save, op, max_missions=max_missions),
        ),
        (
            "tactics_summary",
            "tactics_summary_from_python.json",
            lambda op: export_tactics_summary_json_from_world(save, op, max_players=max_players),
        ),
    ]

    succeeded: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []

    for key, filename, runner in tasks:
        out_path = out_dir / filename
        try:
            runner(out_path)
        except Exception as exc:
            err_text = f"{type(exc).__name__}: {exc}"
            failed.append({"key": key, "output": str(out_path), "error": err_text})
            if not continue_on_error:
                print(f"Bundle failed: {filename}: {err_text}", file=sys.stderr)
                return {
                    "output_dir": str(out_dir.resolve()),
                    "succeeded": succeeded,
                    "failed": failed,
                    "success_count": len(succeeded),
                    "failed_count": len(failed),
                }
            continue
        print(f"Wrote {out_path}")
        succeeded.append({"key": key, "output": str(out_path.resolve())})

    print(f"Bundle complete: {len(succeeded)} succeeded, {len(failed)} failed")
    return {
        "output_dir": str(out_dir.resolve()),
        "succeeded": succeeded,
        "failed": failed,
        "success_count": len(succeeded),
        "failed_count": len(failed),
    }


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export all 9 Godot *_from_python.json files from a single .sav.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write the 9 *_from_python.json files (created if missing)",
    )
    parser.add_argument(
        "--max-upcoming",
        type=int,
        default=8,
        metavar="N",
        help="Passed to schedule export (default: 8)",
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=5,
        metavar="N",
        help="Passed to finance_summary export (default: 5, same as finance_summary_readonly CLI)",
    )
    parser.add_argument(
        "--max-missions",
        type=int,
        default=8,
        metavar="N",
        help="Passed to owner_mission export (default: 8)",
    )
    parser.add_argument(
        "--max-players",
        type=int,
        default=8,
        metavar="N",
        help="Passed to tactics_summary export (default: 8)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue after a failed export; exit 1 if any failed",
    )
    args = parser.parse_args(argv)

    result = export_godot_readonly_bundle(
        args.save,
        args.output_dir,
        max_upcoming=int(args.max_upcoming),
        max_history=int(args.max_history),
        max_missions=int(args.max_missions),
        max_players=int(args.max_players),
        continue_on_error=bool(args.continue_on_error),
    )
    return 0 if result["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
