# scripts/verify.ps1 — Full Gate Verification (V1)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$results = [System.Collections.Generic.List[PSCustomObject]]::new()
$hasFailure = $false

function Record-Check {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "`n>>> Running: $Name" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $Action
        $sw.Stop()
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
            Write-Host "[PASS] $Name ($($sw.Elapsed.TotalSeconds.ToString('F1'))s)" -ForegroundColor Green
            $script:results.Add([PSCustomObject]@{ Check = $Name; Status = "PASS"; Time = "$($sw.Elapsed.TotalSeconds.ToString('F1'))s" })
        } else {
            Write-Host "[FAIL] $Name (Exit code: $LASTEXITCODE)" -ForegroundColor Red
            $script:hasFailure = $true
            $script:results.Add([PSCustomObject]@{ Check = $Name; Status = "FAIL"; Time = "$($sw.Elapsed.TotalSeconds.ToString('F1'))s" })
        }
    } catch {
        $sw.Stop()
        Write-Host "[FAIL] $Name (Error: $_)" -ForegroundColor Red
        $script:hasFailure = $true
        $script:results.Add([PSCustomObject]@{ Check = $Name; Status = "FAIL"; Time = "$($sw.Elapsed.TotalSeconds.ToString('F1'))s" })
    }
}

# 1. Pytest
Record-Check "Backend Tests (pytest)" {
    Set-Location (Join-Path $Root "backend")
    uv run pytest -q
    Set-Location $Root
}

# 2. Mypy
Record-Check "Backend Types (mypy)" {
    Set-Location (Join-Path $Root "backend")
    uv run mypy app
    Set-Location $Root
}

# 3. Ruff
Record-Check "Backend Lint (ruff)" {
    Set-Location (Join-Path $Root "backend")
    uv run ruff check app
    Set-Location $Root
}

# 4. Biome
Record-Check "Frontend Lint (biome)" {
    Set-Location (Join-Path $Root "frontend")
    bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./
    Set-Location $Root
}

# 5. Build
Record-Check "Frontend Bundle Build (bun run build)" {
    Set-Location (Join-Path $Root "frontend")
    bun run build
    Set-Location $Root
}

# 6. Dist Grep
Record-Check "Production Dist Leak Checks (changethis / persona emails)" {
    $distDir = Join-Path $Root "backend\app\frontend"
    if (-not (Test-Path $distDir)) {
        throw "Dist directory does not exist: $distDir"
    }
    $leaks = Get-ChildItem -Path $distDir -Recurse -File | Select-String -Pattern "changethis"
    if ($leaks) {
        throw "Found 'changethis' in dist bundle: $($leaks | Select-Object -First 3)"
    }
    $global:LASTEXITCODE = 0
}

# 7. Capability Map & Coverage
Record-Check "Capability Map Coverage (gen_coverage.py)" {
    Set-Location (Join-Path $Root "backend")
    uv run python ../scripts/gen_coverage.py
    Set-Location $Root
}

# 8. Generated Client Drift
Record-Check "OpenAPI Client Drift Check" {
    git diff --exit-code frontend/src/client
}

# 9. Guide / DEMO.md Drift
Record-Check "Guide / DEMO.md Drift Check" {
    uv run python scripts/generate_demo_md.py
    git diff --exit-code DEMO.md
}

Write-Host "`n=========================================================" -ForegroundColor White
Write-Host "             FULL GATE VERIFICATION SUMMARY" -ForegroundColor White
Write-Host "=========================================================" -ForegroundColor White
$results | Format-Table -AutoSize

if ($hasFailure) {
    Write-Host "Verification GATE FAILED." -ForegroundColor Red
    exit 1
} else {
    Write-Host "ALL CHECKS PASSED. Verification Gate GREEN." -ForegroundColor Green
    exit 0
}
