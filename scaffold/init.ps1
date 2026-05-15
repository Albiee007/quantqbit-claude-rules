#Requires -Version 5.0
# ============================================================================
# Claude Rules Scaffold — PowerShell entrypoint
#
# Thin wrapper around init.sh. Defers all logic to bash because the scaffold
# pipeline (envsubst, find, awk, sed) lives there. If Git Bash (or another
# bash on PATH) is available we forward all args to init.sh and exit with its
# code. Otherwise we print a one-liner pointing the user at Git Bash / WSL.
#
# Usage:
#   .\init.ps1 [options]      # forwards to: bash init.sh [options]
# ============================================================================

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InitSh    = Join-Path $ScriptDir 'init.sh'

if (-not (Test-Path -LiteralPath $InitSh)) {
    Write-Host "[FAIL] Cannot find init.sh next to init.ps1: $InitSh"
    exit 1
}

$bash = Get-Command bash -ErrorAction SilentlyContinue
if ($null -eq $bash) {
    Write-Host "Native PowerShell port not yet implemented. Install Git Bash, WSL, or run init.sh from a bash shell."
    exit 1
}

# Fix E5: disable MSYS auto path conversion. Git Bash mangles arguments that
# look like Unix paths (e.g. --target=/c/foo gets rewritten to a Windows
# path) which breaks --target= and --code-subdir=. Setting MSYS_NO_PATHCONV=1
# is process-scoped (PowerShell child env) so it doesn't pollute the user's
# shell beyond this invocation.
$env:MSYS_NO_PATHCONV = "1"

# Forward all arguments verbatim. Use the bash shim's own path resolution so
# Windows path mangling doesn't trip us up.
& $bash.Source $InitSh @args
exit $LASTEXITCODE
