from typing import Any, List, Optional, Tuple
import random

from basketball_sim.config.game_constants import (
    GENERATOR_INITIAL_SALARY_BASE_PER_OVR,
    INITIAL_TEAM_MONEY_NEW_GAME,
)
from basketball_sim.models.player import Player
from basketball_sim.models.team import Team
from basketball_sim.systems.opening_roster_salary_v11 import _MIN_SALARY_D1, _MIN_SALARY_D2_D3
from basketball_sim.systems.season_transaction_rules import cpu_inseason_fa_allowed_for_simulated_round
from basketball_sim.systems.contract_logic import MIN_SALARY_DEFAULT, get_team_payroll
from basketball_sim.systems.salary_cap_budget import get_hard_cap, get_soft_cap, league_level_for_team


FA_SOFT_CAP_SIGNING_BUFFER_RATIO = 0.08
FA_SOFT_CAP_MIN_ROOM = 8_000_000

# オフ手動FA専用: `estimate_fa_market_value` に対する契約額の下限倍率（例: 1.20 → estimate の 120% 未満に押し上げない）。
# CPU 本格FA・`estimate_fa_market_value` の式本体とは独立。d995b48 由来の暫定。
MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER = 1.20

# 旧 estimate の ovr*12000 加算補正を、開幕ロスター単価へ載せ替えるときのスケール除数
_ESTIMATE_FA_LEGACY_OVR_COEFF = 12000


