"""日程ビュー純関数（読み取り専用）。"""

from basketball_sim.systems.schedule_display import (
    detail_text_for_upcoming_row,
    format_season_event_matchup_line,
    information_panel_schedule_lines,
    is_schedule_row_display_supplement,
    next_advance_display_hints,
    next_round_schedule_lines,
    past_league_result_rows,
    upcoming_rows_for_user_team,
    user_still_active_in_emperor_cup_field,
    user_team_participates_in_easl_stage,
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


class _SeasonEmperorPlaceholder:
    """リーグ SeasonEvent に杯が無いが、杯週フラグだけ立つケース（GUI 一覧補完）。"""

    def __init__(self) -> None:
        self.current_round = 12
        self.total_rounds = 14
        self.season_finished = False
        u = _T(1, "User")
        v = _T(2, "Other")
        self.emperor_cup_bye_teams = [u]
        self.emperor_cup_round1_teams = [v]
        self.emperor_cup_current_teams = []
        self.emperor_cup_played_stages = set()

    def get_events_for_round(self, r: int):
        if r == 13:
            return []
        if r == 14:
            return [_Ev(14, _T(1, "User"), _T(9, "Z"))]
        return []

    def _should_play_emperor_cup_this_round(self, r: int) -> bool:
        return r == 13

    def _get_round_config(self, r: int):
        return {"month": 1}


def test_user_active_emperor_before_play():
    s = _SeasonEmperorPlaceholder()
    assert user_still_active_in_emperor_cup_field(s, _T(1, "User")) is True
    assert user_still_active_in_emperor_cup_field(s, _T(99, "X")) is False


def test_upcoming_adds_emperor_placeholder_when_no_season_event():
    s = _SeasonEmperorPlaceholder()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=False)
    cup = [x for x in rows if x["competition_type"] == "emperor_cup"]
    assert len(cup) == 1
    assert cup[0]["round"] == 13
    assert "全日本" in cup[0]["competition_display"]


def test_upcoming_league_filter_excludes_cup_row():
    s = _Season()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=True)
    assert len(rows) == 1
    assert rows[0]["round"] == 2


class _SeasonEaslPlaceholder:
    """リーグ SeasonEvent に EASL が無いが、当ラウンドに EASL ステージがあるケース。"""

    def __init__(self) -> None:
        self.current_round = 0
        self.total_rounds = 3
        self.season_finished = False
        self.easl_enabled = True
        u = _T(1, "User")
        v = _T(2, "Other")
        self.easl_groups = {"A": [u, v, _T(3, "C"), _T(4, "D")]}
        self.easl_knockout_teams = []
        self.easl_current_finalists = []
        self.easl_matchdays = {"group_md1": [(u, v)]}

    def get_events_for_round(self, r: int):
        return []

    def _get_round_config(self, r: int):
        return {"month": 10 + r}

    def _get_round_easl_stage(self, r: int):
        return "group_md1" if r == 1 else None


def test_user_participates_easl_group_stage():
    s = _SeasonEaslPlaceholder()
    u = _T(1, "User")
    assert user_team_participates_in_easl_stage(s, u, "group_md1") is True
    assert user_team_participates_in_easl_stage(s, _T(99, "X"), "group_md1") is False


def test_upcoming_adds_easl_placeholder_when_no_season_event():
    s = _SeasonEaslPlaceholder()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=False)
    easl_rows = [x for x in rows if x["competition_type"] == "easl"]
    assert len(easl_rows) == 1
    assert easl_rows[0]["round"] == 1
    assert "東アジア" in easl_rows[0]["competition_display"]


