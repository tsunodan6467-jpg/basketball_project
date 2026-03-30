"""
日本独自ルール：選手の枠種別カウントの正本（Match / Team / trade / rotation で共有）。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from basketball_sim.models.player import Player


def player_regulation_bucket(player: Player, *, asia_as_foreign: bool) -> str:
    """
    foreign / special / domestic の3分類。
    nationality は Match 既存どおり大文字始まり（Foreign / Asia / Naturalized）を正とする。
    """
    nat = getattr(player, "nationality", "Japan")
    if nat == "Foreign":
        return "foreign"
    if nat == "Naturalized":
        return "special"
    if nat == "Asia":
        return "foreign" if asia_as_foreign else "special"
    return "domestic"


def player_regulation_bucket_from_rule(player: Player, rule: Dict[str, object]) -> str:
    return player_regulation_bucket(player, asia_as_foreign=bool(rule.get("asia_as_foreign", False)))


def count_regulation_slots(players: List[Player], rule: Dict[str, object]) -> Tuple[int, int]:
    """(foreign カウント, special カウント)"""
    af = bool(rule.get("asia_as_foreign", False))
    foreign = 0
    special = 0
    for p in players:
        b = player_regulation_bucket(p, asia_as_foreign=af)
        if b == "foreign":
            foreign += 1
        elif b == "special":
            special += 1
    return foreign, special


def lineup_passes_on_court(players: List[Player], on_court_rule: Dict[str, object]) -> bool:
    if len(players) != 5:
        return False
    ids = [getattr(p, "player_id", None) for p in players]
    if any(i is None for i in ids):
        return False
    if len(set(ids)) != 5:
        return False
    foreign, special = count_regulation_slots(players, on_court_rule)
    foreign_max = int(on_court_rule.get("foreign_max", 2))
    special_max = int(on_court_rule.get("special_max", 1))
    return foreign <= foreign_max and special <= special_max


def lineup_passes_active(players: List[Player], active_rule: Dict[str, object]) -> bool:
    foreign, special = count_regulation_slots(players, active_rule)
    foreign_max = int(active_rule.get("foreign_max", 3))
    special_max = int(active_rule.get("special_max", 1))
    return foreign <= foreign_max and special <= special_max