def _scale_fa_estimate_bonus(old_bonus: int) -> int:
    """旧 `ovr*12000` ベース時代の円加算を、GENERATOR_INITIAL_SALARY_BASE_PER_OVR 比で整数スケールする。"""
    return int(old_bonus * GENERATOR_INITIAL_SALARY_BASE_PER_OVR // _ESTIMATE_FA_LEGACY_OVR_COEFF)


def fa_market_floor_for_estimate(*, league_market_division: Optional[int] = None) -> int:
    """
    見積・欠損補完用の最低年俸（opening v1.1 と同一の D1 / D2-D3 床）。

    division が取れないときだけ `MIN_SALARY_DEFAULT`（従来の 300_000）にフォールバックする。
    """
    if league_market_division is None:
        return int(MIN_SALARY_DEFAULT)
    d = int(max(1, min(3, int(league_market_division))))
    if d == 1:
        return int(_MIN_SALARY_D1)
    return int(_MIN_SALARY_D2_D3)


def ensure_fa_market_fields(player: Player, *, league_market_division: Optional[int] = None) -> None:
    """
    FA市場用の安全補完。
    既存セーブでも落ちにくいように最低限の属性を埋める。
    """
    if not hasattr(player, "fa_years_waiting") or player.fa_years_waiting is None:
        player.fa_years_waiting = 0

    if not hasattr(player, "is_retired"):
        player.is_retired = False

    if not hasattr(player, "salary") or player.salary is None:
        player.salary = int(fa_market_floor_for_estimate(league_market_division=league_market_division))

    if not hasattr(player, "contract_years_left") or player.contract_years_left is None:
        player.contract_years_left = 0

    if not hasattr(player, "team_id"):
        player.team_id = None


def ensure_team_fa_market_fields(team: Team) -> None:
    """
    Team側の最低限の安全補完。
    """
    if not hasattr(team, "money") or team.money is None:
        team.money = int(INITIAL_TEAM_MONEY_NEW_GAME)

    if not hasattr(team, "players") or team.players is None:
        team.players = []



def estimate_fa_market_value(player: Player, *, league_market_division: Optional[int] = None) -> int:
    """
    FA市場でのざっくり年俸目安（補助値）。

    インシーズンFA の **主たる契約額** は `inseason_fa_contract_salary`（正本帯＋本値のブレンド）。
    本関数はそのブレンドの入力の一つとして残す。FAプール保存の正本は `fa_pool_market_salary`。

    第1弾: 開幕ロスターと同じ `GENERATOR_INITIAL_SALARY_BASE_PER_OVR` オーダーへ寄せる。
    旧 `ovr*12000` 核に載っていた potential / 年齢 / FA待機の加算は、同じ比率で円額スケールする。
    """
    ensure_fa_market_fields(player, league_market_division=league_market_division)

    ovr = int(getattr(player, "ovr", 0))
    age = int(getattr(player, "age", 25))
    potential = str(getattr(player, "potential", "C")).upper()
    fa_wait = int(getattr(player, "fa_years_waiting", 0))

    raw_linear = int(ovr) * int(GENERATOR_INITIAL_SALARY_BASE_PER_OVR)
    legacy_floor = _scale_fa_estimate_bonus(400_000)
    base = max(raw_linear, legacy_floor)

    potential_bonus_map = {
        "S": 250_000,
        "A": 180_000,
        "B": 100_000,
        "C": 0,
        "D": -80_000,
    }
    base += _scale_fa_estimate_bonus(potential_bonus_map.get(potential, 0))

    if age <= 23:
        base += _scale_fa_estimate_bonus(120_000)
    elif age >= 35:
        base -= _scale_fa_estimate_bonus(220_000)
    elif age >= 32:
        base -= _scale_fa_estimate_bonus(120_000)

    if fa_wait >= 1:
        base -= _scale_fa_estimate_bonus(80_000)
    if fa_wait >= 2:
        base -= _scale_fa_estimate_bonus(120_000)
    if fa_wait >= 3:
        base -= _scale_fa_estimate_bonus(150_000)

    return max(
        int(fa_market_floor_for_estimate(league_market_division=league_market_division)),
        int(base),
    )


def fa_pool_market_salary(player: Player, *, league_division: int = 3) -> int:
    """
    FAプール上の `player.salary` の意味を固定する単一入口: 正本 v1.1 帯ベースの市場基準値。
    最終契約額ではない。`estimate_fa_market_value` は補助ブレンドのみ。
    """
    div = int(max(1, min(3, int(league_division))))
    ensure_fa_market_fields(player, league_market_division=div)
    from basketball_sim.systems.resign_salary_anchor import blend_fa_pool_market_salary

    est = int(estimate_fa_market_value(player, league_market_division=div))
    return int(blend_fa_pool_market_salary(player, div, est))


def resolve_league_market_division_for_fa_pool(
    *,
    team: Optional[Team] = None,
    teams: Optional[List[Team]] = None,
    league_market_division: Optional[int] = None,
) -> int:
    """FA プール用の division 文脈（`normalize_free_agents` と同系統）。"""
    if league_market_division is not None:
        return int(max(1, min(3, int(league_market_division))))
    if team is not None:
        return int(league_level_for_team(team))
    if teams:
        from basketball_sim.systems.resign_salary_anchor import median_league_level_for_teams

        return int(median_league_level_for_teams(teams))
    return 3


def assign_fa_pool_market_salary_on_release_to_fa(
    player: Player,
    *,
    team: Optional[Team] = None,
    teams: Optional[List[Team]] = None,
    league_market_division: Optional[int] = None,
) -> None:
    """
    FA プールへ載せる直前に、年俸が 0 以下なら `fa_pool_market_salary`（市場基準値）へ揃える。

    最終契約額ではない。trim / overflow / 落選などの仮置き用。
    """
    if int(getattr(player, "salary", 0) or 0) > 0:
        return
    div = resolve_league_market_division_for_fa_pool(
        team=team, teams=teams, league_market_division=league_market_division
    )
    player.salary = int(fa_pool_market_salary(player, league_division=div))


def inseason_fa_contract_salary(team: Team, player: Player) -> int:
    """
    インシーズンFA の契約・表示・可否判定に使う年俸（円）。

    正本 v1.1 帯（`get_fa_offer_anchor_band`）を主に、`estimate_fa_market_value` を補助ブレンドする。
    `sign_free_agent(..., contract_salary=None)` / CPU インシーズン補強 / GUI 目安で共通。
    """
    from basketball_sim.systems.resign_salary_anchor import blend_inseason_fa_contract_salary

    div = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=div)
    est = int(estimate_fa_market_value(player, league_market_division=div))
    return int(blend_inseason_fa_contract_salary(team, player, est))


