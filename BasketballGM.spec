# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 用。プロジェクトルートで: python -m PyInstaller --noconfirm BasketballGM.spec
# 成果物: dist/BasketballGM.exe（build/ は中間生成）
# 回帰: pip install -r requirements-dev.txt && python -m pytest basketball_sim/tests -q
#        dist\\BasketballGM.exe --smoke（ビルド後の起動確認・対話なし）
# 目的: 単一 exe で CLI を配布試験する（Phase 0: パッケージング）

from PyInstaller.utils.hooks import collect_submodules

# 動的 import やサブパッケージの取りこぼし対策
_hidden = collect_submodules("basketball_sim")

a = Analysis(
    ["basketball_sim/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BasketballGM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
