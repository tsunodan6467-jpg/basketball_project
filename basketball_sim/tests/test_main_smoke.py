"""main.run_smoke の回帰（配布 exe --smoke と同じ経路）。"""

from basketball_sim.main import run_smoke


def test_run_smoke_returns_zero() -> None:
    assert run_smoke() == 0
