<#
.SYNOPSIS
    Run complete RouteOpt pipeline: setup, benchmarks, tests, dashboard

.DESCRIPTION
    Executes the full RouteOpt pipeline in order:
    1. Environment sync (uv sync or pip install)
    2. Benchmark data verification
    3. Matrix building (if needed)
    4. Baseline algorithms test
    5. OR-Tools benchmarks
    6. Exact MILP verification
    7. Scenario sweeps
    7. Tests
    8. Dashboard launch (optional)

.EXAMPLE
    .\scripts\run_all.ps1
    .\scripts\run_all.ps1 -SkipDashboard
    .\scripts\run_all.ps1 -TimeLimit 60
#>

param(
    [switch]$SkipDashboard,
    [int]$TimeLimit = 30,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "RouteOpt Full Pipeline" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# 1. Environment Sync
Write-Host "`n[1/8] Environment Sync" -ForegroundColor Yellow
if (Test-Path "pyproject.toml") {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "Running uv sync..." -ForegroundColor Gray
        uv sync
    } else {
        Write-Host "Running pip install..." -ForegroundColor Gray
        pip install -r requirements.txt
    }
} else {
    Write-Warning "pyproject.toml not found"
}

# 2. Benchmark Data Check
Write-Host "`n[2/8] Benchmark Data Verification" -ForegroundColor Yellow
$cvrplibDir = "data/raw/benchmark/cvrplib"
$solomonDir = "data/raw/benchmark/solomon"

if (Test-Path $cvrplibDir) {
    $cvrpFiles = Get-ChildItem $cvrplibDir -Filter "*.vrp"
    Write-Host "CVRPLIB instances: $($cvrpFiles.Count)" -ForegroundColor Green
} else {
    Write-Warning "CVRPLIB directory not found"
}

if (Test-Path $solomonDir) {
    $solomonFiles = Get-ChildItem $solomonDir -Filter "*.txt"
    Write-Host "Solomon instances: $($solomonFiles.Count)" -ForegroundColor Green
} else {
    Write-Warning "Solomon directory not found"
}

# 3. Matrix Building (placeholder - matrices built on demand)
Write-Host "`n[3/8] Distance Matrices" -ForegroundColor Yellow
Write-Host "Matrices built on-demand with caching" -ForegroundColor Gray

# 4. Baseline Algorithms Test
Write-Host "`n[4/8] Baseline Algorithms Test" -ForegroundColor Yellow
python -m pytest tests/test_algorithms.py -v
if ($LASTEXITCODE -ne 0) { throw "Baseline algorithm tests failed" }

# 5. OR-Tools Benchmarks
Write-Host "`n[5/8] OR-Tools Benchmarks" -ForegroundColor Yellow
Write-Host "Running quick benchmark on A-n32-k5..." -ForegroundColor Gray
python -c "
import sys
sys.path.insert(0, 'src')
from routeopt.data import load_cvrplib_instance
from routeopt.optimization import solve_cvrp_ortools, ORToolsSolverConfig

inst = load_cvrplib_instance('data/raw/benchmark/cvrplib/A-n32-k5.vrp', 'data/raw/benchmark/cvrplib/A-n32-k5.sol')
config = ORToolsSolverConfig(time_limit_seconds=30, scale_factor=1)
sol = solve_cvrp_ortools(inst, inst.distance_matrix, config=config)
print(f'OR-Tools: {sol.total_distance:.1f} distance, {sol.vehicles_used} vehicles, {sol.status}')
"
if ($LASTEXITCODE -ne 0) { throw "OR-Tools benchmark failed" }

# 6. Exact MILP Verification
Write-Host "`n[6/8] Exact MILP Verification" -ForegroundColor Yellow
python -m pytest tests/test_exact_milp.py -v
if ($LASTEXITCODE -ne 0) { throw "Exact MILP tests failed" }

# 7. Scenario Sweeps
Write-Host "`n[7/8] Scenario Sweeps" -Foreground Color Yellow
python -m pytest tests/test_scenarios.py -v
if ($LASTEXITCODE -ne 0) { throw "Scenario tests failed" }

# 8. All Tests
Write-Host "`n[8/8] Full Test Suite" -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { throw "Some tests failed" }

Write-Host "`n===========================================" -ForegroundColor Green
Write-Host "All pipeline steps completed successfully!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

if (-not $SkipDashboard) {
    Write-Host "`nLaunching Streamlit dashboard..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
    python -m streamlit run app/Home.py
} else {
    Write-Host "`nTo launch dashboard: python -m streamlit run app/Home.py" -ForegroundColor Cyan
}