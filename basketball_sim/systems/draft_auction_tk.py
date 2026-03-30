"""
オークション式ドラフトの GUI 入力（Tk）。メインウィンドウからのオフシーズン実行時に使用。
CLI の input() は Tk コールバック内でブロック・KeyboardInterrupt の原因になるため分離する。
"""

from __future__ import annotations

from typing import List, Optional

from basketball_sim.models.team import Team
from basketball_sim.systems.draft_auction import DraftCandidateMeta, TIER_CONFIGS


def _candidate_lines(team: Team, display: List[DraftCandidateMeta]) -> str:
    from basketball_sim.systems.scout_logic import get_visible_prospect_badge_for_team

    lines = ["狙う選手の番号を入力してください。", "0 = 今回は指名しない（パス）", ""]
    for i, m in enumerate(display, 1):
        p = m.player
        pot = str(getattr(p, "potential", "C"))
        label = str(getattr(p, "draft_profile_label", "") or "")
        label_text = f" | {label}" if label else ""
        badge = get_visible_prospect_badge_for_team(team, p)
        grade_text = f" [{badge}]" if badge else ""
        lines.append(
            f"{i:>2}. {p.name:<16} {getattr(p,'position','-'):<2} "
            f"OVR:{getattr(p,'ovr',0):<2} Pot:{pot} | "
            f"{TIER_CONFIGS[m.tier].name}{grade_text} | min:{m.min_price:,}{label_text}"
        )
    return "\n".join(lines)


def prompt_draft_target(
    parent,
    team: Team,
    slot: str,
    display: List[DraftCandidateMeta],
    cap: int,
) -> Optional[int]:
    """戻り値: 選択した選手の id(player)、パス時は None。"""
    import tkinter as tk
    from tkinter import ttk

    _ = cap  # 将来の RB 表示用にシグネチャのみ合わせる

    if not display:
        return None

    body = _candidate_lines(team, display)
    result: dict = {"player_id": None}

    top = tk.Toplevel(parent)
    top.title(f"Slot {slot} 指名 | {getattr(team, 'name', '')}")
    top.transient(parent)
    top.grab_set()
    top.configure(bg="#15171c")

    outer = ttk.Frame(top, padding=12)
    outer.pack(fill="both", expand=True)

    ttk.Label(outer, text=f"--- Slot {slot} Target Selection | {getattr(team, 'name', '')} ---").pack(
        anchor="w", pady=(0, 6)
    )

    tw = tk.Text(outer, height=16, width=88, wrap="word", bg="#222834", fg="#d6dbe3", state="normal")
    tw.insert("1.0", body)
    tw.configure(state="disabled")
    tw.pack(fill="both", expand=True, pady=(0, 8))

    err_var = tk.StringVar(value="")
    ttk.Label(outer, textvariable=err_var, foreground="#e07070").pack(anchor="w")

    row = ttk.Frame(outer)
    row.pack(fill="x", pady=(4, 0))
    ttk.Label(row, text="番号:").pack(side="left", padx=(0, 6))
    ent = ttk.Entry(row, width=8)
    ent.pack(side="left")
    ent.focus_set()

    def on_ok() -> None:
        raw = ent.get().strip()
        err_var.set("")
        if raw == "0":
            result["player_id"] = None
            top.destroy()
            return
        try:
            idx = int(raw) - 1
        except ValueError:
            err_var.set("数字を入力してください。")
            return
        if 0 <= idx < len(display):
            result["player_id"] = id(display[idx].player)
            top.destroy()
            return
        err_var.set("正しい番号を入力してください。")

    def on_cancel() -> None:
        result["player_id"] = None
        top.destroy()

    btn_row = ttk.Frame(outer)
    btn_row.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_row, text="OK", command=on_ok).pack(side="right", padx=(6, 0))
    ttk.Button(btn_row, text="パス (0 と同じ)", command=on_cancel).pack(side="right")

    ent.bind("<Return>", lambda _e: on_ok())
    top.protocol("WM_DELETE_WINDOW", on_cancel)
    parent.wait_window(top)
    return result["player_id"]


def prompt_draft_bid(
    parent,
    team: Team,
    meta: DraftCandidateMeta,
    cap: int,
    remaining: int,
    base_budget: int,
) -> int:
    """最低落札額以上の入札額を返す（キャンセル時は最低額）。"""
    import tkinter as tk
    from tkinter import ttk

    p = meta.player
    min_price = int(meta.min_price)
    result = {"amount": min_price}

    top = tk.Toplevel(parent)
    top.title(f"入札 | {getattr(team, 'name', '')}")
    top.transient(parent)
    top.grab_set()

    outer = ttk.Frame(top, padding=12)
    outer.pack(fill="both", expand=True)

    ttk.Label(
        outer,
        text=(
            f"選手: {getattr(p, 'name', '')}  |  最低落札額（基準）: {min_price:,} 円\n"
            f"RB 残高: {remaining:,} / {base_budget:,}  （キャップ参考: {cap:,}）\n"
            "一発入札（sealed-bid）です。"
        ),
    ).pack(anchor="w", pady=(0, 8))

    err_var = tk.StringVar(value="")
    ttk.Label(outer, textvariable=err_var, foreground="#e07070").pack(anchor="w")

    row = ttk.Frame(outer)
    row.pack(fill="x")
    ttk.Label(row, text="入札額（円）:").pack(side="left", padx=(0, 6))
    ent = ttk.Entry(row, width=16)
    ent.pack(side="left")
    ent.focus_set()

    def on_ok() -> None:
        raw = ent.get().strip().replace(",", "")
        err_var.set("")
        try:
            amount = int(raw)
        except ValueError:
            err_var.set("数字を入力してください。")
            return
        if amount < min_price:
            err_var.set("最低落札額以上を入力してください。")
            return
        result["amount"] = amount
        top.destroy()

    def on_cancel() -> None:
        result["amount"] = min_price
        top.destroy()

    btn_row = ttk.Frame(outer)
    btn_row.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_row, text="OK", command=on_ok).pack(side="right", padx=(6, 0))
    ttk.Button(btn_row, text="最低額で入札", command=on_cancel).pack(side="right")

    ent.bind("<Return>", lambda _e: on_ok())
    top.protocol("WM_DELETE_WINDOW", on_cancel)
    parent.wait_window(top)
    return int(result["amount"])
