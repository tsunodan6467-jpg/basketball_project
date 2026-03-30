"""
大会別の試合登録（active）／オンザコート（on_court）ルールの単一ソース。

Match / RotationSystem / 将来の injury 補修などが同じ辞書を参照する。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from basketball_sim.config.game_constants import (
    LEAGUE_ONCOURT_ASIA_NATURALIZED_CAP,
    LEAGUE_ONCOURT_FOREIGN_CAP,
    LEAGUE_ROSTER_ASIA_NATURALIZED_CAP,
    LEAGUE_ROSTER_FOREIGN_CAP,
)

COMPETITION_RULES: Dict[str, Dict[str, Dict[str, Any]]] = {
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


def normalize_competition_type(competition_type: Optional[str]) -> str:
    normalized = str(competition_type or "regular_season").strip().lower()
    return normalized if normalized in COMPETITION_RULES else "regular_season"


def get_competition_rule(competition_type: Optional[str], phase: str) -> Dict[str, Any]:
    """
    phase: \"active\"（試合登録）または \"on_court\"（5人制限）
    """
    ct = normalize_competition_type(competition_type)
    rules = COMPETITION_RULES.get(ct, COMPETITION_RULES["regular_season"])
    if phase in rules:
        return rules[phase]
    return COMPETITION_RULES["regular_season"][phase]


def league_contract_active_rule() -> Dict[str, Any]:
    """本契約13人の国籍枠（日本リーグ基準）と試合登録 active は同一数値。"""
    return get_competition_rule("regular_season", "active")
