"""
日程メニュー用の読み取り専用ビュー生成（Season を壊さない）。

正本: docs/SCHEDULE_MENU_SPEC_V1.md
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from basketball_sim.systems.competition_display import (
    competition_category,
    competition_display_name,
    competition_display_name_from_event,
)


def _team_matches_side(user_team: Any, side: Any) -> bool:
    if user_team is None or side is None:
        return False
    if user_team is side:
        return True
    uid = getattr(user_team, "team_id", None)
    oid = getattr(side, "team_id", None)
    if uid is not None and oid is not None and int(uid) == int(oid):
        return True
    return False


def home_away_for_user(user_team: Any, home_team: Any, away_team: Any) -> Tuple[str, str]:
    """(一覧用短縮, 詳細用長文)。"""
    if _team_matches_side(user_team, home_team):
        return "H", "ホーム"
    if _team_matches_side(user_team, away_team):
        return "A", "アウェイ"
    return "—", "—"


def opponent_name_for_user(user_team: Any, home_team: Any, away_team: Any) -> str:
    if _team_matches_side(user_team, home_team):
        return str(getattr(away_team, "name", "-") or "-")
    if _team_matches_side(user_team, away_team):
        return str(getattr(home_team, "name", "-") or "-")
    return "-"


def round_month_label(season: Any, round_number: int) -> str:
    getter = getattr(season, "_get_round_config", None)
    if callable(getter):
        try:
            cfg = getter(int(round_number)) or {}
        except Exception:
            cfg = {}
    else:
        cfg = {}
    m = cfg.get("month")
    try:
        if m is not None:
            return f"{int(m)}月頃"
    except (TypeError, ValueError):
        pass
    return "—"


def last_regular_league_round(season: Any) -> int:
    """ROUND_CONFIG 上、リーグ試合数が1以上の最終ラウンド番号（表示・補助用）。"""
    if season is None:
        return 0
    tr = int(getattr(season, "total_rounds", 0) or 0)
    getter = getattr(season, "_get_round_config", None)
    if not callable(getter) or tr <= 0:
        return 0
    best = 0
    for r in range(1, tr + 1):
        try:
            cfg = getter(r) or {}
        except Exception:
            continue
        if int(cfg.get("league_games_per_team", 0) or 0) > 0:
            best = r
    return best


def round_calendar_month_and_week(season: Any, round_number: int) -> Tuple[Optional[int], int]:
    """
    主画面帯など用：config の month と、同一月内の累積ラウンド順から週目 1〜4（ゲーム用・循環）。
    """
    getter = getattr(season, "_get_round_config", None)
    if not callable(getter):
        return None, 1
    try:
        cfg = getter(int(round_number)) or {}
    except Exception:
        return None, 1
    m = cfg.get("month")
    try:
        mi = int(m) if m is not None else None
    except (TypeError, ValueError):
        mi = None
    if mi is None:
        return None, 1
    same = 0
    for r in range(1, int(round_number) + 1):
        try:
            c2 = getter(r) or {}
        except Exception:
            continue
        m2 = c2.get("month")
        try:
            if m2 is not None and int(m2) == mi:
                same += 1
        except (TypeError, ValueError):
            continue
    week = ((same - 1) % 4) + 1
    return mi, week


def schedule_month_week_label(season: Any, round_number: int) -> str:
    """帯・次の試合欄などで共通利用する「○月○週目」（正本）。"""
    mo, wk = round_calendar_month_and_week(season, int(round_number))
    if mo is not None:
        return f"{mo}月{wk}週目"
    return "—"


def main_top_bar_progress_label(
    season: Any,
    *,
    season_year: int,
    current_round: int,
    total_rounds: int,
    season_finished: bool,
) -> str:
    """「1年目　5月1週目　ラウンド29/33」形式（次に進むラウンド基準・終了時は最終ラウンド）。"""
    sy = max(1, int(season_year))
    tr = max(0, int(total_rounds))
    cr = max(0, int(current_round))
    if season is None or tr <= 0:
        return f"{sy}年目　—"
    if bool(season_finished):
        mo, wk = round_calendar_month_and_week(season, tr)
        cal = f"{mo}月{wk}週目" if mo is not None else "—"
        return f"{sy}年目　{cal}　シーズン終了　ラウンド{tr}/{tr}"
    nxt = cr + 1
    if nxt > tr:
        mo, wk = round_calendar_month_and_week(season, tr)
        cal = f"{mo}月{wk}週目" if mo is not None else "—"
        return f"{sy}年目　{cal}　シーズン終了　ラウンド{cr}/{tr}"
    mo, wk = round_calendar_month_and_week(season, nxt)
    cal = f"{mo}月{wk}週目" if mo is not None else "—"
    return f"{sy}年目　{cal}　ラウンド{nxt}/{tr}"


def division_playoff_pending_note_lines(season: Any) -> List[str]:
    """レギュラー消化後〜シーズン締め前の PO 補足（結果は finalize 後）。"""
    if season is None:
        return []
    if bool(getattr(season, "season_finished", False)):
        return []
    lr = last_regular_league_round(season)
    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    if lr <= 0 or cr < lr or cr >= tr:
        return []
    return [
        "（ディビジョンPO）レギュラー終了後：リーグ戦以外の週が続きます。",
        "POの優勝／準優勝はシーズン締め（最終ラウンド完了）後に下段へ反映されます。",
    ]


def user_team_division_playoff_projection_lines(season: Any, user_team: Any) -> List[str]:
    """レギュラー消化後〜締め前：自クラブのPO出場見込み（表示専用）。"""
    if season is None or user_team is None:
        return []
    if bool(getattr(season, "season_finished", False)):
        return []
    lr = last_regular_league_round(season)
    cr = int(getattr(season, "current_round", 0) or 0)
    if lr <= 0 or cr < lr:
        return []
    level = getattr(user_team, "league_level", None)
    if level is None:
        return []
    leagues = getattr(season, "leagues", None)
    if not isinstance(leagues, dict) or level not in leagues:
        return []
    teams = leagues[level]
    if not teams:
        return []
    gs = getattr(season, "get_standings", None)
    if not callable(gs):
        return []
    try:
        standings = gs(list(teams))
    except Exception:
        return []
    rank = None
    for i, t in enumerate(standings, start=1):
        if _team_obj_matches_user(t, user_team):
            rank = i
            break
    if rank is None:
        return []
    label = "PO出場対象（上位8位）" if rank <= 8 else "PO圏外（9位以下）"
    return [
        f"【D{level}】レギュラー順位 {rank}位 → {label}（POの確定結果はシーズン締め後に表示されます）。",
    ]


_EMPEROR_STAGE_ORDER_JA: Tuple[Tuple[str, str], ...] = (
    ("round1", "1回戦"),
    ("round2", "2回戦"),
    ("round3", "3回戦"),
    ("quarterfinal", "準々決勝"),
    ("semifinal", "準決勝"),
    ("final", "決勝"),
)

_EMPEROR_STAGE_INDEX = {k: i for i, (k, _) in enumerate(_EMPEROR_STAGE_ORDER_JA)}


def _emperor_cup_row_display_sim_round(stage_key: str) -> int:
    """
    杯結果の表示用シムラウンド番号（Season.emperor_cup_schedule 正本に合わせる）。
    ラウンド13: round1〜3、ラウンド14: 準々決〜決勝。
    """
    sk = str(stage_key or "")
    if sk in ("round1", "round2", "round3"):
        return 13
    if sk in ("quarterfinal", "semifinal", "final"):
        return 14
    return 13


def _emperor_cup_row_merge_sort_key(row: Dict[str, Any]) -> float:
    """
    過去結果の統合ソート用キー。game_results 由来の疑似ラウンド（0〜33）と同じスケールに載せ、
    杯がシーズン末尾や PO 付近へ吸い寄せられないようにする。
    同一シム週内はステージ自然順（1回戦→決勝）：降順ソートで先頭側に若い段が来るよう (max_idx - stage_i) を付与。
    """
    sk = str(row.get("stage_key") or "round1")
    stage_i = float(_EMPEROR_STAGE_INDEX.get(sk, 0))
    sim_r = float(_emperor_cup_row_display_sim_round(sk))
    mx_in_bucket = 2.0 if sim_r == 13.0 else 5.0
    return sim_r + (mx_in_bucket - stage_i) * 0.001


_CUP_DEF_SCORE_RE = re.compile(
    r"^(.+?)\s+def\.\s+(.+?)\s+\((\d+)-(\d+)\)\s*$"
)


def _sim_round_for_emperor_stage(season: Any, stage_key: str) -> Optional[int]:
    """杯ステージが消化されたシムラウンド番号（表示用の時系列キー）。"""
    getter = getattr(season, "_get_emperor_cup_stage_names", None)
    if not callable(getter):
        return None
    tr = int(getattr(season, "total_rounds", 0) or 0)
    for r in range(1, max(tr, 0) + 1):
        try:
            names = list(getter(r) or [])
        except Exception:
            continue
        if stage_key in names:
            return r
    return None


def _emperor_cup_line_sort_key(
    season: Any, stage_key: str, line_index_in_stage: int
) -> float:
    """
    杯行の時系列キー（降順ソート用・大きいほど一覧の上）。
    T*(r/tr) はシム週ごとに変わるため、週2の準々決勝が週1の1回戦より上に来ることがある。
    ステージ係数を (T/tr+1) 倍にし、ラウンド1つ分の差より常にステージ順を優先する。
    """
    raw = list(getattr(season, "game_results", None) or [])
    T = max(len(raw) - 1, 0)
    tr = max(int(getattr(season, "total_rounds", 0) or 0), 1)
    r = _sim_round_for_emperor_stage(season, stage_key)
    if r is None:
        r = max(tr // 2, 1)
    stage_idx = float(_EMPEROR_STAGE_INDEX.get(stage_key, 0))
    max_s = float(len(_EMPEROR_STAGE_ORDER_JA) - 1)
    w = float(T) / float(tr) + 1.0
    stage_boost = (max_s - stage_idx) * w
    return T * (r / tr) + stage_boost + float(line_index_in_stage) * 0.0001


def _po_past_sort_key_block(season: Any, *, kind: str, level: int = 0) -> float:
    """
    PO 過去行の並びキー（降順ソート用）。
    リーグ・杯より小さくし、一覧の末尾（古い側のブロック）に寄せる。
    同一ブロック内は D1→D2→D3→自クラブの順（自クラブが最下段）。
    """
    if kind == "user":
        return -904.0
    lv = min(max(level, 1), 3)
    return -900.0 - float(lv)


def _parse_emperor_cup_log_line_for_display(
    raw_line: str, user_name: str
) -> Tuple[str, str, str, str]:
    """
    杯ログ1行をテーブル列用に分割。(対戦相手, スコア, 結果欄, H/A)
    """
    s = str(raw_line).strip()
    un = str(user_name).strip()
    if s.startswith("BYE:"):
        return "（シード）", "—", "BYE", "—"
    m = _CUP_DEF_SCORE_RE.match(s)
    if not m or not un:
        return (s[:40] + ("…" if len(s) > 40 else ""), "—", "杯", "—")
    wn = str(m.group(1)).strip()
    ln = str(m.group(2)).strip()
    try:
        ws = int(m.group(3))
        ls = int(m.group(4))
    except (TypeError, ValueError):
        return (s[:40] + ("…" if len(s) > 40 else ""), "—", "杯", "—")
    if un == wn:
        return ln, f"{ws} - {ls}", "勝利", "—"
    if un == ln:
        return wn, f"{ws} - {ls}", "敗戦", "—"
    return (s[:40] + ("…" if len(s) > 40 else ""), "—", "杯", "—")


def _emperor_cup_past_line_is_user_relevant(raw_line: str, user_name: str) -> bool:
    """
    過去結果用：杯ログ1行が自クラブの試合／BYE に該当するか（緩い部分一致は使わない）。
    - def. 行: 勝者・敗者名と完全一致
    - BYE 行: BYE リストのチーム名いずれかと完全一致
    """
    s = str(raw_line).strip()
    un = str(user_name).strip()
    if not s or not un:
        return False
    if s.startswith("BYE:"):
        body = s[4:].strip()
        for part in body.split(","):
            if part.strip() == un:
                return True
        return False
    m = _CUP_DEF_SCORE_RE.match(s)
    if m:
        wn = str(m.group(1)).strip()
        ln = str(m.group(2)).strip()
        return un == wn or un == ln
    return False


def _emperor_cup_log_line_for_user(line: str, user_team: Any) -> bool:
    """杯ログ1行が自クラブに関係するか（名前部分一致・BYE行含む）。"""
    uname = str(getattr(user_team, "name", "") or "").strip()
    if not uname:
        return False
    s = str(line).strip()
    if not s:
        return False
    if uname in s:
        return True
    return False


def emperor_cup_log_digest_lines(
    season: Any, *, limit: int = 12, user_team: Any = None
) -> List[str]:
    """情報画面向け：杯ステージログの短いダイジェスト（user_team 指定時は自クラブ関連のみ）。"""
    logs = getattr(season, "emperor_cup_stage_logs", None) or {}
    if not isinstance(logs, dict) or not logs:
        return []
    out: List[str] = []
    for key, jlabel in _EMPEROR_STAGE_ORDER_JA:
        for ln in logs.get(key, []) or []:
            s = str(ln).strip()
            if not s:
                continue
            if user_team is not None and not _emperor_cup_log_line_for_user(s, user_team):
                continue
            out.append(f"全日本カップ（{jlabel}） {s}")
            if len(out) >= limit:
                return out
    return out


def build_emperor_cup_main_next_lines(
    season: Any, user_team: Any, *, season_year: int
) -> Optional[List[str]]:
    """
    メイン「次の試合情報」用：次ラウンドが全日本カップ週のときの補完（5行＋呼び出し側で6行目に進行ヒント）。
    """
    if season is None or user_team is None:
        return None
    if bool(getattr(season, "season_finished", False)):
        return None
    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return None
    cup_fn = getattr(season, "_should_play_emperor_cup_this_round", None)
    if not callable(cup_fn) or not cup_fn(nxt):
        return None
    sy = max(1, int(season_year))
    mo, wk = round_calendar_month_and_week(season, nxt)
    cal = f"{mo}月{wk}週目" if mo is not None else "—"
    cname = competition_display_name("emperor_cup")
    active = user_still_active_in_emperor_cup_field(season, user_team)
    if active:
        st = "自チームは本大会に登録済み／出場中です（対戦は同ラウンド進行で抽選）。"
    else:
        st = "自チームは全日本カップに不参加、または敗退済みです。"
    return [
        f"{sy}年目　{cal}　ラウンド{nxt}/{tr}　／　{cname}",
        "この「次へ進む」1回で、当該週の杯ラウンドがまとめて処理されます。",
        st,
        "リーグの「次の試合」とは別経路のため、一覧は左「日程」→「すべて」で確認できます。",
        "（リーグ順位・戦績比較は杯対象外です）",
    ]


def build_division_playoff_main_next_lines(
    season: Any, user_team: Any, *, season_year: int
) -> Optional[List[str]]:
    """
    メイン「次の試合情報」用：PO フェーズの表示補完（5行＋6行目は呼び出し側）。
    ・進行中: レギュラー終了後でリーグ次戦が無いとき
    ・終了後: 次の試合が無いときの PO 結果確認導線
    """
    if season is None or user_team is None:
        return None
    sy = max(1, int(season_year))
    tr = int(getattr(season, "total_rounds", 0) or 0)
    fin = bool(getattr(season, "season_finished", False))
    if fin:
        mo, wk = round_calendar_month_and_week(season, max(tr, 1))
        cal = f"{mo}月{wk}週目" if mo is not None else "—"
        lbl, detail = user_team_division_playoff_result_parts(season, user_team)
        return [
            f"{sy}年目　{cal}　シーズン終了　／　ディビジョンPO（処理済み）",
            "【フェーズ】リーグの次の試合はありません。PO はシーズン締めで一括処理されています。",
            f"【自クラブの PO】{lbl} — {detail}",
            "結果の詳細は左「日程」→「過去結果」、または「情報」の大会欄（【D1】〜【D3】）で確認できます。",
            "（ラウンド単位の PO 対戦カードは表示しません）",
        ]
    cr = int(getattr(season, "current_round", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return None
    lr = last_regular_league_round(season)
    if lr <= 0 or nxt <= lr:
        return None
    if count_user_games_in_sim_round(season, user_team, nxt) > 0:
        return None
    mo, wk = round_calendar_month_and_week(season, nxt)
    cal = f"{mo}月{wk}週目" if mo is not None else "—"
    pls = user_team_division_playoff_projection_lines(season, user_team)
    pl0 = (
        pls[0]
        if pls
        else "レギュラー終了後の特別フェーズです（リーグ対戦カードが無い週があります）。"
    )
    return [
        f"{sy}年目　{cal}　ラウンド{nxt}/{tr}　／　ディビジョンPO・シーズン締め期間",
        "【フェーズ】ディビジョンPO／締め進行中（日本リーグの次戦が無い週があります）。",
        f"【自クラブPO見込み】{pl0}",
        "確定した PO 結果は最終ラウンド完了後に反映されます。日程「過去結果」でも確認できます。",
        "（PO 本戦はシミュ内で一括処理され、試合単位のカードは表示しません）",
    ]


def emperor_cup_past_result_rows(season: Any, user_team: Any) -> List[Dict[str, Any]]:
    """日程「過去結果」：自クラブに関係する杯ログのみ（表示専用・列分割済み）。"""
    if season is None or user_team is None:
        return []
    uname = str(getattr(user_team, "name", "") or "").strip()
    if not uname:
        return []
    logs = getattr(season, "emperor_cup_stage_logs", None) or {}
    if not isinstance(logs, dict) or not logs:
        return []
    out: List[Dict[str, Any]] = []
    for key, jlabel in _EMPEROR_STAGE_ORDER_JA:
        lines_in_stage = list(logs.get(key, []) or [])
        for li, ln in enumerate(lines_in_stage):
            s = str(ln).strip()
            if not s:
                continue
            if not _emperor_cup_past_line_is_user_relevant(s, uname):
                continue
            opp, sc, res_col, ha_s = _parse_emperor_cup_log_line_for_display(s, uname)
            if s.startswith("BYE:"):
                opp = "BYE（シード）"
            sk = _emperor_cup_line_sort_key(season, key, li)
            out.append(
                {
                    "opponent": opp,
                    "score": sc,
                    "result": res_col,
                    "ha_short": ha_s,
                    "round_label": jlabel,
                    "competition_display": competition_display_name("emperor_cup"),
                    "note": s,
                    "_sort_key": sk,
                    "stage_key": key,
                }
            )
            if len(out) >= 8:
                return out
        if len(out) >= 8:
            break
    if out:
        return out
    res = getattr(season, "emperor_cup_results", None) or {}
    champ = res.get("champion")
    ru = res.get("runner_up")
    sk_final = _emperor_cup_line_sort_key(season, "final", 0)
    if _team_obj_matches_user(champ, user_team):
        return [
            {
                "opponent": "—",
                "score": "—",
                "result": "優勝",
                "ha_short": "—",
                "round_label": "決勝",
                "competition_display": competition_display_name("emperor_cup"),
                "note": "emperor_cup_results に基づく優勝記録です。",
                "_sort_key": sk_final + 0.001,
                "stage_key": "final",
            }
        ]
    if _team_obj_matches_user(ru, user_team):
        return [
            {
                "opponent": str(getattr(champ, "name", "—") or "—") if champ is not None else "—",
                "score": "—",
                "result": "準優勝",
                "ha_short": "—",
                "round_label": "決勝",
                "competition_display": competition_display_name("emperor_cup"),
                "note": "emperor_cup_results に基づく準優勝記録です。",
                "_sort_key": sk_final,
                "stage_key": "final",
            }
        ]
    if bool(getattr(season, "emperor_cup_enabled", False)) and any(
        logs.get(k) for k, _ in _EMPEROR_STAGE_ORDER_JA
    ):
        return [
            {
                "opponent": "—",
                "score": "—",
                "result": "—",
                "ha_short": "—",
                "round_label": "—",
                "competition_display": competition_display_name("emperor_cup"),
                "note": "自チームに関する杯ログを表示できませんでした（不参加・敗退等）。",
                "_sort_key": _emperor_cup_line_sort_key(season, "round1", 0),
                "stage_key": "round1",
            }
        ]
    return []


def user_team_division_playoff_result_parts(season: Any, user_team: Any) -> Tuple[str, str]:
    """(結果欄の短い区分, 説明文1行)。シーズン終了後の division_playoff_results 参照。"""
    if season is None or user_team is None:
        return ("", "")
    results = getattr(season, "division_playoff_results", None) or {}
    for level in [1, 2, 3]:
        div = results.get(level, {}) if isinstance(results, dict) else {}
        champ = div.get("champion")
        runner_up = div.get("runner_up")
        teams = list(div.get("playoff_teams", []) or [])
        if champ is not None and _team_obj_matches_user(champ, user_team):
            return (
                "優勝",
                f"あなたのクラブはD{level}ディビジョンPOで優勝しました。",
            )
        if runner_up is not None and _team_obj_matches_user(runner_up, user_team):
            return (
                "準優勝",
                f"あなたのクラブはD{level}ディビジョンPOで準優勝しました。",
            )
        if any(_team_obj_matches_user(t, user_team) for t in teams):
            return (
                "出場のみ",
                f"あなたのクラブはD{level}ディビジョンPOに出場しました（優勝・準優勝には届かず敗退）。",
            )
    return ("—", "あなたのクラブのディビジョンPO出場はありません。")


def division_playoff_past_result_rows(season: Any, user_team: Any) -> List[Dict[str, Any]]:
    """日程「過去結果」：シーズン終了後のディビジョンPO結果（表示専用）。"""
    if season is None or user_team is None:
        return []
    if not bool(getattr(season, "season_finished", False)):
        return []
    rows: List[Dict[str, Any]] = []
    results = getattr(season, "division_playoff_results", None) or {}
    for level in [1, 2, 3]:
        div = results.get(level, {}) if isinstance(results, dict) else {}
        champion = _team_name_safe(div.get("champion"))
        runner_up = _team_name_safe(div.get("runner_up"))
        rows.append(
            {
                "opponent": champion,
                "score": f"vs {runner_up}" if runner_up != "—" else "—",
                "result": "PO",
                "ha_short": "—",
                "round_label": f"D{level}",
                "competition_display": competition_display_name("playoff"),
                "note": f"D{level}ディビジョンPOの決勝までの結果です（優勝／準優勝）。",
                "_sort_key": _po_past_sort_key_block(season, kind="div", level=level),
            }
        )
    lbl, desc = user_team_division_playoff_result_parts(season, user_team)
    rows.append(
        {
            "opponent": f"【自クラブ】{lbl}",
            "score": "—",
            "result": lbl,
            "ha_short": "—",
            "round_label": "自チーム",
            "competition_display": competition_display_name("playoff"),
            "note": desc,
            "_sort_key": _po_past_sort_key_block(season, kind="user"),
        }
    )
    return rows


def past_league_and_emperor_result_rows(season: Any, user_team: Any) -> List[Dict[str, Any]]:
    """
    過去結果一覧：統合降順ソート。
    - リーグ: game_results 上の時系列を全ラウンド数で正規化した疑似ラウンド（0〜33台）。
    - 全日本カップ: シムラウンド13・14相当のキー（週13=1〜3回戦、週14=準々〜決勝）でリーグ列に混ぜる。
      杯だけ末尾ブロックにすると終盤リーグ・PO付近に見えるため、ここで位置を固定する。
    - PO: 既存の _sort_key（負の値）を維持し一覧末尾に留まる。
    杯の同一週内は 1回戦→決勝の自然順（stage_key 順）。
    """
    raw = list(getattr(season, "game_results", None) or [])
    mx = max(len(raw) - 1, 1)
    tr = max(int(getattr(season, "total_rounds", 0) or 0), 1)

    base = past_league_result_rows(season, user_team)
    po = division_playoff_past_result_rows(season, user_team)
    cup = emperor_cup_past_result_rows(season, user_team)

    for row in base:
        ikey = float(row.get("_sort_key") if row.get("_sort_key") is not None else row.get("index") or 0)
        row["_merge_sort_key"] = (ikey / float(mx)) * float(tr)

    for row in cup:
        row["_merge_sort_key"] = _emperor_cup_row_merge_sort_key(row)

    for row in po:
        row["_merge_sort_key"] = float(row.get("_sort_key", -900.0))

    merged = base + cup + po
    merged.sort(key=lambda r: float(r.get("_merge_sort_key", 0.0)), reverse=True)
    for row in merged:
        row.pop("_merge_sort_key", None)
        row.pop("_sort_key", None)
        row.pop("stage_key", None)
    for i, row in enumerate(merged, start=1):
        row["display_order"] = i
    return merged


def _team_key_for_schedule(team: Any) -> int:
    tid = getattr(team, "team_id", None)
    return int(tid) if tid is not None else id(team)


def _team_name_safe(team: Any) -> str:
    if team is None:
        return "—"
    return str(getattr(team, "name", "—") or "—")


def _team_obj_matches_user(team_obj: Any, user_team: Any) -> bool:
    """Season の Team 参照とユーザー選択チームの同一判定（team_id 優先・名前フォールバック）。"""
    if team_obj is None or user_team is None:
        return False
    if _team_matches_side(user_team, team_obj):
        return True
    un = str(getattr(user_team, "name", "") or "").strip()
    on = str(getattr(team_obj, "name", "") or "").strip()
    if not un or not on:
        return False
    return un == on


def division_playoff_summary_lines(season: Any) -> List[str]:
    """シーズン終了後のディビジョンPO結果（表示専用）。"""
    rows = []
    results = getattr(season, "division_playoff_results", None) or {}
    for level in [1, 2, 3]:
        div = results.get(level, {}) if isinstance(results, dict) else {}
        champion = _team_name_safe(div.get("champion"))
        runner_up = _team_name_safe(div.get("runner_up"))
        rows.append(f"D{level}: 優勝 {champion} / 準優勝 {runner_up}")
    return rows


def division_playoff_results_prominent_lines(season: Any) -> List[str]:
    """情報画面向け：D1〜D3 を見出し付きで列挙（表示専用）。"""
    if season is None:
        return []
    out: List[str] = []
    results = getattr(season, "division_playoff_results", None) or {}
    for level in [1, 2, 3]:
        div = results.get(level, {}) if isinstance(results, dict) else {}
        champion = _team_name_safe(div.get("champion"))
        runner_up = _team_name_safe(div.get("runner_up"))
        out.append(f"【D{level}】優勝: {champion} ／ 準優勝: {runner_up}")
    return out


def user_team_division_playoff_result_line(season: Any, user_team: Any) -> str:
    """自クラブのディビジョンPO結果を1行で返す（表示専用）。"""
    _, detail = user_team_division_playoff_result_parts(season, user_team)
    return detail


def user_still_active_in_emperor_cup_field(season: Any, user_team: Any) -> bool:
    """全日本カップのブラケットにまだ残っている（または未開催前で登録済み）か。"""
    if season is None or user_team is None:
        return False
    uid = _team_key_for_schedule(user_team)
    cur = getattr(season, "emperor_cup_current_teams", None) or []
    if any(_team_key_for_schedule(t) == uid for t in cur):
        return True
    played = getattr(season, "emperor_cup_played_stages", None) or set()
    if not played:
        bye = getattr(season, "emperor_cup_bye_teams", None) or []
        r1 = getattr(season, "emperor_cup_round1_teams", None) or []
        return any(_team_key_for_schedule(t) == uid for t in bye) or any(
            _team_key_for_schedule(t) == uid for t in r1
        )
    return False


def user_team_participates_in_easl_stage(season: Any, user_team: Any, stage: Optional[str]) -> bool:
    """
    表示用: 当該東アジアトップリーグ（内部キー easl）ステージで自チームが関与する見込みがあるか（SeasonEvent 非格納の補完用）。
    シミュ正本の再現ではなく、漏れ防止のためのヒューリスティック。
    """
    if season is None or user_team is None:
        return False
    st = str(stage or "").strip()
    if not st:
        return False
    if not bool(getattr(season, "easl_enabled", False)):
        return False

    matchdays = getattr(season, "easl_matchdays", None) or {}
    if st.startswith("group_md"):
        pairs = matchdays.get(st, []) or []
        for home_team, away_team in pairs:
            if _team_matches_side(user_team, home_team) or _team_matches_side(user_team, away_team):
                return True
        return False

    if st == "semifinal":
        ko = getattr(season, "easl_knockout_teams", None) or []
        if ko:
            return any(_team_matches_side(user_team, t) for t in ko)
        groups = getattr(season, "easl_groups", None) or {}
        for tlist in groups.values():
            for t in tlist:
                if _team_matches_side(user_team, t):
                    return True
        return False

    if st == "final":
        fin = getattr(season, "easl_current_finalists", None) or []
        if fin:
            return any(_team_matches_side(user_team, t) for t in fin)
        ko = getattr(season, "easl_knockout_teams", None) or []
        if ko:
            return any(_team_matches_side(user_team, t) for t in ko)
        return False

    return False


def _is_all_star_break_round(season: Any, round_number: int) -> bool:
    """ROUND_CONFIG のオールスター週（リーグ試合なしブレーク）か。表示補完用。"""
    getter = getattr(season, "_get_round_config", None)
    if not callable(getter):
        return False
    try:
        cfg = getter(int(round_number)) or {}
    except Exception:
        return False
    if int(cfg.get("league_games_per_team", 0) or 0) != 0:
        return False
    if not bool(cfg.get("is_break_week")):
        return False
    notes = str(cfg.get("notes") or "")
    return "オールスター" in notes


def _append_all_star_break_placeholder_if_needed(
    season: Any,
    user_team: Any,
    round_number: int,
    rounds_until: int,
    month_label: str,
    rows: List[Dict[str, Any]],
) -> None:
    """ラウンド15などリーグ休みのオールスター週を、日程「すべて」で欠番に見えないよう補完する。"""
    if season is None or user_team is None:
        return
    if any(int(row.get("round") or 0) == int(round_number) for row in rows):
        return
    if not _is_all_star_break_round(season, round_number):
        return
    rows.append(
        {
            "round": int(round_number),
            "rounds_until": rounds_until,
            "month_label": month_label,
            "competition_type": "all_star_break",
            "competition_display": "オールスター",
            "competition_category": competition_category("all_star_break"),
            "ha_short": "—",
            "ha_long": "（オールスター週）",
            "opponent": "（日本リーグの対戦カードはありません）",
            "event_id": f"all_star_week_r{int(round_number)}",
            "label": "",
        }
    )


def _append_national_window_placeholder_if_needed(
    season: Any,
    user_team: Any,
    round_number: int,
    rounds_until: int,
    month_label: str,
    rows: List[Dict[str, Any]],
) -> None:
    """
    代表ウィンドウ週は日本リーグの SeasonEvent が空になりやすい。
    全日本カップ / 東アジアトップリーグ と同様、日程「すべて」で見落としにくいよう表示のみ補完する。
    """
    if season is None or user_team is None:
        return
    if any(int(row.get("round") or 0) == int(round_number) for row in rows):
        return
    nat_get = getattr(season, "_get_round_national_window", None)
    if not callable(nat_get):
        return
    try:
        window_key = nat_get(int(round_number))
    except Exception:
        return
    if not window_key:
        return
    resolve = getattr(season, "_resolve_national_team_window_type", None)
    window_type: Optional[str] = None
    if callable(resolve):
        try:
            window_type = resolve(window_key)
        except Exception:
            window_type = None
    label_fn = getattr(season, "_get_national_team_window_label", None)
    label = label_fn(window_type) if callable(label_fn) else "代表ウィーク"
    rows.append(
        {
            "round": int(round_number),
            "rounds_until": rounds_until,
            "month_label": month_label,
            "competition_type": "national_team_window",
            "competition_display": label,
            "competition_category": competition_category("national_team_window"),
            "ha_short": "—",
            "ha_long": "（代表ウィンドウ）",
            "opponent": "（日本リーグの対戦カードはありません）",
            "event_id": f"national_window_r{int(round_number)}",
            "label": str(window_key),
        }
    )


def is_schedule_row_display_supplement(row: Dict[str, Any]) -> bool:
    """SeasonEvent に無い行を日程タブで補完しているか（表示専用）。"""
    eid = str(row.get("event_id") or "")
    return (
        eid.startswith("emperor_cup_week_r")
        or eid.startswith("easl_week_r")
        or eid.startswith("national_window_r")
        or eid.startswith("all_star_week_r")
    )


def count_user_games_in_sim_round(season: Any, user_team: Any, round_number: int) -> int:
    """シミュレーション1ラウンド（進行1回）に含まれる自チームの game イベント数。"""
    if season is None or user_team is None:
        return 0
    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return 0
    try:
        events = list(getter(int(round_number)) or [])
    except Exception:
        return 0
    n = 0
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        h = getattr(ev, "home_team", None)
        a = getattr(ev, "away_team", None)
        if _team_matches_side(user_team, h) or _team_matches_side(user_team, a):
            n += 1
    return n


def next_advance_display_hints(season: Any, user_team: Any) -> Tuple[str, str]:
    """
    案A（表示のみ）: 進行1回あたりの自チーム試合数とまとめ進行の説明。
    Returns:
        (advance_button_area の複数行向け, 「次の試合」パネル向け1行)
    使えないときは ("", "")。
    """
    if season is None or user_team is None:
        return "", ""
    if bool(getattr(season, "season_finished", False)):
        return "", ""
    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return "", ""
    ng = count_user_games_in_sim_round(season, user_team, nxt)
    month_lbl = round_month_label(season, nxt)
    if ng <= 0:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"自チームの対戦カード（リーグ等）はこのラウンドではありません（代表・杯などは同じ進行で処理される場合があります）。"
        )
        one = (
            f"進行予告: ラウンド{nxt}・自チームの対戦カード0件（杯等は同進行）／試合の合間の介入なし"
        )
    elif ng == 1:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"この進行に自チームの試合は合計 1 試合です。"
        )
        one = f"進行予告: ラウンド{nxt}・自チーム 1試合をまとめてシミュ／試合の合間の介入なし"
    else:
        block_a = (
            f"次の「次へ進む」1回で進むのはラウンド {nxt}/{tr}（{month_lbl}）です。"
            f"この進行に自チームの試合は合計 {ng} 試合あり、まとめてシミュされます。"
        )
        one = f"進行予告: ラウンド{nxt}・自チーム {ng}試合まとめ進行／試合の合間の介入なし"
    block_b = "同じラウンド内では、試合と試合のあいだに個別で戦術を変えることはできません（進行前の設定がそのまま使われます）。"
    return f"{block_a}\n{block_b}", one


def upcoming_rows_for_user_team(
    season: Any,
    user_team: Any,
    *,
    league_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    自チームが関係する未来の SeasonEvent 行（主にリーグ戦）。
    current_round は「消化済みラウンド数」。次に進むのは current_round + 1。
    """
    if season is None or user_team is None:
        return []
    if bool(getattr(season, "season_finished", False)):
        return []

    cr = int(getattr(season, "current_round", 0) or 0)
    total = int(getattr(season, "total_rounds", 0) or 0)
    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return []

    rows: List[Dict[str, Any]] = []
    for r in range(cr + 1, total + 1):
        try:
            events = list(getter(r) or [])
        except Exception:
            continue
        mo_u, wk_u = round_calendar_month_and_week(season, r)
        month_lbl = f"{mo_u}月{wk_u}週目" if mo_u is not None else round_month_label(season, r)
        rounds_until = max(0, r - cr)

        for ev in events:
            if str(getattr(ev, "event_type", "") or "") != "game":
                continue
            home_team = getattr(ev, "home_team", None)
            away_team = getattr(ev, "away_team", None)
            if not _team_matches_side(user_team, home_team) and not _team_matches_side(
                user_team, away_team
            ):
                continue
            ct = str(getattr(ev, "competition_type", "") or "")
            if league_only and ct != "regular_season":
                continue
            ha_s, ha_l = home_away_for_user(user_team, home_team, away_team)
            opp = opponent_name_for_user(user_team, home_team, away_team)
            rows.append(
                {
                    "round": r,
                    "rounds_until": rounds_until,
                    "month_label": month_lbl,
                    "competition_type": ct,
                    "competition_display": competition_display_name_from_event(ev),
                    "competition_category": competition_category(ct),
                    "ha_short": ha_s,
                    "ha_long": ha_l,
                    "opponent": opp,
                    "event_id": str(getattr(ev, "event_id", "") or ""),
                    "label": str(getattr(ev, "label", "") or ""),
                }
            )

        if not league_only:
            cup_checker = getattr(season, "_should_play_emperor_cup_this_round", None)
            if callable(cup_checker) and cup_checker(r):
                has_cup_row = any(
                    str(row.get("competition_type") or "") == "emperor_cup" and int(row.get("round") or 0) == r
                    for row in rows
                )
                if not has_cup_row:
                    opp_txt = "（同ラウンド進行で消化・対戦は抽選）"
                    if not user_still_active_in_emperor_cup_field(season, user_team):
                        opp_txt = "（杯週・自チームは不参加または敗退済みの可能性）"
                    rows.append(
                        {
                            "round": r,
                            "rounds_until": rounds_until,
                            "month_label": month_lbl,
                            "competition_type": "emperor_cup",
                            "competition_display": "全日本カップ",
                            "competition_category": "cup",
                            "ha_short": "—",
                            "ha_long": "（大会週）",
                            "opponent": opp_txt,
                            "event_id": f"emperor_cup_week_r{r}",
                            "label": "",
                        }
                    )

            stage_getter = getattr(season, "_get_round_easl_stage", None)
            if callable(stage_getter):
                try:
                    easl_stage = stage_getter(r)
                except Exception:
                    easl_stage = None
                if easl_stage and user_team_participates_in_easl_stage(season, user_team, easl_stage):
                    has_easl_row = any(
                        str(row.get("competition_type") or "") == "easl"
                        and int(row.get("round") or 0) == r
                        for row in rows
                    )
                    if not has_easl_row:
                        rows.append(
                            {
                                "round": r,
                                "rounds_until": rounds_until,
                                "month_label": month_lbl,
                                "competition_type": "easl",
                                "competition_display": competition_display_name("easl"),
                                "competition_category": competition_category("easl"),
                                "ha_short": "—",
                                "ha_long": "（大会週）",
                                "opponent": "（同ラウンド進行で消化・組み合わせは抽選）",
                                "event_id": f"easl_week_r{r}_{easl_stage}",
                                "label": str(easl_stage),
                            }
                        )

            _append_national_window_placeholder_if_needed(
                season, user_team, r, rounds_until, month_lbl, rows
            )
            _append_all_star_break_placeholder_if_needed(
                season, user_team, r, rounds_until, month_lbl, rows
            )
    return rows


