"""
経営メニュー（GUI）用の表示スナップショット。

実行ロジックは持たず、Team / Season から読み取り可能な範囲で
財務・施設・オーナー・直近施策を1か所で整形する。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from basketball_sim.systems.finance_report_display import INSEASON_CASH_KEY_LABELS_JA
from basketball_sim.systems.facility_investment import (
    FACILITY_LABELS,
    FACILITY_MAX_LEVEL,
    FACILITY_ORDER,
    can_commit_facility_upgrade,
    get_facility_upgrade_cost,
)
from basketball_sim.systems.merchandise_management import (
    ADVANCE_COST,
    MERCH_PRODUCTS,
    PHASE_LABEL_JA,
    _next_phase,
    can_advance_merchandise_phase,
    get_merchandise_item,
)
from basketball_sim.systems.pr_campaign_management import (
    MAX_ACTIONS_PER_ROUND,
    PR_CAMPAIGNS,
    can_commit_pr_campaign,
    sync_pr_round_quota,
)
from basketball_sim.systems.salary_cap_budget import (
    get_soft_cap,
    league_level_for_team,
    payroll_exceeds_soft_cap,
)

PR_SORT_DEFAULT = "default"
PR_SORT_COST_ASC = "cost_asc"
PR_SORT_COST_DESC = "cost_desc"
PR_FILTER_ALL = "all"
PR_FILTER_EXECUTABLE = "executable"
PR_FILTER_AFFORDABLE = "affordable"
PR_FILTER_POP_HEAVY = "pop_heavy"
PR_FILTER_FAN_HEAVY = "fan_heavy"
from basketball_sim.systems.sponsor_management import (
    MAIN_SPONSOR_IDS,
    MAIN_SPONSOR_TYPES,
    format_sponsor_apply_preview_line,
)

FormatMoney = Callable[[int], str]
FormatSignedMoney = Callable[[int], str]


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _parse_iso_ts(raw: Any) -> float:
    s = str(raw or "").strip()
    if not s:
        return 0.0
    head = s[:19]
    try:
        return datetime.strptime(head, "%Y-%m-%dT%H:%M:%S").timestamp()
    except ValueError:
        return 0.0


def _sum_inseason_cash_entries(team: Any) -> int:
    raw = getattr(team, "inseason_cash_round_log", None)
    if not isinstance(raw, list):
        return 0
    total = 0
    for e in raw:
        if not isinstance(e, dict):
            continue
        total += _safe_int(e.get("amount"), 0)
    return int(total)


def _total_payroll(team: Any) -> int:
    players = getattr(team, "players", None) or []
    return int(sum(max(0, _safe_int(getattr(p, "salary", 0), 0)) for p in players))


def _mission_runtime_progress(
    team: Any, mission: Dict[str, Any]
) -> Tuple[str, Optional[float]]:
    """evaluate_owner_missions と同様の進捗表示（読み取りのみ）。"""
    tt = mission.get("target_type")
    tv_raw = mission.get("target_value", 0)
    try:
        tv = int(tv_raw)
    except (TypeError, ValueError):
        tv = 0

    latest_completed = None
    seasons = list(getattr(team, "history_seasons", []) or [])
    if seasons:
        last = seasons[-1]
        if isinstance(last, dict):
            latest_completed = last

    if latest_completed is not None:
        wins = _safe_int(
            latest_completed.get("wins", latest_completed.get("regular_wins", 0)),
            0,
        )
        rank_raw = latest_completed.get("rank")
        try:
            latest_rank = int(rank_raw) if rank_raw is not None and str(rank_raw).strip() != "" else None
        except (TypeError, ValueError):
            latest_rank = None
    else:
        wins = _safe_int(getattr(team, "regular_wins", 0), 0)
        est = getattr(team, "_estimate_latest_rank_for_owner", None)
        latest_rank = est() if callable(est) else None

    cashflow = _safe_int(getattr(team, "cashflow_last_season", 0), 0)
    payroll_now = _total_payroll(team)

    young_core = 0
    for player in getattr(team, "players", []) or []:
        if getattr(player, "is_retired", False):
            continue
        if _safe_int(getattr(player, "age", 99), 99) <= 24 and _safe_int(getattr(player, "ovr", 0), 0) >= 68:
            young_core += 1

    if tt == "wins_at_least":
        pct = min(100.0, max(0.0, (wins / max(1, tv)) * 100.0)) if tv > 0 else None
        return f"{wins}勝 / 目標{tv}勝", pct
    if tt == "rank_at_most":
        if latest_rank is None:
            return f"順位不明 / 目標{tv}位以内", None
        if latest_rank <= tv:
            return f"{latest_rank}位 / 目標{tv}位以内", 100.0
        return f"{latest_rank}位 / 目標{tv}位以内", None
    if tt == "cashflow_at_least":
        if tv <= 0:
            ok = cashflow >= tv
            return f"収支{cashflow:+,} / 目標{tv:+,}", 100.0 if ok else max(0.0, 50.0 + min(50.0, cashflow / 1_000_000))
        pct = min(100.0, max(0.0, cashflow / max(1, tv) * 100.0))
        return f"収支{cashflow:+,} / 目標{tv:+,}", pct
    if tt == "payroll_within_budget":
        cap = int(tv * 1.08) if tv > 0 else 0
        ok = payroll_now <= cap if cap > 0 else True
        pct = 100.0 if ok else max(0.0, 100.0 - (payroll_now - cap) / max(1, cap) * 40.0)
        return f"給与総額{payroll_now:,} / 目標{tv:,}＋8%以内", pct
    if tt == "young_core_count_at_least":
        pct = min(100.0, max(0.0, young_core / max(1, tv) * 100.0))
        return f"若手有望株{young_core}人 / 目標{tv}人", pct
    return "評価対象外", None


def _finance_status_and_hint(
    money: int, payroll: int, budget: int, cashflow_last: int, inseason_total: int
) -> Tuple[str, str]:
    flags: List[str] = []
    if money < 3_000_000:
        status = "危険"
        flags.append("資金が非常に薄い")
    elif money < 8_000_000 or (cashflow_last < 0 and money < 15_000_000):
        status = "注意"
        flags.append("資金に余裕が少ない、または前季赤字の影響が残る可能性")
    else:
        status = "安全"
        flags.append("資金はおおむね安全圏")

    if budget > 0 and payroll > int(budget * 1.15):
        status = "危険"
        flags.append("人件費が予算を大きく上回っている")
    elif budget > 0 and payroll > int(budget * 1.05):
        if status == "安全":
            status = "注意"
        flags.append("人件費が年俸予算をやや超過気味")

    if inseason_total <= 0:
        flags.append("シーズン中の入金記録はまだ少ない／未実行")

    hint = flags[0] if flags else "現状は大きな歪みは見えません"
    return status, hint


def _season_remaining_rounds(season: Any) -> Tuple[str, Optional[int]]:
    if season is None:
        return "未設定（シーズン情報なし）", None
    if bool(getattr(season, "season_finished", False)):
        return "シーズン終了済み（残りラウンドなし）", 0
    tr = _safe_int(getattr(season, "total_rounds", 0), 0)
    cr = _safe_int(getattr(season, "current_round", 0), 0)
    if tr <= 0:
        return "未設定", None
    left = max(0, tr - cr)
    return f"残りラウンド {left}（全{tr}）", left


def _pick_last_management_action(team: Any) -> Tuple[str, str, str]:
    """戻り値: (施策名, 結果要約, 実行タイミング表示)"""
    candidates: List[Tuple[float, int, str, str, str]] = []

    def push(ts: float, seq: int, title: str, result: str, when: str) -> None:
        candidates.append((ts, seq, title, result, when))

    seq = 0
    if hasattr(team, "_ensure_history_fields"):
        try:
            team._ensure_history_fields()
        except Exception:
            pass

    mg = getattr(team, "management", None)
    max_known_ts = 0.0
    if isinstance(mg, dict):
        pr_hist = ((mg.get("pr_campaigns") or {}).get("history")) if isinstance(mg.get("pr_campaigns"), dict) else []
        if isinstance(pr_hist, list):
            for row in pr_hist:
                if not isinstance(row, dict):
                    continue
                seq += 1
                ts = _parse_iso_ts(row.get("at"))
                if ts > 0:
                    max_known_ts = max(max_known_ts, ts)
                label = str(row.get("label", "広報施策"))
                pop_d = _safe_int(row.get("popularity_delta"), 0)
                fb_d = _safe_int(row.get("fan_base_delta"), 0)
                rk = str(row.get("round_key", ""))
                when = rk.replace("round_", "Round ") if rk.startswith("round_") else (rk or "時期未記録")
                push(ts, seq, label, f"人気 {pop_d:+} ／ ファン基盤 {fb_d:+}", when)

        sp = mg.get("sponsors")
        if isinstance(sp, dict):
            sh = sp.get("history")
            if isinstance(sh, list):
                for row in sh:
                    if not isinstance(row, dict):
                        continue
                    seq += 1
                    ts = _parse_iso_ts(row.get("at"))
                    if ts > 0:
                        max_known_ts = max(max_known_ts, ts)
                    lab = str(row.get("label", "メインスポンサー変更"))
                    b = _safe_int(row.get("sponsor_power_before"), 0)
                    a = _safe_int(row.get("sponsor_power_after"), 0)
                    push(ts, seq, "スポンサー契約", f"スポンサー力 {b} → {a}", "契約反映時")

        mer = mg.get("merchandise")
        if isinstance(mer, dict):
            mh = mer.get("history")
            if isinstance(mh, list):
                for row in mh:
                    if not isinstance(row, dict):
                        continue
                    seq += 1
                    ts = _parse_iso_ts(row.get("at"))
                    if ts > 0:
                        max_known_ts = max(max_known_ts, ts)
                    name = str(row.get("name", "グッズ"))
                    to_ph = PHASE_LABEL_JA.get(str(row.get("to_phase", "")), str(row.get("to_phase", "")))
                    cost = _safe_int(row.get("cost"), 0)
                    push(ts, seq, f"グッズ開発（{name}）", f"工程進行 → {to_ph}（-{cost:,} 円）", "開発実行時")

    fin_hist = list(getattr(team, "finance_history", None) or [])
    base_ts = max_known_ts if max_known_ts > 0 else 0.0
    for i, e in enumerate(fin_hist):
        if not isinstance(e, dict):
            continue
        note = str(e.get("note", "") or "")
        if "facility_upgrade:" in note:
            seq += 1
            ts = base_ts + float(i + 1) * 1e-3
            parts = note.split(":")
            if len(parts) >= 3:
                fk = parts[1]
                lv_part = parts[2] if len(parts) > 2 else ""
                flab = FACILITY_LABELS.get(fk, fk)
                short = f"{flab} を {lv_part} に更新"
            else:
                short = note
            if len(short) > 88:
                short = short[:85] + "…"
            push(ts, seq, "施設強化", short, "投資実行時")

    if not candidates:
        return "履歴なし", "未実行", "—"

    candidates.sort(key=lambda t: (t[0], t[1]))
    _, _, title, result, when = candidates[-1]
    return title, result, when


def _truncate_reason(msg: str, limit: int = 40) -> str:
    s = str(msg or "").strip()
    if not s:
        return "実行不可"
    return s if len(s) <= limit else s[: max(1, limit - 1)] + "…"


def _facility_upgrade_effect_hint(facility_key: str) -> str:
    if facility_key == "arena_level":
        return "人気・ファン基盤がやや上がる見込み"
    if facility_key == "training_facility_level":
        return "人気がやや上がる見込み"
    if facility_key == "medical_facility_level":
        return "人気がやや上がる見込み（詳細は試合・選手側ロジックで反映）"
    if facility_key == "front_office_level":
        return "スカウト水準が上がる見込み"
    return "関連指標が更新される見込み"


def build_facility_action_preview_lines(
    team: Any,
    *,
    format_money: FormatMoney,
) -> Tuple[Tuple[str, str], ...]:
    """(facility_key, 1行プレビュー) を FACILITY_ORDER 順で。"""
    if team is None:
        return tuple((fk, "未設定（チーム未接続）／実行不可") for fk in FACILITY_ORDER)
    rows: List[Tuple[str, str]] = []
    for fk in FACILITY_ORDER:
        flab = FACILITY_LABELS.get(fk, fk)
        if not bool(getattr(team, "is_user_team", False)):
            rows.append((fk, f"{flab}: 自チームのみ／実行不可"))
            continue
        lv = _safe_int(getattr(team, fk, 1), 1)
        if lv >= FACILITY_MAX_LEVEL:
            rows.append((fk, f"{flab}: 既に最大レベル／実行不可"))
            continue
        cost = int(get_facility_upgrade_cost(team, fk))
        ok, msg = can_commit_facility_upgrade(team, fk)
        hint = _facility_upgrade_effect_hint(fk)
        tail = "実行可" if ok else _truncate_reason(msg)
        rows.append(
            (
                fk,
                f"{flab}: {format_money(cost)}でLv{lv}→Lv{lv + 1}（{hint}）／{tail}",
            )
        )
    return tuple(rows)


def count_executable_pr_campaigns(team: Any, season: Any) -> int:
    """`PR_CAMPAIGNS` について `can_commit_pr_campaign` が True になる件数（フィルタなし）。"""
    if team is None or not PR_CAMPAIGNS:
        return 0
    n = 0
    for spec in PR_CAMPAIGNS:
        ok, _ = can_commit_pr_campaign(team, str(spec["id"]), season)
        if ok:
            n += 1
    return int(n)


def build_pr_dashboard_summary_line(team: Any, season: Any) -> str:
    """
    現況ダッシュボード用の広報要約 1 行（残り枠 + 実行可候補数）。
    `sync_pr_round_quota` / `MAX_ACTIONS_PER_ROUND` / `can_commit_pr_campaign` を再利用。
    """
    if team is None:
        return "■ 広報: チーム未接続"
    if not PR_CAMPAIGNS:
        return "■ 広報: 広報未設定（候補がありません）"
    _key, _allowed, _reason = sync_pr_round_quota(team, season)
    block = team.management.get("pr_campaigns") if isinstance(getattr(team, "management", None), dict) else None
    used = _safe_int((block or {}).get("count_this_round", 0), 0)
    cap = int(MAX_ACTIONS_PER_ROUND)
    left = max(0, cap - used)
    exec_n = count_executable_pr_campaigns(team, season)
    return f"■ 広報: 今ラウンド残り {left} / {cap} 回・実行可候補 {exec_n} 件"


def build_pr_affordance_summary_line(team: Any, season: Any) -> str:
    """
    財務ブロック直下用: 所持金と最安広報コストの距離感（`PR_CAMPAIGNS` の cost と `can_commit` 前提の枠のみ再利用）。
    """
    prefix = "広報余力:"
    if team is None:
        return f"{prefix} チーム未接続"
    if not PR_CAMPAIGNS:
        return f"{prefix} 広報候補なし"
    if not bool(getattr(team, "is_user_team", False)):
        return f"{prefix} 今は広報不可"
    _money_sentinel = object()
    raw_m = getattr(team, "money", _money_sentinel)
    if raw_m is _money_sentinel or raw_m is None:
        return f"{prefix} 所持金不明"
    money = _safe_int(raw_m, 0)

    _key, allowed, _reason = sync_pr_round_quota(team, season)
    if not allowed:
        return f"{prefix} 今は広報不可"
    block = team.management.get("pr_campaigns") if isinstance(getattr(team, "management", None), dict) else None
    used = _safe_int((block or {}).get("count_this_round", 0), 0)
    if used >= int(MAX_ACTIONS_PER_ROUND):
        return f"{prefix} 今は広報不可"

    min_cost = min(int(spec["cost"]) for spec in PR_CAMPAIGNS)
    margin = money - min_cost
    if margin < 0:
        return f"{prefix} 最安広報でも厳しい"
    if margin == 0:
        return f"{prefix} 最安広報でもぎりぎり"
    if margin < 200_000:
        return f"{prefix} 最安広報でもぎりぎり"
    if margin >= min_cost:
        return f"{prefix} 最安広報なら余裕あり"
    return f"{prefix} 最安広報なら実行可能"


def build_sponsor_affordance_summary_line(
    team: Any, selected_sponsor_type_id: Optional[str]
) -> str:
    """
    財務ブロック付近用: スポンサー申込／更新の余力を1行で示す。
    `format_sponsor_apply_preview_line` の文言を短く要約する（新規コスト式は持たない）。
    """
    prefix = "スポンサー余力:"
    if not MAIN_SPONSOR_TYPES:
        return f"{prefix} スポンサー候補なし"
    if team is None:
        return f"{prefix} チーム未接続"

    tid = str(selected_sponsor_type_id or "").strip()
    if not tid:
        mg = getattr(team, "management", None)
        if isinstance(mg, dict):
            sp_blk = mg.get("sponsors")
            if isinstance(sp_blk, dict):
                tid = str(sp_blk.get("main_contract_type") or "").strip()
        if not tid:
            tid = "standard"
    if tid not in MAIN_SPONSOR_IDS:
        return f"{prefix} スポンサー候補なし"

    _ms = object()
    raw_m = getattr(team, "money", _ms)
    if raw_m is _ms or raw_m is None:
        return f"{prefix} 所持金不明"

    if not bool(getattr(team, "is_user_team", False)):
        return f"{prefix} 今は変更不可"

    preview = format_sponsor_apply_preview_line(team, tid)
    if "未設定（チーム未接続）" in preview:
        return f"{prefix} チーム未接続"
    if "自チームのみ" in preview:
        return f"{prefix} 今は変更不可"
    if "契約種別が未設定" in preview:
        return f"{prefix} スポンサー候補なし"
    if "実行不可" in preview:
        return f"{prefix} 条件未達で今は変更不可"
    if "効果なし" in preview or "変更なし" in preview:
        return f"{prefix} 申込コストなし・今は変更を急がなくてよい"
    if "切替想定" in preview and "実行可" in preview:
        return f"{prefix} 申込コストなし・切替を検討可"
    if "実行可" in preview:
        return f"{prefix} 申込コストなし・切替を検討可"
    return f"{prefix} 申込コストなし・プレビューで要確認"


def build_pr_round_remaining_summary(team: Any, season: Any) -> str:
    """
    今ラウンドの広報実行枠（`sync_pr_round_quota` / MAX_ACTIONS_PER_ROUND）を 1 行で示す。
    """
    if team is None:
        return "広報（今ラウンド）: チーム未接続のため未設定"
    key, allowed, reason = sync_pr_round_quota(team, season)
    block = team.management.get("pr_campaigns") if isinstance(getattr(team, "management", None), dict) else None
    used = _safe_int((block or {}).get("count_this_round", 0), 0)
    cap = int(MAX_ACTIONS_PER_ROUND)
    left = max(0, cap - used)
    rnd_disp = str(key).replace("round_", "R") if str(key).startswith("round_") else str(key)
    if not allowed:
        return (
            f"広報（今ラウンド）: 実行不可 — {_truncate_reason(reason)}"
            f"（枠の目安: 残り {left} / {cap} 回・使用 {used}）"
        )
    return (
        f"広報（今ラウンド）: 残り {left} / {cap} 回（使用 {used} 回・キー {rnd_disp}）"
    )


def build_pr_campaign_comparison_entries(
    team: Any,
    season: Any,
    format_money: FormatMoney,
    *,
    sort_mode: str = PR_SORT_DEFAULT,
    filter_mode: str = PR_FILTER_ALL,
) -> Tuple[Tuple[str, str], ...]:
    """
    比較用の (campaign_id, 1行表示) 。実行不可も行に含める（フィルタで絞る場合を除く）。
    該当ゼロ時はプレースホルダ 1 行（id は空文字）。
    """
    money = _safe_int(getattr(team, "money", 0), 0) if team is not None else 0
    raw_rows: List[Tuple[str, str, int, int]] = []

    for def_i, spec in enumerate(PR_CAMPAIGNS):
        cid = str(spec["id"])
        label = str(spec["label"])
        cost = int(spec["cost"])
        pop_d = int(spec.get("popularity_delta", 0))
        fan_d = int(spec.get("fan_base_delta", 0))
        if team is None:
            ok = False
            reason = "チーム未接続"
        else:
            ok, reason = can_commit_pr_campaign(team, cid, season)
        status = "実行可" if ok else _truncate_reason(reason)
        line = f"{label} ｜ {format_money(cost)} ｜ 人気{pop_d:+} ファン{fan_d:+} ｜ {status}"

        if filter_mode == PR_FILTER_EXECUTABLE and not ok:
            continue
        if filter_mode == PR_FILTER_AFFORDABLE and cost > money:
            continue
        if filter_mode == PR_FILTER_POP_HEAVY and pop_d < 2:
            continue
        if filter_mode == PR_FILTER_FAN_HEAVY and fan_d < 240:
            continue
        raw_rows.append((cid, line, cost, def_i))

    if sort_mode == PR_SORT_COST_ASC:
        raw_rows.sort(key=lambda r: (r[2], r[3]))
    elif sort_mode == PR_SORT_COST_DESC:
        raw_rows.sort(key=lambda r: (-r[2], r[3]))
    else:
        raw_rows.sort(key=lambda r: r[3])

    if not raw_rows:
        return (
            (
                "",
                "（該当する施策がありません。フィルタを「すべて」等に変えてください）",
            ),
        )
    return tuple((cid, line) for cid, line, _c, _d in raw_rows)


def build_pr_selection_preview_line(
    team: Any,
    season: Any,
    campaign_id: Optional[str],
    *,
    format_money: FormatMoney,
) -> str:
    if not campaign_id or not str(campaign_id).strip():
        return "広報: 施策が未選択／未設定"
    cid = str(campaign_id).strip()
    spec = next((x for x in PR_CAMPAIGNS if x["id"] == cid), None)
    if spec is None:
        return "広報: 不明な施策／未設定"
    cost = int(spec["cost"])
    pop_d = int(spec.get("popularity_delta", 0))
    fan_d = int(spec.get("fan_base_delta", 0))
    label = str(spec.get("label", cid))
    if team is None:
        return f"広報「{label}」: {format_money(cost)}で人気{pop_d:+}・ファン{fan_d:+}見込み／未設定"
    ok, reason = can_commit_pr_campaign(team, cid, season)
    base = f"広報「{label}」: {format_money(cost)}で人気{pop_d:+}・ファン基盤{fan_d:+}見込み"
    if ok:
        return f"{base}／実行可"
    return f"{base}／{_truncate_reason(reason)}"


def build_merchandise_line_previews(
    team: Any,
    *,
    format_money: FormatMoney,
) -> Tuple[Tuple[str, str], ...]:
    """(product_id, 1行プレビュー)"""
    out: List[Tuple[str, str]] = []
    for tmpl in MERCH_PRODUCTS:
        pid = str(tmpl["id"])
        name = str(tmpl.get("name", pid))
        if team is None:
            out.append((pid, f"「{name}」: 未設定（チーム未接続）／実行不可"))
            continue
        if not bool(getattr(team, "is_user_team", False)):
            out.append((pid, f"「{name}」: 自チームのみ／実行不可"))
            continue
        item = get_merchandise_item(team, pid)
        if item is None:
            out.append((pid, f"「{name}」: データ未取得／実行不可"))
            continue
        phase = str(item.get("phase", "concept"))
        if phase == "on_sale":
            out.append((pid, f"「{name}」: 発売中／追加の開発工程なし"))
            continue
        nxt = _next_phase(phase)
        if nxt is None:
            out.append((pid, f"「{name}」: これ以上進められません／実行不可"))
            continue
        cost = int(ADVANCE_COST.get(phase, 0) or 0)
        next_lab = PHASE_LABEL_JA.get(nxt, nxt)
        ok, reason = can_advance_merchandise_phase(team, pid)
        base = f"「{name}」: {format_money(cost)}で→{next_lab}（年次グッズ収入内訳の改善が見込まれる）"
        if ok:
            out.append((pid, f"{base}／実行可"))
        else:
            out.append((pid, f"{base}／{_truncate_reason(reason)}"))
    return tuple(out)


def build_merchandise_affordance_summary_line(team: Any, *, format_money: FormatMoney) -> str:
    """
    財務ブロック付近用: 全商品ラインのうち「次工程」が最も安い候補を代表に、
    `ADVANCE_COST` / `can_advance_merchandise_phase` / `get_merchandise_item` を再利用して1行に要約。
    """
    prefix = "グッズ余力:"
    if not MERCH_PRODUCTS:
        return f"{prefix} 商品未設定"
    if team is None:
        return f"{prefix} チーム未接続"
    if not bool(getattr(team, "is_user_team", False)):
        return f"{prefix} 今は進行不可"

    _ms = object()
    raw_m = getattr(team, "money", _ms)
    if raw_m is _ms or raw_m is None:
        return f"{prefix} 所持金不明"
    money = _safe_int(raw_m, 0)

    candidates: List[Tuple[int, bool]] = []
    all_on_sale = True

    for tmpl in MERCH_PRODUCTS:
        pid = str(tmpl["id"])
        item = get_merchandise_item(team, pid)
        if item is None:
            return f"{prefix} 商品未設定"
        phase = str(item.get("phase", "concept"))
        if phase == "on_sale":
            continue
        all_on_sale = False
        nxt = _next_phase(phase)
        if nxt is None:
            continue
        cost = int(ADVANCE_COST.get(phase, 0) or 0)
        ok, _reason = can_advance_merchandise_phase(team, pid)
        candidates.append((cost, ok))

    if not candidates:
        if all_on_sale:
            return f"{prefix} 発売中のため追加工程なし"
        return f"{prefix} 今は進行不可"

    costs_ok = [c for c, ok in candidates if ok]
    if costs_ok:
        min_ok = min(costs_ok)
        margin = money - min_ok
        disp = format_money(min_ok)
        if margin == 0 or margin < 200_000:
            return f"{prefix} 次工程 {disp}・ぎりぎり"
        if margin >= min_ok:
            return f"{prefix} 次工程 {disp}・今なら進行可"
        return f"{prefix} 次工程 {disp}・今なら進行可"

    min_block = min(c for c, _ in candidates)
    margin = money - min_block
    disp = format_money(min_block)
    if margin < 0:
        return f"{prefix} 次工程 {disp}・今は厳しい"
    if margin == 0 or margin < 200_000:
        return f"{prefix} 次工程 {disp}・ぎりぎり"
    return f"{prefix} 次工程 {disp}・今は進行不可"


def build_facility_affordance_summary_line(team: Any, *, format_money: FormatMoney) -> str:
    """
    財務ブロック付近用: 未最大の施設のうち最安アップグレードを代表に、
    `get_facility_upgrade_cost` / `can_commit_facility_upgrade` を再利用して1行に要約。
    """
    prefix = "施設余力:"
    if not FACILITY_ORDER:
        return f"{prefix} 投資先なし"
    if team is None:
        return f"{prefix} チーム未接続"
    if not bool(getattr(team, "is_user_team", False)):
        return f"{prefix} 今は投資不可"

    _ms = object()
    raw_m = getattr(team, "money", _ms)
    if raw_m is _ms or raw_m is None:
        return f"{prefix} 所持金不明"
    money = _safe_int(raw_m, 0)

    candidates: List[Tuple[int, bool]] = []
    for fk in FACILITY_ORDER:
        lv = _safe_int(getattr(team, fk, 1), 1)
        if lv >= FACILITY_MAX_LEVEL:
            continue
        cost = int(get_facility_upgrade_cost(team, fk))
        ok, _msg = can_commit_facility_upgrade(team, fk)
        candidates.append((cost, ok))

    if not candidates:
        return f"{prefix} 全施設が最大レベル"

    costs_ok = [c for c, ok in candidates if ok]
    if costs_ok:
        min_ok = min(costs_ok)
        margin = money - min_ok
        disp = format_money(min_ok)
        if margin == 0 or margin < 200_000:
            return f"{prefix} 最安アップグレード {disp}・ぎりぎり"
        if margin >= min_ok:
            return f"{prefix} 最安アップグレード {disp}・今なら投資可"
        return f"{prefix} 最安アップグレード {disp}・今なら投資可"

    min_block = min(c for c, _ in candidates)
    margin = money - min_block
    disp = format_money(min_block)
    if margin < 0:
        return f"{prefix} 最安アップグレード {disp}・今は厳しい"
    if margin == 0 or margin < 200_000:
        return f"{prefix} 最安アップグレード {disp}・ぎりぎり"
    return f"{prefix} 最安アップグレード {disp}・今は投資不可"


def build_action_affordance_summary_line(
    team: Any,
    *,
    pr_executable_count: int,
    sponsor_affordance_summary: str,
    merch_affordance_summary: str,
    facility_affordance_summary: str,
) -> str:
    """
    財務ブロック先頭の総括1行。
    `count_executable_pr_campaigns` と各 affordance 行の文言から実行余地を数えるだけ（新規 can 判定なし）。
    """
    prefix = "総合アクション余力:"
    if team is None:
        return f"{prefix} チーム未接続"
    pr_n = max(0, int(pr_executable_count))
    sp_n = 1 if "切替を検討可" in sponsor_affordance_summary else 0
    merch_n = 1 if (
        "今なら進行可" in merch_affordance_summary or "ぎりぎり" in merch_affordance_summary
    ) else 0
    fac_n = 1 if (
        "今なら投資可" in facility_affordance_summary or "ぎりぎり" in facility_affordance_summary
    ) else 0

    parts: List[str] = []
    if pr_n > 0:
        parts.append(f"広報{pr_n}件")
    if sp_n:
        parts.append("スポンサー1件")
    if merch_n:
        parts.append("グッズ1件")
    if fac_n:
        parts.append("施設1件")

    if not parts:
        return f"{prefix} いま資金を動かせる候補なし"
    return f"{prefix} " + "・".join(parts)


def build_owner_action_guidance_summary_line(
    team: Any,
    *,
    finance_status: str,
    owner_danger: str,
    remaining_rounds: Optional[int],
    has_mission: bool,
    mission_pct: Optional[float],
    action_affordance_summary: str,
) -> str:
    """
    オーナー危険度・残りラウンド・財務状態・総合アクション余力から行動の向きを1行で示す（ルールベース・既存値のみ）。
    """
    prefix = "行動判断:"
    if team is None:
        return f"{prefix} チーム未接続"
    if not has_mission:
        return f"{prefix} ミッション情報なし"

    action_has_room = "いま資金を動かせる候補なし" not in action_affordance_summary

    urgent_owner = (
        ("危険" in owner_danger or "やや危険" in owner_danger)
        and remaining_rounds is not None
        and 0 < remaining_rounds <= 14
    )
    urgent_pct = (
        mission_pct is not None
        and mission_pct < 38.0
        and remaining_rounds is not None
        and 0 < remaining_rounds < 12
    )
    if urgent_owner or urgent_pct:
        return f"{prefix} オーナー要求未達リスクを踏まえ、短期施策を急ぎたい"

    if finance_status == "危険":
        return f"{prefix} いまは資金温存を優先したい"

    if finance_status == "安全" and (
        "注意" in owner_danger or "やや危険" in owner_danger
    ) and action_has_room:
        return f"{prefix} ミッション達成へ投資余地あり"

    if finance_status == "安全" and owner_danger == "おおむね安全":
        return f"{prefix} いまは大きな支出を急がなくてよい"

    if remaining_rounds is not None and remaining_rounds <= 0:
        return f"{prefix} いまは状況確認を優先したい"

    if not action_has_room:
        return f"{prefix} いまは状況確認を優先したい"

    return f"{prefix} 判定材料不足"


def build_finance_pressure_summary_line(
    team: Any,
    *,
    finance_status: str,
    payroll: int,
    budget: int,
    cashflow_last: int,
    inseason_total: int,
) -> str:
    """
    財務 status・前季収支・人件費／年俸予算・リーグ上限（ソフトキャップ）との距離を1行に要約。
    `salary_cap_budget` の既存閾値のみ使用（新しい会計ルールは持たない）。
    """
    prefix = "財務圧力:"
    if team is None:
        return f"{prefix} チーム未接続"

    try:
        ll = league_level_for_team(team)
        soft = int(get_soft_cap(league_level=ll))
    except Exception:
        return f"{prefix} 判定材料不足"

    if soft <= 0:
        return f"{prefix} 判定材料不足"

    pay_i = _safe_int(payroll, 0)
    bud_i = _safe_int(budget, 0)
    cf = int(cashflow_last)
    room = max(0, soft - pay_i)
    room_ratio = float(room) / float(soft) if soft > 0 else 0.0

    over_cap = payroll_exceeds_soft_cap(pay_i, league_level=ll)
    cap_near = over_cap or room_ratio < 0.08
    cap_ok = (not over_cap) and room_ratio >= 0.12

    payroll_heavy = bud_i > 0 and pay_i > int(bud_i * 1.08)

    if cf > 0:
        flow = "plus"
    elif cf < 0:
        flow = "minus"
    else:
        flow = "flat"

    if over_cap:
        return f"{prefix} キャップ接近・大きな追加支出は注意"

    if finance_status == "危険" and flow == "minus" and (payroll_heavy or (bud_i > 0 and pay_i > bud_i)):
        return f"{prefix} 赤字傾向・人件費が重い"

    if cap_near and finance_status in ("注意", "危険"):
        return f"{prefix} キャップ接近・大きな追加支出は注意"

    if finance_status == "注意" and flow == "flat" and (not cap_ok or room_ratio < 0.12):
        return f"{prefix} 今季収支は拮抗・補強余地は小さい"

    if finance_status == "安全" and cap_ok:
        if flow == "plus" or inseason_total > 0:
            return f"{prefix} 今季黒字寄り・キャップ余力あり"
        return f"{prefix} キャップ余力あり・収支は要チェック"

    if cap_near:
        return f"{prefix} キャップ接近・大きな追加支出は注意"

    if finance_status == "危険":
        return f"{prefix} いまは状況確認を優先"

    return f"{prefix} 判定材料不足"


def build_payroll_capacity_summary_line(team: Any, *, roster_pay: Optional[int] = None) -> str:
    """
    現ロスター年俸合計と `payroll_budget`（優先）／`soft_cap` に対する距離感を1行で示す。
    `roster_pay` を渡せばロスター年俸の再集計を省略できる。
    """
    prefix = "年俸枠メモ:"
    if team is None:
        return f"{prefix} チーム未接続"
    pls = getattr(team, "players", None)
    if not isinstance(pls, list):
        return f"{prefix} ロスター情報なし"
    if len(pls) == 0:
        return f"{prefix} ロスター情報なし"
    if roster_pay is None:
        roster_pay = _total_payroll(team)
    else:
        roster_pay = int(roster_pay)
    ref = _reference_budget_for_finance_relative(team)
    if not ref:
        return f"{prefix} 判定材料不足"
    try:
        ll = league_level_for_team(team)
        if payroll_exceeds_soft_cap(roster_pay, league_level=ll):
            return f"{prefix} キャップ近辺で注意"
    except Exception:
        pass
    try:
        ratio = float(roster_pay) / float(ref)
    except Exception:
        return f"{prefix} 判定材料不足"
    if ratio >= 0.97:
        return f"{prefix} 予算近辺で圧迫（大型追加は注意）"
    if ratio >= 0.78:
        return f"{prefix} 予算比でやや重い"
    return f"{prefix} 予算に余裕あり（補強余地あり）"


# ソフトキャップに対する「余白」帯（`room / soft_cap`、ダッシュ用の固定閾値）
_SOFT_CAP_HEADROOM_TIGHT_FRAC = 0.05
_SOFT_CAP_HEADROOM_MODERATE_FRAC = 0.18


def build_soft_cap_headroom_summary_line(team: Any, *, roster_pay: Optional[int] = None) -> str:
    """
    現ロスター年俸とソフトキャップの距離感を1語で示す（金額は出さない）。
    `roster_pay` を渡せば `build_payroll_capacity_summary_line` と同じ集計値を使える。
    """
    prefix = "キャップ余白:"
    if team is None:
        return f"{prefix} チーム未接続"
    pls = getattr(team, "players", None)
    if not isinstance(pls, list):
        return f"{prefix} ロスター情報なし"
    if len(pls) == 0:
        return f"{prefix} ロスター情報なし"
    if roster_pay is None:
        roster_pay_i = _total_payroll(team)
    else:
        roster_pay_i = int(roster_pay)
    try:
        ll = league_level_for_team(team)
        cap = int(get_soft_cap(league_level=ll))
    except Exception:
        return f"{prefix} 判定材料不足"
    if cap <= 0:
        return f"{prefix} 判定材料不足"
    try:
        if payroll_exceeds_soft_cap(roster_pay_i, league_level=ll):
            return f"{prefix} 超過中"
    except Exception:
        return f"{prefix} 判定材料不足"
    room = cap - roster_pay_i
    if room <= 0:
        return f"{prefix} 超過中"
    frac = float(room) / float(cap)
    if frac <= _SOFT_CAP_HEADROOM_TIGHT_FRAC:
        return f"{prefix} ほぼなし"
    if frac <= _SOFT_CAP_HEADROOM_MODERATE_FRAC:
        return f"{prefix} ややあり"
    return f"{prefix} あり"


# 年俸本文と `[cap…]` の間を少し広げる（全角1字・装飾なし）
_PAYROLL_CAP_ALIGN_TAG_GAP = "\u3000"


def _payroll_capacity_cap_align_suffix(payroll_summary: str, cap_headroom_summary: str) -> str:
    """`年俸枠メモ` と `キャップ余白` の読みがズレるときだけ、年俸側に短い補助タグを付ける。"""
    pfx_pay = "年俸枠メモ:"
    pfx_cap = "キャップ余白:"
    if not str(payroll_summary).startswith(pfx_pay) or not str(cap_headroom_summary).startswith(pfx_cap):
        return ""
    body_pay = str(payroll_summary)[len(pfx_pay) :].strip()
    body_cap = str(cap_headroom_summary)[len(pfx_cap) :].strip()
    if not body_pay or not body_cap:
        return ""
    loose_budget = "予算に余裕あり" in body_pay
    tight_budget = ("予算比でやや重い" in body_pay) or ("予算近辺で圧迫" in body_pay)
    cap_tight = body_cap in ("ほぼなし", "超過中")
    cap_loose = body_cap == "あり"
    if loose_budget and cap_tight:
        return f"{_PAYROLL_CAP_ALIGN_TAG_GAP}[cap注意]"
    if tight_budget and cap_loose:
        return f"{_PAYROLL_CAP_ALIGN_TAG_GAP}[cap余白]"
    return ""


# 「■ 財務」〜余力行までのダッシュ表示用（本文ロジックは変えず、長い行だけ見た目を短縮）
_FINANCE_DASHBOARD_LINE_MAX_CHARS = 72


def _clamp_finance_dashboard_line(line: str, max_len: int = _FINANCE_DASHBOARD_LINE_MAX_CHARS) -> str:
    """財務ブロック向けに1行を表示長で切り詰める（`dashboard_text` 用）。"""
    s = str(line or "")
    if len(s) <= max_len:
        return s
    return s[: max(1, max_len - 1)].rstrip() + "…"


def _build_dashboard_finance_lines(
    fin_lines: Sequence[str],
    action_line: str,
    owner_guid_line: str,
    finance_pressure_line: str,
    payroll_capacity_line: str,
    soft_cap_headroom_line: str,
    round_cash_line: str,
    finance_history_note_line: str,
    pr_afford_line: str,
    sponsor_afford_line: str,
    merch_afford_line: str,
    facility_afford_line: str,
) -> Tuple[str, ...]:
    """「■ 財務」直下〜余力行まで、clamp 済みの表示行を表示順でまとめる。"""
    fcd = _clamp_finance_dashboard_line
    rows: List[str] = [fcd(x) for x in fin_lines]
    rows.extend(
        [
            fcd(action_line),
            fcd(owner_guid_line),
            fcd(finance_pressure_line),
            fcd(payroll_capacity_line),
            fcd(soft_cap_headroom_line),
            fcd(round_cash_line),
            fcd(finance_history_note_line),
            fcd(pr_afford_line),
            fcd(sponsor_afford_line),
            fcd(merch_afford_line),
            fcd(facility_afford_line),
        ]
    )
    return tuple(rows)


def build_round_cash_memo_summary_line(
    team: Any,
    season: Any,
    *,
    format_signed_money: FormatSignedMoney,
) -> str:
    """
    `inseason_cash_round_log` のうち、シーズン `current_round` に紐づく記録を要約（キーは `INSEASON_CASH_KEY_LABELS_JA`）。
    シーズン未設定時はログ上の最大ラウンドを「直近」とみなす。
    """
    prefix = "今ラウンド収支メモ:"
    if team is None:
        return f"{prefix} チーム未接続"

    raw = getattr(team, "inseason_cash_round_log", None)
    if not isinstance(raw, list):
        return f"{prefix} 判定材料不足"

    parsed: List[Tuple[int, int, str]] = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        try:
            rn = int(e.get("round_number", -1))
            amt = int(e.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if rn < 0:
            continue
        k = str(e.get("key", "") or "")
        parsed.append((rn, amt, k))

    if not parsed:
        return f"{prefix} 直近記録なし"

    target_rn: Optional[int] = None
    if season is not None and not bool(getattr(season, "season_finished", False)):
        cr = _safe_int(getattr(season, "current_round", 0), 0)
        if cr > 0:
            target_rn = cr
    if target_rn is None:
        target_rn = max(rn for rn, _, __ in parsed)

    rows = [(amt, k) for rn, amt, k in parsed if rn == target_rn]
    if not rows:
        return f"{prefix} 直近記録なし"

    def _label_for_key(k: str) -> str:
        return INSEASON_CASH_KEY_LABELS_JA.get(k, "その他")

    pos_sum = sum(a for a, _ in rows if a > 0)
    neg_sum = sum(a for a, _ in rows if a < 0)
    total = sum(a for a, _ in rows)
    n = len(rows)

    if n > 3:
        if pos_sum > 0 and pos_sum >= abs(neg_sum) * 2:
            return f"{prefix} 収入超過"
        if neg_sum < 0 and abs(neg_sum) >= max(1, pos_sum) * 2:
            return f"{prefix} 支出超過"
        if total > 0:
            return f"{prefix} 小幅黒字"
        if total < 0:
            return f"{prefix} 小幅赤字"
        return f"{prefix} 拮抗気味"

    ordered = sorted(rows, key=lambda x: -abs(x[0]))
    parts: List[str] = []
    for amt, k in ordered[:2]:
        parts.append(f"{_label_for_key(k)} {format_signed_money(amt)}")
    body = " / ".join(parts)
    if n > 2:
        body += " ほか"
    return f"{prefix} {body}"


def _summarize_finance_history_note_body(note: str) -> str:
    """`finance_history` 1件の note をダッシュ用に短くする（意味を変えない範囲でラベル化）。"""
    raw = str(note or "").strip()
    if not raw:
        return ""
    rl = raw.lower()
    if "facility_upgrade:" in raw:
        return "施設投資を実施"
    if raw.startswith("Wins:") or "/ Payroll:" in raw:
        return "前季の財務締めを記録"
    if "pr_campaign" in rl or "広報" in raw:
        return "広報施策を実行"
    if "merch" in rl or "グッズ" in raw:
        return "グッズ工程を進行"
    if "sponsor" in rl or "スポンサー" in raw:
        return "スポンサー更新"
    if (
        "contract" in rl
        or "契約" in raw
        or "free_agent" in rl
        or "fa_" in rl
        or ("payroll" in rl and "/ payroll:" not in rl)
    ):
        return "契約関連の支出あり"
    cleaned = raw.replace("\n", " ").replace("\r", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    max_len = 36
    if len(cleaned) > max_len:
        return cleaned[: max(1, max_len - 1)].rstrip() + "…"
    return cleaned


def _finance_history_cashflow_sign(entry: dict) -> str:
    """`finance_history` 1行の収支向きを `(+)` / `(-)` / `(±0)` / `(?)` で返す。"""
    if "cashflow" in entry:
        raw = entry.get("cashflow")
        if raw is not None:
            try:
                cf = int(raw)
            except (TypeError, ValueError):
                return "(?)"
            if cf > 0:
                return "(+)"
            if cf < 0:
                return "(-)"
            return "(±0)"
    try:
        r = int(entry.get("revenue", 0) or 0)
        ex = int(entry.get("expense", 0) or 0)
        cf = r - ex
    except (TypeError, ValueError):
        return "(?)"
    if cf > 0:
        return "(+)"
    if cf < 0:
        return "(-)"
    return "(±0)"


def _finance_history_season_label_suffix(entry: dict) -> str:
    """`season_label` があるときだけ ` [ラベル]` を返す（長い場合は短くする）。"""
    if "season_label" not in entry:
        return ""
    raw = entry.get("season_label")
    if raw is None:
        return ""
    lab = str(raw).strip().replace("\n", " ").replace("\r", " ")
    while "  " in lab:
        lab = lab.replace("  ", " ")
    if not lab:
        return ""
    lab = lab.replace("[", "").replace("]", "")
    if not lab:
        return ""
    max_inner = 10
    if len(lab) > max_inner:
        lab = lab[: max(1, max_inner - 1)].rstrip() + "…"
    return f" [{lab}]"


# `ending_money` から残高感だけ出す（金額は出さない）。閾値はダッシュ用の単純帯。
_FINANCE_ENDING_MONEY_BAND_FULL = 350_000_000
_FINANCE_ENDING_MONEY_BAND_FAT = 150_000_000
_FINANCE_ENDING_MONEY_BAND_WARN = 50_000_000
# `ending_money / reference_budget` の相対帯（ダッシュ用の固定閾値）
_FINANCE_REL_RATIO_LOOSE = 1.25
_FINANCE_REL_RATIO_TIGHT = 0.55


def _reference_budget_for_finance_relative(team: Any) -> Optional[int]:
    """相対判定の分母。`payroll_budget` を優先し、無効なら `soft_cap`。"""
    if team is None:
        return None
    pb = getattr(team, "payroll_budget", None)
    if pb is not None:
        try:
            v = int(pb)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    try:
        ll = league_level_for_team(team)
        s = int(get_soft_cap(league_level=ll))
        return s if s > 0 else None
    except Exception:
        return None


def _relative_balance_tag(ending_money: int, ref: int) -> str:
    if ref <= 0:
        return ""
    ratio = float(ending_money) / float(ref)
    if ratio >= _FINANCE_REL_RATIO_LOOSE:
        return "相対余裕"
    if ratio >= _FINANCE_REL_RATIO_TIGHT:
        return "相対標準"
    return "相対タイト"


def _finance_history_ending_money_balance_suffix(entry: dict, team: Any) -> str:
    """`ending_money` があるとき `<残高…>`、分母が取れるときだけ `・相対…` を付ける。"""
    if "ending_money" not in entry:
        return ""
    raw = entry.get("ending_money")
    if raw is None:
        return ""
    try:
        m = int(raw)
    except (TypeError, ValueError):
        return ""
    if m >= _FINANCE_ENDING_MONEY_BAND_FULL:
        tag = "残高十分"
    elif m >= _FINANCE_ENDING_MONEY_BAND_FAT:
        tag = "残高厚め"
    elif m >= _FINANCE_ENDING_MONEY_BAND_WARN:
        tag = "残高注意"
    else:
        tag = "残高要警戒"
    ref = _reference_budget_for_finance_relative(team)
    rel = _relative_balance_tag(m, ref) if ref else ""
    if rel:
        return f" <{tag}・{rel}>"
    return f" <{tag}>"


def _join_finance_history_note_bodies(parts: List[str]) -> str:
    """2件までを ` / ` で連結し、長すぎるときは2件目から短くする。"""
    if not parts:
        return ""
    sep = " / "
    max_body = 102
    if len(sep.join(parts)) <= max_body:
        return sep.join(parts)
    if len(parts) == 1:
        one = parts[0]
        if len(one) <= max_body:
            return one
        return one[: max(1, max_body - 1)].rstrip() + "…"
    first, second = parts[0], parts[1]
    room = max_body - len(first) - len(sep)
    if room >= 6:
        second_out = second if len(second) <= room else second[: max(1, room - 1)].rstrip() + "…"
        return f"{first}{sep}{second_out}"
    first_out = first[: max(10, max_body // 2 - 2)].rstrip() + "…"
    room2 = max_body - len(first_out) - len(sep)
    if room2 < 4:
        return first_out
    second_out = second if len(second) <= room2 else second[: max(1, room2 - 1)].rstrip() + "…"
    return f"{first_out}{sep}{second_out}"


def build_finance_history_note_summary_line(team: Any) -> str:
    """`finance_history` 末尾から有効な note を最大2件、要約＋符号＋任意の season_label＋任意の残高感（相対付き）を1行にする。"""
    prefix = "直近財務メモ:"
    if team is None:
        return f"{prefix} チーム未接続"
    if hasattr(team, "_ensure_history_fields"):
        try:
            team._ensure_history_fields()
        except Exception:
            pass
    hist = getattr(team, "finance_history", None)
    if not isinstance(hist, list):
        return f"{prefix} 判定材料不足"
    if not hist:
        return f"{prefix} 直近 note なし"
    if not isinstance(hist[-1], dict):
        return f"{prefix} 判定材料不足"

    parts: List[str] = []
    for e in reversed(hist):
        if len(parts) >= 2:
            break
        if not isinstance(e, dict):
            continue
        note = e.get("note", "")
        if note is None:
            continue
        raw = str(note).strip()
        if not raw:
            continue
        body = _summarize_finance_history_note_body(raw)
        if body:
            sig = _finance_history_cashflow_sign(e)
            sl = _finance_history_season_label_suffix(e)
            em = _finance_history_ending_money_balance_suffix(e, team)
            parts.append(f"{body} {sig}{sl}{em}")

    if not parts:
        return f"{prefix} 直近 note なし"
    joined = _join_finance_history_note_bodies(parts)
    return f"{prefix} {joined}" if joined else f"{prefix} 直近 note なし"


@dataclass(frozen=True)
class ManagementMenuSnapshot:
    """経営ウィンドウ向けに整形済みの表示行。"""

    finance_lines: Tuple[str, ...]
    facility_lines: Tuple[str, ...]
    owner_preamble: str
    dashboard_text: str
    dashboard_finance_lines: Tuple[str, ...]
    facility_action_previews: Tuple[Tuple[str, str], ...]
    pr_selection_preview: str
    sponsor_apply_preview: str
    merch_line_previews: Tuple[Tuple[str, str], ...]
    pr_remaining_summary: str
    pr_comparison_entries: Tuple[Tuple[str, str], ...]
    pr_dashboard_summary: str
    pr_affordance_summary: str
    sponsor_affordance_summary: str
    merch_affordance_summary: str
    facility_affordance_summary: str
    action_affordance_summary: str
    owner_action_guidance_summary: str
    finance_pressure_summary: str
    payroll_capacity_summary: str
    soft_cap_headroom_summary: str
    round_cash_memo_summary: str
    finance_history_note_summary: str


def _placeholder_snapshot(
    *,
    format_money: FormatMoney,
    format_signed_money: FormatSignedMoney,
) -> ManagementMenuSnapshot:
    fin = (
        "資金: 未設定（チーム未接続）",
        "今季（記録）シーズン中入金: 未実行",
        "前季収支（前回結果）: 未設定",
        "人件費総額: 未設定",
        "状態: 未設定",
        "補足: チームを接続すると財務サマリーが表示されます。",
    )
    fac = (
        "状態: 未設定（チーム未接続）",
        "レベル: 未設定",
        "次の投資コスト: 未設定",
        "建設中: 建設中ではない",
        "市場・ファン: 未設定",
        "補足: 接続後に施設・市場指標を表示します。",
    )
    own = (
        "【ミッション現況】\n"
        "現在ミッション: ミッションなし（チーム未接続）\n"
        "達成率: 未設定\n"
        "残り期限: 未設定\n"
        "危険度の目安: 未設定\n"
    )
    pr_dash_ph = "■ 広報: チーム未接続"
    pr_aff_ph = "広報余力: チーム未接続"
    sp_aff_ph = "スポンサー余力: チーム未接続"
    merch_aff_ph = "グッズ余力: チーム未接続"
    fac_aff_ph = "施設余力: チーム未接続"
    action_aff_ph = "総合アクション余力: チーム未接続"
    owner_guid_ph = "行動判断: チーム未接続"
    fin_press_ph = "財務圧力: チーム未接続"
    pay_cap_ph = "年俸枠メモ: チーム未接続"
    cap_room_ph = "キャップ余白: チーム未接続"
    round_cash_ph = "今ラウンド収支メモ: チーム未接続"
    fh_note_ph = "直近財務メモ: チーム未接続"
    dashboard_finance_lines = _build_dashboard_finance_lines(
        fin,
        action_aff_ph,
        owner_guid_ph,
        fin_press_ph,
        pay_cap_ph,
        cap_room_ph,
        round_cash_ph,
        fh_note_ph,
        pr_aff_ph,
        sp_aff_ph,
        merch_aff_ph,
        fac_aff_ph,
    )
    dash = (
        "■ 財務\n"
        + "\n".join(dashboard_finance_lines)
        + "\n\n■ 施設\n"
        + "\n".join(fac)
        + "\n\n"
        + pr_dash_ph
        + "\n\n■ オーナー\n"
        + own.strip()
        + "\n\n■ 実行履歴 / 直近アクション\n"
        "前回施策: 履歴なし\n"
        "結果: 未実行\n"
        "実行タイミング: —\n"
    )
    empty_fac = tuple((fk, "未設定／接続後に表示") for fk in FACILITY_ORDER)
    return ManagementMenuSnapshot(
        finance_lines=fin,
        facility_lines=fac,
        owner_preamble=own,
        dashboard_text=dash,
        dashboard_finance_lines=dashboard_finance_lines,
        facility_action_previews=empty_fac,
        pr_selection_preview="広報: チーム未接続のため未設定",
        sponsor_apply_preview="スポンサー: チーム未接続のため未設定",
        merch_line_previews=tuple(
            (str(t["id"]), f"「{t.get('name', '')}」: 未設定／接続後に表示") for t in MERCH_PRODUCTS
        ),
        pr_remaining_summary="広報（今ラウンド）: 未設定（チーム未接続）",
        pr_comparison_entries=build_pr_campaign_comparison_entries(
            None,
            None,
            format_money,
            sort_mode=PR_SORT_DEFAULT,
            filter_mode=PR_FILTER_ALL,
        ),
        pr_dashboard_summary=pr_dash_ph,
        pr_affordance_summary=pr_aff_ph,
        sponsor_affordance_summary=sp_aff_ph,
        merch_affordance_summary=merch_aff_ph,
        facility_affordance_summary=fac_aff_ph,
        action_affordance_summary=action_aff_ph,
        owner_action_guidance_summary=owner_guid_ph,
        finance_pressure_summary=fin_press_ph,
        payroll_capacity_summary=pay_cap_ph,
        soft_cap_headroom_summary=cap_room_ph,
        round_cash_memo_summary=round_cash_ph,
        finance_history_note_summary=fh_note_ph,
    )


def build_management_menu_snapshot(
    team: Any,
    season: Any,
    *,
    format_money: FormatMoney,
    format_signed_money: FormatSignedMoney,
    selected_pr_campaign_id: Optional[str] = None,
    selected_sponsor_type_id: Optional[str] = None,
    pr_sort_mode: str = PR_SORT_DEFAULT,
    pr_filter_mode: str = PR_FILTER_ALL,
) -> ManagementMenuSnapshot:
    """
    経営メニュー用の表示スナップショットを構築する。

    team が None のときはプレースホルダのみ（空欄にしない）。
    """
    if team is None:
        snap_none = _placeholder_snapshot(format_money=format_money, format_signed_money=format_signed_money)
        pr_id = selected_pr_campaign_id or (PR_CAMPAIGNS[0]["id"] if PR_CAMPAIGNS else None)
        sp_id = selected_sponsor_type_id or "standard"
        pr_line = build_pr_selection_preview_line(None, season, pr_id, format_money=format_money)
        sp_line = format_sponsor_apply_preview_line(None, sp_id)
        rem = build_pr_round_remaining_summary(None, season)
        pr_cmp = build_pr_campaign_comparison_entries(
            None,
            season,
            format_money,
            sort_mode=pr_sort_mode,
            filter_mode=pr_filter_mode,
        )
        return ManagementMenuSnapshot(
            finance_lines=snap_none.finance_lines,
            facility_lines=snap_none.facility_lines,
            owner_preamble=snap_none.owner_preamble,
            dashboard_text=snap_none.dashboard_text,
            dashboard_finance_lines=snap_none.dashboard_finance_lines,
            facility_action_previews=snap_none.facility_action_previews,
            pr_selection_preview=pr_line,
            sponsor_apply_preview=sp_line,
            merch_line_previews=snap_none.merch_line_previews,
            pr_remaining_summary=rem,
            pr_comparison_entries=pr_cmp,
            pr_dashboard_summary=snap_none.pr_dashboard_summary,
            pr_affordance_summary=snap_none.pr_affordance_summary,
            sponsor_affordance_summary=snap_none.sponsor_affordance_summary,
            merch_affordance_summary=snap_none.merch_affordance_summary,
            facility_affordance_summary=snap_none.facility_affordance_summary,
            action_affordance_summary=snap_none.action_affordance_summary,
            owner_action_guidance_summary=snap_none.owner_action_guidance_summary,
            finance_pressure_summary=snap_none.finance_pressure_summary,
            payroll_capacity_summary=snap_none.payroll_capacity_summary,
            soft_cap_headroom_summary=snap_none.soft_cap_headroom_summary,
            round_cash_memo_summary=snap_none.round_cash_memo_summary,
            finance_history_note_summary=snap_none.finance_history_note_summary,
        )

    profile: Dict[str, Any] = {}
    getter = getattr(team, "get_financial_profile", None)
    if callable(getter):
        try:
            profile = getter() or {}
        except Exception:
            profile = {}

    money = _safe_int(getattr(team, "money", profile.get("money", 0)), 0)
    budget = _safe_int(getattr(team, "payroll_budget", profile.get("payroll_budget", 0)), 0)
    cashflow_last = _safe_int(
        getattr(team, "cashflow_last_season", profile.get("cashflow_last_season", 0)),
        0,
    )
    payroll = _total_payroll(team)
    inseason_total = _sum_inseason_cash_entries(team)

    if inseason_total > 0:
        season_money_line = f"今季（記録）シーズン中入金合計: {format_money(inseason_total)}"
    else:
        season_money_line = "今季（記録）シーズン中入金: 未実行（記録なし）"

    status, hint = _finance_status_and_hint(money, payroll, budget, cashflow_last, inseason_total)

    fin_lines = (
        f"資金: {format_money(money)}",
        season_money_line,
        f"前季収支（前回結果）: {format_signed_money(cashflow_last)}",
        f"人件費総額（現ロスター）: {format_money(payroll)}",
        f"状態: {status}",
        f"補足: {hint}",
    )

    market_size = float(getattr(team, "market_size", profile.get("market_size", 1.0)) or 1.0)
    fan_base = _safe_int(getattr(team, "fan_base", profile.get("fan_base", 0)), 0)
    season_tickets = _safe_int(
        getattr(team, "season_ticket_base", profile.get("season_ticket_base", 0)),
        0,
    )
    sponsor_power = _safe_int(getattr(team, "sponsor_power", profile.get("sponsor_power", 0)), 0)

    lv_parts: List[str] = []
    cheapest: Optional[Tuple[int, str, str]] = None
    for fk in FACILITY_ORDER:
        lv = _safe_int(getattr(team, fk, 1), 1)
        flab = FACILITY_LABELS.get(fk, fk)
        lv_parts.append(f"{flab[:2]}{lv}")
        if lv < FACILITY_MAX_LEVEL:
            c = int(get_facility_upgrade_cost(team, fk))
            if cheapest is None or c < cheapest[0]:
                cheapest = (c, flab, fk)

    if cheapest is not None:
        cst, flab, _ = cheapest
        next_invest = f"次の投資コスト（最安の例）: {format_money(cst)}（{flab}）"
        fac_state = "稼働中（建設中ではない）"
        fac_hint = "施設投資の余地あり（ボタンで段階強化）"
    else:
        next_invest = "次の投資コスト: なし（全施設が最大レベル）"
        fac_state = "稼働中（全施設最大・追加投資なし）"
        fac_hint = "施設は上限到達。他の経営施策で差をつけられます"

    fac_lines = (
        f"状態: {fac_state}",
        f"レベル概要: {' / '.join(lv_parts)}",
        next_invest,
        "建設中: 建設中ではない",
        f"市場規模: {market_size:.2f} ／ ファン基盤: {fan_base:,} ／ ST基盤: {season_tickets:,} ／ スポンサー力: {sponsor_power}",
        f"補足: {fac_hint}",
    )

    missions: List[dict] = []
    refresh = getattr(team, "refresh_owner_missions", None)
    if callable(refresh):
        try:
            raw_m = refresh(force=False)
            if isinstance(raw_m, list):
                missions = [m for m in raw_m if isinstance(m, dict)]
        except Exception:
            missions = []

    primary = None
    for m in missions:
        if str(m.get("priority", "")).strip() == "high":
            primary = m
            break
    if primary is None and missions:
        primary = missions[0]

    remaining_label, remaining_n = _season_remaining_rounds(season)

    mission_pct_for_guidance: Optional[float] = None
    if primary is None:
        miss_title = "ミッションなし"
        prog_label = "達成率: 未設定"
        pct_display = "—"
        danger = "未設定"
    else:
        miss_title = str(primary.get("title", "（無題）"))
        prog_text, pct = _mission_runtime_progress(team, primary)
        mission_pct_for_guidance = pct
        if pct is None:
            pct_display = "算出不可（シーズン状況を要参照）"
            prog_label = f"達成状況: {prog_text}"
        else:
            pct_display = f"{pct:.0f}%"
            prog_label = f"達成状況: {prog_text} ／ 達成率目安: {pct_display}"
        trust = _safe_int(getattr(team, "owner_trust", 50), 50)
        if trust < 38:
            danger = "危険（信頼が低め）"
        elif trust < 52:
            danger = "注意"
        else:
            danger = "おおむね安全"
        if pct is not None and pct < 35 and remaining_n is not None and remaining_n > 0 and remaining_n < 8:
            danger = "やや危険（残り時間が少なく達成率が低い）"

    own_preamble = (
        "【ミッション現況】\n"
        f"現在ミッション: {miss_title}\n"
        f"{prog_label}\n"
        f"残り期限: {remaining_label}\n"
        f"危険度の目安: {danger}\n"
    )

    last_title, last_result, last_when = _pick_last_management_action(team)
    pr_dashboard_line = build_pr_dashboard_summary_line(team, season)
    pr_afford_line = build_pr_affordance_summary_line(team, season)

    sp_tid = selected_sponsor_type_id
    if not sp_tid:
        ensure_sp = getattr(team, "management", None)
        if isinstance(ensure_sp, dict):
            sp_blk = ensure_sp.get("sponsors")
            if isinstance(sp_blk, dict):
                sp_tid = str(sp_blk.get("main_contract_type") or "standard")
        if not sp_tid:
            sp_tid = "standard"
    sponsor_afford_line = build_sponsor_affordance_summary_line(team, sp_tid)
    merch_afford_line = build_merchandise_affordance_summary_line(team, format_money=format_money)
    facility_afford_line = build_facility_affordance_summary_line(team, format_money=format_money)
    pr_exec_n = count_executable_pr_campaigns(team, season)
    action_line = build_action_affordance_summary_line(
        team,
        pr_executable_count=pr_exec_n,
        sponsor_affordance_summary=sponsor_afford_line,
        merch_affordance_summary=merch_afford_line,
        facility_affordance_summary=facility_afford_line,
    )
    owner_guid_line = build_owner_action_guidance_summary_line(
        team,
        finance_status=status,
        owner_danger=danger,
        remaining_rounds=remaining_n,
        has_mission=primary is not None,
        mission_pct=mission_pct_for_guidance,
        action_affordance_summary=action_line,
    )
    finance_pressure_line = build_finance_pressure_summary_line(
        team,
        finance_status=status,
        payroll=payroll,
        budget=budget,
        cashflow_last=cashflow_last,
        inseason_total=inseason_total,
    )
    payroll_capacity_line = build_payroll_capacity_summary_line(team, roster_pay=payroll)
    soft_cap_headroom_line = build_soft_cap_headroom_summary_line(team, roster_pay=payroll)
    _cap_align = _payroll_capacity_cap_align_suffix(payroll_capacity_line, soft_cap_headroom_line)
    if _cap_align:
        payroll_capacity_line = f"{payroll_capacity_line}{_cap_align}"
    round_cash_line = build_round_cash_memo_summary_line(
        team,
        season,
        format_signed_money=format_signed_money,
    )
    finance_history_note_line = build_finance_history_note_summary_line(team)

    dashboard_finance_lines = _build_dashboard_finance_lines(
        fin_lines,
        action_line,
        owner_guid_line,
        finance_pressure_line,
        payroll_capacity_line,
        soft_cap_headroom_line,
        round_cash_line,
        finance_history_note_line,
        pr_afford_line,
        sponsor_afford_line,
        merch_afford_line,
        facility_afford_line,
    )
    dash = (
        "■ 財務\n"
        + "\n".join(dashboard_finance_lines)
        + "\n\n■ 施設\n"
        + "\n".join(fac_lines)
        + "\n\n"
        + pr_dashboard_line
        + "\n\n■ オーナー\n"
        + own_preamble.strip()
        + "\n\n■ 実行履歴 / 直近アクション\n"
        f"前回施策: {last_title}\n"
        f"結果: {last_result}\n"
        f"実行タイミング: {last_when}\n"
    )

    fac_prev = build_facility_action_preview_lines(team, format_money=format_money)
    pr_cid = selected_pr_campaign_id
    if not pr_cid and PR_CAMPAIGNS:
        pr_cid = str(PR_CAMPAIGNS[0]["id"])
    pr_line = build_pr_selection_preview_line(team, season, pr_cid, format_money=format_money)

    sp_line = format_sponsor_apply_preview_line(team, sp_tid)

    merch_prev = build_merchandise_line_previews(team, format_money=format_money)

    pr_rem = build_pr_round_remaining_summary(team, season)
    pr_cmp = build_pr_campaign_comparison_entries(
        team,
        season,
        format_money,
        sort_mode=pr_sort_mode,
        filter_mode=pr_filter_mode,
    )

    return ManagementMenuSnapshot(
        finance_lines=tuple(fin_lines),
        facility_lines=tuple(fac_lines),
        owner_preamble=own_preamble,
        dashboard_text=dash,
        dashboard_finance_lines=dashboard_finance_lines,
        facility_action_previews=fac_prev,
        pr_selection_preview=pr_line,
        sponsor_apply_preview=sp_line,
        merch_line_previews=merch_prev,
        pr_remaining_summary=pr_rem,
        pr_comparison_entries=pr_cmp,
        pr_dashboard_summary=pr_dashboard_line,
        pr_affordance_summary=pr_afford_line,
        sponsor_affordance_summary=sponsor_afford_line,
        merch_affordance_summary=merch_afford_line,
        facility_affordance_summary=facility_afford_line,
        action_affordance_summary=action_line,
        owner_action_guidance_summary=owner_guid_line,
        finance_pressure_summary=finance_pressure_line,
        payroll_capacity_summary=payroll_capacity_line,
        soft_cap_headroom_summary=soft_cap_headroom_line,
        round_cash_memo_summary=round_cash_line,
        finance_history_note_summary=finance_history_note_line,
    )

