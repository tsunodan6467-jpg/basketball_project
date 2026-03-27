from dataclasses import dataclass, field
from typing import List, Optional
import random


@dataclass
class Player:
    """
    選手データを表現するクラス。
    各能力値や状態（疲労、ケガなど）を管理します。

    設計方針:
    - 既存システムとの互換性を最優先
    - 将来のGM要素拡張に必要な土台だけ先に保持
    - 未使用の新規項目があっても既存挙動を壊さない
    """

    # 基本情報
    player_id: int
    name: str
    age: int
    nationality: str

    position: str
    height_cm: float
    weight_kg: float

    # 能力値 (0-99想定)
    shoot: int
    three: int
    drive: int
    passing: int
    rebound: int
    defense: int
    ft: int
    stamina: int

    # 総合評価と潜在能力
    ovr: int
    potential: str  # e.g., 'S', 'A', 'B', 'C', 'D'
    archetype: str
    usage_base: int
    # 拡張能力（Phase 1: 定義のみ。試合反映は段階導入）
    handling: int = 50
    iq: int = 50
    speed: int = 50
    power: int = 50

    # 選手人気度 (0〜100)
    popularity: int = 50

    # シーズン成績 (シーズン開始時にリセットされる)
    season_points: int = 0
    season_rebounds: int = 0
    season_assists: int = 0
    season_blocks: int = 0
    season_steals: int = 0
    games_played: int = 0

    # 通算成績（将来の歴史システム用）
    career_points: int = 0
    career_rebounds: int = 0
    career_assists: int = 0
    career_blocks: int = 0
    career_steals: int = 0
    career_games_played: int = 0

    # キャリア履歴
    career_history: List[dict] = field(default_factory=list)

    # Hall of Fame 土台
    peak_ovr: int = 0
    hall_of_fame_score: float = 0.0
    is_hall_of_famer: bool = False
    hall_of_fame_reason: str = ""

    # 契約と所属
    team_id: Optional[int] = None
    salary: int = 0
    contract_years_left: int = 0
    contract_total_years: int = 0
    desired_salary: int = 0
    desired_years: int = 0
    contract_role_expectation: str = "bench"   # star / starter / rotation / bench
    last_contract_team_id: Optional[int] = None
    years_pro: int = 0

    # リーグ履歴 / 国籍履歴
    league_years: int = 0
    original_nationality: Optional[str] = None
    was_naturalized: bool = False

    # 獲得経路（将来のユース / 特別指定 / 履歴システム用）
    acquisition_type: str = "normal"  # normal / draft / trade / free_agent / youth / special_designation / international / reborn
    acquisition_note: str = ""
    # 直近の契約更新種別（Step 2: 再契約 vs 延長の区別用）
    contract_last_action: str = ""

    # ユース（v1土台）
    youth_team_id: Optional[int] = None
    youth_reputation: str = ""  # A/B/C/D（有力候補のみ）
    youth_hidden_score: float = 0.0

    # 成長土台
    growth_type: str = "normal"       # normal / steady / late_bloomer / boom_bust / early_peak
    peak_age: int = 28
    decline_age: int = 32

    # 隠し成長・性格パラメータ（将来システム用）
    work_ethic: int = 50              # 成長しやすさ
    basketball_iq: int = 50           # 安定性
    competitiveness: int = 50         # 勝負強さ / バースト土台
    loyalty: int = 50                 # 残留志向

    # FA志向（将来の交渉ロジック用）
    fa_priority_money: int = 50
    fa_priority_role: int = 50
    fa_priority_winning: int = 50
    fa_priority_fit: int = 50
    fa_priority_security: int = 50       # 長期契約志向
    preferred_team_style: str = ""
    preferred_coach_style: str = ""
    fa_personality: str = "balanced"     # balanced / money / winning / role / fit / security / loyal
    # 個別育成方針（Phase 3）
    training_focus: str = "balanced"     # balanced / shooting / playmaking / defense / physical / iq_handling

    # 物語・称号系の土台
    nickname_title: str = ""
    title_level: int = 0
    star_tier: int = 0                # 0=通常, 1=注目株, 2=スター, 3=スーパースター
    breakout_count: int = 0

    # ケミストリー土台
    chemistry_tag: str = ""
    mentor_player_id: Optional[int] = None

    # 転生 / 再登場情報
    reborn_type: str = "none"  # none / japanese_reborn / international_reborn / special
    reborn_from_player_id: Optional[int] = None
    reborn_from_name: Optional[str] = None
    reborn_archetype_hint: Optional[str] = None
    naturalize_bonus_chance: float = 0.0

    # 既存コード互換のため残すフラグ群
    is_retired: bool = False
    is_icon: bool = False
    icon_locked: bool = False
    development: float = 0.0
    had_naturalized_history: bool = False
    is_reborn: bool = False
    is_international_reborn: bool = False
    draft_origin_type: str = ""
    draft_profile_label: str = ""
    draft_priority_bonus: int = 0
    # ドラフト市場での注目度（正本: docs/DRAFT_AUCTION_SYSTEM.md）
    # "SS" / "S" / ""（通常候補）
    draft_market_grade: str = ""
    # その年の「プロスペクト（6〜10人）」枠かどうか
    is_draft_prospect: bool = False
    reborn_from: Optional[str] = None

    # 試合・シーズンステータス
    fatigue: int = 0
    injury_games_left: int = 0
    minutes_expected: int = 0

    # 代表関連（将来拡張の受け皿）
    is_on_national_team: bool = False
    national_team_type: str = ""
    national_team_country: str = ""
    national_team_return_fatigue_bonus: int = 0
    national_team_history: List[dict] = field(default_factory=list)

    def __post_init__(self):
        # 国籍履歴の初期化
        if self.original_nationality is None:
            if self.nationality == "Naturalized":
                self.original_nationality = "Foreign"
                self.was_naturalized = True
            else:
                self.original_nationality = self.nationality

        # 互換フラグ整理
        if self.nationality == "Naturalized":
            self.had_naturalized_history = True

        if self.reborn_type in ("japanese_reborn", "international_reborn", "special"):
            self.is_reborn = True
            if self.reborn_type == "international_reborn":
                self.is_international_reborn = True

        # potential 正規化
        self.potential = self._normalize_potential(self.potential)

        # archetype 空対策
        if not self.archetype:
            self.archetype = self._infer_archetype()

        # usage_base 安全化
        self.usage_base = int(max(1, min(99, self.usage_base)))

        # popularity 安全化
        self.popularity = int(max(0, min(100, self.popularity)))

        # 能力値安全化
        self._clamp_all_core_attributes()

        # OVR安全化
        self.ovr = int(max(40, min(99, self.ovr)))

        # years / league_years の初期整合
        if self.league_years <= 0 and self.years_pro > 0:
            self.league_years = self.years_pro

        # career_history 安全化
        if self.career_history is None:
            self.career_history = []

        # national team history 安全化
        if self.national_team_history is None:
            self.national_team_history = []

        # Hall of Fame 安全化
        if self.peak_ovr <= 0:
            self.peak_ovr = self.ovr
        else:
            self.peak_ovr = int(max(self.peak_ovr, self.ovr))

        self.hall_of_fame_score = float(max(0.0, self.hall_of_fame_score))
        self.is_hall_of_famer = bool(self.is_hall_of_famer)
        self.hall_of_fame_reason = str(self.hall_of_fame_reason or "")

        # 契約情報の安全化
        self.salary = int(max(0, self.salary))
        self.contract_years_left = int(max(0, self.contract_years_left))
        self.contract_total_years = int(max(0, self.contract_total_years))
        self.desired_salary = int(max(0, self.desired_salary))
        self.desired_years = int(max(0, self.desired_years))
        self.contract_role_expectation = self._normalize_contract_role_expectation(self.contract_role_expectation)
        self.contract_last_action = str(getattr(self, "contract_last_action", "") or "")

        if self.contract_total_years <= 0 and self.contract_years_left > 0:
            self.contract_total_years = self.contract_years_left
        elif self.contract_total_years > 0 and self.contract_years_left > self.contract_total_years:
            self.contract_total_years = self.contract_years_left

        if self.last_contract_team_id is None and self.team_id is not None and self.contract_years_left > 0:
            self.last_contract_team_id = self.team_id

        # 将来用パラメータの自動補正
        self._initialize_growth_profile()
        self._initialize_hidden_traits()
        self._initialize_fa_profile()

    def _normalize_potential(self, raw: str) -> str:
        val = str(raw).upper().strip()
        if val in ("S", "A", "B", "C", "D"):
            return val
        return "C"

    def _normalize_contract_role_expectation(self, raw: str) -> str:
        val = str(raw or "bench").strip().lower()
        if val in ("star", "starter", "rotation", "bench"):
            return val
        return "bench"

    def _clamp_attr(self, value: int) -> int:
        return int(max(1, min(99, value)))

    def _clamp_all_core_attributes(self):
        attr_keys = [
            "shoot", "three", "drive", "passing",
            "rebound", "defense", "ft", "stamina",
            "handling", "iq", "speed", "power",
        ]
        for key in attr_keys:
            setattr(self, key, self._clamp_attr(getattr(self, key, 50)))

    def _infer_archetype(self) -> str:
        scores = {
            "scoring_guard": self.shoot + self.three + self.drive,
            "playmaker": self.passing + self.drive + self.shoot,
            "two_way_wing": self.shoot + self.defense + self.drive,
            "stretch_big": self.three + self.rebound + self.shoot,
            "rim_protector": self.defense + self.rebound + self.stamina,
            "slasher": self.drive + self.shoot + self.stamina,
            "floor_general": self.passing + self.three + self.basketball_iq if hasattr(self, "basketball_iq") else self.passing + self.three,
            "rebounder": self.rebound + self.defense + self.stamina,
        }

        position = self.position
        if position == "PG":
            return "floor_general" if self.passing >= self.shoot else "playmaker"
        if position == "SG":
            return "scoring_guard" if self.three >= self.passing else "playmaker"
        if position == "SF":
            return "two_way_wing"
        if position == "PF":
            return "stretch_big" if self.three >= 70 else "rebounder"
        if position == "C":
            return "rim_protector" if self.defense >= self.shoot else "rebounder"

        return max(scores.items(), key=lambda x: x[1])[0]

    def _initialize_growth_profile(self):
        if self.peak_age <= 0:
            self.peak_age = 28
        if self.decline_age <= 0:
            self.decline_age = 32

        if self.growth_type == "normal":
            roll = random.random()

            if self.potential == "S":
                if roll < 0.30:
                    self.growth_type = "late_bloomer"
                elif roll < 0.65:
                    self.growth_type = "steady"
                else:
                    self.growth_type = "boom_bust"
            elif self.potential == "A":
                if roll < 0.25:
                    self.growth_type = "late_bloomer"
                elif roll < 0.70:
                    self.growth_type = "steady"
                else:
                    self.growth_type = "normal"
            elif self.potential == "B":
                if roll < 0.20:
                    self.growth_type = "steady"
                else:
                    self.growth_type = "normal"
            elif self.potential == "C":
                if roll < 0.15:
                    self.growth_type = "early_peak"
                else:
                    self.growth_type = "normal"
            else:
                self.growth_type = "early_peak"

        if self.growth_type == "late_bloomer":
            self.peak_age = max(self.peak_age, 29)
            self.decline_age = max(self.decline_age, self.peak_age + 4)
        elif self.growth_type == "steady":
            self.peak_age = max(27, self.peak_age)
            self.decline_age = max(self.decline_age, self.peak_age + 4)
        elif self.growth_type == "boom_bust":
            self.peak_age = max(26, self.peak_age)
            self.decline_age = max(self.decline_age, self.peak_age + 3)
        elif self.growth_type == "early_peak":
            self.peak_age = min(self.peak_age, 26)
            self.decline_age = max(self.decline_age, self.peak_age + 3)
        else:
            self.decline_age = max(self.decline_age, self.peak_age + 4)

    def _initialize_hidden_traits(self):
        if self.work_ethic == 50:
            self.work_ethic = self._roll_hidden_by_potential()
        if self.basketball_iq == 50:
            self.basketball_iq = self._roll_hidden_by_potential()
        if self.competitiveness == 50:
            self.competitiveness = self._roll_hidden_by_potential()
        if self.loyalty == 50:
            self.loyalty = random.randint(35, 75)

        self.work_ethic = int(max(1, min(99, self.work_ethic)))
        self.basketball_iq = int(max(1, min(99, self.basketball_iq)))
        self.competitiveness = int(max(1, min(99, self.competitiveness)))
        self.loyalty = int(max(1, min(99, self.loyalty)))

        # Phase 1 互換:
        # - iq が未調整（既定50）の場合は hidden の basketball_iq を移して整合を取る
        # - 既存セーブで iq が無い/0 だった場合の極端値を避ける
        if int(getattr(self, "iq", 50) or 0) <= 0 or int(getattr(self, "iq", 50)) == 50:
            self.iq = int(max(1, min(99, self.basketball_iq)))

    def _roll_hidden_by_potential(self) -> int:
        if self.potential == "S":
            return random.randint(72, 92)
        if self.potential == "A":
            return random.randint(62, 86)
        if self.potential == "B":
            return random.randint(52, 78)
        if self.potential == "C":
            return random.randint(42, 70)
        return random.randint(35, 62)


    def _clamp_preference(self, value: int) -> int:
        return int(max(1, min(99, value)))

    def _initialize_fa_profile(self):
        """
        FA交渉用の志向を安全に初期化する。
        既存挙動を壊さないため、まだ他システムが未使用でも問題ない土台だけ保持する。
        """
        if self.fa_priority_money == 50:
            base = 45 + max(0, self.age - 27) * 2
            if self.popularity >= 70:
                base += 4
            self.fa_priority_money = random.randint(max(25, base - 10), min(90, base + 10))

        if self.fa_priority_role == 50:
            base = 52
            if self.ovr >= 78:
                base += 8
            if self.age <= 24:
                base += 6
            self.fa_priority_role = random.randint(max(25, base - 12), min(90, base + 12))

        if self.fa_priority_winning == 50:
            base = 42 + max(0, self.competitiveness - 50) // 2
            if self.ovr >= 80:
                base += 8
            self.fa_priority_winning = random.randint(max(20, base - 12), min(95, base + 12))

        if self.fa_priority_fit == 50:
            base = 45 + max(0, self.basketball_iq - 50) // 2
            self.fa_priority_fit = random.randint(max(25, base - 10), min(90, base + 10))

        if self.fa_priority_security == 50:
            base = 45 + max(0, self.age - 28) * 3
            if self.potential in ("S", "A") and self.age <= 24:
                base -= 6
            self.fa_priority_security = random.randint(max(20, base - 12), min(92, base + 12))

        self.fa_priority_money = self._clamp_preference(self.fa_priority_money)
        self.fa_priority_role = self._clamp_preference(self.fa_priority_role)
        self.fa_priority_winning = self._clamp_preference(self.fa_priority_winning)
        self.fa_priority_fit = self._clamp_preference(self.fa_priority_fit)
        self.fa_priority_security = self._clamp_preference(self.fa_priority_security)

        if not self.preferred_team_style:
            archetype_style_map = {
                "scoring_guard": "run_and_gun",
                "playmaker": "balanced",
                "two_way_wing": "defense",
                "stretch_big": "three_point",
                "rim_protector": "defense",
                "slasher": "run_and_gun",
                "floor_general": "balanced",
                "rebounder": "inside",
            }
            self.preferred_team_style = archetype_style_map.get(self.archetype, "balanced")

        if not self.preferred_coach_style:
            if self.age <= 24 and self.potential in ("S", "A"):
                self.preferred_coach_style = "development"
            elif self.defense >= max(self.shoot, self.three):
                self.preferred_coach_style = "defense"
            else:
                self.preferred_coach_style = "offense"

        if self.fa_personality == "balanced":
            scores = {
                "money": self.fa_priority_money + max(0, self.popularity - 50) // 2,
                "role": self.fa_priority_role + max(0, self.ovr - 70) // 2,
                "winning": self.fa_priority_winning + max(0, self.competitiveness - 50) // 2,
                "fit": self.fa_priority_fit + max(0, self.basketball_iq - 50) // 2,
                "security": self.fa_priority_security + max(0, self.age - 28),
                "loyal": int(self.loyalty),
            }
            self.fa_personality = max(scores.items(), key=lambda x: x[1])[0]
        self.training_focus = self._normalize_training_focus(getattr(self, "training_focus", "balanced"))

    def _normalize_training_focus(self, raw: str) -> str:
        val = str(raw or "balanced").strip().lower()
        valid = {"balanced", "shooting", "playmaking", "defense", "physical", "iq_handling"}
        return val if val in valid else "balanced"

    def get_free_agency_profile(self) -> dict:
        """
        FA交渉ロジックが参照しやすい形で志向情報を返す。
        """
        return {
            "money": int(self.fa_priority_money),
            "role": int(self.fa_priority_role),
            "winning": int(self.fa_priority_winning),
            "fit": int(self.fa_priority_fit),
            "security": int(self.fa_priority_security),
            "loyalty": int(self.loyalty),
            "preferred_team_style": self.preferred_team_style,
            "preferred_coach_style": self.preferred_coach_style,
            "fa_personality": self.fa_personality,
        }

    def add_career_entry(self, season: int, team_name: str, event: str, note: str = ""):
        """
        選手キャリア履歴を1件追加する。
        同一シーズン・同一チーム・同一イベントの重複登録は防ぐ。
        """
        if self.career_history is None:
            self.career_history = []

        normalized_team = team_name or "Unknown"
        normalized_event = event or "Unknown"

        for row in self.career_history:
            if (
                row.get("season") == season and
                row.get("team") == normalized_team and
                row.get("event") == normalized_event
            ):
                return

        self.career_history.append({
            "season": season,
            "team": normalized_team,
            "event": normalized_event,
            "note": note,
        })

    def print_career(self, max_items: Optional[int] = None):
        """
        キャリア履歴をコンソール表示する。
        """
        rows = self.career_history[:] if self.career_history is not None else []
        if max_items is not None:
            rows = rows[-max_items:]

        print(f"\n=== {self.name} Career ===")

        if not rows:
            print("No career history yet.")
            return

        for row in rows:
            season = row.get("season", "?")
            team = row.get("team", "Unknown")
            event = row.get("event", "Unknown")
            note = row.get("note", "")

            line = f"Season {season}: {team} - {event}"
            if note:
                line += f" - {note}"
            print(line)


    def is_foreign_player(self) -> bool:
        """
        日本独自ルール上で外国籍枠扱いかを返す。
        表記ゆれに強くしつつ、既存挙動は壊さない。
        """
        nationality = str(self.nationality or "").strip().lower()
        original_nationality = str(self.original_nationality or "").strip().lower()

        if nationality in {"foreign", "overseas", "international", "import"}:
            return True

        # 帰化選手は on-the-court 上は外国籍ではなく Asia/帰化枠扱い。
        if nationality in {"naturalized", "asia", "asian", "asianquota", "asian_quota"}:
            return False

        # 念のため元国籍だけ残っているケースには対応するが、
        # nationality が Japan の場合は日本人扱いを優先する。
        if nationality in {"japan", "japanese", "jp"}:
            return False

        if original_nationality in {"foreign", "overseas", "international", "import"} and nationality not in {"japan", "japanese", "jp"}:
            return nationality == ""

        return False

    def is_asia_or_naturalized_player(self) -> bool:
        """
        日本独自ルール上で Asia / 帰化枠扱いかを返す。
        """
        nationality = str(self.nationality or "").strip().lower()
        if nationality in {"naturalized", "asia", "asian", "asianquota", "asian_quota"}:
            return True

        # 将来、履歴だけ残って nationality が未更新のケースにもある程度耐える。
        if bool(self.was_naturalized) and nationality not in {"japan", "japanese", "jp", "foreign", "overseas", "international", "import"}:
            return True

        return False

    def get_japan_roster_slot_type(self) -> str:
        """
        日本独自ルール用の簡易カテゴリを返す。
        returns: "foreign" / "asia_or_naturalized" / "domestic"
        """
        if self.is_asia_or_naturalized_player():
            return "asia_or_naturalized"
        if self.is_foreign_player():
            return "foreign"
        return "domestic"

    def update_peak_ovr(self):
        """
        現在OVRを見てピークOVRを更新する。
        """
        if self.peak_ovr <= 0:
            self.peak_ovr = self.ovr
        else:
            self.peak_ovr = max(self.peak_ovr, self.ovr)

    def calculate_hall_of_fame_score(self) -> float:
        """
        Hall of Fame 判定用の簡易スコアを返す。
        旧版より少し通りやすく調整。
        """
        self.update_peak_ovr()

        score = 0.0
        score += self.career_points / 850.0
        score += self.career_rebounds / 600.0
        score += self.career_assists / 600.0
        score += self.career_blocks / 220.0
        score += self.career_steals / 220.0
        score += self.career_games_played / 65.0
        score += max(0, self.peak_ovr - 68) * 0.95
        score += max(0, self.popularity - 45) * 0.12

        if self.is_icon:
            score += 10.0

        if self.career_points >= 8000:
            score += 3.0
        if self.career_games_played >= 300:
            score += 3.0
        if self.peak_ovr >= 85:
            score += 4.0

        self.hall_of_fame_score = round(score, 2)
        return self.hall_of_fame_score

    def evaluate_hall_of_fame(self) -> bool:
        """
        引退時に Hall of Famer かどうかを簡易判定する。
        旧版より少し緩和。
        """
        score = self.calculate_hall_of_fame_score()

        reasons = []
        if self.career_points >= 10000:
            reasons.append("Elite Scorer")
        if self.career_games_played >= 300:
            reasons.append("Longevity")
        if self.peak_ovr >= 85:
            reasons.append("Superstar Peak")
        if self.popularity >= 80:
            reasons.append("Fan Favorite")
        if self.is_icon:
            reasons.append("Icon Player")

        passed = False
        if score >= 34:
            passed = True
        elif self.career_points >= 12000 and self.peak_ovr >= 82:
            passed = True
        elif self.career_games_played >= 420 and self.peak_ovr >= 80:
            passed = True
        elif self.peak_ovr >= 90 and self.career_points >= 7000:
            passed = True

        self.is_hall_of_famer = passed
        self.hall_of_fame_reason = ", ".join(reasons[:3]) if reasons else ""

        return self.is_hall_of_famer

    def print_hall_of_fame_status(self):
        """
        Hall of Fame 状態をコンソール表示する。
        """
        score = self.calculate_hall_of_fame_score()
        status = "YES" if self.is_hall_of_famer else "NO"

        print(f"\n=== {self.name} Hall of Fame ===")
        print(f"Peak OVR: {self.peak_ovr}")
        print(f"Career Points: {self.career_points}")
        print(f"Career Rebounds: {self.career_rebounds}")
        print(f"Career Assists: {self.career_assists}")
        print(f"Career Games: {self.career_games_played}")
        print(f"HOF Score: {score:.2f}")
        print(f"Hall of Famer: {status}")
        if self.hall_of_fame_reason:
            print(f"Reason: {self.hall_of_fame_reason}")

    def is_injured(self) -> bool:
        """ケガをしているかどうか判定"""
        return self.injury_games_left > 0

    def get_effective_ovr(self) -> int:
        """
        実効OVR。
        疲労によるマイナス補正を適用した状態のOVRを計算します。
        """
        return max(0, self.ovr + self._get_fatigue_penalty())

    def get_roster_sort_weight(self) -> float:
        """
        登録・スターター候補の並び順。
        特別指定は市場グレードで主力寄り（SS）／ローテ寄り（S）の位置づけを反映。
        """
        base = float(self.get_effective_ovr())
        if str(getattr(self, "acquisition_type", "") or "") != "special_designation":
            return base
        g = str(getattr(self, "draft_market_grade", "") or "").upper().strip()
        if g == "SS":
            return base + 10.0
        if g == "S":
            return base + 4.0
        return base + 3.0

    def get_adjusted_attribute(self, attr_name: str) -> int:
        """
        特定の能力値（シュートなど）に対して、疲労補正を適用して返します。
        """
        base_value = getattr(self, attr_name, 0)
        return max(0, base_value + self._get_fatigue_penalty())

    def _get_fatigue_penalty(self) -> int:
        """
        疲労度に応じた補正値:
        0-19: 0
        20-39: -2
        40-59: -5
        60-79: -8
        80+: -12
        """
        if self.fatigue >= 80:
            return -12
        elif self.fatigue >= 60:
            return -8
        elif self.fatigue >= 40:
            return -5
        elif self.fatigue >= 20:
            return -2
        return 0

    def reset_season_stats(self):
        """
        シーズンスタッツを0にリセットします。
        """
        self.season_points = 0
        self.season_rebounds = 0
        self.season_assists = 0
        self.season_blocks = 0
        self.season_steals = 0
        self.games_played = 0

    def apply_season_to_career_stats(self):
        """
        シーズン成績を通算成績に加算する。
        歴史システム導入前でも安全に呼べる土台メソッド。
        """
        self.career_points += self.season_points
        self.career_rebounds += self.season_rebounds
        self.career_assists += self.season_assists
        self.career_blocks += self.season_blocks
        self.career_steals += self.season_steals
        self.career_games_played += self.games_played
        self.update_peak_ovr()

    def get_potential_cap_value(self) -> int:
        """
        potential の天井値を整数で返す。
        将来の成長システム用。
        """
        cap_map = {
            "S": 95,
            "A": 90,
            "B": 84,
            "C": 78,
            "D": 72,
        }
        return cap_map.get(self.potential, 78)

    def add_national_team_history(self, entry: dict) -> None:
        if not isinstance(entry, dict):
            return
        if self.national_team_history is None:
            self.national_team_history = []
        self.national_team_history.append(dict(entry))

    def clear_national_team_assignment(self) -> None:
        self.is_on_national_team = False
        self.national_team_type = ""
        self.national_team_country = ""
        self.national_team_return_fatigue_bonus = 0
        if hasattr(self, "national_team_assigned_round"):
            self.national_team_assigned_round = 0

    def is_before_peak(self) -> bool:
        return self.age < self.peak_age

    def is_in_peak(self) -> bool:
        return self.peak_age <= self.age <= self.decline_age

    def is_after_decline(self) -> bool:
        return self.age > self.decline_age

    def _apply_random_fraction(self, val: int, delta: float) -> int:
        """小数の変動分を確率的に整数に繰り上げ・繰り下げるユーティリティ"""
        int_delta = int(delta)
        fraction = abs(delta) - abs(int_delta)
        if random.random() < fraction:
            int_delta += 1 if delta > 0 else -1
        return max(1, min(99, val + int_delta))

    def apply_performance_progression(self, base_change: float) -> int:
        """
        能力の変動を適用し、パフォーマンス（前年成績）に応じた個別能力の成長を行います。
        独自のOVR再計算式は使わず、「各能力値が動いた分の平均」を正確にOVRの変動分として
        同期させることで、既存ジェネレーターの設計と完全に矛盾させない安全な仕組みです。
        """
        old_ovr = self.ovr

        gp = max(1, self.games_played)
        ppg = self.season_points / gp
        rpg = self.season_rebounds / gp
        apg = self.season_assists / gp

        age_dampener = max(0.0, 1.0 - max(0, self.age - 26) * 0.25)
        ovr_dampener = max(0.1, 1.0 - max(0, self.ovr - 75) * 0.04)

        ethic_bonus = 0.85 + (self.work_ethic / 100) * 0.30
        iq_bonus = 0.90 + (self.basketball_iq / 100) * 0.20

        bonus_multiplier = age_dampener * ovr_dampener * ethic_bonus * iq_bonus

        shoot_bonus = 0.0
        drive_bonus = 0.0
        pass_bonus = 0.0
        reb_bonus = 0.0

        if self.games_played >= 10:
            if ppg >= 15.0:
                shoot_bonus = 0.8 * bonus_multiplier
                drive_bonus = 0.8 * bonus_multiplier
            elif ppg >= 10.0:
                shoot_bonus = 0.4 * bonus_multiplier
                drive_bonus = 0.4 * bonus_multiplier

            if apg >= 6.0:
                pass_bonus = 0.8 * bonus_multiplier
            elif apg >= 4.0:
                pass_bonus = 0.4 * bonus_multiplier

            if rpg >= 8.0:
                reb_bonus = 0.8 * bonus_multiplier
            elif rpg >= 5.0:
                reb_bonus = 0.4 * bonus_multiplier

        total_stat_delta = 0
        count = 0

        attr_keys = ['shoot', 'three', 'drive', 'passing', 'rebound', 'defense', 'ft', 'stamina']
        for key in attr_keys:
            if hasattr(self, key):
                current_val = getattr(self, key)

                specific_bonus = 0.0
                if key in ['shoot', 'three']:
                    specific_bonus = shoot_bonus
                elif key == 'drive':
                    specific_bonus = drive_bonus
                elif key == 'passing':
                    specific_bonus = pass_bonus
                elif key == 'rebound':
                    specific_bonus = reb_bonus

                final_change = (base_change * 0.9) + (specific_bonus * 0.7)
                new_val = self._apply_random_fraction(current_val, final_change)
                setattr(self, key, new_val)

                total_stat_delta += (new_val - current_val)
                count += 1

        if count > 0:
            avg_delta = total_stat_delta / count
            self.ovr += round(avg_delta)
            self.ovr = int(max(40, min(99, self.ovr)))

        self.update_peak_ovr()
        return self.ovr - old_ovr
