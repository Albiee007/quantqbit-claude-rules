#Requires -Version 5.1
# === /init-project-scaffold (per-platform starter) (PowerShell entry point) ===
# Thin wrapper: runs init-scaffold.sh with Git Bash so Windows, macOS and Linux share one
# implementation. Git for Windows' bash is preferred over WSL's bash.exe, which
# cannot resolve Windows paths.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scaffold\init-scaffold.ps1 [options]
#   (same options as init-scaffold.sh; run with --help to list them)
#
# Note: do NOT set MSYS_NO_PATHCONV here. bash.exe would pass it on to native
# git.exe / python.exe, which then receive unresolvable /c/... paths.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$sh = Join-Path $PSScriptRoot 'init-scaffold.sh'
if (-not (Test-Path -LiteralPath $sh)) {
    Write-Host "[FAIL] Cannot find init-scaffold.sh next to this script: $sh"
    exit 2
}

$candidates = @()
foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
    if ($base) {
        $candidates += (Join-Path $base 'Git\bin\bash.exe')
        $candidates += (Join-Path $base 'Programs\Git\bin\bash.exe')
    }
}
$bash = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $bash) {
    $cmd = Get-Command bash -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch 'System32') { $bash = $cmd.Source }
}
if (-not $bash) {
    Write-Host "[FAIL] Git Bash not found. Install Git for Windows (https://git-scm.com/download/win)."
    Write-Host "       Or run init-scaffold.sh from WSL, macOS or Linux."
    exit 2
}

# Clear inherited MSYS path-conversion overrides (see note above).
Remove-Item Env:MSYS_NO_PATHCONV -ErrorAction SilentlyContinue
Remove-Item Env:MSYS2_ARG_CONV_EXCL -ErrorAction SilentlyContinue

& $bash $sh @args
exit $LASTEXITCODE
