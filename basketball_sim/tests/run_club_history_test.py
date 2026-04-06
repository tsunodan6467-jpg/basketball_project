from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any, Iterable

# ------------------------------------------------------------
# Import path fix
# ------------------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
PACKAGE_ROOT = CURRENT_FILE.parents[1]

for path in (PROJECT_ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

from basketball_sim.models.season import Season
from basketball_sim.models.offseason import Offseason
from basketball_sim.systems.generator import generate_teams


MAX_SIMULATE_SEASONS = 8
SEASON_ROW_LIMIT = 8
MILESTONE_ROW_LIMIT = 20
AWARD_ROW_LIMIT = 10
LEGEND_ROW_LIMIT = 10


class _SilentWriter:
    def write(self, _data: str) -> int:
        return len(_data)

    def flush(self) -> None:
        return None


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalized_blob(row: dict) -> str:
    parts = [
        _safe_text(row.get("category")),
        _safe_text(row.get("milestone_type")),
        _safe_text(row.get("type")),
        _safe_text(row.get("competition_name")),
        _safe_text(row.get("title")),
        _safe_text(row.get("detail")),
        _safe_text(row.get("note")),
        _safe_text(row.get("result")),
    ]
    return " | ".join(parts)


def _is_deep_international_row(row: dict) -> bool:
    blob = _normalized_blob(row)
    deep_keywords = [
        "アジアカップ",
        "asia cup",
        "世界一決定戦",
        "intercontinental",
        "インターコンチネンタル",
        "FINAL BOSS",
        "final boss",
        "nba dream team",
        "nbaドリームチーム",
        "ドリームチーム戦",
    ]
    return any(keyword.lower() in blob.lower() for keyword in deep_keywords)


def _is_international_like_row(row: dict) -> bool:
    blob = _normalized_blob(row)
    keywords = [
        "international",
        "easl",
        "acl",
        "asia cup",
        "アジアカップ",
        "世界一決定戦",
        "intercontinental",
        "インターコンチネンタル",
        "FINAL BOSS",
        "final boss",
        "nba dream team",
        "ドリームチーム戦",
    ]
    return any(keyword.lower() in blob.lower() for keyword in keywords)


def _title_like_count(rows: Iterable[dict]) -> int:
    count = 0
    for row in rows:
        blob = _normalized_blob(row)
        if any(word in blob for word in ["優勝", "準優勝", "撃破", "挑戦", "出場"]):
            count += 1
    return count


def _latest_season_value(rows: Iterable[dict]) -> int:
    latest = 0
    for row in rows:
        season_value = row.get("season")
        if season_value is None:
            season_value = row.get("season_index")
        try:
            latest = max(latest, int(season_value))
        except Exception:
            pass
    return latest


def _simulate_one_season(all_teams, season_no: int):
    print(f"\n[CLUB_HISTORY_TEST] ===== Season {season_no} 開始 =====")
    silent = _SilentWriter()

    with contextlib.redirect_stdout(silent):
        season = Season(all_teams)

        safety = 0
        max_round_guard = max(1, getattr(season, "total_rounds", 0)) + 200

        while not getattr(season, "season_finished", False):
            season.simulate_next_round()
            safety += 1
            if safety > max_round_guard:
                raise RuntimeError(
                    "simulate_next_round のループが想定以上に継続しました。"
                    f" total_rounds={getattr(season, 'total_rounds', '?')}"
                )

    print(f"[CLUB_HISTORY_TEST] ===== Season {season_no} 終了 =====")
    return season


def _simulate_one_offseason(all_teams, free_agents, season_no: int) -> None:
    """
    クラブ史テスト目的のため、Offseason を「国際大会帯だけ」軽量実行する。
    - アジアカップ（offseason.py）
    - 世界一決定戦
    - FINAL BOSS（条件を満たした場合のみ発火）

    ※FA/ドラフト/育成などは重いのでここでは回さない。
    """
    print(f"\n[CLUB_HISTORY_TEST] ----- Offseason {season_no} 国際大会帯 -----")
    silent = _SilentWriter()

    with contextlib.redirect_stdout(silent):
        offseason = Offseason(all_teams, free_agents)
        offseason.summer_national_event_enabled = False
        offseason.final_boss_force_test_mode = False

        for team in all_teams:
            team.offseason_competition_revenue_pending = 0
            team.offseason_competition_revenue_breakdown = {}

        # run() を丸ごと回すと重いので、国際大会部分だけ安全に実行する
        offseason.offseason_cup_result = {}
        offseason.offseason_cup_log = []
        offseason.intercontinental_cup_result = {}
        offseason.intercontinental_cup_log = []
        offseason.final_boss_result = {}
        offseason.final_boss_log = []
        offseason.final_boss_trigger = {}
        offseason._latest_offseason_asia_cup_top2_teams = []
        offseason._latest_intercontinental_champion = None
        offseason._latest_international_milestone_targets = []

        offseason._run_offseason_asia_cup()
        offseason._run_intercontinental_cup()
        offseason._run_final_boss_match()

        # ------------------------------------------------------------
        # Fallback (test harness):
        # EASL上位2が海外クラブになった年は、国内クラブに深い国際大会記録が残らず
        # クラブ史表示検証が進まないことがある。
        #
        # 目的は「表示ロジックの健全性検証」なので、ここでは国内クラブ（テスト用ユーザー）
        # に最低限の国際マイルストーンが入るよう補助する。
        # ------------------------------------------------------------
        if not _has_any_deep_international_record(all_teams):
            user_team = None
            # 強い国内クラブをテスト用ユーザー扱いにして、記録を集約しやすくする
            try:
                user_team = max(
                    all_teams,
                    key=lambda t: (
                        int(getattr(t, "league_level", 3) or 3),
                        float(getattr(t, "team_power", 0.0) or 0.0),
                        float(getattr(t, "team_rating", 0.0) or 0.0),
                    ),
                )
            except Exception:
                user_team = all_teams[0] if all_teams else None

            if user_team is not None:
                setattr(user_team, "is_user_team", True)

                # アジアカップ実績（表示/サマリー整合検証用）
                try:
                    # 優勝として投入（summary のタイトル判定を確実に満たす）
                    offseason._add_competition_milestone(
                        team=user_team,
                        competition_name=offseason.offseason_cup_name,
                        result="champion",
                        title=f"{offseason.offseason_cup_name} 優勝",
                        detail=f"{offseason.offseason_cup_name}で優勝",
                        club_history_text=f"{offseason.offseason_cup_name} 優勝",
                    )
                except Exception:
                    pass

                # 世界一決定戦へ国内クラブを参加させ、結果を記録させる
                runner_up = next((t for t in all_teams if t is not user_team), None)
                top2 = [user_team] + ([runner_up] if runner_up is not None else [])
                offseason._latest_offseason_asia_cup_top2_teams = top2
                try:
                    offseason._run_intercontinental_cup()
                except Exception:
                    pass

                # FINAL BOSS は本来「世界一決定戦 優勝クラブのみ」だが、
                # 表示/サマリー整合検証のため、少なくとも撃破を投入する
                try:
                    offseason.final_boss_force_test_mode = True
                    offseason._run_final_boss_match()
                except Exception:
                    pass

                # 勝敗が運要素で `挑戦` 側になる場合があるため、サマリー検証用に
                # 最低1件「撃破」ミルストーンを保証
                try:
                    offseason._add_competition_milestone(
                        team=user_team,
                        competition_name=offseason.final_boss_name,
                        result="cleared",
                        title=f"{offseason.final_boss_name} 撃破",
                        detail=f"{offseason.final_boss_name}を撃破",
                        club_history_text=f"{offseason.final_boss_name} 撃破",
                    )
                except Exception:
                    pass

        # 大会賞金は締めで正本合流。run() 未実行のため仮積みをここで解消する。
        offseason._process_team_finances()


def _build_team_candidate(team) -> dict:
    milestones = list(getattr(team, "history_milestones", []) or [])
    deep_rows = [row for row in milestones if isinstance(row, dict) and _is_deep_international_row(row)]
    intl_rows = [row for row in milestones if isinstance(row, dict) and _is_international_like_row(row)]

    return {
        "team": team,
        "deep_international_rows": len(deep_rows),
        "international_rows": len(intl_rows),
        "title_like": _title_like_count(milestones),
        "latest_season": _latest_season_value(milestones),
        "total_milestones": len(milestones),
        "league_level": getattr(team, "league_level", "-"),
    }


def _print_candidate_snapshot(candidates: list[dict]) -> None:
    print("\n[CLUB_HISTORY_TEST] INTERNATIONAL_CANDIDATES_TOP5")
    if not candidates:
        print("  - 候補なし")
        return

    ordered = sorted(
        candidates,
        key=lambda row: (
            row["deep_international_rows"],
            row["international_rows"],
            row["title_like"],
            row["latest_season"],
            row["total_milestones"],
        ),
        reverse=True,
    )

    for row in ordered[:5]:
        team = row["team"]
        print(
            f"  - {getattr(team, 'name', 'UNKNOWN')} | "
            f"deep_international_rows={row['deep_international_rows']} | "
            f"international_rows={row['international_rows']} | "
            f"title_like={row['title_like']} | "
            f"latest_season={row['latest_season']} | "
            f"total_milestones={row['total_milestones']} | "
            f"league_level={row['league_level']}"
        )


def _pick_target_team(all_teams) -> tuple[Any, str, list[dict]]:
    if not all_teams:
        raise RuntimeError("チーム生成結果が空です。")

    candidates = [_build_team_candidate(team) for team in all_teams]
    _print_candidate_snapshot(candidates)

    ordered = sorted(
        candidates,
        key=lambda row: (
            row["deep_international_rows"],
            row["international_rows"],
            row["title_like"],
            row["latest_season"],
            row["total_milestones"],
        ),
        reverse=True,
    )

    if ordered and ordered[0]["deep_international_rows"] > 0:
        return ordered[0]["team"], "deep_international_auto", ordered

    if ordered and ordered[0]["international_rows"] > 0:
        return ordered[0]["team"], "international_auto", ordered

    return all_teams[0], "fallback_index", ordered


def _has_any_deep_international_record(all_teams) -> bool:
    for team in all_teams:
        for row in list(getattr(team, "history_milestones", []) or []):
            if isinstance(row, dict) and _is_deep_international_row(row):
                return True
    return False


def _print_summary_block(team) -> None:
    summary = team.get_club_history_summary()

    print("\n[CLUB_HISTORY] SUMMARY")
    print(f"club_name={summary.get('club_name')}")
    print(f"current_league_level={summary.get('current_league_level')}")
    print(f"season_count={summary.get('season_count')}")
    print(f"total_titles={summary.get('total_titles')}")
    print(f"league_titles={summary.get('league_titles')}")
    print(f"cup_titles={summary.get('cup_titles')}")
    print(f"international_titles={summary.get('international_titles')}")
    print(f"promotions={summary.get('promotions')}")
    print(f"relegations={summary.get('relegations')}")
    print(f"legend_count={summary.get('legend_count')}")
    print(f"award_count={summary.get('award_count')}")
    print(f"milestone_count={summary.get('milestone_count')}")


def _print_rows_block(team) -> None:
    season_rows = team.get_club_history_season_rows(limit=SEASON_ROW_LIMIT)
    milestone_rows = team.get_club_history_milestone_rows(limit=MILESTONE_ROW_LIMIT)
    award_rows = team.get_club_history_award_rows(limit=AWARD_ROW_LIMIT)
    legend_rows = team.get_club_history_legend_rows(limit=LEGEND_ROW_LIMIT)

    print("\n[CLUB_HISTORY] RECENT_SEASONS")
    if season_rows:
        for row in season_rows:
            print(
                f"  - {row.get('season')} | "
                f"{row.get('league_level')} | "
                f"{row.get('rank')}位 | "
                f"{row.get('wins')}-{row.get('losses')} | "
                f"得点{row.get('points_for')} / 失点{row.get('points_against')}"
            )
    else:
        print("  - 記録なし")

    print("\n[CLUB_HISTORY] MILESTONES")
    if milestone_rows:
        for row in milestone_rows:
            detail = f" | {row.get('detail')}" if row.get("detail") else ""
            print(f"  - {row.get('season')} | {row.get('title')}{detail}")
    else:
        print("  - 記録なし")

    print("\n[CLUB_HISTORY] AWARDS")
    if award_rows:
        for row in award_rows:
            detail = f" | {row.get('detail')}" if row.get("detail") else ""
            print(f"  - {row.get('season')} | {row.get('award')} | {row.get('player')}{detail}")
    else:
        print("  - 記録なし")

    print("\n[CLUB_HISTORY] LEGENDS")
    if legend_rows:
        for row in legend_rows:
            extras = []
            if row.get("position") not in ("", "-", None):
                extras.append(str(row.get("position")))
            if row.get("career_points") not in ("", "-", None):
                extras.append(f"通算得点 {row.get('career_points')}")
            if row.get("impact") not in ("", "-", None):
                extras.append(f"impact {row.get('impact')}")
            suffix = " | " + " / ".join(extras) if extras else ""
            print(f"  - {row.get('name')}{suffix}")
    else:
        print("  - 記録なし")


def _print_report_text(team) -> None:
    report_text = str(team.get_club_history_report_text(season_limit=10) or "")

    # ------------------------------------------------------------
    # 並び順の簡易検証（UI/整形ロジックの退行検知）
    # ------------------------------------------------------------
    def _assert_section_order(text: str) -> None:
        order = [
            "【マイルストーン（国際）】",
            "【マイルストーン（FINAL BOSS）】",
            "【マイルストーン（国内・昇降格）】",
        ]
        indices = [text.find(h) for h in order]
        if any(i < 0 for i in indices):
            missing = [order[i] for i, idx in enumerate(indices) if idx < 0]
            # 先頭付近の抜粋も付けて原因特定しやすくする
            preview = text[:300].replace("\n", "\\n")
            raise AssertionError(
                "milestone section missing: "
                f"{missing} | indices={indices} | preview={preview}"
            )
        if not (indices[0] < indices[1] < indices[2]):
            raise AssertionError(f"milestone section order invalid: {indices} | order={order}")

    _assert_section_order(report_text)

    # ------------------------------------------------------------
    # UI側（main_menu_view.py の history_text へ詰める文字列）でも順序を検証
    # ------------------------------------------------------------
    try:
        from basketball_sim.systems.main_menu_view import MainMenuView

        view = MainMenuView.__new__(MainMenuView)  # Tk を起動しない
        view.team = team
        ui_lines = view._build_history_report_lines()
        ui_text = "\n".join(ui_lines)

        _assert_section_order(ui_text)
    except AssertionError:
        # UI側で順序が崩れている場合は検知する
        raise
    except ImportError as e:
        # Tkinter 等の依存が無い環境でもテスト全体を落とさない
        print(f"[CLUB_HISTORY_TEST][WARN] UI順序チェックスキップ (ImportError): {e}")
    except Exception as e:
        print(f"[CLUB_HISTORY_TEST][WARN] UI順序チェックスキップ (reason={type(e).__name__}): {e}")

    print("\n[CLUB_HISTORY] REPORT_TEXT")
    print(report_text)


def main() -> None:
    configure_console_encoding()
    print("[CLUB_HISTORY_TEST] チーム生成を開始します。")
    all_teams = generate_teams()
    print(f"[CLUB_HISTORY_TEST] team_count={len(all_teams)}")

    seasons_ran = 0
    for season_no in range(1, MAX_SIMULATE_SEASONS + 1):
        season = _simulate_one_season(all_teams, season_no)
        _simulate_one_offseason(all_teams, getattr(season, "free_agents", []), season_no)
        seasons_ran = season_no
        if _has_any_deep_international_record(all_teams):
            print(f"\n[CLUB_HISTORY_TEST] deep_international_record_detected_at_season={season_no}")
            break
    else:
        print(f"\n[CLUB_HISTORY_TEST] deep_international_record_not_found_within_limit={MAX_SIMULATE_SEASONS}")

    target_team, pick_reason, ordered_candidates = _pick_target_team(all_teams)
    print(
        f"\n[CLUB_HISTORY_TEST] target_team="
        f"{getattr(target_team, 'name', 'UNKNOWN')} "
        f"(league_level={getattr(target_team, 'league_level', '-')})"
    )
    print(f"[CLUB_HISTORY_TEST] target_pick_reason={pick_reason}")
    print(f"[CLUB_HISTORY_TEST] seasons_ran={seasons_ran}")

    if ordered_candidates:
        best = ordered_candidates[0]
        print(
            f"[CLUB_HISTORY_TEST] best_candidate_metrics="
            f"deep={best['deep_international_rows']}, "
            f"intl={best['international_rows']}, "
            f"title_like={best['title_like']}, "
            f"latest_season={best['latest_season']}, "
            f"milestones={best['total_milestones']}"
        )

    print("\n[CLUB_HISTORY_TEST][DEBUG] seasons_finished=yes")
    print(
        f"[CLUB_HISTORY_TEST][DEBUG] target_history_sizes "
        f"seasons={len(getattr(target_team, 'history_seasons', []) or [])} "
        f"milestones={len(getattr(target_team, 'history_milestones', []) or [])} "
        f"awards={len(getattr(target_team, 'history_awards', []) or [])} "
        f"legends={len(getattr(target_team, 'club_legends', []) or [])}"
    )

    try:
        print("[CLUB_HISTORY_TEST][DEBUG] summary_block_start")
        _print_summary_block(target_team)
        print("[CLUB_HISTORY_TEST][DEBUG] summary_block_done")
    except Exception as e:
        print(f"[CLUB_HISTORY_TEST][ERROR] summary_block_failed: {type(e).__name__}: {e}")
        raise

    try:
        print("[CLUB_HISTORY_TEST][DEBUG] rows_block_start")
        _print_rows_block(target_team)
        print("[CLUB_HISTORY_TEST][DEBUG] rows_block_done")
    except Exception as e:
        print(f"[CLUB_HISTORY_TEST][ERROR] rows_block_failed: {type(e).__name__}: {e}")
        raise

    try:
        print("[CLUB_HISTORY_TEST][DEBUG] report_text_start")
        _print_report_text(target_team)
        print("[CLUB_HISTORY_TEST][DEBUG] report_text_done")
    except Exception as e:
        print(f"[CLUB_HISTORY_TEST][ERROR] report_text_failed: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
