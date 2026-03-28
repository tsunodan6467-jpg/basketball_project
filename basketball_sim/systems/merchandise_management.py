"""
クラブグッズ開発（management 永続化・第1段は保存＋表示が主）。

売上・本丸の revenue / §0.3 内訳にはまだ接続しない。
docs/GM_MANAGEMENT_MENU_SPEC_V1.md §2.4
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    }
    hist = team.management["merchandise"]["history"]
    hist.append(entry)
    while len(hist) > MAX_MERCH_HISTORY:
        hist.pop(0)

    return True, f"「{name}」を「{label}」まで進めました（-{cost:,} 円）。"


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
    """§2.4: ダミー／簡易式。永続化・正本 revenue には混ぜない。"""
    ensure_merchandise_on_team(team)
    released = sum(
        1 for row in team.management["merchandise"]["items"] if row.get("phase") == "on_sale"
    )
    fb = int(getattr(team, "fan_base", 0))
    pop = int(getattr(team, "popularity", 50))
    # 見かけ上の推定（保存しない）
    base = 120_000 + released * 95_000 + min(400_000, fb * 12) + max(0, pop - 50) * 2_200
    est = int(max(80_000, base))
    lines = [
        "【売上・ランキング（簡易・ダミー表示）】",
        f"推定月次グッズ売上（目安）: 約 {est:,} 円 ※シミュレーション簡易式・本番収支とは未連携",
        f"発売中ライン数: {released} / {len(MERCH_PRODUCTS)}",
        "クラブ内人気（ダミー順）: ①応援タオル ②キーホルダー ③ユニフォーム関連",
    ]
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
        if isinstance(cost, int):
            lines.append(f"- {at}  {name} → {to_ph}  （{cost:,} 円）")
        else:
            lines.append(f"- {at}  {name} → {to_ph}")
    return lines
