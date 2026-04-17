"""
CLI 経営メニュー用の施策サマリー行（表示のみ。施策ロジックは変更しない）。
"""

from __future__ import annotations

from typing import Any, List

from basketball_sim.systems.sponsor_management import label_for_main_sponsor_type


def _cli_hist_count_label(n: int) -> str:
    return f"{int(n)}件" if int(n) > 0 else "履歴なし"


def format_cli_management_policy_header_lines(team: Any) -> List[str]:
    """
    【施策サマリー】【施策の見どころ】用テキスト。
    management を読むのみ（ensure_* での初期化・補正は行わない）。
    """
    if team is None:
        return [
            "【施策サマリー】",
            "メインスポンサー: 情報なし",
            "スポンサー履歴: 履歴なし",
            "広報履歴: 履歴なし",
            "グッズ履歴: 履歴なし",
            "取引ログ: 履歴なし",
            "",
            "【施策の見どころ】",
            "情報なし",
            "",
        ]

    tid = ""
    n_sp = n_pr = n_merch = n_ht = 0
    try:
        mg = getattr(team, "management", None)
        if isinstance(mg, dict):
            sp = mg.get("sponsors")
            if isinstance(sp, dict):
                tid = str(sp.get("main_contract_type") or "").strip()
                sh = sp.get("history")
                if isinstance(sh, list):
                    n_sp = len(sh)
            prb = mg.get("pr_campaigns")
            if isinstance(prb, dict):
                ph = prb.get("history")
                if isinstance(ph, list):
                    n_pr = len(ph)
            mer = mg.get("merchandise")
            if isinstance(mer, dict):
                mh = mer.get("history")
                if isinstance(mh, list):
                    n_merch = len(mh)
        ht = getattr(team, "history_transactions", None)
        if isinstance(ht, list):
            n_ht = len(ht)
    except Exception:
        tid = ""
        n_sp = n_pr = n_merch = n_ht = 0

    if tid:
        try:
            main_disp = str(label_for_main_sponsor_type(tid))
        except Exception:
            main_disp = tid
    else:
        main_disp = "未設定"

    fully_empty = (not tid) and n_sp == 0 and n_pr == 0 and n_merch == 0 and n_ht == 0

    out: List[str] = [
        "【施策サマリー】",
        f"メインスポンサー: {main_disp}",
        f"スポンサー履歴: {_cli_hist_count_label(n_sp)}",
        f"広報履歴: {_cli_hist_count_label(n_pr)}",
        f"グッズ履歴: {_cli_hist_count_label(n_merch)}",
        f"取引ログ: {_cli_hist_count_label(n_ht)}",
        "",
        "【施策の見どころ】",
    ]
    if fully_empty:
        out.append("情報なし")
    else:
        sp_state = "契約中" if tid else "未設定"
        pr_state = "実行済み" if n_pr > 0 else "未実行"
        merch_state = "実行済み" if n_merch > 0 else "未実行"
        tx_state = "履歴あり" if n_ht > 0 else "履歴なし"
        out.extend(
            [
                f"スポンサー: {sp_state}",
                f"広報: {pr_state}",
                f"グッズ: {merch_state}",
                f"取引: {tx_state}",
            ]
        )
    out.append("")
    return out
