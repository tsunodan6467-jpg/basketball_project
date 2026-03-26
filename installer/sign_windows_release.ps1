#Requires -Version 5.1
<#
.SYNOPSIS
  Sign a Windows binary with Authenticode (signtool).

.DESCRIPTION
  Set environment variable SIGNTOOL_PFX_PASSWORD to your PFX password before running.
  Do not commit the PFX file. Prefer a commercial code-signing cert for fewer SmartScreen warnings.

.EXAMPLE
  $env:SIGNTOOL_PFX_PASSWORD = '***'
  .\installer\sign_windows_release.ps1 -TargetPath dist\BasketballGM.exe -PfxPath $HOME\secrets\codesign.pfx

.EXAMPLE
  .\installer\sign_windows_release.ps1 -TargetPath dist\BasketballGM_Setup_0.1.0.exe -PfxPath C:\certs\sign.pfx -Signtool "C:\path\to\signtool.exe"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $TargetPath,

    [Parameter(Mandatory = $true)]
    [string] $PfxPath,

    [string] $TimestampUrl = "http://timestamp.digicert.com",

    [string] $Signtool = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-SignToolPath {
    $roots = @(
        (Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"),
        (Join-Path $env:ProgramFiles "Windows Kits\10\bin")
    )
    foreach ($r in $roots) {
        if (-not (Test-Path -LiteralPath $r)) { continue }
        $hit = Get-ChildItem -LiteralPath $r -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object -Property FullName -Descending |
            Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "TargetPath not found: $TargetPath"
}
if (-not (Test-Path -LiteralPath $PfxPath)) {
    throw "PfxPath not found: $PfxPath"
}

$pass = $env:SIGNTOOL_PFX_PASSWORD
if ([string]::IsNullOrEmpty($pass)) {
    throw "Set environment variable SIGNTOOL_PFX_PASSWORD (PFX password)."
}

$tool = $Signtool
if ([string]::IsNullOrWhiteSpace($tool)) {
    $tool = Find-SignToolPath
}
if ([string]::IsNullOrWhiteSpace($tool) -or -not (Test-Path -LiteralPath $tool)) {
    throw "signtool.exe not found. Install Windows SDK or pass -Signtool with full path."
}

$resolved = (Resolve-Path -LiteralPath $TargetPath).Path
$signArguments = @(
    "sign",
    "/fd", "SHA256",
    "/f", $PfxPath,
    "/p", $pass,
    "/tr", $TimestampUrl,
    "/td", "SHA256",
    $resolved
)

Write-Host "Signing: $resolved"
& $tool @signArguments
if ($LASTEXITCODE -ne 0) {
    throw "signtool sign failed with exit code $LASTEXITCODE"
}

& $tool verify /pa /v $resolved
if ($LASTEXITCODE -ne 0) {
    throw "signtool verify failed with exit code $LASTEXITCODE"
}
Write-Host "OK: $resolved"
