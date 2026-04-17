"""
クラブグッズ開発（management 永続化・第1段は保存＋表示が主）。

発売中ラインはオフシーズン締めの merchandise 収入内訳にボーナスとして接続（折衷）。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §2.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from random import Random
from typing import Any, Dict, List, Optional, Tuple

MERCH_PRODUCTS: Tuple[Dict[str, str], ...] = (
    {"id": "jersey_alt", "category": "ユニフォーム", "name": "オルタネイトジャージ"},
    {"id": "fan_towel", "category": "観戦グッズ", "name": "チーム応援タオル"},
    {"id": "acrylic_keychain", "category": "小物", "name": "アクリルキーホルダー"},
)

PHASE_ORDER = ("concept", "design", "production", "on_sale")
PHASE_LABEL_JA = {
    "concept": "企画中",
    "design": "デザイン",
    "production": "生産・発注",
    "on_sale": "発売中",
}

# 現在フェーズから次へ進めるときの開発費（局所で money のみ減算）
ADVANCE_COST: Dict[str, int] = {
    "concept": 420_000,
    "design": 750_000,
    "production": 1_080_000,
    "on_sale": 0,
}

VALID_PHASES = frozenset(PHASE_ORDER)
MAX_MERCH_HISTORY = 36
MERCH_PRODUCT_IDS = frozenset(p["id"] for p in MERCH_PRODUCTS)

# CLI 候補比較用の短文（表示のみ。フェーズ・コストの正本は既存定数）
MERCH_PRODUCT_CLI_COMPARISON_HINTS: Dict[str, str] = {
    "jersey_alt": "ユニフォーム系・ブランド訴求（工程は重め）",
    "fan_towel": "観戦グッズ・ファン拡大寄り",
    "acrylic_keychain": "小物・比較的ライトに進めやすい",
}

# オフシーズン `record_financial_result` の merchandise 内訳に加算するボーナス（1 シーズン分・簡易式）
_MGMT_MERCH_PER_LINE: Dict[int, int] = {1: 195_000, 2: 108_000, 3: 48_000}
_MGMT_MERCH_BONUS_CAP = 2_800_000


def management_merchandise_revenue_bonus(team: Any, *, league_level: int) -> int:
    """
    `management.merchandise` で「発売中」のラインごとに、年次収入内訳 merchandise に上乗せする額。
    ベースの物販式（Offseason._calculate_team_revenue 内）とは別枠で足す（折衷配線）。
    """
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_merchandise_on_team(team)
    block = team.management.get("merchandise")
    if not isinstance(block, dict):
        return 0
    items = block.get("items")
    if not isinstance(items, list):
        return 0
    released = sum(
        1
        for row in items
        if isinstance(row, dict) and str(row.get("phase", "")) == "on_sale"
    )
    if released <= 0:
        return 0
    ll = int(league_level if league_level in (1, 2, 3) else 3)
    per = int(_MGMT_MERCH_PER_LINE.get(ll, _MGMT_MERCH_PER_LINE[3]))
    pop = int(getattr(team, "popularity", 50))
    pop_mul = 1.0 + max(-0.12, min(0.18, (pop - 50) * 0.0045))
    raw = int(per * released * pop_mul)
    return int(max(0, min(raw, _MGMT_MERCH_BONUS_CAP)))


def ensure_merchandise_on_team(team: Any) -> None:
    if not hasattr(team, "management") or team.management is None or not isinstance(team.management, dict):
        team.management = {}
    mg = team.management
    block = mg.get("merchandise")
    if not isinstance(block, dict):
        block = {}
        mg["merchandise"] = block
    hist = block.get("history")
    if not isinstance(hist, list):
        block["history"] = []

    saved_list = block.get("items")
    saved_by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(saved_list, list):
        for row in saved_list:
            if isinstance(row, dict) and row.get("id"):
                saved_by_id[str(row["id"])] = row

    items: List[Dict[str, Any]] = []
    for tmpl in MERCH_PRODUCTS:
        pid = tmpl["id"]
        base = {"id": pid, "category": tmpl["category"], "name": tmpl["name"]}
        if pid in saved_by_id:
            ph = str(saved_by_id[pid].get("phase", "concept"))
            if ph not in VALID_PHASES:
                ph = "concept"
            base["phase"] = ph
        else:
            base["phase"] = "concept"
        items.append(base)
    block["items"] = items


def _next_phase(phase: str) -> Optional[str]:
    try:
        i = PHASE_ORDER.index(phase)
    except ValueError:
        return None
    if i + 1 >= len(PHASE_ORDER):
        return None
    return PHASE_ORDER[i + 1]


def get_merchandise_item(team: Any, product_id: str) -> Optional[Dict[str, Any]]:
    ensure_merchandise_on_team(team)
    pid = str(product_id)
    for row in team.management["merchandise"]["items"]:
        if row.get("id") == pid:
            return row
    return None


def advance_merchandise_phase(team: Any, product_id: str) -> Tuple[bool, str]:
    if not bool(getattr(team, "is_user_team", False)):
        return False, "自チームのみグッズ開発を進められます。"
    return _advance_merchandise_phase_core(team, product_id, source="user")


def can_advance_merchandise_phase(team: Any, product_id: str) -> Tuple[bool, str]:
    """次工程への進行可否のみ（状態は変えない）。GUI プレビュー用。"""
    if not bool(getattr(team, "is_user_team", False)):
        return False, "自チームのみグッズ開発を進められます。"
    pid = str(product_id or "").strip()
    if pid not in MERCH_PRODUCT_IDS:
        return False, "不明な商品ラインです。"
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_merchandise_on_team(team)
    item = get_merchandise_item(team, pid)
    if item is None:
        return False, "商品データが見つかりません。"
    phase = str(item.get("phase", "concept"))
    if phase not in VALID_PHASES:
        phase = "concept"
    if phase == "on_sale":
        return False, "すでに発売中です。"
    nxt = _next_phase(phase)
    if nxt is None:
        return False, "これ以上進められません。"
    cost = int(ADVANCE_COST.get(phase, 0))
    money = int(getattr(team, "money", 0))
    if money < cost:
        return False, f"資金が不足しています（次段階まで {cost:,} 円）。"
    return True, ""


def _advance_merchandise_phase_core(team: Any, product_id: str, *, source: str) -> Tuple[bool, str]:
    if source not in ("user", "cpu"):
        return False, ""
    if source == "cpu" and bool(getattr(team, "is_user_team", False)):
        return False, ""
    pid = str(product_id or "").strip()
    if pid not in MERCH_PRODUCT_IDS:
        return False, "不明な商品ラインです。"
    if hasattr(team, "_ensure_history_fields"):
        team._ensure_history_fields()
    ensure_merchandise_on_team(team)

    item = get_merchandise_item(team, pid)
    if item is None:
        return False, "商品データが見つかりません。"

    phase = str(item.get("phase", "concept"))
    if phase not in VALID_PHASES:
        phase = "concept"
        item["phase"] = phase

    if phase == "on_sale":
        return False, "すでに発売中です。"

    nxt = _next_phase(phase)
    if nxt is None:
        return False, "これ以上進められません。"

    cost = int(ADVANCE_COST.get(phase, 0))
    money = int(getattr(team, "money", 0))
    if money < cost:
        return False, f"資金が不足しています（次段階まで {cost:,} 円）。"

    team.money = int(money - cost)
    item["phase"] = nxt
    label = PHASE_LABEL_JA.get(nxt, nxt)
    name = str(item.get("name", pid))

    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "product_id": pid,
        "name": name,
        "from_phase": phase,
        "to_phase": nxt,
        "cost": cost,
        "source": source,
    }
    hist = team.management["merchandise"]["history"]
    hist.append(entry)
    while len(hist) > MAX_MERCH_HISTORY:
        hist.pop(0)

    return True, f"「{name}」を「{label}」まで進めました（-{cost:,} 円）。"


def try_cpu_merchandise_advance(team: Any, season: Any, rng: Random) -> bool:
    """CPU クラブ用。未発売ラインを低確率で 1 段階進行。成功時 True。"""
    _ = season  # 将来のシーズンラベル用
    if bool(getattr(team, "is_user_team", False)):
        return False
    if rng.random() >= 0.055:
        return False
    ensure_merchandise_on_team(team)
    candidates = [
        str(row["id"])
        for row in team.management["merchandise"]["items"]
        if isinstance(row, dict) and row.get("phase") != "on_sale"
    ]
    if not candidates:
        return False
    ok, _ = _advance_merchandise_phase_core(team, rng.choice(candidates), source="cpu")
    return ok


def format_merchandise_status_line(item: Dict[str, Any]) -> str:
    name = str(item.get("name", "-"))
    cat = str(item.get("category", "-"))
    ph = str(item.get("phase", "concept"))
    pl = PHASE_LABEL_JA.get(ph, ph)
    return f"{name}（{cat}）｜ 状態: {pl}"


def format_merchandise_row_display(item: Dict[str, Any]) -> str:
    """GUI 1 行表示（次工程コスト付き）。"""
    base = format_merchandise_status_line(item)
    ph = str(item.get("phase", "concept"))
    if ph == "on_sale":
        return base + " ｜ 次の工程: —"
    cost = int(ADVANCE_COST.get(ph, 0) or 0)
    if cost <= 0:
        return base
    return f"{base} ｜ 次の工程: {cost:,} 円"


def estimate_dummy_merch_sales_lines(team: Any) -> List[str]:
    """§2.4: 目安表示用の簡易式。正本はオフシーズン締めの merchandise 内訳（＋発売中ボーナス）。"""
    ensure_merchandise_on_team(team)
    released = sum(
        1 for row in team.management["merchandise"]["items"] if row.get("phase") == "on_sale"
    )
    fb = int(getattr(team, "fan_base", 0))
    pop = int(getattr(team, "popularity", 50))
    # 見かけ上の推定（保存しない）
    base = 120_000 + released * 95_000 + min(400_000, fb * 12) + max(0, pop - 50) * 2_200
    est = int(max(80_000, base))
    bonus = management_merchandise_revenue_bonus(team, league_level=int(getattr(team, "league_level", 3)))
    bonus_note = f"年次締めへの上乗せ（発売中ボーナス・目安）: 約 {bonus:,} 円" if bonus else "年次締めへの上乗せ（発売中ボーナス）: 0 円（発売中ラインなし）"
    lines = [
        "【売上・ランキング（簡易表示）】",
        f"推定月次グッズ売上（目安）: 約 {est:,} 円 ※あくまで目安",
        bonus_note,
        f"発売中ライン数: {released} / {len(MERCH_PRODUCTS)}",
        "クラブ内人気（ダミー順）: ①応援タオル ②キーホルダー ③ユニフォーム関連",
    ]
    return lines


def format_cli_merchandise_management_screen_lines(team: Any) -> List[str]:
    """
    CLI グッズ開発画面用（サマリー＋候補比較）。
    表示のため `ensure_merchandise_on_team` で構造を揃える（既存の履歴表示と同系）。
    """
    if team is None:
        return [
            "【グッズサマリー】",
            "直近施策: 情報なし",
            "実行状態: 情報なし",
            "発売中ライン: 情報なし",
            "履歴: 履歴なし",
            "直近更新: 情報なし",
            "",
            "【候補比較】",
            "情報なし",
            "",
        ]

    hist: List[Any] = []
    items: List[Any] = []
    try:
        if hasattr(team, "_ensure_history_fields"):
            team._ensure_history_fields()
        ensure_merchandise_on_team(team)
        block = team.management.get("merchandise")
        if isinstance(block, dict):
            raw_h = block.get("history")
            if isinstance(raw_h, list):
                hist = raw_h
            raw_i = block.get("items")
            if isinstance(raw_i, list):
                items = raw_i
    except Exception:
        hist = []
        items = []

    n_hist = len(hist)
    hist_disp = f"{n_hist}件" if n_hist > 0 else "履歴なし"

    last_pid = ""
    last_label = "未実行"
    last_update = "履歴なし"
    if hist:
        row = hist[-1]
        if isinstance(row, dict):
            last_pid = str(row.get("product_id") or "").strip()
            nm = str(row.get("name") or "").strip()
            to_ph = str(row.get("to_phase") or "")
            to_l = PHASE_LABEL_JA.get(to_ph, to_ph or "情報なし")
            if nm:
                last_label = f"{nm} → {to_l}"
            else:
                last_label = to_l if to_l else "情報なし"
            at = str(row.get("at") or "").strip()
            at_disp = at[:19].replace("T", " ") if at else ""
            if at_disp:
                last_update = f"{at_disp}  {last_label}"
            else:
                last_update = last_label
        else:
            last_label = "情報なし"
            last_update = "情報なし"

    n_on_sale = 0
    for r in items:
        if isinstance(r, dict) and str(r.get("phase", "")) == "on_sale":
            n_on_sale += 1
    n_lines = len(MERCH_PRODUCTS)
    on_sale_disp = f"{n_on_sale} / {n_lines}"
    if n_on_sale >= n_lines and n_lines > 0:
        exec_state = "全ライン発売中（次工程なし）"
    elif items:
        exec_state = "開発進行中（未発売ラインあり）"
    else:
        exec_state = "情報なし"

    lines: List[str] = [
        "【グッズサマリー】",
        f"直近施策: {last_label}",
        f"実行状態: {exec_state}",
        f"発売中ライン: {on_sale_disp}",
        f"履歴: {hist_disp}",
        f"直近更新: {last_update}",
        "",
        "【候補比較】",
    ]
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in items:
        if isinstance(r, dict) and r.get("id"):
            by_id[str(r["id"])] = r
    for i, tmpl in enumerate(MERCH_PRODUCTS, start=1):
        pid = str(tmpl.get("id", "") or "")
        name = str(tmpl.get("name", pid) or pid)
        cat = str(tmpl.get("category", "") or "")
        hint = MERCH_PRODUCT_CLI_COMPARISON_HINTS.get(pid, "情報なし")
        row = by_id.get(pid, {})
        ph = str(row.get("phase", "concept") or "concept")
        if ph not in VALID_PHASES:
            ph = "concept"
        pl = PHASE_LABEL_JA.get(ph, ph)
        if ph == "on_sale":
            next_s = "次工程なし"
        else:
            try:
                cst = int(ADVANCE_COST.get(ph, 0) or 0)
                next_s = f"次工程 {cst:,}円" if cst > 0 else "情報なし"
            except (TypeError, ValueError):
                next_s = "情報なし"
        mark = "（直近）" if pid and pid == last_pid else ""
        cat_s = f"{cat}／" if cat else ""
        lines.append(f"{i}. {cat_s}{name}{mark}  …  {hint} ｜ {pl} ｜ {next_s}")
    lines.append("")
    return lines


def format_merchandise_history_lines(team: Any, *, limit: int = 6) -> List[str]:
    ensure_merchandise_on_team(team)
    hist = list(team.management["merchandise"].get("history") or [])
    if not hist:
        return ["（開発履歴はまだありません）"]
    lim = max(1, int(limit))
    lines: List[str] = []
    for row in hist[-lim:]:
        if not isinstance(row, dict):
            continue
        at = str(row.get("at", ""))[:19].replace("T", " ")
        name = str(row.get("name", "-"))
        to_ph = PHASE_LABEL_JA.get(str(row.get("to_phase", "")), row.get("to_phase", ""))
        cost = row.get("cost")
        cpu_tag = "［CPU］" if str(row.get("source", "user")) == "cpu" else ""
        if isinstance(cost, int):
            lines.append(f"- {at}  {cpu_tag}{name} → {to_ph}  （{cost:,} 円）")
        else:
            lines.append(f"- {at}  {cpu_tag}{name} → {to_ph}")
    return lines
