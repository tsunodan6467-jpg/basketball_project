"""
Read-only export: ラウンド進行プレビューを .sav から JSON / CLI 出力する。

- `.sav` は load_world で読み込むだけ。上書きしない。
- simulate_next_round / Match.simulate は呼ばない。
- save_world は呼ばない。
- Godot 自動起動なし。
- basketball_sim.systems.round_advance_preview の dict / lines を再利用する。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.round_advance_preview import (
    build_round_advance_preview_dict,
    format_round_advance_preview_lines,
)

__all__ = [
    "write_round_advance_preview_json",
    "build_round_advance_preview_dict_from_world",
    "export_round_advance_preview_json_from_world",
    "format_round_advance_preview_lines_from_world",
]


def _resolve_free_agents(payload: Dict[str, Any], season: Any) -> Any:
    fa = payload.get("free_agents")
    if fa is not None:
        return fa
    if season is not None:
        season_fa = getattr(season, "free_agents", None)
        if season_fa is not None:
            return season_fa
    return None


def _print_line(line: str) -> None:
    text = str(line)
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write((text + "\n").encode(enc, errors="replace"))


def _load_world_context(
    save_path: Path | str,
) -> Tuple[Any, Any, Optional[int], Optional[bool], Any]:
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    season = payload.get("resume_season")

    raw_sc = payload.get("season_count")
    try:
        season_count_i: Optional[int] = int(raw_sc) if raw_sc is not None else None
    except (TypeError, ValueError):
        season_count_i = None

    raw_am = payload.get("at_annual_menu")
    if raw_am is None:
        at_annual_i: Optional[bool] = None
    else:
        at_annual_i = bool(raw_am)

    free_agents = _resolve_free_agents(payload, season)
    return season, user, season_count_i, at_annual_i, free_agents


def write_round_advance_preview_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_round_advance_preview_dict_from_world(
    save_path: Path | str,
    *,
    max_events: int = 32,
    include_weekly_check: bool = True,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でラウンド進行プレビュー dict を返す。セーブファイルは上書きしない。
    """
    season, user, season_count, at_annual_menu, free_agents = _load_world_context(save_path)
    return build_round_advance_preview_dict(
        season,
        user,
        season_count=season_count,
        at_annual_menu=at_annual_menu,
        free_agents=free_agents,
        max_events=max_events,
        include_weekly_check=include_weekly_check,
    )


def export_round_advance_preview_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_events: int = 32,
    include_weekly_check: bool = True,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でラウンド進行プレビュー JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    snap = build_round_advance_preview_dict_from_world(
        save_path,
        max_events=max_events,
        include_weekly_check=include_weekly_check,
    )
    write_round_advance_preview_json(snap, output_path)
    return snap


def format_round_advance_preview_lines_from_world(
    save_path: Path | str,
    *,
    max_events: int = 32,
    include_weekly_check: bool = True,
) -> List[str]:
    """セーブを読み込んで CLI 表示用 lines を返す（ファイル書き出しなし）。"""
    season, user, season_count, at_annual_menu, free_agents = _load_world_context(save_path)
    return format_round_advance_preview_lines(
        season,
        user,
        season_count=season_count,
        at_annual_menu=at_annual_menu,
        free_agents=free_agents,
        max_events=max_events,
        include_weekly_check=include_weekly_check,
    )


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export round advance preview JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-events",
        type=int,
        default=32,
        help="Max rows in next_round_events (default: 32)",
    )
    parser.add_argument(
        "--no-weekly-check",
        action="store_true",
        help="Skip weekly_check_lines in preview",
    )
    parser.add_argument(
        "--print-lines",
        action="store_true",
        help="Print preview lines to stdout",
    )
    args = parser.parse_args(argv)
    include_weekly_check = not args.no_weekly_check
    export_round_advance_preview_json_from_world(
        args.save,
        args.output,
        max_events=int(args.max_events),
        include_weekly_check=include_weekly_check,
    )
    if args.print_lines:
        for line in format_round_advance_preview_lines_from_world(
            args.save,
            max_events=int(args.max_events),
            include_weekly_check=include_weekly_check,
        ):
            _print_line(line)
    _print_line(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
