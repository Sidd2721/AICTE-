# One-command demo bring-up for PowerShell (CHARTER R1, R8)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python scripts/run-demo.py @args
} else {
    python scripts/run-demo.py @args
}
