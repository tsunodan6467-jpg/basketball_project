"""resign_cli_display: CLI 補助表示のみ・落ちないことの軽い検証。"""
from __future__ import annotations

from types import SimpleNamespace

from basketball_sim.systems.resign_cli_display import (
    build_re_sign_depth_hint,
    build_re_sign_priority_label,
    build_re_sign_value_label,
    format_re_sign_cli_hint,
)


def _player(**kw):
    base = dict(
        player_id=1,
        position="SG",
        age=26,
        ovr=68,
        potential="B",
        salary=8_000_000,
        desired_salary=9_000_000,
        three=72,
        shoot=70,
        drive=60,
        passing=58,
        rebound=55,
        defense=74,
        handling=52,
        iq=60,
        speed=65,
        power=58,
        stamina=62,
        ft=68,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_format_hint_non_empty() -> None:
    star = _player(player_id=10, ovr=75, age=28)
    mate = _player(player_id=11, ovr=50, age=22)
    team = SimpleNamespace(league_level=2, players=[star, mate])
    s = format_re_sign_cli_hint(team, star)
    assert s
    assert "優先再契約" in s or "バランス型" in s
    assert "強み:" in s


def test_priority_veteran_cleanup() -> None:
    p = _player(player_id=1, age=35, ovr=55, position="C")
    team = SimpleNamespace(league_level=2, players=[p])
    assert build_re_sign_priority_label(team, p) == "ベテラン整理候補"


def test_priority_future_hold() -> None:
    p = _player(player_id=1, age=22, ovr=58, potential="A", position="PG")
    mates = [_player(player_id=i, ovr=70 + i) for i in range(2, 10)]
    team = SimpleNamespace(league_level=2, players=[p] + mates)
    assert build_re_sign_priority_label(team, p) == "将来確保"


def test_value_label_fallback_no_crash() -> None:
    p = _player()
    team = SimpleNamespace(league_level=2, players=[p])
    v = build_re_sign_value_label(team, p, ask_salary=8_000_000, current_salary=8_000_000)
    assert v in ("残し得", "標準圏", "高額注意", "情報なし")


def test_depth_hint_guard() -> None:
    g = _player(player_id=1, position="PG", ovr=60)
    others = [_player(player_id=i, position="PF", ovr=65) for i in range(2, 6)]
    team = SimpleNamespace(league_level=2, players=[g] + others)
    assert "ガード" in build_re_sign_depth_hint(team, g)