def sync_fa_pool_player_salary_to_estimate(player: Player, league_market_division: int = 3) -> None:
    """
    FAプール正規化専用: `player.salary` を `fa_pool_market_salary`（市場基準値）に揃える。
    関数名は後方互換のため維持。estimate は `fa_pool_market_salary` 内で補助のみ使用。
    **normalize_free_agents からのみ呼ぶこと**（ロスター所属中等への誤爆防止）。
    """
    player.salary = int(fa_pool_market_salary(player, league_division=int(league_market_division)))


def normalize_free_agents(free_agents: List[Player], *, league_market_division: int = 3) -> List[Player]:
    """
    retired選手を除外しつつ、必要属性を補完して返す。
    FAプール上の `player.salary` を `fa_pool_market_salary` に同期し、CPU本格FA等の参照を揃える。
    """
    normalized: List[Player] = []

    for player in free_agents:
        ensure_fa_market_fields(player, league_market_division=int(league_market_division))
        if getattr(player, "is_retired", False):
            continue
        sync_fa_pool_player_salary_to_estimate(player, league_market_division)
        normalized.append(player)

    return normalized


def estimate_fa_contract_years(player: Player) -> int:
    """
    FA契約の安全版年数。
    """
    age = int(getattr(player, "age", 25))
    potential = str(getattr(player, "potential", "C")).upper()

    if age <= 22 and potential in ("S", "A"):
        return 3
    if age <= 28:
        return 2
    if age <= 33:
        return 1
    return 1



def evaluate_team_need_for_player(team: Team, player: Player) -> float:
    """
    チーム需要を簡易評価。
    ポジション不足と若干の戦術適性だけ見る安全版。
    """
    ensure_team_fa_market_fields(team)
    _div_eval = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=_div_eval)

    base_score = float(getattr(player, "ovr", 0))

    player_position = getattr(player, "position", "SF")
    same_pos = sum(1 for p in getattr(team, "players", []) if getattr(p, "position", "SF") == player_position)

    need_bonus = 0.0
    if same_pos <= 1:
        need_bonus += 6.0
    elif same_pos <= 2:
        need_bonus += 3.0

    coach_style = getattr(team, "coach_style", "balanced")
    style_bonus = 0.0

    try:
        if coach_style == "offense":
            if player.get_adjusted_attribute("shoot") >= 70:
                style_bonus += 2.0
        elif coach_style == "defense":
            if player.get_adjusted_attribute("defense") >= 70:
                style_bonus += 2.0
        elif coach_style == "development":
            if str(getattr(player, "potential", "C")).upper() in ("S", "A"):
                style_bonus += 2.0
    except Exception:
        pass

    age = int(getattr(player, "age", 25))
    age_bonus = 0.0
    if age <= 24:
        age_bonus += 1.5
    elif age >= 34:
        age_bonus -= 1.5

    return round(base_score + need_bonus + style_bonus + age_bonus, 2)



def get_team_fa_signing_limit(
    team: Team,
    salary_cap: Optional[int] = None,
) -> int:
    """
    FA契約に使える簡易上限。

    - キャップ未満: 上限まで契約余地あり
    - キャップちょうど〜超過: ルール上は FA 追加不可（市場側の簡易モデル）

    上限額は salary_cap_budget.get_soft_cap（＝リーグ年俸上限 12 億・get_hard_cap と同一）と同一。
    salary_cap を省略時はチーム所属ディビジョンのリーグ年俸上限を使用。
    """
    ensure_team_fa_market_fields(team)

    payroll = get_team_payroll(team)
    if salary_cap is None:
        salary_cap = int(get_hard_cap(league_level=league_level_for_team(team)))
    soft_cap_limit = int(get_soft_cap(salary_cap))

    if payroll >= soft_cap_limit:
        return 0

    if payroll < salary_cap:
        return max(0, soft_cap_limit - payroll)

    buffer_limit = max(FA_SOFT_CAP_MIN_ROOM, int(salary_cap * FA_SOFT_CAP_SIGNING_BUFFER_RATIO))
    return max(0, min(buffer_limit, soft_cap_limit - payroll))



