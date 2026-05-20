"""
Godot ロスター閲覧向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- format_gm_roster_text / compute_auto_role_tags_for_team 等、
  ensure_team_tactics_on_team を呼び得る経路は使わない。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from basketball_sim.systems.japan_regulation_display import get_player_nationality_bucket_label
from basketball_sim.systems.money_display import format_money_yen_ja_readable

_POSITION_ORDER = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}


def _sort_rosters_for_readonly_display(players: List[Any]) -> List[Any]:
    """
    docs/GM_ROSTER_DISPLAY_RULES.md に合わせた並び
    （ポジション PG→C → 同一ポジ OVR 降順 → 名前）。

    gm_dashboard_text.sort_roster_for_gm_view と同一の並びになるようキーを揃えるが、
    getattr が None を返す簡易オブジェクトでも落ちないよう int 化する。
    """

    def _pos_rank(p: Any) -> int:
        raw = getattr(p, "position", None)
        if raw is None:
            return 99
        s = str(raw).strip()
        if not s:
            return 99
        return int(_POSITION_ORDER.get(s, 99))

    def _ovr_neg(p: Any) -> int:
        v = getattr(p, "ovr", None)
        try:
            return -int(v if v is not None else 0)
        except (TypeError, ValueError):
            return 0

    def _name(p: Any) -> str:
        return str(getattr(p, "name", "") or "")

    return sorted(players, key=lambda p: (_pos_rank(p), _ovr_neg(p), _name(p)))


ROSTER_COLUMNS: List[str] = [
    "order",
    "name",
    "position",
    "age",
    "ovr",
    "salary",
    "contract",
    "nationality_slot",
    "status",
]

DEFAULT_NOTES: List[str] = [
    "読み取り専用。操作は含みません。",
]


def _safe_str(value: Any, default: str) -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _safe_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _contract_label(years_left: Any) -> str:
    if years_left is None:
        return "-"
    try:
        n = int(years_left)
    except (TypeError, ValueError):
        return "-"
    if n < 0:
        return "-"
    return f"残り{n}年"


def _status_line(player: Any) -> str:
    injured = False
    games_left = 0
    fn = getattr(player, "is_injured", None)
    if callable(fn):
        try:
            injured = bool(fn())
        except Exception:
            injured = False
    if not injured and bool(getattr(player, "injured", False)):
        injured = True
    if not injured:
        try:
            games_left = int(getattr(player, "injury_games_left", 0) or 0)
        except (TypeError, ValueError):
            games_left = 0
        injured = games_left > 0

    if injured:
        try:
            g = int(getattr(player, "injury_games_left", 0) or 0)
        except (TypeError, ValueError):
            g = 0
        return f"負傷中（残り{g}試合）"

    try:
        fatigue = int(getattr(player, "fatigue", 0) or 0)
    except (TypeError, ValueError):
        fatigue = 0
    if fatigue >= 60:
        return "疲労高"
    if fatigue >= 40:
        return "疲労あり"
    return "良好"


def _salary_fields(player: Any) -> tuple[int, str]:
    raw = getattr(player, "salary", 0)
    try:
        yen = int(raw)
    except (TypeError, ValueError):
        yen = 0
    yen = max(0, yen)
    try:
        label = format_money_yen_ja_readable(yen)
    except Exception:
        label = str(yen)
    return yen, label


def _nationality_slot_label(player: Any) -> str:
    try:
        return str(get_player_nationality_bucket_label(player))
    except Exception:
        return _safe_str(getattr(player, "nationality", None), "不明")


def _player_id_int(player: Any) -> int:
    raw = getattr(player, "player_id", None)
    if raw is None:
        raise ValueError("player_id is required for roster readonly export")
    return int(raw)


def _player_row(order: int, player: Any) -> Dict[str, Any]:
    name = _safe_str(getattr(player, "name", None), "無名選手")
    position = _safe_str(getattr(player, "position", None), "-")
    age_val = _safe_int_optional(getattr(player, "age", None))

    ovr_raw = getattr(player, "ovr", None)
    try:
        ovr = int(ovr_raw) if ovr_raw is not None else 0
    except (TypeError, ValueError):
        ovr = 0

    yen, salary_label = _salary_fields(player)
    cy = getattr(player, "contract_years_left", None)
    contract_label = _contract_label(cy)
    try:
        contract_years_left_int = int(cy) if cy is not None else None
    except (TypeError, ValueError):
        contract_years_left_int = None

    return {
        "player_id": _player_id_int(player),
        "order": int(order),
        "name": name,
        "position": position,
        "age": age_val,
        "ovr": ovr,
        "salary_yen": yen,
        "salary_label": salary_label,
        "contract_years_left": contract_years_left_int,
        "contract_label": contract_label,
        "nationality_slot": _nationality_slot_label(player),
        "status": _status_line(player),
    }


def _build_summary(team: Any, all_players: List[Any]) -> Dict[str, Any]:
    roster_count = len(all_players)
    getter = getattr(team, "get_nationality_slot_summary", None)
    if callable(getter):
        try:
            s = getter(list(all_players))
            if isinstance(s, dict):
                return {
                    "roster_count": int(s.get("total", roster_count)),
                    "domestic_count": int(s.get("domestic", 0)),
                    "foreign_count": int(s.get("foreign", 0)),
                    "asia_or_naturalized_count": int(s.get("asia_or_naturalized", 0)),
                }
        except Exception:
            pass
    return {"roster_count": roster_count}


def build_roster_readonly_dict(team: Any, *, max_players: Optional[int] = None) -> Dict[str, Any]:
    """
    ロスター閲覧用 dict を返す（pickle セーブは触らない）。

    並び: docs/GM_ROSTER_DISPLAY_RULES.md / sort_roster_for_gm_view と同キー
    （None 安全なローカルソート。gm_dashboard_text は import しない）。
    """
    raw_players = list(getattr(team, "players", None) or [])
    sorted_players = _sort_rosters_for_readonly_display(raw_players)
    summary = _build_summary(team, sorted_players)

    if max_players is not None:
        try:
            cap = int(max_players)
        except (TypeError, ValueError):
            cap = 0
        if cap > 0:
            visible = sorted_players[:cap]
        else:
            visible = []
    else:
        visible = list(sorted_players)

    team_name = _safe_str(getattr(team, "name", None), "自クラブ")
    lv_raw = getattr(team, "league_level", None)
    league_level: Optional[int]
    try:
        league_level = int(lv_raw) if lv_raw is not None else None
    except (TypeError, ValueError):
        league_level = None

    rows: List[Dict[str, Any]] = []
    for i, p in enumerate(visible, start=1):
        rows.append(_player_row(i, p))

    return {
        "screen_title": "ロスター（閲覧）",
        "team_name": team_name,
        "league_level": league_level,
        "summary": summary,
        "columns": list(ROSTER_COLUMNS),
        "players": rows,
        "notes": list(DEFAULT_NOTES),
    }


def write_roster_json(data: Dict[str, Any], output_path: Path | str) -> Path:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def export_roster_json_from_world(save_path: Path | str, output_path: Path | str) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でロスター用 JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    snap = build_roster_readonly_dict(user, max_players=None)
    write_roster_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot roster JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    args = parser.parse_args(argv)
    export_roster_json_from_world(args.save, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
