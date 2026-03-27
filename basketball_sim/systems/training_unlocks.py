"""
個別練習ドリルの解放条件（UI・CLI・育成で共通参照）。

GUI の表示/ガードと DevelopmentSystem の実効処理を一致させるため、
判定はこのモジュールに集約する。
"""

from typing import Any


def player_drill_lock_reason(team: Any, drill_key: str) -> str:
    coach = str(getattr(team, "coach_style", "balanced") or "balanced")
    tf = int(getattr(team, "training_facility_level", 1) or 1)
    fo = int(getattr(team, "front_office_level", 1) or 1)
    med = int(getattr(team, "medical_facility_level", 1) or 1)
    if drill_key == "speed_agility" and tf < 3:
        return "トレーニング施設Lv3以上で解放"
    if drill_key == "iq_film" and fo < 2:
        return "フロントオフィスLv2以上で解放"
    if drill_key == "defense_footwork" and coach not in {"defense", "development"}:
        return "HCが「守備重視」または「育成」で解放"
    if drill_key == "strength" and med < 2:
        return "メディカル施設Lv2以上で解放"
    return ""
