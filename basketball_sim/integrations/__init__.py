"""外部サービス連携（Steam 等）の受け皿。"""

from basketball_sim.integrations.steamworks_bridge import try_init_steam

__all__ = ["try_init_steam"]
