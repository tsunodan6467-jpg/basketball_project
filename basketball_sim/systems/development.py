import logging
import random
from typing import List

_logger = logging.getLogger(__name__)


class DevelopmentSystem:
    """
    若手育成 / ベテラン衰退システム（修正版）。

    修正点:
    - potential は「成長上限」としてのみ使う
    - 既に potential を超えている選手を強制的に落とさない
    - 想定外の変動が出たら即エラーにする
    - team.players / team.roster の両方に対応
    - FAプール相当の対象を検出した場合、ログ末尾に [FA] を付与
    """

    VERSION = "20260312-E"

    POTENTIAL_MAP = {
        "S": 95,
        "A": 90,
        "B": 84,
        "C": 78,
        "D": 72,
    }

    @classmethod
    def apply_team_development(cls, team, total_season_games: int = 30) -> List[str]:
        logs = []

        players = cls._extract_players(team)
        is_fa_context = cls._is_free_agent_context(team)

        for player in players:
            if getattr(player, "is_retired", False):
                continue

            if getattr(player, "is_icon", False):
                log = cls._develop_single_player(
                    player=player,
                    team=team,
                    total_season_games=total_season_games,
                    icon_penalty=0.55,
                    is_fa_context=is_fa_context,
                )
            else:
                log = cls._develop_single_player(
                    player=player,
                    team=team,
                    total_season_games=total_season_games,
                    icon_penalty=1.0,
                    is_fa_context=is_fa_context,
                )

            if log:
                logs.append(log)

        return logs

    @classmethod
    def _extract_players(cls, team):
        players = getattr(team, "players", None)
        if players is not None:
            return players

        roster = getattr(team, "roster", None)
        if roster is not None:
            return roster

        return []

    @classmethod
    def _is_free_agent_context(cls, team) -> bool:
        if getattr(team, "is_free_agent_pool", False):
            return True

        if getattr(team, "is_free_agents", False):
            return True

        team_name = str(getattr(team, "name", "")).strip().lower()
        if team_name in {"fa", "free agent", "free agents", "free_agent", "free_agents"}:
            return True

        return False

    @classmethod
    def _develop_single_player(
        cls,
        player,
        team,
        total_season_games: int,
        icon_penalty: float = 1.0,
        is_fa_context: bool = False,
    ):
        old_ovr = int(getattr(player, "ovr", 0))
        age = int(getattr(player, "age", 20))
        games_played = int(getattr(player, "games_played", 0))
        position = getattr(player, "position", "SF")
        potential_value = cls._resolve_potential_value(player)

        if not hasattr(player, "development"):
            setattr(player, "development", cls._generate_development_from_potential(player))

        development = float(getattr(player, "development", 0.6))

        playing_time_factor = min(1.0, games_played / max(1, total_season_games))
        age_factor = cls._get_age_factor(age)
        coach_bonus = cls._get_coach_bonus(team, position)
        strategy_bonus = cls._get_strategy_bonus(team, position)

        branch = "unknown"
        raw_delta = 0
        final_delta = 0

        # 若手〜全盛期前半
        if age <= 27:
            branch = "young"

            # すでに potential を超えている選手は、成長余地0扱い
            growth_room = max(0, potential_value - old_ovr)

            base_growth = (
                growth_room * 0.055
                * development
                * age_factor
                * max(0.20, playing_time_factor)
                * coach_bonus
                * strategy_bonus
                * icon_penalty
            )

            if games_played < 5:
                base_growth *= 0.55
            elif games_played >= 24:
                base_growth *= 1.08

            if growth_room <= 3:
                base_growth *= 0.35
            elif growth_room <= 6:
                base_growth *= 0.60
            elif growth_room <= 10:
                base_growth *= 0.82

            base_growth += random.uniform(-0.25, 0.55)

            raw_delta = cls._roll_delta(base_growth)
            final_delta = max(-1, min(3, raw_delta))

            new_ovr = old_ovr + final_delta

            # potential は「下から伸びる時だけ」上限として使う
            if old_ovr < potential_value:
                new_ovr = min(new_ovr, potential_value)

            new_ovr = max(40, min(99, new_ovr))

        # 28-31は基本横ばい
        elif age <= 31:
            branch = "prime"

            mid_curve = (
                random.uniform(-0.45, 0.35)
                * max(0.75, development)
                * coach_bonus
                * strategy_bonus
                * icon_penalty
            )

            if games_played >= 24:
                mid_curve += 0.20
            elif games_played < 10:
                mid_curve -= 0.20

            raw_delta = cls._roll_delta(mid_curve)
            final_delta = max(-1, min(1, raw_delta))

            new_ovr = max(40, min(99, old_ovr + final_delta))

        # 32歳以上は緩やか衰退
        else:
            branch = "veteran"

            decline = random.uniform(0.35, 1.20)

            mitigation = 0.0
            if getattr(team, "coach_style", "balanced") == "development":
                mitigation += 0.18
            if games_played >= 24:
                mitigation += 0.18
            elif games_played >= 15:
                mitigation += 0.10
            if old_ovr >= 85:
                mitigation += 0.20
            elif old_ovr >= 80:
                mitigation += 0.10

            if age <= 33:
                mitigation += 0.15

            final_decline_value = max(0.10, decline - mitigation)

            if age >= 36:
                final_decline_value += 0.20
            if age >= 38:
                final_decline_value += 0.20

            raw_delta = -cls._roll_delta(final_decline_value)
            final_delta = max(-3, min(0, raw_delta))

            new_ovr = max(40, min(99, old_ovr + final_delta))

        setattr(player, "ovr", int(new_ovr))
        cls._apply_focus_micro_progression(
            player=player,
            team=team,
            age=age,
            games_played=games_played,
            total_season_games=total_season_games,
            branch=branch,
        )

        actual_delta = int(getattr(player, "ovr", 0)) - old_ovr

        if branch == "young" and not (-1 <= actual_delta <= 3):
            raise RuntimeError(
                f"[DEV-ERROR] young branch delta out of range | "
                f"name={player.name} age={age} gp={games_played} "
                f"old={old_ovr} new={player.ovr} actual={actual_delta} "
                f"raw_delta={raw_delta} final_delta={final_delta} "
                f"potential={potential_value} dev={development} "
                f"coach={getattr(team, 'coach_style', 'NA')} strat={getattr(team, 'strategy', 'NA')}"
            )

        if branch == "prime" and not (-1 <= actual_delta <= 1):
            raise RuntimeError(
                f"[DEV-ERROR] prime branch delta out of range | "
                f"name={player.name} age={age} gp={games_played} "
                f"old={old_ovr} new={player.ovr} actual={actual_delta} "
                f"raw_delta={raw_delta} final_delta={final_delta} "
                f"potential={potential_value} dev={development} "
                f"coach={getattr(team, 'coach_style', 'NA')} strat={getattr(team, 'strategy', 'NA')}"
            )

        if branch == "veteran" and not (-3 <= actual_delta <= 0):
            raise RuntimeError(
                f"[DEV-ERROR] veteran branch delta out of range | "
                f"name={player.name} age={age} gp={games_played} "
                f"old={old_ovr} new={player.ovr} actual={actual_delta} "
                f"raw_delta={raw_delta} final_delta={final_delta} "
                f"potential={potential_value} dev={development} "
                f"coach={getattr(team, 'coach_style', 'NA')} strat={getattr(team, 'strategy', 'NA')}"
            )

        if actual_delta == 0:
            return None

        sign = "+" if actual_delta > 0 else ""
        fa_suffix = " [FA]" if is_fa_context else ""

        return (
            f"[DEV-D] {player.name} {sign}{actual_delta} -> OVR {player.ovr} "
            f"(age:{age} gp:{games_played} branch:{branch}){fa_suffix}"
        )

    @classmethod
    def _apply_focus_micro_progression(
        cls,
        player,
        team,
        age: int,
        games_played: int,
        total_season_games: int,
        branch: str,
    ) -> None:
        """
        個別育成方針による微小な能力補正（Phase 3）。
        既存バランスを壊さないよう、年1回の +1 を稀に与えるだけに制限。
        """
        if age >= 32:
            return
        if branch not in {"young", "prime"}:
            return
        gp_ratio = min(1.0, games_played / max(1, total_season_games))
        if gp_ratio < 0.20:
            return

        focus = str(getattr(player, "training_focus", "balanced") or "balanced")
        if focus == "balanced":
            return

        lvl = int(getattr(team, "training_facility_level", 1) or 1)
        # 低頻度・低振れの安全設計（max ~20%）
        proc = min(0.20, 0.05 + lvl * 0.01 + gp_ratio * 0.04)
        if random.random() >= proc:
            return

        focus_map = {
            "shooting": ("shoot", "three", "ft"),
            "playmaking": ("passing", "drive", "handling"),
            "defense": ("defense", "rebound", "iq"),
            "physical": ("stamina", "speed", "power"),
            "iq_handling": ("iq", "handling", "passing"),
        }
        attrs = focus_map.get(focus)
        if not attrs:
            return
        target = random.choice(attrs)
        old = int(getattr(player, target, 50) or 50)
        setattr(player, target, int(max(1, min(99, old + 1))))

    @classmethod
    def _resolve_potential_value(cls, player) -> int:
        raw = getattr(player, "potential", "C")

        if isinstance(raw, (int, float)):
            return max(45, min(99, int(raw)))

        return cls.POTENTIAL_MAP.get(str(raw).upper(), 78)

    @classmethod
    def _generate_development_from_potential(cls, player) -> float:
        raw = getattr(player, "potential", "C")

        if isinstance(raw, (int, float)):
            val = int(raw)
            if val >= 90:
                return round(random.uniform(0.75, 1.00), 2)
            if val >= 82:
                return round(random.uniform(0.60, 0.85), 2)
            if val >= 75:
                return round(random.uniform(0.45, 0.70), 2)
            return round(random.uniform(0.30, 0.55), 2)

        p = str(raw).upper()
        if p == "S":
            return round(random.uniform(0.80, 1.00), 2)
        if p == "A":
            return round(random.uniform(0.68, 0.92), 2)
        if p == "B":
            return round(random.uniform(0.55, 0.80), 2)
        if p == "C":
            return round(random.uniform(0.42, 0.65), 2)
        return round(random.uniform(0.28, 0.50), 2)

    @classmethod
    def _get_age_factor(cls, age: int) -> float:
        if age <= 20:
            return 1.65
        if age <= 23:
            return 1.40
        if age <= 27:
            return 1.00
        if age <= 31:
            return 0.55
        return -0.35

    @classmethod
    def _get_coach_bonus(cls, team, position: str) -> float:
        coach_style = getattr(team, "coach_style", "balanced")

        if coach_style == "development":
            return 1.28

        if coach_style == "offense":
            if position in ("PG", "SG", "SF"):
                return 1.08
            return 0.97

        if coach_style == "defense":
            if position in ("PF", "C"):
                return 1.08
            return 0.98

        return 1.00

    @classmethod
    def _get_strategy_bonus(cls, team, position: str) -> float:
        strategy = getattr(team, "strategy", "balanced")

        if strategy == "run_and_gun":
            if position in ("PG", "SG"):
                return 1.06
            return 0.99

        if strategy == "three_point":
            if position in ("SG", "SF"):
                return 1.06
            return 0.99

        if strategy == "inside":
            if position in ("PF", "C"):
                return 1.06
            return 0.99

        if strategy == "defense":
            if position in ("PF", "C", "SF"):
                return 1.04
            return 1.00

        return 1.00

    @classmethod
    def _roll_delta(cls, base_value: float) -> int:
        if base_value == 0:
            return 0

        sign = 1 if base_value > 0 else -1
        abs_val = abs(base_value)
        whole = int(abs_val)
        frac = abs_val - whole

        delta = whole
        if random.random() < frac:
            delta += 1

        return delta * sign


_logger.debug("DevelopmentSystem loaded (version %s)", DevelopmentSystem.VERSION)