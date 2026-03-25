from typing import List, Dict, Any
from basketball_sim.models.player import Player


class PlayerStatsManager:
    """
    個人成績ランキング管理。
    平均スタッツベースのランキングを扱う。

    現在対応:
    - 得点王（PPG）
    - リバウンド王（RPG）
    - アシスト王（APG）
    - ブロック王（BPG）
    - スティール王（SPG）

    表示強化:
    - ポジション表示
    - OVR表示
    - 合計スタッツ表示
    - 1試合平均 + 総数 を同時表示
    """

    STAT_DEFINITIONS = {
        "points": {
            "label": "得点王",
            "season_attr": "season_points",
            "per_game_label": "PPG",
            "total_label": "PTS",
        },
        "rebounds": {
            "label": "リバウンド王",
            "season_attr": "season_rebounds",
            "per_game_label": "RPG",
            "total_label": "REB",
        },
        "assists": {
            "label": "アシスト王",
            "season_attr": "season_assists",
            "per_game_label": "APG",
            "total_label": "AST",
        },
        "blocks": {
            "label": "ブロック王",
            "season_attr": "season_blocks",
            "per_game_label": "BPG",
            "total_label": "BLK",
        },
        "steals": {
            "label": "スティール王",
            "season_attr": "season_steals",
            "per_game_label": "SPG",
            "total_label": "STL",
        },
    }

    @classmethod
    def get_all_players(cls, teams: List[Any]) -> List[Player]:
        players: List[Player] = []
        for team in teams:
            for player in getattr(team, "players", []):
                players.append(player)
        return players

    @classmethod
    def _safe_games_played(cls, player: Player) -> int:
        games_played = getattr(player, "games_played", 0)
        return games_played if games_played > 0 else 0

    @classmethod
    def _get_team_name(cls, teams: List[Any], player: Player) -> str:
        player_id = getattr(player, "player_id", None)

        for team in teams:
            for team_player in getattr(team, "players", []):
                if getattr(team_player, "player_id", None) == player_id:
                    return getattr(team, "name", "Unknown")

        return "Unknown"

    @classmethod
    def _get_per_game_value(cls, player: Player, season_attr: str) -> float:
        total_value = getattr(player, season_attr, 0)
        games_played = cls._safe_games_played(player)

        if games_played == 0:
            return 0.0

        return total_value / games_played

    @classmethod
    def _build_stat_row(cls, teams: List[Any], player: Player, stat_key: str) -> Dict[str, Any]:
        stat_def = cls.STAT_DEFINITIONS[stat_key]
        season_attr = stat_def["season_attr"]
        per_game_value = cls._get_per_game_value(player, season_attr)
        total_value = getattr(player, season_attr, 0)

        return {
            "player": player,
            "name": getattr(player, "name", "Unknown"),
            "team_name": cls._get_team_name(teams, player),
            "position": getattr(player, "position", "NA"),
            "ovr": getattr(player, "ovr", 0),
            "games_played": getattr(player, "games_played", 0),
            "total": total_value,
            "per_game": per_game_value,
            "display_value": f"{per_game_value:.1f}",
        }

    @classmethod
    def get_leaderboard(
        cls,
        teams: List[Any],
        stat_key: str,
        top_n: int = 10,
        min_games: int = 1
    ) -> List[Dict[str, Any]]:
        if stat_key not in cls.STAT_DEFINITIONS:
            raise ValueError(f"Unknown stat_key: {stat_key}")

        players = cls.get_all_players(teams)

        rows: List[Dict[str, Any]] = []
        for player in players:
            if getattr(player, "is_retired", False):
                continue

            games_played = getattr(player, "games_played", 0)
            if games_played < min_games:
                continue

            rows.append(cls._build_stat_row(teams, player, stat_key))

        rows.sort(
            key=lambda row: (
                row["per_game"],
                row["total"],
                getattr(row["player"], "get_effective_ovr", lambda: 0)()
            ),
            reverse=True
        )

        return rows[:top_n]

    @classmethod
    def get_all_leaderboards(
        cls,
        teams: List[Any],
        top_n: int = 10,
        min_games: int = 1
    ) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}

        for stat_key in cls.STAT_DEFINITIONS.keys():
            result[stat_key] = cls.get_leaderboard(
                teams=teams,
                stat_key=stat_key,
                top_n=top_n,
                min_games=min_games
            )

        return result

    @classmethod
    def print_leaderboards(
        cls,
        teams: List[Any],
        top_n: int = 10,
        min_games: int = 1
    ) -> None:
        leaderboards = cls.get_all_leaderboards(
            teams=teams,
            top_n=top_n,
            min_games=min_games
        )

        print("")
        print("==============================")
        print("      個人成績ランキング")
        print("==============================")

        for stat_key, rows in leaderboards.items():
            stat_def = cls.STAT_DEFINITIONS[stat_key]
            label = stat_def["label"]
            per_game_label = stat_def["per_game_label"]
            total_label = stat_def["total_label"]

            print("")
            print(f"【{label}】")

            if not rows:
                print("該当選手なし")
                continue

            for idx, row in enumerate(rows, start=1):
                print(
                    f"{idx:>2}. "
                    f"{row['name']:<18} "
                    f"({row['team_name']}) "
                    f"{row['position']} "
                    f"OVR:{row['ovr']:<2} "
                    f"{row['display_value']} {per_game_label} "
                    f"/ {row['total']} {total_label} "
                    f"[{row['games_played']}試合]"
                )