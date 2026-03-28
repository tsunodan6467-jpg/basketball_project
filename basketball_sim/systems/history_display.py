"""
歴史メニュー用の読み取り専用ビュー生成（Tk 非依存）。

正本は Team / Season 側。ここは整形・重複吸収・分類のみ。
docs/HISTORY_MENU_SPEC_V1.md
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_TIMELINE_LIMIT_DEFAULT = 120


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def season_label_key(label: Any) -> str:
    """年表の重複判定・マイルストーン突合用にラベルを正規化。"""
    if label is None:
        return ""
    s = str(label).strip()
    if not s or s == "-":
        return ""
    m = re.search(r"Season\s+(\d+)", s, flags=re.IGNORECASE)
    if m:
        return f"S{m.group(1)}"
    if s.isdigit():
        return f"S{s}"
    return s.lower()


def _row_rank_score(row: Dict[str, Any]) -> int:
    r = row.get("rank", "-")
    if r is None or r == "" or r == "-":
        return 0
    try:
        int(r)
        return 2
    except (TypeError, ValueError):
        return 1


def dedupe_timeline_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    同一シーズンラベルが複数ある場合、順位など情報が豊富な行を優先。
    入力の先頭ほど新しいシーズン（get_club_history_season_rows の仕様に合わせる）。
    """
    best: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        k = season_label_key(r.get("season", ""))
        if not k:
            k = f"_row_{len(order)}"
        if k not in best:
            best[k] = r
            order.append(k)
            continue
        cur = best[k]
        if _row_rank_score(r) > _row_rank_score(cur):
            best[k] = r
    return [best[k] for k in order]


