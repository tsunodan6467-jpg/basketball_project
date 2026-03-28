"""information_display 純関数。"""

from basketball_sim.systems.information_display import (
    build_information_news_lines,
    build_player_leaderboard_rows,
    build_standings_rows,
    build_team_summary_rows,
    format_awards_lines_for_division,
    player_stat_options,
)


class _Team:
    def __init__(self, tid: int, name: str, w: int, l: int, pf: int, pa: int, **kw: object) -> None:
        self.team_id = tid
        self.name = name
        self.regular_wins = w
        self.regular_losses = l
        self.regular_points_for = pf
        self.regular_points_against = pa
        self.is_user_team = bool(kw.get("is_user_team", False))


class _Player:
    def __init__(self, pid: int, name: str, **kw: object) -> None:
        self.player_id = pid
        self.name = name
        self.season_points = int(kw.get("season_points", 0))
        self.games_played = int(kw.get("games_played", 0))
        self.season_rebounds = 0
        self.season_assists = 0
        self.season_blocks = 0
        self.season_steals = 0
        self.position = str(kw.get("position", "PG"))
        self.ovr = int(kw.get("ovr", 60))
        self.is_retired = False


class _Season:
    def __init__(self) -> None:
        t1 = _Team(1, "A", 3, 0, 300, 270)
        t2 = _Team(2, "B", 2, 1, 280, 275)
        t3 = _Team(3, "UserTeam", 0, 3, 200, 310, is_user_team=True)
        self.leagues = {1: [t2, t1, t3]}
        self.awards_by_division = {
            1: {
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
        }
        self.season_finished = False

    def get_standings(self, teams):
        return sorted(
            teams,
            key=lambda t: (t.regular_wins, t.regular_points_for - t.regular_points_against),
            reverse=True,
        )

    def _get_team_name(self, player_id):
        return "A" if player_id == 10 else "B"


def test_standings_order_and_user_flag():
    s = _Season()
    rows = build_standings_rows(s, 1, user_team=None)
    assert rows[0]["name"] == "A"
    assert rows[0]["rank"] == 1
    urows = build_standings_rows(s, 1, user_team=_Team(99, "UserTeam", 0, 0, 0, 0))
    user_rows = [r for r in urows if r["is_user_row"]]
    assert len(user_rows) == 1
    assert user_rows[0]["name"] == "UserTeam"


def test_team_summary_averages():
    s = _Season()
    rows = build_team_summary_rows(s, 1)
    a = next(x for x in rows if x["name"] == "A")
    assert a["wins"] == 3 and a["losses"] == 0
    assert abs(a["avg_pf"] - 300 / 3) < 0.001


def test_player_leaderboard():
    p1 = _Player(10, "Star", season_points=90, games_played=3, ovr=70)
    p2 = _Player(11, "Bench", season_points=10, games_played=1, ovr=50)
    t = _Team(1, "A", 1, 0, 100, 90)
    t.players = [p1, p2]
    s = _Season()
    s.leagues[1] = [t]
    rows = build_player_leaderboard_rows(s, 1, "points", top_n=5, min_games=1)
    assert rows[0]["name"] == "Star"


def test_news_external_override():
    lines = build_information_news_lines(
        team_name="X",
        rank_text="1位",
        wins=1,
        losses=0,
        external_items=["only"],
    )
    assert lines == ["only"]


def test_news_default():
    lines = build_information_news_lines(team_name="T", rank_text="-", wins=0, losses=0, external_items=None)
    assert "T" in lines[0]


def test_player_stat_options_non_empty():
    assert len(player_stat_options()) >= 5


def test_awards_empty_midseason():
    s = _Season()
    lines = format_awards_lines_for_division(s, 1)
    assert any("まだ確定" in x or "確定していません" in x for x in lines)


def test_awards_with_mvp():
    s = _Season()
    s.season_finished = True
    s.awards_by_division[1]["mvp"] = _Player(10, "MVP男", season_points=100, games_played=10)
    lines = format_awards_lines_for_division(s, 1)
    text = "\n".join(lines)
    assert "MVP" in text
    assert "MVP男" in text
