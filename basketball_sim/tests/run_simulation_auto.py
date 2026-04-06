from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Any

# ------------------------------------------------------------
# Import path fix (project root)
# ------------------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]

project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

from basketball_sim.main import (
    CITY_MARKET_SIZE,
    apply_user_team_to_league,
    assign_fictional_teams_and_rival,
    auto_draft_players,
    choose_icon_player_auto,
    create_fictional_player_pool,
    create_icon_player,
)
from basketball_sim.models.offseason import Offseason
from basketball_sim.models.season import Season
from basketball_sim.systems.generator import generate_teams
from basketball_sim.utils.sim_rng import init_simulation_random


def _read_env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if raw in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


# True: クラブ史検証のため国際マイルストーンをテスト側で補助する
# False: 純粋な自動進行（ユーザークラブが国際大会に出ない年もあり得る）
def _read_cli_flag(name: str) -> bool:
    # 例: --force-history-international-seed
    return name in set(sys.argv[1:])


FORCE_HISTORY_INTERNATIONAL_SEED = _read_cli_flag("--force-history-international-seed") or _read_env_flag(
    "AUTO_SIM_FORCE_HISTORY_INTERNATIONAL_SEED",
    default=False,
)

TEST_SEED_NOTE = "TEST_SEED"


class _SilentWriter:
    def write(self, _data: str) -> int:
        return len(_data)

    def flush(self) -> None:
        return None


def _pick_test_home_city() -> str:
    # 安全に必ず存在する都市を選ぶ（なければ先頭）
    if "東京" in CITY_MARKET_SIZE:
        return "東京"
    return next(iter(CITY_MARKET_SIZE.keys()))


def _print_summary(user_team: Any) -> None:
    getter = getattr(user_team, "get_club_history_summary", None)
    if callable(getter):
        # TEST 用に投入した milestone は除外して集計値の整合を確認する
        try:
            summary = getter(exclude_test_seed=True) or {}
        except TypeError:
            summary = getter() or {}
        # ------------------------------------------------------------
        # 型保証（将来の退行検知用）
        # ------------------------------------------------------------
        latest_season = summary.get("latest_season", {})
        recent_five_years = summary.get("recent_five_years", [])
        if not isinstance(latest_season, dict):
            raise AssertionError(f"latest_season must be dict, got {type(latest_season)}")
        if not isinstance(recent_five_years, list):
            raise AssertionError(f"recent_five_years must be list, got {type(recent_five_years)}")
        if any(not isinstance(row, dict) for row in recent_five_years):
            raise AssertionError("recent_five_years must be List[dict]")

        club_name = summary.get("club_name", getattr(user_team, "name", "UNKNOWN"))
        print("[AUTO_SIM] club_history_summary")
        print(f"  club_name={club_name}")
        print(f"  season_count={summary.get('season_count')}")
        print(f"  total_titles={summary.get('total_titles')}")
        print(f"  international_titles={summary.get('international_titles')}")
        print(f"  milestone_count={summary.get('milestone_count')}")


def _print_international_milestones(user_team: Any, limit: int = 30) -> None:
    milestones = list(getattr(user_team, "history_milestones", []) or [])
    if not milestones:
        print("[AUTO_SIM] international_milestones")
        print("  (none)")
        return

    keywords = (
        "アジアカップ",
        "世界一決定戦",
        "FINAL BOSS",
        "EASL",
        "東アジアトップリーグ",
        "ACL",
        "オールアジアトーナメント",
        "アジアクラブ選手権",
        "intercontinental",
        "final boss",
        "asia cup",
    )

    picked: list[dict] = []
    for row in reversed(milestones):
        if not isinstance(row, dict):
            continue
        blob = " | ".join(
            [
                str(row.get("competition_name", "")),
                str(row.get("title", "")),
                str(row.get("detail", "")),
                str(row.get("note", "")),
                str(row.get("result", "")),
                str(row.get("milestone_type", row.get("type", ""))),
                str(row.get("category", "")),
            ]
        )
        if any(k.lower() in blob.lower() for k in keywords):
            picked.append(row)
            if len(picked) >= limit:
                break

    print("[AUTO_SIM] international_milestones")
    if not picked:
        print("  (none)")
        return

    for row in picked:
        season = row.get("season", row.get("season_index", "-"))
        comp = row.get("competition_name", "-")
        result = row.get("result", "-")
        title = row.get("title", "-")
        note = str(row.get("note", "") or "").strip()
        note_text = f" | note={note}" if note else ""
        print(f"  - season={season} | {comp} | {result} | {title}{note_text}")


def _print_report_test_markers(user_team: Any) -> None:
    getter = getattr(user_team, "get_club_history_report_text", None)
    if not callable(getter):
        return
    try:
        text = str(getter(season_limit=10) or "")
    except Exception:
        return
    marks = [line for line in text.splitlines() if "[TEST]" in line]
    print("[AUTO_SIM] report_test_markers")
    if not marks:
        print("  (none)")
        return
    for line in marks[:12]:
        print(f"  {line}")


