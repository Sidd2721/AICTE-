# Prerequisite doctor command wrapper for PowerShell (CHARTER R2, R8)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python scripts/doctor.py
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python scripts/doctor.py
} else {
    Write-Error "Neither uv nor python found on PATH. Please install uv or Python 3.14."
}
