# ProofPatch Verification Script for PowerShell
Write-Host "Running ProofPatch environment and test checks..." -ForegroundColor Cyan

# 1. Backend Lint & Formatting
Write-Host "Checking backend lint and formatting with ruff..." -ForegroundColor Yellow
& .venv\Scripts\ruff.exe check backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend lint check failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}
& .venv\Scripts\ruff.exe format --check backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend format check failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 2. Backend Pytest Suite
Write-Host "Running backend tests..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe backend/tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 3. Frontend checks
Write-Host "Running frontend tests, typecheck & build..." -ForegroundColor Yellow
Set-Location frontend
npm test -- --run
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend tests failed!" -ForegroundColor Red
    Set-Location ..
    exit $LASTEXITCODE
}

npm run typecheck
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend typecheck failed!" -ForegroundColor Red
    Set-Location ..
    exit $LASTEXITCODE
}

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    Set-Location ..
    exit $LASTEXITCODE
}
Set-Location ..

Write-Host "All ProofPatch checks passed successfully!" -ForegroundColor Green
