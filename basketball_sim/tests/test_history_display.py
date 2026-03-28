"""history_display 純関数。"""

from basketball_sim.systems.history_display import (
    build_episode_lines,
    build_journey_lines,
    dedupe_timeline_rows,
    fetch_timeline_rows,
    milestone_row_kind,
    season_label_key,
    split_milestone_rows,
    timeline_selection_detail_lines,
)


def test_season_label_key():
    assert season_label_key("Season 3") == "S3"
    assert season_label_key(5) == "S5"
    assert season_label_key("Season 12") == "S12"


def test_dedupe_timeline_prefers_rank():
    rows = [
        {"season": "Season 1", "rank": "-", "wins": 10},
        {"season": "Season 1", "rank": 3, "wins": 10},
    ]
    out = dedupe_timeline_rows(rows)
    assert len(out) == 1
    assert out[0]["rank"] == 3


def test_milestone_split():
    intl = {"title": "ACL", "detail": "優勝", "category": ""}
    boss = {"title": "FINAL BOSS", "detail": "挑戦", "category": ""}
    dom = {"title": "天皇杯", "detail": "", "category": ""}
    a, b, c = split_milestone_rows([intl, boss, dom])
    assert len(a) == 1 and len(b) == 1 and len(c) == 1


def test_milestone_row_kind_acl():
    assert milestone_row_kind({"title": "x", "detail": "ACL 出場", "category": ""}) == "international"


def test_timeline_selection_lines():
    miles = [{"season": "Season 2", "title": "優勝", "detail": "リーグ"}]
    awards = [{"season": "Season 2", "award": "MVP", "player": "A"}]
    raw = [{"season_index": 2, "top_players": [{"player_name": "A", "ovr": 80, "season_points": 20}]}]
    lines = timeline_selection_detail_lines(
        season_display="Season 2",
        milestone_rows=miles,
        award_rows=awards,
        raw_history_seasons=raw,
    )
    text = "\n".join(lines)
    assert "優勝" in text
    assert "MVP" in text
    assert "A" in text


def test_fetch_timeline_rows_none_team():
    assert fetch_timeline_rows(None) == []


def test_build_journey_none_team():
    assert "未接続" in "\n".join(build_journey_lines(None))


class _TeamEp:
    def get_club_history_milestone_rows(self, limit=80):
        return [
            {"title": "天皇杯 優勝", "detail": "", "category": "", "season": "Season 1"},
        ]

    def get_club_history_summary(self):
        return {"season_count": 3}

    def _build_milestone_headlines(self, rows, limit=5):
        return [r["title"] for r in rows]

    def _build_recent_big_milestone_lines(self, rows, limit=5):
        return ["big: test"]


def test_build_episode_minimal():
    lines = build_episode_lines(_TeamEp())
    assert any("国内" in x for x in lines)
