"""外部サービス連携（Steam 等）の受け皿。"""

from basketball_sim.integrations.steamworks_bridge import (
    enforce_steam_license,
    is_steam_initialized,
    pump_steam_callbacks,
    shutdown_steam,
    steam_is_subscribed,
    steam_native_loaded,
    try_init_steam,
    unlock_achievement,
)

__all__ = [
    "enforce_steam_license",
    "is_steam_initialized",
    "pump_steam_callbacks",
    "shutdown_steam",
    "steam_is_subscribed",
    "steam_native_loaded",
    "try_init_steam",
    "unlock_achievement",
]
