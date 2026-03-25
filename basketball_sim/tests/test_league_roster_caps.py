"""国内リーグの外国籍枠定数（game_constants）。"""

from basketball_sim.config.game_constants import (
    LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
    LEAGUE_ONCOURT_FOREIGN_CAP,
    LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    LEAGUE_ROSTER_FOREIGN_CAP,
)


def test_league_caps_match_b_league_style_defaults() -> None:
    assert LEAGUE_ROSTER_FOREIGN_CAP == 3
    assert LEAGUE_ROSTER_ASIA_NATURALIZED_CAP == 1
    assert LEAGUE_ONCOURT_FOREIGN_CAP == 2
    assert LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP == 1
