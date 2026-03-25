# Phase 0: PyInstaller で単一 exe をビルドする（プロジェクトルートで実行）
# 使い方: PowerShell で scripts\build_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "依存: pip install -e `".[build]`" を実行します..."
python -m pip install -e ".[build]"

Write-Host "PyInstaller 実行中..."
python -m PyInstaller --noconfirm BasketballGM.spec

Write-Host "完了: dist\BasketballGM.exe"
