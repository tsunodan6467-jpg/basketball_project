"""
ユーザー環境に書き込むパス（セーブ・ログなど）の共通定義。

Windows では例: C:\\Users\\あなたの名前\\.basketball_sim\\
"""

from __future__ import annotations

from pathlib import Path


def user_data_root() -> Path:
    """アプリ用データのルート（存在しなければ作成）。"""
    p = Path.home() / ".basketball_sim"
    p.mkdir(parents=True, exist_ok=True)
    return p


def saves_dir() -> Path:
    """セーブファイル用フォルダ。"""
    p = user_data_root() / "saves"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """ログ・クラッシュ記録用フォルダ。"""
    p = user_data_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def settings_path() -> Path:
    """
    ユーザー設定（JSON）のパス。

    例: C:\\Users\\あなたの名前\\.basketball_sim\\settings.json
    メモ帳で編集可能。壊れた場合はファイルを消すと既定値に戻ります。
    """
    return user_data_root() / "settings.json"
