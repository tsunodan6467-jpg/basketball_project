"""
広報・ファン施策（週次ガード・management 永続化・局所的な money / popularity / fan_base）。

シーズン進行の「週」は Season.current_round に同期。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §2.3
"""

from __future__ import annotations

from datetime import datetime, timezone
from random import Random
from typing import Any, Dict, List, Optional, Tuple

MAX_ACTIONS_PER_ROUND = 2
MAX_HISTORY = 48

PR_CAMPAIGNS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "sns_buzz",
        "label": "SNS・話題づくり",
        "cost": 650_000,
        "popularity_delta": 1,
        "fan_base_delta": 140,
    },
    {
        "id": "community_day",
        "label": "地域コミュニティDAY",
        "cost": 1_050_000,
        "popularity_delta": 2,
        "fan_base_delta": 240,
    },
    {
        "id": "fan_festival",
        "label": "ファンフェスティバル",
        "cost": 1_650_000,
        "popularity_delta": 3,
        "fan_base_delta": 420,
    },
)

PR_CAMPAIGN_IDS = frozenset(x["id"] for x in PR_CAMPAIGNS)


def ensure_pr_campaigns_on_team(team: Any) -> None:
    if not hasattr(team, "management") or team.management is None or not isinstance(team.management, dict):
        team.management = {}
    mg = team.management
    block = mg.get("pr_campaigns")
    if not isinstance(block, dict):
        block = {}
        mg["pr_campaigns"] = block
    block.setdefault("week_key", "")
    block.setdefault("count_this_round", 0)
    hist = block.get("history")
    if not isinstance(hist, list):
        block["history"] = []


def _campaign_spec(campaign_id: str) -> Optional[Dict[str, Any]]:
    for row in PR_CAMPAIGNS:
        if row["id"] == campaign_id:
            return row
    return None


def resolve_pr_round_context(season: Any) -> Tuple[str, bool, str]:
    """
    戻り値: (week_key, 施策実行可, ユーザー向け不可理由)
    """
    if season is None:
        return ("no_season", False, "シーズン情報がないため実行できません。")
    if bool(getattr(season, "season_finished", False)):
        return ("season_finished", False, "シーズン終了後は広報施策を実行できません。")
    cr = int(getattr(season, "current_round", 0) or 0)
    if cr <= 0:
        return ("pre_round", False, "ラウンド進行が始まってから実行できます。")
    return (f"round_{cr}", True, "")


def sync_pr_round_quota(team: Any, season: Any) -> Tuple[str, bool, str]:
    """週キーが変わったら回数をリセットする。"""
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_pr_campaigns_on_team(team)
    key, allowed, reason = resolve_pr_round_context(season)
    block = team.management["pr_campaigns"]
    if block.get("week_key") != key:
        block["week_key"] = key
        block["count_this_round"] = 0
    return key, allowed, reason


def commit_pr_campaign(team: Any, campaign_id: str, season: Any) -> Tuple[bool, str]:
    if not bool(getattr(team, "is_user_team", False)):
        return False, "自チームのみ広報施策を実行できます。"
    return _commit_pr_campaign_core(team, campaign_id, season, actor="user")


def _commit_pr_campaign_core(team: Any, campaign_id: str, season: Any, *, actor: str) -> Tuple[bool, str]:
    if actor not in ("user", "cpu"):
        return False, ""
    if actor == "cpu" and bool(getattr(team, "is_user_team", False)):
        return False, ""
    cid = str(campaign_id or "").strip()
    if cid not in PR_CAMPAIGN_IDS:
        return False, "不明な施策です。"
    spec = _campaign_spec(cid)
    if spec is None:
        return False, "不明な施策です。"

    key, allowed, reason = sync_pr_round_quota(team, season)
    if not allowed:
        return False, reason

    block = team.management["pr_campaigns"]
    used = int(block.get("count_this_round", 0) or 0)
    if used >= MAX_ACTIONS_PER_ROUND:
        return (
            False,
            f"今週（ラウンド {key.replace('round_', '')}）の実行上限（{MAX_ACTIONS_PER_ROUND}回）に達しています。",
        )

    cost = int(spec["cost"])
    money = int(getattr(team, "money", 0))
    if money < cost:
        return False, f"資金が不足しています（必要 {cost:,} 円）。"

    pop_d = int(spec.get("popularity_delta", 0))
    fan_d = int(spec.get("fan_base_delta", 0))

    team.money = int(money - cost)
    team.popularity = int(max(0, min(100, int(getattr(team, "popularity", 0)) + pop_d)))
    team.fan_base = int(max(0, int(getattr(team, "fan_base", 0)) + fan_d))

    block["count_this_round"] = used + 1
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "round_key": key,
        "campaign_id": cid,
        "label": str(spec["label"]),
        "cost": cost,
        "popularity_delta": pop_d,
        "fan_base_delta": fan_d,
        "actor": actor,
    }
    hist = block["history"]
    hist.append(entry)
    while len(hist) > MAX_HISTORY:
        hist.pop(0)

    return (
        True,
        f"「{spec['label']}」を実施しました（-{cost:,} 円）。"
        f"人気 {pop_d:+}、ファン基盤 {fan_d:+}（試合収入式への本接続は後段）。",
    )


def try_cpu_pr_campaign(team: Any, season: Any, rng: Random) -> bool:
    """CPU クラブ用。低確率でランダム施策を 1 回試行。成功時 True。"""
    if bool(getattr(team, "is_user_team", False)):
        return False
    if rng.random() >= 0.068:
        return False
    cid = rng.choice([x["id"] for x in PR_CAMPAIGNS])
    ok, _ = _commit_pr_campaign_core(team, cid, season, actor="cpu")
    return ok


def format_pr_status_line(team: Any, season: Any) -> str:
    sync_pr_round_quota(team, season)
    _, allowed, reason = resolve_pr_round_context(season)
    block = team.management["pr_campaigns"]
    used = int(block.get("count_this_round", 0) or 0)
    left = max(0, MAX_ACTIONS_PER_ROUND - used)
    key = str(block.get("week_key", ""))
    round_disp = key.replace("round_", "ラウンド ") if key.startswith("round_") else key
    if not allowed:
        return f"実行不可: {reason}"
    return f"対象: {round_disp} ｜ 今週あと {left} 回まで実行可（上限 {MAX_ACTIONS_PER_ROUND} 回／ラウンド）"


def format_pr_history_lines(team: Any, *, limit: int = 10) -> List[str]:
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_pr_campaigns_on_team(team)
    hist = list(team.management["pr_campaigns"].get("history") or [])
    if not hist:
        return ["（実行履歴はまだありません）"]
    lim = max(1, int(limit))
    lines: List[str] = []
    for row in hist[-lim:]:
        if not isinstance(row, dict):
            continue
        at = str(row.get("at", ""))[:19].replace("T", " ")
        label = str(row.get("label", "-"))
        cost = row.get("cost")
        cpu_tag = "［CPU］" if str(row.get("actor", "user")) == "cpu" else ""
        if isinstance(cost, int):
            lines.append(f"- {at}  {cpu_tag}{label}  （{cost:,} 円）")
        else:
            lines.append(f"- {at}  {cpu_tag}{label}")
    return lines
