"""
CLI 向けオフシーズン「進行サマリー」表示（表示のみ）。

処理順・ロジックは models/offseason.Offseason.run に触れない。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from basketball_sim.systems.offseason_phases import OFFSEASON_PHASES
except Exception:  # pragma: no cover - import guard for odd environments
    OFFSEASON_PHASES: Sequence[Tuple[str, str]] = []


def _phase_row(phase_no: int) -> Optional[Tuple[str, str]]:
    try:
        idx = int(phase_no) - 1
        phases = list(OFFSEASON_PHASES or [])
        if 0 <= idx < len(phases):
            return phases[idx][0], phases[idx][1]
    except Exception:
        pass
    return None


def _short_title(title: str, max_len: int = 44) -> str:
    t = str(title or "").strip()
    if not t:
        return "情報なし"
    if "：" in t:
        tail = t.split("：", 1)[1].strip()
        if tail:
            t = tail
    if len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


# phase_id -> (主な判断の一文, 次に見るべき項目の一文)
_FOCUS_BY_PHASE: Dict[str, Tuple[str, str]] = {
    "O01": ("前年資産の取り込みと枠の前提", "来期ドラフト資産・ルーキー予算"),
    "O02": ("大会・国際イベントの結果把握", "主要選手の消耗・国際日程の影響"),
    "O03": ("年齢・成長・帰化・引退の反映", "スタッツと潜在の変化"),
    "O04": ("ユースの出入りと将来枠", "昇格見込みとドラフト送り"),
    "O05": ("満了に対する再契約判断", "延長・提示額・放出の検討"),
    "O06": ("スカウトと来期ドラフト候補", "候補プロファイルと指名順イメージ"),
    "O07": ("前シーズン実績のリセット理解", "開幕前の評価ベース"),
    "O08": ("契約年数減算と満了処理", "ロスター枠と翌年キャップ影響"),
    "O09": ("国際マーケット枠の更新", "外国人枠・補強ルート"),
    "O10": ("特別指定離脱後のプール反映", "ドラフト枠と上位候補"),
    "O11": ("ドラフト指名と枠の確定", "オークション画面・候補比較・指名後の枠"),
    "O12": ("CPU トレードの結果把握", "ロスター変化と補填ニーズ"),
    "O13": ("FA での補強・整理", "FA 一覧・予算・育成との兼ね合い"),
    "O14": ("FA プール維持・待機選手", "残留枠と再挑戦の余地"),
    "O15": ("財務決算とオーナーミッション", "収支・要求・投資判断"),
    "O16": ("治療・監督レビュー・戦術・招待", "来季システム・怪我リスク"),
    "O17": ("本契約ロスター整合性の確認", "インシーズン前の最終チェック"),
}


def _pending_hints(offseason: Any, phase_id: str) -> List[str]:
    out: List[str] = []
    try:
        if phase_id == "O11":
            pool = getattr(offseason, "draft_pool", None)
            if isinstance(pool, list) and len(pool) > 0:
                out.append("ドラフト候補プールあり")
        if phase_id == "O13":
            fa = getattr(offseason, "free_agents", None)
            if isinstance(fa, list) and len(fa) > 0:
                out.append("FA 候補あり")
        if phase_id == "O06":
            fut = getattr(offseason, "future_draft_pool", None)
            if isinstance(fut, list) and len(fut) > 0:
                out.append("来期ドラフト候補あり")
    except Exception:
        pass
    if phase_id == "O15":
        out.append("経営・ミッションの確認")
    return out[:3]


def build_offseason_focus_summary(offseason: Any, phase_no: int) -> Dict[str, Any]:
    """
    表示用の辞書。情報欠損時はプレースホルダを入れる。
    """
    row = _phase_row(phase_no)
    if row is None:
        return {
            "phase_no": int(phase_no),
            "phase_id": "情報なし",
            "title": "情報なし",
            "main_judgment": "情報なし",
            "next_focus": "情報なし",
            "pending": [],
        }
    pid, title = row
    pair = _FOCUS_BY_PHASE.get(pid)
    if pair is None:
        main_j, next_f = "情報なし", "情報なし"
    else:
        main_j, next_f = pair
    pending = _pending_hints(offseason, pid)
    return {
        "phase_no": int(phase_no),
        "phase_id": pid,
        "title": title,
        "main_judgment": main_j,
        "next_focus": next_f,
        "pending": pending,
    }


def format_offseason_progress_cli_lines(offseason: Any, phase_no: int) -> List[str]:
    """
    1 ブロックあたり数行の進行サマリー（CLI print 用）。
    """
    try:
        if _phase_row(phase_no) is None:
            return []
        summary = build_offseason_focus_summary(offseason, phase_no)
        pid = summary.get("phase_id") or "情報なし"
        title_full = str(summary.get("title") or "")
        short = _short_title(title_full)
        main_j = str(summary.get("main_judgment") or "情報なし")
        next_f = str(summary.get("next_focus") or "情報なし")
        pending = summary.get("pending") or []
        lines = [
            "【オフシーズン進行】",
            f"現在: [{pid}] {short}",
            f"主な判断: {main_j} ／ 次に見る: {next_f}",
        ]
        if isinstance(pending, list) and pending:
            lines.append(f"未確認の目安: {'・'.join(str(p) for p in pending)}")
        return lines
    except Exception:
        return []
