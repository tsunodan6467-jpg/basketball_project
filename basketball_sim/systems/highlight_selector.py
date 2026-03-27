"""
Highlight Selector

役割:
presentation_events から「見せる価値のあるプレー」を抽出する

安全設計:
- 既存システムに一切影響を与えない
- presentation_layer の出力を読むだけ
- Match を渡す場合も PresentationLayer を内部で生成するだけ（シミュ結果は変更しない）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from basketball_sim.config.game_constants import (
    HIGHLIGHT_BIG_STAGE_COMPETITIONS,
    HIGHLIGHT_CONTEXT_PRESET_TABLE,
)

HIGHLIGHT_DEFAULT_MAX_EVENTS = 10
HIGHLIGHT_DEFAULT_MIN_SCORE = 18
HIGHLIGHT_PLAYOFF_MAX_EVENTS = 12
HIGHLIGHT_BIG_STAGE_MAX_EVENTS = 14
HIGHLIGHT_PLAYOFF_MIN_SCORE = 16
HIGHLIGHT_BIG_STAGE_MIN_SCORE = 14
HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS = 180
HIGHLIGHT_PLAYOFF_MAX_TOTAL_SECONDS = 240
HIGHLIGHT_BIG_STAGE_MAX_TOTAL_SECONDS = 300

SYNTHETIC_TIPOFF_PLAY_NO = -1
_FIRST_HALF_QUARTERS = (1, 2)
_FIRST_HALF_MIN_PLAYS = 2
_MAX_PLAYER_SHARE = 0.45
_MAX_PLAYER_MIN = 2
_MAX_S_TIER_EVENTS = 2


@dataclass(frozen=True)
class HighlightContextPreset:
    max_events: int
    min_score: int
    max_total_seconds: int


HIGHLIGHT_CONTEXT_PRESETS: Dict[str, HighlightContextPreset] = {
    key: HighlightContextPreset(
        max_events=int(values.get("max_events", HIGHLIGHT_DEFAULT_MAX_EVENTS)),
        min_score=int(values.get("min_score", HIGHLIGHT_DEFAULT_MIN_SCORE)),
        max_total_seconds=int(values.get("max_total_seconds", HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS)),
    )
    for key, values in HIGHLIGHT_CONTEXT_PRESET_TABLE.items()
}


def _build_safe_highlight_context_presets(
    raw_table: Dict[str, Dict[str, int]],
) -> Dict[str, HighlightContextPreset]:
    safe: Dict[str, HighlightContextPreset] = {}
    fallback = HighlightContextPreset(
        max_events=HIGHLIGHT_DEFAULT_MAX_EVENTS,
        min_score=HIGHLIGHT_DEFAULT_MIN_SCORE,
        max_total_seconds=HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS,
    )
    for key, values in raw_table.items():
        if not isinstance(values, dict):
            safe[key] = fallback
            continue
        try:
            max_events = int(values.get("max_events", fallback.max_events))
            min_score = int(values.get("min_score", fallback.min_score))
            max_total_seconds = int(values.get("max_total_seconds", fallback.max_total_seconds))
        except (TypeError, ValueError):
            safe[key] = fallback
            continue

        if max_events < 1:
            max_events = fallback.max_events
        if min_score < 0:
            min_score = fallback.min_score
        if max_total_seconds < 1:
            max_total_seconds = fallback.max_total_seconds
        safe[key] = HighlightContextPreset(
            max_events=max_events,
            min_score=min_score,
            max_total_seconds=max_total_seconds,
        )

    if "regular" not in safe:
        safe["regular"] = fallback
    if "playoff" not in safe:
        safe["playoff"] = safe["regular"]
    if "big_stage" not in safe:
        safe["big_stage"] = safe["playoff"]

    return safe


def validate_highlight_context_presets() -> bool:
    """外部設定の妥当性を簡易検証する。運用時チェック用。"""
    required = {"regular", "playoff", "big_stage"}
    if not isinstance(HIGHLIGHT_CONTEXT_PRESET_TABLE, dict):
        return False
    if not required.issubset(set(HIGHLIGHT_CONTEXT_PRESET_TABLE.keys())):
        return False
    for key in required:
        entry = HIGHLIGHT_CONTEXT_PRESET_TABLE.get(key)
        if not isinstance(entry, dict):
            return False
        try:
            max_events = int(entry.get("max_events", 0))
            min_score = int(entry.get("min_score", -1))
            max_total_seconds = int(entry.get("max_total_seconds", 0))
        except (TypeError, ValueError):
            return False
        if max_events < 1 or min_score < 0 or max_total_seconds < 1:
            return False
    return True


def _select_context_preset_key(*, is_playoff: bool, is_big_stage: bool) -> str:
    if is_big_stage:
        return "big_stage"
    if is_playoff:
        return "playoff"
    return "regular"


def _get_context_preset(*, is_playoff: bool, is_big_stage: bool) -> HighlightContextPreset:
    key = _select_context_preset_key(is_playoff=is_playoff, is_big_stage=is_big_stage)
    presets = _build_safe_highlight_context_presets(HIGHLIGHT_CONTEXT_PRESET_TABLE)
    return presets.get(key, presets["regular"])


def _quarter_num(event: Dict) -> int:
    q = event.get("quarter")
    return int(q) if isinstance(q, int) else 0


def _is_synthetic_tipoff(event: Dict) -> bool:
    return event.get("presentation_type") == "synthetic_tipoff"


def _is_first_half_play(event: Dict) -> bool:
    if _is_synthetic_tipoff(event):
        return False
    return _quarter_num(event) in _FIRST_HALF_QUARTERS


def _is_q1_quarter_start(event: Dict) -> bool:
    return event.get("presentation_type") == "quarter_start" and event.get("quarter") == 1


def _find_q1_quarter_start(presentation_events: List[Dict]) -> Dict | None:
    for e in presentation_events:
        if _is_q1_quarter_start(e):
            return dict(e)
    return None


def _make_synthetic_tipoff_event() -> Dict:
    return {
        "play_no": SYNTHETIC_TIPOFF_PLAY_NO,
        "quarter": 1,
        "clock_seconds": 600,
        "home_score": 0,
        "away_score": 0,
        "presentation_type": "synthetic_tipoff",
        "headline": "ティップオフ",
        "main_text": "試合開始。センターサークルでジャンプボール。",
        "importance": "low",
        "highlight_score": 0,
        "highlight_tags": [],
        "raw_play": {},
    }


def _is_opening_clip(event: Dict) -> bool:
    return _is_synthetic_tipoff(event) or _is_q1_quarter_start(event)


def _trim_playlist_to_max(working: List[Dict], max_events: int) -> List[Dict]:
    """max_events まで削る。先頭の opening（合成ティップオフ or Q1 quarter_start）は可能なら維持。"""
    if len(working) <= max_events:
        return working
    out = list(working)
    while len(out) > max_events:
        fh_count = sum(1 for e in out if _is_first_half_play(e))

        def collect(strict_fh: bool) -> List[int]:
            rem: List[int] = []
            for i, e in enumerate(out):
                if i == 0 and _is_opening_clip(e):
                    continue
                if _is_first_half_play(e) and fh_count <= _FIRST_HALF_MIN_PLAYS and strict_fh:
                    continue
                rem.append(i)
            return rem

        removable = collect(strict_fh=True)
        if not removable:
            removable = collect(strict_fh=False)
        if not removable:
            removable = [len(out) - 1]
        drop_i = min(
            removable,
            key=lambda i: (
                0 if not _is_first_half_play(out[i]) else 1,
                int(out[i].get("highlight_score", 0)),
                -_quarter_num(out[i]),
            ),
        )
        out.pop(drop_i)
    return out


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_force_s_event(event: Dict) -> bool:
    tags = event.get("highlight_tags") or []
    tag_set = {str(t) for t in tags} if isinstance(tags, list) else set()
    ptype = str(event.get("presentation_type") or "")
    quarter = _to_int(event.get("quarter"), 0)
    clock = _to_int(event.get("clock_seconds"), 9999)
    score = _to_int(event.get("highlight_score"), 0)

    if "buzzer" in tag_set:
        return True
    if "lead_change" in tag_set and quarter >= 4 and clock <= 30:
        return True
    if "go_ahead" in tag_set and quarter >= 4 and clock <= 30:
        return True
    if ptype in {"block", "steal"} and "clutch" in tag_set and quarter >= 4 and clock <= 30:
        return True
    return score >= 90


def _assign_highlight_tier(event: Dict) -> str:
    if _is_force_s_event(event):
        return "S"
    score = _to_int(event.get("highlight_score"), 0)
    if score >= 50:
        return "S"
    if score >= 30:
        return "A"
    if score >= 18:
        return "B"
    return "none"


def _select_tiered_highlights_timeline(
    presentation_events: List[Dict],
    *,
    top_n: int,
    min_score: int,
) -> List[Dict]:
    candidates = [dict(e) for e in presentation_events if _to_int(e.get("highlight_score"), 0) >= min_score]
    if not candidates:
        return []

    for e in candidates:
        e["highlight_tier"] = _assign_highlight_tier(e)
        if _is_force_s_event(e):
            e["force_tier"] = "S"

    force_s = [e for e in candidates if e.get("force_tier") == "S"]
    force_s.sort(key=lambda x: (_to_int(x.get("highlight_score"), 0), -_to_int(x.get("play_no"), 0)), reverse=True)

    s_candidates = [e for e in candidates if e.get("highlight_tier") == "S" and e.get("force_tier") != "S"]
    a_candidates = [e for e in candidates if e.get("highlight_tier") == "A"]
    b_candidates = [e for e in candidates if e.get("highlight_tier") == "B"]

    for bucket in (s_candidates, a_candidates, b_candidates):
        bucket.sort(key=lambda x: (_to_int(x.get("highlight_score"), 0), -_to_int(x.get("play_no"), 0)), reverse=True)

    selected: List[Dict] = []
    used = set()

    def take_from(bucket: List[Dict], limit: int) -> None:
        for e in bucket:
            if len(selected) >= top_n or limit <= 0:
                return
            pn = e.get("play_no")
            if pn in used:
                continue
            selected.append(dict(e))
            used.add(pn)
            limit -= 1

    # 強制Sは本数上限を超えても先に拾う（ただし top_n は超えない）
    take_from(force_s, top_n)
    s_capacity = max(0, _MAX_S_TIER_EVENTS - sum(1 for e in selected if e.get("highlight_tier") == "S"))
    take_from(s_candidates, s_capacity)
    take_from(a_candidates, top_n - len(selected))
    take_from(b_candidates, top_n - len(selected))

    selected.sort(key=lambda x: _to_int(x.get("play_no"), 0))
    return selected


def _append_selection_reason(event: Dict, reason: str) -> Dict:
    out = dict(event)
    reasons = out.get("selection_reasons")
    if not isinstance(reasons, list):
        reasons = []
    if reason not in reasons:
        reasons.append(reason)
    out["selection_reasons"] = reasons
    out["selection_reason"] = reasons[-1] if reasons else "selected"
    return out


def _extract_possession_no(event: Dict) -> Optional[int]:
    raw_play = event.get("raw_play")
    if isinstance(raw_play, dict):
        pn = raw_play.get("possession_no")
        if isinstance(pn, int):
            return pn
    pn2 = event.get("possession_no")
    if isinstance(pn2, int):
        return pn2
    return None


def _dedupe_same_possession_keep_best(working: List[Dict]) -> List[Dict]:
    """
    同一 possession_no の重複を抑制。highlight_score が高い方を残す。
    possession_no が無いイベントはそのまま残す。
    """
    if len(working) < 2:
        return working
    best_by_pos: Dict[int, Dict] = {}
    no_pos: List[Dict] = []
    for e in working:
        pn = _extract_possession_no(e)
        if pn is None:
            no_pos.append(dict(e))
            continue
        cur = best_by_pos.get(pn)
        if cur is None or int(e.get("highlight_score", 0)) > int(cur.get("highlight_score", 0)):
            best_by_pos[pn] = _append_selection_reason(dict(e), "best_in_possession")
    out = [*no_pos, *best_by_pos.values()]
    out.sort(key=lambda e: int(e.get("play_no", 0)))
    return out


def _limit_focus_player_concentration(
    working: List[Dict],
    presentation_events: List[Dict],
    max_events: int,
) -> List[Dict]:
    """
    同一 focus_player_name の偏りを抑える。
    置換候補は未採用プレーから、同じプレイ番号範囲に近いものを優先して探索する。
    """
    if len(working) < 4:
        return working
    out = [dict(e) for e in working]
    limit = max(_MAX_PLAYER_MIN, int(max_events * _MAX_PLAYER_SHARE))
    for _ in range(6):
        counts: Dict[str, int] = {}
        for e in out:
            fp = e.get("focus_player_name")
            if isinstance(fp, str) and fp.strip():
                counts[fp] = counts.get(fp, 0) + 1
        crowded = [name for name, cnt in counts.items() if cnt > limit]
        if not crowded:
            break
        crowded_set = set(crowded)
        present = {e.get("play_no") for e in out}
        changed = False
        # 低スコア側から置換
        crowded_indices = [
            i for i, e in enumerate(out)
            if isinstance(e.get("focus_player_name"), str) and e.get("focus_player_name") in crowded_set
        ]
        crowded_indices.sort(key=lambda i: int(out[i].get("highlight_score", 0)))
        for idx in crowded_indices:
            src = out[idx]
            src_play = int(src.get("play_no", 0))
            best: Dict | None = None
            best_key: tuple[int, int] | None = None
            for cand in presentation_events:
                if not isinstance(cand, dict):
                    continue
                pn = cand.get("play_no")
                if pn in present:
                    continue
                cfp = cand.get("focus_player_name")
                if isinstance(cfp, str) and cfp in crowded_set:
                    continue
                cscore = int(cand.get("highlight_score", 0))
                # スコアを優先しつつ、元イベントに近い play_no を優先
                key = (cscore, -abs(int(cand.get("play_no", 0)) - src_play))
                if best_key is None or key > best_key:
                    best_key = key
                    best = dict(cand)
            if best is not None:
                out[idx] = _append_selection_reason(best, "player_balance_backfill")
                present = {e.get("play_no") for e in out}
                changed = True
                break
        if not changed:
            break
    out.sort(key=lambda e: int(e.get("play_no", 0)))
    return out


def _estimate_clip_seconds(event: Dict) -> int:
    ptype = str(event.get("presentation_type") or "")
    score = int(event.get("highlight_score", 0))
    if ptype == "synthetic_tipoff":
        return 4
    if ptype in {"quarter_start", "quarter_end"}:
        return 5
    if ptype == "game_end":
        return 6

    # 安全な初期推定。高スコアほどやや長くする
    base = 14
    if ptype in {"score_make_3", "block", "steal"}:
        base = 16
    if score >= 80:
        base += 8
    elif score >= 60:
        base += 5
    elif score >= 40:
        base += 2
    return max(8, min(base, 26))


def _derive_emphasis_level(event: Dict) -> str:
    tier = str(event.get("highlight_tier") or "")
    if event.get("force_tier") == "S":
        return "max"
    if tier == "S":
        return "high"
    if tier == "A":
        return "medium"
    if tier == "B":
        return "low"
    return "none"


def _derive_clip_role(event: Dict) -> str:
    ptype = str(event.get("presentation_type") or "")
    if ptype in {"synthetic_tipoff", "quarter_start"}:
        return "opening"
    if ptype in {"quarter_end", "game_end"}:
        return "closing"
    if event.get("force_tier") == "S":
        return "climax"
    tier = str(event.get("highlight_tier") or "")
    if tier == "S":
        return "key_play"
    if tier == "A":
        return "flow_keep"
    if tier == "B":
        return "bridge"
    return "normal"


def _derive_recommended_camera_style(event: Dict) -> str:
    ptype = str(event.get("presentation_type") or "")
    if ptype in {"synthetic_tipoff", "quarter_start", "quarter_end", "game_end"}:
        return "scoreboard_hold"
    if event.get("force_tier") == "S":
        return "cinematic"
    tier = str(event.get("highlight_tier") or "")
    if tier == "S":
        return "replay_focus"
    if tier == "A":
        return "highlight_follow"
    return "broadcast"


def _enrich_event_plan_metadata(event: Dict, index: int) -> Dict:
    out = dict(event)
    estimated = _estimate_clip_seconds(out)
    if "highlight_tier" not in out:
        out["highlight_tier"] = _assign_highlight_tier(out)
    if _is_force_s_event(out):
        out["force_tier"] = "S"
    out["clip_order"] = index
    out["estimated_clip_seconds"] = estimated
    out["emphasis_level"] = _derive_emphasis_level(out)
    out["clip_role"] = _derive_clip_role(out)
    out["recommended_camera_style"] = _derive_recommended_camera_style(out)
    return out


def _build_highlight_plan_metadata(events: List[Dict]) -> List[Dict]:
    return [_enrich_event_plan_metadata(e, i) for i, e in enumerate(events)]


def _is_climax_candidate(event: Dict) -> bool:
    if event.get("force_tier") == "S":
        return True
    if str(event.get("clip_role") or "") == "climax":
        return True
    if str(event.get("highlight_tier") or "") == "S":
        quarter = _to_int(event.get("quarter"), 0)
        if quarter >= 4:
            return True
    return False


def _shape_finale_order(events: List[Dict]) -> List[Dict]:
    """
    ラスト 1〜2 本をクライマックス寄せにする。
    採用セットは変えず、並び順のみ調整する。
    """
    if len(events) < 4:
        return events
    out = [dict(e) for e in events]

    # 1) 最終クリップはクライマックス候補を優先
    best_last_idx = None
    best_last_key: tuple[int, int, int] | None = None
    for i, e in enumerate(out):
        if _is_opening_clip(e):
            continue
        if not _is_climax_candidate(e):
            continue
        key = (
            _to_int(e.get("quarter"), 0),
            _to_int(e.get("clock_seconds"), 9999) * -1,  # 残り時間が少ないほど優先
            _to_int(e.get("highlight_score"), 0),
        )
        if best_last_key is None or key > best_last_key:
            best_last_key = key
            best_last_idx = i
    if best_last_idx is not None and best_last_idx != len(out) - 1:
        last_ev = out.pop(best_last_idx)
        out.append(_append_selection_reason(last_ev, "finale_anchor_last"))

    # 2) 最後から2本目も終盤寄りを優先
    if len(out) >= 5:
        tail_locked_idx = len(out) - 1
        best_pen_idx = None
        best_pen_key: tuple[int, int] | None = None
        for i, e in enumerate(out[:-1]):
            if _is_opening_clip(e):
                continue
            quarter = _to_int(e.get("quarter"), 0)
            score = _to_int(e.get("highlight_score"), 0)
            if quarter < 3 and score < 45:
                continue
            key = (quarter, score)
            if best_pen_key is None or key > best_pen_key:
                best_pen_key = key
                best_pen_idx = i
        pen_idx = len(out) - 2
        if best_pen_idx is not None and best_pen_idx != pen_idx and best_pen_idx != tail_locked_idx:
            ev = out.pop(best_pen_idx)
            out.insert(len(out) - 1, _append_selection_reason(ev, "finale_support_penultimate"))
    return out


def _total_estimated_seconds(events: List[Dict]) -> int:
    return sum(_estimate_clip_seconds(e) for e in events)


def _trim_playlist_to_seconds(
    working: List[Dict],
    max_events: int,
    max_total_seconds: int,
) -> List[Dict]:
    """推定総尺が上限以下になるまで削る。先頭 opening と前半最低本数は可能な範囲で維持。"""
    if max_total_seconds <= 0:
        return working
    out = list(working)
    while out and _total_estimated_seconds(out) > max_total_seconds:
        fh_count = sum(1 for e in out if _is_first_half_play(e))
        removable: List[int] = []
        for i, e in enumerate(out):
            if i == 0 and _is_opening_clip(e):
                continue
            if _is_first_half_play(e) and fh_count <= _FIRST_HALF_MIN_PLAYS and max_events >= _FIRST_HALF_MIN_PLAYS + 1:
                continue
            removable.append(i)
        if not removable:
            for i, e in enumerate(out):
                if i == 0 and _is_opening_clip(e):
                    continue
                removable.append(i)
        if not removable:
            break
        drop_i = min(
            removable,
            key=lambda i: (
                0 if not _is_first_half_play(out[i]) else 1,
                _estimate_clip_seconds(out[i]),
                int(out[i].get("highlight_score", 0)),
            ),
        )
        out.pop(drop_i)
    return out


def _ensure_first_half_minimum(
    working: List[Dict],
    presentation_events: List[Dict],
    max_events: int,
) -> List[Dict]:
    """Q1–Q2 のプレイを最低 2 本含める（合成ティップオフはカウントしない）。max_events が 3 未満のときはスキップ。"""
    if max_events < _FIRST_HALF_MIN_PLAYS + 1:
        return working
    out = [dict(e) for e in working]
    present = {e.get("play_no") for e in out}
    fh_pool = [dict(e) for e in presentation_events if _is_first_half_play(e)]
    fh_pool.sort(key=lambda e: int(e.get("highlight_score", 0)), reverse=True)

    while True:
        fh_in = [e for e in out if _is_first_half_play(e)]
        if len(fh_in) >= _FIRST_HALF_MIN_PLAYS:
            break
        added = False
        for e in fh_pool:
            pn = e.get("play_no")
            if pn in present:
                continue
            out.append(_append_selection_reason(dict(e), "first_half_backfill"))
            present.add(pn)
            added = True
            break
        if not added:
            break

    out.sort(key=lambda e: int(e.get("play_no", 0)))
    return _trim_playlist_to_max(out, max_events)


_TYPES_SKIP_CONSECUTIVE_BREAK = frozenset(
    {"quarter_start", "quarter_end", "game_end", "synthetic_tipoff"},
)


def _reduce_consecutive_same_presentation_type(
    working: List[Dict],
    presentation_events: List[Dict],
) -> List[Dict]:
    """
    隣接して同じ presentation_type になるのを、間に挟まれた未採用プレーで置き換えて緩和する。
    時系列（play_no 昇順）は保つ。
    """
    if len(working) < 2:
        return working

    out = [dict(e) for e in working]
    for _ in range(5):
        present = {e.get("play_no") for e in out}
        changed = False
        i = 0
        while i < len(out) - 1:
            a = out[i]
            b = out[i + 1]
            ta = str(a.get("presentation_type") or "")
            tb = str(b.get("presentation_type") or "")
            if ta != tb or ta in _TYPES_SKIP_CONSECUTIVE_BREAK:
                i += 1
                continue
            pa = int(a.get("play_no", 0))
            pb = int(b.get("play_no", 0))
            if pb <= pa + 1:
                i += 1
                continue
            best: Dict | None = None
            best_score = -1
            for e in presentation_events:
                if not isinstance(e, dict):
                    continue
                pn = e.get("play_no")
                if pn in present:
                    continue
                try:
                    pni = int(pn) if pn is not None else -1
                except (TypeError, ValueError):
                    continue
                if not (pa < pni < pb):
                    continue
                et = str(e.get("presentation_type") or "")
                if et == ta or et in _TYPES_SKIP_CONSECUTIVE_BREAK:
                    continue
                sc = int(e.get("highlight_score", 0))
                if sc > best_score:
                    best_score = sc
                    best = dict(e)
            if best is not None:
                out[i + 1] = _append_selection_reason(best, "break_consecutive_type")
                present = {e.get("play_no") for e in out}
                changed = True
            i += 1
        if not changed:
            break
    return out


def _ensure_tipoff_opening(
    working: List[Dict],
    presentation_events: List[Dict],
    max_events: int,
) -> List[Dict]:
    """
    ログに Q1 の quarter_start がある場合は先頭に置く（無ければ synthetic_tipoff）。
    既に先頭が Q1 quarter_start なら二重にしない。
    """
    if not working:
        return working
    out = [dict(e) for e in working]
    q1 = _find_q1_quarter_start(presentation_events)
    if out and _is_q1_quarter_start(out[0]):
        return _trim_playlist_to_max(out, max_events)
    if q1 is not None:
        pn = q1.get("play_no")
        rest = [dict(e) for e in out if e.get("play_no") != pn]
        rest.sort(key=lambda e: int(e.get("play_no", 0)))
        out = [_append_selection_reason(dict(q1), "opening_q1_start"), *rest]
    else:
        rest = [dict(e) for e in out]
        rest.sort(key=lambda e: int(e.get("play_no", 0)))
        out = [_append_selection_reason(_make_synthetic_tipoff_event(), "opening_synthetic_tipoff"), *rest]
    return _trim_playlist_to_max(out, max_events)


class HighlightSelector:
    def __init__(self, presentation_events: List[Dict]):
        self.events = presentation_events

    # =========================================================
    # メイン機能
    # =========================================================
    def select_highlights(
        self,
        top_n: int = 15,
        min_score: int = 20,
    ) -> List[Dict]:
        """
        ハイライト抽出

        top_n: 最大抽出数
        min_score: 最低スコア
        """
        candidates = [
            e for e in self.events
            if e.get("highlight_score", 0) >= min_score
        ]

        candidates.sort(
            key=lambda x: x.get("highlight_score", 0),
            reverse=True,
        )

        return candidates[:top_n]

    # =========================================================
    # 時系列ハイライト（流れ重視）
    # =========================================================
    def select_highlights_timeline(
        self,
        top_n: int = 20,
        min_score: int = 18,
    ) -> List[Dict]:
        """
        時系列を保ったハイライト

        重要:
        - 先に highlight_score 上位を抽出
        - その後で play_no 順に並べ直す

        これにより
        「試合開始から条件を満たしたプレーを先頭から top_n 件取る」
        バグを防ぐ
        """
        candidates = [
            e for e in self.events
            if e.get("highlight_score", 0) >= min_score
        ]

        candidates.sort(
            key=lambda x: x.get("highlight_score", 0),
            reverse=True,
        )
        selected = candidates[:top_n]

        selected.sort(key=lambda x: x.get("play_no", 0))
        return selected

    # =========================================================
    # クラッチ抽出
    # =========================================================
    def select_clutch_highlights(self) -> List[Dict]:
        """
        接戦＋終盤だけ抜き出す
        """
        result = []

        for e in self.events:
            tags = e.get("highlight_tags", [])

            if "clutch" in tags or "lead_change" in tags:
                result.append(e)

        return result

    # =========================================================
    # デバッグ表示
    # =========================================================
    def debug_print(self, highlights: List[Dict]) -> None:
        print("[HIGHLIGHTS]")
        print(f"count={len(highlights)}")

        for e in highlights:
            print(
                f"Play#{e.get('play_no')} | "
                f"{e.get('presentation_type')} | "
                f"score={e.get('highlight_score')} | "
                f"{e.get('headline')}"
            )

    def debug_print_plan(self, highlights: List[Dict]) -> None:
        """HighlightPlan の要点（選定理由・演出メタ）を1行で確認する。"""
        print("[HIGHLIGHT_PLAN]")
        print(f"count={len(highlights)}")
        for e in highlights:
            reasons = e.get("selection_reasons")
            if not isinstance(reasons, list):
                reasons = []
            reason_text = ",".join(str(r) for r in reasons[-3:]) if reasons else "-"
            print(
                f"Play#{e.get('play_no', '-')} | "
                f"{e.get('presentation_type', '-')} | "
                f"tier={e.get('highlight_tier', '-')} | "
                f"force={e.get('force_tier', '-')} | "
                f"role={e.get('clip_role', '-')} | "
                f"camera={e.get('recommended_camera_style', '-')} | "
                f"emp={e.get('emphasis_level', '-')} | "
                f"sec={e.get('estimated_clip_seconds', '-')} | "
                f"reasons={reason_text}"
            )


def build_highlight_playlist_events(
    presentation_events: List[Dict],
    *,
    max_events: int = HIGHLIGHT_DEFAULT_MAX_EVENTS,
    min_score: int = HIGHLIGHT_DEFAULT_MIN_SCORE,
    max_total_seconds: int = HIGHLIGHT_DEFAULT_MAX_TOTAL_SECONDS,
) -> List[Dict]:
    """
    観戦用ハイライト列（docs/HIGHLIGHT_MODE_SPEC.md の段階実装）。

    既存の `highlight_score` と tier(S/A/B) を使って採用し、時系列で並べる。
    候補が空なら min_score を 10、0 と段階的に下げて再試行する。
    max_events が 3 以上のとき Q1–Q2 を最低 2 本含める。
    ログに Q1 の quarter_start が無ければ先頭に synthetic_tipoff を挿入する。
    隣接同種は、間番号に未採用プレーがあれば低減する。
    仕上げに推定総尺が max_total_seconds を超えないよう調整する。
    """
    if not presentation_events:
        return []

    sel = HighlightSelector(presentation_events)
    for ms in (min_score, 10, 0):
        base = _select_tiered_highlights_timeline(
            sel.events,
            top_n=max_events,
            min_score=ms,
        )
        if not base:
            continue
        working = [_append_selection_reason(dict(e), "tier_selected") for e in base]
        working = _ensure_first_half_minimum(working, presentation_events, max_events)
        working = _ensure_tipoff_opening(working, presentation_events, max_events)
        working = _dedupe_same_possession_keep_best(working)
        working = _reduce_consecutive_same_presentation_type(working, presentation_events)
        working = _limit_focus_player_concentration(working, presentation_events, max_events)
        working = _trim_playlist_to_max(working, max_events)
        working = _trim_playlist_to_seconds(working, max_events, max_total_seconds)
        if working:
            working = _shape_finale_order(working)
            return _build_highlight_plan_metadata(working)
    return []


def build_highlight_override_events_from_match(
    match: Any,
    *,
    max_events: Optional[int] = None,
    min_score: Optional[int] = None,
    max_total_seconds: Optional[int] = None,
) -> List[Dict]:
    """
    試合からプレゼンイベントを生成し、ハイライト用の短い列だけ返す。
    シミュレーションは変更しない（PresentationLayer は読み取り変換のみ）。
    """
    from basketball_sim.systems.presentation_layer import PresentationLayer

    layer = PresentationLayer(match)
    events = layer.build()
    resolved_max_events, resolved_min_score, resolved_max_total_seconds = _resolve_highlight_limits_for_match(
        match=match,
        max_events=max_events,
        min_score=min_score,
        max_total_seconds=max_total_seconds,
    )
    return build_highlight_playlist_events(
        events,
        max_events=resolved_max_events,
        min_score=resolved_min_score,
        max_total_seconds=resolved_max_total_seconds,
    )


def build_highlight_debug_summary(events: List[Dict]) -> str:
    """
    1試合分のハイライト選定結果を軽量テキストで返す。
    調整時にログへ出しやすいよう、主要メタのみを集約する。
    """
    if not events:
        return "[HIGHLIGHT_DEBUG] empty"

    total_seconds = sum(_estimate_clip_seconds(e) for e in events)
    tier_counts: Dict[str, int] = {}
    reason_counts: Dict[str, int] = {}
    style_counts: Dict[str, int] = {}
    for e in events:
        tier = str(e.get("highlight_tier") or "none")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        style = str(e.get("recommended_camera_style") or "-")
        style_counts[style] = style_counts.get(style, 0) + 1
        reasons = e.get("selection_reasons")
        if isinstance(reasons, list):
            for r in reasons:
                key = str(r)
                reason_counts[key] = reason_counts.get(key, 0) + 1

    def fmt_counts(d: Dict[str, int]) -> str:
        items = sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
        return ",".join(f"{k}:{v}" for k, v in items[:8]) if items else "-"

    return (
        f"[HIGHLIGHT_DEBUG] count={len(events)} total_est_sec={total_seconds} "
        f"tiers={fmt_counts(tier_counts)} styles={fmt_counts(style_counts)} "
        f"reasons={fmt_counts(reason_counts)}"
    )


def _resolve_highlight_limits_for_match(
    match: Any,
    *,
    max_events: Optional[int],
    min_score: Optional[int],
    max_total_seconds: Optional[int],
) -> tuple[int, int, int]:
    """
    試合文脈からハイライトの上限を安全に決める。
    - 明示指定がある場合は明示値を優先
    - 重要試合ほど上限本数を増やし、閾値を少し下げる
    """
    competition_type = str(getattr(match, "competition_type", "regular_season") or "regular_season").strip().lower()
    is_playoff = bool(getattr(match, "is_playoff", False) or competition_type == "playoff")
    is_big_stage = competition_type in HIGHLIGHT_BIG_STAGE_COMPETITIONS
    preset = _get_context_preset(is_playoff=is_playoff, is_big_stage=is_big_stage)

    if max_events is None:
        resolved_max_events = preset.max_events
    else:
        resolved_max_events = int(max_events)

    if min_score is None:
        resolved_min_score = preset.min_score
    else:
        resolved_min_score = int(min_score)

    if max_total_seconds is None:
        resolved_max_total_seconds = preset.max_total_seconds
    else:
        resolved_max_total_seconds = int(max_total_seconds)

    if resolved_max_events < 1:
        resolved_max_events = 1
    if resolved_min_score < 0:
        resolved_min_score = 0
    if resolved_max_total_seconds < 1:
        resolved_max_total_seconds = 1

    return resolved_max_events, resolved_min_score, resolved_max_total_seconds
