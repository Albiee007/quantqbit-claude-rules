---
paths:
  - "**/*.ps1"
  - "**/*.psm1"
  - "**/*.psd1"
---

# PowerShell Conventions

## Pairing

Scripts for developer workstations ship as a `.ps1` + `.sh` pair with the same name, flags and behaviour, so Windows, macOS and Linux all work without modification. A thin `.ps1` wrapper that hands off to Git Bash is acceptable when the logic is complex. Say so in the header comment.

## Safety header

```powershell
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
```

## Style

- Functions use approved `Verb-Noun` names (`Get-Verb`) with a `[CmdletBinding()]` `param()` block.
- Use full cmdlet names in scripts, never aliases (`Get-ChildItem`, not `ls`/`gci`).
- Write paths with `Join-Path`. Never build them by string concatenation or with hardcoded `C:\Users\...`.
- Target Windows PowerShell 5.1 unless the project declares `pwsh` 7+:
  - no `&&`, `||`, `?:` or `??`
  - no `ConvertFrom-Json -AsHashtable`
- When writing a file other tools will read, pass `-Encoding utf8` explicitly. Line endings follow `.gitattributes` (`*.ps1 eol=crlf`).
- Use `Write-Host` for user-facing progress only. Emit data objects on the pipeline.
- Log markers `[INFO] [OK] [WARN] [FAIL]` match the bash scripts.

## Native commands

- Check `$LASTEXITCODE` after every native executable call. `$ErrorActionPreference` does not cover them.
- Quote arguments that contain spaces. Use `--%` only when truly necessary.

## Verification

- Parse check: `[System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$errors)` must return no errors.
- Run `Invoke-ScriptAnalyzer -Path <file>` if PSScriptAnalyzer is installed.
