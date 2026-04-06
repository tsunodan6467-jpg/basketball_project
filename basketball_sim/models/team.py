from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Mapping

from basketball_sim.systems.competition_rules import league_contract_active_rule
from basketball_sim.systems.japan_regulation import count_regulation_slots, player_regulation_bucket_from_rule

from .player import Player

OWNER_TRUST_MILD_DEFICIT_THRESHOLD = 20_000_000
OWNER_TRUST_MAX_NEGATIVE_DELTA_PER_SEASON = -15

# `docs/INSEASON_REVENUE_KEY_POLICY.md` §3（正本非経由のラウンド追跡用）
INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY = "inseason_league_distribution_round"


@dataclass
class Team:
    """
    チームデータを表現するクラス。
    所属選手（ロスター）や勝利数、チームステータスを管理します。
    1部リーグ〜3部リーグ (league_level: 1, 2, 3) が存在します。
    """
    team_id: int
    name: str
    league_level: int
    strategy: str = "balanced"

    coach_style: str = "balanced"
    usage_policy: str = "balanced"
    # チーム練習方針（毎週固定。変更時のみGMメニューから更新）
    team_training_focus: str = "balanced"  # balanced / shooting / defense / transition / precision_offense / intense_defense
    # 戦術メニュー用拡張設定（Phase A: 永続化のみ。試合反映は Phase B 以降で Team.strategy 等と接続）
    team_tactics: Dict[str, Any] = field(default_factory=dict)
    # 経営メニュー用ネスト（version キー付き）。スポンサー・広報等はここに集約。
    management: Dict[str, Any] = field(default_factory=dict)

    home_city: str = ""
    is_user_team: bool = False

    players: List[Player] = field(default_factory=list)
    starting_lineup: List[int] = field(default_factory=list)
    sixth_man_id: Optional[int] = None
    bench_order: List[int] = field(default_factory=list)

    popularity: int = 50
    market_size: float = 1.0
    # 仮バランス調整: 経営即死を避けるための初期運転資金（後で本設計へ差し替え想定）
    money: int = 2_000_000_000

    fan_base: int = 5000
    season_ticket_base: int = 2500
    sponsor_power: int = 50

    arena_level: int = 1
    training_facility_level: int = 1
    medical_facility_level: int = 1
    front_office_level: int = 1

    payroll_budget: int = 120000000
    owner_expectation: str = "playoff_race"
    owner_trust: int = 50
    owner_missions: List[dict] = field(default_factory=list)
    owner_mission_history: List[dict] = field(default_factory=list)

    revenue_last_season: int = 0
    expense_last_season: int = 0
    cashflow_last_season: int = 0
    finance_history: List[dict] = field(default_factory=list)
    # シーズン中の非正本キャッシュイン（当面 B）。`record_financial_result` とは別リスト。
    inseason_cash_round_log: List[dict] = field(default_factory=list)
    # オフ内の国際大会賞金等を、締めの record_financial_result に合流させるための仮積み（外部チームは即時 money のまま）
    offseason_competition_revenue_pending: int = 0
    offseason_competition_revenue_breakdown: Dict[str, int] = field(default_factory=dict)

    scout_level: int = 50
    scout_focus: str = "balanced"
    scout_dispatch: str = "college"

    rookie_budget: int = 40000000
    rookie_budget_remaining: int = 40000000

    # -------------------------
    # Youth system (v1 foundation)
    # 正本: docs/YOUTH_SYSTEM_V1.md
    # -------------------------
    youth_players: List[Player] = field(default_factory=list)
    # 16〜18歳のコールアップ（ユース枠）: 通常ロスター13人枠とは別管理
    youth_callups: List[Player] = field(default_factory=list)
    youth_capacity: int = 10
    youth_callups_limit_per_year: int = 2
    youth_callups_used_this_year: int = 0
    youth_graduate_rights_limit_per_year: int = 2
    youth_graduate_rights_used_this_year: int = 0

    youth_policy_global: str = "balanced"  # technical / physical / balanced
    youth_policy_focus: str = "balanced"   # pg / shooter / big / defender / balanced
    youth_investment: Dict[str, int] = field(
        default_factory=lambda: {"facility": 50, "coaching": 50, "scout": 50, "community": 50}
    )
    youth_prospect_ids: List[int] = field(default_factory=list)
    youth_rights_players: List[Player] = field(default_factory=list)
    icon_youth_return_reservations: List[dict] = field(default_factory=list)

    # -------------------------
    # Special designation (v1)
    # - ドラフト候補から「1年だけ・0円」で加入できる特別枠（13人枠外）
    # -------------------------
    special_designation_players: List[Player] = field(default_factory=list)

    # 負傷者リスト（本契約13枠に含む。試合の登録対象から外すのみ）
    injured_reserve_ids: List[int] = field(default_factory=list)

    # -------------------------
    # League shared state (v1 minimal)
    # - 将来拡張を避けるため、リーグ共通の一部状態を Team に載せて永続化する
    # -------------------------
    league_future_draft_pool: List[Player] = field(default_factory=list)
    league_future_draft_year: int = 0

    regular_wins: int = 0
    regular_losses: int = 0
    regular_points_for: int = 0
    regular_points_against: int = 0

    total_wins: int = 0
    total_losses: int = 0

    last_season_wins: int = 0
    last_season_losses: int = 0

    team_offense: float = 0.0
    team_defense: float = 0.0
    team_power: float = 0.0

    history_seasons: List[dict] = field(default_factory=list)
    history_transactions: List[dict] = field(default_factory=list)
    history_awards: List[dict] = field(default_factory=list)
    history_milestones: List[dict] = field(default_factory=list)

    club_legends: List[dict] = field(default_factory=list)
    all_time_player_archive: List[dict] = field(default_factory=list)

    def __post_init__(self):
        valid_coach_styles = {"balanced", "offense", "defense", "development"}
        if self.coach_style not in valid_coach_styles:
            self.coach_style = "balanced"

        valid_usage_policies = {"balanced", "win_now", "development"}
        if self.usage_policy not in valid_usage_policies:
            self.usage_policy = "balanced"
        valid_team_training_focus = {
            "balanced", "shooting", "defense", "transition", "precision_offense", "intense_defense"
        }
        if getattr(self, "team_training_focus", "balanced") not in valid_team_training_focus:
            self.team_training_focus = "balanced"

        self.scout_level = int(max(1, min(100, getattr(self, "scout_level", 50))))
        valid_scout_focuses = {"balanced", "shooting", "defense", "athletic", "playmaking", "inside"}
        if getattr(self, "scout_focus", "balanced") not in valid_scout_focuses:
            self.scout_focus = "balanced"

        valid_scout_dispatches = {"highschool", "college", "overseas"}
        if getattr(self, "scout_dispatch", "college") not in valid_scout_dispatches:
            self.scout_dispatch = "college"

        self.rookie_budget = int(max(0, getattr(self, "rookie_budget", 40000000)))
        # ソフトキャップ運用のため、remaining はマイナスも許容する（税を含めた支出管理）
        self.rookie_budget_remaining = int(getattr(self, "rookie_budget_remaining", self.rookie_budget))

        # youth defaults / safety
        self.youth_capacity = int(max(0, getattr(self, "youth_capacity", 10)))
        self.youth_callups_limit_per_year = int(max(0, getattr(self, "youth_callups_limit_per_year", 2)))
        self.youth_callups_used_this_year = int(max(0, getattr(self, "youth_callups_used_this_year", 0)))
        self.youth_graduate_rights_limit_per_year = int(max(0, getattr(self, "youth_graduate_rights_limit_per_year", 2)))
        self.youth_graduate_rights_used_this_year = int(max(0, getattr(self, "youth_graduate_rights_used_this_year", 0)))

        if not hasattr(self, "youth_players") or self.youth_players is None:
            self.youth_players = []
        if not hasattr(self, "youth_callups") or self.youth_callups is None:
            self.youth_callups = []
        if not hasattr(self, "icon_youth_return_reservations") or self.icon_youth_return_reservations is None:
            self.icon_youth_return_reservations = []
        if not hasattr(self, "special_designation_players") or self.special_designation_players is None:
            self.special_designation_players = []
        if not hasattr(self, "injured_reserve_ids") or self.injured_reserve_ids is None:
            self.injured_reserve_ids = []

        if not hasattr(self, "league_future_draft_pool") or self.league_future_draft_pool is None:
            self.league_future_draft_pool = []
        if not hasattr(self, "league_future_draft_year") or self.league_future_draft_year is None:
            self.league_future_draft_year = 0

        inv = getattr(self, "youth_investment", None)
        if not isinstance(inv, dict):
            inv = {"facility": 50, "coaching": 50, "scout": 50, "community": 50}
        for k in ("facility", "coaching", "scout", "community"):
            inv[k] = int(max(0, min(100, inv.get(k, 50))))
        self.youth_investment = inv

        if getattr(self, "youth_policy_global", "balanced") not in {"technical", "physical", "balanced"}:
            self.youth_policy_global = "balanced"
        if getattr(self, "youth_policy_focus", "balanced") not in {"pg", "shooter", "big", "defender", "balanced"}:
            self.youth_policy_focus = "balanced"

        self.fan_base = int(max(0, getattr(self, "fan_base", 5000)))
        self.season_ticket_base = int(max(0, getattr(self, "season_ticket_base", 2500)))
        self.sponsor_power = int(max(1, min(100, getattr(self, "sponsor_power", 50))))

        self.arena_level = int(max(1, min(10, getattr(self, "arena_level", 1))))
        self.training_facility_level = int(max(1, min(10, getattr(self, "training_facility_level", 1))))
        self.medical_facility_level = int(max(1, min(10, getattr(self, "medical_facility_level", 1))))
        self.front_office_level = int(max(1, min(10, getattr(self, "front_office_level", 1))))

        self.payroll_budget = int(max(0, getattr(self, "payroll_budget", 120000000)))
        valid_owner_expectations = {
            "rebuild",
            "playoff_race",
            "promotion",
            "title_challenge",
            "title_or_bust",
        }
        if getattr(self, "owner_expectation", "playoff_race") not in valid_owner_expectations:
            self.owner_expectation = "playoff_race"

        self.owner_trust = int(max(0, min(100, getattr(self, "owner_trust", 50))))
        if not isinstance(getattr(self, "owner_missions", []), list):
            self.owner_missions = []
        if not isinstance(getattr(self, "owner_mission_history", []), list):
            self.owner_mission_history = []

        self.revenue_last_season = int(getattr(self, "revenue_last_season", 0) or 0)
        self.expense_last_season = int(getattr(self, "expense_last_season", 0) or 0)
        self.cashflow_last_season = int(getattr(self, "cashflow_last_season", 0) or 0)

        self._ensure_history_fields()

    def _ensure_history_fields(self):
        if not hasattr(self, "history_seasons") or self.history_seasons is None:
            self.history_seasons = []

        if not hasattr(self, "history_transactions") or self.history_transactions is None:
            self.history_transactions = []

        if not hasattr(self, "history_awards") or self.history_awards is None:
            self.history_awards = []

        if not hasattr(self, "history_milestones") or self.history_milestones is None:
            self.history_milestones = []

        if not hasattr(self, "club_legends") or self.club_legends is None:
            self.club_legends = []

        if not hasattr(self, "all_time_player_archive") or self.all_time_player_archive is None:
            self.all_time_player_archive = []

        if not hasattr(self, "starting_lineup") or self.starting_lineup is None:
            self.starting_lineup = []

        if not hasattr(self, "sixth_man_id"):
            self.sixth_man_id = None

        if not hasattr(self, "bench_order") or self.bench_order is None:
            self.bench_order = []

        if not hasattr(self, "usage_policy") or self.usage_policy is None:
            self.usage_policy = "balanced"
        if not hasattr(self, "team_training_focus") or self.team_training_focus is None:
            self.team_training_focus = "balanced"
        if self.team_training_focus not in {
            "balanced", "shooting", "defense", "transition", "precision_offense", "intense_defense"
        }:
            self.team_training_focus = "balanced"

        if not hasattr(self, "scout_level") or self.scout_level is None:
            self.scout_level = 50
        self.scout_level = int(max(1, min(100, self.scout_level)))

        if not hasattr(self, "scout_focus") or self.scout_focus is None:
            self.scout_focus = "balanced"
        valid_scout_focuses = {"balanced", "shooting", "defense", "athletic", "playmaking", "inside"}
        if self.scout_focus not in valid_scout_focuses:
            self.scout_focus = "balanced"

        if not hasattr(self, "scout_dispatch") or self.scout_dispatch is None:
            self.scout_dispatch = "college"
        valid_scout_dispatches = {"highschool", "college", "overseas"}
        if self.scout_dispatch not in valid_scout_dispatches:
            self.scout_dispatch = "college"

        if not hasattr(self, "rookie_budget") or self.rookie_budget is None:
            self.rookie_budget = 30000000
        self.rookie_budget = int(max(0, self.rookie_budget))

        if not hasattr(self, "rookie_budget_remaining") or self.rookie_budget_remaining is None:
            self.rookie_budget_remaining = self.rookie_budget
        self.rookie_budget_remaining = int(max(0, self.rookie_budget_remaining))

        if not hasattr(self, "fan_base") or self.fan_base is None:
            self.fan_base = 5000
        self.fan_base = int(max(0, self.fan_base))

        if not hasattr(self, "season_ticket_base") or self.season_ticket_base is None:
            self.season_ticket_base = 2500
        self.season_ticket_base = int(max(0, self.season_ticket_base))

        if not hasattr(self, "sponsor_power") or self.sponsor_power is None:
            self.sponsor_power = 50
        self.sponsor_power = int(max(1, min(100, self.sponsor_power)))

        if not hasattr(self, "arena_level") or self.arena_level is None:
            self.arena_level = 1
        self.arena_level = int(max(1, min(10, self.arena_level)))

        if not hasattr(self, "training_facility_level") or self.training_facility_level is None:
            self.training_facility_level = 1
        self.training_facility_level = int(max(1, min(10, self.training_facility_level)))

        if not hasattr(self, "medical_facility_level") or self.medical_facility_level is None:
            self.medical_facility_level = 1
        self.medical_facility_level = int(max(1, min(10, self.medical_facility_level)))

        if not hasattr(self, "front_office_level") or self.front_office_level is None:
            self.front_office_level = 1
        self.front_office_level = int(max(1, min(10, self.front_office_level)))

        if not hasattr(self, "payroll_budget") or self.payroll_budget is None:
            self.payroll_budget = 120000000
        self.payroll_budget = int(max(0, self.payroll_budget))

        if not hasattr(self, "owner_expectation") or self.owner_expectation is None:
            self.owner_expectation = "playoff_race"
        valid_owner_expectations = {
            "rebuild",
            "playoff_race",
            "promotion",
            "title_challenge",
            "title_or_bust",
        }
        if self.owner_expectation not in valid_owner_expectations:
            self.owner_expectation = "playoff_race"

        if not hasattr(self, "owner_trust") or self.owner_trust is None:
            self.owner_trust = 50
        self.owner_trust = int(max(0, min(100, self.owner_trust)))

        if not hasattr(self, "owner_missions") or self.owner_missions is None:
            self.owner_missions = []
        if not hasattr(self, "owner_mission_history") or self.owner_mission_history is None:
            self.owner_mission_history = []

        if not hasattr(self, "revenue_last_season") or self.revenue_last_season is None:
            self.revenue_last_season = 0
        self.revenue_last_season = int(self.revenue_last_season)

        if not hasattr(self, "expense_last_season") or self.expense_last_season is None:
            self.expense_last_season = 0
        self.expense_last_season = int(self.expense_last_season)

        if not hasattr(self, "cashflow_last_season") or self.cashflow_last_season is None:
            self.cashflow_last_season = 0
        self.cashflow_last_season = int(self.cashflow_last_season)

        if not hasattr(self, "finance_history") or self.finance_history is None:
            self.finance_history = []

        if not hasattr(self, "inseason_cash_round_log") or self.inseason_cash_round_log is None:
            self.inseason_cash_round_log = []
        elif not isinstance(self.inseason_cash_round_log, list):
            self.inseason_cash_round_log = []

        if not hasattr(self, "team_tactics") or self.team_tactics is None:
            self.team_tactics = {}
        elif not isinstance(self.team_tactics, dict):
            self.team_tactics = {}

        if not hasattr(self, "management") or self.management is None:
            self.management = {}
        elif not isinstance(self.management, dict):
            self.management = {}

        from basketball_sim.systems.sponsor_management import ensure_sponsor_management_on_team

        ensure_sponsor_management_on_team(self)

        from basketball_sim.systems.pr_campaign_management import ensure_pr_campaigns_on_team

        ensure_pr_campaigns_on_team(self)

        from basketball_sim.systems.merchandise_management import ensure_merchandise_on_team

        ensure_merchandise_on_team(self)

        log = self.management.get("cpu_mgmt_log")
        if not isinstance(log, list):
            self.management["cpu_mgmt_log"] = []

    def reset_rookie_budget(self):
        self.rookie_budget_remaining = int(max(0, self.rookie_budget))

    def spend_rookie_budget(self, amount: int):
        self.rookie_budget_remaining = int(self.rookie_budget_remaining - max(0, int(amount)))

    def record_inseason_league_distribution_round(self, *, round_number: int, amount: int) -> None:
        """`money` に足したシーズン中収益と同額・同キーを `inseason_cash_round_log` に残す（正本外）。"""
        self._ensure_history_fields()
        key = INSEASON_LEAGUE_DISTRIBUTION_ROUND_KEY
        rn = int(round_number)
        amt = int(amount)
        log = self.inseason_cash_round_log
        for e in log:
            if e.get("key") == key and int(e.get("round_number", -9_999_999)) == rn:
                return
        log.append({"key": key, "amount": amt, "round_number": rn})

    def get_financial_profile(self) -> dict:
        self._ensure_history_fields()
        return {
            "money": int(self.money),
            "fan_base": int(self.fan_base),
            "season_ticket_base": int(self.season_ticket_base),
            "sponsor_power": int(self.sponsor_power),
            "arena_level": int(self.arena_level),
            "training_facility_level": int(self.training_facility_level),
            "medical_facility_level": int(self.medical_facility_level),
            "front_office_level": int(self.front_office_level),
            "payroll_budget": int(self.payroll_budget),
            "owner_expectation": self.owner_expectation,
            "owner_trust": int(self.owner_trust),
            "revenue_last_season": int(self.revenue_last_season),
            "expense_last_season": int(self.expense_last_season),
            "cashflow_last_season": int(self.cashflow_last_season),
        }

    def record_financial_result(
        self,
        revenue: int,
        expense: int,
        note: str = "",
        season_label: Optional[str] = None,
        *,
        breakdown_revenue: Optional[Mapping[str, int]] = None,
        breakdown_expense: Optional[Mapping[str, int]] = None,
    ) -> dict:
        self._ensure_history_fields()

        revenue = int(revenue or 0)
        expense = int(expense or 0)
        cashflow = revenue - expense

        self.revenue_last_season = revenue
        self.expense_last_season = expense
        self.cashflow_last_season = cashflow
        self.money = int(self.money + cashflow)

        payload = {
            "season_label": season_label,
            "revenue": revenue,
            "expense": expense,
            "cashflow": cashflow,
            "ending_money": int(self.money),
            "note": note,
        }
        br = self._coerce_finance_breakdown(breakdown_revenue)
        be = self._coerce_finance_breakdown(breakdown_expense)
        if br is not None and sum(br.values()) == revenue:
            payload["breakdown_revenue"] = dict(br)
        if be is not None and sum(be.values()) == expense:
            payload["breakdown_expense"] = dict(be)
        self.finance_history.append(payload)
        return payload

    @staticmethod
    def _coerce_finance_breakdown(raw: Any) -> Optional[Dict[str, int]]:
        if raw is None or not isinstance(raw, Mapping):
            return None
        out: Dict[str, int] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = int(v)
            except (TypeError, ValueError):
                continue
        return out or None

    def get_finance_report_text(self) -> str:
        self._ensure_history_fields()

        owner_expectation_labels = {
            "rebuild": "再建",
            "playoff_race": "PO争い",
            "promotion": "昇格必達",
            "title_challenge": "優勝挑戦",
            "title_or_bust": "優勝必須",
        }

        lines = [
            f"{self.name} 経営レポート",
            "==============================",
            f"所持金: {int(self.money):,}",
            f"給与予算: {int(self.payroll_budget):,}",
            f"人気: {int(self.popularity)} / 市場規模: {float(self.market_size):.2f}",
            f"ファン基盤: {int(self.fan_base):,} / シーズンチケット基盤: {int(self.season_ticket_base):,}",
            f"スポンサー力: {int(self.sponsor_power)}",
            (
                f"施設: アリーナLv{int(self.arena_level)} / 育成Lv{int(self.training_facility_level)} "
                f"/ メディカルLv{int(self.medical_facility_level)} / フロントLv{int(self.front_office_level)}"
            ),
            f"オーナー期待値: {owner_expectation_labels.get(self.owner_expectation, self.owner_expectation)}",
            f"オーナー信頼度: {int(self.owner_trust)} / 100",
            (
                f"前季収支: 収入{int(self.revenue_last_season):,} / 支出{int(self.expense_last_season):,} "
                f"/ 収支{int(self.cashflow_last_season):+,}"
            ),
        ]

        if self.owner_missions:
            active_titles = " / ".join(m.get("title", "-") for m in self.owner_missions[:2])
            if active_titles:
                lines.append(f"今季ノルマ: {active_titles}")

        if self.finance_history:
            latest = self.finance_history[-1]
            if latest.get("note"):
                lines.append(f"最新メモ: {latest['note']}")

        lines.append("内訳・財務推移の詳細は経営ウィンドウ「詳細レポート」を参照。")

        return "\n".join(lines)

    def get_finance_report_detail_text(self, *, history_limit: int = 5) -> str:
        from basketball_sim.systems.finance_report_display import format_finance_report_detail_lines

        return "\n".join(format_finance_report_detail_lines(self, history_limit=history_limit))


    def _get_owner_expectation_label(self) -> str:
        label_map = {
            "rebuild": "再建",
            "playoff_race": "PO争い",
            "promotion": "昇格必達",
            "title_challenge": "優勝挑戦",
            "title_or_bust": "優勝必須",
        }
        return label_map.get(self.owner_expectation, self.owner_expectation)

    def _estimate_latest_rank_for_owner(self) -> Optional[int]:
        seasons = list(getattr(self, "history_seasons", []) or [])
        latest = seasons[-1] if seasons else None
        if isinstance(latest, dict):
            try:
                rank = latest.get("rank")
                if rank is not None:
                    return int(rank)
            except (TypeError, ValueError):
                pass

        total_games = int(self.regular_wins + self.regular_losses)
        if total_games <= 0:
            return None

        win_pct = self.regular_wins / max(1, total_games)
        if win_pct >= 0.78:
            return 1
        if win_pct >= 0.68:
            return 2
        if win_pct >= 0.58:
            return 4
        if win_pct >= 0.50:
            return 7
        if win_pct >= 0.42:
            return 10
        return 13

    def _build_owner_mission_templates(self) -> List[dict]:
        expectation = getattr(self, "owner_expectation", "playoff_race")
        league_level = int(getattr(self, "league_level", 3))
        trust = int(getattr(self, "owner_trust", 50))
        latest_completed = None
        seasons = list(getattr(self, "history_seasons", []) or [])
        if seasons:
            latest_completed = seasons[-1] if isinstance(seasons[-1], dict) else None

        if isinstance(latest_completed, dict):
            latest_wins = self._safe_to_int(
                latest_completed.get("wins", latest_completed.get("regular_wins", 0)),
                0,
            )
            latest_losses = self._safe_to_int(
                latest_completed.get("losses", latest_completed.get("regular_losses", 0)),
                0,
            )
            total_games = max(30, latest_wins + latest_losses)
        else:
            total_games = max(30, int(self.regular_wins + self.regular_losses) or 30)

        if expectation == "rebuild":
            win_target = max(12, int(total_games * 0.40))
        elif expectation == "promotion":
            win_target = max(18, int(total_games * 0.63))
        elif expectation == "title_challenge":
            win_target = max(20, int(total_games * 0.67))
        elif expectation == "title_or_bust":
            win_target = max(22, int(total_games * 0.72))
        else:
            win_target = max(15, int(total_games * 0.50))

        if league_level == 1:
            rank_target = 8 if expectation in {"playoff_race", "rebuild"} else 4
            if expectation == "title_or_bust":
                rank_target = 2
        elif league_level == 2:
            rank_target = 4 if expectation in {"promotion", "title_challenge", "title_or_bust"} else 8
        else:
            rank_target = 2 if expectation in {"promotion", "title_challenge", "title_or_bust"} else 6

        positive_cashflow_target = 0 if trust >= 45 else 500_000
        payroll_limit = int(getattr(self, "payroll_budget", 0))

        youth_target = 2 if expectation == "rebuild" else 1
        if trust >= 70 and expectation in {"title_challenge", "title_or_bust"}:
            youth_target = 0

        templates = [
            {
                "mission_id": "wins_target",
                "title": f"{win_target}勝以上を確保",
                "description": "レギュラーシーズンで一定以上の勝ち星を積み、競争力を示す。",
                "category": "results",
                "target_type": "wins_at_least",
                "target_value": win_target,
                "reward_trust": 6,
                "penalty_trust": -7,
                "priority": "high",
            },
            {
                "mission_id": "rank_target",
                "title": f"{rank_target}位以内で終える",
                "description": "順位面でも存在感を示し、オーナーの期待ラインを上回る。",
                "category": "results",
                "target_type": "rank_at_most",
                "target_value": rank_target,
                "reward_trust": 7,
                "penalty_trust": -8,
                "priority": "high",
            },
            {
                "mission_id": "finance_target",
                "title": "単年収支を黒字で終える" if positive_cashflow_target <= 0 else "単年収支の大幅悪化を避ける",
                "description": "経営の健全性を保ち、補強余力を残す。",
                "category": "finance",
                "target_type": "cashflow_at_least",
                "target_value": positive_cashflow_target,
                "reward_trust": 5,
                "penalty_trust": -6,
                "priority": "medium",
            },
        ]

        if payroll_limit > 0:
            templates.append(
                {
                    "mission_id": "payroll_discipline",
                    "title": "給与予算を大きく超過しない",
                    "description": "大型契約を出し過ぎず、来季運営に余白を残す。",
                    "category": "finance",
                    "target_type": "payroll_within_budget",
                    "target_value": payroll_limit,
                    "reward_trust": 4,
                    "penalty_trust": -5,
                    "priority": "medium",
                }
            )

        if youth_target > 0:
            templates.append(
                {
                    "mission_id": "youth_development",
                    "title": f"若手有望株を{youth_target}人以上育成",
                    "description": "24歳以下の主力候補を育て、将来の核を作る。",
                    "category": "development",
                    "target_type": "young_core_count_at_least",
                    "target_value": youth_target,
                    "reward_trust": 4,
                    "penalty_trust": -3,
                    "priority": "medium",
                }
            )

        return templates

    def refresh_owner_missions(self, force: bool = False) -> List[dict]:
        self._ensure_history_fields()
        if self.owner_missions and not force:
            return self.owner_missions

        self.owner_missions = []
        for template in self._build_owner_mission_templates():
            mission = dict(template)
            mission["status"] = "active"
            mission["progress_text"] = "未評価"
            mission["season_label"] = None
            self.owner_missions.append(mission)
        return self.owner_missions

    def _get_latest_completed_season_for_owner(self) -> Optional[dict]:
        self._ensure_history_fields()
        seasons = list(getattr(self, "history_seasons", []) or [])
        if not seasons:
            return None

        preferred_row = None
        fallback_row = None

        for row in reversed(seasons):
            if not isinstance(row, dict):
                continue

            wins = self._safe_to_int(row.get("wins", row.get("regular_wins", 0)), 0)
            losses = self._safe_to_int(row.get("losses", row.get("regular_losses", 0)), 0)

            if wins <= 0 and losses <= 0:
                continue

            if fallback_row is None:
                fallback_row = row

            rank_raw = row.get("rank")
            if rank_raw is not None and str(rank_raw).strip() != "":
                preferred_row = row
                break

        latest = preferred_row or fallback_row
        if latest is None:
            return None

        wins = self._safe_to_int(latest.get("wins", latest.get("regular_wins", 0)), 0)
        losses = self._safe_to_int(latest.get("losses", latest.get("regular_losses", 0)), 0)

        rank_raw = latest.get("rank")
        rank_value = None
        try:
            if rank_raw is not None and str(rank_raw).strip() != "":
                rank_value = int(rank_raw)
        except (TypeError, ValueError):
            rank_value = None

        return {
            "season_index": latest.get("season_index", latest.get("season")),
            "wins": wins,
            "losses": losses,
            "rank": rank_value,
            "points_for": self._safe_to_int(latest.get("points_for", 0), 0),
            "points_against": self._safe_to_int(latest.get("points_against", 0), 0),
            "point_diff": self._safe_to_int(latest.get("point_diff", 0), 0),
        }

    def _count_young_core_players(self) -> int:
        count = 0
        for player in getattr(self, "players", []):
            if getattr(player, "is_retired", False):
                continue
            if int(getattr(player, "age", 99)) <= 24 and int(getattr(player, "ovr", 0)) >= 68:
                count += 1
        return count

    def evaluate_owner_missions(self, season_label: Optional[str] = None) -> dict:
        self._ensure_history_fields()
        missions = self.refresh_owner_missions(force=False)

        latest_completed = self._get_latest_completed_season_for_owner()

        if latest_completed is not None:
            wins = int(latest_completed.get("wins", 0))
            latest_rank = latest_completed.get("rank")
        else:
            wins = int(getattr(self, "regular_wins", 0))
            latest_rank = self._estimate_latest_rank_for_owner()

        cashflow = int(getattr(self, "cashflow_last_season", 0))
        payroll_now = int(sum(max(0, int(getattr(p, "salary", 0))) for p in getattr(self, "players", [])))
        young_core_count = self._count_young_core_players()

        results = []
        trust_delta_total = 0

        for mission in missions:
            target_type = mission.get("target_type")
            target_value = mission.get("target_value", 0)
            success = False
            progress_text = "未評価"

            if target_type == "wins_at_least":
                success = wins >= int(target_value)
                progress_text = f"{wins}勝 / 目標{int(target_value)}勝"
            elif target_type == "rank_at_most":
                if latest_rank is None:
                    success = False
                    progress_text = f"順位不明 / 目標{int(target_value)}位以内"
                else:
                    success = latest_rank <= int(target_value)
                    progress_text = f"{latest_rank}位 / 目標{int(target_value)}位以内"
            elif target_type == "cashflow_at_least":
                success = cashflow >= int(target_value)
                progress_text = f"収支{cashflow:+,} / 目標{int(target_value):+,}"
            elif target_type == "payroll_within_budget":
                success = payroll_now <= int(target_value * 1.08)
                progress_text = f"給与総額{payroll_now:,} / 目標{int(target_value):,}以内"
            elif target_type == "young_core_count_at_least":
                success = young_core_count >= int(target_value)
                progress_text = f"若手有望株{young_core_count}人 / 目標{int(target_value)}人"
            else:
                progress_text = "評価対象外"

            trust_delta = int(mission.get("reward_trust", 0) if success else mission.get("penalty_trust", 0))
            if not success and target_type == "cashflow_at_least":
                shortfall = int(target_value) - cashflow
                if shortfall <= OWNER_TRUST_MILD_DEFICIT_THRESHOLD:
                    # 軽微な赤字（または目標との差が小さいケース）は減点を緩める。
                    trust_delta = max(trust_delta, -2)

            # 単年での急落を防ぐガードレール（ミッション失敗を無効化しない範囲）。
            if trust_delta_total + trust_delta < OWNER_TRUST_MAX_NEGATIVE_DELTA_PER_SEASON:
                trust_delta = OWNER_TRUST_MAX_NEGATIVE_DELTA_PER_SEASON - trust_delta_total
            trust_delta_total += trust_delta

            result_row = {
                "mission_id": mission.get("mission_id"),
                "title": mission.get("title", "-"),
                "status": "success" if success else "failed",
                "progress_text": progress_text,
                "trust_delta": trust_delta,
                "season_label": season_label,
            }
            mission.update(result_row)
            results.append(result_row)

        self.owner_trust = int(max(0, min(100, self.owner_trust + trust_delta_total)))
        resolved_season_label = season_label
        if not resolved_season_label and latest_completed is not None:
            idx = latest_completed.get("season_index")
            if idx is not None:
                resolved_season_label = f"Season {idx}"

        history_payload = {
            "season_label": resolved_season_label,
            "owner_expectation": self.owner_expectation,
            "owner_trust_after": int(self.owner_trust),
            "trust_delta_total": int(trust_delta_total),
            "results": results,
        }
        self.owner_mission_history.append(history_payload)
        return history_payload

    @staticmethod
    def _owner_mission_category_label(category: Any) -> str:
        labels = {
            "results": "成績",
            "finance": "財務",
            "development": "育成",
        }
        key = str(category or "").strip()
        return labels.get(key, key or "その他")

    @staticmethod
    def _owner_mission_priority_label(priority: Any) -> str:
        labels = {"high": "高", "medium": "中", "low": "低"}
        key = str(priority or "medium").strip()
        return labels.get(key, key)

    @staticmethod
    def _owner_mission_target_summary(mission: dict) -> str:
        tt = mission.get("target_type")
        tv = mission.get("target_value", 0)
        try:
            tv_int = int(tv)
        except (TypeError, ValueError):
            tv_int = 0
        if tt == "wins_at_least":
            return f"目標: {tv_int}勝以上"
        if tt == "rank_at_most":
            return f"目標: {tv_int}位以内"
        if tt == "cashflow_at_least":
            return f"目標: 収支 {tv_int:+,} 円以上"
        if tt == "payroll_within_budget":
            return f"目標: 給与総額 {tv_int:,} 円＋8%以内"
        if tt == "young_core_count_at_least":
            return f"目標: 若手有望株 {tv_int} 人以上"
        return ""

    def get_owner_mission_report_text(self) -> str:
        self._ensure_history_fields()
        missions = self.refresh_owner_missions(force=False)

        lines = [
            f"{self.name} オーナーミッション",
            "==============================",
            f"オーナー方針: {self._get_owner_expectation_label()}",
            f"オーナー信頼度: {int(self.owner_trust)} / 100",
            "",
            "【今季ミッション一覧】",
        ]

        if missions:
            for i, mission in enumerate(missions, start=1):
                cat = self._owner_mission_category_label(mission.get("category"))
                pr = self._owner_mission_priority_label(mission.get("priority"))
                title = mission.get("title", "-")
                lines.append(f"{i}. [{cat}・優先度:{pr}] {title}")
                desc = str(mission.get("description", "") or "").strip()
                if desc:
                    lines.append(f"   説明: {desc}")
                tgt = self._owner_mission_target_summary(mission)
                if tgt:
                    lines.append(f"   {tgt}")
                try:
                    rw = int(mission.get("reward_trust", 0))
                    pn = int(mission.get("penalty_trust", 0))
                except (TypeError, ValueError):
                    rw, pn = 0, 0
                lines.append(f"   報酬/ペナルティ: 達成で信頼 {rw:+} ／ 未達で信頼 {pn:+}")
                lines.append(f"   進捗: {mission.get('progress_text', '未評価')}")
                lines.append("")
        else:
            lines.append("- まだミッションは設定されていません。")
            lines.append("")

        if self.owner_mission_history:
            latest = self.owner_mission_history[-1]
            lines.append("【直近シーズンの評価】")
            sl = latest.get("season_label")
            if sl:
                lines.append(f"対象: {sl}")
            lines.append(
                f"信頼度の合計変動: {int(latest.get('trust_delta_total', 0)):+} "
                f"→ 評価後 {int(latest.get('owner_trust_after', self.owner_trust))} / 100"
            )
            lines.append("内訳:")
            for row in latest.get("results", []):
                state = "達成" if row.get("status") == "success" else "未達"
                try:
                    td = int(row.get("trust_delta", 0))
                except (TypeError, ValueError):
                    td = 0
                lines.append(
                    f"  - {row.get('title', '-')}: {state}（信頼 {td:+}）"
                    f" - {row.get('progress_text', '')}"
                )
            lines.append("")

            older = list(reversed(self.owner_mission_history[:-1]))[:2]
            if older:
                lines.append("【過去の評価（最大2件）】")
                for entry in older:
                    label = entry.get("season_label") or "（シーズン未記録）"
                    try:
                        total_d = int(entry.get("trust_delta_total", 0))
                        after = int(entry.get("owner_trust_after", 0))
                    except (TypeError, ValueError):
                        total_d, after = 0, int(self.owner_trust)
                    lines.append(f"- {label}: 信頼合計 {total_d:+} → 評価後 {after} / 100")
                lines.append("")

        lines.append("※ ミッションの編集は行えません。評価はオフシーズン処理で更新されます。")

        return "\n".join(lines).rstrip()


    def count_foreign_players(self, players: Optional[List[Player]] = None) -> int:
        """
        チーム内の外国籍枠扱い人数を返す。
        players を渡した場合は、その対象集合だけを数える。
        """
        target_players = self.players if players is None else players
        rule = league_contract_active_rule()
        foreign, _special = count_regulation_slots(target_players, rule)
        return int(foreign)

    def count_asia_naturalized_players(self, players: Optional[List[Player]] = None) -> int:
        """
        チーム内の Asia / 帰化枠扱い人数を返す。
        players を渡した場合は、その対象集合だけを数える。
        """
        target_players = self.players if players is None else players
        rule = league_contract_active_rule()
        _foreign, special = count_regulation_slots(target_players, rule)
        return int(special)

    def get_nationality_slot_summary(self, players: Optional[List[Player]] = None) -> dict:
        """
        日本独自ルール用の国籍枠サマリーを返す。
        roster と active/lineup の両方で再利用しやすい共通API。
        """
        target_players = self.players if players is None else players
        rule = league_contract_active_rule()
        foreign_count, asia_nat_count = count_regulation_slots(target_players, rule)
        total_count = len(target_players)
        domestic_count = max(0, total_count - foreign_count - asia_nat_count)
        return {
            "total": int(total_count),
            "domestic": int(domestic_count),
            "foreign": int(foreign_count),
            "asia_or_naturalized": int(asia_nat_count),
        }

    def can_add_player_by_japan_rule(
        self,
        player: Player,
        foreign_limit: int = 3,
        asia_nat_limit: int = 1,
        players: Optional[List[Player]] = None,
    ) -> bool:
        """
        日本独自ルール前提で、その選手を追加可能かを返す。
        デフォルトは登録枠想定（外国籍3、Asia/帰化1）。
        """
        target_players = list(self.players if players is None else players)
        rule = league_contract_active_rule()
        foreign_c, special_c = count_regulation_slots(target_players, rule)
        bucket = player_regulation_bucket_from_rule(player, rule)

        if bucket == "foreign":
            return foreign_c < int(foreign_limit)
        if bucket == "special":
            return special_c < int(asia_nat_limit)
        return True

    def add_player(self, player: Player, *, force: bool = False):
        """
        本契約ロスターへ追加。force=True はドラフト/トレード処理など、
        直後に枠調整する内部経路のみ。
        """
        if player in self.players:
            return

        if not force:
            from basketball_sim.systems.roster_rules import RosterViolationError, can_add_contract_player

            ok, reason = can_add_contract_player(self, player)
            if not ok:
                raise RosterViolationError(reason)

        self.players.append(player)
        player.team_id = self.team_id

    def remove_player(self, player: Player):
        if player in self.players:
            self.players.remove(player)
            player.team_id = None

        player_id = getattr(player, "player_id", None)
        if player_id is not None and getattr(self, "injured_reserve_ids", None):
            self.injured_reserve_ids = [pid for pid in self.injured_reserve_ids if pid != player_id]
        if player_id in self.starting_lineup:
            self.starting_lineup = [
                pid for pid in self.starting_lineup
                if pid != player_id
            ]

        if self.sixth_man_id == player_id:
            self.sixth_man_id = None

        if player_id in self.bench_order:
            self.bench_order = [pid for pid in self.bench_order if pid != player_id]

    def add_history_transaction(
        self,
        transaction_type: str,
        player: Optional[Player] = None,
        note: str = "",
        *,
        trade_cash_delta: Optional[int] = None,
        trade_counterparty_team_id: Optional[int] = None,
        trade_counterparty_name: str = "",
    ):
        """
        history_transactions に1件追加。トレード現金は trade_cash_delta 等で機械可読に残せる
        （`TRADE_CASH_ACCOUNTING_POLICY.md`）。未指定時は従来どおり note のみ。
        trade_cash_delta: 当チーム視点の現金増減（支払いは負、受取は正）。
        """
        self._ensure_history_fields()
        row: Dict[str, Any] = {
            "transaction_type": transaction_type,
            "player_id": getattr(player, "player_id", None) if player is not None else None,
            "player_name": getattr(player, "name", "") if player is not None else "",
            "note": note,
        }
        if trade_cash_delta is not None:
            row["trade_cash_delta"] = int(trade_cash_delta)
            tid = trade_counterparty_team_id
            row["trade_counterparty_team_id"] = int(tid) if tid is not None else None
            row["trade_counterparty_name"] = str(trade_counterparty_name or "")
        self.history_transactions.append(row)

    def add_history_award(self, award_type: str, note: str = ""):
        self._ensure_history_fields()
        self.history_awards.append({
            "award_type": award_type,
            "note": note,
        })

    def add_history_milestone(self, milestone_type="milestone", note: str = ""):
        self._ensure_history_fields()

        if isinstance(milestone_type, dict):
            payload = milestone_type.copy()
        else:
            payload = {
                "milestone_type": milestone_type,
                "note": note,
            }

        self.history_milestones.append(payload)

    def _build_archive_payload(self, player: Player) -> dict:
        return {
            "player_id": getattr(player, "player_id", None),
            "player_name": getattr(player, "name", "Unknown"),
            "career_points": getattr(player, "career_points", 0),
            "career_rebounds": getattr(player, "career_rebounds", 0),
            "career_assists": getattr(player, "career_assists", 0),
            "career_blocks": getattr(player, "career_blocks", 0),
            "career_steals": getattr(player, "career_steals", 0),
            "career_games_played": getattr(player, "career_games_played", 0),
            "peak_ovr": getattr(player, "peak_ovr", getattr(player, "ovr", 0)),
            "is_hall_of_famer": getattr(player, "is_hall_of_famer", False),
            "is_icon": getattr(player, "is_icon", False),
        }

    def archive_player_record(self, player: Player):
        self._ensure_history_fields()

        payload = self._build_archive_payload(player)
        player_id = payload["player_id"]

        for row in self.all_time_player_archive:
            if row.get("player_id") == player_id:
                row.update(payload)
                return

        self.all_time_player_archive.append(payload)

    def add_club_legend(self, player: Player, reason: str = "", legacy_score: float = 0.0):
        self._ensure_history_fields()
        self.archive_player_record(player)

        player_id = getattr(player, "player_id", None)
        payload = {
            "player_id": player_id,
            "player_name": getattr(player, "name", "Unknown"),
            "peak_ovr": getattr(player, "peak_ovr", getattr(player, "ovr", 0)),
            "career_points": getattr(player, "career_points", 0),
            "career_games_played": getattr(player, "career_games_played", 0),
            "legacy_score": round(float(legacy_score), 2),
            "reason": reason,
        }

        for row in self.club_legends:
            if row.get("player_id") == player_id:
                row.update(payload)
                self.club_legends.sort(
                    key=lambda x: (
                        x.get("legacy_score", 0),
                        x.get("peak_ovr", 0),
                        x.get("career_points", 0),
                    ),
                    reverse=True
                )
                return

        self.club_legends.append(payload)
        self.club_legends.sort(
            key=lambda x: (
                x.get("legacy_score", 0),
                x.get("peak_ovr", 0),
                x.get("career_points", 0),
            ),
            reverse=True
        )

    def calculate_player_legacy_score(self, player: Player) -> float:
        team_career_seasons = 0
        team_career_events = 0

        for row in getattr(player, "career_history", []):
            if row.get("team") == self.name:
                team_career_events += 1
                if row.get("event") not in ("Trade", "Free Agent", "Draft", "Retire"):
                    team_career_seasons += 1

        score = 0.0
        score += getattr(player, "career_points", 0) / 900.0
        score += getattr(player, "career_games_played", 0) / 70.0
        score += getattr(player, "peak_ovr", getattr(player, "ovr", 0)) * 0.22
        score += team_career_events * 1.5
        score += team_career_seasons * 2.0

        if getattr(player, "is_hall_of_famer", False):
            score += 8.0
        if getattr(player, "is_icon", False):
            score += 6.0

        return round(score, 2)

    def maybe_add_club_legend(self, player: Player):
        self.archive_player_record(player)
        legacy_score = self.calculate_player_legacy_score(player)

        reasons = []
        if getattr(player, "career_points", 0) >= 4000:
            reasons.append("Scoring Legacy")
        if getattr(player, "career_games_played", 0) >= 180:
            reasons.append("Longevity")
        if getattr(player, "peak_ovr", getattr(player, "ovr", 0)) >= 84:
            reasons.append("Star Peak")
        if getattr(player, "is_hall_of_famer", False):
            reasons.append("Hall of Famer")
        if getattr(player, "is_icon", False):
            reasons.append("Icon Player")

        passed = False
        if legacy_score >= 28:
            passed = True
        elif getattr(player, "career_points", 0) >= 6000 and getattr(player, "peak_ovr", getattr(player, "ovr", 0)) >= 82:
            passed = True
        elif getattr(player, "career_games_played", 0) >= 260 and getattr(player, "peak_ovr", getattr(player, "ovr", 0)) >= 80:
            passed = True

        if passed:
            self.add_club_legend(
                player=player,
                reason=", ".join(reasons[:3]),
                legacy_score=legacy_score
            )

    def archive_current_players_for_history(self):
        self._ensure_history_fields()
        for player in self.players:
            self.archive_player_record(player)

    def _build_all_time_rows(self) -> List[dict]:
        self._ensure_history_fields()

        rows = []
        used_ids = set()

        for player in self.players:
            player_id = getattr(player, "player_id", None)
            rows.append({
                "player_id": player_id,
                "player_name": getattr(player, "name", "Unknown"),
                "career_points": getattr(player, "career_points", 0),
                "career_rebounds": getattr(player, "career_rebounds", 0),
                "career_assists": getattr(player, "career_assists", 0),
                "career_blocks": getattr(player, "career_blocks", 0),
                "career_steals": getattr(player, "career_steals", 0),
                "career_games_played": getattr(player, "career_games_played", 0),
                "peak_ovr": getattr(player, "peak_ovr", getattr(player, "ovr", 0)),
                "legacy_score": getattr(player, "hall_of_fame_score", 0.0),
            })
            used_ids.add(player_id)

        for archived in self.all_time_player_archive:
            player_id = archived.get("player_id")
            if player_id in used_ids:
                continue
            rows.append({
                "player_id": player_id,
                "player_name": archived.get("player_name", "Unknown"),
                "career_points": archived.get("career_points", 0),
                "career_rebounds": archived.get("career_rebounds", 0),
                "career_assists": archived.get("career_assists", 0),
                "career_blocks": archived.get("career_blocks", 0),
                "career_steals": archived.get("career_steals", 0),
                "career_games_played": archived.get("career_games_played", 0),
                "peak_ovr": archived.get("peak_ovr", 0),
                "legacy_score": archived.get("legacy_score", 0.0),
            })
            used_ids.add(player_id)

        for legend in self.club_legends:
            player_id = legend.get("player_id")
            if player_id in used_ids:
                continue
            rows.append({
                "player_id": player_id,
                "player_name": legend.get("player_name", "Unknown"),
                "career_points": legend.get("career_points", 0),
                "career_rebounds": legend.get("career_rebounds", 0),
                "career_assists": legend.get("career_assists", 0),
                "career_blocks": legend.get("career_blocks", 0),
                "career_steals": legend.get("career_steals", 0),
                "career_games_played": legend.get("career_games_played", 0),
                "peak_ovr": legend.get("peak_ovr", 0),
                "legacy_score": legend.get("legacy_score", 0.0),
            })
            used_ids.add(player_id)

        return rows

    def _build_single_season_rows(self) -> List[dict]:
        rows = []
        for season in self.history_seasons:
            season_index = season.get("season_index", "?")
            for p in season.get("top_players", []):
                rows.append({
                    "season_index": season_index,
                    "player_id": p.get("player_id"),
                    "player_name": p.get("player_name", "Unknown"),
                    "season_points": p.get("season_points", 0),
                    "season_assists": p.get("season_assists", 0),
                    "season_rebounds": p.get("season_rebounds", 0),
                    "season_blocks": p.get("season_blocks", 0),
                    "season_steals": p.get("season_steals", 0),
                })
        return rows

    def get_single_season_points_records(self, top_n: int = 5) -> List[dict]:
        rows = self._build_single_season_rows()
        rows.sort(
            key=lambda x: (
                x.get("season_points", 0),
                x.get("season_assists", 0),
                x.get("season_rebounds", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_single_season_assist_records(self, top_n: int = 5) -> List[dict]:
        rows = self._build_single_season_rows()
        rows.sort(
            key=lambda x: (
                x.get("season_assists", 0),
                x.get("season_points", 0),
                x.get("season_rebounds", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_single_season_rebound_records(self, top_n: int = 5) -> List[dict]:
        rows = self._build_single_season_rows()
        rows.sort(
            key=lambda x: (
                x.get("season_rebounds", 0),
                x.get("season_points", 0),
                x.get("season_assists", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_single_season_block_records(self, top_n: int = 5) -> List[dict]:
        rows = self._build_single_season_rows()
        rows.sort(
            key=lambda x: (
                x.get("season_blocks", 0),
                x.get("season_rebounds", 0),
                x.get("season_points", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_single_season_steal_records(self, top_n: int = 5) -> List[dict]:
        rows = self._build_single_season_rows()
        rows.sort(
            key=lambda x: (
                x.get("season_steals", 0),
                x.get("season_assists", 0),
                x.get("season_points", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def _calc_per_game(self, total_value: int, games_played: int) -> float:
        if games_played <= 0:
            return 0.0
        return round(total_value / games_played, 2)

    def _calc_impact_score(self, row: dict) -> float:
        gp = row.get("career_games_played", 0)
        ppg = self._calc_per_game(row.get("career_points", 0), gp)
        rpg = self._calc_per_game(row.get("career_rebounds", 0), gp)
        apg = self._calc_per_game(row.get("career_assists", 0), gp)
        bpg = self._calc_per_game(row.get("career_blocks", 0), gp)
        spg = self._calc_per_game(row.get("career_steals", 0), gp)

        impact = (
            ppg * 1.2 +
            rpg * 0.9 +
            apg * 1.0 +
            bpg * 1.5 +
            spg * 1.5
        )
        return round(impact, 2)

    def get_all_time_scorers(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_points", 0),
                x.get("career_games_played", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_all_time_ppg(self, top_n: int = 5, min_games: int = 20) -> List[dict]:
        rows = self._build_all_time_rows()
        qualified_rows = [row for row in rows if row.get("career_games_played", 0) >= min_games]

        for row in qualified_rows:
            row["ppg"] = self._calc_per_game(
                row.get("career_points", 0),
                row.get("career_games_played", 0)
            )

        qualified_rows.sort(
            key=lambda x: (
                x.get("ppg", 0.0),
                x.get("career_points", 0),
                x.get("career_games_played", 0),
            ),
            reverse=True
        )
        return qualified_rows[:top_n]

    def get_all_time_rpg(self, top_n: int = 5, min_games: int = 20) -> List[dict]:
        rows = self._build_all_time_rows()
        qualified_rows = [row for row in rows if row.get("career_games_played", 0) >= min_games]

        for row in qualified_rows:
            row["rpg"] = self._calc_per_game(
                row.get("career_rebounds", 0),
                row.get("career_games_played", 0)
            )

        qualified_rows.sort(
            key=lambda x: (
                x.get("rpg", 0.0),
                x.get("career_rebounds", 0),
                x.get("career_games_played", 0),
            ),
            reverse=True
        )
        return qualified_rows[:top_n]

    def get_all_time_apg(self, top_n: int = 5, min_games: int = 20) -> List[dict]:
        rows = self._build_all_time_rows()
        qualified_rows = [row for row in rows if row.get("career_games_played", 0) >= min_games]

        for row in qualified_rows:
            row["apg"] = self._calc_per_game(
                row.get("career_assists", 0),
                row.get("career_games_played", 0)
            )

        qualified_rows.sort(
            key=lambda x: (
                x.get("apg", 0.0),
                x.get("career_assists", 0),
                x.get("career_games_played", 0),
            ),
            reverse=True
        )
        return qualified_rows[:top_n]

    def get_all_time_impact(self, top_n: int = 5, min_games: int = 20) -> List[dict]:
        rows = self._build_all_time_rows()
        qualified_rows = [row for row in rows if row.get("career_games_played", 0) >= min_games]

        for row in qualified_rows:
            row["impact"] = self._calc_impact_score(row)
            gp = row.get("career_games_played", 0)
            row["ppg"] = self._calc_per_game(row.get("career_points", 0), gp)
            row["rpg"] = self._calc_per_game(row.get("career_rebounds", 0), gp)
            row["apg"] = self._calc_per_game(row.get("career_assists", 0), gp)

        qualified_rows.sort(
            key=lambda x: (
                x.get("impact", 0.0),
                x.get("career_points", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return qualified_rows[:top_n]

    def get_all_time_games(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_games_played", 0),
                x.get("career_points", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_all_time_assists(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_assists", 0),
                x.get("career_games_played", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_all_time_rebounds(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_rebounds", 0),
                x.get("career_games_played", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_all_time_blocks(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_blocks", 0),
                x.get("career_games_played", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def get_all_time_steals(self, top_n: int = 5) -> List[dict]:
        rows = self._build_all_time_rows()
        rows.sort(
            key=lambda x: (
                x.get("career_steals", 0),
                x.get("career_games_played", 0),
                x.get("peak_ovr", 0),
            ),
            reverse=True
        )
        return rows[:top_n]

    def record_season_history(self):
        self._ensure_history_fields()
        self.archive_current_players_for_history()

        top_players = sorted(
            [p for p in self.players if not getattr(p, "is_retired", False)],
            key=lambda p: getattr(p, "ovr", 0),
            reverse=True
        )[:5]

        top_payload = [
            {
                "player_id": getattr(p, "player_id", None),
                "player_name": getattr(p, "name", ""),
                "ovr": getattr(p, "ovr", 0),
                "acquisition_type": getattr(p, "acquisition_type", "unknown"),
                "season_points": getattr(p, "season_points", 0),
                "season_assists": getattr(p, "season_assists", 0),
                "season_rebounds": getattr(p, "season_rebounds", 0),
                "season_blocks": getattr(p, "season_blocks", 0),
                "season_steals": getattr(p, "season_steals", 0),
            }
            for p in top_players
        ]

        # Season 終了時に _record_division_season_history が先に1行積むため、
        # オフシーズンの reset で二重行にならないよう top_players のみ最終行へ合流する。
        if self.history_seasons:
            last = self.history_seasons[-1]
            if isinstance(last, dict) and not last.get("top_players"):
                last["top_players"] = top_payload
                return

        self.history_seasons.append(
            {
                "season_index": len(self.history_seasons) + 1,
                "league_level": self.league_level,
                "regular_wins": self.regular_wins,
                "regular_losses": self.regular_losses,
                "points_for": self.regular_points_for,
                "points_against": self.regular_points_against,
                "point_diff": self.regular_points_for - self.regular_points_against,
                "team_power": round(self.team_power, 2),
                "coach_style": self.coach_style,
                "strategy": self.strategy,
                "usage_policy": self.usage_policy,
                "bench_order": self.bench_order[:],
                "top_players": top_payload,
            }
        )

    def _get_available_players(self) -> List[Player]:
        return [
            p for p in self.players
            if not p.is_injured() and not p.is_retired
        ]

    def _select_balanced_starting_five(self, players: List[Player]) -> List[Player]:
        sorted_players = sorted(players, key=lambda p: p.get_effective_ovr(), reverse=True)

        starters = []
        required_positions = ["PG", "SG", "SF", "PF", "C"]

        for pos in required_positions:
            pos_candidates = [p for p in sorted_players if getattr(p, "position", "SF") == pos and p not in starters]
            if pos_candidates:
                starters.append(pos_candidates[0])

        if len(starters) < 5:
            for p in sorted_players:
                if p in starters:
                    continue
                starters.append(p)
                if len(starters) >= 5:
                    break

        return starters[:5]

    def _get_starting_five_from_custom_lineup(self) -> List[Player]:
        if not self.starting_lineup:
            return []

        available = self._get_available_players()
        available_map = {
            getattr(p, "player_id", None): p
            for p in available
        }

        lineup = []
        used_ids = set()

        for player_id in self.starting_lineup:
            if player_id in used_ids:
                continue
            player = available_map.get(player_id)
            if player is None:
                continue
            lineup.append(player)
            used_ids.add(player_id)
            if len(lineup) >= 5:
                break

        if len(lineup) < 5:
            remaining = self._select_balanced_starting_five(
                [p for p in available if getattr(p, "player_id", None) not in used_ids]
            )
            for p in remaining:
                if getattr(p, "player_id", None) in used_ids:
                    continue
                lineup.append(p)
                used_ids.add(getattr(p, "player_id", None))
                if len(lineup) >= 5:
                    break

        return lineup[:5]

    def set_starting_lineup_by_players(self, players: List[Player]):
        valid_players = []
        used_ids = set()

        for p in players:
            if p is None:
                continue
            if p.is_injured() or p.is_retired:
                continue

            player_id = getattr(p, "player_id", None)
            if player_id in used_ids:
                continue

            if p not in self.players:
                continue

            valid_players.append(p)
            used_ids.add(player_id)

            if len(valid_players) >= 5:
                break

        self.starting_lineup = [
            getattr(p, "player_id", None)
            for p in valid_players
            if getattr(p, "player_id", None) is not None
        ]

    def clear_starting_lineup(self):
        self.starting_lineup = []

    def get_starting_five(self) -> List[Player]:
        custom_lineup = self._get_starting_five_from_custom_lineup()
        if len(custom_lineup) >= 5:
            return custom_lineup

        available = self._get_available_players()
        return self._select_balanced_starting_five(available)

    def get_sixth_man(self) -> Optional[Player]:
        available = self._get_available_players()
        starter_ids = {
            getattr(p, "player_id", None)
            for p in self.get_starting_five()
        }

        if self.sixth_man_id is not None:
            for p in available:
                if getattr(p, "player_id", None) == self.sixth_man_id and getattr(p, "player_id", None) not in starter_ids:
                    return p

        bench_candidates = [
            p for p in available
            if getattr(p, "player_id", None) not in starter_ids
        ]
        if not bench_candidates:
            return None

        return sorted(bench_candidates, key=lambda p: p.get_effective_ovr(), reverse=True)[0]

    def set_sixth_man(self, player: Optional[Player]):
        if player is None:
            self.sixth_man_id = None
            return

        if player not in self.players:
            return

        if player.is_injured() or player.is_retired:
            return

        starter_ids = {
            getattr(p, "player_id", None)
            for p in self.get_starting_five()
        }
        player_id = getattr(player, "player_id", None)
        if player_id in starter_ids:
            return

        self.sixth_man_id = player_id

    def clear_sixth_man(self):
        self.sixth_man_id = None

    def set_usage_policy(self, policy: str):
        valid_policies = {"balanced", "win_now", "development"}
        if policy in valid_policies:
            self.usage_policy = policy

    def get_usage_policy_label(self) -> str:
        label_map = {
            "balanced": "Balanced",
            "win_now": "Win Now",
            "development": "Development",
        }
        return label_map.get(self.usage_policy, "Balanced")

    def set_scout_focus(self, focus: str):
        valid_focuses = {"balanced", "shooting", "defense", "athletic", "playmaking", "inside"}
        if focus in valid_focuses:
            self.scout_focus = focus

    def get_scout_focus_label(self) -> str:
        label_map = {
            "balanced": "Balanced",
            "shooting": "Shooting",
            "defense": "Defense",
            "athletic": "Athletic",
            "playmaking": "Playmaking",
            "inside": "Inside",
        }
        return label_map.get(self.scout_focus, "Balanced")

    def set_scout_dispatch(self, dispatch: str):
        valid_dispatches = {"highschool", "college", "overseas"}
        if dispatch in valid_dispatches:
            self.scout_dispatch = dispatch

    def get_scout_dispatch_label(self) -> str:
        label_map = {
            "highschool": "High School",
            "college": "College",
            "overseas": "Overseas",
        }
        return label_map.get(getattr(self, "scout_dispatch", "college"), "College")

    def _get_available_bench_candidates(self) -> List[Player]:
        starter_ids = {
            getattr(p, "player_id", None)
            for p in self.get_starting_five()
        }
        return [
            p for p in self._get_available_players()
            if getattr(p, "player_id", None) not in starter_ids
        ]

    def get_bench_order_players(self) -> List[Player]:
        available_bench = self._get_available_bench_candidates()
        available_map = {
            getattr(p, "player_id", None): p
            for p in available_bench
        }

        ordered_players: List[Player] = []
        used_ids = set()

        order_ids: List[int] = list(self.bench_order)
        if not order_ids:
            try:
                from basketball_sim.systems.team_tactics import get_rotation_bench_order_player_ids

                order_ids = get_rotation_bench_order_player_ids(self)
            except Exception:
                order_ids = []

        for player_id in order_ids:
            player = available_map.get(player_id)
            if player is None:
                continue
            if player_id in used_ids:
                continue
            ordered_players.append(player)
            used_ids.add(player_id)

        remaining = sorted(
            [p for p in available_bench if getattr(p, "player_id", None) not in used_ids],
            key=lambda p: p.get_effective_ovr(),
            reverse=True
        )
        ordered_players.extend(remaining)
        return ordered_players

    def set_bench_order_by_players(self, players: List[Player]):
        starter_ids = {
            getattr(p, "player_id", None)
            for p in self.get_starting_five()
        }

        ordered_ids: List[int] = []
        used_ids = set()

        for p in players:
            if p is None:
                continue
            if p not in self.players:
                continue
            if p.is_injured() or p.is_retired:
                continue

            player_id = getattr(p, "player_id", None)
            if player_id is None or player_id in used_ids:
                continue
            if player_id in starter_ids:
                continue

            ordered_ids.append(player_id)
            used_ids.add(player_id)

        self.bench_order = ordered_ids

    def clear_bench_order(self):
        self.bench_order = []

    def get_coach_style_modifiers(self) -> dict:
        if self.coach_style == "offense":
            return {
                "offense_bonus": 1.5,
                "defense_bonus": 0.0,
                "development_bonus": 0.0,
            }
        elif self.coach_style == "defense":
            return {
                "offense_bonus": 0.0,
                "defense_bonus": 1.5,
                "development_bonus": 0.0,
            }
        elif self.coach_style == "development":
            return {
                "offense_bonus": 0.5,
                "defense_bonus": 0.5,
                "development_bonus": 1.5,
            }
        else:
            return {
                "offense_bonus": 0.0,
                "defense_bonus": 0.0,
                "development_bonus": 0.0,
            }

    def calculate_team_strength(self):
        starters = self.get_starting_five()
        if not starters:
            self.team_offense = 0.0
            self.team_defense = 0.0
            return

        total_offense = 0.0
        total_defense = 0.0

        for p in starters:
            off = (
                p.get_adjusted_attribute('shoot') * 0.30 +
                p.get_adjusted_attribute('three') * 0.25 +
                p.get_adjusted_attribute('drive') * 0.20 +
                p.get_adjusted_attribute('passing') * 0.15 +
                p.get_adjusted_attribute('stamina') * 0.10
            )

            dfn = (
                p.get_adjusted_attribute('defense') * 0.60 +
                p.get_adjusted_attribute('rebound') * 0.25 +
                p.get_adjusted_attribute('stamina') * 0.15
            )

            total_offense += off
            total_defense += dfn

        self.team_offense = total_offense / len(starters)
        self.team_defense = total_defense / len(starters)

        coach_mod = self.get_coach_style_modifiers()
        self.team_offense += coach_mod["offense_bonus"]
        self.team_defense += coach_mod["defense_bonus"]

    def calculate_team_power(self):
        if not self.players:
            self.team_power = 0.0
            return

        active_players = [p for p in self.players if not getattr(p, 'is_retired', False)]
        if not active_players:
            self.team_power = 0.0
            return

        sorted_players = sorted(active_players, key=lambda p: getattr(p, 'ovr', 0), reverse=True)
        top_players = sorted_players[:8]

        self.team_power = sum(getattr(p, 'ovr', 0) for p in top_players) / len(top_players)

    def record_game(self, is_win: bool, points_scored: int, points_allowed: int, is_playoff: bool = False):
        if is_win:
            self.total_wins += 1
        else:
            self.total_losses += 1

        if not is_playoff:
            if is_win:
                self.regular_wins += 1
            else:
                self.regular_losses += 1
            self.regular_points_for += points_scored
            self.regular_points_against += points_allowed

        starters = self.get_starting_five()
        import random

        for p in self.players:
            if p.is_injured() or p.is_retired:
                continue

            if p in starters:
                p.fatigue = min(100, p.fatigue + 10)
            else:
                p.fatigue = min(100, p.fatigue + 2)

            if random.random() < 0.01:
                p.injury_games_left = random.randint(1, 5)

    def process_injury_recovery(self):
        for p in self.players:
            if p.injury_games_left > 0:
                p.injury_games_left -= 1

    def reset_season_stats(self):
        self.last_season_wins = self.regular_wins
        self.last_season_losses = self.regular_losses

        self.calculate_team_power()
        self.record_season_history()

        self.regular_wins = 0
        self.regular_losses = 0
        self.regular_points_for = 0
        self.regular_points_against = 0
        self.total_wins = 0
        self.total_losses = 0


    def get_club_history_summary(self, exclude_test_seed: bool = True) -> dict:
        self._ensure_history_fields()

        seasons = list(getattr(self, "history_seasons", []) or [])
        milestones = list(getattr(self, "history_milestones", []) or [])
        awards = list(getattr(self, "history_awards", []) or [])
        legends = list(getattr(self, "club_legends", []) or [])

        total_titles = 0
        league_titles = 0
        cup_titles = 0
        international_titles = 0
        promotions = 0
        relegations = 0

        cup_keywords = (
            "天皇杯",
            "皇帝杯",
            "全日本カップ",
            "emperor",
        )
        # history_milestones は naming整理の影響で title/detail が表記ゆれします。
        # そのため、国内/国際の表示名（日本語）と旧表記（EASL/ACL 等）を両方拾えるようにします。
        international_keywords = (
            # 国内の大陸大会ルート（season.py 側）
            "acl",
            "easl",
            "東アジアトップリーグ",
            "オールアジアトーナメント",
            "アジアクラブ選手権",
            # オフシーズンの国際大会（offseason.py 側）
            "asia cup",
            "アジアカップ",
            "世界一決定戦",
            "intercontinental",
            "インターコンチネンタル",
            # 隠し要素
            "final boss",
            "FINAL BOSS",
            "nba dream team",
            "nbaドリームチーム",
            "ドリームチーム戦",
        )

        for item in milestones:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "") or "")
            category = str(item.get("category", "") or "")
            milestone_type = str(item.get("milestone_type", item.get("type", "")) or "")
            note = str(item.get("note", "") or "")
            competition_name = str(item.get("competition_name", "") or "")
            result = str(item.get("result", "") or "")

            if exclude_test_seed and "test_seed" in note.lower():
                continue

            title_blob = " | ".join(
                [
                    title.lower(),
                    note.lower(),
                    competition_name.lower(),
                    category.lower(),
                    milestone_type.lower(),
                    result.lower(),
                ]
            )

            # クラブ史の「主要実績（タイトル扱い）」としてカウントする条件。
            # 既存の「優勝」だけだと FINAL BOSS は `result="cleared"` / `title="撃破"` なので
            # カウントされないケースがあるため、撃破も国際主要実績として扱う。
            is_title = (
                "優勝" in title
                or "優勝" in note
                or "撃破" in title
                or "撃破" in note
                or milestone_type.lower() in {"champion", "winner"}
                or result.lower() in {"champion", "winner", "victory", "cleared"}
            )

            if is_title:
                total_titles += 1

                if any(keyword in title_blob for keyword in international_keywords):
                    international_titles += 1
                elif any(keyword in title_blob for keyword in cup_keywords) or "カップ" in title:
                    cup_titles += 1
                else:
                    league_titles += 1

            if "昇格" in title or milestone_type == "promotion" or "promot" in category.lower():
                promotions += 1

            if "降格" in title or milestone_type == "relegation" or "relegat" in category.lower():
                relegations += 1

        def _normalize_season_row(row: dict) -> dict:
            # 返り値のみ整形（history_seasons 本体は変更しない）
            copied = dict(row)
            season_value = copied.get("season")
            if season_value is None:
                season_value = copied.get("season_index")
            copied["season"] = self._format_history_season_label(season_value)
            return copied

        latest_season = _normalize_season_row(seasons[-1]) if seasons and isinstance(seasons[-1], dict) else {}
        if seasons:
            raw_recent = seasons[-5:] if len(seasons) > 5 else seasons[:]
        else:
            raw_recent = []
        # 常に list を返す（空なら []）
        recent_five_years: List[dict] = [_normalize_season_row(r) for r in raw_recent if isinstance(r, dict)]

        return {
            "club_name": getattr(self, "name", "Unknown Club"),
            "team_id": getattr(self, "team_id", None),
            "current_league_level": getattr(self, "league_level", None),
            "season_count": len(seasons),
            "latest_season": latest_season,
            "recent_five_years": recent_five_years,
            "total_titles": total_titles,
            "league_titles": league_titles,
            "cup_titles": cup_titles,
            "international_titles": international_titles,
            "promotions": promotions,
            "relegations": relegations,
            "legend_count": len(legends),
            "award_count": len(awards),
            "milestone_count": len(
                [
                    m
                    for m in milestones
                    if isinstance(m, dict) and not (exclude_test_seed and "test_seed" in str(m.get("note", "") or "").lower())
                ]
            ),
        }

    def get_club_history_season_rows(self, limit: int | None = None) -> List[dict]:
        self._ensure_history_fields()

        def _format_season_label(value) -> str:
            # 旧実装互換（内部用）。実体は共通ヘルパーへ集約。
            return self._format_history_season_label(value)

        seasons = list(getattr(self, "history_seasons", []) or [])
        if limit is not None and limit > 0:
            seasons = seasons[-limit:]

        rows: List[dict] = []
        for item in reversed(seasons):
            if not isinstance(item, dict):
                continue

            season_label = item.get("season")
            if season_label is None:
                season_label = item.get("season_index", "-")
            season_label = self._format_history_season_label(season_label)

            wins = item.get("wins", item.get("regular_wins", "-"))
            losses = item.get("losses", item.get("regular_losses", "-"))

            league_level_value = item.get("league_level", "-")
            if isinstance(league_level_value, int):
                league_level_label = f"D{league_level_value}"
            else:
                league_level_text = str(league_level_value)
                if league_level_text.isdigit():
                    league_level_label = f"D{league_level_text}"
                elif league_level_text.startswith("D"):
                    league_level_label = league_level_text
                else:
                    league_level_label = league_level_text

            rows.append(
                {
                    "season": season_label,
                    "league_level": league_level_label,
                    "rank": item.get("rank", "-"),
                    "wins": wins,
                    "losses": losses,
                    "win_pct": item.get("win_pct", "-"),
                    "points_for": item.get("points_for", "-"),
                    "points_against": item.get("points_against", "-"),
                    "point_diff": item.get(
                        "point_diff",
                        (item.get("points_for", 0) - item.get("points_against", 0))
                        if isinstance(item.get("points_for"), (int, float)) and isinstance(item.get("points_against"), (int, float))
                        else "-",
                    ),
                    "note": item.get("note", ""),
                }
            )
        return rows

    def _format_history_season_label(self, value) -> str:
        """
        クラブ史表示用の season 表記を "Season N" に寄せる。
        - 3 / "3" -> "Season 3"
        - "Season 3" はそのまま
        - 空/None は "-"
        """
        if value is None:
            return "-"
        if isinstance(value, int):
            return f"Season {value}"
        text = str(value).strip()
        if not text:
            return "-"
        low = text.lower()
        if low.startswith("season"):
            return text
        if text.isdigit():
            return f"Season {int(text)}"
        return text

    def get_club_history_milestone_rows(self, limit: int | None = None) -> List[dict]:
        self._ensure_history_fields()

        milestones = list(getattr(self, "history_milestones", []) or [])
        if limit is not None and limit > 0:
            milestones = milestones[-limit:]

        rows: List[dict] = []
        for item in reversed(milestones):
            if not isinstance(item, dict):
                continue

            season_label = item.get("season")
            season_low = str(season_label).strip().lower() if season_label is not None else ""
            if (season_label is None) or (season_low in {"", "-", "unknown", "season unknown", "season 0"}):
                season_label = item.get("season_index", "-")

            # "0" は未設定の代用品として扱い、表示は Season 1 へ寄せる
            if season_label in (0, "0"):
                season_label = 1

            season_label = self._format_history_season_label(season_label)

            title = item.get("title")
            if not title:
                title = item.get("competition_name") or item.get("milestone_type") or item.get("type") or "-"

            detail = item.get("detail", "")
            if not detail and item.get("note"):
                detail = item.get("note", "")

            note = item.get("note", "") or ""
            is_test_seed = "test_seed" in str(note).lower()

            rows.append(
                {
                    "season": season_label,
                    "category": item.get("category", item.get("milestone_type", item.get("type", "-"))),
                    "title": title,
                    "detail": detail,
                    "note": note,
                    "is_test_seed": is_test_seed,
                }
            )
        return rows

    def get_club_history_award_rows(self, limit: int | None = None) -> List[dict]:
        self._ensure_history_fields()

        awards = list(getattr(self, "history_awards", []) or [])
        if limit is not None and limit > 0:
            awards = awards[-limit:]

        rows: List[dict] = []
        for item in reversed(awards):
            if not isinstance(item, dict):
                continue

            season_label = item.get("season")
            if season_label is None:
                season_label = item.get("season_index", "-")
            season_label = self._format_history_season_label(season_label)

            rows.append(
                {
                    "season": season_label,
                    "award": item.get("award", item.get("award_type", "-")),
                    "player": item.get("player_name", item.get("player", "-")),
                    "detail": item.get("detail", item.get("note", "")),
                }
            )
        return rows

    def get_club_history_legend_rows(self, limit: int | None = None) -> List[dict]:
        self._ensure_history_fields()

        legends = list(getattr(self, "club_legends", []) or [])
        if limit is not None and limit > 0:
            legends = legends[:limit]

        rows: List[dict] = []
        for item in legends:
            if isinstance(item, dict):
                rows.append(
                    {
                        "name": item.get("name", item.get("player_name", "-")),
                        "position": item.get("position", "-"),
                        "career_points": item.get("career_points", "-"),
                        "impact": item.get("impact", item.get("legacy_score", "-")),
                        "detail": item.get("detail", item.get("reason", "")),
                    }
                )
            else:
                rows.append(
                    {
                        "name": str(item),
                        "position": "-",
                        "career_points": "-",
                        "impact": "-",
                        "detail": "",
                    }
                )
        return rows


    def _format_league_label_for_history(self, league_value) -> str:
        if isinstance(league_value, int):
            return f"D{league_value}"
        league_text = str(league_value)
        if league_text.isdigit():
            return f"D{league_text}"
        if league_text.startswith("D"):
            return league_text
        return league_text

    def _safe_to_int(self, value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_history_status_tags(self, season_row: dict) -> List[str]:
        tags: List[str] = []

        rank = season_row.get("rank")
        rank_int = None
        try:
            rank_int = int(rank)
        except (TypeError, ValueError):
            rank_int = None

        wins = self._safe_to_int(season_row.get("wins"), 0)
        losses = self._safe_to_int(season_row.get("losses"), 0)
        note_text = str(season_row.get("note", "") or "")

        if rank_int == 1:
            tags.append("リーグ制覇")
        elif rank_int is not None and rank_int <= 3:
            tags.append("上位進出")
        elif rank_int is not None and rank_int >= 10:
            tags.append("苦戦")

        for keyword, label in (
            ("優勝", "優勝"),
            ("準優勝", "準優勝"),
            ("ベスト4", "ベスト4"),
            ("撃破", "撃破"),
            ("挑戦", "挑戦"),
            ("昇格", "昇格"),
            ("降格", "降格"),
            ("プレーオフ", "PO進出"),
            # 旧表記（残っている場合に備える）
            ("EASL", "国際大会"),
            ("ACL", "国際大会"),
            ("皇帝杯", "カップ戦"),
            # 表示名（命名整理後）
            ("天皇杯", "カップ戦"),
            ("全日本カップ", "カップ戦"),
            ("東アジアトップリーグ", "国際大会"),
            ("オールアジアトーナメント", "国際大会"),
            ("アジアクラブ選手権", "国際大会"),
            ("アジアカップ", "国際大会"),
            ("世界一決定戦", "国際大会"),
            ("FINAL BOSS", "国際大会"),
        ):
            if keyword in note_text and label not in tags:
                tags.append(label)

        point_diff = season_row.get("point_diff")
        if isinstance(point_diff, (int, float)):
            if point_diff >= 120:
                tags.append("圧倒的攻守")
            elif point_diff >= 60:
                tags.append("好成績")
            elif point_diff <= -120:
                tags.append("再建途上")
            elif point_diff <= -60:
                tags.append("守勢")

        if wins > losses and "好成績" not in tags and "リーグ制覇" not in tags and "上位進出" not in tags:
            tags.append("勝ち越し")
        elif wins < losses and "苦戦" not in tags and "再建途上" not in tags:
            tags.append("負け越し")

        deduped: List[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)

        return deduped[:3]

    def _build_club_identity_line(self, summary: dict) -> str:
        total_titles = self._safe_to_int(summary.get("total_titles", 0))
        promotions = self._safe_to_int(summary.get("promotions", 0))
        relegations = self._safe_to_int(summary.get("relegations", 0))
        season_count = self._safe_to_int(summary.get("season_count", 0))

        latest_rank_int = None
        latest = summary.get("latest_season") or {}
        try:
            latest_rank_int = int(latest.get("rank"))
        except (TypeError, ValueError):
            latest_rank_int = None

        if total_titles >= 5:
            grade_label = "名門"
            description = "国内屈指の実績を積み上げてきたクラブ。"
        elif total_titles >= 2:
            grade_label = "実力派"
            description = "優勝経験を持つ、常に上位をうかがう実力派クラブ。"
        elif promotions >= 2 and relegations == 0:
            grade_label = "成長株"
            description = "昇格を重ねながら力を伸ばしてきた上昇志向のクラブ。"
        elif relegations >= 2 and promotions == 0:
            grade_label = "再建途上"
            description = "苦しい時期を経験しつつも、巻き返しを目指す再建途上のクラブ。"
        elif season_count >= 8:
            grade_label = "古参"
            description = "長い歴史の中で独自の足跡を残してきたクラブ。"
        else:
            grade_label = "新興勢力"
            description = "まだ歴史は浅いが、これから色を作っていく段階のクラブ。"

        if latest_rank_int == 1:
            description += " 直近シーズンは頂点に立った。"
        elif latest_rank_int is not None and latest_rank_int <= 3:
            description += " 直近シーズンは上位争いに食い込んだ。"
        elif latest_rank_int is not None and latest_rank_int >= 10:
            description += " 直近シーズンは巻き返しが課題になっている。"

        if summary.get("international_titles", 0):
            description += " 国際舞台でも実績がある。"
        elif summary.get("cup_titles", 0):
            description += " カップ戦でも存在感を示してきた。"
        elif summary.get("legend_count", 0) >= 3:
            description += " すでに複数のクラブレジェンドを擁する。"

        return f"クラブ格: {grade_label} | {description}"

    def _build_recent_trend_line(self, season_rows: List[dict]) -> str:
        if not season_rows:
            return "まだ十分なシーズン履歴がありません。"

        chronological_rows = list(reversed(season_rows))
        recent_three = chronological_rows[-3:]
        latest_row = chronological_rows[-1]

        latest_wins = self._safe_to_int(latest_row.get("wins"), 0)
        latest_losses = self._safe_to_int(latest_row.get("losses"), 0)

        latest_rank = None
        try:
            latest_rank = int(latest_row.get("rank"))
        except (TypeError, ValueError):
            latest_rank = None

        latest_diff = latest_row.get("point_diff")

        if len(chronological_rows) == 1:
            parts: List[str] = []

            if latest_rank == 1:
                parts.append("創設初期からいきなり頂点に立った")
            elif latest_rank is not None and latest_rank <= 3:
                parts.append("創設初期から上位争いに加わった")
            elif latest_rank is not None and latest_rank <= 8:
                parts.append("初年度から一定の戦える土台を示した")
            else:
                parts.append("初年度は苦しい船出となったが、立て直しの余地を残した")

            if isinstance(latest_diff, (int, float)):
                if latest_diff >= 80:
                    parts.append("得失点差でも力強さを示した")
                elif latest_diff <= -80:
                    parts.append("得失点差の改善が次季の焦点になる")

            if latest_wins > latest_losses:
                parts.append("勝ち越しで来季へ希望をつないだ")
            elif latest_wins == latest_losses and latest_wins > 0:
                parts.append("五分の成績で今後の伸びしろを感じさせる")
            elif latest_wins + latest_losses > 0:
                parts.append("来季は白星先行への転換がテーマになる")

            return " / ".join(parts[:3])

        wins = [self._safe_to_int(row.get("wins"), 0) for row in recent_three]
        ranks: List[int] = []
        for row in recent_three:
            try:
                ranks.append(int(row.get("rank")))
            except (TypeError, ValueError):
                pass

        trend_parts: List[str] = []

        if len(wins) >= 2:
            if wins[-1] > wins[0]:
                trend_parts.append("直近では勝ち星を伸ばしている")
            elif wins[-1] < wins[0]:
                trend_parts.append("直近では勝率面に課題を残している")
            else:
                trend_parts.append("直近の成績は横ばい傾向")

        if ranks:
            best_rank = min(ranks)
            if latest_rank == 1:
                trend_parts.append("ついにリーグ頂点へ到達")
            elif best_rank <= 3:
                trend_parts.append("上位争いに食い込む地力がある")
            else:
                trend_parts.append("中位から上位進出を狙う段階")

        if isinstance(latest_diff, (int, float)):
            if latest_diff >= 80:
                trend_parts.append("得失点差も優秀")
            elif latest_diff <= -80:
                trend_parts.append("得失点差の改善が今後の焦点")

        if not trend_parts:
            return "長期的な傾向を判断するには、もう少し履歴が必要です。"
        return " / ".join(trend_parts[:3])

    def _build_milestone_headlines(self, milestone_rows: List[dict], limit: int = 5) -> List[str]:
        headlines: List[str] = []
        priority_words = (
            # 強調したい結果種別
            "優勝",
            "準優勝",
            "ベスト4",
            "撃破",
            "挑戦",
            # 昇降格・国内/国際
            "昇格",
            "降格",
            "東アジアトップリーグ",
            "オールアジアトーナメント",
            "アジアクラブ選手権",
            "全日本カップ",
            "天皇杯",
            "アジアカップ",
            "世界一決定戦",
            "FINAL BOSS",
            # 旧表記（互換）
            "EASL",
            "ACL",
            "皇帝杯",
            # その他
            "プレーオフ",
        )

        def _season_number(value) -> int:
            """
            season 表記を共通ヘルパーで正規化してから数値化する。
            取得できない場合は 0。
            """
            label = self._format_history_season_label(value)
            digits = "".join(ch for ch in str(label) if ch.isdigit())
            try:
                return int(digits) if digits else 0
            except Exception:
                return 0

        indexed_rows = []
        for i, row in enumerate(milestone_rows):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "") or "")
            detail = str(row.get("detail", "") or "")
            is_priority = any(word in title or word in detail for word in priority_words)
            season_no = _season_number(row.get("season", row.get("season_index")))
            # 新しいシーズンを上、同一シーズン内は重要語優先、最後は元順で安定化
            indexed_rows.append((i, season_no, 0 if is_priority else 1, row))

        sorted_rows = [t[3] for t in sorted(indexed_rows, key=lambda t: (-t[1], t[2], t[0]))]

        for row in sorted_rows:
            season = row.get("season", "-")
            title = str(row.get("title", "-"))
            detail = str(row.get("detail", "") or "")
            test_mark = " [TEST]" if bool(row.get("is_test_seed")) else ""
            if detail:
                headlines.append(f"{season}: {title}{test_mark}（{detail}）")
            else:
                headlines.append(f"{season}: {title}{test_mark}")
            if len(headlines) >= limit:
                break

        return headlines

    def _build_recent_big_milestone_lines(self, milestone_rows: List[dict], limit: int = 4) -> List[str]:
        priority_words = (
            # 強調したい結果種別
            "優勝",
            "準優勝",
            "ベスト4",
            "撃破",
            "挑戦",
            # 昇降格・国内/国際
            "昇格",
            "降格",
            "東アジアトップリーグ",
            "オールアジアトーナメント",
            "アジアクラブ選手権",
            "全日本カップ",
            "天皇杯",
            "アジアカップ",
            "世界一決定戦",
            "FINAL BOSS",
            # 旧表記（互換）
            "EASL",
            "ACL",
            "皇帝杯",
            # その他
            "プレーオフ",
        )
        picked: List[str] = []
        seen_keys = set()

        for row in milestone_rows:
            title = str(row.get("title", ""))
            detail = str(row.get("detail", ""))
            if not any(word in title or word in detail for word in priority_words):
                continue

            season = row.get("season", "-")
            dedupe_key = (season, title)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            detail_text = f"（{detail}）" if detail else ""
            test_mark = " [TEST]" if bool(row.get("is_test_seed")) else ""
            picked.append(f"- {season}: {title}{test_mark}{detail_text}")

            if len(picked) >= limit:
                break

        return picked

    def _build_legend_headlines(self, legend_rows: List[dict], limit: int = 3) -> List[str]:
        headlines: List[str] = []
        for row in legend_rows[:limit]:
            name = row.get("name", "-")
            pieces: List[str] = []
            if row.get("position") not in ("", "-"):
                pieces.append(str(row.get("position")))
            if row.get("career_points") not in ("", "-"):
                pieces.append(f"通算得点{row.get('career_points')}")
            if row.get("impact") not in ("", "-"):
                pieces.append(f"impact {row.get('impact')}")
            if row.get("detail"):
                pieces.append(str(row.get("detail")))
            suffix = " / ".join(pieces)
            headlines.append(f"{name} - {suffix}" if suffix else str(name))
        return headlines

    def _build_empty_legend_message(self) -> str:
        seasons = len(getattr(self, "history_seasons", []) or [])
        if seasons >= 5:
            return "まだクラブレジェンド選定前。次代の象徴選手の誕生を待っている。"
        return "まだクラブレジェンドは不在。これから歴史を作る段階。"

    def get_club_history_report_text(self, season_limit: int = 10) -> str:
        summary = self.get_club_history_summary()
        season_rows = self.get_club_history_season_rows(limit=season_limit)
        # 3ブロック表示（国際/FINAL BOSS/国内）で取りこぼしが出ないよう、
        # 取得は多めに行い、表示側の limit で絞る。
        milestone_rows = self.get_club_history_milestone_rows(limit=60)
        legend_rows = self.get_club_history_legend_rows(limit=10)

        lines: List[str] = []
        club_name = summary["club_name"]
        league_label = self._format_league_label_for_history(summary["current_league_level"])

        lines.append(f"==============================")
        lines.append(f"{club_name} クラブ史レポート")
        lines.append(f"==============================")
        lines.append(f"現在所属: {league_label}")
        lines.append(f"通算シーズン数: {summary['season_count']}")
        lines.append(self._build_club_identity_line(summary))
        lines.append("")
        lines.append(
            f"主要実績: タイトル{summary['total_titles']}回 "
            f"(リーグ{summary['league_titles']} / カップ{summary['cup_titles']} / 国際{summary['international_titles']})"
        )
        lines.append(
            f"昇格{summary['promotions']}回 / 降格{summary['relegations']}回 / "
            f"レジェンド{summary['legend_count']}人 / クラブ表彰{summary['award_count']}件"
        )
        lines.append("")

        lines.append("【最近の流れ】")
        lines.append(self._build_recent_trend_line(season_rows))
        lines.append("")

        lines.append("【最近のシーズン】")
        if season_rows:
            for row in season_rows:
                tags = self._build_history_status_tags(row)
                tag_text = f" [{' / '.join(tags)}]" if tags else ""
                point_diff = row.get("point_diff")
                diff_text = "-"
                if isinstance(point_diff, (int, float)):
                    diff_text = f"{int(point_diff):+}"
                lines.append(
                    f"- {row['season']} | {row['league_level']} | {row['rank']}位 | "
                    f"{row['wins']}勝{row['losses']}敗 | 得失点差{diff_text}{tag_text}"
                )
                if row.get("note"):
                    lines.append(f"  メモ: {row['note']}")
        else:
            lines.append("- まだシーズン履歴がありません。")
        lines.append("")

        # ------------------------------------------------------------
        # Milestones (domestic / international / final boss)
        # ------------------------------------------------------------
        def _is_final_boss_row(row: dict) -> bool:
            blob = " | ".join([str(row.get("title", "")), str(row.get("detail", "")), str(row.get("category", ""))])
            return "final boss" in blob.lower() or "FINAL BOSS" in blob

        def _is_international_row(row: dict) -> bool:
            blob = " | ".join([str(row.get("title", "")), str(row.get("detail", "")), str(row.get("category", ""))])
            keys = [
                "EASL",
                "ACL",
                "東アジアトップリーグ",
                "オールアジアトーナメント",
                "アジアクラブ選手権",
                "アジアカップ",
                "世界一決定戦",
                "intercontinental",
                "インターコンチネンタル",
            ]
            low = blob.lower()
            return any(k.lower() in low for k in keys)

        final_boss_rows = [r for r in milestone_rows if isinstance(r, dict) and _is_final_boss_row(r)]
        international_rows = [
            r for r in milestone_rows if isinstance(r, dict) and (not _is_final_boss_row(r)) and _is_international_row(r)
        ]
        domestic_rows = [
            r
            for r in milestone_rows
            if isinstance(r, dict) and (not _is_final_boss_row(r)) and (not _is_international_row(r))
        ]

        lines.append("【マイルストーン（国際）】")
        intl_headlines = self._build_milestone_headlines(international_rows, limit=5)
        if intl_headlines:
            for line in intl_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- まだ国際大会のマイルストーンはありません。")
        lines.append("")

        lines.append("【マイルストーン（FINAL BOSS）】")
        boss_headlines = self._build_milestone_headlines(final_boss_rows, limit=4)
        if boss_headlines:
            for line in boss_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- FINAL BOSS への挑戦履歴はまだありません。")
        lines.append("")

        lines.append("【マイルストーン（国内・昇降格）】")
        dom_headlines = self._build_milestone_headlines(domestic_rows, limit=5)
        if dom_headlines:
            for line in dom_headlines:
                lines.append(f"- {line}")
        else:
            lines.append("- まだ国内のマイルストーンはありません。")
        lines.append("")

        recent_big_lines = self._build_recent_big_milestone_lines(milestone_rows, limit=4)
        if recent_big_lines and summary["season_count"] >= 2:
            lines.append("【近年の象徴的トピック】")
            lines.extend(recent_big_lines)
            lines.append("")

        lines.append("【クラブレジェンド】")
        legend_headlines = self._build_legend_headlines(legend_rows, limit=5)
        if legend_headlines:
            for line in legend_headlines:
                lines.append(f"- {line}")
        else:
            lines.append(f"- {self._build_empty_legend_message()}")

        return "\n".join(lines)

    def print_history(self):
        self._ensure_history_fields()

        print()
        print(self.get_club_history_report_text(season_limit=10))
        print()

        print("【単年記録】")

        single_season_points = self.get_single_season_points_records(top_n=1)
        if not single_season_points:
            print("単年記録はまだありません。")
        else:
            row = single_season_points[0]
            print("最多得点シーズン")
            print(
                f"1. {row.get('player_name', 'Unknown')} | "
                f"{row.get('season_points', 0)} PTS | "
                f"Season {row.get('season_index', '?')}"
            )

            single_season_assists = self.get_single_season_assist_records(top_n=1)
            if single_season_assists:
                row = single_season_assists[0]
                print("\n最多アシストシーズン")
                print(
                    f"1. {row.get('player_name', 'Unknown')} | "
                    f"{row.get('season_assists', 0)} AST | "
                    f"Season {row.get('season_index', '?')}"
                )

            single_season_rebounds = self.get_single_season_rebound_records(top_n=1)
            if single_season_rebounds:
                row = single_season_rebounds[0]
                print("\n最多リバウンドシーズン")
                print(
                    f"1. {row.get('player_name', 'Unknown')} | "
                    f"{row.get('season_rebounds', 0)} REB | "
                    f"Season {row.get('season_index', '?')}"
                )

            single_season_blocks = self.get_single_season_block_records(top_n=1)
            if single_season_blocks:
                row = single_season_blocks[0]
                print("\n最多ブロックシーズン")
                print(
                    f"1. {row.get('player_name', 'Unknown')} | "
                    f"{row.get('season_blocks', 0)} BLK | "
                    f"Season {row.get('season_index', '?')}"
                )

            single_season_steals = self.get_single_season_steal_records(top_n=1)
            if single_season_steals:
                row = single_season_steals[0]
                print("\n最多スティールシーズン")
                print(
                    f"1. {row.get('player_name', 'Unknown')} | "
                    f"{row.get('season_steals', 0)} STL | "
                    f"Season {row.get('season_index', '?')}"
                )

        print("\n【トランザクション履歴】")
        if not self.history_transactions:
            print("トランザクション履歴はまだありません。")
        else:
            for row in self.history_transactions[-10:]:
                transaction_type = row.get("transaction_type", "unknown").replace("_", " ").title()
                player_name = row.get("player_name", "Unknown")
                note = row.get("note", "")
                if note:
                    print(f"- {transaction_type} | {player_name} | {note}")
                else:
                    print(f"- {transaction_type} | {player_name}")

        print("\n【クラブ表彰】")
        award_rows = self.get_club_history_award_rows(limit=10)
        if not award_rows:
            print("クラブ表彰はまだありません。")
        else:
            for row in award_rows:
                detail = f" | {row['detail']}" if row.get("detail") else ""
                print(f"- {row['season']} | {row['award']} | {row['player']}{detail}")

        print("\n【歴代インパクトランキング】")
        impact_rows = self.get_all_time_impact(top_n=5, min_games=20)
        if not impact_rows:
            print("インパクト履歴はまだありません。")
        else:
            for i, row in enumerate(impact_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"Impact:{row.get('impact', 0.0):.2f} | "
                    f"PPG:{row.get('ppg', 0.0):.2f} | "
                    f"RPG:{row.get('rpg', 0.0):.2f} | "
                    f"APG:{row.get('apg', 0.0):.2f}"
                )

        print("\n【歴代通算得点ランキング】")
        scoring_rows = self.get_all_time_scorers(top_n=5)
        if not scoring_rows:
            print("通算得点履歴はまだありません。")
        else:
            for i, row in enumerate(scoring_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"PTS:{row.get('career_points', 0)} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )

        print("\n【歴代PPGランキング】")
        ppg_rows = self.get_all_time_ppg(top_n=5, min_games=20)
        if not ppg_rows:
            print("PPG履歴はまだありません。")
        else:
            for i, row in enumerate(ppg_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"PPG:{row.get('ppg', 0.0):.2f} | "
                    f"PTS:{row.get('career_points', 0)} | "
                    f"GP:{row.get('career_games_played', 0)}"
                )

        print("\n【歴代RPGランキング】")
        rpg_rows = self.get_all_time_rpg(top_n=5, min_games=20)
        if not rpg_rows:
            print("RPG履歴はまだありません。")
        else:
            for i, row in enumerate(rpg_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"RPG:{row.get('rpg', 0.0):.2f} | "
                    f"REB:{row.get('career_rebounds', 0)} | "
                    f"GP:{row.get('career_games_played', 0)}"
                )

        print("\n【歴代APGランキング】")
        apg_rows = self.get_all_time_apg(top_n=5, min_games=20)
        if not apg_rows:
            print("APG履歴はまだありません。")
        else:
            for i, row in enumerate(apg_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"APG:{row.get('apg', 0.0):.2f} | "
                    f"AST:{row.get('career_assists', 0)} | "
                    f"GP:{row.get('career_games_played', 0)}"
                )

        print("\n【歴代出場試合数ランキング】")
        games_rows = self.get_all_time_games(top_n=5)
        if not games_rows:
            print("出場試合数履歴はまだありません。")
        else:
            for i, row in enumerate(games_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"PTS:{row.get('career_points', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )

        print("\n【歴代通算アシストランキング】")
        assist_rows = self.get_all_time_assists(top_n=5)
        if not assist_rows:
            print("アシスト履歴はまだありません。")
        else:
            for i, row in enumerate(assist_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"AST:{row.get('career_assists', 0)} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )

        print("\n【歴代通算リバウンドランキング】")
        rebound_rows = self.get_all_time_rebounds(top_n=5)
        if not rebound_rows:
            print("リバウンド履歴はまだありません。")
        else:
            for i, row in enumerate(rebound_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"REB:{row.get('career_rebounds', 0)} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )

        print("\n【歴代通算ブロックランキング】")
        block_rows = self.get_all_time_blocks(top_n=5)
        if not block_rows:
            print("ブロック履歴はまだありません。")
        else:
            for i, row in enumerate(block_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"BLK:{row.get('career_blocks', 0)} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )

        print("\n【歴代通算スティールランキング】")
        steal_rows = self.get_all_time_steals(top_n=5)
        if not steal_rows:
            print("スティール履歴はまだありません。")
        else:
            for i, row in enumerate(steal_rows, 1):
                print(
                    f"{i}. {row.get('player_name', 'Unknown')} | "
                    f"STL:{row.get('career_steals', 0)} | "
                    f"GP:{row.get('career_games_played', 0)} | "
                    f"Peak:{row.get('peak_ovr', 0)}"
                )