def fetch_timeline_rows(team: Any, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if team is None:
        return []
    lim = limit if limit is not None else _TIMELINE_LIMIT_DEFAULT
    getter = getattr(team, "get_club_history_season_rows", None)
    if not callable(getter):
        return []
    try:
        raw = list(getter(limit=lim) or [])
    except Exception:
        return []
    return dedupe_timeline_rows([r for r in raw if isinstance(r, dict)])


def milestone_row_kind(row: Dict[str, Any]) -> str:
    """main_menu_view の分類と同等（表示専用）。"""
    blob = " | ".join(
        [
            str(row.get("title", "")),
            str(row.get("detail", "")),
            str(row.get("category", "")),
        ]
    )
    low = blob.lower()
    if "final boss" in low or "FINAL BOSS" in blob:
        return "final_boss"
    keys = [
        "EASL",
        "ACL",
        "東アジアトップリーグ",
        "アジアクラブ選手権",
        "アジアカップ",
        "世界一決定戦",
        "intercontinental",
        "インターコンチネンタル",
    ]
    if any(k.lower() in low for k in keys):
        return "international"
    return "domestic"


def split_milestone_rows(milestone_rows: List[Dict[str, Any]]) -> Tuple[List[dict], List[dict], List[dict]]:
    international: List[dict] = []
    boss: List[dict] = []
    domestic: List[dict] = []
    for r in milestone_rows:
        if not isinstance(r, dict):
            continue
        k = milestone_row_kind(r)
        if k == "final_boss":
            boss.append(r)
        elif k == "international":
            international.append(r)
        else:
            domestic.append(r)
    return international, boss, domestic


def parse_season_index_from_label(label: Any) -> Optional[int]:
    if label is None:
        return None
    s = str(label).strip()
    m = re.search(r"Season\s+(\d+)", s, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return None


def timeline_selection_detail_lines(
    *,
    season_display: str,
    milestone_rows: List[Dict[str, Any]],
    award_rows: List[Dict[str, Any]],
    raw_history_seasons: List[Any],
) -> List[str]:
    """年表行選択時の詳細（マイルストーン・表彰・主力抜粋）。"""
    lines: List[str] = []
    sk = season_label_key(season_display)
    lines.append(f"シーズン: {season_display}")
    lines.append("")

    idx = parse_season_index_from_label(season_display)

    mhits: List[str] = []
    for r in milestone_rows:
        if not isinstance(r, dict):
            continue
        if season_label_key(r.get("season", "")) == sk:
            t = str(r.get("title", "") or "-")
            d = str(r.get("detail", "") or "").strip()
            if d:
                mhits.append(f"・{t} — {d}")
            else:
                mhits.append(f"・{t}")
    lines.append("【このシーズンのマイルストーン抜粋】")
    if mhits:
        lines.extend(mhits[:12])
        if len(mhits) > 12:
            lines.append(f"… 他 {len(mhits) - 12} 件")
    else:
        lines.append("（該当なし）")
    lines.append("")

    ahits: List[str] = []
    for r in award_rows:
        if not isinstance(r, dict):
            continue
        if season_label_key(r.get("season", "")) == sk:
            aw = str(r.get("award", r.get("award_type", "-")))
            pl = str(r.get("player", r.get("player_name", "-")))
            ahits.append(f"・{aw} | {pl}")
    lines.append("【このシーズンのクラブ表彰】")
    if ahits:
        lines.extend(ahits)
    else:
        lines.append("（該当なし）")
    lines.append("")
    lines.append(
        "※ 古いセーブでは表彰行にシーズンが無く、この欄が空になる場合があります。"
    )
    lines.append("")

    lines.append("【記録に残る主力（シーズン終了時スナップショット）】")
    top_found = False
    if idx is not None:
        for item in raw_history_seasons:
            if not isinstance(item, dict):
                continue
            si = item.get("season_index", item.get("season"))
            try:
                si_int = int(si) if si is not None else None
            except (TypeError, ValueError):
                si_int = None
            if si_int != idx:
                continue
            tops = item.get("top_players") or []
            if isinstance(tops, list) and tops:
                top_found = True
                for p in tops[:8]:
                    if not isinstance(p, dict):
                        continue
                    nm = str(p.get("player_name", p.get("name", "-")))
                    ov = p.get("ovr", "-")
                    sp = p.get("season_points", 0)
                    lines.append(f"・{nm}  OVR{ov}  得点{sp}")
            break
    if not top_found:
        lines.append("（データなし — 当該シーズンに top_players 記録が無い場合があります）")

    return lines


def build_journey_lines(team: Any) -> List[str]:
    """チームの歩みタブ: サマリ＋クラブ格＋最近の流れ。"""
    if team is None:
        return ["チームが未接続です。"]

    summary: Dict[str, Any] = {}
    getter = getattr(team, "get_club_history_summary", None)
    if callable(getter):
        try:
            summary = getter() or {}
        except Exception:
            summary = {}

    lines: List[str] = []

    league_label = "-"
    try:
        fmt_getter = getattr(team, "_format_league_label_for_history", None)
        if callable(fmt_getter):
            league_label = str(fmt_getter(summary.get("current_league_level", getattr(team, "league_level", 0))))
        else:
            lv = summary.get("current_league_level", getattr(team, "league_level", "-"))
            league_label = f"D{lv}" if lv not in (None, "", "-") else "-"
    except Exception:
        league_label = "-"

    if isinstance(summary, dict) and summary:
        season_count = _safe_int(summary.get("season_count", 0))
        total_titles = _safe_int(summary.get("total_titles", summary.get("title_count", 0)))
        league_titles = _safe_int(summary.get("league_titles", 0))
        cup_titles = _safe_int(summary.get("cup_titles", 0))
        international_titles = _safe_int(summary.get("international_titles", 0))
        promotions = _safe_int(summary.get("promotions", 0))
        relegations = _safe_int(summary.get("relegations", 0))
        legend_count = _safe_int(summary.get("legend_count", 0))
        award_count = _safe_int(summary.get("award_count", 0))

        lines.append(f"現在所属: {league_label}")
        lines.append(f"通算シーズン数: {season_count}")
        ident = "-"
        ig = getattr(team, "_build_club_identity_line", None)
        if callable(ig):
            try:
                ident = str(ig(summary))
            except Exception:
                pass
        lines.append(ident)
        lines.append("")
        lines.append(
            f"主要実績: タイトル{total_titles}回 "
            f"(リーグ{league_titles} / カップ{cup_titles} / 国際{international_titles})"
        )
        lines.append(
            f"昇格{promotions}回 / 降格{relegations}回 / "
            f"レジェンド{legend_count}人 / クラブ表彰{award_count}件"
        )
    else:
        sc = 0
        try:
            sc = len(list(getattr(team, "history_seasons", []) or []))
        except Exception:
            sc = 0
        lines.append(f"現在所属: {league_label}")
        lines.append(f"通算シーズン数: {sc}")
        lines.append("クラブ概要データはまだありません")

    lines.append("")
    lines.append("【最近の流れ】")
    season_rows: List[dict] = []
    sg = getattr(team, "get_club_history_season_rows", None)
    if callable(sg):
        try:
            season_rows = list(sg(limit=10) or [])
        except Exception:
            season_rows = []
    trend = "まだ十分なシーズン履歴がありません。"
    tg = getattr(team, "_build_recent_trend_line", None)
    if season_rows and callable(tg):
        try:
            trend = str(tg(season_rows) or trend)
        except Exception:
            pass
    lines.append(trend)
    return lines


def legend_view_options() -> List[Tuple[str, str]]:
    """(コンボ表示, internal_key)"""
    return [
        ("クラブレジェンド", "club_legends"),
        ("通算得点", "all_time_points"),
        ("通算出場試合", "all_time_games"),
        ("シーズン得点（記録上位）", "single_season_points"),
        ("シーズンアシスト（記録上位）", "single_season_assists"),
    ]


def fetch_legend_table_rows(team: Any, view_key: str, *, top_n: int = 25) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if team is None:
        return rows

    if view_key == "club_legends":
        getter = getattr(team, "get_club_history_legend_rows", None)
        if not callable(getter):
            return rows
        try:
            raw = list(getter(limit=top_n) or [])
        except Exception:
            return rows
        for i, r in enumerate(raw, start=1):
            if not isinstance(r, dict):
                continue
            rows.append(
                {
                    "rk": i,
                    "name": r.get("name", r.get("player_name", "-")),
                    "c1": r.get("career_points", "-"),
                    "c2": r.get("impact", r.get("legacy_score", "-")),
                    "c3": (str(r.get("detail", r.get("reason", "")) or ""))[:40],
                }
            )
        return rows

    if view_key == "all_time_points":
        fn = getattr(team, "get_all_time_scorers", None)
        if not callable(fn):
            return rows
        try:
            raw = list(fn(top_n=top_n) or [])
        except Exception:
            return rows
        for i, r in enumerate(raw, start=1):
            if not isinstance(r, dict):
                continue
            rows.append(
                {
                    "rk": i,
                    "name": r.get("player_name", "-"),
                    "c1": r.get("career_points", "-"),
                    "c2": r.get("career_games_played", "-"),
                    "c3": r.get("peak_ovr", "-"),
                }
            )
        return rows

    if view_key == "all_time_games":
        fn = getattr(team, "get_all_time_games", None)
        if not callable(fn):
            return rows
        try:
            raw = list(fn(top_n=top_n) or [])
        except Exception:
            return rows
        for i, r in enumerate(raw, start=1):
            if not isinstance(r, dict):
                continue
            rows.append(
                {
                    "rk": i,
                    "name": r.get("player_name", "-"),
                    "c1": r.get("career_games_played", "-"),
                    "c2": r.get("career_points", "-"),
                    "c3": r.get("peak_ovr", "-"),
                }
            )
        return rows

    if view_key == "single_season_points":
        fn = getattr(team, "get_single_season_points_records", None)
        if not callable(fn):
            return rows
        try:
            raw = list(fn(top_n=top_n) or [])
        except Exception:
            return rows
        for i, r in enumerate(raw, start=1):
            if not isinstance(r, dict):
                continue
            si = r.get("season_index", "-")
            rows.append(
                {
                    "rk": i,
                    "name": r.get("player_name", "-"),
                    "c1": f"S{si}",
                    "c2": r.get("season_points", "-"),
                    "c3": r.get("season_assists", "-"),
                }
            )
        return rows

    if view_key == "single_season_assists":
        fn = getattr(team, "get_single_season_assist_records", None)
        if not callable(fn):
            return rows
        try:
            raw = list(fn(top_n=top_n) or [])
        except Exception:
            return rows
        for i, r in enumerate(raw, start=1):
            if not isinstance(r, dict):
                continue
            si = r.get("season_index", "-")
            rows.append(
                {
                    "rk": i,
                    "name": r.get("player_name", "-"),
                    "c1": f"S{si}",
                    "c2": r.get("season_assists", "-"),
                    "c3": r.get("season_points", "-"),
                }
            )
        return rows

    return rows


def build_episode_lines(team: Any, *, milestone_limit: int = 80) -> List[str]:
    """エピソード = マイルストーン分類＋既存ヘッドライン生成に委譲。"""
    lines: List[str] = []
    if team is None:
        return ["チームが未接続です。"]

    mg = getattr(team, "get_club_history_milestone_rows", None)
    milestone_rows: List[dict] = []
    if callable(mg):
        try:
            milestone_rows = [r for r in (mg(limit=milestone_limit) or []) if isinstance(r, dict)]
        except Exception:
            milestone_rows = []

    intl, boss, dom = split_milestone_rows(milestone_rows)
    hg = getattr(team, "_build_milestone_headlines", None)

    def _block(title: str, subrows: List[dict], lim: int) -> None:
        lines.append(title)
        if callable(hg):
            try:
                hs = list(hg(subrows, limit=lim) or [])
            except Exception:
                hs = []
        else:
            hs = []
        if hs:
            for h in hs:
                lines.append(f"- {h}")
        else:
            lines.append("- （該当なし）")
        lines.append("")

    _block("【マイルストーン（国際）】", intl, 8)
    _block("【マイルストーン（FINAL BOSS）】", boss, 6)
    _block("【マイルストーン（国内・昇降格・カップ等）】", dom, 10)

    lines.append("【近年の象徴的トピック（自動抜粋）】")
    rg = getattr(team, "_build_recent_big_milestone_lines", None)
    sc = 0
    try:
        summ = team.get_club_history_summary() or {}
        sc = _safe_int(summ.get("season_count", 0))
    except Exception:
        sc = 0
    if callable(rg) and sc >= 2:
        try:
            big = list(rg(milestone_rows, limit=5) or [])
        except Exception:
            big = []
        if big:
            lines.extend(big)
        else:
            lines.append("- （該当なし）")
    else:
        lines.append("- （シーズン数が少ない、またはデータなし）")

    lines.append("")
    lines.append("※ 物語的なラベルは保存されず、マイルストーン記録からの表示専用抜粋です。")
    return lines


def build_culture_lines(team: Any) -> List[str]:
    """経営・文化: 財務履歴＋施設現在値＋オーナーミッション履歴。"""
    from basketball_sim.systems.finance_report_display import format_finance_report_detail_lines

    lines: List[str] = []
    if team is None:
        return ["チームが未接続です。"]

    lines.append("=== 財務・収支（記録ベース） ===")
    lines.append("")
    try:
        lines.extend(format_finance_report_detail_lines(team, history_limit=10))
    except Exception:
        lines.append("財務履歴の表示に失敗しました。")

    lines.append("")
    lines.append("=== 施設・フロント（現在レベル） ===")
    lines.append("")
    try:
        lines.append(
            f"アリーナ Lv{int(getattr(team, 'arena_level', 1))}  "
            f"/ 育成 Lv{int(getattr(team, 'training_facility_level', 1))}  "
            f"/ メディカル Lv{int(getattr(team, 'medical_facility_level', 1))}  "
            f"/ フロント Lv{int(getattr(team, 'front_office_level', 1))}"
        )
    except Exception:
        lines.append("施設情報を取得できませんでした。")

    lines.append("")
    lines.append("=== スポンサー履歴（要約） ===")
    lines.append("")
    try:
        from basketball_sim.systems.sponsor_management import format_sponsor_history_lines

        sl = format_sponsor_history_lines(team)
        lines.extend(sl if sl else ["（履歴なし）"])
    except Exception:
        lines.append("（表示できませんでした）")

    lines.append("")
    lines.append("=== 広報（PR）履歴（要約） ===")
    lines.append("")
    try:
        from basketball_sim.systems.pr_campaign_management import format_pr_history_lines

        pl = format_pr_history_lines(team)
        lines.extend(pl if pl else ["（履歴なし）"])
    except Exception:
        lines.append("（表示できませんでした）")

    lines.append("")
    lines.append("=== 物販履歴（要約） ===")
    lines.append("")
    try:
        from basketball_sim.systems.merchandise_management import format_merchandise_history_lines

        ml = format_merchandise_history_lines(team, limit=8)
        lines.extend(ml if ml else ["（履歴なし）"])
    except Exception:
        lines.append("（表示できませんでした）")

    lines.append("")
    lines.append("=== オーナーミッション（シーズン締め履歴・新しい順） ===")
    lines.append("")
    hist = list(getattr(team, "owner_mission_history", None) or [])
    if not hist:
        lines.append("（まだ履歴がありません）")
        lines.append("")
        lines.append(
            "※ スポンサー・PR・物販の詳細は各 GM メニューでも確認できます。"
        )
        return lines

    for payload in reversed(hist[-12:]):
        if not isinstance(payload, dict):
            continue
        sl = str(payload.get("season_label", "-"))
        trust = payload.get("owner_trust_after", "-")
        delta = payload.get("trust_delta_total", "-")
        lines.append(f"--- {sl}  信頼度(後): {trust}  合計変動: {delta} ---")
        for res in payload.get("results") or []:
            if not isinstance(res, dict):
                continue
            st = res.get("status", "-")
            tl = res.get("title", "-")
            pt = res.get("progress_text", "")
            lines.append(f"  [{st}] {tl}  {pt}")
        lines.append("")

    lines.append("※ スポンサー・PR・物販の詳細は各 GM メニュー側の履歴表示が正本に近い場合があります。")
    return lines