def next_round_schedule_lines(season: Any, user_team: Any) -> List[str]:
    """次ラウンド（シミュ進行1回分）の自チーム試合サマリ。複数あれば列挙。"""
    if season is None or user_team is None:
        return ["データがありません。"]
    if bool(getattr(season, "season_finished", False)):
        lines = ["シーズンは終了しています。", "ディビジョンPO結果（レギュラー終了後に処理済み）:"]
        lines.extend(division_playoff_summary_lines(season))
        lines.append(user_team_division_playoff_result_line(season, user_team))
        lines.append("詳細は情報画面・クラブ史で確認できます。")
        return lines

    cr = int(getattr(season, "current_round", 0) or 0)
    total = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > total:
        return ["これ以上のリーグラウンドはありません。"]

    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return ["日程データを取得できませんでした。"]

    try:
        events = list(getter(nxt) or [])
    except Exception:
        return ["日程データを取得できませんでした。"]

    mine: List[str] = []
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        home_team = getattr(ev, "home_team", None)
        away_team = getattr(ev, "away_team", None)
        if not _team_matches_side(user_team, home_team) and not _team_matches_side(
            user_team, away_team
        ):
            continue
        ha_s, _ = home_away_for_user(user_team, home_team, away_team)
        opp = opponent_name_for_user(user_team, home_team, away_team)
        comp = competition_display_name_from_event(ev)
        dow = str(getattr(ev, "day_of_week", "") or "")
        dow_jp = {"Wed": "水", "Sat": "土", "Sun": "日"}.get(dow, "")
        dprefix = f"{dow_jp} " if dow_jp and str(getattr(ev, "competition_type", "") or "") == "regular_season" else ""
        mine.append(f"・{comp}  {dprefix}{ha_s}  vs {opp}")

    cup_fn = getattr(season, "_should_play_emperor_cup_this_round", None)
    if callable(cup_fn) and cup_fn(nxt):
        if user_still_active_in_emperor_cup_field(season, user_team):
            mine.append("・全日本カップ（同ラウンド進行で消化・日程タブの「すべて」にも表示）")
        else:
            mine.append(
                "・全日本カップ（同ラウンド進行で消化・自チームは不参加または敗退済みの可能性があります）"
            )

    easl_get = getattr(season, "_get_round_easl_stage", None)
    if callable(easl_get):
        try:
            easl_stage = easl_get(nxt)
        except Exception:
            easl_stage = None
        if easl_stage and user_team_participates_in_easl_stage(season, user_team, easl_stage):
            mine.append(
                f"・{competition_display_name('easl')}（同ラウンド進行で消化・日程タブの「すべて」にも表示）"
            )

    nat_get = getattr(season, "_get_round_national_window", None)
    if callable(nat_get):
        try:
            nat_key = nat_get(nxt)
        except Exception:
            nat_key = None
        if nat_key:
            resolve = getattr(season, "_resolve_national_team_window_type", None)
            wtype: Optional[str] = None
            if callable(resolve):
                try:
                    wtype = resolve(nat_key)
                except Exception:
                    wtype = None
            label_fn = getattr(season, "_get_national_team_window_label", None)
            nat_label = label_fn(wtype) if callable(label_fn) else "代表ウィーク"
            mine.append(
                f"・{nat_label}（日本リーグの対戦カードなし・日程「すべて」で表示補完）"
            )

    if _is_all_star_break_round(season, nxt):
        mine.append("・オールスター（日本リーグの対戦カードなし・日程「すべて」で表示補完）")

    lr_po = last_regular_league_round(season)
    if lr_po > 0 and nxt > lr_po:
        mine.append(
            "・ディビジョンPO／シーズン締め：リーグ戦なしの週です（POの結果は最終ラウンド完了後に情報へ反映）。"
        )
        for pl in user_team_division_playoff_projection_lines(season, user_team):
            mine.append(f"・{pl}")

    cal_h = schedule_month_week_label(season, nxt)
    header = f"次の進行（ラウンド {nxt} / 全 {total}・{cal_h}）"
    ng = count_user_games_in_sim_round(season, user_team, nxt)
    if ng <= 0:
        count_line = "この進行に含まれる自チームの対戦カード（game）: 0 試合（杯・代表などは下の行と同じ進行で処理）"
    elif ng == 1:
        count_line = "この進行に含まれる自チームの対戦カード（game）: 1 試合"
    else:
        count_line = f"この進行に含まれる自チームの対戦カード（game）: {ng} 試合（同一ラウンド内はまとめてシミュ）"
    footer = (
        "「次へ進む」1回＝このラウンドまるごと進みます。"
        "試合の合間に個別の戦術介入はありません（進行前の設定が同じラウンド内すべてに使われます）。"
    )

    if not mine:
        return [
            header,
            count_line,
            "このラウンドに自チームのリーグ対戦の行はありません（代表ウィーク・杯週の可能性があります）。",
            footer,
        ]
    return [header, count_line, *mine, footer]


