#Requires -Version 5.1
# === harness sync bootstrap (PowerShell entrypoint) ===
# Thin wrapper: forwards all arguments to harness-sync.sh via Git Bash, so Windows, macOS and
# Linux run the same logic. Prefers Git for Windows' bash over WSL's bash.exe,
# which cannot resolve Windows paths.
# Usage: .$(basename "harness/bin/harness-sync.ps1") [options]   (same options as harness-sync.sh)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$sh = Join-Path $PSScriptRoot 'harness-sync.sh'
if (-not (Test-Path -LiteralPath $sh)) {
    Write-Host "[FAIL] Cannot find harness-sync.sh next to this script: $sh"
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
    Write-Host "[FAIL] Git Bash not found. Install Git for Windows (https://git-scm.com/download/win), or run harness-sync.sh from WSL, macOS or Linux."
    exit 2
}

# Stop MSYS from rewriting arguments that look like Unix paths.
$env:MSYS_NO_PATHCONV = '1'
& $bash $sh @args
exit $LASTEXITCODE
