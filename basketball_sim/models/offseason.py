import random
from typing import List, Optional, Dict
from .team import Team
from .player import Player
from .match import Match
from basketball_sim.systems.draft import conduct_draft
from basketball_sim.systems.draft_auction import conduct_auction_draft
from basketball_sim.systems.free_agency import conduct_free_agency
from basketball_sim.systems.development import DevelopmentSystem
from basketball_sim.systems.top_prospect_generator import generate_top_prospects

try:
    from basketball_sim.systems.contract_logic import (
        ensure_contract_fields,
        calculate_desired_contract_terms,
        evaluate_resign_offer,
        apply_resign_offer,
        advance_contract_years,
    )
except Exception:
    ensure_contract_fields = None
    calculate_desired_contract_terms = None
    evaluate_resign_offer = None
    apply_resign_offer = None
    advance_contract_years = None

try:
    from basketball_sim.systems.free_agent_market import (
        age_free_agents_one_year,
        retire_stale_free_agents,
        maintain_minimum_fa_pool,
    )
except Exception:
    age_free_agents_one_year = None
    retire_stale_free_agents = None
    maintain_minimum_fa_pool = None


def assign_team_strategies(teams: List[Team]):
    """
    各チームに次季戦術を割り当てる。
    基本は現戦術を維持し、一定確率でのみ変更する。
    弱いチームほど路線変更しやすく、強いチームほど継続しやすい。

    coach_style に応じて、変更時の候補戦術を強めに寄せる。
    """
    strategies = [
        "balanced",
        "run_and_gun",
        "three_point",
        "defense",
        "inside",
    ]

    for team in teams:
        current_strategy = getattr(team, "strategy", "balanced")
        wins = getattr(team, "last_season_wins", getattr(team, "regular_wins", 15))
        coach_style = getattr(team, "coach_style", "balanced")

        if wins <= 10:
            change_prob = 0.55
        elif wins <= 14:
            change_prob = 0.38
        elif wins <= 18:
            change_prob = 0.24
        else:
            change_prob = 0.12

        if current_strategy not in strategies:
            current_strategy = "balanced"

        if random.random() < change_prob:
            if coach_style == "offense":
                adjusted_weights = {
                    "balanced": 0.12,
                    "run_and_gun": 0.34,
                    "three_point": 0.34,
                    "defense": 0.08,
                    "inside": 0.12,
                }
            elif coach_style == "defense":
                adjusted_weights = {
                    "balanced": 0.18,
                    "run_and_gun": 0.08,
                    "three_point": 0.08,
                    "defense": 0.50,
                    "inside": 0.16,
                }
            elif coach_style == "development":
                adjusted_weights = {
                    "balanced": 0.45,
                    "run_and_gun": 0.10,
                    "three_point": 0.10,
                    "defense": 0.10,
                    "inside": 0.25,
                }
            else:
                adjusted_weights = {
                    "balanced": 0.35,
                    "run_and_gun": 0.20,
                    "three_point": 0.20,
                    "defense": 0.15,
                    "inside": 0.10,
                }

            candidate_strategies = [s for s in strategies if s != current_strategy]
            candidate_weights = [adjusted_weights[s] for s in candidate_strategies]

            team.strategy = random.choices(
                candidate_strategies,
                weights=candidate_weights,
                k=1
            )[0]
        else:
            team.strategy = current_strategy


def print_team_strategies(teams: List[Team]):
    """
    次季のチーム戦術一覧を表示する。
    """
    print("\n[Team Strategies for Next Season]")

    strategy_count = {
        "balanced": 0,
        "run_and_gun": 0,
        "three_point": 0,
        "defense": 0,
        "inside": 0,
    }

    sorted_teams = sorted(teams, key=lambda t: (t.league_level, t.name))

    for team in sorted_teams:
        strategy = getattr(team, "strategy", "balanced")
        coach_style = getattr(team, "coach_style", "balanced")
        strategy_count[strategy] = strategy_count.get(strategy, 0) + 1
        print(f"D{team.league_level} | {team.name:<25} | {strategy:<12} | coach:{coach_style}")

    print("\n[Strategy Summary]")
    for strategy, count in strategy_count.items():
        print(f"{strategy:<12}: {count}")


