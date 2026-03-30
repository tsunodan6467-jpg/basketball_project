"""ホーム「今やること」表示の文言・内訳ヘルパ（Tk 起動なし）。"""

from types import MethodType, SimpleNamespace

from basketball_sim.systems.main_menu_view import MainMenuView


def test_is_home_tasks_empty_line_accepts_legacy_and_current() -> None:
    assert MainMenuView._is_home_tasks_empty_line(
        "（要確認の項目はありません。各メニューで随時確認してください）"
    )
    assert MainMenuView._is_home_tasks_empty_line(MainMenuView.HOME_TASKS_EMPTY_LINE)
    assert not MainMenuView._is_home_tasks_empty_line("[優先] テスト")


def test_format_task_line_for_display() -> None:
    assert MainMenuView._format_task_line_for_display("[優先] 施設ポイント") == "【急ぎ】施設ポイント"
    assert MainMenuView._format_task_line_for_display("[任意] FA候補") == "【あとで】FA候補"
    assert MainMenuView._format_task_line_for_display("そのまま") == "そのまま"


def test_task_status_short_mixed_and_empty() -> None:
    view = MainMenuView.__new__(MainMenuView)
    view.external_tasks = None
    view.team = None
    view._get_task_lines = MethodType(MainMenuView._get_task_lines, view)
    assert MainMenuView._task_status_short(view) == "なし"

    view2 = MainMenuView.__new__(MainMenuView)
    view2.external_tasks = ["[優先] a", "[任意] b"]
    view2._get_task_lines = MethodType(MainMenuView._get_task_lines, view2)
    s = MainMenuView._task_status_short(view2)
    assert "急ぎ1" in s and "あとで1" in s and "計2" in s


def test_home_task_urgent_normal_counts() -> None:
    view = MainMenuView.__new__(MainMenuView)
    lines = [MainMenuView.HOME_TASKS_EMPTY_LINE]
    assert view._home_task_urgent_normal_counts(lines) is None
    assert view._home_task_urgent_normal_counts(["[優先] x", "[任意] y"]) == (1, 1)


def test_format_injured_players_priority_line_names_and_tail() -> None:
    view = MainMenuView.__new__(MainMenuView)
    injured = [
        SimpleNamespace(name="山田太郎", injury_games_left=3),
        SimpleNamespace(name="短い", injury_games_left=1),
    ]
    line = view._format_injured_players_priority_line(injured)
    assert line.startswith("[優先] 負傷者2名:")
    assert "山田太郎（残り約3）" in line
    assert "短い（残り約1）" in line
    assert "戦術①" in line and "人事①" in line


def test_format_injured_players_priority_line_many_players_tail() -> None:
    view = MainMenuView.__new__(MainMenuView)
    injured = [SimpleNamespace(name=f"P{i}", injury_games_left=i) for i in range(7)]
    line = view._format_injured_players_priority_line(injured)
    assert "…ほか2名" in line
    assert "P0" in line and "P4" in line
    assert "P6" not in line.split("…")[0]


def test_injured_players_on_user_team_filters() -> None:
    view = MainMenuView.__new__(MainMenuView)
    view.team = None
    assert view._injured_players_on_user_team() == []

    ok = SimpleNamespace(name="A", injury_games_left=2)

    def _inj() -> bool:
        return True

    ok.is_injured = _inj  # type: ignore[attr-defined]
    bad = SimpleNamespace(name="B", injured=False)
    view.team = SimpleNamespace(players=[bad, ok])
    got = view._injured_players_on_user_team()
    assert len(got) == 1 and getattr(got[0], "name", None) == "A"
