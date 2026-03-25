# push_to_github.ps1 -- GitHub first push (Phase 0 CI)

# 以下は日本語可。先頭行は ASCII のみ（BOM 二重時のパース事故を防ぐ）

# 使い方: .\scripts\push_to_github.ps1  [-RepoName name]



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



# origin が無いとき git は stderr に出す。Stop だとエラー扱いで止まるため一時的に抑止

$remoteUrl = ""

$prevEap = $ErrorActionPreference

$ErrorActionPreference = "SilentlyContinue"

$out = & $git @("remote", "get-url", "origin") 2>$null

$ec = $LASTEXITCODE

$ErrorActionPreference = $prevEap

if ($ec -eq 0 -and $null -ne $out -and "$out" -ne "") {

    $remoteUrl = [string]$out

}



if ($remoteUrl) {

    Write-Host "remote origin あり: $remoteUrl"

    Write-Host "push: $branch を origin へ"

    & $git @("push", "-u", "origin", $branch)

    if ($LASTEXITCODE -ne 0) {

        Write-Error "git push が失敗しました（上の赤字を確認）。"

        exit 1

    }

} else {

    Write-Host "GitHub にリポジトリ '$RepoName' を作成し、push します..."

    & $gh @("repo", "create", $RepoName, "--public", "--source=.", "--remote=origin", "--push")

    if ($LASTEXITCODE -ne 0) {

        Write-Error "gh repo create または push が失敗しました（上の赤字を確認）。"

        exit 1

    }

}



Write-Host ""

Write-Host "成功: 完了。GitHub の Actions タブで CI が動いているか確認してください。"

