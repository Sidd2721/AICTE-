<#
.SYNOPSIS
    Share the live FDR Portal demo with anyone over a Cloudflare Tunnel (Sprint 2 Track 1).

.DESCRIPTION
    1. Verifies that the local PostgreSQL database and FastAPI backend are reachable.
    2. Runs demo preparation / reset if requested or if backend is offline.
    3. Checks for `cloudflared` on PATH.
    4. If cloudflared is present, spawns a temporary HTTPS tunnel to http://localhost:8000.
    5. If absent, prints simple winget installation instructions.
#>

[CmdletBinding()]
param(
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Join-Path $ScriptDir ".."
Set-Location $RootDir

Write-Host "`n=== AICTE FDR Portal: Instant Public Share (Track 1) ===" -ForegroundColor Cyan

# 1. Check if backend is responding
$backendHealthy = $false
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/utils/health-check" -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($resp) { $backendHealthy = $true }
} catch {
    $backendHealthy = $false
}

if (-not $backendHealthy -or $Reset) {
    Write-Host "[1/2] Preparing demo state (migrations + rich synthetic seed data)..." -ForegroundColor Yellow
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv run python scripts/run-demo.py --reset --no-launch
    } else {
        python scripts/run-demo.py --reset --no-launch
    }
    
    if (-not $backendHealthy) {
        Write-Host "Backend server is not running on port 8000." -ForegroundColor Yellow
        Write-Host "Please start the backend in a separate terminal window:" -ForegroundColor Yellow
        Write-Host "    powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1`n" -ForegroundColor White
    }
} else {
    Write-Host "[1/2] Local backend detected active on http://localhost:8000" -ForegroundColor Green
}

# 2. Check for cloudflared
Write-Host "[2/2] Checking Cloudflare Tunnel (cloudflared)..." -ForegroundColor Yellow
$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue

if (-not $cloudflaredCmd) {
    Write-Host "`n[!] 'cloudflared' was not found on your system PATH." -ForegroundColor Red
    Write-Host "To share this running portal over an instant public HTTPS tunnel without firewall setup:" -ForegroundColor White
    Write-Host "    winget install Cloudflare.cloudflared" -ForegroundColor Cyan
    Write-Host "Or download the binary directly from:" -ForegroundColor White
    Write-Host "    https://github.com/cloudflare/cloudflared/releases/latest" -ForegroundColor DarkCyan
    Write-Host "`nAfter installation, open a new shell and re-run:" -ForegroundColor White
    Write-Host "    powershell -ExecutionPolicy Bypass -File scripts/share.ps1`n" -ForegroundColor Yellow
    exit 0
}

Write-Host "Starting Cloudflare quick tunnel to http://localhost:8000..." -ForegroundColor Green
Write-Host "Anyone with this link can use the demo logins; share only with your audience; close the tunnel after." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to terminate the public tunnel at any time.`n" -ForegroundColor Gray

& cloudflared tunnel --url http://localhost:8000
