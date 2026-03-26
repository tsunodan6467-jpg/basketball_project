from typing import List, Optional, Dict, Tuple

from basketball_sim.config.game_constants import (
    LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
    LEAGUE_ONCOURT_FOREIGN_CAP,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team


class RotationSystem:
    """
    試合中のローテーション管理

    目的:
    - 往復交代を減らす
    - ベンチを自然に使う
    - match.py の get_lineup() 主体運用に対応
    - 終盤は主力寄りに締める
    - デバッグで交代停止理由を確認できる
    - 9〜12人ロスターで極端な0.0 minを減らす

    今回の追加:
    - team.usage_policy を target minutes に安全反映
      balanced   : 現状維持
      win_now    : 主力重視
      development: 若手重視
    - team.bench_order をベンチ優先順位として安全反映
      7番手 / 8番手 / 9番手… の優先度を交代候補評価に加点
    - OUT選手のポジションに応じた小さめの適合加点を追加
      同ポジ優先だが、絶対固定にはしない

    設計方針:
    - 既存の substitution logic は壊さない
    - target minutes / in-candidate 評価 / best substitute 評価に
      ベンチ序列を薄く載せるだけ
    - 6thマンは最優先、その次にベンチ序列が効く
    - ポジション適合は _find_best_substitute() に小さく載せるだけ
    """

    DEBUG_ROTATION = False

    def __init__(
        self,
        team: Team,
        active_players: List[Player],
        starters: Optional[List[Player]] = None
    ):
        self.team = team
        self.active_players = [p for p in active_players if not p.is_injured() and not p.is_retired]

        sorted_players = sorted(
            self.active_players,
            key=lambda p: p.get_effective_ovr(),
            reverse=True
        )

        if starters and len(starters) >= 5:
            self.current_lineup = starters[:5]
        else:
            self.current_lineup = sorted_players[:5]

        self.bench = [p for p in sorted_players if p not in self.current_lineup]

        # 実分換算の出場時間
        self.player_minutes: Dict[int, float] = {self._player_key(p): 0.0 for p in self.active_players}
        self.player_stints: Dict[int, int] = {self._player_key(p): 0 for p in self.active_players}

        self.last_sub_out_possession: Dict[int, int] = {}
        self.last_sub_in_possession: Dict[int, int] = {}
        self.lineup_entry_possession: Dict[int, int] = {
            self._player_key(p): 0 for p in self.current_lineup
        }

        self.last_processed_possession = 0
        self.last_sub_check_possession = -999

        self.quarter = 1
        self.possession_in_quarter = 0
        self.total_possessions = 160

        self._pending_sub_logs: List[str] = []

        # 同一ペア往復抑制
        self.last_pair_swap_possession: Dict[Tuple[int, int], int] = {}

    def _debug(self, message: str):
        if self.DEBUG_ROTATION:
            print(f"[ROT-DEBUG] {self.team.name} | {message}")

    def _player_key(self, player: Player) -> int:
        return id(player)

    def _is_foreign(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") == "Foreign"

    def _is_asia_or_naturalized(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") in ("Asia", "Naturalized")

    def _count_foreign(self, players: List[Player]) -> int:
        return sum(1 for p in players if self._is_foreign(p))

    def _count_asia_nat(self, players: List[Player]) -> int:
        return sum(1 for p in players if self._is_asia_or_naturalized(p))

    def _get_minutes(self, player: Player) -> float:
        return self.player_minutes.get(self._player_key(player), 0.0)

    def _add_minutes(self, player: Player, value: float):
        key = self._player_key(player)
        self.player_minutes[key] = self.player_minutes.get(key, 0.0) + value

    def _get_stints(self, player: Player) -> int:
        return self.player_stints.get(self._player_key(player), 0)

    def _add_stint(self, player: Player, value: int = 1):
        key = self._player_key(player)
        self.player_stints[key] = self.player_stints.get(key, 0) + value

    def _sync_current_lineup(self, current_lineup: List[Player], possession: int):
        incoming_keys = {self._player_key(p) for p in current_lineup}
        current_keys = {self._player_key(p) for p in self.current_lineup}

        if incoming_keys == current_keys:
            return

        self.current_lineup = current_lineup[:]
        self.bench = [p for p in self.active_players if p not in self.current_lineup]

        for p in self.current_lineup:
            key = self._player_key(p)
            if key not in self.lineup_entry_possession:
                self.lineup_entry_possession[key] = possession

    def _possession_to_minutes(self, possessions: int) -> float:
        total_poss = max(1, self.total_possessions)
        return possessions * (40.0 / total_poss)

    def _update_play_time_until(self, possession: int):
        delta = possession - self.last_processed_possession
        if delta <= 0:
            return

        add_minutes = self._possession_to_minutes(delta)

        for p in self.current_lineup:
            self._add_minutes(p, add_minutes)

        self.last_processed_possession = possession

    def _current_stint_length(self, player: Player, possession: int) -> int:
        key = self._player_key(player)
        entry = self.lineup_entry_possession.get(key, possession)
        return max(0, possession - entry)

    def _is_late_game(self, possession: int, total_possessions: int) -> bool:
        return possession >= max(0, total_possessions - 20)

    def _is_closing_time(self, possession: int, total_possessions: int) -> bool:
        return possession >= max(0, total_possessions - 10)

    def _rotation_depth(self) -> int:
        return len(self.active_players)

    def _bench_size(self) -> int:
        return max(0, len(self.active_players) - 5)

    def _get_rank_map(self) -> Dict[int, int]:
        sorted_players = sorted(
            self.active_players,
            key=lambda p: p.get_effective_ovr(),
            reverse=True
        )
        return {self._player_key(p): idx for idx, p in enumerate(sorted_players)}

    def _get_usage_policy(self) -> str:
        policy = getattr(self.team, "usage_policy", "balanced")
        if policy not in {"balanced", "win_now", "development"}:
            return "balanced"
        return policy

    def _get_sixth_man_key(self) -> Optional[int]:
        if hasattr(self.team, "get_sixth_man"):
            sixth = self.team.get_sixth_man()
            if sixth is not None:
                return self._player_key(sixth)
        return None

    def _get_bench_order_bonus_map(self) -> Dict[int, float]:
        bonus_map: Dict[int, float] = {}

        if not hasattr(self.team, "get_bench_order_players"):
            return bonus_map

        try:
            ordered_bench = self.team.get_bench_order_players()
        except Exception:
            return bonus_map

        # 軽量版:
        # 6thマンの次に 7番手 / 8番手 / 9番手 / 10番手…
        # を薄く優先するだけに留める
        bench_priority_bonus = [3.0, 2.2, 1.6, 1.1, 0.7, 0.4, 0.2]

        for idx, player in enumerate(ordered_bench):
            key = self._player_key(player)
            if idx < len(bench_priority_bonus):
                bonus_map[key] = bench_priority_bonus[idx]
            else:
                bonus_map[key] = 0.0

        return bonus_map

    def _get_position_fit_bonus(self, out_player: Player, in_player: Player) -> float:
        out_pos = getattr(out_player, "position", "SF")
        in_pos = getattr(in_player, "position", "SF")

        fit_map = {
            "PG": {"PG": 4.0, "SG": 1.5, "SF": 0.3, "PF": 0.0, "C": 0.0},
            "SG": {"SG": 4.0, "SF": 2.0, "PG": 1.2, "PF": 0.4, "C": 0.0},
            "SF": {"SF": 4.0, "SG": 1.8, "PF": 1.8, "PG": 0.5, "C": 0.5},
            "PF": {"PF": 4.0, "C": 2.0, "SF": 1.0, "SG": 0.2, "PG": 0.0},
            "C": {"C": 4.0, "PF": 2.2, "SF": 0.5, "SG": 0.0, "PG": 0.0},
        }

        return fit_map.get(out_pos, {}).get(in_pos, 0.0)

    def _clamp_target_minutes(self, minutes: float) -> float:
        return max(4.0, min(38.0, float(minutes)))

    def _build_target_minutes_map(self) -> Dict[int, float]:
        sorted_players = sorted(
            self.active_players,
            key=lambda p: p.get_effective_ovr(),
            reverse=True
        )

        player_count = len(sorted_players)

        if player_count <= 8:
            base_targets = [33, 32, 31, 30, 28, 24, 22, 20]
        elif player_count <= 9:
            base_targets = [31, 30, 29, 28, 26, 22, 20, 18, 16]
        elif player_count <= 10:
            base_targets = [30, 29, 28, 27, 25, 21, 19, 17, 15, 13]
        elif player_count <= 11:
            base_targets = [29, 28, 27, 26, 24, 20, 18, 16, 14, 12, 10]
        else:
            base_targets = [28, 27, 26, 25, 23, 19, 17, 15, 13, 11, 9, 8]

        targets: Dict[int, float] = {}
        rank_map = {self._player_key(p): i for i, p in enumerate(sorted_players)}
        starter_keys = {self._player_key(p) for p in self.current_lineup}
        sixth_man_key = self._get_sixth_man_key()
        usage_policy = self._get_usage_policy()
        bench_bonus_map = self._get_bench_order_bonus_map()

        for i, p in enumerate(sorted_players):
            key = self._player_key(p)
            if i < len(base_targets):
                target = float(base_targets[i])
            else:
                target = 6.0

            age = getattr(p, "age", 25)
            ovr = p.get_effective_ovr()
            is_starter = key in starter_keys
            is_sixth_man = sixth_man_key == key
            rank = rank_map.get(key, 99)

            if usage_policy == "win_now":
                if rank <= 2:
                    target += 4.5
                elif rank <= 4:
                    target += 2.5
                elif rank == 5:
                    target += 1.0
                elif rank >= 8:
                    target -= 3.0
                elif rank >= 6:
                    target -= 1.5

                if is_starter:
                    target += 1.5
                if age >= 29 and ovr >= 74:
                    target += 0.8

            elif usage_policy == "development":
                if age <= 21:
                    target += 5.0
                elif age <= 23:
                    target += 3.5
                elif age <= 25:
                    target += 2.0
                elif age <= 27:
                    target += 0.8

                # Youth callups (16〜18) should get some floor time
                # when the team is explicitly in development mode.
                if str(getattr(p, "acquisition_type", "") or "") == "youth":
                    target = max(target, 8.0)

                if rank <= 2 and ovr >= 78:
                    target -= 2.5
                elif rank <= 4 and ovr >= 74:
                    target -= 1.5

                if age >= 30:
                    target -= 1.5
                elif age >= 28:
                    target -= 0.8

            if is_sixth_man and not is_starter:
                target += 3.0
                if usage_policy == "win_now":
                    target += 1.5
                elif usage_policy == "development" and age <= 24:
                    target += 1.5
            elif not is_starter:
                target += bench_bonus_map.get(key, 0.0) * 0.55

            targets[key] = self._clamp_target_minutes(target)

        return targets

    def _count_bench_low_minutes(self, threshold: float = 1.0) -> int:
        return sum(1 for p in self.bench if self._get_minutes(p) <= threshold)

    def _count_bench_zero_minutes(self) -> int:
        return sum(1 for p in self.bench if self._get_minutes(p) <= 0.1)

    def _need_force_bench_exposure(self, possession: int, total_possessions: int) -> bool:
        if self._is_late_game(possession, total_possessions):
            return False
        return self._count_bench_zero_minutes() >= 1

    def _can_sub_in(self, player: Player, possession: int, total_possessions: int) -> bool:
        key = self._player_key(player)
        last_out = self.last_sub_out_possession.get(key, -999)

        cooldown_possessions = 12
        if self._rotation_depth() <= 10:
            cooldown_possessions = 10
        if self._rotation_depth() <= 9:
            cooldown_possessions = 8

        if self._is_late_game(possession, total_possessions):
            cooldown_possessions = min(cooldown_possessions, 10)
        if self._is_closing_time(possession, total_possessions):
            cooldown_possessions = min(cooldown_possessions, 8)

        if self._get_minutes(player) <= 0.1 and not self._is_late_game(possession, total_possessions):
            cooldown_possessions = min(cooldown_possessions, 6)

        # Development policy: youth callups rotate in a bit more easily
        if (
            self._get_usage_policy() == "development"
            and str(getattr(player, "acquisition_type", "") or "") == "youth"
            and not self._is_late_game(possession, total_possessions)
        ):
            cooldown_possessions = min(cooldown_possessions, 6)

        return (possession - last_out) >= cooldown_possessions

    def _can_sub_out(self, player: Player, possession: int, total_possessions: int) -> bool:
        key = self._player_key(player)
        last_in = self.last_sub_in_possession.get(key, -999)
        stint_len = self._current_stint_length(player, possession)

        min_stint_possessions = 12
        if self._rotation_depth() <= 10:
            min_stint_possessions = 10
        if self._rotation_depth() <= 9:
            min_stint_possessions = 8

        if self._is_late_game(possession, total_possessions):
            min_stint_possessions = min(min_stint_possessions, 10)
        if self._is_closing_time(possession, total_possessions):
            min_stint_possessions = min(min_stint_possessions, 8)

        if self._need_force_bench_exposure(possession, total_possessions):
            min_stint_possessions = max(6, min_stint_possessions - 2)

        if possession - last_in < min_stint_possessions:
            return False
        if stint_len < min_stint_possessions:
            return False

        return True

    def _is_lineup_legal_after_swap(
        self,
        lineup: List[Player],
        out_player: Player,
        in_player: Player
    ) -> bool:
        new_lineup = lineup[:]
        if out_player not in new_lineup:
            return False
        if in_player in new_lineup:
            return False

        idx = new_lineup.index(out_player)
        new_lineup[idx] = in_player

        foreign = self._count_foreign(new_lineup)
        asia_nat = self._count_asia_nat(new_lineup)

        return (
            foreign <= LEAGUE_ONCOURT_FOREIGN_CAP
            and asia_nat <= LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP
        )

    def _pair_swap_blocked(self, out_player: Player, in_player: Player, possession: int) -> bool:
        if self._get_minutes(in_player) <= 2.0:
            return False

        out_key = self._player_key(out_player)
        in_key = self._player_key(in_player)

        recent_1 = self.last_pair_swap_possession.get((out_key, in_key), -999)
        recent_2 = self.last_pair_swap_possession.get((in_key, out_key), -999)
        recent = max(recent_1, recent_2)

        block_window = 18
        if self._rotation_depth() <= 10:
            block_window = 14
        if self._rotation_depth() <= 9:
            block_window = 12

        return (possession - recent) < block_window

    def _get_out_candidates(
        self,
        possession: int,
        total_possessions: int,
        target_map: Dict[int, float]
    ) -> List[Player]:
        candidates = []
        rank_map = self._get_rank_map()
        is_late = self._is_late_game(possession, total_possessions)
        is_closing = self._is_closing_time(possession, total_possessions)
        bench_fresh_count = self._count_bench_low_minutes(1.0)
        bench_zero_count = self._count_bench_zero_minutes()

        for p in self.current_lineup:
            if not self._can_sub_out(p, possession, total_possessions):
                continue

            stamina = p.get_adjusted_attribute("stamina")
            played = self._get_minutes(p)
            target = target_map.get(self._player_key(p), 20.0)
            ovr = p.get_effective_ovr()
            rank = rank_map.get(self._player_key(p), 99)
            stint = self._current_stint_length(p, possession)

            score = 0.0
            over_target = played - target

            if over_target >= 4.0:
                score += 4.0
            elif over_target >= 2.5:
                score += 2.5
            elif over_target >= 1.0:
                score += 1.0

            if stamina <= 45:
                score += 4.0
            elif stamina <= 55:
                score += 2.8
            elif stamina <= 65:
                score += 1.7
            elif stamina <= 75:
                score += 0.8

            if played >= 3.0 and stint >= 14:
                score += 0.8
            if played >= 4.5 and stint >= 20:
                score += 1.0
            if played >= 6.0 and stint >= 28:
                score += 1.4

            if bench_zero_count >= 1 and rank >= 4 and played >= 3.0:
                score += 1.0
            if bench_zero_count >= 2 and rank >= 5 and played >= 3.0:
                score += 1.2
            if bench_fresh_count >= 2 and rank >= 5 and played >= 3.0:
                score += 0.9
            if bench_fresh_count >= 3 and rank >= 7 and played >= 2.5:
                score += 0.9

            if self._rotation_depth() <= 10 and rank >= 4 and played >= 4.0:
                score += 0.6
            if self._rotation_depth() <= 9 and rank >= 3 and played >= 5.0:
                score += 0.6

            if rank >= 8:
                score += 1.0
            elif rank >= 6:
                score += 0.4

            if is_late and rank <= 2:
                score -= 1.8
            elif is_late and rank <= 4:
                score -= 0.8

            if is_closing and rank <= 4:
                score -= 2.5
            if is_closing and ovr >= 78:
                score -= 1.0

            threshold = 0.6
            if bench_zero_count >= 1 and not is_late:
                threshold = 0.1

            if score >= threshold:
                candidates.append((p, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in candidates]

    def _get_force_exposure_out_candidates(
        self,
        possession: int,
        total_possessions: int
    ) -> List[Player]:
        """
        未出場ベンチが残っているのに通常 out_candidates が空だった時の救済。
        序盤〜中盤のみ、主に主力下位〜中位を弱めに押し出す。
        """
        if not self._need_force_bench_exposure(possession, total_possessions):
            return []

        rank_map = self._get_rank_map()
        candidates = []

        for p in self.current_lineup:
            if not self._can_sub_out(p, possession, total_possessions):
                continue

            played = self._get_minutes(p)
            stint = self._current_stint_length(p, possession)
            rank = rank_map.get(self._player_key(p), 99)
            stamina = p.get_adjusted_attribute("stamina")

            score = 0.0

            if played >= 2.5:
                score += 1.2
            if played >= 4.0:
                score += 1.0
            if stint >= 10:
                score += 1.0
            if stint >= 14:
                score += 0.6

            if rank >= 4:
                score += 1.2
            elif rank == 3:
                score += 0.4

            if stamina <= 70:
                score += 0.5

            if score > 0:
                candidates.append((p, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in candidates]

    def _get_in_candidates(
        self,
        possession: int,
        total_possessions: int,
        target_map: Dict[int, float]
    ) -> List[Player]:
        candidates = []
        rank_map = self._get_rank_map()
        is_late = self._is_late_game(possession, total_possessions)
        is_closing = self._is_closing_time(possession, total_possessions)
        bench_zero_count = self._count_bench_zero_minutes()
        sixth_man_key = self._get_sixth_man_key()
        bench_bonus_map = self._get_bench_order_bonus_map()

        for p in self.bench:
            if p.is_injured() or p.is_retired:
                continue
            if not self._can_sub_in(p, possession, total_possessions):
                continue

            stamina = p.get_adjusted_attribute("stamina")
            ovr = p.get_effective_ovr()
            played = self._get_minutes(p)
            target = target_map.get(self._player_key(p), 16.0)
            rank = rank_map.get(self._player_key(p), 99)

            shortage = max(0.0, target - played)

            score = 0.0
            score += shortage * 1.0
            score += stamina * 0.33
            score += ovr * 0.50

            if played <= 0.1:
                score += 8.0
            elif played <= 2.0:
                score += 4.0
            elif played <= 4.0:
                score += 2.0

            if self._player_key(p) == sixth_man_key:
                score += 5.5
                if not is_closing:
                    score += 1.5
            else:
                score += bench_bonus_map.get(self._player_key(p), 0.0) * 1.35

            if not is_late and bench_zero_count >= 1 and played <= 0.1:
                score += 3.0
            if not is_late and bench_zero_count >= 2 and played <= 2.0:
                score += 1.5

            if self._rotation_depth() <= 10 and rank >= 7 and not is_closing:
                score += 1.2
            if self._rotation_depth() <= 9 and rank >= 6 and not is_closing:
                score += 1.0

            if is_late and rank <= 4:
                score += 4.0
            elif is_late and rank >= 8:
                score -= 2.0

            if is_closing and rank <= 4:
                score += 7.0
            elif is_closing and rank >= 8:
                score -= 6.0

            candidates.append((p, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in candidates]

    def _find_best_substitute(
        self,
        out_player: Player,
        in_candidates: List[Player],
        possession: int,
        total_possessions: int
    ) -> Optional[Player]:
        if not in_candidates:
            return None

        out_ovr = out_player.get_effective_ovr()
        rank_map = self._get_rank_map()
        is_late = self._is_late_game(possession, total_possessions)
        is_closing = self._is_closing_time(possession, total_possessions)
        bench_zero_count = self._count_bench_zero_minutes()
        sixth_man_key = self._get_sixth_man_key()
        bench_bonus_map = self._get_bench_order_bonus_map()

        best_player = None
        best_score = -10**9
        blocked_pair_count = 0
        illegal_count = 0

        for p in in_candidates:
            if not self._is_lineup_legal_after_swap(self.current_lineup, out_player, p):
                illegal_count += 1
                continue
            if self._pair_swap_blocked(out_player, p, possession):
                blocked_pair_count += 1
                continue

            stamina = p.get_adjusted_attribute("stamina")
            ovr = p.get_effective_ovr()
            played = self._get_minutes(p)
            rank = rank_map.get(self._player_key(p), 99)

            diff_penalty = abs(ovr - out_ovr) * 0.35
            freshness_bonus = max(0.0, 18.0 - played) * 0.35

            score = (ovr * 1.08) + (stamina * 0.80) + freshness_bonus - diff_penalty

            if played <= 0.1:
                score += 5.0
            elif played <= 2.0:
                score += 2.5

            if self._player_key(p) == sixth_man_key:
                score += 4.5
            else:
                score += bench_bonus_map.get(self._player_key(p), 0.0) * 1.10

            score += self._get_position_fit_bonus(out_player, p)

            if bench_zero_count >= 1 and not is_late and played <= 0.1:
                score += 3.0

            if self._rotation_depth() <= 10 and rank >= 7 and not is_closing:
                score += 1.0

            if is_late and rank <= 4:
                score += 4.0
            elif is_late and rank >= 8:
                score -= 2.0

            if is_closing and rank <= 4:
                score += 7.0
            elif is_closing and rank >= 8:
                score -= 6.0

            if score > best_score:
                best_score = score
                best_player = p

        if best_player is None:
            self._debug(
                f"best_sub_none | out={out_player.name} | "
                f"in_candidates={len(in_candidates)} | illegal={illegal_count} | pair_blocked={blocked_pair_count}"
            )

        return best_player

    def _apply_substitution(
        self,
        out_player: Player,
        in_player: Player,
        possession: int
    ):
        out_index = self.current_lineup.index(out_player)
        self.current_lineup[out_index] = in_player

        if in_player in self.bench:
            self.bench.remove(in_player)
        if out_player not in self.bench:
            self.bench.append(out_player)

        out_key = self._player_key(out_player)
        in_key = self._player_key(in_player)

        self.last_sub_out_possession[out_key] = possession
        self.last_sub_in_possession[in_key] = possession
        self.lineup_entry_possession[in_key] = possession
        self._add_stint(in_player, 1)

        self.last_pair_swap_possession[(out_key, in_key)] = possession

        self._pending_sub_logs.append(f"[SUB] {self.team.name} | {out_player.name}→{in_player.name}")
        self._debug(f"SUB_OK | {out_player.name}→{in_player.name} | pos={possession}")

    def _should_substitute_now(
        self,
        possession: int,
        possession_in_quarter: int,
        total_possessions: int
    ) -> bool:
        if possession <= 0:
            return False

        if possession_in_quarter <= 0:
            return False

        if possession == self.last_sub_check_possession:
            return False

        if possession_in_quarter in (10, 20, 30):
            return True

        if possession_in_quarter == 15 and self.quarter in (1, 2, 3):
            return True

        if possession_in_quarter == 25 and self.quarter in (1, 2, 3):
            if self._need_force_bench_exposure(possession, total_possessions):
                return True

        if self._rotation_depth() <= 10 and possession_in_quarter == 5 and self.quarter in (2, 3):
            return True

        if self.quarter == 4 and possession_in_quarter >= max(1, total_possessions // 4 - 6):
            return possession_in_quarter == 20

        return False

    def _run_rotation(
        self,
        possession: int,
        total_possessions: int,
        possession_in_quarter: int
    ) -> List[Player]:
        self.total_possessions = max(1, total_possessions)
        self._update_play_time_until(possession)

        if len(self.current_lineup) < 5:
            return self.current_lineup[:]

        if not self._should_substitute_now(possession, possession_in_quarter, total_possessions):
            return self.current_lineup[:]

        self.last_sub_check_possession = possession
        self._pending_sub_logs = []

        self._debug(
            f"trigger | Q{self.quarter} {possession_in_quarter} | "
            f"pos={possession}/{total_possessions} | lineup={','.join(p.name for p in self.current_lineup)}"
        )

        target_map = self._build_target_minutes_map()
        out_candidates = self._get_out_candidates(possession, total_possessions, target_map)
        in_candidates = self._get_in_candidates(possession, total_possessions, target_map)

        if not out_candidates and self._need_force_bench_exposure(possession, total_possessions):
            out_candidates = self._get_force_exposure_out_candidates(possession, total_possessions)
            if out_candidates:
                self._debug(f"force_exposure_out_fallback | count={len(out_candidates)}")

        self._debug(
            f"candidate_counts | out={len(out_candidates)} | in={len(in_candidates)} | bench={len(self.bench)}"
        )

        if out_candidates:
            self._debug(
                "out_top | " + ", ".join(
                    f"{p.name}(min={self._get_minutes(p):.1f},stint={self._current_stint_length(p, possession)})"
                    for p in out_candidates[:3]
                )
            )
        else:
            self._debug("out_top | none")

        if in_candidates:
            self._debug(
                "in_top | " + ", ".join(
                    f"{p.name}(min={self._get_minutes(p):.1f})"
                    for p in in_candidates[:3]
                )
            )
        else:
            self._debug("in_top | none")

        if not out_candidates or not in_candidates:
            self._debug("skip_rotation | empty_candidates")
            return self.current_lineup[:]

        is_late = self._is_late_game(possession, total_possessions)
        is_closing = self._is_closing_time(possession, total_possessions)
        bench_zero_count = self._count_bench_zero_minutes()

        if is_closing:
            max_subs = 1
        elif is_late:
            max_subs = 1
        else:
            max_subs = 2

        if not is_late and bench_zero_count >= 2 and self._bench_size() >= 3:
            max_subs = 3
        elif not is_late and bench_zero_count >= 1 and self._bench_size() >= 2:
            max_subs = max(max_subs, 2)

        if self._rotation_depth() <= 10:
            max_subs = min(max_subs, 2)

        subs_made = 0
        used_in_keys = set()
        used_out_keys = set()

        for out_player in out_candidates:
            if subs_made >= max_subs:
                break

            out_key = self._player_key(out_player)
            if out_key in used_out_keys:
                continue
            if out_player not in self.current_lineup:
                continue

            available_ins = [
                p for p in in_candidates
                if self._player_key(p) not in used_in_keys and p not in self.current_lineup
            ]

            in_player = self._find_best_substitute(out_player, available_ins, possession, total_possessions)
            if in_player is None:
                continue

            self._apply_substitution(out_player, in_player, possession)

            used_out_keys.add(out_key)
            used_in_keys.add(self._player_key(in_player))
            subs_made += 1

        if subs_made == 0:
            self._debug("skip_rotation | no_sub_applied")

        return self.current_lineup[:]

    def get_lineup(
        self,
        current_lineup: Optional[List[Player]] = None,
        possession: int = 0,
        total_possessions: int = 160,
        quarter: int = 1,
        possession_in_quarter: int = 0,
        possessions_per_quarter: int = 0,
        score_diff: int = 0
    ) -> List[Player]:
        if current_lineup:
            self._sync_current_lineup(current_lineup, possession)

        self.quarter = quarter
        self.possession_in_quarter = possession_in_quarter
        self.total_possessions = max(1, total_possessions)

        return self._run_rotation(
            possession=possession,
            total_possessions=total_possessions,
            possession_in_quarter=possession_in_quarter
        )

    # ===== 旧互換メソッド群 =====

    def start_quarter(self, quarter: int):
        self.quarter = quarter
        self.possession_in_quarter = 0

    def get_current_lineup(self) -> List[Player]:
        return self.current_lineup[:]

    def advance_possession(self):
        self.total_possessions += 1
        self.possession_in_quarter += 1

        add_minutes = self._possession_to_minutes(1)
        for p in self.current_lineup:
            self._add_minutes(p, add_minutes)

        self.last_processed_possession = self.total_possessions

    def should_substitute(self) -> bool:
        if self.possession_in_quarter <= 0:
            return False

        if self.possession_in_quarter in (10, 20, 30):
            return True

        if self.possession_in_quarter == 15 and self.quarter in (1, 2, 3):
            return True

        if self.possession_in_quarter == 25 and self.quarter in (1, 2, 3):
            if self._count_bench_zero_minutes() >= 1:
                return True

        if self._rotation_depth() <= 10 and self.possession_in_quarter == 5 and self.quarter in (2, 3):
            return True

        return False

    def make_substitutions(self) -> List[str]:
        self._pending_sub_logs = []

        possession = self.total_possessions
        target_map = self._build_target_minutes_map()
        out_candidates = self._get_out_candidates(possession, self.total_possessions, target_map)
        in_candidates = self._get_in_candidates(possession, self.total_possessions, target_map)

        if not out_candidates and self._count_bench_zero_minutes() >= 1 and not self._is_late_game(possession, self.total_possessions):
            out_candidates = self._get_force_exposure_out_candidates(possession, self.total_possessions)
            if out_candidates:
                self._debug(f"legacy_force_exposure_out_fallback | count={len(out_candidates)}")

        if not out_candidates or not in_candidates:
            self._debug("legacy_make_subs | empty_candidates")
            return []

        is_late = self._is_late_game(possession, self.total_possessions)
        is_closing = self._is_closing_time(possession, self.total_possessions)
        bench_zero_count = self._count_bench_zero_minutes()

        if is_closing:
            max_subs = 1
        elif is_late:
            max_subs = 1
        else:
            max_subs = 2

        if not is_late and bench_zero_count >= 2 and self._bench_size() >= 3:
            max_subs = 3
        elif not is_late and bench_zero_count >= 1 and self._bench_size() >= 2:
            max_subs = max(max_subs, 2)

        if self._rotation_depth() <= 10:
            max_subs = min(max_subs, 2)

        subs_made = 0
        used_in_keys = set()
        used_out_keys = set()

        for out_player in out_candidates:
            if subs_made >= max_subs:
                break

            out_key = self._player_key(out_player)
            if out_key in used_out_keys:
                continue
            if out_player not in self.current_lineup:
                continue

            available_ins = [
                p for p in in_candidates
                if self._player_key(p) not in used_in_keys and p not in self.current_lineup
            ]

            in_player = self._find_best_substitute(
                out_player,
                available_ins,
                possession,
                self.total_possessions
            )
            if in_player is None:
                continue

            self._apply_substitution(out_player, in_player, possession)

            used_out_keys.add(out_key)
            used_in_keys.add(self._player_key(in_player))
            subs_made += 1

        return self._pending_sub_logs[:]
