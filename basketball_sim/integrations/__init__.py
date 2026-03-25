"""外部サービス連携（Steam 等）の受け皿。"""

from basketball_sim.integrations.steamworks_bridge import (
    is_steam_initialized,
    try_init_steam,
)

__all__ = ["is_steam_initialized", "try_init_steam"]
