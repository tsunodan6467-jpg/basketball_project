"""
Steam / Steamworks 連携の受け皿（Phase 0）。

目的:
- 本番で Steam を使うとき、初期化・実績（unlock_achievement）をここに集約する。
- Steam クラウドセーブは初回リリースでは採用しない（ローカルセーブのみ。`STEAMWORKS_DESIGN.md` §3）。
- Rich Presence は v1 では未実装（同 §4）。
- Steam オーバーレイはクライアント設定に従う（コードから無効化しない。トラブル時の案内は同 §5）。
- EULA・プライバシーはストア／文書が主（ゲーム内同意 UI は未。同 §6）。
- Steam なし / 開発中の PC でも必ずクラッシュしない。

環境変数（任意）:
- BASKETBALL_SIM_DISABLE_STEAM=1 … Steam 初期化を試みない（ログは DEBUG のみ）。
- BASKETBALL_SIM_FAKE_STEAM=1 … 接続成功をシミュレート（CI や UI 分岐のテスト用）。
- BASKETBALL_SIM_STEAM_APPID=480 … 将来の SDK 用の App ID ヒント（未使用でも可）。
- BASKETBALL_SIM_STEAM_DLL=… steam_api64.dll（または steam_api.dll）のフルパス（任意）。
- BASKETBALL_SIM_REQUIRE_STEAM_LICENSE=1 … 未購入時に起動終了（settings の steam_require_license でも可）。
- BASKETBALL_SIM_STEAM_LICENSE_STRICT=1 … BIsSubscribed を呼べない場合も終了（既定は警告のうえ続行）。

Steam リリース時:
- パートナー向け Steamworks SDK を配置し、steam_api64.dll を ctypes または公式バインディングで読み込む。
- 開発時は実行ファイルと同じフォルダに steam_appid.txt（App ID のみ1行）を置くのが一般的。

ネイティブ DLL:
- Windows かつ上記 DLL が見つかり SteamAPI_Init が成功したときのみ実接続。失敗時は従来どおり False で継続。
- メインループ（tkinter）では pump_steam_callbacks を定期的に呼ぶ必要がある（MainMenuView が担当）。

設計の整理（API 優先度・クラウド要否・コールバック方針）:
- 同ディレクトリの STEAMWORKS_DESIGN.md を参照。
"""

from __future__ import annotations

import atexit
import ctypes
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import basketball_sim.config.steam_achievements as _steam_achievements_cfg

LOG = logging.getLogger("basketball_sim.steam")

_initialized: bool = False
_app_id_hint: Optional[int] = None
_steam_dll: Optional[ctypes.CDLL] = None
_steam_apps_ptr: Optional[int] = None
_steam_user_stats_ptr: Optional[int] = None

_STEAM_ACHIEVEMENT_NAME_MAX_LEN = 128


def _truthy_env(name: str) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    return raw in ("1", "true", "yes", "y", "on")


