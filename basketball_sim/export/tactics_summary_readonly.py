"""
Godot 戦術・ローテーションサマリー（閲覧）向けの読み取り専用スナップショット（DTO）。

- Tk 仮 GUI / Godot には依存しない。
- セーブファイルを書き換えない。export は load_world による読み取りのみ。
- Team.team_tactics への代入・キー更新は行わない。
- メモリ上で Team を正規化するヘルパー（ensure 系・safe-get 系の戦術初期化）は呼ばない。
- getattr で読んだ dict は copy.deepcopy したコピーに対してのみ normalize_team_tactics を適用する。
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCREEN_TITLE = "戦術・ローテーションサマリー（閲覧）"

DEFAULT_NOTES: List[str] = [
    "読み取り専用。戦術変更・ローテーション保存・先発自動決定などの操作は含みません。",
]

NOTE_NO_TEAM = "チーム情報が未接続のため、戦術・ローテーション情報の一部は表示できません。"

NOTE_NO_TACTICS = "戦術設定が未接続です。"

# team_tactics.py のキーに合わせた表示ラベル（読取専用・固定文言）
_OFFENSE_TEMPO_JA = {
    "slow": "遅め（スロー）",
    "standard": "標準",
    "fast": "速め（ファスト）",
}
_OFFENSE_STYLE_JA = {
    "balanced": "バランス",
    "inside": "ペイント重視",
    "three_point": "3ポイント重視",
    "drive": "ドライブ重視",
}
_OFFENSE_CREATION_JA = {
    "ball_move": "ボールムーブ",
    "pick_and_roll": "ピックアンドロール",
    "iso": "アイソレーション",
    "post": "ポスト",
}
_DEFENSE_STYLE_JA = {
    "balanced": "バランス",
    "protect_paint": "ペイント死守",
    "protect_three": "外線死守",
    "pressure": "プレッシャー",
}
_REBOUND_STYLE_JA = {
    "get_back": "リターンメイン",
    "balanced": "バランス",
    "crash_offense": "オフェンスクラッシュ",
}
_TRANSITION_STYLE_JA = {
    "push": "プッシュ",
    "situational": "状況次第",
    "half_court": "ハーフコート",
}
_SUB_POLICY_JA = {
    "standard": "スタンダード",
    "starters_long": "先発長め",
    "bench_deep": "ベンチ厚め",
    "youth_dev": "若手育成寄り",
}
_FATIGUE_POLICY_JA = {
    "strict": "厳しめ",
    "standard": "標準",
    "push": "推し進め",
}
_FOUL_POLICY_JA = {
    "early_pull": "早期交代",
    "standard": "標準",
    "ride": "抱え込み",
}
_CLUTCH_POLICY_JA = {
    "stars": "スター中心",
    "hot_hand": "ホットハンド",
    "defense": "守備重視",
    "offense": "攻撃重視",
}
_USAGE_PRIORITY_JA = {
    "win": "勝利優先",
    "balanced": "バランス",
    "development": "育成優先",
}
_AGE_BALANCE_JA = {
    "veteran": "ベテラン寄り",
    "balanced": "バランス",
    "youth": "若手寄り",
}
_INJURY_CARE_JA = {
    "high": "高（コンディション重視）",
    "standard": "標準",
    "low": "低",
}


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


def _team_display_name(team: Any) -> str:
    if team is None:
        return "-"
    n = _safe_get(team, "name", None)
    if isinstance(n, str) and n.strip():
        return n.strip()
    return "-"


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


def _valid_player_ids(team: Any) -> Set[int]:
    ids: Set[int] = set()
    if team is None:
        return ids
    players = _safe_get(team, "players", None) or []
    if not isinstance(players, (list, tuple)):
        return ids
    for p in players:
        if p is None:
            continue
        pid = _safe_get(p, "player_id", None)
        try:
            if pid is not None:
                ids.add(int(pid))
        except (TypeError, ValueError):
            continue
    return ids


def _player_by_id(team: Any) -> Dict[int, Any]:
    out: Dict[int, Any] = {}
    if team is None:
        return out
    players = _safe_get(team, "players", None) or []
    if not isinstance(players, (list, tuple)):
        return out
    for p in players:
        if p is None:
            continue
        pid = _safe_get(p, "player_id", None)
        try:
            if pid is not None:
                out[int(pid)] = p
        except (TypeError, ValueError):
            continue
    return out


def _label_or_dash(mapping: Dict[str, str], key: Optional[str]) -> str:
    if key is None or not str(key).strip():
        return "-"
    k = str(key).strip()
    return mapping.get(k, k)


def _play_style_label(strategy: Optional[str]) -> str:
    if strategy is None or not str(strategy).strip():
        return "-"
    s = str(strategy).strip()
    mapping = {
        "balanced": "バランス",
        "run_and_gun": "ラン＆ガン",
        "defense": "ディフェンス重視",
        "inside": "インサイド重視",
        "three_point": "3ポイント重視",
    }
    return mapping.get(s, s)


def _normalized_tactics_copy(team: Any) -> Tuple[Dict[str, Any], bool]:
    """
    Team を変更せず、正規化済み tactics dict のみ返す。
    戻り値: (normalized_dict, had_raw_dict)
    """
    from basketball_sim.systems.team_tactics import normalize_team_tactics

    if team is None:
        return {}, False
    raw = _safe_get(team, "team_tactics", None)
    if not isinstance(raw, dict):
        return normalize_team_tactics({}, valid_player_ids=_valid_player_ids(team)), False
    snapshot = copy.deepcopy(raw)
    return normalize_team_tactics(snapshot, valid_player_ids=_valid_player_ids(team)), True


def _preset_labels(norm: Dict[str, Any]) -> Tuple[Optional[str], str, Optional[str], str]:
    from basketball_sim.systems.team_tactics import PLAYSTYLE_PRESET_DEFS, ROTATION_PRESET_DEFS

    pm = norm.get("preset_meta") if isinstance(norm.get("preset_meta"), dict) else {}
    ps_id = pm.get("playstyle_preset_id")
    ps_key = str(ps_id).strip() if ps_id is not None and str(ps_id).strip() else None
    ps_label = "-"
    if ps_key and ps_key in PLAYSTYLE_PRESET_DEFS:
        meta = PLAYSTYLE_PRESET_DEFS[ps_key]
        if isinstance(meta, dict):
            lab = meta.get("label_ja")
            if isinstance(lab, str) and lab.strip():
                ps_label = lab.strip()
            else:
                ps_label = ps_key
    elif ps_key:
        ps_label = ps_key

    rot_id = pm.get("rotation_preset_id")
    rk = str(rot_id).strip() if rot_id is not None and str(rot_id).strip() else None
    rot_label = "-"
    if rk and rk in ROTATION_PRESET_DEFS:
        meta = ROTATION_PRESET_DEFS[rk]
        if isinstance(meta, dict):
            lab = meta.get("label_ja")
            if isinstance(lab, str) and lab.strip():
                rot_label = lab.strip()
            else:
                rot_label = rk
    elif rk:
        rot_label = rk

    return ps_key, ps_label, rk, rot_label  # type: ignore[return-value]


def _build_summary(
    team: Any,
    norm: Dict[str, Any],
    *,
    had_raw_dict: bool,
    season_count: Optional[int],
    at_annual_menu: Optional[bool],
) -> Dict[str, Any]:
    ts = norm.get("team_strategy") if isinstance(norm.get("team_strategy"), dict) else {}
    rot = norm.get("rotation") if isinstance(norm.get("rotation"), dict) else {}
    starters = rot.get("starters") if isinstance(rot.get("starters"), dict) else {}
    starter_count = sum(1 for _pos, pid in starters.items() if pid is not None)
    tm = rot.get("target_minutes") if isinstance(rot.get("target_minutes"), dict) else {}
    target_minutes_count = len(tm)
    bench = rot.get("bench_order")
    bench_len = len(bench) if isinstance(bench, (list, tuple)) else 0

    play_style = None
    if team is not None:
        ps = _safe_get(team, "strategy", None)
        if ps is not None and str(ps).strip():
            play_style = str(ps).strip()

    ps_key, ps_label, rot_preset_key, rot_preset_label = _preset_labels(norm)

    offense_style = str(ts.get("offense_style") or "").strip() or None
    if offense_style == "three_point":
        three_point_policy_label = _OFFENSE_STYLE_JA.get("three_point", "3ポイント重視")
        paint_policy_label = "-"
    elif offense_style == "inside":
        three_point_policy_label = "-"
        paint_policy_label = _OFFENSE_STYLE_JA.get("inside", "ペイント重視")
    elif offense_style:
        three_point_policy_label = "-"
        paint_policy_label = "-"
    else:
        three_point_policy_label = "-"
        paint_policy_label = "-"

    return {
        "tactic_preset": ps_key,
        "tactic_preset_label": ps_label if ps_label != "-" else None,
        "play_style": play_style,
        "play_style_label": _play_style_label(play_style) if play_style else "-",
        "offense_tempo": ts.get("offense_tempo"),
        "offense_tempo_label": _label_or_dash(_OFFENSE_TEMPO_JA, str(ts.get("offense_tempo") or None)),
        "offense_focus": ts.get("offense_style"),
        "offense_focus_label": _label_or_dash(_OFFENSE_STYLE_JA, str(ts.get("offense_style") or None)),
        "offense_build": ts.get("offense_creation"),
        "offense_build_label": _label_or_dash(_OFFENSE_CREATION_JA, str(ts.get("offense_creation") or None)),
        "defense_style": ts.get("defense_style"),
        "defense_style_label": _label_or_dash(_DEFENSE_STYLE_JA, str(ts.get("defense_style") or None)),
        "rebound_style": ts.get("rebound_style"),
        "rebound_style_label": _label_or_dash(_REBOUND_STYLE_JA, str(ts.get("rebound_style") or None)),
        "transition_style": ts.get("transition_style"),
        "transition_style_label": _label_or_dash(_TRANSITION_STYLE_JA, str(ts.get("transition_style") or None)),
        "rotation_policy": rot_preset_key,
        "rotation_policy_label": rot_preset_label if rot_preset_label != "-" else None,
        "starter_count": starter_count,
        "target_minutes_count": target_minutes_count,
        "has_team_tactics": bool(team is not None and had_raw_dict),
        "has_rotation_settings": bool(starter_count > 0 or target_minutes_count > 0 or bench_len > 0),
        "three_point_policy_label": three_point_policy_label,
        "paint_policy_label": paint_policy_label,
        "season_count": season_count,
        "at_annual_menu": at_annual_menu,
    }


def _tactic_items(norm: Dict[str, Any], team: Any) -> List[Dict[str, Any]]:
    ts = norm.get("team_strategy") if isinstance(norm.get("team_strategy"), dict) else {}
    pb = norm.get("playbook") if isinstance(norm.get("playbook"), dict) else {}
    ps_key, ps_label, rot_key, rot_label = _preset_labels(norm)

    items: List[Dict[str, Any]] = []

    def add(key: str, label: str, value: Any, display: str, memo: str = "") -> None:
        items.append(
            {
                "key": key,
                "label": label,
                "value": value,
                "display_value": display,
                "memo": memo,
            }
        )

    add("tactic_preset", "戦術プリセット", ps_key, ps_label if ps_label != "-" else "未設定", "preset_meta.playstyle_preset_id")
    add("play_style", "プレイスタイル", _safe_get(team, "strategy", None) if team else None, _play_style_label(str(_safe_get(team, "strategy", None) or "") or None) if team else "-", "Team.strategy")
    add("offense_tempo", "オフェンステンポ", ts.get("offense_tempo"), _label_or_dash(_OFFENSE_TEMPO_JA, str(ts.get("offense_tempo") or None)))
    add("offense_style", "オフェンス傾向", ts.get("offense_style"), _label_or_dash(_OFFENSE_STYLE_JA, str(ts.get("offense_style") or None)))
    add("offense_creation", "オフェンス組み立て", ts.get("offense_creation"), _label_or_dash(_OFFENSE_CREATION_JA, str(ts.get("offense_creation") or None)))
    add("defense_style", "ディフェンス方針", ts.get("defense_style"), _label_or_dash(_DEFENSE_STYLE_JA, str(ts.get("defense_style") or None)))
    add("rebound_style", "リバウンド方針", ts.get("rebound_style"), _label_or_dash(_REBOUND_STYLE_JA, str(ts.get("rebound_style") or None)))
    add("transition_style", "速攻方針", ts.get("transition_style"), _label_or_dash(_TRANSITION_STYLE_JA, str(ts.get("transition_style") or None)))
    add("rotation_preset", "ローテーション用プリセット", rot_key, rot_label if rot_label != "-" else "未設定", "preset_meta.rotation_preset_id")

    # プレイブック（存在するキーのみ要約）
    pb_parts = [f"{k}:{pb.get(k)}" for k in ("pick_and_roll", "post_up", "transition") if k in pb]
    add(
        "playbook_focus",
        "プレイブック（抜粋）",
        pb_parts,
        " / ".join(pb_parts) if pb_parts else "-",
        "3P/ペイント比率は offense_style と playbook の組み合わせで読み取り",
    )
    return items


def _rotation_items(norm: Dict[str, Any]) -> List[Dict[str, Any]]:
    rot = norm.get("rotation") if isinstance(norm.get("rotation"), dict) else {}
    up = norm.get("usage_policy") if isinstance(norm.get("usage_policy"), dict) else {}
    starters = rot.get("starters") if isinstance(rot.get("starters"), dict) else {}
    starter_count = sum(1 for _p, pid in starters.items() if pid is not None)
    tm = rot.get("target_minutes") if isinstance(rot.get("target_minutes"), dict) else {}
    bench = rot.get("bench_order")
    bench_len = len(bench) if isinstance(bench, (list, tuple)) else 0

    items: List[Dict[str, Any]] = []

    def add(key: str, label: str, value: Any, display: str, memo: str = "") -> None:
        items.append({"key": key, "label": label, "value": value, "display_value": display, "memo": memo})

    add("sub_policy", "ローテーション方針（交代）", rot.get("sub_policy"), _label_or_dash(_SUB_POLICY_JA, str(rot.get("sub_policy") or None)), "rotation.sub_policy")
    add("usage_priority", "起用方針（優先度）", up.get("priority"), _label_or_dash(_USAGE_PRIORITY_JA, str(up.get("priority") or None)), "usage_policy.priority")
    add("starter_slots_filled", "先発設定数", starter_count, f"{starter_count} スロット", "rotation.starters の非空数")
    add("target_minutes_slots", "目標出場時間設定数", len(tm), f"{len(tm)} 名分", "rotation.target_minutes")
    add("bench_order_configured", "ベンチ起用順の設定", bench_len, "あり" if bench_len > 0 else "未設定/空", "rotation.bench_order")
    add("age_balance", "若手起用方針（年齢バランス）", up.get("age_balance"), _label_or_dash(_AGE_BALANCE_JA, str(up.get("age_balance") or None)), "usage_policy.age_balance")
    inj = str(up.get("injury_care") or "")
    inj_label = _label_or_dash(_INJURY_CARE_JA, inj or None)
    add("injury_care", "コンディション重視（負債管理）", up.get("injury_care"), inj_label, "usage_policy.injury_care")
    add("fatigue_policy", "疲労方針", rot.get("fatigue_policy"), _label_or_dash(_FATIGUE_POLICY_JA, str(rot.get("fatigue_policy") or None)))
    add("foul_policy", "ファウル方針", rot.get("foul_policy"), _label_or_dash(_FOUL_POLICY_JA, str(rot.get("foul_policy") or None)))
    add("clutch_policy", "クラッチ方針", rot.get("clutch_policy"), _label_or_dash(_CLUTCH_POLICY_JA, str(rot.get("clutch_policy") or None)))
    return items


def _build_player_role_items(
    team: Any,
    norm: Dict[str, Any],
    *,
    max_players: int,
) -> List[Dict[str, Any]]:
    from basketball_sim.systems.team_tactics import STARTER_POSITIONS, japanese_label_for_main_role_key

    if team is None or max_players <= 0:
        return []
    by_id = _player_by_id(team)
    rot = norm.get("rotation") if isinstance(norm.get("rotation"), dict) else {}
    starters = rot.get("starters") if isinstance(rot.get("starters"), dict) else {}
    tm_raw = rot.get("target_minutes") if isinstance(rot.get("target_minutes"), dict) else {}
    roles = norm.get("roles") if isinstance(norm.get("roles"), dict) else {}

    rows: List[Dict[str, Any]] = []
    seen: Set[int] = set()

    def append_row(
        *,
        order: int,
        pid: int,
        slot_label: str,
        is_starter: bool,
    ) -> None:
        if len(rows) >= max_players:
            return
        p = by_id.get(pid)
        name = "-"
        pos = "-"
        if p is not None:
            nm = _safe_get(p, "name", None)
            if isinstance(nm, str) and nm.strip():
                name = nm.strip()
            po = _safe_get(p, "position", None)
            if po is not None and str(po).strip():
                pos = str(po).strip()
        rdict = roles.get(str(pid))
        if not isinstance(rdict, dict):
            rdict = {}
        main_role = str(rdict.get("main_role") or "none").strip() or "none"
        role_label = japanese_label_for_main_role_key(main_role) or "未設定"
        minutes = tm_raw.get(str(pid))
        if minutes is None:
            minutes = tm_raw.get(pid)  # type: ignore[arg-type]
        tm_float: Optional[float] = None
        if minutes is not None:
            try:
                tm_float = float(minutes)
            except (TypeError, ValueError):
                tm_float = None
        tm_label = f"{tm_float:.1f} 分/試合" if tm_float is not None else "-"
        rows.append(
            {
                "order": order,
                "player_name": name,
                "role": main_role,
                "role_label": role_label,
                "position": pos,
                "target_minutes": tm_float,
                "target_minutes_label": tm_label,
                "starter": is_starter,
                "starter_label": "先発" if is_starter else "ベンチ",
                "memo": slot_label,
            }
        )
        seen.add(pid)

    order = 0
    for pos in STARTER_POSITIONS:
        if len(rows) >= max_players:
            break
        pid_raw = starters.get(pos)
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pid = None
        if pid is None or pid in seen:
            continue
        order += 1
        append_row(order=order, pid=pid, slot_label=f"先発 {pos}", is_starter=True)

    bench_order = rot.get("bench_order")
    if isinstance(bench_order, (list, tuple)):
        for pid_raw in bench_order:
            if len(rows) >= max_players:
                break
            try:
                pid = int(pid_raw)
            except (TypeError, ValueError):
                continue
            if pid in seen:
                continue
            order += 1
            append_row(order=order, pid=pid, slot_label="ベンチ順", is_starter=False)

    return rows


def _sections(team: Any, summary: Dict[str, Any], tactic_items: List[Any], rotation_items: List[Any]) -> List[Dict[str, Any]]:
    lines_intro = [
        f"チーム: {summary.get('play_style_label', '-')}",
        f"戦術プリセット: {summary.get('tactic_preset_label') or '-'}",
        f"ローテプリセット: {summary.get('rotation_policy_label') or '-'}",
    ]
    if team is None:
        lines_intro = [NOTE_NO_TEAM]

    tactic_lines = [f"{x.get('label','?')}: {x.get('display_value','-')}" for x in tactic_items[:12]]
    lines_intro = lines_intro + tactic_lines[:8]

    ts = summary
    attack_lines = [
        f"テンポ: {ts.get('offense_tempo_label', '-')}",
        f"攻撃傾向: {ts.get('offense_focus_label', '-')}",
        f"組み立て: {ts.get('offense_build_label', '-')}",
        f"3P/ペイント系の読み: {ts.get('three_point_policy_label', '-')}",
    ]
    defense_lines = [
        f"ディフェンス: {ts.get('defense_style_label', '-')}",
        f"リバウンド: {ts.get('rebound_style_label', '-')}",
        f"速攻: {ts.get('transition_style_label', '-')}",
    ]
    rot_lines = [f"{x.get('label','?')}: {x.get('display_value','-')}" for x in rotation_items[:12]]
    notes_lines = list(DEFAULT_NOTES)
    if team is not None and not summary.get("has_team_tactics"):
        notes_lines.append(NOTE_NO_TACTICS)

    return [
        {"title": "戦術概要", "lines": lines_intro},
        {"title": "攻撃方針", "lines": attack_lines},
        {"title": "守備方針", "lines": defense_lines},
        {"title": "ローテーション", "lines": rot_lines if rot_lines else ["ローテーション項目は未設定、またはデータ未接続です。"]},
        {"title": "注意", "lines": notes_lines},
    ]


def build_tactics_summary_readonly_dict(
    team: Any,
    *,
    season_count: Optional[int] = None,
    at_annual_menu: Optional[bool] = None,
    max_players: int = 8,
) -> Dict[str, Any]:
    notes: List[str] = list(DEFAULT_NOTES)
    if team is None:
        notes.append(NOTE_NO_TEAM)

    norm, had_raw = _normalized_tactics_copy(team)
    if team is not None and not had_raw:
        notes.append(NOTE_NO_TACTICS)

    summary = _build_summary(team, norm, had_raw_dict=had_raw, season_count=season_count, at_annual_menu=at_annual_menu)
    tactic_items = _tactic_items(norm, team)
    rotation_items = _rotation_items(norm)
    player_role_items = _build_player_role_items(team, norm, max_players=max(0, int(max_players)))
    sections = _sections(team, summary, tactic_items, rotation_items)

    return {
        "screen_title": SCREEN_TITLE,
        "team_name": _team_display_name(team),
        "league_level": _league_level_optional(team),
        "summary": summary,
        "tactic_items": tactic_items,
        "rotation_items": rotation_items,
        "player_role_items": player_role_items,
        "sections": sections,
        "notes": notes,
    }


def write_tactics_summary_json(data: Dict[str, Any], output_path: Path | str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_tactics_summary_json_from_world(
    save_path: Path | str,
    output_path: Path | str,
    *,
    max_players: int = 8,
) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** で戦術サマリー閲覧用 JSON を書き出す。セーブファイルは上書きしない。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
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
    data = build_tactics_summary_readonly_dict(
        user,
        season_count=season_count_i,
        at_annual_menu=at_annual_i,
        max_players=int(max_players),
    )
    write_tactics_summary_json(data, output_path)
    return data


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot tactics / rotation summary JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    parser.add_argument(
        "--max-players",
        type=int,
        default=8,
        metavar="N",
        help="Max player rows in player_role_items (default: 8)",
    )
    args = parser.parse_args(argv)
    export_tactics_summary_json_from_world(args.save, args.output, max_players=int(args.max_players))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
