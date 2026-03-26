"""`python -m basketball_sim` で CLI を起動するためのエントリ。"""

import sys

from basketball_sim.main import run_smoke, simulate


def main() -> None:
    if "--smoke" in sys.argv:
        raise SystemExit(run_smoke())
    simulate()


if __name__ == "__main__":
    main()
