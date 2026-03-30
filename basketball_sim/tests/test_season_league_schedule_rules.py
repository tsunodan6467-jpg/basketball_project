"""リーグ日程生成: 土日同一相手・水曜別相手・水曜1試合（正本）。"""

from __future__ import annotations

from basketball_sim.models.season import Season
from basketball_sim.models.team import Team


def _fake_teams(n: int) -> list[Team]:
    out: list[Team] = []
    for i in range(n):
        t = Team.__new__(Team)
        t.team_id = i + 1
        t.name = f"T{i + 1}"
        out.append(t)
    return out


def _opp_set(team: Team, games: list[tuple]) -> set[int]:
    tid = int(team.team_id)
    others: set[int] = set()
    for h, a in games:
        if h is team:
            others.add(int(a.team_id))
        elif a is team:
            others.add(int(h.team_id))
    return others


def _ha_roles_for_team(team: Team, games: list[tuple]) -> list[str]:
    roles: list[str] = []
    for h, a in games:
        if h is team:
            roles.append("H")
        elif a is team:
            roles.append("A")
    return roles


def _undirected_pair_ids(games: list[tuple]) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for h, a in games:
        if h is None or a is None:
            continue
        x, y = sorted((int(h.team_id), int(a.team_id)))
        out.add((x, y))
    return out


def test_two_game_week_each_team_faces_one_opponent_twice() -> None:
    teams = _fake_teams(8)
    s = Season.__new__(Season)
    cycle = Season._build_double_round_robin_rounds(s, teams)
    chunk, adv = Season.collect_league_week_matchups(cycle, 0, 2, False)
    assert adv == 1
    # 8 チーム・4 対戦 × 土日の 2 試合 = 8 試合
    assert len(chunk) == 8
    for t in teams:
        opps = _opp_set(t, chunk)
        assert len(opps) == 1
        ha = _ha_roles_for_team(t, chunk)
        assert ha == ["H", "H"] or ha == ["A", "A"]


def test_three_game_week_weekend_same_opponent_midweek_different() -> None:
    teams = _fake_teams(8)
    s = Season.__new__(Season)
    cycle = Season._build_double_round_robin_rounds(s, teams)
    chunk, adv = Season.collect_league_week_matchups(cycle, 0, 3, True)
    assert adv >= 2
    n_by_team: dict[int, set[int]] = {int(t.team_id): set() for t in teams}
    for h, a in chunk:
        n_by_team[int(h.team_id)].add(int(a.team_id))
        n_by_team[int(a.team_id)].add(int(h.team_id))
    for t in teams:
        opps = n_by_team[int(t.team_id)]
        assert len(opps) == 2
        counts: dict[int, int] = {}
        for h, a in chunk:
            if h is t:
                counts[int(a.team_id)] = counts.get(int(a.team_id), 0) + 1
            elif a is t:
                counts[int(h.team_id)] = counts.get(int(h.team_id), 0) + 1
        assert sorted(counts.values()) == [1, 2]


def test_three_game_week_weekend_ha_unified_before_midweek() -> None:
    teams = _fake_teams(8)
    s = Season.__new__(Season)
    cycle = Season._build_double_round_robin_rounds(s, teams)
    chunk, _ = Season.collect_league_week_matchups(cycle, 0, 3, True)
    # 週末 8 試合 → 水曜 4 試合
    weekend, mid = chunk[:8], chunk[8:]
    assert len(weekend) == 8 and len(mid) == 4
    for t in teams:
        assert _ha_roles_for_team(t, weekend) == ["H", "H"] or _ha_roles_for_team(t, weekend) == ["A", "A"]
        assert len(_ha_roles_for_team(t, mid)) == 1


def test_three_game_week_total_match_count() -> None:
    teams = _fake_teams(8)
    s = Season.__new__(Season)
    cycle = Season._build_double_round_robin_rounds(s, teams)
    chunk, _ = Season.collect_league_week_matchups(cycle, 0, 3, True)
    assert len(chunk) == 12  # 週末 8 + 水曜 4


def test_double_rr_interleaves_home_and_away_legs_per_round() -> None:
    """各 RR ラウンドの第1戦とリターン戦がサイクル上で隣接し、対戦カード集合が一致する。"""
    teams = _fake_teams(8)
    s = Season.__new__(Season)
    cycle = Season._build_double_round_robin_rounds(s, teams)
    assert len(cycle) == 14  # 7 ラウンド ×（第1戦 + リターン）
    for k in range(7):
        a = _undirected_pair_ids(cycle[2 * k])
        b = _undirected_pair_ids(cycle[2 * k + 1])
        assert a == b
        assert len(a) == 4
