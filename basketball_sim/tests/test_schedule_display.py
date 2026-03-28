"""日程ビュー純関数（読み取り専用）。"""

from basketball_sim.systems.schedule_display import (
    detail_text_for_upcoming_row,
    format_season_event_matchup_line,
    information_panel_schedule_lines,
    next_round_schedule_lines,
    past_league_result_rows,
    upcoming_rows_for_user_team,
)


class _T:
    def __init__(self, tid: int, name: str) -> None:
        self.team_id = tid
        self.name = name


class _Ev:
    def __init__(self, rnd: int, home: _T, away: _T, ct: str = "regular_season") -> None:
        self.event_id = f"r{rnd}_{home.name}_{away.name}"
        self.event_type = "game"
        self.round_number = rnd
        self.home_team = home
        self.away_team = away
        self.competition_type = ct
        self.label = "lbl"


class _Season:
    def __init__(self) -> None:
        self.current_round = 1
        self.total_rounds = 2
        self.season_finished = False
        u = _T(1, "User")
        v = _T(2, "Other")
        w = _T(3, "Third")
        self._events = {
            2: [_Ev(2, u, v), _Ev(2, u, w, ct="emperor_cup")],
        }

    def get_events_for_round(self, r: int):
        return list(self._events.get(r, []))

    def _get_round_config(self, r: int):
        return {"month": 10 + r}


def test_upcoming_includes_future_user_games():
    s = _Season()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=False)
    assert len(rows) == 2
    league_rows = [x for x in rows if x["competition_type"] == "regular_season"]
    assert len(league_rows) == 1
    r2 = league_rows[0]
    assert r2["opponent"] == "Other"
    assert r2["ha_short"] == "H"
    assert r2["competition_display"] == "日本リーグ"


def test_upcoming_league_filter_excludes_cup_row():
    s = _Season()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=True)
    assert len(rows) == 1
    assert rows[0]["round"] == 2


def test_next_round_lines():
    s = _Season()
    u = _T(1, "User")
    lines = next_round_schedule_lines(s, u)
    assert any("2 / 2" in ln for ln in lines)
    assert any("Other" in ln for ln in lines)


def test_past_results_from_game_results():
    class _S2:
        season_finished = False
        game_results = [
            {"home_team": "User", "away_team": "X", "home_score": 80, "away_score": 70},
            {"home_team": "Y", "away_team": "User", "home_score": 60, "away_score": 75},
        ]

    u = _T(1, "User")
    rows = past_league_result_rows(_S2(), u)
    assert len(rows) == 2
    assert rows[0]["display_order"] == 1
    assert rows[0]["opponent"] == "Y"
    assert rows[0]["result"] == "勝利"
    assert rows[1]["display_order"] == 2
    assert rows[1]["opponent"] == "X"


def test_information_panel_lines():
    s = _Season()
    lines = information_panel_schedule_lines(s, max_events=10)
    assert "次ラウンド: 2 / 2" in lines[0]
    assert any("日本リーグ" in x for x in lines)


def test_format_event_line():
    u, v = _T(1, "A"), _T(2, "B")
    ev = _Ev(1, u, v)
    assert "日本リーグ" in format_season_event_matchup_line(ev)
    assert "A vs B" in format_season_event_matchup_line(ev)


def test_detail_text_for_upcoming():
    row = {
        "round": 5,
        "rounds_until": 2,
        "month_label": "12月頃",
        "competition_display": "日本リーグ",
        "ha_long": "ホーム",
        "ha_short": "H",
        "opponent": "Cats",
        "label": "x",
    }
    t = detail_text_for_upcoming_row(row)
    assert "ラウンド: 5" in t
    assert "Cats" in t
