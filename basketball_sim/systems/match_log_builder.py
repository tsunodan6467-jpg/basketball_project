"""
user_team 関与試合の軽量 match_log エントリを組み立てる（読み取り専用）。

full PBP / full commentary は保存しない。Team / Player オブジェクトは dict に入れない。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = ["build_user_match_log_entry"]

_KEY_PLAY_FIELDS = (
    "play_no",
    "quarter",
    "result_type",
    "text",
    "commentary_text",
    "home_score",
    "away_score",
)


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _team_name(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj.strip()
    return str(getattr(obj, "name", "") or "").strip()


def _event_attr(event: Any, name: str, default: Any = None) -> Any:
    if event is None:
        return default
    try:
        return getattr(event, name, default)
    except Exception:
        return default


def _match_team_name(match: Any, side: str) -> str:
    if match is None:
        return ""
    key = f"{side}_team"
    try:
        return _team_name(getattr(match, key, None))
    except Exception:
        return ""


def _teams_match(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    if a is b:
        return True
    na, nb = _team_name(a), _team_name(b)
    return na != "" and na == nb


def _user_involved(user_team: Any, home_team: Any, away_team: Any) -> bool:
    if user_team is None:
        return False
    return _teams_match(user_team, home_team) or _teams_match(user_team, away_team)


def _score_result_for_user(
    user_team: Any,
    home_team: Any,
    away_team: Any,
    home_score: Any,
    away_score: Any,
) -> str:
    hs = _safe_int(home_score)
    als = _safe_int(away_score)
    if hs is None or als is None:
        return "unknown"
    if _teams_match(user_team, home_team):
        if hs > als:
            return "W"
        if hs < als:
            return "L"
        return "D"
    if _teams_match(user_team, away_team):
        if als > hs:
            return "W"
        if als < hs:
            return "L"
        return "D"
    return "unknown"


def _summary_line(
    user_name: str,
    home_name: str,
    away_name: str,
    user_team: Any,
    home_team: Any,
    away_team: Any,
    home_score: Any,
    away_score: Any,
) -> str:
    hs = _safe_int(home_score)
    als = _safe_int(away_score)
    if _teams_match(user_team, home_team):
        opponent = away_name or "—"
        user_score, opp_score = hs, als
    else:
        opponent = home_name or "—"
        user_score, opp_score = als, hs

    if user_score is None or opp_score is None:
        mark = "？"
        score_text = f"{user_name} 結果不明 {opponent}"
    elif user_score > opp_score:
        mark = "○"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"
    elif user_score < opp_score:
        mark = "●"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"
    else:
        mark = "△"
        score_text = f"{user_name} {user_score} - {opp_score} {opponent}"
    return f"{mark} {score_text}"


def _commentary_excerpt(
    match: Any,
    *,
    max_head: int = 5,
    max_tail: int = 5,
) -> Dict[str, Any]:
    lines: List[str] = []
    try:
        getter = getattr(match, "get_commentary_lines", None)
        if callable(getter):
            raw = getter()
            if raw:
                lines = [str(x) for x in raw]
    except Exception:
        lines = []

    total = len(lines)
    head = lines[:max_head] if max_head > 0 else []
    tail = lines[-max_tail:] if max_tail > 0 and total > 0 else []
    if total > 0 and max_head + max_tail >= total and head and tail:
        overlap = len(head) + len(tail) - total
        if overlap > 0 and len(tail) > overlap:
            tail = tail[overlap:]
    return {"head": head, "tail": tail, "total_lines": total}


def _plain_dict(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in obj.items():
        if key == "events":
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
    return out


def _key_plays_excerpt(match: Any, *, max_key_plays: int = 8) -> List[Dict[str, Any]]:
    if max_key_plays <= 0:
        return []
    raw_plays: List[Any] = []
    try:
        getter = getattr(match, "get_play_sequence_log", None)
        if callable(getter):
            fetched = getter()
            if fetched:
                raw_plays = list(fetched)[-max_key_plays:]
    except Exception:
        raw_plays = []

    result: List[Dict[str, Any]] = []
    for play in raw_plays:
        if not isinstance(play, dict):
            continue
        excerpt: Dict[str, Any] = {}
        for field in _KEY_PLAY_FIELDS:
            if field in play:
                excerpt[field] = play[field]
        plain = _plain_dict(excerpt)
        if plain:
            result.append(plain)
    return result


def _stable_match_id(event_id: str, home_name: str, away_name: str, event: Any) -> str:
    if event_id:
        return event_id
    rnd = _event_attr(event, "round_number")
    if rnd is None:
        rnd = _event_attr(event, "week")
    if rnd is None:
        rnd = "?"
    return f"{rnd}-{home_name}-{away_name}"


def build_user_match_log_entry(
    *,
    match: Any,
    event: Any,
    user_team: Any,
    home_score: Any,
    away_score: Any,
    max_commentary_head: int = 5,
    max_commentary_tail: int = 5,
    max_key_plays: int = 8,
) -> Optional[Dict[str, Any]]:
    home_team_obj = _event_attr(event, "home_team") or getattr(match, "home_team", None)
    away_team_obj = _event_attr(event, "away_team") or getattr(match, "away_team", None)

    if not _user_involved(user_team, home_team_obj, away_team_obj):
        return None

    home_name = _team_name(home_team_obj) or _match_team_name(match, "home")
    away_name = _team_name(away_team_obj) or _match_team_name(match, "away")
    user_name = _team_name(user_team)

    event_id = str(_event_attr(event, "event_id") or "")
    round_number = _safe_int(_event_attr(event, "round_number"))
    if round_number is None:
        round_number = _safe_int(_event_attr(event, "week"))

    return {
        "match_id": _stable_match_id(event_id, home_name, away_name, event),
        "event_id": event_id,
        "round": round_number,
        "competition_type": str(_event_attr(event, "competition_type") or ""),
        "stage": str(_event_attr(event, "stage") or ""),
        "week": _safe_int(_event_attr(event, "week")),
        "day_of_week": str(_event_attr(event, "day_of_week") or ""),
        "home_team": home_name,
        "away_team": away_name,
        "home_score": _safe_int(home_score),
        "away_score": _safe_int(away_score),
        "user_team_involved": True,
        "user_team": user_name,
        "user_result": _score_result_for_user(
            user_team, home_team_obj, away_team_obj, home_score, away_score
        ),
        "summary_line": _summary_line(
            user_name,
            home_name,
            away_name,
            user_team,
            home_team_obj,
            away_team_obj,
            home_score,
            away_score,
        ),
        "commentary_excerpt": _commentary_excerpt(
            match,
            max_head=max_commentary_head,
            max_tail=max_commentary_tail,
        ),
        "key_plays": _key_plays_excerpt(match, max_key_plays=max_key_plays),
        "captured_at": "simulate_next_round",
    }
