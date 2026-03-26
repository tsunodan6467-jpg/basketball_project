import random
from collections import Counter
from typing import Tuple, List, Optional, Dict

from .team import Team
from .player import Player
from basketball_sim.config.game_constants import (
    CLOCK_SECONDS_PER_REGULATION_QUARTER,
    FORFEIT_SCORE,
    LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
    LEAGUE_ONCOURT_FOREIGN_CAP,
    LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    LEAGUE_ROSTER_FOREIGN_CAP,
    MINIMUM_ACTIVE_PLAYERS_FOR_GAME,
)
from basketball_sim.systems.rotation import RotationSystem


class Match:
    """
    1試合を管理するクラス。

    仕様:
    - 1チームのロスターは13人想定
    - 試合登録は12人
    - 外国籍ルールを試合登録にも適用
      Foreign 最大3
      Asia / Naturalized 合計1

    - コート上5人にも外国籍ルールを適用
      Foreign 最大2
      Asia / Naturalized 合計1

    - RotationSystem を使って試合中の交代を管理
    - [SUB] ログには Q / そのQ内のポゼッション を表示
    - [MINUTES] ログで試合ごとの出場時間を表示

    今回の強化:
    - オフェンスリバウンド後にセカンドチャンス攻撃を発生
    - ショット選択を usage_base + 能力 + ポジション + 戦術で強化
    - アシスト / ブロック / スティール / リバウンドの記録者を自然化
    - ラインナップ能力に応じて 3P比率 / 2P比率 / OREB率 を動的化
    - 得点効率が高くなりすぎないよう成功率を微調整

    今回の調整:
    - アシスト発生率を安全に引き上げ
    - 3P成功時はアシストされやすく、2Pは中間、セカンドチャンスはやや低め
    - パサー選定をPG/SG/高Passing寄りにして、自然なAST分布に寄せる
    - ブロック記録者をよりPF/C中心に寄せ、ガードの不自然ブロックを減らす

    今回の追加:
    - ポジション別スタッツ傾向を安全に強化
      PG -> AST寄り / 得点やや抑制
      SG -> 得点寄り
      SF -> バランス
      PF -> REB寄り / インサイド得点やや増
      C  -> REB / BLK寄り / 3P得点はかなり抑制

    今回のBリーグ寄り微調整:
    - 平均得点を80点前後へ寄せるため、2P成功率を安全に上方補正
    - 3Pは上げすぎず、100点ゲームは時々出る程度に抑制
    - セカンドチャンス効率を少しだけ改善
    - FT成功率をほんの少しだけ改善

    今回の役割分布微調整:
    - PG の AST をもう少し伸ばす
    - SG の得点役を少し強める
    - C のインサイド得点を少し戻す
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        is_playoff: bool = False,
        competition_type: str = "regular_season"
    ):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.is_playoff = is_playoff
        self.competition_type = self._normalize_competition_type(competition_type)

        self.current_possession = 0
        self.total_possessions = 0

        self.home_active_players, self.home_inactive = self._select_active_roster(self.home_team)
        self.away_active_players, self.away_inactive = self._select_active_roster(self.away_team)

        self._print_active_roster(self.home_team, self.home_active_players, self.home_inactive)
        self._print_active_roster(self.away_team, self.away_active_players, self.away_inactive)

        self.home_starters = self._get_starting_five_from_players(self.home_active_players)
        self.away_starters = self._get_starting_five_from_players(self.away_active_players)

        self._print_starting_five(self.home_team, self.home_starters)
        self._print_starting_five(self.away_team, self.away_starters)

        self.home_current_lineup = list(self.home_starters)
        self.away_current_lineup = list(self.away_starters)

        self.home_rotation = RotationSystem(self.home_team, self.home_active_players, self.home_starters)
        self.away_rotation = RotationSystem(self.away_team, self.away_active_players, self.away_starters)

        self._minutes_tracker = {}
        self.play_by_play_log: List[Dict] = []
        self.commentary_log: List[Dict] = []
        self.commentary_index: int = 0
        self.play_sequence_log: List[Dict] = []
        self.play_sequence_index: int = 0

        self._event_context_quarter: Optional[int] = None
        self._event_context_clock_seconds: Optional[int] = None
        self._event_context_possession_no: Optional[int] = None

        self.minimum_active_players_required = MINIMUM_ACTIVE_PLAYERS_FOR_GAME
        self.forfeit_score = FORFEIT_SCORE

    def _player_key(self, player: Player):
        return getattr(player, "player_id", None) or id(player)

    def _team_key(self, team: Team):
        return getattr(team, "team_id", None) or getattr(team, "name", "unknown_team")

    def _player_log_key(self, player: Optional[Player]):
        if player is None:
            return None
        return getattr(player, "player_id", None) or getattr(player, "name", None) or id(player)

    def _is_home_team(self, team: Optional[Team]) -> bool:
        return team is not None and team == self.home_team

    def _build_score_snapshot(self, scoring_team: Optional[Team] = None, points: int = 0) -> Tuple[int, int]:
        home_score = self.home_score
        away_score = self.away_score

        if scoring_team is not None and points:
            if self._is_home_team(scoring_team):
                home_score += points
            else:
                away_score += points

        return home_score, away_score

    def _get_clock_seconds(self, possession_index: int) -> int:
        quarter, possession_in_quarter, possessions_per_quarter = self._get_quarter_info(possession_index)
        if possessions_per_quarter <= 0:
            return 0

        ratio_remaining = (possessions_per_quarter - possession_in_quarter + 1) / possessions_per_quarter
        cap = CLOCK_SECONDS_PER_REGULATION_QUARTER
        return max(0, min(cap, int(ratio_remaining * cap)))

    def _set_event_context(
        self,
        quarter: Optional[int] = None,
        clock_seconds: Optional[int] = None,
        possession_no: Optional[int] = None,
    ) -> None:
        self._event_context_quarter = quarter
        self._event_context_clock_seconds = clock_seconds
        self._event_context_possession_no = possession_no

    def _clear_event_context(self) -> None:
        self._event_context_quarter = None
        self._event_context_clock_seconds = None
        self._event_context_possession_no = None

    def _get_forfeit_team(self) -> Optional[Team]:
        home_count = len(self.home_active_players)
        away_count = len(self.away_active_players)
        minimum_required = self.minimum_active_players_required

        if home_count >= minimum_required and away_count >= minimum_required:
            return None

        if home_count < minimum_required and away_count >= minimum_required:
            return self.home_team

        if away_count < minimum_required and home_count >= minimum_required:
            return self.away_team

        if home_count < minimum_required and away_count < minimum_required:
            return self.home_team

        return None

    def _simulate_forfeit_game(self, forfeiting_team: Team) -> Tuple[Team, int, int]:
        winner = self.away_team if forfeiting_team == self.home_team else self.home_team

        if forfeiting_team == self.home_team:
            self.home_score = 0
            self.away_score = self.forfeit_score
            forfeiting_active = self.home_active_players
            winner_active = self.away_active_players
            forfeiting_lineup = self.home_current_lineup
            winner_lineup = self.away_current_lineup
        else:
            self.home_score = self.forfeit_score
            self.away_score = 0
            forfeiting_active = self.away_active_players
            winner_active = self.home_active_players
            forfeiting_lineup = self.away_current_lineup
            winner_lineup = self.home_current_lineup

        print(
            f"[FORFEIT] {forfeiting_team.name} は登録可能選手不足のため不戦敗 | "
            f"ACTIVE人数: {len(forfeiting_active)} / 必要人数: {self.minimum_active_players_required}"
        )
        print(f"[FORFEIT-RESULT] 勝者: {winner.name} | スコア: {self.home_team.name} {self.home_score} - {self.away_score} {self.away_team.name}")

        self._record_event(
            event_type="forfeit",
            description_key="forfeit",
            possession_index=0,
            quarter_override=1,
            clock_seconds_override=CLOCK_SECONDS_PER_REGULATION_QUARTER,
            meta={
                "forfeit_team_id": self._team_key(forfeiting_team),
                "winner_team_id": self._team_key(winner),
                "required_active_players": self.minimum_active_players_required,
                "forfeit_active_count": len(forfeiting_active),
                "competition_type": self.competition_type,
            },
        )
        self._record_event(
            event_type="game_end",
            description_key="game_end",
            possession_index=0,
            quarter_override=1,
            clock_seconds_override=0,
            meta={
                "winner_team_id": self._team_key(winner),
                "is_playoff": self.is_playoff,
                "overtime_count": 0,
                "ended_by_forfeit": True,
            },
        )

        self._record_team_game(
            self.home_team,
            self.home_active_players,
            self.home_current_lineup,
            winner == self.home_team,
            self.home_score,
            self.away_score,
            is_playoff=self.is_playoff,
        )
        self._record_team_game(
            self.away_team,
            self.away_active_players,
            self.away_current_lineup,
            winner == self.away_team,
            self.away_score,
            self.home_score,
            is_playoff=self.is_playoff,
        )

        self.home_team.process_injury_recovery()
        self.away_team.process_injury_recovery()

        self._print_minutes_log(self.home_team, self.home_active_players)
        self._print_minutes_log(self.away_team, self.away_active_players)
        self._print_play_by_play_debug_summary()
        self._print_commentary_preview()
        self._print_play_sequence_preview()

        return winner, self.home_score, self.away_score

    def _get_overtime_clock_seconds(self, possession_in_overtime: int, total_overtime_possessions: int) -> int:
        if total_overtime_possessions <= 0:
            return 0

        ratio_remaining = (total_overtime_possessions - possession_in_overtime + 1) / (total_overtime_possessions + 1)
        return max(1, min(300, int(ratio_remaining * 300)))

    def _record_event(
        self,
        event_type: str,
        offense_team: Optional[Team] = None,
        defense_team: Optional[Team] = None,
        primary_player: Optional[Player] = None,
        secondary_player: Optional[Player] = None,
        description_key: Optional[str] = None,
        meta: Optional[Dict] = None,
        scoring_team: Optional[Team] = None,
        points: int = 0,
        possession_index: Optional[int] = None,
        quarter_override: Optional[int] = None,
        clock_seconds_override: Optional[int] = None,
    ) -> None:
        if possession_index is None:
            possession_index = self.current_possession

        quarter = quarter_override
        if quarter is None:
            if self._event_context_quarter is not None:
                quarter = self._event_context_quarter
            else:
                quarter, _, _ = self._get_quarter_info(max(0, possession_index))

        clock_seconds = clock_seconds_override
        if clock_seconds is None:
            if self._event_context_clock_seconds is not None:
                clock_seconds = self._event_context_clock_seconds
            else:
                clock_seconds = self._get_clock_seconds(max(0, possession_index))

        if self._event_context_possession_no is not None:
            event_possession_no = self._event_context_possession_no
        else:
            event_possession_no = max(0, possession_index) + 1

        home_score, away_score = self._build_score_snapshot(scoring_team=scoring_team, points=points)

        event = {
            "quarter": quarter,
            "clock_seconds": clock_seconds,
            "possession_no": event_possession_no,
            "offense_team_id": self._team_key(offense_team) if offense_team is not None else None,
            "defense_team_id": self._team_key(defense_team) if defense_team is not None else None,
            "event_type": event_type,
            "primary_player_id": self._player_log_key(primary_player),
            "primary_player_name": getattr(primary_player, "name", None) if primary_player is not None else None,
            "secondary_player_id": self._player_log_key(secondary_player),
            "secondary_player_name": getattr(secondary_player, "name", None) if secondary_player is not None else None,
            "description_key": description_key or event_type,
            "home_score": home_score,
            "away_score": away_score,
            "meta": meta.copy() if meta else {},
        }
        self.play_by_play_log.append(event)

    def _add_lineup_minutes(self, lineup: List[Player]):
        for p in lineup:
            key = self._player_key(p)
            self._minutes_tracker[key] = self._minutes_tracker.get(key, 0) + 1

    def _get_player_minutes(self, player: Player) -> float:
        if self.total_possessions <= 0:
            return 0.0
        key = self._player_key(player)
        on_court_possessions = self._minutes_tracker.get(key, 0)
        return 40.0 * on_court_possessions / self.total_possessions

    def _print_minutes_log(self, team: Team, active_players: List[Player]):
        print(f"[MINUTES] {team.name}")

        rows = []
        for p in active_players:
            minutes = self._get_player_minutes(p)
            rows.append((minutes, p))

        rows.sort(key=lambda x: x[0], reverse=True)

        for i, (minutes, p) in enumerate(rows, 1):
            print(f"  {i:>2}. {p.name:<20} {minutes:>4.1f} min")

    def _format_pbp_event_for_debug(self, event: Dict) -> str:
        quarter = event.get("quarter", "?")
        clock_seconds = int(event.get("clock_seconds", 0) or 0)
        minutes = max(0, clock_seconds) // 60
        seconds = max(0, clock_seconds) % 60
        event_type = event.get("event_type", "unknown")
        primary = event.get("primary_player_name") or "-"
        secondary = event.get("secondary_player_name") or "-"
        score = f'{event.get("home_score", 0)}-{event.get("away_score", 0)}'
        return (
            f"Q{quarter} {minutes:02d}:{seconds:02d} | {event_type:<16} "
            f"| primary={primary} | secondary={secondary} | score={score}"
        )

    def _print_play_by_play_debug_summary(self):
        print("[PBP] Debug Summary")
        total_events = len(self.play_by_play_log)
        print(f"[PBP] total_events={total_events}")

        if total_events == 0:
            print("[PBP] play_by_play_log is empty")
            return

        event_counter = Counter(
            event.get("event_type", "unknown")
            for event in self.play_by_play_log
        )

        print("[PBP] event_type_counts")
        for event_type, count in sorted(event_counter.items()):
            print(f"  - {event_type:<16}: {count}")

        head_count = min(5, total_events)
        tail_count = min(5, total_events)

        print(f"[PBP] first_{head_count}")
        for event in self.play_by_play_log[:head_count]:
            print(f"  {self._format_pbp_event_for_debug(event)}")

        print(f"[PBP] last_{tail_count}")
        for event in self.play_by_play_log[-tail_count:]:
            print(f"  {self._format_pbp_event_for_debug(event)}")


    def _event_clock_label(self, event: Dict) -> str:
        quarter = event.get("quarter", "?")
        clock_seconds = int(event.get("clock_seconds", 0) or 0)
        minutes = max(0, clock_seconds) // 60
        seconds = max(0, clock_seconds) % 60
        return f"Q{quarter} {minutes:02d}:{seconds:02d}"

    def _get_event_player_name(self, event: Dict, key: str) -> str:
        name = event.get(key)
        return name if name else "その選手"

    def _commentary_pick(self, options: List[str], seed_value: int) -> str:
        if not options:
            return ""
        return options[seed_value % len(options)]

    def _get_score_before_event(self, event_index: int) -> Tuple[int, int]:
        if event_index <= 0:
            return 0, 0
        prev_event = self.play_by_play_log[event_index - 1]
        return int(prev_event.get("home_score", 0)), int(prev_event.get("away_score", 0))

    def _infer_scoring_side(self, event: Dict, event_index: int) -> Optional[str]:
        prev_home, prev_away = self._get_score_before_event(event_index)
        curr_home = int(event.get("home_score", 0))
        curr_away = int(event.get("away_score", 0))

        if curr_home > prev_home:
            return "home"
        if curr_away > prev_away:
            return "away"
        return None

    def _team_name_by_side(self, side: Optional[str]) -> str:
        if side == "home":
            return getattr(self.home_team, "name", "ホーム")
        if side == "away":
            return getattr(self.away_team, "name", "アウェー")
        return "どちらのチーム"

    def _is_clutch_time(self, event: Dict) -> bool:
        quarter = int(event.get("quarter", 0) or 0)
        clock_seconds = int(event.get("clock_seconds", 0) or 0)
        return quarter >= 4 and clock_seconds <= 120

    def _abs_score_diff(self, event: Dict) -> int:
        return abs(int(event.get("home_score", 0)) - int(event.get("away_score", 0)))

    def _is_blowout_margin(self, event: Dict, threshold: int = 18) -> bool:
        return self._abs_score_diff(event) >= threshold

    def _is_close_margin(self, event: Dict, max_diff: int = 6) -> bool:
        return self._abs_score_diff(event) <= max_diff

    def _build_miss_context_tail(self, event: Dict, event_index: int) -> str:
        """シュート不発のあとに付ける短い状況テキスト（空のことも多い）。"""
        seed = int(event.get("possession_no", 0) or 0) + int(event.get("clock_seconds", 0) or 0) + event_index
        if self._is_blowout_margin(event, 20):
            opts = [
                "この時間帯は点差が大きく開いています。",
                "試合の流れは大きく傾いています。",
            ]
            return self._commentary_pick(opts, seed)
        if self._is_clutch_time(event) and self._is_close_margin(event, 5):
            opts = [
                "ここは一攻一防が重みを増します。",
                "まだ勝負はここからです。",
            ]
            return self._commentary_pick(opts, seed)
        if self._is_close_margin(event, 8):
            if self._is_clutch_time(event):
                return ""
            return self._commentary_pick(
                [
                    "まだ流れはどちらにも転びます。",
                    "一気に流れが変わるかもしれません。",
                ],
                seed,
            )
        return ""

    def _get_scoring_run_info(self, event_index: int) -> Tuple[Optional[str], int]:
        run_side: Optional[str] = None
        run_points = 0

        for idx in range(event_index, -1, -1):
            event = self.play_by_play_log[idx]
            event_type = event.get("event_type")
            if event_type not in {"made_3", "made_2", "made_ft"}:
                continue

            side = self._infer_scoring_side(event, idx)
            if side is None:
                continue

            prev_home, prev_away = self._get_score_before_event(idx)
            curr_home = int(event.get("home_score", 0))
            curr_away = int(event.get("away_score", 0))
            added_points = max(curr_home - prev_home, curr_away - prev_away)

            if run_side is None:
                run_side = side
                run_points += added_points
                continue

            if side != run_side:
                break

            run_points += added_points

        return run_side, run_points

    def _build_score_state_text(self, event: Dict, event_index: int) -> str:
        home_score = int(event.get("home_score", 0))
        away_score = int(event.get("away_score", 0))

        if home_score == away_score:
            return "これで同点です。"

        lead_side = "home" if home_score > away_score else "away"
        diff = abs(home_score - away_score)
        team_name = self._team_name_by_side(lead_side)

        if diff == 1:
            return f"{team_name}が1点だけ前に出ました。"
        if diff <= 3:
            return f"{team_name}がわずかにリードを守ります。"
        if diff <= 7:
            return f"{team_name}が{diff}点リード。"
        if diff <= 12:
            return f"{team_name}が主導権を握る{diff}点差。"
        return f"{team_name}が{diff}点差まで広げました。"

    def _build_game_end_state_text(self, event: Dict, event_index: int) -> str:
        home_score = int(event.get("home_score", 0))
        away_score = int(event.get("away_score", 0))

        if home_score == away_score:
            return "延長にもつれ込む大接戦の末、決着は次の時間帯に委ねられます。"

        winner_side = "home" if home_score > away_score else "away"
        diff = abs(home_score - away_score)
        team_name = self._team_name_by_side(winner_side)

        if diff == 1:
            return f"{team_name}が1点差を守り切り、勝利をつかみました。"
        if diff <= 3:
            return f"{team_name}が接戦をものにしました。"
        if diff <= 7:
            return f"{team_name}がリードを守り切って勝利です。"
        if diff <= 12:
            return f"{team_name}が主導権を保ったまま勝ち切りました。"
        return f"{team_name}が最後まで流れを渡さず快勝です。"

    def _build_scoring_context_text(self, event: Dict, event_index: int) -> str:
        side = self._infer_scoring_side(event, event_index)
        if side is None:
            return ""

        prev_home, prev_away = self._get_score_before_event(event_index)
        curr_home = int(event.get("home_score", 0))
        curr_away = int(event.get("away_score", 0))

        prev_diff = abs(prev_home - prev_away)
        curr_diff = abs(curr_home - curr_away)

        if prev_home == prev_away and curr_home != curr_away:
            return "均衡を破る一撃です。"

        prev_lead_side: Optional[str] = None
        if prev_home != prev_away:
            prev_lead_side = "home" if prev_home > prev_away else "away"

        if curr_home == curr_away:
            return "これで試合は振り出しに戻りました。"

        curr_lead_side: Optional[str] = None
        if curr_home != curr_away:
            curr_lead_side = "home" if curr_home > curr_away else "away"

        if (
            prev_lead_side
            and curr_lead_side
            and prev_lead_side != curr_lead_side
            and curr_lead_side == side
        ):
            return "ここで逆転しました。"

        run_side, run_points = self._get_scoring_run_info(event_index)
        if run_side == side and run_points >= 8:
            return f"{self._team_name_by_side(side)}は{run_points}連続得点です。"
        if run_side == side and 5 <= run_points < 8:
            return self._commentary_pick(
                [
                    f"{self._team_name_by_side(side)}がちょっとした流れをつかみます。",
                    f"{self._team_name_by_side(side)}が小さな連続得点を重ねます。",
                ],
                int(event.get("possession_no", 0) or 0) + event_index,
            )

        if self._is_clutch_time(event):
            if curr_diff <= 3:
                return "終盤の大きな得点です。"
            return "この時間帯で貴重な加点になりました。"

        if prev_diff < 10 <= curr_diff:
            return "これで点差は二桁に乗りました。"

        if prev_diff >= 10 and curr_diff <= 6:
            return "点差を詰めて、流れを引き戻します。"

        return self._build_score_state_text(event, event_index)

    def _build_quarter_transition_text(self, event: Dict, event_index: int) -> str:
        score_text = f'{event.get("home_score", 0)}-{event.get("away_score", 0)}'
        clock_label = self._event_clock_label(event)
        quarter = event.get("quarter", "?")
        meta = event.get("meta", {}) or {}
        event_type = event.get("event_type", "unknown")

        if event_type == "quarter_start":
            if meta.get("is_overtime"):
                options = [
                    f"[{clock_label}] 延長開始です。スコアは{score_text}。ここから1本の価値がさらに重くなります。",
                    f"[{clock_label}] 延長戦に突入。スコアは{score_text}。会場の緊張感が一気に高まります。",
                ]
            else:
                qn = int(quarter or 0)
                if qn == 1:
                    options = [
                        f"[{clock_label}] 第{quarter}クォーター開始です。スコアは{score_text}。",
                        f"[{clock_label}] 第{quarter}クォーターが始まります。スコアは{score_text}。",
                        f"[{clock_label}] 試合開始です。スコアは{score_text}。ここから10分の攻防が始まります。",
                    ]
                elif qn == 2:
                    options = [
                        f"[{clock_label}] 第{quarter}クォーター開始です。スコアは{score_text}。前半は残り10分です。",
                        f"[{clock_label}] 第{quarter}クォーターが始まります。スコアは{score_text}。",
                        f"[{clock_label}] 前半の後半戦に入ります。スコアは{score_text}。",
                    ]
                elif qn == 3:
                    options = [
                        f"[{clock_label}] 第{quarter}クォーター開始です。スコアは{score_text}。後半戦のスタートです。",
                        f"[{clock_label}] 第{quarter}クォーターが始まります。スコアは{score_text}。",
                        f"[{clock_label}] 後半に入ります。スコアは{score_text}。",
                    ]
                elif qn == 4:
                    options = [
                        f"[{clock_label}] 第{quarter}クォーター開始です。スコアは{score_text}。",
                        f"[{clock_label}] 最終クォーターです。スコアは{score_text}。",
                        f"[{clock_label}] 第{quarter}クォーターが始まります。スコアは{score_text}。",
                        f"[{clock_label}] 残り10分。スコアは{score_text}。",
                    ]
                else:
                    options = [
                        f"[{clock_label}] 第{quarter}クォーター開始です。スコアは{score_text}。",
                        f"[{clock_label}] 第{quarter}クォーターが始まります。スコアは{score_text}。",
                    ]
            seed = int(event.get("possession_no", 0) or 0) + int(event.get("quarter", 0) or 0)
            return self._commentary_pick(options, seed)

        if event_type == "quarter_end":
            if not meta.get("is_overtime") and int(quarter or 0) >= 4:
                return ""
            state_text = self._build_score_state_text(event, event_index)
            if meta.get("is_overtime"):
                return f"[{clock_label}] 延長終了。スコアは{score_text}。{state_text}"
            return f"[{clock_label}] 第{quarter}クォーター終了。スコアは{score_text}。{state_text}"

        if event_type == "game_end":
            state_text = self._build_game_end_state_text(event, event_index)
            return f"[{clock_label}] 試合終了。最終スコアは{score_text}。{state_text}"

        return ""

    def _build_commentary_text(self, event: Dict, event_index: Optional[int] = None) -> Optional[str]:
        event_type = event.get("event_type", "unknown")
        primary = self._get_event_player_name(event, "primary_player_name")
        secondary = event.get("secondary_player_name")
        score_text = f'{event.get("home_score", 0)}-{event.get("away_score", 0)}'
        clock_label = self._event_clock_label(event)

        if event_index is None:
            try:
                event_index = self.play_by_play_log.index(event)
            except ValueError:
                event_index = 0

        if event_type in {"quarter_start", "quarter_end", "game_end"}:
            return self._build_quarter_transition_text(event, event_index)

        seed = int(event.get("possession_no", 0) or 0) + int(event.get("clock_seconds", 0) or 0)

        if event_type == "made_3":
            if secondary:
                options = [
                    f"[{clock_label}] {primary}が3ポイント成功。{secondary}のアシストです。スコアは{score_text}。",
                    f"[{clock_label}] {secondary}からつないで{primary}が3ポイントを沈めました。スコアは{score_text}。",
                    f"[{clock_label}] {primary}が外から決め切りました。{secondary}が好アシスト。スコアは{score_text}。",
                    f"[{clock_label}] {primary}が外角から狙い澄まして3点。{secondary}は見事なパスを送りました。スコアは{score_text}。",
                    f"[{clock_label}] {secondary}が時間を作った。{primary}が3ポイントを沈めます。スコアは{score_text}。",
                ]
            else:
                options = [
                    f"[{clock_label}] {primary}が3ポイント成功。スコアは{score_text}。",
                    f"[{clock_label}] {primary}が長距離砲を沈めました。スコアは{score_text}。",
                    f"[{clock_label}] {primary}、値千金の3ポイントです。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がプルアップから3点。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がキャッチアンドシュート。3ポイントが入ります。スコアは{score_text}。",
                ]
            base = self._commentary_pick(options, seed)
            context = self._build_scoring_context_text(event, event_index)
            return f"{base} {context}".strip()

        if event_type == "made_2":
            if secondary:
                options = [
                    f"[{clock_label}] {primary}が2ポイント成功。{secondary}のアシストです。スコアは{score_text}。",
                    f"[{clock_label}] {secondary}が切り崩して{primary}がフィニッシュ。スコアは{score_text}。",
                    f"[{clock_label}] {primary}が確実に2点を取りました。{secondary}の好判断です。スコアは{score_text}。",
                    f"[{clock_label}] {secondary}がディフェンスを引きつけ、{primary}がレイアップを落とします。スコアは{score_text}。",
                    f"[{clock_label}] {primary}が中距離を沈めました。{secondary}のパスがきいています。スコアは{score_text}。",
                ]
            else:
                options = [
                    f"[{clock_label}] {primary}が2ポイント成功。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がペイント内で決めました。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がきっちり加点。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がドライブから2点。スコアは{score_text}。",
                    f"[{clock_label}] {primary}がターンアラウンドで決めました。スコアは{score_text}。",
                ]
            base = self._commentary_pick(options, seed)
            context = self._build_scoring_context_text(event, event_index)
            return f"{base} {context}".strip()

        if event_type == "made_ft":
            options = [
                f"[{clock_label}] {primary}がフリースロー成功。スコアは{score_text}。",
                f"[{clock_label}] {primary}が落ち着いてフリースローを沈めます。スコアは{score_text}。",
                f"[{clock_label}] {primary}が1点を積み上げました。スコアは{score_text}。",
                f"[{clock_label}] {primary}がラインを確実にこなします。スコアは{score_text}。",
            ]
            base = self._commentary_pick(options, seed)
            context = self._build_scoring_context_text(event, event_index)
            return f"{base} {context}".strip()

        if event_type == "miss_3":
            options = [
                f"[{clock_label}] {primary}の3ポイントは外れました。",
                f"[{clock_label}] {primary}が外から狙いましたが決まりません。",
                f"[{clock_label}] {primary}のロングレンジはリングに嫌われました。",
                f"[{clock_label}] {primary}が3ポイントを放ちましたが、これは外れ。",
            ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] {primary}が勝負の3ポイントを放ちましたが、これは決まりません。")
            base = self._commentary_pick(options, seed)
            tail = self._build_miss_context_tail(event, event_index)
            return f"{base} {tail}".strip() if tail else base

        if event_type == "miss_2":
            options = [
                f"[{clock_label}] {primary}のシュートは外れました。",
                f"[{clock_label}] {primary}が中でねじ込みにいきましたが決め切れません。",
                f"[{clock_label}] {primary}のアタックは惜しくもノーゴール。",
                f"[{clock_label}] {primary}がレイアップを放ちましたが、リングに届きません。",
            ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] {primary}が終盤のシュートを託されましたが、ここは外れました。")
            base = self._commentary_pick(options, seed)
            tail = self._build_miss_context_tail(event, event_index)
            return f"{base} {tail}".strip() if tail else base

        if event_type == "miss_ft":
            options = [
                f"[{clock_label}] {primary}のフリースローは外れました。",
                f"[{clock_label}] {primary}、フリースローを決め切れません。",
                f"[{clock_label}] {primary}のフリースローは得点になりません。",
                f"[{clock_label}] {primary}のフリースローはリングを外れました。",
            ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] {primary}がフリースローを落とします。終盤の重い一投でした。")
            base = self._commentary_pick(options, seed)
            tail = self._build_miss_context_tail(event, event_index)
            return f"{base} {tail}".strip() if tail else base

        if event_type == "off_rebound":
            options = [
                f"[{clock_label}] {primary}がオフェンスリバウンド。攻撃継続です。",
                f"[{clock_label}] {primary}が執念のオフェンスリバウンドをもぎ取りました。",
                f"[{clock_label}] {primary}がこぼれ球を回収。もう一度チャンスです。",
                f"[{clock_label}] {primary}がセカンドチャンスを作ります。",
            ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] {primary}が終盤の大事なオフェンスリバウンド。")
            return self._commentary_pick(options, seed)

        if event_type == "def_rebound":
            options = [
                f"[{clock_label}] {primary}がディフェンスリバウンドを確保。",
                f"[{clock_label}] {primary}がしっかり守ってリバウンドを回収しました。",
                f"[{clock_label}] {primary}がボールを収めて攻守交代です。",
                f"[{clock_label}] {primary}がリバウンドを握り、カウンターのきっかけを作ります。",
            ]
            return self._commentary_pick(options, seed)

        if event_type == "steal":
            if secondary:
                options = [
                    f"[{clock_label}] {secondary}がスティール。{primary}からボールを奪いました。",
                    f"[{clock_label}] {secondary}が読み切ってスティール。{primary}のドリブルを止めます。",
                    f"[{clock_label}] {secondary}が鋭い手を出してスティール成功です。",
                    f"[{clock_label}] {secondary}がパスコースを断ち切りました。",
                ]
            else:
                options = [
                    f"[{clock_label}] スティールが決まりました。",
                    f"[{clock_label}] 守備がボールを引っかけました。",
                ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] 終盤のスティール。流れが大きく動きます。")
            return self._commentary_pick(options, seed)

        if event_type == "block":
            if secondary:
                options = [
                    f"[{clock_label}] {secondary}がブロック。{primary}のシュートを止めました。",
                    f"[{clock_label}] {secondary}が空中戦を制してブロック成功。",
                    f"[{clock_label}] {secondary}が{primary}のフィニッシュを叩き落としました。",
                    f"[{clock_label}] {secondary}がタイミングよく跳び、{primary}を封じます。",
                ]
            else:
                options = [
                    f"[{clock_label}] ブロックが決まりました。",
                    f"[{clock_label}] 強烈なブロックが飛び出しました。",
                ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] 終盤のブロック。会場がどよめきます。")
            return self._commentary_pick(options, seed)

        if event_type == "turnover":
            options = [
                f"[{clock_label}] {primary}がターンオーバー。",
                f"[{clock_label}] {primary}、ここはボールを失いました。",
                f"[{clock_label}] {primary}のプレーがミスにつながります。",
                f"[{clock_label}] {primary}がパスを切られました。",
            ]
            if self._is_clutch_time(event):
                options.append(f"[{clock_label}] {primary}に痛いターンオーバー。終盤で大きなミスです。")
            return self._commentary_pick(options, seed)

        if event_type == "substitution":
            player_out = event.get("primary_player_name")
            player_in = event.get("secondary_player_name")
            if player_out and player_in:
                options = [
                    f"[{clock_label}] 交代です。{player_out}に代わって{player_in}が入ります。",
                    f"[{clock_label}] ベンチが動きます。{player_out}が下がって{player_in}を投入。",
                ]
                return self._commentary_pick(options, seed)
            return f"[{clock_label}] 交代がありました。"

        return None

    def get_commentary_entries(self) -> List[Dict]:
        entries: List[Dict] = []
        for idx, event in enumerate(self.play_by_play_log):
            text = self._build_commentary_text(event, event_index=idx)
            if not text:
                continue
            entry = {
                "index": len(entries),
                "source_event_index": idx,
                "quarter": event.get("quarter"),
                "clock_seconds": event.get("clock_seconds"),
                "event_type": event.get("event_type"),
                "text": text,
                "home_score": event.get("home_score", 0),
                "away_score": event.get("away_score", 0),
                "primary_player_name": event.get("primary_player_name"),
                "secondary_player_name": event.get("secondary_player_name"),
            }
            entries.append(entry)
        self.commentary_log = entries
        return entries


    def get_commentary_lines(self) -> List[str]:
        return [entry["text"] for entry in self.get_commentary_entries()]

    def reset_commentary_cursor(self) -> None:
        self.commentary_index = 0

    def get_commentary_count(self) -> int:
        return len(self.get_commentary_entries())

    def get_commentary_entry_at(self, index: int) -> Optional[Dict]:
        entries = self.get_commentary_entries()
        if index < 0 or index >= len(entries):
            return None
        return entries[index]

    def get_next_commentary_entry(self) -> Optional[Dict]:
        entry = self.get_commentary_entry_at(self.commentary_index)
        if entry is None:
            return None
        self.commentary_index += 1
        return entry

    def peek_next_commentary_entry(self) -> Optional[Dict]:
        return self.get_commentary_entry_at(self.commentary_index)

    def _print_commentary_preview(self, preview_count: int = 8) -> None:
        commentary_entries = self.get_commentary_entries()
        commentary_lines = [entry["text"] for entry in commentary_entries]
        total_lines = len(commentary_lines)

        print("[COMMENTARY] Preview")
        print(f"[COMMENTARY] total_lines={total_lines}")
        print(f"[COMMENTARY] sequential_access_ready={'yes' if total_lines > 0 else 'no'}")

        if total_lines == 0:
            print("[COMMENTARY] no commentary lines")
            return

        head_count = min(preview_count, total_lines)
        tail_count = min(preview_count, total_lines)

        print(f"[COMMENTARY] first_{head_count}")
        for line in commentary_lines[:head_count]:
            print(f"  {line}")

        print(f"[COMMENTARY] last_{tail_count}")
        for line in commentary_lines[-tail_count:]:
            print(f"  {line}")

    def _is_play_terminator_event(self, event_type: str) -> bool:
        return event_type in {
            "made_2",
            "made_3",
            "made_ft",
            "miss_ft",
            "turnover",
            "def_rebound",
            "quarter_end",
            "game_end",
        }

    def _classify_play_result_type(self, events: List[Dict]) -> str:
        event_types = [event.get("event_type", "unknown") for event in events]

        if not event_types:
            return "empty_play"

        if "game_end" in event_types:
            return "game_end"
        if "quarter_end" in event_types:
            return "quarter_end"
        if "turnover" in event_types:
            return "turnover"
        if "steal" in event_types and "turnover" not in event_types:
            return "steal"
        if "made_3" in event_types:
            return "made_3"
        if "made_2" in event_types:
            return "made_2"
        if "made_ft" in event_types:
            return "made_ft"
        if "block" in event_types and "def_rebound" in event_types:
            return "block_def_rebound"
        if "miss_3" in event_types and "def_rebound" in event_types:
            return "miss_3_def_rebound"
        if "miss_2" in event_types and "def_rebound" in event_types:
            return "miss_2_def_rebound"
        if "miss_3" in event_types and "off_rebound" in event_types:
            return "miss_3_off_rebound_continue"
        if "miss_2" in event_types and "off_rebound" in event_types:
            return "miss_2_off_rebound_continue"
        if "quarter_start" in event_types:
            return "quarter_start"
        return event_types[-1]

    def _build_play_commentary_text(self, events: List[Dict]) -> str:
        lines = []
        for event in events:
            text = self._build_commentary_text(event)
            if text:
                lines.append(text)
        return " ".join(lines)

    def _extract_play_roles(self, events: List[Dict]) -> Dict[str, Optional[str]]:
        roles: Dict[str, Optional[str]] = {
            "initial_shooter_name": None,
            "final_shooter_name": None,
            "initial_rebounder_name": None,
            "final_rebounder_name": None,
            "off_rebounder_name": None,
            "def_rebounder_name": None,
            "assister_name": None,
            "stealer_name": None,
            "turnover_player_name": None,
            "blocker_name": None,
            "blocked_player_name": None,
            "scorer_name": None,
            "free_throw_shooter_name": None,
            "shooter_name": None,
            "rebounder_name": None,
            "finish_type": None,
        }

        for event in events:
            event_type = event.get("event_type", "unknown")
            primary = event.get("primary_player_name")
            secondary = event.get("secondary_player_name")

            if event_type in {"made_2", "made_3", "miss_2", "miss_3"} and primary:
                if roles["initial_shooter_name"] is None:
                    roles["initial_shooter_name"] = primary
                roles["final_shooter_name"] = primary
                roles["shooter_name"] = primary

            if event_type in {"made_2", "made_3"}:
                if primary:
                    roles["scorer_name"] = primary
                if secondary:
                    roles["assister_name"] = secondary
                if event_type == "made_2":
                    finish_type = (event.get("meta") or {}).get("finish_type")
                    if finish_type:
                        roles["finish_type"] = finish_type

            if event_type in {"made_ft", "miss_ft"} and primary:
                if roles["free_throw_shooter_name"] is None:
                    roles["free_throw_shooter_name"] = primary
                roles["final_shooter_name"] = primary
                roles["shooter_name"] = primary
                if event_type == "made_ft":
                    roles["scorer_name"] = primary

            if event_type == "off_rebound" and primary:
                if roles["initial_rebounder_name"] is None:
                    roles["initial_rebounder_name"] = primary
                roles["final_rebounder_name"] = primary
                roles["off_rebounder_name"] = primary
                roles["rebounder_name"] = primary

            if event_type == "def_rebound" and primary:
                if roles["initial_rebounder_name"] is None:
                    roles["initial_rebounder_name"] = primary
                roles["final_rebounder_name"] = primary
                roles["def_rebounder_name"] = primary
                roles["rebounder_name"] = primary

            if event_type == "steal":
                if primary and roles["turnover_player_name"] is None:
                    roles["turnover_player_name"] = primary
                if secondary:
                    roles["stealer_name"] = secondary

            if event_type == "turnover" and primary:
                if roles["turnover_player_name"] is None:
                    roles["turnover_player_name"] = primary

            if event_type == "block":
                if primary:
                    roles["blocked_player_name"] = primary
                if secondary:
                    roles["blocker_name"] = secondary

        return roles

    def _resolve_play_primary_secondary(self, result_type: str, roles: Dict[str, Optional[str]]) -> Tuple[Optional[str], Optional[str]]:
        if result_type == "made_3":
            return roles.get("scorer_name"), roles.get("assister_name")
        if result_type == "made_2":
            return roles.get("scorer_name"), roles.get("assister_name")
        if result_type == "made_ft":
            return roles.get("free_throw_shooter_name"), None
        if result_type in {"miss_3_def_rebound", "miss_2_def_rebound"}:
            return roles.get("final_shooter_name"), roles.get("def_rebounder_name")
        if result_type in {"miss_3_off_rebound_continue", "miss_2_off_rebound_continue"}:
            return roles.get("final_shooter_name"), roles.get("off_rebounder_name")
        if result_type == "block_def_rebound":
            return roles.get("blocked_player_name"), roles.get("blocker_name") or roles.get("def_rebounder_name")
        if result_type == "turnover":
            return roles.get("turnover_player_name"), roles.get("stealer_name")
        if result_type == "steal":
            return roles.get("stealer_name"), roles.get("turnover_player_name")
        return None, None

    def _build_play_sequence_entry(self, play_no: int, events: List[Dict]) -> Optional[Dict]:
        if not events:
            return None

        first_event = events[0]
        last_event = events[-1]
        result_type = self._classify_play_result_type(events)
        roles = self._extract_play_roles(events)
        primary_name, secondary_name = self._resolve_play_primary_secondary(result_type, roles)

        return {
            "play_no": play_no,
            "quarter": first_event.get("quarter"),
            "start_clock_seconds": first_event.get("clock_seconds"),
            "end_clock_seconds": last_event.get("clock_seconds"),
            "offense_team_id": first_event.get("offense_team_id"),
            "defense_team_id": first_event.get("defense_team_id"),
            "result_type": result_type,
            "primary_player_name": primary_name,
            "secondary_player_name": secondary_name,
            "initial_shooter_name": roles.get("initial_shooter_name"),
            "final_shooter_name": roles.get("final_shooter_name"),
            "initial_rebounder_name": roles.get("initial_rebounder_name"),
            "final_rebounder_name": roles.get("final_rebounder_name"),
            "off_rebounder_name": roles.get("off_rebounder_name"),
            "def_rebounder_name": roles.get("def_rebounder_name"),
            "shooter_name": roles.get("shooter_name"),
            "assister_name": roles.get("assister_name"),
            "rebounder_name": roles.get("rebounder_name"),
            "stealer_name": roles.get("stealer_name"),
            "turnover_player_name": roles.get("turnover_player_name"),
            "blocker_name": roles.get("blocker_name"),
            "blocked_player_name": roles.get("blocked_player_name"),
            "scorer_name": roles.get("scorer_name"),
            "free_throw_shooter_name": roles.get("free_throw_shooter_name"),
            "finish_type": roles.get("finish_type"),
            "home_score": last_event.get("home_score", 0),
            "away_score": last_event.get("away_score", 0),
            "events": [dict(event) for event in events],
            "commentary_text": self._build_play_commentary_text(events),
            "is_transition_play": False,
            "transition_trigger_type": None,
            "transition_action": None,
            "transition_origin_player_name": None,
            "transition_finisher_name": roles.get("scorer_name") or roles.get("final_shooter_name"),
        }

    def _annotate_transition_context(self, plays: List[Dict]) -> None:
        if not plays:
            return

        scoring_like_results = {
            "made_2",
            "made_3",
            "made_ft",
            "miss_2_def_rebound",
            "miss_3_def_rebound",
            "miss_2_off_rebound_continue",
            "miss_3_off_rebound_continue",
            "block_def_rebound",
        }

        for i, play in enumerate(plays):
            play["is_transition_play"] = False
            play["transition_trigger_type"] = None
            play["transition_action"] = None
            play["transition_origin_player_name"] = None
            if play.get("transition_finisher_name") is None:
                play["transition_finisher_name"] = play.get("scorer_name") or play.get("final_shooter_name")

            if i == 0:
                continue

            prev = plays[i - 1]
            if play.get("quarter") != prev.get("quarter"):
                continue
            if play.get("offense_team_id") != prev.get("defense_team_id"):
                continue
            if play.get("result_type") not in scoring_like_results:
                continue

            prev_result = prev.get("result_type")
            trigger_type = None
            transition_action = None
            origin_name = None

            if prev_result == "turnover":
                if prev.get("stealer_name"):
                    trigger_type = "steal"
                    origin_name = prev.get("stealer_name")
                else:
                    trigger_type = "turnover"
                    origin_name = prev.get("turnover_player_name")
                transition_action = "counter"
            elif prev_result == "steal":
                trigger_type = "steal"
                transition_action = "counter"
                origin_name = prev.get("stealer_name")
            elif prev_result == "block_def_rebound":
                trigger_type = "block"
                transition_action = "counter"
                origin_name = prev.get("blocker_name") or prev.get("def_rebounder_name")
            elif prev_result in {"miss_2_def_rebound", "miss_3_def_rebound"}:
                next_events = play.get("events") if isinstance(play.get("events"), list) else []
                next_result = play.get("result_type")
                scorer_pos = str(play.get("scorer_position") or play.get("primary_player_position") or "").upper()
                has_assist = bool(play.get("assister_name") or play.get("secondary_player_name"))
                quick_finish = next_result in {"made_2", "made_3", "miss_2", "miss_3"} and len(next_events) <= 2
                perimeter_or_wing = scorer_pos in {"PG", "SG", "SF"}

                if quick_finish and (perimeter_or_wing or has_assist):
                    trigger_type = "def_rebound"
                    transition_action = "primary_break"
                    origin_name = prev.get("def_rebounder_name")

            if trigger_type is None:
                continue

            play["is_transition_play"] = True
            play["transition_trigger_type"] = trigger_type
            play["transition_action"] = transition_action
            play["transition_origin_player_name"] = origin_name
            if play.get("transition_finisher_name") is None:
                play["transition_finisher_name"] = play.get("scorer_name") or play.get("final_shooter_name")

    def get_play_sequence_log(self) -> List[Dict]:
        plays: List[Dict] = []
        current_events: List[Dict] = []

        for event in self.play_by_play_log:
            event_type = event.get("event_type", "unknown")

            if event_type == "quarter_start":
                if current_events:
                    entry = self._build_play_sequence_entry(len(plays), current_events)
                    if entry is not None:
                        plays.append(entry)
                    current_events = []
                entry = self._build_play_sequence_entry(len(plays), [event])
                if entry is not None:
                    plays.append(entry)
                continue

            if event_type == "substitution":
                continue

            current_events.append(event)

            if self._is_play_terminator_event(event_type):
                entry = self._build_play_sequence_entry(len(plays), current_events)
                if entry is not None:
                    plays.append(entry)
                current_events = []

        if current_events:
            entry = self._build_play_sequence_entry(len(plays), current_events)
            if entry is not None:
                plays.append(entry)

        self._annotate_transition_context(plays)
        self.play_sequence_log = plays
        return plays

    def reset_play_cursor(self) -> None:
        self.play_sequence_index = 0

    def get_play_count(self) -> int:
        return len(self.get_play_sequence_log())

    def get_play_at(self, index: int) -> Optional[Dict]:
        plays = self.get_play_sequence_log()
        if index < 0 or index >= len(plays):
            return None
        return plays[index]

    def get_next_play(self) -> Optional[Dict]:
        play = self.get_play_at(self.play_sequence_index)
        if play is None:
            return None
        self.play_sequence_index += 1
        return play

    def peek_next_play(self) -> Optional[Dict]:
        return self.get_play_at(self.play_sequence_index)

    def _format_play_sequence_for_debug(self, play: Dict) -> str:
        quarter = play.get("quarter", "?")
        clock_seconds = int(play.get("end_clock_seconds", 0) or 0)
        minutes = max(0, clock_seconds) // 60
        seconds = max(0, clock_seconds) % 60
        result_type = play.get("result_type", "unknown")
        primary = play.get("primary_player_name") or "-"
        secondary = play.get("secondary_player_name") or "-"
        score = f'{play.get("home_score", 0)}-{play.get("away_score", 0)}'
        transition_action = play.get("transition_action") or "-"
        trigger_type = play.get("transition_trigger_type") or "-"
        return (
            f"Play#{play.get('play_no', '?'):>3} | Q{quarter} {minutes:02d}:{seconds:02d} | "
            f"{result_type:<24} | primary={primary} | secondary={secondary} | score={score} "
            f"| transition={transition_action} | trigger={trigger_type}"
        )

    def _print_play_sequence_preview(self, preview_count: int = 5) -> None:
        plays = self.get_play_sequence_log()
        total_plays = len(plays)

        print("[PLAY] Preview")
        print(f"[PLAY] total_plays={total_plays}")
        print(f"[PLAY] sequential_access_ready={'yes' if total_plays > 0 else 'no'}")

        if total_plays == 0:
            print("[PLAY] no play sequence data")
            return

        head_count = min(preview_count, total_plays)
        tail_count = min(preview_count, total_plays)

        print(f"[PLAY] first_{head_count}")
        for play in plays[:head_count]:
            print(f"  {self._format_play_sequence_for_debug(play)}")

        print(f"[PLAY] last_{tail_count}")
        for play in plays[-tail_count:]:
            print(f"  {self._format_play_sequence_for_debug(play)}")

    COMPETITION_RULES = {
        "regular_season": {
            "active": {
                "foreign_max": LEAGUE_ROSTER_FOREIGN_CAP,
                "special_max": LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
            "on_court": {
                "foreign_max": LEAGUE_ONCOURT_FOREIGN_CAP,
                "special_max": LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
        },
        "playoff": {
            "active": {
                "foreign_max": LEAGUE_ROSTER_FOREIGN_CAP,
                "special_max": LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
            "on_court": {
                "foreign_max": LEAGUE_ONCOURT_FOREIGN_CAP,
                "special_max": LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
        },
        "final_boss": {
            "active": {
                "foreign_max": LEAGUE_ROSTER_FOREIGN_CAP,
                "special_max": LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
            "on_court": {
                "foreign_max": LEAGUE_ONCOURT_FOREIGN_CAP,
                "special_max": LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
                "asia_as_foreign": False,
                "special_label": "Asia/帰化",
            },
        },
        "emperor_cup": {
            "active": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": True, "special_label": "帰化"},
            "on_court": {"foreign_max": 1, "special_max": 1, "asia_as_foreign": True, "special_label": "帰化"},
        },
        "easl": {
            "active": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
            "on_court": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
        },
        "asia_cup": {
            "active": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
            "on_court": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
        },
        "asia_cl": {
            "active": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
            "on_court": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
        },
        "intercontinental": {
            "active": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
            "on_court": {"foreign_max": 2, "special_max": 1, "asia_as_foreign": False, "special_label": "帰化/アジア"},
        },
    }

    def _normalize_competition_type(self, competition_type: Optional[str]) -> str:
        normalized = str(competition_type or "regular_season").strip().lower()
        return normalized if normalized in self.COMPETITION_RULES else "regular_season"

    def _get_competition_rule(self, phase: str) -> Dict[str, object]:
        rules = self.COMPETITION_RULES.get(self.competition_type, self.COMPETITION_RULES["regular_season"])
        if phase in rules:
            return rules[phase]
        return self.COMPETITION_RULES["regular_season"][phase]

    def _get_player_regulation_bucket(self, player: Player, phase: str) -> str:
        nat = getattr(player, "nationality", "Japan")
        rule = self._get_competition_rule(phase)

        if nat == "Foreign":
            return "foreign"
        if nat == "Naturalized":
            return "special"
        if nat == "Asia":
            return "foreign" if bool(rule.get("asia_as_foreign", False)) else "special"
        return "domestic"

    def _count_regulation_slots(self, players: List[Player], phase: str) -> Tuple[int, int]:
        foreign = 0
        special = 0
        for player in players:
            bucket = self._get_player_regulation_bucket(player, phase)
            if bucket == "foreign":
                foreign += 1
            elif bucket == "special":
                special += 1
        return foreign, special

    def _get_regulation_log_labels(self, phase: str) -> Tuple[str, str]:
        rule = self._get_competition_rule(phase)
        foreign_label = "外国籍扱い" if bool(rule.get("asia_as_foreign", False)) else "外国籍"
        special_label = str(rule.get("special_label", "Asia/帰化"))
        return foreign_label, special_label

    def _is_foreign(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") == "Foreign"

    def _is_asia_or_naturalized(self, player: Player) -> bool:
        return getattr(player, "nationality", "Japan") in ("Asia", "Naturalized")

    def _count_foreign(self, players: List[Player], phase: str = "on_court") -> int:
        foreign, _ = self._count_regulation_slots(players, phase)
        return foreign

    def _count_asia_nat(self, players: List[Player], phase: str = "on_court") -> int:
        _, special = self._count_regulation_slots(players, phase)
        return special

    def _print_active_roster(self, team: Team, active: List[Player], inactive: List[Player]):
        foreign = self._count_foreign(active, phase="active")
        asia_nat = self._count_asia_nat(active, phase="active")
        foreign_label, special_label = self._get_regulation_log_labels("active")

        inactive_names = ", ".join(p.name for p in inactive[:3]) if inactive else "None"

        print(
            f"[ACTIVE] {team.name} | 登録{len(active)}名 | "
            f"登録外:{inactive_names} | "
            f"{foreign_label}:{foreign} | {special_label}:{asia_nat}"
        )

    def _print_starting_five(self, team: Team, starters: List[Player]):
        foreign = self._count_foreign(starters, phase="on_court")
        asia_nat = self._count_asia_nat(starters, phase="on_court")
        foreign_label, special_label = self._get_regulation_log_labels("on_court")
        names = ", ".join(p.name for p in starters)

        print(
            f"[STARTERS] {team.name} | 5人 | "
            f"{foreign_label}:{foreign} | {special_label}:{asia_nat} | {names}"
        )

    def _select_active_roster(self, team: Team):
        players = [p for p in team.players if not p.is_injured() and not p.is_retired]

        # Youth callups (16〜18) are not part of the normal 13-man roster,
        # but can be registered for games when the team is in development mode.
        allow_youth = (
            getattr(team, "coach_style", "balanced") == "development"
            or getattr(team, "usage_policy", "balanced") == "development"
        )
        youth_pool = []
        if allow_youth:
            youth_pool = [
                p for p in (getattr(team, "youth_callups", []) or [])
                if not p.is_injured() and not p.is_retired
            ]

        players = sorted(players, key=lambda p: p.get_effective_ovr(), reverse=True)
        focus = str(getattr(team, "youth_policy_focus", "balanced") or "balanced")
        global_policy = str(getattr(team, "youth_policy_global", "balanced") or "balanced")

        def youth_sort_key(p: Player):
            pos = str(getattr(p, "position", "") or "")
            # v1: 方針に合わせて「選ぶ1人」を寄せる（能力配分は後で詰める）
            focus_bonus = 0
            if focus == "pg":
                focus_bonus = 4 if pos == "PG" else 1 if pos in {"SG"} else 0
            elif focus == "shooter":
                focus_bonus = 4 if pos in {"SG", "SF"} else 1 if pos in {"PG"} else 0
            elif focus == "big":
                focus_bonus = 4 if pos in {"C", "PF"} else 1 if pos in {"SF"} else 0
            elif focus == "defender":
                focus_bonus = 3 if pos in {"SF", "PF"} else 2 if pos in {"SG", "PG"} else 1 if pos == "C" else 0
            else:
                focus_bonus = 1

            # v1: 全体方針（technical/physical）も「候補の選ばれ方」にだけ反映
            # - technical: shoot/three/passing/iq 寄りの選手が少し優先される
            # - physical : stamina/drive/rebound/defense 寄りの選手が少し優先される
            skill_bonus = 0.0
            try:
                if global_policy == "technical":
                    skill_bonus = (
                        p.get_adjusted_attribute("shoot") * 0.04
                        + p.get_adjusted_attribute("three") * 0.03
                        + p.get_adjusted_attribute("passing") * 0.03
                        + p.get_adjusted_attribute("iq") * 0.02
                    )
                elif global_policy == "physical":
                    skill_bonus = (
                        p.get_adjusted_attribute("stamina") * 0.03
                        + p.get_adjusted_attribute("drive") * 0.03
                        + p.get_adjusted_attribute("rebound") * 0.02
                        + p.get_adjusted_attribute("defense") * 0.02
                    )
            except Exception:
                skill_bonus = 0.0

            return (
                focus_bonus,
                round(float(skill_bonus), 2),
                p.get_effective_ovr(),
                -int(getattr(p, "age", 18) or 18),
                str(getattr(p, "name", "")),
            )

        youth_pool = sorted(youth_pool, key=youth_sort_key, reverse=True)

        active = []
        rule = self._get_competition_rule("active")
        foreign_max = int(rule.get("foreign_max", 3))
        special_max = int(rule.get("special_max", 1))

        for p in players:
            if len(active) >= 12:
                break

            bucket = self._get_player_regulation_bucket(p, "active")
            current_foreign, current_special = self._count_regulation_slots(active, "active")

            if bucket == "foreign" and current_foreign >= foreign_max:
                continue
            if bucket == "special" and current_special >= special_max:
                continue

            active.append(p)

        # At most 1 youth callup can be registered (v1 safety).
        if allow_youth and youth_pool and len(active) >= 12:
            y = youth_pool[0]
            bucket = self._get_player_regulation_bucket(y, "active")
            current_foreign, current_special = self._count_regulation_slots(active, "active")
            can_add = True
            if bucket == "foreign" and current_foreign >= foreign_max:
                can_add = False
            if bucket == "special" and current_special >= special_max:
                can_add = False

            if can_add:
                # replace the lowest effective OVR player in active (never replace icon)
                replace_candidates = [p for p in active if not bool(getattr(p, "icon_locked", False))]
                if replace_candidates:
                    drop = min(replace_candidates, key=lambda p: p.get_effective_ovr())
                    active.remove(drop)
                    active.append(y)

        inactive = [p for p in players if p not in active]
        return active, inactive

    def _get_starting_five_from_players(self, players: List[Player]) -> List[Player]:
        sorted_players = sorted(players, key=lambda p: p.get_effective_ovr(), reverse=True)

        starters = []
        rule = self._get_competition_rule("on_court")
        foreign_max = int(rule.get("foreign_max", 2))
        special_max = int(rule.get("special_max", 1))

        for p in sorted_players:
            if len(starters) >= 5:
                break

            bucket = self._get_player_regulation_bucket(p, "on_court")
            current_foreign, current_special = self._count_regulation_slots(starters, "on_court")

            if bucket == "foreign" and current_foreign >= foreign_max:
                continue
            if bucket == "special" and current_special >= special_max:
                continue

            starters.append(p)

        if len(starters) < 5:
            for p in sorted_players:
                if p in starters:
                    continue
                starters.append(p)
                if len(starters) >= 5:
                    break

        return starters[:5]

    def _calculate_team_strength_from_players(self, team: Team, lineup: List[Player]) -> Tuple[float, float]:
        if not lineup:
            return 0.0, 0.0

        off = 0.0
        deff = 0.0

        for p in lineup:
            off += (
                p.get_adjusted_attribute("shoot") * 0.30 +
                p.get_adjusted_attribute("three") * 0.25 +
                p.get_adjusted_attribute("drive") * 0.20 +
                p.get_adjusted_attribute("passing") * 0.15 +
                p.get_adjusted_attribute("stamina") * 0.10
            )

            deff += (
                p.get_adjusted_attribute("defense") * 0.60 +
                p.get_adjusted_attribute("rebound") * 0.25 +
                p.get_adjusted_attribute("stamina") * 0.15
            )

        off /= len(lineup)
        deff /= len(lineup)

        coach_style = getattr(team, "coach_style", "balanced")
        if coach_style == "offense":
            off += 1.5
        elif coach_style == "defense":
            deff += 1.5
        elif coach_style == "development":
            off += 0.5
            deff += 0.5

        return off, deff

    def _get_total_possessions(self) -> int:
        base = 160

        strategy_pace_map = {
            "balanced": 0,
            "run_and_gun": 10,
            "three_point": 4,
            "defense": -8,
            "inside": -2,
        }

        coach_pace_map = {
            "balanced": 0,
            "offense": 4,
            "defense": -4,
            "development": 0,
        }

        home_strategy = getattr(self.home_team, "strategy", "balanced")
        away_strategy = getattr(self.away_team, "strategy", "balanced")
        home_coach = getattr(self.home_team, "coach_style", "balanced")
        away_coach = getattr(self.away_team, "coach_style", "balanced")

        home_adj = strategy_pace_map.get(home_strategy, 0) + coach_pace_map.get(home_coach, 0)
        away_adj = strategy_pace_map.get(away_strategy, 0) + coach_pace_map.get(away_coach, 0)

        total = base + home_adj + away_adj
        return max(140, min(180, total))

    def _get_quarter_lengths(self) -> List[int]:
        total = max(4, self.total_possessions)
        base = total // 4
        remainder = total % 4

        lengths = [base] * 4
        for i in range(remainder):
            lengths[i] += 1

        return lengths

    def _get_quarter_info(self, possession_index: int) -> Tuple[int, int, int]:
        lengths = self._get_quarter_lengths()

        running = 0
        for idx, q_len in enumerate(lengths):
            if possession_index < running + q_len:
                possession_in_quarter = possession_index - running + 1
                return idx + 1, possession_in_quarter, q_len
            running += q_len

        return 4, lengths[-1], lengths[-1]

    def _lineup_signature(self, lineup: List[Player]) -> List[str]:
        return [p.name for p in lineup]

    def _log_substitutions(
        self,
        team: Team,
        old_lineup: List[Player],
        new_lineup: List[Player],
        possession_index: int
    ):
        old_names = {p.name for p in old_lineup}
        new_names = {p.name for p in new_lineup}

        outs = [p for p in old_lineup if p.name not in new_names]
        ins = [p for p in new_lineup if p.name not in old_names]

        if not outs and not ins:
            return

        pair_count = min(len(outs), len(ins))
        changes = []

        for i in range(pair_count):
            changes.append(f"{outs[i].name}→{ins[i].name}")

        if len(outs) > pair_count:
            for p in outs[pair_count:]:
                changes.append(f"{p.name}→OUT")

        if len(ins) > pair_count:
            for p in ins[pair_count:]:
                changes.append(f"IN→{p.name}")

        quarter, possession_in_quarter, possessions_per_quarter = self._get_quarter_info(possession_index)

        print(
            f"[SUB][Q{quarter} {possession_in_quarter}/{possessions_per_quarter}] "
            f"{team.name} | " + ", ".join(changes)
        )

        self._record_event(
            event_type="substitution",
            offense_team=team,
            description_key="substitution",
            possession_index=possession_index,
            meta={
                "team_name": team.name,
                "changes": list(changes),
            },
        )

    def _validate_lineup(
        self,
        lineup: List[Player],
        fallback: List[Player],
        team: Team
    ) -> List[Player]:
        if not lineup or len(lineup) < 5:
            return fallback

        unique = []
        seen = set()
        for p in lineup:
            if p.name in seen:
                continue
            unique.append(p)
            seen.add(p.name)

        if len(unique) < 5:
            pool = self.home_active_players if team == self.home_team else self.away_active_players
            for p in pool:
                if p.name in seen:
                    continue
                unique.append(p)
                seen.add(p.name)
                if len(unique) >= 5:
                    break

        unique = unique[:5]

        foreign = self._count_foreign(unique, phase="on_court")
        asia_nat = self._count_asia_nat(unique, phase="on_court")
        rule = self._get_competition_rule("on_court")
        foreign_max = int(rule.get("foreign_max", 2))
        special_max = int(rule.get("special_max", 1))

        if foreign > foreign_max or asia_nat > special_max:
            return fallback

        return unique

    def _get_rotation_lineup(
        self,
        rotation_obj: RotationSystem,
        current_lineup: List[Player],
        team: Team,
        possession_index: int
    ) -> List[Player]:
        quarter, possession_in_quarter, possessions_per_quarter = self._get_quarter_info(possession_index)

        try:
            rotation_obj.start_quarter(quarter)
        except Exception:
            pass

        try:
            lineup = rotation_obj.get_lineup(
                current_lineup=current_lineup,
                possession=possession_index,
                total_possessions=self.total_possessions,
                quarter=quarter,
                possession_in_quarter=possession_in_quarter,
                possessions_per_quarter=possessions_per_quarter,
                score_diff=self.home_score - self.away_score
            )
        except Exception:
            return current_lineup

        return self._validate_lineup(lineup, current_lineup, team)

    def _maybe_update_rotations(self, possession_index: int):
        new_home_lineup = self._get_rotation_lineup(
            self.home_rotation,
            self.home_current_lineup,
            self.home_team,
            possession_index
        )
        if self._lineup_signature(new_home_lineup) != self._lineup_signature(self.home_current_lineup):
            self._log_substitutions(
                self.home_team,
                self.home_current_lineup,
                new_home_lineup,
                possession_index
            )
            self.home_current_lineup = list(new_home_lineup)

        new_away_lineup = self._get_rotation_lineup(
            self.away_rotation,
            self.away_current_lineup,
            self.away_team,
            possession_index
        )
        if self._lineup_signature(new_away_lineup) != self._lineup_signature(self.away_current_lineup):
            self._log_substitutions(
                self.away_team,
                self.away_current_lineup,
                new_away_lineup,
                possession_index
            )
            self.away_current_lineup = list(new_away_lineup)

    def _get_position_stat_weights(self, player: Player) -> Dict[str, float]:
        pos = getattr(player, "position", "SF")

        table = {
            "PG": {
                "score": 0.90,
                "three_score": 0.98,
                "two_score": 0.88,
                "ft_score": 0.92,
                "assist": 1.72,
                "rebound": 0.42,
                "block": 0.10,
                "steal": 1.28,
            },
            "SG": {
                "score": 1.22,
                "three_score": 1.24,
                "two_score": 1.15,
                "ft_score": 1.12,
                "assist": 1.18,
                "rebound": 0.58,
                "block": 0.20,
                "steal": 1.10,
            },
            "SF": {
                "score": 1.03,
                "three_score": 1.03,
                "two_score": 1.04,
                "ft_score": 1.02,
                "assist": 0.95,
                "rebound": 0.88,
                "block": 0.55,
                "steal": 0.96,
            },
            "PF": {
                "score": 0.98,
                "three_score": 0.82,
                "two_score": 1.12,
                "ft_score": 1.02,
                "assist": 0.72,
                "rebound": 1.20,
                "block": 1.38,
                "steal": 0.78,
            },
            "C": {
                "score": 0.96,
                "three_score": 0.48,
                "two_score": 1.24,
                "ft_score": 1.00,
                "assist": 0.50,
                "rebound": 1.38,
                "block": 1.82,
                "steal": 0.64,
            },
        }
        return table.get(pos, table["SF"])

    def _position_weight(self, player: Player, stat_type: str) -> float:
        weights = self._get_position_stat_weights(player)
        return weights.get(stat_type, 1.0)

    def _pick_assister(self, offense_lineup: List[Player], shooter: Player) -> Optional[Player]:
        passers = [p for p in offense_lineup if p != shooter]
        if not passers:
            return None

        weights = []
        for p in passers:
            passing = p.get_adjusted_attribute("passing")
            drive = p.get_adjusted_attribute("drive")
            shoot = p.get_adjusted_attribute("shoot")
            ovr = p.get_effective_ovr()

            weight = 0.0
            weight += passing * 1.70
            weight += drive * 0.40
            weight += shoot * 0.15
            weight += max(0, ovr - 50) * 0.60
            weight *= self._position_weight(p, "assist")

            weights.append(max(1, int(weight)))

        return random.choices(passers, weights=weights, k=1)[0]

    def _pick_blocker(self, defense_lineup: List[Player], is_three: bool = False) -> Player:
        weights = []
        for p in defense_lineup:
            defense_attr = p.get_adjusted_attribute("defense")
            rebound_attr = p.get_adjusted_attribute("rebound")
            stamina_attr = p.get_adjusted_attribute("stamina")
            pos = getattr(p, "position", "SF")

            weight = 0.0
            weight += defense_attr * 0.95
            weight += rebound_attr * 0.85
            weight += stamina_attr * 0.20

            if pos == "C":
                weight += 28
            elif pos == "PF":
                weight += 18
            elif pos == "SF":
                weight += 5
            elif pos == "SG":
                weight -= 8
            elif pos == "PG":
                weight -= 14

            if is_three:
                if pos == "C":
                    weight -= 10
                elif pos == "PF":
                    weight -= 4
                elif pos in ("SG", "SF"):
                    weight += 2

            weight *= self._position_weight(p, "block")
            weights.append(max(1, int(weight)))

        return random.choices(defense_lineup, weights=weights, k=1)[0]

    def _pick_stealer(self, defense_lineup: List[Player]) -> Player:
        weights = []
        for p in defense_lineup:
            weight = (
                p.get_adjusted_attribute("defense") * 0.70 +
                p.get_adjusted_attribute("passing") * 0.10 +
                p.get_adjusted_attribute("stamina") * 0.20
            )
            weight *= self._position_weight(p, "steal")
            weights.append(max(1, int(weight)))
        return random.choices(defense_lineup, weights=weights, k=1)[0]

    def _pick_rebounder(self, lineup: List[Player], side: str) -> Player:
        weights = []
        for p in lineup:
            weight = p.get_adjusted_attribute("rebound")
            if side == "offense":
                weight += p.get_adjusted_attribute("drive") * 0.10
            else:
                weight += p.get_adjusted_attribute("defense") * 0.10
            weight *= self._position_weight(p, "rebound")
            weights.append(max(1, int(weight)))
        return random.choices(lineup, weights=weights, k=1)[0]

    def _get_lineup_profile(self, lineup: List[Player]) -> dict:
        if not lineup:
            return {
                "three": 50.0,
                "shoot": 50.0,
                "drive": 50.0,
                "passing": 50.0,
                "rebound": 50.0,
                "big_count": 0,
                "guard_count": 0,
            }

        three_avg = sum(p.get_adjusted_attribute("three") for p in lineup) / len(lineup)
        shoot_avg = sum(p.get_adjusted_attribute("shoot") for p in lineup) / len(lineup)
        drive_avg = sum(p.get_adjusted_attribute("drive") for p in lineup) / len(lineup)
        passing_avg = sum(p.get_adjusted_attribute("passing") for p in lineup) / len(lineup)
        rebound_avg = sum(p.get_adjusted_attribute("rebound") for p in lineup) / len(lineup)

        big_count = sum(1 for p in lineup if getattr(p, "position", "SF") in ("PF", "C"))
        guard_count = sum(1 for p in lineup if getattr(p, "position", "SF") in ("PG", "SG"))

        return {
            "three": three_avg,
            "shoot": shoot_avg,
            "drive": drive_avg,
            "passing": passing_avg,
            "rebound": rebound_avg,
            "big_count": big_count,
            "guard_count": guard_count,
        }

    def _get_assist_chance(
        self,
        offense_team: Team,
        offense_lineup: List[Player],
        shooter: Player,
        shot_profile: str,
        is_second_chance: bool = False
    ) -> float:
        if shot_profile == "ft":
            return 0.0

        profile = self._get_lineup_profile(offense_lineup)
        strategy = getattr(offense_team, "strategy", "balanced")
        coach_style = getattr(offense_team, "coach_style", "balanced")
        shooter_pos = getattr(shooter, "position", "SF")

        if shot_profile == "three":
            assist_rate = 0.68
        else:
            assist_rate = 0.57

        passing_push = (profile["passing"] - 65.0) * 0.0030
        assist_rate += passing_push

        if strategy == "balanced":
            assist_rate += 0.01
        elif strategy == "three_point":
            assist_rate += 0.05
        elif strategy == "inside":
            assist_rate += 0.03
        elif strategy == "run_and_gun":
            assist_rate -= 0.02
        elif strategy == "defense":
            assist_rate -= 0.01

        if coach_style == "offense":
            assist_rate += 0.03
        elif coach_style == "development":
            assist_rate += 0.01
        elif coach_style == "defense":
            assist_rate -= 0.01

        if shooter_pos == "PG":
            assist_rate -= 0.06
        elif shooter_pos == "SG":
            assist_rate += 0.01
        elif shooter_pos == "SF":
            assist_rate += 0.02
        elif shooter_pos in ("PF", "C"):
            assist_rate += 0.05

        if is_second_chance:
            assist_rate -= 0.14

        return max(0.28, min(0.82, assist_rate))

    def _get_shot_mix(
        self,
        offense_team: Team,
        defense_team: Team,
        offense_lineup: List[Player],
        defense_lineup: List[Player],
    ) -> Tuple[float, float, float]:
        offense_strategy = getattr(offense_team, "strategy", "balanced")
        offense_coach = getattr(offense_team, "coach_style", "balanced")
        defense_strategy = getattr(defense_team, "strategy", "balanced")
        defense_coach = getattr(defense_team, "coach_style", "balanced")

        off_profile = self._get_lineup_profile(offense_lineup)
        def_profile = self._get_lineup_profile(defense_lineup)

        three_cutoff = 0.35
        two_cutoff = 0.90
        shot_rate_adjust = 0.0

        if offense_strategy == "run_and_gun":
            three_cutoff += 0.04
            two_cutoff += 0.02
            shot_rate_adjust += 0.005
        elif offense_strategy == "three_point":
            three_cutoff += 0.10
            two_cutoff += 0.02
            shot_rate_adjust += 0.003
        elif offense_strategy == "inside":
            three_cutoff -= 0.08
            two_cutoff += 0.03
            shot_rate_adjust += 0.006
        elif offense_strategy == "defense":
            three_cutoff -= 0.03
            shot_rate_adjust -= 0.003

        if offense_coach == "offense":
            three_cutoff += 0.03
            two_cutoff += 0.01
            shot_rate_adjust += 0.004
        elif offense_coach == "defense":
            three_cutoff -= 0.02
            two_cutoff -= 0.01
        elif offense_coach == "development":
            three_cutoff -= 0.01
            shot_rate_adjust += 0.001

        if defense_strategy == "defense":
            shot_rate_adjust -= 0.010
        elif defense_strategy == "run_and_gun":
            shot_rate_adjust += 0.004

        if defense_coach == "defense":
            shot_rate_adjust -= 0.006
        elif defense_coach == "offense":
            shot_rate_adjust += 0.002

        three_push = (off_profile["three"] - 65.0) * 0.0025
        inside_push = ((off_profile["drive"] + off_profile["rebound"]) / 2 - 65.0) * 0.0018
        guard_push = (off_profile["guard_count"] - 2) * 0.015
        big_push = (off_profile["big_count"] - 2) * 0.015

        perimeter_defense_pressure = (def_profile["guard_count"] - 2) * 0.010
        paint_defense_pressure = (def_profile["big_count"] - 2) * 0.010

        three_cutoff += three_push + guard_push
        three_cutoff -= max(0.0, perimeter_defense_pressure)

        three_cutoff -= inside_push * 0.35
        three_cutoff -= max(0.0, big_push) * 0.01
        three_cutoff += min(0.0, big_push) * -0.005

        two_cutoff += inside_push + max(0.0, big_push) * 0.02
        two_cutoff -= max(0.0, paint_defense_pressure) * 0.01

        shot_rate_adjust += (off_profile["shoot"] - 65.0) * 0.0003
        shot_rate_adjust += (off_profile["passing"] - 65.0) * 0.0002

        three_cutoff = max(0.18, min(0.58, three_cutoff))
        two_cutoff = max(three_cutoff + 0.20, min(0.95, two_cutoff))
        shot_rate_adjust = max(-0.020, min(0.020, shot_rate_adjust))

        return three_cutoff, two_cutoff, shot_rate_adjust

    def _get_offense_rebound_rate(
        self,
        offense_team: Team,
        defense_team: Team,
        offense_lineup: List[Player],
        defense_lineup: List[Player],
        was_blocked: bool,
    ) -> float:
        offense_strategy = getattr(offense_team, "strategy", "balanced")
        offense_coach = getattr(offense_team, "coach_style", "balanced")
        defense_strategy = getattr(defense_team, "strategy", "balanced")
        defense_coach = getattr(defense_team, "coach_style", "balanced")

        off_profile = self._get_lineup_profile(offense_lineup)
        def_profile = self._get_lineup_profile(defense_lineup)

        offense_reb_rate = 0.25

        rebound_gap = off_profile["rebound"] - def_profile["rebound"]
        offense_reb_rate += rebound_gap * 0.0022
        offense_reb_rate += (off_profile["big_count"] - def_profile["big_count"]) * 0.012

        if offense_strategy == "inside":
            offense_reb_rate += 0.04
        elif offense_strategy == "three_point":
            offense_reb_rate -= 0.01

        if defense_strategy == "defense":
            offense_reb_rate -= 0.03

        if offense_coach == "offense":
            offense_reb_rate += 0.01
        elif offense_coach == "development":
            offense_reb_rate += 0.005

        if defense_coach == "defense":
            offense_reb_rate -= 0.01

        if was_blocked:
            offense_reb_rate -= 0.03

        return max(0.16, min(0.38, offense_reb_rate))

    def _get_shooter_weight(
        self,
        player: Player,
        offense_team: Team,
        offense_lineup: List[Player],
        shot_profile: str
    ) -> int:
        usage_base = max(1, int(getattr(player, "usage_base", 50)))
        ovr = int(getattr(player, "get_effective_ovr", lambda: getattr(player, "ovr", 50))())
        position = getattr(player, "position", "SF")
        strategy = getattr(offense_team, "strategy", "balanced")
        coach_style = getattr(offense_team, "coach_style", "balanced")

        shoot_attr = player.get_adjusted_attribute("shoot")
        three_attr = player.get_adjusted_attribute("three")
        drive_attr = player.get_adjusted_attribute("drive")
        passing_attr = player.get_adjusted_attribute("passing")
        rebound_attr = player.get_adjusted_attribute("rebound")

        position_weights = self._get_position_stat_weights(player)

        weight = usage_base
        weight += max(0, ovr - 50) * 2

        if shot_profile == "three":
            weight += int(three_attr * 1.6)
            weight += int(shoot_attr * 0.5)

            if position in ("PG", "SG", "SF"):
                weight += 10
            if strategy == "three_point":
                if position in ("SG", "SF", "PG"):
                    weight += 22
                weight += int(three_attr * 0.5)
            elif strategy == "run_and_gun":
                if position in ("PG", "SG"):
                    weight += 14
            elif strategy == "inside":
                if position in ("PF", "C"):
                    weight -= 8

            weight = int(weight * position_weights["score"] * position_weights["three_score"])

        elif shot_profile == "two":
            weight += int(shoot_attr * 1.1)
            weight += int(drive_attr * 1.2)

            if position in ("SG", "SF", "PF"):
                weight += 8
            if strategy == "inside":
                if position in ("PF", "C", "SF"):
                    weight += 22
                weight += int(rebound_attr * 0.4)
            elif strategy == "run_and_gun":
                if position in ("PG", "SG", "SF"):
                    weight += 10

            weight = int(weight * position_weights["score"] * position_weights["two_score"])

        elif shot_profile == "ft":
            weight += int(drive_attr * 1.0)
            weight += int(shoot_attr * 0.6)
            weight += int(passing_attr * 0.2)

            if position in ("PG", "SG", "SF"):
                weight += 6
            if strategy == "inside":
                if position in ("PF", "C", "SF"):
                    weight += 10
            elif strategy == "run_and_gun":
                if position in ("PG", "SG"):
                    weight += 8

            weight = int(weight * position_weights["score"] * position_weights["ft_score"])

        if coach_style == "offense":
            weight += 8
        elif coach_style == "development":
            if position in ("PG", "SG", "SF"):
                weight += 4

        sorted_lineup = sorted(
            offense_lineup,
            key=lambda p: p.get_effective_ovr(),
            reverse=True
        )
        if player in sorted_lineup[:1]:
            weight += 18
        elif player in sorted_lineup[:2]:
            weight += 10

        return max(1, int(weight))

    def _select_shooter(
        self,
        offense_team: Team,
        offense_lineup: List[Player],
        shot_profile: str
    ) -> Player:
        weights = [
            self._get_shooter_weight(p, offense_team, offense_lineup, shot_profile)
            for p in offense_lineup
        ]
        return random.choices(offense_lineup, weights=weights, k=1)[0]

    def simulate(self) -> Tuple[Team, int, int]:
        forfeiting_team = self._get_forfeit_team()
        if forfeiting_team is not None:
            return self._simulate_forfeit_game(forfeiting_team)

        self.total_possessions = self._get_total_possessions()

        last_quarter = None

        for i in range(self.total_possessions):
            self.current_possession = i
            quarter, _, _ = self._get_quarter_info(i)

            if quarter != last_quarter:
                if last_quarter is not None:
                    self._record_event(
                        event_type="quarter_end",
                        description_key="quarter_end",
                        possession_index=max(0, i - 1),
                        quarter_override=last_quarter,
                        clock_seconds_override=0,
                        meta={"quarter": last_quarter},
                    )

                self._record_event(
                    event_type="quarter_start",
                    description_key="quarter_start",
                    possession_index=i,
                    quarter_override=quarter,
                    clock_seconds_override=CLOCK_SECONDS_PER_REGULATION_QUARTER,
                    meta={"quarter": quarter},
                )
                last_quarter = quarter

            self._maybe_update_rotations(i)

            self._add_lineup_minutes(self.home_current_lineup)
            self._add_lineup_minutes(self.away_current_lineup)

            if i % 2 == 0:
                offense_team = self.home_team
                defense_team = self.away_team
                offense_lineup = self.home_current_lineup
                defense_lineup = self.away_current_lineup
                is_home = True
            else:
                offense_team = self.away_team
                defense_team = self.home_team
                offense_lineup = self.away_current_lineup
                defense_lineup = self.home_current_lineup
                is_home = False

            offense_team_offense, _ = self._calculate_team_strength_from_players(offense_team, offense_lineup)
            _, defense_team_defense = self._calculate_team_strength_from_players(defense_team, defense_lineup)

            points = self._simulate_possession(
                offense_team,
                defense_team,
                offense_lineup,
                defense_lineup,
                offense_team_offense,
                defense_team_defense
            )

            if is_home:
                self.home_score += points
            else:
                self.away_score += points

        if last_quarter is not None:
            self._record_event(
                event_type="quarter_end",
                description_key="quarter_end",
                possession_index=max(0, self.total_possessions - 1),
                quarter_override=last_quarter,
                clock_seconds_override=0,
                meta={"quarter": last_quarter},
            )

        overtime_count = 0
        overtime_period_possessions = 2
        overtime_base_possession_no = self.total_possessions

        while self.home_score == self.away_score:
            overtime_count += 1
            overtime_quarter = 4 + overtime_count
            self._record_event(
                event_type="quarter_start",
                description_key="overtime_start",
                possession_index=max(0, self.total_possessions - 1),
                quarter_override=overtime_quarter,
                clock_seconds_override=300,
                meta={"quarter": overtime_quarter, "is_overtime": True},
            )

            self._add_lineup_minutes(self.home_current_lineup)
            self._add_lineup_minutes(self.away_current_lineup)

            home_team_offense, _ = self._calculate_team_strength_from_players(self.home_team, self.home_current_lineup)
            away_team_offense, _ = self._calculate_team_strength_from_players(self.away_team, self.away_current_lineup)
            _, home_team_defense = self._calculate_team_strength_from_players(self.home_team, self.home_current_lineup)
            _, away_team_defense = self._calculate_team_strength_from_players(self.away_team, self.away_current_lineup)

            overtime_home_possession_no = overtime_base_possession_no + ((overtime_count - 1) * overtime_period_possessions) + 1
            self._set_event_context(
                quarter=overtime_quarter,
                clock_seconds=self._get_overtime_clock_seconds(1, overtime_period_possessions),
                possession_no=overtime_home_possession_no,
            )
            try:
                self.home_score += self._simulate_possession(
                    self.home_team,
                    self.away_team,
                    self.home_current_lineup,
                    self.away_current_lineup,
                    home_team_offense,
                    away_team_defense
                )
            finally:
                self._clear_event_context()

            overtime_away_possession_no = overtime_base_possession_no + ((overtime_count - 1) * overtime_period_possessions) + 2
            self._set_event_context(
                quarter=overtime_quarter,
                clock_seconds=self._get_overtime_clock_seconds(2, overtime_period_possessions),
                possession_no=overtime_away_possession_no,
            )
            try:
                self.away_score += self._simulate_possession(
                    self.away_team,
                    self.home_team,
                    self.away_current_lineup,
                    self.home_current_lineup,
                    away_team_offense,
                    home_team_defense
                )
            finally:
                self._clear_event_context()

            self._record_event(
                event_type="quarter_end",
                description_key="overtime_end",
                possession_index=max(0, self.total_possessions - 1),
                quarter_override=overtime_quarter,
                clock_seconds_override=0,
                meta={"quarter": overtime_quarter, "is_overtime": True},
            )

        final_quarter = 4 + overtime_count if overtime_count > 0 else max(1, last_quarter or 4)
        self._record_event(
            event_type="game_end",
            description_key="game_end",
            possession_index=max(0, self.total_possessions - 1),
            quarter_override=final_quarter,
            clock_seconds_override=0,
            meta={
                "winner_team_id": self._team_key(self.home_team if self.home_score > self.away_score else self.away_team),
                "is_playoff": self.is_playoff,
                "overtime_count": overtime_count,
            },
        )

        if not self.is_playoff:
            played_players = set()
            for player in self.home_active_players + self.away_active_players:
                if player.name in played_players:
                    continue
                player.games_played += 1
                played_players.add(player.name)

        home_win = self.home_score > self.away_score

        self._record_team_game(
            self.home_team,
            self.home_active_players,
            self.home_current_lineup,
            home_win,
            self.home_score,
            self.away_score,
            is_playoff=self.is_playoff
        )
        self._record_team_game(
            self.away_team,
            self.away_active_players,
            self.away_current_lineup,
            not home_win,
            self.away_score,
            self.home_score,
            is_playoff=self.is_playoff
        )

        self.home_team.process_injury_recovery()
        self.away_team.process_injury_recovery()

        self._print_minutes_log(self.home_team, self.home_active_players)
        self._print_minutes_log(self.away_team, self.away_active_players)
        self._print_play_by_play_debug_summary()
        self._print_commentary_preview()
        self._print_play_sequence_preview()

        winner = self.home_team if home_win else self.away_team
        return winner, self.home_score, self.away_score

    def _record_team_game(
        self,
        team: Team,
        active_players: List[Player],
        closing_lineup: List[Player],
        is_win: bool,
        points_scored: int,
        points_allowed: int,
        is_playoff: bool = False
    ):
        if is_win:
            team.total_wins += 1
        else:
            team.total_losses += 1

        if not is_playoff:
            if is_win:
                team.regular_wins += 1
            else:
                team.regular_losses += 1
            team.regular_points_for += points_scored
            team.regular_points_against += points_allowed

        closing_names = {p.name for p in closing_lineup}

        for p in active_players:
            if p.is_injured() or p.is_retired:
                continue

            if p.name in closing_names:
                p.fatigue = min(100, p.fatigue + 8)
            else:
                p.fatigue = min(100, p.fatigue + 4)

            if random.random() < 0.01:
                p.injury_games_left = random.randint(1, 5)


    def _resolve_finish_type(
        self,
        shooter: Player,
        shot_profile: str,
        *,
        is_second_chance: bool = False,
        is_transition_play: bool = False,
        assisted: bool = False,
    ) -> Optional[str]:
        if shot_profile != "two":
            return None

        position = str(getattr(shooter, "position", "") or "").upper()
        archetype = str(getattr(shooter, "archetype", "") or "").lower()
        drive_attr = float(shooter.get_adjusted_attribute("drive") or 0)
        rebound_attr = float(shooter.get_adjusted_attribute("rebound") or 0)
        height_cm = float(getattr(shooter, "height_cm", 0) or 0)
        ovr = float(getattr(shooter, "ovr", 0) or 0)

        recent_transition = bool(is_transition_play)
        if not recent_transition and self.play_sequence_log:
            prev_result = str((self.play_sequence_log[-1] or {}).get("result_type", "") or "")
            recent_transition = prev_result in {
                "turnover",
                "steal",
                "def_rebound",
                "block_def_rebound",
                "miss_2_def_rebound",
                "miss_3_def_rebound",
            }

        # 場面優先でダンク候補を拾う。
        # まずは「出ること」を優先し、頻度は後で絞る。
        base_score = 0.0
        if position == "C":
            base_score += 3.0
        elif position == "PF":
            base_score += 2.6
        elif position == "SF":
            base_score += 1.8
        elif position == "SG":
            base_score += 0.8

        if height_cm >= 208:
            base_score += 2.0
        elif height_cm >= 203:
            base_score += 1.5
        elif height_cm >= 198:
            base_score += 1.0
        elif height_cm >= 193:
            base_score += 0.4

        if drive_attr >= 88:
            base_score += 1.8
        elif drive_attr >= 80:
            base_score += 1.2
        elif drive_attr >= 72:
            base_score += 0.6

        if rebound_attr >= 90:
            base_score += 1.4
        elif rebound_attr >= 82:
            base_score += 1.0
        elif rebound_attr >= 74:
            base_score += 0.4

        if ovr >= 80:
            base_score += 0.5
        elif ovr >= 72:
            base_score += 0.2

        if assisted:
            base_score += 0.8
        if is_second_chance:
            base_score += 1.1
        if recent_transition:
            base_score += 1.4

        archetype_keywords = (
            "slasher",
            "rim",
            "rebound",
            "big",
            "stretch_big",
            "two_way_wing",
            "finisher",
            "dunker",
        )
        if any(keyword in archetype for keyword in archetype_keywords):
            base_score += 0.9

        # ガードは条件を強めに。
        if position == "SG" and not (drive_attr >= 84 and height_cm >= 193):
            return None
        if position not in {"C", "PF", "SF", "SG"}:
            return None

        if base_score < 3.6:
            return None

        base_rate = 0.14
        if position == "C":
            base_rate += 0.18
        elif position == "PF":
            base_rate += 0.14
        elif position == "SF":
            base_rate += 0.08
        else:
            base_rate += 0.03

        if recent_transition:
            base_rate += 0.18
        if is_second_chance:
            base_rate += 0.14
        if assisted:
            base_rate += 0.10
        if height_cm >= 203:
            base_rate += 0.08
        if drive_attr >= 82:
            base_rate += 0.08
        if rebound_attr >= 82:
            base_rate += 0.06
        if any(keyword in archetype for keyword in archetype_keywords):
            base_rate += 0.06

        # 明確にダンクしやすい場面はさらに優遇。
        if position in {"PF", "C"} and (recent_transition or is_second_chance or assisted):
            base_rate += 0.10
        if position == "SF" and recent_transition and drive_attr >= 80:
            base_rate += 0.08

        base_rate = max(0.0, min(0.82, base_rate))
        if random.random() >= base_rate:
            return None

        return "dunk"

    def _simulate_second_chance(
        self,
        offense_team: Team,
        defense_team: Team,
        offense_lineup: List[Player],
        defense_lineup: List[Player],
        offense_team_offense: float,
        defense_team_defense: float,
        rebounder: Player
    ) -> int:
        if not offense_lineup or not defense_lineup:
            return 0

        three_cutoff, two_cutoff, shot_rate_adjust = self._get_shot_mix(
            offense_team,
            defense_team,
            offense_lineup,
            defense_lineup,
        )

        three_cutoff = max(0.08, three_cutoff - 0.12)
        two_cutoff = max(three_cutoff + 0.25, min(0.96, two_cutoff + 0.03))
        shot_rate_adjust = min(0.030, shot_rate_adjust + 0.004)

        rand_val = random.random()
        pts = 0
        is_ft = False
        shot_profile = "two"

        if rand_val < three_cutoff:
            shooter = self._select_shooter(offense_team, offense_lineup, "three")
            three_attr = shooter.get_adjusted_attribute("three")
            pts = 3
            shot_profile = "three"
            final_rate = 0.200 + (three_attr * 0.0017) + ((offense_team_offense - defense_team_defense) * 0.0006) + 0.006 + shot_rate_adjust
        elif rand_val < two_cutoff:
            shooter = self._select_shooter(offense_team, offense_lineup, "two")
            if random.random() < 0.28:
                shooter = rebounder
            shoot_attr = shooter.get_adjusted_attribute("shoot")
            drive_attr = shooter.get_adjusted_attribute("drive")
            pts = 2
            shot_profile = "two"
            final_rate = 0.302 + (shoot_attr * 0.0014) + (drive_attr * 0.00075) + ((offense_team_offense - defense_team_defense) * 0.00055) + 0.006 + shot_rate_adjust
        else:
            shooter = self._select_shooter(offense_team, offense_lineup, "ft")
            ft_attr = shooter.get_adjusted_attribute("ft")
            pts = 1
            is_ft = True
            shot_profile = "ft"
            final_rate = 0.53 + (ft_attr * 0.0040)

        final_rate = max(0.08, min(0.84, final_rate))

        assister = None
        if random.random() < final_rate:
            if not self.is_playoff:
                shooter.season_points += pts

                assist_rate = self._get_assist_chance(
                    offense_team=offense_team,
                    offense_lineup=offense_lineup,
                    shooter=shooter,
                    shot_profile=shot_profile,
                    is_second_chance=True
                )

                if not is_ft and random.random() < assist_rate:
                    assister = self._pick_assister(offense_lineup, shooter)
                    if assister is not None:
                        assister.season_assists += 1

            finish_type = self._resolve_finish_type(
                shooter,
                shot_profile,
                is_second_chance=True,
                is_transition_play=False,
                assisted=assister is not None,
            )

            event_type = "made_ft" if is_ft else ("made_3" if pts == 3 else "made_2")
            description_key = f"second_chance_{event_type}"
            self._record_event(
                event_type=event_type,
                offense_team=offense_team,
                defense_team=defense_team,
                primary_player=shooter,
                secondary_player=assister,
                description_key=description_key,
                scoring_team=offense_team,
                points=pts,
                meta={
                    "shot_profile": shot_profile,
                    "second_chance": True,
                    "assisted": assister is not None,
                    "rebounder_id": self._player_log_key(rebounder),
                    "finish_type": finish_type,
                },
            )
            return pts

        rebounder_def = self._pick_rebounder(defense_lineup, side="defense")
        if not self.is_playoff:
            rebounder_def.season_rebounds += 1

        event_type = "miss_ft" if is_ft else ("miss_3" if pts == 3 else "miss_2")
        self._record_event(
            event_type=event_type,
            offense_team=offense_team,
            defense_team=defense_team,
            primary_player=shooter,
            description_key=f"second_chance_{event_type}",
            meta={
                "shot_profile": shot_profile,
                "second_chance": True,
                "rebounder_id": self._player_log_key(rebounder),
            },
        )
        self._record_event(
            event_type="def_rebound",
            offense_team=offense_team,
            defense_team=defense_team,
            primary_player=rebounder_def,
            description_key="def_rebound_after_second_chance",
            meta={
                "second_chance": True,
            },
        )

        return 0

    def _simulate_possession(
        self,
        offense_team: Team,
        defense_team: Team,
        offense_lineup: List[Player],
        defense_lineup: List[Player],
        offense_team_offense: float,
        defense_team_defense: float
    ) -> int:
        if not offense_lineup or not defense_lineup:
            return 0

        defense_pressure = sum(p.get_adjusted_attribute("defense") for p in defense_lineup) / len(defense_lineup)
        offense_ball_security = sum(
            (p.get_adjusted_attribute("passing") + p.get_adjusted_attribute("drive")) / 2
            for p in offense_lineup
        ) / len(offense_lineup)

        steal_rate = 0.045 + ((defense_pressure - offense_ball_security) * 0.00035)

        defense_strategy = getattr(defense_team, "strategy", "balanced")
        defense_coach = getattr(defense_team, "coach_style", "balanced")
        offense_strategy = getattr(offense_team, "strategy", "balanced")
        offense_coach = getattr(offense_team, "coach_style", "balanced")

        if defense_strategy == "defense":
            steal_rate += 0.010
        elif defense_strategy == "run_and_gun":
            steal_rate -= 0.003

        if defense_coach == "defense":
            steal_rate += 0.006
        elif defense_coach == "offense":
            steal_rate -= 0.002

        if offense_strategy == "run_and_gun":
            steal_rate += 0.004
        elif offense_strategy == "inside":
            steal_rate -= 0.002

        if offense_coach == "development":
            steal_rate += 0.001

        steal_rate = max(0.015, min(0.090, steal_rate))

        if random.random() < steal_rate:
            stealer = self._pick_stealer(defense_lineup)
            if not self.is_playoff:
                stealer.season_steals += 1

            ball_handler = self._select_shooter(offense_team, offense_lineup, "two")
            self._record_event(
                event_type="steal",
                offense_team=offense_team,
                defense_team=defense_team,
                primary_player=ball_handler,
                secondary_player=stealer,
                description_key="steal_turnover",
                meta={
                    "turnover": True,
                },
            )
            self._record_event(
                event_type="turnover",
                offense_team=offense_team,
                defense_team=defense_team,
                primary_player=ball_handler,
                secondary_player=stealer,
                description_key="live_ball_turnover",
                meta={
                    "caused_by_steal": True,
                },
            )
            return 0

        team_adjust = (offense_team_offense - defense_team_defense) * 0.0008
        three_cutoff, two_cutoff, shot_rate_adjust = self._get_shot_mix(
            offense_team,
            defense_team,
            offense_lineup,
            defense_lineup,
        )

        rand_val = random.random()
        pts = 0
        is_ft = False
        is_three = False
        shot_profile = "two"

        if rand_val < three_cutoff:
            shooter = self._select_shooter(offense_team, offense_lineup, "three")
            three_attr = shooter.get_adjusted_attribute("three")
            pts = 3
            is_three = True
            shot_profile = "three"
            final_rate = 0.165 + (three_attr * 0.0017) + ((offense_team_offense - defense_team_defense) * 0.0006) + shot_rate_adjust

        elif rand_val < two_cutoff:
            shooter = self._select_shooter(offense_team, offense_lineup, "two")
            shoot_attr = shooter.get_adjusted_attribute("shoot")
            drive_attr = shooter.get_adjusted_attribute("drive")
            pts = 2
            shot_profile = "two"
            final_rate = 0.273 + (shoot_attr * 0.0014) + (drive_attr * 0.00065) + ((offense_team_offense - defense_team_defense) * 0.00055) + shot_rate_adjust

        else:
            shooter = self._select_shooter(offense_team, offense_lineup, "ft")
            ft_attr = shooter.get_adjusted_attribute("ft")
            pts = 1
            is_ft = True
            shot_profile = "ft"
            final_rate = 0.51 + (ft_attr * 0.0040)

        final_rate = max(0.05, min(0.82, final_rate))

        assister = None
        if random.random() < final_rate:
            if not self.is_playoff:
                shooter.season_points += pts

                assist_rate = self._get_assist_chance(
                    offense_team=offense_team,
                    offense_lineup=offense_lineup,
                    shooter=shooter,
                    shot_profile=shot_profile,
                    is_second_chance=False
                )

                if not is_ft and random.random() < assist_rate:
                    assister = self._pick_assister(offense_lineup, shooter)
                    if assister is not None:
                        assister.season_assists += 1

            finish_type = self._resolve_finish_type(
                shooter,
                shot_profile,
                is_second_chance=False,
                is_transition_play=False,
                assisted=assister is not None,
            )

            event_type = "made_ft" if is_ft else ("made_3" if pts == 3 else "made_2")
            description_key = event_type if assister is None else f"{event_type}_assisted"
            self._record_event(
                event_type=event_type,
                offense_team=offense_team,
                defense_team=defense_team,
                primary_player=shooter,
                secondary_player=assister,
                description_key=description_key,
                scoring_team=offense_team,
                points=pts,
                meta={
                    "shot_profile": shot_profile,
                    "assisted": assister is not None,
                    "second_chance": False,
                    "finish_type": finish_type,
                },
            )
            return pts

        was_blocked = False
        blocker = None
        if not is_ft:
            avg_defense = sum(p.get_adjusted_attribute("defense") for p in defense_lineup) / len(defense_lineup)
            avg_rebound = sum(p.get_adjusted_attribute("rebound") for p in defense_lineup) / len(defense_lineup)

            block_rate = 0.04 + (avg_defense * 0.00015) + (avg_rebound * 0.00005)
            if not is_three:
                block_rate += 0.02
            if defense_strategy == "defense":
                block_rate += 0.01
            if defense_coach == "defense":
                block_rate += 0.006

            block_rate = max(0.01, min(0.14, block_rate))

            if random.random() < block_rate:
                was_blocked = True
                blocker = self._pick_blocker(defense_lineup, is_three=is_three)
                if not self.is_playoff:
                    blocker.season_blocks += 1

                self._record_event(
                    event_type="block",
                    offense_team=offense_team,
                    defense_team=defense_team,
                    primary_player=shooter,
                    secondary_player=blocker,
                    description_key="blocked_shot",
                    meta={
                        "shot_profile": shot_profile,
                    },
                )

        event_type = "miss_ft" if is_ft else ("miss_3" if pts == 3 else "miss_2")
        self._record_event(
            event_type=event_type,
            offense_team=offense_team,
            defense_team=defense_team,
            primary_player=shooter,
            secondary_player=blocker,
            description_key="missed_shot_blocked" if was_blocked else event_type,
            meta={
                "shot_profile": shot_profile,
                "was_blocked": was_blocked,
                "second_chance": False,
            },
        )

        offense_reb_rate = self._get_offense_rebound_rate(
            offense_team,
            defense_team,
            offense_lineup,
            defense_lineup,
            was_blocked,
        )

        offense_gets_rebound = random.random() < offense_reb_rate

        if offense_gets_rebound:
            rebounder = self._pick_rebounder(offense_lineup, side="offense")

            if not self.is_playoff:
                rebounder.season_rebounds += 1

            self._record_event(
                event_type="off_rebound",
                offense_team=offense_team,
                defense_team=defense_team,
                primary_player=rebounder,
                description_key="off_rebound",
                meta={
                    "after_block": was_blocked,
                    "after_miss": event_type,
                },
            )

            return self._simulate_second_chance(
                offense_team,
                defense_team,
                offense_lineup,
                defense_lineup,
                offense_team_offense,
                defense_team_defense,
                rebounder
            )

        rebounder = self._pick_rebounder(defense_lineup, side="defense")

        if not self.is_playoff:
            rebounder.season_rebounds += 1

        self._record_event(
            event_type="def_rebound",
            offense_team=offense_team,
            defense_team=defense_team,
            primary_player=rebounder,
            description_key="def_rebound",
            meta={
                "after_block": was_blocked,
                "after_miss": event_type,
            },
        )

        return 0
