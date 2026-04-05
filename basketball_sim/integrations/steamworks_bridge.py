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
_steam_dll_path: Optional[str] = None
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


def _steam_dll_seems_to_contain_init_symbol(path: Path) -> bool:
    """PE 内に export 名として期待される文字列があるか（取り違え DLL の簡易検査）。"""
    try:
        return b"SteamAPI_Init" in path.read_bytes()
    except OSError:
        return False


def _load_steam_windows_dll(resolved: str) -> ctypes.CDLL:
    """
    Windows で steam_api64.dll を読み込む。

    Python 3.8+ では依存 DLL の探索に exe 横ディレクトリが含まれないことがあるため、
    読み込み前に add_dll_directory を試す。
    """
    parent = str(Path(resolved).resolve().parent)
    add_fn = getattr(os, "add_dll_directory", None)
    if callable(add_fn):
        add_fn(parent)
    return ctypes.CDLL(resolved)


def _get_proc_address(dll: ctypes.CDLL, name: str) -> Optional[int]:
    """Windows: GetProcAddress で export アドレスを取得（ctypes の属性解決が失敗するときのフォールバック）。"""
    if platform.system() != "Windows":
        return None
    handle = getattr(dll, "_handle", None)
    if handle is None:
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    gpa = k32.GetProcAddress
    gpa.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    gpa.restype = ctypes.c_void_p
    proc = gpa(ctypes.c_void_p(handle), name.encode("ascii"))
    if not proc:
        return None
    return int(proc)


def _bind_cdecl_fn(dll: ctypes.CDLL, name: str, restype: Any) -> Optional[Callable[..., Any]]:
    """属性または GetProcAddress + CFUNCTYPE で C 宣言どおりの関数を得る。"""
    try:
        fn = getattr(dll, name)
    except AttributeError:
        addr = _get_proc_address(dll, name)
        if addr is None:
            return None
        fn = ctypes.CFUNCTYPE(restype)(addr)
    fn.argtypes = []
    fn.restype = restype
    return fn


def _missing_steam_core_exports(dll: Any) -> List[str]:
    """ctypes が解決できないコア API 名（診断用）。"""
    missing: List[str] = []
    for n in ("SteamAPI_Init", "SteamAPI_Shutdown", "SteamAPI_RunCallbacks"):
        try:
            getattr(dll, n)
        except AttributeError:
            if isinstance(dll, ctypes.CDLL) and _get_proc_address(dll, n) is not None:
                continue
            missing.append(n)
    return missing


def _bind_core_exports(dll: Any) -> Optional[tuple[Callable[..., bool], Callable[[], None], Callable[[], None]]]:
    if not isinstance(dll, ctypes.CDLL):
        return None
    init_fn = _bind_cdecl_fn(dll, "SteamAPI_Init", ctypes.c_bool)
    if init_fn is None:
        LOG.debug("Steam: SteamAPI_Init が解決できません（属性・GetProcAddress とも失敗）")
        return None
    shutdown_fn = _bind_cdecl_fn(dll, "SteamAPI_Shutdown", None)
    if shutdown_fn is None:
        LOG.debug("Steam: SteamAPI_Shutdown が解決できません")
        return None
    run_fn = _bind_cdecl_fn(dll, "SteamAPI_RunCallbacks", None)
    if run_fn is None:
        LOG.debug("Steam: SteamAPI_RunCallbacks が解決できません")
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
    global _steam_dll, _steam_dll_path, _initialized, _steam_apps_ptr, _steam_user_stats_ptr

    if platform.system() != "Windows":
        LOG.debug("Steam: ネイティブ DLL は Windows のみ対象です。")
        return False

    for path in _steam_dll_candidate_files():
        if not path.is_file():
            continue
        resolved = str(path.resolve())
        try:
            dll = _load_steam_windows_dll(resolved)
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
        _steam_dll_path = resolved
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


