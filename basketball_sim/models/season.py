import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .team import Team
from .player import Player
from .match import Match
from basketball_sim.systems.player_stats import PlayerStatsManager
from basketball_sim.systems.free_agent_market import run_cpu_fa_market_cycle


@dataclass
class Competition:
    competition_id: str
    name: str
    competition_type: str
    season_phase: str
    format_type: str
    is_domestic: bool = True
    is_active: bool = False
    sort_order: int = 0


@dataclass
class SeasonEvent:
    event_id: str
    week: int
    day_of_week: str
    event_type: str
    competition_id: str
    competition_type: str
    stage: str
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    round_number: int = 0
    is_playoff: bool = False
    label: str = ""




ROUND_CONFIG = {
    1:  {"month": 10, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ開幕週"},
    2:  {"month": 10, "league_games_per_team": 2, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},
    3:  {"month": 10, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md1", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD1"},
    4:  {"month": 10, "league_games_per_team": 2, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},

    5:  {"month": 11, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "通常週"},
    6:  {"month": 11, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md2", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD2"},
    7:  {"month": 11, "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": "window_1", "is_break_week": True,  "notes": "代表ウィーク①"},
    8:  {"month": 11, "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},

    9:  {"month": 12, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "通常週"},
    10: {"month": 12, "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md3", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD3"},
    11: {"month": 12, "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},
    12: {"month": 12, "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},

    13: {"month": 1,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": "emperor_cup_week1", "national_team_window": None,       "is_break_week": True,  "notes": "天皇杯集中週①"},
    14: {"month": 1,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": "emperor_cup_week2", "national_team_window": None,       "is_break_week": True,  "notes": "天皇杯集中週②"},
    15: {"month": 1,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ再開"},
    16: {"month": 1,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md4", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD4"},

    17: {"month": 2,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},
    18: {"month": 2,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md5", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD5"},
    19: {"month": 2,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": "group_md6", "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "EASL MD6"},
    20: {"month": 2,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": "window_2", "is_break_week": True,  "notes": "代表ウィーク②"},

    21: {"month": 3,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ終盤"},
    22: {"month": 3,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ終盤"},
    23: {"month": 3,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": "knockout",  "cup_event": None,                "national_team_window": None,       "is_break_week": True,  "notes": "EASL決勝大会週"},
    24: {"month": 3,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ終盤"},

    25: {"month": 4,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "通常週"},
    26: {"month": 4,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},
    27: {"month": 4,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "通常週"},
    28: {"month": 4,  "league_games_per_team": 3, "has_midweek_league": True,  "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "圧縮週"},

    29: {"month": 5,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "リーグ最終盤"},
    30: {"month": 5,  "league_games_per_team": 2, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": False, "notes": "レギュラー最終週"},

    31: {"month": 5,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": True,  "notes": "CS / PO"},
    32: {"month": 5,  "league_games_per_team": 0, "has_midweek_league": False, "easl_event": None,        "cup_event": None,                "national_team_window": None,       "is_break_week": True,  "notes": "CS決勝 / 昇降格"},
}

NATIONAL_TEAM_CYCLE = {
    1: {"window_1": "asia_qualifier",  "window_2": "asia_qualifier",  "summer": "asia_cup"},
    2: {"window_1": "world_qualifier", "window_2": "world_qualifier", "summer": "friendly"},
    3: {"window_1": "world_qualifier", "window_2": "world_qualifier", "summer": "world_cup"},
    4: {"window_1": "friendly",        "window_2": "friendly",        "summer": "olympics"},
}


class Season:
    """
    1シーズンの進行（スケジュール・順位決定・プレーオフ・昇降格）を管理するクラス。
    3リーグ (1部〜3部) それぞれに対してスケジュールを作成し試合を行います。

    追加仕様:
    - ラウンド単位でシーズン進行可能
    - シーズン途中で順位表・個人成績ランキングを確認可能
    - D1 / D2 / D3 それぞれで上位8チームによるプレーオフを実施
    - D2優勝/準優勝 → D1昇格
    - D3優勝/準優勝 → D2昇格
    - シーズン表彰は各ディビジョンごとに実施
    - MVP条件:
        * 出場試合数8割以上
        * プレーオフ進出チーム所属

    今回の基盤追加:
    - シーズン終了時に個人成績を通算成績へ加算
    - 将来の歴史システム / 通算ランキングの土台
    - 将来の複数大会対応のため competition / season_event / phase を追加
    - 天皇杯の最小実装を追加
    - EASLの最小実装を追加
      * 国内2チーム + 海外架空10チーム
      * 4チーム×3グループ
      * ホーム&アウェイ総当たり（各チーム6試合）
      * 各組1位 + 2位最上位1チームで4強
      * 準決勝 / 決勝
    - EASL上位2チームをACL出場権として明示保存
    - ACLの最小実装を追加
      * EASL上位2チーム + 海外架空6チーム
      * 準々決勝 / 準決勝 / 決勝
    """

    def __init__(self, all_teams: List[Team], free_agents: Optional[List] = None):
        self.all_teams = all_teams
        self.free_agents = free_agents if free_agents is not None else []

        # 互換用（全体代表値）
        self.mvp = None
        self.roty = None
        self.scoring_champ = None
        self.rebound_champ = None
        self.assist_champ = None
        self.block_champ = None
        self.steal_champ = None
        self.all_league_first = []
        self.all_league_second = []
        self.all_league_third = []

        # ディビジョン別表彰データ
        self.awards_by_division = {
            1: self._create_empty_award_bucket(),
            2: self._create_empty_award_bucket(),
            3: self._create_empty_award_bucket(),
        }

        self.total_points = 0
        self.game_count = 0
        self.game_results = []

        self.current_round = 0
        self.season_finished = False
        self._finalized = False
        self._career_stats_applied = False

        self.phase = "regular_season"

        self.leagues = {1: [], 2: [], 3: []}
        for team in self.all_teams:
            lvl = max(1, min(3, team.league_level))
            self.leagues[lvl].append(team)

        self.schedule_by_round = self._prepare_regular_season_schedule()
        self.total_rounds = len(self.schedule_by_round)
        self.round_config = self._build_round_config()
        self.national_team_cycle = dict(NATIONAL_TEAM_CYCLE)
        self.easl_round_to_stage = self._build_easl_round_to_stage_map()

        self.competitions = self._build_competitions()
        self.season_events = self._build_season_events_from_regular_season()
        self.events_by_round = self._group_events_by_round(self.season_events)

        # 天皇杯
        self.emperor_cup_enabled = True
        self.emperor_cup_schedule = {
            13: ["round1", "round2", "round3"],
            14: ["quarterfinal", "semifinal", "final"],
        }
        self.emperor_cup_results = {
            "champion": None,
            "runner_up": None,
            "semifinalists": [],
        }
        self.emperor_cup_stage_logs = {}
        self._initialize_emperor_cup_state()

        # EASL
        self.easl_enabled = True
        self.easl_schedule = self.easl_round_to_stage.copy()
        self.easl_results = {
            "champion": None,
            "runner_up": None,
            "semifinalists": [],
            "participants": [],
        }
        self.easl_stage_logs = {}
        self.easl_groups = {}
        self.easl_group_records = {}
        self.easl_knockout_teams = []
        self.easl_matchdays = {}
        self.easl_semifinal_pairs = []
        self.easl_current_finalists = []
        self.easl_played_stages = set()
        self.easl_acl_qualifiers = []
        self.easl_top2_payloads = []
        self._foreign_exhibition_team_counter = 10000
        self._foreign_exhibition_player_counter = 500000
        self._initialize_easl_state()

        # ACL
        self.acl_enabled = True
        self.acl_results = {
            "champion": None,
            "runner_up": None,
            "semifinalists": [],
            "participants": [],
        }
        self.acl_stage_logs = {}
        self.acl_played = False


    def _build_round_config(self) -> Dict[int, dict]:
        config: Dict[int, dict] = {}
        for round_no in range(1, self.total_rounds + 1):
            base = {
                "month": None,
                "league_games_per_team": 2,
                "has_midweek_league": False,
                "easl_event": None,
                "cup_event": None,
                "national_team_window": None,
                "is_break_week": False,
                "notes": "",
            }
            base.update(ROUND_CONFIG.get(round_no, {}))
            config[round_no] = base
        return config

    def _get_round_config(self, round_number: int) -> dict:
        return self.round_config.get(round_number, {})

    def _get_round_month(self, round_number: int) -> Optional[int]:
        return self._get_round_config(round_number).get("month")

    def _get_round_easl_event(self, round_number: int) -> Optional[str]:
        return self._get_round_config(round_number).get("easl_event")

    def _get_round_cup_event(self, round_number: int) -> Optional[str]:
        return self._get_round_config(round_number).get("cup_event")

    def _get_round_national_window(self, round_number: int) -> Optional[str]:
        return self._get_round_config(round_number).get("national_team_window")

    def _is_break_week(self, round_number: int) -> bool:
        return bool(self._get_round_config(round_number).get("is_break_week"))

    def _regular_season_games_per_team_target(self) -> int:
        total = 0
        for round_no in range(1, self.total_rounds + 1):
            cfg = self._get_round_config(round_no)
            total += int(cfg.get("league_games_per_team", 0) or 0)
        return max(1, total)


    def _get_cycle_year(self) -> int:
        season_no = max(1, int(getattr(self, "season_no", 1)))
        return ((season_no - 1) % 4) + 1

    def _resolve_national_team_window_type(self, window_key: Optional[str]) -> Optional[str]:
        if not window_key:
            return None
        cycle_year = self._get_cycle_year()
        cycle_row = self.national_team_cycle.get(cycle_year, {})
        return cycle_row.get(window_key)

    def _get_national_team_window_label(self, window_type: Optional[str]) -> str:
        label_map = {
            "asia_qualifier": "アジアカップ予選",
            "asia_cup": "アジアカップ本戦",
            "world_qualifier": "ワールドカップ予選",
            "world_cup": "ワールドカップ本戦",
            "friendly": "代表強化試合",
            "olympics": "オリンピック",
        }
        if not window_type:
            return "代表ウィーク"
        return label_map.get(window_type, window_type)

    def _print_national_team_window_banner(self, round_number: int) -> None:
        window_key = self._get_round_national_window(round_number)
        window_type = self._resolve_national_team_window_type(window_key)
        label = self._get_national_team_window_label(window_type)
        cycle_year = self._get_cycle_year()
        print(f"\n[National Team Window] Round {round_number} | cycle_year={cycle_year} | {label}")
        print("代表ウィークのため、このラウンドのクラブ公式戦は行いません。")


    def _is_japan_national_team_eligible(self, player: Player, window_type: Optional[str]) -> bool:
        if player is None:
            return False

        nationality_values = [
            str(getattr(player, "nationality", "") or "").strip().lower(),
            str(getattr(player, "original_nationality", "") or "").strip().lower(),
        ]
        was_naturalized = bool(getattr(player, "was_naturalized", False))

        japan_like = {
            "japan",
            "japanese",
            "jp",
            "jpn",
            "local",
        }
        nationality_ok = was_naturalized or any(value in japan_like for value in nationality_values if value)
        if not nationality_ok:
            return False

        age = int(getattr(player, "age", 25) or 25)
        ovr = float(getattr(player, "ovr", 0) or 0)
        injury_games_left = int(getattr(player, "injury_games_left", 0) or 0)
        fatigue = float(getattr(player, "fatigue", 0) or 0)
        popularity = float(getattr(player, "popularity", 0) or 0)
        minutes = float(getattr(player, "minutes", 0) or 0)

        if injury_games_left > 0:
            return False
        if age < 18 or age > 37:
            return False
        if fatigue >= 90:
            return False

        min_ovr_map = {
            "friendly": 56,
            "asia_qualifier": 58,
            "world_qualifier": 60,
            "asia_cup": 62,
            "world_cup": 65,
            "olympics": 67,
        }
        min_ovr = float(min_ovr_map.get(window_type or "", 58))

        # 若手は少しだけ救済して将来性枠を残す
        young_prospect_ok = age <= 22 and ovr >= max(54.0, min_ovr - 4.0) and popularity >= 20

        # 実戦実績が薄い場合は少しだけ厳しくする
        baseline_ok = ovr >= min_ovr and (minutes >= 8 or popularity >= 30)

        return bool(baseline_ok or young_prospect_ok)

    def _get_player_national_team_history_count(self, player: Player) -> int:
        history = list(getattr(player, "national_team_history", []) or [])
        return len(history)

    def _get_national_team_candidate_score(self, player: Player, window_type: Optional[str]) -> float:
        ovr = float(getattr(player, "ovr", 0))
        popularity = float(getattr(player, "popularity", 0))
        age = int(getattr(player, "age", 25) or 25)
        star_tier = float(getattr(player, "star_tier", 0) or 0)
        title_level = float(getattr(player, "title_level", 0) or 0)
        breakout_count = float(getattr(player, "breakout_count", 0) or 0)
        fatigue = float(getattr(player, "fatigue", 0) or 0)
        injury_games_left = int(getattr(player, "injury_games_left", 0) or 0)

        potential_cap_value = 0.0
        if hasattr(player, "get_potential_cap_value"):
            try:
                potential_cap_value = float(player.get_potential_cap_value())
            except Exception:
                potential_cap_value = 0.0

        score = ovr * 1.85
        score += popularity * 0.12
        score += potential_cap_value * 0.08
        score += star_tier * 4.0
        score += title_level * 2.5
        score += breakout_count * 1.5

        national_team_caps = self._get_player_national_team_history_count(player)
        score += min(12.0, float(national_team_caps) * 2.0)

        # 若手抜擢はアジア予選 / 強化試合でやや強め
        if window_type in {"asia_qualifier", "friendly"}:
            if age <= 24:
                score += 6.0
            elif age >= 31:
                score -= 3.0

        # 本戦系は実力重視
        if window_type in {"world_cup", "olympics"}:
            score += ovr * 0.25
            if age <= 22:
                score -= 2.0

        # 直近コンディションの悪さは軽く減点
        score -= fatigue * 0.25
        score -= injury_games_left * 8.0

        return round(score, 2)

    def _clear_national_team_flags_for_all_players(self) -> None:
        for team in self.all_teams:
            for player in getattr(team, "players", []) or []:
                if hasattr(player, "clear_national_team_assignment"):
                    player.clear_national_team_assignment()
                else:
                    setattr(player, "is_on_national_team", False)
                    setattr(player, "national_team_type", "")
                    setattr(player, "national_team_country", "")
                    setattr(player, "national_team_return_fatigue_bonus", 0)
                    setattr(player, "national_team_assigned_round", 0)

    def _get_national_team_return_fatigue_bonus(self, window_type: Optional[str]) -> int:
        bonus_map = {
            "friendly": 4,
            "asia_qualifier": 6,
            "world_qualifier": 7,
            "asia_cup": 9,
            "world_cup": 12,
            "olympics": 14,
        }
        return int(bonus_map.get(window_type or "", 5))

    def _get_national_team_return_popularity_bonus(self, window_type: Optional[str]) -> int:
        bonus_map = {
            "friendly": 1,
            "asia_qualifier": 2,
            "world_qualifier": 2,
            "asia_cup": 3,
            "world_cup": 4,
            "olympics": 5,
        }
        return int(bonus_map.get(window_type or "", 1))

    def _apply_club_national_team_selection_popularity_bonus(
        self,
        club_selection_counts: Dict[str, int],
    ) -> None:
        if not club_selection_counts:
            return

        for team in self.all_teams:
            team_name = str(getattr(team, "name", "") or "")
            selected_count = int(club_selection_counts.get(team_name, 0) or 0)
            if selected_count <= 0:
                continue

            current_popularity = float(getattr(team, "popularity", 0) or 0)
            popularity_bonus = min(3, selected_count)
            new_popularity = min(100.0, current_popularity + popularity_bonus)
            setattr(team, "popularity", new_popularity)

    def _get_national_team_return_growth_base(self, window_type: Optional[str]) -> float:
        growth_map = {
            "friendly": 0.10,
            "asia_qualifier": 0.18,
            "world_qualifier": 0.22,
            "asia_cup": 0.30,
            "world_cup": 0.42,
            "olympics": 0.52,
        }
        return float(growth_map.get(window_type or "", 0.10))

    def _get_national_team_growth_focus_keys(self, player: Player) -> List[str]:
        position = str(getattr(player, "position", "") or "").upper()
        if position == "PG":
            return ["passing", "drive", "stamina"]
        if position == "SG":
            return ["shoot", "three", "drive"]
        if position == "SF":
            return ["shoot", "drive", "defense"]
        if position == "PF":
            return ["rebound", "defense", "stamina"]
        if position == "C":
            return ["rebound", "defense", "stamina"]

        archetype = str(getattr(player, "archetype", "") or "").lower()
        if archetype in {"floor_general", "playmaker"}:
            return ["passing", "drive", "stamina"]
        if archetype in {"scoring_guard", "slasher"}:
            return ["shoot", "drive", "three"]
        if archetype in {"two_way_wing"}:
            return ["shoot", "drive", "defense"]
        if archetype in {"stretch_big"}:
            return ["three", "rebound", "stamina"]
        if archetype in {"rim_protector", "rebounder"}:
            return ["rebound", "defense", "stamina"]

        return ["shoot", "drive", "stamina"]

    def _apply_national_team_return_growth(self, player: Player, window_type: Optional[str]) -> int:
        if player is None:
            return 0

        base_growth = self._get_national_team_return_growth_base(window_type)
        work_ethic = float(getattr(player, "work_ethic", 50) or 50)
        iq = float(getattr(player, "basketball_iq", 50) or 50)
        competitiveness = float(getattr(player, "competitiveness", 50) or 50)
        age = int(getattr(player, "age", 25) or 25)
        potential_cap = 0
        if hasattr(player, "get_potential_cap_value"):
            try:
                potential_cap = int(player.get_potential_cap_value())
            except Exception:
                potential_cap = 0

        hidden_bonus = 0.85 + ((work_ethic + iq + competitiveness) / 300.0) * 0.30
        age_bonus = 1.08 if age <= 24 else 0.96 if age >= 30 else 1.0
        cap_bonus = 1.04 if potential_cap >= 84 else 0.98 if potential_cap <= 76 else 1.0

        final_growth = base_growth * hidden_bonus * age_bonus * cap_bonus
        focus_keys = self._get_national_team_growth_focus_keys(player)

        total_delta = 0
        count = 0
        for key in focus_keys:
            if not hasattr(player, key):
                continue
            current_val = int(getattr(player, key, 0) or 0)
            if hasattr(player, "_apply_random_fraction"):
                try:
                    new_val = int(player._apply_random_fraction(current_val, final_growth))
                except Exception:
                    new_val = current_val
            else:
                delta = 1 if final_growth >= 0.5 else 0
                new_val = max(1, min(99, current_val + delta))

            setattr(player, key, new_val)
            total_delta += (new_val - current_val)
            count += 1

        if count <= 0:
            return 0

        old_ovr = int(getattr(player, "ovr", 0) or 0)
        avg_delta = total_delta / float(count)
        new_ovr = int(max(40, min(99, old_ovr + round(avg_delta))))
        setattr(player, "ovr", new_ovr)

        if hasattr(player, "update_peak_ovr"):
            try:
                player.update_peak_ovr()
            except Exception:
                pass

        return int(new_ovr - old_ovr)

    def _apply_pending_national_team_returns(self, current_round: int) -> None:
        returned_players = []
        for team in self.all_teams:
            for player in getattr(team, "players", []) or []:
                if not bool(getattr(player, "is_on_national_team", False)):
                    continue

                assigned_round = int(getattr(player, "national_team_assigned_round", 0) or 0)
                if assigned_round <= 0 or assigned_round >= int(current_round):
                    continue

                fatigue_bonus = int(getattr(player, "national_team_return_fatigue_bonus", 0) or 0)
                team_type = str(getattr(player, "national_team_type", "") or "")
                popularity_bonus = self._get_national_team_return_popularity_bonus(team_type)

                if fatigue_bonus > 0:
                    current_fatigue = float(getattr(player, "fatigue", 0) or 0)
                    setattr(player, "fatigue", current_fatigue + fatigue_bonus)

                current_popularity = float(getattr(player, "popularity", 0) or 0)
                setattr(player, "popularity", current_popularity + popularity_bonus)

                growth_delta = self._apply_national_team_return_growth(player, team_type)

                returned_players.append(
                    (
                        getattr(player, "name", "UNKNOWN"),
                        getattr(team, "name", ""),
                        team_type,
                        fatigue_bonus,
                        popularity_bonus,
                        growth_delta,
                    )
                )

                if hasattr(player, "clear_national_team_assignment"):
                    player.clear_national_team_assignment()
                else:
                    setattr(player, "is_on_national_team", False)
                    setattr(player, "national_team_type", "")
                    setattr(player, "national_team_country", "")
                    setattr(player, "national_team_return_fatigue_bonus", 0)
                    setattr(player, "national_team_assigned_round", 0)

        if returned_players:
            print("\n[National Team Return]")
            for name, team_name, team_type, fatigue_bonus, popularity_bonus, growth_delta in returned_players[:12]:
                label = self._get_national_team_window_label(team_type)
                caps = 0
                for team in self.all_teams:
                    if getattr(team, "name", "") != team_name:
                        continue
                    for player in getattr(team, "players", []) or []:
                        if getattr(player, "name", "") == name:
                            caps = self._get_player_national_team_history_count(player)
                            break
                    if caps:
                        break
                print(
                    f" {name} | Team:{team_name} | from={label} | fatigue+={fatigue_bonus} | popularity+={popularity_bonus} | ovr+={growth_delta} | caps={caps}"
                )

    def _normalize_position_for_national_team(self, player: Player) -> str:
        pos = str(getattr(player, "position", "") or "").strip().upper()
        if pos in {"PG", "SG", "SF", "PF", "C"}:
            return pos
        return "UTIL"

    def _select_national_team_roster_with_balance(
        self,
        scored_rows: List[Tuple[Player, float]],
        roster_size: int = 12,
    ) -> Tuple[List[Tuple[Player, float]], List[Tuple[Player, float]], Dict[str, int]]:
        minimum_plan: Dict[str, int] = {
            "PG": 2,
            "SG": 2,
            "SF": 2,
            "PF": 2,
            "C": 2,
        }

        selected: List[Tuple[Player, float]] = []
        selected_ids = set()
        position_counts: Dict[str, int] = {key: 0 for key in minimum_plan.keys()}

        rows_by_position: Dict[str, List[Tuple[Player, float]]] = {key: [] for key in minimum_plan.keys()}
        utility_rows: List[Tuple[Player, float]] = []

        for row in scored_rows:
            player, _score = row
            pos = self._normalize_position_for_national_team(player)
            if pos in rows_by_position:
                rows_by_position[pos].append(row)
            else:
                utility_rows.append(row)

        for pos, minimum_count in minimum_plan.items():
            for row in rows_by_position.get(pos, []):
                player, _score = row
                pid = id(player)
                if pid in selected_ids:
                    continue
                selected.append(row)
                selected_ids.add(pid)
                position_counts[pos] += 1
                if position_counts[pos] >= minimum_count:
                    break

        remaining_rows: List[Tuple[Player, float]] = []
        for row in scored_rows:
            player, _score = row
            if id(player) in selected_ids:
                continue
            remaining_rows.append(row)

        for row in remaining_rows:
            if len(selected) >= roster_size:
                break
            player, _score = row
            pos = self._normalize_position_for_national_team(player)
            selected.append(row)
            selected_ids.add(id(player))
            if pos in position_counts:
                position_counts[pos] += 1

        selected_sorted = sorted(
            selected,
            key=lambda row: (
                row[1],
                float(getattr(row[0], "ovr", 0) or 0),
                float(getattr(row[0], "popularity", 0) or 0),
                -int(getattr(row[0], "age", 99) or 99),
                str(getattr(row[0], "name", "")),
            ),
            reverse=True,
        )
        reserve_rows = [row for row in scored_rows if id(row[0]) not in selected_ids][:6]
        return selected_sorted[:roster_size], reserve_rows, position_counts

    def _run_national_team_window_log_only(self, round_number: int) -> None:
        window_key = self._get_round_national_window(round_number)
        window_type = self._resolve_national_team_window_type(window_key)
        label = self._get_national_team_window_label(window_type)

        # 前回の招集状態は一旦クリア
        self._clear_national_team_flags_for_all_players()

        eligible_players: List[Player] = []
        for team in self.all_teams:
            for player in getattr(team, "players", []) or []:
                if not self._is_japan_national_team_eligible(player, window_type):
                    continue
                eligible_players.append(player)

        scored_rows = []
        for player in eligible_players:
            score = self._get_national_team_candidate_score(player, window_type)
            scored_rows.append((player, score))

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

        selected_rows, reserve_rows, position_counts = self._select_national_team_roster_with_balance(
            scored_rows,
            roster_size=12,
        )

        print(f"[National Team Selection] 日本代表候補選考 | event={label} | eligible={len(scored_rows)}")
        if not selected_rows:
            print("  選出対象なし")
            return

        club_selection_counts = {}
        for player, _score in selected_rows:
            team_name = ""
            for team in self.all_teams:
                if getattr(player, "team_id", None) == getattr(team, "team_id", None):
                    team_name = getattr(team, "name", "")
                    break
            team_name = team_name or "UNKNOWN"
            club_selection_counts[team_name] = club_selection_counts.get(team_name, 0) + 1

        sorted_club_counts = sorted(
            club_selection_counts.items(),
            key=lambda row: (-row[1], row[0]),
        )

        print("[National Team Club Summary]")
        for idx, (team_name, count) in enumerate(sorted_club_counts[:8], start=1):
            print(f" {idx:>2}. {team_name:<24} selected={count}")

        self._apply_club_national_team_selection_popularity_bonus(club_selection_counts)

        print("[National Team Roster]")
        for idx, (player, score) in enumerate(selected_rows, start=1):
            team_name = ""
            for team in self.all_teams:
                if getattr(player, "team_id", None) == getattr(team, "team_id", None):
                    team_name = getattr(team, "name", "")
                    break

            prior_caps = self._get_player_national_team_history_count(player)

            setattr(player, "is_on_national_team", True)
            setattr(player, "national_team_type", window_type or "")
            setattr(player, "national_team_country", "Japan")
            setattr(
                player,
                "national_team_return_fatigue_bonus",
                self._get_national_team_return_fatigue_bonus(window_type),
            )
            setattr(player, "national_team_assigned_round", int(round_number))

            if hasattr(player, "add_national_team_history"):
                try:
                    player.add_national_team_history({
                        "season": max(1, int(getattr(self, "season_no", 1) or 1)),
                        "round": round_number,
                        "window_key": window_key,
                        "window_type": window_type,
                        "event_label": label,
                        "country": "Japan",
                        "selected": True,
                        "selection_score": score,
                    })
                except Exception:
                    pass

            pos = str(getattr(player, "position", "-"))
            age = int(getattr(player, "age", 0) or 0)
            ovr = int(getattr(player, "ovr", 0) or 0)
            caps = self._get_player_national_team_history_count(player)
            exp_tag = " | NT_EXP" if prior_caps >= 1 else ""
            print(
                f" {idx:>2}. {getattr(player, 'name', 'UNKNOWN'):<18} "
                f"{pos:<2} Age:{age:<2} OVR:{ovr:<2} "
                f"Team:{team_name} | score={score:.2f} | caps={caps}{exp_tag}"
            )

        print("[National Team Career Summary]")
        for idx, (player, _score) in enumerate(selected_rows, start=1):
            caps = self._get_player_national_team_history_count(player)
            latest_label = self._get_national_team_window_label(str(getattr(player, "national_team_type", "") or ""))
            print(
                f" {idx:>2}. {getattr(player, 'name', 'UNKNOWN'):<18} "
                f"caps={caps} | latest={latest_label}"
            )


    def _build_easl_round_to_stage_map(self) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        for round_no, row in self.round_config.items():
            stage = row.get("easl_event")
            if not stage:
                continue
            if stage == "knockout":
                mapping[round_no] = "semifinal"
                if round_no + 2 <= self.total_rounds:
                    mapping[round_no + 2] = "final"
            else:
                mapping[round_no] = stage
        if "final" not in mapping.values():
            mapping[29] = "final"
        return dict(sorted(mapping.items()))

    def _get_round_easl_stage(self, round_number: int) -> Optional[str]:
        return self.easl_round_to_stage.get(round_number)

    def _create_empty_award_bucket(self):
        return {
            "mvp": None,
            "roty": None,
            "scoring_champ": None,
            "rebound_champ": None,
            "assist_champ": None,
            "block_champ": None,
            "steal_champ": None,
            "all_league_first": [],
            "all_league_second": [],
            "all_league_third": [],
        }

    def _player_id(self, player):
        return getattr(player, "player_id", None) if player is not None else None

    def _player_ids(self, players):
        return {getattr(p, "player_id", None) for p in players if p is not None}

    def _team_player_ids(self, team):
        return {getattr(p, "player_id", None) for p in team.players if p is not None}

    def _build_competitions(self) -> Dict[str, Competition]:
        items = [
            Competition(
                competition_id="regular_season",
                name="Regular Season",
                competition_type="regular_season",
                season_phase="regular_season",
                format_type="league",
                is_domestic=True,
                is_active=True,
                sort_order=10,
            ),
            Competition(
                competition_id="division_playoffs",
                name="Division Playoffs",
                competition_type="playoff",
                season_phase="domestic_postseason",
                format_type="tournament",
                is_domestic=True,
                is_active=True,
                sort_order=20,
            ),
            Competition(
                competition_id="emperor_cup",
                name="全日本カップ",
                competition_type="emperor_cup",
                season_phase="regular_season",
                format_type="tournament",
                is_domestic=True,
                is_active=True,
                sort_order=30,
            ),
            Competition(
                competition_id="easl",
                name="東アジアトップリーグ",
                competition_type="easl",
                season_phase="regular_season",
                format_type="group_and_knockout",
                is_domestic=False,
                is_active=True,
                sort_order=40,
            ),
            Competition(
                competition_id="asia_cl",
                name="アジアクラブ選手権",
                competition_type="asia_cl",
                season_phase="continental_postseason",
                format_type="tournament",
                is_domestic=False,
                is_active=True,
                sort_order=50,
            ),
            Competition(
                competition_id="intercontinental_cup",
                name="世界一決定戦",
                competition_type="intercontinental",
                season_phase="world_postseason",
                format_type="tournament",
                is_domestic=False,
                is_active=False,
                sort_order=60,
            ),
            Competition(
                competition_id="final_boss",
                name="FINAL BOSS",
                competition_type="final_boss",
                season_phase="world_postseason",
                format_type="special_match",
                is_domestic=False,
                is_active=False,
                sort_order=70,
            ),
        ]
        return {c.competition_id: c for c in items}

    def _build_season_events_from_regular_season(self) -> List[SeasonEvent]:
        events: List[SeasonEvent] = []

        for round_idx, round_games in enumerate(self.schedule_by_round, start=1):
            week = round_idx
            day_of_week = "Sat"

            for game_idx, (home_team, away_team) in enumerate(round_games, start=1):
                event_id = f"regular_season_r{round_idx}_g{game_idx}"
                events.append(
                    SeasonEvent(
                        event_id=event_id,
                        week=week,
                        day_of_week=day_of_week,
                        event_type="game",
                        competition_id="regular_season",
                        competition_type="regular_season",
                        stage="regular_season",
                        home_team=home_team,
                        away_team=away_team,
                        round_number=round_idx,
                        is_playoff=False,
                        label=f"R{round_idx} {home_team.name} vs {away_team.name}",
                    )
                )

        return events

    def _group_events_by_round(self, events: List[SeasonEvent]) -> Dict[int, List[SeasonEvent]]:
        grouped: Dict[int, List[SeasonEvent]] = {}
        for event in events:
            grouped.setdefault(event.round_number, []).append(event)
        return grouped

    def get_competition(self, competition_id: str) -> Optional[Competition]:
        return self.competitions.get(competition_id)

    def get_events_for_round(self, round_number: int) -> List[SeasonEvent]:
        return self.events_by_round.get(round_number, [])

    def _set_phase(self, new_phase: str):
        self.phase = new_phase

    def _record_competition_team_result(
        self,
        competition_id: str,
        team,
        result_type: str,
        extra: Optional[dict] = None
    ):
        if team is None:
            return

        competition_name = self.competitions[competition_id].name if competition_id in self.competitions else competition_id

        title_map = {
            "promoted": "昇格",
            "relegated": "降格",
            "division_playoff_champion": "ディビジョン優勝",
            "division_playoff_runner_up": "ディビジョン準優勝",
            "emperor_cup_champion": "天皇杯優勝",
            "emperor_cup_runner_up": "天皇杯準優勝",
            "emperor_cup_semifinalist": "天皇杯ベスト4",
            "easl_participant": "EASL出場",
            "easl_group_winner": "EASLグループ首位通過",
            "easl_semifinalist": "EASLベスト4",
            "easl_champion": "EASL優勝",
            "easl_runner_up": "EASL準優勝",
            "acl_qualified_from_easl": "アジアクラブ選手権出場権獲得",
            "acl_participant": "アジアクラブ選手権出場",
            "acl_semifinalist": "アジアクラブ選手権ベスト4",
            "acl_champion": "アジアクラブ選手権優勝",
            "acl_runner_up": "アジアクラブ選手権準優勝",
        }

        detail = ""
        if extra:
            from_division = extra.get("from_division")
            to_division = extra.get("to_division")
            division = extra.get("division")
            group = extra.get("group")

            if result_type in {"promoted", "relegated"} and from_division and to_division:
                detail = f"D{from_division} → D{to_division}"
            elif result_type in {"division_playoff_champion", "division_playoff_runner_up"} and division:
                detail = f"D{division}"
            elif result_type == "easl_group_winner" and group:
                detail = f"Group {group}"
            elif division:
                detail = f"D{division}"

        season_value = getattr(self, "season_no", None)
        if season_value is None:
            season_value = getattr(self, "season_index", None)
        if season_value is None and hasattr(team, "history_seasons"):
            season_value = len(getattr(team, "history_seasons", []) or []) + 1

        payload = {
            "type": result_type,
            "milestone_type": result_type,
            "competition_id": competition_id,
            "competition_name": competition_name,
            "season_phase": self.phase,
            "season": season_value,
            "season_index": season_value,
            "title": title_map.get(result_type, competition_name),
            "detail": detail,
        }
        if extra:
            payload.update(extra)

        if hasattr(team, "add_history_milestone"):
            team.add_history_milestone(payload)

    def _record_division_season_history(self):
        for level in [1, 2, 3]:
            standings = self.get_standings(self.leagues[level])
            for rank, team in enumerate(standings, start=1):
                wins = getattr(team, "regular_wins", 0)
                losses = getattr(team, "regular_losses", 0)
                points_for = getattr(team, "regular_points_for", 0)
                points_against = getattr(team, "regular_points_against", 0)
                point_diff = points_for - points_against
                games = wins + losses
                win_pct = round((wins / games), 3) if games > 0 else 0.0

                if hasattr(team, "_ensure_history_fields"):
                    team._ensure_history_fields()

                season_index = len(getattr(team, "history_seasons", []) or []) + 1
                history_row = {
                    "season_index": season_index,
                    "season": season_index,
                    "league_level": level,
                    "division": level,
                    "rank": rank,
                    "wins": wins,
                    "losses": losses,
                    "regular_wins": wins,
                    "regular_losses": losses,
                    "win_pct": win_pct,
                    "points_for": points_for,
                    "points_against": points_against,
                    "point_diff": point_diff,
                    "team_power": round(getattr(team, "team_power", 0.0), 2),
                    "coach_style": getattr(team, "coach_style", "balanced"),
                    "strategy": getattr(team, "strategy", "balanced"),
                    "usage_policy": getattr(team, "usage_policy", "balanced"),
                    "season_type": "regular_season",
                }

                if hasattr(team, "history_seasons"):
                    team.history_seasons.append(history_row)

                season_milestone = {
                    "type": "season_summary",
                    "milestone_type": "season_summary",
                    "season": season_index,
                    "season_index": season_index,
                    "season_type": "regular_season",
                    "division": level,
                    "rank": rank,
                    "wins": wins,
                    "losses": losses,
                    "points_for": points_for,
                    "points_against": points_against,
                    "title": f"D{level} {rank}位",
                    "detail": f"{wins}勝{losses}敗 / 得点{points_for} / 失点{points_against} / 得失点差{point_diff:+}",
                }

                if hasattr(team, "add_history_milestone"):
                    team.add_history_milestone(season_milestone)

    def _build_double_round_robin_rounds(self, league_teams: List[Team]) -> List[List[Tuple[Team, Team]]]:
        if not league_teams:
            return []

        teams = league_teams[:]
        if len(teams) % 2 != 0:
            teams.append(None)

        first_half_rounds = []
        rotation = teams[:]

        for _ in range(len(rotation) - 1):
            round_games = []
            pair_count = len(rotation) // 2

            for i in range(pair_count):
                t1 = rotation[i]
                t2 = rotation[-(i + 1)]

                if t1 is None or t2 is None:
                    continue

                if i % 2 == 0:
                    round_games.append((t1, t2))
                else:
                    round_games.append((t2, t1))

            first_half_rounds.append(round_games)

            fixed = rotation[0]
            rest = rotation[1:]
            rest = [rest[-1]] + rest[:-1]
            rotation = [fixed] + rest

        second_half_rounds = []
        for round_games in first_half_rounds:
            reversed_round = [(away, home) for home, away in round_games]
            second_half_rounds.append(reversed_round)

        all_rounds = first_half_rounds + second_half_rounds

        for round_games in all_rounds:
            random.shuffle(round_games)

        return all_rounds

    def _prepare_regular_season_schedule(self) -> List[List[Tuple[Team, Team]]]:
        total_rounds = max(ROUND_CONFIG.keys()) if ROUND_CONFIG else 0
        if total_rounds <= 0:
            return []

        # ROUND_CONFIG の league_games_per_team を実際の日程へ反映する。
        # 1ラウンド内で複数試合を実施することで、想定試合数（60試合/年）を満たす。
        per_level_cycle_rounds: Dict[int, List[List[Tuple[Team, Team]]]] = {}
        per_level_cycle_cursor: Dict[int, int] = {}

        for level in [1, 2, 3]:
            cycle_rounds = self._build_double_round_robin_rounds(self.leagues[level])
            per_level_cycle_rounds[level] = cycle_rounds
            per_level_cycle_cursor[level] = 0

        schedule_by_round: List[List[Tuple[Team, Team]]] = []
        for round_no in range(1, total_rounds + 1):
            cfg = ROUND_CONFIG.get(round_no, {})
            games_per_team = int(cfg.get("league_games_per_team", 0) or 0)
            combined_round: List[Tuple[Team, Team]] = []

            for level in [1, 2, 3]:
                cycle_rounds = per_level_cycle_rounds[level]
                if not cycle_rounds or games_per_team <= 0:
                    continue

                for _ in range(games_per_team):
                    idx = per_level_cycle_cursor[level] % len(cycle_rounds)
                    combined_round.extend(cycle_rounds[idx])
                    per_level_cycle_cursor[level] += 1

            random.shuffle(combined_round)
            schedule_by_round.append(combined_round)

        return schedule_by_round

    # =========================
    # Emperor Cup
    # =========================
    def _initialize_emperor_cup_state(self):
        shuffled_teams = self.all_teams[:]
        random.shuffle(shuffled_teams)

        self.emperor_cup_bye_teams = shuffled_teams[:16]
        self.emperor_cup_round1_teams = shuffled_teams[16:]
        self.emperor_cup_current_teams = []
        self.emperor_cup_played_stages = set()

    def _pair_teams_randomly(self, teams: List) -> List[Tuple]:
        working = teams[:]
        random.shuffle(working)

        pairs = []
        for i in range(0, len(working), 2):
            if i + 1 >= len(working):
                break
            t1 = working[i]
            t2 = working[i + 1]

            if random.random() < 0.5:
                pairs.append((t1, t2))
            else:
                pairs.append((t2, t1))

        return pairs

    def _should_play_emperor_cup_this_round(self, round_number: int) -> bool:
        return self.emperor_cup_enabled and self._get_round_cup_event(round_number) is not None

    def _get_emperor_cup_stage_names(self, round_number: int) -> List[str]:
        cup_event = self._get_round_cup_event(round_number)
        if cup_event == "emperor_cup_week1":
            return ["round1", "round2", "round3"]
        if cup_event == "emperor_cup_week2":
            return ["quarterfinal", "semifinal", "final"]

        stage_value = self.emperor_cup_schedule.get(round_number)
        if stage_value is None:
            return []
        if isinstance(stage_value, list):
            return stage_value[:]
        return [stage_value]

    def _store_emperor_cup_stage_log(self, stage: str, lines: List[str]):
        self.emperor_cup_stage_logs[stage] = lines[:]

    def _print_emperor_cup_stage_summary(self, stage: str):
        lines = self.emperor_cup_stage_logs.get(stage, [])
        if not lines:
            return

        print(f"\n[全日本カップ {stage} 結果]")
        for line in lines:
            print(line)

    def _print_emperor_cup_bracket_summary(self):
        print("\n--- 全日本カップ トーナメント概要 ---")

        order = ["round1", "round2", "round3", "quarterfinal", "semifinal", "final"]
        stage_title = {
            "round1": "Round 1",
            "round2": "Round 2",
            "round3": "Round 3",
            "quarterfinal": "Quarterfinal",
            "semifinal": "Semifinal",
            "final": "Final",
        }

        for stage in order:
            lines = self.emperor_cup_stage_logs.get(stage, [])
            if not lines:
                continue
            print(f"\n[{stage_title[stage]}]")
            for line in lines:
                print(line)

        champion = self.emperor_cup_results.get("champion")
        runner_up = self.emperor_cup_results.get("runner_up")
        semifinalists = self.emperor_cup_results.get("semifinalists", [])

        print("\n[Final Result]")
        if champion is not None:
            print(f"Champion : {champion.name}")
        if runner_up is not None:
            print(f"Runner-up: {runner_up.name}")
        if semifinalists:
            print("Best 4:")
            for team in semifinalists:
                print(f"- {team.name}")

    def _format_cup_result_line(
        self,
        winner,
        loser,
        home_team,
        away_team,
        home_score: int,
        away_score: int
    ) -> str:
        if winner == home_team:
            winner_score = home_score
            loser_score = away_score
        else:
            winner_score = away_score
            loser_score = home_score

        return f"{winner.name} def. {loser.name} ({winner_score}-{loser_score})"

    def _play_emperor_cup_stage(self, stage: str):
        if stage in self.emperor_cup_played_stages:
            return

        print("\n--- 全日本カップ ---")
        print(f"Stage: {stage}")

        stage_log_lines = []

        if stage == "round1":
            pairings = self._pair_teams_randomly(self.emperor_cup_round1_teams)
            winners = []

            print(f"BYE Teams: {len(self.emperor_cup_bye_teams)}")
            print(f"Round 1 Teams: {len(self.emperor_cup_round1_teams)}")

            bye_names = ", ".join(team.name for team in self.emperor_cup_bye_teams)
            stage_log_lines.append(f"BYE: {bye_names}")

            for home_team, away_team in pairings:
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                winners.append(winner)
                loser = away_team if winner == home_team else home_team
                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=loser,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

            self.emperor_cup_current_teams = self.emperor_cup_bye_teams + winners

        elif stage == "round2":
            pairings = self._pair_teams_randomly(self.emperor_cup_current_teams)
            winners = []

            for home_team, away_team in pairings:
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                winners.append(winner)
                loser = away_team if winner == home_team else home_team
                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=loser,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

            self.emperor_cup_current_teams = winners

        elif stage == "round3":
            pairings = self._pair_teams_randomly(self.emperor_cup_current_teams)
            winners = []

            for home_team, away_team in pairings:
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                winners.append(winner)
                loser = away_team if winner == home_team else home_team
                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=loser,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

            self.emperor_cup_current_teams = winners

        elif stage == "quarterfinal":
            pairings = self._pair_teams_randomly(self.emperor_cup_current_teams)
            winners = []
            losers = []

            for home_team, away_team in pairings:
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                winners.append(winner)
                loser = away_team if winner == home_team else home_team
                losers.append(loser)
                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=loser,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

            self.emperor_cup_results["semifinalists"] = losers[:]
            self.emperor_cup_current_teams = winners

        elif stage == "semifinal":
            pairings = self._pair_teams_randomly(self.emperor_cup_current_teams)
            winners = []
            losers = []

            for home_team, away_team in pairings:
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                winners.append(winner)
                loser = away_team if winner == home_team else home_team
                losers.append(loser)
                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=loser,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

            self.emperor_cup_results["semifinalists"] = losers[:]
            self.emperor_cup_current_teams = winners

        elif stage == "final":
            if len(self.emperor_cup_current_teams) >= 2:
                home_team, away_team = self._pair_teams_randomly(self.emperor_cup_current_teams)[0]
                winner, home_score, away_score = Match(
                    home_team=home_team,
                    away_team=away_team,
                    is_playoff=True,
                    competition_type="emperor_cup"
                ).simulate()
                runner_up = away_team if winner == home_team else home_team

                self.emperor_cup_results["champion"] = winner
                self.emperor_cup_results["runner_up"] = runner_up
                self.emperor_cup_current_teams = [winner]

                stage_log_lines.append(
                    self._format_cup_result_line(
                        winner=winner,
                        loser=runner_up,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                    )
                )

                print(f"全日本カップ優勝: {winner.name}")
                print(f"全日本カップ準優勝: {runner_up.name}")

                self._record_competition_team_result(
                    competition_id="emperor_cup",
                    team=winner,
                    result_type="emperor_cup_champion",
                )
                self._record_competition_team_result(
                    competition_id="emperor_cup",
                    team=runner_up,
                    result_type="emperor_cup_runner_up",
                )

                for team in self.emperor_cup_results.get("semifinalists", []):
                    self._record_competition_team_result(
                        competition_id="emperor_cup",
                        team=team,
                        result_type="emperor_cup_semifinalist",
                    )

        self._store_emperor_cup_stage_log(stage, stage_log_lines)
        self._print_emperor_cup_stage_summary(stage)
        self.emperor_cup_played_stages.add(stage)

        remain_count = len(self.emperor_cup_current_teams)
        print(f"Remaining Teams after {stage}: {remain_count}")

    def _play_emperor_cup_round(self, round_number: int):
        stage_names = self._get_emperor_cup_stage_names(round_number)
        if not stage_names:
            return

        for stage in stage_names:
            if stage in self.emperor_cup_played_stages:
                continue
            self._play_emperor_cup_stage(stage)
    # =========================
    # EASL
    # =========================
    def _initialize_easl_state(self):
        if not self.easl_enabled:
            return

        domestic_teams = self._select_easl_domestic_teams()
        foreign_teams = self._generate_easl_foreign_teams()

        all_easl_teams = domestic_teams + foreign_teams
        self.easl_results["participants"] = all_easl_teams[:]

        self._build_easl_groups(all_easl_teams)
        self._build_easl_matchdays()

    def _get_latest_d1_playoff_finalists(self) -> List[Team]:
        latest_season = None
        champion = None
        runner_up = None

        for team in self.leagues.get(1, []):
            for row in list(getattr(team, "history_milestones", []) or []):
                row_type = row.get("milestone_type") or row.get("type")
                if row_type not in {"division_playoff_champion", "division_playoff_runner_up"}:
                    continue
                division = row.get("division")
                if division is None:
                    division = row.get("league_level")
                if division not in {1, "1"}:
                    continue
                season_value = row.get("season")
                if season_value is None:
                    season_value = row.get("season_index")
                try:
                    season_no = int(season_value)
                except Exception:
                    continue
                if latest_season is None or season_no > latest_season:
                    latest_season = season_no
                    champion = None
                    runner_up = None
                if season_no != latest_season:
                    continue
                if row_type == "division_playoff_champion":
                    champion = team
                elif row_type == "division_playoff_runner_up":
                    runner_up = team

        ordered = []
        if champion is not None:
            ordered.append(champion)
        if runner_up is not None and runner_up not in ordered:
            ordered.append(runner_up)
        return ordered

    def _select_easl_domestic_teams(self) -> List[Team]:
        d1_teams = list(self.leagues.get(1, []))
        selected: List[Team] = []

        print("\n[EASL国内出場チーム選定]")
        if getattr(self, "season_no", 1) <= 1:
            scored = []
            for team in d1_teams:
                team_power = getattr(team, "team_power", None)
                if team_power is None:
                    team_power = getattr(team, "overall_power", None)
                if team_power is None:
                    team_power = getattr(team, "ovr", None)
                scored.append((team, team_power))
            usable_scored = [(team, power) for team, power in scored if isinstance(power, (int, float))]
            if len(usable_scored) >= 2:
                usable_scored.sort(key=lambda x: float(x[1]), reverse=True)
                selected = [usable_scored[0][0], usable_scored[1][0]]
                print(f"1. {selected[0].name} | season1_team_power={float(usable_scored[0][1]):.1f}")
                print(f"2. {selected[1].name} | season1_team_power={float(usable_scored[1][1]):.1f}")
            else:
                pool = d1_teams[:]
                random.shuffle(pool)
                selected = pool[:2]
                for idx, team in enumerate(selected, start=1):
                    print(f"{idx}. {team.name} | season1_random")
        else:
            finalists = self._get_latest_d1_playoff_finalists()
            if len(finalists) >= 2:
                selected = finalists[:2]
                print(f"1. {selected[0].name} | 前年D1プレーオフ優勝")
                print(f"2. {selected[1].name} | 前年D1プレーオフ準優勝")
            else:
                d1_standings = self.get_standings(self.leagues[1])
                if len(d1_standings) >= 2:
                    selected = [d1_standings[0], d1_standings[1]]
                elif len(d1_standings) == 1:
                    selected = [d1_standings[0]]
                else:
                    selected = []
                while len(selected) < 2 and len(d1_teams) > len(selected):
                    fallback = d1_teams[len(selected)]
                    if fallback not in selected:
                        selected.append(fallback)
                for idx, team in enumerate(selected[:2], start=1):
                    print(f"{idx}. {team.name} | fallback")

        while len(selected) < 2 and len(d1_teams) > len(selected):
            fallback = d1_teams[len(selected)]
            if fallback not in selected:
                selected.append(fallback)

        for team in selected[:2]:
            self._record_competition_team_result(
                competition_id="easl",
                team=team,
                result_type="easl_participant",
                extra={"participant_type": "domestic"}
            )

        return selected[:2]

    def _generate_easl_foreign_teams(self) -> List[Team]:
        specs = [
            ("Seoul Falcons", "Korea", random.randint(80, 86)),
            ("Taipei Suns", "Taiwan", random.randint(79, 85)),
            ("Manila Waves", "Philippines", random.randint(80, 86)),
            ("Macau Black Bears", "Macau", random.randint(78, 84)),
            ("Ulaan Storm", "Mongolia", random.randint(76, 82)),
            ("Jakarta Garuda", "Indonesia", random.randint(77, 83)),
            ("Shanghai Comets", "China", random.randint(82, 88)),
            ("Shenzhen Leopards", "China", random.randint(81, 87)),
            ("West Asia Stars", "West Asia", random.randint(80, 86)),
            ("Oceania Breakers", "Oceania", random.randint(78, 84)),
        ]

        foreign_teams: List[Team] = []
        for name, region, power in specs:
            foreign_teams.append(self._create_easl_foreign_team(name=name, region=region, power=power))

        return foreign_teams

    def _next_foreign_team_id(self) -> int:
        current = self._foreign_exhibition_team_counter
        self._foreign_exhibition_team_counter -= 1
        return current

    def _next_foreign_player_id(self) -> int:
        current = self._foreign_exhibition_player_counter
        self._foreign_exhibition_player_counter -= 1
        return current

    def _create_foreign_exhibition_player(self, team_id: int, base_name: str, region: str, position: str, ovr: int, nationality: str) -> Player:
        position_archetypes = {
            "PG": "playmaker",
            "SG": "shooter",
            "SF": "wing",
            "PF": "stretch_big",
            "C": "rim_protector",
        }
        position_height = {
            "PG": 183,
            "SG": 191,
            "SF": 199,
            "PF": 205,
            "C": 211,
        }
        position_weight = {
            "PG": 80,
            "SG": 88,
            "SF": 97,
            "PF": 108,
            "C": 116,
        }
        position_usage = {
            "PG": 23,
            "SG": 22,
            "SF": 21,
            "PF": 19,
            "C": 18,
        }

        shoot = max(45, min(99, ovr + random.randint(-8, 5)))
        three = max(35, min(99, ovr + random.randint(-10, 6)))
        drive = max(40, min(99, ovr + random.randint(-8, 6)))
        passing = max(38, min(99, ovr + random.randint(-10, 5)))
        rebound = max(38, min(99, ovr + random.randint(-8, 7)))
        defense = max(42, min(99, ovr + random.randint(-7, 7)))
        ft = max(45, min(99, ovr + random.randint(-6, 8)))
        stamina = max(55, min(99, ovr + random.randint(-5, 8)))

        if position == "PG":
            passing = min(99, passing + 8)
            drive = min(99, drive + 5)
        elif position == "SG":
            shoot = min(99, shoot + 6)
            three = min(99, three + 8)
        elif position == "SF":
            defense = min(99, defense + 4)
            drive = min(99, drive + 4)
        elif position == "PF":
            rebound = min(99, rebound + 7)
            defense = min(99, defense + 5)
        elif position == "C":
            rebound = min(99, rebound + 10)
            defense = min(99, defense + 8)
            three = max(30, three - 6)

        return Player(
            player_id=self._next_foreign_player_id(),
            name=base_name,
            age=random.randint(24, 31),
            nationality=nationality,
            position=position,
            height_cm=position_height[position] + random.randint(-4, 4),
            weight_kg=position_weight[position] + random.randint(-5, 6),
            shoot=shoot,
            three=three,
            drive=drive,
            passing=passing,
            rebound=rebound,
            defense=defense,
            ft=ft,
            stamina=stamina,
            ovr=ovr,
            potential="B",
            archetype=position_archetypes[position],
            usage_base=position_usage[position],
            team_id=team_id,
            popularity=45,
            acquisition_type="international",
            acquisition_note=f"{region} foreign club",
            years_pro=random.randint(3, 9),
            league_years=random.randint(1, 5),
        )

    def _create_easl_foreign_team(self, name: str, region: str, power: int) -> Team:
        team_id = self._next_foreign_team_id()
        team = Team(
            team_id=team_id,
            name=name,
            league_level=1,
            strategy="balanced",
            coach_style=random.choice(["balanced", "offense", "defense"]),
            usage_policy="balanced",
            home_city=region,
            market_size=1.0,
            popularity=55,
        )
        setattr(team, "is_foreign_club", True)
        setattr(team, "foreign_region", region)
        setattr(team, "team_power", float(power))

        position_plan = [
            ("PG", 2),
            ("SG", 3),
            ("SF", 3),
            ("PF", 3),
            ("C", 2),
        ]
        # EASLレギュレーションでそのまま戦えるよう、ベンチ登録想定は
        # Foreign 2 / Asia 1 / Local 10 に寄せる。
        nationality_slots = ["Foreign", "Foreign", "Asia"] + ["Local"] * 10
        random.shuffle(nationality_slots)

        player_index = 1
        for position, count in position_plan:
            for _ in range(count):
                nationality = nationality_slots.pop()
                player_ovr = max(62, min(95, power + random.randint(-8, 6)))
                player = self._create_foreign_exhibition_player(
                    team_id=team_id,
                    base_name=f"{name.split()[0]}_{player_index}",
                    region=region,
                    position=position,
                    ovr=player_ovr,
                    nationality=nationality,
                )
                team.add_player(player)
                player_index += 1

        return team

    def _simulate_competition_match(self, home_team, away_team, competition_type: str) -> Tuple[object, int, int]:
        if isinstance(home_team, Team) and isinstance(away_team, Team):
            result = Match(home_team, away_team, is_playoff=True, competition_type=competition_type).simulate()
            if isinstance(result, tuple):
                winner = result[0]
                home_score = result[1] if len(result) > 1 else 0
                away_score = result[2] if len(result) > 2 else 0
                return winner, home_score, away_score
            winner = result
            home_score = getattr(home_team, "last_game_score", 0)
            away_score = getattr(away_team, "last_game_score", 0)
            return winner, home_score, away_score

        return self._simulate_easl_game(home_team, away_team)

    def _build_easl_groups(self, teams: List):
        working = teams[:]
        random.shuffle(working)

        self.easl_groups = {
            "A": working[0:4],
            "B": working[4:8],
            "C": working[8:12],
        }

        self.easl_group_records = {}
        for group_name, group_teams in self.easl_groups.items():
            for team in group_teams:
                key = self._easl_team_key(team)
                self.easl_group_records[key] = {
                    "team": team,
                    "group": group_name,
                    "wins": 0,
                    "losses": 0,
                    "points_for": 0,
                    "points_against": 0,
                }

    def _build_easl_matchdays(self):
        self.easl_matchdays = {}
        for group_name, group_teams in self.easl_groups.items():
            a, b, c, d = group_teams

            schedule = {
                "group_md1": [(a, b), (c, d)],
                "group_md2": [(a, c), (b, d)],
                "group_md3": [(a, d), (b, c)],
                "group_md4": [(b, a), (d, c)],
                "group_md5": [(c, a), (d, b)],
                "group_md6": [(d, a), (c, b)],
            }

            for stage, pairs in schedule.items():
                self.easl_matchdays.setdefault(stage, [])
                self.easl_matchdays[stage].extend(pairs)

    def _easl_team_key(self, team) -> str:
        if isinstance(team, dict):
            return f"foreign::{team['name']}"
        return f"domestic::{team.name}"

    def _simulate_easl_game(self, home_team, away_team) -> Tuple[object, int, int]:
        home_power = self._get_easl_team_power(home_team)
        away_power = self._get_easl_team_power(away_team)

        base_home = random.randint(68, 92)
        base_away = random.randint(68, 92)

        home_score = base_home + int((home_power - away_power) * 1.2) + random.randint(0, 6)
        away_score = base_away + int((away_power - home_power) * 1.0) + random.randint(0, 4)

        home_score = max(50, home_score)
        away_score = max(50, away_score)

        while home_score == away_score:
            home_score += random.randint(3, 8)
            away_score += random.randint(0, 6)

        winner = home_team if home_score > away_score else away_team
        return winner, home_score, away_score

    def _get_easl_team_power(self, team) -> int:
        if isinstance(team, dict):
            return int(team.get("power", 80))

        roster = getattr(team, "players", [])
        if not roster:
            return 75

        top_players = sorted(roster, key=lambda p: getattr(p, "ovr", 50), reverse=True)[:8]
        if not top_players:
            return 75

        return int(sum(getattr(p, "ovr", 50) for p in top_players) / len(top_players))

    def _get_easl_team_name(self, team) -> str:
        if isinstance(team, dict):
            return team["name"]
        return team.name

    def _build_easl_top2_payload(self, team, result_type: str) -> dict:
        return {
            "type": result_type,
            "name": self._get_easl_team_name(team),
            "is_external": bool(getattr(team, "is_foreign_club", False)),
            "region": getattr(team, "foreign_region", getattr(team, "home_city", "External")),
            "power": int(getattr(team, "team_power", self._get_easl_team_power(team))),
        }

    def _broadcast_easl_top2_payloads(self):
        payloads = list(self.easl_top2_payloads or [])
        for team in self.all_teams:
            setattr(team, "_latest_easl_top2_payloads", payloads)

    def _update_easl_group_record(self, team, points_for: int, points_against: int, is_win: bool):
        key = self._easl_team_key(team)
        record = self.easl_group_records[key]
        record["points_for"] += points_for
        record["points_against"] += points_against
        if is_win:
            record["wins"] += 1
        else:
            record["losses"] += 1

    def _get_easl_group_standings(self, group_name: str) -> List[dict]:
        rows = [
            rec for rec in self.easl_group_records.values()
            if rec["group"] == group_name
        ]
        rows.sort(
            key=lambda r: (
                r["wins"],
                r["points_for"] - r["points_against"],
                r["points_for"],
                random.random(),
            ),
            reverse=True
        )
        return rows

    def _print_easl_group_tables(self):
        print("\n[EASL Group Standings]")
        for group_name in ["A", "B", "C"]:
            print(f"\nGroup {group_name}")
            rows = self._get_easl_group_standings(group_name)
            for i, row in enumerate(rows, 1):
                team_name = self._get_easl_team_name(row["team"])
                diff = row["points_for"] - row["points_against"]
                print(
                    f" {i}. {team_name:<24} "
                    f"{row['wins']}-{row['losses']} "
                    f"Diff:{diff:+}"
                )

    def _select_easl_knockout_teams(self):
        group_winners = []
        second_place_rows = []

        for group_name in ["A", "B", "C"]:
            standings = self._get_easl_group_standings(group_name)
            if len(standings) >= 1:
                group_winners.append(standings[0]["team"])
                self._record_competition_team_result(
                    competition_id="easl",
                    team=standings[0]["team"],
                    result_type="easl_group_winner",
                    extra={"group": group_name}
                )
            if len(standings) >= 2:
                second_place_rows.append(standings[1])

        second_place_rows.sort(
            key=lambda r: (
                r["wins"],
                r["points_for"] - r["points_against"],
                r["points_for"],
                random.random(),
            ),
            reverse=True
        )

        best_second = second_place_rows[0]["team"] if second_place_rows else None

        knockout = group_winners[:]
        if best_second is not None:
            knockout.append(best_second)

        self.easl_knockout_teams = knockout[:4]
        return self.easl_knockout_teams

    def _store_easl_stage_log(self, stage: str, lines: List[str]):
        self.easl_stage_logs[stage] = lines[:]

    def _print_easl_stage_summary(self, stage: str):
        lines = self.easl_stage_logs.get(stage, [])
        if not lines:
            return

        print(f"\n[EASL {stage} Results]")
        for line in lines:
            print(line)

    def _print_easl_summary(self):
        print("\n--- EASL Summary ---")

        stage_order = [
            "group_md1", "group_md2", "group_md3",
            "group_md4", "group_md5", "group_md6",
            "semifinal", "final"
        ]
        for stage in stage_order:
            lines = self.easl_stage_logs.get(stage, [])
            if not lines:
                continue
            print(f"\n[{stage}]")
            for line in lines:
                print(line)

        self._print_easl_group_tables()

        champion = self.easl_results.get("champion")
        runner_up = self.easl_results.get("runner_up")
        semifinalists = self.easl_results.get("semifinalists", [])

        print("\n[EASL Final Result]")
        if champion is not None:
            print(f"Champion : {self._get_easl_team_name(champion)}")
        if runner_up is not None:
            print(f"Runner-up: {self._get_easl_team_name(runner_up)}")
        if semifinalists:
            print("Best 4:")
            for team in semifinalists:
                print(f"- {self._get_easl_team_name(team)}")

        if self.easl_acl_qualifiers:
            print("\n[アジアクラブ選手権出場権（東アジアトップリーグ）]")
            for i, team in enumerate(self.easl_acl_qualifiers, 1):
                print(f"{i}. {self._get_easl_team_name(team)}")

    def _format_easl_result_line(self, winner, loser, home_team, away_team, home_score: int, away_score: int) -> str:
        if winner == home_team:
            winner_score = home_score
            loser_score = away_score
        else:
            winner_score = away_score
            loser_score = home_score
        return f"{self._get_easl_team_name(winner)} def. {self._get_easl_team_name(loser)} ({winner_score}-{loser_score})"

    def _set_easl_acl_qualifiers(self):
        champion = self.easl_results.get("champion")
        runner_up = self.easl_results.get("runner_up")

        qualifiers = []
        if champion is not None:
            qualifiers.append(champion)
        if runner_up is not None:
            qualifiers.append(runner_up)

        self.easl_acl_qualifiers = qualifiers[:2]

        for team in self.easl_acl_qualifiers:
            self._record_competition_team_result(
                competition_id="easl",
                team=team,
                result_type="acl_qualified_from_easl"
            )

    def get_acl_qualifiers_from_easl(self) -> List:
        return self.easl_acl_qualifiers[:]

    def _play_easl_stage(self, round_number: int):
        stage = self._get_round_easl_stage(round_number)
        if stage is None or stage in self.easl_played_stages:
            return

        print("\n--- EASL ---")
        print(f"Stage: {stage}")

        stage_lines = []

        if stage.startswith("group_md"):
            pairings = self.easl_matchdays.get(stage, [])
            for home_team, away_team in pairings:
                print(f"[EASL-MATCH] competition_type=easl | stage={stage} | {self._get_easl_team_name(home_team)} vs {self._get_easl_team_name(away_team)}")
                winner, home_score, away_score = self._simulate_competition_match(home_team, away_team, "easl")
                loser = away_team if winner == home_team else home_team

                self._update_easl_group_record(home_team, home_score, away_score, winner == home_team)
                self._update_easl_group_record(away_team, away_score, home_score, winner == away_team)

                stage_lines.append(
                    self._format_easl_result_line(
                        winner, loser, home_team, away_team, home_score, away_score
                    )
                )

            if stage == "group_md6":
                knockout = self._select_easl_knockout_teams()
                stage_lines.append("Knockout Teams:")
                for team in knockout:
                    stage_lines.append(f"- {self._get_easl_team_name(team)}")

            self._store_easl_stage_log(stage, stage_lines)
            self._print_easl_stage_summary(stage)
            self._print_easl_group_tables()

        elif stage == "semifinal":
            knockout = self.easl_knockout_teams[:]
            if len(knockout) < 4:
                knockout = self._select_easl_knockout_teams()

            random.shuffle(knockout)
            self.easl_semifinal_pairs = [
                (knockout[0], knockout[1]),
                (knockout[2], knockout[3]),
            ]
            winners = []
            losers = []

            for home_team, away_team in self.easl_semifinal_pairs:
                print(f"[EASL-MATCH] competition_type=easl | stage={stage} | {self._get_easl_team_name(home_team)} vs {self._get_easl_team_name(away_team)}")
                winner, home_score, away_score = self._simulate_competition_match(home_team, away_team, "easl")
                loser = away_team if winner == home_team else home_team
                winners.append(winner)
                losers.append(loser)
                stage_lines.append(
                    self._format_easl_result_line(
                        winner, loser, home_team, away_team, home_score, away_score
                    )
                )

            self.easl_current_finalists = winners[:]
            self.easl_results["semifinalists"] = losers[:]

            for team in winners + losers:
                self._record_competition_team_result(
                    competition_id="easl",
                    team=team,
                    result_type="easl_semifinalist"
                )

            self._store_easl_stage_log(stage, stage_lines)
            self._print_easl_stage_summary(stage)

        elif stage == "final":
            if len(self.easl_current_finalists) >= 2:
                home_team, away_team = self.easl_current_finalists[0], self.easl_current_finalists[1]
                print(f"[EASL-MATCH] competition_type=easl | stage={stage} | {self._get_easl_team_name(home_team)} vs {self._get_easl_team_name(away_team)}")
                winner, home_score, away_score = self._simulate_competition_match(home_team, away_team, "easl")
                runner_up = away_team if winner == home_team else home_team

                self.easl_results["champion"] = winner
                self.easl_results["runner_up"] = runner_up
                self._set_easl_acl_qualifiers()

                stage_lines.append(
                    self._format_easl_result_line(
                        winner, runner_up, home_team, away_team, home_score, away_score
                    )
                )

                print(f"EASL Champion: {self._get_easl_team_name(winner)}")
                print(f"EASL Runner-up: {self._get_easl_team_name(runner_up)}")

                self.easl_top2_payloads = [
                    self._build_easl_top2_payload(winner, "easl_champion"),
                    self._build_easl_top2_payload(runner_up, "easl_runner_up"),
                ]
                self.easl_results["top2_payloads"] = self.easl_top2_payloads[:]
                self._broadcast_easl_top2_payloads()

                if self.easl_acl_qualifiers:
                    print("[アジアクラブ選手権出場チーム]")
                    for i, team in enumerate(self.easl_acl_qualifiers, 1):
                        print(f" {i}. {self._get_easl_team_name(team)}")

                self._record_competition_team_result(
                    competition_id="easl",
                    team=winner,
                    result_type="easl_champion"
                )
                self._record_competition_team_result(
                    competition_id="easl",
                    team=runner_up,
                    result_type="easl_runner_up"
                )

                self._store_easl_stage_log(stage, stage_lines)
                self._print_easl_stage_summary(stage)

        self.easl_played_stages.add(stage)

    def _should_play_easl_this_round(self, round_number: int) -> bool:
        return self.easl_enabled and self._get_round_easl_stage(round_number) is not None

    # =========================
    # ACL
    # =========================
    def _generate_acl_foreign_teams(self) -> List[dict]:
        names = [
            ("Riyadh Falcons", "West Asia", random.randint(80, 86)),
            ("Dubai Mirage", "West Asia", random.randint(80, 86)),
            ("Sydney Waves", "Oceania", random.randint(78, 84)),
            ("Melbourne Storm", "Oceania", random.randint(78, 84)),
            ("Beijing Guardians", "China", random.randint(82, 88)),
            ("Shanghai Comets", "China", random.randint(82, 88)),
        ]

        teams = []
        for name, region, power in names:
            teams.append({
                "name": name,
                "region": region,
                "power": power,
                "is_foreign_club": True,
            })

        return teams

    def _get_acl_team_name(self, team) -> str:
        if isinstance(team, dict):
            return team["name"]
        return team.name

    def _get_acl_team_power(self, team) -> int:
        if isinstance(team, dict):
            return int(team.get("power", 80))

        roster = getattr(team, "players", [])
        if not roster:
            return 75

        top_players = sorted(roster, key=lambda p: getattr(p, "ovr", 50), reverse=True)[:8]
        if not top_players:
            return 75

        return int(sum(getattr(p, "ovr", 50) for p in top_players) / len(top_players))

    def _simulate_acl_game(self, home_team, away_team) -> Tuple[object, int, int]:
        home_power = self._get_acl_team_power(home_team)
        away_power = self._get_acl_team_power(away_team)

        base_home = random.randint(70, 94)
        base_away = random.randint(70, 94)

        home_score = base_home + int((home_power - away_power) * 1.25) + random.randint(0, 6)
        away_score = base_away + int((away_power - home_power) * 1.05) + random.randint(0, 4)

        home_score = max(55, home_score)
        away_score = max(55, away_score)

        while home_score == away_score:
            home_score += random.randint(3, 8)
            away_score += random.randint(0, 6)

        winner = home_team if home_score > away_score else away_team
        return winner, home_score, away_score

    def _format_acl_result_line(self, winner, loser, home_team, away_team, home_score: int, away_score: int) -> str:
        if winner == home_team:
            winner_score = home_score
            loser_score = away_score
        else:
            winner_score = away_score
            loser_score = home_score
        return f"{self._get_acl_team_name(winner)} def. {self._get_acl_team_name(loser)} ({winner_score}-{loser_score})"

    def _store_acl_stage_log(self, stage: str, lines: List[str]):
        self.acl_stage_logs[stage] = lines[:]

    def _print_acl_stage_summary(self, stage: str):
        lines = self.acl_stage_logs.get(stage, [])
        if not lines:
            return

        print(f"\n[アジアクラブ選手権 {stage} 結果]")
        for line in lines:
            print(line)

    def _print_acl_summary(self):
        print("\n--- アジアクラブ選手権 Summary ---")

        stage_order = ["quarterfinal", "semifinal", "final"]
        for stage in stage_order:
            lines = self.acl_stage_logs.get(stage, [])
            if not lines:
                continue
            print(f"\n[{stage}]")
            for line in lines:
                print(line)

        champion = self.acl_results.get("champion")
        runner_up = self.acl_results.get("runner_up")
        semifinalists = self.acl_results.get("semifinalists", [])

        print("\n[アジアクラブ選手権 最終結果]")
        if champion is not None:
            print(f"Champion : {self._get_acl_team_name(champion)}")
        if runner_up is not None:
            print(f"Runner-up: {self._get_acl_team_name(runner_up)}")
        if semifinalists:
            print("Best 4:")
            for team in semifinalists:
                print(f"- {self._get_acl_team_name(team)}")

    def _play_acl_competition(self):
        if not self.acl_enabled or self.acl_played:
            return
        if len(self.easl_acl_qualifiers) < 2:
            return

        print("\n=== アジアクラブ選手権 ===")

        domestic_teams = self.get_acl_qualifiers_from_easl()[:2]
        foreign_teams = self._generate_acl_foreign_teams()

        participants = domestic_teams + foreign_teams
        self.acl_results["participants"] = participants[:]

        for team in domestic_teams:
            self._record_competition_team_result(
                competition_id="asia_cl",
                team=team,
                result_type="acl_participant"
            )

        print("\nアジアクラブ選手権出場チーム:")
        for i, team in enumerate(participants, 1):
            print(f"{i}. {self._get_acl_team_name(team)}")

        easl_champ = domestic_teams[0]
        easl_runner = domestic_teams[1]

        west1 = foreign_teams[0]
        west2 = foreign_teams[1]
        oce1 = foreign_teams[2]
        oce2 = foreign_teams[3]
        china1 = foreign_teams[4]
        china2 = foreign_teams[5]

        quarterfinals = [
            (easl_champ, oce2),
            (china1, west2),
            (easl_runner, west1),
            (china2, oce1),
        ]

        print("\n--- アジアクラブ選手権 準々決勝 ---")
        qf_lines = []
        qf_winners = []
        qf_losers = []

        for home_team, away_team in quarterfinals:
            winner, home_score, away_score = self._simulate_acl_game(home_team, away_team)
            loser = away_team if winner == home_team else home_team
            qf_winners.append(winner)
            qf_losers.append(loser)
            qf_lines.append(
                self._format_acl_result_line(
                    winner, loser, home_team, away_team, home_score, away_score
                )
            )

        self._store_acl_stage_log("quarterfinal", qf_lines)
        self._print_acl_stage_summary("quarterfinal")

        semifinals = [
            (qf_winners[0], qf_winners[1]),
            (qf_winners[2], qf_winners[3]),
        ]

        print("\n--- アジアクラブ選手権 準決勝 ---")
        sf_lines = []
        sf_winners = []
        sf_losers = []

        for home_team, away_team in semifinals:
            winner, home_score, away_score = self._simulate_acl_game(home_team, away_team)
            loser = away_team if winner == home_team else home_team
            sf_winners.append(winner)
            sf_losers.append(loser)
            sf_lines.append(
                self._format_acl_result_line(
                    winner, loser, home_team, away_team, home_score, away_score
                )
            )

        self.acl_results["semifinalists"] = sf_losers[:]

        for team in sf_winners + sf_losers:
            if not isinstance(team, dict):
                self._record_competition_team_result(
                    competition_id="asia_cl",
                    team=team,
                    result_type="acl_semifinalist"
                )

        self._store_acl_stage_log("semifinal", sf_lines)
        self._print_acl_stage_summary("semifinal")

        print("\n--- アジアクラブ選手権 決勝 ---")
        final_lines = []

        home_team, away_team = sf_winners[0], sf_winners[1]
        winner, home_score, away_score = self._simulate_acl_game(home_team, away_team)
        runner_up = away_team if winner == home_team else home_team

        self.acl_results["champion"] = winner
        self.acl_results["runner_up"] = runner_up

        final_lines.append(
            self._format_acl_result_line(
                winner, runner_up, home_team, away_team, home_score, away_score
            )
        )

        if not isinstance(winner, dict):
            self._record_competition_team_result(
                competition_id="asia_cl",
                team=winner,
                result_type="acl_champion"
            )
        if not isinstance(runner_up, dict):
            self._record_competition_team_result(
                competition_id="asia_cl",
                team=runner_up,
                result_type="acl_runner_up"
            )

        self._store_acl_stage_log("final", final_lines)
        self._print_acl_stage_summary("final")

        print("\n[アジアクラブ選手権 最終結果]")
        print(f"Champion: {self._get_acl_team_name(winner)}")
        print(f"Runner-up: {self._get_acl_team_name(runner_up)}")

        self.acl_played = True

    # =========================
    # In-season FA
    # =========================
    def _process_inseason_free_agency(self, round_number: int):
        if not self.free_agents:
            return

        logs = run_cpu_fa_market_cycle(
            teams=self.all_teams,
            free_agents=self.free_agents,
            max_signings_per_team=1,
            simulated_round=round_number,
        )

        if not logs:
            return

        print("\n[In-Season Free Agency]")
        for line in logs:
            print(line)

    # =========================
    # Simulation
    # =========================
    def simulate_next_round(self):
        if self.season_finished:
            print("\nシーズンはすでに終了しています。")
            return

        if self.current_round == 0:
            print("\n--- Reguler Season Simulation ---")

        self._set_phase("regular_season")

        round_number = self.current_round + 1
        round_events = self.get_events_for_round(round_number)
        national_window_key = self._get_round_national_window(round_number)
        is_national_team_break = bool(national_window_key)

        print(f"\n========== ラウンド {round_number}/{self.total_rounds} ==========")

        if is_national_team_break:
            self._print_national_team_window_banner(round_number)
            self._run_national_team_window_log_only(round_number)
        else:
            self._apply_pending_national_team_returns(round_number)

        round_points = 0
        round_game_count = 0

        for event in round_events:
            if event.event_type != "game":
                continue
            if event.home_team is None or event.away_team is None:
                continue
            if is_national_team_break and event.competition_type == "regular_season":
                continue

            match = Match(
                home_team=event.home_team,
                away_team=event.away_team,
                is_playoff=event.is_playoff,
                competition_type=event.competition_type
            )
            _, home_score, away_score = match.simulate()
            self.game_results.append({
                "home_team": event.home_team.name,
                "away_team": event.away_team.name,
                "home_score": home_score,
                "away_score": away_score,
                "score_diff": abs(home_score - away_score),
                "total_score": home_score + away_score,
            })
            round_points += (home_score + away_score)
            round_game_count += 1

        self._process_inseason_free_agency(round_number)

        if self._should_play_easl_this_round(round_number):
            self._play_easl_stage(round_number)

        if self._should_play_emperor_cup_this_round(round_number):
            self._play_emperor_cup_round(round_number)

        self.total_points += round_points
        self.game_count += round_game_count
        self.current_round += 1

        try:
            from basketball_sim.systems.cpu_management import run_cpu_management_after_round

            run_cpu_management_after_round(self)
        except Exception:
            pass

        avg_total = round_points / round_game_count if round_game_count > 0 else 0.0
        print(f"ラウンド消化試合数: {round_game_count}")
        print(f"ラウンド平均総得点: {avg_total:.1f}")

        if self.current_round >= self.total_rounds:
            self._finalize_season()

    def simulate_multiple_rounds(self, rounds: int):
        if rounds <= 0:
            return

        for _ in range(rounds):
            if self.season_finished:
                break
            self.simulate_next_round()

    def simulate_to_end(self):
        while not self.season_finished:
            self.simulate_next_round()

    def simulate_season(self):
        self.simulate_to_end()

    def _finalize_season(self):
        if self._finalized:
            return

        self._finalized = True
        self._set_phase("domestic_postseason")

        print("\nSeason finished")

        if self.game_count > 0:
            avg_team_score = self.total_points / (self.game_count * 2)
            avg_total_score = self.total_points / self.game_count
            print("\n--- League Scoring Stats ---")
            print(f"Games Played: {self.game_count}")
            print(f"Average Team Score: {avg_team_score:.1f}")
            print(f"Average Total Score: {avg_total_score:.1f}")
            self._print_scoring_distribution_summary()

        if self.easl_results["champion"] is not None:
            print("\n--- 東アジアトップリーグ 結果 ---")
            print(f"Champion: {self._get_easl_team_name(self.easl_results['champion'])}")
            if self.easl_results["runner_up"] is not None:
                print(f"Runner-up: {self._get_easl_team_name(self.easl_results['runner_up'])}")
            self._print_easl_summary()

        if self.emperor_cup_results["champion"] is not None:
            print("\n--- 全日本カップ 結果 ---")
            print(f"Champion: {self.emperor_cup_results['champion'].name}")
            if self.emperor_cup_results["runner_up"] is not None:
                print(f"Runner-up: {self.emperor_cup_results['runner_up'].name}")
            self._print_emperor_cup_bracket_summary()

        self._print_stat_leaders_by_division()
        self._calculate_and_print_awards_by_division()

        playoff_results = self._simulate_all_playoffs()
        self._record_playoff_results(playoff_results)
        self._process_promotion_relegation(self.leagues, playoff_results)

        self._set_phase("continental_postseason")
        self._play_acl_competition()

        if self.acl_results["champion"] is not None:
            self._print_acl_summary()

        self._update_popularity()
        self._print_popularity_rankings()

        self._process_finances()

        self._record_division_season_history()
        self._print_position_stat_profile()

        self._apply_career_stats()

        self._set_phase("offseason")
        self.season_finished = True

    def _record_playoff_results(self, playoff_results: dict):
        for level in [1, 2, 3]:
            result = playoff_results.get(level, {})
            champion = result.get("champion")
            runner_up = result.get("runner_up")

            self._record_competition_team_result(
                competition_id="division_playoffs",
                team=champion,
                result_type="division_playoff_champion",
                extra={"division": level}
            )
            self._record_competition_team_result(
                competition_id="division_playoffs",
                team=runner_up,
                result_type="division_playoff_runner_up",
                extra={"division": level}
            )

    def print_midseason_leaderboards(self):
        print("\n==============================")
        print("   シーズン途中ランキング")
        print("==============================")

        if self.game_count == 0:
            print("まだ試合が行われていないため、ランキングはありません。")
            return

        PlayerStatsManager.print_leaderboards(
            teams=self.all_teams,
            top_n=10,
            min_games=1
        )

    def print_midseason_standings(self):
        print("\n==============================")
        print("      シーズン途中順位表")
        print("==============================")

        for level in [1, 2, 3]:
            teams_in_league = self.leagues[level]
            if not teams_in_league:
                continue

            standings = self.get_standings(teams_in_league)

            print(f"\n[Division {level}]")
            for i, t in enumerate(standings, 1):
                point_diff = t.regular_points_for - t.regular_points_against
                print(
                    f" {i}. {t.name:<25} "
                    f"({t.regular_wins}-{t.regular_losses}) "
                    f"得失点差:{point_diff:+}"
                )

    def print_progress(self):
        print("\n==============================")
        print("          進行状況")
        print("==============================")
        print(f"現在フェーズ: {self.phase}")
        print(f"消化ラウンド: {self.current_round}/{self.total_rounds}")
        print(f"残りラウンド: {self.total_rounds - self.current_round}")
        print(f"消化試合数: {self.game_count}")

        if self.easl_enabled:
            played = sorted(list(self.easl_played_stages))
            easl_status = ", ".join(played) if played else "未開催"
            print(f"EASL進行: {easl_status}")

            if self.easl_acl_qualifiers:
                names = ", ".join(self._get_easl_team_name(t) for t in self.easl_acl_qualifiers)
                print(f"アジアクラブ選手権出場権(東アジアトップリーグ): {names}")

        if self.emperor_cup_enabled:
            played = sorted(list(self.emperor_cup_played_stages))
            cup_status = ", ".join(played) if played else "未開催"
            print(f"天皇杯進行: {cup_status}")

        if self.acl_enabled:
            if self.acl_played:
                champion = self.acl_results.get("champion")
                champion_name = self._get_acl_team_name(champion) if champion is not None else "TBD"
                print(f"アジアクラブ選手権進行: 完了 / Champion: {champion_name}")
            else:
                print("アジアクラブ選手権進行: 未開催")

    def get_standings(self, teams: List[Team]) -> List[Team]:
        return sorted(
            teams,
            key=lambda t: (t.regular_wins, t.regular_points_for - t.regular_points_against),
            reverse=True
        )

    def _get_playoff_teams_for_level(self, level: int) -> List[Team]:
        standings = self.get_standings(self.leagues[level])
        return standings[:8]

    def _simulate_playoffs_for_division(self, level: int):
        playoff_teams = self._get_playoff_teams_for_level(level)

        print(f"\n--- Division {level} Playoffs ---")

        if not playoff_teams:
            print("対象チームなし")
            return {
                "champion": None,
                "runner_up": None,
                "playoff_teams": [],
            }

        if len(playoff_teams) < 8:
            champion = playoff_teams[0]
            runner_up = playoff_teams[1] if len(playoff_teams) >= 2 else None
            if champion:
                print(f"Champion: {champion.name}")
            if runner_up:
                print(f"Runner-up: {runner_up.name}")
            return {
                "champion": champion,
                "runner_up": runner_up,
                "playoff_teams": playoff_teams,
            }

        qf_winners = []
        matchups = [(0, 7), (1, 6), (2, 5), (3, 4)]

        for h_rank, a_rank in matchups:
            t1 = playoff_teams[h_rank]
            t2 = playoff_teams[a_rank]
            winner, _, _ = Match(home_team=t1, away_team=t2, is_playoff=True, competition_type="playoff").simulate()
            qf_winners.append(winner)

        sf_winners = []
        for i in range(0, 4, 2):
            t1 = qf_winners[i]
            t2 = qf_winners[i + 1]
            winner, _, _ = Match(home_team=t1, away_team=t2, is_playoff=True, competition_type="playoff").simulate()
            sf_winners.append(winner)

        champion, _, _ = Match(home_team=sf_winners[0], away_team=sf_winners[1], is_playoff=True, competition_type="playoff").simulate()
        runner_up = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]

        print(f"Champion: {champion.name}")
        print(f"Runner-up: {runner_up.name}")

        return {
            "champion": champion,
            "runner_up": runner_up,
            "playoff_teams": playoff_teams,
        }

    def _simulate_all_playoffs(self):
        results = {}
        for level in [1, 2, 3]:
            results[level] = self._simulate_playoffs_for_division(level)
        return results

    def _teams_below_payroll_floor(self, leagues: dict, level: int) -> List[Team]:
        from basketball_sim.systems.contract_logic import get_team_payroll
        from basketball_sim.systems.salary_cap_budget import get_payroll_floor

        floor = get_payroll_floor(level)
        if floor <= 0:
            return []
        out: List[Team] = []
        for t in leagues[level]:
            if int(get_team_payroll(t)) < floor:
                out.append(t)
        return out

    def _promotion_candidates_from_division(
        self,
        playoff_results: dict,
        standings: List[Team],
        division_level: int,
        needed: int,
    ) -> List[Team]:
        if needed <= 0:
            return []
        div_result = playoff_results.get(division_level, {})
        promoted: List[Team] = []
        eligible = set(standings)
        champ = div_result.get("champion")
        ru = div_result.get("runner_up")
        if champ is not None and champ in eligible:
            promoted.append(champ)
        if ru is not None and ru not in promoted and ru in eligible:
            promoted.append(ru)
        for t in standings:
            if t not in promoted:
                promoted.append(t)
            if len(promoted) >= needed:
                break
        return promoted[:needed]

    def _process_promotion_relegation(self, leagues: dict, playoff_results: dict):
        print("\n--- Final Standings & Promotion/Relegation ---")

        d1_standings = self.get_standings(leagues[1])
        d2_standings = self.get_standings(leagues[2])
        d3_standings = self.get_standings(leagues[3])

        print("\n[Division 1]")
        for i, t in enumerate(d1_standings, 1):
            print(f" {i}. {t.name:<25} ({t.regular_wins}-{t.regular_losses})")

        print("\n[Division 2]")
        for i, t in enumerate(d2_standings, 1):
            print(f" {i}. {t.name:<25} ({t.regular_wins}-{t.regular_losses})")

        print("\n[Division 3]")
        for i, t in enumerate(d3_standings, 1):
            print(f" {i}. {t.name:<25} ({t.regular_wins}-{t.regular_losses})")

        d1_floor_violators = self._teams_below_payroll_floor(leagues, 1)
        d2_floor_violators = self._teams_below_payroll_floor(leagues, 2)

        d1_must_down = set(d1_standings[-2:] if len(d1_standings) >= 2 else []) | set(d1_floor_violators)
        d1_relegated = [t for t in d1_standings if t in d1_must_down]

        d2_must_down = set(d2_standings[-2:] if len(d2_standings) >= 2 else []) | set(d2_floor_violators)
        d2_relegated = [t for t in d2_standings if t in d2_must_down]

        n_d1_down = len(d1_relegated)
        n_d2_down = len(d2_relegated)

        d2_relegated_set = set(d2_relegated)
        eligible_d2 = [t for t in d2_standings if t not in d2_relegated_set]
        d2_promoted = self._promotion_candidates_from_division(
            playoff_results, eligible_d2, 2, n_d1_down
        )
        d3_promoted = self._promotion_candidates_from_division(
            playoff_results, d3_standings, 3, n_d2_down
        )

        print("\n[League Changes for Next Season]")

        for t in d1_relegated:
            t.league_level = 2
            tag = " [ペイロール下限未達]" if t in d1_floor_violators else ""
            print(f"  v Relegated: {t.name} (D1 -> D2){tag}")
            extra = {"from_division": 1, "to_division": 2}
            if t in d1_floor_violators:
                extra["reason"] = "payroll_floor"
            self._record_competition_team_result(
                competition_id="regular_season",
                team=t,
                result_type="relegated",
                extra=extra,
            )

        for t in d2_promoted:
            t.league_level = 1
            print(f"  ^ Promoted:  {t.name} (D2 -> D1)")
            self._record_competition_team_result(
                competition_id="regular_season",
                team=t,
                result_type="promoted",
                extra={"from_division": 2, "to_division": 1}
            )

        for t in d2_relegated:
            t.league_level = 3
            if t in d2_floor_violators:
                print(f"  v Relegated: {t.name} (D2 -> D3) [ペイロール下限未達]")
            else:
                print(f"  v Relegated: {t.name} (D2 -> D3)")
            extra = {"from_division": 2, "to_division": 3}
            if t in d2_floor_violators:
                extra["reason"] = "payroll_floor"
            self._record_competition_team_result(
                competition_id="regular_season",
                team=t,
                result_type="relegated",
                extra=extra,
            )

        for t in d3_promoted:
            t.league_level = 2
            print(f"  ^ Promoted:  {t.name} (D3 -> D2)")
            self._record_competition_team_result(
                competition_id="regular_season",
                team=t,
                result_type="promoted",
                extra={"from_division": 3, "to_division": 2}
            )

    def _get_players_in_level(self, level: int):
        players = []
        for t in self.leagues[level]:
            players.extend(t.players)
        return players

    def _get_qualified_players_in_level(self, level: int, min_games: int = 15):
        return [p for p in self._get_players_in_level(level) if p.games_played >= min_games]

    def _get_team_name(self, player_id: int) -> str:
        for t in self.all_teams:
            for p in t.players:
                if p.player_id == player_id:
                    return t.name
        return "Unknown"

    def _get_team_wins(self, player_id: int) -> int:
        for t in self.all_teams:
            for p in t.players:
                if p.player_id == player_id:
                    return t.regular_wins
        return 0

    def _get_division_leader(self, level: int, stat_key: str, min_games: int = 15):
        rows = PlayerStatsManager.get_leaderboard(
            teams=self.leagues[level],
            stat_key=stat_key,
            top_n=1,
            min_games=min_games
        )
        return rows[0]["player"] if rows else None

    def _print_stat_leaders_by_division(self):
        for level in [1, 2, 3]:
            qualified_players = self._get_qualified_players_in_level(level, min_games=15)
            if not qualified_players:
                continue

            print("\n==============================")
            print(f"   Division {level} 個人成績ランキング")
            print("==============================")

            PlayerStatsManager.print_leaderboards(
                teams=self.leagues[level],
                top_n=10,
                min_games=15
            )

    def _calculate_and_print_awards_by_division(self):
        target_games = self._regular_season_games_per_team_target()
        mvp_min_games = math.ceil(target_games * 0.8)

        for level in [1, 2, 3]:
            qualified_players = self._get_qualified_players_in_level(level, min_games=15)
            if not qualified_players:
                continue

            bucket = self._create_empty_award_bucket()
            playoff_teams = self._get_playoff_teams_for_level(level)

            bucket["scoring_champ"] = self._get_division_leader(level, "points", min_games=15)
            bucket["rebound_champ"] = self._get_division_leader(level, "rebounds", min_games=15)
            bucket["assist_champ"] = self._get_division_leader(level, "assists", min_games=15)
            bucket["block_champ"] = self._get_division_leader(level, "blocks", min_games=15)
            bucket["steal_champ"] = self._get_division_leader(level, "steals", min_games=15)

            rookies = [p for p in qualified_players if p.years_pro == 0]
            if rookies:
                bucket["roty"] = max(
                    rookies,
                    key=lambda p: (
                        (p.season_points / p.games_played) * 0.45 +
                        (p.season_rebounds / p.games_played) * 0.18 +
                        (p.season_assists / p.games_played) * 0.18 +
                        (p.season_blocks / p.games_played) * 0.08 +
                        (p.season_steals / p.games_played) * 0.06 +
                        p.ovr * 0.05
                    )
                )

            mvp_candidates = []
            for p in qualified_players:
                if p.games_played < mvp_min_games:
                    continue

                belongs_to_playoff_team = False
                player_id = getattr(p, "player_id", None)
                for t in playoff_teams:
                    if player_id in self._team_player_ids(t):
                        belongs_to_playoff_team = True
                        break

                if not belongs_to_playoff_team:
                    continue

                ppg = p.season_points / p.games_played
                rpg = p.season_rebounds / p.games_played
                apg = p.season_assists / p.games_played
                bpg = p.season_blocks / p.games_played
                spg = p.season_steals / p.games_played
                team_wins = self._get_team_wins(p.player_id)

                mvp_score = (
                    ppg * 0.40 +
                    rpg * 0.18 +
                    apg * 0.18 +
                    bpg * 0.08 +
                    spg * 0.06 +
                    (team_wins / max(1, target_games)) * 10 +
                    p.ovr * 0.05
                )
                mvp_candidates.append((mvp_score, p))

            mvp_candidates.sort(key=lambda x: x[0], reverse=True)
            bucket["mvp"] = mvp_candidates[0][1] if mvp_candidates else None

            all_league_players = [p for _, p in mvp_candidates[:15]]
            bucket["all_league_first"] = all_league_players[:5]
            bucket["all_league_second"] = all_league_players[5:10]
            bucket["all_league_third"] = all_league_players[10:15]

            self.awards_by_division[level] = bucket

            print("\n==============================")
            print(f"      Division {level} シーズン表彰")
            print("==============================")

            if bucket["mvp"]:
                print("\nMVP")
                print(f"{bucket['mvp'].name} ({self._get_team_name(bucket['mvp'].player_id)})")

            if bucket["roty"]:
                print("\n新人王")
                print(f"{bucket['roty'].name} ({self._get_team_name(bucket['roty'].player_id)})")

            if bucket["scoring_champ"]:
                p = bucket["scoring_champ"]
                print("\n得点王")
                print(f"{p.name} ({self._get_team_name(p.player_id)}) {p.season_points / p.games_played:.1f} PPG")

            if bucket["rebound_champ"]:
                p = bucket["rebound_champ"]
                print("\nリバウンド王")
                print(f"{p.name} ({self._get_team_name(p.player_id)}) {p.season_rebounds / p.games_played:.1f} RPG")

            if bucket["assist_champ"]:
                p = bucket["assist_champ"]
                print("\nアシスト王")
                print(f"{p.name} ({self._get_team_name(p.player_id)}) {p.season_assists / p.games_played:.1f} APG")

            if bucket["block_champ"]:
                p = bucket["block_champ"]
                print("\nブロック王")
                print(f"{p.name} ({self._get_team_name(p.player_id)}) {p.season_blocks / p.games_played:.1f} BPG")

            if bucket["steal_champ"]:
                p = bucket["steal_champ"]
                print("\nスティール王")
                print(f"{p.name} ({self._get_team_name(p.player_id)}) {p.season_steals / p.games_played:.1f} SPG")

            print("\n【ベスト5】")
            for i, p in enumerate(bucket["all_league_first"], 1):
                print(
                    f"{i}. {p.name} ({self._get_team_name(p.player_id)}) - "
                    f"{p.season_points / p.games_played:.1f} PPG, "
                    f"{p.season_rebounds / p.games_played:.1f} RPG, "
                    f"{p.season_assists / p.games_played:.1f} APG, "
                    f"{p.season_blocks / p.games_played:.1f} BPG, "
                    f"{p.season_steals / p.games_played:.1f} SPG"
                )

            print("\n【ベスト5 セカンドチーム】")
            for i, p in enumerate(bucket["all_league_second"], 1):
                print(
                    f"{i}. {p.name} ({self._get_team_name(p.player_id)}) - "
                    f"{p.season_points / p.games_played:.1f} PPG, "
                    f"{p.season_rebounds / p.games_played:.1f} RPG, "
                    f"{p.season_assists / p.games_played:.1f} APG, "
                    f"{p.season_blocks / p.games_played:.1f} BPG, "
                    f"{p.season_steals / p.games_played:.1f} SPG"
                )

            print("\n【ベスト5 サードチーム】")
            for i, p in enumerate(bucket["all_league_third"], 1):
                print(
                    f"{i}. {p.name} ({self._get_team_name(p.player_id)}) - "
                    f"{p.season_points / p.games_played:.1f} PPG, "
                    f"{p.season_rebounds / p.games_played:.1f} RPG, "
                    f"{p.season_assists / p.games_played:.1f} APG, "
                    f"{p.season_blocks / p.games_played:.1f} BPG, "
                    f"{p.season_steals / p.games_played:.1f} SPG"
                )

        d1 = self.awards_by_division[1]
        self.mvp = d1["mvp"]
        self.roty = d1["roty"]
        self.scoring_champ = d1["scoring_champ"]
        self.rebound_champ = d1["rebound_champ"]
        self.assist_champ = d1["assist_champ"]
        self.block_champ = d1["block_champ"]
        self.steal_champ = d1["steal_champ"]
        self.all_league_first = d1["all_league_first"]
        self.all_league_second = d1["all_league_second"]
        self.all_league_third = d1["all_league_third"]

    def _update_popularity(self):
        mvp_ids = set()
        roty_ids = set()
        title_holder_ids = set()
        first_ids = set()
        second_ids = set()
        third_ids = set()

        for level in [1, 2, 3]:
            bucket = self.awards_by_division[level]

            if bucket["mvp"] is not None:
                mvp_ids.add(self._player_id(bucket["mvp"]))

            if bucket["roty"] is not None:
                roty_ids.add(self._player_id(bucket["roty"]))

            for key in ["scoring_champ", "rebound_champ", "assist_champ", "block_champ", "steal_champ"]:
                if bucket[key] is not None:
                    title_holder_ids.add(self._player_id(bucket[key]))

            first_ids |= self._player_ids(bucket["all_league_first"])
            second_ids |= self._player_ids(bucket["all_league_second"])
            third_ids |= self._player_ids(bucket["all_league_third"])

        all_players = []
        for t in self.all_teams:
            all_players.extend(t.players)

        for p in all_players:
            diff = 0
            pid = self._player_id(p)

            if pid in mvp_ids:
                diff += 6
            if pid in roty_ids:
                diff += 3
            if pid in title_holder_ids:
                diff += 3
            if pid in first_ids:
                diff += 3
            elif pid in second_ids:
                diff += 2
            elif pid in third_ids:
                diff += 1

            if p.games_played < 15:
                diff -= 1
            if p.games_played < 10:
                diff -= 2
            if p.injury_games_left > 10:
                diff -= 2
            if p.age >= 34 and p.ovr < 75:
                diff -= 1

            if p.popularity >= 95:
                diff -= 2
            elif p.popularity >= 90:
                diff -= 1

            if diff <= 0 and p.popularity > 50:
                diff -= 1

            if diff > 0:
                if p.popularity >= 95:
                    diff = int(diff * 0.2)
                elif p.popularity >= 90:
                    diff = int(diff * 0.4)
                elif p.popularity >= 85:
                    diff = int(diff * 0.6)

            p.popularity = max(0, min(100, p.popularity + diff))

        for t in self.all_teams:
            diff = 0
            team_player_ids = self._team_player_ids(t)

            win_diff = t.regular_wins - 15
            if win_diff > 10:
                diff += 3
            elif win_diff > 5:
                diff += 1
            elif win_diff < -10:
                diff -= 3
            elif win_diff < -5:
                diff -= 1

            if team_player_ids & mvp_ids:
                diff += 2

            if team_player_ids & title_holder_ids:
                diff += 1

            if team_player_ids & (first_ids | second_ids | third_ids):
                diff += 1

            if t.popularity >= 90:
                diff -= 2
            elif t.popularity >= 85:
                diff -= 1

            if diff <= 0 and t.popularity > 50:
                diff -= 1

            if diff > 0:
                if t.popularity >= 90:
                    diff = int(diff * 0.3)
                elif t.popularity >= 85:
                    diff = int(diff * 0.5)

            t.popularity = max(0, min(100, t.popularity + diff))

    def _print_popularity_rankings(self):
        print("\n[Most Popular Players]")
        all_players = []
        for t in self.all_teams:
            all_players.extend(t.players)

        top_players = sorted(all_players, key=lambda p: p.popularity, reverse=True)[:10]
        for i, p in enumerate(top_players, 1):
            print(f"{i}. {p.name} ({self._get_team_name(p.player_id)}) - Popularity {p.popularity}")

        print("\n[Most Popular Teams]")
        top_teams = sorted(self.all_teams, key=lambda t: t.popularity, reverse=True)[:10]
        for i, t in enumerate(top_teams, 1):
            print(f"{i}. {t.name} - Popularity {t.popularity}")

    def _process_finances(self):
        finances_log = []

        for t in self.all_teams:
            if t.league_level == 1:
                base_attendance = 7000
                ticket_price = 55
                base_front_cost = 2500000
                arena_cost = 1000000
                league_sponsor_base = 6000000
            elif t.league_level == 2:
                base_attendance = 5000
                ticket_price = 50
                base_front_cost = 1000000
                arena_cost = 500000
                league_sponsor_base = 5400000
            else:
                base_attendance = 3500
                ticket_price = 45
                base_front_cost = 400000
                arena_cost = 200000
                league_sponsor_base = 5000000

            pop_bonus = (t.popularity - 50) * 30
            win_bonus = (t.regular_wins - 15) * 40

            star_bonus = 0
            star_sponsor_bonus = 0
            for p in t.players:
                pop = getattr(p, "popularity", 50)
                if pop >= 85:
                    star_bonus += 800
                    star_sponsor_bonus += 800000
                elif pop >= 70:
                    star_bonus += 300
                    star_sponsor_bonus += 300000

            attendance = base_attendance + pop_bonus + win_bonus + star_bonus
            attendance = int(attendance * getattr(t, "market_size", 1.0))

            if t.league_level == 1:
                attendance = max(4000, min(14000, attendance))
            elif t.league_level == 2:
                attendance = max(3500, min(8000, attendance))
            else:
                attendance = max(2500, min(6500, attendance))

            home_games = 15

            ticket_revenue = attendance * ticket_price * home_games

            sponsor_win_bonus = (t.regular_wins - 15) * 30000
            sponsor_pop_bonus = (t.popularity - 50) * 20000
            sponsor_revenue = league_sponsor_base + sponsor_win_bonus + sponsor_pop_bonus + star_sponsor_bonus

            m_size = getattr(t, "market_size", 1.0)
            sponsor_revenue = int(sponsor_revenue * ((m_size + 1.0) / 2))
            sponsor_revenue = max(1000000, sponsor_revenue)

            revenue = ticket_revenue + sponsor_revenue

            roster_salary = sum(getattr(p, "salary", 0) for p in t.players)

            popularity_cost = t.popularity * 5000
            operating_cost = base_front_cost + arena_cost + popularity_cost

            expenses = roster_salary + operating_cost
            profit = int(revenue - expenses)

            t.money += profit

            if t.money < -5000000:
                t.money = -5000000

            finances_log.append({
                "team": t,
                "ticket_rev": ticket_revenue,
                "sponsor_rev": sponsor_revenue,
                "revenue": revenue,
                "expenses": expenses,
                "profit": profit,
                "attendance": attendance
            })

        print("\n[Richest Clubs]")
        top_teams_finances = sorted(finances_log, key=lambda x: x["team"].money, reverse=True)[:5]

        for i, data in enumerate(top_teams_finances, 1):
            t = data["team"]
            avg_att = int(data["attendance"])
            print(f"{i}. {t.name:<25} - {t.money:12,}円 | (Att: {avg_att:5d})")
            print(f"      Ticket: {data['ticket_rev']:,}円 | Sponsor: {data['sponsor_rev']:,}円")
            print(f"      Exp:    {data['expenses']:,}円 | Profit:  {data['profit']:,}円")

        print("\n[Poorest Clubs]")
        bottom_teams_finances = sorted(finances_log, key=lambda x: x["team"].money)[:5]

        for i, data in enumerate(bottom_teams_finances, 1):
            t = data["team"]
            avg_att = int(data["attendance"])
            print(f"{i}. {t.name:<25} - {t.money:12,}円 | (Att: {avg_att:5d})")
            print(f"      Ticket: {data['ticket_rev']:,}円 | Sponsor: {data['sponsor_rev']:,}円")
            print(f"      Exp:    {data['expenses']:,}円 | Profit:  {data['profit']:,}円")

    def _print_scoring_distribution_summary(self):
        if not self.game_results:
            return

        team_scores = []
        diff_20 = 0
        diff_30 = 0
        diff_40 = 0

        for row in self.game_results:
            home_score = int(row.get("home_score", 0))
            away_score = int(row.get("away_score", 0))
            score_diff = int(row.get("score_diff", 0))

            team_scores.append(home_score)
            team_scores.append(away_score)

            if score_diff >= 20:
                diff_20 += 1
            if score_diff >= 30:
                diff_30 += 1
            if score_diff >= 40:
                diff_40 += 1

        score_100_plus = sum(1 for s in team_scores if s >= 100)
        score_90s = sum(1 for s in team_scores if 90 <= s <= 99)
        score_80s = sum(1 for s in team_scores if 80 <= s <= 89)
        score_70s = sum(1 for s in team_scores if 70 <= s <= 79)
        score_60s = sum(1 for s in team_scores if 60 <= s <= 69)
        score_under_60 = sum(1 for s in team_scores if s < 60)

        print("\n==============================")
        print("   SCORING DISTRIBUTION")
        print("==============================")
        print(f"100+ points: {score_100_plus}")
        print(f"90s points : {score_90s}")
        print(f"80s points : {score_80s}")
        print(f"70s points : {score_70s}")
        print(f"60s points : {score_60s}")
        print(f"Under 60   : {score_under_60}")
        print()
        print(f"20+ pt games: {diff_20}")
        print(f"30+ pt games: {diff_30}")
        print(f"40+ pt games: {diff_40}")

    def _print_position_stat_profile(self):
        position_rows = {
            "PG": {"players": 0, "games": 0, "pts": 0, "ast": 0, "reb": 0, "blk": 0, "stl": 0},
            "SG": {"players": 0, "games": 0, "pts": 0, "ast": 0, "reb": 0, "blk": 0, "stl": 0},
            "SF": {"players": 0, "games": 0, "pts": 0, "ast": 0, "reb": 0, "blk": 0, "stl": 0},
            "PF": {"players": 0, "games": 0, "pts": 0, "ast": 0, "reb": 0, "blk": 0, "stl": 0},
            "C": {"players": 0, "games": 0, "pts": 0, "ast": 0, "reb": 0, "blk": 0, "stl": 0},
        }

        for team in self.all_teams:
            for player in getattr(team, "players", []):
                pos = getattr(player, "position", None)
                if pos not in position_rows:
                    continue

                gp = int(getattr(player, "games_played", 0))
                if gp <= 0:
                    continue

                row = position_rows[pos]
                row["players"] += 1
                row["games"] += gp
                row["pts"] += int(getattr(player, "season_points", 0))
                row["ast"] += int(getattr(player, "season_assists", 0))
                row["reb"] += int(getattr(player, "season_rebounds", 0))
                row["blk"] += int(getattr(player, "season_blocks", 0))
                row["stl"] += int(getattr(player, "season_steals", 0))

        print("\n==============================")
        print("   POSITION STAT PROFILE")
        print("==============================")

        for pos in ["PG", "SG", "SF", "PF", "C"]:
            row = position_rows[pos]
            player_count = row["players"]
            games = row["games"]

            if games <= 0:
                print(f"\n[{pos}] No data")
                continue

            print(f"\n[{pos}] Players:{player_count} TotalGP:{games}")
            print(f"  PTS {row['pts'] / games:.1f}")
            print(f"  AST {row['ast'] / games:.1f}")
            print(f"  REB {row['reb'] / games:.1f}")
            print(f"  BLK {row['blk'] / games:.1f}")
            print(f"  STL {row['stl'] / games:.1f}")

    def _apply_career_stats(self):
        if self._career_stats_applied:
            return

        for team in self.all_teams:
            for player in getattr(team, "players", []):
                if hasattr(player, "apply_season_to_career_stats"):
                    player.apply_season_to_career_stats()

        self._career_stats_applied = True