def _parse_app_id() -> Optional[int]:
    raw = os.environ.get("BASKETBALL_SIM_STEAM_APPID", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        LOG.warning("BASKETBALL_SIM_STEAM_APPID が整数ではありません: %s", raw)
        return None


def _find_steam_appid_txt() -> Optional[Path]:
    """実行ファイル直下またはカレントに steam_appid.txt があればそのパス。"""
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        candidates.append(Path(sys.executable).resolve().parent / "steam_appid.txt")
    candidates.append(Path.cwd() / "steam_appid.txt")
    for p in candidates:
        if p.is_file():
            return p
    return None


def _steam_dll_names() -> List[str]:
    bits = platform.architecture()[0]
    if bits == "64bit":
        return ["steam_api64.dll", "steam_api.dll"]
    return ["steam_api.dll", "steam_api64.dll"]


def _steam_dll_candidate_files() -> List[Path]:
    names = _steam_dll_names()
    out: List[Path] = []
    env = os.environ.get("BASKETBALL_SIM_STEAM_DLL", "").strip()
    if env:
        out.append(Path(env))
    base_dirs: List[Path] = []
    if getattr(sys, "frozen", False) and getattr(sys, "executable", None):
        base_dirs.append(Path(sys.executable).resolve().parent)
    base_dirs.append(Path.cwd())
    for d in base_dirs:
        for n in names:
            out.append(d / n)
    return out


def _bind_core_exports(dll: ctypes.CDLL) -> Optional[tuple[Callable[..., bool], Callable[[], None], Callable[[], None]]]:
    try:
        init_fn = dll.SteamAPI_Init
        init_fn.argtypes = []
        init_fn.restype = ctypes.c_bool
        shutdown_fn = dll.SteamAPI_Shutdown
        shutdown_fn.argtypes = []
        shutdown_fn.restype = None
        run_fn = dll.SteamAPI_RunCallbacks
        run_fn.argtypes = []
        run_fn.restype = None
    except AttributeError:
        return None
    return (init_fn, shutdown_fn, run_fn)


def _try_get_isteam_apps(dll: ctypes.CDLL) -> Optional[int]:
    """SteamAPI_SteamApps_vNNN から ISteamApps* を取得（SDK 版差に対応）。"""
    for v in range(50, 7, -1):
        name = f"SteamAPI_SteamApps_v{v:03d}"
        try:
            fn = getattr(dll, name)
        except AttributeError:
            continue
        fn.argtypes = []
        fn.restype = ctypes.c_void_p
        try:
            ptr = fn()
        except Exception:
            continue
        if ptr:
            LOG.debug("Steam: %s -> ISteamApps*", name)
            return int(ptr)
    return None


def _try_get_isteam_user_stats(dll: ctypes.CDLL) -> Optional[int]:
    """SteamAPI_SteamUserStats_vNNN から ISteamUserStats* を取得。"""
    for v in range(50, 7, -1):
        name = f"SteamAPI_SteamUserStats_v{v:03d}"
        try:
            fn = getattr(dll, name)
        except AttributeError:
            continue
        fn.argtypes = []
        fn.restype = ctypes.c_void_p
        try:
            ptr = fn()
        except Exception:
            continue
        if ptr:
            LOG.debug("Steam: %s -> ISteamUserStats*", name)
            return int(ptr)
    return None


def _try_native_init() -> bool:
    """DLL が利用可能なら SteamAPI_Init まで試す。成功時のみ True。"""
    global _steam_dll, _initialized, _steam_apps_ptr, _steam_user_stats_ptr

    if platform.system() != "Windows":
        LOG.debug("Steam: ネイティブ DLL は Windows のみ対象です。")
        return False

    for path in _steam_dll_candidate_files():
        if not path.is_file():
            continue
        resolved = str(path.resolve())
        try:
            dll = ctypes.CDLL(resolved)
        except OSError as exc:
            LOG.debug("Steam: DLL を読み込めませんでした %s (%s)", path, exc)
            continue
        bound = _bind_core_exports(dll)
        if bound is None:
            LOG.debug("Steam: SteamAPI_* が見つかりません: %s", path)
            continue
        init_fn, _shutdown_fn, _run_fn = bound
        try:
            ok = bool(init_fn())
        except OSError as exc:
            LOG.info("Steam: SteamAPI_Init が OSError: %s (%s)", path, exc)
            continue
        except Exception as exc:
            LOG.warning("Steam: SteamAPI_Init が例外終了: %s (%s)", path, exc)
            continue
        if not ok:
            LOG.info(
                "Steam: SteamAPI_Init が false（クライアント未起動・App ID 不一致など）: %s",
                path,
            )
            continue
        _steam_dll = dll
        _initialized = True
        _steam_apps_ptr = _try_get_isteam_apps(dll)
        if _steam_apps_ptr is None:
            LOG.warning(
                "Steam: ISteamApps を取得できませんでした（SDK と DLL の版が合わない可能性）。"
            )
        _steam_user_stats_ptr = _try_get_isteam_user_stats(dll)
        if _steam_user_stats_ptr is None:
            LOG.debug(
                "Steam: ISteamUserStats を取得できませんでした（実績 API は利用不可）。"
            )
        atexit.register(shutdown_steam)
        LOG.info("Steam: ネイティブ API 初期化 OK (%s)", path)
        return True
    return False


def steam_is_subscribed() -> Optional[bool]:
    """
    ISteamApps::BIsSubscribed の結果。ネイティブ未接続・API 不足時は None。
    """
    global _steam_apps_ptr
    dll = _steam_dll
    if dll is None:
        return None
    if _steam_apps_ptr is None:
        _steam_apps_ptr = _try_get_isteam_apps(dll)
    if _steam_apps_ptr is None:
        return None
    try:
        fn = dll.SteamAPI_ISteamApps_BIsSubscribed
    except AttributeError:
        return None
    fn.argtypes = [ctypes.c_void_p]
    fn.restype = ctypes.c_bool
    try:
        return bool(fn(ctypes.c_void_p(_steam_apps_ptr)))
    except Exception:
        return None


def unlock_achievement(api_name: str) -> bool:
    """
    ISteamUserStats::SetAchievement（成功時は可能なら StoreStats）。

    - ネイティブ未接続: False（クラッシュしない）。
    - BASKETBALL_SIM_FAKE_STEAM: DEBUG ログのうえ True（分岐テスト用）。
    - steam_achievements.STEAM_ACHIEVEMENT_API_NAMES が空でないとき、
      未登録の API 名は警告して False（ダッシュボードとのズレ防止）。
    """
    if not isinstance(api_name, str):
        return False
    name = api_name.strip()
    if not name or len(name) > _STEAM_ACHIEVEMENT_NAME_MAX_LEN:
        LOG.debug("Steam: unlock_achievement: 無効な API 名")
        return False
    reg = _steam_achievements_cfg.STEAM_ACHIEVEMENT_API_NAMES
    if reg and name not in reg:
        LOG.warning(
            "Steam: unlock_achievement: steam_achievements.py に未登録の API 名: %s",
            name,
        )
        return False

    if _truthy_env("BASKETBALL_SIM_FAKE_STEAM"):
        LOG.debug("Steam: unlock_achievement (FAKE): %s", name)
        return True

    dll = _steam_dll
    if dll is None:
        return False

    global _steam_user_stats_ptr
    if _steam_user_stats_ptr is None:
        _steam_user_stats_ptr = _try_get_isteam_user_stats(dll)
    if _steam_user_stats_ptr is None:
        LOG.debug("Steam: unlock_achievement: ISteamUserStats なし")
        return False

    try:
        set_fn = dll.SteamAPI_ISteamUserStats_SetAchievement
    except AttributeError:
        return False
    set_fn.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    set_fn.restype = ctypes.c_bool
    try:
        ok = bool(
            set_fn(
                ctypes.c_void_p(_steam_user_stats_ptr),
                name.encode("utf-8"),
            )
        )
    except Exception as exc:
        LOG.debug("Steam: SetAchievement: %s", exc)
        return False
    if not ok:
        return False
    try:
        store_fn = dll.SteamAPI_ISteamUserStats_StoreStats
        store_fn.argtypes = [ctypes.c_void_p]
        store_fn.restype = ctypes.c_bool
        store_fn(ctypes.c_void_p(_steam_user_stats_ptr))
    except Exception as exc:
        LOG.debug("Steam: StoreStats: %s", exc)
    return True


def _steam_license_required(settings: Optional[Dict[str, Any]]) -> bool:
    if _truthy_env("BASKETBALL_SIM_REQUIRE_STEAM_LICENSE"):
        return True
    if isinstance(settings, dict) and bool(settings.get("steam_require_license")):
        return True
    return False


def enforce_steam_license(settings: Optional[Dict[str, Any]] = None) -> None:
    """
    settings / 環境変数で有効なとき、ネイティブ Steam で未購入なら終了する。
    BASKETBALL_SIM_FAKE_STEAM 時はスキップ（開発・テスト用）。
    """
    if not _steam_license_required(settings):
        return
    if _truthy_env("BASKETBALL_SIM_FAKE_STEAM"):
        LOG.debug("Steam: ライセンス強制は FAKE_STEAM のためスキップ")
        return
    if not is_steam_initialized():
        LOG.error(
            "Steam: ライセンス確認が有効ですが Steam に接続できませんでした。"
        )
        sys.exit(2)
    if not steam_native_loaded():
        LOG.error(
            "Steam: ライセンス確認が有効ですがネイティブ Steam API に接続していません。"
        )
        sys.exit(5)
    sub = steam_is_subscribed()
    if sub is False:
        print("このゲームは Steam での購入が必要です。", file=sys.stderr)
        sys.exit(3)
    if sub is None:
        if _truthy_env("BASKETBALL_SIM_STEAM_LICENSE_STRICT"):
            LOG.error(
                "Steam: STEAM_LICENSE_STRICT により BIsSubscribed 利用不可時は終了します。"
            )
            sys.exit(4)
        LOG.warning(
            "Steam: BIsSubscribed を確認できませんでした。緩格モードのため起動を続けます。"
        )


def steam_native_loaded() -> bool:
    """ctypes で Steam API DLL を読み込み Init 済みなら True（フェイク初期化は含まない）。"""
    return _steam_dll is not None


def is_steam_initialized() -> bool:
    """try_init_steam が成功したあと True（フェイク含む）。"""
    return _initialized


def pump_steam_callbacks() -> None:
    """SteamAPI_RunCallbacks。ネイティブ未接続なら何もしない。"""
    dll = _steam_dll
    if dll is None:
        return
    try:
        dll.SteamAPI_RunCallbacks()
    except Exception as exc:
        LOG.debug("Steam: RunCallbacks: %s", exc)


def shutdown_steam() -> None:
    """
    SteamAPI_Shutdown（ネイティブ接続時）と内部状態のクリア。
    フェイク初期化のみの場合はフラグのみオフ。
    """
    global _initialized, _steam_dll, _steam_apps_ptr, _steam_user_stats_ptr
    dll = _steam_dll
    if dll is not None:
        try:
            dll.SteamAPI_Shutdown()
        except Exception as exc:
            LOG.debug("Steam: Shutdown: %s", exc)
        _steam_dll = None
    _steam_apps_ptr = None
    _steam_user_stats_ptr = None
    _initialized = False


def try_init_steam() -> bool:
    """
    Steam API を初期化する。成功なら True。

    - 未統合の環境では False（クラッシュしない）。
    - BASKETBALL_SIM_FAKE_STEAM で True を返せる（テスト用）。
    - Windows で steam_api64.dll 等があり SteamAPI_Init が成功すれば True。
    """
    global _initialized, _app_id_hint

    if _initialized:
        return True

    if _truthy_env("BASKETBALL_SIM_DISABLE_STEAM"):
        LOG.debug("Steam: BASKETBALL_SIM_DISABLE_STEAM によりスキップ")
        return False

    _app_id_hint = _parse_app_id()
    appid_file = _find_steam_appid_txt()
    if appid_file is not None:
        LOG.debug("Steam: steam_appid.txt を検出: %s", appid_file)

    if _truthy_env("BASKETBALL_SIM_FAKE_STEAM"):
        _initialized = True
        LOG.info(
            "Steam: フェイク初期化 OK（BASKETBALL_SIM_FAKE_STEAM）。実 API は未接続。"
        )
        return True

    if _try_native_init():
        return True

    LOG.debug(
        "Steam: ネイティブ DLL なし、または Init 失敗。クライアントなしで続行します。"
    )
    return False
