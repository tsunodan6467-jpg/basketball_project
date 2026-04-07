"""
オフシーズン・本格FA（`conduct_free_agency`）直前の、ユーザーチーム向け手動1人獲得 GUI。

`Offseason.run` から `pre_conduct_free_agency_ui_prompt` 経由でだけ呼ばれる想定。
契約反映は `sign_free_agent` に集約する（`conduct_free_agency` 本体は変更しない）。
"""

from __future__ import annotations

from typing import Any, List, Optional

from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


def remove_player_from_free_agent_pool(free_agents: List[Player], player: Player) -> bool:
    """
    FA プールから選手を除去（同一オブジェクトまたは player_id 一致）。
    戻り値: 除去できたら True。
    """
    if player in free_agents:
        free_agents.remove(player)
        return True
    pid = getattr(player, "player_id", None)
    if pid is not None:
        for fp in list(free_agents):
            if getattr(fp, "player_id", None) == pid:
                free_agents.remove(fp)
                return True
    return False


def run_user_offseason_fa_one_pick(
    parent: Any,
    *,
    teams: List[Team],
    free_agents: List[Player],
    user_team: Team,
) -> None:
    """
    モーダルウィンドウ: FA プールから最大1人を `sign_free_agent` で獲得するか、スキップする。
    `teams` は将来拡張用に受け取るのみ（現状未使用）。
    """
    _ = teams

    import tkinter as tk
    from tkinter import messagebox, ttk

    from basketball_sim.systems.free_agent_market import (
        ensure_fa_market_fields,
        ensure_team_fa_market_fields,
        estimate_fa_contract_years,
        estimate_fa_market_value,
        get_team_fa_signing_limit,
        normalize_free_agents,
        precheck_user_fa_sign,
        sign_free_agent,
    )
    from basketball_sim.systems.roster_rules import RosterViolationError

    ensure_team_fa_market_fields(user_team)
    raw = list(free_agents)
    candidates = normalize_free_agents(raw)
    candidates.sort(
        key=lambda p: (-int(getattr(p, "ovr", 0) or 0), str(getattr(p, "name", "")))
    )

    _fa_nat_ja = {
        "Japan": "日本",
        "Foreign": "外国籍",
        "Asia": "アジア",
        "Naturalized": "帰化",
    }

    top = tk.Toplevel(parent)
    top.title("オフFA（手動で1人まで）")
    top.configure(bg="#15171c")
    try:
        top.transient(parent)
    except Exception:
        pass
    top.geometry("820x480")
    top.minsize(680, 400)
    top.grab_set()

    outer = ttk.Frame(top, padding=12)
    outer.pack(fill="both", expand=True)

    ttk.Label(
        outer,
        text=(
            "本格FA市場（CPU）の直前です。FAプールから最大1人だけ手動で獲得できます。"
            "年俸は市場目安が自動適用されます（交渉・金額入力なし）。"
            "スキップすると従来どおり CPU のみが補強します（手動獲得後も CPU は走ります）。"
        ),
        wraplength=780,
    ).pack(fill="x", pady=(0, 6))

    hint_var = tk.StringVar(value="選手を選ぶか、「スキップ」で CPU FA のみに進みます。")
    ttk.Label(outer, textvariable=hint_var, wraplength=780).pack(fill="x", pady=(0, 6))

    tree_fr = ttk.Frame(outer)
    tree_fr.pack(fill="both", expand=True, pady=(0, 8))
    tree_fr.rowconfigure(0, weight=1)
    tree_fr.columnconfigure(0, weight=1)

    cols = ("name", "pos", "ovr", "age", "nat", "salary")
    tv = ttk.Treeview(
        tree_fr,
        columns=cols,
        show="headings",
        height=12,
        selectmode="browse",
    )
    tv.heading("name", text="選手名")
    tv.heading("pos", text="POS")
    tv.heading("ovr", text="OVR")
    tv.heading("age", text="年齢")
    tv.heading("nat", text="国籍区分")
    tv.heading("salary", text="年俸目安")
    tv.column("name", width=200, stretch=True)
    tv.column("pos", width=44, stretch=False)
    tv.column("ovr", width=48, stretch=False)
    tv.column("age", width=48, stretch=False)
    tv.column("nat", width=72, stretch=False)
    tv.column("salary", width=120, stretch=False)

    vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=vsb.set)
    tv.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    item_to_player: dict[str, Player] = {}
    for p in candidates:
        ensure_fa_market_fields(p)
        pid = getattr(p, "player_id", None)
        iid = str(pid) if pid is not None else f"id_{id(p)}"
        item_to_player[iid] = p
        nat_key = str(getattr(p, "nationality", "Japan") or "Japan")
        nat_j = _fa_nat_ja.get(nat_key, nat_key)
        est = int(estimate_fa_market_value(p))
        tv.insert(
            "",
            tk.END,
            iid=iid,
            values=(
                str(getattr(p, "name", "?")),
                str(getattr(p, "position", "?")),
                int(getattr(p, "ovr", 0) or 0),
                int(getattr(p, "age", 0) or 0),
                nat_j,
                f"{est:,}",
            ),
        )

    status_var = tk.StringVar(value="")
    ttk.Label(outer, textvariable=status_var, wraplength=780).pack(fill="x", pady=(0, 4))

    if not candidates:
        hint_var.set("FA プールに契約可能な選手がいません。スキップして CPU FA に進んでください。")

    def _selected_player() -> Optional[Player]:
        sel = tv.selection()
        if not sel:
            return None
        return item_to_player.get(str(sel[0]))

    def on_skip() -> None:
        try:
            top.grab_release()
        except Exception:
            pass
        top.destroy()

    def on_check() -> None:
        player = _selected_player()
        if player is None:
            messagebox.showinfo("オフFA", "一覧から選手を選択してください。", parent=top)
            return
        ensure_team_fa_market_fields(user_team)
        ensure_fa_market_fields(player)
        sal = int(estimate_fa_market_value(player))
        yrs = int(estimate_fa_contract_years(player))
        room = int(get_team_fa_signing_limit(user_team))
        money = int(getattr(user_team, "money", 0) or 0)
        ok, reason = precheck_user_fa_sign(user_team, player)
        nm = str(getattr(player, "name", "?"))
        if ok:
            status_var.set(f"「{nm}」: 契約可能（確認済み）。")
            messagebox.showinfo(
                "オフFA（制限確認）",
                f"選手: {nm}\n"
                f"年俸目安: {sal:,} 円\n"
                f"契約年数: {yrs} 年\n"
                f"サラリー契約余地: {room:,} 円\n"
                f"所持金: {money:,} 円\n\n"
                "上記条件で契約できます。「契約する」で確定してください。",
                parent=top,
            )
        else:
            status_var.set(f"「{nm}」: 契約不可 — {reason}")
            messagebox.showwarning(
                "オフFA（制限確認）",
                f"選手: {nm}\n"
                f"年俸目安: {sal:,} 円\n"
                f"サラリー契約余地: {room:,} 円\n"
                f"所持金: {money:,} 円\n\n"
                f"契約できません: {reason}",
                parent=top,
            )

    def on_sign() -> None:
        player = _selected_player()
        if player is None:
            messagebox.showinfo("オフFA", "一覧から選手を選択してください。", parent=top)
            return
        ok, reason = precheck_user_fa_sign(user_team, player)
        nm = str(getattr(player, "name", "?"))
        if not ok:
            messagebox.showwarning("オフFA", reason, parent=top)
            return
        sal = int(estimate_fa_market_value(player))
        yrs = int(estimate_fa_contract_years(player))
        if not messagebox.askyesno(
            "オフFA（最終確認）",
            f"{nm} と契約しますか？\n\n年俸目安 {sal:,} 円 / {yrs} 年\n"
            "（`sign_free_agent` で反映。所持金の即時減算はありません。）\n\n"
            "その後、CPU による本格FAも実行されます。",
            parent=top,
        ):
            return
        try:
            sign_free_agent(user_team, player)
        except RosterViolationError as exc:
            messagebox.showwarning("オフFA", str(exc), parent=top)
            return
        roster = list(getattr(user_team, "players", []) or [])
        if player not in roster:
            messagebox.showwarning(
                "オフFA",
                "契約の反映に失敗しました（ルールにより見送られた可能性があります）。",
                parent=top,
            )
            return
        if not remove_player_from_free_agent_pool(free_agents, player):
            # プールに無い場合でもロスター反映は済んでいる; ログのみ
            pass
        messagebox.showinfo(
            "オフFA",
            f"{nm} を獲得しました。続けて CPU 本格FAが実行されます。",
            parent=top,
        )
        try:
            top.grab_release()
        except Exception:
            pass
        top.destroy()

    btn_row = ttk.Frame(outer)
    btn_row.pack(fill="x")

    tk.Button(btn_row, text="スキップ", command=on_skip, width=12).pack(side="left")
    tk.Button(btn_row, text="制限を確認", command=on_check, width=14).pack(side="right", padx=(8, 0))
    tk.Button(btn_row, text="契約する", command=on_sign, width=12).pack(side="right")

    top.protocol("WM_DELETE_WINDOW", on_skip)
    top.wait_window(top)
