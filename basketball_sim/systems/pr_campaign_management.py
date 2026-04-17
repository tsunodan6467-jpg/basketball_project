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

# CLI 候補比較用の短文（表示のみ。cost / delta の数値ロジックは変更しない）
PR_CAMPAIGN_CLI_COMPARISON_HINTS: Dict[str, str] = {
    "sns_buzz": "低コスト即効・話題・知名度寄り",
    "community_day": "地元密着・中コストで人気とファン基盤",
    "fan_festival": "大型イベント・高コスト・集客・ファン拡大",
}


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


def can_commit_pr_campaign(team: Any, campaign_id: str, season: Any) -> Tuple[bool, str]:
    """
    広報施策の実行可否のみ（状態は変えない）。GUI プレビュー用。
    `sync_pr_round_quota` は週キー変更時に management を更新し得る（既存の format_pr_status_line と同様）。
    """
    if not bool(getattr(team, "is_user_team", False)):
        return False, "自チームのみ広報施策を実行できます。"
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
    return True, ""


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

    if actor == "user":
        ok_pre, err_pre = can_commit_pr_campaign(team, cid, season)
        if not ok_pre:
            return False, err_pre
    else:
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

    key, _, _ = sync_pr_round_quota(team, season)
    block = team.management["pr_campaigns"]
    used = int(block.get("count_this_round", 0) or 0)
    cost = int(spec["cost"])
    money = int(getattr(team, "money", 0))

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


def format_cli_pr_campaign_management_screen_lines(team: Any, season: Any) -> List[str]:
    """
    CLI 広報施策画面用（サマリー＋候補比較）。
    `format_pr_status_line` で週次枠を既存どおり同期表示する（表示目的の既存経路の再利用）。
    """
    if team is None:
        return [
            "【広報サマリー】",
            "直近施策: 情報なし",
            "実行状態: 情報なし",
            "週次情報: 情報なし",
            "履歴: 履歴なし",
            "直近更新: 情報なし",
            "",
            "【候補比較】",
            "情報なし",
            "",
        ]

    hist: List[Any] = []
    n_hist = 0
    try:
        mg = getattr(team, "management", None)
        if isinstance(mg, dict):
            block = mg.get("pr_campaigns")
            if isinstance(block, dict):
                raw_h = block.get("history")
                if isinstance(raw_h, list):
                    hist = raw_h
                    n_hist = len(hist)
    except Exception:
        hist = []
        n_hist = 0

    last_label = "未実行"
    last_update = "履歴なし"
    last_cid = ""
    if hist:
        row = hist[-1]
        if isinstance(row, dict):
            lab = str(row.get("label") or "").strip()
            last_label = lab if lab else "情報なし"
            last_cid = str(row.get("campaign_id") or "").strip()
            at = str(row.get("at") or "").strip()
            at_disp = at[:19].replace("T", " ") if at else ""
            if at_disp:
                last_update = f"{at_disp}  {last_label}"
            else:
                last_update = last_label
        else:
            last_label = "情報なし"
            last_update = "情報なし"

    hist_disp = f"{n_hist}件" if n_hist > 0 else "履歴なし"

    frame = "情報なし"
    exec_state = "情報なし"
    if season is not None:
        try:
            frame = format_pr_status_line(team, season)
            block = team.management.get("pr_campaigns")
            if isinstance(block, dict):
                used = int(block.get("count_this_round", 0) or 0)
                _, allowed, _ = resolve_pr_round_context(season)
                if not allowed:
                    exec_state = "未実行"
                elif used >= MAX_ACTIONS_PER_ROUND:
                    exec_state = f"上限到達（今週 {MAX_ACTIONS_PER_ROUND} 回消化）"
                elif used > 0:
                    exec_state = f"実行済み（今週 {used} / {MAX_ACTIONS_PER_ROUND}）"
                else:
                    exec_state = "未実行"
        except Exception:
            frame = "情報なし"
            exec_state = "情報なし"
    else:
        frame = "情報なし（シーズン未接続）"
        exec_state = "情報なし"

    lines: List[str] = [
        "【広報サマリー】",
        f"直近施策: {last_label}",
        f"実行状態: {exec_state}",
        f"週次情報: {frame}",
        f"履歴: {hist_disp}",
        f"直近更新: {last_update}",
        "",
        "【候補比較】",
    ]
    for i, spec in enumerate(PR_CAMPAIGNS, start=1):
        cid = str(spec.get("id", "") or "")
        lab = str(spec.get("label", cid) or cid)
        hint = PR_CAMPAIGN_CLI_COMPARISON_HINTS.get(cid, "情報なし")
        try:
            cost = int(spec.get("cost", 0) or 0)
            cost_s = f"{cost:,}円"
        except (TypeError, ValueError):
            cost_s = "情報なし"
        mark = "（直近）" if cid and cid == last_cid else ""
        lines.append(f"{i}. {lab}{mark}  …  {hint}（{cost_s}）")
    lines.append("")
    return lines


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