class _SeasonNationalWindowPlaceholder:
    """代表ウィンドウ週で SeasonEvent が空のケース（日程「すべて」補完）。"""

    def __init__(self) -> None:
        self.current_round = 5
        self.total_rounds = 10
        self.season_finished = False
        self.season_no = 1
        self.national_team_cycle = {
            1: {"window_1": "asia_qualifier", "window_2": "asia_qualifier", "summer": "asia_cup"},
        }

    def get_events_for_round(self, r: int):
        return []

    def _get_round_config(self, r: int):
        configs = {
            7: {"month": 11, "national_team_window": "window_1"},
            8: {"month": 11, "national_team_window": None},
        }
        return configs.get(r, {"month": 10, "national_team_window": None})

    def _get_round_national_window(self, r: int):
        return self._get_round_config(r).get("national_team_window")

    def _resolve_national_team_window_type(self, window_key):
        cy = ((int(getattr(self, "season_no", 1)) - 1) % 4) + 1
        row = self.national_team_cycle.get(cy, {})
        return row.get(window_key)

    def _get_national_team_window_label(self, window_type):
        return "アジアカップ予選" if window_type == "asia_qualifier" else "代表ウィーク"


def test_upcoming_adds_national_window_placeholder():
    s = _SeasonNationalWindowPlaceholder()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=False)
    nat = [x for x in rows if x["competition_type"] == "national_team_window"]
    assert len(nat) == 1
    assert nat[0]["round"] == 7
    assert "アジア" in nat[0]["competition_display"]
    assert is_schedule_row_display_supplement(nat[0])


def test_upcoming_league_filter_excludes_national_placeholder():
    s = _SeasonNationalWindowPlaceholder()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=True)
    assert not any(x["competition_type"] == "national_team_window" for x in rows)


class _SeasonAllStarPlaceholder:
    """オールスター週で SeasonEvent が空のケース（日程「すべて」補完）。"""

    def __init__(self) -> None:
        self.current_round = 14
        self.total_rounds = 16
        self.season_finished = False

    def get_events_for_round(self, r: int):
        return []

    def _get_round_config(self, r: int):
        if int(r) == 15:
            return {
                "month": 1,
                "league_games_per_team": 0,
                "is_break_week": True,
                "notes": "1月第3週・オールスター週（リーグ休み）",
            }
        return {"month": 1, "league_games_per_team": 2, "is_break_week": False, "notes": ""}


def test_upcoming_adds_all_star_placeholder():
    s = _SeasonAllStarPlaceholder()
    u = _T(1, "User")
    rows = upcoming_rows_for_user_team(s, u, league_only=False)
    as_rows = [x for x in rows if x["competition_type"] == "all_star_break"]
    assert len(as_rows) == 1
    assert as_rows[0]["round"] == 15
    assert as_rows[0]["competition_display"] == "オールスター"
    assert is_schedule_row_display_supplement(as_rows[0])


def test_detail_text_marks_display_supplement():
    row = {
        "round": 7,
        "rounds_until": 1,
        "month_label": "11月頃",
        "competition_display": "アジアカップ予選",
        "ha_long": "（代表ウィンドウ）",
        "ha_short": "—",
        "opponent": "（日本リーグの対戦カードはありません）",
        "event_id": "national_window_r7",
        "label": "window_1",
    }
    t = detail_text_for_upcoming_row(row)
    assert "表示補完" in t


def test_next_round_lines_include_national_window_hint():
    s = _SeasonNationalWindowPlaceholder()
    s.current_round = 6
    u = _T(1, "User")
    lines = next_round_schedule_lines(s, u)
    assert any("アジア" in ln and "表示補完" in ln for ln in lines)


def test_next_round_lines_include_easl_hint():
    s = _SeasonEaslPlaceholder()
    u = _T(1, "User")
    lines = next_round_schedule_lines(s, u)
    assert any("東アジア" in ln for ln in lines)


def test_next_round_lines():
    s = _Season()
    u = _T(1, "User")
    lines = next_round_schedule_lines(s, u)
    assert any("ラウンド 2" in ln and "全 2" in ln for ln in lines)
    assert any("2 試合" in ln for ln in lines)
    assert any("Other" in ln for ln in lines)


def test_next_advance_display_hints_multi_game_round():
    s = _Season()
    u = _T(1, "User")
    block, one = next_advance_display_hints(s, u)
    assert "2 試合" in block
    assert "まとめてシミュ" in block
    assert "進行予告" in one


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
    assert "次の進行で消化するラウンド: 2 / 2" in lines[0]
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
