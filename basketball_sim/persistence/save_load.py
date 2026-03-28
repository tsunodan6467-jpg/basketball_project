"""
セーブデータの読み書き。

目的（初心者向けの説明）:
- ゲームの状態（全チーム・FA選手・進行状況など）をファイルに書き出し、
  あとから続きから再開できるようにする。
- 形式にバージョン番号を付け、将来データ構造が変わっても判別できるようにする。

制約（現段階）:
- シーズン途中の途中ラウンドは保存しない。年度進行メニュー（オフシーズン処理の直後）から保存。
- 実装は pickle（Python 同士の復元向け）。将来 JSON 等に差し替え可能。
"""

from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional

from basketball_sim.config.game_constants import GAME_ID, PAYLOAD_SCHEMA_VERSION
from basketball_sim.utils.paths import saves_dir

SAVE_FORMAT_VERSION = 1


def default_save_dir() -> Path:
    """ユーザーのホーム配下に保存フォルダを置く（プロジェクト外・上書きしにくい）。"""
    return saves_dir()


def default_save_path(slot: str = "quicksave") -> Path:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in slot.strip().lower())
    if not safe:
        safe = "quicksave"
    return default_save_dir() / f"{safe}.sav"


def save_world(path: Path | str, payload: Dict[str, Any]) -> None:
    """
    payload には pickle 可能なオブジェクトのみ入れること。
    必須キーは load_world 側の検証を参照。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "format_version": SAVE_FORMAT_VERSION,
        "game_id": GAME_ID,
        "saved_at_unix": int(time.time()),
        "payload": payload,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)


def load_world(path: Path | str) -> Dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with open(path, "rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise ValueError("セーブファイル形式が不正です。")
    ver = int(blob.get("format_version", 0) or 0)
    if ver > SAVE_FORMAT_VERSION:
        raise ValueError(f"未対応のセーブバージョンです: {ver}（期待以下: {SAVE_FORMAT_VERSION}）")
    if ver < SAVE_FORMAT_VERSION:
        blob = migrate_blob_to_current(blob)
        ver = int(blob.get("format_version", 0) or 0)
    if ver != SAVE_FORMAT_VERSION:
        raise ValueError(f"セーブの移行に失敗しました: {ver}")
    if blob.get("game_id") != GAME_ID:
        raise ValueError("別のゲーム用のセーブファイルの可能性があります。")
    payload = blob.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("セーブ内容が不正です。")
    normalize_payload(payload)
    return payload


def migrate_blob_to_current(blob: Dict[str, Any]) -> Dict[str, Any]:
    """
    ファイル先頭の blob を現在の SAVE_FORMAT_VERSION へ段階的に変換する（将来用フック）。

    現状は形式1のみで中身の変更は無い。バージョンを上げるときはここに分岐を足す。
    """
    ver = int(blob.get("format_version", 0) or 0)
    if ver < 1:
        raise ValueError("セーブファイル形式が古すぎます。")
    # if ver == 1: ... -> bump to 2 など
    return blob


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    旧セーブ互換: 後から追加したキーにデフォルトを入れる（呼び出し側で payload を上書きする）。
    load_world の戻りで必ず通す。
    """
    if "tracked_player_name" not in payload:
        payload["tracked_player_name"] = None
    if "at_annual_menu" not in payload:
        payload["at_annual_menu"] = False
    if "payload_schema_version" not in payload:
        payload["payload_schema_version"] = PAYLOAD_SCHEMA_VERSION
    if "simulation_seed" not in payload:
        payload["simulation_seed"] = None

    teams = payload.get("teams")
    if isinstance(teams, list):
        from basketball_sim.systems.team_tactics import ensure_team_tactics_on_team

        for t in teams:
            try:
                ensure_team_tactics_on_team(t)
            except Exception:
                continue
            try:
                from basketball_sim.systems.sponsor_management import ensure_sponsor_management_on_team

                ensure_sponsor_management_on_team(t)
            except Exception:
                continue
            try:
                from basketball_sim.systems.pr_campaign_management import ensure_pr_campaigns_on_team

                ensure_pr_campaigns_on_team(t)
            except Exception:
                continue
    return payload


def validate_payload(payload: Dict[str, Any]) -> None:
    required = ("teams", "free_agents", "user_team_id", "season_count")
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"セーブデータに不足があります: {', '.join(missing)}")


def find_user_team(teams: Any, user_team_id: int) -> Any:
    """セーブに記録した team_id からユーザークラブを復元する。"""
    for t in teams:
        if getattr(t, "team_id", None) == user_team_id:
            return t
    raise ValueError(f"ユーザークラブ team_id={user_team_id} が見つかりません。")