def steam_init_diagnostics_lines() -> List[str]:
    """
    --steam-diag 用: try_init_steam が False のときの切り分け（開発者向け）。

    steam_loaded_dll_path が None でも「DLL 未検出」と「SteamAPI_Init が false」は別原因になり得るため、
    候補パスごとに短い理由を返す。
    """
    lines: List[str] = []
    if platform.system() != "Windows":
        lines.append("platform: Windows 以外のためネイティブ Steam DLL は対象外です。")
        return lines
    if _truthy_env("BASKETBALL_SIM_DISABLE_STEAM"):
        lines.append("環境変数 BASKETBALL_SIM_DISABLE_STEAM が有効のため Steam 初期化をスキップしています。")
        return lines

    appid_path = _find_steam_appid_txt()
    if appid_path is not None:
        lines.append(f"steam_appid.txt: {appid_path}")
    else:
        lines.append("steam_appid.txt: （見つかりません。exe と同じフォルダ、またはカレントに配置）")

    if getattr(sys, "frozen", False) and getattr(sys, "executable", None):
        lines.append(f"実行ファイル: {sys.executable}")
    env_dll = os.environ.get("BASKETBALL_SIM_STEAM_DLL", "").strip()
    if env_dll:
        lines.append(f"BASKETBALL_SIM_STEAM_DLL: {env_dll}")

    lines.append(f"Python プロセス: {platform.architecture()[0]}（steam_api64.dll は 64bit 用。ここが 32bit だと DLL は使えません）")
    lines.append("DLL 候補:")
    seen: set[str] = set()
    for path in _steam_dll_candidate_files():
        key = str(path.resolve()) if path.is_file() else str(path)
        if key in seen:
            continue
        seen.add(key)

        if not path.is_file():
            lines.append(f"  なし: {path}")
            continue

        resolved = str(path.resolve())
        lines.append(f"  あり: {resolved}")
        looks_like_steam = _steam_dll_seems_to_contain_init_symbol(Path(resolved))
        lines.append(f"    → ファイル内に 'SteamAPI_Init' 文字列: {looks_like_steam}")
        if not looks_like_steam:
            lines.append(
                "    → 本物の redistributable_bin\\win64\\steam_api64.dll ではない可能性が高いです。"
                " SDK zip を開き直し、検索で見つかった複数候補があれば win64 配下だけを使ってください。"
            )
        try:
            dll = _load_steam_windows_dll(resolved)
        except OSError as exc:
            lines.append(f"    → CDLL 失敗: {exc}")
            continue

        hmod = getattr(dll, "_handle", None)
        lines.append(f"    → LoadLibrary ハンドル: {hmod!r}")
        for sym in ("SteamAPI_Init", "SteamAPI_Shutdown", "SteamAPI_RunCallbacks"):
            try:
                g = getattr(dll, sym)
                get_ok = callable(g)
            except AttributeError:
                get_ok = False
            gpa = _get_proc_address(dll, sym) if hmod is not None else None
            lines.append(
                f"    → {sym}: getattr={'OK' if get_ok else 'NG'}, "
                f"GetProcAddress={'0x%x' % gpa if gpa else 'NULL'}"
            )

        bound = _bind_core_exports(dll)
        if bound is None:
            miss = _missing_steam_core_exports(dll)
            if miss:
                lines.append(
                    "    → 未解決の export: "
                    + ", ".join(miss)
                    + "（上の GetProcAddress がすべて NULL なら DLL が本物でないか、32bit Python 等のアーキ不一致）"
                )
            else:
                lines.append(
                    "    → export は見えるのにバインド失敗（ctypes の型設定で例外の可能性。ログを確認）"
                )
            continue

        init_fn, shutdown_fn, _run_fn = bound
        try:
            ok = bool(init_fn())
        except OSError as exc:
            lines.append(f"    → SteamAPI_Init OSError: {exc}")
            continue
        except Exception as exc:
            lines.append(f"    → SteamAPI_Init 例外: {exc}")
            continue

        lines.append(f"    → SteamAPI_Init 戻り値: {ok}")
        if ok:
            try:
                shutdown_fn()
            except Exception as exc:
                lines.append(f"    → 診断後 Shutdown で例外: {exc}")
            else:
                lines.append("    → （診断のため Init 成功後に Shutdown 済み。続けて本初期化を試します）")
        else:
            lines.append(
                "    → false のときは: Steam クライアント未起動・未ログイン・"
                "steam_appid.txt の App ID 誤り・このアカウントがアプリにアクセスできない等を疑う"
            )
    return lines


def steam_loaded_dll_path() -> Optional[str]:
    """ネイティブ接続時に読み込んだ DLL の絶対パス。未接続なら None。"""
    return _steam_dll_path


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
    global _initialized, _steam_dll, _steam_dll_path, _steam_apps_ptr, _steam_user_stats_ptr
    dll = _steam_dll
    if dll is not None:
        try:
            dll.SteamAPI_Shutdown()
        except Exception as exc:
            LOG.debug("Steam: Shutdown: %s", exc)
        _steam_dll = None
    _steam_dll_path = None
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
