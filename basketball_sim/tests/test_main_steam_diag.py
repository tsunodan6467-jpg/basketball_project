"""main.run_steam_diag の回帰（例外なく 0 を返す）。"""

from basketball_sim.main import run_steam_diag


def test_run_steam_diag_returns_zero() -> None:
    assert run_steam_diag() == 0

