<#
.SYNOPSIS
  Windows entry point for the Actions-independent release toolchain (tools/release).

.DESCRIPTION
  Runs `python -m tools.release` from the repository root with the project's virtual
  environment. It adds nothing of its own: every rule lives in the Python package, so the
  behaviour is the same from PowerShell, Git Bash or a scheduled task.

  Nothing changes the host or the registry unless --execute is given together with an owner
  approval record. See docs/release/RELEASE_AUTOMATION_RUNBOOK.md.

.EXAMPLE
  .\tools\release.ps1 plan --manifest docs\release\samples\release-manifest.d0142d8.sample.json
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
# A linked worktree has no .venv of its own: fall back to the main checkout's.
$common = (& git -C $root rev-parse --path-format=absolute --git-common-dir 2>$null)
$main = if ($common) { Split-Path -Parent $common } else { $root }
# The outer @() keeps a single match an array; otherwise $candidates[0] is its first character.
$candidates = @(@(
    $env:CLM_RELEASE_PYTHON,
    (Join-Path $root '.venv\Scripts\python.exe'),
    (Join-Path $main '.venv\Scripts\python.exe')
) | Where-Object { $_ -and (Test-Path $_) })
$python = if ($candidates) { $candidates[0] } else { 'python' }

Push-Location $root
try {
    & $python -B -m tools.release @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
