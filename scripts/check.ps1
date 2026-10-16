# ProofPatch Verification Script for PowerShell
Write-Host "Running ProofPatch environment and test checks..." -ForegroundColor Cyan

# 1. Backend tests
Write-Host "Running backend tests..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe backend/tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 2. Frontend checks
Write-Host "Running frontend tests & build..." -ForegroundColor Yellow
Set-Location frontend
npm test -- --run
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend tests failed!" -ForegroundColor Red
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
