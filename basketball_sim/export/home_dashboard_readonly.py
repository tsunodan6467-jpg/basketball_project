"""
Godot ホーム画面向けの読み取り専用スナップショット（DTO）。

- Tk / MainMenuView には依存しない。
- セーブファイルを書き換えない。export 用に load_world するのは読み取りのみ（既存の復元経路）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 小さな取得ヘルパ（MainMenuView._safe_get 相当・UI 非依存）
# ---------------------------------------------------------------------------


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


def _first_non_empty(*values: Any) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _team_display_name(team: Any) -> str:
    n = _safe_get(team, "name", None)
    if isinstance(n, str) and n.strip():
        return n.strip()
    return "自クラブ"


def _iter_league_teams(season: Any, team: Any) -> List[Any]:
    """MainMenuView._iter_league_teams と同等の母集団（読み取り専用）。"""
    if season is not None and team is not None:
        leagues = _safe_get(season, "leagues", None)
        level = _safe_get(team, "league_level", None)
        try:
            if isinstance(leagues, dict) and level in leagues and leagues[level]:
                return list(leagues[level])
        except Exception:
            pass
    teams = _first_non_empty(
        _safe_get(season, "teams", None),
        _safe_get(season, "league_teams", None),
        _safe_get(team, "league_teams", None),
    )
    if teams:
        return list(teams)
    return [team] if team is not None else []


def _compute_rank_text(season: Any, team: Any) -> str:
    if team is None:
        return "-"
    team_name = _team_display_name(team)
    ranked_list = list(_iter_league_teams(season, team))
    ranked = sorted(
        ranked_list,
        key=lambda t: (
            -(int(_safe_get(t, "regular_wins", 0) or 0)),
            int(_safe_get(t, "regular_losses", 0) or 0),
            str(_safe_get(t, "name", "")),
        ),
    )
    for idx, t in enumerate(ranked, start=1):
        if str(_safe_get(t, "name", "")) == team_name:
            return f"{idx}位"
    return "-"


def _owner_trust_text(team: Any) -> str:
    value = _first_non_empty(
        _safe_get(team, "owner_trust", None),
        _safe_get(team, "owner_confidence", None),
        _safe_get(team, "chairman_trust", None),
    )
    if value is None:
        return "未設定"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _money_text(team: Any) -> str:
    try:
        from basketball_sim.systems.money_display import format_money_yen_ja_readable

        return format_money_yen_ja_readable(int(_safe_get(team, "money", 0) or 0))
    except Exception:
        raw = _safe_get(team, "money", None)
        if raw is None:
            return "資金: 取得できません"
        return f"資金: {raw}"


def _season_progress_label(season: Any) -> str:
    if season is None:
        return "シーズン未接続"
    try:
        from basketball_sim.systems.schedule_display import main_top_bar_progress_label

        sn = int(_safe_get(season, "season_no", 1) or 1)
        cr = int(_safe_get(season, "current_round", 0) or 0)
        tr = int(_safe_get(season, "total_rounds", 0) or 0)
        fin = bool(_safe_get(season, "season_finished", False))
        return main_top_bar_progress_label(
            season,
            season_year=sn,
            current_round=cr,
            total_rounds=tr,
            season_finished=fin,
        )
    except Exception:
        return "シーズン進行中"


def _division_text(team: Any) -> str:
    lv = _safe_get(team, "league_level", None)
    if lv is None:
        return "所属未定"
    try:
        return f"D{int(lv)}"
    except Exception:
        return str(lv)


def _salary_cap_summary(team: Any) -> str:
    try:
        from basketball_sim.systems.contract_logic import get_team_payroll
        from basketball_sim.systems.money_display import format_money_yen_ja_readable
        from basketball_sim.systems.salary_cap_budget import (
            cap_status,
            compute_luxury_tax,
            get_soft_cap,
            league_level_for_team,
        )

        if team is None:
            return "給与キャップ：チームなし"
        payroll = int(get_team_payroll(team))
        lv = league_level_for_team(team)
        league_cap = int(get_soft_cap(league_level=lv))
        st = cap_status(payroll, league_level=lv)
        status_ja = {
            "under_cap": "キャップ内",
            "over_soft_cap": "キャップ超過",
        }.get(str(st), str(st))
        room_soft = league_cap - payroll
        if room_soft >= 0:
            room_str = f"余裕 {format_money_yen_ja_readable(room_soft)}"
        else:
            room_str = f"超過 {format_money_yen_ja_readable(abs(room_soft))}"
        tax = int(compute_luxury_tax(payroll, league_level=lv))
        tax_str = f" / 贅沢税 {format_money_yen_ja_readable(tax)}" if tax > 0 else ""
        return (
            f"給与合計 {format_money_yen_ja_readable(payroll)}（キャップ "
            f"{format_money_yen_ja_readable(league_cap)}） | {status_ja} | {room_str}{tax_str}"
        )
    except Exception:
        return "給与キャップ：未接続"


def _is_injured_player(player: Any) -> bool:
    m = getattr(player, "is_injured", None)
    if callable(m):
        try:
            return bool(m())
        except Exception:
            return False
    return bool(_safe_get(player, "injured", False))


def _injury_warning_note(team: Any) -> str:
    if team is None:
        return "注意事項：未接続"
    players = _safe_get(team, "players", None) or []
    if not isinstance(players, (list, tuple)):
        return "注意事項：未接続"
    n = 0
    for p in players:
        try:
            if _is_injured_player(p):
                n += 1
        except Exception:
            continue
    if n:
        return f"負傷者が {n} 名います（詳細は本ゲーム内メニューで確認）"
    return "目立った注意事項はありません（簡易表示）"


def _recent_form_text(team: Any) -> str:
    """直近5試合の文字列。取得できなければフォールバック。"""
    getter = getattr(team, "recent_results_summary", None) if team is not None else None
    if callable(getter):
        try:
            s = getter()
            if isinstance(s, str) and s.strip():
                return s.strip()
        except Exception:
            pass
    # Team に履歴文字列属性がある場合のみ（存在しない環境ではスキップ）
    for attr in ("recent_form_text", "last_five_games_text"):
        raw = _safe_get(team, attr, None)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return "直近成績：未接続"


def _next_game_one_line(season: Any, team: Any) -> str:
    if season is None or team is None:
        return "次戦情報：未接続"
    try:
        from basketball_sim.systems.schedule_display import (
            build_division_playoff_main_next_lines,
            build_emperor_cup_main_next_lines,
            next_advance_display_hints,
            upcoming_rows_for_user_team,
        )

        sn = int(_safe_get(season, "season_no", 1) or 1)
        cup = build_emperor_cup_main_next_lines(season, team, season_year=sn)
        if cup:
            parts = [str(x).strip() for x in cup[:3] if str(x).strip()]
            if parts:
                return " / ".join(parts)
        po = build_division_playoff_main_next_lines(season, team, season_year=sn)
        if po:
            parts = [str(x).strip() for x in po[:3] if str(x).strip()]
            if parts:
                return " / ".join(parts)
        rows = upcoming_rows_for_user_team(season, team, league_only=False)
        if rows:
            r0 = rows[0]
            opp = str(r0.get("opponent") or "").strip() or "対戦相手未定"
            ha = str(r0.get("ha_long") or r0.get("ha_short") or "").strip() or "—"
            comp = str(r0.get("competition_display") or "").strip() or "試合"
            month = str(r0.get("month_label") or "").strip()
            head = f"次戦：{opp}（{ha}）・{comp}"
            return f"{head}・{month}" if month else head
        _block, one = next_advance_display_hints(season, team)
        if isinstance(one, str) and one.strip():
            return one.strip()
    except Exception:
        pass
    return "次戦情報：未接続"


def _club_summary_lines(season: Any, team: Any, rank_record: str, money: str, division: str) -> List[str]:
    lines: List[str] = [
        f"順位・戦績: {rank_record}",
        f"ディビジョン: {division} / 資金: {money}",
    ]
    if season is not None:
        fin = bool(_safe_get(season, "season_finished", False))
        lines.append("シーズン状態: 終了" if fin else "シーズン状態: 進行中")
    else:
        lines.append("シーズン状態: セーブにシーズン未同梱（年度メニュー直後など）")
    try:
        cap_line = _salary_cap_summary(team)
        if cap_line != "給与キャップ：未接続":
            lines.append(cap_line)
    except Exception:
        pass
    if len(lines) < 4:
        lines.append("※ 本ブロックは読み取り専用スナップショットです（本番ロジック非変更）。")
    return lines[:6]


def _task_lines(team: Any, season: Any, *, max_tasks: int) -> List[str]:
    out: List[str] = []
    if team is None:
        return ["チーム情報がありません（セーブ要確認）"][:max_tasks]
    pts = _safe_get(team, "facility_upgrade_points", None)
    if isinstance(pts, (int, float)) and int(pts) > 0:
        out.append(f"施設投資ポイント {int(pts)} 点（経営メニューで確認）")
    players = _safe_get(team, "players", None) or []
    if isinstance(players, (list, tuple)):
        inj = sum(1 for p in players if _is_injured_player(p))
        if inj:
            out.append(f"負傷者 {inj} 名の確認（人事・戦術メニュー）")
    fa_short = _safe_get(team, "fa_shortlist", None)
    if isinstance(fa_short, list) and fa_short:
        out.append(f"FA候補 {len(fa_short)} 件（人事メニュー）")
    mission = _safe_get(team, "owner_mission", None)
    if mission:
        out.append(f"オーナーミッション: {mission}")
    if not out:
        out.append("ホーム上の緊急タスクは検出されませんでした（各メニューで随時確認）")
    out.append("次戦に向けて戦術・ローテーションを確認（読み取り確認）")
    return out[:max_tasks]


def _news_lines(team: Any, season: Any, *, max_news: int) -> List[str]:
    name = _team_display_name(team)
    rank = _compute_rank_text(season, team)
    wins = int(_safe_get(team, "regular_wins", 0) or 0)
    losses = int(_safe_get(team, "regular_losses", 0) or 0)
    lines = [
        f"{name} は現在 {rank}、戦績 {wins}勝{losses}敗（スナップショット）",
        "リーグの動きは情報メニューで詳細確認できます（本DTOは簡易ヘッドラインのみ）。",
    ]
    if season is not None and bool(_safe_get(season, "season_finished", False)):
        lines.append("レギュラーシーズンは終了状態です（オフシーズンは本ゲーム内で進行）。")
    return lines[:max_news]


def build_home_dashboard_readonly_dict(
    season: Any,
    team: Any,
    *,
    max_tasks: int = 3,
    max_news: int = 3,
) -> Dict[str, Any]:
    """
    Godot `home_dashboard_mock.json` と同一キーの dict を返す（読み取り専用）。

    season が None の場合（年度メニュー直後のセーブ等）は、シーズン依存項目をフォールバックする。
    """
    club_name = _team_display_name(team)
    season_label = _season_progress_label(season)
    division = _division_text(team)
    rank = _compute_rank_text(season, team)
    wins = int(_safe_get(team, "regular_wins", 0) or 0)
    losses = int(_safe_get(team, "regular_losses", 0) or 0)
    if rank == "-":
        rank_record = f"順位未確定 / {wins}勝{losses}敗"
    else:
        rank_record = f"{rank} / {wins}勝{losses}敗"
    money = _money_text(team)
    owner_trust = _owner_trust_text(team)
    salary_cap = _salary_cap_summary(team)
    recent_form = _recent_form_text(team)
    warnings = _injury_warning_note(team)
    next_game = _next_game_one_line(season, team)
    club_summary = _club_summary_lines(season, team, rank_record, money, division)
    tasks = _task_lines(team, season, max_tasks=max_tasks)
    news = _news_lines(team, season, max_news=max_news)
    return {
        "club_name": club_name,
        "season_label": season_label,
        "division": division,
        "rank_record": rank_record,
        "money": money,
        "owner_trust": owner_trust,
        "salary_cap": salary_cap,
        "recent_form": recent_form,
        "warnings": warnings,
        "next_game": next_game,
        "club_summary": club_summary,
        "tasks": tasks,
        "news": news,
    }


def write_home_dashboard_json(snapshot: Dict[str, Any], output_path: Path | str) -> None:
    """UTF-8 で JSON を書き出す（pickle セーブは触らない）。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_home_dashboard_json_from_world(save_path: Path | str, output_path: Path | str) -> Dict[str, Any]:
    """
    セーブを **読み込むだけ** でホーム用 JSON を書き出す。セーブファイルは上書きしない。

    Returns:
        書き出したスナップショット dict（呼び出し側のテスト用）。
    """
    from basketball_sim.persistence.save_load import find_user_team, load_world, validate_payload

    payload = load_world(save_path)
    validate_payload(payload)
    teams = payload["teams"]
    user = find_user_team(teams, int(payload["user_team_id"]))
    season = payload.get("resume_season")
    snap = build_home_dashboard_readonly_dict(season, user, max_tasks=3, max_news=3)
    write_home_dashboard_json(snap, output_path)
    return snap


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only: export Godot home dashboard JSON from a .sav file.",
    )
    parser.add_argument("--save", type=Path, required=True, help="Path to .sav (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Output .json path")
    args = parser.parse_args(argv)
    export_home_dashboard_json_from_world(args.save, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