class Offseason:
    """
    オフシーズン中の処理を実行するクラス。
    各処理は決められた順序で呼び出されます。
    """

    def __init__(self, teams: List[Team], free_agents: List[Player]):
        self.teams = teams
        self.free_agents = free_agents
        self.draft_pool: List[Player] = []
        self.re_signed_player_ids = set()

        self.international_reborn_pool = {
            "Foreign": [],
            "Asia": [],
        }

        self.retired_star_pool: List[Player] = []
        self.top_prospects: List[Player] = []

        self.offseason_cup_enabled = True
        self.offseason_cup_name = "アジアカップ"
        self.offseason_cup_result = {}
        self.offseason_cup_log = []

        self.intercontinental_cup_enabled = True
        self.intercontinental_cup_name = "世界一決定戦"
        self.intercontinental_cup_result = {}
        self.intercontinental_cup_log = []

        self.final_boss_enabled = True
        self.final_boss_name = "FINAL BOSS"
        self.final_boss_result = {}
        self.final_boss_log = []
        self.final_boss_trigger = {}
        self.final_boss_force_test_mode = False

        self.summer_national_event_enabled = True
        self.summer_national_event_name = "夏代表大会"
        self.summer_national_event_result = {}
        self.summer_national_event_log = []

        self._latest_offseason_asia_cup_top2_teams: List[Team] = []
        self._latest_intercontinental_champion: Optional[Team] = None
        self._latest_international_milestone_targets: List[Team] = []
        self._external_competition_team_counter = -2000
        self._external_competition_player_counter = -200000

        # 国際マイルストーンの詳細デバッグ出力は本番では行わない

    def run(self):
        print("\n--- Offseason Processing ---")
        self.re_signed_player_ids.clear()
        self.draft_pool = []
        self.top_prospects = []
        self.retired_star_pool = []
        self.international_reborn_pool = {"Foreign": [], "Asia": []}
        self.offseason_cup_result = {}
        self.offseason_cup_log = []
        self.intercontinental_cup_result = {}
        self.intercontinental_cup_log = []
        self.final_boss_result = {}
        self.final_boss_log = []
        self.final_boss_trigger = {}
        self.summer_national_event_result = {}
        self.summer_national_event_log = []
        self._latest_offseason_asia_cup_top2_teams = []
        self._latest_intercontinental_champion = None
        self._latest_international_milestone_targets = []

        for team in self.teams:
            if hasattr(team, "reset_rookie_budget"):
                team.reset_rookie_budget()

        self._run_offseason_asia_cup()
        self._run_intercontinental_cup()
        self._run_final_boss_match()
        self._run_summer_national_team_event()
        self._age_players()
        self._player_progression()
        self._process_naturalization()
        self._retire_and_reincarnate()
        self._resign_players()
        self._assign_scout_dispatches()
        self._reset_team_stats()
        self._reset_player_stats()
        self._decrease_contracts()
        self._refresh_international_market()
        self._generate_draft_pool()
        self._run_draft_combine()
        # 正本: docs/DRAFT_AUCTION_SYSTEM.md
        conduct_auction_draft(self.teams, self.draft_pool, self.free_agents)

        from basketball_sim.systems.trade import conduct_trades
        conduct_trades(self.teams)

        conduct_free_agency(self.teams, self.free_agents)
        self._maintain_free_agent_market()
        self._process_team_finances()
        self._process_owner_missions()
        self._heal_players()
        self._review_team_coaches()
        assign_team_strategies(self.teams)
        print_team_strategies(self.teams)

        print("--- Offseason Finished ---\n")

    def _get_offseason_cup_team_sort_key(self, team: Team):
        last_wins = getattr(team, "last_season_wins", getattr(team, "regular_wins", 0))
        regular_wins = getattr(team, "regular_wins", 0)
        team_ovr = sum(getattr(p, "ovr", 0) for p in getattr(team, "players", [])[:10])
        return (
            -int(last_wins),
            -int(regular_wins),
            -int(team_ovr),
            str(getattr(team, "name", "")),
        )

    def _get_latest_easl_top2_payloads(self) -> List[dict]:
        # まず season.py から各クラブへ配布された payload を拾う
        for team in self.teams:
            payloads = getattr(team, "_latest_easl_top2_payloads", None)
            if payloads:
                ordered = []
                champion = next((p for p in payloads if (p.get("type") or p.get("result_type")) == "easl_champion"), None)
                runner_up = next((p for p in payloads if (p.get("type") or p.get("result_type")) == "easl_runner_up"), None)
                if champion is not None:
                    ordered.append(champion)
                if runner_up is not None:
                    ordered.append(runner_up)
                if ordered:
                    return ordered

        # fallback: 国内クラブ history_milestones から拾う
        latest_season = None
        payloads: List[dict] = []
        for team in self.teams:
            milestones = list(getattr(team, "history_milestones", []) or [])
            for row in milestones:
                row_type = row.get("milestone_type") or row.get("type")
                if row_type not in {"easl_champion", "easl_runner_up"}:
                    continue
                season_value = row.get("season")
                if season_value is None:
                    season_value = row.get("season_index")
                if season_value is None:
                    continue
                try:
                    season_no = int(season_value)
                except Exception:
                    continue
                payload = {
                    "name": getattr(team, "name", ""),
                    "team": team,
                    "is_external": False,
                    "type": row_type,
                    "season": season_no,
                }
                if latest_season is None or season_no > latest_season:
                    latest_season = season_no
                    payloads = [payload]
                elif season_no == latest_season:
                    payloads.append(payload)

        if latest_season is None:
            return []

        ordered: List[dict] = []
        champion = next((p for p in payloads if p["type"] == "easl_champion"), None)
        runner_up = next((p for p in payloads if p["type"] == "easl_runner_up"), None)
        if champion is not None:
            ordered.append(champion)
        if runner_up is not None:
            ordered.append(runner_up)
        return ordered

    def _build_team_from_easl_payload(self, payload: dict) -> Optional[Team]:
        if not isinstance(payload, dict):
            return None

        team_obj = payload.get("team")
        if isinstance(team_obj, Team):
            return team_obj

        team_name = payload.get("name")
        if team_name:
            for team in self.teams:
                if getattr(team, "name", "") == team_name:
                    return team

        if not team_name:
            return None

        region = payload.get("region") or payload.get("home_city") or "External"
        power = int(payload.get("power", 78))
        return self._create_external_asia_cup_team(team_name, region, power)

    def _build_external_competition_player(self, team_id: int, region: str, position: str, ovr: int, nationality: str) -> Player:
        self._external_competition_player_counter -= 1
        height_map = {"PG": 183, "SG": 190, "SF": 198, "PF": 205, "C": 211}
        weight_map = {"PG": 78, "SG": 85, "SF": 95, "PF": 104, "C": 112}
        skill_base = max(55, min(95, int(ovr)))
        return Player(
            player_id=self._external_competition_player_counter,
            name=f"{region}_{position}_{abs(self._external_competition_player_counter)}",
            age=random.randint(24, 31),
            nationality=nationality,
            position=position,
            height_cm=height_map.get(position, 195),
            weight_kg=weight_map.get(position, 90),
            shoot=skill_base,
            three=max(45, skill_base - random.randint(0, 10)),
            drive=max(45, skill_base - random.randint(0, 10)),
            passing=max(40, skill_base - random.randint(5, 15)),
            rebound=max(40, skill_base - random.randint(0, 12)),
            defense=max(45, skill_base - random.randint(0, 10)),
            ft=max(50, skill_base - random.randint(0, 10)),
            stamina=random.randint(65, 85),
            ovr=skill_base,
            potential="B",
            archetype="balanced",
            usage_base=random.randint(14, 24),
            team_id=team_id,
            salary=0,
            contract_years_left=1,
            years_pro=random.randint(2, 10),
            league_years=random.randint(1, 8),
        )

    def _create_external_asia_cup_team(self, name: str, region: str, power: int) -> Team:
        self._external_competition_team_counter -= 1
        team = Team(team_id=self._external_competition_team_counter, name=name, league_level=0)
        team.home_city = region
        team.market_size = 1.0
        team.popularity = 55
        team.money = 8000000
        base_positions = ["PG", "PG", "SG", "SG", "SG", "SF", "SF", "SF", "PF", "PF", "PF", "C", "C"]
        roster: List[Player] = []
        for idx, pos in enumerate(base_positions):
            if idx < 2:
                nationality = "Foreign"
                ovr = power + random.randint(0, 4)
            elif idx == 2:
                nationality = "Asia"
                ovr = power + random.randint(-1, 3)
            else:
                nationality = "Japan"
                ovr = power + random.randint(-6, 2)
            roster.append(self._build_external_competition_player(team.team_id, region, pos, ovr, nationality))
        team.players = roster
        return team

    def _select_offseason_asia_cup_teams(self) -> List[Team]:
        participants: List[Team] = []
        used_names = set()

        # 1) 東アジアトップリーグ上位2を最優先で入れる（国内外問わず）
        easl_top2 = self._get_latest_easl_top2_payloads()
        for payload in easl_top2:
            team = self._build_team_from_easl_payload(payload)
            if team is None:
                continue
            team_name = getattr(team, "name", "")
            if not team_name or team_name in used_names:
                continue
            participants.append(team)
            used_names.add(team_name)

        # 2) 他地域6枠で補完し、必ず8チーム化を目指す
        external_specs = [
            ("West Asia Falcons", "WestAsia", 76),
            ("Gulf Kings", "WestAsia", 75),
            ("Delhi Tigers", "SouthAsia", 74),
            ("Ashgabat Horses", "CentralAsia", 74),
            ("Tashkent Storm", "CentralAsia", 75),
            ("Doha Waves", "WestAsia", 76),
            ("Riyadh Falcons", "WestAsia", 77),
            ("Karachi Kings", "SouthAsia", 74),
        ]
        for name, region, power in external_specs:
            if len(participants) >= 8:
                break
            if name in used_names:
                continue
            participants.append(self._create_external_asia_cup_team(name, region, power))
            used_names.add(name)

        return participants[:8]

    def _ensure_team_history_containers(self, team: Team):
        if not hasattr(team, "club_history") or team.club_history is None:
            team.club_history = []
        if not hasattr(team, "history_milestones") or team.history_milestones is None:
            team.history_milestones = []

    def _is_history_target_team(self, team: Optional[Team]) -> bool:
        if team is None:
            return False
        team_name = str(getattr(team, "name", "") or "").strip()
        return len(team_name) > 0

    def _build_competition_milestone(
        self,
        team: Team,
        competition_name: str,
        result: str,
        title: str,
        detail: str,
        note: str = "",
        milestone_type: str = "international_competition",
        category: str = "international",
    ) -> dict:
        season_index = int(getattr(team, "season_year", 0) or 0)
        # team.season_year が未設定でも Season N を必ず埋める（表示/ソートの一貫性のため）
        if season_index <= 0:
            try:
                # オフシーズン国際大会は「直前に終わったシーズン（Season N）」扱いにする
                season_index = len(getattr(team, "history_seasons", []) or [])
            except Exception:
                season_index = 1
        if season_index <= 0:
            season_index = 1

        season_label = f"Season {season_index}"
        return {
            "season_index": season_index,
            "season": season_label,
            "category": category,
            "milestone_type": milestone_type,
            "competition_name": competition_name,
            "title": title,
            "detail": detail,
            "note": note,
            "result": result,
            "team_name": getattr(team, "name", ""),
        }

    def _add_competition_milestone(
        self,
        team: Optional[Team],
        competition_name: str,
        result: str,
        title: str,
        detail: str,
        note: str = "",
        milestone_type: str = "international_competition",
        category: str = "international",
        club_history_text: Optional[str] = None,
    ):
        if not self._is_history_target_team(team):
            return
        self._ensure_team_history_containers(team)
        milestone = self._build_competition_milestone(
            team=team,
            competition_name=competition_name,
            result=result,
            title=title,
            detail=detail,
            note=note,
            milestone_type=milestone_type,
            category=category,
        )
        if hasattr(team, "add_history_milestone"):
            team.add_history_milestone(milestone)
        else:
            team.history_milestones.append(milestone)
        if club_history_text:
            team.club_history.append(club_history_text)

    def _record_offseason_asia_cup_result(
        self,
        champion: Team,
        runner_up: Team,
        semifinalists: List[Team],
        participants: List[Team],
    ):
        self.offseason_cup_result = {
            "name": self.offseason_cup_name,
            "champion": getattr(champion, "name", ""),
            "runner_up": getattr(runner_up, "name", ""),
            "semifinalists": [getattr(team, "name", "") for team in semifinalists],
            "participants": [getattr(team, "name", "") for team in participants],
        }
        self._latest_offseason_asia_cup_top2_teams = [champion, runner_up]
        self._latest_international_milestone_targets = [champion, runner_up] + list(semifinalists)

        for team in participants:
            self._ensure_team_history_containers(team)

        self._add_competition_milestone(
            team=champion,
            competition_name=self.offseason_cup_name,
            result="champion",
            title=f"{self.offseason_cup_name} 優勝",
            detail=f"{self.offseason_cup_name}で優勝",
            club_history_text=f"{self.offseason_cup_name} 優勝",
        )
        self._add_competition_milestone(
            team=runner_up,
            competition_name=self.offseason_cup_name,
            result="runner_up",
            title=f"{self.offseason_cup_name} 準優勝",
            detail=f"{self.offseason_cup_name}で準優勝",
            club_history_text=f"{self.offseason_cup_name} 準優勝",
        )
        for team in semifinalists:
            if team not in (champion, runner_up):
                self._add_competition_milestone(
                    team=team,
                    competition_name=self.offseason_cup_name,
                    result="best4",
                    title=f"{self.offseason_cup_name} ベスト4",
                    detail=f"{self.offseason_cup_name}でベスト4",
                    club_history_text=f"{self.offseason_cup_name} ベスト4",
                )

    def _apply_offseason_asia_cup_rewards(self, champion: Team, runner_up: Team):
        champion.money = int(getattr(champion, "money", 0) + 3000000)
        runner_up.money = int(getattr(runner_up, "money", 0) + 1500000)
        champion.popularity = min(100, int(getattr(champion, "popularity", 50) + 4))
        runner_up.popularity = min(100, int(getattr(runner_up, "popularity", 50) + 2))

    def _play_offseason_cup_round(
        self,
        teams: List[Team],
        round_name: str,
        competition_name: Optional[str] = None,
        competition_type: str = "asia_cup",
        competition_log: Optional[List[dict]] = None,
    ) -> List[Team]:
        display_name = competition_name or self.offseason_cup_name
        log_bucket = competition_log if competition_log is not None else self.offseason_cup_log

        print(f"\n[{display_name} - {round_name}]")
        winners = []

        for index in range(0, len(teams), 2):
            team_a = teams[index]
            team_b = teams[index + 1]
            match = Match(team_a, team_b, is_playoff=True, competition_type=competition_type)
            result = match.simulate()
            if isinstance(result, tuple):
                winner = result[0]
                if len(result) >= 3:
                    score_a = int(result[1])
                    score_b = int(result[2])
                else:
                    score_a = int(getattr(team_a, "score", 0))
                    score_b = int(getattr(team_b, "score", 0))
            else:
                winner = result
                score_a = int(getattr(team_a, "score", 0))
                score_b = int(getattr(team_b, "score", 0))

            loser = team_b if winner == team_a else team_a
            print(
                f"{team_a.name} {score_a} - {score_b} {team_b.name} | "
                f"WIN: {getattr(winner, 'name', 'Unknown')} | competition_type={competition_type}"
            )
            log_bucket.append({
                "competition": display_name,
                "competition_type": competition_type,
                "round": round_name,
                "team_a": team_a.name,
                "team_b": team_b.name,
                "score_a": int(score_a),
                "score_b": int(score_b),
                "winner": getattr(winner, "name", ""),
                "loser": getattr(loser, "name", ""),
            })
            winners.append(winner)

        return winners

    def _run_offseason_asia_cup(self):
        self.offseason_cup_result = {}
        self.offseason_cup_log = []
        self._external_competition_team_counter = -2000
        self._external_competition_player_counter = -200000

        if not getattr(self, "offseason_cup_enabled", True):
            return

        participants = self._select_offseason_asia_cup_teams()
        if len(participants) < 8:
            print(f"[{self.offseason_cup_name}] 参加チーム不足のため開催をスキップします。")
            return

        print(f"\n--- {self.offseason_cup_name} 開催（シーズン終了直後） ---")
        print("[参加チーム]")
        easl_names = {payload.get("name") for payload in self._get_latest_easl_top2_payloads()}
        for idx, team in enumerate(participants, start=1):
            label = "海外招待"
            if getattr(team, "name", "") in easl_names:
                label = "東アジアトップリーグ上位2"
            elif getattr(team, "team_id", 0) > 0:
                label = "国内クラブ"
            wins = getattr(team, "last_season_wins", getattr(team, "regular_wins", 0))
            print(f"{idx}. {team.name} | {label} | D{getattr(team, 'league_level', '?')} | 昨季勝利:{wins}")

        quarterfinal_winners = self._play_offseason_cup_round(participants, "準々決勝")
        semifinalists = list(quarterfinal_winners)
        semifinal_winners = self._play_offseason_cup_round(quarterfinal_winners, "準決勝")

        finalists = list(semifinal_winners)
        champion_list = self._play_offseason_cup_round(finalists, "決勝")
        if not champion_list:
            print(f"[{self.offseason_cup_name}] 決勝結果の取得に失敗しました。")
            return

        champion = champion_list[0]
        runner_up = finalists[1] if finalists[0] == champion else finalists[0]

        self._record_offseason_asia_cup_result(
            champion=champion,
            runner_up=runner_up,
            semifinalists=semifinalists,
            participants=participants,
        )
        self._apply_offseason_asia_cup_rewards(champion, runner_up)

        print(f"\n[{self.offseason_cup_name} 結果]")
        print(f"優勝: {champion.name}")
        print(f"準優勝: {runner_up.name}")
        print(
            f"報酬 | 優勝賞金: 3,000,000 / 準優勝賞金: 1,500,000 | "
            f"人気補正: 優勝 +4 / 準優勝 +2"
        )

    def _create_external_intercontinental_team(self, name: str, region: str, power: int) -> Team:
        return self._create_external_asia_cup_team(name, region, power)

    def _select_intercontinental_cup_teams(self) -> List[Team]:
        participants: List[Team] = []
        used_names = set()

        for team in self._latest_offseason_asia_cup_top2_teams:
            team_name = getattr(team, "name", "")
            if not team_name or team_name in used_names:
                continue
            participants.append(team)
            used_names.add(team_name)

        external_specs = [
            ("Euro League Select", "Europe", 82),
            ("Americas Elite", "Americas", 81),
        ]
        for name, region, power in external_specs:
            if len(participants) >= 4:
                break
            if name in used_names:
                continue
            participants.append(self._create_external_intercontinental_team(name, region, power))
            used_names.add(name)

        return participants[:4]

    def _record_intercontinental_cup_result(
        self,
        champion: Team,
        runner_up: Team,
        semifinalists: List[Team],
        participants: List[Team],
    ):
        self.intercontinental_cup_result = {
            "name": self.intercontinental_cup_name,
            "champion": getattr(champion, "name", ""),
            "runner_up": getattr(runner_up, "name", ""),
            "semifinalists": [getattr(team, "name", "") for team in semifinalists],
            "participants": [getattr(team, "name", "") for team in participants],
        }
        self._latest_intercontinental_champion = champion
        self._latest_international_milestone_targets = [champion, runner_up] + list(semifinalists)
        champion_is_player_club = self._is_user_team(champion)
        self.final_boss_trigger = {
            "qualified": champion_is_player_club,
            "team_name": getattr(champion, "name", ""),
            "team_id": getattr(champion, "team_id", None),
            "from_competition": self.intercontinental_cup_name,
            "is_player_club": champion_is_player_club,
        }

        for team in participants:
            self._ensure_team_history_containers(team)

        self._add_competition_milestone(
            team=champion,
            competition_name=self.intercontinental_cup_name,
            result="champion",
            title=f"{self.intercontinental_cup_name} 優勝",
            detail=f"{self.intercontinental_cup_name}で優勝",
            club_history_text=f"{self.intercontinental_cup_name} 優勝",
        )
        self._add_competition_milestone(
            team=runner_up,
            competition_name=self.intercontinental_cup_name,
            result="runner_up",
            title=f"{self.intercontinental_cup_name} 準優勝",
            detail=f"{self.intercontinental_cup_name}で準優勝",
            club_history_text=f"{self.intercontinental_cup_name} 準優勝",
        )
        for team in semifinalists:
            if team not in (champion, runner_up):
                self._add_competition_milestone(
                    team=team,
                    competition_name=self.intercontinental_cup_name,
                    result="best4",
                    title=f"{self.intercontinental_cup_name} ベスト4",
                    detail=f"{self.intercontinental_cup_name}でベスト4",
                    club_history_text=f"{self.intercontinental_cup_name} ベスト4",
                )

    def _apply_intercontinental_cup_rewards(self, champion: Team, runner_up: Team):
        champion.money = int(getattr(champion, "money", 0) + 5000000)
        runner_up.money = int(getattr(runner_up, "money", 0) + 2500000)
        champion.popularity = min(100, int(getattr(champion, "popularity", 50) + 6))
        runner_up.popularity = min(100, int(getattr(runner_up, "popularity", 50) + 3))

    def _run_intercontinental_cup(self):
        self.intercontinental_cup_result = {}
        self.intercontinental_cup_log = []

        if not getattr(self, "intercontinental_cup_enabled", True):
            return

        participants = self._select_intercontinental_cup_teams()
        if len(participants) < 4:
            print(f"[{self.intercontinental_cup_name}] 参加チーム不足のため開催をスキップします。")
            return

        print(f"\n--- {self.intercontinental_cup_name} 開催（アジアカップ終了直後） ---")
        print("[参加チーム]")
        asia_top2_names = {getattr(team, "name", "") for team in self._latest_offseason_asia_cup_top2_teams}
        for idx, team in enumerate(participants, start=1):
            label = "海外王者"
            if getattr(team, "name", "") in asia_top2_names:
                label = "アジアカップ上位2"
            elif getattr(team, "team_id", 0) > 0:
                label = "国内クラブ"
            wins = getattr(team, "last_season_wins", getattr(team, "regular_wins", 0))
            print(f"{idx}. {team.name} | {label} | D{getattr(team, 'league_level', '?')} | 昨季勝利:{wins}")

        semifinal_winners = self._play_offseason_cup_round(
            participants,
            "準決勝",
            competition_name=self.intercontinental_cup_name,
            competition_type="intercontinental",
            competition_log=self.intercontinental_cup_log,
        )
        semifinalists = list(participants)
        finalists = list(semifinal_winners)
        champion_list = self._play_offseason_cup_round(
            finalists,
            "決勝",
            competition_name=self.intercontinental_cup_name,
            competition_type="intercontinental",
            competition_log=self.intercontinental_cup_log,
        )
        if not champion_list:
            print(f"[{self.intercontinental_cup_name}] 決勝結果の取得に失敗しました。")
            return

        champion = champion_list[0]
        runner_up = finalists[1] if finalists[0] == champion else finalists[0]

        self._record_intercontinental_cup_result(
            champion=champion,
            runner_up=runner_up,
            semifinalists=semifinalists,
            participants=participants,
        )
        self._apply_intercontinental_cup_rewards(champion, runner_up)

        print(f"\n[{self.intercontinental_cup_name} 結果]")
        print(f"優勝: {champion.name}")
        print(f"準優勝: {runner_up.name}")
        if self.final_boss_trigger.get("qualified"):
            print(f"[FINAL BOSS] {champion.name} が挑戦権を獲得しました。")
        else:
            print(f"[FINAL BOSS] 今回の挑戦権獲得クラブはありません。")
        print(
            f"報酬 | 優勝賞金: 5,000,000 / 準優勝賞金: 2,500,000 | "
            f"人気補正: 優勝 +6 / 準優勝 +3"
        )

    def _create_final_boss_team(self) -> Team:
        team = self._create_external_asia_cup_team("NBA Dream Team", "USA", 90)
        team.popularity = 100
        team.money = 999999999

        for player in team.players:
            base_ovr = max(84, min(99, int(getattr(player, "ovr", 84)) + random.randint(2, 6)))
            player.ovr = base_ovr
            player.shoot = max(75, min(99, int(getattr(player, "shoot", base_ovr)) + random.randint(1, 5)))
            player.three = max(70, min(99, int(getattr(player, "three", base_ovr - 2)) + random.randint(1, 5)))
            player.drive = max(75, min(99, int(getattr(player, "drive", base_ovr - 1)) + random.randint(1, 5)))
            player.passing = max(68, min(99, int(getattr(player, "passing", base_ovr - 6)) + random.randint(1, 4)))
            player.rebound = max(68, min(99, int(getattr(player, "rebound", base_ovr - 6)) + random.randint(1, 4)))
            player.defense = max(75, min(99, int(getattr(player, "defense", base_ovr - 1)) + random.randint(1, 5)))
            player.ft = max(72, min(99, int(getattr(player, "ft", base_ovr - 2)) + random.randint(1, 5)))
            player.stamina = max(80, min(99, int(getattr(player, "stamina", 80)) + random.randint(2, 8)))

        return team

    def _record_final_boss_result(
        self,
        challenger: Team,
        boss_team: Team,
        winner: Team,
        loser: Team,
        challenger_score: int,
        boss_score: int,
    ):
        self.final_boss_result = {
            "name": self.final_boss_name,
            "challenger": getattr(challenger, "name", ""),
            "boss_team": getattr(boss_team, "name", ""),
            "winner": getattr(winner, "name", ""),
            "loser": getattr(loser, "name", ""),
            "challenger_score": int(challenger_score),
            "boss_score": int(boss_score),
            "cleared": winner == challenger,
        }

        self.final_boss_log.append({
            "competition": self.final_boss_name,
            "competition_type": "final_boss",
            "round": "special_match",
            "team_a": getattr(challenger, "name", ""),
            "team_b": getattr(boss_team, "name", ""),
            "score_a": int(challenger_score),
            "score_b": int(boss_score),
            "winner": getattr(winner, "name", ""),
            "loser": getattr(loser, "name", ""),
        })
        self._latest_international_milestone_targets = [challenger]

        self._ensure_team_history_containers(challenger)
        if winner == challenger:
            self._add_competition_milestone(
                team=challenger,
                competition_name=self.final_boss_name,
                result="cleared",
                title=f"{self.final_boss_name} 撃破",
                detail=f"{self.final_boss_name}を撃破",
                club_history_text=f"{self.final_boss_name} 撃破",
            )
        else:
            self._add_competition_milestone(
                team=challenger,
                competition_name=self.final_boss_name,
                result="challenge",
                title=f"{self.final_boss_name} 挑戦",
                detail=f"{self.final_boss_name}に挑戦",
                club_history_text=f"{self.final_boss_name} 挑戦",
            )

    def _apply_final_boss_rewards(self, challenger: Team, cleared: bool):
        if cleared:
            challenger.money = int(getattr(challenger, "money", 0) + 10000000)
            challenger.popularity = min(100, int(getattr(challenger, "popularity", 50) + 10))
        else:
            challenger.money = int(getattr(challenger, "money", 0) + 1000000)
            challenger.popularity = min(100, int(getattr(challenger, "popularity", 50) + 2))

    def _run_final_boss_match(self):
        self.final_boss_result = {}
        self.final_boss_log = []

        if not getattr(self, "final_boss_enabled", True):
            return

        force_test_mode = bool(getattr(self, "final_boss_force_test_mode", False))
        challenger = self._latest_intercontinental_champion
        qualified = bool(self.final_boss_trigger.get("qualified"))

        if force_test_mode and not qualified:
            forced_user_team = self._get_user_team()
            if forced_user_team is not None:
                challenger = forced_user_team
                self._latest_intercontinental_champion = forced_user_team
                self.final_boss_trigger = {
                    "qualified": True,
                    "team_name": getattr(forced_user_team, "name", ""),
                    "team_id": getattr(forced_user_team, "team_id", None),
                    "from_competition": "FORCED_TEST",
                    "is_player_club": True,
                    "forced_test": True,
                }
                qualified = True
                print(f"[FINAL BOSS TEST] 強制発火テストを有効化: {forced_user_team.name}")

        if not qualified:
            return

        if challenger is None or not self._is_user_team(challenger):
            print(f"[{self.final_boss_name}] 挑戦クラブ解決に失敗したためスキップします。")
            return

        boss_team = self._create_final_boss_team()

        print(f"\n--- {self.final_boss_name} 開催（隠し要素） ---")
        print(f"挑戦クラブ: {challenger.name}")
        print(f"対戦相手: {boss_team.name}")

        result = Match(challenger, boss_team, is_playoff=True, competition_type="final_boss").simulate()
        if isinstance(result, tuple):
            winner = result[0]
            if len(result) >= 3:
                challenger_score = int(result[1])
                boss_score = int(result[2])
            else:
                challenger_score = int(getattr(challenger, "score", 0))
                boss_score = int(getattr(boss_team, "score", 0))
        else:
            winner = result
            challenger_score = int(getattr(challenger, "score", 0))
            boss_score = int(getattr(boss_team, "score", 0))

        loser = boss_team if winner == challenger else challenger

        print(
            f"{challenger.name} {challenger_score} - {boss_score} {boss_team.name} | "
            f"WIN: {getattr(winner, 'name', 'Unknown')} | competition_type=final_boss"
        )

        self._record_final_boss_result(
            challenger=challenger,
            boss_team=boss_team,
            winner=winner,
            loser=loser,
            challenger_score=challenger_score,
            boss_score=boss_score,
        )
        self._apply_final_boss_rewards(challenger, cleared=(winner == challenger))

        print(f"\n[{self.final_boss_name} 結果]")
        print(f"勝者: {getattr(winner, 'name', 'Unknown')}")
        if winner == challenger:
            print("[FINAL BOSS] プレイヤークラブがNBAドリームチームを撃破しました。隠し要素クリアです。")
            print("報酬 | 撃破報酬: 10,000,000 | 人気補正: +10")
        else:
            print("[FINAL BOSS] NBAドリームチームは健在です。再挑戦を待ちます。")
            print("報酬 | 参加報酬: 1,000,000 | 人気補正: +2")

    def _maintain_free_agent_market(self):
        print("Maintaining Free Agent Market...")

        if age_free_agents_one_year is not None:
            age_free_agents_one_year(self.free_agents)

        retired_fa = []
        if retire_stale_free_agents is not None:
            self.free_agents, retired_fa = retire_stale_free_agents(self.free_agents)

        if maintain_minimum_fa_pool is not None:
            self.free_agents = maintain_minimum_fa_pool(
                self.free_agents,
                target_minimum=40,
                generator_func=self._generate_fa_fallback_player,
            )

        if retired_fa:
            print(f"[FA-MARKET] Retired from FA market: {len(retired_fa)}")
        print(f"[FA-MARKET] Current active FA count: {len(self.free_agents)}")

    def _generate_fa_fallback_player(self):
        from basketball_sim.systems.generator import generate_international_free_agent

        player = generate_international_free_agent(nationality="Japan")
        player.contract_years_left = 0
        player.team_id = None
        player.fa_years_waiting = 0
        player.salary = max(getattr(player, "ovr", 0) * 10000, 350000)
        return player

    def _all_players(self) -> List[Player]:
        return self.free_agents + [p for t in self.teams for p in t.players]

    def _get_latest_completed_season_no(self) -> int:
        latest = 0
        for team in self.teams:
            for row in list(getattr(team, "history_seasons", []) or []):
                if not isinstance(row, dict):
                    continue
                season_value = row.get("season")
                if season_value is None:
                    season_value = row.get("season_index")
                try:
                    latest = max(latest, int(season_value))
                except Exception:
                    continue
        return max(1, latest)

    def _get_summer_national_cycle_year(self) -> int:
        latest_season = self._get_latest_completed_season_no()
        return ((latest_season - 1) % 4) + 1

    def _resolve_summer_national_event_type(self) -> str:
        cycle_year = self._get_summer_national_cycle_year()
        mapping = {
            1: "asia_cup",
            2: "friendly",
            3: "world_cup",
            4: "olympics",
        }
        return mapping.get(cycle_year, "friendly")

    def _get_summer_national_event_label(self, event_type: str) -> str:
        labels = {
            "asia_cup": "アジアカップ本戦",
            "friendly": "強化試合 / 強化合宿",
            "world_cup": "ワールドカップ本戦",
            "olympics": "オリンピック",
        }
        return labels.get(event_type or "", "夏代表大会")

    def _is_japan_national_team_eligible(self, player, event_type: str) -> bool:
        if player is None:
            return False

        nationality_values = [
            str(getattr(player, "nationality", "") or "").strip().lower(),
            str(getattr(player, "original_nationality", "") or "").strip().lower(),
        ]
        was_naturalized = bool(getattr(player, "was_naturalized", False))
        japan_like = {"japan", "japanese", "jp", "jpn", "local"}

        nationality_ok = was_naturalized or any(value in japan_like for value in nationality_values if value)
        if not nationality_ok:
            return False

        age = int(getattr(player, "age", 25) or 25)
        ovr = float(getattr(player, "ovr", 0) or 0)
        injury_games_left = int(getattr(player, "injury_games_left", 0) or 0)
        fatigue = float(getattr(player, "fatigue", 0) or 0)
        popularity = float(getattr(player, "popularity", 0) or 0)
        minutes_expected = float(getattr(player, "minutes_expected", 0) or 0)

        if injury_games_left > 0:
            return False
        if age < 18 or age > 37:
            return False
        if fatigue >= 90:
            return False

        min_ovr_map = {
            "friendly": 56,
            "asia_cup": 62,
            "world_cup": 65,
            "olympics": 67,
        }
        min_ovr = float(min_ovr_map.get(event_type or "", 58))
        young_prospect_ok = age <= 22 and ovr >= max(54.0, min_ovr - 4.0) and popularity >= 20
        baseline_ok = ovr >= min_ovr and (minutes_expected >= 8 or popularity >= 30)
        return bool(baseline_ok or young_prospect_ok)

    def _get_player_team_name(self, player) -> str:
        team_id = getattr(player, "team_id", None)
        for team in self.teams:
            if getattr(team, "team_id", None) == team_id:
                return str(getattr(team, "name", "") or "UNKNOWN")
        return "UNKNOWN"

    def _get_player_national_team_history_count(self, player) -> int:
        history = list(getattr(player, "national_team_history", []) or [])
        return len(history)

    def _get_summer_national_team_candidate_score(self, player, event_type: str) -> float:
        ovr = float(getattr(player, "ovr", 0) or 0)
        popularity = float(getattr(player, "popularity", 0) or 0)
        age = int(getattr(player, "age", 25) or 25)
        fatigue = float(getattr(player, "fatigue", 0) or 0)
        potential_cap_value = 0.0
        if hasattr(player, "get_potential_cap_value"):
            try:
                potential_cap_value = float(player.get_potential_cap_value())
            except Exception:
                potential_cap_value = 0.0

        score = ovr * 1.9
        score += popularity * 0.12
        score += potential_cap_value * 0.08
        score += float(getattr(player, "star_tier", 0) or 0) * 4.0
        score += float(getattr(player, "title_level", 0) or 0) * 2.0
        score += float(getattr(player, "breakout_count", 0) or 0) * 1.5
        national_team_caps = self._get_player_national_team_history_count(player)
        score += min(12.0, float(national_team_caps) * 2.0)
        score -= fatigue * 0.2

        if event_type in {"world_cup", "olympics"}:
            score += ovr * 0.25
            if age <= 22:
                score -= 2.0
        elif event_type == "friendly":
            if age <= 24:
                score += 6.0
            elif age >= 31:
                score -= 3.0

        return round(score, 2)

    def _normalize_position_for_national_team(self, player) -> str:
        pos = str(getattr(player, "position", "") or "").strip().upper()
        if pos in {"PG", "SG", "SF", "PF", "C"}:
            return pos
        return "UTIL"

    def _select_summer_national_team_candidates(self, event_type: str):
        eligible_players = []
        for team in self.teams:
            for player in list(getattr(team, "players", []) or []):
                if not self._is_japan_national_team_eligible(player, event_type):
                    continue
                eligible_players.append(player)

        scored_rows = [(player, self._get_summer_national_team_candidate_score(player, event_type)) for player in eligible_players]
        scored_rows.sort(
            key=lambda row: (
                row[1],
                float(getattr(row[0], "ovr", 0) or 0),
                float(getattr(row[0], "popularity", 0) or 0),
                -int(getattr(row[0], "age", 99) or 99),
                str(getattr(row[0], "name", "")),
            ),
            reverse=True,
        )

        required_slots = {"PG": 2, "SG": 2, "SF": 2, "PF": 2, "C": 2}
        selected = []
        used_ids = set()

        for position, required_count in required_slots.items():
            position_rows = [
                row for row in scored_rows
                if self._normalize_position_for_national_team(row[0]) == position
                and id(row[0]) not in used_ids
            ]
            for player, score in position_rows[:required_count]:
                selected.append((player, score))
                used_ids.add(id(player))

        for player, score in scored_rows:
            if len(selected) >= 12:
                break
            if id(player) in used_ids:
                continue
            selected.append((player, score))
            used_ids.add(id(player))

        selected.sort(
            key=lambda row: (
                row[1],
                float(getattr(row[0], "ovr", 0) or 0),
                float(getattr(row[0], "popularity", 0) or 0),
            ),
            reverse=True,
        )
        return [player for player, _score in selected[:12]]

    def _get_summer_national_event_fatigue_bonus(self, event_type: str) -> int:
        bonus_map = {
            "friendly": 4,
            "asia_cup": 9,
            "world_cup": 12,
            "olympics": 14,
        }
        return int(bonus_map.get(event_type or "", 5))

    def _get_summer_national_event_popularity_bonus(self, event_type: str) -> int:
        bonus_map = {
            "friendly": 1,
            "asia_cup": 3,
            "world_cup": 4,
            "olympics": 5,
        }
        return int(bonus_map.get(event_type or "", 1))

    def _get_summer_national_event_growth_base(self, event_type: str) -> float:
        growth_map = {
            "friendly": 0.10,
            "asia_cup": 0.30,
            "world_cup": 0.42,
            "olympics": 0.52,
        }
        return float(growth_map.get(event_type or "", 0.12))

    def _get_summer_national_event_growth_fields(self, player) -> list[str]:
        pos = str(getattr(player, "position", "") or "").strip().upper()
        if pos == "PG":
            return ["passing", "drive", "stamina"]
        if pos == "SG":
            return ["shoot", "three", "drive"]
        if pos == "SF":
            return ["shoot", "drive", "defense"]
        if pos in {"PF", "C"}:
            return ["rebound", "defense", "stamina"]
        return ["drive", "defense", "stamina"]

    def _apply_summer_national_event_effects(self, selected_players: list, event_type: str) -> None:
        if not selected_players:
            return

        fatigue_bonus = self._get_summer_national_event_fatigue_bonus(event_type)
        popularity_bonus = self._get_summer_national_event_popularity_bonus(event_type)
        growth_base = self._get_summer_national_event_growth_base(event_type)

        print("[Summer National Team Effects]")
        for player in selected_players:
            current_fatigue = float(getattr(player, "fatigue", 0) or 0)
            setattr(player, "fatigue", current_fatigue + fatigue_bonus)

            current_popularity = float(getattr(player, "popularity", 0) or 0)
            new_popularity = min(100.0, current_popularity + popularity_bonus)
            setattr(player, "popularity", new_popularity)

            age = int(getattr(player, "age", 25) or 25)
            work_ethic = float(getattr(player, "work_ethic", 50) or 50)
            basketball_iq = float(getattr(player, "basketball_iq", 50) or 50)
            competitiveness = float(getattr(player, "competitiveness", 50) or 50)

            potential_cap_value = 0.0
            if hasattr(player, "get_potential_cap_value"):
                try:
                    potential_cap_value = float(player.get_potential_cap_value())
                except Exception:
                    potential_cap_value = 0.0

            age_factor = 1.0
            if age <= 22:
                age_factor = 1.18
            elif age >= 31:
                age_factor = 0.82

            mentality_factor = 1.0 + ((work_ethic + basketball_iq + competitiveness) - 150.0) / 600.0
            cap_factor = 1.0 + max(0.0, potential_cap_value - float(getattr(player, "ovr", 0) or 0)) / 300.0

            growth_value = growth_base * age_factor * mentality_factor * cap_factor

            growth_fields = self._get_summer_national_event_growth_fields(player)
            total_delta = 0
            for field_name in growth_fields:
                current_value = int(getattr(player, field_name, 0) or 0)
                delta = int(round(growth_value))
                new_value = max(1, min(99, current_value + delta))
                setattr(player, field_name, new_value)
                total_delta += new_value - current_value

            current_ovr = int(getattr(player, "ovr", 0) or 0)
            ovr_gain = int(round(total_delta / max(1, len(growth_fields))))
            new_ovr = max(1, min(99, current_ovr + ovr_gain))
            setattr(player, "ovr", new_ovr)

            team_name = self._get_player_team_name(player)
            print(
                f" {getattr(player, 'name', 'UNKNOWN')} | Team:{team_name} | "
                f"fatigue+={fatigue_bonus} | popularity+={popularity_bonus} | ovr+={new_ovr - current_ovr}"
            )

    def _run_summer_national_team_event(self):
        self.summer_national_event_result = {}
        self.summer_national_event_log = []

        if not getattr(self, "summer_national_event_enabled", True):
            return

        cycle_year = self._get_summer_national_cycle_year()
        event_type = self._resolve_summer_national_event_type()
        event_label = self._get_summer_national_event_label(event_type)

        self.summer_national_event_name = event_label
        selected_players = self._select_summer_national_team_candidates(event_type)

        self.summer_national_event_result = {
            "cycle_year": cycle_year,
            "event_type": event_type,
            "event_label": event_label,
            "implemented": True,
            "roster_count": len(selected_players),
            "roster_names": [getattr(player, "name", "UNKNOWN") for player in selected_players],
        }
        self.summer_national_event_log.append(
            f"cycle_year={cycle_year} | event_type={event_type} | event_label={event_label} | roster_count={len(selected_players)}"
        )

        print(f"\n--- 夏代表大会帯 ---")
        print(f"[Summer National Team Event] cycle_year={cycle_year} | {event_label}")

        if selected_players:
            club_counts = {}
            career_rows = []
            current_season_no = max(1, int(self._get_latest_completed_season_no() or 1))
            print("[Summer National Team Roster]")
            for idx, player in enumerate(selected_players, start=1):
                team_name = self._get_player_team_name(player)
                club_counts[team_name] = club_counts.get(team_name, 0) + 1
                pos = str(getattr(player, "position", "-") or "-")
                age = int(getattr(player, "age", 0) or 0)
                ovr = int(getattr(player, "ovr", 0) or 0)
                score = self._get_summer_national_team_candidate_score(player, event_type)
                prior_caps = self._get_player_national_team_history_count(player)

                if hasattr(player, "add_national_team_history"):
                    try:
                        player.add_national_team_history({
                            "season": current_season_no,
                            "round": 0,
                            "window_key": "summer",
                            "window_type": event_type,
                            "event_label": event_label,
                            "country": "Japan",
                            "selected": True,
                            "selection_score": score,
                        })
                    except Exception:
                        pass

                caps = self._get_player_national_team_history_count(player)
                latest_label = event_label
                exp_tag = " | NT_EXP" if prior_caps >= 1 else ""
                career_rows.append((getattr(player, "name", "UNKNOWN"), caps, latest_label))
                print(
                    f" {idx:>2}. {getattr(player, 'name', 'UNKNOWN'):<18} "
                    f"{pos:<2} Age:{age:<2} OVR:{ovr:<2} "
                    f"Team:{team_name} | score={score:.2f} | caps={caps}{exp_tag}"
                )
            print("[Summer National Team Career Summary]")
            for idx, (player_name, caps, latest_label) in enumerate(career_rows, start=1):
                print(f" {idx:>2}. {player_name:<18} caps={caps} | latest={latest_label}")
            print("[Summer National Team Club Summary]")
            for idx, (team_name, count) in enumerate(sorted(club_counts.items(), key=lambda row: (-row[1], row[0]))[:8], start=1):
                print(f" {idx:>2}. {team_name:<24} selected={count}")
            self._apply_summer_national_event_effects(selected_players, event_type)
        else:
            print("※ 今回は代表候補を選出できませんでした。")


    def _age_players(self):

        for p in self._all_players():
            if getattr(p, "is_retired", False):
                continue
            p.age += 1
            p.years_pro += 1

            if not hasattr(p, "league_years"):
                p.league_years = getattr(p, "years_pro", 0)
            p.league_years += 1

    def _get_team_wins(self, team: Team) -> int:
        return getattr(team, "last_season_wins", getattr(team, "regular_wins", 15))

    def _get_team_by_player(self, player: Player):
        for team in self.teams:
            if player in team.players:
                return team
        return None


    def _is_asia_or_naturalized_player(self, player: Player) -> bool:
        if hasattr(player, "is_asia_or_naturalized_player"):
            try:
                return bool(player.is_asia_or_naturalized_player())
            except Exception:
                pass
        return getattr(player, "nationality", "Japan") in ("Asia", "Naturalized")

    def _count_team_asia_naturalized_players(self, team: Team, exclude_player: Optional[Player] = None) -> int:
        count = 0
        for player in getattr(team, "players", []):
            if exclude_player is not None and player is exclude_player:
                continue
            if self._is_asia_or_naturalized_player(player):
                count += 1
        return count

    def _can_naturalize_player_for_team(self, player: Player) -> bool:
        team = self._get_team_by_player(player)
        if team is None:
            return False
        return self._count_team_asia_naturalized_players(team, exclude_player=player) < 1

    def _is_user_team(self, team: Team) -> bool:
        return bool(getattr(team, "is_user_team", False))

    def _get_user_team(self) -> Optional[Team]:
        for team in self.teams:
            if self._is_user_team(team):
                return team
        return None

    def _prompt_yes_no(self, message: str, default: str = "y") -> bool:
        default = default.lower().strip()
        suffix = "[Y/n]" if default == "y" else "[y/N]"

        while True:
            try:
                raw = input(f"{message} {suffix}: ").strip().lower()
            except EOFError:
                # 非対話実行（テスト/自動進行）では入力が取得できないことがある
                raw = default

            if raw == "":
                raw = default

            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False

            print("y か n で入力してください。")

    def _user_team_resign_decision(
        self,
        team: Team,
        player: Player,
        new_salary: int,
        desired_years: int,
        resign_score: float,
        threshold: float,
        current_team_salary: int,
        salary_cap: int,
    ) -> bool:
        print("\n[USER RE-SIGN]")
        print(
            f"{player.name} | {player.position} | Age:{player.age} | "
            f"OVR:{player.ovr} | GP:{player.games_played}"
        )
        print(
            f"Current Salary: ${getattr(player, 'salary', 0):,} | "
            f"Proposed: ${new_salary:,} / {desired_years} years"
        )
        print(
            f"Re-sign Score: {resign_score:.1f} | "
            f"Base Threshold: {threshold:.1f}"
        )
        print(
            f"Team Payroll After Sign: ${current_team_salary:,} | "
            f"Cap Limit(120%): ${int(salary_cap * 1.2):,}"
        )

        if current_team_salary > salary_cap * 1.2:
            print(
                f"[USER-RE-SIGN] {team.name} cannot offer to {player.name} "
                f"because payroll would exceed 120% cap."
            )
            return False

        return self._prompt_yes_no(
            f"{player.name} にこの条件で再契約オファーを出しますか？",
            default="y"
        )

    def _get_new_coach_style(self, old_style: str, team: Team) -> str:
        wins = self._get_team_wins(team)

        if wins <= 10:
            candidates = ["offense", "defense", "development", "balanced"]
            weights = [0.28, 0.28, 0.24, 0.20]
        elif wins <= 14:
            candidates = ["offense", "defense", "development", "balanced"]
            weights = [0.25, 0.25, 0.20, 0.30]
        else:
            candidates = ["offense", "defense", "development", "balanced"]
            weights = [0.18, 0.18, 0.14, 0.50]

        candidates = [c for c in candidates if c != old_style]

        base_map = {
            "offense": weights[0],
            "defense": weights[1],
            "development": weights[2],
            "balanced": weights[3],
        }
        candidate_weights = [base_map[c] for c in candidates]

        return random.choices(candidates, weights=candidate_weights, k=1)[0]

    def _review_team_coaches(self):
        print("\n[Coach Review]")

        for team in self.teams:
            current_style = getattr(team, "coach_style", "balanced")
            wins = self._get_team_wins(team)

            if wins <= 8:
                change_prob = 0.70
            elif wins <= 12:
                change_prob = 0.50
            elif wins <= 16:
                change_prob = 0.28
            elif wins <= 20:
                change_prob = 0.15
            else:
                change_prob = 0.08

            if random.random() < change_prob:
                new_style = self._get_new_coach_style(current_style, team)
                team.coach_style = new_style
                print(
                    f"[COACH-CHANGE] {team.name} | wins:{wins} | "
                    f"{current_style} -> {new_style}"
                )
            else:
                print(
                    f"[COACH-KEEP]   {team.name} | wins:{wins} | "
                    f"{current_style}"
                )

    def _calculate_resign_score(self, player: Player, team: Team, new_salary: int) -> float:
        current_salary = max(1, getattr(player, "salary", 1))
        salary_ratio = new_salary / current_salary
        salary_basis = max(0, min(100, (salary_ratio - 0.5) * 100))
        salary_score = salary_basis * 0.55

        l_score = {1: 100, 2: 50, 3: 0}.get(getattr(team, "league_level", 3), 0)
        w_score = (self._get_team_wins(team) / 30) * 100
        p_score = getattr(team, "popularity", 50)
        team_basis = (l_score * 0.5) + (w_score * 0.3) + (p_score * 0.2)
        team_score = team_basis * 0.25

        sorted_players = sorted(team.players, key=lambda p: p.ovr, reverse=True)
        rank_map = {p.player_id: rank for rank, p in enumerate(sorted_players, 1)}
        rank = rank_map.get(player.player_id, 99)

        if rank <= 3:
            role_basis = 100
        elif rank <= 5:
            role_basis = 85
        elif rank <= 9:
            role_basis = 50
        else:
            role_basis = 10

        gp = getattr(player, "games_played", 0)
        if gp < 10:
            if player.ovr >= 80:
                role_basis -= 5
            elif player.ovr >= 75:
                role_basis -= 15
            else:
                role_basis -= 30

        role_basis = max(0, min(100, role_basis))
        loyalty_score = role_basis * 0.20

        base_score = salary_score + team_score + loyalty_score

        retention_bonus = 0.0
        if player.ovr >= 85:
            retention_bonus = 35.0
        elif player.ovr >= 80:
            retention_bonus = 30.0
        elif player.ovr >= 75:
            retention_bonus = 25.0
        elif player.ovr >= 70:
            retention_bonus = 12.0

        return base_score + retention_bonus

    def _resign_players(self):
        print("Conducting Re-signing...")
        salary_cap = 15_000_000

        user_teams = [team for team in self.teams if self._is_user_team(team)]
        if not user_teams:
            print("[USER-RE-SIGN] User team not found.")
        else:
            for user_team in user_teams:
                expiring_preview = [
                    p for p in user_team.players
                    if getattr(p, "contract_years_left", 0) == 1
                ]
                expiring_preview.sort(key=lambda p: (p.ovr, getattr(p, "games_played", 0)), reverse=True)

                print(f"\n=== USER TEAM RE-SIGN: {user_team.name} ===")
                print(f"再契約対象選手: {len(expiring_preview)}人")

                if not expiring_preview:
                    print("今オフは再契約確認対象の選手はいません。")
                else:
                    print("[対象一覧]")
                    for i, p in enumerate(expiring_preview, 1):
                        desired_salary = getattr(p, "desired_salary", getattr(p, "salary", 0))
                        desired_years = getattr(p, "desired_years", 3)
                        print(
                            f"{i}. {p.name:<15} {p.position} "
                            f"OVR:{p.ovr} Age:{p.age} GP:{getattr(p, 'games_played', 0)} "
                            f"Current:${getattr(p, 'salary', 0):,} "
                            f"Ask:${desired_salary:,}/{desired_years}y"
                        )

        for team in self.teams:
            expiring_players = [
                p for p in team.players
                if getattr(p, "contract_years_left", 0) == 1
            ]

            if not expiring_players:
                continue

            expiring_players.sort(
                key=lambda p: (p.ovr, getattr(p, "games_played", 0)),
                reverse=True
            )
            lost_70_plus_count = 0

            for player in expiring_players:
                if ensure_contract_fields is not None:
                    ensure_contract_fields(player)

                if calculate_desired_contract_terms is not None:
                    desired_salary, desired_years = calculate_desired_contract_terms(player)
                else:
                    current_salary = max(getattr(player, "salary", 0), player.ovr * 10000)
                    desired_salary = max(current_salary, player.ovr * 10000)
                    if player.age <= 24:
                        desired_years = 4
                    elif player.age <= 29:
                        desired_years = 3
                    elif player.age <= 33:
                        desired_years = 2
                    else:
                        desired_years = 1

                player.desired_salary = int(desired_salary)
                player.desired_years = int(desired_years)
                player.contract_total_years = max(
                    getattr(player, "contract_total_years", 0),
                    getattr(player, "contract_years_left", 0)
                )
                player.last_contract_team_id = getattr(team, "team_id", None)

                current_team_salary = (
                    sum(getattr(p, "salary", 0) for p in team.players)
                    - getattr(player, "salary", 0)
                    + player.desired_salary
                )

                if evaluate_resign_offer is not None:
                    result = evaluate_resign_offer(
                        player=player,
                        team=team,
                        offered_salary=player.desired_salary,
                        offered_years=player.desired_years,
                    )
                    resign_score = float(result.get("score", 0.0))
                    threshold = float(result.get("threshold", 50.0))
                    accepted = bool(result.get("accepted", False))
                else:
                    resign_score = self._calculate_resign_score(player, team, player.desired_salary)
                    threshold = 50.0
                    if player.ovr >= 70 and lost_70_plus_count >= 1:
                        threshold -= 15.0 * lost_70_plus_count

                    accepted = resign_score >= threshold
                    if player.ovr >= 85 and resign_score >= 20.0:
                        accepted = True
                    elif player.ovr >= 80 and resign_score >= 35.0:
                        accepted = True
                    elif player.ovr >= 75 and resign_score >= 45.0:
                        accepted = True

                if self._is_user_team(team):
                    user_offers = self._user_team_resign_decision(
                        team=team,
                        player=player,
                        new_salary=player.desired_salary,
                        desired_years=player.desired_years,
                        resign_score=resign_score,
                        threshold=threshold,
                        current_team_salary=current_team_salary,
                        salary_cap=salary_cap,
                    )

                    if not user_offers:
                        accepted = False
                        if player.ovr >= 70:
                            lost_70_plus_count += 1
                        print(
                            f"[USER-RE-SIGN] {team.name} chose not to offer {player.name} "
                            f"(OVR:{player.ovr})"
                        )
                        continue

                if accepted:
                    if current_team_salary > salary_cap * 1.2:
                        print(
                            f"[RE-SIGN] {team.name} could not re-sign {player.name} "
                            f"(OVR:{player.ovr}) due to salary cap (over 120%)"
                        )
                        accepted = False
                        if player.ovr >= 70:
                            lost_70_plus_count += 1
                    else:
                        if apply_resign_offer is not None:
                            apply_resign_offer(
                                player=player,
                                team=team,
                                salary=player.desired_salary,
                                years=player.desired_years,
                            )
                        else:
                            player.salary = int(player.desired_salary)
                            player.contract_years_left = int(player.desired_years)
                            player.contract_total_years = int(player.desired_years)
                            player.last_contract_team_id = getattr(team, "team_id", None)

                        self.re_signed_player_ids.add(player.player_id)
                        print(
                            f"[RE-SIGN] {team.name} re-signed {player.name} "
                            f"(OVR:{player.ovr}) for ${int(player.desired_salary):,} / "
                            f"{int(player.desired_years)} years | score={resign_score:.1f}"
                        )

                if not accepted:
                    if player.ovr >= 70:
                        lost_70_plus_count += 1
                    print(
                        f"[RE-SIGN] {team.name} did not re-sign {player.name} "
                        f"(OVR:{player.ovr}) | score={resign_score:.1f}"
                    )

    def _reset_team_stats(self):
        for team in self.teams:
            if hasattr(team, "reset_season_stats"):
                team.reset_season_stats()

    def _reset_player_stats(self):
        for p in self._all_players():
            if hasattr(p, "reset_season_stats"):
                p.reset_season_stats()

    def _decrease_contracts(self):
        if advance_contract_years is not None:
            for team in self.teams:
                remaining_players, leaving_players = advance_contract_years(
                    players=list(team.players),
                    skip_player_ids=self.re_signed_player_ids,
                )
                team.players = remaining_players
                for p in leaving_players:
                    p.team_id = None
                    self.free_agents.append(p)
            return

        for team in self.teams:
            leaving = []
            for player in team.players:
                if player.player_id in self.re_signed_player_ids:
                    continue

                if ensure_contract_fields is not None:
                    ensure_contract_fields(player)

                player.contract_years_left = getattr(player, "contract_years_left", 1) - 1
                if player.contract_years_left <= 0:
                    leaving.append(player)

            for p in leaving:
                team.remove_player(p)
                self.free_agents.append(p)

    def _player_progression(self):
        print("Processing Player Growth and Decline...")

        for team in self.teams:
            dev_logs = DevelopmentSystem.apply_team_development(
                team=team,
                total_season_games=30
            )
            for log in dev_logs:
                print(log)

        for player in self.free_agents:
            if getattr(player, "is_retired", False):
                continue

            holder = type(
                "FreeAgentHolder",
                (),
                {"players": [player], "coach_style": "balanced", "strategy": "balanced"}
            )()

            dev_logs = DevelopmentSystem.apply_team_development(
                team=holder,
                total_season_games=30
            )
            for log in dev_logs:
                print(f"{log} [FA]")

    def _process_naturalization(self):
        print("Processing Naturalization...")

        for p in self._all_players():
            if getattr(p, "is_retired", False):
                continue

            nat = getattr(p, "nationality", "Japan")
            if nat != "Foreign":
                continue

            team = self._get_team_by_player(p)
            if team is None:
                # Free agent stateでの帰化は行わない。チーム在籍選手のみ対象。
                continue

            if not self._can_naturalize_player_for_team(p):
                print(
                    f"[NATURALIZE-SKIP] {p.name} | Team:{team.name} already has Asia/Naturalized slot filled"
                )
                continue

            years_in_league = getattr(p, "league_years", getattr(p, "years_pro", 0))
            if years_in_league < 7:
                continue

            chance = 0.02

            if getattr(p, "had_naturalized_history", False):
                chance = 0.85

            if random.random() < chance:
                p.nationality = "Naturalized"
                p.had_naturalized_history = True
                print(
                    f"[NATURALIZE] {p.name} became Naturalized | "
                    f"Team:{team.name} | Years in League:{years_in_league} | Chance:{chance:.2f}"
                )

    def _remove_player_from_current_place(self, player: Player):
        removed = False

        for team in self.teams:
            if player in team.players:
                team.remove_player(player)
                removed = True
                break

        if not removed and player in self.free_agents:
            self.free_agents.remove(player)

    def _build_japanese_reborn_prospect(self, retired_player: Player):
        from basketball_sim.systems.generator import generate_draft_prospect

        target_ovr = max(50, min(65, int(retired_player.ovr * 0.75)))

        new_prospect = generate_draft_prospect(
            age_override=18,
            base_ovr_override=max(53, target_ovr)
        )

        new_prospect.position = retired_player.position
        new_prospect.height_cm = retired_player.height_cm
        new_prospect.weight_kg = retired_player.weight_kg
        new_prospect.nationality = "Japan"

        new_prospect.reborn_from = retired_player.name
        new_prospect.is_reborn = True
        new_prospect.reborn_type = "jp"
        new_prospect.draft_origin_type = "reborn"
        new_prospect.draft_priority_bonus = max(
            getattr(new_prospect, "draft_priority_bonus", 0),
            2 if retired_player.ovr >= 78 else 0
        )
        new_prospect.draft_profile_label = f"転生新人 / 元:{retired_player.name}"

        if getattr(retired_player, "had_naturalized_history", False):
            new_prospect.had_naturalized_history = True

        return new_prospect

    def _store_reincarnation_candidate(self, retired_player: Player):
        peak = getattr(retired_player, "peak_ovr", getattr(retired_player, "ovr", 0))
        if peak < 82 and not getattr(retired_player, "is_hall_of_famer", False) and not getattr(retired_player, "is_icon", False):
            return

        retired_player.reincarnation_delay = random.randint(1, 3)
        self.retired_star_pool.append(retired_player)

    def _store_international_reborn(self, retired_player: Player):
        nat = getattr(retired_player, "nationality", "Japan")

        if nat in ("Foreign", "Naturalized"):
            market_key = "Foreign"
        elif nat == "Asia":
            market_key = "Asia"
        else:
            return

        self.international_reborn_pool[market_key].append({
            "from_name": retired_player.name,
            "position": retired_player.position,
            "height_cm": retired_player.height_cm,
            "weight_kg": retired_player.weight_kg,
            "ovr": retired_player.ovr,
            "archetype": getattr(retired_player, "archetype", "Balanced"),
            "had_naturalized_history": getattr(retired_player, "had_naturalized_history", False),
        })

        print(f"[REBORN-INTL] {retired_player.name} stored for future {market_key} market")

    def _retire_and_reincarnate(self):
        print("Processing Retirements...")

        for p in list(self._all_players()):
            if getattr(p, "is_retired", False):
                continue

            retire_prob = 0.0
            if p.age >= 39:
                retire_prob = 0.85
            elif p.age >= 37:
                retire_prob = 0.40
            elif p.age >= 35:
                retire_prob = 0.15

            if retire_prob <= 0:
                continue

            if p.ovr <= 65:
                retire_prob += 0.25
            elif p.ovr >= 80:
                retire_prob -= 0.15

            if getattr(p, "games_played", 0) < 5:
                retire_prob += 0.20
            elif getattr(p, "games_played", 0) >= 25:
                retire_prob -= 0.10

            retire_prob = max(0.01, min(0.99, retire_prob))

            if random.random() >= retire_prob:
                continue

            team_before_retire = self._get_team_by_player(p)

            if hasattr(p, "add_career_entry"):
                season_value = max(1, getattr(p, "years_pro", 0))
                retire_team_name = team_before_retire.name if team_before_retire is not None else "Free Agent"
                p.add_career_entry(
                    season=season_value,
                    team_name=retire_team_name,
                    event="Retire",
                    note=f"Age {p.age}"
                )

            if hasattr(p, "calculate_hall_of_fame_score"):
                hof_score = p.calculate_hall_of_fame_score()
                peak_ovr = getattr(p, "peak_ovr", getattr(p, "ovr", 0))
                print(
                    f"[RETIRE-CHECK] {p.name} | HOF Score:{hof_score:.2f} | "
                    f"Peak OVR:{peak_ovr} | Career PTS:{getattr(p, 'career_points', 0)} | "
                    f"Career GP:{getattr(p, 'career_games_played', 0)}"
                )

            if hasattr(p, "evaluate_hall_of_fame"):
                hof_result = p.evaluate_hall_of_fame()
                if hof_result:
                    print(
                        f"[HALL OF FAME] {p.name} inducted | "
                        f"score={getattr(p, 'hall_of_fame_score', 0):.2f} | "
                        f"reason={getattr(p, 'hall_of_fame_reason', '')}"
                    )

            if team_before_retire is not None and hasattr(team_before_retire, "maybe_add_club_legend"):
                before_count = len(getattr(team_before_retire, "club_legends", []))
                team_before_retire.maybe_add_club_legend(p)
                after_count = len(getattr(team_before_retire, "club_legends", []))
                if after_count > before_count:
                    print(
                        f"[CLUB LEGEND] {p.name} added to {team_before_retire.name} legends | "
                        f"score={team_before_retire.club_legends[0].get('legacy_score', 0):.2f}"
                    )

            p.is_retired = True
            print(
                f"[RETIRE] {p.name} / Age:{p.age} / OVR:{p.ovr} / Nat:{getattr(p, 'nationality', 'Japan')}"
            )

            self._store_reincarnation_candidate(p)
            self._remove_player_from_current_place(p)

            nat = getattr(p, "nationality", "Japan")

            if nat == "Japan":
                if random.random() < 0.60:
                    new_prospect = self._build_japanese_reborn_prospect(p)
                    self.draft_pool.append(new_prospect)
                    print(f"[REBORN-JP] {p.name} -> {new_prospect.name}")
            else:
                self._store_international_reborn(p)

    def _make_international_player(self, market_type: str, reborn_data=None):
        from basketball_sim.systems.generator import generate_international_free_agent

        nationality = "Foreign" if market_type == "Foreign" else "Asia"

        if reborn_data is not None:
            target_ovr = max(58, min(78, int(reborn_data["ovr"] * 0.82)))
            naturalize_bonus_chance = 0.0
            if reborn_data.get("had_naturalized_history", False) and nationality == "Foreign":
                naturalize_bonus_chance = 0.83

            player = generate_international_free_agent(
                nationality=nationality,
                reborn_profile={
                    "position": reborn_data["position"],
                    "height_cm": reborn_data["height_cm"],
                    "weight_kg": reborn_data["weight_kg"],
                    "archetype": reborn_data.get("archetype", "Balanced"),
                    "target_ovr": target_ovr,
                    "naturalize_bonus_chance": naturalize_bonus_chance,
                }
            )
            player.reborn_from = reborn_data["from_name"]
            player.is_international_reborn = True
            player.had_naturalized_history = reborn_data.get("had_naturalized_history", False)
            return player

        return generate_international_free_agent(nationality=nationality)

    def _refresh_international_market(self):
        print("Refreshing International Market...")

        foreign_to_add = 3
        asia_to_add = 1

        added_players = []

        for _ in range(foreign_to_add):
            reborn_data = None
            if self.international_reborn_pool["Foreign"]:
                reborn_data = self.international_reborn_pool["Foreign"].pop(0)

            player = self._make_international_player("Foreign", reborn_data)
            player.contract_years_left = random.randint(1, 2)
            player.salary = max(player.ovr * 12000, 500000)
            self.free_agents.append(player)
            added_players.append((player, reborn_data, "Foreign"))

        for _ in range(asia_to_add):
            reborn_data = None
            if self.international_reborn_pool["Asia"]:
                reborn_data = self.international_reborn_pool["Asia"].pop(0)

            player = self._make_international_player("Asia", reborn_data)
            player.contract_years_left = random.randint(1, 2)
            player.salary = max(player.ovr * 11000, 450000)
            self.free_agents.append(player)
            added_players.append((player, reborn_data, "Asia"))

        for player, reborn_data, market_type in added_players:
            if reborn_data is not None:
                print(
                    f"[INTL-REBORN] {player.name} | {market_type} | "
                    f"OVR:{player.ovr} | from:{reborn_data['from_name']}"
                )
            else:
                print(f"[INTL-NEW] {player.name} | {market_type} | OVR:{player.ovr}")

    def _build_top_reincarnation_prospect(self, profile: dict) -> Optional[Player]:
        from basketball_sim.systems.generator import generate_draft_prospect

        origin_player_id = profile.get("origin_player_id")
        origin_player = None
        for p in self.retired_star_pool:
            if getattr(p, "player_id", None) == origin_player_id:
                origin_player = p
                break

        if origin_player is None:
            return None

        new_prospect = generate_draft_prospect(
            age_override=profile.get("age", 20),
            base_ovr_override=max(55, int(profile.get("ovr", 68))),
        )

        new_prospect.position = getattr(origin_player, "position", new_prospect.position)
        new_prospect.height_cm = getattr(origin_player, "height_cm", getattr(new_prospect, "height_cm", 190))
        new_prospect.weight_kg = getattr(origin_player, "weight_kg", getattr(new_prospect, "weight_kg", 85))
        new_prospect.nationality = "Japan"
        new_prospect.age = int(profile.get("age", 20))
        new_prospect.ovr = int(profile.get("ovr", new_prospect.ovr))
        new_prospect.potential = profile.get("potential", "A")

        new_prospect.is_reborn = True
        new_prospect.reborn_type = "jp"
        new_prospect.reborn_from = getattr(origin_player, "name", "Unknown")
        new_prospect.draft_origin_type = "reborn"
        new_prospect.draft_priority_bonus = max(getattr(new_prospect, "draft_priority_bonus", 0), 4)
        entry_type = profile.get("entry_type", "college")
        new_prospect.draft_profile_label = f"転生新人 / 元:{new_prospect.reborn_from} / {entry_type}"

        return new_prospect

    def _build_homage_prospect(self, profile: dict) -> Player:
        from basketball_sim.systems.generator import generate_special_draft_prospect, generate_draft_prospect

        try:
            new_prospect = generate_special_draft_prospect()
        except Exception:
            new_prospect = generate_draft_prospect(
                age_override=profile.get("age", 21),
                base_ovr_override=max(68, int(profile.get("ovr", 72))),
            )

        new_prospect.age = int(profile.get("age", 21))
        new_prospect.ovr = int(profile.get("ovr", getattr(new_prospect, "ovr", 72)))
        new_prospect.potential = profile.get("potential", "A")
        new_prospect.draft_origin_type = "special"
        new_prospect.reborn_type = "special"
        new_prospect.is_featured_prospect = True
        new_prospect.draft_priority_bonus = max(getattr(new_prospect, "draft_priority_bonus", 0), 8)

        archetype = profile.get("archetype", "Special Prospect")
        label_map = {
            "Sniper": "天才シューター",
            "Floor General": "天才ポイントガード",
            "Defensive Monster": "守備職人",
            "Athletic Freak": "怪物アスリート",
            "Point Forward": "大型ポイントフォワード",
            "Stretch Big": "ストレッチビッグ",
        }
        # 呼び名（固定）: 完全架空選手は「通常新人」。オマージュ枠はその亜種として扱う。
        new_prospect.draft_profile_label = f"通常新人 / オマージュ:{label_map.get(archetype, archetype)}"
        return new_prospect

    def _build_legend_rookie_prospect(self, profile: dict) -> Player:
        from basketball_sim.systems.generator import generate_draft_prospect

        new_prospect = generate_draft_prospect(
            age_override=profile.get("age", 21),
            base_ovr_override=max(62, int(profile.get("ovr", 70))),
        )

        new_prospect.name = str(profile.get("name") or new_prospect.name)
        pos = str(profile.get("position") or getattr(new_prospect, "position", "SG") or "SG")
        new_prospect.position = pos
        new_prospect.age = int(profile.get("age", 21))
        new_prospect.ovr = int(profile.get("ovr", getattr(new_prospect, "ovr", 70)))
        new_prospect.potential = profile.get("potential", "A")

        archetype = str(profile.get("archetype", "") or "")
        new_prospect.archetype = archetype or getattr(new_prospect, "archetype", "")

        new_prospect.draft_origin_type = "legend_rookie"
        new_prospect.draft_priority_bonus = max(getattr(new_prospect, "draft_priority_bonus", 0), 6)

        label_map = {
            "Sniper": "神シューター",
            "Floor General": "伝説の司令塔",
            "Defensive Monster": "守備のレジェンド",
            "Athletic Freak": "怪物ルーキー",
        }
        new_prospect.draft_profile_label = f"レジェンドルーキー / {label_map.get(archetype, '特別枠')}"
        return new_prospect

    def _build_generic_top_prospect(self, profile: dict) -> Player:
        from basketball_sim.systems.generator import generate_draft_prospect

        new_prospect = generate_draft_prospect(
            age_override=profile.get("age", 20),
            base_ovr_override=max(60, int(profile.get("ovr", 68))),
        )
        new_prospect.age = int(profile.get("age", 20))
        new_prospect.ovr = int(profile.get("ovr", getattr(new_prospect, "ovr", 68)))
        new_prospect.potential = profile.get("potential", "B")
        new_prospect.draft_priority_bonus = max(getattr(new_prospect, "draft_priority_bonus", 0), 1)
        if not hasattr(new_prospect, "draft_profile_label"):
            new_prospect.draft_profile_label = "通常新人"
        return new_prospect

    def _build_player_from_top_profile(self, profile: dict) -> Optional[Player]:
        profile_type = profile.get("type", "generic")

        if profile_type == "reincarnation":
            return self._build_top_reincarnation_prospect(profile)
        if profile_type == "homage":
            return self._build_homage_prospect(profile)
        if profile_type == "legend_rookie":
            return self._build_legend_rookie_prospect(profile)
        return self._build_generic_top_prospect(profile)

    def _generate_draft_pool(self):
        from basketball_sim.systems.generator import generate_draft_prospect

        profiles = generate_top_prospects(self.retired_star_pool)
        self.top_prospects = []

        for profile in profiles:
            player = self._build_player_from_top_profile(profile)
            if player is None:
                continue
            self.draft_pool.append(player)
            self.top_prospects.append(player)

        needed = len(self.teams) - len(self.draft_pool)
        for _ in range(max(0, needed)):
            new_p = generate_draft_prospect()
            self.draft_pool.append(new_p)

        for p in self.draft_pool:
            if getattr(p, "draft_origin_type", "") == "special":
                if not hasattr(p, "draft_profile_label"):
                    p.draft_profile_label = "目玉新人"
                if not hasattr(p, "draft_priority_bonus"):
                    p.draft_priority_bonus = 8
                continue

            if getattr(p, "is_reborn", False):
                from_name = getattr(p, "reborn_from", "Unknown")
                if not hasattr(p, "draft_profile_label"):
                    p.draft_profile_label = f"転生新人 / 元:{from_name}"
                p.draft_origin_type = "reborn"
                if not hasattr(p, "draft_priority_bonus"):
                    p.draft_priority_bonus = 2
            else:
                if not hasattr(p, "draft_profile_label"):
                    p.draft_profile_label = "通常新人"
                p.draft_origin_type = "normal"
                if not hasattr(p, "draft_priority_bonus"):
                    p.draft_priority_bonus = 0

    def _normalize_scout_dispatch(self, raw_dispatch: str) -> str:
        valid = {"highschool", "college", "overseas"}
        if raw_dispatch in valid:
            return raw_dispatch
        return "college"

    def _get_scout_dispatch_label(self, dispatch: str) -> str:
        label_map = {
            "highschool": "High School",
            "college": "College",
            "overseas": "Overseas",
        }
        return label_map.get(dispatch, "College")

    def _set_team_scout_dispatch(self, team: Team, dispatch: str):
        dispatch = self._normalize_scout_dispatch(dispatch)
        if hasattr(team, "set_scout_dispatch"):
            team.set_scout_dispatch(dispatch)
        else:
            team.scout_dispatch = dispatch

    def _choose_user_scout_dispatch(self, team: Team):
        print("\n=== Scout Dispatch ===")
        print("来年のドラフト候補調査先を選んでください")
        print("1. 高校")
        print("2. 大学")
        print("3. 海外")

        mapping = {
            "1": "highschool",
            "2": "college",
            "3": "overseas",
        }

        while True:
            try:
                raw = input("番号: ").strip()
            except EOFError:
                raw = "2"  # college（安定・無難）
            if raw in mapping:
                dispatch = mapping[raw]
                self._set_team_scout_dispatch(team, dispatch)
                print(
                    f"[SCOUT-DISPATCH] {team.name} -> "
                    f"{self._get_scout_dispatch_label(dispatch)}"
                )
                return
            print("正しい番号を入力してください。")

    def _choose_ai_scout_dispatch(self, team: Team) -> str:
        coach_style = getattr(team, "coach_style", "balanced")
        strategy = getattr(team, "strategy", "balanced")

        if coach_style == "development":
            return "highschool"
        if strategy == "run_and_gun":
            return "overseas"
        if strategy == "inside":
            return "college"
        if coach_style == "offense":
            return random.choices(["college", "overseas", "highschool"], weights=[45, 40, 15], k=1)[0]
        if coach_style == "defense":
            return random.choices(["college", "highschool", "overseas"], weights=[50, 30, 20], k=1)[0]
        return random.choices(["college", "highschool", "overseas"], weights=[50, 30, 20], k=1)[0]

    def _assign_scout_dispatches(self):
        user_team = next((t for t in self.teams if self._is_user_team(t)), None)
        if user_team is not None:
            self._choose_user_scout_dispatch(user_team)

        for team in self.teams:
            if self._is_user_team(team):
                dispatch = self._normalize_scout_dispatch(getattr(team, "scout_dispatch", "college"))
                self._set_team_scout_dispatch(team, dispatch)
                continue

            dispatch = self._choose_ai_scout_dispatch(team)
            self._set_team_scout_dispatch(team, dispatch)

        print("\n[Scout Dispatch Summary]")
        for team in sorted(self.teams, key=lambda t: (t.league_level, t.name)):
            dispatch = self._normalize_scout_dispatch(getattr(team, "scout_dispatch", "college"))
            print(
                f"D{team.league_level} | {team.name:<25} | "
                f"dispatch:{self._get_scout_dispatch_label(dispatch)}"
            )

    def _get_dispatch_ovr_error_bonus(self, dispatch: str) -> int:
        dispatch = self._normalize_scout_dispatch(dispatch)
        if dispatch == "college":
            return 1
        return 0

    def _get_dispatch_attribute_error_bonus(self, dispatch: str, attr_name: str) -> int:
        dispatch = self._normalize_scout_dispatch(dispatch)
        if dispatch == "college" and attr_name in {"shoot", "defense", "stamina", "drive", "passing"}:
            return 1
        return 0

    def _get_dispatch_potential_view(self, player: Player, dispatch: str) -> str:
        dispatch = self._normalize_scout_dispatch(dispatch)
        actual = str(getattr(player, "potential", "C")).upper()

        if dispatch == "highschool":
            return actual

        mistake_roll = 0.10
        if dispatch == "college":
            mistake_roll = 0.18
        elif dispatch == "overseas":
            mistake_roll = 0.22

        if random.random() >= mistake_roll:
            return actual

        if actual == "S":
            return random.choice(["A", "B"])
        if actual == "A":
            return random.choice(["S", "B"])
        if actual == "B":
            return random.choice(["A", "C"])
        if actual == "C":
            return random.choice(["B", "D"])
        return random.choice(["C", "D"])

    def _get_dispatch_buzz_bonus(self, player: Player, dispatch: str) -> float:
        dispatch = self._normalize_scout_dispatch(dispatch)
        age = int(getattr(player, "age", 20))
        potential = str(getattr(player, "potential", "C")).upper()
        bonus = 0.0

        if dispatch == "highschool":
            if age <= 19:
                bonus += 2.0
            if potential in ("S", "A"):
                bonus += 2.0
        elif dispatch == "college":
            if age >= 20:
                bonus += 1.0
            bonus += max(0.0, (getattr(player, "ovr", 60) - 68) * 0.08)
        elif dispatch == "overseas":
            if getattr(player, "is_reborn", False):
                bonus += 2.5
            if getattr(player, "draft_origin_type", "") == "special":
                bonus += 2.5
            if getattr(player, "is_featured_prospect", False):
                bonus += 1.5

        return bonus

    def _normalize_scout_focus(self, raw_focus: str) -> str:
        valid = {"balanced", "shooting", "defense", "athletic", "playmaking"}
        if raw_focus in valid:
            return raw_focus
        return "balanced"

    def _get_scout_focus_label(self, focus: str) -> str:
        label_map = {
            "balanced": "Balanced",
            "shooting": "Shooting",
            "defense": "Defense",
            "athletic": "Athletic",
            "playmaking": "Playmaking",
        }
        return label_map.get(focus, "Balanced")

    def _choose_user_scout_focus(self, team: Team):
        print("\n=== Draft Combine / Scout Focus ===")
        print("1. Balanced")
        print("2. Shooting")
        print("3. Defense")
        print("4. Athletic")
        print("5. Playmaking")

        while True:
            try:
                raw = input("番号: ").strip()
            except EOFError:
                raw = "1"  # balanced（安定・無難）
            mapping = {
                "1": "balanced",
                "2": "shooting",
                "3": "defense",
                "4": "athletic",
                "5": "playmaking",
            }
            if raw in mapping:
                focus = mapping[raw]
                if hasattr(team, "set_scout_focus"):
                    team.set_scout_focus(focus)
                else:
                    team.scout_focus = focus
                return
            print("正しい番号を入力してください。")

    def _assign_ai_scout_focus(self):
        for team in self.teams:
            if self._is_user_team(team):
                continue

            coach_style = getattr(team, "coach_style", "balanced")
            strategy = getattr(team, "strategy", "balanced")

            if coach_style == "defense" or strategy == "defense":
                focus = "defense"
            elif coach_style == "offense" or strategy == "three_point":
                focus = "shooting"
            elif strategy == "run_and_gun":
                focus = "athletic"
            elif coach_style == "development":
                focus = "playmaking"
            else:
                focus = "balanced"

            if hasattr(team, "set_scout_focus"):
                team.set_scout_focus(focus)
            else:
                team.scout_focus = focus

    def _get_scout_ovr_error(self, scout_level: int) -> int:
        if scout_level >= 90:
            return 2
        if scout_level >= 75:
            return 4
        if scout_level >= 60:
            return 6
        if scout_level >= 45:
            return 8
        return 10

    def _estimate_attribute(self, player: Player, attr_name: str, scout_level: int, focused: bool, dispatch: str = "college") -> str:
        error = self._get_scout_ovr_error(scout_level)
        error -= self._get_dispatch_attribute_error_bonus(dispatch, attr_name)
        if focused:
            error = max(1, error // 2)
        else:
            error = max(1, error)

        try:
            real_value = int(player.get_adjusted_attribute(attr_name))
        except Exception:
            real_value = max(40, min(99, int(getattr(player, "ovr", 60))))

        low = max(40, real_value - error)
        high = min(99, real_value + error)

        if scout_level < 45 and not focused and random.random() < 0.35:
            return "?"
        if low == high:
            return str(low)
        return f"{low}-{high}"

    def _attach_scout_report_for_team(self, team: Team):
        focus = self._normalize_scout_focus(getattr(team, "scout_focus", "balanced"))
        scout_level = int(getattr(team, "scout_level", 50))
        dispatch = self._normalize_scout_dispatch(getattr(team, "scout_dispatch", "college"))

        for player in self.draft_pool:
            if not hasattr(player, "scout_reports") or player.scout_reports is None:
                player.scout_reports = {}

            focused_attrs = {
                "shooting": {"shoot", "three"},
                "defense": {"defense", "rebound"},
                "athletic": {"stamina", "drive"},
                "playmaking": {"passing", "iq"},
                "balanced": set(),
            }.get(focus, set())

            ovr_error = max(1, self._get_scout_ovr_error(scout_level) - self._get_dispatch_ovr_error_bonus(dispatch))
            real_ovr = int(getattr(player, "ovr", 60))
            low = max(45, real_ovr - ovr_error)
            high = min(99, real_ovr + ovr_error)

            report = {
                "ovr_range": f"{low}-{high}" if low != high else str(low),
                "potential_view": self._get_dispatch_potential_view(player, dispatch),
                "shoot_view": self._estimate_attribute(player, "shoot", scout_level, "shoot" in focused_attrs or "three" in focused_attrs, dispatch=dispatch),
                "defense_view": self._estimate_attribute(player, "defense", scout_level, "defense" in focused_attrs, dispatch=dispatch),
                "athletic_view": self._estimate_attribute(player, "stamina", scout_level, "stamina" in focused_attrs or "drive" in focused_attrs, dispatch=dispatch),
                "focus": focus,
                "focus_label": self._get_scout_focus_label(focus),
                "dispatch": dispatch,
                "dispatch_label": self._get_scout_dispatch_label(dispatch),
            }
            player.scout_reports[getattr(team, "team_id", None)] = report

    def _run_draft_combine(self):
        if not self.draft_pool:
            return

        user_team = next((t for t in self.teams if self._is_user_team(t)), None)
        if user_team is not None:
            self._choose_user_scout_focus(user_team)

        self._assign_ai_scout_focus()

        for team in self.teams:
            self._attach_scout_report_for_team(team)

        print("\n=== Draft Combine ===")
        print(f"Draft Prospects: {len(self.draft_pool)}")

        if user_team is not None:
            focus = self._normalize_scout_focus(getattr(user_team, "scout_focus", "balanced"))
            dispatch = self._normalize_scout_dispatch(getattr(user_team, "scout_dispatch", "college"))
            print(
                f"User Scout Focus: {self._get_scout_focus_label(focus)} | "
                f"Scout Level: {int(getattr(user_team, 'scout_level', 50))} | "
                f"Dispatch: {self._get_scout_dispatch_label(dispatch)}"
            )

        user_dispatch = "college"
        if user_team is not None:
            user_dispatch = self._normalize_scout_dispatch(getattr(user_team, "scout_dispatch", "college"))

        buzz_pool = sorted(
            self.draft_pool,
            key=lambda p: (
                getattr(p, "ovr", 0) + self._get_dispatch_buzz_bonus(p, user_dispatch),
                getattr(p, "draft_priority_bonus", 0),
                getattr(p, "potential", "C"),
            ),
            reverse=True,
        )[:10]

        print("\n[Combine Buzz]")
        for i, p in enumerate(buzz_pool, 1):
            label = getattr(p, "draft_profile_label", "通常新人")
            if user_team is not None:
                report = getattr(p, "scout_reports", {}).get(getattr(user_team, "team_id", None), {})
                ovr_view = report.get("ovr_range", str(getattr(p, "ovr", 0)))
                shoot_view = report.get("shoot_view", "?")
                defense_view = report.get("defense_view", "?")
                athletic_view = report.get("athletic_view", "?")
                potential_view = report.get("potential_view", getattr(p, "potential", "C"))
                dispatch_label = report.get("dispatch_label", "College")
                print(
                    f"{i}. {p.name} | {p.position} | OVR:{ovr_view} | "
                    f"Potential:{potential_view} | "
                    f"Shoot:{shoot_view} | Defense:{defense_view} | Athletic:{athletic_view} | "
                    f"Dispatch:{dispatch_label} | {label}"
                )
            else:
                print(
                    f"{i}. {p.name} | {p.position} | OVR:{getattr(p, 'ovr', 0)} | "
                    f"Potential:{getattr(p, 'potential', 'C')} | {label}"
                )

    def _heal_players(self):
        for p in self._all_players():
            p.fatigue = 0
            p.injury_games_left = 0


    def _calculate_team_revenue(self, team: Team) -> int:
        wins = self._get_team_wins(team)
        league_level = int(getattr(team, "league_level", 3))
        popularity = int(getattr(team, "popularity", 50))
        market_size = float(getattr(team, "market_size", 1.0))
        fan_base = int(getattr(team, "fan_base", 50))
        sponsor_power = int(getattr(team, "sponsor_power", 50))
        arena_level = int(getattr(team, "arena_level", 1))
        season_ticket_base = int(getattr(team, "season_ticket_base", 50))

        gate_base = {1: 1_620_000, 2: 880_000, 3: 360_000}.get(league_level, 360_000)
        gate_revenue = int(
            gate_base
            + wins * {1: 31_000, 2: 19_000, 3: 10_500}.get(league_level, 10_500)
            + popularity * 2_650
            + int(market_size * 38_000)
            + fan_base * 1_550
            + season_ticket_base * 2_250
            + max(0, arena_level - 1) * 28_000
        )

        sponsor_base = {1: 420_000, 2: 205_000, 3: 82_000}.get(league_level, 82_000)
        sponsor_revenue = int(
            sponsor_base
            + sponsor_power * 3_850
            + popularity * 1_150
            + max(0, wins - 15) * 4_200
        )

        merch_base = {1: 155_000, 2: 84_000, 3: 36_000}.get(league_level, 36_000)
        merch_revenue = int(
            merch_base
            + popularity * 1_180
            + fan_base * 950
            + max(0, wins - 15) * 2_250
        )

        media_distribution = {1: 420_000, 2: 150_000, 3: 30_000}.get(league_level, 30_000)

        performance_bonus = 0
        if league_level == 1:
            if wins >= 24:
                performance_bonus = 170_000
            elif wins >= 20:
                performance_bonus = 85_000
            elif wins >= 16:
                performance_bonus = 28_000
        elif league_level == 2:
            if wins >= 22:
                performance_bonus = 90_000
            elif wins >= 18:
                performance_bonus = 38_000
        else:
            if wins >= 20:
                performance_bonus = 36_000
            elif wins >= 16:
                performance_bonus = 14_000

        total_revenue = gate_revenue + sponsor_revenue + merch_revenue + media_distribution + performance_bonus
        return int(total_revenue)

    def _calculate_team_expenses(self, team: Team) -> tuple[int, int, int]:
        payroll = int(sum(max(0, int(getattr(p, "salary", 0))) for p in getattr(team, "players", [])))

        league_level = int(getattr(team, "league_level", 3))
        wins = self._get_team_wins(team)
        market_size = float(getattr(team, "market_size", 1.0))
        arena_level = int(getattr(team, "arena_level", 1))
        training_level = int(getattr(team, "training_facility_level", 1))
        medical_level = int(getattr(team, "medical_facility_level", 1))
        front_office_level = int(getattr(team, "front_office_level", 1))
        scout_level = int(getattr(team, "scout_level", 50))
        popularity = int(getattr(team, "popularity", 50))

        facility_maintenance = int(
            1_520_000
            + arena_level * 500_000
            + training_level * 325_000
            + medical_level * 280_000
            + front_office_level * 260_000
        )

        scouting_and_ops = int(
            2_450_000
            + scout_level * 26_000
            + int(market_size * 44_000)
        )

        travel_cost = {1: 1_820_000, 2: 1_420_000, 3: 1_180_000}.get(league_level, 1_180_000)
        league_fee = {1: 3_050_000, 2: 2_180_000, 3: 1_650_000}.get(league_level, 1_650_000)
        admin_cost = int(1_320_000 + front_office_level * 165_000)
        game_ops_cost = {1: 1_220_000, 2: 900_000, 3: 680_000}.get(league_level, 680_000)

        underperformance_penalty = 0
        if league_level == 1 and wins <= 12:
            underperformance_penalty = 520_000
        elif league_level == 2 and wins <= 11:
            underperformance_penalty = 380_000
        elif league_level == 3 and wins <= 10:
            underperformance_penalty = 260_000

        fan_service_cost = int(360_000 + popularity * 18_000)

        total_expense = int(
            payroll
            + facility_maintenance
            + scouting_and_ops
            + travel_cost
            + league_fee
            + admin_cost
            + game_ops_cost
            + underperformance_penalty
            + fan_service_cost
        )
        return total_expense, payroll, facility_maintenance

    def _get_owner_expectation_label(self, team: Team, wins: int) -> str:
        current = str(getattr(team, "owner_expectation", "stay_competitive"))

        league_level = int(getattr(team, "league_level", 3))
        if league_level == 1:
            if wins >= 22:
                return "title_chase"
            if wins >= 17:
                return "playoff_push"
            if wins >= 12:
                return current
            return "rebuild_pressure"

        if league_level == 2:
            if wins >= 20:
                return "promotion_push"
            if wins >= 14:
                return current
            return "rebuild_pressure"

        if wins >= 18:
            return "promotion_push"
        if wins >= 12:
            return current
        return "rebuild_pressure"


    def _format_owner_expectation_label(self, expectation: str) -> str:
        label_map = {
            "rebuild": "再建",
            "playoff_race": "PO争い",
            "promotion": "昇格必達",
            "title_challenge": "優勝挑戦",
            "title_or_bust": "優勝必須",
            "title_chase": "優勝争い",
            "playoff_push": "PO進出重視",
            "promotion_push": "昇格狙い",
            "rebuild_pressure": "再建圧力",
            "stay_competitive": "競争力維持",
        }
        return label_map.get(expectation, expectation)

    def _normalize_owner_expectation_for_missions(self, expectation: str) -> str:
        mapping = {
            "title_chase": "title_challenge",
            "playoff_push": "playoff_race",
            "promotion_push": "promotion",
            "rebuild_pressure": "rebuild",
            "stay_competitive": "playoff_race",
        }
        return mapping.get(expectation, expectation)

    def _process_owner_missions(self):
        print("\n[Owner Mission Review]")

        for team in sorted(self.teams, key=lambda t: (getattr(t, "league_level", 3), getattr(t, "name", ""))):
            if not hasattr(team, "refresh_owner_missions") or not hasattr(team, "evaluate_owner_missions"):
                continue

            season_label = f"Season {max(1, int(getattr(team, 'history_seasons', [])[-1].get('season', 1))) if getattr(team, 'history_seasons', []) else 1}"

            had_active_missions = bool(getattr(team, "owner_missions", []))
            evaluation_payload = None

            if had_active_missions:
                try:
                    evaluation_payload = team.evaluate_owner_missions(season_label=season_label)
                except Exception:
                    evaluation_payload = None

            normalized_expectation = self._normalize_owner_expectation_for_missions(
                str(getattr(team, "owner_expectation", "playoff_race"))
            )
            team.owner_expectation = normalized_expectation

            try:
                team.refresh_owner_missions(force=True)
            except Exception:
                pass

            trust_value = int(getattr(team, "owner_trust", 50))
            print(
                f"[OWNER] D{getattr(team, 'league_level', 3)} | {team.name} | "
                f"Expectation:{self._format_owner_expectation_label(normalized_expectation)} | "
                f"Trust:{trust_value}/100"
            )

            if evaluation_payload is not None:
                print(
                    f"[OWNER-EVAL] {team.name} | "
                    f"TrustDelta:{int(evaluation_payload.get('trust_delta_total', 0)):+} | "
                    f"After:{int(evaluation_payload.get('owner_trust_after', trust_value))}"
                )
                for row in evaluation_payload.get("results", []):
                    state = "達成" if row.get("status") == "success" else "未達"
                    print(
                        f"  - {row.get('title', '-')} | {state} | "
                        f"{row.get('progress_text', '')} | Trust:{int(row.get('trust_delta', 0)):+}"
                    )

            if self._is_user_team(team):
                print(f"\n=== USER TEAM OWNER REPORT: {team.name} ===")
                if evaluation_payload is None and not had_active_missions:
                    print("初年度のため、今オフは評価のみなし。次季オーナーミッションを設定しました。")
                elif evaluation_payload is None:
                    print("ミッション評価は行われませんでした。次季ノルマのみ更新します。")
                if hasattr(team, "get_owner_mission_report_text"):
                    try:
                        report_text = team.get_owner_mission_report_text()
                    except Exception:
                        report_text = ""
                    if report_text:
                        print(report_text)

    def _process_team_finances(self):
        print("\n[Finance Settlement]")

        sorted_teams = sorted(self.teams, key=lambda t: (getattr(t, "league_level", 3), getattr(t, "name", "")))

        for team in sorted_teams:
            if not hasattr(team, "money"):
                team.money = 10_000_000

            wins = self._get_team_wins(team)
            revenue = self._calculate_team_revenue(team)
            expense, payroll, facility_maintenance = self._calculate_team_expenses(team)
            cashflow = int(revenue - expense)

            team.revenue_last_season = revenue
            team.expense_last_season = expense
            team.cashflow_last_season = cashflow
            league_level = int(getattr(team, "league_level", 3))
            base_budget = {1: 7_900_000, 2: 5_450_000, 3: 3_650_000}.get(league_level, 3_650_000)
            team.payroll_budget = max(
                base_budget,
                int(
                    base_budget
                    + float(getattr(team, "market_size", 1.0)) * 12_500
                    + getattr(team, "popularity", 50) * 6_200
                    + getattr(team, "sponsor_power", 50) * 5_000
                    + getattr(team, "fan_base", 50) * 3_600
                )
            )
            team.owner_expectation = self._normalize_owner_expectation_for_missions(
                self._get_owner_expectation_label(team, wins)
            )

            team.money = int(getattr(team, "money", 0) + cashflow)

            if hasattr(team, "record_financial_result"):
                try:
                    team.record_financial_result(
                        revenue=revenue,
                        expense=expense,
                        cashflow=cashflow,
                        note=f"Wins:{wins} / Payroll:{payroll:,} / Facility:{facility_maintenance:,}",
                    )
                except TypeError:
                    try:
                        team.record_financial_result(revenue, expense, cashflow)
                    except Exception:
                        if hasattr(team, "finance_history"):
                            team.finance_history.append({
                                "revenue": revenue,
                                "expense": expense,
                                "cashflow": cashflow,
                                "wins": wins,
                                "payroll": payroll,
                                "facility_maintenance": facility_maintenance,
                            })
                except Exception:
                    if hasattr(team, "finance_history"):
                        team.finance_history.append({
                            "revenue": revenue,
                            "expense": expense,
                            "cashflow": cashflow,
                            "wins": wins,
                            "payroll": payroll,
                            "facility_maintenance": facility_maintenance,
                        })
            elif hasattr(team, "finance_history"):
                team.finance_history.append({
                    "revenue": revenue,
                    "expense": expense,
                    "cashflow": cashflow,
                    "wins": wins,
                    "payroll": payroll,
                    "facility_maintenance": facility_maintenance,
                })

            print(
                f"[FINANCE] D{getattr(team, 'league_level', 3)} | {team.name} | "
                f"Revenue:${revenue:,} | Expense:${expense:,} | Payroll:${payroll:,} | "
                f"Facility:${facility_maintenance:,} | Cashflow:${cashflow:,} | Money:${int(getattr(team, 'money', 0)):,}"
            )

            if self._is_user_team(team):
                print(f"\n=== USER TEAM FINANCE REPORT: {team.name} ===")
                print(
                    f"売上: ${revenue:,} / 支出: ${expense:,} / 人件費: ${payroll:,} / "
                    f"施設維持費: ${facility_maintenance:,}"
                )
                print(
                    f"最終収支: ${cashflow:,} / 現在資金: ${int(getattr(team, 'money', 0)):,} / "
                    f"来季人件費目安: ${int(getattr(team, 'payroll_budget', 0)):,}"
                )
                print(f"オーナー期待: {getattr(team, 'owner_expectation', 'stay_competitive')}")
                if hasattr(team, "get_finance_report_text"):
                    try:
                        report_text = team.get_finance_report_text()
                    except Exception:
                        report_text = ""
                    if report_text:
                        print(report_text)
