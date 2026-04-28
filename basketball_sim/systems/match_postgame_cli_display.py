"""
試合直後 CLI 用の短い振り返りサマリー（表示のみ。試合結果・スタッツ計算は変更しない）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.match_preview_cli_display import build_matchup_edges_summary


def _side_key(team_id: Any, home_id: Any, away_id: Any) -> Optional[str]:
    if team_id is None:
        return None
    if team_id == home_id:
        return "home"
    if team_id == away_id:
        return "away"
    return None


def _starter_id_name_sets(starters: Any) -> Tuple[set, set]:
    ids: set = set()
    names: set = set()
    if not starters:
        return ids, names
    try:
        for p in starters:
            if p is None:
                continue
            pid = getattr(p, "player_id", None)
            if pid is not None:
                ids.add(pid)
            nm = getattr(p, "name", None)
            if nm:
                names.add(nm)
    except Exception:
        pass
    return ids, names


def _aggregate_from_pbp(match: Any) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
    """
    play_by_play_log からホーム／アウェイの比較用スカラーを集計する。
    不戦敗などログが実質無い場合は None。
    """
    try:
        log = list(getattr(match, "play_by_play_log", None) or [])
        home_team = getattr(match, "home_team", None)
        away_team = getattr(match, "away_team", None)
        home_id = getattr(match, "_team_key")(home_team) if callable(getattr(match, "_team_key", None)) else None
        away_id = getattr(match, "_team_key")(away_team) if callable(getattr(match, "_team_key", None)) else None
    except Exception:
        return None

    if not log or home_team is None or away_team is None or home_id is None or away_id is None:
        return None

    if any(str(e.get("event_type") or "") == "forfeit" for e in log):
        return None

    home_sid, home_nms = _starter_id_name_sets(getattr(match, "home_starters", None))
    away_sid, away_nms = _starter_id_name_sets(getattr(match, "away_starters", None))

    home_stats: Dict[str, float] = {
        "made_3": 0.0,
        "made_2": 0.0,
        "made_ft": 0.0,
        "ast": 0.0,
        "oreb": 0.0,
        "dreb": 0.0,
        "stl": 0.0,
        "blk": 0.0,
        "bench_pts": 0.0,
    }
    away_stats = {k: 0.0 for k in home_stats}

    for ev in log:
        try:
            et = str(ev.get("event_type") or "")
            oid = ev.get("offense_team_id")
            did = ev.get("defense_team_id")
            oh = _side_key(oid, home_id, away_id)
            dh = _side_key(did, home_id, away_id)
            meta = ev.get("meta") if isinstance(ev.get("meta"), dict) else {}
            dkey = str(ev.get("description_key") or "")
            pid = ev.get("primary_player_id")
            pname = ev.get("primary_player_name")
            assisted = bool(meta.get("assisted")) or dkey.endswith("_assisted")

            if et == "made_3" and oh:
                bucket = home_stats if oh == "home" else away_stats
                bucket["made_3"] += 1.0
                if assisted and ev.get("secondary_player_name"):
                    bucket["ast"] += 1.0
                sid, snames = (home_sid, home_nms) if oh == "home" else (away_sid, away_nms)
                is_starter = (pid is not None and pid in sid) or (pname in snames)
                if pname and not is_starter:
                    bucket["bench_pts"] += 3.0

            elif et == "made_2" and oh:
                bucket = home_stats if oh == "home" else away_stats
                bucket["made_2"] += 1.0
                if assisted and ev.get("secondary_player_name"):
                    bucket["ast"] += 1.0
                sid, snames = (home_sid, home_nms) if oh == "home" else (away_sid, away_nms)
                is_starter = (pid is not None and pid in sid) or (pname in snames)
                if pname and not is_starter:
                    bucket["bench_pts"] += 2.0

            elif et == "made_ft" and oh:
                bucket = home_stats if oh == "home" else away_stats
                bucket["made_ft"] += 1.0
                if assisted and ev.get("secondary_player_name"):
                    bucket["ast"] += 1.0
                sid, snames = (home_sid, home_nms) if oh == "home" else (away_sid, away_nms)
                is_starter = (pid is not None and pid in sid) or (pname in snames)
                if pname and not is_starter:
                    bucket["bench_pts"] += 1.0

            elif et == "off_rebound" and oh:
                (home_stats if oh == "home" else away_stats)["oreb"] += 1.0

            elif et == "def_rebound" and dh:
                (home_stats if dh == "home" else away_stats)["dreb"] += 1.0

            elif et == "steal" and dh:
                (home_stats if dh == "home" else away_stats)["stl"] += 1.0

            elif et == "block" and dh:
                (home_stats if dh == "home" else away_stats)["blk"] += 1.0

        except Exception:
            continue

    # ログが極端に薄い場合はフォールバックへ
    activity = sum(home_stats.values()) + sum(away_stats.values())
    if activity < 8.0:
        return None

    return home_stats, away_stats


def _compare_axis(u: float, o: float, thresh: float) -> str:
    d = u - o
    if d > thresh:
        return "上回った"
    if d < -thresh:
        return "下回った"
    return "五分"


def _outside_score(row: Dict[str, float]) -> float:
    return row["made_3"] * 3.0


def _inside_score(row: Dict[str, float]) -> float:
    return row["made_2"] * 2.0 + row["oreb"] + row["dreb"]


def _defense_score(row: Dict[str, float]) -> float:
    return row["dreb"] + row["stl"] + row["blk"]


def build_postgame_edges_summary(match: Any, user_team: Any) -> Optional[Dict[str, Any]]:
    """
    自チーム視点で各軸の「上回った／五分／下回った」と生差分を返す。
    PBP から集計できない場合は布陣比較の近似（match_preview と同系）にフォールバック。
    """
    try:
        home_team = getattr(match, "home_team", None)
        away_team = getattr(match, "away_team", None)
        if user_team is None or home_team is None or away_team is None:
            return None
        is_user_home = user_team is home_team
        opp = away_team if is_user_home else home_team
    except Exception:
        return None

    agg = _aggregate_from_pbp(match)
    if agg is not None:
        home_row, away_row = agg
        urow = home_row if is_user_home else away_row
        orow = away_row if is_user_home else home_row

        out: Dict[str, Any] = {}
        o3 = _outside_score(urow) - _outside_score(orow)
        ins = _inside_score(urow) - _inside_score(orow)
        ast = urow["ast"] - orow["ast"]
        df = _defense_score(urow) - _defense_score(orow)
        bn = urow["bench_pts"] - orow["bench_pts"]

        out["outside"] = _compare_axis(_outside_score(urow), _outside_score(orow), 4.0)
        out["inside"] = _compare_axis(_inside_score(urow), _inside_score(orow), 6.0)
        out["handler"] = _compare_axis(urow["ast"], orow["ast"], 2.0)
        out["bench"] = _compare_axis(urow["bench_pts"], orow["bench_pts"], 4.0)
        out["defense"] = _compare_axis(_defense_score(urow), _defense_score(orow), 5.0)

        out["_raw"] = {
            "outside_diff": o3,
            "inside_diff": ins,
            "ast_diff": ast,
            "def_diff": df,
            "bench_diff": bn,
        }
        out["_source"] = "pbp"
        return out

    # --- フォールバック: 試合前サマリーと同系の布陣比較を「試合後風」ラベルに写す ---
    pre = build_matchup_edges_summary(user_team, opp)
    if pre is None:
        return None
    mp = {"自チーム優位": "上回った", "相手優位": "下回った", "五分": "五分"}
    return {
        "outside": mp.get(str(pre.get("outside", "五分")), "五分"),
        "inside": mp.get(str(pre.get("inside", "五分")), "五分"),
        "handler": mp.get(str(pre.get("handler", "五分")), "五分"),
        "bench": mp.get(str(pre.get("bench", "五分")), "五分"),
        "defense": mp.get(str(pre.get("defense", "五分")), "五分"),
        "_raw": {},
        "_source": "lineup_fallback",
    }


def _safe_box_score_rows(match: Any) -> List[Dict[str, Any]]:
    try:
        fn = getattr(match, "get_player_box_score_rows", None)
        if not callable(fn):
            return []
        rows = fn()
        if not isinstance(rows, list):
            return []
        return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []


def _row_belongs_to_user_team(row: Dict[str, Any], user_team: Any) -> bool:
    if user_team is None:
        return False
    try:
        uid = getattr(user_team, "team_id", None)
        if uid is not None:
            rid = row.get("team_id", None)
            if rid is not None:
                return int(rid) == int(uid)
    except Exception:
        pass
    try:
        un = str(getattr(user_team, "name", "") or "")
        rn = str(row.get("team_name") or "")
        if un and rn and un == rn:
            return True
    except Exception:
        pass
    return False


def _row_pf_minutes_name(row: Dict[str, Any]) -> Tuple[str, int, float]:
    name = str(row.get("player_name") or "?")
    try:
        pf = int(row.get("pf", 0) or 0)
    except (TypeError, ValueError):
        pf = 0
    try:
        minutes = float(row.get("minutes", 0) or 0.0)
    except (TypeError, ValueError):
        minutes = 0.0
    return name, pf, minutes


def _format_pf_summary_lines(match: Any, user_team: Any) -> List[str]:
    """
    個人 PF の最小表示行（自チームのみ。PF>=1 の選手のみ列挙。
    全員 PF=0 なら「PF記録なし」1 行。データ不十分なら空。
    """
    if user_team is None:
        return []
    try:
        rows = _safe_box_score_rows(match)
    except Exception:
        return []
    if not rows:
        return []
    own: List[Dict[str, Any]] = []
    for r in rows:
        try:
            if _row_belongs_to_user_team(r, user_team):
                own.append(r)
        except Exception:
            continue
    if not own:
        return []
    with_pf: List[Dict[str, Any]] = []
    for r in own:
        try:
            _n, pfi, _m = _row_pf_minutes_name(r)
            if pfi >= 1:
                with_pf.append(r)
        except Exception:
            continue
    if with_pf:
        keyed: List[Tuple[int, float, Dict[str, Any]]] = []
        for r in with_pf:
            try:
                _nm, pfi, mins = _row_pf_minutes_name(r)
                keyed.append((pfi, mins, r))
            except Exception:
                continue
        keyed.sort(key=lambda t: (-t[0], -t[1]))
        out: List[str] = ["ファウル（PF）:"]
        for _pfi, _mins, r in keyed:
            try:
                nm, pfi, mins = _row_pf_minutes_name(r)
                out.append(f"- {nm} PF {pfi} / {mins:.1f}分")
            except Exception:
                continue
        return out
    return ["PF記録なし"]


def _safe_team_foul_maps(match: Any) -> Tuple[Dict[int, int], Dict[int, int]]:
    try:
        home_map = getattr(match, "home_team_fouls_by_quarter", None)
        away_map = getattr(match, "away_team_fouls_by_quarter", None)
    except Exception:
        return {}, {}
    if not isinstance(home_map, dict) or not isinstance(away_map, dict):
        return {}, {}

    def _normalize(src: Dict[Any, Any]) -> Dict[int, int]:
        out: Dict[int, int] = {}
        for k, v in src.items():
            try:
                q = int(k)
                c = int(v)
            except (TypeError, ValueError):
                continue
            if q <= 0 or c < 0:
                continue
            out[q] = c
        return out

    return _normalize(home_map), _normalize(away_map)


def _quarter_label(q: int) -> str:
    if q <= 4:
        return f"Q{q}"
    return f"OT{q - 4}"


def _format_team_foul_row(label: str, foul_map: Dict[int, int], quarters: List[int]) -> str:
    parts = [f"{_quarter_label(q)} {int(foul_map.get(q, 0) or 0)}" for q in quarters]
    return f"- {label}: " + " / ".join(parts)


def _format_team_foul_summary_lines(match: Any) -> List[str]:
    home_map, away_map = _safe_team_foul_maps(match)
    if not home_map and not away_map:
        return []

    quarters = sorted(set(home_map.keys()) | set(away_map.keys()))
    if not quarters:
        return ["チームファウル記録なし"]

    home_name = str(getattr(getattr(match, "home_team", None), "name", "") or "ホーム")
    away_name = str(getattr(getattr(match, "away_team", None), "name", "") or "アウェイ")
    out = ["チームファウル:"]
    out.append(_format_team_foul_row(home_name, home_map, quarters))
    out.append(_format_team_foul_row(away_name, away_map, quarters))
    return out


def _narrative_lines(user_won: bool, edges: Dict[str, Any]) -> Tuple[str, str, str]:
    axes = [
        ("outside", "外角"),
        ("inside", "インサイド"),
        ("handler", "ハンドラー"),
        ("bench", "ベンチ"),
        ("defense", "守備"),
    ]
    raw = edges.get("_raw") if isinstance(edges.get("_raw"), dict) else {}
    win_words = [ja for key, ja in axes if edges.get(key) == "上回った"]
    lose_words = [ja for key, ja in axes if edges.get(key) == "下回った"]

    if user_won:
        win_line = "勝因: " + ("・".join(win_words[:2]) if win_words else "接戦を押し切った")
        lose_line = "敗因: —" if not lose_words else "敗因: " + "・".join(lose_words[:2])
    else:
        lose_line = "敗因: " + ("・".join(lose_words[:2]) if lose_words else "細部で及ばず")
        win_line = "勝因: —" if not win_words else "勝因: " + "・".join(win_words[:2])

    # 分岐点: raw 差分で最も差が開いた軸
    best_k = None
    best_mag = -1e9
    raw_map = {
        "outside": float(raw.get("outside_diff", 0.0)),
        "inside": float(raw.get("inside_diff", 0.0)),
        "handler": float(raw.get("ast_diff", 0.0)),
        "bench": float(raw.get("bench_diff", 0.0)),
        "defense": float(raw.get("def_diff", 0.0)),
    }
    for key, ja in axes:
        d = raw_map.get(key, 0.0)
        mag = abs(d)
        if mag > best_mag:
            best_mag = mag
            best_k = ja

    if best_k and best_mag >= 1.0:
        if user_won:
            pivot_line = f"分岐点: {best_k}の差が結果に効きやすかった"
        else:
            pivot_line = f"分岐点: {best_k}で押し負けた展開が目立った"
    else:
        pivot_line = "分岐点: 各所の積み重ねが勝敗を分けた"

    return win_line, lose_line, pivot_line


def format_match_postgame_cli_lines(match: Any, user_team: Any) -> List[str]:
    """試合 simulate 直後想定。自チーム視点の短い振り返り。"""
    try:
        home_team = getattr(match, "home_team", None)
        away_team = getattr(match, "away_team", None)
        hs = int(getattr(match, "home_score", 0) or 0)
        aws = int(getattr(match, "away_score", 0) or 0)
        if user_team is None or home_team is None or away_team is None:
            return ["【試合後サマリー】", "情報なし", ""]
        is_user_home = user_team is home_team
        user_won = (hs > aws) if is_user_home else (aws > hs)
        opp_name = str(getattr(away_team if is_user_home else home_team, "name", "") or "相手")
        score_line = f"結果: {home_team.name} {hs} - {aws} {away_team.name}（{'勝利' if user_won else '敗北'}）"
    except Exception:
        return ["【試合後サマリー】", "情報なし", ""]

    pf_lines: List[str] = []
    try:
        pf_lines = _format_pf_summary_lines(match, user_team)
    except Exception:
        pf_lines = []
    team_foul_lines: List[str] = []
    try:
        team_foul_lines = _format_team_foul_summary_lines(match)
    except Exception:
        team_foul_lines = []

    edges = build_postgame_edges_summary(match, user_team)
    if edges is None:
        out_none: List[str] = ["【試合後サマリー】", score_line]
        if pf_lines:
            out_none.extend(pf_lines)
        if team_foul_lines:
            out_none.extend(team_foul_lines)
        out_none.extend(["情報なし（比較材料が不足しています）", ""])
        return out_none

    if edges.get("_source") == "lineup_fallback":
        hdr = f"※スタッツ参照不可のため布陣比較の近似です / vs {opp_name}"
    else:
        hdr = f"vs {opp_name}"

    line1 = (
        f"外角勝負: {edges['outside']} / インサイド勝負: {edges['inside']} / "
        f"ハンドラー勝負: {edges['handler']}"
    )
    line2 = f"守備強度: {edges['defense']} / ベンチ勝負: {edges['bench']}"
    w, l, p = _narrative_lines(user_won, edges)
    out: List[str] = ["【試合後サマリー】", score_line]
    if pf_lines:
        out.extend(pf_lines)
    if team_foul_lines:
        out.extend(team_foul_lines)
    out.extend([hdr, line1, line2, w, l, p, ""])
    return out


__all__ = ["build_postgame_edges_summary", "format_match_postgame_cli_lines"]
