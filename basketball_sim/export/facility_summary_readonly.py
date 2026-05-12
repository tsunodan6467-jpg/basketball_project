"""
Godot 施設サマリー（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team の施設関連スカラーを getattr で読むのみ（代入・レベル変更・投資処理は行わない）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SCREEN_TITLE = "施設サマリー（閲覧）"
DEFAULT_TEAM_NAME = "自クラブ"
FACILITY_MAX_LEVEL = 10
FACILITY_COUNT = 4

DEFAULT_NOTES: List[str] = [
    "読み取り専用。施設投資やレベルアップ操作は含みません。",
]

_EFFECT_HINTS: Dict[str, str] = {
    "arena": "集客・収入・ホーム環境に関わる施設です。",
    "training": "育成・練習環境に関わる施設です。",
    "medical": "負傷・疲労ケアに関わる施設です。",
    "front_office": "経営・編成・クラブ運営に関わる施設です。",
}

_FACILITY_DEFS: List[Dict[str, str]] = [
    {"key": "arena", "attr": "arena_level", "label": "アリーナ"},
    {"key": "training", "attr": "training_facility_level", "label": "練習施設"},
    {"key": "medical", "attr": "medical_facility_level", "label": "メディカル"},
    {"key": "front_office", "attr": "front_office_level", "label": "フロントオフィス"},
]


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


def _clamp_level_display(value: Any) -> int:
    """表示用に 1〜10 に収める（Team 本体は変更しない）。"""
    if value is None:
        return 1
    try:
        if isinstance(value, str) and not value.strip():
            return 1
        n = int(float(value))
    except (TypeError, ValueError):
        return 1
    return max(1, min(FACILITY_MAX_LEVEL, n))


def _facility_upgrade_points_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, n)


def _team_display_name(team: Any) -> str:
    if team is None:
        return DEFAULT_TEAM_NAME
    n = _safe_get(team, "name", None)
    if isinstance(n, str) and n.strip():
        return n.strip()
    return DEFAULT_TEAM_NAME


def _league_level_optional(team: Any) -> Any:
    if team is None:
        return None
    lv = _safe_get(team, "league_level", None)
    if lv is None:
        return None
    try:
        return int(lv)
    except (TypeError, ValueError):
        return None


def build_facility_summary_readonly_dict(team: Any) -> Dict[str, Any]:
    """
    Godot 向け施設サマリー dict を返す（読み取り専用）。

    team が None の場合も例外にしない（既定値と注記）。
    """
    notes = list(DEFAULT_NOTES)
    if team is None:
        notes.append("チーム情報が未接続のため既定値を表示しています。")

    levels: List[int] = []
    facilities: List[Dict[str, Any]] = []
    for spec in _FACILITY_DEFS:
        raw = _safe_get(team, spec["attr"], None) if team is not None else None
        lv = _clamp_level_display(raw)
        levels.append(lv)
        facilities.append(
            {
                "key": spec["key"],
                "label": spec["label"],
                "level": lv,
                "max_level": FACILITY_MAX_LEVEL,
                "level_label": f"Lv.{lv} / {FACILITY_MAX_LEVEL}",
                "effect_hint": _EFFECT_HINTS.get(spec["key"], ""),
            }
        )

    pts_src = _safe_get(team, "facility_upgrade_points", None) if team is not None else None
    pts = _facility_upgrade_points_int(pts_src)

    avg = sum(levels) / float(FACILITY_COUNT) if levels else 1.0
    avg_rounded = round(avg, 1)
    max_lv = max(levels) if levels else 1

    summary: Dict[str, Any] = {
        "facility_upgrade_points": pts,
        "average_level": avg_rounded,
        "max_level": FACILITY_MAX_LEVEL,
        "facility_count": FACILITY_COUNT,
    }

    team_name = _team_display_name(team)
    ll = _league_level_optional(team)

    lines_overview = [
        f"施設強化ポイント: {pts}",
        f"平均施設レベル: {avg_rounded} / {FACILITY_MAX_LEVEL}",
        f"最高施設レベル: {max_lv} / {FACILITY_MAX_LEVEL}",
    ]
    lines_current = [
        f"{facilities[0]['label']} Lv.{facilities[0]['level']}",
        f"{facilities[1]['label']} Lv.{facilities[1]['level']}",
        f"{facilities[2]['label']} Lv.{facilities[2]['level']}",
        f"{facilities[3]['label']} Lv.{facilities[3]['level']}",
    ]
    lines_caution = [
        "読み取り専用です。",
        "施設投資・レベルアップ操作は未接続です。",
    ]

    sections: List[Dict[str, Any]] = [
        {"title": "施設概要", "lines": lines_overview},
        {"title": "現在の施設", "lines": lines_current},
        {"title": "注意", "lines": lines_caution},
    ]

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": team_name,
        "league_level": ll,
        "summary": summary,
        "facilities": facilities,
        "sections": sections,
        "notes": notes,
    }


def write_facility_summary_json(data: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_facility_summary_json_from_world(save_path: Path | str, output_path: Path | str) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で施設サマリー用 JSON を書き出す。セーブファイルは上書きしない。

    resume_season は参照しない（Team スカラーのみ）。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    snap = build_facility_summary_readonly_dict(user)
    write_facility_summary_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot facility summary JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    args = parser.parse_args(argv)
    export_facility_summary_json_from_world(args.save, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