def precheck_user_fa_sign(
    team: Team,
    player: Player,
    *,
    contract_salary: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    GUI 向け: `sign_free_agent` 実行前の可否と簡潔な理由。

    `sign_free_agent` は所持金を見ないため、ここで `can_team_afford_free_agent` も含める。

    `contract_salary` を渡した場合（オフ手動FA・本格FA同型オファー）、その額で所持金・
    サラリー余地を判定する。未指定時は `inseason_fa_contract_salary`（正本帯主＋estimate 補助）。
    """
    from basketball_sim.config.game_constants import CONTRACT_ROSTER_MAX
    from basketball_sim.systems.roster_rules import can_add_contract_player

    ensure_team_fa_market_fields(team)
    _div_pre = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=_div_pre)

    ok_roster, roster_msg = can_add_contract_player(team, player)
    if not ok_roster:
        code = roster_msg or ""
        if code == "contract_roster_full":
            return False, f"本契約ロスターが上限（{CONTRACT_ROSTER_MAX}人）に達しています。"
        if code == "nationality_slot":
            return False, "国籍枠の都合により追加できません。"
        return False, code or "ロスターに追加できません。"

    if not can_team_sign_player_by_japan_rule(team, player):
        return False, "国籍枠・チームルールにより契約できません。"

    if contract_salary is not None:
        sal = int(contract_salary)
        if sal <= 0:
            return False, "本格FAと同型のオファー額が算出できません（0円以下）。"
        afford = can_team_afford_fa_salary(team, sal)
        label = "契約年俸（本格FA同型）"
    else:
        sal = int(inseason_fa_contract_salary(team, player))
        afford = can_team_afford_free_agent(team, player)
        label = "年俸目安"

    if not afford:
        room = int(get_team_fa_signing_limit(team))
        money = int(getattr(team, "money", 0) or 0)
        if money < sal:
            return False, f"所持金が不足しています（{label} {sal:,} 円、所持 {money:,} 円）。"
        return False, (
            f"サラリー上限の契約余地が不足しています（{label} {sal:,} 円、余地 {room:,} 円）。"
        )

    return True, ""


def can_team_afford_free_agent(
    team: Team,
    player: Player,
    salary_cap: Optional[int] = None,
) -> bool:
    """
    所持金 + サラリーキャップの両方で判定する。
    """
    ensure_team_fa_market_fields(team)
    ask = inseason_fa_contract_salary(team, player)
    return can_team_afford_fa_salary(team, ask, salary_cap=salary_cap)


def can_team_afford_fa_salary(
    team: Team,
    ask: int,
    salary_cap: Optional[int] = None,
) -> bool:
    """明示年俸 `ask` で所持金・サラリー契約余地を判定（オフ手動FAの本格FA同型オファー用）。"""
    ensure_team_fa_market_fields(team)
    ask = int(ask)
    if int(getattr(team, "money", 0)) < ask:
        return False
    signing_limit = get_team_fa_signing_limit(team, salary_cap=salary_cap)
    return ask <= signing_limit



def can_team_sign_player_by_japan_rule(team: Team, player: Player) -> bool:
    """
    日本独自ルール用の安全チェック。

    優先順位:
    1. roster_rules.can_add_contract_player（本契約13＋国籍）
    2. Team の can_add_player_by_japan_rule
    3. nationality フォールバック

    目的は CPU FA が明確な枠超過契約をしないようにすること。
    """
    ensure_team_fa_market_fields(team)
    _div_jp = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=_div_jp)

    try:
        from basketball_sim.systems.roster_rules import can_add_contract_player

        ok, _ = can_add_contract_player(team, player)
        return bool(ok)
    except Exception:
        pass

    can_add = getattr(team, "can_add_player_by_japan_rule", None)
    if callable(can_add):
        try:
            return bool(can_add(player))
        except Exception:
            pass

    players = list(getattr(team, "players", []) or [])
    nationality = str(getattr(player, "nationality", "Japan") or "Japan")

    foreign_count = 0
    asia_nat_count = 0
    for existing in players:
        existing_nat = str(getattr(existing, "nationality", "Japan") or "Japan")
        if existing_nat == "Foreign":
            foreign_count += 1
        elif existing_nat in ("Asia", "Naturalized"):
            asia_nat_count += 1

    if nationality == "Foreign":
        return foreign_count < 3
    if nationality in ("Asia", "Naturalized"):
        return asia_nat_count < 1
    return True



def pick_best_free_agent_for_team(team: Team, free_agents: List[Player]) -> Optional[Player]:
    """
    チーム視点で最も欲しいFAを1人返す。
    """
    candidates = []

    _div_pick = int(league_level_for_team(team))
    for player in free_agents:
        ensure_fa_market_fields(player, league_market_division=_div_pick)
        if getattr(player, "is_retired", False):
            continue
        if not can_team_afford_free_agent(team, player):
            continue
        if not can_team_sign_player_by_japan_rule(team, player):
            continue

        score = evaluate_team_need_for_player(team, player)
        score += random.uniform(-0.5, 0.5)
        candidates.append((score, player))

    if not candidates:
        return None

    candidates.sort(key=lambda row: row[0], reverse=True)
    return candidates[0][1]



def sign_free_agent(
    team: Team,
    player: Player,
    *,
    contract_salary: Optional[int] = None,
    contract_years: Optional[int] = None,
) -> None:
    """
    FA契約を反映。
    日本独自ルールの最終ガードもここで行う。

    年俸相当の `money` 即時減算は行わない（R1 / 締めのみ方式）。
    年俸コストはオフ `_process_team_finances` の payroll → `record_financial_result` に一元化する。

    `contract_salary` / `contract_years` を指定した場合（オフ手動FA・CPU本格FA同型のオファー）、
    それをそのまま適用する。未指定時は `inseason_fa_contract_salary` / `estimate_fa_contract_years`。
    """
    ensure_team_fa_market_fields(team)
    _div_sign = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=_div_sign)

    if not can_team_sign_player_by_japan_rule(team, player):
        return

    if contract_salary is not None:
        salary = int(contract_salary)
        years = (
            int(contract_years)
            if contract_years is not None
            else int(estimate_fa_contract_years(player))
        )
    else:
        salary = int(inseason_fa_contract_salary(team, player))
        years = int(estimate_fa_contract_years(player))

    if salary <= 0:
        return

    signing_room = int(get_team_fa_signing_limit(team))
    if salary > signing_room:
        return

    player.salary = salary
    player.contract_years_left = years
    player.fa_years_waiting = 0

    if hasattr(player, "contract_total_years"):
        player.contract_total_years = years
    if hasattr(player, "last_contract_team_id"):
        player.last_contract_team_id = getattr(team, "team_id", None)
    if hasattr(player, "acquisition_type"):
        player.acquisition_type = "free_agent"
    if hasattr(player, "acquisition_note"):
        player.acquisition_note = f"signed_by_{getattr(team, 'name', 'unknown_team')}"

    if hasattr(team, "add_player"):
        team.add_player(player)
    else:
        team.players.append(player)
        player.team_id = getattr(team, "team_id", None)

    if hasattr(team, "add_history_transaction"):
        team.add_history_transaction(
            transaction_type="free_agent_sign",
            player=player,
            note=f"salary={salary} | years={years}",
        )


def offseason_manual_fa_offer_and_years(team: Team, player: Player) -> Tuple[int, int]:
    """
    オフ手動FA（`conduct_free_agency` 直前）専用: CPU 本格FA と同じ
    `free_agency._calculate_offer` / `_determine_contract_years` を読むだけ（本体は変更しない）。

    処理の流れ（`docs/OFFSEASON_MANUAL_FA_ALIGNMENT_PLAN_2026-04.md` と対応）:

    1. **signing_room** … `get_team_fa_signing_limit` による契約可能な年俸余地の上限。
    2. **core_offer（主経路）** … `_calculate_offer`。`player.salary` 等を芯に、予算・キャップで圧縮された額。
    3. **estimate フォールバック** … `core_offer <= 0` かつ余地ありのとき、主経路が 0 でも
       表示＝契約を成立させるため `estimate_fa_market_value` を芯にし `min(estimate, signing_room)` で上書き。
    4. **manual_floor_offer（オフ手動専用下限）** … `estimate * MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER`
       （d995b48 由来の暫定倍率。インシーズンFA には使わない）。
    5. **final_salary** … `max(core_offer, manual_floor_offer)` を `signing_room` でクリップ。

    `_calculate_offer` が 0 になりうる背景: オフFA直前は `_process_team_finances` より前で
    `payroll_budget` が実ペイロールに追いついておらず `room_to_budget` が 0 となりうる、等。
    """
    from basketball_sim.systems.free_agency import _calculate_offer, _determine_contract_years

    ensure_team_fa_market_fields(team)
    _div_manual = int(league_level_for_team(team))
    ensure_fa_market_fields(player, league_market_division=_div_manual)

    # --- 1. サイン可能な年俸余地（キャップ系の単一入口） ---
    signing_room = int(get_team_fa_signing_limit(team))
    has_signing_room = signing_room > 0

    # --- 2. 主経路: CPU 本格FA 同型のオファー芯 ---
    core_offer = int(_calculate_offer(team, player))

    # --- 3. フォールバック: 主経路が 0 以下だがキャップ上は余地があるとき estimate で芯を立てる ---
    estimate_for_floor: Optional[int] = None
    needs_estimate_fallback = core_offer <= 0 and has_signing_room
    if needs_estimate_fallback:
        estimate_for_floor = int(estimate_fa_market_value(player, league_market_division=_div_manual))
        core_offer = min(estimate_for_floor, signing_room)

    if core_offer <= 0:
        return 0, 1

    # 下限計算用に estimate を1回確保（フォールバック済みなら再利用）
    if estimate_for_floor is None:
        estimate_for_floor = int(estimate_fa_market_value(player, league_market_division=_div_manual))

    # --- 4. オフ手動専用下限（estimate × 定数倍率） ---
    manual_floor_offer = int(estimate_for_floor * MANUAL_OFFSEASON_FA_OFFER_FLOOR_MULTIPLIER)

    # --- 5. 下限適用後、signing_room で最終クリップ ---
    final_salary = min(max(core_offer, manual_floor_offer), signing_room)

    if final_salary <= 0:
        return 0, 1

    years = int(_determine_contract_years(player, team, final_salary))
    return final_salary, max(1, years)


def age_free_agents_one_year(free_agents: List[Player]) -> None:
    """
    オフシーズンごとにFA待機年数を進める。
    """
    for player in free_agents:
        ensure_fa_market_fields(player)
        if getattr(player, "is_retired", False):
            continue
        player.fa_years_waiting += 1



def calculate_fa_retirement_probability(player: Player) -> float:
    """
    FA選手用の引退確率。
    - 高齢
    - 低OVR
    - 長期FA
    で上がる
    - peak_ovr が高い元スターはやや粘る
    """
    ensure_fa_market_fields(player)

    age = int(getattr(player, "age", 25))
    ovr = int(getattr(player, "ovr", 0))
    peak_ovr = int(getattr(player, "peak_ovr", ovr))
    fa_wait = int(getattr(player, "fa_years_waiting", 0))

    prob = 0.0

    if age >= 38:
        prob += 0.45
    elif age >= 35:
        prob += 0.22
    elif age >= 32:
        prob += 0.08

    if ovr <= 58:
        prob += 0.20
    elif ovr <= 64:
        prob += 0.10

    if fa_wait >= 1:
        prob += 0.08
    if fa_wait >= 2:
        prob += 0.16
    if fa_wait >= 3:
        prob += 0.24

    if peak_ovr >= 85:
        prob -= 0.12
    elif peak_ovr >= 80:
        prob -= 0.06

    return max(0.01, min(0.95, round(prob, 3)))



def retire_stale_free_agents(free_agents: List[Player]) -> Tuple[List[Player], List[Player]]:
    """
    FA市場から引退する選手を処理。
    戻り値:
    - remaining_free_agents
    - retired_players
    """
    remaining: List[Player] = []
    retired: List[Player] = []

    for player in free_agents:
        ensure_fa_market_fields(player)

        if getattr(player, "is_retired", False):
            retired.append(player)
            continue

        prob = calculate_fa_retirement_probability(player)
        if random.random() < prob:
            player.is_retired = True
            retired.append(player)
        else:
            remaining.append(player)

    return remaining, retired



def maintain_minimum_fa_pool(
    free_agents: List[Player],
    target_minimum: int,
    generator_func=None,
    *,
    league_market_division: int = 3,
) -> List[Player]:
    """
    FA市場が枯れすぎないように最低人数を維持する。
    generator_func は Player を1人返す関数を想定。
    """
    normalized = normalize_free_agents(free_agents, league_market_division=league_market_division)

    if generator_func is None:
        return normalized

    while len(normalized) < max(0, int(target_minimum)):
        try:
            player = generator_func()
        except Exception:
            break

        ensure_fa_market_fields(player, league_market_division=int(league_market_division))
        player.contract_years_left = 0
        player.team_id = None
        # 補充選手の FA プール年俸は `fa_pool_market_salary` を単一正本とする（最終 normalize でも再同期される）
        sync_fa_pool_player_salary_to_estimate(player, int(league_market_division))
        normalized.append(player)

    return normalize_free_agents(normalized, league_market_division=league_market_division)


def _cpu_fa_cycle_participation_probability(team: Any) -> float:
    """
    インシーズン CPU FA サイクル用の薄い参加確率（1.0 = 常に試行）。
    ユーザーチームは常に 1.0（本経路では通常来ないが無変更担保）。
    """
    if bool(getattr(team, "is_user_team", False)):
        return 1.0
    try:
        from basketball_sim.systems.cpu_club_strategy import get_cpu_club_strategy

        a = float(get_cpu_club_strategy(team, None).fa_aggressiveness)
    except Exception:
        return 1.0
    if a != a or abs(a - 1.0) > 0.25:
        return 1.0
    # hold 付近 0.97 を基準に、ag から ±数％相当だけシフト（体感で暴れない）
    p = 0.97 + 0.12 * (a - 1.0)
    return max(0.925, min(0.992, p))


def _cpu_fa_cycle_participation_gate(team: Any) -> bool:
    p = _cpu_fa_cycle_participation_probability(team)
    if p >= 1.0:
        return True
    return random.random() < p


def run_cpu_fa_market_cycle(
    teams: List[Team],
    free_agents: List[Player],
    max_signings_per_team: int = 1,
    *,
    simulated_round: Optional[int] = None,
) -> List[str]:
    """
    CPUチームがFAを拾う簡易サイクル。
    シーズン中FA補強の土台として使える安全版。

    simulated_round: シーズンシミュレーション中のラウンド番号（1始まり）を渡すと、
    レギュラー中トレード/FA締切後は処理しない（空リストを返す）。オフ等で呼ぶ場合は None。
    """
    if simulated_round is not None and not cpu_inseason_fa_allowed_for_simulated_round(
        int(simulated_round)
    ):
        return []

    from basketball_sim.systems.resign_salary_anchor import median_league_level_for_teams

    logs: List[str] = []
    div_m = int(median_league_level_for_teams(teams))
    market = normalize_free_agents(free_agents, league_market_division=div_m)

    for team in teams:
        ensure_team_fa_market_fields(team)

        sign_count = 0
        while sign_count < max_signings_per_team:
            if not _cpu_fa_cycle_participation_gate(team):
                break
            target = pick_best_free_agent_for_team(team, market)
            if target is None:
                break

            if len(getattr(team, "players", [])) >= 14:
                break

            sign_free_agent(team, target)
            if target in market:
                market.remove(target)

            logs.append(
                f"[FA-SIGN] {team.name} signed {target.name} "
                f"(OVR:{getattr(target, 'ovr', 0)}) | "
                f"Salary:{inseason_fa_contract_salary(team, target)} | "
                f"Years:{estimate_fa_contract_years(target)} | "
                f"Payroll:{get_team_payroll(team)} / SoftCap:{int(get_soft_cap(league_level=league_level_for_team(team)))}"
            )
            sign_count += 1

    free_agents.clear()
    free_agents.extend(market)
    return logs