def format_season_event_matchup_line(event: Any) -> str:
    """SeasonEvent 相当を情報画面・ログ用の1行に整形（大会名は本作固定マッピング）。"""
    et = str(getattr(event, "event_type", "") or "")
    if et and et != "game":
        return str(getattr(event, "label", "") or getattr(event, "title", "") or "")

    home = getattr(event, "home_team", None)
    away = getattr(event, "away_team", None)
    hn = str(getattr(home, "name", "-") or "-") if home is not None else "-"
    an = str(getattr(away, "name", "-") or "-") if away is not None else "-"
    if hn == "-" or an == "-":
        return str(getattr(event, "label", "") or "")

    comp = competition_display_name_from_event(event)
    dow = str(getattr(event, "day_of_week", "") or "")
    dow_jp = {"Wed": "水", "Sat": "土", "Sun": "日"}.get(dow, "")
    ct = str(getattr(event, "competition_type", "") or "")
    prefix = f"{dow_jp} " if dow_jp and ct == "regular_season" else ""
    return f"[{comp}] {prefix}{hn} vs {an}"


def information_panel_schedule_lines(
    season: Any, *, max_events: int = 7, user_team: Any = None
) -> List[str]:
    """情報ウィンドウ「次ラウンド予定」用。全会場の対戦を列挙（schedule_display 正本）。"""
    if season is None:
        return ["シーズン未接続", "—"]
    if bool(getattr(season, "season_finished", False)):
        lines = ["シーズンは終了しています。", "ディビジョンPO結果（レギュラー終了後に処理済み）:"]
        lines.extend(division_playoff_summary_lines(season))
        if user_team is not None:
            uline = user_team_division_playoff_result_line(season, user_team)
            if uline:
                lines.append(uline)
        return lines

    cr = int(getattr(season, "current_round", 0) or 0)
    tr = int(getattr(season, "total_rounds", 0) or 0)
    nxt = cr + 1
    if nxt > tr:
        return ["これ以上のリーグラウンドはありません。", "—"]

    getter = getattr(season, "get_events_for_round", None)
    if not callable(getter):
        return ["日程データを取得できませんでした。", "—"]
    try:
        events = list(getter(nxt) or [])
    except Exception:
        return ["日程データを取得できませんでした。", "—"]

    cal_i = schedule_month_week_label(season, nxt)
    lines = [f"次の進行で消化するラウンド: {nxt} / {tr}  （{cal_i}）"]
    added = 0
    for ev in events:
        if str(getattr(ev, "event_type", "") or "") != "game":
            continue
        line = format_season_event_matchup_line(ev)
        if line:
            lines.append(line)
            added += 1
        if added >= max_events:
            break

    cup_chk = getattr(season, "_should_play_emperor_cup_this_round", None)
    if callable(cup_chk) and cup_chk(nxt):
        lines.append(f"[{competition_display_name('emperor_cup')}] 当ラウンドで杯が進行します（リーグ game は無い場合があります）。")

    lr_i = last_regular_league_round(season)
    if lr_i > 0 and nxt > lr_i:
        lines.append("ディビジョンPO／シーズン締め期間の週の可能性があります（リーグ戦なし・結果は締め後）。")
        if user_team is not None:
            lines.extend(user_team_division_playoff_projection_lines(season, user_team))

    if _is_all_star_break_round(season, nxt):
        lines.append("[オールスター] 当ラウンドは日本リーグの試合はありません（ブレーク週）。")

    if added == 0:
        if not _is_all_star_break_round(season, nxt):
            lines.append("このラウンドに game イベントがありません（代表ウィーク等の可能性）。")
        lines.append("詳細は左メニュー「日程」から確認できます。")

    return lines