def main() -> None:
    configure_console_encoding()
    init_simulation_random()
    print("[AUTO_SIM] generate_world_start")
    print(f"[AUTO_SIM] force_history_international_seed={FORCE_HISTORY_INTERNATIONAL_SEED}")

    team_name = "テストクラブ"
    home_city = _pick_test_home_city()
    market_size = float(CITY_MARKET_SIZE.get(home_city, 1.0))

    teams = generate_teams()
    user_team = apply_user_team_to_league(teams, team_name, home_city, market_size)

    icon_data = choose_icon_player_auto()
    icon_player = create_icon_player(icon_data)

    fictional_pool = create_fictional_player_pool()
    auto_draft_players(fictional_pool, user_team, icon_player)

    free_agents: list[Any] = []
    assign_fictional_teams_and_rival(teams, user_team, fictional_pool, free_agents)

    print("[AUTO_SIM] simulate_season_start")
    season = Season(teams, free_agents)

    # 出力が非常に多くなるので、基本はサイレントで完走確認だけ行う
    silent = _SilentWriter()
    with contextlib.redirect_stdout(silent):
        season.simulate_to_end()

    print("[AUTO_SIM] simulate_season_done")

    print("[AUTO_SIM] offseason_start")
    offseason = Offseason(teams, free_agents)
    # Offseason.run() は再契約/FA/ドラフト等まで含み時間がかかるため、
    # 自動テストでは国際大会帯のみ軽量に実行してクラッシュ有無を確認する。
    offseason.summer_national_event_enabled = False
    with contextlib.redirect_stdout(silent):
        offseason._run_offseason_asia_cup()

        if FORCE_HISTORY_INTERNATIONAL_SEED:
            # Offseason 側の国際マイルストーン生成は team.season_year を参照して
            # "Season X" を付けるため、テスト側で現在シーズン番号を補助する。
            try:
                seasons = list(getattr(user_team, "history_seasons", []) or [])
                # オフシーズン国際大会は「直前に終わった Season N」扱いに合わせる
                season_no = len(seasons) if seasons else 1
                setattr(user_team, "season_year", season_no)
            except Exception:
                pass

            # ------------------------------------------------------------
            # テスト用の強制検証モード:
            # ユーザークラブが国際大会に出場しない年が普通にあるため、
            # クラブ史表示の検証に必要なマイルストーンだけはテスト側で補助する。
            # （ゲーム本編仕様は変更しない）
            # ------------------------------------------------------------
            try:
                milestones = list(getattr(user_team, "history_milestones", []) or [])
                has_asia_cup = any(
                    isinstance(m, dict) and str(m.get("competition_name", "")).strip() == str(offseason.offseason_cup_name).strip()
                    for m in milestones
                )
                if not has_asia_cup:
                    offseason._add_competition_milestone(
                        team=user_team,
                        competition_name=offseason.offseason_cup_name,
                        result="participant",
                        title=f"{offseason.offseason_cup_name} 出場",
                        detail=f"{offseason.offseason_cup_name}に出場",
                        note=TEST_SEED_NOTE,
                        club_history_text=f"{offseason.offseason_cup_name} 出場",
                    )

                # サマリー検証用に「優勝」も最低1件保証（international_titles/total_titles が増える）
                has_asia_cup_champion = any(
                    isinstance(m, dict)
                    and str(m.get("competition_name", "")).strip() == str(offseason.offseason_cup_name).strip()
                    and (
                        str(m.get("result", "")).lower() in {"champion", "winner", "victory"}
                        or "優勝" in str(m.get("title", ""))
                    )
                    for m in milestones
                )
                if not has_asia_cup_champion:
                    offseason._add_competition_milestone(
                        team=user_team,
                        competition_name=offseason.offseason_cup_name,
                        result="champion",
                        title=f"{offseason.offseason_cup_name} 優勝",
                        detail=f"{offseason.offseason_cup_name}で優勝",
                        note=TEST_SEED_NOTE,
                        club_history_text=f"{offseason.offseason_cup_name} 優勝",
                    )
            except Exception:
                pass

            # 世界一決定戦は Offseason 内部で「アジアカップ上位2」を参照するため、
            # ユーザークラブが確実に参加するよう top2 を補助して実行する。
            try:
                runner_up = next((t for t in teams if t is not user_team), None)
                top2 = [user_team] + ([runner_up] if runner_up is not None else [])
                offseason._latest_offseason_asia_cup_top2_teams = top2
            except Exception:
                pass

        offseason._run_intercontinental_cup()

        # FINAL BOSS は本来条件付きだが、検証モードでは強制発火を許可する
        offseason.final_boss_force_test_mode = bool(FORCE_HISTORY_INTERNATIONAL_SEED)
        offseason._run_final_boss_match()

        # サマリー検証用に「FINAL BOSS 撃破（cleared）」も最低1件保証
        if FORCE_HISTORY_INTERNATIONAL_SEED:
            try:
                milestones = list(getattr(user_team, "history_milestones", []) or [])
                has_final_boss_cleared = any(
                    isinstance(m, dict)
                    and str(m.get("competition_name", "")).strip() == str(offseason.final_boss_name).strip()
                    and (
                        str(m.get("result", "")).lower() == "cleared"
                        or "撃破" in str(m.get("title", ""))
                    )
                    for m in milestones
                )
                if not has_final_boss_cleared:
                    offseason._add_competition_milestone(
                        team=user_team,
                        competition_name=offseason.final_boss_name,
                        result="cleared",
                        title=f"{offseason.final_boss_name} 撃破",
                        detail=f"{offseason.final_boss_name}を撃破",
                        note=TEST_SEED_NOTE,
                        club_history_text=f"{offseason.final_boss_name} 撃破",
                    )
            except Exception:
                pass

        # 国際大会賞金は締めで正本に合流する。ここでは run() 全体を回さないため、
        # 仮積み pending を解消するために締めのみ実行する。
        offseason._process_team_finances()

    print("[AUTO_SIM] offseason_done")
    _print_summary(user_team)
    _print_international_milestones(user_team, limit=30)
    _print_report_test_markers(user_team)
    print("[AUTO_SIM] ok")


if __name__ == "__main__":
    main()

