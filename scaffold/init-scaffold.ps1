#Requires -Version 5.0
# ============================================================================
# Claude Scaffold — PowerShell entrypoint (umbrella dispatcher)
#
# Thin wrapper around init-scaffold.sh. Defers all logic to bash because the
# scaffold pipeline (envsubst, find, awk, sed) lives there. If Git Bash (or
# another bash on PATH) is available we forward all args to init-scaffold.sh
# and exit with its code. Otherwise we print a one-liner pointing the user
# at Git Bash / WSL.
#
# Usage:
#   .\init-scaffold.ps1 [options]   # forwards to: bash init-scaffold.sh [options]
# ============================================================================

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InitSh    = Join-Path $ScriptDir 'init-scaffold.sh'

if (-not (Test-Path -LiteralPath $InitSh)) {
    Write-Host "[FAIL] Cannot find init-scaffold.sh next to init-scaffold.ps1: $InitSh"
    exit 1
}

$bash = Get-Command bash -ErrorAction SilentlyContinue
if ($null -eq $bash) {
    Write-Host "[FAIL] bash not found on PATH."
    Write-Host "       Install Git Bash (https://git-scm.com/download/win) or run init-scaffold.sh under WSL."
    exit 1
}

# Disable MSYS auto path conversion. Git Bash mangles arguments that look
# like Unix paths (e.g. --target=/c/foo gets rewritten to a Windows path)
# which breaks --target=, --src-dir=, etc. Setting MSYS_NO_PATHCONV=1 is
# process-scoped (PowerShell child env) so it doesn't pollute the user's
# shell beyond this invocation. Mirrors init.ps1 fix E5.
$env:MSYS_NO_PATHCONV = "1"

# Forward all arguments verbatim. Use the bash shim's own path resolution so
# Windows path mangling doesn't trip us up.
& $bash.Source $InitSh @args
exit $LASTEXITCODE
