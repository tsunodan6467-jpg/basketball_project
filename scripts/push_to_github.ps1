# GitHub に初回 push（Phase 0: CI を走らせる）
# このファイルは UTF-8（BOM 付き）で保存（Windows PowerShell 5.1 互換）
#
# 使い方（プロジェクトルートから）:
#   .\scripts\push_to_github.ps1
#   .\scripts\push_to_github.ps1 -RepoName my-basketball-sim

param(
    [string]$RepoName = "basketball_project"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    $git = $gitCmd.Source
} else {
    $git = "C:\Program Files\Git\bin\git.exe"
}
if (-not (Test-Path $git)) {
    Write-Error "git が見つかりません。Git for Windows をインストールしてください。"
    exit 1
}

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    Write-Error "GitHub CLI が見つかりません。winget install GitHub.cli を実行してください。"
    exit 1
}

$authOk = $false
$null = & $gh @("auth", "status") 2>&1
if ($LASTEXITCODE -eq 0) { $authOk = $true }

if (-not $authOk) {
    Write-Host ""
    Write-Host "GitHub CLI にログインしていません。次を実行してから、もう一度このスクリプトを実行してください。"
    Write-Host ('  ' + $gh + ' auth login -h github.com -p https -w')
    Write-Host ""
    exit 1
}

$branch = (& $git @("branch", "--show-current"))
if ($branch) { $branch = $branch.Trim() }
if (-not $branch) { $branch = "main" }

$remoteUrl = ""
$out = & $git @("remote", "get-url", "origin") 2>&1
if ($LASTEXITCODE -eq 0) { $remoteUrl = [string]$out } else { $remoteUrl = "" }

if ($remoteUrl) {
    Write-Host "remote origin あり: $remoteUrl"
    Write-Host "push: $branch を origin へ"
    & $git @("push", "-u", "origin", $branch)
} else {
    Write-Host "GitHub にリポジトリ '$RepoName' を作成し、push します..."
    & $gh @("repo", "create", $RepoName, "--public", "--source=.", "--remote=origin", "--push")
}

Write-Host "完了。GitHub の Actions タブで CI が動いているか確認してください。"