def past_league_result_rows(season: Any, user_team: Any) -> List[Dict[str, Any]]:
    """
    game_results から自チーム分のみ（第1稿は日本リーグ相当として固定表示）。
    ラウンド・H/A・延長はデータなしのため — / 不明。
    """
    if season is None or user_team is None:
        return []
    uname = str(getattr(user_team, "name", "") or "")
    if not uname:
        return []

    raw = list(getattr(season, "game_results", None) or [])
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        h = str(row.get("home_team", "") or "")
        aw = str(row.get("away_team", "") or "")
        if uname not in (h, aw):
            continue
        try:
            hs = int(row.get("home_score", 0) or 0)
            als = int(row.get("away_score", 0) or 0)
        except (TypeError, ValueError):
            continue
        if h == uname:
            ha_short, ha_long = "H", "ホーム"
            opp = aw
            won = hs > als
            is_draw = hs == als
        else:
            ha_short, ha_long = "A", "アウェイ"
            opp = h
            won = als > hs
            is_draw = hs == als

        if is_draw:
            wl = "引分"
        else:
            wl = "勝利" if won else "敗戦"
        score_line = f"{hs} - {als}"

        out.append(
            {
                "index": idx,
                "_sort_key": float(idx),
                "opponent": opp,
                "score": score_line,
                "result": wl,
                "ha_short": ha_short,
                "ha_long": ha_long,
                "competition_display": competition_display_name("regular_season"),
                "round_label": "—",
                "ot_label": "—",
                "note": (
                    "日本リーグ戦の記録のみ表示（大会種別・節は game_results に未格納のため —）。"
                    " 上が新しい試合順です。"
                ),
            }
        )
    out.reverse()
    for i, row in enumerate(out, start=1):
        row["display_order"] = i
    return out


def detail_text_for_upcoming_row(row: Dict[str, Any]) -> str:
    """一覧行 dict から詳細テキスト。"""
    lines = [
        f"ラウンド: {row.get('round', '—')}",
        f"あと {row.get('rounds_until', '—')} ラウンドで到来（シーズン進行ベース）",
        f"時期目安: {row.get('month_label', '—')}",
        f"大会: {row.get('competition_display', '—')}",
        f"H/A: {row.get('ha_long', '—')} ({row.get('ha_short', '—')})",
        f"対戦相手: {row.get('opponent', '—')}",
    ]
    lbl = row.get("label")
    if lbl:
        lines.append(f"内部ラベル: {lbl}")
    if is_schedule_row_display_supplement(row):
        lines.append(
            "※この行は SeasonEvent に無い大会・ウィンドウのため、日程タブでは表示補完です。"
            "進行は他の行と同じラウンド内で一括処理されます。"
        )
    return "\n".join(lines)
