"""テストランナー用: Windows 等でコンソール出力の文字化けを抑える。"""

from __future__ import annotations

import sys


def configure_console_encoding() -> None:
    """
    Windows 環境で日本語ログが文字化けしやすいため、テスト側で stdout/stderr を UTF-8 に寄せる。
    （ゲーム本編の挙動には影響させない）
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
