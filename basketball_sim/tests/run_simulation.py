from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートを Python パスに追加して、`basketball_sim.*` の絶対importを通す
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]  # .../basketball_project

project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from basketball_sim.tests.test_console_encoding import configure_console_encoding

from basketball_sim.main import simulate


if __name__ == "__main__":
    # テストとして、1シーズン回るか確認するためのエントリポイント
    configure_console_encoding()
    simulate()