"""
CPU クラブ向けの軽量「戦略プロファイル」（第1段）。

新しい Team フィールドは増やさず、既存属性だけから read-only の補正係数を返す。
呼び出し側は任意だが、トレード閾値や裏経営ロールなどに薄く掛ける想定。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from basketball_sim.systems.club_profile import get_club_base_profile

_VALID_EXPECTATIONS = frozenset(
    {"rebuild", "playoff_race", "promotion", "title_challenge", "title_or_bust"}
)

# 今季勝率と同じく、勝敗がまだ形成されていない間は骨格ロック・補助を弱める
_MIN_REGULAR_GP_FOR_RECORD_SIGNALS = 4


@dataclass(frozen=True)
class StrategyProfile:
    """CPU クラブの戦略タグと、既存ロジックへ掛ける弱いスカラー補正のみ。"""

    strategy_tag: str  # "rebuild" | "hold" | "push"
    fa_aggressiveness: float
    trade_loss_tolerance: float
    future_value_weight: float


_DEFAULT = StrategyProfile(
    strategy_tag="hold",
    fa_aggressiveness=1.0,
    trade_loss_tolerance=1.0,
    future_value_weight=1.0,
)


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _regular_games_played(team: Any) -> int:
    w = max(0, _safe_int(getattr(team, "regular_wins", 0), 0))
    l = max(0, _safe_int(getattr(team, "regular_losses", 0), 0))
    return min(80, w + l)


def _current_win_pct(team: Any) -> Optional[float]:
    w = max(0, _safe_int(getattr(team, "regular_wins", 0), 0))
    l = max(0, _safe_int(getattr(team, "regular_losses", 0), 0))
    if w + l < _MIN_REGULAR_GP_FOR_RECORD_SIGNALS:
        return None
    return w / float(w + l)


def _last_season_win_pct(team: Any) -> Optional[float]:
    w = max(0, _safe_int(getattr(team, "last_season_wins", 0), 0))
    l = max(0, _safe_int(getattr(team, "last_season_losses", 0), 0))
    if w + l < 8:
        return None
    return w / float(w + l)


def _opening_gp0_score_add(team: Any, exp: str, money: int, ll: int) -> Tuple[int, int]:
    """
    GP==0（開幕直前相当）のみの薄い補助。半減後に加算し、試合前でも意味のある材料だけ使う。
    """
    if _regular_games_played(team) != 0:
        return 0, 0
    ep = 0
    er = 0
    if exp == "promotion":
        ep += 1
    rk = _latest_history_rank(team)
    if rk is not None:
        if rk <= 3:
            ep += 1
        elif rk >= 14:
            er += 1
    if money < 5_000_000:
        er += 1
    elif 100_000_000 < money < 500_000_000:
        ep += 1

    # 全クラブ同一超富裕・rank 欠損の開幕で傾向が完全フラットなときだけ、
    # 既存の team_id + league_level から決定的に薄い push/rebuild を割り振る（wins 非使用）。
    if rk is None and money >= 500_000_000 and exp == "playoff_race":
        salt = (_safe_int(getattr(team, "team_id", 0), 0) + ll * 17) % 7
        if salt == 0:
            ep += 2
        elif salt == 1:
            er += 2

    return min(ep, 2), min(er, 2)


def _latest_history_rank(team: Any) -> Optional[int]:
    hist = getattr(team, "history_seasons", None)
    if not isinstance(hist, list) or not hist:
        return None
    last = hist[-1]
    if not isinstance(last, dict):
        return None
    rk = last.get("rank")
    if rk is None:
        return None
    s = str(rk).strip()
    if not s or s == "-":
        return None
    try:
        r = int(s)
    except (TypeError, ValueError):
        return None
    if 1 <= r <= 16:
        return r
    return None


def _tendency_scores(
    team: Any,
    exp: str,
    ll: int,
    wins: int,
    money: int,
) -> Tuple[int, int]:
    """軽い push / rebuild 方向スコア（差が小さいときは hold に寄せる）。"""
    push_s = 0
    reb_s = 0
    gp = _regular_games_played(team)

    wp = _current_win_pct(team)
    if wp is not None:
        if wp >= 0.62:
            push_s += 2
        elif wp >= 0.54:
            push_s += 1
        elif wp <= 0.36:
            reb_s += 2
        elif wp <= 0.44:
            reb_s += 1

    lwp = _last_season_win_pct(team)
    if lwp is not None:
        if lwp >= 0.58:
            push_s += 1
        elif lwp <= 0.40:
            reb_s += 1

    rk = _latest_history_rank(team)
    if rk is not None:
        if rk <= 3:
            push_s += 2
        elif rk <= 6:
            push_s += 1
        elif rk >= 14:
            reb_s += 2
        elif rk >= 11:
            reb_s += 1

    if money < 6_000_000:
        reb_s += 2
    elif money < 15_000_000:
        reb_s += 1
    elif money > 95_000_000:
        push_s += 1

    if exp == "promotion":
        push_s += 1
    if gp >= _MIN_REGULAR_GP_FOR_RECORD_SIGNALS:
        if ll == 1 and wins >= 12:
            push_s += 1
        if ll >= 2 and wins <= 8:
            reb_s += 1

    if gp < _MIN_REGULAR_GP_FOR_RECORD_SIGNALS:
        push_s //= 2
        reb_s //= 2

    if gp == 0:
        op, oreb = _opening_gp0_score_add(team, exp, money, ll)
        push_s += op
        reb_s += oreb

    return push_s, reb_s


def _opening_profile_strategy_hint(team: Any) -> Tuple[int, int]:
    """
    今季 GP < _MIN_REGULAR_GP_FOR_RECORD_SIGNALS のみ。
    club_profile の read-only 値から push_s / reb_s へ最大 +1 ずつ。
    （exp 由来の早期 return は _resolve_strategy_tag 側で先に処理済みの想定。）
    """
    if _regular_games_played(team) >= _MIN_REGULAR_GP_FOR_RECORD_SIGNALS:
        return 0, 0
    try:
        prof = get_club_base_profile(team)
        wn = float(prof.win_now_pressure)
        fin = float(prof.financial_power)
        yth = float(prof.youth_development_bias)
    except Exception:
        return 0, 0

    push_h = 1 if wn >= 1.04 else 0
    reb_h = 0
    if yth >= 1.04:
        reb_h = 1
    if fin <= 0.98:
        reb_h = 1
    reb_h = min(1, reb_h)

    if fin >= 1.04:
        reb_h = 0

    if push_h and reb_h:
        push_h, reb_h = 1, 0

    return push_h, reb_h


def _resolve_strategy_tag(
    team: Any,
    exp: str,
    ll: int,
    wins: int,
    money: int,
) -> str:
    if exp == "rebuild":
        return "rebuild"
    if exp in ("title_or_bust", "title_challenge"):
        return "push"

    push_s, reb_s = _tendency_scores(team, exp, ll, wins, money)

    op, oreb = _opening_profile_strategy_hint(team)
    push_s += op
    reb_s += oreb

    # 曖昧帯のみ: クラブ基礎プロファイルで最大±1（勝利圧 vs 資金力の差分）
    if -1 <= push_s - reb_s <= 1:
        try:
            prof = get_club_base_profile(team)
            net = float(prof.win_now_pressure) - float(prof.financial_power)
            if net > 0.035:
                push_s += 1
            elif net < -0.035:
                reb_s += 1
        except Exception:
            pass

    if ll == 1 and wins >= 14:
        return "push"
    if (
        ll >= 2
        and wins <= 6
        and _regular_games_played(team) >= _MIN_REGULAR_GP_FOR_RECORD_SIGNALS
    ):
        return "rebuild"
    if exp == "promotion" and ll == 3 and wins >= 9:
        return "push"

    if push_s - reb_s >= 2:
        return "push"
    if reb_s - push_s >= 2:
        return "rebuild"
    return "hold"


def get_cpu_club_strategy(team: Any, season: Optional[Any] = None) -> StrategyProfile:
    """
    既存の owner_expectation / league_level / 勝敗 / 所持金 /（取れれば）順位・前季から軽く分類する。
    season は現状未使用（呼び出し互換のため受けるのみ）。深い参照はせず、欠損時は中立。
    """
    del season
    try:
        if team is None:
            return _DEFAULT
        if bool(getattr(team, "is_user_team", False)):
            return _DEFAULT

        exp = str(getattr(team, "owner_expectation", "playoff_race") or "playoff_race").strip().lower()
        if exp not in _VALID_EXPECTATIONS:
            exp = "playoff_race"

        ll = max(1, min(3, _safe_int(getattr(team, "league_level", 2), 2)))
        wins = max(0, min(40, _safe_int(getattr(team, "regular_wins", 0), 0)))
        money = max(0, _safe_int(getattr(team, "money", 0), 0))

        tag = _resolve_strategy_tag(team, exp, ll, wins, money)

        if tag == "rebuild":
            fa_agg = 0.94
            trade_tol = 1.06
            fut_w = 1.06
        elif tag == "push":
            fa_agg = 1.06
            trade_tol = 0.94
            fut_w = 0.94
        else:
            fa_agg = 1.0
            trade_tol = 1.0
            fut_w = 1.0

        if money < 12_000_000:
            fa_agg *= 0.98
        if money < 5_000_000:
            fa_agg *= 0.98

        return StrategyProfile(
            strategy_tag=tag,
            fa_aggressiveness=round(max(0.88, min(1.12, fa_agg)), 4),
            trade_loss_tolerance=round(max(0.88, min(1.12, trade_tol)), 4),
            future_value_weight=round(max(0.88, min(1.12, fut_w)), 4),
        )
    except Exception:
        return _DEFAULT
